//! UI layout browser: BFLYT pane preview + panes table + raw JSON.

use eframe::egui;

use crate::app::ViewerApp;
use crate::data::game_font::GameFont;
use crate::data::layout_scene;
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
    show_hidden: bool,
    clip: bool,
    /// Game fonts by layout font name (`2D9.bffnt`); None = not exported.
    fonts: std::collections::HashMap<String, Option<std::sync::Arc<GameFont>>>,
    /// Scene of the selected layout (selection index, scene).
    scene: Option<(Option<usize>, std::sync::Arc<layout_scene::Scene>)>,
    y_up: Option<bool>,
    zoom: f32,
    offset: egui::Vec2,
    fit: bool,
    json: Option<serde_json::Value>,
    /// the panes of the layout as loaded (baseline for revert and for the changed count)
    original: Option<serde_json::Value>,
    original_for: Option<usize>,
    undo: Vec<serde_json::Value>,
    redo: Vec<serde_json::Value>,
    selected_pane: Option<usize>,
    /// pane whose fields are being edited right now (one undo step per burst)
    edit_group: Option<usize>,
    pane_drag: bool,
    raw: TextState,
    tab: Tab,
    /// Export/Replace workflow state (JSON -> BFLYT/BFLAN -> SARC -> PACK).
    tools: crate::ui::asset_jobs::AssetTools,
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
            show_hidden: false,
            clip: true,
            fonts: Default::default(),
            scene: None,
            y_up: None,
            zoom: 1.0,
            offset: egui::Vec2::ZERO,
            fit: true,
            json: None,
            original: None,
            original_for: None,
            undo: Vec::new(),
            redo: Vec::new(),
            selected_pane: None,
            edit_group: None,
            pane_drag: false,
            raw: TextState::default(),
            tab: Tab::Preview,
            tools: Default::default(),
        }
    }
}

const PANE_KEYS: [&str; 5] = ["translate", "rotate", "scale", "size", "text"];

fn panes_of(doc: &serde_json::Value) -> &[serde_json::Value] {
    doc.get("panes").and_then(|v| v.as_array()).map(|v| v.as_slice()).unwrap_or(&[])
}

/// Indices of the panes whose editable fields differ from the loaded layout.
fn changed_panes(json: &serde_json::Value, original: &serde_json::Value) -> Vec<usize> {
    let (now, then) = (panes_of(json), panes_of(original));
    now.iter()
        .zip(then.iter())
        .enumerate()
        .filter(|(_, (a, b))| PANE_KEYS.iter().any(|k| a.get(*k) != b.get(*k)))
        .map(|(i, _)| i)
        .collect()
}

impl LayoutsPanel {
    /// The panes as loaded; captured the first time the layout is shown after loading.
    fn ensure_original(&mut self) {
        if self.original_for != self.selected || self.original.is_none() {
            self.original = self.json.clone();
            self.original_for = self.selected;
            self.undo.clear();
            self.redo.clear();
            self.selected_pane = None;
        }
    }

    pub fn edited_panes(&self) -> usize {
        match (&self.json, &self.original) {
            (Some(j), Some(o)) if self.original_for == self.selected => changed_panes(j, o).len(),
            _ => 0,
        }
    }

    pub fn name_of_selected_layout(&self, app_data: Option<&crate::app::Data>) -> String {
        self.selected
            .and_then(|i| app_data?.layouts.items.get(i))
            .map(|l| l.stem.clone())
            .unwrap_or_default()
    }

    fn snapshot(&mut self) {
        if let Some(json) = &self.json {
            self.undo.push(json.clone());
            if self.undo.len() > 60 {
                self.undo.remove(0);
            }
            self.redo.clear();
        }
    }

    pub fn undo_action(&mut self) {
        if let Some(prev) = self.undo.pop() {
            if let Some(cur) = self.json.take() {
                self.redo.push(cur);
            }
            self.json = Some(prev);
            self.scene = None;
        }
    }

    pub fn redo_action(&mut self) {
        if let Some(next) = self.redo.pop() {
            if let Some(cur) = self.json.take() {
                self.undo.push(cur);
            }
            self.json = Some(next);
            self.scene = None;
        }
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }

    fn revert_all(&mut self) {
        if let Some(original) = self.original.clone() {
            self.snapshot();
            self.json = Some(original);
            self.scene = None;
        }
    }

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

