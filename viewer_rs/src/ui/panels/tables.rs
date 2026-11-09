//! Parameter tables: a searchable, grouped table list, and a spreadsheet editor
//! for the BXON rows.
//!
//! Editing model: [`TableDoc`] keeps the original `.bxon` bytes and each named
//! field is a byte offset inside a row, so a number edit is a same-size scalar
//! write. A text edit appends the new string to the end of the file and
//! repoints that one row's field (the old string stays, unused). Nothing lands in the repository until **Save to mod**, which rebuilds
//! the containing RomFS pack under `mod/romfs/` and never touches `game_data/`
//! or `original/`.
//!
//! The grid only builds the visible rows (`egui_extras::TableBuilder` is
//! virtualised), which is what makes the 2875-row item table and the 1043-row
//! monster tables usable.

use std::collections::HashMap;

use eframe::egui;

use crate::app::{Data, ViewerApp};
use crate::data::tables::{Field, FieldType, TableDoc, Value};
use crate::theme;
use crate::ui::{Lang, TextState};
use crate::utils::{human_count, human_size};

#[derive(Clone, Copy, PartialEq, Eq, Default)]
enum Tab {
    #[default]
    Grid,
    Structure,
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
    fn default() -> Self {
        Self::Name
    }
}

/// The cell currently being edited. Only one is open at a time.
struct EditState {
    row: usize,
    field: usize,
    text: String,
    error: Option<String>,
    /// Focus is grabbed on the first frame only, so clicking away commits.
    fresh: bool,
}

/// Everything the grid asks for while it draws. Applied afterwards, so the draw
/// closure never needs two mutable borrows of the app at once.
enum Action {
    Begin(usize, usize),
    Commit(usize, usize, String),
    Set(usize, usize, Value),
    Cancel,
    Undo,
    Redo,
    Revert,
    Save,
    /// Copy this row into the next free (id 0) row.
    AddEntry(usize),
}

pub struct TablesPanel {
    pub query: String,
    pub category: Option<String>,
    sort: SortKey,
    sort_desc: bool,
    list: Vec<usize>,
    selected: Option<usize>,
    /// The grid row the user last opened a cell in; "Add entry" copies it.
    last_row: Option<usize>,
    dirty: bool,
    request: Option<String>,
    json: Option<serde_json::Value>,
    raw: TextState,
    tab: Tab,
    /// The table opened for editing.
    doc: Option<TableDoc>,
    /// Which list entry `doc` belongs to, so selecting another table reloads.
    doc_for: Option<usize>,
    edit: Option<EditState>,
    /// Row indices matching the row filter.
    visible: Vec<usize>,
    row_filter: String,
    row_filter_dirty: bool,
    status: String,
    status_bad: bool,
    save_job: Option<std::sync::mpsc::Receiver<Result<String, String>>>,
    /// Display type for tables with no schema.
    generic_type: FieldType,
}

impl Default for TablesPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            category: None,
            // Grouped by category on first open: the 5,929-table list is only
            // navigable when syscmn/ sits next to syscmn/.
            sort: SortKey::Category,
            sort_desc: false,
            list: Vec::new(),
            selected: None,
            last_row: None,
            dirty: true, // build the list on first show
            request: None,
            json: None,
            raw: TextState::default(),
            tab: Tab::default(),
            doc: None,
            doc_for: None,
            edit: None,
            visible: Vec::new(),
            row_filter: String::new(),
            row_filter_dirty: true,
            status: String::new(),
            status_bad: false,
            save_job: None,
            generic_type: FieldType::U32,
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
        self.sort = SortKey::Category;
        self.sort_desc = false;
        self.dirty = true;
        self.doc = None;
        self.doc_for = None;
        self.edit = None;
    }

    fn sort_list(&mut self, data: &Data) {
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

    fn open_doc(&mut self, dirs: &crate::utils::Dirs, index: usize, rel: &str) {
        self.doc = TableDoc::open(dirs, rel);
        self.doc_for = Some(index);
        self.edit = None;
        self.row_filter_dirty = true;
        self.status = match &self.doc {
            Some(doc) if doc.has_schema() => String::new(),
            Some(_) => "no field names for this table yet; use the raw columns".into(),
            None => "cannot open the original BXON for this table".into(),
        };
        self.status_bad = self.doc.is_none();
    }

    fn refresh_visible(&mut self) {
        let Some(doc) = &self.doc else {
            self.visible.clear();
            return;
        };
        let needle = self.row_filter.trim().to_lowercase();
        self.visible = if needle.is_empty() {
            (0..doc.row_count()).collect()
        } else {
            (0..doc.row_count())
                .filter(|r| {
                    doc.labels()[*r].to_lowercase().contains(&needle)
                        || doc.id_of(*r).to_string().contains(&needle)
                })
                .collect()
        };
        self.row_filter_dirty = false;
    }

    pub fn modified_cells(&self) -> usize {
        let Some(doc) = &self.doc else { return 0 };
        let mut n = 0;
        for row in 0..doc.row_count() {
            for field in doc.fields() {
                if doc.is_dirty(row, field) {
                    n += 1;
                }
            }
        }
        n
    }
}

