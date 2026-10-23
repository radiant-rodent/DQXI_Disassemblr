//! Level editor MVP: load a decoded map, view its environment mesh, inspect
//! placement records, edit transforms, undo/redo, and export a patched BXON.

use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver};
use std::sync::Arc;

use eframe::egui;
use serde::{Deserialize, Serialize};

use crate::app::{paint_mesh_viewport, ViewerApp};
use crate::math::{Mat4, Vec3};
use crate::render::camera::Camera;
use crate::render::gpu::RenderOptions;
use crate::render::mesh::Mesh;
use crate::theme;
use crate::utils::{human_count, human_size};

#[derive(Clone, Debug, Deserialize, Serialize, Default)]
pub struct FieldOffsets {
    #[serde(default)]
    pub position: [String; 3],
    #[serde(default)]
    pub position_shadow: [String; 3],
    #[serde(default)]
    pub scale: [String; 3],
    #[serde(default)]
    pub rotation: [String; 3],
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct SceneObject {
    pub id: String,
    pub kind: String,
    pub position: [f32; 3],
    pub scale: [f32; 3],
    #[serde(default)]
    pub rotation: [f32; 3],
    pub record_offset: String,
    #[serde(default)]
    pub field_offsets: FieldOffsets,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Scene {
    pub id: String,
    pub source: String,
    #[serde(default)]
    pub background_bch: Option<String>,
    #[serde(default)]
    pub objects: Vec<SceneObject>,
}

struct Loaded {
    scene: Scene,
    mesh: Option<Mesh>,
}

pub struct EditorPanel {
    pub query: String,
    maps: Vec<String>,
    filtered: Vec<String>,
    selected_map: Option<String>,
    scene: Option<Scene>,
    original: Vec<SceneObject>,
    selected_object: Option<usize>,
    pub camera: Camera,
    mesh: Option<Arc<Mesh>>,
    mesh_id: u64,
    loading: bool,
    status: String,
    rx: Receiver<Result<Loaded, String>>,
    dirty: bool,
    undo: Vec<Vec<SceneObject>>,
    redo: Vec<Vec<SceneObject>>,
    pub show_objects: bool,
    pub show_bounds: bool,
    pub show_grid: bool,
    pub show_axes: bool,
    pub wireframe: bool,
    pub flat: bool,
    pub drag_selected: bool,
    pub snap: bool,
    drag_object: Option<usize>,
    drag_start: Option<([f32; 3], egui::Pos2)>,
}

impl Default for EditorPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            maps: Vec::new(),
            filtered: Vec::new(),
            selected_map: None,
            scene: None,
            original: Vec::new(),
            selected_object: None,
            camera: Camera::default(),
            mesh: None,
            mesh_id: 0,
            loading: false,
            status: "Choose a map to begin.".into(),
            rx: channel().1,
            dirty: false,
            undo: Vec::new(),
            redo: Vec::new(),
            show_objects: true,
            show_bounds: true,
            show_grid: true,
            show_axes: true,
            wireframe: false,
            flat: false,
            drag_selected: true,
            snap: true,
            drag_object: None,
            drag_start: None,
        }
    }
}

impl EditorPanel {
    pub fn map_count(&self) -> usize {
        self.maps.len()
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.filtered = self.maps.clone();
    }

