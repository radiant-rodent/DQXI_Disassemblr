//! Decompiled code browser: function catalogue + source trees.

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::ui::{Lang, TextState};
use crate::utils::{human_count, human_size};

/// Rows per page in the function and file lists.
pub const PAGE: usize = 250;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    Functions,
    Sources,
}

pub struct CodePanel {
    pub query: String,
    mode: Option<String>,
    list: Vec<usize>,
    selected: Option<usize>,
    dirty: bool,
    request: Option<String>,
    text: TextState,
    tab: Tab,
    group: usize,
    groups: Vec<(String, Vec<(String, std::path::PathBuf, u64)>)>,
    file_selected: Option<usize>,
    file_text: TextState,
    find: String,
    page: usize,
    file_page: usize,
    /// show Ghidra's raw output instead of the readable view
    raw: bool,
    /// C source, assembly listing, patch diff or the assembly editor
    view: View,
    /// assembly listing of the selected function (from `tools.code_edit show`)
    asm: TextState,
    asm_for: Option<u32>,
    /// editable copy of the listing for the selected function
    edit: String,
    edit_for: Option<u32>,
    job: crate::ui::tool_job::ToolJob,
    /// what the running job is for: "show", "load-edit", "apply", "revert"
    job_kind: String,
    message: String,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum View {
    Source,
    Assembly,
    Diff,
    Edit,
}

impl Default for CodePanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            mode: None,
            list: Vec::new(),
            selected: None,
            dirty: true,
            request: None,
            text: TextState::default(),
            tab: Tab::Functions,
            group: 0,
            groups: Vec::new(),
            file_selected: None,
            file_text: TextState::default(),
            find: String::new(),
            page: 0,
            file_page: 0,
            raw: false,
            view: View::Source,
            asm: TextState::default(),
            asm_for: None,
            edit: String::new(),
            edit_for: None,
            job: Default::default(),
            job_kind: String::new(),
            message: String::new(),
        }
    }
}

impl CodePanel {
    pub fn request(&mut self, query: &str) {
        self.request = Some(query.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.mode = None;
        self.dirty = true;
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if app.data.is_none() {
        ui.label(theme::dim_label("indexing decompiled code\u{2026}"));
        return;
    }
    if let Some(data) = app.data.as_mut() {
        if !data.code.ready {
            data.code.ensure(&app.dirs);
        }
    }
    if let Some(query) = app.panels.code.request.take() {
        app.panels.code.query = query;
        app.panels.code.dirty = true;
    }
    // The source trees are only needed by the Sources tab, so scan them when it is first opened.
    if app.panels.code.tab == Tab::Sources && app.panels.code.groups.is_empty() {
        let dirs = app.dirs.clone();
        if let Some(data) = app.data.as_mut() {
            let groups = data.code.source_groups(&dirs).to_vec();
            app.panels.code.groups = groups;
        }
    }
    if app.panels.code.dirty {
        if let Some(data) = app.data.as_deref() {
            let panel = &mut app.panels.code;
            panel.list = data.code.search(&panel.query, panel.mode.as_deref(), 20000);
            panel.dirty = false;
            panel.page = 0;
            if let Some(query) = panel.request.take() {
                panel.query = query;
                panel.list = data.code.search(&panel.query, panel.mode.as_deref(), 20000);
                if let Some(first) = panel.list.first().copied() {
                    panel.selected = Some(first);
                    panel.text = TextState::default();
                }
            }
        }
    }

    ui.horizontal(|ui| {
        ui.label(theme::heading("Code"));
        let (functions, discovered, lifted) = app
            .data
            .as_deref()
            .map(|d| (d.code.functions.len(), d.code.total_discovered, d.code.decompiled_count))
            .unwrap_or((0, 0, 0));
        ui.label(theme::faint_label(format!(
            "{} catalogued  \u{b7}  {} discovered  \u{b7}  {} lifted",
            human_count(functions),
            human_count(discovered),
            human_count(lifted)
        )));
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            for (label, tab) in [("Sources & assembly", Tab::Sources), ("Decompiled functions", Tab::Functions)] {
                if ui.selectable_label(app.panels.code.tab == tab, label).clicked() {
                    app.panels.code.tab = tab;
                }
            }
        });
    });
    ui.separator();
    match app.panels.code.tab {
        Tab::Functions => functions_tab(app, ui),
        Tab::Sources => sources_tab(app, ui),
    }
}