    /// Writes the edited layout and rebuilds its pack (File > Save All, and the Save button).
pub fn save_layout(app: &mut ViewerApp) {
    let Some(index) = app.panels.layouts.selected else { return };
    let Some(item) = app.data.as_deref().and_then(|d| d.layouts.items.get(index)).cloned() else { return };
    let Some(doc) = app.panels.layouts.json.clone() else { return };
    let asset = item
        .path
        .strip_prefix(&app.dirs.layouts)
        .map(|p| p.to_string_lossy().replace('\\', "/"))
        .unwrap_or_default();
    let root = app.dirs.root.clone();
    let dir = root.join("editor_projects").join("layouts");
    let _ = std::fs::create_dir_all(&dir);
    let file = dir.join(format!("{}.json", item.stem));
    match serde_json::to_string_pretty(&doc).map_err(|e| e.to_string()).and_then(|t| std::fs::write(&file, t).map_err(|e| e.to_string())) {
        Ok(()) => {
            let panel = &mut app.panels.layouts;
            panel.tools.import_path = file.to_string_lossy().into_owned();
            panel.tools.start_replace(&root, "layout", &asset, Vec::new(), true);
            app.status = format!("saving layout {} to the mod\u{2026}", item.stem);
        }
        Err(e) => app.status = format!("cannot write {}: {e}", file.display()),
    }
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
        panel.scene = None;
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

/// Writes the edited layout and rebuilds its pack (File > Save All, and the Save button).
pub fn save_active(app: &mut ViewerApp) {
    LayoutsPanel::save_layout(app)
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
            let nav = crate::ui::list_nav(ui.ctx(), &list, selected.as_ref());
            if let Some((item, _)) = &nav {
                clicked = Some(item.clone());
            }
            let nav_row = nav.map(|(_, r)| r);
            use egui_extras::{Column, TableBuilder};
            use crate::ui::TableNav;
            TableBuilder::new(ui)
                .id_salt("layout_scroll")
                .nav_scroll(nav_row)
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
                .map(|l| (l.stem.clone(), l.pack.clone(), l.kind.clone(), l.size, l.path.clone()));
            let Some((stem, pack, kind, size, path)) = info else {
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
            let asset = path
                .strip_prefix(&app.dirs.layouts)
                .map(|p| p.to_string_lossy().replace('\\', "/"))
                .unwrap_or_default();
            let root = app.dirs.root.clone();
            let mut done: Option<String> = None;
            let mut preview_doc: Option<serde_json::Value> = None;
            {
                let panel = &mut app.panels.layouts;
                egui::CollapsingHeader::new("Replace layout…")
                    .id_salt("layout_replace")
                    .show(ui, |ui| {
                        ui.label(theme::faint_label(
                            "Export the JSON, edit pane translate/rotate/scale/size or same-length text, \
                             then import it. Sections are rewritten in place, so the layout must keep \
                             its byte size (adding panes or longer strings is not supported yet).",
                        ));
                        ui.add(
                            egui::TextEdit::singleline(&mut panel.tools.import_path)
                                .hint_text("edited layout .json path")
                                .desired_width(f32::INFINITY),
                        );
                        ui.horizontal(|ui| {
                            if ui.button("Export JSON…").clicked() {
                                panel.tools.start_export(&root, "layout", &asset);
                            }
                            if ui.button("Replace + preview").clicked() {
                                panel.tools.start_replace(&root, "layout", &asset, Vec::new(), false);
                            }
                            if ui.button("Replace + save to mod").clicked() {
                                panel.tools.start_replace(&root, "layout", &asset, Vec::new(), true);
                            }
                        });
                        let fresh = panel.tools.show_status(ui, &root);
                        if fresh {
                            if let Some(file) = panel.tools.preview_path(&root) {
                                preview_doc = std::fs::read_to_string(&file)
                                    .ok()
                                    .and_then(|text| serde_json::from_str(&text).ok());
                            }
                            done = Some(match panel.tools.error.clone() {
                                Some(error) => format!("layout replace failed: {error}"),
                                None => panel.tools.message.clone(),
                            });
                        }
                    });
            }
            if let Some(message) = done {
                app.status = message;
            }
            if let Some(doc) = preview_doc {
                let pretty = serde_json::to_string_pretty(&doc).unwrap_or_default();
                app.panels.layouts.raw.set(&pretty, Lang::Json);
                app.panels.layouts.json = Some(doc);
                app.panels.layouts.original = None; // the replaced file is the new baseline
                app.panels.layouts.fit = true;
                app.panels.layouts.y_up = None;
                app.panels.layouts.tab = Tab::Preview;
            }
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
        ui.checkbox(&mut app.panels.layouts.show_textures, "Textures");
        ui.checkbox(&mut app.panels.layouts.show_labels, "Pane outlines");
        ui.checkbox(&mut app.panels.layouts.show_hidden, "Hidden panes")
            .on_hover_text("panes whose visible flag is off; the game usually shows them through an animation");
        ui.checkbox(&mut app.panels.layouts.clip, "Clip to screen");
        if ui.button("Fit").clicked() {
            app.panels.layouts.fit = true;
            app.panels.layouts.offset = egui::Vec2::ZERO;
        }
    });
    app.panels.layouts.ensure_original();
    layout_toolbar(app, ui);
    let scene = scene_for(app);
    egui::Panel::right("layout_inspector")
        .resizable(true)
        .default_size(300.0)
        .min_size(230.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| layout_inspector(app, ui));
    for warning in scene.warnings.iter().take(3) {
        ui.label(theme::faint_label(warning.clone()));
    }

    let size = ui.available_size();
    let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click_and_drag());
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 0.0, theme::BG_INPUT);
    let (sw, sh) = (scene.width.max(1.0), scene.height.max(1.0));
    if app.panels.layouts.fit {
        let scale = ((rect.width() - 24.0) / sw).min((rect.height() - 24.0) / sh);
        app.panels.layouts.zoom = scale.max(0.01);
    }
    // a drag that starts on the selected pane moves it; anywhere else it pans the view
    let selected_name = app
        .panels
        .layouts
        .selected_pane
        .and_then(|i| panes_of(app.panels.layouts.json.as_ref()?).get(i)?.get("name")?.as_str().map(String::from));
    if response.drag_started() {
        let at = response.interact_pointer_pos();
        let layout_scale = app.panels.layouts.zoom;
        let c = rect.center() + app.panels.layouts.offset;
        let hit = match (&selected_name, at) {
            (Some(name), Some(p)) => scene.quads.iter().any(|q| {
                &q.pane == name && {
                    let pts = q.corners.map(|k| egui::pos2(c.x + k.x * layout_scale, c.y - k.y * layout_scale));
                    egui::Rect::from_points(&pts).contains(p)
                }
            }),
            _ => false,
        };
        app.panels.layouts.pane_drag = hit;
        if hit {
            app.panels.layouts.snapshot();
        }
    }
    if response.dragged() {
        if app.panels.layouts.pane_drag {
            let d = response.drag_delta() / app.panels.layouts.zoom.max(0.001);
            if let Some(i) = app.panels.layouts.selected_pane {
                nudge_translate(&mut app.panels.layouts, i, d.x, -d.y);
            }
        } else {
            app.panels.layouts.offset += response.drag_delta();
            app.panels.layouts.fit = false;
        }
    }
    if response.drag_stopped() {
        app.panels.layouts.pane_drag = false;
    }
    if response.hovered() {
        let scroll = ui.input(|i| i.smooth_scroll_delta.y);
        if scroll != 0.0 {
            let pointer = ui.input(|i| i.pointer.hover_pos());
            let layouts = &mut app.panels.layouts;
            crate::ui::wheel_zoom(&mut layouts.zoom, &mut layouts.offset, scroll, rect.center(), pointer);
            layouts.fit = false;
        }
    }
    // layout space is y-up with (0,0) at the screen centre
    let scale = app.panels.layouts.zoom;
    let centre = rect.center() + app.panels.layouts.offset;
    let to_screen = |p: egui::Pos2| egui::pos2(centre.x + p.x * scale, centre.y - p.y * scale);
    let screen = egui::Rect::from_center_size(centre, egui::vec2(sw * scale, sh * scale));
    painter.rect_filled(screen, 0.0, egui::Color32::BLACK);
    let painter = if app.panels.layouts.clip { painter.with_clip_rect(screen.intersect(rect)) } else { painter };

    let show_hidden = app.panels.layouts.show_hidden;
    let mut hovered: Option<&layout_scene::Quad> = None;
    let pointer = response.hover_pos();
    for quad in &scene.quads {
        if !quad.visible && !show_hidden {
            continue;
        }
        let pts = quad.corners.map(to_screen);
        let fade = if quad.visible { 1.0 } else { 0.35 };
        if !quad.frame_only {
            let texture = if app.panels.layouts.show_textures {
                quad.texture.as_ref().and_then(|name| {
                    let path = app.data.as_deref()?.textures.resolve(name)?.path.clone();
                    app.layout_tex.get(ui.ctx(), &app.pool, &path).map(|h| h.id())
                })
            } else {
                None
            };
            let mut mesh = match texture {
                Some(id) => egui::Mesh::with_texture(id),
                None => egui::Mesh::default(),
            };
            for i in 0..4 {
                let uv = if texture.is_some() { quad.uv[i] } else { egui::pos2(0.0, 0.0) };
                let mut color = quad.colors[i].gamma_multiply(fade);
                if texture.is_none() && quad.texture.is_some() {
                    // texture not extracted (or textures off): show where it goes
                    color = theme::COL_STRING.gamma_multiply(0.25 * fade);
                }
                mesh.vertices.push(egui::epaint::Vertex { pos: pts[i], uv, color });
            }
            mesh.indices.extend_from_slice(&[0, 1, 2, 2, 1, 3]);
            painter.add(egui::Shape::mesh(mesh));
        }
        if let Some(text) = &quad.text {
            let font = text.font.as_ref().and_then(|name| game_font(app, name));
            let sheets: Vec<Option<egui::TextureId>> = match &font {
                Some(f) => f.sheets.iter().map(|p| app.font_tex.get(ui.ctx(), &app.pool, p).map(|h| h.id())).collect(),
                None => Vec::new(),
            };
            match &font {
                Some(f) if sheets.iter().all(|s| s.is_some()) => {
                    let sheets: Vec<egui::TextureId> = sheets.into_iter().flatten().collect();
                    draw_game_text(&painter, &pts, text, f, &sheets, scale, fade);
                }
                _ => draw_text(&painter, &pts, text, scale, fade),
            }
        }
        if app.panels.layouts.show_labels && quad.frame_only && quad.depth == 0 {
            let outline = vec![pts[0], pts[1], pts[3], pts[2], pts[0]];
            painter.add(egui::Shape::line(outline, egui::Stroke::new(1.0, theme::INFO.gamma_multiply(0.35))));
        }
        if let Some(p) = pointer {
            if quad.depth == 0 && egui::Rect::from_points(&pts).contains(p) {
                hovered = Some(quad);
            }
        }
    }
    painter.rect_stroke(screen, 0.0, egui::Stroke::new(1.0, theme::BORDER_LIGHT), egui::StrokeKind::Outside);
    if let Some(name) = &selected_name {
        for quad in scene.quads.iter().filter(|q| &q.pane == name) {
            let pts = quad.corners.map(to_screen);
            let outline = vec![pts[0], pts[1], pts[3], pts[2], pts[0]];
            painter.add(egui::Shape::line(outline, egui::Stroke::new(2.0, theme::ACCENT)));
        }
    }
    if response.clicked() {
        if let Some(p) = response.interact_pointer_pos() {
            // the topmost visible quad under the pointer
            let top = scene
                .quads
                .iter()
                .filter(|q| (q.visible || show_hidden) && !q.frame_only || q.depth == 0)
                .filter(|q| egui::Rect::from_points(&q.corners.map(to_screen)).contains(p))
                .last()
                .map(|q| q.pane.clone());
            let panel = &mut app.panels.layouts;
            panel.selected_pane = top.and_then(|name| {
                panes_of(panel.json.as_ref()?).iter().position(|pane| pane.get("name").and_then(|v| v.as_str()) == Some(name.as_str()))
            });
        }
    }
    if let Some(quad) = hovered {
        let pts = quad.corners.map(to_screen);
        let outline = vec![pts[0], pts[1], pts[3], pts[2], pts[0]];
        painter.add(egui::Shape::line(outline, egui::Stroke::new(1.5, theme::ACCENT)));
        let texture = quad.texture.as_deref().unwrap_or("-");
        let note = if quad.visible { "" } else { "\nhidden until an animation shows it" };
        response.on_hover_text(format!("{}  ({})\ntexture: {}{}", quad.pane, quad.kind, texture, note));
    }
}

