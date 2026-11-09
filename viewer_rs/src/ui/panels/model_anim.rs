//! Animation player for the model viewport: pick a motion file, pick one of its
//! skeletal animations and play it. The skeleton, skin weights and per-frame bone
//! matrices come from `SpicaRef rig` (see `data/rig.rs`); skinning runs on the CPU
//! and the posed vertices are streamed into the already uploaded mesh.

use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver};
use std::sync::Arc;

use eframe::egui;

use crate::data::rig::{Rig, Skin};
use crate::render::mesh::Mesh;
use crate::theme;
use crate::utils::Pool;

/// The game runs its skeletal animations at 30 frames per second.
const FPS: f32 = 30.0;
/// How long a model stays selected before its suggested motion loads (so that
/// arrowing through the list does not start one conversion per row).
const AUTO_LOAD_DELAY: f64 = 0.6;

pub struct Motion {
    pub name: String,
    pub bch: PathBuf,
}

pub struct AnimPlayer {
    motions: Option<Vec<Motion>>,
    motion: Option<usize>,
    motion_filter: String,
    anim_filter: String,
    rig: Option<Arc<Rig>>,
    skin: Option<Skin>,
    skin_mesh: u64,
    anim: Option<usize>,
    time: f32,
    pub playing: bool,
    speed: f32,
    looping: bool,
    rx: Receiver<(u64, Result<Rig, String>)>,
    token: u64,
    loading: bool,
    status: String,
    posed: Option<(u64, Arc<Vec<f32>>)>,
    serial: u64,
    dirty: bool,
    /// context time at which the suggested motion should load
    auto_at: Option<f64>,
    suggested: Vec<usize>,
    model: String,
    model_bch: Option<PathBuf>,
    /// the viewport still shows an animated pose that must be replaced by the bind pose
    restore: bool,
}

impl Default for AnimPlayer {
    fn default() -> Self {
        Self {
            motions: None,
            motion: None,
            motion_filter: String::new(),
            anim_filter: String::new(),
            rig: None,
            skin: None,
            skin_mesh: 0,
            anim: None,
            time: 0.0,
            playing: false,
            speed: 1.0,
            looping: true,
            rx: channel().1,
            token: 0,
            loading: false,
            status: String::new(),
            posed: None,
            serial: 0,
            dirty: false,
            auto_at: None,
            suggested: Vec::new(),
            model: String::new(),
            model_bch: None,
            restore: false,
        }
    }
}

/// Motion packs that belong to a model, from the game's naming: `m100x` uses
/// `m100_*`, `ani00001a` uses `a001_*`, `r001x` uses `r001_*`, `cha01xxx` uses `pc001_*`.
fn motion_key(model: &str) -> Option<String> {
    let m = model.to_ascii_lowercase();
    let digits = |s: &str, n: usize| -> Option<u32> {
        let d: String = s.chars().take_while(|c| c.is_ascii_digit()).take(n).collect();
        (d.len() == n).then(|| d.parse().ok()).flatten()
    };
    if let Some(rest) = m.strip_prefix("ani") {
        return Some(format!("a{:03}_", digits(rest, 5)?));
    }
    if let Some(rest) = m.strip_prefix("cha") {
        return Some(format!("pc{:03}_", digits(rest, 2)?));
    }
    if let Some(rest) = m.strip_prefix('m') {
        return Some(format!("m{:03}_", digits(rest, 3)?));
    }
    if let Some(rest) = m.strip_prefix('r') {
        return Some(format!("r{:03}_", digits(rest, 3)?));
    }
    None
}

fn scan_motions(root: &Path) -> Vec<Motion> {
    let dir = root.join("game_data").join("packs").join("3d").join("motion");
    let mut out = Vec::new();
    let Ok(entries) = std::fs::read_dir(&dir) else { return out };
    for entry in entries.flatten() {
        let path = entry.path();
        let Some(bch) = std::fs::read_dir(&path).ok().and_then(|d| {
            d.flatten()
                .map(|e| e.path())
                .find(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("bch")))
        }) else {
            continue;
        };
        out.push(Motion { name: entry.file_name().to_string_lossy().into_owned(), bch });
    }
    out.sort_by(|a, b| a.name.cmp(&b.name));
    out
}

