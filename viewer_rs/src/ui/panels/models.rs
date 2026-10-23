//! Model browser with the GPU viewport.

use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver};
use std::sync::Arc;

use eframe::egui;

use crate::app::{paint_mesh_viewport, ViewerApp};
use crate::render::camera::Camera;
use crate::render::gpu::RenderOptions;
use crate::render::mesh::Mesh;
use crate::theme;
use crate::utils::{human_count, human_size, read_text};

#[derive(PartialEq, Eq, Clone, Copy)]
enum Tab {
    Viewport,
    Catalog,
}

#[derive(PartialEq, Eq, Clone, Copy)]
enum SortKey {
    Name,
    Category,
    Size,
}

pub struct ModelsPanel {
    pub query: String,
    pub category: Option<String>,
    sort: SortKey,
    sort_desc: bool,
    list: Vec<usize>,
    selected: Option<usize>,
    dirty: bool,
    pub camera: Camera,
    pub wireframe: bool,
    pub show_grid: bool,
    pub show_axes: bool,
    pub flat: bool,
    pub highlight: bool,
    /// show parts the game hides by default (alternate hand poses)
    pub show_hidden: bool,
    mesh: Option<Arc<Mesh>>,
    mesh_id: u64,
    loading: Option<usize>,
    stats: String,
    detail: Vec<(String, String)>,
    rx: Receiver<(usize, Result<Mesh, String>)>,
    catalog: Option<String>,
    catalog_state: crate::ui::TextState,
    tab: Tab,
    request: Option<String>,
    frame_pending: bool,
    /// Face poses from game_assets/models/face_expressions.json (eyes, mouth, uses).
    poses: Option<Vec<Pose>>,
    pose: Option<usize>,
    pose_rx: Receiver<(u64, Result<std::path::PathBuf, String>)>,
}

/// One facial expression: eye and mouth atlas translations, and how often the
/// game's animations use it.
#[derive(Clone, Copy)]
pub(crate) struct Pose {
    pub eyes: (f32, f32),
    pub mouth: (f32, f32),
    pub uses: u64,
}

impl Pose {
    fn label(&self, index: usize) -> String {
        if index == 0 {
            return "default (as exported)".into();
        }
        format!(
            "#{index}: eyes {:.2},{:.2}  mouth {:.2},{:.2}  ({} uses)",
            self.eyes.0, self.eyes.1, self.mouth.0, self.mouth.1, self.uses
        )
    }
}

/// The BCH a model export came from:
/// `game_assets/models/<rel>/<stem>/<stem>.obj` <- `game_data/<rel>/<stem>.bch`.
pub(crate) fn source_bch(root: &Path, rel_dir: &str, name: &str) -> Option<PathBuf> {
    let parent = Path::new(rel_dir).parent()?;
    Some(root.join("game_data").join(parent).join(format!("{name}.bch")))
}

/// Top poses from the expression catalogue, with the export default first.
pub(crate) fn load_poses(models_dir: &Path) -> Vec<Pose> {
    let mut out = vec![Pose { eyes: (0.0, 0.0), mouth: (0.0, 0.0), uses: 0 }];
    let Ok(text) = std::fs::read_to_string(models_dir.join("face_expressions.json")) else {
        return out;
    };
    let Ok(json) = serde_json::from_str::<serde_json::Value>(&text) else {
        return out;
    };
    let pair = |v: &serde_json::Value| -> (f32, f32) {
        (
            v.get(0).and_then(|x| x.as_f64()).unwrap_or(0.0) as f32,
            v.get(1).and_then(|x| x.as_f64()).unwrap_or(0.0) as f32,
        )
    };
    for pose in json["poses"].as_array().into_iter().flatten().take(40) {
        let p = Pose {
            eyes: pair(&pose["eyes"]),
            mouth: pair(&pose["mouth"]),
            uses: pose["count"].as_u64().unwrap_or(0),
        };
        if p.eyes != (0.0, 0.0) || p.mouth != (0.0, 0.0) {
            out.push(p);
        }
    }
    out
}

