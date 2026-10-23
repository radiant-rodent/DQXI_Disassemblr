//! Dialogue browser backed by the read-only translation database.

use eframe::egui;

use crate::app::ViewerApp;
use crate::data::dialogues::{DialogueRow, Location, PcRow};
use crate::theme;
use crate::ui::TextState;
use crate::utils::{elide, human_count};

const PAGE: usize = 250;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    Source,
    Pc,
}

pub struct DialoguesPanel {
    tab: Tab,
    pub query: String,
    file: Option<String>,
    status: Option<i64>,
    origin: Option<String>,
    page: usize,
    rows: Vec<DialogueRow>,
    total: usize,
    selected: Option<usize>,
    locations: Vec<Location>,
    jp: TextState,
    en: TextState,
    pc_query: String,
    pc_page: usize,
    pc_rows: Vec<PcRow>,
    pc_selected: Option<usize>,
    pc_jp: TextState,
    pc_en: TextState,
    dirty: bool,
    request: Option<(String, Option<String>)>,
}

impl Default for DialoguesPanel {
    fn default() -> Self {
        Self {
            tab: Tab::Source,
            query: String::new(),
            file: None,
            status: None,
            origin: None,
            page: 0,
            rows: Vec::new(),
            total: 0,
            selected: None,
            locations: Vec::new(),
            jp: TextState::default(),
            en: TextState::default(),
            pc_query: String::new(),
            pc_page: 0,
            pc_rows: Vec::new(),
            pc_selected: None,
            pc_jp: TextState::default(),
            pc_en: TextState::default(),
            dirty: true,
            request: None,
        }
    }
}

impl DialoguesPanel {
    pub fn request(&mut self, query: &str, file: Option<&str>) {
        self.request = Some((query.to_string(), file.map(|f| f.to_string())));
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.file = None;
        self.status = None;
        self.origin = None;
        self.dirty = true;
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let available = app
        .data
        .as_deref()
        .map(|d| d.dialogues.available())
        .unwrap_or(false);
    if !available {
        ui.label(theme::dim_label(
            "dialogue database not found \u{2014} other sections still work",
        ));
        return;
    }
    let stats = app
        .data
        .as_mut()
        .map(|d| d.dialogues.stats())
        .unwrap_or_default();
    if let Some((query, file)) = app.panels.dialogues.request.take() {
        app.panels.dialogues.query = query;
        app.panels.dialogues.file = file;
        app.panels.dialogues.tab = Tab::Source;
        app.panels.dialogues.page = 0;
        app.panels.dialogues.dirty = true;
    }

    ui.horizontal(|ui| {
        ui.label(theme::heading("Dialogues"));
        ui.label(theme::faint_label(format!(
            "{} source entries  \u{b7}  {} locations  \u{b7}  {} reviewed  \u{b7}  {} translated  \u{b7}  {} untranslated  \u{b7}  {} PC rows",
            human_count(stats.sources),
            human_count(stats.entries),
            human_count(stats.reviewed),
            human_count(stats.translated),
            human_count(stats.untranslated),
            human_count(stats.pc_rows)
        )));
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            for (label, tab) in [("PC text (official English)", Tab::Pc), ("Game dialogue (3DS)", Tab::Source)] {
                if ui.selectable_label(app.panels.dialogues.tab == tab, label).clicked() {
                    app.panels.dialogues.tab = tab;
                }
            }
        });
    });
    ui.separator();
    if app.panels.dialogues.tab == Tab::Source {
        source_tab(app, ui, &stats.by_file);
    } else {
        pc_tab(app, ui);
    }
}

