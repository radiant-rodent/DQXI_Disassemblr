//! Editor shell, modelled on Godot's: a menu bar, workspace tabs, a project
//! (FileSystem) dock, an output dock and a Quick Open palette. The panels stay in
//! their own modules; the shell only decides where they live and how to reach
//! any project resource from anywhere.

use std::collections::{BTreeMap, HashSet};

use eframe::egui;

use crate::app::{Section, ViewerApp, Workspace, WORKSPACES};
use crate::theme;
use crate::utils::human_count;

/// Something in the project that can be opened in its editor.
#[derive(Clone)]
pub enum Target {
    Texture(String),
    Model(String),
    Layout(String),
    Script(String),
    Table(String),
    Audio(String),
    Area(String),
    Level(String),
    /// an action from the command palette (`>` prefix / Ctrl+Shift+P)
    Command(String),
}

impl Target {
    pub fn kind(&self) -> &'static str {
        match self {
            Target::Texture(_) => "texture",
            Target::Model(_) => "model",
            Target::Layout(_) => "layout",
            Target::Script(_) => "script",
            Target::Table(_) => "table",
            Target::Audio(_) => "audio",
            Target::Area(_) => "area",
            Target::Level(_) => "level",
            Target::Command(_) => "command",
        }
    }
}

impl ViewerApp {
    /// Opens a project resource in the editor that owns it.
    pub fn open_target(&mut self, target: &Target) {
        if !matches!(target, Target::Command(_)) {
            self.opened.push(target.clone());
        }
        match target {
            Target::Texture(n) => self.open_textures(n, None),
            Target::Model(n) => self.open_model(n),
            Target::Layout(n) => self.open_layout(n),
            Target::Script(n) => self.open_scripts(n),
            Target::Table(n) => self.open_tables(n),
            Target::Audio(n) => self.open_audio(n),
            Target::Area(n) => self.open_area(n),
            Target::Level(n) => {
                self.panels.editor.request(n);
                self.go(Section::Editor);
            }
            Target::Command(id) => {
                self.run_command(id);
                return;
            }
        }
        self.status = format!("opened {} {}", target.kind(), target.name());
    }
}

impl Target {
    pub fn name(&self) -> &str {
        match self {
            Target::Texture(n)
            | Target::Model(n)
            | Target::Layout(n)
            | Target::Script(n)
            | Target::Table(n)
            | Target::Audio(n)
            | Target::Area(n)
            | Target::Level(n)
            | Target::Command(n) => n,
        }
    }
}

/// Every action reachable from the command palette: (id, title, shortcut).
pub fn commands() -> Vec<(String, String, &'static str)> {
    let mut out: Vec<(String, String, &'static str)> = vec![
        ("save".into(), "Save level".into(), "Ctrl+S"),
        ("saveall".into(), "Save all open edits".into(), "Ctrl+Shift+S"),
        ("undo".into(), "Undo".into(), "Ctrl+Z"),
        ("redo".into(), "Redo".into(), "Ctrl+Y"),
        ("revert".into(), "Revert every change in the open level".into(), ""),
        ("export".into(), "Export mod".into(), ""),
        ("play".into(), "Play in emulator".into(), ""),
        ("project".into(), "Toggle project dock".into(), "Ctrl+B"),
        ("output".into(), "Toggle output dock".into(), "Ctrl+J"),
        ("folder".into(), "Open project folder".into(), ""),
        ("tour".into(), "Start the tour".into(), ""),
        ("tool:select".into(), "Tool: Select".into(), "Q"),
        ("tool:move".into(), "Tool: Move".into(), "W"),
        ("tool:rotate".into(), "Tool: Rotate".into(), "E"),
        ("tool:scale".into(), "Tool: Scale".into(), "R"),
    ];
    for ws in WORKSPACES {
        for section in ws.sections() {
            out.push((format!("go:{}", section.title()), format!("Go to {}  \u{203a}  {}", ws.title(), section.title()), ""));
        }
    }
    out
}

impl ViewerApp {
    /// Undo in whichever editor is in front.
    pub fn undo_active(&mut self) {
        match self.section {
            Section::Editor => self.panels.editor.undo_action(),
            Section::Tables => crate::ui::panels::tables::undo_active(self),
            Section::Layouts => self.panels.layouts.undo_action(),
            Section::Dialogues => self.panels.dialogues.undo_action(),
            _ => {}
        }
    }

    pub fn redo_active(&mut self) {
        match self.section {
            Section::Editor => self.panels.editor.redo_action(),
            Section::Tables => crate::ui::panels::tables::redo_active(self),
            Section::Layouts => self.panels.layouts.redo_action(),
            Section::Dialogues => self.panels.dialogues.redo_action(),
            _ => {}
        }
    }

    pub fn can_undo_active(&self) -> bool {
        match self.section {
            Section::Editor => self.panels.editor.can_undo(),
            Section::Tables => crate::ui::panels::tables::can_undo_active(self),
            Section::Layouts => self.panels.layouts.can_undo(),
            Section::Dialogues => self.panels.dialogues.can_undo(),
            _ => false,
        }
    }

    pub fn can_redo_active(&self) -> bool {
        match self.section {
            Section::Editor => self.panels.editor.can_redo(),
            Section::Tables => crate::ui::panels::tables::can_redo_active(self),
            Section::Layouts => self.panels.layouts.can_redo(),
            Section::Dialogues => self.panels.dialogues.can_redo(),
            _ => false,
        }
    }

    /// File > Save All: the open level, table and script, each through its own save path.
    pub fn save_all(&mut self) {
        let root = self.dirs.root.clone();
        let mut saved: Vec<&str> = Vec::new();
        if !self.panels.editor.unsaved_levels().is_empty() {
            self.panels.editor.save_all_levels(&root);
            saved.push("levels");
        }
        if self.panels.tables.modified_cells() > 0 {
            crate::ui::panels::tables::save_active(self);
            saved.push("table");
        }
        if self.panels.dialogues.dirty_count() > 0 {
            let mut panel = std::mem::take(&mut self.panels.dialogues);
            panel.save_open_bank(self);
            self.panels.dialogues = panel;
            saved.push("dialogues");
        }
        if self.panels.layouts.edited_panes() > 0 {
            crate::ui::panels::layouts::save_active(self);
            saved.push("layout");
        }
        if self.panels.scripts.is_dirty() {
            crate::ui::panels::scripts::save_active(self);
            saved.push("script");
        }
        self.status = if saved.is_empty() {
            "nothing to save".into()
        } else {
            format!("saving {}\u{2026}", saved.join(", "))
        };
    }

