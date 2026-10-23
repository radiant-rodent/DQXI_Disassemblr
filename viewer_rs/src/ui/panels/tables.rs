//! Parameter table browser (BXON JSON as a tree + raw text).

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::ui::{Lang, TextState};
use crate::utils::{human_count, human_size};

#[derive(Clone, Copy, PartialEq, Eq, Default)]
enum Tab {
    #[default]
    Tree,
    Raw,
    Summary,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum SortKey {
    Name,
    Category,
    Size,
}

impl Default for SortKey {
    fn default() -> Self { Self::Name }
}

pub struct TablesPanel {
    pub query: String,
    pub category: Option<String>,
    sort: SortKey,
    sort_desc: bool,
    list: Vec<usize>,
    selected: Option<usize>,
    dirty: bool,
    request: Option<String>,
    json: Option<serde_json::Value>,
    raw: TextState,
    tab: Tab,
}

impl Default for TablesPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            category: None,
            sort: SortKey::Name,
            sort_desc: false,
            list: Vec::new(),
            selected: None,
            dirty: true, // build the list on first show
            request: None,
            json: None,
            raw: TextState::default(),
            tab: Tab::default(),
        }
    }
}

impl TablesPanel {
    pub fn request(&mut self, query: &str) {
        self.request = Some(query.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.category = None;
        self.sort = SortKey::Name;
        self.sort_desc = false;
        self.dirty = true;
    }

    fn sort_list(&mut self, data: &crate::app::Data) {
        let desc = self.sort_desc;
        self.list.sort_by(|a, b| {
            let ta = &data.tables.items[*a];
            let tb = &data.tables.items[*b];
            let ord = match self.sort {
                SortKey::Name => ta.name.to_lowercase().cmp(&tb.name.to_lowercase()),
                SortKey::Category => ta.category.to_lowercase().cmp(&tb.category.to_lowercase()),
                SortKey::Size => ta.size.cmp(&tb.size),
            };
            if desc { ord.reverse() } else { ord }
        });
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if !app.data().is_some_and(|d| d.tables.ready) {
        ui.label(theme::dim_label("indexing tables\u{2026}"));
        return;
    }
    if let Some(query) = app.panels.tables.request.take() {
        app.panels.tables.query = query;
        app.panels.tables.dirty = true;
    }
    if app.panels.tables.dirty {
        if let Some(data) = app.data.as_deref() {
            let panel = &mut app.panels.tables;
            panel.list = data.tables.search(&panel.query, panel.category.as_deref());
            panel.sort_list(data);
            panel.dirty = false;
            if let Some(name) = panel.request.take() {
                if let Some(index) = panel
                    .list
                    .iter()
                    .copied()
                    .find(|i| data.tables.items[*i].name.eq_ignore_ascii_case(&name))
                    .or_else(|| data.tables.items.iter().position(|t| t.name.eq_ignore_ascii_case(&name)))
                {
                    panel.selected = Some(index);
                    let path = data.tables.items[index].path.clone();
                    let json = app.data.as_mut().and_then(|d| d.tables.load(&path));
                    if let Some(json) = &json {
                        let pretty = serde_json::to_string_pretty(json).unwrap_or_default();
                        app.panels.tables.raw.set(&pretty, Lang::Json);
                    }
                    app.panels.tables.json = json;
                }
            }
        }
    }

    egui::Panel::left("table_list")
        .exact_size(300.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Parameter tables"));
            let categories: Vec<(String, usize)> = app
                .data
                .as_deref()
                .map(|d| d.tables.categories().to_vec())
                .unwrap_or_default();
            let label = app
                .panels
                .tables
                .category
                .clone()
                .unwrap_or_else(|| "All categories".into());
            egui::ComboBox::from_id_salt("table_category")
                .selected_text(label)
                .width(f32::INFINITY)
                .show_ui(ui, |ui| {
                    if ui.selectable_label(app.panels.tables.category.is_none(), "All categories").clicked() {
                        app.panels.tables.category = None;
                        app.panels.tables.dirty = true;
                    }
                    for (name, count) in categories {
                        let selected = app.panels.tables.category.as_deref() == Some(name.as_str());
                        if ui.selectable_label(selected, format!("{name}  ({count})")).clicked() {
                            app.panels.tables.category = Some(name);
                            app.panels.tables.dirty = true;
                        }
                    }
                });
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.tables.query)
                        .hint_text("Search tables\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.tables.dirty = true;
            }
            ui.label(theme::faint_label(format!("{} tables", human_count(app.panels.tables.list.len()))));
            ui.horizontal(|ui| {
                egui::ComboBox::from_id_salt("table_sort")
                    .selected_text(match app.panels.tables.sort {
                        SortKey::Name => "Sort: name",
                        SortKey::Category => "Sort: category",
                        SortKey::Size => "Sort: size",
                    })
                    .show_ui(ui, |ui| {
                        for (key, label) in [(SortKey::Name, "Name"), (SortKey::Category, "Category"), (SortKey::Size, "Size")] {
                            if ui.selectable_label(app.panels.tables.sort == key, label).clicked() {
                                app.panels.tables.sort = key;
                                app.panels.tables.dirty = true;
                            }
                        }
                    });
                if ui.button(if app.panels.tables.sort_desc { "Descending" } else { "Ascending" }).clicked() {
                    app.panels.tables.sort_desc = !app.panels.tables.sort_desc;
                    app.panels.tables.dirty = true;
                }
            });
            ui.separator();
            let list = app.panels.tables.list.clone();
            let selected = app.panels.tables.selected;
            let mut clicked = None;
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("table_scroll")
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::remainder().at_least(110.0))
                .column(Column::exact(80.0))
                .header(20.0, |mut header| {
                    for title in ["Table", "Size"] {
                        header.col(|ui| {
                            ui.label(theme::faint_label(title));
                        });
                    }
                })
                .body(|body| {
                    body.rows(18.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let Some(table) = app.data.as_deref().and_then(|d| d.tables.items.get(index))
                        else {
                            return;
                        };
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            ui.label(egui::RichText::new(table.name.clone()).size(12.0));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(human_size(table.size)));
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(index) = clicked {
                app.panels.tables.selected = Some(index);
                app.panels.tables.json = None;
                app.panels.tables.raw = TextState::default();
            }
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let Some(index) = app.panels.tables.selected else {
                ui.label(theme::faint_label("Select a table."));
                return;
            };
            let info = app
                .data
                .as_deref()
                .and_then(|d| d.tables.items.get(index))
                .map(|t| (t.name.clone(), t.category.clone(), t.size, t.path.clone()));
            let Some((name, category, size, path)) = info else { return };
            if app.panels.tables.json.is_none() {
                let json = app.data.as_mut().and_then(|d| d.tables.load(&path));
                if let Some(json) = &json {
                    let pretty = serde_json::to_string_pretty(json).unwrap_or_default();
                    app.panels.tables.raw.set(&pretty, Lang::Json);
                }
                app.panels.tables.json = json;
            }
            let summary = app
                .data
                .as_mut()
                .map(|d| d.tables.summary(index))
                .unwrap_or_default();
            ui.horizontal(|ui| {
                ui.label(theme::heading(name.clone()));
                ui.label(theme::dim_label(format!("{category}  \u{b7}  {}", human_size(size))));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    for (label, tab) in [("Summary", Tab::Summary), ("Raw JSON", Tab::Raw), ("Structure", Tab::Tree)] {
                        if ui.selectable_label(app.panels.tables.tab == tab, label).clicked() {
                            app.panels.tables.tab = tab;
                        }
                    }
                });
            });
            ui.separator();
            match app.panels.tables.tab {
                Tab::Tree => {
                    if let Some(json) = app.panels.tables.json.clone() {
                        egui::ScrollArea::vertical()
                            .id_salt("table_tree")
                            .auto_shrink([false, false])
                            .show(ui, |ui| crate::ui::json_tree(ui, &json, "root", 0));
                    }
                }
                Tab::Raw => {
                    let state = std::mem::take(&mut app.panels.tables.raw);
                    crate::ui::text_view(ui, "table_raw", &state, false);
                    app.panels.tables.raw = state;
                }
                Tab::Summary => {
                    let rows: Vec<(&str, String)> = vec![
                        ("category", category.clone()),
                        ("file", path.to_string_lossy().into_owned()),
                        ("size", human_size(size)),
                        ("shape", summary),
                    ];
                    crate::ui::kv_rows(ui, &rows);
                }
            }
        });
}