fn source_tab(app: &mut ViewerApp, ui: &mut egui::Ui, files: &[(String, usize)]) {
    let files = files.to_vec();
    ensure_selection(app);
    ui.horizontal(|ui| {
        if ui
            .add(
                egui::TextEdit::singleline(&mut app.panels.dialogues.query)
                    .hint_text("Search Japanese or English text\u{2026}")
                    .desired_width(280.0),
            )
            .changed()
        {
            app.panels.dialogues.page = 0;
            app.panels.dialogues.dirty = true;
        }
        let label = app
            .panels
            .dialogues
            .file
            .clone()
            .unwrap_or_else(|| "All files".into());
        egui::ComboBox::from_id_salt("dialogue_file")
            .selected_text(elide(&label, 34))
            .width(280.0)
            .show_ui(ui, |ui| {
                if ui.selectable_label(app.panels.dialogues.file.is_none(), "All files").clicked() {
                    app.panels.dialogues.file = None;
                    app.panels.dialogues.dirty = true;
                }
                for (file, count) in files.iter().take(400) {
                    let selected = app.panels.dialogues.file.as_deref() == Some(file.as_str());
                    if ui.selectable_label(selected, format!("{file}  ({count})")).clicked() {
                        app.panels.dialogues.file = Some(file.clone());
                        app.panels.dialogues.dirty = true;
                    }
                }
            });
        let label = match app.panels.dialogues.status {
            None => "All statuses".to_string(),
            Some(0) => "untranslated".to_string(),
            Some(1) => "translated".to_string(),
            _ => "reviewed".to_string(),
        };
        egui::ComboBox::from_id_salt("dialogue_status")
            .selected_text(label)
            .width(120.0)
            .show_ui(ui, |ui| {
                for (label, value) in [("All statuses", None), ("untranslated", Some(0)), ("translated", Some(1)), ("reviewed", Some(2))] {
                    if ui
                        .selectable_label(app.panels.dialogues.status == value, label)
                        .clicked()
                    {
                        app.panels.dialogues.status = value;
                        app.panels.dialogues.dirty = true;
                    }
                }
            });
        let label = app
            .panels
            .dialogues
            .origin
            .clone()
            .unwrap_or_else(|| "All origins".into());
        egui::ComboBox::from_id_salt("dialogue_origin")
            .selected_text(label)
            .width(110.0)
            .show_ui(ui, |ui| {
                if ui.selectable_label(app.panels.dialogues.origin.is_none(), "All origins").clicked() {
                    app.panels.dialogues.origin = None;
                    app.panels.dialogues.dirty = true;
                }
                for origin in ["pc", "ai", "manual"] {
                    let selected = app.panels.dialogues.origin.as_deref() == Some(origin);
                    if ui.selectable_label(selected, origin).clicked() {
                        app.panels.dialogues.origin = Some(origin.to_string());
                        app.panels.dialogues.dirty = true;
                    }
                }
            });
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            let pages = (app.panels.dialogues.total.div_ceil(PAGE)).max(1);
            if ui.button("Next \u{25b6}").clicked() && app.panels.dialogues.page + 1 < pages {
                app.panels.dialogues.page += 1;
                app.panels.dialogues.dirty = true;
            }
            ui.label(theme::faint_label(format!(
                "page {} / {}  \u{b7}  {} entries",
                app.panels.dialogues.page + 1,
                pages,
                human_count(app.panels.dialogues.total)
            )));
            if ui.button("\u{25c0} Prev").clicked() && app.panels.dialogues.page > 0 {
                app.panels.dialogues.page = app.panels.dialogues.page.saturating_sub(1);
                app.panels.dialogues.dirty = true;
            }
        });
    });

    if app.panels.dialogues.dirty {
        let (query, file, status, origin, page) = {
            let panel = &app.panels.dialogues;
            (
                panel.query.clone(),
                panel.file.clone(),
                panel.status,
                panel.origin.clone(),
                panel.page,
            )
        };
        if let Some(data) = app.data.as_mut() {
            let total = data
                .dialogues
                .count_sources(&query, file.as_deref(), status, origin.as_deref());
            let rows = data.dialogues.search_sources(
                &query,
                file.as_deref(),
                status,
                origin.as_deref(),
                page * PAGE,
                PAGE,
            );
            app.panels.dialogues.total = total;
            app.panels.dialogues.rows = rows;
            app.panels.dialogues.dirty = false;
            // preview the first row so the JP/EN panes are never empty
            if app.panels.dialogues.selected.is_none() && !app.panels.dialogues.rows.is_empty() {
                let entry = app.panels.dialogues.rows[0].clone();
                app.panels.dialogues.selected = Some(0);
                let mut jp = crate::ui::TextState::default();
                jp.set(&entry.jp, crate::ui::Lang::Plain);
                let mut en = crate::ui::TextState::default();
                en.set(
                    if entry.en.is_empty() { "(not translated yet)" } else { &entry.en },
                    crate::ui::Lang::Plain,
                );
                app.panels.dialogues.jp = jp;
                app.panels.dialogues.en = en;
                app.panels.dialogues.locations =
                    data.dialogues.locations(entry.id);
            }
        }
    }

    ui.separator();
    let rows = app.panels.dialogues.rows.clone();
    let selected = app.panels.dialogues.selected;
    let mut clicked = None;
    let detail_height = 250.0;
    let list_height = (ui.available_height() - detail_height - 16.0).max(120.0);
    ui.allocate_ui(egui::vec2(ui.available_width(), list_height), |ui| {
        use egui_extras::{Column, TableBuilder};
        TableBuilder::new(ui)
            .id_salt("dialogue_rows")
            .striped(true)
            .resizable(true)
            .sense(egui::Sense::click())
            .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
            .auto_shrink([false, false])
            .column(Column::exact(70.0))
            .column(Column::exact(170.0))
            .column(Column::initial(420.0).at_least(160.0))
            .column(Column::remainder().at_least(160.0))
            .header(20.0, |mut header| {
                for title in ["Source", "Status", "Japanese", "English translation"] {
                    header.col(|ui| {
                        ui.label(theme::faint_label(title));
                    });
                }
            })
            .body(|body| {
                body.rows(18.0, rows.len(), |mut row| {
                    let index = row.index();
                    let entry = &rows[index];
                    let color = if entry.status == 0 { theme::WARN } else { theme::TEXT };
                    row.set_selected(selected == Some(index));
                    row.col(|ui| {
                        ui.label(theme::mono(format!("#{}", entry.id)));
                    });
                    row.col(|ui| {
                        ui.label(theme::dim_label(format!(
                            "{} ({})",
                            entry.status_text(),
                            entry.origin
                        )));
                    });
                    row.col(|ui| {
                        ui.label(
                            egui::RichText::new(entry.jp.split_whitespace().collect::<Vec<_>>().join(" "))
                                .size(12.0)
                                .color(color),
                        );
                    });
                    row.col(|ui| {
                        ui.label(
                            egui::RichText::new(
                                entry.en.split_whitespace().collect::<Vec<_>>().join(" "),
                            )
                            .size(12.0)
                            .color(theme::TEXT_DIM),
                        );
                    });
                    if row.response().clicked() {
                        clicked = Some(index);
                    }
                });
            });
    });
    ui.separator();
    ui.allocate_ui(egui::vec2(ui.available_width(), detail_height), |ui| {
        ui.columns(2, |columns| {
            columns[0].label(theme::accent("Japanese source"));
            columns[1].label(theme::accent("English translation"));
            let jp = std::mem::take(&mut app.panels.dialogues.jp);
            crate::ui::text_view(&mut columns[0], "dialogue_jp", &jp, false);
            app.panels.dialogues.jp = jp;
            let en = std::mem::take(&mut app.panels.dialogues.en);
            crate::ui::text_view(&mut columns[1], "dialogue_en", &en, false);
            app.panels.dialogues.en = en;
        });
        ui.separator();
        ui.label(theme::faint_label("Where it lives in the ROM"));
        let locations = app.panels.dialogues.locations.clone();
        egui::ScrollArea::vertical()
            .id_salt("dialogue_locations")
            .auto_shrink([false, false])
            .show(ui, |ui| {
                for location in &locations {
                    ui.label(theme::mono(format!(
                        "{:<8} {:<34} {:<28} {:<10} {}",
                        elide(&location.kind, 8),
                        elide(&location.file, 34),
                        elide(&location.entry, 28),
                        location
                            .loc
                            .map(|v| format!("0x{v:X}"))
                            .unwrap_or_else(|| "-".into()),
                        elide(&location.category, 20)
                    )));
                }
            });
    });
    if let Some(row) = clicked {
        app.panels.dialogues.selected = Some(row);
        let entry = rows[row].clone();
        let mut jp = TextState::default();
        jp.set(&entry.jp, crate::ui::Lang::Plain);
        let mut en = TextState::default();
        en.set(
            if entry.en.is_empty() { "(not translated yet)" } else { &entry.en },
            crate::ui::Lang::Plain,
        );
        app.panels.dialogues.jp = jp;
        app.panels.dialogues.en = en;
        let locations = app
            .data
            .as_mut()
            .map(|d| d.dialogues.locations(entry.id))
            .unwrap_or_default();
        app.panels.dialogues.locations = locations;
        app.status = format!("source #{} \u{b7} {}", entry.id, entry.status_text());
    }
}