// ---------------------------------------------------------------------------
// reference dropdown data
// ---------------------------------------------------------------------------
#[derive(Default)]
struct RefTable {
    list: Vec<(i64, String)>,
    map: HashMap<i64, String>,
}

thread_local! {
    /// `table rel` -> id/name pairs, filled once per table and reused by every
    /// cell so a 24-slot shop does not rescan the 2875-row item table.
    static REFERENCES: std::cell::RefCell<HashMap<String, RefTable>> =
        std::cell::RefCell::new(HashMap::new());
}

fn reference_ready(table: &str) -> bool {
    REFERENCES.with(|cache| cache.borrow().contains_key(table))
}

fn cache_reference(table: &str, options: Vec<(i64, String)>) {
    REFERENCES.with(|cache| {
        let mut map = HashMap::with_capacity(options.len());
        for (id, label) in &options {
            map.entry(*id).or_insert_with(|| label.clone());
        }
        cache
            .borrow_mut()
            .insert(table.to_string(), RefTable { list: options, map });
    });
}

fn reference_list(table: &str) -> Vec<(i64, String)> {
    REFERENCES.with(|cache| {
        cache
            .borrow()
            .get(table)
            .map(|t| t.list.clone())
            .unwrap_or_default()
    })
}

fn reference_name(table: &str, id: i64) -> Option<String> {
    REFERENCES.with(|cache| {
        cache
            .borrow()
            .get(table)
            .and_then(|t| t.map.get(&id).cloned())
    })
}

// ---------------------------------------------------------------------------
// entry point
// ---------------------------------------------------------------------------
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
                    .or_else(|| {
                        data.tables
                            .items
                            .iter()
                            .position(|t| t.name.eq_ignore_ascii_case(&name))
                    })
                {
                    panel.selected = Some(index);
                    let path = data.tables.items[index].path.clone();
                    let json = app.data_mut().and_then(|d| d.tables.load(&path));
                    if let Some(json) = &json {
                        let pretty = serde_json::to_string_pretty(json).unwrap_or_default();
                        app.panels.tables.raw.set(&pretty, Lang::Json);
                    }
                    app.panels.tables.json = json;
                }
            }
        }
    }

    list_panel(app, ui);
    inspector_panel(app, ui);
    detail_panel(app, ui);
}