impl AnimPlayer {
    /// A different model was loaded: drop the rig and pose, remember what to suggest.
    pub fn model_changed(&mut self, root: &Path, name: &str, model_bch: Option<PathBuf>, now: f64) {
        self.rig = None;
        self.skin = None;
        self.anim = None;
        self.time = 0.0;
        self.playing = false;
        self.posed = None;
        self.restore = false;
        self.loading = false;
        self.token = self.token.wrapping_add(1);
        self.status.clear();
        self.model = name.to_string();
        self.model_bch = model_bch;
        let motions = self.motions.get_or_insert_with(|| scan_motions(root));
        self.suggested = match motion_key(name) {
            Some(key) => motions
                .iter()
                .enumerate()
                .filter(|(_, m)| m.name.starts_with(&key))
                .map(|(i, _)| i)
                .collect(),
            None => Vec::new(),
        };
        // prefer the field motions (walking, idling) when a model has several packs
        self.suggested.sort_by_key(|&i| !motions[i].name.ends_with("_fld"));
        self.motion = None;
        self.auto_at = self.suggested.first().map(|_| now + AUTO_LOAD_DELAY);
    }

    fn start_load(&mut self, pool: &Pool, root: &Path, motion: usize) {
        let (Some(model_bch), Some(motions)) = (self.model_bch.clone(), self.motions.as_ref()) else {
            self.status = "this model has no source BCH to animate".into();
            return;
        };
        let Some(m) = motions.get(motion) else { return };
        self.motion = Some(motion);
        self.rig = None;
        self.skin = None;
        self.anim = None;
        self.playing = false;
        self.time = 0.0;
        self.loading = true;
        self.token = self.token.wrapping_add(1);
        self.status = format!("loading {}\u{2026}", m.name);
        let (tx, rx) = channel();
        self.rx = rx;
        let token = self.token;
        let motion_bch = m.bch.clone();
        let exe = root
            .join("tools")
            .join("spica_ref")
            .join("bin")
            .join("Release")
            .join("net9.0")
            .join("SpicaRef.exe");
        let cache = root.join("build").join("rig_cache");
        let out = cache.join(format!("{}__{}.bin", self.model, m.name));
        pool.submit(move || {
            let result = (|| {
                if !out.is_file() {
                    if !exe.is_file() {
                        return Err("build tools/spica_ref first: dotnet build tools/spica_ref -c Release".to_string());
                    }
                    std::fs::create_dir_all(&cache).map_err(|e| e.to_string())?;
                    let tmp = out.with_extension("tmp");
                    let output = std::process::Command::new(&exe)
                        .arg("rig")
                        .arg(&model_bch)
                        .arg(&motion_bch)
                        .arg(&tmp)
                        .output()
                        .map_err(|e| format!("cannot run SpicaRef: {e}"))?;
                    if !output.status.success() || !tmp.is_file() {
                        let _ = std::fs::remove_file(&tmp);
                        return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
                    }
                    std::fs::rename(&tmp, &out).map_err(|e| e.to_string())?;
                }
                Rig::load(&out)
            })();
            let _ = tx.send((token, result));
        });
    }

    fn poll(&mut self) {
        let Ok((token, result)) = self.rx.try_recv() else { return };
        if token != self.token {
            return;
        }
        self.loading = false;
        match result {
            Ok(rig) => {
                let usable = rig.animations.iter().filter(|a| !a.tracks.is_empty()).count();
                self.status = format!(
                    "{} animations ({} match this skeleton)",
                    rig.animations.len(),
                    usable
                );
                self.anim = rig.animations.iter().position(|a| a.tracks.len() > 8);
                self.rig = Some(Arc::new(rig));
                self.skin_mesh = 0;
                self.time = 0.0;
                self.playing = self.anim.is_some();
                self.dirty = true;
            }
            Err(e) => self.status = format!("animation load failed: {e}"),
        }
    }