    fn scan_maps(&mut self, root: &Path) {
        if !self.maps.is_empty() {
            return;
        }
        let dir = root.join("game_assets/maps");
        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.join("scene.json").is_file() {
                    if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                        self.maps.push(name.to_string());
                    }
                }
            }
        }
        self.maps.sort();
        self.filtered = self.maps.clone();
        if self.maps.is_empty() {
            self.status = "No decoded maps. Run: python tools/map_tool.py export --all".into();
        }
    }

    fn filter(&mut self) {
        let q = self.query.to_lowercase();
        self.filtered = self
            .maps
            .iter()
            .filter(|m| q.is_empty() || m.to_lowercase().contains(&q))
            .cloned()
            .collect();
    }

    fn select(&mut self, root: &Path, pool: &crate::utils::Pool, map: &str) {
        self.selected_map = Some(map.to_string());
        self.scene = None;
        self.mesh = None;
        self.selected_object = None;
        self.drag_object = None;
        self.drag_start = None;
        self.undo.clear();
        self.redo.clear();
        self.dirty = false;
        self.loading = true;
        self.status = format!("Loading {map}\u{2026}");
        let scene_path = root.join("game_assets/maps").join(map).join("scene.json");
        let root = root.to_path_buf();
        let map_name = map.to_string();
        let (tx, rx) = channel();
        self.rx = rx;
        pool.submit(move || {
            let result = (|| -> Result<Loaded, String> {
                let text = std::fs::read_to_string(&scene_path)
                    .map_err(|e| format!("read {}: {e}", scene_path.display()))?;
                let scene: Scene = serde_json::from_str(&text)
                    .map_err(|e| format!("parse {}: {e}", scene_path.display()))?;
                let mesh = scene
                    .background_bch
                    .as_deref()
                    .and_then(|bch| background_obj(&root, &map_name, bch))
                    .and_then(|path| crate::render::mesh::load_obj(&path).ok());
                Ok(Loaded { scene, mesh })
            })();
            let _ = tx.send(result);
        });
    }

    fn poll(&mut self) {
        let Ok(result) = self.rx.try_recv() else { return };
        self.loading = false;
        match result {
            Ok(loaded) => {
                let count = loaded.scene.objects.len();
                self.status = match &loaded.mesh {
                    Some(mesh) => format!(
                        "{} objects  \u{b7}  {} tris  \u{b7}  {}",
                        human_count(count),
                        human_count(mesh.triangle_count),
                        human_size(mesh.vertices.len() as u64 * 4 + mesh.indices.len() as u64 * 4)
                    ),
                    None => format!(
                        "{} objects  \u{b7}  no converted background mesh (run convert_assets.py --models)",
                        human_count(count)
                    ),
                };
                if let Some(mesh) = &loaded.mesh {
                    self.camera.frame(&mesh.bounds);
                    self.mesh = Some(Arc::new(mesh.clone()));
                    self.mesh_id = self.mesh_id.wrapping_add(1);
                }
                self.original = loaded.scene.objects.clone();
                self.scene = Some(loaded.scene);
            }
            Err(e) => {
                self.status = e;
            }
        }
    }

    fn edits(&self) -> Vec<(String, f32)> {
        let Some(scene) = &self.scene else { return Vec::new() };
        let mut out = Vec::new();
        for (obj, orig) in scene.objects.iter().zip(self.original.iter()) {
            for i in 0..3 {
                if (obj.position[i] - orig.position[i]).abs() > 1e-6 {
                    if let Some(off) = obj.field_offsets.position.get(i) {
                        out.push((off.clone(), obj.position[i]));
                    }
                    if let Some(off) = obj.field_offsets.position_shadow.get(i) {
                        if !off.is_empty() {
                            out.push((off.clone(), obj.position[i]));
                        }
                    }
                }
                if (obj.scale[i] - orig.scale[i]).abs() > 1e-6 {
                    if let Some(off) = obj.field_offsets.scale.get(i) {
                        out.push((off.clone(), obj.scale[i]));
                    }
                }
                if (obj.rotation[i] - orig.rotation[i]).abs() > 1e-6 {
                    if let Some(off) = obj.field_offsets.rotation.get(i) {
                        out.push((off.clone(), obj.rotation[i]));
                    }
                }
            }
        }
        out
    }

    fn save_project(&mut self, root: &Path) {
        let Some(scene) = &self.scene else { return };
        if let Err(e) = validate_objects(&scene.objects) {
            self.status = e;
            return;
        }
        let edits: Vec<serde_json::Value> = self
            .edits()
            .into_iter()
            .map(|(offset, value)| serde_json::json!({"offset": offset, "value": value}))
            .collect();
        let project = serde_json::json!({
            "format": "DQXI_LEVEL_EDIT",
            "map": scene.id,
            "source": scene.source,
            "objects": scene.objects,
            "edits": edits,
        });
        let dir = root.join("editor_projects");
        let _ = std::fs::create_dir_all(&dir);
        let path = dir.join(format!("{}.json", scene.id));
        match serde_json::to_string_pretty(&project)
            .map_err(|e| e.to_string())
            .and_then(|text| std::fs::write(&path, text).map_err(|e| e.to_string()))
        {
            Ok(()) => {
                self.dirty = false;
                self.status = format!("Saved project {}", path.display());
            }
            Err(e) => self.status = format!("Save failed: {e}"),
        }
    }

    fn load_project(&mut self, root: &Path) {
        let Some(scene) = &self.scene else { return };
        let path = root.join("editor_projects").join(format!("{}.json", scene.id));
        let text = match std::fs::read_to_string(&path) {
            Ok(t) => t,
            Err(e) => {
                self.status = format!("No project to load: {e}");
                return;
            }
        };
        let value: serde_json::Value = match serde_json::from_str(&text) {
            Ok(v) => v,
            Err(e) => {
                self.status = format!("Project parse failed: {e}");
                return;
            }
        };
        let Some(objects) = value.get("objects") else {
            self.status = "Project has no objects array".into();
            return;
        };
        match serde_json::from_value::<Vec<SceneObject>>(objects.clone()) {
            Ok(objects) => {
                if let Some(scene) = self.scene.as_mut() {
                    self.undo.push(scene.objects.clone());
                    self.redo.clear();
                    scene.objects = objects;
                }
                self.dirty = true;
                self.status = format!("Loaded project {}", path.display());
            }
            Err(e) => self.status = format!("Project object parse failed: {e}"),
        }
    }

    fn export_patch(&mut self, root: &Path) {
        let Some(scene) = &self.scene else { return };
        if let Err(e) = validate_objects(&scene.objects) {
            self.status = e;
            return;
        }
        let source = root.join(&scene.source);
        let mut bytes = match std::fs::read(&source) {
            Ok(b) => b,
            Err(e) => {
                self.status = format!("Cannot read {}: {e}", source.display());
                return;
            }
        };
        let edits = self.edits();
        if let Err(e) = apply_float_edits(&mut bytes, &edits) {
            self.status = e;
            return;
        }
        let out = root
            .join("game_assets/maps")
            .join(&scene.id)
            .join("level3d.patched.bxon");
        match std::fs::write(&out, &bytes) {
            Ok(()) => {
                self.dirty = false;
                self.status = format!(
                    "Exported {} float edits to {} (same size: {})",
                    edits.len(),
                    out.display(),
                    bytes.len() == std::fs::metadata(&source).map(|m| m.len() as usize).unwrap_or(0)
                );
            }
            Err(e) => self.status = format!("Export failed: {e}"),
        }
    }
}