impl Default for ModelsPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            category: None,
            sort: SortKey::Name,
            sort_desc: false,
            list: Vec::new(),
            selected: None,
            dirty: true,
            camera: Camera::default(),
            wireframe: false,
            show_grid: true,
            show_axes: true,
            flat: false,
            highlight: false,
            show_hidden: false,
            mesh: None,
            mesh_id: 0,
            loading: None,
            stats: String::new(),
            detail: Vec::new(),
            rx: channel().1,
            catalog: None,
            catalog_state: crate::ui::TextState::default(),
            tab: Tab::Viewport,
            request: None,
            frame_pending: false,
            poses: None,
            pose: None,
            pose_rx: channel().1,
        }
    }
}

impl ModelsPanel {
    pub fn request(&mut self, name: &str) {
        self.request = Some(name.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.category = None;
        self.sort = SortKey::Name;
        self.sort_desc = false;
        self.dirty = true;
    }

    fn sort_list(&mut self, data: &crate::app::Data) {
        let desc = self.sort_desc;
        self.list.sort_by(|a, b| {
            let ma = &data.models.items[*a];
            let mb = &data.models.items[*b];
            let ord = match self.sort {
                SortKey::Name => ma.name.to_lowercase().cmp(&mb.name.to_lowercase()),
                SortKey::Category => ma.category.to_lowercase().cmp(&mb.category.to_lowercase()),
                SortKey::Size => ma.size.cmp(&mb.size),
            };
            if desc { ord.reverse() } else { ord }
        });
    }

    fn refresh(&mut self, app: &ViewerApp) {
        let Some(data) = app.data() else { return };
        self.list = data.models.search(&self.query, self.category.as_deref());
        self.sort_list(data);
        self.dirty = false;
    }

    fn start_load(&mut self, pool: &crate::utils::Pool, index: usize, path: &std::path::Path) {
        if self.selected == Some(index) && self.mesh.is_some() && self.loading.is_none() {
            return;
        }
        self.selected = Some(index);
        self.loading = Some(index);
        self.detail.clear();
        let (tx, rx) = channel();
        self.rx = rx;
        let path = path.to_path_buf();
        pool.submit(move || {
            let result = crate::render::mesh::load_obj(&path);
            let _ = tx.send((index, result));
        });
    }

    fn poll(&mut self, data: Option<&crate::app::Data>) {
        let Ok((index, result)) = self.rx.try_recv() else { return };
        let _ = data;
        self.loading = None;
        if self.selected != Some(index) {
            return;
        }
        match result {
            Ok(mesh) => {
                self.camera.frame(&mesh.bounds);
                self.stats = format!(
                    "{}  \u{b7}  {}{}  \u{b7}  {} tris  \u{b7}  {} verts",
                    mesh.material,
                    human_count(mesh.parts),
                    if mesh.parts == 1 { " mesh" } else { " meshes" },
                    human_count(mesh.triangle_count),
                    human_count(mesh.vertex_count)
                );
                if let Some(data) = data {
                    if let Some(model) = data.models.items.get(index) {
                        self.detail = vec![
                            ("model".into(), model.name.clone()),
                            ("in-game name".into(), model.display_name.clone().unwrap_or_else(|| "-".into())),
                            ("category".into(), model.category.clone()),
                            ("meshes / objects".into(), human_count(mesh.parts)),
                            ("triangles".into(), human_count(mesh.triangle_count)),
                            ("vertices".into(), human_count(mesh.vertex_count)),
                            ("dimensions".into(), mesh.dims_text()),
                            ("raw extents".into(), {
                                let s = mesh.raw_bounds.size();
                                format!("{:.2} x {:.2} x {:.2}", s.x, s.y, s.z)
                            }),
                            ("sidecar files".into(), model.sidecars()),
                            ("directory".into(), model.rel_dir.clone()),
                            ("source".into(), model.obj.to_string_lossy().into_owned()),
                        ];
                        if mesh.non_finite > 0 || mesh.outliers > 0 {
                            self.detail.push((
                                "data repair".into(),
                                format!(
                                    "{} non-finite and {} stray vertices ignored when framing",
                                    human_count(mesh.non_finite),
                                    human_count(mesh.outliers)
                                ),
                            ));
                        }
                    }
                }
                self.mesh = Some(Arc::new(mesh));
                self.mesh_id = self.mesh_id.wrapping_add(1);
                self.pose = None;
            }
            Err(e) => self.stats = format!("failed to load: {e}"),
        }
    }

    fn load_catalog(&mut self, app: &ViewerApp) {
        if self.catalog.is_some() {
            return;
        }
        let path = app.dirs.models.join("MODELS_CATALOG.md");
        self.catalog = Some(read_text(&path).unwrap_or_else(|e| format!("catalog unavailable: {e}")));
    }
}

struct CatalogText {
    state: crate::ui::TextState,
}

impl CatalogText {
    fn ensure(&mut self, text: &str) {
        if self.state.lines.is_empty() {
            self.state.set(text, crate::ui::Lang::Plain);
        }
    }
}

fn find_blender() -> Option<PathBuf> {
    for candidate in [
        PathBuf::from(r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"),
        PathBuf::from(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"),
        PathBuf::from(r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"),
    ] {
        if candidate.is_file() {
            return Some(candidate);
        }
    }
    let path = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path) {
        let exe = dir.join("blender.exe");
        if exe.is_file() {
            return Some(exe);
        }
    }
    None
}

/// Opens the model in Blender. The glTF carries textures and materials, so it is
/// preferred over the OBJ; the viewport switches to material preview and frames
/// the model.
pub fn open_in_blender(obj: &Path) -> Result<(), String> {
    let blender = find_blender().ok_or_else(|| {
        "Blender not found. Install Blender or add blender.exe to PATH.".to_string()
    })?;
    let gltf = obj.with_extension("gltf");
    let (source, import) = if gltf.is_file() {
        (gltf, "bpy.ops.import_scene.gltf")
    } else {
        (obj.to_path_buf(), "bpy.ops.wm.obj_import")
    };
    let script = std::env::temp_dir().join("dqxi_open_in_blender.py");
    let path = source.to_string_lossy().replace('\\', "/");
    std::fs::write(
        &script,
        format!(
            r#"import bpy
bpy.ops.wm.read_homefile(use_empty=True)
{import}(filepath={path:?})
# parts the game hides by default (alternate hand poses) come in hidden
for ob in bpy.context.scene.objects:
    if ob.get("dqxi_hidden"):
        ob.hide_set(True)
        ob.hide_render = True
def frame():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            area.spaces.active.shading.type = 'MATERIAL'
            region = next(r for r in area.regions if r.type == 'WINDOW')
            with bpy.context.temp_override(window=window, area=area, region=region):
                bpy.ops.view3d.view_all()
    return None
bpy.app.timers.register(frame, first_interval=0.5)
"#
        ),
    )
    .map_err(|e| format!("cannot write Blender script: {e}"))?;
    std::process::Command::new(blender)
        .arg("--python")
        .arg(&script)
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("cannot launch Blender: {e}"))
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    {
        let panel = &mut app.panels.models;
        let data = app.data.as_deref();
        panel.poll(data);
    }

    if !app.data().is_some_and(|d| d.models.ready) {
        ui.label(theme::dim_label("indexing models\u{2026}"));
        return;
    }
    if app.panels.models.dirty {
        let panel = &mut app.panels.models;
        let Some(data) = app.data.as_deref() else { return };
        panel.list = data.models.search(&panel.query, panel.category.as_deref());
        panel.sort_list(data);
        panel.dirty = false;
        let auto = panel.selected.is_none().then(|| panel.list.first().copied()).flatten();
        if panel.request.is_none() {
            if let Some(index) = auto {
                let path = data.models.items[index].obj.clone();
                panel.start_load(&app.pool, index, &path);
            }
        }
        if let Some(name) = panel.request.take() {
            let found = panel
                .list
                .iter()
                .copied()
                .find(|i| data.models.items[*i].name.eq_ignore_ascii_case(&name))
                .or_else(|| {
                    data.models
                        .items
                        .iter()
                        .position(|m| m.name.eq_ignore_ascii_case(&name))
                });
            if let Some(index) = found {
                let path = data.models.items[index].obj.clone();
                panel.start_load(&app.pool, index, &path);
            }
        }
    }

    ui.horizontal(|ui| {
        ui.label(theme::heading("Model library"));
        ui.label(theme::faint_label("extracted NW4C meshes, grouped by category"));
    });
    ui.separator();

    egui::Panel::left("models_list")
        .exact_size(330.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                let changed = ui
                    .add(
                        egui::TextEdit::singleline(&mut app.panels.models.query)
                            .hint_text("Search models\u{2026}"),
                    )
                    .changed();
                if changed {
                    app.panels.models.dirty = true;
                }
                if ui.button("\u{2715}").on_hover_text("clear filter").clicked() {
                    app.panels.models.query.clear();
                    app.panels.models.category = None;
                    app.panels.models.dirty = true;
                }
            });
            let categories: Vec<(String, usize)> = app
                .data()
                .map(|d| d.models.categories().to_vec())
                .unwrap_or_default();
            let label = app
                .panels
                .models
                .category
                .clone()
                .unwrap_or_else(|| "All categories".into());
            egui::ComboBox::from_id_salt("model_category")
                .selected_text(label)
                .width(ui.available_width())
                .show_ui(ui, |ui| {
                    if ui.selectable_label(app.panels.models.category.is_none(), "All categories").clicked() {
                        app.panels.models.category = None;
                        app.panels.models.dirty = true;
                    }
                    for (name, count) in categories {
                        let selected = app.panels.models.category.as_deref() == Some(name.as_str());
                        if ui.selectable_label(selected, format!("{name}  ({count})")).clicked() {
                            app.panels.models.category = Some(name);
                            app.panels.models.dirty = true;
                        }
                    }
                });
            ui.horizontal(|ui| {
                egui::ComboBox::from_id_salt("model_sort")
                    .selected_text(match app.panels.models.sort {
                        SortKey::Name => "Sort: name",
                        SortKey::Category => "Sort: category",
                        SortKey::Size => "Sort: size",
                    })
                    .show_ui(ui, |ui| {
                        for (key, label) in [(SortKey::Name, "Name"), (SortKey::Category, "Category"), (SortKey::Size, "Size")] {
                            if ui.selectable_label(app.panels.models.sort == key, label).clicked() {
                                app.panels.models.sort = key;
                                app.panels.models.dirty = true;
                            }
                        }
                    });
                if ui.button(if app.panels.models.sort_desc { "Descending" } else { "Ascending" }).clicked() {
                    app.panels.models.sort_desc = !app.panels.models.sort_desc;
                    app.panels.models.dirty = true;
                }
            });
            ui.separator();
            let total = app.data().map(|d| d.models.items.len()).unwrap_or(0);
            ui.label(theme::faint_label(format!(
                "{} of {} models",
                human_count(app.panels.models.list.len()),
                human_count(total)
            )));
            let selected = app.panels.models.selected;
            let list = app.panels.models.list.clone();
            let mut clicked = None;
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("models_list_scroll")
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::remainder().at_least(110.0))
                .column(Column::initial(100.0).at_least(70.0))
                .column(Column::exact(78.0))
                .header(20.0, |mut header| {
                    for title in ["Model", "Category", "OBJ"] {
                        header.col(|ui| {
                            ui.label(theme::faint_label(title));
                        });
                    }
                })
                .body(|body| {
                    body.rows(18.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let Some(model) = app.data.as_deref().and_then(|d| d.models.items.get(index))
                        else {
                            return;
                        };
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            let label = model.display_name.clone().unwrap_or_else(|| model.name.clone());
                            let resp = ui.label(egui::RichText::new(label).size(12.0));
                            if model.display_name.is_some() {
                                resp.on_hover_text(format!("model id: {}", model.name));
                            }
                        });
                        row.col(|ui| {
                            ui.label(theme::dim_label(model.category.clone()));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(human_size(model.size)));
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(index) = clicked {
                let path = app
                    .data()
                    .and_then(|d| d.models.items.get(index))
                    .map(|m| m.obj.clone());
                let name = app
                    .data()
                    .and_then(|d| d.models.items.get(index))
                    .map(|m| m.name.clone())
                    .unwrap_or_default();
                let panel = &mut app.panels.models;
                panel.stats = format!("Loading {name}\u{2026}");
                if let Some(path) = path {
                    panel.start_load(&app.pool, index, &path);
                }
            }
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                let name = app
                    .panels
                    .models
                    .selected
                    .and_then(|i| app.data().and_then(|d| d.models.items.get(i)))
                    .map(|m| m.name.clone())
                    .unwrap_or_else(|| "No model selected".into());
                ui.label(theme::heading(name));
                ui.label(theme::dim_label(app.panels.models.stats.clone()));
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.button("Catalog").clicked() {
                        app.panels.models.tab = Tab::Catalog;
                    }
                    if ui.button("Viewport").clicked() {
                        app.panels.models.tab = Tab::Viewport;
                    }
                    let obj = app
                        .panels
                        .models
                        .selected
                        .and_then(|i| app.data().and_then(|d| d.models.items.get(i)))
                        .map(|m| m.obj.clone());
                    if let Some(obj) = obj {
                        if ui.button("Open in Blender").clicked() {
                            match open_in_blender(&obj) {
                                Ok(()) => app.status = "opened model in Blender".into(),
                                Err(e) => app.status = e,
                            }
                        }
                    }
                });
            });
            ui.separator();
            match app.panels.models.tab {
                Tab::Viewport => viewport(app, ui),
                Tab::Catalog => catalog(app, ui),
            }
        });
}

