//! DQXI Studio - Squirrel script editor.
//!
//! Shows the 769 script packs as a tree (category -> area/event), opens either
//! the readable `.nut` source or the annotated disassembly listing, and builds
//! the edited text back into `script.cnut` with `tools/script_build.py`.
//!
//! The right side lists the script's functions/events, the native engine calls
//! it makes (name + summary), and who calls the selected function.

use std::path::PathBuf;
use std::sync::mpsc::{Receiver, TryRecvError};
use std::sync::Arc;

use eframe::egui;
use serde::Deserialize;

use crate::app::ViewerApp;
use crate::data::scripts::{local_callers, AreaMeta, FuncMeta};
use crate::theme;
use crate::ui::{highlight_line, Lang};
use crate::utils::{human_count, human_size};

#[derive(Clone, Copy, PartialEq, Eq, Default, Debug)]
enum Mode {
    #[default]
    Source,
    Assembly,
}

impl Mode {
    fn label(self) -> &'static str {
        match self {
            Mode::Source => "Squirrel source",
            Mode::Assembly => "Assembly listing",
        }
    }

    fn tier(self) -> &'static str {
        match self {
            Mode::Source => "source",
            Mode::Assembly => "asm",
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Default)]
enum SideTab {
    #[default]
    Functions,
    Natives,
    Callers,
}

#[derive(Default)]
struct Buffer {
    text: String,
    loaded: String,
    path: Option<PathBuf>,
    /// Set when the readable source does not exist for this pack.
    unavailable: Option<String>,
}

impl Buffer {
    fn open(&mut self, path: Option<PathBuf>, text: Option<String>, missing: Option<String>) {
        self.path = path;
        self.text = text.unwrap_or_default();
        self.loaded = self.text.clone();
        self.unavailable = missing;
    }

    fn dirty(&self) -> bool {
        self.text != self.loaded
    }

    fn revert(&mut self) {
        self.text = self.loaded.clone();
    }
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum JobKind {
    Compile,
    Save,
}

#[derive(Default, Deserialize)]
struct ToolResult {
    #[serde(default)]
    ok: bool,
    #[serde(default)]
    errors: Vec<String>,
    #[serde(default)]
    tier: String,
    #[serde(default)]
    bytes: usize,
    #[serde(default)]
    reused: usize,
    #[serde(default)]
    compiled: usize,
    #[serde(default)]
    functions: usize,
    #[serde(default)]
    pack: String,
    #[serde(default)]
    member: String,
    #[serde(default)]
    mod_file: String,
    #[serde(default)]
    size: usize,
    #[serde(default)]
    sha256: String,
}

enum Job {
    Built(ToolResult, JobKind),
    Failed(String),
}

#[derive(Default)]
pub struct ScriptsPanel {
    pub query: String,
    dirty: bool,
    list: Vec<usize>,
    selected: Option<usize>,
    /// Index whose files are currently in the buffers.
    loaded_index: Option<usize>,
    mode: Mode,
    source: Buffer,
    asm: Buffer,
    errors: Vec<String>,
    status: String,
    status_bad: bool,
    job: Option<Receiver<Job>>,
    side_tab: SideTab,
    func_index: Option<usize>,
    native_index: Option<usize>,
    find: String,
    /// 1-based line the editor caret should move to.
    jump_to: Option<usize>,
    /// Scroll the editor to this 1-based line on the next frame.
    scroll_to: Option<usize>,
    /// Area/line requested by a cross-reference click.
    pending_open: Option<(String, usize)>,
    /// Area requested by global search / `DQXI_START_QUERY`.
    pending_select: Option<String>,
    pub request: Option<String>,
    group_meta_missing: bool,
}

impl ScriptsPanel {
    pub fn new() -> Self {
        Self {
            dirty: true,
            ..Default::default()
        }
    }