    pub fn run_command(&mut self, id: &str) {
        let root = self.dirs.root.clone();
        match id {
            "save" => self.panels.editor.save_current(&root),
            "saveall" => self.save_all(),
            "undo" => self.undo_active(),
            "redo" => self.redo_active(),
            "revert" => self.panels.editor.revert_all(),
            "export" => {
                self.go(Section::Playtest);
                self.panels.playtest.open_export(&root);
            }
            "play" => {
                self.go(Section::Playtest);
                self.panels.playtest.open_play(&root);
            }
            "project" => self.shell.show_project = !self.shell.show_project,
            "output" => self.shell.show_output = !self.shell.show_output,
            "folder" => {
                let _ = std::process::Command::new("explorer").arg(&root).spawn();
            }
            "tour" => self.tour.start(),
            _ => {
                if let Some(tool) = id.strip_prefix("tool:") {
                    self.panels.editor.set_tool_by_name(tool);
                } else if let Some(title) = id.strip_prefix("go:") {
                    if let Some(section) = crate::app::SECTIONS.iter().find(|s| s.title() == title) {
                        self.go(*section);
                    }
                }
            }
        }
    }

    /// Everything with edits that are not on disk yet.
    pub fn unsaved(&self) -> Vec<String> {
        let mut out = Vec::new();
        for (id, n) in self.panels.editor.unsaved_levels() {
            out.push(format!("Level {id}: {n} node(s) changed, not saved"));
        }
        let panes = self.panels.layouts.edited_panes();
        if panes > 0 {
            out.push(format!("Layout {}: {panes} pane(s) edited, not written to the mod", self.panels.layouts.name_of_selected_layout(self.data.as_deref())));
        }
        let lines = self.panels.dialogues.dirty_count();
        if lines > 0 {
            out.push(format!("Dialogues: {lines} edited line(s), not written to the mod"));
        }
        if self.panels.scripts.is_dirty() {
            out.push("Script: edits not compiled to the mod".to_string());
        }
        let cells = self.panels.tables.modified_cells();
        if cells > 0 {
            out.push(format!("Tables: {cells} modified cell(s), not written to the mod"));
        }
        out
    }
}

struct Row {
    depth: usize,
    label: String,
    /// `Some(id)` for a folder
    folder: Option<String>,
    count: Option<usize>,
    target: Option<Target>,
    key: String,
}

struct Hit {
    kind: &'static str,
    label: String,
    target: Target,
}

#[derive(Default)]
pub struct Shell {
    pub show_project: bool,
    pub show_output: bool,
    started: bool,
    output: Vec<(f64, String)>,
    last_status: String,
    expanded: HashSet<String>,
    filter: String,
    rows: Vec<Row>,
    signature: (usize, usize, String, usize),
    cursor: usize,
    current: Option<String>,
    scroll_to_cursor: bool,
    pub palette_open: bool,
    palette_query: String,
    palette_hits: Vec<Hit>,
    palette_selected: usize,
    palette_fresh: bool,
    window_title: String,
    docs: Vec<Target>,
    current_doc: Option<usize>,
    saved_layout: String,
    prefs_loaded: bool,
    prefs_open: bool,
    keys_open: bool,
    ui_scale: f32,
    saved_prefs: String,
}

impl Shell {
    pub fn init(&mut self, root: &std::path::Path) {
        if !self.started {
            self.started = true;
            self.show_project = true;
            self.show_output = false;
            self.expanded.insert("models".into());
            // restore the layout of the last session (editor_layout.json)
            if let Ok(text) = std::fs::read_to_string(root.join("editor_layout.json")) {
                if let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) {
                    self.show_project = v["show_project"].as_bool().unwrap_or(true);
                    self.show_output = v["show_output"].as_bool().unwrap_or(false);
                    self.ui_scale = v["ui_scale"].as_f64().map(|x| (x as f32).clamp(0.75, 2.0)).unwrap_or(1.0);
                    if let Some(list) = v["expanded"].as_array() {
                        self.expanded = list.iter().filter_map(|x| x.as_str().map(String::from)).collect();
                    }
                }
            }
            self.saved_layout = self.layout_json();
        }
    }

    fn layout_json(&self) -> String {
        let mut expanded: Vec<&String> = self.expanded.iter().collect();
        expanded.sort();
        serde_json::json!({
            "show_project": self.show_project,
            "show_output": self.show_output,
            "ui_scale": self.ui_scale,
            "expanded": expanded,
        })
        .to_string()
    }

    /// Writes the layout when it changed.
    pub fn persist_layout(&mut self, root: &std::path::Path) {
        let now = self.layout_json();
        if now != self.saved_layout {
            let _ = std::fs::write(root.join("editor_layout.json"), &now);
            self.saved_layout = now;
        }
    }

    /// Mirrors every status-bar message into the Output dock.
    pub fn record_status(&mut self, now: f64, status: &str) {
        if status != self.last_status {
            self.last_status = status.to_string();
            if !status.is_empty() {
                self.output.push((now, status.to_string()));
                if self.output.len() > 2000 {
                    self.output.drain(0..500);
                }
            }
        }
    }

    fn toggle(&mut self, id: &str) {
        if !self.expanded.remove(id) {
            self.expanded.insert(id.to_string());
        }
        self.signature.3 = usize::MAX; // force a rebuild
    }
}

// ---------------------------------------------------------------------------
// project tree
// ---------------------------------------------------------------------------

type Leaf = (String, String, Target); // group, label, target

