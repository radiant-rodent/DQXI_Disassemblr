//! Animation player for the model viewport: pick a motion file, pick one of its
//! skeletal animations and play it. The skeleton, skin weights and per-frame bone
//! matrices come from `SpicaRef rig` (see `data/rig.rs`); skinning runs on the CPU
//! and the posed vertices are streamed into the already uploaded mesh.
//!
//! Only the motion packs and clips that actually work on the model's rig are listed:
//! `game_assets/animations/compat.json` (tools/anim_compat.py, from `SpicaRef compat`)
//! says, per distinct skeleton, which sets and clips pose it correctly.

use std::collections::{HashMap, HashSet};
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
    /// compat.json set key (motion folder, or "cs/<path>")
    pub set: String,
    pub bch: PathBuf,
    /// clips of this pack that work on the current rig (None: all of them)
    pub only: Option<HashSet<String>>,
}

/// Bump when `SpicaRef rig` output changes, so stale files in build/rig_cache are not reused.
const RIG_CACHE_VERSION: u32 = 2;

/// game_assets/animations/compat.json: model -> skeleton -> working sets/clips.
struct Compat {
    models: HashMap<String, usize>,
    sets: Vec<Vec<(String, Option<HashSet<String>>)>>,
}

fn load_compat(root: &Path) -> Option<Compat> {
    let text = std::fs::read_to_string(root.join("game_assets").join("animations").join("compat.json")).ok()?;
    let v: serde_json::Value = serde_json::from_str(&text).ok()?;
    let models = v["models"]
        .as_object()?
        .iter()
        .filter_map(|(k, i)| Some((k.clone(), i.as_u64()? as usize)))
        .collect();
    let sets = v["skeletons"]
        .as_array()?
        .iter()
        .map(|sk| {
            sk["sets"]
                .as_object()
                .map(|o| {
                    o.iter()
                        .map(|(name, clips)| {
                            let only = clips
                                .as_array()
                                .map(|a| a.iter().filter_map(|c| c.as_str().map(str::to_string)).collect());
                            (name.clone(), only)
                        })
                        .collect()
                })
                .unwrap_or_default()
        })
        .collect();
    Some(Compat { models, sets })
}

pub struct AnimPlayer {
    /// every pack under 3d/motion (scanned once)
    all_motions: Option<Vec<Motion>>,
    compat: Option<Option<Compat>>,
    /// the packs that work on the current model
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
    /// clips of the loaded pack that work on this rig (None: all)
    only: Option<HashSet<String>>,
    /// result of a running "Export .glb" job
    export_rx: Option<Receiver<String>>,
    /// the viewport still shows an animated pose that must be replaced by the bind pose
    restore: bool,
}