fn functions_tab(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        if ui
            .add(
                egui::TextEdit::singleline(&mut app.panels.code.query)
                    .hint_text("Search name or paste 0x00100050\u{2026}")
                    .desired_width(320.0),
            )
            .changed()
        {
            app.panels.code.dirty = true;
        }
        for (label, value) in [("all", None), ("arm", Some("arm")), ("thumb", Some("thumb"))] {
            if ui
                .selectable_label(app.panels.code.mode.as_deref() == value, label)
                .clicked()
            {
                app.panels.code.mode = value.map(|v| v.to_string());
                app.panels.code.dirty = true;
            }
        }
        let (patched, version) = app
            .data
            .as_deref()
            .map(|d| (d.code.patched_count(), d.code.version_label.clone()))
            .unwrap_or_default();
        if patched > 0 {
            let on = app.panels.code.mode.as_deref() == Some("patched");
            if ui
                .selectable_label(on, egui::RichText::new(format!("patched ({patched})")).color(theme::ACCENT))
                .on_hover_text(format!("Functions and code caves the {version} patch changed or added"))
                .clicked()
            {
                app.panels.code.mode = if on { None } else { Some("patched".into()) };
                app.panels.code.dirty = true;
            }
        }
        ui.label(theme::faint_label(format!(
            "{} matches",
            human_count(app.panels.code.list.len())
        )));
        if ui.button("Copy address").clicked() {
            if let Some(index) = app.panels.code.selected {
                if let Some(func) = app.data.as_deref().and_then(|d| d.code.functions.get(index)) {
                    ui.ctx().copy_text(func.addr_hex());
                }
            }
        }
    });
    egui::Panel::left("code_list")
        .exact_size(400.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(6)))
        .show(ui, |ui| {
            let total = app.panels.code.list.len();
            pager(ui, &mut app.panels.code.page, total);
            let start = (app.panels.code.page * PAGE).min(total);
            let list = app.panels.code.list[start..(start + PAGE).min(total)].to_vec();
            let selected = app.panels.code.selected;
            let mut clicked = None;
            let nav = crate::ui::list_nav(ui.ctx(), &list, selected.as_ref());
            if let Some((item, _)) = &nav {
                clicked = Some(item.clone());
            }
            let nav_row = nav.map(|(_, r)| r);
            use egui_extras::{Column, TableBuilder};
            use crate::ui::TableNav;
            TableBuilder::new(ui)
                .id_salt("code_scroll")
                .nav_scroll(nav_row)
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::remainder().at_least(120.0))
                .column(Column::exact(100.0))
                .column(Column::exact(60.0))
                .column(Column::exact(60.0))
                .header(20.0, |mut header| {
                    for title in ["Function", "Address", "Bytes", "Mode"] {
                        header.col(|ui| {
                            ui.label(theme::faint_label(title));
                        });
                    }
                })
                .body(|body| {
                    body.rows(17.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let Some(func) = app.data.as_deref().and_then(|d| d.code.functions.get(index))
                        else {
                            return;
                        };
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            match &func.patch {
                                Some(kind) => {
                                    ui.label(
                                        egui::RichText::new(format!("\u{25cf} {}", func.name))
                                            .size(12.0)
                                            .color(theme::ACCENT),
                                    )
                                    .on_hover_text(patch_kind_text(kind));
                                }
                                None => {
                                    ui.label(egui::RichText::new(func.name.clone()).size(12.0));
                                }
                            }
                        });
                        row.col(|ui| {
                            ui.label(theme::mono(func.addr_hex()));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(func.size.to_string()));
                        });
                        row.col(|ui| {
                            ui.label(theme::dim_label(func.mode.clone()));
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(index) = clicked {
                app.panels.code.selected = Some(index);
                app.panels.code.text = TextState::default();
                let is_cave = app
                    .data
                    .as_deref()
                    .and_then(|d| d.code.functions.get(index))
                    .map(|f| f.file.as_os_str().is_empty())
                    .unwrap_or(false);
                if is_cave && app.panels.code.view == View::Source {
                    app.panels.code.view = View::Assembly;
                }
            }
        });
    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(6)))
        .show(ui, |ui| {
            let Some(index) = app.panels.code.selected else {
                ui.label(theme::faint_label("Select a function."));
                return;
            };
            detail(app, ui, index);
        });
}

fn patch_kind_text(kind: &str) -> &'static str {
    match kind {
        "hook" => "changed by the patch: branches into the patch's own code",
        "cave" => "code the patch added (code cave in free space)",
        _ => "instructions or literals changed by the patch",
    }
}