    pub fn request(&mut self, query: &str) {
        self.request = Some(query.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.dirty = true;
    }

    fn buffer(&self) -> &Buffer {
        match self.mode {
            Mode::Source => &self.source,
            Mode::Assembly => &self.asm,
        }
    }

    fn buffer_mut(&mut self) -> &mut Buffer {
        match self.mode {
            Mode::Source => &mut self.source,
            Mode::Assembly => &mut self.asm,
        }
    }

    fn area(&self, app: &ViewerApp) -> Option<String> {
        let index = self.selected?;
        app.data()?.scripts.items.get(index).map(|s| s.area.clone())
    }
}

// ---------------------------------------------------------------------------
// loading
// ---------------------------------------------------------------------------

fn load_selection(app: &mut ViewerApp) {
    let Some(index) = app.panels.scripts.selected else { return };
    let Some(script) = app.data().and_then(|d| d.scripts.items.get(index)).cloned() else {
        return;
    };
    let source_path = script.source_path();
    let asm_path = Some(script.path.clone());
    let (source_text, source_missing) = match &source_path {
        Some(path) => (
            app.data.as_deref_mut().map(|d| d.scripts.text(path)),
            None,
        ),
        None => (
            None,
            Some("no script.decompiled.nut - run python tools/squirrel_decompile.py --all".to_string()),
        ),
    };
    let asm_text = app
        .data
        .as_deref_mut()
        .map(|d| d.scripts.text(&script.path));

    let panel = &mut app.panels.scripts;
    panel.source.open(source_path, source_text, source_missing);
    panel.asm.open(asm_path, asm_text, None);
    panel.loaded_index = Some(index);
    panel.errors.clear();
    panel.status.clear();
    panel.status_bad = false;
    panel.func_index = None;
    panel.native_index = None;
    panel.jump_to = None;
    panel.scroll_to = None;
    if let Some((area, line)) = panel.pending_open.take() {
        if area == script.area {
            panel.jump_to = Some(line);
            panel.scroll_to = Some(line);
        }
    }
}

// ---------------------------------------------------------------------------
// background build
// ---------------------------------------------------------------------------

fn start_job(app: &mut ViewerApp, kind: JobKind) {
    if app.panels.scripts.job.is_some() {
        return;
    }
    let Some(area) = app.panels.scripts.area(app) else { return };
    let tier = app.panels.scripts.mode.tier();
    let text = app.panels.scripts.buffer().text.clone();
    if text.is_empty() {
        app.panels.scripts.status = "nothing to build".into();
        app.panels.scripts.status_bad = true;
        return;
    }
    let root = app.dirs.root.clone();
    let edit_dir = root.join("build").join("script_edits").join(&area);
    if let Err(err) = std::fs::create_dir_all(&edit_dir) {
        app.panels.scripts.status = format!("cannot create {}: {err}", edit_dir.display());
        app.panels.scripts.status_bad = true;
        return;
    }
    let src = edit_dir.join("edit.nut");
    if let Err(err) = std::fs::write(&src, &text) {
        app.panels.scripts.status = format!("cannot write {}: {err}", src.display());
        app.panels.scripts.status_bad = true;
        return;
    }
    let (tx, rx) = std::sync::mpsc::channel();
    app.panels.scripts.job = Some(rx);
    app.panels.scripts.status = match kind {
        JobKind::Compile => "compiling\u{2026}".to_string(),
        JobKind::Save => "compiling and staging the pack\u{2026}".to_string(),
    };
    app.panels.scripts.status_bad = false;
    app.panels.scripts.errors.clear();

    std::thread::spawn(move || {
        let script = root.join("tools").join("script_build.py");
        let mut command = std::process::Command::new("python");
        command
            .arg(&script)
            .arg(if kind == JobKind::Save { "pack" } else { "compile" })
            .arg(&src)
            .arg("--area")
            .arg(&area)
            .arg("--tier")
            .arg(tier)
            .arg("--json")
            .current_dir(&root);
        if kind == JobKind::Save {
            command.arg("--mod").arg(root.join("mod"));
        }
        let job = match command.output() {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let parsed: Option<ToolResult> = stdout
                    .lines()
                    .rev()
                    .find(|line| line.trim_start().starts_with('{'))
                    .and_then(|line| serde_json::from_str(line).ok());
                match parsed {
                    Some(result) => Job::Built(result, kind),
                    None => Job::Failed(format!(
                        "the build tool produced no result.\n{}\n{}",
                        stdout.trim(),
                        String::from_utf8_lossy(&output.stderr).trim()
                    )),
                }
            }
            Err(err) => Job::Failed(format!(
                "could not run python ({err}). Build manually with:\n\
                 python tools/script_build.py {} {} --area {} --tier {}",
                if kind == JobKind::Save { "pack" } else { "compile" },
                src.display(),
                area,
                tier
            )),
        };
        let _ = tx.send(job);
    });
}

fn poll_job(app: &mut ViewerApp, ui: &egui::Ui) {
    let Some(rx) = &app.panels.scripts.job else { return };
    match rx.try_recv() {
        Ok(Job::Built(result, kind)) => {
            let panel = &mut app.panels.scripts;
            panel.job = None;
            if result.ok {
                panel.errors.clear();
                panel.status_bad = false;
                panel.status = if kind == JobKind::Save {
                    let size = if result.size > 0 { result.size } else { result.bytes };
                    format!(
                        "staged {}:{} -> {} ({} bytes)",
                        result.pack, result.member, result.mod_file, size
                    )
                } else if result.tier == "source" {
                    format!(
                        "compiled {} bytes: {} function(s) reused, {} recompiled",
                        result.bytes, result.reused, result.compiled
                    )
                } else {
                    format!("assembled {} bytes ({} functions)", result.bytes, result.functions)
                };
            } else {
                panel.status = if kind == JobKind::Save {
                    "save failed".to_string()
                } else {
                    "compile failed".to_string()
                };
                panel.status_bad = true;
                panel.errors = if result.errors.is_empty() {
                    vec!["the build tool reported a failure without a message".to_string()]
                } else {
                    result.errors
                };
            }
        }
        Ok(Job::Failed(message)) => {
            app.panels.scripts.job = None;
            app.panels.scripts.status_bad = true;
            app.panels.scripts.status = message;
        }
        Err(TryRecvError::Empty) => {
            ui.ctx().request_repaint_after(std::time::Duration::from_millis(120));
        }
        Err(TryRecvError::Disconnected) => {
            app.panels.scripts.job = None;
            app.panels.scripts.status_bad = true;
            app.panels.scripts.status = "the build job stopped without a result".into();
        }
    }
}

// ---------------------------------------------------------------------------
// syntax highlighting
// ---------------------------------------------------------------------------

/// Lay out the whole editor text with the shared Squirrel colourer.
///
/// Adjacent same-colour sections are merged: `highlight_line` emits one
/// section per punctuation/space character, which would be thousands of
/// sections for a 3,000-line script.
fn highlighted(ui: &egui::Ui, text: &str, wrap_width: f32) -> Arc<egui::Galley> {
    let mono = egui::FontId::monospace(12.5);
    let mut job = egui::text::LayoutJob::default();
    job.wrap.max_width = wrap_width.max(1.0);
    for (line_no, line) in text.split('\n').enumerate() {
        if line_no > 0 {
            job.append(
                "\n",
                0.0,
                egui::TextFormat {
                    font_id: mono.clone(),
                    color: theme::MONO,
                    ..Default::default()
                },
            );
        }
        let coloured = highlight_line(line, Lang::Nut);
        for section in &coloured.sections {
            let piece = &coloured.text[section.byte_range.start.0..section.byte_range.end.0];
            if piece.is_empty() {
                continue;
            }
            if let Some(last) = job.sections.last_mut() {
                if last.format.color == section.format.color
                    && last.format.font_id == section.format.font_id
                    && last.leading_space == 0.0
                {
                    job.text.push_str(piece);
                    last.byte_range.end.0 += piece.len();
                    continue;
                }
            }
            job.append(piece, 0.0, section.format.clone());
        }
    }
    ui.ctx().fonts_mut(|f| f.layout_job(job))
}

fn line_offset(text: &str, line: usize) -> usize {
    let mut offset = 0;
    for (index, part) in text.split_inclusive('\n').enumerate() {
        if index + 1 >= line {
            return offset;
        }
        offset += part.len();
    }
    text.len()
}

fn error_line(message: &str) -> Option<usize> {
    message
        .strip_prefix("line ")
        .and_then(|rest| rest.split(':').next())
        .and_then(|value| value.trim().parse().ok())
}

// ---------------------------------------------------------------------------
// function list (falls back to scanning the text when the index is missing)
// ---------------------------------------------------------------------------

fn functions_from_text(text: &str, assembly: bool) -> Vec<FuncMeta> {
    let mut out = Vec::new();
    for (index, line) in text.lines().enumerate() {
        let trimmed = line.trim_start();
        // source: `function Name(args) {`
        // listing: `function 'Name'('this', ...) /* ... */ {`
        let (name, params) = if let Some(rest) = trimmed.strip_prefix("function '") {
            let Some((name, tail)) = rest.split_once('\'') else { continue };
            let params = tail
                .trim_start_matches('(')
                .split_once(')')
                .map(|(p, _)| p.trim().to_string())
                .unwrap_or_default();
            (name.trim().to_string(), params)
        } else if let Some(rest) = trimmed.strip_prefix("function ") {
            let Some((name, tail)) = rest.split_once('(') else { continue };
            let params = tail
                .split_once(')')
                .map(|(p, _)| p.trim().to_string())
                .unwrap_or_default();
            (name.trim().to_string(), params)
        } else {
            continue;
        };
        if name.is_empty() || (assembly && name == "main") {
            continue;
        }
        out.push(FuncMeta {
            name,
            params,
            line: index + 1,
        });
    }
    out
}

fn side_functions(meta: Option<&AreaMeta>, text: &str, assembly: bool) -> Vec<FuncMeta> {
    // The index stores line numbers into script.decompiled.nut. In Assembly
    // mode the listing has its own line numbering, so parse the open text.
    if assembly {
        return functions_from_text(text, true);
    }
    match meta {
        Some(meta) if !meta.functions.is_empty() => meta.functions.clone(),
        _ => functions_from_text(text, false),
    }
}

// ---------------------------------------------------------------------------
// UI
// ---------------------------------------------------------------------------

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if !app.data().is_some_and(|d| d.scripts.ready) {
        ui.label(theme::dim_label("indexing scripts\u{2026}"));
        return;
    }
    if let Some(query) = app.panels.scripts.request.take() {
        app.panels.scripts.query = query.clone();
        app.panels.scripts.pending_select = Some(query);
        app.panels.scripts.dirty = true;
    }
    if app.panels.scripts.dirty {
        if let Some(data) = app.data.as_deref() {
            let panel = &mut app.panels.scripts;
            panel.list = data.scripts.search(&panel.query);
            panel.group_meta_missing = data.scripts.meta.is_none();
            panel.dirty = false;
            if let Some(name) = panel.pending_select.take() {
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
    if app.panels.scripts.selected != app.panels.scripts.loaded_index {
        load_selection(app);
    }
    poll_job(app, ui);

    // Ctrl+B compile, Ctrl+S save to mod
    let (compile_key, save_key) = ui.input(|i| {
        (
            i.modifiers.command && i.key_pressed(egui::Key::B),
            i.modifiers.command && i.key_pressed(egui::Key::S),
        )
    });
    if compile_key {
        start_job(app, JobKind::Compile);
    }
    if save_key {
        start_job(app, JobKind::Save);
    }

    list_panel(app, ui);

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let Some(index) = app.panels.scripts.selected else {
                ui.label(theme::faint_label("Select a script pack."));
                return;
            };
            let Some(script) = app.data().and_then(|d| d.scripts.items.get(index)).cloned() else {
                return;
            };
            let meta = app
                .data()
                .and_then(|d| d.scripts.area_meta(&script.area))
                .cloned();
            let area = script.area.clone();

            header(app, ui, &script, meta.as_ref());
            toolbar(app, ui);
            if app.panels.scripts.group_meta_missing && app.panels.scripts.mode == Mode::Source {
                ui.label(theme::faint_label(
                    "script_index.json is missing: run `python tools/script_build.py index` \
                     for native summaries and cross-references.",
                ));
            }
            side_panel(app, ui, meta.as_ref(), &area);
            footer(app, ui);
            editor(app, ui, &area);
        });
}

fn list_panel(app: &mut ViewerApp, ui: &mut egui::Ui) {
    egui::Panel::left("script_list")
        .exact_size(300.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Scripts"));
            ui.label(theme::faint_label(
                "events \u{b7} cutscenes \u{b7} quests \u{b7} logic",
            ));
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.scripts.query)
                        .hint_text("Search area, scene or category\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.scripts.dirty = true;
            }
            let total = app.panels.scripts.list.len();
            let areas = app.data().map(|d| d.scripts.items.len()).unwrap_or(0);
            ui.label(theme::faint_label(format!(
                "{} of {} packs",
                human_count(total),
                human_count(areas)
            )));
            ui.separator();

            // category -> area rows. Categories come from the generated index
            // (organize_scripts.py names); without it, use the PACK prefix.
            let mut categories: Vec<(String, Vec<usize>)> = Vec::new();
            let mut seen: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
            if let Some(data) = app.data.as_deref() {
                for &index in &app.panels.scripts.list {
                    let Some(script) = data.scripts.items.get(index) else { continue };
                    let category = data
                        .scripts
                        .area_meta(&script.area)
                        .map(|m| m.category.clone())
                        .filter(|c| !c.is_empty())
                        .unwrap_or_else(|| {
                            if script.area.contains("_cs_") {
                                "Cutscenes".into()
                            } else {
                                "General".into()
                            }
                        });
                    match seen.get(&category) {
                        Some(&at) => categories[at].1.push(index),
                        None => {
                            seen.insert(category.clone(), categories.len());
                            categories.push((category, vec![index]));
                        }
                    }
                }
            }
            categories.sort_by(|a, b| category_key(&a.0).cmp(&category_key(&b.0)));

            let selected = app.panels.scripts.selected;
            let mut clicked = None;
            egui::ScrollArea::vertical()
                .id_salt("script_tree")
                .auto_shrink([false, false])
                .show(ui, |ui| {
                    for (category, indices) in &categories {
                        egui::CollapsingHeader::new(
                            egui::RichText::new(format!("{category} ({})", indices.len())).size(12.0),
                        )
                        .id_salt(("script_cat", category))
                        .default_open(category == "Scenarios" || category == "General")
                        .show(ui, |ui| {
                            for &index in indices {
                                let Some(data) = app.data.as_deref() else { continue };
                                let Some(script) = data.scripts.items.get(index) else { continue };
                                let meta = data.scripts.area_meta(&script.area);
                                let title = meta
                                    .filter(|m| !m.title.is_empty())
                                    .map(|m| m.title.as_str())
                                    .unwrap_or(script.area.as_str());
                                let label = egui::RichText::new(crate::utils::elide(title, 34)).size(12.0);
                                let response = ui.selectable_label(selected == Some(index), label);
                                let events = meta.map(|m| m.functions.len()).unwrap_or(0);
                                response
                                    .clone()
                                    .on_hover_text(format!(
                                        "{}\n{}\n{} events · {}",
                                        script.area,
                                        meta.map(|m| m.description.as_str()).unwrap_or(""),
                                        human_count(events),
                                        human_size(script.size)
                                    ));
                                if response.clicked() {
                                    clicked = Some(index);
                                }
                            }
                        });
                    }
                });
            if let Some(index) = clicked {
                app.panels.scripts.selected = Some(index);
            }
        });
}