/// Moves the pane in its parent's space (layout y is up).
fn nudge_translate(panel: &mut LayoutsPanel, index: usize, dx: f32, dy: f32) {
    let Some(pane) = panel
        .json
        .as_mut()
        .and_then(|j| j.get_mut("panes"))
        .and_then(|v| v.as_array_mut())
        .and_then(|a| a.get_mut(index))
    else {
        return;
    };
    if let Some(t) = pane.get_mut("translate").and_then(|v| v.as_array_mut()) {
        for (slot, delta) in t.iter_mut().zip([dx, dy]) {
            if let Some(v) = slot.as_f64() {
                *slot = serde_json::json!(((v as f32 + delta) * 100.0).round() / 100.0);
            }
        }
        panel.scene = None;
    }
}

fn layout_toolbar(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let edited = app.panels.layouts.edited_panes();
    ui.horizontal(|ui| {
        let panel = &mut app.panels.layouts;
        if ui.add_enabled(panel.can_undo(), egui::Button::new("Undo")).on_hover_text("Ctrl+Z").clicked() {
            panel.undo_action();
        }
        if ui.add_enabled(panel.can_redo(), egui::Button::new("Redo")).on_hover_text("Ctrl+Y").clicked() {
            panel.redo_action();
        }
        if ui.add_enabled(edited > 0, egui::Button::new("Revert all")).clicked() {
            panel.revert_all();
        }
        ui.separator();
        if edited > 0 {
            ui.label(egui::RichText::new(format!("\u{25cf} {edited} pane(s) edited")).color(theme::ACCENT).size(12.0));
        } else {
            ui.label(theme::faint_label("click a pane to select it \u{b7} drag it to move \u{b7} edit values on the right"));
        }
        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
            if ui
                .add_enabled(edited > 0, egui::Button::new("Save to mod"))
                .on_hover_text("Rebuild the layout and stage mod/romfs/<pack>.pack (Ctrl+S)")
                .clicked()
            {
                save_active(app);
            }
        });
    });
    if !ui.ctx().egui_wants_keyboard_input() {
        let (undo, redo, save) = ui.ctx().input(|i| {
            let c = i.modifiers.command;
            (
                c && !i.modifiers.shift && i.key_pressed(egui::Key::Z),
                c && (i.key_pressed(egui::Key::Y) || (i.modifiers.shift && i.key_pressed(egui::Key::Z))),
                c && !i.modifiers.shift && i.key_pressed(egui::Key::S),
            )
        });
        if undo {
            app.panels.layouts.undo_action();
        }
        if redo {
            app.panels.layouts.redo_action();
        }
        if save && edited > 0 {
            save_active(app);
        }
    }
    ui.separator();
}