fn detail(app: &mut ViewerApp, ui: &mut egui::Ui, index: usize) {
    let Some(func) = app.data.as_deref().and_then(|d| d.code.functions.get(index)).cloned() else {
        return;
    };
    let patch = app.data.as_deref().and_then(|d| d.code.patch_of(index)).cloned();
    let version = app.data.as_deref().map(|d| d.code.version_label.clone()).unwrap_or_default();
    let has_c = !func.file.as_os_str().is_empty();
    poll_job(app, func.address);

    ui.horizontal(|ui| {
        ui.label(theme::heading(func.name.clone()));
        ui.label(theme::dim_label(format!(
            "{}  \u{b7}  {} bytes  \u{b7}  {}",
            func.addr_hex(),
            func.size,
            func.mode
        )));
    });
    if let Some(p) = &patch {
        egui::Frame::new()
            .fill(theme::BG_RAISED)
            .inner_margin(egui::Margin::same(6))
            .show(ui, |ui| {
                ui.label(
                    egui::RichText::new(format!(
                        "\u{25cf} Changed by the {version} patch \u{2014} {} ({} bytes)",
                        patch_kind_text(&p.kind),
                        p.changed_bytes
                    ))
                    .color(theme::ACCENT),
                );
                for link in &p.links {
                    ui.label(theme::dim_label(link.clone()));
                }
                for note in p.notes.iter().take(6) {
                    ui.label(theme::faint_label(note.clone()));
                }
                if has_c {
                    ui.label(theme::faint_label(
                        "The C views show the retail code (decompiled before the patch); Assembly, Patch diff and Edit show the patched bytes.",
                    ));
                }
            });
    }
    ui.horizontal(|ui| {
        let panel = &mut app.panels.code;
        let pick = |ui: &mut egui::Ui, on: bool, enabled: bool, label: &str, tip: &str| -> bool {
            ui.add_enabled(enabled, egui::Button::selectable(on, label)).on_hover_text(tip).clicked()
        };
        if pick(ui, panel.view == View::Source && !panel.raw, has_c, "Readable", "Names, self->fields, plain types (tools/readable_c.py)") {
            panel.view = View::Source;
            panel.raw = false;
            panel.text = TextState::default();
        }
        if pick(ui, panel.view == View::Source && panel.raw, has_c, "Raw Ghidra", "Ghidra's output exactly as generated") {
            panel.view = View::Source;
            panel.raw = true;
            panel.text = TextState::default();
        }
        if pick(ui, panel.view == View::Assembly, true, "Assembly", "The instructions as they are now: mod/code/code.bin, else the active game version") {
            panel.view = View::Assembly;
        }
        let diff = patch.as_ref().map(|p| !p.original.is_empty()).unwrap_or(false);
        if pick(ui, panel.view == View::Diff, diff, "Patch diff", "Retail instructions next to the patched ones") {
            panel.view = View::Diff;
        }
        if pick(ui, panel.view == View::Edit, true, "Edit assembly", "Change this function; saved into mod/code/code.bin") {
            panel.view = View::Edit;
        }
        if has_c {
            ui.label(theme::faint_label(func.file.to_string_lossy()));
        }
    });
    ui.separator();
    match app.panels.code.view {
        View::Source if has_c => {
            if app.panels.code.text.lines.is_empty() {
                let readable = readable_path(&app.dirs, &func.file).filter(|_| !app.panels.code.raw);
                let text = match readable.and_then(|p| crate::utils::read_text(&p).ok()) {
                    Some(text) => text,
                    None => app.data.as_mut().map(|d| d.code.text(index)).unwrap_or_default(),
                };
                let mut state = TextState::default();
                state.set(&text, Lang::C);
                app.panels.code.text = state;
            }
            let state = std::mem::take(&mut app.panels.code.text);
            crate::ui::text_view(ui, "code_text", &state, true);
            app.panels.code.text = state;
        }
        View::Source | View::Assembly => {
            if app.panels.code.asm_for != Some(func.address) && !app.panels.code.job.running() {
                start_job(app, "show", vec!["show".into(), func.addr_hex()], None);
            }
            if app.panels.code.asm_for != Some(func.address) {
                ui.label(theme::faint_label("disassembling\u{2026}"));
            } else {
                let state = std::mem::take(&mut app.panels.code.asm);
                crate::ui::text_view(ui, "code_asm", &state, true);
                app.panels.code.asm = state;
            }
        }
        View::Diff => diff_view(ui, patch.as_ref()),
        View::Edit => edit_view(app, ui, &func, &version),
    }
}

fn start_job(app: &mut ViewerApp, kind: &str, args: Vec<String>, stdin: Option<String>) {
    let root = app.dirs.root.clone();
    let panel = &mut app.panels.code;
    if panel.job.running() {
        return;
    }
    panel.job_kind = kind.to_string();
    panel.job.start(&root, kind, "tools.code_edit", args, stdin);
}