fn push_section(
    shell: &Shell,
    rows: &mut Vec<Row>,
    id: &str,
    title: &str,
    total: usize,
    flat: bool,
    filter: &str,
    leaves: impl FnOnce() -> Vec<Leaf>,
) {
    let filtering = !filter.is_empty();
    let open = filtering || shell.expanded.contains(id);
    if !open {
        rows.push(Row { depth: 0, label: title.into(), folder: Some(id.into()), count: Some(total), target: None, key: id.into() });
        return;
    }
    let mut groups: BTreeMap<String, Vec<(String, Target)>> = BTreeMap::new();
    let mut shown = 0;
    for (group, label, target) in leaves() {
        if filtering && !label.to_lowercase().contains(filter) && !target.name().to_lowercase().contains(filter) {
            continue;
        }
        shown += 1;
        groups.entry(if flat { String::new() } else { group }).or_default().push((label, target));
    }
    if filtering && shown == 0 {
        return;
    }
    rows.push(Row { depth: 0, label: title.into(), folder: Some(id.into()), count: Some(if filtering { shown } else { total }), target: None, key: id.into() });
    for (group, items) in groups {
        if flat {
            for (label, target) in items {
                let key = format!("{id}/{label}");
                rows.push(Row { depth: 1, label, folder: None, count: None, target: Some(target), key });
            }
            continue;
        }
        let gid = format!("{id}/{group}");
        let gopen = filtering || shell.expanded.contains(&gid);
        rows.push(Row { depth: 1, label: group, folder: Some(gid.clone()), count: Some(items.len()), target: None, key: gid.clone() });
        if gopen {
            for (label, target) in items {
                let key = format!("{gid}/{label}");
                rows.push(Row { depth: 2, label, folder: None, count: None, target: Some(target), key });
            }
        }
    }
}

fn signature(app: &ViewerApp, shell: &Shell) -> (usize, usize, String, usize) {
    let (a, b) = match app.data.as_deref() {
        Some(d) => (
            d.textures.items.len() + d.models.items.len() + d.layouts.items.len() + d.scripts.items.len(),
            d.tables.items.len() + d.audio.streams.len() + d.areas.areas.len(),
        ),
        None => (0, 0),
    };
    (a, b + app.panels.editor.map_count(), shell.filter.to_lowercase(), shell.expanded.len())
}

fn rebuild(app: &ViewerApp, shell: &mut Shell) {
    let filter = shell.filter.to_lowercase();
    let mut rows = Vec::new();
    let Some(d) = app.data.as_deref() else {
        shell.rows = rows;
        return;
    };
    let levels = app.panels.editor.maps();
    push_section(shell, &mut rows, "levels", "Levels", levels.len(), false, &filter, || {
        levels
            .iter()
            .map(|m| (m.chars().take(4).collect::<String>(), m.clone(), Target::Level(m.clone())))
            .collect()
    });
    push_section(shell, &mut rows, "maps", "Areas", d.areas.areas.len(), true, &filter, || {
        d.areas.areas.iter().map(|a| (String::new(), a.clone(), Target::Area(a.clone()))).collect()
    });
    push_section(shell, &mut rows, "models", "Models", d.models.items.len(), false, &filter, || {
        d.models
            .items
            .iter()
            .map(|m| (m.category.clone(), m.display_name.clone().unwrap_or_else(|| m.name.clone()), Target::Model(m.name.clone())))
            .collect()
    });
    push_section(shell, &mut rows, "textures", "Textures", d.textures.items.len(), false, &filter, || {
        d.textures.items.iter().map(|t| (t.pack.clone(), t.name.clone(), Target::Texture(t.name.clone()))).collect()
    });
    push_section(shell, &mut rows, "audio", "Audio", d.audio.streams.len(), false, &filter, || {
        d.audio.streams.iter().map(|s| (s.kind.clone(), s.name.clone(), Target::Audio(s.name.clone()))).collect()
    });
    push_section(shell, &mut rows, "layouts", "UI layouts", d.layouts.items.len(), false, &filter, || {
        d.layouts.items.iter().map(|l| (l.pack.clone(), l.stem.clone(), Target::Layout(l.stem.clone()))).collect()
    });
    push_section(shell, &mut rows, "tables", "Data tables", d.tables.items.len(), false, &filter, || {
        d.tables.items.iter().map(|t| (t.category.clone(), t.name.clone(), Target::Table(t.name.clone()))).collect()
    });
    push_section(shell, &mut rows, "scripts", "Scripts", d.scripts.items.len(), true, &filter, || {
        d.scripts.items.iter().map(|s| (String::new(), s.area.clone(), Target::Script(s.area.clone()))).collect()
    });
    shell.rows = rows;
}