// ---------------------------------------------------------------------------
// left: grouped table list
// ---------------------------------------------------------------------------
fn list_panel(app: &mut ViewerApp, ui: &mut egui::Ui) {
    egui::Panel::left("table_list")
        .exact_size(320.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Parameter tables"));
            let total = app.data().map(|d| d.tables.items.len()).unwrap_or(0);
            let named = app.data().map(|d| d.tables.named_tables()).unwrap_or(0);
            ui.label(theme::faint_label(format!(
                "{} tables \u{b7} {named} with field names",
                human_count(total)
            )));
            let categories: Vec<(String, usize)> = app
                .data()
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
                    if ui
                        .selectable_label(app.panels.tables.category.is_none(), "All categories")
                        .clicked()
                    {
                        app.panels.tables.category = None;
                        app.panels.tables.dirty = true;
                    }
                    for (name, count) in categories {
                        let selected = app.panels.tables.category.as_deref() == Some(name.as_str());
                        if ui
                            .selectable_label(selected, format!("{name}  ({count})"))
                            .clicked()
                        {
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
            ui.label(theme::faint_label(format!(
                "{} tables",
                human_count(app.panels.tables.list.len())
            )));
            ui.horizontal(|ui| {
                egui::ComboBox::from_id_salt("table_sort")
                    .selected_text(match app.panels.tables.sort {
                        SortKey::Name => "Sort: name",
                        SortKey::Category => "Sort: category",
                        SortKey::Size => "Sort: size",
                    })
                    .show_ui(ui, |ui| {
                        for (key, label) in [
                            (SortKey::Name, "Name"),
                            (SortKey::Category, "Category"),
                            (SortKey::Size, "Size"),
                        ] {
                            if ui
                                .selectable_label(app.panels.tables.sort == key, label)
                                .clicked()
                            {
                                app.panels.tables.sort = key;
                                app.panels.tables.dirty = true;
                            }
                        }
                    });
                if ui
                    .button(if app.panels.tables.sort_desc {
                        "Descending"
                    } else {
                        "Ascending"
                    })
                    .clicked()
                {
                    app.panels.tables.sort_desc = !app.panels.tables.sort_desc;
                    app.panels.tables.dirty = true;
                }
            });
            ui.separator();
            let list = app.panels.tables.list.clone();
            let selected = app.panels.tables.selected;
            let mut clicked = None;
            let nav = crate::ui::list_nav(ui.ctx(), &list, selected.as_ref());
            if let Some((item, _)) = &nav {
                clicked = Some(item.clone());
            }
            let nav_row = nav.map(|(_, r)| r);
            use egui_extras::{Column, TableBuilder};
            use crate::ui::TableNav;
            TableBuilder::new(ui)
                .id_salt("table_scroll")
                .nav_scroll(nav_row)
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::remainder().at_least(120.0))
                .column(Column::exact(18.0))
                .column(Column::exact(68.0))
                .header(20.0, |mut header| {
                    for title in ["Table", "", "Size"] {
                        header.col(|ui| {
                            ui.label(theme::faint_label(title));
                        });
                    }
                })
                .body(|body| {
                    body.rows(18.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let Some(table) = app.data().and_then(|d| d.tables.items.get(index)) else {
                            return;
                        };
                        let name = table.name.clone();
                        let size = table.size;
                        let named = app
                            .data()
                            .and_then(|d| d.tables.schema_for(&table.rel))
                            .is_some();
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            let text = egui::RichText::new(name)
                                .size(12.0)
                                .color(if named { theme::TEXT } else { theme::TEXT_DIM });
                            let response = ui.label(text);
                            if !named {
                                response.on_hover_text("no field names yet - editable by offset");
                            }
                        });
                        row.col(|ui| {
                            if named {
                                let _ = ui
                                    .label(egui::RichText::new("\u{25cf}").color(theme::ACCENT).size(8.0))
                                    .on_hover_text("has field names");
                            }
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(human_size(size)));
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(index) = clicked {
                if app.panels.tables.selected != Some(index) {
                    app.panels.tables.selected = Some(index);
                    app.panels.tables.json = None;
                    app.panels.tables.raw = TextState::default();
                    app.panels.tables.doc = None;
                    app.panels.tables.doc_for = None;
                    app.panels.tables.edit = None;
                }
            }
        });
}

// ---------------------------------------------------------------------------
// right: header, tabs and the grid
// ---------------------------------------------------------------------------
/// Right-hand Inspector: what the open table is, and what has changed in it.
fn inspector_panel(app: &mut ViewerApp, ui: &mut egui::Ui) {
    egui::Panel::right("table_inspector")
        .exact_size(280.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Inspector"));
            ui.separator();
            let Some(index) = app.panels.tables.selected else {
                ui.label(theme::faint_label("Select a table in the list."));
                return;
            };
            let Some((name, category, size, rel)) = app
                .data()
                .and_then(|d| d.tables.items.get(index))
                .map(|t| (t.name.clone(), t.category.clone(), t.size, t.rel.clone()))
            else {
                return;
            };
            egui::CollapsingHeader::new(egui::RichText::new("Table").strong()).default_open(true).show(ui, |ui| {
                crate::ui::kv_rows(
                    ui,
                    &[
                        ("name", name.clone()),
                        ("category", category.clone()),
                        ("file", rel.clone()),
                        ("size", human_size(size)),
                    ],
                );
            });
            let mut action: Option<Action> = None;
            if app.panels.tables.doc_for == Some(index) {
                if let Some(doc) = app.panels.tables.doc.as_ref() {
                    egui::CollapsingHeader::new(egui::RichText::new("Schema").strong()).default_open(true).show(ui, |ui| {
                        let title = doc.schema.as_ref().map(|s| s.title.clone()).filter(|t| !t.is_empty());
                        crate::ui::kv_rows(
                            ui,
                            &[
                                ("rows", doc.row_count().to_string()),
                                ("row size", format!("{} bytes", doc.row_size)),
                                ("fields", doc.fields().len().to_string()),
                                ("field names", if doc.has_schema() { "known".into() } else { "unknown (raw words)".to_string() }),
                                ("schema", title.unwrap_or_else(|| "-".into())),
                            ],
                        );
                    });
                    egui::CollapsingHeader::new(egui::RichText::new(format!("Changes ({})", doc.edit_count())).strong())
                        .default_open(true)
                        .show(ui, |ui| {
                            if doc.has_changes() {
                                ui.label(format!("{} edited cells", app.panels.tables.modified_cells()));
                                ui.horizontal(|ui| {
                                    if ui.button("Save to mod").clicked() {
                                        action = Some(Action::Save);
                                    }
                                    if ui.button("Revert all").clicked() {
                                        action = Some(Action::Revert);
                                    }
                                });
                            } else {
                                ui.label(theme::faint_label("This table matches the retail file."));
                            }
                        });
                } else {
                    ui.label(theme::faint_label("Open the Grid tab to edit this table."));
                }
            } else {
                ui.label(theme::faint_label("Open the Grid tab to edit this table."));
            }
            if let Some(action) = action {
                apply(app, action);
            }
        });
}

fn detail_panel(app: &mut ViewerApp, ui: &mut egui::Ui) {
    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let Some(index) = app.panels.tables.selected else {
                ui.label(theme::faint_label("Select a table."));
                return;
            };
            let Some((name, category, size, path, rel)) = app
                .data()
                .and_then(|d| d.tables.items.get(index))
                .map(|t| {
                    (
                        t.name.clone(),
                        t.category.clone(),
                        t.size,
                        t.path.clone(),
                        t.rel.clone(),
                    )
                })
            else {
                return;
            };

            // header
            ui.horizontal(|ui| {
                ui.label(theme::heading(name.clone()));
                ui.label(theme::dim_label(format!("{category}  \u{b7}  {}", human_size(size))));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    for (label, tab) in [
                        ("Summary", Tab::Summary),
                        ("Raw JSON", Tab::Raw),
                        ("Structure", Tab::Structure),
                        ("Grid", Tab::Grid),
                    ] {
                        if ui
                            .selectable_label(app.panels.tables.tab == tab, label)
                            .clicked()
                        {
                            app.panels.tables.tab = tab;
                        }
                    }
                });
            });

            if app.panels.tables.tab == Tab::Grid {
                grid_tab(app, ui, index, &rel);
                return;
            }

            if app.panels.tables.json.is_none() {
                let json = app.data_mut().and_then(|d| d.tables.load(&path));
                if let Some(json) = &json {
                    let pretty = serde_json::to_string_pretty(json).unwrap_or_default();
                    app.panels.tables.raw.set(&pretty, Lang::Json);
                }
                app.panels.tables.json = json;
            }
            let summary = app.data_mut().map(|d| d.tables.summary(index)).unwrap_or_default();
            ui.separator();
            match app.panels.tables.tab {
                Tab::Structure => {
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
                Tab::Grid => {}
            }
        });
}