    fn animation_length(&self) -> f32 {
        self.rig
            .as_ref()
            .zip(self.anim)
            .and_then(|(r, i)| r.animations.get(i))
            .map(|a| a.frames.max(1.0))
            .unwrap_or(1.0)
    }

    fn select_animation(&mut self, anim: Option<usize>) {
        self.anim = anim;
        self.time = 0.0;
        self.dirty = true;
        if anim.is_none() {
            self.playing = false;
        }
    }

    /// Step the clock, handle keys and pose the mesh. Returns the vertex set to
    /// draw and whether the mesh must be re-uploaded to return to the bind pose.
    pub fn tick(&mut self, ctx: &egui::Context, mesh: Option<&Arc<Mesh>>, mesh_id: u64, pool: &Pool, root: &Path) -> bool {
        self.poll();
        let now = ctx.input(|i| i.time);
        if let Some(at) = self.auto_at {
            if now >= at {
                self.auto_at = None;
                if let Some(&first) = self.suggested.first() {
                    if self.motion.is_none() && !self.loading {
                        self.start_load(pool, root, first);
                    }
                }
            } else {
                ctx.request_repaint_after(std::time::Duration::from_millis(((at - now) * 1000.0) as u64 + 20));
            }
        }
        if self.loading {
            ctx.request_repaint_after(std::time::Duration::from_millis(100));
        }
        if !ctx.egui_wants_keyboard_input() {
            let (space, left, right, shift) = ctx.input(|i| {
                (
                    i.key_pressed(egui::Key::Space),
                    i.key_pressed(egui::Key::ArrowLeft),
                    i.key_pressed(egui::Key::ArrowRight),
                    i.modifiers.shift,
                )
            });
            if space && self.anim.is_some() {
                self.playing = !self.playing;
            }
            if (left || right) && self.anim.is_some() {
                let step = if shift { 10.0 } else { 1.0 };
                self.playing = false;
                self.time = (self.time + if right { step } else { -step }).clamp(0.0, self.animation_length());
                self.dirty = true;
            }
        }
        let (Some(rig), Some(mesh)) = (self.rig.clone(), mesh) else {
            return std::mem::take(&mut self.restore);
        };
        if self.playing {
            let dt = ctx.input(|i| i.unstable_dt).min(0.1);
            let length = self.animation_length();
            self.time += dt * FPS * self.speed;
            if self.time >= length {
                if self.looping {
                    self.time %= length;
                } else {
                    self.time = length;
                    self.playing = false;
                }
            }
            self.dirty = true;
            ctx.request_repaint();
        }
        if self.skin_mesh != mesh_id {
            self.skin = Some(rig.bind_to(&mesh.vertices));
            self.skin_mesh = mesh_id;
            self.dirty = true;
        }
        if self.dirty {
            self.dirty = false;
            if let Some(skin) = &self.skin {
                if self.anim.is_some() && skin.matched > 0 {
                    let matrices = rig.skin_matrices(self.anim, self.time);
                    self.serial += 1;
                    self.posed = Some((self.serial, Arc::new(skin.pose(&rig, &matrices))));
                    self.restore = true;
                } else if self.posed.take().is_some() {
                    return std::mem::take(&mut self.restore);
                }
            }
        }
        false
    }

    pub fn posed(&self) -> Option<(u64, Arc<Vec<f32>>)> {
        self.posed.clone()
    }