impl ModelsPanel {
    /// Bakes the selected pose with tools/face_expressions.py on the pool.
    fn bake_pose(&mut self, pool: &crate::utils::Pool, root: &Path, model: &crate::data::models::Model, index: usize, pose: Pose) {
        let Some(bch) = source_bch(root, &model.rel_dir, &model.name) else { return };
        let out = std::env::temp_dir().join(format!("dqxi_face_{}_{index}.png", model.name));
        let tool = root.join("tools").join("face_expressions.py");
        let (tx, rx) = channel();
        self.pose_rx = rx;
        let id = self.mesh_id;
        self.stats = format!("baking expression #{index}\u{2026}");
        pool.submit(move || {
            let result = std::process::Command::new("python")
                .arg(&tool)
                .arg("bake")
                .arg(&bch)
                .arg(format!("--eyes={},{}", pose.eyes.0, pose.eyes.1))
                .arg(format!("--mouth={},{}", pose.mouth.0, pose.mouth.1))
                .arg("--out")
                .arg(&out)
                .output()
                .map_err(|e| format!("cannot run python: {e}"))
                .and_then(|o| {
                    if o.status.success() {
                        Ok(out)
                    } else {
                        Err(String::from_utf8_lossy(&o.stderr).trim().to_string())
                    }
                });
            let _ = tx.send((id, result));
        });
    }