fn category_key(category: &str) -> (u8, String) {
    let order = [
        "Scenarios",
        "Cutscenes",
        "Boss_Battles",
        "Dungeons",
        "Overworld_Fields",
        "Fields",
        "Battles",
        "Tickington_Past_Worlds",
        "StreetPass_Yocchi_Quests",
        "General",
    ];
    let rank = order.iter().position(|c| *c == category).unwrap_or(order.len()) as u8;
    (rank, category.to_string())
}

fn header(app: &mut ViewerApp, ui: &mut egui::Ui, script: &crate::data::scripts::Script,
          meta: Option<&AreaMeta>) {
    let lines = app.panels.scripts.buffer().text.lines().count();
    let function_count = meta.map(|m| m.functions.len()).unwrap_or(0);
    let native_count = meta.map(|m| m.natives.len()).unwrap_or(0);
    ui.horizontal(|ui| {
        ui.label(theme::heading(
            meta.filter(|m| !m.title.is_empty())
                .map(|m| m.title.clone())
                .unwrap_or_else(|| script.area.clone()),
        ));
        ui.label(theme::dim_label(format!(
            "{}  \u{b7}  {}  \u{b7}  {} functions  \u{b7}  {} native calls  \u{b7}  {} lines",
            script.area,
            human_size(script.size),
            human_count(function_count),
            human_count(native_count),
            human_count(lines),
        )));
    });
    if let Some(meta) = meta {
        if !meta.description.is_empty() {
            ui.label(theme::faint_label(meta.description.clone()));
        }
    }
}

