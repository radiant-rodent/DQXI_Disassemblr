//! Game text / dialogue editor.
//!
//! Two sources live here:
//!
//! * **Game text banks** - the UTF-16 strings inside the BXON tables of the
//!   retail PACKs, exported by `tools/text_tool.py` to `game_assets/text`.
//!   These are the lines the game actually shows; edits are saved through the
//!   Python tool into `mod/romfs/<pack>` (LayeredFS).
//! * **Dialogue database** - the read-only translation workspace browser that
//!   was here before (`..\3DS_Translate`), kept as reference.
//!
//! The preview measures tagged text with the game's own BFFNT glyph widths
//! (`glyph width` per character, not an estimate) against the textbox width of
//! the bank, and warns about missing glyphs, overflowing lines and messages
//! longer than the message-window buffer.

use std::collections::HashMap;
use std::sync::mpsc::{Receiver, TryRecvError};

use eframe::egui;

use crate::app::ViewerApp;
use crate::data::dialogues::{
    self, plain_text, tags_of, BankMeta, DialogueRow, GlyphFont, Location, PcRow, Piece, TextEntry,
    TextHit, TextIndex, ARG_NAMES, FORMAT_CODES,
};
use crate::theme;
use crate::ui::TextState;
use crate::utils::{elide, human_count};

const PAGE: usize = 250;
/// The message window copies each message into a 255-unit UTF-16 buffer; a
/// longer string is cut off and the box stays blank (reference gamefont.py).
const MESSAGE_MAX_UNITS: usize = 255;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    Text,
    Source,
    Pc,
}

/// Background loading state of the exported text banks.
enum TextLoad {
    Idle,
    Loading(Receiver<TextIndex>),
    Ready(Box<TextIndex>),
    Failed(String),
}

impl Default for TextLoad {
    fn default() -> Self {
        TextLoad::Idle
    }
}

/// A dedicated thread that owns a loaded `TextIndex` and answers full-text
/// queries, so searching all 68k lines never blocks the window.
struct SearchWorker {
    queries: std::sync::mpsc::Sender<String>,
    hits: Receiver<(String, Vec<TextHit>)>,
    pending: Option<String>,
    results: Vec<TextHit>,
    results_for: String,
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

    // ---- game text banks ------------------------------------------------
    text: TextLoad,
    bank_filter: String,
    category: Option<String>,
    scene: Option<String>,
    bank: Option<usize>,
    global_query: String,
    entry_query: String,
    role_filter: Option<String>,
    selected_entry: Option<usize>,
    drafts: HashMap<String, Vec<TextEntry>>,
    /// text edits as (bank key, entry, text before); typing in one entry is one step
    undo: Vec<(String, usize, String)>,
    redo: Vec<(String, usize, String)>,
    search: Option<SearchWorker>,
    edit: String,
    edit_for: Option<(String, usize)>,
    width_override: Option<f32>,
    zoom: f32,
    status_text: String,
    status_text_bad: bool,
    save_job: Option<Receiver<Result<String, String>>>,
    /// Edited entries of the bank being saved (applied to the index on success).
    save_entries: Option<(usize, Vec<TextEntry>)>,
}