fn grid_tab(app: &mut ViewerApp, ui: &mut egui::Ui, index: usize, rel: &str) {
    if app.panels.tables.doc_for != Some(index) {
        let dirs = app.dirs.clone();
        let mut panel = std::mem::take(&mut app.panels.tables);
        panel.open_doc(&dirs, index, rel);
        app.panels.tables = panel;
    }
    if app.panels.tables.row_filter_dirty {
        let mut panel = std::mem::take(&mut app.panels.tables);
        panel.refresh_visible();
        app.panels.tables = panel;
    }
    poll_save_job(app, ui);

    if app.panels.tables.doc.is_none() {
        ui.label(
            egui::RichText::new(format!(
                "cannot open the original BXON for {rel} - is game_data/packs present?"
            ))
            .color(theme::ERR),
        );
        return;
    }

    // Phase 1: read everything the toolbar needs, then let go of the document
    // so the toolbar can apply actions to the app.
    let (rows, row_size, column_count, changes, edits, has_schema, schema_title, note, wanted, doc_error) = {
        let doc = app.panels.tables.doc.as_ref().expect("checked above");
        let wanted: Vec<String> = doc
            .fields()
            .iter()
            .filter_map(|f| f.reference.as_ref().map(|r| r.table.clone()))
            .collect();
        (
            doc.row_count(),
            doc.row_size,
            doc.fields().len(),
            doc.has_changes(),
            doc.edit_count(),
            doc.has_schema(),
            doc.schema
                .as_ref()
                .map(|s| s.title.clone())
                .filter(|t| !t.is_empty()),
            doc.schema.as_ref().map(|s| s.note.clone()).unwrap_or_default(),
            wanted,
            doc.error.clone(),
        )
    };

    // Phase 2: load any id -> name lists this table needs, once each.
    if !wanted.is_empty() {
        let dirs = app.dirs.clone();
        for table in wanted {
            if reference_ready(&table) {
                continue;
            }
            let options = app
                .data_mut()
                .map(|d| d.tables.reference_options(&dirs, &table))
                .unwrap_or_default();
            cache_reference(&table, options);
        }
    }

    let modified = app.panels.tables.modified_cells();
    let busy = app.panels.tables.save_job.is_some();

    ui.horizontal_wrapped(|ui| {
        if let Some(title) = &schema_title {
            ui.label(theme::heading(title.clone()));
            ui.separator();
        }
        ui.label(theme::dim_label(format!(
            "{rows} rows \u{b7} {row_size} bytes each \u{b7} {column_count} columns"
        )));
        ui.separator();
        ui.add_enabled_ui(app.panels.tables.edit.is_none() && !busy, |ui| {
            if ui.button("Undo").on_hover_text("Ctrl+Z").clicked() {
                apply(app, Action::Undo);
            }
            if ui.button("Redo").on_hover_text("Ctrl+Y").clicked() {
                apply(app, Action::Redo);
            }
        });
        let free = app.panels.tables.doc.as_ref().map(|d| d.free_rows().len()).unwrap_or(0);
        if free > 0 {
            ui.separator();
            let source = app.panels.tables.last_row;
            let label = match source {
                Some(row) => format!("Add entry (copy row {row})"),
                None => "Add entry".to_string(),
            };
            if ui
                .add_enabled(source.is_some() && app.panels.tables.edit.is_none() && !busy,
                             egui::Button::new(label))
                .on_hover_text(format!(
                    "turn one of the {free} unused rows (id 0) into a copy of the row you last edited, with a new id. The table keeps its size, so the game accepts it. Open a cell first to pick the row to copy."
                ))
                .clicked()
            {
                if let Some(row) = source {
                    apply(app, Action::AddEntry(row));
                }
            }
        }
        ui.separator();
        if ui
            .add_enabled(changes && !busy, egui::Button::new("Revert"))
            .on_hover_text("throw away every edit in this table")
            .clicked()
        {
            apply(app, Action::Revert);
        }
        let label = if changes {
            format!("Save to mod ({modified} cells)")
        } else {
            "Save to mod".to_string()
        };
        if ui
            .add_enabled(changes && !busy, egui::Button::new(label))
            .on_hover_text(
                "writes build/table_edits/<table>.bxon, then rebuilds mod/romfs/<pack>.pack \
                 so a LayeredFS mod picks it up. original/ and game_data/ are never touched",
            )
            .clicked()
        {
            apply(app, Action::Save);
        }
        if edits > 0 {
            ui.label(theme::faint_label(format!("{edits} edits")));
        }
    });

    if !note.is_empty() {
        ui.label(theme::faint_label(note));
    }
    if !has_schema {
        ui.label(
            egui::RichText::new(
                "No field names for this table yet. The columns are raw offsets and stay \
                 editable; add an entry to tools/table_schemas.json to name them.",
            )
            .color(theme::WARN)
            .size(11.5),
        );
        ui.horizontal(|ui| {
            ui.label(theme::faint_label("Show each column as"));
            let mut chosen = app.panels.tables.generic_type;
            egui::ComboBox::from_id_salt("generic_type")
                .selected_text(chosen.name())
                .show_ui(ui, |ui| {
                    for ty in [FieldType::U8, FieldType::U16, FieldType::U32, FieldType::F32] {
                        if ui.selectable_label(chosen == ty, ty.name()).clicked() {
                            chosen = ty;
                        }
                    }
                });
            if chosen != app.panels.tables.generic_type {
                app.panels.tables.generic_type = chosen;
                if let Some(doc) = app.panels.tables.doc.as_mut() {
                    doc.set_generic_type(chosen);
                }
            }
        });
    }

    if !app.panels.tables.status.is_empty() {
        let color = if app.panels.tables.status_bad {
            theme::ERR
        } else {
            theme::OK
        };
        ui.label(
            egui::RichText::new(app.panels.tables.status.clone())
                .color(color)
                .size(11.5),
        );
    }
    if let Some(error) = doc_error {
        ui.label(egui::RichText::new(error).color(theme::ERR).size(11.5));
        return;
    }

    ui.horizontal(|ui| {
        ui.label(theme::faint_label("Filter rows"));
        if ui
            .add(
                egui::TextEdit::singleline(&mut app.panels.tables.row_filter)
                    .hint_text("name or id\u{2026}")
                    .desired_width(240.0),
            )
            .changed()
        {
            app.panels.tables.row_filter_dirty = true;
        }
        if ui.button("Clear").clicked() {
            app.panels.tables.row_filter.clear();
            app.panels.tables.row_filter_dirty = true;
        }
        ui.label(theme::faint_label(format!(
            "{} shown",
            human_count(app.panels.tables.visible.len())
        )));
    });
    ui.separator();

    if app.panels.tables.row_filter_dirty {
        let mut panel = std::mem::take(&mut app.panels.tables);
        panel.refresh_visible();
        app.panels.tables = panel;
    }

    // ---- the grid ------------------------------------------------------
    let fields: Vec<Field> = app
        .panels
        .tables
        .doc
        .as_ref()
        .map(|d| d.fields().to_vec())
        .unwrap_or_default();
    let visible = app.panels.tables.visible.clone();
    if fields.is_empty() || visible.is_empty() {
        ui.label(theme::faint_label("nothing to show"));
        return;
    }
    let mut actions: Vec<Action> = Vec::new();
    let mut edit = app.panels.tables.edit.take();
    {
        let doc = app.panels.tables.doc.as_ref().expect("checked above");
        draw_grid(ui, doc, &fields, &visible, &mut edit, &mut actions);
    }
    app.panels.tables.edit = edit;

    // Keyboard shortcuts are handled once, after the draw.
    let ctx = ui.ctx().clone();
    if app.panels.tables.edit.is_some() {
        if ctx.input(|i| i.key_pressed(egui::Key::Escape)) {
            actions.push(Action::Cancel);
        }
    } else if !busy {
        if ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::Z)) {
            actions.push(Action::Undo);
        }
        if ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::Y)) {
            actions.push(Action::Redo);
        }
    }

    for action in actions {
        apply(app, action);
    }
}

