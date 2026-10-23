//! Texture browser with a virtualised thumbnail grid.

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::ui::ImagePaneState;
use crate::utils::{human_count, human_size};

#[derive(Clone, Copy, PartialEq, Eq)]
enum SortKey {
    Name,
    Size,
    Pixels,
}

pub struct TexturesPanel {
    pub query: String,
    pub pack: Option<String>,
    sort: SortKey,
    sort_desc: bool,
    pub thumb_size: f32,
    list: Vec<usize>,
    pub selected: Option<usize>,
    dirty: bool,
    request: Option<(String, Option<String>)>,
    pane: ImagePaneState,
}

impl Default for TexturesPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            pack: None,
            sort: SortKey::Name,
            sort_desc: false,
            thumb_size: 148.0,
            list: Vec::new(),
            selected: None,
            dirty: true,
            request: None,
            pane: ImagePaneState::default(),
        }
    }
}

impl TexturesPanel {
    pub fn request(&mut self, query: &str, pack: Option<&str>) {
        self.request = Some((query.to_string(), pack.map(|p| p.to_string())));
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.pack = None;
        self.sort = SortKey::Name;
        self.sort_desc = false;
        self.dirty = true;
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if !app.data().is_some_and(|d| d.textures.ready) {
        ui.label(theme::dim_label("indexing textures\u{2026}"));
        return;
    }
    if let Some((query, pack)) = app.panels.textures.request.take() {
        app.panels.textures.query = query;
        app.panels.textures.pack = pack;
        app.panels.textures.dirty = true;
    }
    if app.panels.textures.dirty {
        if let Some(data) = app.data.as_deref() {
            let panel = &mut app.panels.textures;
            panel.list = data.textures.search(&panel.query, panel.pack.as_deref(), None);
            let desc = panel.sort_desc;
            panel.list.sort_by(|a, b| {
                let ta = &data.textures.items[*a];
                let tb = &data.textures.items[*b];
                let ord = match panel.sort {
                    SortKey::Name => ta.name.to_lowercase().cmp(&tb.name.to_lowercase()),
                    SortKey::Size => ta.size.cmp(&tb.size),
                    SortKey::Pixels => {
                        let pa = ta.width.unwrap_or(0) as u64 * ta.height.unwrap_or(0) as u64;
                        let pb = tb.width.unwrap_or(0) as u64 * tb.height.unwrap_or(0) as u64;
                        pa.cmp(&pb)
                    }
                };
                if desc { ord.reverse() } else { ord }
            });
            panel.dirty = false;
        }
    }

    egui::Panel::left("texture_filters")
        .exact_size(286.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Texture library"));
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.textures.query)
                        .hint_text("Search textures\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.textures.dirty = true;
            }
            let packs: Vec<(String, usize)> = app
                .data
                .as_deref()
                .map(|d| d.textures.packs().to_vec())
                .unwrap_or_default();
            let label = app
                .panels
                .textures
                .pack
                .clone()
                .unwrap_or_else(|| "All packs".into());
            egui::ComboBox::from_id_salt("texture_pack")
                .selected_text(crate::utils::elide(&label, 30))
                .width(f32::INFINITY)
                .show_ui(ui, |ui| {
                    if ui.selectable_label(app.panels.textures.pack.is_none(), "All packs").clicked() {
                        app.panels.textures.pack = None;
                        app.panels.textures.dirty = true;
                    }
                    for (name, count) in packs {
                        let selected = app.panels.textures.pack.as_deref() == Some(name.as_str());
                        if ui.selectable_label(selected, format!("{name}  ({count})")).clicked() {
                            app.panels.textures.pack = Some(name);
                            app.panels.textures.dirty = true;
                        }
                    }
                });
            ui.horizontal(|ui| {
                egui::ComboBox::from_id_salt("texture_sort")
                    .selected_text(match app.panels.textures.sort {
                        SortKey::Name => "Sort: name",
                        SortKey::Size => "Sort: size",
                        SortKey::Pixels => "Sort: pixels",
                    })
                    .show_ui(ui, |ui| {
                        for (key, label) in [(SortKey::Name, "Name"), (SortKey::Size, "Size"), (SortKey::Pixels, "Pixels")] {
                            if ui.selectable_label(app.panels.textures.sort == key, label).clicked() {
                                app.panels.textures.sort = key;
                                app.panels.textures.dirty = true;
                            }
                        }
                    });
                if ui.button(if app.panels.textures.sort_desc { "Descending" } else { "Ascending" }).clicked() {
                    app.panels.textures.sort_desc = !app.panels.textures.sort_desc;
                    app.panels.textures.dirty = true;
                }
            });
            ui.horizontal(|ui| {
                ui.label(theme::faint_label("Thumb"));
                for size in [112.0f32, 148.0, 200.0, 256.0] {
                    let selected = (app.panels.textures.thumb_size - size).abs() < 1.0;
                    if ui.selectable_label(selected, format!("{}", size as i32)).clicked() {
                        app.panels.textures.thumb_size = size;
                    }
                }
            });
            let total = app.data.as_deref().map(|d| d.textures.total_bytes).unwrap_or(0);
            let failure = app
                .thumbs
                .failures
                .values()
                .next()
                .map(|e| format!("  \u{b7}  thumb error: {}", crate::utils::elide(e, 60)))
                .unwrap_or_default();
            ui.label(theme::faint_label(format!(
                "{} shown \u{b7} {} total \u{b7} {} cached \u{b7} {} pending{}",
                human_count(app.panels.textures.list.len()),
                human_size(total),
                human_count(app.thumbs.ready),
                human_count(app.thumbs.queued),
                failure
            )));
            if app.thumbs.is_pending() {
                ui.ctx().request_repaint_after(std::time::Duration::from_millis(100));
            }
            ui.separator();
            ui.label(theme::faint_label(
                "Thumbnails decode on worker threads and are cached to disk, so scrolling stays smooth.",
            ));
        });

    egui::Panel::right("texture_preview")
        .default_size(430.0)
        .resizable(true)
        .size_range(240.0..=760.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let texture = app
                .panels
                .textures
                .selected
                .and_then(|i| app.data.as_deref().map(|d| d.textures.items[i].clone()));
            let Some(tex) = texture else {
                ui.label(theme::faint_label("Select a texture to preview it."));
                return;
            };
            ui.label(theme::heading(tex.name.clone()));
            ui.label(theme::faint_label(tex.rel.clone()));
            ui.add_space(4.0);
            let handle = app.thumbs.get(ui.ctx(), &app.pool, &tex.path);
            match handle {
                Some(handle) => {
                    crate::ui::image_pane(ui, &handle, &mut app.panels.textures.pane, theme::BG_INPUT);
                }
                None => {
                    ui.allocate_space(egui::vec2(ui.available_width(), 180.0));
                    ui.ctx().request_repaint_after(std::time::Duration::from_millis(80));
                }
            }
            ui.add_space(6.0);
            let rows: Vec<(&str, String)> = vec![
                ("pack", tex.pack.clone()),
                ("resolution", tex.dims()),
                ("format", tex.format.clone()),
                ("file size", human_size(tex.size)),
                ("bflim size", tex.bflim_size.map(human_size).unwrap_or_else(|| "-".into())),
                ("alignment", tex.alignment.map(|v| v.to_string()).unwrap_or_else(|| "-".into())),
                ("flags", tex.flags.map(|v| v.to_string()).unwrap_or_else(|| "-".into())),
            ];
            crate::ui::kv_rows(ui, &rows);
            ui.horizontal(|ui| {
                if ui.button("Open externally").clicked() {
                    let _ = std::process::Command::new("cmd")
                        .args(["/C", "start", ""])
                        .arg(&tex.path)
                        .spawn();
                }
                if ui.button("Copy path").clicked() {
                    ui.ctx().copy_text(tex.path.to_string_lossy().into_owned());
                }
                if ui.button("Fit").clicked() {
                    app.panels.textures.pane.fit = true;
                }
            });
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let list = app.panels.textures.list.clone();
            let cell = egui::vec2(app.panels.textures.thumb_size, app.panels.textures.thumb_size);
            let selected = app.panels.textures.selected;
            let spacing = 8.0;
            let columns = ((ui.available_width() + spacing) / (cell.x + spacing)).floor().max(1.0) as usize;
            let rows = list.len().div_ceil(columns);
            let row_height = cell.y + spacing + 18.0;
            let mut clicked: Option<usize> = None;
            egui::ScrollArea::vertical()
                .id_salt("texture_grid")
                .auto_shrink([false, false])
                .show_rows(ui, row_height, rows, |ui, range| {
                    for row in range {
                        ui.horizontal(|ui| {
                            for column in 0..columns {
                                let i = row * columns + column;
                                if i >= list.len() {
                                    break;
                                }
                                let index = list[i];
                                let (rect, response) = ui.allocate_exact_size(cell, egui::Sense::click());
                                let painter = ui.painter_at(rect);
                                painter.rect_filled(rect, 2.0, theme::BG_INPUT);
                                let path = app
                                    .data
                                    .as_deref()
                                    .and_then(|d| d.textures.items.get(index))
                                    .map(|t| t.path.clone());
                                let name = app
                                    .data
                                    .as_deref()
                                    .and_then(|d| d.textures.items.get(index))
                                    .map(|t| t.name.clone())
                                    .unwrap_or_default();
                                if let Some(path) = &path {
                                    if let Some(handle) = app.thumbs.get(ui.ctx(), &app.pool, path) {
                                        let tex_size = handle.size_vec2();
                                        let scale = (rect.width() / tex_size.x.max(1.0))
                                            .min(rect.height() / tex_size.y.max(1.0));
                                        let image_rect =
                                            egui::Rect::from_center_size(rect.center(), tex_size * scale);
                                        painter.image(
                                            handle.id(),
                                            image_rect,
                                            egui::Rect::from_min_max(
                                                egui::pos2(0.0, 0.0),
                                                egui::pos2(1.0, 1.0),
                                            ),
                                            egui::Color32::WHITE,
                                        );
                                    } else {
                                        painter.text(
                                            rect.center(),
                                            egui::Align2::CENTER_CENTER,
                                            "\u{2026}",
                                            egui::FontId::proportional(16.0),
                                            theme::TEXT_FAINT,
                                        );
                                        ui.ctx()
                                            .request_repaint_after(std::time::Duration::from_millis(60));
                                    }
                                }
                                painter.rect_stroke(
                                    rect,
                                    2.0,
                                    egui::Stroke::new(
                                        2.0,
                                        if selected == Some(index) { theme::ACCENT } else { theme::BG_PANEL },
                                    ),
                                    egui::StrokeKind::Inside,
                                );
                                painter.text(
                                    rect.left_bottom() + egui::vec2(2.0, 2.0),
                                    egui::Align2::LEFT_TOP,
                                    crate::utils::elide(&name, 26),
                                    egui::FontId::proportional(11.0),
                                    if selected == Some(index) { theme::TEXT } else { theme::TEXT_DIM },
                                );
                                if response.clicked() {
                                    clicked = Some(index);
                                }
                            }
                        });
                    }
                });
            if let Some(index) = clicked {
                app.panels.textures.selected = Some(index);
                app.panels.textures.pane.fit = true;
                app.status = format!(
                    "{} selected",
                    app.data
                        .as_deref()
                        .and_then(|d| d.textures.items.get(index))
                        .map(|t| t.name.clone())
                        .unwrap_or_default()
                );
            }
        });
}

