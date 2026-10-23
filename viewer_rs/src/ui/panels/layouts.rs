//! UI layout browser: BFLYT pane preview + panes table + raw JSON.

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::utils::{human_count, human_size};
use crate::ui::{Lang, TextState};

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    Preview,
    Panes,
    Raw,
}

#[derive(Clone)]
struct PaneBox {
    name: String,
    kind: String,
    x0: f32,
    y0: f32,
    x1: f32,
    y1: f32,
    text: String,
}

pub struct LayoutsPanel {
    pub query: String,
    pub pack: Option<String>,
    kind: Option<String>,
    list: Vec<usize>,
    pub selected: Option<usize>,
    dirty: bool,
    request: Option<String>,
    show_textures: bool,
    show_labels: bool,
    y_up: Option<bool>,
    zoom: f32,
    offset: egui::Vec2,
    fit: bool,
    json: Option<serde_json::Value>,
    raw: TextState,
    tab: Tab,
}

impl Default for LayoutsPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            pack: None,
            kind: None,
            list: Vec::new(),
            selected: None,
            dirty: true,
            request: None,
            show_textures: true,
            show_labels: true,
            y_up: None,
            zoom: 1.0,
            offset: egui::Vec2::ZERO,
            fit: true,
            json: None,
            raw: TextState::default(),
            tab: Tab::Preview,
        }
    }
}