fn poll_save_job(app: &mut ViewerApp, ui: &egui::Ui) {
    let Some(rx) = &app.panels.tables.save_job else { return };
    match rx.try_recv() {
        Ok(Ok(text)) => {
            app.panels.tables.status = text;
            app.panels.tables.status_bad = false;
            app.panels.tables.save_job = None;
        }
        Ok(Err(text)) => {
            app.panels.tables.status = text;
            app.panels.tables.status_bad = true;
            app.panels.tables.save_job = None;
        }
        Err(std::sync::mpsc::TryRecvError::Empty) => {
            ui.ctx().request_repaint_after(std::time::Duration::from_millis(150));
        }
        Err(std::sync::mpsc::TryRecvError::Disconnected) => {
            app.panels.tables.status = "the save job stopped without a result".into();
            app.panels.tables.status_bad = true;
            app.panels.tables.save_job = None;
        }
    }
}

/// Hooks for the shell's Edit / File menus.
pub fn undo_active(app: &mut ViewerApp) {
    apply(app, Action::Undo);
}

pub fn redo_active(app: &mut ViewerApp) {
    apply(app, Action::Redo);
}

pub fn save_active(app: &mut ViewerApp) {
    if app.panels.tables.save_job.is_none() && app.panels.tables.modified_cells() > 0 {
        apply(app, Action::Save);
    }
}