/// X / Y / (Z) drag fields for one array value of a pane, with a revert button.
fn array_row(ui: &mut egui::Ui, label: &str, now: &mut Vec<f64>, original: Option<&Vec<f64>>, speed: f64) -> bool {
    let mut changed = false;
    ui.horizontal(|ui| {
        ui.add_sized([58.0, 18.0], egui::Label::new(theme::dim_label(label)));
        for (i, tag) in ["X", "Y", "Z"].iter().enumerate().take(now.len()) {
            ui.label(egui::RichText::new(*tag).color(theme::TEXT_FAINT).size(11.0));
            let mut v = now[i] as f32;
            if ui.add(egui::DragValue::new(&mut v).speed(speed).max_decimals(2)).changed() {
                now[i] = v as f64;
                changed = true;
            }
        }
        let differs = original.is_some_and(|o| o != now);
        if ui.add_enabled(differs, egui::Button::new("reset").small()).on_hover_text("Back to the value in the retail file").clicked() {
            if let Some(o) = original {
                *now = o.clone();
                changed = true;
            }
        }
    });
    changed
}

fn layout_inspector(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.label(theme::heading("Inspector"));
    ui.separator();
    let Some(index) = app.panels.layouts.selected_pane else {
        ui.label(theme::faint_label("Select a pane in the preview."));
        return;
    };
    let (Some(json), Some(orig)) = (app.panels.layouts.json.clone(), app.panels.layouts.original.clone()) else { return };
    let (Some(pane), Some(orig_pane)) = (panes_of(&json).get(index).cloned(), panes_of(&orig).get(index).cloned()) else {
        ui.label(theme::faint_label("That pane is not in this layout."));
        return;
    };
    let name = pane.get("name").and_then(|v| v.as_str()).unwrap_or("(unnamed)").to_string();
    let kind = pane.get("type").and_then(|v| v.as_str()).unwrap_or("?").to_string();
    ui.horizontal(|ui| {
        ui.label(theme::heading(name.clone()));
        ui.label(theme::faint_label(kind));
    });
    ui.label(theme::faint_label(format!("pane {index} of {}", panes_of(&json).len())));
    ui.add_space(4.0);

    let take = |p: &serde_json::Value, key: &str| -> Option<Vec<f64>> {
        p.get(key)?.as_array().map(|a| a.iter().filter_map(|v| v.as_f64()).collect())
    };
    let mut edited: Vec<(&str, serde_json::Value)> = Vec::new();
    egui::CollapsingHeader::new(egui::RichText::new("Transform").strong()).default_open(true).show(ui, |ui| {
        for (key, label, speed) in [("translate", "Position", 0.5), ("rotate", "Rotation", 0.5), ("scale", "Scale", 0.01), ("size", "Size", 0.5)] {
            if let Some(mut now) = take(&pane, key) {
                let original = take(&orig_pane, key);
                if array_row(ui, label, &mut now, original.as_ref(), speed) {
                    edited.push((key, serde_json::json!(now)));
                }
            }
        }
    });
    if let Some(text) = pane.get("text").and_then(|v| v.as_str()) {
        let mut text = text.to_string();
        egui::CollapsingHeader::new(egui::RichText::new("Text").strong()).default_open(true).show(ui, |ui| {
            if ui.add(egui::TextEdit::multiline(&mut text).desired_rows(2).desired_width(f32::INFINITY)).changed() {
                edited.push(("text", serde_json::json!(text)));
            }
            ui.label(theme::faint_label("Longer than the reserved space grows the layout past its retail size."));
        });
    }
    egui::CollapsingHeader::new(egui::RichText::new("Pane").strong()).default_open(false).show(ui, |ui| {
        let rows: Vec<(String, String)> = ["type", "visible", "alpha", "origin", "flags"]
            .iter()
            .filter_map(|k| pane.get(*k).map(|v| (k.to_string(), v.to_string())))
            .collect();
        crate::ui::kv_rows(ui, &rows.iter().map(|(k, v)| (k.as_str(), v.clone())).collect::<Vec<_>>());
    });
    if !edited.is_empty() {
        let panel = &mut app.panels.layouts;
        if panel.edit_group != Some(index) || panel.undo.is_empty() {
            panel.snapshot();
        }
        panel.edit_group = Some(index);
        if let Some(target) = panel
            .json
            .as_mut()
            .and_then(|j| j.get_mut("panes"))
            .and_then(|v| v.as_array_mut())
            .and_then(|a| a.get_mut(index))
        {
            for (key, value) in edited {
                target[key] = value;
            }
        }
        panel.scene = None;
    } else if !ui.ctx().input(|i| i.pointer.any_down()) {
        app.panels.layouts.edit_group = None;
    }
}