impl ScriptsPanel {
    /// Unsaved edits in either view of the open script.
    pub fn is_dirty(&self) -> bool {
        self.source.dirty() || self.asm.dirty()
    }
}

/// File > Save All: compile and stage the open script.
pub fn save_active(app: &mut ViewerApp) {
    if app.panels.scripts.job.is_none() && !app.panels.scripts.buffer().text.is_empty() {
        start_job(app, JobKind::Save);
    }
}

fn toolbar(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let busy = app.panels.scripts.job.is_some();
    let dirty = app.panels.scripts.buffer().dirty();
    ui.horizontal(|ui| {
        let mut mode = app.panels.scripts.mode;
        ui.selectable_value(&mut mode, Mode::Source, "Squirrel source")
            .on_hover_text("Readable decompiled source; rebuilt by the Python compiler");
        ui.selectable_value(&mut mode, Mode::Assembly, "Assembly listing")
            .on_hover_text("Bit-exact annotated bytecode listing (always round-trips)");
        if mode != app.panels.scripts.mode {
            app.panels.scripts.mode = mode;
            app.panels.scripts.errors.clear();
            app.panels.scripts.status.clear();
            app.panels.scripts.status_bad = false;
            app.panels.scripts.func_index = None;
        }
        ui.separator();
        if app.panels.scripts.buffer().unavailable.is_some() {
            ui.label(theme::faint_label("source unavailable"));
        }
        if dirty {
            ui.label(egui::RichText::new("\u{25cf} modified").color(theme::WARN).size(11.0));
        }
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if ui
                .add_enabled(!busy && !app.panels.scripts.buffer().text.is_empty(),
                             egui::Button::new("Save to mod"))
                .on_hover_text("Compile and stage mod/romfs/<pack> (Ctrl+S)")
                .clicked()
            {
                start_job(app, JobKind::Save);
            }
            if ui
                .add_enabled(!busy && !app.panels.scripts.buffer().text.is_empty(),
                             egui::Button::new("Compile"))
                .on_hover_text("Compile to a .cnut and list errors (Ctrl+B)")
                .clicked()
            {
                start_job(app, JobKind::Compile);
            }
            if ui
                .add_enabled(dirty, egui::Button::new("Revert"))
                .on_hover_text("Discard edits in this view")
                .clicked()
            {
                let panel = &mut app.panels.scripts;
                panel.buffer_mut().revert();
                panel.errors.clear();
                panel.status = "reverted to the file on disk".into();
                panel.status_bad = false;
            }
            ui.add(
                egui::TextEdit::singleline(&mut app.panels.scripts.find)
                    .hint_text("Find\u{2026}")
                    .desired_width(140.0),
            );
            if ui.button("Find").clicked() {
                let needle = app.panels.scripts.find.to_lowercase();
                if !needle.is_empty() {
                    let panel = &mut app.panels.scripts;
                    let line = panel
                        .buffer()
                        .text
                        .lines()
                        .position(|l| l.to_lowercase().contains(&needle))
                        .map(|i| i + 1);
                    panel.jump_to = line;
                    panel.scroll_to = line;
                }
            }
            if busy {
                ui.spinner();
            }
            if let Some(path) = app.panels.scripts.buffer().path.clone() {
                if ui.button("Copy path").on_hover_text(path.display().to_string()).clicked() {
                    ui.ctx().copy_text(path.display().to_string());
                }
            }
        });
    });
    ui.separator();
}