fn poll_job(app: &mut ViewerApp, address: u32) {
    let Some(result) = app.panels.code.job.poll() else { return };
    let kind = app.panels.code.job_kind.clone();
    let panel = &mut app.panels.code;
    match kind.as_str() {
        "show" => {
            let mut state = TextState::default();
            state.set(if result.ok { &result.stdout } else { &result.stderr }, Lang::Asm);
            panel.asm = state;
            panel.asm_for = Some(address);
        }
        "load-edit" => {
            if result.ok {
                panel.edit = result.stdout.clone();
                panel.edit_for = Some(address);
                panel.message.clear();
            } else {
                panel.message = result.summary();
            }
        }
        _ => {
            panel.message = result.summary();
            if result.ok {
                // the listings changed: load them again
                panel.asm_for = None;
                if kind == "revert" {
                    panel.edit_for = None;
                }
            }
        }
    }
    if kind == "apply" || kind == "revert" || (!result.ok && kind != "show") {
        app.status = format!("code edit: {}", app.panels.code.message);
    }
}

fn diff_view(ui: &mut egui::Ui, patch: Option<&crate::data::versions::CodePatch>) {
    let Some(p) = patch else {
        ui.label(theme::faint_label("This function is the same in the retail game and the active version."));
        return;
    };
    // listing lines are "ADDRESS  BYTES     insn": show the bytes and the instruction
    let body = |line: &str| line.get(10..).unwrap_or("").to_string();
    egui::ScrollArea::both().id_salt("code_diff").auto_shrink([false, false]).show(ui, |ui| {
        egui::Grid::new("code_diff_grid").striped(true).spacing([16.0, 2.0]).show(ui, |ui| {
            ui.label(theme::faint_label("address"));
            ui.label(theme::faint_label("retail"));
            ui.label(theme::faint_label("patched"));
            ui.end_row();
            let n = p.original.len().max(p.patched.len());
            for i in 0..n {
                let a = p.original.get(i).map(String::as_str).unwrap_or("");
                let b = p.patched.get(i).map(String::as_str).unwrap_or("");
                let changed = a != b;
                let addr = b.get(..8).or_else(|| a.get(..8)).unwrap_or("");
                ui.label(theme::mono(addr.to_string()));
                ui.label(theme::mono(body(a)).color(if changed { theme::ERR } else { theme::TEXT_DIM }));
                ui.label(theme::mono(body(b)).color(if changed { theme::OK } else { theme::TEXT_DIM }));
                ui.end_row();
            }
        });
    });
}

fn edit_view(app: &mut ViewerApp, ui: &mut egui::Ui, func: &crate::data::code::Function, version: &str) {
    let busy = app.panels.code.job.running();
    if app.panels.code.edit_for != Some(func.address) {
        if !busy {
            start_job(app, "load-edit", vec!["show".into(), func.addr_hex()], None);
        }
        ui.label(theme::faint_label("loading the listing\u{2026}"));
        return;
    }
    ui.horizontal(|ui| {
        if ui
            .add_enabled(!busy, theme::filled_button("Assemble & save to mod", theme::ACCENT))
            .on_hover_text("Assembles the listing at this address (it must fit in the function and be ARMv6K-only) into mod/code/code.bin")
            .clicked()
        {
            let text = app.panels.code.edit.clone();
            start_job(app, "apply", vec!["apply".into(), func.addr_hex(), "--asm".into(), "-".into()], Some(text));
        }
        if ui
            .add_enabled(!busy, egui::Button::new(format!("Revert to {version}")))
            .on_hover_text("Puts the active game version's bytes back for this function")
            .clicked()
        {
            start_job(app, "revert", vec!["revert".into(), func.addr_hex()], None);
        }
        if ui.add_enabled(!busy, egui::Button::new("Reload")).clicked() {
            app.panels.code.edit_for = None;
        }
        if busy {
            ui.spinner();
        }
        let msg = app.panels.code.message.clone();
        if !msg.is_empty() {
            let ok = app.panels.code.job.last.as_ref().map(|r| r.ok).unwrap_or(true);
            ui.label(egui::RichText::new(msg).color(if ok { theme::OK } else { theme::ERR }));
        }
    });
    ui.label(theme::faint_label(
        "One instruction per line; the address and bytes columns are ignored. Branch targets are absolute (bl #0x724a00). Comments start with ; or @.",
    ));
    egui::ScrollArea::vertical().id_salt("code_edit").auto_shrink([false, false]).show(ui, |ui| {
        ui.add(
            egui::TextEdit::multiline(&mut app.panels.code.edit)
                .font(egui::TextStyle::Monospace)
                .code_editor()
                .desired_width(f32::INFINITY)
                .desired_rows(30),
        );
    });
}