    /// Swaps the face texture once a bake finishes.
    fn poll_pose(&mut self) {
        let Ok((id, result)) = self.pose_rx.try_recv() else { return };
        if id != self.mesh_id {
            return; // a different model was loaded meanwhile
        }
        match result {
            Ok(png) => {
                if let Some(mesh) = self.mesh.as_ref() {
                    let mut mesh = (**mesh).clone();
                    for group in &mut mesh.groups {
                        let is_face = group
                            .texture_path
                            .as_ref()
                            .and_then(|p| p.file_name())
                            .map(|n| n.to_string_lossy().contains("_composite") || n.to_string_lossy().starts_with("dqxi_face_"))
                            .unwrap_or(false);
                        if is_face {
                            group.texture_path = Some(png.clone());
                        }
                    }
                    self.mesh = Some(Arc::new(mesh));
                    self.mesh_id = self.mesh_id.wrapping_add(1);
                    self.stats = "expression applied".into();
                }
            }
            Err(e) => self.stats = format!("expression bake failed: {e}"),
        }
    }

    fn has_layered_face(&self) -> bool {
        self.mesh.as_ref().is_some_and(|m| {
            m.groups.iter().any(|g| {
                g.texture_path
                    .as_ref()
                    .and_then(|p| p.file_name())
                    .is_some_and(|n| {
                        let n = n.to_string_lossy();
                        n.contains("_composite") || n.starts_with("dqxi_face_")
                    })
            })
        })
    }
}