pub fn can_undo_active(app: &ViewerApp) -> bool {
    app.panels.tables.doc.as_ref().is_some_and(|d| d.can_undo())
}

pub fn can_redo_active(app: &ViewerApp) -> bool {
    app.panels.tables.doc.as_ref().is_some_and(|d| d.can_redo())
}

fn apply(app: &mut ViewerApp, action: Action) {
    match action {
        Action::Begin(row, field) => {
            app.panels.tables.last_row = Some(row);
            let Some(doc) = app.panels.tables.doc.as_ref() else { return };
            let Some(spec) = doc.fields().get(field).cloned() else { return };
            if spec.read_only {
                return;
            }
            let text = match doc.value(row, &spec) {
                Value::Int(v) => v.to_string(),
                Value::Float(v) => format!("{v}"),
                Value::Text(t) => t,
            };
            app.panels.tables.edit = Some(EditState {
                row,
                field,
                text,
                error: None,
                fresh: true,
            });
        }
        Action::Commit(row, field, text) => {
            let Some(doc) = app.panels.tables.doc.as_mut() else { return };
            let Some(spec) = doc.fields().get(field).cloned() else { return };
            let result = doc
                .validate(&spec, &text)
                .and_then(|value| doc.set(row, &spec, &value));
            commit_result(app, result, None);
        }
        Action::Set(row, field, value) => {
            let Some(doc) = app.panels.tables.doc.as_mut() else { return };
            let Some(spec) = doc.fields().get(field).cloned() else { return };
            let text = match &value {
                Value::Int(v) => v.to_string(),
                Value::Float(v) => format!("{v}"),
                Value::Text(t) => t.clone(),
            };
            let result = doc
                .validate(&spec, &text)
                .and_then(|_| doc.set(row, &spec, &value));
            commit_result(app, result, None);
        }
        Action::Cancel => app.panels.tables.edit = None,
        Action::AddEntry(source) => {
            let Some(doc) = app.panels.tables.doc.as_mut() else { return };
            match doc.claim_row(source) {
                Ok(row) => {
                    let left = doc.free_rows().len();
                    let label = doc.label(row);
                    app.panels.tables.last_row = Some(row);
                    app.panels.tables.status = format!(
                        "row {row} is a new copy of row {source} ({label}); edit its name and fields there, then Save to mod. {left} free rows left."
                    );
                    app.panels.tables.status_bad = false;
                }
                Err(message) => {
                    app.panels.tables.status = message;
                    app.panels.tables.status_bad = true;
                }
            }
        }
        Action::Undo => {
            if let Some(doc) = app.panels.tables.doc.as_mut() {
                doc.undo();
            }
            app.panels.tables.edit = None;
        }
        Action::Redo => {
            if let Some(doc) = app.panels.tables.doc.as_mut() {
                doc.redo();
            }
            app.panels.tables.edit = None;
        }
        Action::Revert => {
            if let Some(doc) = app.panels.tables.doc.as_mut() {
                doc.revert();
            }
            app.panels.tables.edit = None;
            app.panels.tables.status = "reverted to the file on disk".into();
            app.panels.tables.status_bad = false;
            app.panels.tables.row_filter_dirty = true;
        }
        Action::Save => start_save(app),
    }
}

fn commit_result(app: &mut ViewerApp, result: Result<usize, String>, fallback: Option<String>) {
    match result {
        Ok(_) => {
            app.panels.tables.edit = None;
            app.panels.tables.status.clear();
            app.panels.tables.status_bad = false;
        }
        Err(message) => {
            let mut panel = std::mem::take(&mut app.panels.tables);
            if let Some(edit) = panel.edit.as_mut() {
                edit.error = Some(message.clone());
                edit.fresh = false;
            } else if let Some(text) = fallback {
                panel.status = text;
            }
            panel.status = message;
            panel.status_bad = true;
            app.panels.tables = panel;
        }
    }
}

