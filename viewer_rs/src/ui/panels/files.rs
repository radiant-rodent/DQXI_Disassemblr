//! Raw-file browser for the exact extracted RomFS tree.

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::utils::{human_count, human_size, read_text};

#[derive(Clone, Copy, PartialEq, Eq)]
enum SortKey {
    Path,
    Size,
}

impl Default for SortKey {
    fn default() -> Self { Self::Path }
}

#[derive(Default)]
pub struct FilesPanel {
    pub query: String,
    pub kind: Option<String>,
    sort: SortKey,
    sort_desc: bool,
    selected: Option<usize>,
    list: Vec<usize>,
    dirty: bool,
    preview: crate::ui::TextState,
    preview_path: Option<std::path::PathBuf>,
}

impl FilesPanel {
    pub fn reset(&mut self) {
        self.query.clear();
        self.kind = None;
        self.sort = SortKey::Path;
        self.sort_desc = false;
        self.dirty = true;
    }

    fn ensure_preview(&mut self, path: &std::path::Path) {
        if self.preview_path.as_deref() == Some(path) {
            return;
        }
        self.preview_path = Some(path.to_path_buf());
        let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("").to_lowercase();
        let text = match ext.as_str() {
            "json" | "md" | "txt" | "nut" | "s" | "c" | "h" | "py" | "ld" => {
                read_text(path).unwrap_or_else(|e| format!("// cannot read: {e}"))
            }
            _ => hex_preview(path),
        };
        self.preview.set(&text, crate::ui::Lang::Plain);
    }
}

fn hex_preview(path: &std::path::Path) -> String {
    let Ok(bytes) = std::fs::read(path) else {
        return "cannot read file".into();
    };
    let limit = bytes.len().min(16 * 1024);
    let mut out = format!("{} bytes\n\n", bytes.len());
    for (row, chunk) in bytes[..limit].chunks(16).enumerate() {
        let mut hex = String::new();
        let mut ascii = String::new();
        for b in chunk {
            hex.push_str(&format!("{b:02X} "));
            ascii.push(if (0x20..0x7F).contains(b) { *b as char } else { '.' });
        }
        out.push_str(&format!("{:08X}  {:<48}  {}\n", row * 16, hex, ascii));
    }
    if bytes.len() > limit {
        out.push_str("\n... preview truncated at 16 KiB ...\n");
    }
    out
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let Some(data) = app.data.as_deref() else {
        ui.label(theme::dim_label("indexing raw files…"));
        return;
    };
    if app.panels.files.dirty {
        app.panels.files.list = data.files.search(&app.panels.files.query, app.panels.files.kind.as_deref(), 5000);
        let desc = app.panels.files.sort_desc;
        let key = app.panels.files.sort;
        app.panels.files.list.sort_by(|a, b| {
            let fa = &data.files.items[*a];
            let fb = &data.files.items[*b];
            let ord = match key {
                SortKey::Path => fa.rel.to_lowercase().cmp(&fb.rel.to_lowercase()),
                SortKey::Size => fa.size.cmp(&fb.size),
            };
            if desc { ord.reverse() } else { ord }
        });
        app.panels.files.dirty = false;
        if app.panels.files.selected.is_none() {
            app.panels.files.selected = app.panels.files.list.first().copied();
        }
    }
    let kinds = data.files.kinds().to_vec();
    let total = data.files.items.len();

    egui::Panel::left("raw_files_list")
        .exact_size(430.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Raw game data"));
            ui.label(theme::faint_label(format!(
                "{} files · {}",
                human_count(total),
                human_size(data.files.total_bytes)
            )));
            if ui
                .add(egui::TextEdit::singleline(&mut app.panels.files.query).hint_text("Filter paths…"))
                .changed()
            {
                app.panels.files.dirty = true;
            }
            egui::ComboBox::from_id_salt("raw_kind")
                .selected_text(app.panels.files.kind.clone().unwrap_or_else(|| "All kinds".into()))
                .show_ui(ui, |ui| {
                    if ui.selectable_label(app.panels.files.kind.is_none(), "All kinds").clicked() {
                        app.panels.files.kind = None;
                        app.panels.files.dirty = true;
                    }
                    for (kind, count) in kinds {
                        if ui
                            .selectable_label(app.panels.files.kind.as_deref() == Some(kind.as_str()), format!("{kind} ({count})"))
                            .clicked()
                        {
                            app.panels.files.kind = Some(kind);
                            app.panels.files.dirty = true;
                        }
                    }
                });
            ui.separator();
            ui.horizontal(|ui| {
                egui::ComboBox::from_id_salt("raw_sort")
                    .selected_text(match app.panels.files.sort {
                        SortKey::Path => "Sort: path",
                        SortKey::Size => "Sort: size",
                    })
                    .show_ui(ui, |ui| {
                        for (key, label) in [(SortKey::Path, "Path"), (SortKey::Size, "Size")] {
                            if ui.selectable_label(app.panels.files.sort == key, label).clicked() {
                                app.panels.files.sort = key;
                                app.panels.files.dirty = true;
                            }
                        }
                    });
                if ui.button(if app.panels.files.sort_desc { "Descending" } else { "Ascending" }).clicked() {
                    app.panels.files.sort_desc = !app.panels.files.sort_desc;
                    app.panels.files.dirty = true;
                }
            });
            let list = app.panels.files.list.clone();
            let selected = app.panels.files.selected;
            let mut clicked = None;
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("raw_file_table")
                .striped(true)
                .sense(egui::Sense::click())
                .column(Column::remainder().at_least(160.0))
                .column(Column::exact(74.0))
                .header(20.0, |mut header| {
                    header.col(|ui| { ui.label(theme::faint_label("Path")); });
                    header.col(|ui| { ui.label(theme::faint_label("Size")); });
                })
                .body(|body| {
                    body.rows(17.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let f = &data.files.items[index];
                        row.set_selected(selected == Some(index));
                        row.col(|ui| { ui.label(egui::RichText::new(&f.rel).size(11.5)); });
                        row.col(|ui| { ui.label(theme::faint_label(human_size(f.size))); });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(i) = clicked {
                app.panels.files.selected = Some(i);
            }
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let Some(index) = app.panels.files.selected else {
                ui.label(theme::faint_label("Select a file."));
                return;
            };
            let Some(f) = data.files.items.get(index) else { return };
            ui.horizontal(|ui| {
                ui.label(theme::heading(f.rel.clone()));
                ui.label(theme::faint_label(format!("{} · {}", f.kind, human_size(f.size))));
                if ui.button("Reveal").clicked() {
                    let _ = std::process::Command::new("explorer")
                        .arg(format!("/select,{}", f.path.display()))
                        .spawn();
                }
                if ui.button("Copy path").clicked() {
                    ui.ctx().copy_text(f.path.display().to_string());
                }
            });
            ui.separator();
            let path = f.path.clone();
            app.panels.files.ensure_preview(&path);
            let state = std::mem::take(&mut app.panels.files.preview);
            crate::ui::text_view(ui, "raw_file_preview", &state, false);
            app.panels.files.preview = state;
        });
}