fn side_panel(app: &mut ViewerApp, ui: &mut egui::Ui, meta: Option<&AreaMeta>, area: &str) {
    egui::Panel::right("script_side")
        .default_size(330.0)
        .resizable(true)
        .size_range(220.0..=620.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(6)))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.selectable_value(&mut app.panels.scripts.side_tab, SideTab::Functions,
                                    format!("Functions ({})",
                                            meta.map(|m| m.functions.len()).unwrap_or(0)));
                ui.selectable_value(&mut app.panels.scripts.side_tab, SideTab::Natives,
                                    format!("Natives ({})", meta.map(|m| m.natives.len()).unwrap_or(0)));
                ui.selectable_value(&mut app.panels.scripts.side_tab, SideTab::Callers, "Callers");
            });
            ui.separator();
            match app.panels.scripts.side_tab {
                SideTab::Functions => functions_tab(app, ui, meta, area),
                SideTab::Natives => natives_tab(app, ui, meta),
                SideTab::Callers => callers_tab(app, ui, area),
            }
        });
}

fn functions_tab(app: &mut ViewerApp, ui: &mut egui::Ui, meta: Option<&AreaMeta>, area: &str) {
    let assembly = app.panels.scripts.mode == Mode::Assembly;
    let text = app.panels.scripts.buffer().text.clone();
    let functions = side_functions(meta, &text, assembly);
    let selected = app.panels.scripts.func_index;
    ui.label(theme::faint_label("Events and functions in this pack"));
    let mut clicked = None;
    let view_id = egui::Id::new(("script_functions_view", area, assembly));
    let (view_offset, view_height): (f32, f32) = ui.ctx().data(|d| d.get_temp(view_id)).unwrap_or((0.0, 0.0));
    let rows: Vec<usize> = (0..functions.len()).collect();
    let mut scroll_offset = None;
    if let Some((row, _)) = crate::ui::list_nav(ui.ctx(), &rows, selected.as_ref()) {
        clicked = Some(row);
        let top = row as f32 * 18.0;
        if top < view_offset {
            scroll_offset = Some(top);
        } else if top + 18.0 > view_offset + view_height {
            scroll_offset = Some(top + 18.0 - view_height);
        }
    }
    let mut list = egui::ScrollArea::vertical()
        .id_salt(("script_functions", area, assembly))
        .auto_shrink([false, false]);
    if let Some(offset) = scroll_offset {
        list = list.vertical_scroll_offset(offset.max(0.0));
    }
    let list_output = list
        .show_rows(ui, 18.0, functions.len(), |ui, range| {
            for row in range {
                let f = &functions[row];
                let text = egui::RichText::new(crate::utils::elide(
                    &format!("{}({})", f.name, f.params),
                    44,
                ))
                .monospace()
                .size(11.0);
                if ui.selectable_label(selected == Some(row), text).clicked() {
                    clicked = Some(row);
                }
            }
        });
    ui.ctx().data_mut(|d| d.insert_temp(view_id, (list_output.state.offset().y, list_output.inner_rect.height())));
    if let Some(row) = clicked {
        let f = &functions[row];
        app.panels.scripts.func_index = Some(row);
        app.panels.scripts.jump_to = Some(f.line);
        app.panels.scripts.scroll_to = Some(f.line);
    }
}