fn project_dock(app: &mut ViewerApp, shell: &mut Shell, ui: &mut egui::Ui) {
    ui.add_space(4.0);
    ui.horizontal(|ui| {
        ui.label(theme::heading("Project"));
        ui.label(theme::faint_label("Ctrl+B"));
    });
    let entry = ui.add(
        egui::TextEdit::singleline(&mut shell.filter)
            .hint_text("Filter files\u{2026}")
            .desired_width(f32::INFINITY),
    );
    if std::mem::take(&mut shell.palette_fresh) {
        // palette closed: nothing to do, kept so the field exists for later focus requests
    }
    if entry.changed() {
        shell.signature.3 = usize::MAX;
    }
    let sig = signature(app, shell);
    if sig != shell.signature {
        shell.signature = sig;
        rebuild(app, shell);
        shell.cursor = shell.cursor.min(shell.rows.len().saturating_sub(1));
    }
    ui.separator();

    // keyboard: the dock owns the arrows while the pointer is over it
    let hovered = ui.rect_contains_pointer(ui.max_rect()) && !ui.ctx().egui_wants_keyboard_input();
    let mut activate: Option<usize> = None;
    if hovered && !shell.rows.is_empty() {
        let (up, down, left, right, enter) = ui.ctx().input_mut(|i| {
            (
                i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowUp),
                i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowDown),
                i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowLeft),
                i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowRight),
                i.consume_key(egui::Modifiers::NONE, egui::Key::Enter),
            )
        });
        let last = shell.rows.len() - 1;
        if up {
            shell.cursor = shell.cursor.saturating_sub(1);
            shell.scroll_to_cursor = true;
        }
        if down {
            shell.cursor = (shell.cursor + 1).min(last);
            shell.scroll_to_cursor = true;
        }
        let row = &shell.rows[shell.cursor.min(last)];
        let folder = row.folder.clone();
        let open = folder.as_ref().is_some_and(|f| shell.expanded.contains(f));
        if right && folder.is_some() && !open {
            activate = Some(shell.cursor);
        }
        if left {
            if let Some(f) = folder.filter(|_| open) {
                shell.toggle(&f);
            } else {
                // jump to the parent folder
                let depth = row.depth;
                if depth > 0 {
                    if let Some(p) = (0..shell.cursor).rev().find(|i| shell.rows[*i].depth < depth) {
                        shell.cursor = p;
                        shell.scroll_to_cursor = true;
                    }
                }
            }
        }
        if enter {
            activate = Some(shell.cursor);
        }
    }

    let total = shell.rows.len();
    let cursor = shell.cursor;
    let mut clicked: Option<usize> = None;
    let mut area = egui::ScrollArea::vertical().id_salt("project_tree").auto_shrink([false, false]);
    if std::mem::take(&mut shell.scroll_to_cursor) {
        area = area.vertical_scroll_offset((cursor as f32 * 19.0 - 120.0).max(0.0));
    }
    area.show_rows(ui, 19.0, total, |ui, range| {
        for i in range {
            let row = &shell.rows[i];
            let selected = shell.current.as_deref() == Some(row.key.as_str());
            let (rect, response) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 19.0), egui::Sense::click_and_drag());
            let painter = ui.painter_at(rect);
            if let Some(Target::Model(name)) = &row.target {
                // models can be dragged onto drop zones (the Inspector's character slot)
                if response.drag_started() {
                    response.dnd_set_drag_payload(name.clone());
                }
                if response.dragged() {
                    if let Some(p) = ui.ctx().pointer_latest_pos() {
                        let layer = egui::LayerId::new(egui::Order::Tooltip, egui::Id::new("dnd_ghost"));
                        ui.ctx().layer_painter(layer).text(p + egui::vec2(12.0, 12.0), egui::Align2::LEFT_TOP, name, egui::FontId::proportional(12.0), theme::ACCENT);
                    }
                }
            }
            if i == cursor {
                painter.rect_filled(rect, 2.0, theme::BG_HOVER);
            }
            if selected {
                painter.rect_filled(rect, 2.0, theme::BG_SELECT);
            } else if response.hovered() {
                painter.rect_filled(rect, 2.0, theme::BG_HOVER);
            }
            let x = rect.left() + 6.0 + row.depth as f32 * 14.0;
            let mid = rect.center().y;
            if let Some(id) = &row.folder {
                let open = shell.filter.is_empty() && shell.expanded.contains(id) || !shell.filter.is_empty();
                let c = theme::TEXT_DIM;
                if open {
                    painter.add(egui::Shape::convex_polygon(
                        vec![egui::pos2(x, mid - 2.0), egui::pos2(x + 8.0, mid - 2.0), egui::pos2(x + 4.0, mid + 3.0)],
                        c,
                        egui::Stroke::NONE,
                    ));
                } else {
                    painter.add(egui::Shape::convex_polygon(
                        vec![egui::pos2(x + 1.0, mid - 4.0), egui::pos2(x + 1.0, mid + 4.0), egui::pos2(x + 6.0, mid)],
                        c,
                        egui::Stroke::NONE,
                    ));
                }
            }
            let text_x = x + 14.0;
            let color = if row.folder.is_some() { theme::TEXT } else { theme::TEXT_DIM };
            let label = crate::utils::elide(&row.label, 34);
            painter.text(egui::pos2(text_x, mid), egui::Align2::LEFT_CENTER, label, egui::FontId::proportional(12.0), color);
            if let Some(n) = row.count {
                painter.text(
                    egui::pos2(rect.right() - 6.0, mid),
                    egui::Align2::RIGHT_CENTER,
                    human_count(n),
                    egui::FontId::proportional(10.5),
                    theme::TEXT_FAINT,
                );
            }
            if response.clicked() {
                clicked = Some(i);
            }
        }
    });
    if shell.rows.is_empty() {
        ui.label(theme::faint_label("Nothing indexed yet\u{2026}"));
    }

    let pick = clicked.or(activate);
    if let Some(i) = pick {
        shell.cursor = i;
        let (folder, target, key) = {
            let r = &shell.rows[i];
            (r.folder.clone(), r.target.clone(), r.key.clone())
        };
        if let Some(f) = folder {
            if shell.filter.is_empty() {
                shell.toggle(&f);
            }
        } else if let Some(t) = target {
            shell.current = Some(key);
            app.open_target(&t);
        }
    }
}

// ---------------------------------------------------------------------------
// output dock
// ---------------------------------------------------------------------------

fn output_dock(shell: &mut Shell, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label(theme::heading("Output"));
        ui.label(theme::faint_label(format!("{} messages", shell.output.len())));
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if ui.button("Clear").clicked() {
                shell.output.clear();
            }
            if ui.button("Copy").clicked() {
                let text: Vec<String> = shell.output.iter().map(|(t, m)| format!("[{}] {m}", clock(*t))).collect();
                ui.ctx().copy_text(text.join("\n"));
            }
        });
    });
    ui.separator();
    let lines = shell.output.len();
    egui::ScrollArea::vertical()
        .id_salt("output_dock")
        .stick_to_bottom(true)
        .auto_shrink([false, false])
        .show_rows(ui, 16.0, lines, |ui, range| {
            for i in range {
                let (t, m) = &shell.output[i];
                ui.horizontal(|ui| {
                    ui.label(theme::mono(format!("[{}]", clock(*t))));
                    let lower = m.to_lowercase();
                    let color = if lower.contains("fail") || lower.contains("error") {
                        theme::ERR
                    } else if lower.contains("warn") {
                        theme::WARN
                    } else {
                        theme::TEXT_DIM
                    };
                    ui.label(egui::RichText::new(m).color(color).size(12.0));
                });
            }
        });
}

fn clock(seconds: f64) -> String {
    let s = seconds as u64;
    format!("{:02}:{:02}:{:02}", s / 3600, (s / 60) % 60, s % 60)
}

// ---------------------------------------------------------------------------
// Quick Open
// ---------------------------------------------------------------------------