/// Text in the editor font at the pane's font size, aligned like the game aligns it.
fn draw_text(painter: &egui::Painter, pts: &[egui::Pos2; 4], text: &layout_scene::TextDraw, scale: f32, fade: f32) {
    if text.text.is_empty() {
        return;
    }
    let bb = egui::Rect::from_points(pts);
    let (x, hx) = match text.h_align {
        1 => (bb.left(), egui::Align::Min),
        2 => (bb.right(), egui::Align::Max),
        _ => (bb.center().x, egui::Align::Center),
    };
    let (y, vy) = match text.v_align {
        1 => (bb.top(), egui::Align::Min),
        2 => (bb.bottom(), egui::Align::Max),
        _ => (bb.center().y, egui::Align::Center),
    };
    let size = (text.size * scale).clamp(4.0, 200.0);
    painter.text(
        egui::pos2(x, y),
        egui::Align2([hx, vy]),
        &text.text,
        egui::FontId::proportional(size),
        text.top.gamma_multiply(fade),
    );
}

fn game_font(app: &mut ViewerApp, name: &str) -> Option<std::sync::Arc<GameFont>> {
    let root = app.dirs.root.clone();
    app.panels
        .layouts
        .fonts
        .entry(name.to_string())
        .or_insert_with(|| GameFont::load(&root, name).map(std::sync::Arc::new))
        .clone()
}