/// Write the patched table, then rebuild its RomFS pack into `mod/romfs`.
///
/// The pack rebuild lives in Python (`tools/patch_asset.rebuild_pack`) because
/// that is where the PACK/PACA layout code already is. It runs on a thread so a
/// 10 MB `gamecmn.pack` does not freeze the window.
fn start_save(app: &mut ViewerApp) {
    // Final validation gate: no modified cell leaves the editor unless it still
    // fits its field, even if the value got there through undo/redo or a schema
    // change after the cell was typed.
    if let Some(doc) = app.panels.tables.doc.as_ref() {
        if let Some(error) = doc.validation_error() {
            app.panels.tables.status = format!("cannot save: {error}");
            app.panels.tables.status_bad = true;
            return;
        }
    }
    let Some(doc) = app.panels.tables.doc.as_ref() else { return };
    let rel = doc.rel.clone();
    let bytes = doc.bytes.clone();
    let root = app.dirs.root.clone();
    let out = root
        .join("build")
        .join("table_edits")
        .join(&rel)
        .with_extension("bxon");
    if let Some(parent) = out.parent() {
        if std::fs::create_dir_all(parent).is_err() {
            app.panels.tables.status = format!("cannot create {}", parent.display());
            app.panels.tables.status_bad = true;
            return;
        }
    }
    if let Err(err) = std::fs::write(&out, &bytes) {
        app.panels.tables.status = format!("cannot write {}: {err}", out.display());
        app.panels.tables.status_bad = true;
        return;
    }
    let (tx, rx) = std::sync::mpsc::channel();
    app.panels.tables.save_job = Some(rx);
    app.panels.tables.status = format!("wrote {} - rebuilding the pack\u{2026}", out.display());
    app.panels.tables.status_bad = false;
    std::thread::spawn(move || {
        let script = root.join("tools").join("table_edit.py");
        let result = std::process::Command::new("python")
            .arg(&script)
            .arg("save-mod")
            .arg(&rel)
            .arg("--patched")
            .arg(&out)
            .current_dir(&root)
            .output();
        let message = match result {
            Ok(output) if output.status.success() => Ok(format!(
                "saved: {}",
                String::from_utf8_lossy(&output.stdout).trim()
            )),
            Ok(output) => Err(format!(
                "pack rebuild failed: {}",
                String::from_utf8_lossy(&output.stderr).trim()
            )),
            Err(err) => Err(format!(
                "could not run python ({err}). The patched BXON is at {}. Rebuild it with: \
                 python tools/table_edit.py save-mod {rel} --patched <file>",
                out.display()
            )),
        };
        let _ = tx.send(message);
    });
}

// ---------------------------------------------------------------------------
// grid drawing
// ---------------------------------------------------------------------------
fn draw_grid(
    ui: &mut egui::Ui,
    doc: &TableDoc,
    fields: &[Field],
    visible: &[usize],
    edit: &mut Option<EditState>,
    actions: &mut Vec<Action>,
) {
    use egui_extras::{Column, TableBuilder};
    let mut builder = TableBuilder::new(ui)
        .id_salt(("table_grid", doc.rel.clone()))
        .striped(true)
        .resizable(true)
        .sense(egui::Sense::hover())
        .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
        .auto_shrink([false, false])
        .column(Column::exact(52.0));
    for _ in fields {
        builder = builder.column(Column::initial(150.0).at_least(64.0).clip(true));
    }
    builder
        .header(24.0, |mut header| {
            header.col(|ui| {
                ui.label(theme::faint_label("#"));
            });
            for field in fields {
                header.col(|ui| {
                    let color = match field.confidence.as_str() {
                        "raw" => theme::TEXT_FAINT,
                        "inferred" => theme::TEXT_DIM,
                        _ => theme::ACCENT,
                    };
                    let _ = ui
                        .label(egui::RichText::new(field.name.clone()).size(11.5).color(color))
                        .on_hover_text(hover_text(field));
                });
            }
        })
        .body(|body| {
            body.rows(20.0, visible.len(), |mut row| {
                let doc_row = visible[row.index()];
                row.col(|ui| {
                    ui.label(theme::faint_label(format!("{doc_row}")));
                });
                for (field_index, field) in fields.iter().enumerate() {
                    row.col(|ui| {
                        draw_cell(ui, doc, doc_row, field_index, field, edit, actions);
                    });
                }
            });
        });
}

fn hover_text(field: &Field) -> String {
    let mut text = format!(
        "{}\n{} at +0x{:02X}   [{}]",
        field.name,
        field.ty.name(),
        field.offset,
        field.confidence
    );
    if let Some((low, high)) = field.range {
        text.push_str(&format!("\naccepted range {low}..{high}"));
    }
    if let Some(reference) = &field.reference {
        text.push_str(&format!("\nids come from {}", reference.table));
    }
    if !field.labels.is_empty() {
        let pairs: Vec<String> = field.labels.iter().map(|(v, l)| format!("{v}={l}")).collect();
        text.push_str(&format!("\nvalues: {}", pairs.join("  ")));
    }
    if field.read_only {
        text.push_str("\nread-only (text)");
    }
    if !field.why.is_empty() {
        text.push_str("\n\n");
        text.push_str(&field.why);
    }
    text
}