fn sources_tab(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        let groups: Vec<String> = app
            .panels
            .code
            .groups
            .iter()
            .map(|(name, files)| format!("{name}  ({})", files.len()))
            .collect();
        for (index, label) in groups.iter().enumerate() {
            if ui
                .selectable_label(app.panels.code.group == index, label)
                .clicked()
            {
                app.panels.code.group = index;
                app.panels.code.file_page = 0;
                app.panels.code.file_selected = None;
                app.panels.code.file_text = TextState::default();
            }
        }
    });
    ui.separator();
    let files = app
        .panels
        .code
        .groups
        .get(app.panels.code.group)
        .map(|(_, files)| files.clone())
        .unwrap_or_default();
    egui::Panel::left("code_files")
        .exact_size(330.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(6)))
        .show(ui, |ui| {
            let selected = app.panels.code.file_selected;
            let mut clicked = None;
            pager(ui, &mut app.panels.code.file_page, files.len());
            let start = (app.panels.code.file_page * PAGE).min(files.len());
            let end = (start + PAGE).min(files.len());
            egui::ScrollArea::vertical()
                .id_salt("code_files_scroll")
                .auto_shrink([false, false])
                .show_rows(ui, 17.0, end - start, |ui, range| {
                    for row in range.start + start..range.end + start {
                        let (rel, _, size) = &files[row];
                        let text = egui::RichText::new(format!(
                            "{:<44} {:>9}",
                            crate::utils::elide(rel, 44),
                            human_size(*size)
                        ))
                        .monospace()
                        .size(11.0);
                        if ui.selectable_label(selected == Some(row), text).clicked() {
                            clicked = Some(row);
                        }
                    }
                });
            if let Some(row) = clicked {
                app.panels.code.file_selected = Some(row);
                app.panels.code.file_text = TextState::default();
            }
        });
    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(6)))
        .show(ui, |ui| {
            let Some(row) = app.panels.code.file_selected else {
                ui.label(theme::faint_label("Select a file."));
                return;
            };
            let Some((rel, path, size)) = files.get(row).cloned() else { return };
            if app.panels.code.file_text.lines.is_empty() {
                let text = crate::utils::read_text(&path).unwrap_or_else(|e| format!("// {e}"));
                let mut state = TextState::default();
                state.set(&text, Lang::from_ext(path.extension().and_then(|e| e.to_str()).unwrap_or("")));
                app.panels.code.file_text = state;
            }
            ui.horizontal(|ui| {
                ui.label(theme::heading(
                    path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default(),
                ));
                ui.label(theme::dim_label(format!(
                    "{}  \u{b7}  {} lines  \u{b7}  {}",
                    rel,
                    human_count(app.panels.code.file_text.lines.len()),
                    human_size(size)
                )));
                if ui.button("Copy path").clicked() {
                    ui.ctx().copy_text(path.to_string_lossy().into_owned());
                }
            });
            ui.separator();
            let state = std::mem::take(&mut app.panels.code.file_text);
            crate::ui::text_view(ui, "code_file", &state, true);
            app.panels.code.file_text = state;
        });
}

/// decomp/ghidra/<rel> -> decomp/readable/<rel> when the readable view exists.
fn readable_path(dirs: &crate::utils::Dirs, file: &std::path::Path) -> Option<std::path::PathBuf> {
    let rel = file.strip_prefix(dirs.decomp.join("ghidra")).ok()?;
    let path = dirs.decomp.join("readable").join(rel);
    path.is_file().then_some(path)
}

/// "< Prev  page 3 / 73  Next >" for a list of `total` rows; returns true on change.
pub fn pager(ui: &mut egui::Ui, page: &mut usize, total: usize) -> bool {
    let pages = total.div_ceil(PAGE).max(1);
    if *page >= pages {
        *page = pages - 1;
    }
    let before = *page;
    ui.horizontal(|ui| {
        if ui.add_enabled(*page > 0, egui::Button::new("\u{2190} Prev")).clicked() {
            *page -= 1;
        }
        ui.label(theme::dim_label(format!("page {} / {}", *page + 1, pages)));
        if ui.add_enabled(*page + 1 < pages, egui::Button::new("Next \u{2192}")).clicked() {
            *page += 1;
        }
        let first = (*page * PAGE).min(total);
        ui.label(theme::faint_label(format!(
            "{}\u{2013}{} of {}",
            if total == 0 { 0 } else { first + 1 },
            (first + PAGE).min(total),
            human_count(total)
        )));
    });
    *page != before
}