fn natives_tab(app: &mut ViewerApp, ui: &mut egui::Ui, meta: Option<&AreaMeta>) {
    let Some(meta) = meta else {
        ui.label(theme::faint_label("No script_index.json entry for this pack."));
        return;
    };
    if meta.natives.is_empty() {
        ui.label(theme::faint_label("This script calls no native engine functions."));
        return;
    }
    ui.label(theme::faint_label("Native engine calls used by this script"));
    let selected = app.panels.scripts.native_index;
    let mut clicked = None;
    egui::ScrollArea::vertical()
        .id_salt(("script_natives", meta.title.clone()))
        .auto_shrink([false, false])
        .max_height(ui.available_height() - 150.0)
        .show(ui, |ui| {
            for (row, name) in meta.natives.iter().enumerate() {
                let info = app.data().and_then(|d| d.scripts.native(name));
                let summary = info.map(|i| i.summary.as_str()).unwrap_or("");
                let address = info.map(|i| i.address.as_str()).unwrap_or("");
                let text = egui::RichText::new(format!(
                    "{name}  {}",
                    crate::utils::elide(summary, 40)
                ))
                .size(11.0);
                let response = ui.selectable_label(selected == Some(row), text);
                response.clone().on_hover_text(format!("{name}\n{address}\n{summary}"));
                if response.clicked() {
                    clicked = Some(row);
                }
            }
        });
    if let Some(row) = clicked {
        app.panels.scripts.native_index = Some(row);
    }
    ui.separator();
    if let Some(row) = app.panels.scripts.native_index {
        if let Some(name) = meta.natives.get(row) {
            if let Some(info) = app.data().and_then(|d| d.scripts.native(name)) {
                ui.label(theme::accent(name.clone()));
                ui.label(theme::faint_label(info.address.clone()));
                ui.label(theme::dim_label(info.summary.clone()));
                if !info.documented_as.is_empty() {
                    ui.label(theme::faint_label(format!("native implementation: {}", info.documented_as)));
                }
            }
        }
    }
}