pub fn validate_objects(objects: &[SceneObject]) -> Result<(), String> {
    for obj in objects {
        if obj.position.iter().chain(obj.scale.iter()).chain(obj.rotation.iter()).any(|v| !v.is_finite()) {
            return Err(format!("{} has a non-finite transform", obj.id));
        }
        if obj.scale.iter().any(|v| v.abs() > 1e7) || obj.position.iter().any(|v| v.abs() > 1e7) {
            return Err(format!("{} has an implausible transform", obj.id));
        }
    }
    Ok(())
}

pub fn apply_float_edits(bytes: &mut [u8], edits: &[(String, f32)]) -> Result<usize, String> {
    for (off, value) in edits {
        let parsed = u32::from_str_radix(off.trim_start_matches("0x"), 16)
            .map_err(|_| format!("invalid offset {off}"))? as usize;
        if parsed + 4 > bytes.len() {
            return Err(format!("offset 0x{parsed:X} outside {} byte buffer", bytes.len()));
        }
        bytes[parsed..parsed + 4].copy_from_slice(&value.to_le_bytes());
    }
    Ok(edits.len())
}

fn background_obj(root: &Path, map: &str, bch: &str) -> Option<PathBuf> {
    let rel = Path::new(bch).strip_prefix("game_data").ok()?;
    let mut dir = root.join("game_assets/models").join(rel);
    dir.set_extension("");
    let stem = Path::new(bch).file_stem()?.to_string_lossy();
    let direct = dir.join(format!("{stem}.obj"));
    if direct.is_file() {
        return Some(direct);
    }
    // Asset conversion may have used a curated directory name; search the map folder.
    for candidate in [
        dir.join(format!("Map_{map}.obj")),
        dir.join(format!("Map_{map}_cs.obj")),
    ] {
        if candidate.is_file() {
            return Some(candidate);
        }
    }
    None
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    {
        let root = app.dirs.root.clone();
        let pool = &app.pool;
        let panel = &mut app.panels.editor;
        panel.scan_maps(&root);
        if panel.selected_map.is_none() {
            if let Ok(map) = std::env::var("DQXI_EDITOR_MAP") {
                if panel.maps.iter().any(|m| m == &map) {
                    panel.select(&root, pool, &map);
                }
            }
        }
        panel.poll();
    }

    if let Some(map) = app.panels.editor.selected_map.clone() {
        if app.panels.editor.scene.is_none() && !app.panels.editor.loading {
            let root = app.dirs.root.clone();
            app.panels.editor.select(&root, &app.pool, &map);
        }
    }
    if app.panels.editor.loading {
        ui.ctx().request_repaint_after(std::time::Duration::from_millis(100));
    }

    egui::Panel::left("editor_maps")
        .exact_size(232.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Levels"));
            ui.label(theme::faint_label(format!("{} decoded maps", human_count(app.panels.editor.maps.len()))));
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.editor.query)
                        .hint_text("Search map id\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.editor.filter();
            }
            ui.separator();
            let filtered = app.panels.editor.filtered.clone();
            let selected = app.panels.editor.selected_map.clone();
            let mut clicked = None;
            egui::ScrollArea::vertical()
                .id_salt("editor_map_list")
                .auto_shrink([false, false])
                .show_rows(ui, 19.0, filtered.len(), |ui, range| {
                    for i in range {
                        let map = &filtered[i];
                        if ui.selectable_label(selected.as_deref() == Some(map.as_str()), map).clicked() {
                            clicked = Some(map.clone());
                        }
                    }
                });
            if let Some(map) = clicked {
                let root = app.dirs.root.clone();
                app.panels.editor.select(&root, &app.pool, &map);
            }
        });

    if let Some(scene) = app.panels.editor.scene.clone() {
        let root = app.dirs.root.clone();
        egui::Panel::right("editor_inspector")
            .exact_size(380.0)
            .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
            .show(ui, |ui| {
                ui.horizontal(|ui| {
                    ui.label(theme::heading(scene.id.clone()));
                    if app.panels.editor.dirty {
                        ui.label(egui::RichText::new("modified").color(theme::ACCENT));
                    }
                });
                ui.label(theme::faint_label(app.panels.editor.status.clone()));
                ui.separator();
                ui.horizontal_wrapped(|ui| {
                    if ui.button("Undo").clicked() {
                        if let Some(prev) = app.panels.editor.undo.pop() {
                            if let Some(cur) = app.panels.editor.scene.as_mut() {
                                app.panels.editor.redo.push(cur.objects.clone());
                                cur.objects = prev;
                            }
                            app.panels.editor.dirty = true;
                        }
                    }
                    if ui.button("Redo").clicked() {
                        if let Some(next) = app.panels.editor.redo.pop() {
                            if let Some(cur) = app.panels.editor.scene.as_mut() {
                                app.panels.editor.undo.push(cur.objects.clone());
                                cur.objects = next;
                            }
                            app.panels.editor.dirty = true;
                        }
                    }
                    if ui.button("Save project").clicked() {
                        let panel = &mut app.panels.editor;
                        panel.save_project(&root);
                    }
                    if ui.button("Load project").clicked() {
                        let panel = &mut app.panels.editor;
                        panel.load_project(&root);
                    }
                    if ui.button("Export BXON").clicked() {
                        let panel = &mut app.panels.editor;
                        panel.export_patch(&root);
                    }
                });
                ui.separator();
                ui.label(theme::faint_label(format!("{} placement candidates", human_count(scene.objects.len()))));
                let mut selected = app.panels.editor.selected_object;
                egui::ScrollArea::vertical()
                    .id_salt("editor_object_list")
                    .max_height(190.0)
                    .show_rows(ui, 18.0, scene.objects.len(), |ui, range| {
                        for i in range {
                            let obj = &scene.objects[i];
                            let label = format!(
                                "{:>3} {:<10} ({:.2}, {:.2}, {:.2})",
                                i, obj.kind, obj.position[0], obj.position[1], obj.position[2]
                            );
                            if ui.selectable_label(selected == Some(i), label).clicked() {
                                selected = Some(i);
                            }
                        }
                    });
                app.panels.editor.selected_object = selected;
                if let Some(i) = selected {
                    if let Some(obj) = app.panels.editor.scene.as_ref().and_then(|s| s.objects.get(i)).cloned() {
                        ui.separator();
                        ui.horizontal(|ui| {
                            ui.label(theme::heading(format!("{} {}", obj.kind, obj.id)));
                            if ui.button("Focus").on_hover_text("Center the camera on this marker").clicked() {
                                app.panels.editor.camera.target = Vec3::new(obj.position[0], obj.position[1], obj.position[2]);
                                app.panels.editor.camera.distance = app.panels.editor.camera.distance.min(40.0).max(5.0);
                            }
                        });
                        let before = app.panels.editor.scene.as_ref().map(|s| s.objects.clone());
                        let mut changed = false;
                        if let Some(object) = app
                            .panels
                            .editor
                            .scene
                            .as_mut()
                            .and_then(|s| s.objects.get_mut(i))
                        {
                            ui.label(theme::faint_label("position"));
                            changed |= drag3(ui, &mut object.position, 0.05);
                            ui.label(theme::faint_label("scale"));
                            changed |= drag3(ui, &mut object.scale, 0.05);
                            ui.label(theme::faint_label("rotation (radians)"));
                            changed |= drag3(ui, &mut object.rotation, 0.01);
                        }
                        if changed {
                            if let Some(before) = before {
                                app.panels.editor.undo.push(before);
                                app.panels.editor.redo.clear();
                                app.panels.editor.dirty = true;
                            }
                        }
                    }
                }
            });
        editor_viewport(app, ui, &scene);
    } else {
        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
            .show(ui, |ui| {
                ui.centered_and_justified(|ui| {
                    if app.panels.editor.loading {
                        ui.label(theme::dim_label(format!("Loading {}…", app.panels.editor.selected_map.clone().unwrap_or_default())));
                    } else {
                        ui.label(theme::dim_label("Select a level on the left. Maps are decoded from game_data/level3d."));
                    }
                });
            });
    }
}