fn search_palette(app: &ViewerApp, query: &str) -> Vec<Hit> {
    let mut hits: Vec<Hit> = Vec::new();
    if let Some(rest) = query.trim_start().strip_prefix('>') {
        let q = rest.trim().to_lowercase();
        for (id, title, keys) in commands() {
            if q.is_empty() || title.to_lowercase().contains(&q) {
                let label = if keys.is_empty() { title } else { format!("{title}    [{keys}]") };
                hits.push(Hit { kind: "command", label, target: Target::Command(id) });
            }
        }
        return hits;
    }
    let q = query.trim().to_lowercase();
    let Some(d) = app.data.as_deref() else { return hits };
    if q.is_empty() {
        return hits;
    }
    const PER_KIND: usize = 9;
    fn take<'a>(
        hits: &mut Vec<Hit>,
        kind: &'static str,
        q: &str,
        items: impl Iterator<Item = (String, Target)> + 'a,
    ) {
        let mut found: Vec<(bool, String, Target)> = Vec::new();
        for (label, target) in items {
            let l = label.to_lowercase();
            if l.contains(q) {
                found.push((!l.starts_with(q), label, target));
                if found.len() >= 400 {
                    break;
                }
            }
        }
        found.sort_by(|a, b| a.0.cmp(&b.0).then(a.1.len().cmp(&b.1.len())));
        for (_, label, target) in found.into_iter().take(PER_KIND) {
            hits.push(Hit { kind, label, target });
        }
    }
    take(&mut hits, "level", &q, app.panels.editor.maps().iter().map(|m| (m.clone(), Target::Level(m.clone()))));
    take(&mut hits, "model", &q, d.models.items.iter().map(|m| {
        let label = match &m.display_name {
            Some(display) => format!("{display}  ({})", m.name),
            None => m.name.clone(),
        };
        (label, Target::Model(m.name.clone()))
    }));
    take(&mut hits, "texture", &q, d.textures.items.iter().map(|t| (t.name.clone(), Target::Texture(t.name.clone()))));
    take(&mut hits, "audio", &q, d.audio.streams.iter().map(|s| (s.name.clone(), Target::Audio(s.name.clone()))));
    take(&mut hits, "table", &q, d.tables.items.iter().map(|t| (t.name.clone(), Target::Table(t.name.clone()))));
    take(&mut hits, "script", &q, d.scripts.items.iter().map(|s| (s.area.clone(), Target::Script(s.area.clone()))));
    take(&mut hits, "layout", &q, d.layouts.items.iter().map(|l| (l.stem.clone(), Target::Layout(l.stem.clone()))));
    take(&mut hits, "area", &q, d.areas.areas.iter().map(|a| (a.clone(), Target::Area(a.clone()))));
    hits
}

fn palette(app: &mut ViewerApp, shell: &mut Shell, ctx: &egui::Context) {
    if !shell.palette_open {
        return;
    }
    let mut open = true;
    let mut chosen: Option<Target> = None;
    egui::Window::new("Quick Open")
        .title_bar(false)
        .anchor(egui::Align2::CENTER_TOP, egui::vec2(0.0, 70.0))
        .fixed_size(egui::vec2(560.0, 0.0))
        .frame(
            egui::Frame::new()
                .fill(theme::BG_RAISED)
                .stroke(egui::Stroke::new(1.0, theme::BORDER_LIGHT))
                .corner_radius(6.0)
                .inner_margin(egui::Margin::same(10)),
        )
        .show(ctx, |ui| {
            // read the keys first: the text field swallows Enter and the arrows
            let (down, up, enter, esc) = ui.input_mut(|i| {
                (
                    i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowDown),
                    i.consume_key(egui::Modifiers::NONE, egui::Key::ArrowUp),
                    i.consume_key(egui::Modifiers::NONE, egui::Key::Enter),
                    i.key_pressed(egui::Key::Escape),
                )
            });
            let entry = ui.add(
                egui::TextEdit::singleline(&mut shell.palette_query)
                    .hint_text("Open anything: a model, texture, table, level, sound\u{2026}   (type > for commands)")
                    .desired_width(f32::INFINITY),
            );
            if !entry.has_focus() {
                entry.request_focus();
            }
            if entry.changed() {
                shell.palette_hits = search_palette(app, &shell.palette_query);
                shell.palette_selected = 0;
            }
            let n = shell.palette_hits.len();
            if n > 0 {
                if down {
                    shell.palette_selected = (shell.palette_selected + 1).min(n - 1);
                }
                if up {
                    shell.palette_selected = shell.palette_selected.saturating_sub(1);
                }
                if enter {
                    chosen = Some(shell.palette_hits[shell.palette_selected].target.clone());
                }
            }
            if esc {
                open = false;
            }
            ui.add_space(4.0);
            egui::ScrollArea::vertical().max_height(360.0).auto_shrink([false, true]).min_scrolled_height(260.0).show(ui, |ui| {
                for (i, hit) in shell.palette_hits.iter().enumerate() {
                    let selected = i == shell.palette_selected;
                    let (rect, response) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 22.0), egui::Sense::click());
                    if selected {
                        ui.painter().rect_filled(rect, 3.0, theme::BG_SELECT);
                        response.scroll_to_me(None);
                    } else if response.hovered() {
                        ui.painter().rect_filled(rect, 3.0, theme::BG_HOVER);
                    }
                    ui.painter().text(
                        rect.left_center() + egui::vec2(8.0, 0.0),
                        egui::Align2::LEFT_CENTER,
                        crate::utils::elide(&hit.label, 54),
                        egui::FontId::proportional(13.0),
                        theme::TEXT,
                    );
                    ui.painter().text(
                        rect.right_center() - egui::vec2(8.0, 0.0),
                        egui::Align2::RIGHT_CENTER,
                        hit.kind,
                        egui::FontId::proportional(11.0),
                        theme::TEXT_FAINT,
                    );
                    if response.clicked() {
                        chosen = Some(hit.target.clone());
                    }
                }
                if shell.palette_hits.is_empty() && !shell.palette_query.trim().is_empty() {
                    ui.label(theme::faint_label("No matches"));
                }
            });
        });
    if let Some(target) = chosen {
        app.open_target(&target);
        open = false;
    }
    if !open {
        shell.palette_open = false;
        shell.palette_query.clear();
        shell.palette_hits.clear();
        shell.palette_fresh = true;
    }
}