fn callers_tab(app: &mut ViewerApp, ui: &mut egui::Ui, area: &str) {
    let assembly = app.panels.scripts.mode == Mode::Assembly;
    let text = app.panels.scripts.buffer().text.clone();
    let funcs = if assembly {
        functions_from_text(&text, true)
    } else {
        match app.data().and_then(|d| d.scripts.area_meta(area)) {
            Some(meta) if !meta.functions.is_empty() => meta.functions.clone(),
            _ => functions_from_text(&text, false),
        }
    };
    let index = app.panels.scripts.func_index;
    let Some(index) = index.filter(|i| *i < funcs.len()) else {
        ui.label(theme::faint_label("Select a function to see its callers."));
        return;
    };
    let func = &funcs[index];
    ui.label(theme::accent(format!("{}({})", func.name, func.params)));
    let source = &app.panels.scripts.source.text;
    if source.is_empty() {
        ui.label(theme::faint_label("open Squirrel source to see same-script callers"));
    } else {
        let local = local_callers(source, &func.name);
        if local.is_empty() {
            ui.label(theme::faint_label("no call sites in this script"));
        } else {
            ui.label(theme::faint_label(format!("{} call site(s) in this script:", local.len())));
            let mut clicked = None;
            egui::ScrollArea::vertical()
                .id_salt(("script_callers_local", func.name.clone()))
                .max_height(160.0)
                .auto_shrink([false, false])
                .show(ui, |ui| {
                    for (line, caller) in &local {
                        if ui
                            .add(egui::Label::new(theme::mono(format!("{line:>5}  {caller}")).size(11.0))
                                .sense(egui::Sense::click()))
                            .on_hover_text("jump to the call")
                            .clicked()
                        {
                            clicked = Some(*line);
                        }
                    }
                });
            if let Some(line) = clicked {
                if assembly {
                    // Source line numbers only line up with script.decompiled.nut,
                    // so switch there instead of jumping into the listing.
                    app.panels.scripts.mode = Mode::Source;
                }
                app.panels.scripts.jump_to = Some(line);
                app.panels.scripts.scroll_to = Some(line);
            }
        }
    }
    ui.separator();
    let xref = app.data().and_then(|d| d.scripts.xrefs(&func.name)).cloned();
    match xref {
        Some(info) => {
            ui.label(theme::faint_label(format!(
                "{} call site(s); the function is defined in {} pack(s)",
                human_count(info.count),
                human_count(info.defined_in)
            )));
            let mut open = None;
            egui::ScrollArea::vertical()
                .id_salt(("script_callers_other", func.name.clone()))
                .auto_shrink([false, false])
                .show(ui, |ui| {
                    for row in &info.callers {
                        if row.script == area {
                            continue;
                        }
                        if ui
                            .add(egui::Label::new(
                                theme::mono(format!("{}  {}", row.script, row.caller)).size(11.0),
                            ).sense(egui::Sense::click()))
                            .on_hover_text("open that script")
                            .clicked()
                        {
                            open = Some(row.script.clone());
                        }
                    }
                    if info.count > info.callers.len() {
                        ui.label(theme::faint_label(format!(
                            "\u{2026} {} more (sample of {})",
                            info.count - info.callers.len(),
                            info.callers.len()
                        )));
                    }
                });
            if let Some(script) = open {
                app.panels.scripts.request = Some(script);
                app.panels.scripts.dirty = true;
            }
        }
        None => {
            ui.label(theme::faint_label("no cross-references recorded for this name"));
        }
    }
}

fn footer(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let has_errors = !app.panels.scripts.errors.is_empty();
    let status = app.panels.scripts.status.clone();
    let bad = app.panels.scripts.status_bad;
    if !status.is_empty() || has_errors {
        egui::Panel::bottom("script_status")
            .resizable(false)
            .show(ui, |ui| {
                if !status.is_empty() {
                    ui.label(
                        egui::RichText::new(status)
                            .color(if bad { theme::ERR } else { theme::TEXT_DIM })
                            .size(11.5),
                    );
                }
                if has_errors {
                    let errors = app.panels.scripts.errors.clone();
                    let mut jump = None;
                    egui::ScrollArea::vertical()
                        .id_salt("script_errors")
                        .max_height(110.0)
                        .auto_shrink([false, false])
                        .show(ui, |ui| {
                            for error in &errors {
                                let text = egui::RichText::new(error).color(theme::ERR).monospace().size(11.0);
                                if ui
                                    .add(egui::Label::new(text).sense(egui::Sense::click()))
                                    .on_hover_text("jump to the reported line")
                                    .clicked()
                                {
                                    jump = error_line(error);
                                }
                            }
                        });
                    if let Some(line) = jump {
                        app.panels.scripts.jump_to = Some(line);
                        app.panels.scripts.scroll_to = Some(line);
                    }
                }
            });
    }
}