fn draw_cell(
    ui: &mut egui::Ui,
    doc: &TableDoc,
    row: usize,
    field_index: usize,
    field: &Field,
    edit: &mut Option<EditState>,
    actions: &mut Vec<Action>,
) {
    if doc.is_dirty(row, field) {
        ui.painter()
            .rect_filled(ui.max_rect().shrink(1.0), 2.0, theme::BG_SELECT);
    }
    let editing = edit
        .as_ref()
        .is_some_and(|e| e.row == row && e.field == field_index);

    if editing {
        if let Some(reference) = &field.reference {
            let options = reference_list(&reference.table);
            let current = edit
                .as_ref()
                .and_then(|e| e.text.parse::<i64>().ok())
                .unwrap_or(-1);
            let current_label = reference_name(&reference.table, current)
                .unwrap_or_else(|| current.to_string());
            let mut chosen = None;
            let mut cancel = false;
            // A 2,875-entry item list needs a filter; the text lives in egui's
            // temporary store so it survives the per-frame rebuild of the popup.
            let filter_id = egui::Id::new(("ref_filter", row, field_index));
            egui::ComboBox::from_id_salt(("cell_ref", row, field_index))
                .selected_text(truncate(&current_label, 30))
                .width(340.0)
                .show_ui(ui, |ui| {
                    let mut filter: String =
                        ui.data(|d| d.get_temp(filter_id).unwrap_or_default());
                    let changed = ui
                        .add(
                            egui::TextEdit::singleline(&mut filter)
                                .hint_text("type to filter\u{2026}")
                                .desired_width(300.0),
                        )
                        .changed();
                    if changed {
                        ui.data_mut(|d| d.insert_temp(filter_id, filter.clone()));
                    }
                    if ui.button("cancel").clicked() {
                        cancel = true;
                    }
                    let needle = filter.trim().to_lowercase();
                    let mut shown = 0usize;
                    egui::ScrollArea::vertical().max_height(320.0).show(ui, |ui| {
                        for (id, label) in &options {
                            if !needle.is_empty()
                                && !label.to_lowercase().contains(&needle)
                                && !id.to_string().contains(&needle)
                            {
                                continue;
                            }
                            if shown >= 400 {
                                ui.label(theme::faint_label("400 matches shown - refine the filter"));
                                break;
                            }
                            shown += 1;
                            if ui
                                .selectable_label(*id == current, format!("{id} \u{2014} {label}"))
                                .clicked()
                            {
                                chosen = Some(*id);
                            }
                        }
                        if options.is_empty() {
                            ui.label(theme::faint_label("no ids loaded for this table"));
                        }
                    });
                });
            if let Some(id) = chosen {
                actions.push(Action::Set(row, field_index, Value::Int(id)));
            } else if cancel {
                actions.push(Action::Cancel);
            }
            return;
        }
        if !field.labels.is_empty() {
            let state = edit.as_ref().expect("editing");
            let current = state.text.parse::<i64>().unwrap_or(0);
            let mut chosen = None;
            egui::ComboBox::from_id_salt(("cell_enum", row, field_index))
                .selected_text(
                    field
                        .labels
                        .iter()
                        .find(|(v, _)| *v == current)
                        .map(|(_, l)| l.clone())
                        .unwrap_or_else(|| current.to_string()),
                )
                .show_ui(ui, |ui| {
                    for (value, label) in &field.labels {
                        if ui.selectable_label(*value == current, label).clicked() {
                            chosen = Some(*value);
                        }
                    }
                });
            if let Some(value) = chosen {
                actions.push(Action::Set(row, field_index, Value::Int(value)));
            }
            return;
        }
        let state = edit.as_mut().expect("editing");
        let response = ui.add(
            egui::TextEdit::singleline(&mut state.text)
                .desired_width(f32::INFINITY)
                .hint_text(field.ty.name()),
        );
        if state.fresh {
            response.request_focus();
            state.fresh = false;
        }
        if response.lost_focus() {
            actions.push(Action::Commit(row, field_index, state.text.clone()));
        }
        if let Some(error) = &state.error {
            let _ = response.on_hover_text(error.clone());
        }
        return;
    }

    let value = doc.value(row, field);
    let text = cell_text(doc, &value, field);
    let color = if field.read_only {
        theme::TEXT_DIM
    } else if doc.is_dirty(row, field) {
        theme::ACCENT
    } else {
        theme::TEXT
    };
    let response = ui.add(
        egui::Label::new(egui::RichText::new(text).size(11.5).color(color))
            .truncate()
            .sense(egui::Sense::click()),
    );
    let response = response.on_hover_text(hover_text(field));
    if response.clicked() && !field.read_only {
        actions.push(Action::Begin(row, field_index));
    }
}

fn cell_text(doc: &TableDoc, value: &Value, field: &Field) -> String {
    match value {
        Value::Text(text) => truncate(&text.replace('\n', " "), 40),
        Value::Float(v) => format!("{v:.4}"),
        Value::Int(v) => {
            if let Some((_, label)) = field.labels.iter().find(|(k, _)| k == v) {
                return label.clone();
            }
            if let Some(reference) = &field.reference {
                if let Some(name) = reference_name(&reference.table, *v) {
                    return format!("{v} \u{2014} {}", truncate(&name, 22));
                }
            }
            let _ = doc;
            v.to_string()
        }
    }
}

fn truncate(text: &str, limit: usize) -> String {
    if text.chars().count() <= limit {
        return text.to_string();
    }
    let mut out: String = text.chars().take(limit.saturating_sub(1)).collect();
    out.push('\u{2026}');
    out
}