fn drag3(ui: &mut egui::Ui, values: &mut [f32; 3], speed: f64) -> bool {
    let mut changed = false;
    ui.horizontal(|ui| {
        changed |= ui.add(egui::DragValue::new(&mut values[0]).speed(speed).prefix("x ")).changed();
        changed |= ui.add(egui::DragValue::new(&mut values[1]).speed(speed).prefix("y ")).changed();
        changed |= ui.add(egui::DragValue::new(&mut values[2]).speed(speed).prefix("z ")).changed();
    });
    changed
}

fn editor_viewport(app: &mut ViewerApp, ui: &mut egui::Ui, scene: &Scene) {
    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.label(theme::heading("World"));
                ui.label(theme::faint_label("drag: orbit  \u{b7}  drag marker: move selected  \u{b7}  right/middle-drag: pan  \u{b7}  wheel: zoom"));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.checkbox(&mut app.panels.editor.wireframe, "Wireframe");
                    ui.checkbox(&mut app.panels.editor.show_axes, "Axes");
                    ui.checkbox(&mut app.panels.editor.show_grid, "Grid");
                    ui.checkbox(&mut app.panels.editor.show_objects, "Objects");
                    ui.checkbox(&mut app.panels.editor.show_bounds, "Bounds");
                    ui.checkbox(&mut app.panels.editor.drag_selected, "Drag selected")
                        .on_hover_text("When on, dragging a marker moves it in the camera plane; otherwise drag orbits");
                    ui.checkbox(&mut app.panels.editor.snap, "Snap 0.25")
                        .on_hover_text("Round moved positions to quarter-unit steps");
                });
            });
            ui.separator();
            let mut camera = app.panels.editor.camera;
            let opts = RenderOptions {
                wireframe: app.panels.editor.wireframe,
                show_grid: app.panels.editor.show_grid,
                show_axes: app.panels.editor.show_axes,
                flat: app.panels.editor.flat,
                ..Default::default()
            };
            let mesh = app.panels.editor.mesh.as_ref().map(|m| (app.panels.editor.mesh_id, m.clone()));
            let response = paint_mesh_viewport(ui, app.renderer.clone(), &camera, opts, mesh);
            let rect = response.rect;
            let pointer = response.interact_pointer_pos();
            if response.drag_started_by(egui::PointerButton::Primary) && app.panels.editor.drag_selected {
                if let (Some(pos), Some(i)) = (pointer, pointer.and_then(|p| pick_marker(&scene, &camera, rect, p))) {
                    if let Some(obj) = scene.objects.get(i) {
                        app.panels.editor.undo.push(scene.objects.clone());
                        app.panels.editor.redo.clear();
                        app.panels.editor.selected_object = Some(i);
                        app.panels.editor.drag_object = Some(i);
                        app.panels.editor.drag_start = Some((obj.position, pos));
                        app.panels.editor.dirty = true;
                    }
                }
            }
            if response.dragged_by(egui::PointerButton::Primary) {
                if let (Some(i), Some((start_pos, start_ptr)), Some(ptr)) = (
                    app.panels.editor.drag_object,
                    app.panels.editor.drag_start,
                    pointer,
                ) {
                    let forward = camera.target.sub(camera.eye()).normalized();
                    let right = forward.cross(Vec3::new(0.0, 1.0, 0.0)).normalized();
                    let up = right.cross(forward).normalized();
                    let scale = 2.0 * camera.distance * (camera.fov.to_radians() * 0.5).tan()
                        / rect.height().max(1.0);
                    let dx = (ptr.x - start_ptr.x) * scale;
                    let dy = (ptr.y - start_ptr.y) * scale;
                    let mut pos = Vec3::new(start_pos[0], start_pos[1], start_pos[2])
                        .add(right.scale(dx))
                        .add(up.scale(-dy));
                    if app.panels.editor.snap {
                        pos = Vec3::new(
                            (pos.x * 4.0).round() / 4.0,
                            (pos.y * 4.0).round() / 4.0,
                            (pos.z * 4.0).round() / 4.0,
                        );
                    }
                    if let Some(obj) = app
                        .panels
                        .editor
                        .scene
                        .as_mut()
                        .and_then(|s| s.objects.get_mut(i))
                    {
                        obj.position = [pos.x, pos.y, pos.z];
                    }
                } else {
                    let d = response.drag_delta();
                    if d != egui::Vec2::ZERO {
                        camera.orbit(d.x, d.y);
                    }
                }
            }
            if response.drag_stopped_by(egui::PointerButton::Primary) {
                app.panels.editor.drag_object = None;
                app.panels.editor.drag_start = None;
            }
            if response.dragged_by(egui::PointerButton::Secondary)
                || response.dragged_by(egui::PointerButton::Middle)
            {
                let d = response.drag_delta();
                if d != egui::Vec2::ZERO {
                    camera.pan(d.x, d.y, rect.height());
                }
            }
            let scroll = ui.input(|i| i.smooth_scroll_delta.y);
            if response.hovered() && scroll != 0.0 {
                camera.zoom(scroll);
            }
            app.panels.editor.camera = camera;

            if app.panels.editor.show_objects && rect.width() > 1.0 && rect.height() > 1.0 {
                let mvp = camera.mvp(rect.width() / rect.height());
                let painter = ui.painter_at(rect);
                let selected = app.panels.editor.selected_object;
                let mut picked: Option<(usize, f32)> = None;
                for (i, obj) in scene.objects.iter().enumerate() {
                    let p = Vec3::new(obj.position[0], obj.position[1], obj.position[2]);
                    let Some(pos) = project(mvp, p, rect) else { continue };
                    let is_sel = selected == Some(i);
                    let color = if is_sel { theme::ACCENT } else { egui::Color32::from_rgb(0x6a, 0xb8, 0xd8) };
                    let r = if is_sel { 6.0 } else { 3.5 };
                    painter.circle_filled(pos, r, color);
                    painter.circle_stroke(pos, r + 1.0, egui::Stroke::new(1.0, egui::Color32::from_black_alpha(180)));
                    if app.panels.editor.show_bounds && obj.kind == "placement" {
                        draw_bounds_box(&painter, mvp, obj, rect, if is_sel { theme::ACCENT } else { color });
                    }
                    if let Some(pointer) = response.hover_pos() {
                        let d = pointer.distance(pos);
                        if d < 10.0 && picked.map(|(_, best)| d < best).unwrap_or(true) {
                            picked = Some((i, d));
                        }
                    }
                }
                if response.clicked() {
                    if let Some((i, _)) = picked {
                        app.panels.editor.selected_object = Some(i);
                    }
                }
            }
            if app.panels.editor.loading {
                ui.ctx().request_repaint_after(std::time::Duration::from_millis(100));
            }
        });
}