fn editor(app: &mut ViewerApp, ui: &mut egui::Ui, area: &str) {
    let panel = &mut app.panels.scripts;
    if let Some(missing) = panel.buffer().unavailable.clone() {
        ui.add_space(20.0);
        ui.label(egui::RichText::new(missing).color(theme::WARN));
        return;
    }
    let mode = panel.mode;
    let id = egui::Id::new(("script_editor", area.to_string(), mode.tier()));
    let jump = panel.jump_to.take();
    let scroll_to = panel.scroll_to.take();
    let line_count = panel.buffer().text.lines().count().max(1);
    let mut scroll = egui::ScrollArea::vertical()
        .id_salt(("script_editor_scroll", area.to_string(), mode.tier()))
        .auto_shrink([false, false]);
    if let Some(line) = scroll_to {
        scroll = scroll.vertical_scroll_offset((line.saturating_sub(3)) as f32 * 15.0);
    }
    let mut layouter = |ui: &egui::Ui, buf: &dyn egui::TextBuffer, wrap_width: f32| {
        highlighted(ui, buf.as_str(), wrap_width)
    };
    let output = {
        let text = &mut panel.buffer_mut().text;
        scroll.show(ui, |ui| {
            egui::TextEdit::multiline(text)
                .id(id)
                .code_editor()
                .desired_rows(line_count)
                .desired_width(f32::INFINITY)
                .lock_focus(true)
                .layouter(&mut layouter)
                .show(ui)
        })
    };
    if let Some(line) = jump {
        let text = &panel.buffer().text;
        let byte = line_offset(text, line);
        let chars = text[..byte.min(text.len())].chars().count();
        let mut state = output.inner.state.clone();
        state.cursor.set_char_range(Some(egui::text_selection::CCursorRange::one(
            egui::text::CCursor::new(chars),
        )));
        state.store(ui.ctx(), id);
        output.inner.response.response.request_focus();
        ui.ctx().request_repaint();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn source_functions_are_listed_with_lines() {
        let text = "// header\nfunction StartEvent(func) {\n}\nfunction OnBeginScene() {}\n";
        let funcs = functions_from_text(text, false);
        assert_eq!(funcs.len(), 2);
        assert_eq!(funcs[0].name, "StartEvent");
        assert_eq!(funcs[0].params, "func");
        assert_eq!(funcs[0].line, 2);
        assert_eq!(funcs[1].line, 4);
    }

    #[test]
    fn assembly_functions_use_the_quoted_name() {
        let text = "function 'main'('this') /* stack=5 */ {\n  [   0] RETURN 255 0 0 0\n}\n\
                    function 'StartEvent'('this', 'func') {\n}\n";
        let funcs = functions_from_text(text, true);
        assert_eq!(funcs.len(), 1, "main is the script body, not an event");
        assert_eq!(funcs[0].name, "StartEvent");
        assert_eq!(funcs[0].params, "'this', 'func'");
        assert_eq!(funcs[0].line, 4);
    }

    #[test]
    fn line_and_error_helpers() {
        let text = "one\ntwo\nthree";
        assert_eq!(line_offset(text, 1), 0);
        assert_eq!(line_offset(text, 2), 4);
        assert_eq!(line_offset(text, 99), text.len());
        assert_eq!(error_line("line 42: unexpected '}'"), Some(42));
        assert_eq!(error_line("assembly failed: boom"), None);
    }

    #[test]
    fn buffer_dirty_tracks_edits() {
        let mut buffer = Buffer::default();
        buffer.open(None, Some("a <- 1;\n".into()), None);
        assert!(!buffer.dirty());
        buffer.text.push_str("b <- 2;\n");
        assert!(buffer.dirty());
        buffer.revert();
        assert!(!buffer.dirty());
    }

    #[test]
    fn categories_are_ordered_with_scenarios_first() {
        let mut names = vec!["General", "Cutscenes", "Scenarios", "Battles"];
        names.sort_by_key(|name| category_key(name));
        assert_eq!(names[0], "Scenarios");
        assert_eq!(names[1], "Cutscenes");
        assert_eq!(names[3], "General");
    }

    #[test]
    fn build_tool_json_parses() {
        // Exact shape printed by `python tools/script_build.py pack ... --json`.
        let json = r#"{"ok": true, "bytes": 5337, "tier": "source", "functions": 12,
            "reused": 12, "compiled": 0, "pack": "/script/a_000.pack",
            "member": "script.cnut", "mod_file": "mod\\romfs\\script\\a_000.pack",
            "size": 5416, "original_size": 5416, "sha256": "abc",
            "compiled_file": "build/script_edits/a_000/script.cnut"}"#;
        let result: ToolResult = serde_json::from_str(json).expect("panel must parse the tool");
        assert!(result.ok);
        assert_eq!(result.reused, 12);
        assert_eq!(result.compiled, 0);
        assert_eq!(result.member, "script.cnut");
    }

    #[test]
    fn build_tool_error_json_parses() {
        let json = r#"{"ok": false, "errors": ["line 12: expected '}'"], "tier": "source"}"#;
        let result: ToolResult = serde_json::from_str(json).expect("error result");
        assert!(!result.ok);
        assert_eq!(result.errors.len(), 1);
        assert_eq!(error_line(&result.errors[0]), Some(12));
    }
}