// ---------------------------------------------------------------------------
// menu bar, workspace tabs
// ---------------------------------------------------------------------------

fn shortcut(ui: &mut egui::Ui, text: &str) {
    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
        ui.label(theme::faint_label(text));
    });
}

fn menu_item(ui: &mut egui::Ui, label: &str, keys: &str, enabled: bool) -> bool {
    let mut clicked = false;
    ui.horizontal(|ui| {
        ui.set_min_width(210.0);
        clicked = ui.add_enabled(enabled, egui::Button::new(label).frame(false)).clicked();
        shortcut(ui, keys);
    });
    clicked
}

pub fn menu_bar(app: &mut ViewerApp, shell: &mut Shell, ui: &mut egui::Ui) {
    let in_editor = app.section == Section::Editor;
    ui.horizontal(|ui| {
        ui.label(egui::RichText::new("DQXI").color(theme::ACCENT).size(17.0).strong());
        ui.add_space(6.0);
        ui.menu_button("File", |ui| {
            if menu_item(ui, "Quick Open\u{2026}", "Ctrl+P", true) {
                shell.palette_open = true;
                ui.close();
            }
            if menu_item(ui, "Command palette\u{2026}", "Ctrl+Shift+P", true) {
                shell.palette_open = true;
                shell.palette_query = ">".into();
                shell.palette_hits = search_palette(app, ">");
                shell.palette_selected = 0;
                ui.close();
            }
            if menu_item(ui, "Save", "Ctrl+S", in_editor) {
                app.panels.editor.save_current(&app.dirs.root.clone());
                ui.close();
            }
            if menu_item(ui, "Save All", "Ctrl+Shift+S", !app.unsaved().is_empty()) {
                app.save_all();
                ui.close();
            }
            ui.separator();
            if menu_item(ui, "Export mod\u{2026}", "", true) {
                let root = app.dirs.root.clone();
                app.go(Section::Playtest);
                app.panels.playtest.open_export(&root);
                ui.close();
            }
            if menu_item(ui, "Open project folder", "", true) {
                let _ = std::process::Command::new("explorer").arg(&app.dirs.root).spawn();
                ui.close();
            }
        });
        ui.menu_button("Edit", |ui| {
            if menu_item(ui, "Undo", "Ctrl+Z", app.can_undo_active()) {
                app.undo_active();
                ui.close();
            }
            if menu_item(ui, "Redo", "Ctrl+Y", app.can_redo_active()) {
                app.redo_active();
                ui.close();
            }
            ui.separator();
            if menu_item(ui, "Preferences...", "", true) {
                shell.prefs_open = true;
                ui.close();
            }
            ui.separator();
            if menu_item(ui, "Search everywhere", "Ctrl+F", true) {
                app.focus_search = true;
                ui.close();
            }
        });
        ui.menu_button("View", |ui| {
            if menu_item(ui, if shell.show_project { "Hide project dock" } else { "Show project dock" }, "Ctrl+B", true) {
                shell.show_project = !shell.show_project;
                ui.close();
            }
            if menu_item(ui, if shell.show_output { "Hide output" } else { "Show output" }, "Ctrl+J", true) {
                shell.show_output = !shell.show_output;
                ui.close();
            }
            if menu_item(ui, "Reset layout", "", true) {
                shell.show_project = true;
                shell.show_output = false;
                shell.ui_scale = 1.0;
                app.panels.editor.show_scene_dock = true;
                app.panels.editor.show_inspector_dock = true;
                ui.ctx().set_zoom_factor(1.0);
                ui.close();
            }
            ui.separator();
            if menu_item(ui, "Next workspace", "Ctrl+Tab", true) {
                app.cycle_section(true);
                ui.close();
            }
            if menu_item(ui, "Previous workspace", "Ctrl+Shift+Tab", true) {
                app.cycle_section(false);
                ui.close();
            }
        });
        ui.menu_button("Go", |ui| {
            for ws in WORKSPACES {
                for section in ws.sections() {
                    if menu_item(ui, &format!("{}  \u{203a}  {}", ws.title(), section.title()), "", true) {
                        app.go(*section);
                        ui.close();
                    }
                }
            }
        });
        ui.menu_button("Help", |ui| {
            if menu_item(ui, "Tour", "", true) {
                app.tour.start();
                ui.close();
            }
            if menu_item(ui, "Keyboard shortcuts", "", true) {
                shell.keys_open = true;
                ui.close();
            }
        });
        ui.add_space(16.0);
        // workspace tabs
        let current = app.section.workspace();
        for ws in WORKSPACES {
            let selected = ws == current;
            let text = egui::RichText::new(ws.title()).size(13.5);
            let text = if selected { text.color(theme::ACCENT).strong() } else { text.color(theme::TEXT_DIM) };
            let response = ui.add(egui::Button::new(text).frame(false).min_size(egui::vec2(58.0, 24.0)));
            if selected {
                let r = response.rect;
                ui.painter().line_segment(
                    [egui::pos2(r.left() + 6.0, r.bottom() + 1.0), egui::pos2(r.right() - 6.0, r.bottom() + 1.0)],
                    egui::Stroke::new(2.0, theme::ACCENT),
                );
            }
            if response.clicked() && !selected {
                app.go(ws.sections()[0]);
            }
        }
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if ui
                .add(theme::filled_button("\u{25b6} Play", theme::ACCENT))
                .on_hover_text("Validate, export Luma, and boot Azahar with the mod applied")
                .clicked()
            {
                let root = app.dirs.root.clone();
                app.go(Section::Playtest);
                app.panels.playtest.open_play(&root);
            }
            if ui.button("Export").on_hover_text("Validate the mod workspace, then write the selected target").clicked() {
                let root = app.dirs.root.clone();
                app.go(Section::Playtest);
                app.panels.playtest.open_export(&root);
            }
            let entry = ui.add(
                egui::TextEdit::singleline(&mut app.search_text)
                    .hint_text("Search text everywhere\u{2026}")
                    .desired_width(210.0),
            );
            if app.focus_search {
                entry.request_focus();
                app.focus_search = false;
            }
            if entry.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
                let q = app.search_text.clone();
                app.open_search(&q);
            }
            if ui.button("Quick Open").on_hover_text("Ctrl+P").clicked() {
                shell.palette_open = true;
            }
        });
    });
}