fn draw_bounds_box(
    painter: &egui::Painter,
    mvp: Mat4,
    obj: &SceneObject,
    rect: egui::Rect,
    color: egui::Color32,
) {
    let c = Vec3::new(obj.position[0], obj.position[1], obj.position[2]);
    let h = Vec3::new(
        (obj.scale[0].abs() * 0.5).max(0.01),
        (obj.scale[1].abs() * 0.5).max(0.01),
        (obj.scale[2].abs() * 0.5).max(0.01),
    );
    let corners = [
        Vec3::new(c.x - h.x, c.y - h.y, c.z - h.z),
        Vec3::new(c.x + h.x, c.y - h.y, c.z - h.z),
        Vec3::new(c.x + h.x, c.y + h.y, c.z - h.z),
        Vec3::new(c.x - h.x, c.y + h.y, c.z - h.z),
        Vec3::new(c.x - h.x, c.y - h.y, c.z + h.z),
        Vec3::new(c.x + h.x, c.y - h.y, c.z + h.z),
        Vec3::new(c.x + h.x, c.y + h.y, c.z + h.z),
        Vec3::new(c.x - h.x, c.y + h.y, c.z + h.z),
    ];
    let projected: Vec<Option<egui::Pos2>> = corners.iter().map(|p| project(mvp, *p, rect)).collect();
    let edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)];
    let stroke = egui::Stroke::new(1.0, color.gamma_multiply(0.55));
    for (a, b) in edges {
        if let (Some(a), Some(b)) = (projected[a], projected[b]) {
            painter.line_segment([a, b], stroke);
        }
    }
}