impl LayoutsPanel {
    pub fn request(&mut self, query: &str) {
        self.request = Some(query.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.pack = None;
        self.kind = None;
        self.dirty = true;
    }

    fn select_layout(app: &mut ViewerApp, index: usize) {
        let path = app
            .data
            .as_deref()
            .and_then(|d| d.layouts.items.get(index))
            .map(|l| l.path.clone());
        let json = match (&path, app.data.as_mut()) {
            (Some(path), Some(data)) => data.layouts.load(path),
            _ => None,
        };
        let panel = &mut app.panels.layouts;
        panel.selected = Some(index);
        panel.fit = true;
        panel.offset = egui::Vec2::ZERO;
        if let Some(json) = &json {
            let pretty = serde_json::to_string_pretty(json).unwrap_or_default();
            panel.raw.set(&pretty, Lang::Json);
        }
        panel.json = json;
    }
}

fn select_layout(app: &mut ViewerApp, index: usize) {
    LayoutsPanel::select_layout(app, index)
}

// -- BFLYT pane geometry (ported from the Python viewer) ---------------------
fn pane_box(pane: &serde_json::Value, y_up: bool) -> (f32, f32, f32, f32) {
    let num = |key: &str, index: usize, default: f32| -> f32 {
        pane.get(key)
            .and_then(|v| v.as_array())
            .and_then(|a| a.get(index))
            .and_then(|v| v.as_f64())
            .map(|v| v as f32)
            .unwrap_or(default)
    };
    let x = num("translate", 0, 0.0);
    let y = num("translate", 1, 0.0);
    let w = num("size", 0, 0.0);
    let h = num("size", 1, 0.0);
    if y_up {
        (x, y - h, x + w, y)
    } else {
        (x, y, x + w, y + h)
    }
}

fn fit_error(boxes: &[(f32, f32, f32, f32)], w: f32, h: f32) -> f32 {
    if boxes.is_empty() || w <= 0.0 || h <= 0.0 {
        return 0.0;
    }
    let xs0 = boxes.iter().map(|b| b.0).fold(f32::MAX, f32::min);
    let ys0 = boxes.iter().map(|b| b.1).fold(f32::MAX, f32::min);
    let xs1 = boxes.iter().map(|b| b.2).fold(f32::MIN, f32::max);
    let ys1 = boxes.iter().map(|b| b.3).fold(f32::MIN, f32::max);
    let (bw, bh) = (xs1 - xs0, ys1 - ys0);
    if bw <= 0.0 || bh <= 0.0 {
        return 0.0;
    }
    let aspect_err = ((bw / bh) - (w / h)).abs() / (w / h);
    let overflow = (bw - w).max(0.0) / w + (bh - h).max(0.0) / h;
    aspect_err + overflow
}

fn choose_y_up(panes: &[serde_json::Value], w: f32, h: f32) -> bool {
    let up: Vec<_> = panes.iter().map(|p| pane_box(p, true)).collect();
    let down: Vec<_> = panes.iter().map(|p| pane_box(p, false)).collect();
    fit_error(&up, w, h) <= fit_error(&down, w, h)
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if !app.data().is_some_and(|d| d.layouts.ready) {
        ui.label(theme::dim_label("indexing layout files\u{2026}"));
        return;
    }
    if let Some(query) = app.panels.layouts.request.take() {
        app.panels.layouts.query = query;
        app.panels.layouts.dirty = true;
    }
    if app.panels.layouts.dirty {
        if let Some(data) = app.data.as_deref() {
            let panel = &mut app.panels.layouts;
            panel.list = data.layouts.search(
                &panel.query,
                panel.pack.as_deref(),
                panel.kind.as_deref(),
            );
            panel.dirty = false;
            if let Some(name) = panel.request.take() {
                if let Some(index) = panel
                    .list
                    .iter()
                    .copied()
                    .find(|i| data.layouts.items[*i].stem.contains(&name))
                {
                    panel.selected = Some(index);
                    let path = data.layouts.items[index].path.clone();
                    if let Some(data) = app.data.as_mut() {
                        app.panels.layouts.json = data.layouts.load(&path);
                    }
                    if let Some(json) = &app.panels.layouts.json {
                        let pretty = serde_json::to_string_pretty(json).unwrap_or_default();
                        app.panels.layouts.raw.set(&pretty, Lang::Json);
                    }
                }
            }
        }
    }

    egui::Panel::left("layout_list")
        .exact_size(330.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Layout packs"));
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.layouts.query)
                        .hint_text("Search layouts\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.layouts.dirty = true;
            }
            let packs: Vec<(String, usize)> = app
                .data
                .as_deref()
                .map(|d| d.layouts.packs().to_vec())
                .unwrap_or_default();
            let label = app
                .panels
                .layouts
                .pack
                .clone()
                .unwrap_or_else(|| "All packs".into());
            egui::ComboBox::from_id_salt("layout_pack")
                .selected_text(crate::utils::elide(&label, 30))
                .width(f32::INFINITY)
                .show_ui(ui, |ui| {
                    if ui.selectable_label(app.panels.layouts.pack.is_none(), "All packs").clicked() {
                        app.panels.layouts.pack = None;
                        app.panels.layouts.dirty = true;
                    }
                    for (name, count) in packs {
                        let selected = app.panels.layouts.pack.as_deref() == Some(name.as_str());
                        if ui.selectable_label(selected, format!("{name}  ({count})")).clicked() {
                            app.panels.layouts.pack = Some(name);
                            app.panels.layouts.dirty = true;
                        }
                    }
                });
            ui.horizontal(|ui| {
                for (label, value) in [("all", None), ("layout", Some("layout")), ("anim", Some("anim"))] {
                    let selected = app.panels.layouts.kind.as_deref() == value;
                    if ui.selectable_label(selected, label).clicked() {
                        app.panels.layouts.kind = value.map(|v| v.to_string());
                        app.panels.layouts.dirty = true;
                    }
                }
                ui.label(theme::faint_label(format!(
                    "{} files",
                    human_count(app.panels.layouts.list.len())
                )));
            });
            ui.separator();
            let list = app.panels.layouts.list.clone();
            let selected = app.panels.layouts.selected;
            let mut clicked = None;
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("layout_scroll")
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::remainder().at_least(120.0))
                .column(Column::exact(60.0))
                .column(Column::exact(80.0))
                .header(20.0, |mut header| {
                    for title in ["File", "Kind", "Size"] {
                        header.col(|ui| {
                            ui.label(theme::faint_label(title));
                        });
                    }
                })
                .body(|body| {
                    body.rows(18.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let Some(item) = app.data.as_deref().and_then(|d| d.layouts.items.get(index))
                        else {
                            return;
                        };
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            ui.label(egui::RichText::new(item.stem.clone()).size(12.0));
                        });
                        row.col(|ui| {
                            ui.label(theme::dim_label(item.kind.clone()));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(human_size(item.size)));
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(index) = clicked {
                select_layout(app, index);
            }
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let info = app
                .panels
                .layouts
                .selected
                .and_then(|i| app.data.as_deref().and_then(|d| d.layouts.items.get(i)))
                .map(|l| (l.stem.clone(), l.pack.clone(), l.kind.clone(), l.size));
            let Some((stem, pack, kind, size)) = info else {
                ui.label(theme::faint_label("Select a layout file."));
                return;
            };
            ui.horizontal(|ui| {
                ui.label(theme::heading(stem.clone()));
                ui.label(theme::dim_label(format!("{pack}  \u{b7}  {kind}  \u{b7}  {}", human_size(size))));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    for (label, tab) in [("Raw JSON", Tab::Raw), ("Panes", Tab::Panes), ("Preview", Tab::Preview)] {
                        if ui.selectable_label(app.panels.layouts.tab == tab, label).clicked() {
                            app.panels.layouts.tab = tab;
                        }
                    }
                });
            });
            ui.separator();
            match app.panels.layouts.tab {
                Tab::Preview => preview(app, ui),
                Tab::Panes => panes_table(app, ui),
                Tab::Raw => {
                    let state = std::mem::take(&mut app.panels.layouts.raw);
                    crate::ui::text_view(ui, "layout_raw", &state, false);
                    app.panels.layouts.raw = state;
                }
            }
        });
}