/// Section tabs of the active workspace, like Godot's editor-screen tabs.
pub fn section_tabs(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        let ws: Workspace = app.section.workspace();
        for section in ws.sections() {
            let selected = *section == app.section;
            let text = format!("      {}", section.title());
            let label = if selected {
                egui::RichText::new(text).color(theme::TEXT).strong()
            } else {
                egui::RichText::new(text).color(theme::TEXT_DIM)
            };
            let response = ui.add(
                egui::Button::new(label)
                    .fill(if selected { theme::BG_PANEL } else { theme::BG_RAISED })
                    .corner_radius(egui::CornerRadius { nw: 4, ne: 4, sw: 0, se: 0 })
                    .min_size(egui::vec2(96.0, 24.0)),
            );
            let color = if selected { theme::ACCENT } else { theme::TEXT_DIM };
            section.paint_icon(ui.painter(), egui::pos2(response.rect.left() + 14.0, response.rect.center().y), color);
            if response.clicked() {
                app.go(*section);
            }
        }
    });
}

/// Open documents, like the script tabs in Godot: the last resources you opened, one click to go back.
fn document_tabs(app: &mut ViewerApp, shell: &mut Shell, ui: &mut egui::Ui) {
    let unsaved_levels = app.panels.editor.unsaved_levels();
    let mut reopen: Option<usize> = None;
    let mut close: Option<usize> = None;
    egui::ScrollArea::horizontal().id_salt("doc_tabs_scroll").auto_shrink([false, true]).show(ui, |ui| {
        ui.horizontal(|ui| {
            for (i, doc) in shell.docs.iter().enumerate() {
                let active = shell.current_doc == Some(i);
                let mut title = format!("{}  {}", doc.kind(), crate::utils::elide(doc.name(), 22));
                if matches!(doc, Target::Level(n) if unsaved_levels.iter().any(|(id, _)| id == n)) {
                    title.push_str("  \u{25cf}");
                }
                let text = egui::RichText::new(title).size(12.0);
                let text = if active { text.color(theme::TEXT) } else { text.color(theme::TEXT_DIM) };
                let tab = ui.add(egui::Button::new(text).fill(if active { theme::BG_RAISED } else { theme::BG }).frame(true));
                if tab.clicked() {
                    reopen = Some(i);
                }
                if tab.middle_clicked() {
                    close = Some(i);
                }
                tab.on_hover_text("Click to open \u{b7} middle-click or x to close");
                if ui.add(egui::Button::new(theme::faint_label("x")).frame(false)).clicked() {
                    close = Some(i);
                }
                ui.add_space(4.0);
            }
        });
    });
    if let Some(i) = close {
        shell.docs.remove(i);
        shell.current_doc = None;
    } else if let Some(i) = reopen {
        let target = shell.docs[i].clone();
        shell.current_doc = Some(i);
        app.open_target(&target);
        // re-opening should not reorder the strip
        app.opened.clear();
    }
}

