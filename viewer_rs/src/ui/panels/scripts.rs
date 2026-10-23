//! Squirrel script browser: decompiled pseudo-source or disassembly text + function outline.

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::ui::{Lang, TextState};
use crate::utils::{human_count, human_size};

#[derive(Clone, Copy, PartialEq, Eq, Default)]
enum SortKey {
    #[default]
    Name,
    Size,
}

#[derive(Default)]
pub struct ScriptsPanel {
    pub query: String,
    sort: SortKey,
    sort_desc: bool,
    list: Vec<usize>,
    selected: Option<usize>,
    dirty: bool,
    request: Option<String>,
    func_index: Option<usize>,
    outline: Vec<(String, String, String)>,
    text: TextState,
    find: String,
    scroll_to: Option<usize>,
    /// Show `script.decompiled.nut` (read-only) instead of the editable disassembly.
    show_decompiled: bool,
    /// Whether the loaded text came from the decompiled file.
    loaded_decompiled: bool,
}

impl ScriptsPanel {
    pub fn new() -> Self {
        Self {
            dirty: true, // build the pack list on first show
            show_decompiled: true,
            ..Default::default()
        }
    }
}

impl ScriptsPanel {
    pub fn request(&mut self, query: &str) {
        self.request = Some(query.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.sort = SortKey::Name;
        self.sort_desc = false;
        self.dirty = true;
    }

    fn sort_list(&mut self, data: &crate::app::Data) {
        let desc = self.sort_desc;
        self.list.sort_by(|a, b| {
            let sa = &data.scripts.items[*a];
            let sb = &data.scripts.items[*b];
            let ord = match self.sort {
                SortKey::Name => sa.area.to_lowercase().cmp(&sb.area.to_lowercase()),
                SortKey::Size => sa.size.cmp(&sb.size),
            };
            if desc { ord.reverse() } else { ord }
        });
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if !app.data().is_some_and(|d| d.scripts.ready) {
        ui.label(theme::dim_label("indexing scripts\u{2026}"));
        return;
    }
    if let Some(query) = app.panels.scripts.request.take() {
        app.panels.scripts.query = query;
        app.panels.scripts.dirty = true;
    }
    if app.panels.scripts.dirty {
        if let Some(data) = app.data.as_deref() {
            let panel = &mut app.panels.scripts;
            panel.list = data.scripts.search(&panel.query);
            panel.sort_list(data);
            panel.dirty = false;
            if let Some(name) = panel.request.take() {
                if let Some(index) = panel
                    .list
                    .iter()
                    .copied()
                    .find(|i| data.scripts.items[*i].area == name)
                    .or_else(|| data.scripts.items.iter().position(|s| s.area == name))
                {
                    panel.selected = Some(index);
                }
            }
        }
    }

    egui::Panel::left("script_list")
        .exact_size(260.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Script packs"));
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.scripts.query)
                        .hint_text("Search areas\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.scripts.dirty = true;
            }
            ui.label(theme::faint_label(format!(
                "{} packs",
                human_count(app.panels.scripts.list.len())
            )));
            ui.horizontal(|ui| {
                egui::ComboBox::from_id_salt("script_sort")
                    .selected_text(match app.panels.scripts.sort {
                        SortKey::Name => "Sort: name",
                        SortKey::Size => "Sort: size",
                    })
                    .show_ui(ui, |ui| {
                        for (key, label) in [(SortKey::Name, "Name"), (SortKey::Size, "Size")] {
                            if ui.selectable_label(app.panels.scripts.sort == key, label).clicked() {
                                app.panels.scripts.sort = key;
                                app.panels.scripts.dirty = true;
                            }
                        }
                    });
                if ui.button(if app.panels.scripts.sort_desc { "Descending" } else { "Ascending" }).clicked() {
                    app.panels.scripts.sort_desc = !app.panels.scripts.sort_desc;
                    app.panels.scripts.dirty = true;
                }
            });
            ui.separator();
            let list = app.panels.scripts.list.clone();
            let selected = app.panels.scripts.selected;
            let mut clicked = None;
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("script_scroll")
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::remainder().at_least(90.0))
                .column(Column::exact(80.0))
                .header(20.0, |mut header| {
                    for title in ["Script pack", "Size"] {
                        header.col(|ui| {
                            ui.label(theme::faint_label(title));
                        });
                    }
                })
                .body(|body| {
                    body.rows(18.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let Some(script) = app.data.as_deref().and_then(|d| d.scripts.items.get(index))
                        else {
                            return;
                        };
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            ui.label(egui::RichText::new(script.area.clone()).size(12.0));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(human_size(script.size)));
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(index) = clicked {
                app.panels.scripts.selected = Some(index);
                app.panels.scripts.outline.clear();
                app.panels.scripts.text = TextState::default();
                app.panels.scripts.func_index = None;
            }
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let Some(index) = app.panels.scripts.selected else {
                ui.label(theme::faint_label("Select a script pack."));
                return;
            };
            let Some(data) = app.data.as_deref() else { return };
            let Some(script) = data.scripts.items.get(index) else { return };
            let area = script.area.clone();
            let decompiled = crate::data::scripts::decompiled_path(&script.path);
            let use_decompiled = app.panels.scripts.show_decompiled && decompiled.is_some();
            let path = match (&decompiled, use_decompiled) {
                (Some(p), true) => p.clone(),
                _ => script.path.clone(),
            };
            let size = crate::data::file_size(&path);
            if app.panels.scripts.loaded_decompiled != use_decompiled {
                app.panels.scripts.text = TextState::default();
                app.panels.scripts.func_index = None;
            }
            if app.panels.scripts.text.lines.is_empty() {
                let text = app
                    .data
                    .as_mut()
                    .map(|d| d.scripts.text(&path))
                    .unwrap_or_default();
                let outline = app
                    .data
                    .as_deref()
                    .map(|d| {
                        if use_decompiled {
                            d.scripts.outline_decompiled(&text)
                        } else {
                            d.scripts.outline(&text)
                        }
                    })
                    .unwrap_or_default();
                app.panels.scripts.loaded_decompiled = use_decompiled;
                let mut state = TextState::default();
                state.set(&text, Lang::Nut);
                app.panels.scripts.text = state;
                app.panels.scripts.outline = outline;
            }
            ui.horizontal(|ui| {
                ui.label(theme::heading(area.clone()));
                ui.label(theme::dim_label(format!(
                    "{} lines  \u{b7}  {} functions  \u{b7}  {}",
                    human_count(app.panels.scripts.text.lines.len()),
                    human_count(app.panels.scripts.outline.len()),
                    human_size(size)
                )));
            });
            ui.horizontal(|ui| {
                ui.add_enabled_ui(decompiled.is_some(), |ui| {
                    let panel = &mut app.panels.scripts;
                    ui.selectable_value(&mut panel.show_decompiled, true, "Decompiled")
                        .on_hover_text("Read-only pseudo-source from tools/squirrel_decompile.py")
                        .on_disabled_hover_text("No script.decompiled.nut: run python tools/squirrel_decompile.py --all");
                    ui.selectable_value(&mut panel.show_decompiled, false, "Disassembly")
                        .on_hover_text("script.nut: the editable assembly listing");
                });
                if use_decompiled {
                    ui.label(theme::faint_label("read-only, edit the disassembly"));
                }
                ui.separator();
                ui.add(
                    egui::TextEdit::singleline(&mut app.panels.scripts.find)
                        .hint_text("Find in file\u{2026}")
                        .desired_width(220.0),
                );
                if ui.button("Find").clicked() {
                    let needle = app.panels.scripts.find.to_lowercase();
                    if !needle.is_empty() {
                        let found = app
                            .panels
                            .scripts
                            .text
                            .lines
                            .iter()
                            .position(|l| l.to_lowercase().contains(&needle));
                        app.panels.scripts.scroll_to = found;
                    }
                }
                if ui.button("Copy path").clicked() {
                    ui.ctx().copy_text(path.to_string_lossy().into_owned());
                }
            });
            ui.separator();
            egui::Panel::right("script_functions")
                .default_size(260.0)
                .resizable(true)
                .size_range(180.0..=520.0)
                .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(6)))
                .show(ui, |ui| {
                    ui.label(theme::faint_label("Functions in this pack"));
                    let outline = app.panels.scripts.outline.clone();
                    let selected = app.panels.scripts.func_index;
                    let mut clicked = None;
                    egui::ScrollArea::vertical()
                        .id_salt("script_outline")
                        .auto_shrink([false, false])
                        .show_rows(ui, 17.0, outline.len(), |ui, range| {
                            for row in range {
                                let (name, args, comment) = &outline[row];
                                let text = egui::RichText::new(crate::utils::elide(
                                    &format!("{name}({args}) {comment}"),
                                    58,
                                ))
                                .monospace()
                                .size(11.0);
                                if ui.selectable_label(selected == Some(row), text).clicked() {
                                    clicked = Some(row);
                                }
                            }
                        });
                    if let Some(row) = clicked {
                        app.panels.scripts.func_index = Some(row);
                        let needle = if app.panels.scripts.loaded_decompiled {
                            format!("function {}(", outline[row].0)
                        } else {
                            format!("function '{}'", outline[row].0)
                        };
                        let found = app
                            .panels
                            .scripts
                            .text
                            .lines
                            .iter()
                            .position(|l| l.contains(&needle));
                        app.panels.scripts.scroll_to = found;
                    }
                });
            let mut state = std::mem::take(&mut app.panels.scripts.text);
            state.scroll_to = app.panels.scripts.scroll_to.take();
            crate::ui::text_view(ui, "script_text", &state, true);
            app.panels.scripts.text = state;
        });
}