fn panes_table(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let boxes = build_boxes(app);
    if boxes.is_empty() {
        let names = harvest_anim_targets(app);
        if names.is_empty() {
            ui.label(theme::faint_label("No pane data in this file."));
        } else {
            ui.label(theme::faint_label("BFLAN animation targets (from binary payloads)"));
            for name in names {
                ui.label(theme::mono(name));
            }
        }
        return;
    }
    egui::ScrollArea::vertical()
        .id_salt("layout_panes")
        .auto_shrink([false, false])
        .show_rows(ui, 18.0, boxes.len(), |ui, range| {
            for row in range {
                let pane = &boxes[row];
                ui.label(
                    egui::RichText::new(format!(
                        "{:<26} {:<7} {:>8.0},{:<8.0} {:>7.0} x {:<7.0} {}",
                        crate::utils::elide(&pane.name, 26),
                        pane.kind,
                        pane.x0,
                        pane.y0,
                        pane.x1 - pane.x0,
                        pane.y1 - pane.y0,
                        crate::utils::elide(&pane.text, 40)
                    ))
                    .monospace()
                    .size(11.5)
                    .color(theme::TEXT),
                );
            }
        });
}

fn build_boxes(app: &ViewerApp) -> Vec<PaneBox> {
    let Some(json) = app.panels.layouts.json.as_ref() else {
        return Vec::new();
    };
    let Some(panes) = json.get("panes").and_then(|v| v.as_array()) else {
        return Vec::new();
    };
    let y_up = app.panels.layouts.y_up.unwrap_or(true);
    panes
        .iter()
        .filter_map(|pane| {
            let name = pane.get("name").and_then(|v| v.as_str()).unwrap_or("(unnamed)").to_string();
            let kind = pane.get("type").and_then(|v| v.as_str()).unwrap_or("?").to_string();
            let (x0, y0, x1, y1) = pane_box(pane, y_up);
            Some(PaneBox {
                name,
                kind,
                x0,
                y0,
                x1,
                y1,
                text: pane
                    .get("text")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string(),
            })
        })
        .collect()
}

fn harvest_anim_targets(app: &ViewerApp) -> Vec<String> {
    let Some(json) = app.panels.layouts.json.as_ref() else {
        return Vec::new();
    };
    let Some(sections) = json.get("raw_sections").and_then(|v| v.as_array()) else {
        return Vec::new();
    };
    let mut out: Vec<String> = Vec::new();
    for section in sections {
        let Some(hex) = section.get("payload_hex").and_then(|v| v.as_str()) else {
            continue;
        };
        let bytes: Vec<u8> = (0..hex.len() / 2)
            .filter_map(|i| u8::from_str_radix(&hex[i * 2..i * 2 + 2], 16).ok())
            .collect();
        let mut current = String::new();
        for byte in bytes {
            if (0x20..0x7f).contains(&byte) {
                current.push(byte as char);
            } else {
                if current.len() >= 3 && !out.contains(&current) && !current.chars().all(|c| c.is_ascii_digit()) {
                    out.push(current.clone());
                }
                current.clear();
            }
        }
        if out.len() > 40 {
            break;
        }
    }
    out
}