impl Default for DialoguesPanel {
    fn default() -> Self {
        Self {
            tab: Tab::Text,
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
            text: TextLoad::Idle,
            bank_filter: String::new(),
            category: None,
            scene: None,
            bank: None,
            global_query: String::new(),
            entry_query: String::new(),
            role_filter: None,
            selected_entry: None,
            drafts: HashMap::new(),
            undo: Vec::new(),
            redo: Vec::new(),
            search: None,
            edit: String::new(),
            edit_for: None,
            width_override: None,
            zoom: 2.0,
            status_text: String::new(),
            status_text_bad: false,
            save_job: None,
            save_entries: None,
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
        self.bank_filter.clear();
        self.entry_query.clear();
        self.scene = None;
        self.category = None;
        self.dirty = true;
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if app.panels.dialogues.tab == Tab::Text {
        // Take the panel out while it edits the app: the text tab needs
        // `&mut app` for saving and the index at the same time.
        let mut panel = std::mem::take(&mut app.panels.dialogues);
        panel.text_tab(app, ui);
        app.panels.dialogues = panel;
        return;
    }
    let available = app
        .data
        .as_deref()
        .map(|d| d.dialogues.available())
        .unwrap_or(false);
    if !available {
        ui.horizontal(|ui| {
            ui.label(theme::heading("Dialogues"));
            tab_buttons(ui, &mut app.panels.dialogues.tab);
        });
        ui.separator();
        ui.label(theme::dim_label(
            "dialogue database not found \u{2014} the game text tab still works",
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
        tab_buttons(ui, &mut app.panels.dialogues.tab);
    });
    ui.separator();
    if app.panels.dialogues.tab == Tab::Source {
        source_tab(app, ui, &stats.by_file);
    } else {
        pc_tab(app, ui);
    }
}

/// The section's tab strip (right aligned).
fn tab_buttons(ui: &mut egui::Ui, tab: &mut Tab) {
    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
        for (label, value) in [
            ("PC text (official English)", Tab::Pc),
            ("Dialogue database (3DS)", Tab::Source),
            ("Game text (editable)", Tab::Text),
        ] {
            if ui.selectable_label(*tab == value, label).clicked() {
                *tab = value;
            }
        }
    });
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
    let nav = crate::ui::list_nav(ui.ctx(), &(0..rows.len()).collect::<Vec<_>>(), selected.as_ref());
    if let Some((item, _)) = &nav {
        clicked = Some(*item);
    }
    let nav_row = nav.map(|(_, r)| r);
    let detail_height = 250.0;
    let list_height = (ui.available_height() - detail_height - 16.0).max(120.0);
    ui.allocate_ui(egui::vec2(ui.available_width(), list_height), |ui| {
        use egui_extras::{Column, TableBuilder};
        use crate::ui::TableNav;
        TableBuilder::new(ui)
            .id_salt("dialogue_rows")
            .nav_scroll(nav_row)
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
    let nav = crate::ui::list_nav(ui.ctx(), &(0..rows.len()).collect::<Vec<_>>(), selected.as_ref());
    if let Some((item, _)) = &nav {
        clicked = Some(*item);
    }
    let nav_row = nav.map(|(_, r)| r);
    let detail_height = 220.0;
    let list_height = (ui.available_height() - detail_height - 16.0).max(120.0);
    ui.allocate_ui(egui::vec2(ui.available_width(), list_height), |ui| {
        use egui_extras::{Column, TableBuilder};
        use crate::ui::TableNav;
        TableBuilder::new(ui)
            .id_salt("pc_rows")
            .nav_scroll(nav_row)
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

// ===========================================================================
// Game text tab
// ===========================================================================
impl DialoguesPanel {
    fn index(&self) -> Option<&TextIndex> {
        match &self.text {
            TextLoad::Ready(index) => Some(index),
            _ => None,
        }
    }

    fn index_mut(&mut self) -> Option<&mut TextIndex> {
        match &mut self.text {
            TextLoad::Ready(index) => Some(index),
            _ => None,
        }
    }

    fn ensure_loaded(&mut self, app: &mut ViewerApp) {
        match &self.text {
            TextLoad::Idle => {
                let root = app.dirs.root.clone();
                let (tx, rx) = std::sync::mpsc::channel();
                std::thread::spawn(move || {
                    let _ = tx.send(TextIndex::load(&root));
                });
                self.text = TextLoad::Loading(rx);
            }
            TextLoad::Loading(rx) => {
                let result = match rx.try_recv() {
                    Ok(index) => Some(Ok(index)),
                    Err(TryRecvError::Empty) => None,
                    Err(TryRecvError::Disconnected) => {
                        Some(Err("the text index loader stopped without a result".to_string()))
                    }
                };
                if let Some(result) = result {
                    self.text = match result {
                        Ok(index) if index.available() => TextLoad::Ready(Box::new(index)),
                        Ok(index) => {
                            TextLoad::Failed(index.error.unwrap_or_else(|| "no text banks".into()))
                        }
                        Err(err) => TextLoad::Failed(err),
                    };
                }
            }
            _ => {}
        }
    }

    fn text_tab(&mut self, app: &mut ViewerApp, ui: &mut egui::Ui) {
        self.ensure_loaded(app);
        self.poll_save(ui.ctx());
        if let TextLoad::Failed(message) = &self.text {
            let message = message.clone();
            ui.horizontal(|ui| {
                ui.label(theme::heading("Game text"));
                tab_buttons(ui, &mut self.tab);
            });
            ui.separator();
            ui.label(egui::RichText::new(message).color(theme::WARN));
            ui.label(theme::dim_label(
                "The text banks are generated: run `python tools/text_tool.py export` \
                 (it writes game_assets/text/index.json) and try again.",
            ));
            if ui.button("Retry").clicked() {
                self.text = TextLoad::Idle;
            }
            return;
        }
        if matches!(self.text, TextLoad::Loading(_) | TextLoad::Idle) {
            ui.horizontal(|ui| {
                ui.spinner();
                ui.label(theme::dim_label("loading text banks\u{2026}"));
            });
            ui.ctx().request_repaint();
            return;
        }
        self.text_ui(app, ui);
    }

    fn text_ui(&mut self, app: &mut ViewerApp, ui: &mut egui::Ui) {
        let Some(index) = self.index() else { return };
        let bank_count = index.banks.len();
        let total = index.total_entries;
        let font_count = index.fonts.len();
        let families = index.families.clone();
        ui.horizontal(|ui| {
            ui.label(theme::heading("Game text"));
            ui.label(theme::faint_label(format!(
                "{} banks  \u{b7}  {} strings  \u{b7}  {} families  \u{b7}  {} game fonts",
                human_count(bank_count),
                human_count(total),
                families.len(),
                font_count
            )));
            tab_buttons(ui, &mut self.tab);
        });
        if font_count == 0 {
            ui.label(
                egui::RichText::new(
                    "game fonts not found under game_data/romfs/font - the preview falls back \
                     to a fixed width estimate",
                )
                .color(theme::WARN),
            );
        }
        ui.separator();

        if self.bank.is_none() && bank_count > 0 {
            let default = self
                .index()
                .and_then(|i| {
                    i.banks
                        .iter()
                        .position(|b| b.key == "param/region/r001/npc_ie")
                })
                .unwrap_or(0);
            self.select_bank(default);
        }

        self.global_search_row(app, ui);
        self.hits_list(ui);

        let Some(meta) = self.current_bank() else {
            ui.label(theme::dim_label("no text bank selected"));
            return;
        };
        self.bank_picker(ui, &meta);
        // The picker may have switched banks this frame: re-read the metadata
        // so the editor previews the new bank's font and box width.
        let Some(meta) = self.current_bank() else {
            return;
        };
        self.entry_browser(ui);
        self.editor(app, ui, &meta);
    }

    // ---------------------------------------------------------------- search
    fn global_search_row(&mut self, app: &mut ViewerApp, ui: &mut egui::Ui) {
        let mut changed = false;
        ui.horizontal(|ui| {
            ui.label(theme::faint_label("Find in every bank"));
            if ui
                .add(
                    egui::TextEdit::singleline(&mut self.global_query)
                        .hint_text("2+ characters of dialogue, a speaker or a tag\u{2026}")
                        .desired_width(340.0),
                )
                .changed()
            {
                changed = true;
            }
            if ui.button("Clear").clicked() {
                self.global_query.clear();
                self.search = None;
            }
            if let Some(worker) = &self.search {
                if worker.pending.is_some() {
                    ui.spinner();
                    ui.label(theme::faint_label("searching\u{2026}"));
                } else if !worker.results.is_empty() {
                    ui.label(theme::faint_label(format!(
                        "{} match(es) for \u{201c}{}\u{201d}",
                        human_count(worker.results.len()),
                        elide(&worker.results_for, 24)
                    )));
                } else if !worker.results_for.is_empty() {
                    ui.label(theme::faint_label(format!(
                        "no match for \u{201c}{}\u{201d}",
                        elide(&worker.results_for, 24)
                    )));
                }
            }
        });
        if changed {
            self.start_search(app);
        }
        self.poll_search(ui.ctx());
    }

    fn start_search(&mut self, app: &mut ViewerApp) {
        let query = self.global_query.trim().to_string();
        if query.chars().count() < 2 {
            self.search = None;
            return;
        }
        if self.search.is_none() {
            let root = app.dirs.root.clone();
            let (queries, query_rx) = std::sync::mpsc::channel::<String>();
            let (hits_tx, hits) = std::sync::mpsc::channel::<(String, Vec<TextHit>)>();
            std::thread::spawn(move || {
                let mut index = TextIndex::load(&root);
                if !index.available() {
                    return;
                }
                index.ensure_all();
                while let Ok(text) = query_rx.recv() {
                    let hits = index.search(&text, 400);
                    if hits_tx.send((text, hits)).is_err() {
                        break;
                    }
                }
            });
            self.search = Some(SearchWorker {
                queries,
                hits,
                pending: None,
                results: Vec::new(),
                results_for: String::new(),
            });
        }
        if let Some(worker) = &mut self.search {
            worker.pending = Some(query.clone());
            let _ = worker.queries.send(query);
        }
    }

    fn poll_search(&mut self, ctx: &egui::Context) {
        let Some(worker) = &mut self.search else { return };
        let mut latest = None;
        while let Ok((query, hits)) = worker.hits.try_recv() {
            if worker.pending.as_deref() == Some(query.as_str()) {
                latest = Some((query, hits));
            }
        }
        if let Some((query, hits)) = latest {
            worker.pending = None;
            worker.results_for = query;
            worker.results = hits;
        }
        if worker.pending.is_some() {
            ctx.request_repaint_after(std::time::Duration::from_millis(80));
        }
    }

    fn hits_list(&mut self, ui: &mut egui::Ui) {
        let Some(worker) = &self.search else { return };
        if worker.results.is_empty() || worker.pending.is_some() {
            return;
        }
        let hits = worker.results.clone();
        let mut clicked = None;
        egui::CollapsingHeader::new(format!("{} search match(es)", human_count(hits.len())))
            .default_open(true)
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .id_salt("text_search_hits")
                    .max_height(150.0)
                    .auto_shrink([false, true])
                    .show(ui, |ui| {
                        for hit in &hits {
                            let Some(index) = self.index() else { break };
                            let Some(meta) = index.bank_meta(hit.bank) else { continue };
                            let label = format!(
                                "{:<38} {:<14} {}",
                                elide(&meta.key, 38),
                                elide(if hit.speaker.is_empty() {
                                    "-"
                                } else {
                                    &hit.speaker
                                }, 14),
                                elide(&hit.text, 110)
                            );
                            if ui
                                .selectable_label(false, theme::mono(label))
                                .on_hover_text(&hit.text)
                                .clicked()
                            {
                                clicked = Some(hit.clone());
                            }
                        }
                    });
            });
        if let Some(hit) = clicked {
            self.open_hit(hit);
        }
    }

    fn open_hit(&mut self, hit: TextHit) {
        self.select_bank(hit.bank);
        self.selected_entry = Some(hit.entry);
        self.load_edit();
    }

    // ---------------------------------------------------------------- browser
    fn current_bank(&self) -> Option<BankMeta> {
        let index = self.index()?;
        let bank = self.bank?;
        index.bank_meta(bank).cloned()
    }

    fn select_bank(&mut self, bank: usize) {
        if self.bank == Some(bank) {
            return;
        }
        self.bank = Some(bank);
        self.selected_entry = None;
        self.edit.clear();
        self.edit_for = None;
        self.width_override = None;
        let key = {
            let Some(index) = self.index() else { return };
            match index.bank_meta(bank) {
                Some(meta) => meta.key.clone(),
                None => return,
            }
        };
        if self.drafts.contains_key(&key) {
            return;
        }
        let entries = self
            .index_mut()
            .and_then(|index| index.ensure_bank(bank).map(|doc| doc.entries.clone()));
        if let Some(entries) = entries {
            // Start on a real line, not on the first speaker-name string.
            let first_text = entries.iter().position(|e| e.role == "text").unwrap_or(0);
            self.drafts.insert(key, entries);
            self.selected_entry = Some(first_text);
            self.load_edit();
        }
    }

    fn entries(&self) -> Option<&Vec<TextEntry>> {
        let meta = self.current_bank()?;
        self.drafts.get(&meta.key)
    }

    fn entries_mut(&mut self) -> Option<&mut Vec<TextEntry>> {
        let key = self.current_bank()?.key;
        self.drafts.get_mut(&key)
    }

    fn load_edit(&mut self) {
        let Some(meta) = self.current_bank() else { return };
        let Some(index) = self.selected_entry else { return };
        let text = self
            .drafts
            .get(&meta.key)
            .and_then(|entries| entries.get(index))
            .map(|entry| entry.text.clone())
            .unwrap_or_default();
        self.edit = text;
        self.edit_for = Some((meta.key, index));
    }

    // ---- entry points for the Level editor's Dialogue group -------------------------------------

    /// Starts loading the text banks if that has not happened yet and collects a finished save.
    pub fn prepare(app: &mut ViewerApp, ctx: &egui::Context) {
        let mut panel = std::mem::take(&mut app.panels.dialogues);
        panel.ensure_loaded(app);
        panel.poll_save(ctx);
        app.panels.dialogues = panel;
    }

    pub fn ready(&self) -> bool {
        self.index().is_some()
    }

    /// Makes `key` (e.g. `param/region/r021/npc_ie`) the open bank; false when there is no such bank.
    /// Err(other bank key) when another bank has unsaved edits (they would be lost by switching).
    pub fn open_bank_key(&mut self, key: &str) -> Result<bool, String> {
        let Some(i) = self.index().and_then(|ix| ix.banks.iter().position(|b| b.key == key)) else { return Ok(false) };
        if self.bank != Some(i) && self.dirty_count() > 0 && self.save_job.is_none() {
            if let Some(meta) = self.current_bank() {
                return Err(meta.key);
            }
        }
        let had_selection = self.selected_entry;
        self.select_bank(i);
        if self.bank == Some(i) && had_selection.is_some() {
            self.selected_entry = had_selection;
        }
        Ok(true)
    }

    /// Text of entry `id` of the open bank (the draft, so unsaved edits show).
    pub fn line_text(&self, id: usize) -> Option<String> {
        self.entries()?.get(id).map(|e| e.text.clone())
    }

    /// Retail / last saved text of entry `id` of the open bank.
    pub fn original_text(&self, id: usize) -> Option<String> {
        let bank = self.bank?;
        self.index()?.entries_for(bank)?.entries.get(id).map(|e| e.text.clone())
    }

    /// Edits entry `id` of the open bank; typing in one entry is one undo step.
    pub fn set_line_text(&mut self, id: usize, text: String) {
        let Some(key) = self.current_bank().map(|m| m.key) else { return };
        let Some(entry) = self.entries_mut().and_then(|e| e.get_mut(id)) else { return };
        if entry.text == text {
            return;
        }
        let old = std::mem::replace(&mut entry.text, text);
        let same = self.undo.last().is_some_and(|(k, i, _)| *k == key && *i == id);
        if !same {
            self.undo.push((key, id, old));
            if self.undo.len() > 200 {
                self.undo.remove(0);
            }
        }
        self.redo.clear();
        self.edit_for = None;
    }

    /// Writes the open bank into the mod (same path as the Dialogues editor's Save).
    pub fn save_now(&mut self, app: &mut ViewerApp) {
        self.save(app);
    }

    pub fn status_line(&self) -> Option<(String, bool)> {
        if self.status_text.is_empty() {
            None
        } else {
            Some((self.status_text.clone(), self.status_text_bad))
        }
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }

    fn swap_step(&mut self, from_undo: bool) {
        let step = if from_undo { self.undo.pop() } else { self.redo.pop() };
        let Some((key, index, text)) = step else { return };
        let Some(entry) = self.drafts.get_mut(&key).and_then(|e| e.get_mut(index)) else { return };
        let current = std::mem::replace(&mut entry.text, text);
        let other = (key.clone(), index, current);
        if from_undo {
            self.redo.push(other);
        } else {
            self.undo.push(other);
        }
        if self.current_bank().map(|m| m.key) == Some(key) {
            self.selected_entry = Some(index);
        }
        self.edit_for = None;
    }

    pub fn undo_action(&mut self) {
        self.swap_step(true);
    }

    pub fn redo_action(&mut self) {
        self.swap_step(false);
    }

    /// Edited lines in the open bank (the shell's unsaved-changes count).
    pub fn dirty_count(&self) -> usize {
        let Some(meta) = self.current_bank() else { return 0 };
        let Some(draft) = self.drafts.get(&meta.key) else { return 0 };
        let Some(bank) = self.bank else { return 0 };
        let Some(original) = self.index().and_then(|i| i.entries_for(bank)) else {
            return 0;
        };
        draft
            .iter()
            .zip(original.entries.iter())
            .filter(|(a, b)| a.text != b.text)
            .count()
    }

    fn bank_picker(&mut self, ui: &mut egui::Ui, meta: &BankMeta) {
        // Build owned lists first: the combo closures below mutate `self`.
        let (families, scenes, options) = {
            let Some(index) = self.index() else { return };
            let families = index.families.clone();
            let mut scenes: Vec<String> = index.banks.iter().map(|b| b.scene.clone()).collect();
            scenes.sort();
            scenes.dedup();
            let filter = self.bank_filter.to_lowercase();
            let mut options: Vec<(usize, String, usize, String)> = Vec::new();
            for (i, bank) in index.banks.iter().enumerate() {
                if let Some(category) = &self.category {
                    if &bank.category != category {
                        continue;
                    }
                }
                if let Some(scene) = &self.scene {
                    if &bank.scene != scene {
                        continue;
                    }
                }
                if !filter.is_empty() && !bank.key.to_lowercase().contains(&filter) {
                    continue;
                }
                options.push((i, bank.key.clone(), bank.count, bank.kind.clone()));
                if options.len() >= 300 {
                    break;
                }
            }
            (families, scenes, options)
        };
        let mut picked = None;
        ui.horizontal_wrapped(|ui| {
            let label = self
                .category
                .clone()
                .unwrap_or_else(|| "All categories".into());
            egui::ComboBox::from_id_salt("text_category")
                .selected_text(elide(&label, 22))
                .width(170.0)
                .show_ui(ui, |ui| {
                    if ui
                        .selectable_label(self.category.is_none(), "All categories")
                        .clicked()
                    {
                        self.category = None;
                    }
                    for (family, count) in &families {
                        let selected = self.category.as_deref() == Some(family.as_str());
                        if ui
                            .selectable_label(selected, format!("{family}  ({count})"))
                            .clicked()
                        {
                            self.category = Some(family.clone());
                        }
                    }
                });
            let label = self.scene.clone().unwrap_or_else(|| "All scenes".into());
            egui::ComboBox::from_id_salt("text_scene")
                .selected_text(elide(&label, 18))
                .width(140.0)
                .show_ui(ui, |ui| {
                    if ui
                        .selectable_label(self.scene.is_none(), "All scenes")
                        .clicked()
                    {
                        self.scene = None;
                    }
                    for scene in &scenes {
                        if ui
                            .selectable_label(self.scene.as_deref() == Some(scene.as_str()), scene)
                            .clicked()
                        {
                            self.scene = Some(scene.clone());
                        }
                    }
                });
            ui.add(
                egui::TextEdit::singleline(&mut self.bank_filter)
                    .hint_text("filter bank key\u{2026}")
                    .desired_width(150.0),
            );
            egui::ComboBox::from_id_salt("text_bank")
                .selected_text(elide(&format!("{}  ({} strings)", meta.key, meta.count), 48))
                .width(400.0)
                .show_ui(ui, |ui| {
                    for (i, key, count, kind) in &options {
                        if ui
                            .selectable_label(
                                self.bank == Some(*i),
                                format!("{:<44} {:>6}  {}", elide(key, 44), count, kind),
                            )
                            .clicked()
                        {
                            picked = Some(*i);
                        }
                    }
                });
            ui.label(theme::faint_label(format!(
                "{} \u{b7} {} strings \u{b7} {} speaker(s) \u{b7} {} \u{b7} {} px \u{b7} {} lines",
                meta.kind,
                human_count(meta.count),
                human_count(meta.speakers),
                meta.font,
                meta.box_width as u32,
                meta.box_lines
            )));
            ui.label(theme::faint_label(format!("pack {}", meta.pack)));
        });
        if let Some(bank) = picked {
            self.select_bank(bank);
        }
    }

    fn entry_browser(&mut self, ui: &mut egui::Ui) {
        let Some(meta) = self.current_bank() else { return };
        // Take the draft out while the table holds it, so the filter widgets
        // can still mutate `self` in the same frame.
        let Some(entries) = self.drafts.remove(&meta.key) else { return };
        let needle = self.entry_query.to_lowercase();
        let role = self.role_filter.clone();
        let visible: Vec<usize> = entries
            .iter()
            .enumerate()
            .filter(|(_, entry)| {
                if let Some(role) = &role {
                    if &entry.role != role {
                        return false;
                    }
                }
                if needle.is_empty() {
                    return true;
                }
                entry.text.to_lowercase().contains(&needle)
                    || entry.speaker.to_lowercase().contains(&needle)
                    || entry.location.to_lowercase().contains(&needle)
            })
            .map(|(i, _)| i)
            .collect();
        let selected = self.selected_entry;
        let mut clicked = None;
        ui.horizontal_wrapped(|ui| {
            ui.add(
                egui::TextEdit::singleline(&mut self.entry_query)
                    .hint_text("filter this bank (text, speaker, location)\u{2026}")
                    .desired_width(300.0),
            );
            let role_label = match &self.role_filter {
                None => "Every role",
                Some(role) if role == "speaker" => "Speakers only",
                Some(_) => "Text lines only",
            };
            egui::ComboBox::from_id_salt("text_role")
                .selected_text(role_label)
                .width(140.0)
                .show_ui(ui, |ui| {
                    for (label, value) in [
                        ("Every role", None),
                        ("Text lines only", Some("text".to_string())),
                        ("Speakers only", Some("speaker".to_string())),
                    ] {
                        if ui
                            .selectable_label(self.role_filter == value, label)
                            .clicked()
                        {
                            self.role_filter = value;
                        }
                    }
                });
            ui.label(theme::faint_label(format!(
                "{} of {} rows",
                human_count(visible.len()),
                human_count(entries.len())
            )));
        });
        let height = (ui.available_height() * 0.36).clamp(130.0, 360.0);
        ui.allocate_ui(egui::vec2(ui.available_width(), height), |ui| {
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("game_text_rows")
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::exact(46.0))
                .column(Column::exact(56.0))
                .column(Column::initial(110.0).at_least(70.0))
                .column(Column::initial(150.0).at_least(90.0))
                .column(Column::remainder().at_least(140.0))
                .header(20.0, |mut header| {
                    for title in ["#", "Role", "Speaker", "Location", "Text"] {
                        header.col(|ui| {
                            ui.label(theme::faint_label(title));
                        });
                    }
                })
                .body(|body| {
                    body.rows(18.0, visible.len(), |mut row| {
                        let index = visible[row.index()];
                        let entry = &entries[index];
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            ui.label(theme::mono(format!("{index}")));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(entry.role.clone()));
                        });
                        row.col(|ui| {
                            ui.label(theme::dim_label(elide(&entry.speaker, 24)));
                        });
                        row.col(|ui| {
                            ui.label(theme::mono(elide(&entry.location, 30)));
                        });
                        row.col(|ui| {
                            ui.label(
                                egui::RichText::new(elide(&plain_text(&entry.text), 160))
                                    .size(12.0),
                            );
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
        });
        self.drafts.insert(meta.key, entries);
        if let Some(index) = clicked {
            self.selected_entry = Some(index);
            self.load_edit();
        }
    }

    // ---------------------------------------------------------------- editor
    #[allow(deprecated)] // a fixed widget id is exactly what the palette needs
    fn editor(&mut self, app: &mut ViewerApp, ui: &mut egui::Ui, meta: &BankMeta) {
        let Some(base_bank) = self.bank else { return };
        let selected = self.selected_entry;
        if let Some(index) = selected {
            let want = (meta.key.clone(), index);
            if self.edit_for.as_ref() != Some(&want) {
                self.load_edit();
            }
        }
        let mut edit = std::mem::take(&mut self.edit);
        let mut changed = false;
        let mut save_clicked = false;
        ui.separator();
        // Inspector: facts about the bank and the selected entry
        egui::CollapsingHeader::new(egui::RichText::new("Inspector").strong())
            .id_salt("dialogue_inspector")
            .default_open(false)
            .show(ui, |ui| {
                let entry = selected.and_then(|i| self.entries().and_then(|e| e.get(i)).cloned());
                let text_now = if selected.is_some() { edit.clone() } else { String::new() };
                let mut rows: Vec<(&str, String)> = vec![
                    ("bank", meta.key.clone()),
                    ("pack / member", format!("{} / {}", meta.pack, meta.member)),
                    ("category", format!("{}  \u{b7}  {}", meta.category, meta.kind)),
                    ("font / box", format!("{}  \u{b7}  {:.0} px, {} lines", meta.font, meta.box_width, meta.box_lines)),
                    ("entries", format!("{} ({} speakers)", meta.count, meta.speakers)),
                ];
                if let Some(entry) = &entry {
                    rows.push(("entry", format!("#{}  at 0x{:X}", entry.id, entry.offset)));
                    rows.push(("role", entry.role.clone()));
                    rows.push(("speaker", entry.speaker.clone()));
                    rows.push(("location", entry.location.clone()));
                    let pages = text_now.matches("[page]").count() + 1;
                    rows.push(("length", format!("{} characters, {} lines, ~{} message page(s)", text_now.chars().count(), text_now.lines().count().max(1), pages)));
                    rows.push(("state", if text_now == entry.text { "unchanged".to_string() } else { "edited (not saved)".to_string() }));
                }
                crate::ui::kv_rows(ui, &rows);
                ui.label(theme::faint_label("Tags (colours, names, pauses) are shown as written; the preview below uses the game's font and box size."));
            });
        ui.horizontal_wrapped(|ui| {
            match selected {
                Some(index) => {
                    let (location, role, speaker) = self
                        .entries()
                        .and_then(|entries| entries.get(index))
                        .map(|entry| {
                            (
                                entry.location.clone(),
                                entry.role.clone(),
                                entry.speaker.clone(),
                            )
                        })
                        .unwrap_or_default();
                    ui.label(theme::accent(format!("entry {index}")));
                    ui.label(theme::mono(location));
                    ui.label(theme::faint_label(role));
                    if !speaker.is_empty() {
                        ui.label(theme::dim_label(format!("\u{2014} {speaker}")));
                    }
                }
                None => {
                    ui.label(theme::dim_label("pick a line in the list above"));
                }
            }
            let dirty = self.dirty_count();
            ui.separator();
            ui.label(theme::faint_label(format!("{dirty} unsaved change(s)")));
            let busy = self.save_job.is_some();
            if ui
                .add_enabled(
                    dirty > 0 && !busy && selected.is_some(),
                    egui::Button::new("Save to mod"),
                )
                .on_hover_text(
                    "rebuild this bank with the edited strings and stage its RomFS pack \
                     under mod/romfs (LayeredFS). game_data/ and original/ are never touched",
                )
                .clicked()
            {
                save_clicked = true;
            }
            if self.save_job.is_some() {
                ui.spinner();
                ui.label(theme::faint_label("rebuilding the pack\u{2026}"));
            }
            if ui
                .add_enabled(dirty > 0 && !busy, egui::Button::new("Revert bank"))
                .on_hover_text("throw away every edit in this bank")
                .clicked()
            {
                self.drafts.remove(&meta.key);
                let entries = self
                    .index_mut()
                    .and_then(|index| index.ensure_bank(base_bank).map(|doc| doc.entries.clone()));
                if let Some(entries) = entries {
                    self.drafts.insert(meta.key.clone(), entries);
                }
                self.selected_entry = selected;
                self.load_edit();
                self.status_text = "reverted this bank".into();
                self.status_text_bad = false;
            }
            ui.separator();
            let mut width = self.width_override.unwrap_or(meta.box_width);
            if ui
                .add(
                    egui::DragValue::new(&mut width)
                        .range(40.0..=900.0)
                        .speed(1.0)
                        .prefix("box "),
                )
                .on_hover_text("textbox width in game pixels (bank default shown)")
                .changed()
            {
                self.width_override = Some(width);
            }
            ui.add(
                egui::DragValue::new(&mut self.zoom)
                    .range(0.5..=3.0)
                    .speed(0.05)
                    .prefix("zoom "),
            );
        });
        if !self.status_text.is_empty() {
            let color = if self.status_text_bad {
                theme::ERR
            } else {
                theme::TEXT_DIM
            };
            ui.label(egui::RichText::new(self.status_text.clone()).color(color));
        }
        if save_clicked {
            self.save(app);
        }

        let width = self.width_override.unwrap_or(meta.box_width);
        let font = self
            .index()
            .and_then(|index| index.bank_font(base_bank))
            .cloned();
        let column_width = ((ui.available_width() - 12.0) / 2.0).max(120.0);
        ui.columns(2, |columns| {
            let id = egui::Id::new("game_text_edit");
            columns[0].label(theme::accent("Text (tags are game codes)"));
            let response = columns[0].add(
                egui::TextEdit::multiline(&mut edit)
                    .id(id)
                    .desired_rows(7)
                    .desired_width(f32::INFINITY)
                    .font(egui::TextStyle::Monospace)
                    .code_editor(),
            );
            if response.changed() {
                changed = true;
            }
            columns[0].horizontal_wrapped(|ui| {
                ui.label(theme::faint_label("Insert"));
                for (tag, hint, back) in [
                    ("{PLAYER}", "the hero's / acting character's name", 0),
                    ("{NAME}", "battle: attacker or monster name", 0),
                    ("{TARGET}", "battle: the one being acted on", 0),
                    ("{ITEM}", "item or skill name", 0),
                    ("{NUMBER}", "a number (damage, EXP, value)", 0),
                    ("{CR}", "wait for the player to press a button", 0),
                    ("{PAGE}", "start a new message box", 0),
                    ("{ruby:|}", "furigana: {ruby:base|reading}", 1),
                ] {
                    if ui.button(tag).on_hover_text(hint).clicked() {
                        insert_tag(ui, id, &mut edit, tag, back);
                        changed = true;
                    }
                }
                if ui.button("all tags").on_hover_text(
                    "message-argument slots and formatting switches",
                ).clicked() {
                    self.status_text = dialogues::ARG_NAMES
                        .iter()
                        .map(|(name, slot)| format!("{{v:{slot:X}}}={{{name}}}"))
                        .chain(dialogues::FORMAT_CODES.iter().map(|c| format!("{{FMT:{c:02X}}}")))
                        .collect::<Vec<_>>()
                        .join("  ");
                    self.status_text_bad = false;
                }
            });
            columns[0].label(theme::faint_label(format!(
                "{} UTF-16 units{}  \u{b7}  tags: {}",
                dialogues::encode_tagged(&edit).map(|raw| raw.encode_utf16().count()).unwrap_or(0),
                if font.as_ref().map(|f| f.name.as_str()) == Some("3D14") {
                    format!(" (message buffer: {MESSAGE_MAX_UNITS})")
                } else {
                    String::new()
                },
                {
                    let tags = tags_of(&edit);
                    if tags.is_empty() {
                        "none".to_string()
                    } else {
                        elide(&tags.join(" "), 60)
                    }
                }
            )));

            // ---- preview -------------------------------------------------
            columns[1].label(theme::accent("Preview with the game's glyph widths"));
            match &font {
                Some(font) => {
                    self.draw_preview(&mut columns[1], &edit, font, width, column_width);
                    for warning in warnings(&edit, font, width, meta.box_lines) {
                        columns[1].label(egui::RichText::new(warning).color(theme::WARN).size(12.0));
                    }
                }
                None => {
                    columns[1].label(theme::dim_label(
                        "BFFNT font not loaded; cannot measure this bank",
                    ));
                }
            }
        });

        if changed {
            if let Some(sel) = selected {
                if let Some(entries) = self.entries_mut() {
                    if let Some(entry) = entries.get_mut(sel) {
                        if entry.text != edit {
                            let old = entry.text.clone();
                            entry.text = edit.clone();
                            let k = meta.key.clone();
                            let same = self.undo.last().is_some_and(|(key, i, _)| *key == k && *i == sel);
                            if !same {
                                self.undo.push((k, sel, old));
                                if self.undo.len() > 200 {
                                    self.undo.remove(0);
                                }
                            }
                            self.redo.clear();
                        }
                    }
                }
            }
        }
        self.edit = edit;
    }

    fn draw_preview(
        &self,
        ui: &mut egui::Ui,
        tagged: &str,
        font: &GlyphFont,
        width: f32,
        available: f32,
    ) {
        let pages = split_pages(tagged);
        // Fit the game's pixel box into the space the column really has.
        let scale = (self.zoom)
            .min((available - 16.0) / width.max(1.0))
            .max(0.35);
        let line_h = (font.height.max(12) as f32) * scale;
        let pad = 6.0 * scale;
        let box_w = width * scale;
        let text_color = theme::TEXT;
        for (page_index, page) in pages.iter().enumerate() {
            if pages.len() > 1 {
                ui.label(theme::faint_label(format!(
                    "message box {} of {}",
                    page_index + 1,
                    pages.len()
                )));
            }
            let lines = page.len().max(1) as f32;
            let (rect, _) = ui.allocate_exact_size(
                egui::vec2(box_w + pad * 2.0 + 4.0, lines * line_h + pad * 2.0),
                egui::Sense::hover(),
            );
            let painter = ui.painter();
            painter.rect_filled(rect, 3.0, egui::Color32::from_rgb(0x0c, 0x0d, 0x12));
            painter.rect_stroke(
                rect,
                3.0,
                egui::Stroke::new(1.0, theme::ACCENT_DIM),
                egui::StrokeKind::Inside,
            );
            let font_id = egui::FontId::proportional(line_h * 0.86);
            let chip_bg = egui::Color32::from_rgb(0x23, 0x2a, 0x36);
            for (line_index, line) in page.iter().enumerate() {
                let y = rect.top() + pad + line_index as f32 * line_h;
                let mut x = rect.left() + pad;
                for piece in line {
                    match piece {
                        Piece::Text(c) => {
                            let color = if font.has(*c) {
                                text_color
                            } else {
                                theme::ERR
                            };
                            painter.text(
                                egui::pos2(x, y),
                                egui::Align2::LEFT_TOP,
                                c.to_string(),
                                font_id.clone(),
                                color,
                            );
                            x += font.advance(*c) as f32 * scale;
                        }
                        Piece::Var(slot) => {
                            let w = dialogues::var_width(font) * scale;
                            painter.rect_filled(
                                egui::Rect::from_min_size(
                                    egui::pos2(x, y + 1.0),
                                    egui::vec2(w, line_h - 2.0),
                                ),
                                2.0,
                                chip_bg,
                            );
                            painter.text(
                                egui::pos2(x + 2.0, y + line_h * 0.12),
                                egui::Align2::LEFT_TOP,
                                arg_label(*slot),
                                egui::FontId::proportional((line_h * 0.55).max(8.0)),
                                theme::TEXT_DIM,
                            );
                            x += w;
                        }
                        Piece::Cr | Piece::Newline | Piece::Page => {}
                    }
                }
                if x > rect.right() - pad {
                    painter.line_segment(
                        [
                            egui::pos2(rect.right() - 1.0, rect.top()),
                            egui::pos2(rect.right() - 1.0, rect.bottom()),
                        ],
                        egui::Stroke::new(2.0, theme::ERR),
                    );
                }
            }
        }
        ui.label(theme::faint_label(format!(
            "{} font \u{b7} {} glyph height \u{b7} box {} px \u{b7} {:.1}\u{d7}",
            font.name, font.height, width, scale
        )));
    }

    // ---------------------------------------------------------------- save
    /// File > Save All: rebuild the open bank and stage its pack.
    pub fn save_open_bank(&mut self, app: &mut ViewerApp) {
        self.save(app);
    }

    fn save(&mut self, app: &mut ViewerApp) {
        let Some(bank) = self.bank else { return };
        let Some(meta) = self.current_bank() else { return };
        let Some(entries) = self.drafts.get(&meta.key).cloned() else { return };
        for entry in &entries {
            if let Err(err) = dialogues::encode_tagged(&entry.text) {
                self.status_text = format!("cannot save {}: {err}", entry.location);
                self.status_text_bad = true;
                return;
            }
        }
        let Some(doc) = self
            .index()
            .and_then(|index| index.bank_document(bank, &entries))
        else {
            self.status_text = "cannot build the bank document".into();
            self.status_text_bad = true;
            return;
        };
        let path = app
            .dirs
            .root
            .join("build")
            .join("text_edits")
            .join(format!("{}.json", meta.key));
        if let Some(parent) = path.parent() {
            if std::fs::create_dir_all(parent).is_err() {
                self.status_text = format!("cannot create {}", parent.display());
                self.status_text_bad = true;
                return;
            }
        }
        match std::fs::write(&path, serde_json::to_vec_pretty(&doc).unwrap_or_default()) {
            Ok(()) => {}
            Err(err) => {
                self.status_text = format!("cannot write {}: {err}", path.display());
                self.status_text_bad = true;
                return;
            }
        }
        let root = app.dirs.root.clone();
        let key = meta.key.clone();
        let (tx, rx) = std::sync::mpsc::channel();
        self.save_job = Some(rx);
        self.save_entries = Some((bank, entries));
        self.status_text = format!("wrote {} - rebuilding the pack\u{2026}", path.display());
        self.status_text_bad = false;
        std::thread::spawn(move || {
            let result = std::process::Command::new("python")
                .arg(root.join("tools").join("text_tool.py"))
                .arg("save-mod")
                .arg("--bank")
                .arg(&key)
                .arg("--json")
                .arg(&path)
                .current_dir(&root)
                .output();
            let message = match result {
                Ok(output) if output.status.success() => Ok(String::from_utf8_lossy(&output.stdout)
                    .trim()
                    .to_string()),
                Ok(output) => Err(format!(
                    "text rebuild failed: {}",
                    String::from_utf8_lossy(&output.stderr).trim()
                )),
                Err(err) => Err(format!(
                    "could not run python ({err}). The edited JSON is at {}. Rebuild it with: \
                     python tools/text_tool.py save-mod --bank {key} --json <file>",
                    path.display()
                )),
            };
            let _ = tx.send(message);
        });
    }

    fn poll_save(&mut self, ctx: &egui::Context) {
        // Take the receiver out: the arms below mutate `self`.
        let Some(rx) = self.save_job.take() else { return };
        match rx.try_recv() {
            Ok(Ok(text)) => {
                self.status_text = format!("saved: {text}");
                self.status_text_bad = false;
                if let Some((bank, entries)) = self.save_entries.take() {
                    if let Some(index) = self.index_mut() {
                        index.set_bank_entries(bank, entries);
                    }
                    // The draft now matches the cached bank again, so the
                    // "unsaved changes" count drops to zero.
                    self.load_edit();
                }
            }
            Ok(Err(text)) => {
                self.status_text = text;
                self.status_text_bad = true;
                self.save_entries = None;
            }
            Err(TryRecvError::Empty) => {
                // still rebuilding the PACK
                self.save_job = Some(rx);
                ctx.request_repaint_after(std::time::Duration::from_millis(150));
            }
            Err(TryRecvError::Disconnected) => {
                self.status_text = "the save job stopped without a result".into();
                self.status_text_bad = true;
                self.save_entries = None;
            }
        }
    }
}

/// Insert a palette tag at the text cursor (falls back to the end).
fn insert_tag(ui: &egui::Ui, id: egui::Id, text: &mut String, tag: &str, back: usize) {
    let state = egui::text_edit::TextEditState::load(ui.ctx(), id);
    let cursor = state
        .as_ref()
        .and_then(|state| state.cursor.char_range())
        .map(|range| range.primary.index.0)
        .unwrap_or_else(|| text.chars().count());
    let byte = char_to_byte(text, cursor);
    text.insert_str(byte, tag);
    let new_cursor = cursor + tag.chars().count() - back;
    if let Some(mut state) = state {
        state
            .cursor
            .set_char_range(Some(egui::text_selection::CCursorRange::one(
                egui::epaint::text::cursor::CCursor::new(new_cursor),
            )));
        state.store(ui.ctx(), id);
    }
}

fn char_to_byte(text: &str, index: usize) -> usize {
    text.char_indices()
        .nth(index)
        .map(|(byte, _)| byte)
        .unwrap_or(text.len())
}

/// Display label of a U+0004 slot in the preview.
fn arg_label(slot: u8) -> String {
    if let Some((name, _)) = ARG_NAMES.iter().find(|(_, value)| *value == slot) {
        return format!("{{{name}}}");
    }
    if FORMAT_CODES.contains(&slot) {
        return format!("{{FMT:{slot:02X}}}");
    }
    format!("{{v:{slot:X}}}")
}

/// Tagged text split into message boxes -> lines -> pieces, for the preview.
fn split_pages(tagged: &str) -> Vec<Vec<Vec<Piece>>> {
    let mut pages: Vec<Vec<Vec<Piece>>> = vec![vec![Vec::new()]];
    for piece in dialogues::pieces(tagged).unwrap_or_default() {
        match piece {
            Piece::Page => pages.push(vec![Vec::new()]),
            Piece::Newline => {
                if let Some(page) = pages.last_mut() {
                    page.push(Vec::new());
                }
            }
            other => {
                if let Some(line) = pages.last_mut().and_then(|page| page.last_mut()) {
                    line.push(other);
                }
            }
        }
    }
    pages
}

/// What the game would do wrong with this text, in plain words.
fn warnings(tagged: &str, font: &GlyphFont, width: f32, lines: usize) -> Vec<String> {
    let mut out = Vec::new();
    if let Err(err) = dialogues::encode_tagged(tagged) {
        out.push(format!("tag error: {err}"));
        return out;
    }
    let measure = dialogues::measure(tagged, font);
    if !measure.missing.is_empty() {
        let list: Vec<String> = measure
            .missing
            .iter()
            .take(12)
            .map(|c| format!("{c} (U+{:04X})", *c as u32))
            .collect();
        out.push(format!(
            "{} glyph(s) missing from {}: {}",
            measure.missing.len(),
            font.name,
            list.join(", ")
        ));
    }
    for (page, widths) in measure.pages.iter().enumerate() {
        for (line, w) in widths.iter().enumerate() {
            if *w > width {
                out.push(format!(
                    "message {} line {}: {:.0} px, the box holds {:.0} px",
                    page + 1,
                    line + 1,
                    w,
                    width
                ));
            }
        }
        if widths.len() > lines {
            out.push(format!(
                "message {} has {} lines; the box shows {}",
                page + 1,
                widths.len(),
                lines
            ));
        }
    }
    if font.name == "3D14" && measure.units > MESSAGE_MAX_UNITS {
        out.push(format!(
            "{} UTF-16 units: the message buffer holds {MESSAGE_MAX_UNITS}, \
             the rest is cut off",
            measure.units
        ));
    }
    out
}

#[cfg(test)]
mod text_panel_tests {
    use super::*;
    use std::path::Path;

    #[test]
    fn text_undo_and_redo_swap_the_entry_text() {
        let mut panel = DialoguesPanel::default();
        let entry = |t: &str| TextEntry { id: 0, offset: 0, role: "text".into(), speaker: String::new(), location: String::new(), text: t.into() };
        panel.drafts.insert("bank".into(), vec![entry("new")]);
        panel.undo.push(("bank".into(), 0, "old".into()));
        assert!(panel.can_undo() && !panel.can_redo());
        panel.undo_action();
        assert_eq!(panel.drafts["bank"][0].text, "old");
        assert!(!panel.can_undo() && panel.can_redo());
        panel.redo_action();
        assert_eq!(panel.drafts["bank"][0].text, "new");
    }

    fn font() -> Option<GlyphFont> {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent()?;
        let data = std::fs::read(root.join("game_data/romfs/font/3D14.bffnt")).ok()?;
        GlyphFont::parse("3D14", &data)
    }

    #[test]
    fn preview_splits_message_boxes_and_lines() {
        let pages = split_pages("one\ntwo{PAGE}three");
        assert_eq!(pages.len(), 2);
        assert_eq!(pages[0].len(), 2);
        assert_eq!(pages[1].len(), 1);
        // {CR} is a button wait, not a line break
        let pages = split_pages("a{CR}b");
        assert_eq!(pages.len(), 1);
        assert_eq!(pages[0].len(), 1);
        assert_eq!(pages[0][0].len(), 3); // 'a', the wait, 'b'
    }

    #[test]
    fn palette_labels_are_readable() {
        assert_eq!(arg_label(1), "{PLAYER}");
        assert_eq!(arg_label(8), "{NUMBER}");
        assert_eq!(arg_label(0x66), "{FMT:66}");
        assert_eq!(arg_label(0x20), "{v:20}");
    }

    #[test]
    fn character_offsets_handle_multibyte_text() {
        let text = "あい{PLAYER}";
        assert_eq!(char_to_byte(text, 0), 0);
        assert_eq!(char_to_byte(text, 2), 6);
        assert_eq!(char_to_byte(text, 3), 7);
        assert_eq!(char_to_byte(text, 99), text.len());
    }

    #[test]
    fn warnings_name_missing_glyphs_and_overflow() {
        let Some(font) = font() else { return };
        let missing = warnings("ok \u{10FFFD}", &font, 321.0, 3);
        assert!(missing.iter().any(|w| w.contains("missing")), "{missing:?}");
        let long = "word ".repeat(80);
        let wide = warnings(&long, &font, 120.0, 3);
        assert!(wide.iter().any(|w| w.contains("px")), "{wide:?}");
        let many = warnings("a\nb\nc\nd", &font, 321.0, 3);
        assert!(many.iter().any(|w| w.contains("4 lines")), "{many:?}");
        assert!(warnings("short line", &font, 321.0, 3).is_empty());
        assert!(warnings("{BOGUS}", &font, 321.0, 3)
            .iter()
            .any(|w| w.starts_with("tag error")));
    }
}