/// Keep a valid row selected and the JP/EN panes filled.
fn ensure_selection(app: &mut ViewerApp) {
    let out_of_range = app
        .panels
        .dialogues
        .selected
        .map(|sel| sel >= app.panels.dialogues.rows.len())
        .unwrap_or(true);
    if out_of_range {
        app.panels.dialogues.selected = None;
    }
    if app.panels.dialogues.selected.is_some() && !app.panels.dialogues.jp.lines.is_empty() {
        return;
    }
    let Some(entry) = app.panels.dialogues.rows.first().cloned() else {
        return;
    };
    app.panels.dialogues.selected = Some(0);
    let mut jp = TextState::default();
    jp.set(&entry.jp, crate::ui::Lang::Plain);
    let mut en = TextState::default();
    en.set(
        if entry.en.is_empty() { "(not translated yet)" } else { &entry.en },
        crate::ui::Lang::Plain,
    );
    app.panels.dialogues.jp = jp;
    app.panels.dialogues.en = en;
    if let Some(data) = app.data.as_mut() {
        app.panels.dialogues.locations = data.dialogues.locations(entry.id);
    }
}

fn pc_tab(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        if ui
            .add(
                egui::TextEdit::singleline(&mut app.panels.dialogues.pc_query)
                    .hint_text("Search official PC text\u{2026}")
                    .desired_width(320.0),
            )
            .changed()
        {
            app.panels.dialogues.pc_page = 0;
            load_pc(app);
        }
        if ui.button("Next \u{25b6}").clicked() {
            app.panels.dialogues.pc_page += 1;
            load_pc(app);
        }
        if ui.button("\u{25c0} Prev").clicked() {
            app.panels.dialogues.pc_page = app.panels.dialogues.pc_page.saturating_sub(1);
            load_pc(app);
        }
        ui.label(theme::faint_label(format!(
            "page {}  \u{b7}  {} rows",
            app.panels.dialogues.pc_page + 1,
            human_count(app.panels.dialogues.pc_rows.len())
        )));
    });
    if app.panels.dialogues.pc_rows.is_empty() {
        load_pc(app);
    }
    ui.separator();
    let rows = app.panels.dialogues.pc_rows.clone();
    let selected = app.panels.dialogues.pc_selected;
    let mut clicked = None;
    let detail_height = 220.0;
    let list_height = (ui.available_height() - detail_height - 16.0).max(120.0);
    ui.allocate_ui(egui::vec2(ui.available_width(), list_height), |ui| {
        use egui_extras::{Column, TableBuilder};
        TableBuilder::new(ui)
            .id_salt("pc_rows")
            .striped(true)
            .resizable(true)
            .sense(egui::Sense::click())
            .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
            .auto_shrink([false, false])
            .column(Column::initial(220.0).at_least(120.0))
            .column(Column::initial(170.0).at_least(100.0))
            .column(Column::remainder().at_least(140.0))
            .column(Column::remainder().at_least(140.0))
            .header(20.0, |mut header| {
                for title in ["Key", "Table", "Japanese", "PC English"] {
                    header.col(|ui| {
                        ui.label(theme::faint_label(title));
                    });
                }
            })
            .body(|body| {
                body.rows(18.0, rows.len(), |mut row| {
                    let index = row.index();
                    let entry = &rows[index];
                    row.set_selected(selected == Some(index));
                    row.col(|ui| {
                        ui.label(theme::mono(entry.key.clone()));
                    });
                    row.col(|ui| {
                        ui.label(theme::dim_label(entry.file.clone()));
                    });
                    row.col(|ui| {
                        ui.label(
                            egui::RichText::new(
                                entry.jp.split_whitespace().collect::<Vec<_>>().join(" "),
                            )
                            .size(12.0),
                        );
                    });
                    row.col(|ui| {
                        ui.label(
                            egui::RichText::new(
                                entry.en.split_whitespace().collect::<Vec<_>>().join(" "),
                            )
                            .size(12.0)
                            .color(theme::TEXT_DIM),
                        );
                    });
                    if row.response().clicked() {
                        clicked = Some(index);
                    }
                });
            });
    });
    ui.separator();
    ui.allocate_ui(egui::vec2(ui.available_width(), detail_height), |ui| {
        ui.columns(2, |columns| {
            columns[0].label(theme::accent("Japanese"));
            columns[1].label(theme::accent("Official English (PC)"));
            let jp = std::mem::take(&mut app.panels.dialogues.pc_jp);
            crate::ui::text_view(&mut columns[0], "pc_jp", &jp, false);
            app.panels.dialogues.pc_jp = jp;
            let en = std::mem::take(&mut app.panels.dialogues.pc_en);
            crate::ui::text_view(&mut columns[1], "pc_en", &en, false);
            app.panels.dialogues.pc_en = en;
        });
    });
    if let Some(row) = clicked {
        app.panels.dialogues.pc_selected = Some(row);
        let entry = rows[row].clone();
        let mut jp = TextState::default();
        jp.set(&entry.jp, crate::ui::Lang::Plain);
        let mut en = TextState::default();
        en.set(&entry.en, crate::ui::Lang::Plain);
        app.panels.dialogues.pc_jp = jp;
        app.panels.dialogues.pc_en = en;
    }
}

fn load_pc(app: &mut ViewerApp) {
    let query = app.panels.dialogues.pc_query.clone();
    let page = app.panels.dialogues.pc_page;
    if let Some(data) = app.data.as_mut() {
        let rows = data.dialogues.search_pc(&query, page * PAGE, PAGE);
        app.panels.dialogues.pc_rows = rows;
    }
}