/// Text with the game's own glyphs: font size scales the font's cell, lines advance by
/// the font's line feed, and the block is placed and aligned like the game does.
fn draw_game_text(
    painter: &egui::Painter,
    pts: &[egui::Pos2; 4],
    text: &layout_scene::TextDraw,
    font: &GameFont,
    sheets: &[egui::TextureId],
    scale: f32,
    fade: f32,
) {
    if text.text.is_empty() || font.height <= 0.0 || font.width <= 0.0 {
        return;
    }
    let bb = egui::Rect::from_points(pts);
    // layout units -> screen pixels per font pixel
    let sx = text.size_x / font.width * scale;
    let sy = text.size / font.height * scale;
    let char_space = if sx > 0.0 { text.char_space * scale / sx } else { 0.0 };
    let line_h = font.line_feed * sy + text.line_space * scale;
    let lines: Vec<(Vec<_>, f32)> = text.text.split('\n').map(|l| font.place_line(l, char_space)).collect();
    let block_w = lines.iter().map(|l| l.1 * sx).fold(0.0, f32::max);
    let block_h = line_h * lines.len() as f32 - text.line_space * scale;
    let x0 = match text.h_align {
        1 => bb.left(),
        2 => bb.right() - block_w,
        _ => bb.center().x - block_w / 2.0,
    };
    let y0 = match text.v_align {
        1 => bb.top(),
        2 => bb.bottom() - block_h,
        _ => bb.center().y - block_h / 2.0,
    };
    let line_align = match text.line_align {
        1 => 1,
        2 => 0,
        3 => 2,
        _ => text.h_align,
    };
    let mut meshes: Vec<egui::Mesh> = sheets.iter().map(|id| egui::Mesh::with_texture(*id)).collect();
    for (i, (glyphs, width)) in lines.iter().enumerate() {
        let w = width * sx;
        let lx = match line_align {
            1 => x0,
            2 => x0 + block_w - w,
            _ => x0 + (block_w - w) / 2.0,
        };
        let ly = y0 + i as f32 * line_h;
        for g in glyphs {
            let Some(mesh) = meshes.get_mut(g.sheet) else { continue };
            let r = egui::Rect::from_min_max(
                egui::pos2(lx + g.rect.min.x * sx, ly + g.rect.min.y * sy),
                egui::pos2(lx + g.rect.max.x * sx, ly + g.rect.max.y * sy),
            );
            // vertical gradient: top colour at the line top, bottom colour at the cell bottom
            let (top, bottom) = (text.top.gamma_multiply(fade), text.bottom.gamma_multiply(fade));
            let base = mesh.vertices.len() as u32;
            for (pos, uv, color) in [
                (r.left_top(), g.uv.left_top(), top),
                (r.right_top(), g.uv.right_top(), top),
                (r.left_bottom(), g.uv.left_bottom(), bottom),
                (r.right_bottom(), g.uv.right_bottom(), bottom),
            ] {
                mesh.vertices.push(egui::epaint::Vertex { pos, uv, color });
            }
            mesh.indices.extend_from_slice(&[base, base + 1, base + 2, base + 2, base + 1, base + 3]);
        }
    }
    for mesh in meshes {
        painter.add(egui::Shape::mesh(mesh));
    }
}

/// The selected layout's scene, rebuilt only when the selection changes.
fn scene_for(app: &mut ViewerApp) -> std::sync::Arc<layout_scene::Scene> {
    let key = app.panels.layouts.selected;
    if let Some((k, scene)) = &app.panels.layouts.scene {
        if *k == key {
            return scene.clone();
        }
    }
    let dir = key
        .and_then(|i| app.data.as_deref()?.layouts.items.get(i))
        .and_then(|l| l.path.parent().map(|p| p.to_path_buf()));
    let scene = match (app.panels.layouts.json.clone(), app.data.as_mut()) {
        (Some(json), Some(data)) => layout_scene::build(&json, &mut |name| {
            let dir = dir.as_ref()?;
            data.layouts.load(&dir.join(format!("{name}.bflyt.json")))
        }),
        _ => layout_scene::Scene::default(),
    };
    let scene = std::sync::Arc::new(scene);
    app.panels.layouts.scene = Some((key, scene.clone()));
    scene
}