/// Everything around the central panel. Call once per frame from `App::ui`.
pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let ctx = ui.ctx().clone();
    let mut shell = std::mem::take(&mut app.shell);
    shell.init(&app.dirs.root.clone());
    app.panels.editor.ensure_maps(&app.dirs.root.clone());
    let now = ctx.input(|i| i.time);
    shell.record_status(now, &app.status.clone());

    // global shortcuts
    let save_all = ctx.input(|i| i.modifiers.command && i.modifiers.shift && i.key_pressed(egui::Key::S));
    if save_all {
        app.save_all();
    }
    for target in std::mem::take(&mut app.opened) {
        let key = (target.kind(), target.name().to_string());
        shell.docs.retain(|d| (d.kind(), d.name().to_string()) != key);
        shell.docs.push(target);
        if shell.docs.len() > 14 {
            shell.docs.remove(0);
        }
        shell.current_doc = Some(shell.docs.len() - 1);
    }
    let (quick, project, output, save, undo, redo) = ctx.input(|i| {
        let c = i.modifiers.command;
        (
            c && !i.modifiers.shift && i.key_pressed(egui::Key::P),
            c && i.key_pressed(egui::Key::B),
            c && i.key_pressed(egui::Key::J),
            c && !i.modifiers.shift && i.key_pressed(egui::Key::S),
            c && !i.modifiers.shift && i.key_pressed(egui::Key::Z),
            c && (i.key_pressed(egui::Key::Y) || (i.modifiers.shift && i.key_pressed(egui::Key::Z))),
        )
    });
    if quick {
        shell.palette_open = !shell.palette_open;
    }
    let commands_key = ctx.input(|i| i.modifiers.command && i.modifiers.shift && i.key_pressed(egui::Key::P));
    if commands_key {
        shell.palette_open = true;
        shell.palette_query = ">".into();
        shell.palette_hits = search_palette(app, ">");
        shell.palette_selected = 0;
    }
    if project {
        shell.show_project = !shell.show_project;
    }
    if output {
        shell.show_output = !shell.show_output;
    }
    if app.section == Section::Editor && !ctx.egui_wants_keyboard_input() {
        if save {
            let root = app.dirs.root.clone();
            app.panels.editor.save_current(&root);
        }
        if undo {
            app.panels.editor.undo_action();
        }
        if redo {
            app.panels.editor.redo_action();
        }
    }

    egui::Panel::top("menubar")
        .frame(egui::Frame::new().fill(theme::BG_RAISED).inner_margin(egui::Margin::symmetric(10, 5)))
        .show(ui, |ui| menu_bar(app, &mut shell, ui));
    egui::Panel::top("section_tabs")
        .frame(egui::Frame::new().fill(theme::BG_RAISED).inner_margin(egui::Margin { left: 10, right: 10, top: 0, bottom: 0 }))
        .show(ui, |ui| section_tabs(app, ui));
    if !shell.docs.is_empty() {
        egui::Panel::top("doc_tabs")
            .frame(egui::Frame::new().fill(theme::BG).inner_margin(egui::Margin::symmetric(10, 2)))
            .show(ui, |ui| document_tabs(app, &mut shell, ui));
    }
    egui::Panel::bottom("status")
        .frame(egui::Frame::new().fill(theme::BG_RAISED).inner_margin(egui::Margin::symmetric(12, 4)))
        .show(ui, |ui| app.status_bar_ui(ui, &mut shell));
    if shell.show_output {
        egui::Panel::bottom("output")
            .resizable(true)
            .default_size(150.0)
            .min_size(70.0)
            .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
            .show(ui, |ui| output_dock(&mut shell, ui));
    }
    if shell.show_project {
        egui::Panel::left("project")
            .resizable(true)
            .default_size(236.0)
            .min_size(160.0)
            .max_size(460.0)
            .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::symmetric(8, 4)))
            .show(ui, |ui| {
                ui.with_layout(egui::Layout::bottom_up(egui::Align::LEFT), |ui| {
                    ui.add_space(4.0);
                    ui.label(theme::faint_label(app.boot_label_pub()));
                    let progress = app.boot_progress();
                    ui.add(egui::ProgressBar::new(progress).desired_height(4.0));
                    ui.separator();
                    ui.with_layout(egui::Layout::top_down(egui::Align::LEFT), |ui| {
                        project_dock(app, &mut shell, ui);
                    });
                });
            });
    }
    palette(app, &mut shell, &ctx);
    let dirty = !app.unsaved().is_empty();
    let title = format!(
        "{}DQXI Studio \u{2014} {}",
        if dirty { "\u{25cf} " } else { "" },
        app.section.title()
    );
    if title != shell.window_title {
        ctx.send_viewport_cmd(egui::ViewportCommand::Title(title.clone()));
        shell.window_title = title;
    }
    shell.persist_layout(&app.dirs.root.clone());
    if shell.ui_scale < 0.5 {
        shell.ui_scale = 1.0;
    }
    if (ctx.zoom_factor() - shell.ui_scale).abs() > 0.001 && !shell.prefs_open {
        ctx.set_zoom_factor(shell.ui_scale);
    }
    if shell.keys_open {
        let mut open = true;
        egui::Window::new("Keyboard shortcuts").open(&mut open).collapsible(false).resizable(false).anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0]).show(&ctx, |ui| {
            let groups: [(&str, &[(&str, &str)]); 3] = [
                ("Everywhere", &[
                    ("Ctrl+P", "Quick Open (any level, model, texture, sound, table, script)"),
                    ("Ctrl+Shift+P", "Command palette"),
                    ("Ctrl+F", "Search everywhere"),
                    ("Ctrl+B / Ctrl+J", "Show or hide the Project dock / Output"),
                    ("Ctrl+S / Ctrl+Shift+S", "Save / Save All"),
                    ("Ctrl+Z / Ctrl+Y", "Undo / Redo in the front editor"),
                    ("Ctrl+Tab / Ctrl+Shift+Tab", "Next / previous workspace"),
                ]),
                ("Level Editor viewport", &[
                    ("Q W E R", "Select / Move / Rotate / Scale"),
                    ("F", "Focus the selection"),
                    ("Esc", "Deselect"),
                    ("Ctrl+D / Delete", "Duplicate / delete the selection"),
                    ("Drag (Select tool) or Shift+drag", "Box select"),
                    ("Shift+click", "Add or remove a node from the selection"),
                    ("Right-drag / wheel", "Pan / zoom"),
                ]),
                ("Scene tree", &[
                    ("Up / Down", "Move the selection"),
                    ("Double-click", "Select and focus"),
                    ("Right-click", "Focus, Duplicate, Delete"),
                ]),
            ];
            for (title, rows) in groups {
                ui.label(egui::RichText::new(title).strong());
                egui::Grid::new(("keys", title)).num_columns(2).spacing([16.0, 3.0]).show(ui, |ui| {
                    for (key, what) in rows {
                        ui.label(theme::mono(*key));
                        ui.label(theme::dim_label(*what));
                        ui.end_row();
                    }
                });
                ui.add_space(6.0);
            }
        });
        if !open {
            shell.keys_open = false;
        }
    }
    if shell.prefs_open {
        let mut open = true;
        egui::Window::new("Preferences").open(&mut open).collapsible(false).resizable(false).anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0]).show(&ctx, |ui| {
            let ed = &mut app.panels.editor;
            ui.label(egui::RichText::new("Viewport").strong());
            ui.checkbox(&mut ed.snap, "Snap while dragging gizmos");
            ui.horizontal(|ui| {
                ui.label("Snap step");
                ui.add(egui::DragValue::new(&mut ed.snap_step).speed(0.05).range(0.01..=10.0).suffix(" m"));
            });
            ui.checkbox(&mut ed.show_grid, "Grid");
            ui.checkbox(&mut ed.show_axes, "Axes");
            ui.checkbox(&mut ed.show_labels, "Node labels");
            ui.checkbox(&mut ed.show_bounds, "Placement bounds");
            ui.checkbox(&mut ed.show_collision, "Collision overlay");
            ui.checkbox(&mut ed.show_objects, "Node markers");
            ui.separator();
            ui.label(egui::RichText::new("Interface").strong());
            ui.horizontal(|ui| {
                ui.label("UI scale");
                if ui.add(egui::Slider::new(&mut shell.ui_scale, 0.75..=2.0).fixed_decimals(2)).drag_stopped() {
                    ctx.set_zoom_factor(shell.ui_scale);
                }
                if ui.small_button("Reset").clicked() {
                    shell.ui_scale = 1.0;
                    ctx.set_zoom_factor(1.0);
                }
            });
            ui.label(theme::faint_label("Saved automatically (editor_prefs.json, editor_layout.json)."));
        });
        if !open {
            shell.prefs_open = false;
        }
    }
    {
        // viewport preferences survive restarts (editor_prefs.json)
        let path = app.dirs.root.join("editor_prefs.json");
        if !shell.prefs_loaded {
            shell.prefs_loaded = true;
            if let Ok(text) = std::fs::read_to_string(&path) {
                app.panels.editor.apply_prefs(&text);
            }
            shell.saved_prefs = app.panels.editor.prefs_json();
        }
        let now = app.panels.editor.prefs_json();
        if now != shell.saved_prefs {
            let _ = std::fs::write(&path, &now);
            shell.saved_prefs = now;
        }
    }
    app.shell = shell;
}