impl Default for AnimPlayer {
    fn default() -> Self {
        Self {
            all_motions: None,
            compat: None,
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
            only: None,
            export_rx: None,
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
        let name = entry.file_name().to_string_lossy().into_owned();
        out.push(Motion { set: name.clone(), name, bch, only: None });
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
        self.model = name.to_string();
        self.model_bch = model_bch;
        let all = self.all_motions.get_or_insert_with(|| scan_motions(root));
        let compat = self.compat.get_or_insert_with(|| load_compat(root));
        let stem = self
            .model_bch
            .as_ref()
            .and_then(|p| p.file_stem())
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_else(|| name.to_string());
        let motions: Vec<Motion> = match compat {
            Some(c) => match c.models.get(&stem).and_then(|&i| c.sets.get(i)) {
                Some(sets) => sets
                    .iter()
                    .filter_map(|(set, only)| {
                        let bch = match set.strip_prefix("cs/") {
                            Some(rel) => root.join("game_data").join("packs").join(format!("{rel}.bch")),
                            None => all.iter().find(|m| &m.name == set)?.bch.clone(),
                        };
                        let name = match set.strip_prefix("cs/") {
                            Some(r) if r.contains("/cs/") => format!("cutscene: {}", r.rsplit('/').next().unwrap_or(r)),
                            Some(r) => format!("in file: {r}"),
                            None => set.clone(),
                        };
                        Some(Motion { name, set: set.clone(), bch, only: only.clone() })
                    })
                    .collect(),
                None => Vec::new(),
            },
            // no compat table yet: offer everything, unverified
            None => all.iter().map(|m| Motion { name: m.name.clone(), set: m.set.clone(), bch: m.bch.clone(), only: None }).collect(),
        };
        self.status = match (compat.is_some(), motions.is_empty()) {
            (false, _) => "game_assets/animations/compat.json missing (python tools/anim_compat.py): all packs listed, unverified".into(),
            (true, true) => "no animation works on this rig".into(),
            (true, false) => format!("{} motion packs work on this rig", motions.len()),
        };
        self.suggested = match motion_key(name) {
            Some(key) => motions
                .iter()
                .enumerate()
                .filter(|(_, m)| m.name.starts_with(&key))
                .map(|(i, _)| i)
                .collect(),
            None => Vec::new(),
        };
        if self.suggested.is_empty() {
            self.suggested = (0..motions.len()).filter(|&i| !motions[i].set.starts_with("cs/")).take(1).collect();
        }
        // prefer the field motions (walking, idling) when a model has several packs
        self.suggested.sort_by_key(|&i| !motions[i].name.ends_with("_fld"));
        self.motion = None;
        self.motions = Some(motions);
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
        let tag: String = m.name.chars().map(|c| if c.is_ascii_alphanumeric() || c == '_' { c } else { '_' }).collect();
        let out = cache.join(format!("{}__{}__v{RIG_CACHE_VERSION}.bin", self.model, tag));
        self.only = m.only.clone();
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

    /// `python tools/export_glb.py <model> [--with <set>]` -> game_assets/blender/<model>.glb
    fn start_export(&mut self, pool: &Pool, root: &Path, set: Option<String>) {
        let Some(stem) = self.model_bch.as_ref().and_then(|p| p.file_stem()).map(|s| s.to_string_lossy().into_owned()) else {
            return;
        };
        let (tx, rx) = channel();
        self.export_rx = Some(rx);
        self.status = format!("exporting {stem}.glb\u{2026}");
        let root = root.to_path_buf();
        pool.submit(move || {
            let mut cmd = std::process::Command::new("python");
            cmd.current_dir(&root).arg(root.join("tools").join("export_glb.py")).arg(&stem);
            if let Some(set) = &set {
                cmd.arg("--with").arg(set);
            }
            let msg = match cmd.output() {
                Ok(o) if o.status.success() => {
                    let path = root.join("game_assets").join("blender").join(format!("{stem}.glb"));
                    match super::models::open_file_in_blender(&path) {
                        Ok(()) => format!("exported {} and opened it in Blender", path.display()),
                        Err(e) => format!("exported {} ({e})", path.display()),
                    }
                }
                Ok(o) => format!("export failed: {}", String::from_utf8_lossy(&o.stderr).trim().lines().last().unwrap_or("")),
                Err(e) => format!("export failed: cannot run python: {e}"),
            };
            let _ = tx.send(msg);
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
                let only = self.only.clone();
                let ok = move |a: &crate::data::rig::Animation| {
                    !a.tracks.is_empty() && only.as_ref().is_none_or(|o| o.contains(&a.name))
                };
                let usable = rig.animations.iter().filter(|a| ok(a)).count();
                self.status = format!("{usable} of {} animations work on this rig", rig.animations.len());
                // start on a full-body clip: an idle if there is one, else the clip driving the most bones
                // (short clips like cbla_talk0 only move a few bones and are layered over another clip in game)
                self.anim = rig
                    .animations
                    .iter()
                    .position(|a| ok(a) && a.name.contains("idle") && a.tracks.len() > 8)
                    .or_else(|| {
                        (0..rig.animations.len()).filter(|&i| ok(&rig.animations[i])).max_by_key(|&i| rig.animations[i].tracks.len())
                    });
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
                                let works = !a.tracks.is_empty() && self.only.as_ref().is_none_or(|o| o.contains(&a.name));
                                if !works || (!filter.is_empty() && !a.name.to_lowercase().contains(&filter)) {
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
            if self.model_bch.is_some() {
                let busy = self.export_rx.is_some();
                let set = self.motion.and_then(|i| motions.get(i)).map(|m| m.set.clone());
                let tip = match &set {
                    Some(s) => format!("Export game_assets/blender/<model>.glb (joints, skin weights = weight paint, textures, the model's default motion sets plus {s}, as actions) and open it in Blender"),
                    None => "Export game_assets/blender/<model>.glb (joints, skin weights = weight paint, textures, the model's own motion sets as actions) and open it in Blender".to_string(),
                };
                if ui.add_enabled(!busy, egui::Button::new(if busy { "Exporting\u{2026}" } else { "Rigged \u{2192} Blender" })).on_hover_text(tip).clicked() {
                    self.start_export(pool, root, set);
                }
            }
            ui.label(theme::faint_label(self.status.clone()));
        });
        if let Some(rx) = &self.export_rx {
            if let Ok(msg) = rx.try_recv() {
                self.status = msg;
                self.export_rx = None;
            } else {
                ui.ctx().request_repaint_after(std::time::Duration::from_millis(200));
            }
        }
        // never turn "not scanned yet" into "scanned, found nothing"
        self.motions = had_motions.then_some(motions);
    }
}