fn viewport(app: &mut ViewerApp, ui: &mut egui::Ui) {
    app.panels.models.poll_pose();
    // diagnostics first, so it is never clipped by the viewport
    if let Ok(renderer) = app.renderer.lock() {
        let error = renderer
            .error
            .as_ref()
            .map(|e| format!("   ERROR: {e}"))
            .unwrap_or_default();
        ui.label(theme::faint_label(format!(
            "GL {}  \u{b7}  on GPU: {}  \u{b7}  drawn: {} tris  \u{b7}  paints: {}  \u{b7}  {}{}",
            renderer.version.trim(),
            if renderer.has_mesh() { 1 } else { 0 },
            human_count(renderer.last_drawn),
            renderer.last_paints,
            renderer.mesh_label,
            error,
        )));
    }
    let mut camera = app.panels.models.camera;
    let opts = RenderOptions {
        wireframe: app.panels.models.wireframe,
        show_grid: app.panels.models.show_grid,
        show_axes: app.panels.models.show_axes,
        flat: app.panels.models.flat,
        highlight: app.panels.models.highlight,
        show_hidden: app.panels.models.show_hidden,
        ..Default::default()
    };
    let mut refresh = false;
    let mesh = app
        .panels
        .models
        .mesh
        .as_ref()
        .map(|m| (app.panels.models.mesh_id, m.clone()));
    let response = paint_mesh_viewport(ui, app.renderer.clone(), &camera, opts, mesh);
    if response.dragged_by(egui::PointerButton::Primary) {
        let d = response.drag_delta();
        if d != egui::Vec2::ZERO {
            camera.orbit(d.x, d.y);
            refresh = true;
        }
    }
    if response.dragged_by(egui::PointerButton::Secondary)
        || response.dragged_by(egui::PointerButton::Middle)
    {
        let d = response.drag_delta();
        if d != egui::Vec2::ZERO {
            camera.pan(d.x, d.y, response.rect.height());
            refresh = true;
        }
    }
    let scroll = ui.input(|i| i.smooth_scroll_delta.y);
    if response.hovered() && scroll != 0.0 {
        camera.zoom(scroll);
        refresh = true;
    }
    if response.double_clicked() {
        camera = Camera::default();
        app.panels.models.frame_pending = true;
        refresh = true;
    }
    app.panels.models.camera = camera;
    if refresh {
        ui.ctx().request_repaint();
    }
    if app.panels.models.loading.is_some() {
        ui.ctx().request_repaint_after(std::time::Duration::from_millis(120));
    }
    if let Ok(renderer) = app.renderer.lock() {
        if !renderer.has_mesh() {
            // first paint / upload still pending
            ui.ctx().request_repaint_after(std::time::Duration::from_millis(150));
        }
    }

    ui.add_space(4.0);
    ui.horizontal(|ui| {
        let panel = &mut app.panels.models;
        ui.checkbox(&mut panel.wireframe, "Wireframe");
        ui.checkbox(&mut panel.show_grid, "Grid");
        ui.checkbox(&mut panel.show_axes, "Axes");
        ui.checkbox(&mut panel.flat, "Flat shading");
        ui.checkbox(&mut panel.highlight, "Highlight");
        ui.checkbox(&mut panel.show_hidden, "Hand variants")
            .on_hover_text("Characters carry several hand poses; the game shows one. Tick to see them all.");
        ui.checkbox(&mut panel.camera.invert_horizontal, "Invert horizontal drag")
            .on_hover_text("Flip which way the model turns when you drag sideways");
        ui.checkbox(&mut panel.camera.invert_vertical, "Invert vertical drag")
            .on_hover_text("Flip which way the model tips when you drag up/down");
        if ui.button("Reset view").clicked() {
            panel.camera = Camera::default();
            panel.frame_pending = true;
        }
        if ui.button("Fit").clicked() {
            panel.frame_pending = true;
        }
        if panel.has_layered_face() {
            let poses = panel.poses.get_or_insert_with(|| load_poses(&app.dirs.models)).clone();
            let current = panel.pose.unwrap_or(0);
            let mut chosen = None;
            egui::ComboBox::from_id_salt("face_pose")
                .selected_text(format!("Expression: {}", if current == 0 { "default".to_string() } else { format!("#{current}") }))
                .width(170.0)
                .show_ui(ui, |ui| {
                    for (i, pose) in poses.iter().enumerate() {
                        if ui.selectable_label(current == i, pose.label(i)).clicked() {
                            chosen = Some(i);
                        }
                    }
                })
                .response
                .on_hover_text("Facial expressions used by the game's animations, most common first");
            if let Some(i) = chosen {
                let model = panel.selected.and_then(|s| app.data.as_deref().and_then(|d| d.models.items.get(s).cloned()));
                if let Some(model) = model {
                    panel.pose = Some(i);
                    panel.bake_pose(&app.pool, &app.dirs.root, &model, i, poses[i]);
                }
            }
        }
        if ui.button("\u{2212}").on_hover_text("zoom out").clicked() {
            panel.camera.zoom_steps(-1.0);
        }
        if ui.button("+").on_hover_text("zoom in").clicked() {
            panel.camera.zoom_steps(1.0);
        }
        ui.label(theme::faint_label("drag: orbit  \u{b7}  right-drag: pan  \u{b7}  wheel: zoom  \u{b7}  double-click: reset"));
    });
    ui.add_space(4.0);
    ui.separator();
    let detail = app.panels.models.detail.clone();
    egui::ScrollArea::vertical()
        .id_salt("model_detail")
        .max_height(170.0)
        .show(ui, |ui| {
            if detail.is_empty() {
                ui.label(theme::faint_label("Select a model to inspect it."));
            } else {
                crate::ui::kv_rows(ui, &detail.iter().map(|(k, v)| (k.as_str(), v.clone())).collect::<Vec<_>>());
            }
        });
}

fn catalog(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if app.panels.models.catalog.is_none() {
        let path = app.dirs.models.join("MODELS_CATALOG.md");
        app.panels.models.catalog =
            Some(read_text(&path).unwrap_or_else(|e| format!("catalog unavailable: {e}")));
    }
    let text = app.panels.models.catalog.clone().unwrap_or_default();
    if app.panels.models.catalog_state.lines.is_empty() && !text.is_empty() {
        app.panels.models.catalog_state.set(&text, crate::ui::Lang::Plain);
    }
    let state = std::mem::take(&mut app.panels.models.catalog_state);
    crate::ui::text_view(ui, "models_catalog_view", &state, false);
    app.panels.models.catalog_state = state;
}