    pub fn ui(&mut self, ui: &mut egui::Ui, pool: &Pool, root: &Path) {
        let taken = self.motions.take();
        let motions = taken.unwrap_or_default();
        let had_motions = !motions.is_empty();
        ui.horizontal_wrapped(|ui| {
            ui.label(theme::faint_label("Animation"));
            let current = self
                .motion
                .and_then(|i| motions.get(i))
                .map(|m| m.name.clone())
                .unwrap_or_else(|| "choose motion pack".into());
            let mut chosen = None;
            egui::ComboBox::from_id_salt("anim_motion")
                .selected_text(current)
                .width(190.0)
                .show_ui(ui, |ui| {
                    ui.add(egui::TextEdit::singleline(&mut self.motion_filter).hint_text("filter\u{2026}"));
                    let filter = self.motion_filter.to_lowercase();
                    let mut order: Vec<usize> = self.suggested.clone();
                    order.extend((0..motions.len()).filter(|i| !self.suggested.contains(i)));
                    egui::ScrollArea::vertical().max_height(300.0).show(ui, |ui| {
                        for i in order {
                            let m = &motions[i];
                            if !filter.is_empty() && !m.name.to_lowercase().contains(&filter) {
                                continue;
                            }
                            let label = if self.suggested.contains(&i) {
                                format!("{}  (suggested)", m.name)
                            } else {
                                m.name.clone()
                            };
                            if ui.selectable_label(self.motion == Some(i), label).clicked() {
                                chosen = Some(i);
                            }
                        }
                    });
                });
            if let Some(i) = chosen {
                self.auto_at = None;
                self.start_load(pool, root, i);
            }
            if let Some(rig) = self.rig.clone() {
                let current = self
                    .anim
                    .and_then(|i| rig.animations.get(i))
                    .map(|a| a.name.clone())
                    .unwrap_or_else(|| "bind pose".into());
                let mut picked: Option<Option<usize>> = None;
                egui::ComboBox::from_id_salt("anim_clip")
                    .selected_text(current)
                    .width(210.0)
                    .show_ui(ui, |ui| {
                        ui.add(egui::TextEdit::singleline(&mut self.anim_filter).hint_text("filter\u{2026}"));
                        let filter = self.anim_filter.to_lowercase();
                        egui::ScrollArea::vertical().max_height(300.0).show(ui, |ui| {
                            if ui.selectable_label(self.anim.is_none(), "bind pose").clicked() {
                                picked = Some(None);
                            }
                            for (i, a) in rig.animations.iter().enumerate() {
                                if a.tracks.is_empty() || (!filter.is_empty() && !a.name.to_lowercase().contains(&filter)) {
                                    continue;
                                }
                                let label = format!("{}  ({} bones, {:.0} f)", a.name, a.tracks.len(), a.frames);
                                if ui.selectable_label(self.anim == Some(i), label).clicked() {
                                    picked = Some(Some(i));
                                }
                            }
                        });
                    });
                if let Some(p) = picked {
                    self.select_animation(p);
                    self.playing = p.is_some();
                }
                let has = self.anim.is_some();
                if ui
                    .add_enabled(has, egui::Button::new(if self.playing { "Pause" } else { "Play" }))
                    .on_hover_text("Space")
                    .clicked()
                {
                    if !self.playing && self.time >= self.animation_length() {
                        self.time = 0.0;
                    }
                    self.playing = !self.playing;
                }
                let length = self.animation_length();
                let mut time = self.time;
                ui.add_enabled_ui(has, |ui| {
                    ui.spacing_mut().slider_width = 180.0;
                    if ui
                        .add(egui::Slider::new(&mut time, 0.0..=length).show_value(false))
                        .on_hover_text("Left / Right step one frame (Shift: ten)")
                        .changed()
                    {
                        self.time = time;
                        self.playing = false;
                        self.dirty = true;
                    }
                    ui.label(theme::faint_label(format!("{:.0} / {:.0}", self.time, length)));
                    ui.checkbox(&mut self.looping, "Loop");
                    ui.add(egui::DragValue::new(&mut self.speed).range(0.1..=3.0).speed(0.05).prefix("x"))
                        .on_hover_text("Playback speed");
                });
                if let Some(skin) = &self.skin {
                    if skin.matched * 2 < skin.total() {
                        ui.label(
                            egui::RichText::new("skin does not match this mesh").color(theme::WARN).size(11.0),
                        );
                    }
                }
            }
            ui.label(theme::faint_label(self.status.clone()));
        });
        // never turn "not scanned yet" into "scanned, found nothing"
        self.motions = had_motions.then_some(motions);
    }
}