fn preview(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.checkbox(&mut app.panels.layouts.show_textures, "Show textures");
        ui.checkbox(&mut app.panels.layouts.show_labels, "Pane labels");
        ui.label(theme::faint_label("Orientation:"));
        for (label, value) in [("auto", None), ("y-up", Some(true)), ("y-down", Some(false))] {
            if ui
                .selectable_label(app.panels.layouts.y_up == value, label)
                .clicked()
            {
                app.panels.layouts.y_up = value;
            }
        }
        if ui.button("Fit").clicked() {
            app.panels.layouts.fit = true;
            app.panels.layouts.offset = egui::Vec2::ZERO;
        }
    });
    let boxes = build_boxes(app);
    let (lw, lh) = app
        .panels
        .layouts
        .json
        .as_ref()
        .and_then(|j| j.get("layout"))
        .map(|l| {
            (
                l.get("width").and_then(|v| v.as_f64()).unwrap_or(320.0) as f32,
                l.get("height").and_then(|v| v.as_f64()).unwrap_or(240.0) as f32,
            )
        })
        .unwrap_or((320.0, 240.0));
    if !boxes.is_empty() && app.panels.layouts.y_up.is_none() {
        if let Some(panes) = app
            .panels
            .layouts
            .json
            .as_ref()
            .and_then(|j| j.get("panes"))
            .and_then(|v| v.as_array())
        {
            app.panels.layouts.y_up = Some(choose_y_up(panes, lw, lh));
        }
    }

    let size = ui.available_size();
    let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click_and_drag());
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 0.0, theme::BG_INPUT);
    let bounds = if boxes.is_empty() {
        (0.0, 0.0, lw, lh)
    } else {
        (
            boxes.iter().map(|b| b.x0).fold(f32::MAX, f32::min),
            boxes.iter().map(|b| b.y0).fold(f32::MAX, f32::min),
            boxes.iter().map(|b| b.x1).fold(f32::MIN, f32::max),
            boxes.iter().map(|b| b.y1).fold(f32::MIN, f32::max),
        )
    };
    let bw = (bounds.2 - bounds.0).max(1.0);
    let bh = (bounds.3 - bounds.1).max(1.0);
    if app.panels.layouts.fit {
        let scale = ((rect.width() - 24.0) / bw).min((rect.height() - 24.0) / bh);
        app.panels.layouts.zoom = scale.max(0.01);
    }
    if response.dragged() {
        app.panels.layouts.offset += response.drag_delta();
        app.panels.layouts.fit = false;
    }
    if response.hovered() {
        let scroll = ui.input(|i| i.smooth_scroll_delta.y);
        if scroll != 0.0 {
            let factor = if scroll > 0.0 { 1.1 } else { 1.0 / 1.1 };
            app.panels.layouts.zoom = (app.panels.layouts.zoom * factor).clamp(0.02, 8.0);
            app.panels.layouts.fit = false;
        }
    }
    let scale = app.panels.layouts.zoom;
    let origin = rect.center() + app.panels.layouts.offset
        - egui::vec2(bw * scale * 0.5, bh * scale * 0.5)
        - egui::vec2(bounds.0 * scale, bounds.1 * scale);
    let to_screen = |x: f32, y: f32| origin + egui::vec2(x * scale, y * scale);
    painter.rect_stroke(
        egui::Rect::from_min_max(to_screen(bounds.0, bounds.1), to_screen(bounds.2, bounds.3)),
        0.0,
        egui::Stroke::new(1.0, theme::BORDER_LIGHT),
        egui::StrokeKind::Outside,
    );
    for pane in &boxes {
        let pane_rect = egui::Rect::from_min_max(
            to_screen(pane.x0, pane.y0),
            to_screen(pane.x1, pane.y1),
        );
        let color = match pane.kind.as_str() {
            "pic1" => theme::COL_STRING,
            "txt1" => theme::ACCENT,
            "wnd1" => theme::COL_KEYWORD,
            "pan1" => theme::INFO,
            _ => theme::COL_PUNCT,
        };
        painter.rect_filled(pane_rect, 0.0, color.gamma_multiply(0.12));
        painter.rect_stroke(pane_rect, 0.0, egui::Stroke::new(1.0, color.gamma_multiply(0.7)), egui::StrokeKind::Inside);
        if app.panels.layouts.show_textures && pane.kind == "pic1" {
            if let Some(path) = resolve_texture(app, &pane.name) {
                if let Some(handle) = app.layout_tex.get(ui.ctx(), &app.pool, &path) {
                    painter.image(
                        handle.id(),
                        pane_rect,
                        egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(1.0, 1.0)),
                        egui::Color32::WHITE,
                    );
                }
            }
        }
        if !pane.text.is_empty() {
            painter.text(
                pane_rect.left_top() + egui::vec2(3.0, 3.0),
                egui::Align2::LEFT_TOP,
                crate::utils::elide(&pane.text, 40),
                egui::FontId::proportional(12.0),
                theme::JP_TEXT,
            );
        } else if app.panels.layouts.show_labels {
            painter.text(
                pane_rect.left_top() + egui::vec2(3.0, 3.0),
                egui::Align2::LEFT_TOP,
                crate::utils::elide(&pane.name, 24),
                egui::FontId::proportional(11.0),
                theme::TEXT_DIM,
            );
        }
    }
}

fn resolve_texture(app: &ViewerApp, pane_name: &str) -> Option<std::path::PathBuf> {
    let data = app.data.as_deref()?;
    let json = app.panels.layouts.json.as_ref()?;
    let name = pane_name.to_lowercase();
    let textures: Vec<String> = json
        .get("textures")
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default();
    let mut candidates: Vec<&String> = textures.iter().filter(|t| t.to_lowercase().starts_with(&name)).collect();
    if candidates.is_empty() {
        candidates = textures.iter().filter(|t| t.to_lowercase().contains(&name)).collect();
    }
    for candidate in candidates {
        if let Some(tex) = data.textures.resolve(candidate) {
            return Some(tex.path.clone());
        }
    }
    None
}