fn pick_marker(scene: &Scene, camera: &Camera, rect: egui::Rect, pointer: egui::Pos2) -> Option<usize> {
    let mvp = camera.mvp(rect.width() / rect.height());
    let mut best: Option<(usize, f32)> = None;
    for (i, obj) in scene.objects.iter().enumerate() {
        let p = Vec3::new(obj.position[0], obj.position[1], obj.position[2]);
        if let Some(pos) = project(mvp, p, rect) {
            let d = pointer.distance(pos);
            if d < 12.0 && best.map(|(_, b)| d < b).unwrap_or(true) {
                best = Some((i, d));
            }
        }
    }
    best.map(|(i, _)| i)
}

fn project(mvp: Mat4, p: Vec3, rect: egui::Rect) -> Option<egui::Pos2> {
    let m = mvp.0;
    let x = m[0] * p.x + m[4] * p.y + m[8] * p.z + m[12];
    let y = m[1] * p.x + m[5] * p.y + m[9] * p.z + m[13];
    let z = m[2] * p.x + m[6] * p.y + m[10] * p.z + m[14];
    let w = m[3] * p.x + m[7] * p.y + m[11] * p.z + m[15];
    if w.abs() < 1e-6 || z / w < -1.0 || z / w > 1.0 {
        return None;
    }
    let nx = x / w;
    let ny = y / w;
    if !nx.is_finite() || !ny.is_finite() {
        return None;
    }
    Some(egui::pos2(
        rect.left() + (nx * 0.5 + 0.5) * rect.width(),
        rect.top() + (1.0 - (ny * 0.5 + 0.5)) * rect.height(),
    ))
}
