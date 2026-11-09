//! Level editor MVP: load a decoded map, view its environment mesh, inspect
//! placement records, edit transforms, undo/redo, and export a patched BXON.

use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver};
use std::sync::Arc;

use eframe::egui;
use serde::{Deserialize, Serialize};

use crate::app::{paint_mesh_viewport_scene, Instances, ViewerApp};
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

/// The level an exit leads to, by its destination map id.
fn exit_dest(obj: &SceneObject) -> Option<&'static str> {
    let id = obj.props.iter().find(|p| p.name == "destination map")?.value;
    MAPS.get()?.get(id as usize).map(|s| s.as_str()).filter(|s| !s.is_empty())
}

/// Moves, deleted flags and added boxes of the collision editor (one undo step).
type CollisionState = (Vec<[f32; 3]>, Vec<bool>, Vec<([f32; 3], [f32; 3])>);

/// A model drawn at the actors that use it, loaded in the background.
enum ModelState {
    Loading,
    Ready(Arc<Mesh>),
    Failed,
}

/// What an actor's entity id means, from `game_assets/maps/entity_models.json` (tools/entity_table.py).
#[derive(Clone, Debug, Default)]
pub struct Entity {
    pub model: String,
    pub name: String,
    pub jp: String,
}

static ENTITIES: std::sync::OnceLock<Vec<Entity>> = std::sync::OnceLock::new();
/// Region of every level (low byte of its level_map row) and each region's actor id -> model table
/// (param/region/r<region+1>/npc_list: id = row, word 7 = index into res_model3d's name list).
static LEVEL_REGIONS: std::sync::OnceLock<std::collections::HashMap<String, i32>> = std::sync::OnceLock::new();
static NPC_TABLES: std::sync::OnceLock<std::collections::HashMap<i32, Vec<Entity>>> = std::sync::OnceLock::new();
/// Rows of fieldcmn/fixed_drop_param: (item id, count). A gimmick record's drop row points here (docs/GIMMICK_DECOMP.md).
static FIXED_DROPS: std::sync::OnceLock<Vec<(u32, u32)>> = std::sync::OnceLock::new();
static ITEM_NAMES: std::sync::OnceLock<std::collections::HashMap<u32, String>> = std::sync::OnceLock::new();
/// Region of the open level (-1 = unknown), set every frame.
static CUR_REGION: std::sync::atomic::AtomicI32 = std::sync::atomic::AtomicI32::new(-1);
/// `game_assets/maps/npc_talks.json` (tools/npc_talk.py): what every region character says, and the events
/// the area scripts start for them.
static NPC_TALKS: std::sync::OnceLock<serde_json::Value> = std::sync::OnceLock::new();
/// Level name of every map id (row of syscmn/level_map.json), from the same file.
static MAPS: std::sync::OnceLock<Vec<String>> = std::sync::OnceLock::new();

fn load_entities(root: &Path) {
    if ENTITIES.get().is_some() {
        return;
    }
    let doc = std::fs::read_to_string(root.join("game_assets/maps/entity_models.json"))
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok());
    let maps: Vec<String> = doc
        .as_ref()
        .and_then(|v| v.get("maps"))
        .and_then(|v| v.as_array())
        .map(|a| a.iter().map(|m| m.as_str().unwrap_or("").to_string()).collect())
        .unwrap_or_default();
    let _ = MAPS.set(maps);
    let regions: std::collections::HashMap<String, i32> = doc
        .as_ref()
        .and_then(|v| v.get("level_regions"))
        .and_then(|v| v.as_object())
        .map(|o| o.iter().filter_map(|(k, v)| v.as_i64().map(|n| (k.clone(), n as i32))).collect())
        .unwrap_or_default();
    let _ = LEVEL_REGIONS.set(regions);
    let tables: std::collections::HashMap<i32, Vec<Entity>> = doc
        .as_ref()
        .and_then(|v| v.get("npc_tables"))
        .and_then(|v| v.as_object())
        .map(|o| {
            o.iter()
                .filter_map(|(k, v)| {
                    let rows = v
                        .as_array()?
                        .iter()
                        .map(|m| {
                            let model = m.as_str().unwrap_or("").to_string();
                            Entity { name: model.clone(), model, jp: String::new() }
                        })
                        .collect();
                    Some((k.parse().ok()?, rows))
                })
                .collect()
        })
        .unwrap_or_default();
    let _ = NPC_TABLES.set(tables);
    let drops: Vec<(u32, u32)> = doc
        .as_ref()
        .and_then(|v| v.get("fixed_drops"))
        .and_then(|v| v.as_array())
        .map(|a| {
            a.iter()
                .map(|r| {
                    let r = r.as_array();
                    let get = |i: usize| r.and_then(|r| r.get(i)).and_then(|v| v.as_u64()).unwrap_or(0) as u32;
                    (get(0), get(1))
                })
                .collect()
        })
        .unwrap_or_default();
    let _ = FIXED_DROPS.set(drops);
    let talks = std::fs::read_to_string(root.join("game_assets/maps/npc_talks.json"))
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .unwrap_or(serde_json::Value::Null);
    let _ = NPC_TALKS.set(talks);
    let items: std::collections::HashMap<u32, String> = std::fs::read_to_string(root.join("game_assets/maps/item_names.json"))
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .and_then(|v| v.as_object().cloned())
        .map(|o| o.into_iter().filter_map(|(k, v)| Some((k.parse().ok()?, v.as_str()?.to_string()))).collect())
        .unwrap_or_default();
    let _ = ITEM_NAMES.set(items);
    let list = doc
        .and_then(|v| v.get("monsters").cloned())
        .and_then(|v| v.as_array().cloned())
        .unwrap_or_default();
    let list = list
        .iter()
        .map(|m| Entity {
            model: m.get("model").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            name: m.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            jp: m.get("jp").and_then(|v| v.as_str()).unwrap_or("").to_string(),
        })
        .collect();
    let _ = ENTITIES.set(list);
}

/// What a gimmick (chest / search spot) gives: its drop row -> fixed_drop_param row -> item name and count.
fn gimmick_contents(obj: &SceneObject) -> Option<String> {
    let row = obj.props.iter().find(|p| p.name == "drop row")?.value;
    if row == 0xFFFF {
        return Some("nothing fixed (glitter / random)".into());
    }
    let (item, count) = *FIXED_DROPS.get()?.get(row as usize)?;
    if item == 0xFFFF {
        return Some("nothing".into());
    }
    let name = ITEM_NAMES.get().and_then(|m| m.get(&item)).cloned().unwrap_or_else(|| format!("item {item}"));
    Some(format!("{name} x{count}"))
}

/// The model an actor shows in the game: its id is a row of the level's region table (see `NPC_TABLES`).
fn monster_of(obj: &SceneObject) -> Option<&'static Entity> {
    let id = obj.props.iter().find(|p| p.name == "entity id")?.value;
    let region = CUR_REGION.load(std::sync::atomic::Ordering::Relaxed);
    let e = NPC_TABLES.get()?.get(&region)?.get(id as usize)?;
    if e.model.is_empty() {
        None
    } else {
        Some(e)
    }
}

/// A tagged game string the way the player reads it: ruby kept as the base text, line breaks and pages as breaks.
fn readable(tagged: &str) -> String {
    use crate::data::dialogues::{pieces, Piece};
    let Ok(list) = pieces(tagged) else { return tagged.to_string() };
    let mut out = String::new();
    for piece in list {
        match piece {
            Piece::Text(c) => out.push(c),
            Piece::Var(_) => out.push('\u{ff0a}'),
            Piece::Cr | Piece::Newline => {
                // `{CR}` is usually followed by a real newline: one break, not two
                if !out.ends_with('\n') {
                    out.push('\n');
                }
            }
            Piece::Page => out.push_str("\n\u{2500}\u{2500} next page \u{2500}\u{2500}\n"),
        }
    }
    out.trim().to_string()
}

fn time_names(mask: u64) -> String {
    if mask & 0xF == 0xF || mask == 0 {
        return "any time of day".into();
    }
    let names = ["morning", "daytime", "evening", "night"];
    let list: Vec<&str> = (0..4).filter(|b| mask & (1 << b) != 0).map(|b| names[b]).collect();
    list.join(" / ")
}

/// The Dialogue group of an NPC: every conversation the character can have, with the story condition that
/// selects it, the variants played in turn, and the lines (editable). Also lists events the area script starts
/// for this character instead (docs/DIALOGUE_FORMAT.md).
fn dialogue_section(app: &mut ViewerApp, ui: &mut egui::Ui, obj: &SceneObject, level: &str) {
    let class = obj.props.iter().find(|p| p.name == "entity class").map(|p| p.value).unwrap_or(0);
    let Some(id) = obj.props.iter().find(|p| p.name == "entity id").map(|p| p.value) else { return };
    let region = CUR_REGION.load(std::sync::atomic::Ordering::Relaxed);
    if class != 0x200 || region < 0 {
        return;
    }
    let Some(talks) = NPC_TALKS.get().filter(|v| !v.is_null()) else {
        egui::CollapsingHeader::new(egui::RichText::new("Dialogue").strong()).default_open(true).show(ui, |ui| {
            ui.label(theme::faint_label("Run python tools/npc_talk.py to export what NPCs say."));
        });
        return;
    };
    let region_key = (region + 1).to_string();
    let bank = talks["regions"][&region_key]["bank"].as_str().unwrap_or("").to_string();
    let character = &talks["regions"][&region_key]["characters"][id.to_string()];
    // events the area script starts for this character
    let area = level.rsplit_once('_').map(|(a, _)| a).unwrap_or(level).to_string();
    let events: Vec<(String, bool)> = talks["area_events"][&area]
        .as_array()
        .map(|a| {
            a.iter()
                .filter(|e| e["rg_id"].as_i64() == Some(id) && (e["region"].is_null() || e["region"].as_i64() == Some(region as i64)))
                .map(|e| (e["event"].as_str().unwrap_or("").to_string(), true))
                .collect()
        })
        .unwrap_or_default();
    egui::CollapsingHeader::new(egui::RichText::new("Dialogue").strong()).default_open(true).id_salt("dialogue_group").show(ui, |ui| {
        ui.label(theme::faint_label(format!("character #{id} of region {} \u{b7} {bank}", region + 1)));
        for (event, _) in &events {
            ui.horizontal_wrapped(|ui| {
                ui.label(egui::RichText::new("Triggers an event:").color(theme::WARN));
                ui.label(theme::mono(event.clone()));
                if ui.small_button("Open script").on_hover_text("The area script starts this event instead of the default talk while its story condition holds").clicked() {
                    app.open_scripts(event);
                }
            });
        }
        let Some(talks_list) = character["talks"].as_array().filter(|t| !t.is_empty()) else {
            ui.label(theme::faint_label("This character has no talk lines of its own (silent, or handled entirely by script)."));
            return;
        };
        crate::ui::panels::dialogues::DialoguesPanel::prepare(app, ui.ctx());
        if !app.panels.dialogues.ready() {
            ui.horizontal(|ui| {
                ui.spinner();
                ui.label(theme::faint_label("loading text banks\u{2026}"));
            });
            return;
        }
        match app.panels.dialogues.open_bank_key(&bank) {
            Ok(true) => {}
            Ok(false) => {
                ui.label(theme::faint_label("text bank not found"));
                return;
            }
            Err(other) => {
                ui.label(egui::RichText::new(format!("{other} has unsaved dialogue edits. Save them before editing another region's NPCs.")).color(theme::WARN));
                if ui.button("Save those edits to the mod").clicked() {
                    let mut panel = std::mem::take(&mut app.panels.dialogues);
                    panel.save_now(app);
                    app.panels.dialogues = panel;
                }
                return;
            }
        }
        ui.label(theme::faint_label("The game plays the last conversation whose story condition and time of day match. A conversation with several variants plays them one after another when you talk again."));
        for talk in talks_list {
            let t = talk["t"].as_u64().unwrap_or(0);
            let orig = [
                talk["group"].as_u64().unwrap_or(0) as u8,
                talk["min"].as_u64().unwrap_or(0) as u8,
                talk["time"].as_u64().unwrap_or(15) as u8,
                talk["first"].as_u64().unwrap_or(0) as u8,
            ];
            let edit_key = (region + 1, id, t);
            let mut cond = app.panels.editor.talk_edits.get(&edit_key).copied().unwrap_or(orig);
            let (group, min, time) = (cond[0] as u64, cond[1] as u64, cond[2] as u64);
            let variants = talk["variants"].as_array().cloned().unwrap_or_default();
            let when = if group == 0 && min == 0 { "default".to_string() } else { format!("story flag {group} \u{2265} {min}") };
            let lines_total: usize = variants.iter().map(|v| v.as_array().map(|a| a.len()).unwrap_or(0)).sum();
            let title = format!("{}Conversation {t}  \u{b7}  {when}  \u{b7}  {}", if cond != orig { "\u{25cf} " } else { "" }, time_names(time));
            egui::CollapsingHeader::new(egui::RichText::new(title).color(theme::TEXT_DIM))
                .id_salt(("talk", id, t))
                .default_open(false)
                .show(ui, |ui| {
                    ui.horizontal_wrapped(|ui| {
                        ui.label(theme::faint_label("Appears when story flag"));
                        ui.add(egui::DragValue::new(&mut cond[0]).range(0..=255));
                        ui.label(theme::faint_label("\u{2265}"));
                        ui.add(egui::DragValue::new(&mut cond[1]).range(0..=255));
                        for (bit, name) in [(1u8, "morning"), (2, "day"), (4, "evening"), (8, "night")] {
                            let mut on = cond[2] & bit != 0;
                            if ui.checkbox(&mut on, name).changed() {
                                cond[2] = if on { cond[2] | bit } else { cond[2] & !bit };
                            }
                        }
                        if cond != orig && ui.small_button("Reset").clicked() {
                            cond = orig;
                        }
                    });
                    if let Some(r) = talk.get("redirect") {
                        ui.label(theme::faint_label(format!(
                            "Says the same as the conversation for story flag {} \u{2265} {}.",
                            r["group"].as_u64().unwrap_or(0),
                            r["index"].as_u64().unwrap_or(0)
                        )));
                    }
                    if lines_total == 0 {
                        ui.label(theme::faint_label("No lines of its own."));
                    }
                    for (vi, variant) in variants.iter().enumerate() {
                        if variants.len() > 1 {
                            ui.label(egui::RichText::new(format!("Variant {} of {}", vi + 1, variants.len())).color(theme::ACCENT).size(11.5));
                        }
                        for (li, line) in variant.as_array().cloned().unwrap_or_default().iter().enumerate() {
                            let (Some(e), speaker) = (line["e"].as_u64(), line["s"].as_u64()) else { continue };
                            let name = speaker.and_then(|s| app.panels.dialogues.line_text(s as usize)).unwrap_or_default();
                            let Some(mut text) = app.panels.dialogues.line_text(e as usize) else { continue };
                            let edit_id = ui.make_persistent_id(("talkline_edit", id, t, vi, li));
                            let mut editing: bool = ui.data(|d| d.get_temp(edit_id).unwrap_or(false));
                            egui::Frame::new()
                                .fill(theme::BG_INPUT)
                                .corner_radius(4.0)
                                .inner_margin(egui::Margin::symmetric(8, 6))
                                .show(ui, |ui| {
                                    ui.set_width(ui.available_width());
                                    ui.horizontal(|ui| {
                                        if !name.is_empty() {
                                            ui.label(egui::RichText::new(readable(&name)).color(theme::ACCENT).strong().size(12.0));
                                        }
                                        let original = app.panels.dialogues.original_text(e as usize);
                                        let modified = original.as_deref().is_some_and(|o| o != text);
                                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                                            if modified {
                                                if ui.small_button("Revert").on_hover_text("Back to the text of the game file").clicked() {
                                                    if let Some(o) = original.clone() {
                                                        app.panels.dialogues.set_line_text(e as usize, o.clone());
                                                        text = o;
                                                    }
                                                }
                                                ui.label(egui::RichText::new("\u{25cf}").color(theme::ACCENT).size(10.0));
                                            }
                                            if ui.small_button(if editing { "Done" } else { "Edit" }).on_hover_text("Edit the raw text with its tags ({CR} line break, {ruby:base|reading}, {PLAYER} ...)").clicked() {
                                                editing = !editing;
                                            }
                                        });
                                    });
                                    if editing {
                                        let before = text.clone();
                                        ui.add(
                                            egui::TextEdit::multiline(&mut text)
                                                .id_salt(("talkline", id, t, vi, li))
                                                .desired_rows(3)
                                                .desired_width(f32::INFINITY)
                                                .font(egui::TextStyle::Monospace),
                                        );
                                        if text != before {
                                            app.panels.dialogues.set_line_text(e as usize, text.clone());
                                        }
                                        ui.label(theme::faint_label("Preview:"));
                                    }
                                    ui.add(egui::Label::new(egui::RichText::new(readable(&text)).size(13.0).color(theme::TEXT)).wrap());
                                });
                            ui.data_mut(|d| d.insert_temp(edit_id, editing));
                            ui.add_space(4.0);
                        }
                    }
                });
        }
        let pending = app.panels.editor.talk_edits.len();
        if pending > 0 {
            ui.horizontal(|ui| {
                ui.label(theme::faint_label(format!("{pending} conversation condition(s) changed")));
                if ui.button("Save conditions to mod").on_hover_text("Rewrites this region's npc_ie bank with the new story / time conditions").clicked() {
                    let rows: Vec<serde_json::Value> = app
                        .panels
                        .editor
                        .talk_edits
                        .iter()
                        .filter(|((r, _, _), _)| *r == region + 1)
                        .map(|((_, c, t), v)| serde_json::json!({"char": c, "talk": t, "group": v[0], "min": v[1], "time": v[2], "first": v[3]}))
                        .collect();
                    let file = app.dirs.root.join("build").join("npc_condition_edits.json");
                    let _ = std::fs::create_dir_all(app.dirs.root.join("build"));
                    let _ = std::fs::write(&file, serde_json::to_vec(&rows).unwrap_or_default());
                    let out = std::process::Command::new("python")
                        .arg(app.dirs.root.join("tools").join("npc_talk.py"))
                        .arg("set-cond")
                        .arg("--region")
                        .arg((region + 1).to_string())
                        .arg("--json")
                        .arg(&file)
                        .current_dir(&app.dirs.root)
                        .output();
                    app.status = match out {
                        Ok(o) if o.status.success() => "Conversation conditions written to the mod (param/region pack)".to_string(),
                        Ok(o) => format!("conditions not saved: {}", String::from_utf8_lossy(&o.stderr).trim()),
                        Err(e) => format!("could not run python: {e}"),
                    };
                }
            });
        }
        let dirty = app.panels.dialogues.dirty_count();
        ui.horizontal(|ui| {
            if ui.add_enabled(dirty > 0, egui::Button::new(format!("Save dialogue to mod ({dirty})"))).clicked() {
                let mut panel = std::mem::take(&mut app.panels.dialogues);
                panel.save_now(app);
                app.panels.dialogues = panel;
            }
            if ui.button("Open in Dialogue editor").on_hover_text("Preview with the game's font and box size").clicked() {
                app.go(crate::app::Section::Dialogues);
            }
        });
        if let Some((msg, bad)) = app.panels.dialogues.status_line() {
            ui.label(egui::RichText::new(msg).size(11.0).color(if bad { theme::ERR } else { theme::TEXT_FAINT }));
        }
    });
}

/// A typed value of a record that the editor can show and (when `editable`) write back: `ty` is u8 / u16 / u32.
#[derive(Clone, Debug, Deserialize, Serialize, PartialEq)]
pub struct Prop {
    pub name: String,
    pub offset: String,
    #[serde(rename = "type")]
    pub ty: String,
    pub value: i64,
    #[serde(default)]
    pub editable: bool,
    #[serde(default)]
    pub hint: String,
}

impl Prop {
    fn max(&self) -> i64 {
        match self.ty.as_str() {
            "u8" => 0xFF,
            "u16" => 0xFFFF,
            _ => 0xFFFF_FFFF,
        }
    }
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
    /// record size in bytes (68 placement, 120 transform); needed to place a duplicate
    #[serde(default)]
    pub shape: u32,
    /// removed from the level when the project is exported
    #[serde(default)]
    pub deleted: bool,
    /// a new record: the retail record (offset) it is a copy of
    #[serde(default)]
    pub new_from: Option<String>,
    /// typed record fields beyond the transform (actors: which entity it is, ...)
    #[serde(default)]
    pub props: Vec<Prop>,
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

/// A level that is open but not in front: its edits, undo history and camera stay alive.
struct Parked {
    scene: Scene,
    original: Vec<SceneObject>,
    selected_object: Option<usize>,
    camera: Camera,
    mesh: Option<Arc<Mesh>>,
    undo: Vec<Vec<SceneObject>>,
    redo: Vec<Vec<SceneObject>>,
    dirty: bool,
    status: String,
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
    /// collision overlay (View > Collision)
    pub show_collision: bool,
    collision: Arc<Vec<crate::data::collision::Shape>>,
    collision_for: String,
    pub collision_sel: Option<usize>,
    /// how far each collision shape has been moved (same order as `collision`), written by Save to mod
    collision_moves: Vec<[f32; 3]>,
    /// shapes removed from the level (Save to mod drops them from the collision file)
    collision_dropped: Vec<bool>,
    /// new collision boxes (min, max) added in the editor; Save to mod appends them to the collision file
    collision_boxes: Vec<([f32; 3], [f32; 3])>,
    /// level slot the current level is cloned into (Level > Clone into slot)
    clone_target: String,
    /// edited conversation conditions: (region, character, conversation) -> [group, minimum, time mask, first-time byte]
    talk_edits: std::collections::BTreeMap<(i32, i64, u64), [u8; 4]>,
    /// start of a Shift+drag box select in the viewport
    marquee: Option<egui::Pos2>,
    history_open: bool,
    /// nodes selected besides `selected_object` (Shift+click in the viewport); group move / delete act on all of them
    multi: Vec<usize>,
    multi_offset: [f32; 3],
    /// undo steps for collision edits (moves, deletes, added boxes); a drag counts as one step
    collision_undo: Vec<CollisionState>,
    collision_undo_open: bool,
    clone_open: bool,
    pub show_bounds: bool,
    pub show_grid: bool,
    pub show_scene_dock: bool,
    /// Scene dock on the right, Inspector on the left
    pub swap_docks: bool,
    /// show the Scene / Inspector dock as a free window instead of a side panel
    pub float_scene: bool,
    pub float_inspector: bool,
    pub show_inspector_dock: bool,
    pub show_axes: bool,
    pub wireframe: bool,
    pub flat: bool,
    pub snap: bool,
    pub snap_step: f32,
    pub tool: Tool,
    pub show_labels: bool,
    tree_filter: String,
    /// show only the actors of this layer key (top byte of `key 60`)
    layer_filter: Option<u32>,
    collapsed: std::collections::HashSet<String>,
    tree_scroll: bool,
    pending_focus: bool,
    gizmo: Option<GizmoDrag>,
    /// node whose inspector fields are currently being edited (one undo step per burst)
    edit_group: Option<usize>,
    /// Export/Save-to-mod workflow state (project JSON -> level3d.bxon -> PACK).
    tools: crate::ui::asset_jobs::AssetTools,
    /// other open levels, by id
    parked: std::collections::HashMap<String, Parked>,
    /// real models drawn at actors (View > Models)
    pub show_models: bool,
    models: std::collections::HashMap<String, ModelState>,
    model_tx: std::sync::mpsc::Sender<(String, Result<Mesh, String>)>,
    model_rx: Receiver<(String, Result<Mesh, String>)>,
}

impl Default for EditorPanel {
    fn default() -> Self {
        let model_channel = channel();
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
            show_collision: true,
            collision: Arc::new(Vec::new()),
            collision_for: String::new(),
            collision_sel: None,
            collision_moves: Vec::new(),
            collision_dropped: Vec::new(),
            collision_boxes: Vec::new(),
            clone_target: String::new(),
            talk_edits: std::collections::BTreeMap::new(),
            marquee: None,
            history_open: false,
            multi: Vec::new(),
            multi_offset: [0.0; 3],
            collision_undo: Vec::new(),
            collision_undo_open: false,
            clone_open: false,
            show_bounds: true,
            show_grid: true,
            show_scene_dock: true,
            swap_docks: false,
            float_scene: false,
            float_inspector: false,
            show_inspector_dock: true,
            show_axes: true,
            wireframe: false,
            flat: false,
            snap: true,
            snap_step: 0.25,
            tool: Tool::Move,
            show_labels: false,
            tree_filter: String::new(),
            layer_filter: None,
            collapsed: Default::default(),
            tree_scroll: false,
            pending_focus: false,
            gizmo: None,
            edit_group: None,
            tools: Default::default(),
            parked: Default::default(),
            show_models: true,
            models: Default::default(),
            model_tx: model_channel.0,
            model_rx: model_channel.1,
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

    pub fn ensure_maps(&mut self, root: &Path) {
        load_entities(root);
        self.scan_maps(root);
    }

    /// Decoded levels; scanned lazily the first time the editor or project dock needs them.
    pub fn maps(&self) -> &[String] {
        &self.maps
    }

    /// Opens `map` the next time the editor is drawn.
    pub fn request(&mut self, map: &str) {
        if self.selected_map.as_deref() == Some(map) && self.scene.is_some() {
            return;
        }
        self.park_current();
        self.selected_map = Some(map.to_string());
        self.scene = None;
        self.loading = false;
    }

    /// Moves the level in front into the background, keeping its edits.
    fn park_current(&mut self) {
        let (Some(map), Some(scene)) = (self.selected_map.clone(), self.scene.take()) else { return };
        self.parked.insert(
            map,
            Parked {
                scene,
                original: std::mem::take(&mut self.original),
                selected_object: self.selected_object.take(),
                camera: self.camera,
                mesh: self.mesh.take(),
                undo: std::mem::take(&mut self.undo),
                redo: std::mem::take(&mut self.redo),
                dirty: std::mem::replace(&mut self.dirty, false),
                status: std::mem::take(&mut self.status),
            },
        );
        self.gizmo = None;
        self.edit_group = None;
    }

    /// Brings a parked level back; false when it was never opened.
    fn restore(&mut self, map: &str) -> bool {
        let Some(p) = self.parked.remove(map) else { return false };
        self.selected_map = Some(map.to_string());
        self.scene = Some(p.scene);
        self.original = p.original;
        self.selected_object = p.selected_object;
        self.camera = p.camera;
        self.mesh = p.mesh;
        self.mesh_id = self.mesh_id.wrapping_add(1);
        self.undo = p.undo;
        self.redo = p.redo;
        self.dirty = p.dirty;
        self.status = p.status;
        self.loading = false;
        true
    }

    /// Levels with edits that are not on disk yet (the one in front and the parked ones).
    pub fn unsaved_levels(&self) -> Vec<(String, usize)> {
        let mut out = Vec::new();
        if let Some(scene) = &self.scene {
            let n = self.changed_objects().len();
            if self.dirty || n > 0 {
                out.push((scene.id.clone(), n));
            }
        }
        for (id, p) in &self.parked {
            let n = changed_between(&p.scene.objects, &p.original).len();
            if p.dirty || n > 0 {
                out.push((id.clone(), n));
            }
        }
        out.sort();
        out
    }

    /// Writes the project file of every level that has unsaved edits.
    pub fn save_all_levels(&mut self, root: &Path) -> usize {
        let mut saved = 0;
        if self.dirty {
            self.save_project(root);
            saved += 1;
        }
        for p in self.parked.values_mut().filter(|p| p.dirty) {
            match write_project(root, &p.scene, &p.original, &[], &[], &[]) {
                Ok(_) => {
                    p.dirty = false;
                    saved += 1;
                }
                Err(e) => self.status = e,
            }
        }
        saved
    }

    pub fn open_levels(&self) -> Vec<String> {
        let mut v: Vec<String> = self.parked.keys().cloned().collect();
        v.extend(self.selected_map.clone().filter(|_| self.scene.is_some()));
        v
    }

    pub fn collision_changed(&self) -> bool {
        self.collision_moves.iter().any(|d| d.iter().any(|v| v.abs() > 1e-6))
    }

    pub fn is_dirty(&self) -> bool {
        self.dirty
    }

    pub fn changed_count(&self) -> usize {
        self.changed_objects().len()
    }

    pub fn level_name(&self) -> String {
        self.scene.as_ref().map(|s| s.id.clone()).unwrap_or_default()
    }

    pub fn revert_all(&mut self) {
        if self.scene.is_some() {
            self.begin_change();
            let original = self.original.clone();
            if let Some(s) = self.scene.as_mut() {
                s.objects = original;
            }
        }
    }

    pub fn set_tool_by_name(&mut self, name: &str) {
        self.tool = match name {
            "select" => Tool::Select,
            "rotate" => Tool::Rotate,
            "scale" => Tool::Scale,
            _ => Tool::Move,
        };
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }

    pub fn undo_action(&mut self) {
        if let Some(prev) = self.undo.pop() {
            if let Some(cur) = self.scene.as_mut() {
                self.redo.push(cur.objects.clone());
                cur.objects = prev;
                self.dirty = true;
            }
        }
    }

    /// Jump back to the state *before* undo step `k` (0 = the oldest); the later states move to the redo stack.
    pub fn jump_to_step(&mut self, k: usize) {
        if k >= self.undo.len() {
            return;
        }
        let Some(cur) = self.scene.as_mut() else { return };
        let later: Vec<Vec<SceneObject>> = self.undo.drain(k + 1..).collect();
        let target = self.undo.pop().unwrap_or_default();
        self.redo.push(cur.objects.clone());
        for state in later.into_iter().rev() {
            self.redo.push(state);
        }
        cur.objects = target;
        self.dirty = true;
    }

    /// Short description of what step `k` changed: nodes that differ between the state before it and the state after it.
    fn step_summary(&self, k: usize) -> String {
        let before = &self.undo[k];
        let after: &Vec<SceneObject> = if k + 1 < self.undo.len() { &self.undo[k + 1] } else { match self.scene.as_ref() { Some(s) => &s.objects, None => return String::new() } };
        let mut names = Vec::new();
        for (i, (a, b)) in before.iter().zip(after.iter()).enumerate() {
            if a.position != b.position || a.scale != b.scale || a.rotation != b.rotation || a.deleted != b.deleted || a.props != b.props {
                names.push(object_label(i, b));
            }
        }
        if after.len() > before.len() {
            names.push(format!("{} added", after.len() - before.len()));
        }
        match names.len() {
            0 => "no node change".into(),
            1 => names[0].clone(),
            n => format!("{} and {} more", names[0], n - 1),
        }
    }

    pub fn redo_action(&mut self) {
        if let Some(next) = self.redo.pop() {
            if let Some(cur) = self.scene.as_mut() {
                self.undo.push(cur.objects.clone());
                cur.objects = next;
                self.dirty = true;
            }
        }
    }

    /// Ctrl+S: write the project file for the open level.
    pub fn save_current(&mut self, root: &Path) {
        self.save_project(root);
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
        if self.scene.is_some() && self.selected_map.as_deref() != Some(map) {
            self.park_current();
        }
        if self.restore(map) {
            return;
        }
        self.selected_map = Some(map.to_string());
        self.scene = None;
        self.mesh = None;
        self.selected_object = None;
        self.gizmo = None;
        self.edit_group = None;
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
                } else if let Some(bounds) = object_bounds(&loaded.scene.objects) {
                    // no background mesh: frame the markers and show an empty floor
                    self.camera.frame(&bounds);
                    self.mesh = Some(Arc::new(placeholder_mesh(&loaded.scene.id, bounds)));
                    self.mesh_id = self.mesh_id.wrapping_add(1);
                }
                if let Some(i) = std::env::var("DQXI_EDITOR_SELECT").ok().and_then(|v| v.parse::<usize>().ok()) {
                    self.selected_object = Some(i).filter(|i| *i < loaded.scene.objects.len());
                }
                self.original = loaded.scene.objects.clone();
                if std::env::var("DQXI_EDITOR_FOCUS").is_ok() {
                    let scene = loaded.scene.clone();
                    self.focus_selection(&scene);
                   
                }
                self.scene = Some(loaded.scene);
            }
            Err(e) => {
                self.status = e;
            }
        }
    }

    fn edits(&self) -> Vec<(String, f32)> {
        match &self.scene {
            Some(scene) => edits_between(&scene.objects, &self.original),
            None => Vec::new(),
        }
    }

    fn save_project(&mut self, root: &Path) {
        let Some(scene) = &self.scene else { return };
        match write_project(root, scene, &self.original, &self.collision_moves, &self.collision_dropped, &self.collision_boxes) {
            Ok(path) => {
                self.dirty = false;
                self.status = format!("Saved project {path}");
            }
            Err(e) => self.status = e,
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
    /// Writes the project and stages `mod/romfs/level3d/<map>.pack` in one go.
    fn save_to_mod(&mut self, root: &Path) {
        let Some(scene) = &self.scene else { return };
        let map = scene.id.clone();
        self.save_project(root);
        if self.status.starts_with("Save failed") {
            return;
        }
        let project = root.join("editor_projects").join(format!("{map}.json"));
        if !project.is_file() {
            self.status = "project file was not written".into();
            return;
        }
        self.tools.import_path = project.to_string_lossy().into_owned();
        self.tools.start_replace(root, "map", &map, Vec::new(), true);
    }
}

fn object_bounds(objects: &[SceneObject]) -> Option<crate::render::mesh::Bounds> {
    let mut it = objects.iter().filter(|o| o.position.iter().all(|v| v.is_finite() && v.abs() < 1e6));
    let first = it.next()?;
    let mut min = Vec3::new(first.position[0], first.position[1], first.position[2]);
    let mut max = min;
    for o in it {
        min = Vec3::new(min.x.min(o.position[0]), min.y.min(o.position[1]), min.z.min(o.position[2]));
        max = Vec3::new(max.x.max(o.position[0]), max.y.max(o.position[1]), max.z.max(o.position[2]));
    }
    // never frame a single point from inside it
    let pad = Vec3::new(2.0, 2.0, 2.0);
    Some(crate::render::mesh::Bounds { min: min.sub(pad), max: max.add(pad) })
}

/// A zero-area triangle that makes the viewport draw its grid and axes for levels
/// that have no converted background mesh.
fn placeholder_mesh(name: &str, bounds: crate::render::mesh::Bounds) -> Mesh {
    use crate::render::mesh::STRIDE;
    let c = bounds.center();
    let mut vertices = vec![0.0f32; 3 * STRIDE];
    for v in 0..3 {
        vertices[v * STRIDE] = c.x;
        vertices[v * STRIDE + 1] = bounds.min.y;
        vertices[v * STRIDE + 2] = c.z;
        vertices[v * STRIDE + 4] = 1.0;
        vertices[v * STRIDE + 10] = 1.0;
        vertices[v * STRIDE + 11] = 1.0;
        vertices[v * STRIDE + 12] = 1.0;
        vertices[v * STRIDE + 13] = 1.0;
    }
    Mesh {
        name: name.to_string(),
        material: String::new(),
        color: [0.5, 0.5, 0.5],
        vertices,
        indices: vec![0, 1, 2],
        groups: Vec::new(),
        vertex_count: 3,
        triangle_count: 0,
        parts: 1,
        bounds,
        raw_bounds: bounds,
        non_finite: 0,
        outliers: 0,
    }
}

fn original_by_id(original: &[SceneObject]) -> std::collections::HashMap<&str, &SceneObject> {
    original.iter().map(|o| (o.id.as_str(), o)).collect()
}

/// Nodes that differ from the retail file: moved, added or deleted.
fn changed_between(objects: &[SceneObject], original: &[SceneObject]) -> Vec<usize> {
    let by_id = original_by_id(original);
    objects
        .iter()
        .enumerate()
        .filter(|(_, o)| match by_id.get(o.id.as_str()) {
            None => !o.deleted,
            Some(orig) => {
                o.deleted != orig.deleted
                    || o.position != orig.position
                    || o.scale != orig.scale
                    || o.rotation != orig.rotation
                    || o.props.iter().zip(orig.props.iter()).any(|(a, b)| a.value != b.value)
            }
        })
        .map(|(i, _)| i)
        .collect()
}

fn edits_between(objects: &[SceneObject], original: &[SceneObject]) -> Vec<(String, f32)> {
    let by_id = original_by_id(original);
    let mut out = Vec::new();
    for obj in objects.iter().filter(|o| !o.deleted && o.new_from.is_none()) {
        let Some(orig) = by_id.get(obj.id.as_str()) else { continue };
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

/// Edited typed properties of retail records: (offset, type, value).
fn prop_edits_between(objects: &[SceneObject], original: &[SceneObject]) -> Vec<(String, String, i64)> {
    let by_id = original_by_id(original);
    let mut out = Vec::new();
    for obj in objects.iter().filter(|o| !o.deleted && o.new_from.is_none()) {
        let Some(orig) = by_id.get(obj.id.as_str()) else { continue };
        for (p, q) in obj.props.iter().zip(orig.props.iter()) {
            if p.editable && p.value != q.value {
                out.push((p.offset.clone(), p.ty.clone(), p.value));
            }
        }
    }
    out
}

/// Structural changes for `tools/level_records.py`: duplicates first, then deletes.
fn ops_between(objects: &[SceneObject], original: &[SceneObject]) -> Vec<serde_json::Value> {
    let by_id = original_by_id(original);
    let mut ops = Vec::new();
    for o in objects.iter().filter(|o| !o.deleted) {
        if let Some(src) = &o.new_from {
            ops.push(serde_json::json!({
                "op": "duplicate",
                "offset": src,
                "shape": o.shape,
                "set": {
                    "position": o.position,
                    "scale": o.scale,
                    "rotation": o.rotation,
                    "props": o.props.iter().filter(|p| p.editable).map(|p| (p.name.clone(), p.value)).collect::<std::collections::BTreeMap<_, _>>(),
                },
            }));
        }
    }
    for o in objects.iter().filter(|o| o.deleted && by_id.contains_key(o.id.as_str())) {
        ops.push(serde_json::json!({"op": "delete", "offset": o.record_offset}));
    }
    ops
}

/// Writes `editor_projects/<level>.json` (objects plus the byte edits they imply).
fn write_project(root: &Path, scene: &Scene, original: &[SceneObject], collision: &[[f32; 3]], dropped: &[bool], boxes: &[([f32; 3], [f32; 3])]) -> Result<String, String> {
    validate_objects(&scene.objects)?;
    let mut edits: Vec<serde_json::Value> = edits_between(&scene.objects, original)
        .into_iter()
        .map(|(offset, value)| serde_json::json!({"offset": offset, "value": value}))
        .collect();
    edits.extend(
        prop_edits_between(&scene.objects, original)
            .into_iter()
            .map(|(offset, ty, value)| serde_json::json!({"offset": offset, "type": ty, "value": value})),
    );
    let project = serde_json::json!({
        "format": "DQXI_LEVEL_EDIT",
        "map": scene.id,
        "source": scene.source,
        "objects": scene.objects,
        "edits": edits,
        "ops": ops_between(&scene.objects, original),
        "collision": collision
            .iter()
            .enumerate()
            .filter(|(i, d)| d.iter().any(|v| v.abs() > 1e-6) || dropped.get(*i).copied().unwrap_or(false))
            .map(|(i, d)| serde_json::json!({"shape": i, "delta": d, "drop": dropped.get(i).copied().unwrap_or(false)}))
            .collect::<Vec<_>>(),
        "collision_boxes": boxes.iter().map(|(lo, hi)| serde_json::json!({"lo": lo, "hi": hi})).collect::<Vec<_>>(),
    });
    let dir = root.join("editor_projects");
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join(format!("{}.json", scene.id));
    serde_json::to_string_pretty(&project)
        .map_err(|e| e.to_string())
        .and_then(|text| std::fs::write(&path, text).map_err(|e| e.to_string()))
        .map_err(|e| format!("Save failed: {e}"))?;
    Ok(path.display().to_string())
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

// ---------------------------------------------------------------------------
// Godot-style editor UI: scene tree | viewport with tool gizmos | inspector
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Tool {
    Select,
    Move,
    Rotate,
    Scale,
}

impl Tool {
    fn label(self) -> &'static str {
        match self {
            Tool::Select => "Select",
            Tool::Move => "Move",
            Tool::Rotate => "Rotate",
            Tool::Scale => "Scale",
        }
    }
    fn key(self) -> &'static str {
        match self {
            Tool::Select => "Q",
            Tool::Move => "W",
            Tool::Rotate => "E",
            Tool::Scale => "R",
        }
    }
    fn hint(self) -> &'static str {
        match self {
            Tool::Select => "Click a marker to select it",
            Tool::Move => "Drag an arrow to move along that axis",
            Tool::Rotate => "Drag a ring to rotate around that axis",
            Tool::Scale => "Drag a handle to scale along that axis, or the centre cube to scale evenly",
        }
    }
}

/// A gizmo drag in progress: which handle, the value it started from and where.
#[derive(Clone, Copy)]
pub struct GizmoDrag {
    object: usize,
    tool: Tool,
    /// 0..3 = X/Y/Z, 3 = uniform (scale centre cube)
    axis: usize,
    start: [f32; 3],
    pointer: egui::Pos2,
}

const AXIS_COLORS: [egui::Color32; 3] = [
    egui::Color32::from_rgb(0xe8, 0x5a, 0x4f),
    egui::Color32::from_rgb(0x6b, 0xcb, 0x77),
    egui::Color32::from_rgb(0x4d, 0x8f, 0xf0),
];
const AXES: [Vec3; 3] = [Vec3 { x: 1.0, y: 0.0, z: 0.0 }, Vec3 { x: 0.0, y: 1.0, z: 0.0 }, Vec3 { x: 0.0, y: 0.0, z: 1.0 }];

fn kind_title(kind: &str) -> &'static str {
    match kind {
        "actor" => "Actors",
        "trigger" => "Triggers",
        "exit" => "Exits",
        "gimmick" => "Gimmicks",
        "symbol" => "Symbols",
        "placement" => "Placements",
        "transform" => "Transforms",
        _ => "Other",
    }
}

fn object_label(i: usize, obj: &SceneObject) -> String {
    let name = match obj.kind.as_str() {
        "actor" => "Actor",
        "trigger" => "Trigger",
        "exit" => "Exit",
        "gimmick" => "Gimmick",
        "symbol" => "Symbol",
        "placement" => "Placement",
        "transform" => "Transform",
        other => other,
    };
    let tag = if obj.deleted {
        "  (deleted)"
    } else if obj.new_from.is_some() {
        "  (new)"
    } else {
        ""
    };
    let entity = match monster_of(obj) {
        Some(m) if !m.name.is_empty() => format!("  \u{b7} {}", m.name),
        _ => obj
            .props
            .iter()
            .find(|p| p.name == "entity id")
            .map(|p| format!("  #{}", p.value))
            .unwrap_or_default(),
    };
    let entity = if obj.kind == "trigger" {
        String::new()
    } else if obj.kind == "exit" {
        exit_dest(obj).map(|d| format!("  >  {d}")).unwrap_or_default()
    } else if obj.kind == "gimmick" {
        gimmick_contents(obj).map(|d| format!("  \u{b7}  {d}")).unwrap_or_default()
    } else {
        entity
    };
    // actors carry their level group (top byte of key 60) and, when not "both", the view they are created in
    let entity = if obj.kind == "actor" {
        let group = obj.props.iter().find(|p| p.name == "key 60").map(|p| (p.value >> 24) & 0xFF);
        let view = match obj.props.iter().find(|p| p.name == "entity class").map(|p| (p.value >> 8) & 0xFF) {
            Some(1) => " 3D",
            Some(2) => " 2D",
            _ => "",
        };
        match group {
            Some(g) => format!("{entity}  [g{g}{view}]"),
            None => entity,
        }
    } else {
        entity
    };
    format!("{name} {i:03}{entity}{tag}")
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
    let Some(scene) = app.panels.editor.scene.clone() else {
        start_page(app, ui);
        return;
    };
    // the region decides what an actor id means; recomputed every frame so switching levels is safe
    CUR_REGION.store(
        LEVEL_REGIONS.get().and_then(|m| m.get(&scene.id)).copied().unwrap_or(-1),
        std::sync::atomic::Ordering::Relaxed,
    );
    if app.panels.editor.collision_for != scene.id {
        let shapes = crate::data::collision::load(&app.dirs.root, &scene.id).unwrap_or_default();
        let panel = &mut app.panels.editor;
        panel.collision_moves = vec![[0.0; 3]; shapes.len()];
        panel.collision_dropped = vec![false; shapes.len()];
        panel.collision_boxes.clear();
        panel.collision_undo.clear();
        panel.collision = Arc::new(shapes);
        panel.collision_for = scene.id.clone();
        panel.collision_sel = None;
    }
    editor_shortcuts(app, ui.ctx(), &scene);
    let root = app.dirs.root.clone();

    let swapped = app.panels.editor.swap_docks;
    let dock_frame = || egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8));
    if app.panels.editor.show_scene_dock && app.panels.editor.float_scene {
        let mut open = true;
        egui::Window::new("Scene").open(&mut open).default_pos([270.0, 150.0]).default_size([260.0, 520.0]).resizable(true).show(ui.ctx(), |ui| scene_dock(app, ui, &scene));
        if !open {
            app.panels.editor.float_scene = false;
        }
    } else if app.panels.editor.show_scene_dock {
        let panel = if swapped { egui::Panel::right("editor_scene_r") } else { egui::Panel::left("editor_scene") };
        panel.resizable(true).default_size(250.0).min_size(180.0).frame(dock_frame()).show(ui, |ui| scene_dock(app, ui, &scene));
    }
    if app.panels.editor.show_inspector_dock && app.panels.editor.float_inspector {
        let mut open = true;
        egui::Window::new("Inspector").open(&mut open).default_pos([ui.ctx().content_rect().right() - 360.0, 150.0]).default_size([340.0, 560.0]).resizable(true).show(ui.ctx(), |ui| inspector_dock(app, ui, &scene, &root));
        if !open {
            app.panels.editor.float_inspector = false;
        }
    } else if app.panels.editor.show_inspector_dock {
        let panel = if swapped { egui::Panel::left("editor_inspector_l") } else { egui::Panel::right("editor_inspector") };
        panel.resizable(true).default_size(340.0).min_size(250.0).frame(dock_frame()).show(ui, |ui| inspector_dock(app, ui, &scene, &root));
    }
    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG).inner_margin(egui::Margin::same(0)))
        .show(ui, |ui| {
            toolbar(app, ui, &scene, &root);
            editor_viewport(app, ui, &scene);
        });
}

fn start_page(app: &mut ViewerApp, ui: &mut egui::Ui) {
    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.vertical_centered(|ui| {
                ui.add_space(ui.available_height() * 0.3);
                if app.panels.editor.loading {
                    ui.label(theme::heading(format!("Loading {}\u{2026}", app.panels.editor.selected_map.clone().unwrap_or_default())));
                    return;
                }
                ui.label(theme::heading("Level Editor"));
                ui.add_space(4.0);
                ui.label(theme::dim_label(format!("{} decoded levels", human_count(app.panels.editor.maps.len()))));
                ui.add_space(10.0);
                ui.label(theme::faint_label("Open a level from the Project dock (Levels), or press Ctrl+P and type its id."));
                ui.add_space(10.0);
                if ui.button("Quick Open\u{2026}").clicked() {
                    app.shell.palette_open = true;
                }
                ui.add_space(14.0);
                ui.label(theme::faint_label("Tools: Q select \u{b7} W move \u{b7} E rotate \u{b7} R scale \u{b7} F focus \u{b7} Ctrl+Z undo \u{b7} Ctrl+S save"));
            });
        });
}

/// Godot-style editor keys: Q/W/E/R tools, F focus, Esc deselect, Delete/Ctrl+D (not yet supported).
fn editor_shortcuts(app: &mut ViewerApp, ctx: &egui::Context, scene: &Scene) {
    if ctx.egui_wants_keyboard_input() {
        return;
    }
    let (q, w, e, r, f, esc, del, dup) = ctx.input(|i| {
        let plain = !i.modifiers.command && !i.modifiers.alt;
        (
            plain && i.key_pressed(egui::Key::Q),
            plain && i.key_pressed(egui::Key::W),
            plain && i.key_pressed(egui::Key::E),
            plain && i.key_pressed(egui::Key::R),
            plain && i.key_pressed(egui::Key::F),
            i.key_pressed(egui::Key::Escape),
            i.key_pressed(egui::Key::Delete),
            i.modifiers.command && i.key_pressed(egui::Key::D),
        )
    });
    let panel = &mut app.panels.editor;
    if q {
        panel.tool = Tool::Select;
    }
    if w {
        panel.tool = Tool::Move;
    }
    if e {
        panel.tool = Tool::Rotate;
    }
    if r {
        panel.tool = Tool::Scale;
    }
    if esc {
        panel.selected_object = None;
    }
    if f {
        panel.focus_selection(scene);
    }
    if dup {
        if let Err(e) = panel.duplicate_selected() {
            app.status = e;
        }
    }
    if del {
        if let Err(e) = panel.delete_selected() {
            app.status = e;
        }
    }
}

impl EditorPanel {
    fn focus_selection(&mut self, scene: &Scene) {
        if let Some(obj) = self.selected_object.and_then(|i| scene.objects.get(i)) {
            self.camera.target = Vec3::new(obj.position[0], obj.position[1], obj.position[2]);
            let radius = obj.scale.iter().fold(1.0f32, |a, b| a.max(b.abs()));
            self.camera.distance = (radius * 4.0).clamp(4.0, 60.0);
        }
    }

    /// Ctrl+D: a copy of the selected node, placed beside it.
    pub fn duplicate_selected(&mut self) -> Result<(), String> {
        let i = self.selected_object.ok_or("Select a node first")?;
        let src = self
            .scene
            .as_ref()
            .and_then(|s| s.objects.get(i))
            .cloned()
            .ok_or("Select a node first")?;
        if src.deleted {
            return Err("That node is deleted; restore it first".into());
        }
        if src.shape == 0 && src.new_from.is_none() {
            return Err("This level's records carry no size information; re-export it with python tools/map_tool.py export".into());
        }
        self.begin_change();
        let scene = self.scene.as_mut().ok_or("No level open")?;
        let next = scene
            .objects
            .iter()
            .filter_map(|o| o.id.strip_prefix("new_").and_then(|n| n.parse::<usize>().ok()))
            .max()
            .map(|n| n + 1)
            .unwrap_or(1);
        let mut copy = src.clone();
        copy.id = format!("new_{next}");
        copy.new_from = Some(src.new_from.clone().unwrap_or_else(|| src.record_offset.clone()));
        copy.field_offsets = FieldOffsets::default();
        copy.position[0] += src.scale[0].abs().max(1.0);
        // an actor whose class mask excludes the normal 3D view would never appear: the copy is created in both views
        let mut widened = false;
        if copy.kind == "actor" {
            if let Some(p) = copy.props.iter_mut().find(|p| p.name == "entity class") {
                if (p.value >> 8) & 0xFF != 3 {
                    p.value = 0x300;
                    widened = true;
                }
            }
        }
        scene.objects.insert(i + 1, copy);
        self.selected_object = Some(i + 1);
        self.tree_scroll = true;
        self.status = if widened {
            "Duplicated; the copy's class was set to 0x300 so it is created in both the 3D view and the 2D mode (its level group stays: a disabled group hides it)".into()
        } else {
            "Duplicated. The copy is added to the level when you save to the mod (appending actor records is proven in the emulator; other kinds are not yet)".into()
        };
        Ok(())
    }

    /// Delete: new copies vanish, retail records are marked and removed on export.
    pub fn delete_selected(&mut self) -> Result<(), String> {
        let i = self.selected_object.ok_or("Select a node first")?;
        let obj = self
            .scene
            .as_ref()
            .and_then(|s| s.objects.get(i))
            .cloned()
            .ok_or("Select a node first")?;
        self.begin_change();
        let scene = self.scene.as_mut().ok_or("No level open")?;
        if obj.new_from.is_some() {
            scene.objects.remove(i);
            self.selected_object = None;
            self.status = "Removed the copy".into();
        } else {
            scene.objects[i].deleted = true;
            self.status = "Deleted (actor deletes are emulator-proven, see docs/LEVEL_FORMAT.md; other kinds are not)".into();
        }
        Ok(())
    }

    /// Viewport preferences as JSON (written to `editor_prefs.json` when they change).
    pub fn prefs_json(&self) -> String {
        serde_json::json!({
            "snap": self.snap,
            "snap_step": self.snap_step,
            "show_objects": self.show_objects,
            "show_collision": self.show_collision,
            "show_bounds": self.show_bounds,
            "show_grid": self.show_grid,
            "show_scene_dock": self.show_scene_dock,
            "swap_docks": self.swap_docks,
            "float_scene": self.float_scene,
            "float_inspector": self.float_inspector,
            "show_inspector_dock": self.show_inspector_dock,
            "show_axes": self.show_axes,
            "show_labels": self.show_labels,
        })
        .to_string()
    }

    pub fn apply_prefs(&mut self, text: &str) {
        let Ok(v) = serde_json::from_str::<serde_json::Value>(text) else { return };
        let b = |k: &str, d: bool| v[k].as_bool().unwrap_or(d);
        self.snap = b("snap", self.snap);
        self.snap_step = v["snap_step"].as_f64().map(|x| x as f32).filter(|x| *x > 0.0).unwrap_or(self.snap_step);
        self.show_objects = b("show_objects", self.show_objects);
        self.show_collision = b("show_collision", self.show_collision);
        self.show_bounds = b("show_bounds", self.show_bounds);
        self.show_grid = b("show_grid", self.show_grid);
        self.show_scene_dock = b("show_scene_dock", true);
        self.swap_docks = b("swap_docks", false);
        self.float_scene = b("float_scene", false);
        self.float_inspector = b("float_inspector", false);
        self.show_inspector_dock = b("show_inspector_dock", true);
        self.show_axes = b("show_axes", self.show_axes);
        self.show_labels = b("show_labels", self.show_labels);
    }

    /// Every selected node: the primary one and the Shift+click extras.
    fn selection(&self) -> Vec<usize> {
        let mut all: Vec<usize> = self.selected_object.into_iter().collect();
        for i in &self.multi {
            if !all.contains(i) {
                all.push(*i);
            }
        }
        all
    }

    /// Moves every selected node by `delta` (one undo step).
    fn move_selection(&mut self, delta: [f32; 3]) {
        let ids = self.selection();
        if ids.is_empty() {
            return;
        }
        self.begin_change();
        if let Some(scene) = self.scene.as_mut() {
            for i in ids {
                if let Some(o) = scene.objects.get_mut(i) {
                    for a in 0..3 {
                        o.position[a] += delta[a];
                    }
                }
            }
        }
        self.status = format!("Moved {} node(s)", self.selection().len());
    }

    /// Deletes every selected node (copies are removed, retail records flagged), one undo step.
    fn delete_all_selected(&mut self) {
        let mut ids = self.selection();
        if ids.is_empty() {
            return;
        }
        ids.sort_unstable_by(|a, b| b.cmp(a));
        self.begin_change();
        let n = ids.len();
        if let Some(scene) = self.scene.as_mut() {
            for i in ids {
                if i >= scene.objects.len() {
                    continue;
                }
                if scene.objects[i].new_from.is_some() {
                    scene.objects.remove(i);
                } else {
                    scene.objects[i].deleted = true;
                }
            }
        }
        self.selected_object = None;
        self.multi.clear();
        self.status = format!("Deleted {n} node(s)");
    }

    /// Records an undo step before the first change of a drag or edit.
    fn begin_change(&mut self) {
        if let Some(scene) = &self.scene {
            self.undo.push(scene.objects.clone());
            self.redo.clear();
            self.dirty = true;
        }
    }

    fn changed_objects(&self) -> Vec<usize> {
        let Some(scene) = &self.scene else { return Vec::new() };
        changed_between(&scene.objects, &self.original)
    }
}

fn toolbar(app: &mut ViewerApp, ui: &mut egui::Ui, scene: &Scene, root: &Path) {
    egui::Frame::new()
        .fill(theme::BG_RAISED)
        .inner_margin(egui::Margin::symmetric(8, 4))
        .show(ui, |ui| {
            ui.horizontal_wrapped(|ui| {
                let panel = &mut app.panels.editor;
                for tool in [Tool::Select, Tool::Move, Tool::Rotate, Tool::Scale] {
                    let selected = panel.tool == tool;
                    let text = egui::RichText::new(tool.label());
                    let text = if selected { text.color(theme::ON_LIGHT).strong() } else { text.color(theme::TEXT_DIM) };
                    let button = egui::Button::new(text).fill(if selected { theme::ACCENT } else { theme::BG_HOVER });
                    if ui.add(button).on_hover_text(format!("{}  ({})\n{}", tool.label(), tool.key(), tool.hint())).clicked() {
                        panel.tool = tool;
                    }
                }
                ui.separator();
                ui.checkbox(&mut panel.snap, "Snap").on_hover_text("Round moves to the step, rotations to 15\u{b0}");
                ui.add_enabled(
                    panel.snap,
                    egui::DragValue::new(&mut panel.snap_step).range(0.01..=16.0).speed(0.05).max_decimals(2),
                )
                .on_hover_text("Snap step in world units");
                ui.separator();
                if ui.button("Focus").on_hover_text("Centre the camera on the selection (F)").clicked() {
                    panel.focus_selection(scene);
                }
                ui.separator();
                if ui.button("Duplicate").on_hover_text("Copy the selected node (Ctrl+D)").clicked() {
                    if let Err(e) = panel.duplicate_selected() {
                        panel.status = e;
                    }
                }
                if ui.button("Delete").on_hover_text("Remove the selected node from the level (Delete)").clicked() {
                    if let Err(e) = panel.delete_selected() {
                        panel.status = e;
                    }
                }
                if ui.selectable_label(panel.history_open, "History").on_hover_text("List every edit step of this level and jump back to any of them").clicked() {
                    panel.history_open = !panel.history_open;
                }
                if ui.selectable_label(panel.clone_open, "Level").on_hover_text("Clone this level into an unused slot (new map)").clicked() {
                    panel.clone_open = !panel.clone_open;
                }
                ui.menu_button("View", |ui| {
                    ui.checkbox(&mut panel.show_objects, "Markers");
                    ui.checkbox(&mut panel.show_collision, "Collision")
                        .on_hover_text("Draw the wall collision shapes of the level (3d/bg/<level>_chit.rcb)");
                    ui.checkbox(&mut panel.show_bounds, "Bounding boxes");
                    ui.checkbox(&mut panel.show_labels, "Labels");
                    ui.checkbox(&mut panel.show_models, "Models at actors")
                        .on_hover_text("Draw each monster's real model at its marker");
                    ui.separator();
                    ui.checkbox(&mut panel.show_scene_dock, "Scene dock");
                    ui.checkbox(&mut panel.swap_docks, "Swap dock sides");
                    ui.checkbox(&mut panel.float_scene, "Float Scene dock");
                    ui.checkbox(&mut panel.float_inspector, "Float Inspector dock");
                    ui.checkbox(&mut panel.show_inspector_dock, "Inspector dock");
                    ui.separator();
                    ui.checkbox(&mut panel.show_grid, "Grid");
                    ui.checkbox(&mut panel.show_axes, "Axes");
                    ui.checkbox(&mut panel.wireframe, "Wireframe");
                    ui.checkbox(&mut panel.flat, "Flat shading");
                    ui.separator();
                    if ui.button("Reset camera").clicked() {
                        panel.camera = Camera::default();
                        if let Some(mesh) = panel.mesh.clone() {
                            panel.camera.frame(&mesh.bounds);
                        }
                        ui.close();
                    }
                });
                ui.separator();
                {
                    if ui.add_enabled(!panel.undo.is_empty(), egui::Button::new("Undo")).on_hover_text("Ctrl+Z").clicked() {
                        panel.undo_action();
                    }
                    if ui.add_enabled(!panel.redo.is_empty(), egui::Button::new("Redo")).on_hover_text("Ctrl+Y").clicked() {
                        panel.redo_action();
                    }
                    if ui.add_enabled(panel.dirty, egui::Button::new("Save")).on_hover_text("Write the project file (Ctrl+S)").clicked() {
                        panel.save_project(root);
                    }
                    if ui.button("Export BXON").on_hover_text("Write level3d.patched.bxon next to the source").clicked() {
                        panel.export_patch(root);
                    }
                    if ui
                        .button("Save to mod")
                        .on_hover_text("Patch level3d.bxon and stage mod/romfs/level3d/<map>.pack for Luma LayeredFS")
                        .clicked()
                    {
                        panel.save_to_mod(root);
                    }
                }
            });
        });
    if app.panels.editor.history_open {
        let mut open = true;
        let mut jump: Option<usize> = None;
        egui::Window::new("History").open(&mut open).collapsible(false).default_width(320.0).anchor(egui::Align2::RIGHT_TOP, [-360.0, 120.0]).show(ui.ctx(), |ui| {
            let panel = &app.panels.editor;
            if panel.undo.is_empty() {
                ui.label(theme::faint_label("No edits yet. Every move, delete, duplicate or property change becomes a step here."));
            }
            egui::ScrollArea::vertical().max_height(320.0).show(ui, |ui| {
                ui.label(egui::RichText::new("Now").color(theme::ACCENT).strong());
                for k in (0..panel.undo.len()).rev() {
                    let text = format!("{:02}  {}", k + 1, panel.step_summary(k));
                    if ui.selectable_label(false, text).on_hover_text("Go back to the state before this step").clicked() {
                        jump = Some(k);
                    }
                }
                ui.label(theme::faint_label("Original"));
            });
            if !panel.redo.is_empty() {
                ui.label(theme::faint_label(format!("{} step(s) can be redone (Ctrl+Y)", panel.redo.len())));
            }
        });
        if let Some(k) = jump {
            app.panels.editor.jump_to_step(k);
        }
        app.panels.editor.history_open = open;
    }
    if app.panels.editor.clone_open {
        let mut open = true;
        let current = scene.id.clone();
        egui::Window::new("Clone level into slot").open(&mut open).collapsible(false).resizable(false).anchor(egui::Align2::RIGHT_TOP, [-360.0, 120.0]).show(ui.ctx(), |ui| {
            let panel = &mut app.panels.editor;
            ui.label(theme::faint_label("Writes a copy of this level over the chosen level slot in mod/romfs (that level is replaced in the mod). Then point an exit at the slot's map id."));
            let maps = panel.maps.clone();
            egui::ComboBox::from_id_salt("clone_slot")
                .selected_text(if panel.clone_target.is_empty() { "choose slot\u{2026}".to_string() } else { panel.clone_target.clone() })
                .width(220.0)
                .show_ui(ui, |ui| {
                    for m in maps.iter().filter(|m| **m != current && m.len() == current.len()) {
                        if ui.selectable_label(panel.clone_target == **m, m).clicked() {
                            panel.clone_target = m.clone();
                        }
                    }
                });
            let model_id = ui.make_persistent_id("clone_model_path");
            let mut model: String = ui.data_mut(|d| d.get_temp(model_id).unwrap_or_default());
            ui.add(egui::TextEdit::singleline(&mut model).hint_text("optional: background model .bch (e.g. from Import OBJ)").desired_width(300.0));
            ui.data_mut(|d| d.insert_temp(model_id, model.clone()));
            if ui
                .add_enabled(!panel.clone_target.is_empty(), egui::Button::new("Clone into slot"))
                .on_hover_text("Writes the level3d, level2d and background packs of this level under the slot's name into mod/romfs (tools/new_map.py). Point an exit's destination at the slot's map id to enter it.")
                .clicked()
            {
                let mut cmd = std::process::Command::new("python");
                cmd.args(["tools/new_map.py", &current, &panel.clone_target]).arg(root.join("mod"));
                if !model.trim().is_empty() {
                    cmd.arg("--bch").arg(model.trim());
                }
                let result = cmd.current_dir(root).output();
                panel.status = match result {
                    Ok(o) if o.status.success() => format!("Cloned {current} into {} (mod/romfs); aim an exit at that map", panel.clone_target),
                    Ok(o) => format!("Clone failed: {}", String::from_utf8_lossy(&o.stderr).lines().last().unwrap_or("")),
                    Err(e) => format!("Clone failed: {e}"),
                };
            }
            ui.separator();
            ui.label(egui::RichText::new("Demo").strong());
            ui.label(theme::faint_label("Builds the demo \"custom room\" into mod/romfs: the church door leads into a new room with an NPC who says a new line (tools/custom_room.py, docs/CUSTOM_ROOM.md). Overwrites those files in mod/."));
            if ui.button("Build demo room into mod/").clicked() {
                let result = std::process::Command::new("python")
                    .args(["tools/custom_room.py", "build", "--mod"])
                    .arg(root.join("mod"))
                    .env("CR_DONOR", "church")
                    .env("CR_PLAIN", "coll")
                    .env("CR_SKIP", "monster")
                    .env("PYTHONUTF8", "1")
                    .current_dir(root)
                    .output();
                app.panels.editor.status = match result {
                    Ok(o) if o.status.success() => "Demo room written to mod/romfs: export the mod and walk out of the Heliodor church".to_string(),
                    Ok(o) => format!("Demo build failed: {}", String::from_utf8_lossy(&o.stderr).lines().last().unwrap_or("")),
                    Err(e) => format!("Demo build failed: {e}"),
                };
            }
            ui.label(theme::faint_label(app.panels.editor.status.clone()));
        });
        app.panels.editor.clone_open = open;
    }
    let fresh = {
        let panel = &mut app.panels.editor;
        panel.tools.show_status(ui, root)
    };
    if fresh {
        let panel = &mut app.panels.editor;
        app.status = match panel.tools.error.clone() {
            Some(error) => format!("map save failed: {error}"),
            None => panel.tools.message.clone(),
        };
    }
}

// -- scene dock ---------------------------------------------------------------

enum TreeRow {
    Root,
    Group(&'static str, usize),
    /// actors of one level group (top byte of key 60) under the Actors group
    SubGroup(u32, usize),
    Object(usize),
}

fn scene_dock(app: &mut ViewerApp, ui: &mut egui::Ui, scene: &Scene) {
    let changed = app.panels.editor.changed_objects();
    ui.horizontal(|ui| {
        ui.label(theme::heading("Scene"));
        if app.panels.editor.dirty {
            ui.label(egui::RichText::new("\u{25cf} unsaved").color(theme::ACCENT).size(11.0));
        }
    });
    ui.add(
        egui::TextEdit::singleline(&mut app.panels.editor.tree_filter)
            .hint_text("Filter nodes\u{2026}")
            .desired_width(f32::INFINITY),
    );
    // an actor's class word (+0x5E) is a display-mode mask: the level loader keeps a record only when
    // (mask & mode) != 0 with mode 1 = normal 3D, 2 = 2D mode (Event_Sequence_DispatchCommands)
    let layer_of = |o: &SceneObject| o.props.iter().find(|p| p.name == "entity class").map(|p| ((p.value >> 8) & 0xFF) as u32);
    let mixed = scene.objects.iter().filter(|o| o.kind == "actor").filter_map(layer_of).any(|m| m != 3);
    if mixed {
        let current = app.panels.editor.layer_filter;
        egui::ComboBox::from_id_salt("layer_filter")
            .selected_text(match current {
                Some(1) => "Actors in 3D mode",
                Some(2) => "Actors in 2D mode",
                _ => "All actors",
            })
            .width(ui.available_width())
            .show_ui(ui, |ui| {
                if ui.selectable_label(current.is_none(), "All actors").clicked() {
                    app.panels.editor.layer_filter = None;
                }
                if ui.selectable_label(current == Some(1), "Actors in 3D mode").on_hover_text("what the game creates in the normal 3D view").clicked() {
                    app.panels.editor.layer_filter = Some(1);
                }
                if ui.selectable_label(current == Some(2), "Actors in 2D mode").on_hover_text("what the game creates when the 2D mode is on").clicked() {
                    app.panels.editor.layer_filter = Some(2);
                }
            });
    } else {
        app.panels.editor.layer_filter = None;
    }
    ui.separator();

    let layer_filter = app.panels.editor.layer_filter;
    let filter = app.panels.editor.tree_filter.to_lowercase();
    let mut rows: Vec<TreeRow> = vec![TreeRow::Root];
    let mut visible_objects: Vec<usize> = Vec::new();
    for kind in ["actor", "symbol", "exit", "gimmick", "trigger", "placement", "transform"] {
        let members: Vec<usize> = scene
            .objects
            .iter()
            .enumerate()
            .filter(|(i, o)| {
                o.kind == kind
                    && (kind != "actor" || layer_filter.is_none() || layer_of(o).map_or(true, |m| m & layer_filter.unwrap_or(3) != 0))
                    && (filter.is_empty()
                        || object_label(*i, o).to_lowercase().contains(&filter)
                        || o.id.to_lowercase().contains(&filter))
            })
            .map(|(i, _)| i)
            .collect();
        if members.is_empty() {
            continue;
        }
        rows.push(TreeRow::Group(kind_title(kind), members.len()));
        if !app.panels.editor.collapsed.contains(kind) || !filter.is_empty() {
            let group_of = |i: usize| -> u32 {
                scene.objects[i].props.iter().find(|p| p.name == "key 60").map(|p| ((p.value >> 24) & 0xFF) as u32).unwrap_or(0)
            };
            let mut groups: Vec<u32> = if kind == "actor" { members.iter().map(|i| group_of(*i)).collect() } else { Vec::new() };
            groups.sort_unstable();
            groups.dedup();
            if groups.len() > 1 {
                for g in groups {
                    let of_group: Vec<usize> = members.iter().copied().filter(|i| group_of(*i) == g).collect();
                    rows.push(TreeRow::SubGroup(g, of_group.len()));
                    if !app.panels.editor.collapsed.contains(&format!("actor_g{g}")) || !filter.is_empty() {
                        visible_objects.extend(of_group.iter().copied());
                        rows.extend(of_group.into_iter().map(TreeRow::Object));
                    }
                }
            } else {
                visible_objects.extend(members.iter().copied());
                rows.extend(members.into_iter().map(TreeRow::Object));
            }
        }
    }
    let selected = app.panels.editor.selected_object;
    let mut pick: Option<usize> = None;
    let mut toggle: Option<&'static str> = None;
    let mut sub_toggle: Option<String> = None;
    if let Some((i, _)) = crate::ui::list_nav(ui.ctx(), &visible_objects, selected.as_ref()) {
        pick = Some(i);
        app.panels.editor.tree_scroll = true;
    }
    let mut area = egui::ScrollArea::vertical().id_salt("editor_scene_tree").auto_shrink([false, false]);
    if std::mem::take(&mut app.panels.editor.tree_scroll) {
        if let Some(at) = rows.iter().position(|r| matches!(r, TreeRow::Object(i) if Some(*i) == pick.or(selected))) {
            area = area.vertical_scroll_offset((at as f32 * 19.0 - 140.0).max(0.0));
        }
    }
    area.show_rows(ui, 19.0, rows.len(), |ui, range| {
        for at in range {
            let (rect, response) = ui.allocate_exact_size(egui::vec2(ui.available_width(), 19.0), egui::Sense::click());
            let painter = ui.painter_at(rect);
            let mid = rect.center().y;
            match &rows[at] {
                TreeRow::Root => {
                    painter.text(
                        egui::pos2(rect.left() + 4.0, mid),
                        egui::Align2::LEFT_CENTER,
                        &scene.id,
                        egui::FontId::proportional(12.5),
                        theme::TEXT,
                    );
                    painter.text(
                        egui::pos2(rect.right() - 4.0, mid),
                        egui::Align2::RIGHT_CENTER,
                        format!("{} nodes", human_count(scene.objects.len())),
                        egui::FontId::proportional(10.5),
                        theme::TEXT_FAINT,
                    );
                }
                TreeRow::Group(title, count) => {
                    let kind = match *title {
                        "Actors" => "actor",
                        "Triggers" => "trigger",
                        "Exits" => "exit",
                        "Gimmicks" => "gimmick",
                        "Symbols" => "symbol",
                        "Placements" => "placement",
                        _ => "transform",
                    };
                    let open = !app.panels.editor.collapsed.contains(kind) || !filter.is_empty();
                    let x = rect.left() + 10.0;
                    let pts = if open {
                        vec![egui::pos2(x, mid - 2.0), egui::pos2(x + 8.0, mid - 2.0), egui::pos2(x + 4.0, mid + 3.0)]
                    } else {
                        vec![egui::pos2(x + 1.0, mid - 4.0), egui::pos2(x + 1.0, mid + 4.0), egui::pos2(x + 6.0, mid)]
                    };
                    painter.add(egui::Shape::convex_polygon(pts, theme::TEXT_DIM, egui::Stroke::NONE));
                    painter.text(egui::pos2(x + 14.0, mid), egui::Align2::LEFT_CENTER, *title, egui::FontId::proportional(12.0), theme::TEXT_DIM);
                    painter.text(
                        egui::pos2(rect.right() - 4.0, mid),
                        egui::Align2::RIGHT_CENTER,
                        human_count(*count),
                        egui::FontId::proportional(10.5),
                        theme::TEXT_FAINT,
                    );
                    if response.clicked() {
                        toggle = Some(kind_static(kind));
                    }
                }
                TreeRow::SubGroup(g, count) => {
                    let key = format!("actor_g{g}");
                    let open = !app.panels.editor.collapsed.contains(&key) || !filter.is_empty();
                    let x = rect.left() + 22.0;
                    let pts = if open {
                        vec![egui::pos2(x, mid - 2.0), egui::pos2(x + 7.0, mid - 2.0), egui::pos2(x + 3.5, mid + 2.5)]
                    } else {
                        vec![egui::pos2(x + 1.0, mid - 3.5), egui::pos2(x + 1.0, mid + 3.5), egui::pos2(x + 5.0, mid)]
                    };
                    painter.add(egui::Shape::convex_polygon(pts, theme::TEXT_DIM, egui::Stroke::NONE));
                    painter.text(egui::pos2(x + 12.0, mid), egui::Align2::LEFT_CENTER, format!("Level group {g}"), egui::FontId::proportional(11.5), theme::TEXT_DIM);
                    painter.text(egui::pos2(rect.right() - 4.0, mid), egui::Align2::RIGHT_CENTER, human_count(*count), egui::FontId::proportional(10.5), theme::TEXT_FAINT);
                    if response.clicked() {
                        sub_toggle = Some(key);
                    }
                }
                TreeRow::Object(i) => {
                    let is_sel = selected == Some(*i) || app.panels.editor.multi.contains(i);
                    if is_sel {
                        painter.rect_filled(rect, 2.0, theme::BG_SELECT);
                    } else if response.hovered() {
                        painter.rect_filled(rect, 2.0, theme::BG_HOVER);
                    }
                    let obj = &scene.objects[*i];
                    let dot = kind_color(&obj.kind);
                    painter.circle_filled(egui::pos2(rect.left() + 24.0, mid), 3.5, dot);
                    let modified = changed.contains(i);
                    painter.text(
                        egui::pos2(rect.left() + 34.0, mid),
                        egui::Align2::LEFT_CENTER,
                        object_label(*i, obj),
                        egui::FontId::proportional(12.0),
                        if obj.deleted { theme::ERR } else if is_sel { theme::TEXT } else { theme::TEXT_DIM },
                    );
                    if modified {
                        painter.text(
                            egui::pos2(rect.right() - 6.0, mid),
                            egui::Align2::RIGHT_CENTER,
                            "\u{25cf}",
                            egui::FontId::proportional(10.0),
                            theme::ACCENT,
                        );
                    }
                    if response.clicked() {
                        pick = Some(*i);
                    }
                    if response.double_clicked() {
                        pick = Some(*i);
                        app.panels.editor.pending_focus = true;
                    }
                    if response.secondary_clicked() && app.panels.editor.selected_object != Some(*i) && !app.panels.editor.multi.contains(i) {
                        app.panels.editor.multi.clear();
                        app.panels.editor.selected_object = Some(*i);
                    }
                    response.context_menu(|ui| {
                        if ui.button("Focus   F").clicked() {
                            app.panels.editor.selected_object = Some(*i);
                            app.panels.editor.focus_selection(scene);
                            ui.close();
                        }
                        if ui.button("Duplicate   Ctrl+D").clicked() {
                            if let Err(e) = app.panels.editor.duplicate_selected() {
                                app.status = e;
                            }
                            ui.close();
                        }
                        if ui.button("Delete   Del").clicked() {
                            if app.panels.editor.multi.is_empty() {
                                if let Err(e) = app.panels.editor.delete_selected() {
                                    app.status = e;
                                }
                            } else {
                                app.panels.editor.delete_all_selected();
                            }
                            ui.close();
                        }
                        if !app.panels.editor.multi.is_empty() && ui.button("Clear selection   Esc").clicked() {
                            app.panels.editor.multi.clear();
                            ui.close();
                        }
                    });
                }
            }
        }
    });
    if let Some(key) = sub_toggle {
        let panel = &mut app.panels.editor;
        if !panel.collapsed.remove(&key) {
            panel.collapsed.insert(key);
        }
    }
    if let Some(kind) = toggle {
        let panel = &mut app.panels.editor;
        if !panel.collapsed.remove(kind) {
            panel.collapsed.insert(kind.to_string());
        }
    }
    if let Some(i) = pick {
        if ui.input(|inp| inp.modifiers.shift) && app.panels.editor.selected_object.is_some() && app.panels.editor.selected_object != Some(i) {
            // Shift+click in the tree adds / removes a node from the group selection
            let p = &mut app.panels.editor;
            if let Some(at) = p.multi.iter().position(|m| *m == i) {
                p.multi.remove(at);
            } else {
                p.multi.push(i);
            }
            return;
        }
        app.panels.editor.multi.clear();
        app.panels.editor.selected_object = Some(i);
        if std::mem::take(&mut app.panels.editor.pending_focus) {
            app.panels.editor.focus_selection(scene);
        }
    }
}

fn kind_static(kind: &str) -> &'static str {
    match kind {
        "actor" => "actor",
        "trigger" => "trigger",
        "exit" => "exit",
        "gimmick" => "gimmick",
        "symbol" => "symbol",
        "placement" => "placement",
        _ => "transform",
    }
}

fn kind_color(kind: &str) -> egui::Color32 {
    match kind {
        "actor" => egui::Color32::from_rgb(0xf0, 0x9a, 0x4b),
        "trigger" => egui::Color32::from_rgb(0x4d, 0xd0, 0xb8),
        "exit" => egui::Color32::from_rgb(0xf2, 0xc9, 0x4c),
        "gimmick" => egui::Color32::from_rgb(0xd9, 0x8c, 0xff),
        "symbol" => egui::Color32::from_rgb(0xe5, 0x5b, 0x5b),
        "placement" => egui::Color32::from_rgb(0x6a, 0xb8, 0xd8),
        _ => egui::Color32::from_rgb(0xc7, 0x92, 0xea),
    }
}

// -- inspector ------------------------------------------------------------------

/// One labelled X/Y/Z row with coloured axis tags and a reset button.
fn vec3_row(ui: &mut egui::Ui, label: &str, values: &mut [f32; 3], original: [f32; 3], speed: f64, scale: f32, suffix: &str) -> bool {
    let mut changed = false;
    ui.horizontal(|ui| {
        ui.add_sized([62.0, 18.0], egui::Label::new(theme::dim_label(label)));
        for (i, tag) in ["X", "Y", "Z"].iter().enumerate() {
            ui.label(egui::RichText::new(*tag).color(AXIS_COLORS[i]).strong().size(11.0));
            let mut shown = values[i] * scale;
            let response = ui.add(
                egui::DragValue::new(&mut shown)
                    .speed(speed)
                    .max_decimals(3)
                    .suffix(suffix),
            );
            if response.changed() {
                values[i] = shown / scale;
                changed = true;
            }
        }
        let differs = values.iter().zip(original.iter()).any(|(a, b)| (a - b).abs() > 1e-6);
        if ui
            .add_enabled(differs, egui::Button::new("reset").small())
            .on_hover_text("Revert to the value in the retail file")
            .clicked()
        {
            *values = original;
            changed = true;
        }
    });
    changed
}

/// The level's collision shapes: pick one to highlight it in the viewport.
/// Wraps the collision group with undo: every change pushes the state before it (a drag is one step).
fn collision_section(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let snapshot = |p: &EditorPanel| -> CollisionState { (p.collision_moves.clone(), p.collision_dropped.clone(), p.collision_boxes.clone()) };
    let before = snapshot(&app.panels.editor);
    let can_undo = !app.panels.editor.collision_undo.is_empty();
    if can_undo && ui.small_button("Undo collision edit").on_hover_text("Revert the last move, delete or added box").clicked() {
        if let Some((moves, dropped, boxes)) = app.panels.editor.collision_undo.pop() {
            let p = &mut app.panels.editor;
            p.collision_moves = moves;
            p.collision_dropped = dropped;
            p.collision_boxes = boxes;
            p.dirty = true;
        }
    }
    let before = if can_undo { snapshot(&app.panels.editor) } else { before };
    collision_section_inner(app, ui);
    let after = snapshot(&app.panels.editor);
    let down = ui.input(|i| i.pointer.any_down());
    let p = &mut app.panels.editor;
    if after != before {
        if !(down && p.collision_undo_open) {
            p.collision_undo.push(before);
            if p.collision_undo.len() > 100 {
                p.collision_undo.remove(0);
            }
        }
        p.collision_undo_open = down;
    } else if !down {
        p.collision_undo_open = false;
    }
}

fn collision_section_inner(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let shapes = app.panels.editor.collision.clone();
    if shapes.is_empty() && app.panels.editor.collision_boxes.is_empty() {
        return;
    }
    egui::CollapsingHeader::new(egui::RichText::new(format!("Collision ({} shapes)", shapes.len())).strong())
        .id_salt("collision_section")
        .default_open(false)
        .show(ui, |ui| {
            ui.checkbox(&mut app.panels.editor.show_collision, "Show in viewport");
            ui.label(theme::faint_label("red = wall, teal = floor. Select a shape to move it; Save to mod writes the collision into the mod."));
            egui::ScrollArea::vertical().max_height(190.0).id_salt("collision_list").show(ui, |ui| {
                for (i, s) in shapes.iter().enumerate() {
                    let (min, max) = s.bounds();
                    let label = format!(
                        "{:02}  {}  \u{b7}  {} tris  \u{b7}  x {:.1}..{:.1}",
                        i,
                        if s.name.is_empty() { "(unnamed)" } else { s.name.as_str() },
                        s.triangles.len(),
                        min[0],
                        max[0]
                    );
                    let label = if app.panels.editor.collision_dropped.get(i).copied().unwrap_or(false) {
                        format!("{label}  (deleted)")
                    } else {
                        label
                    };
                    let on = app.panels.editor.collision_sel == Some(i);
                    if ui.selectable_label(on, label).clicked() {
                        app.panels.editor.collision_sel = if on { None } else { Some(i) };
                    }
                }
            });
            ui.horizontal(|ui| {
                if ui.button("Add box").on_hover_text("Add a new solid box at the camera target (emulator-proven: it blocks the player)").clicked() {
                    let t = app.panels.editor.camera.target;
                    app.panels.editor.collision_boxes.push(([t.x - 1.0, t.y, t.z - 1.0], [t.x + 1.0, t.y + 2.0, t.z + 1.0]));
                    app.panels.editor.dirty = true;
                }
            });
            let mut remove: Option<usize> = None;
            let mut touched = false;
            for (bi, (lo, hi)) in app.panels.editor.collision_boxes.iter_mut().enumerate() {
                ui.label(egui::RichText::new(format!("New box {bi}")).color(egui::Color32::from_rgb(0x9b, 0xe5, 0x6a)));
                ui.horizontal(|ui| {
                    for (axis, name) in ["x", "y", "z"].iter().enumerate() {
                        ui.label(format!("min {name}"));
                        touched |= ui.add(egui::DragValue::new(&mut lo[axis]).speed(0.05)).changed();
                    }
                });
                ui.horizontal(|ui| {
                    for (axis, name) in ["x", "y", "z"].iter().enumerate() {
                        ui.label(format!("max {name}"));
                        touched |= ui.add(egui::DragValue::new(&mut hi[axis]).speed(0.05)).changed();
                    }
                    if ui.button("remove").clicked() {
                        remove = Some(bi);
                    }
                });
            }
            if let Some(bi) = remove {
                app.panels.editor.collision_boxes.remove(bi);
                touched = true;
            }
            if touched {
                app.panels.editor.dirty = true;
            }
            if let Some(si) = app.panels.editor.collision_sel.filter(|i| *i < shapes.len()) {
                ui.add_space(4.0);
                ui.label(egui::RichText::new(format!("Shape {si} offset")).strong());
                let mut d = app.panels.editor.collision_moves.get(si).copied().unwrap_or([0.0; 3]);
                let before = d;
                ui.horizontal(|ui| {
                    for (axis, name) in ["X", "Y", "Z"].iter().enumerate() {
                        ui.label(*name);
                        ui.add(egui::DragValue::new(&mut d[axis]).speed(0.05).suffix(" m"));
                    }
                    if ui.button("reset").clicked() {
                        d = [0.0; 3];
                    }
                });
                let gone = app.panels.editor.collision_dropped.get(si).copied().unwrap_or(false);
                if ui
                    .button(if gone { "Restore shape" } else { "Delete shape" })
                    .on_hover_text("Remove this shape from the level's collision (emulator-proven: the player walks through it)")
                    .clicked()
                {
                    if let Some(slot) = app.panels.editor.collision_dropped.get_mut(si) {
                        *slot = !gone;
                    }
                    app.panels.editor.dirty = true;
                }
                if d != before {
                    if let Some(slot) = app.panels.editor.collision_moves.get_mut(si) {
                        *slot = d;
                    }
                    app.panels.editor.dirty = true;
                }
            }
        });
    ui.add_space(6.0);
}

fn inspector_dock(app: &mut ViewerApp, ui: &mut egui::Ui, scene: &Scene, _root: &Path) {
    ui.label(theme::heading("Inspector"));
    ui.separator();
    collision_section(app, ui);
    if !app.panels.editor.multi.is_empty() {
        let n = app.panels.editor.selection().len();
        egui::CollapsingHeader::new(egui::RichText::new(format!("Selection ({n} nodes)")).strong()).default_open(true).show(ui, |ui| {
            ui.label(theme::faint_label("Shift+click adds or removes nodes. The group moves and deletes as one undo step."));
            let mut off = app.panels.editor.multi_offset;
            ui.horizontal(|ui| {
                for (axis, name) in ["X", "Y", "Z"].iter().enumerate() {
                    ui.label(*name);
                    ui.add(egui::DragValue::new(&mut off[axis]).speed(0.05).suffix(" m"));
                }
            });
            app.panels.editor.multi_offset = off;
            ui.horizontal(|ui| {
                if ui.button("Move all by").clicked() {
                    app.panels.editor.move_selection(off);
                    app.panels.editor.multi_offset = [0.0; 3];
                }
                if ui.button("Delete all").clicked() {
                    app.panels.editor.delete_all_selected();
                }
                if ui.button("Clear selection").clicked() {
                    app.panels.editor.multi.clear();
                }
            });
        });
    }
    let Some(i) = app.panels.editor.selected_object.filter(|i| *i < scene.objects.len()) else {
        ui.add_space(8.0);
        ui.label(theme::faint_label("Select a node in the Scene tree or click a marker in the viewport."));
        ui.add_space(12.0);
        changes_section(app, ui, scene);
        return;
    };
    let obj = app.panels.editor.scene.as_ref().and_then(|s| s.objects.get(i)).cloned().unwrap_or_else(|| scene.objects[i].clone());
    let original = app
        .panels
        .editor
        .original
        .iter()
        .find(|o| o.id == obj.id)
        .cloned()
        .unwrap_or_else(|| obj.clone());
    if obj.deleted {
        ui.horizontal(|ui| {
            ui.label(theme::heading(object_label(i, &obj)));
        });
        ui.label(egui::RichText::new("This node is deleted and will be removed from the level on export.").color(theme::ERR));
        if ui.button("Restore").clicked() {
            let panel = &mut app.panels.editor;
            panel.begin_change();
            if let Some(o) = panel.scene.as_mut().and_then(|s| s.objects.get_mut(i)) {
                o.deleted = false;
            }
        }
        ui.add_space(8.0);
        changes_section(app, ui, scene);
        return;
    }
    ui.horizontal(|ui| {
        ui.label(theme::heading(object_label(i, &obj)));
        ui.label(theme::faint_label(obj.kind.clone()));
    });
    match &obj.new_from {
        Some(src) => ui.label(theme::faint_label(format!("new node  \u{b7}  copy of the record at {src}"))),
        None => ui.label(theme::faint_label(format!("id {}  \u{b7}  record at {}", obj.id, obj.record_offset))),
    };
    ui.add_space(4.0);

    let before = app.panels.editor.scene.as_ref().map(|s| s.objects.clone());
    let mut edited: Option<SceneObject> = None;
    let mut working = obj.clone();
    let mut changed = false;
    egui::CollapsingHeader::new(egui::RichText::new("Transform").strong())
        .default_open(true)
        .show(ui, |ui| {
            changed |= vec3_row(ui, "Position", &mut working.position, original.position, 0.05, 1.0, "");
            changed |= vec3_row(ui, "Rotation", &mut working.rotation, original.rotation, 0.5, 180.0 / std::f32::consts::PI, "\u{b0}");
            if obj.kind != "actor" {
                changed |= vec3_row(ui, "Scale", &mut working.scale, original.scale, 0.05, 1.0, "");
            }
        });
    if !working.props.is_empty() {
        egui::CollapsingHeader::new(egui::RichText::new("Properties").strong())
            .default_open(true)
            .show(ui, |ui| {
                for (k, prop) in working.props.iter_mut().enumerate() {
                    let orig_value = original.props.get(k).map(|p| p.value).unwrap_or(prop.value);
                    ui.horizontal(|ui| {
                        ui.add_sized([86.0, 18.0], egui::Label::new(theme::dim_label(prop.name.clone())));
                        if prop.editable {
                            let mut v = prop.value;
                            let max = prop.max();
                            if ui.add(egui::DragValue::new(&mut v).range(0..=max).speed(0.2)).changed() {
                                prop.value = v;
                                changed = true;
                            }
                            ui.label(theme::faint_label(format!("0x{:X}", prop.value)));
                            if ui
                                .add_enabled(prop.value != orig_value, egui::Button::new("reset").small())
                                .on_hover_text("Back to the value in the retail file")
                                .clicked()
                            {
                                prop.value = orig_value;
                                changed = true;
                            }
                        } else {
                            ui.label(theme::mono(format!("0x{:X}", prop.value)));
                            ui.label(theme::faint_label("read-only"));
                        }
                    })
                    .response
                    .on_hover_text(prop.hint.clone());
                }
            });
    }
    if obj.kind == "actor" {
        let mut open_model: Option<String> = None;
        egui::CollapsingHeader::new(egui::RichText::new("Entity").strong()).default_open(true).show(ui, |ui| {
            match monster_of(&working) {
                Some(m) => {
                    ui.horizontal(|ui| {
                        ui.label(egui::RichText::new(if m.name.is_empty() { "(unnamed)" } else { m.name.as_str() }).color(theme::TEXT).strong());
                        ui.label(theme::faint_label(format!("model {}", m.model)));
                    });
                    if !m.jp.is_empty() {
                        ui.label(theme::faint_label(m.jp.clone()));
                    }
                    if ui.button("Show model").on_hover_text("Open this actor's model in the Models panel").clicked() {
                        open_model = Some(format!("{}_h", m.model));
                    }
                }
                None => {
                    ui.label(theme::faint_label(
                        "No model for this id in the level's region table.",
                    ));
                }
            }
            // searchable monster picker: sets entity class 0x300 and the row id
            let filter_id = ui.make_persistent_id("entity_pick_filter");
            let mut filter: String = ui.data_mut(|d| d.get_temp(filter_id).unwrap_or_default());
            egui::ComboBox::from_id_salt("entity_picker")
                .selected_text("Change character\u{2026}")
                .width(220.0)
                .show_ui(ui, |ui| {
                    ui.add(egui::TextEdit::singleline(&mut filter).hint_text("search name or model\u{2026}"));
                    let needle = filter.to_lowercase();
                    let region = CUR_REGION.load(std::sync::atomic::Ordering::Relaxed);
                    let list = NPC_TABLES.get().and_then(|t| t.get(&region)).map(|v| v.as_slice()).unwrap_or(&[]);
                    let hits: Vec<usize> = list
                        .iter()
                        .enumerate()
                        .filter(|(_, e)| {
                            !e.model.is_empty()
                                && (needle.is_empty()
                                || e.name.to_lowercase().contains(&needle)
                                || e.model.to_lowercase().contains(&needle)
                                || e.jp.contains(&needle))
                        })
                        .map(|(i, _)| i)
                        .collect();
                    egui::ScrollArea::vertical().max_height(280.0).show_rows(ui, 18.0, hits.len(), |ui, range| {
                        for r in range {
                            let id = hits[r];
                            let e = &list[id];
                            let label = format!("{}  ({})  #{id}", if e.name.is_empty() { "(unnamed)" } else { e.name.as_str() }, e.model);
                            if ui.selectable_label(false, label).clicked() {
                                for prop in working.props.iter_mut() {
                                    match prop.name.as_str() {
                                        "entity id" => prop.value = id as i64,
                                        _ => {}
                                    }
                                }
                                changed = true;
                                ui.close();
                            }
                        }
                    });
                });
            ui.data_mut(|d| d.insert_temp(filter_id, filter));
            // drop zone: drag a character model from the Project dock to give this actor that model
            let note_id = ui.make_persistent_id("entity_drop_note");
            let (_, dropped) = ui.dnd_drop_zone::<String, _>(egui::Frame::group(ui.style()), |ui| {
                ui.set_min_width(ui.available_width() - 12.0);
                ui.label(theme::faint_label("Drop a character model from the Project dock here"));
            });
            if let Some(name) = dropped {
                let region = CUR_REGION.load(std::sync::atomic::Ordering::Relaxed);
                let list = NPC_TABLES.get().and_then(|t| t.get(&region)).map(|v| v.as_slice()).unwrap_or(&[]);
                let want = name.to_lowercase();
                let want = want.trim_end_matches(".bch").trim_end_matches("_h").trim_end_matches("_l");
                let note = match list.iter().position(|e| !e.model.is_empty() && e.model.to_lowercase() == want) {
                    Some(id) => {
                        for prop in working.props.iter_mut() {
                            if prop.name == "entity id" {
                                prop.value = id as i64;
                            }
                        }
                        changed = true;
                        format!("{name} is NPC row #{id} of this region")
                    }
                    None => format!("No NPC row of this region uses {name}"),
                };
                ui.data_mut(|d| d.insert_temp(note_id, note));
            }
            if let Some(note) = ui.data(|d| d.get_temp::<String>(note_id)) {
                ui.label(theme::faint_label(note));
            }
        });
        if let Some(name) = open_model {
            app.open_model(&name);
        }
        if let Some(class) = working.props.iter().find(|p| p.name == "entity class").map(|p| p.value) {
            let shown = match (class >> 8) & 0xFF {
                1 => "only in the normal 3D view",
                2 => "only in the 2D mode (it will NOT appear in 3D)",
                3 => "in both the 3D view and the 2D mode",
                _ => "never (mask 0: the game skips this record)",
            };
            ui.label(theme::faint_label(format!("Created {shown}: the high byte of the entity class is a display-mode mask (docs/CUSTOM_ROOM.md).")));
        }
        if let Some(key) = working.props.iter().find(|p| p.name == "key 60").map(|p| p.value) {
            ui.label(theme::faint_label(format!(
                "Level group {}: the area script switches groups on and off (SetLevelGroupEnable); a record of a disabled group is not shown even in the right view.",
                (key >> 24) & 0xFF
            )));
        }
        dialogue_section(app, ui, &working, &scene.id);
    }
    if obj.kind == "gimmick" {
        egui::CollapsingHeader::new(egui::RichText::new("Contents").strong()).default_open(true).show(ui, |ui| {
            ui.label(egui::RichText::new(gimmick_contents(&working).unwrap_or_else(|| "unknown row".into())).color(theme::TEXT).strong());
            ui.label(theme::faint_label("The drop row selects a row of fieldcmn/fixed_drop_param (item + count). Emulator-proven: changing the row changes the item the game reports (docs/GIMMICK_DECOMP.md). Edit the table rows in Data > Tables."));
        });
    }
    if obj.kind == "exit" {
        let mut open_level: Option<String> = None;
        egui::CollapsingHeader::new(egui::RichText::new("Destination").strong()).default_open(true).show(ui, |ui| {
            match exit_dest(&working) {
                Some(name) => {
                    ui.label(egui::RichText::new(name).color(theme::TEXT).strong());
                    if ui.button("Open level").on_hover_text("Open the level this exit leads to").clicked() {
                        open_level = Some(name.to_string());
                    }
                }
                None => {
                    ui.label(theme::faint_label("This map id has no level in syscmn/level_map."));
                }
            }
            ui.label(theme::faint_label("Entry of the level's map-jump table (+0x68). The scripts' TrgMapJumpEvent(map, locator, ...) takes the destination from it."));
            let filter_id = ui.make_persistent_id("dest_pick_filter");
            let mut filter: String = ui.data_mut(|d| d.get_temp(filter_id).unwrap_or_default());
            egui::ComboBox::from_id_salt("dest_picker")
                .selected_text("Change destination\u{2026}")
                .width(220.0)
                .show_ui(ui, |ui| {
                    ui.add(egui::TextEdit::singleline(&mut filter).hint_text("level name\u{2026}"));
                    let needle = filter.to_lowercase();
                    let list = MAPS.get().map(|v| v.as_slice()).unwrap_or(&[]);
                    let hits: Vec<usize> = list
                        .iter()
                        .enumerate()
                        .filter(|(_, n)| !n.is_empty() && (needle.is_empty() || n.to_lowercase().contains(&needle)))
                        .map(|(i, _)| i)
                        .collect();
                    egui::ScrollArea::vertical().max_height(280.0).show_rows(ui, 18.0, hits.len(), |ui, range| {
                        for r in range {
                            let id = hits[r];
                            if ui.selectable_label(false, format!("{}  (map {id})", list[id])).clicked() {
                                for prop in working.props.iter_mut().filter(|p| p.name == "destination map") {
                                    prop.value = id as i64;
                                }
                                changed = true;
                                ui.close();
                            }
                        }
                    });
                });
            ui.data_mut(|d| d.insert_temp(filter_id, filter));
        });
        if let Some(name) = open_level {
            app.panels.editor.request(&name);
        }
    }
    if obj.kind == "trigger" {
        egui::CollapsingHeader::new(egui::RichText::new("Trigger").strong()).default_open(true).show(ui, |ui| {
            ui.label(theme::faint_label("An event volume: the id selects entries in the level's trigger table (+0x68) and scripts. It is not a map id; where a door leads is decided by script (docs/LEVEL_FORMAT.md, Warps)."));
        });
    }
    if changed {
        edited = Some(working);
    }
    if let (Some(o), Some(before)) = (edited, before) {
        let panel = &mut app.panels.editor;
        // one undo step per burst of edits to the same node
        if panel.edit_group != Some(i) || panel.undo.is_empty() {
            panel.undo.push(before);
            panel.redo.clear();
        }
        panel.edit_group = Some(i);
        panel.dirty = true;
        if let Some(target) = panel.scene.as_mut().and_then(|s| s.objects.get_mut(i)) {
            *target = o;
        }
    } else if !ui.ctx().input(|inp| inp.pointer.any_down()) {
        app.panels.editor.edit_group = None;
    }

    egui::CollapsingHeader::new(egui::RichText::new("Record").strong()).default_open(true).show(ui, |ui| {
        crate::ui::kv_rows(
            ui,
            &[
                ("kind", obj.kind.clone()),
                ("id", obj.id.clone()),
                ("record offset", obj.record_offset.clone()),
                ("level", scene.id.clone()),
            ],
        );
    });
    egui::CollapsingHeader::new(egui::RichText::new("File fields").strong()).default_open(false).show(ui, |ui| {
        ui.label(theme::faint_label("Bytes in level3d.bxon that Save to mod rewrites for this node."));
        let fo = &obj.field_offsets;
        let join = |v: &[String; 3]| v.iter().filter(|s| !s.is_empty()).cloned().collect::<Vec<_>>().join("  ");
        crate::ui::kv_rows(
            ui,
            &[
                ("position", join(&fo.position)),
                ("position (shadow)", join(&fo.position_shadow)),
                ("scale", join(&fo.scale)),
                ("rotation", join(&fo.rotation)),
            ],
        );
    });
    ui.add_space(6.0);
    changes_section(app, ui, scene);
}

/// Every node that differs from the retail file, with a one-click revert.
fn changes_section(app: &mut ViewerApp, ui: &mut egui::Ui, scene: &Scene) {
    let changed = app.panels.editor.changed_objects();
    egui::CollapsingHeader::new(egui::RichText::new(format!("Changes ({})", changed.len())).strong())
        .default_open(true)
        .show(ui, |ui| {
            if changed.is_empty() {
                ui.label(theme::faint_label("This level matches the retail file."));
                return;
            }
            let mut revert: Option<usize> = None;
            let mut select: Option<usize> = None;
            egui::ScrollArea::vertical().max_height(160.0).id_salt("editor_changes").show(ui, |ui| {
                for &i in &changed {
                    ui.horizontal(|ui| {
                        if ui.add(egui::Button::new(object_label(i, &scene.objects[i])).frame(false)).clicked() {
                            select = Some(i);
                        }
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if ui.small_button("revert").clicked() {
                                revert = Some(i);
                            }
                        });
                    });
                }
            });
            if ui.button("Revert all").clicked() {
                let panel = &mut app.panels.editor;
                panel.begin_change();
                let original = panel.original.clone();
                if let Some(s) = panel.scene.as_mut() {
                    s.objects = original;
                }
            }
            let panel = &mut app.panels.editor;
            if let Some(i) = select {
                panel.selected_object = Some(i);
                panel.tree_scroll = true;
            }
            if let Some(i) = revert {
                panel.begin_change();
                let id = panel.scene.as_ref().and_then(|s| s.objects.get(i)).map(|o| o.id.clone());
                let orig = id.as_ref().and_then(|id| panel.original.iter().find(|o| &o.id == id).cloned());
                if let Some(s) = panel.scene.as_mut() {
                    match orig {
                        Some(orig) => {
                            if let Some(t) = s.objects.get_mut(i) {
                                *t = orig;
                            }
                        }
                        None => {
                            s.objects.remove(i);
                        }
                    }
                }
                panel.selected_object = None;
            }
        });
}

// -- viewport --------------------------------------------------------------------

/// Column-major model matrix: facing about the vertical axis, uniform scale, translation.
fn placement_matrix(position: [f32; 3], facing: f32, scale: f32) -> [f32; 16] {
    let (sn, cs) = facing.sin_cos();
    [
        cs * scale, 0.0, -sn * scale, 0.0,
        0.0, scale, 0.0, 0.0,
        sn * scale, 0.0, cs * scale, 0.0,
        position[0], position[1], position[2], 1.0,
    ]
}

/// The real model of every monster actor, loaded in the background and drawn at its position.
fn actor_instances(app: &mut ViewerApp, ctx: &egui::Context) -> Option<Instances> {
    // finished loads
    {
        let panel = &mut app.panels.editor;
        while let Ok((key, result)) = panel.model_rx.try_recv() {
            panel.models.insert(
                key,
                match result {
                    Ok(mesh) => ModelState::Ready(Arc::new(mesh)),
                    Err(_) => ModelState::Failed,
                },
            );
        }
    }
    if !app.panels.editor.show_models {
        return Some(Instances { uploads: Vec::new(), draws: Vec::new() });
    }
    let scene = app.panels.editor.scene.clone()?;
    let mut wanted: Vec<(String, [f32; 3], f32)> = Vec::new();
    for obj in scene.objects.iter().filter(|o| o.kind == "actor" && !o.deleted) {
        if let Some(m) = monster_of(obj) {
            if !m.model.is_empty() {
                wanted.push((format!("{}_h", m.model), obj.position, obj.rotation[1]));
            }
        }
    }
    // start loads for models not seen yet (a few at a time)
    let loading = app.panels.editor.models.values().filter(|m| matches!(m, ModelState::Loading)).count();
    let mut budget = 4usize.saturating_sub(loading);
    for (key, _, _) in &wanted {
        if budget == 0 {
            break;
        }
        if app.panels.editor.models.contains_key(key) {
            continue;
        }
        if !app.data.as_deref().is_some_and(|d| d.models.ready) {
            // the model index loads in the background; try again next frame
            ctx.request_repaint_after(std::time::Duration::from_millis(200));
            break;
        }
        let path = app.data.as_deref().and_then(|d| d.models.get(key)).map(|m| m.obj.clone());
        match path {
            Some(path) => {
                app.panels.editor.models.insert(key.clone(), ModelState::Loading);
                let tx = app.panels.editor.model_tx.clone();
                let key = key.clone();
                app.pool.submit(move || {
                    let _ = tx.send((key, crate::render::mesh::load_obj(&path)));
                });
                budget -= 1;
            }
            None => {
                app.panels.editor.models.insert(key.clone(), ModelState::Failed);
            }
        }
    }
    if std::env::var("DQXI_DEBUG_MODELS").is_ok() {
        let panel = &app.panels.editor;
        eprintln!("models: wanted={} ready={} index_ready={}", wanted.len(),
            panel.models.values().filter(|m| matches!(m, ModelState::Ready(_))).count(),
            app.data.as_deref().is_some_and(|d| d.models.ready));
        for (k, st) in &panel.models {
            eprintln!("  {k}: {}", match st { ModelState::Loading => "loading", ModelState::Ready(_) => "ready", ModelState::Failed => "failed" });
        }
    }
    let panel = &app.panels.editor;
    let mut uploads: Vec<(String, Arc<Mesh>)> = Vec::new();
    let mut draws: Vec<(String, [f32; 16])> = Vec::new();
    for (key, position, facing) in wanted {
        if let Some(ModelState::Ready(mesh)) = panel.models.get(&key) {
            if !uploads.iter().any(|(k, _)| *k == key) {
                uploads.push((key.clone(), mesh.clone()));
            }
            draws.push((key, placement_matrix(position, facing, 1.0)));
        }
    }
    if panel.models.values().any(|m| matches!(m, ModelState::Loading)) {
        ctx.request_repaint_after(std::time::Duration::from_millis(150));
    }
    Some(Instances { uploads, draws })
}

fn world(obj: &SceneObject) -> Vec3 {
    Vec3::new(obj.position[0], obj.position[1], obj.position[2])
}

fn gizmo_length(camera: &Camera) -> f32 {
    camera.distance * 0.16
}

fn dist_to_segment(p: egui::Pos2, a: egui::Pos2, b: egui::Pos2) -> f32 {
    let ab = b - a;
    let len2 = ab.length_sq();
    if len2 < 1e-6 {
        return p.distance(a);
    }
    let t = (((p - a).dot(ab)) / len2).clamp(0.0, 1.0);
    p.distance(a + ab * t)
}

fn ring_points(center: Vec3, axis: usize, radius: f32) -> Vec<Vec3> {
    let (u, v) = match axis {
        0 => (AXES[1], AXES[2]),
        1 => (AXES[2], AXES[0]),
        _ => (AXES[0], AXES[1]),
    };
    (0..=48)
        .map(|k| {
            let t = k as f32 / 48.0 * std::f32::consts::TAU;
            center.add(u.scale(t.cos() * radius)).add(v.scale(t.sin() * radius))
        })
        .collect()
}

/// Which gizmo handle (if any) is under the pointer: (axis, distance).
fn gizmo_hit(tool: Tool, obj: &SceneObject, camera: &Camera, rect: egui::Rect, pointer: egui::Pos2) -> Option<usize> {
    let mvp = camera.mvp(rect.width() / rect.height());
    let c = world(obj);
    let origin = project(mvp, c, rect)?;
    let len = gizmo_length(camera);
    let mut best: Option<(usize, f32)> = None;
    let mut consider = |axis: usize, d: f32, limit: f32| {
        if d < limit && best.map(|(_, b)| d < b).unwrap_or(true) {
            best = Some((axis, d));
        }
    };
    match tool {
        Tool::Select => {}
        Tool::Move | Tool::Scale => {
            for a in 0..3 {
                if let Some(tip) = project(mvp, c.add(AXES[a].scale(len)), rect) {
                    consider(a, dist_to_segment(pointer, origin, tip), 7.0);
                }
            }
            if tool == Tool::Scale {
                consider(3, pointer.distance(origin), 9.0);
            }
        }
        Tool::Rotate => {
            for a in 0..3 {
                let pts: Vec<Option<egui::Pos2>> = ring_points(c, a, len * 0.9).into_iter().map(|p| project(mvp, p, rect)).collect();
                for w in pts.windows(2) {
                    if let (Some(p), Some(q)) = (w[0], w[1]) {
                        consider(a, dist_to_segment(pointer, p, q), 6.0);
                    }
                }
            }
        }
    }
    best.map(|(a, _)| a)
}

fn draw_gizmo(painter: &egui::Painter, tool: Tool, obj: &SceneObject, camera: &Camera, rect: egui::Rect, hot: Option<usize>) {
    let mvp = camera.mvp(rect.width() / rect.height());
    let c = world(obj);
    let Some(origin) = project(mvp, c, rect) else { return };
    let len = gizmo_length(camera);
    let color = |a: usize| {
        let base = AXIS_COLORS[a];
        if hot == Some(a) { egui::Color32::from_rgb(0xff, 0xe0, 0x6a) } else { base }
    };
    match tool {
        Tool::Select => {}
        Tool::Move | Tool::Scale => {
            for a in 0..3 {
                let Some(tip) = project(mvp, c.add(AXES[a].scale(len)), rect) else { continue };
                painter.line_segment([origin, tip], egui::Stroke::new(if hot == Some(a) { 3.5 } else { 2.5 }, color(a)));
                if tool == Tool::Move {
                    let dir = (tip - origin).normalized();
                    let side = egui::vec2(-dir.y, dir.x);
                    painter.add(egui::Shape::convex_polygon(
                        vec![tip + dir * 9.0, tip - dir * 3.0 + side * 5.0, tip - dir * 3.0 - side * 5.0],
                        color(a),
                        egui::Stroke::NONE,
                    ));
                } else {
                    painter.rect_filled(egui::Rect::from_center_size(tip, egui::vec2(9.0, 9.0)), 1.0, color(a));
                }
            }
            if tool == Tool::Scale {
                let c3 = if hot == Some(3) { egui::Color32::from_rgb(0xff, 0xe0, 0x6a) } else { egui::Color32::WHITE };
                painter.rect_filled(egui::Rect::from_center_size(origin, egui::vec2(11.0, 11.0)), 1.0, c3);
            }
        }
        Tool::Rotate => {
            for a in 0..3 {
                let pts: Vec<egui::Pos2> = ring_points(c, a, len * 0.9).into_iter().filter_map(|p| project(mvp, p, rect)).collect();
                painter.add(egui::Shape::line(pts, egui::Stroke::new(if hot == Some(a) { 3.0 } else { 2.0 }, color(a))));
            }
        }
    }
    painter.circle_filled(origin, 3.0, egui::Color32::WHITE);
}

fn editor_viewport(app: &mut ViewerApp, ui: &mut egui::Ui, scene: &Scene) {
    let mut camera = app.panels.editor.camera;
    let opts = RenderOptions {
        wireframe: app.panels.editor.wireframe,
        show_grid: app.panels.editor.show_grid,
        show_axes: app.panels.editor.show_axes,
        flat: app.panels.editor.flat,
        ..Default::default()
    };
    let mesh = app.panels.editor.mesh.as_ref().map(|m| (app.panels.editor.mesh_id, m.clone()));
    let instances = actor_instances(app, ui.ctx());
    let response = paint_mesh_viewport_scene(ui, app.renderer.clone(), &camera, opts, mesh, None, instances);
    let rect = response.rect;
    let pointer = response.interact_pointer_pos();
    let hover = response.hover_pos();
    let tool = app.panels.editor.tool;
    let selected = app.panels.editor.selected_object.filter(|i| *i < scene.objects.len());
    let live_selected = selected.and_then(|i| app.panels.editor.scene.as_ref().and_then(|s| s.objects.get(i)).cloned());

    // -- drag handling: gizmo handle first, otherwise orbit
    if response.drag_started_by(egui::PointerButton::Primary) {
        let handle = match (&live_selected, pointer) {
            (Some(obj), Some(p)) if rect.width() > 1.0 => gizmo_hit(tool, obj, &camera, rect, p),
            _ => None,
        };
        if let (Some(axis), Some(i), Some(obj), Some(p)) = (handle, selected, &live_selected, pointer) {
            let start = match tool {
                Tool::Move => obj.position,
                Tool::Rotate => obj.rotation,
                _ => obj.scale,
            };
            app.panels.editor.begin_change();
            app.panels.editor.gizmo = Some(GizmoDrag { object: i, tool, axis, start, pointer: p });
        } else {
            app.panels.editor.gizmo = None;
            if tool == Tool::Select || ui.input(|i| i.modifiers.shift) {
                app.panels.editor.marquee = pointer;
            }
        }
    }
    if response.dragged_by(egui::PointerButton::Primary) {
        if app.panels.editor.marquee.is_some() {
            // box select: no orbit while the rectangle is being dragged
        } else if let (Some(g), Some(ptr)) = (app.panels.editor.gizmo, pointer) {
            let mvp = camera.mvp(rect.width() / rect.height());
            let snap = app.panels.editor.snap;
            let step = app.panels.editor.snap_step.max(0.001);
            let obj_pos = app
                .panels
                .editor
                .scene
                .as_ref()
                .and_then(|s| s.objects.get(g.object))
                .map(world)
                .unwrap_or_else(Vec3::zero);
            let len = gizmo_length(&camera);
            let delta = ptr - g.pointer;
            let mut value = g.start;
            let rounded = |v: f32, s: f32| if snap { (v / s).round() * s } else { v };
            match g.tool {
                Tool::Move | Tool::Scale if g.axis < 3 => {
                    if let (Some(o), Some(t)) = (project(mvp, obj_pos, rect), project(mvp, obj_pos.add(AXES[g.axis].scale(len)), rect)) {
                        let screen = t - o;
                        let px = screen.length().max(1.0);
                        let along = delta.dot(screen / px) / px * len;
                        value[g.axis] = rounded(g.start[g.axis] + along, step);
                    }
                }
                Tool::Scale => {
                    let factor = (1.0 + (delta.x - delta.y) * 0.005).max(0.01);
                    for k in 0..3 {
                        value[k] = g.start[k] * factor;
                    }
                }
                Tool::Rotate => {
                    let turn = delta.x * 0.012;
                    let snapped = if snap { (turn / 0.261_799_4).round() * 0.261_799_4 } else { turn };
                    value[g.axis] = g.start[g.axis] + snapped;
                }
                _ => {}
            }
            if g.tool == Tool::Move {
                // the whole Shift+click / box selection follows the dragged node
                let extra = app.panels.editor.multi.clone();
                if let Some(scene) = app.panels.editor.scene.as_mut() {
                    if let Some(old) = scene.objects.get(g.object).map(|o| o.position) {
                        for i in extra {
                            if i != g.object {
                                if let Some(o) = scene.objects.get_mut(i) {
                                    for a in 0..3 {
                                        o.position[a] += value[a] - old[a];
                                    }
                                }
                            }
                        }
                    }
                }
            }
            if let Some(obj) = app.panels.editor.scene.as_mut().and_then(|s| s.objects.get_mut(g.object)) {
                match g.tool {
                    Tool::Move => obj.position = value,
                    Tool::Rotate => obj.rotation = value,
                    _ => obj.scale = value,
                }
            }
        } else {
            let d = response.drag_delta();
            if d != egui::Vec2::ZERO {
                camera.orbit(d.x, d.y);
            }
        }
    }
    if response.drag_stopped_by(egui::PointerButton::Primary) {
        app.panels.editor.gizmo = None;
        if let (Some(start), Some(end)) = (app.panels.editor.marquee.take(), pointer.or(hover)) {
            if rect.width() > 1.0 {
                let sel_rect = egui::Rect::from_two_pos(start, end);
                let mvp = camera.mvp(rect.width() / rect.height());
                let hits: Vec<usize> = app
                    .panels
                    .editor
                    .scene
                    .as_ref()
                    .map(|s| {
                        s.objects
                            .iter()
                            .enumerate()
                            .filter(|(_, o)| !o.deleted && o.kind != "exit" && project(mvp, world(o), rect).map(|p| sel_rect.contains(p)).unwrap_or(false))
                            .map(|(i, _)| i)
                            .collect()
                    })
                    .unwrap_or_default();
                let p = &mut app.panels.editor;
                p.multi.clear();
                if let Some((first, rest)) = hits.split_first() {
                    p.selected_object = Some(*first);
                    p.multi = rest.to_vec();
                    p.status = format!("Box selected {} node(s)", hits.len());
                }
            }
        }
    }
    if response.dragged_by(egui::PointerButton::Secondary) || response.dragged_by(egui::PointerButton::Middle) {
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

    // -- overlay: markers, bounds, gizmo
    let live_scene = app.panels.editor.scene.clone().unwrap_or_else(|| scene.clone());
    let hot = match (&live_selected, hover) {
        (Some(obj), Some(p)) if app.panels.editor.gizmo.is_none() && rect.width() > 1.0 => gizmo_hit(tool, obj, &camera, rect, p),
        _ => app.panels.editor.gizmo.map(|g| g.axis),
    };
    if rect.width() > 1.0 && rect.height() > 1.0 {
        let mvp = camera.mvp(rect.width() / rect.height());
        let painter = ui.painter_at(rect);
        let mut picked: Option<(usize, f32)> = None;
        if app.panels.editor.show_objects {
            for (i, obj) in live_scene.objects.iter().enumerate() {
                if obj.deleted || obj.kind == "exit" {
                    continue;
                }
                let Some(pos) = project(mvp, world(obj), rect) else { continue };
                let is_sel = selected == Some(i) || app.panels.editor.multi.contains(&i);
                let base = kind_color(&obj.kind);
                let color = if is_sel { theme::ACCENT } else { base };
                let r = if is_sel { 5.5 } else { 3.2 };
                painter.circle_filled(pos, r, color);
                painter.circle_stroke(pos, r + 1.0, egui::Stroke::new(1.0, egui::Color32::from_black_alpha(180)));
                if obj.kind == "actor" {
                    // facing: the game's rotation about the vertical axis, 0 = +Z
                    let ry = obj.rotation[1];
                    let tip = Vec3::new(obj.position[0] + ry.sin() * 1.0, obj.position[1], obj.position[2] + ry.cos() * 1.0);
                    if let Some(t) = project(mvp, tip, rect) {
                        painter.line_segment([pos, t], egui::Stroke::new(if is_sel { 2.5 } else { 1.5 }, color));
                    }
                }
                if app.panels.editor.show_bounds && obj.kind == "placement" && (is_sel || live_scene.objects.len() < 400) {
                    draw_bounds_box(&painter, mvp, obj, rect, color);
                }
                if app.panels.editor.show_labels || is_sel {
                    painter.text(
                        pos + egui::vec2(8.0, -8.0),
                        egui::Align2::LEFT_BOTTOM,
                        object_label(i, obj),
                        egui::FontId::proportional(11.0),
                        if is_sel { theme::TEXT } else { theme::TEXT_DIM },
                    );
                }
                if let Some(p) = hover {
                    let d = p.distance(pos);
                    if d < 10.0 && picked.map(|(_, best)| d < best).unwrap_or(true) {
                        picked = Some((i, d));
                    }
                }
            }
        }
        if app.panels.editor.show_collision {
            let sel = app.panels.editor.collision_sel;
            let mut budget = 30000usize;
            for (si, shape) in app.panels.editor.collision.iter().enumerate() {
                if app.panels.editor.collision_dropped.get(si).copied().unwrap_or(false) {
                    continue;
                }
                let picked = sel == Some(si);
                let color = if picked {
                    theme::ACCENT
                } else if shape.attribute == 0 {
                    egui::Color32::from_rgba_unmultiplied(0xf0, 0x5a, 0x4b, 150)
                } else {
                    egui::Color32::from_rgba_unmultiplied(0x4d, 0xd0, 0xb8, 90)
                };
                let stroke = egui::Stroke::new(if picked { 2.0 } else { 1.0 }, color);
                let moved = app.panels.editor.collision_moves.get(si).copied().unwrap_or([0.0; 3]);
                for tri in &shape.triangles {
                    if budget == 0 {
                        break;
                    }
                    budget -= 1;
                    let pts: Vec<Option<egui::Pos2>> = tri
                        .iter()
                        .map(|k| {
                            let v = shape.vertices[*k as usize];
                            project(mvp, Vec3::new(v[0] + moved[0], v[1] + moved[1], v[2] + moved[2]), rect)
                        })
                        .collect();
                    for (a, b) in [(0usize, 1usize), (1, 2), (2, 0)] {
                        if let (Some(p), Some(q)) = (pts[a], pts[b]) {
                            painter.line_segment([p, q], stroke);
                        }
                    }
                }
            }
        }
        if app.panels.editor.show_collision {
            let stroke = egui::Stroke::new(1.5, egui::Color32::from_rgb(0x9b, 0xe5, 0x6a));
            for (lo, hi) in &app.panels.editor.collision_boxes {
                let corner = |i: usize| {
                    let x = if i & 1 == 0 { lo[0] } else { hi[0] };
                    let y = if i & 2 == 0 { lo[1] } else { hi[1] };
                    let z = if i & 4 == 0 { lo[2] } else { hi[2] };
                    project(mvp, Vec3::new(x, y, z), rect)
                };
                for a in 0..8usize {
                    for bit in [1usize, 2, 4] {
                        let b = a ^ bit;
                        if a < b {
                            if let (Some(p), Some(q)) = (corner(a), corner(b)) {
                                painter.line_segment([p, q], stroke);
                            }
                        }
                    }
                }
            }
        }
        if let Some(obj) = live_scene.objects.get(selected.unwrap_or(usize::MAX)).filter(|o| !o.deleted && o.kind != "exit") {
            draw_gizmo(&painter, tool, obj, &camera, rect, hot);
        }
        // clicking an empty spot keeps the selection; clicking a marker selects it
        if response.clicked() && hot.is_none() {
            if let Some((i, _)) = picked {
                if ui.input(|inp| inp.modifiers.shift) && app.panels.editor.selected_object.is_some() {
                    let p = &mut app.panels.editor;
                    if let Some(at) = p.multi.iter().position(|m| *m == i) {
                        p.multi.remove(at);
                    } else if p.selected_object != Some(i) {
                        p.multi.push(i);
                    }
                } else {
                    app.panels.editor.selected_object = Some(i);
                    app.panels.editor.multi.clear();
                    app.panels.editor.tree_scroll = true;
                }
            }
        }
        if let (Some(start), Some(now)) = (app.panels.editor.marquee, hover.or(pointer)) {
            let r = egui::Rect::from_two_pos(start, now);
            painter.rect_filled(r, 0.0, theme::ACCENT.gamma_multiply(0.15));
            painter.rect_stroke(r, 0.0, egui::Stroke::new(1.0, theme::ACCENT), egui::StrokeKind::Inside);
        }
        // viewport HUD
        let hud = format!(
            "{}  \u{b7}  {}  \u{b7}  {}",
            tool.label(),
            if app.panels.editor.snap { format!("snap {}", app.panels.editor.snap_step) } else { "free".into() },
            app.panels.editor.status
        );
        painter.text(
            rect.left_bottom() + egui::vec2(10.0, -8.0),
            egui::Align2::LEFT_BOTTOM,
            hud,
            egui::FontId::proportional(11.0),
            theme::TEXT_FAINT,
        );
        painter.text(
            rect.right_bottom() + egui::vec2(-10.0, -8.0),
            egui::Align2::RIGHT_BOTTOM,
            if tool == Tool::Select {
                "drag: box select \u{b7} Shift+click: add \u{b7} right-drag: pan \u{b7} wheel: zoom \u{b7} F: focus"
            } else {
                "drag: orbit \u{b7} Shift+drag: box select \u{b7} right-drag: pan \u{b7} wheel: zoom \u{b7} F: focus"
            },
            egui::FontId::proportional(11.0),
            theme::TEXT_FAINT,
        );
        if let Some(g) = app.panels.editor.gizmo {
            ui.ctx().set_cursor_icon(egui::CursorIcon::Grabbing);
            let _ = g;
        } else if hot.is_some() {
            ui.ctx().set_cursor_icon(egui::CursorIcon::Grab);
        }
    }
    if app.panels.editor.loading || app.panels.editor.gizmo.is_some() {
        ui.ctx().request_repaint_after(std::time::Duration::from_millis(50));
    }
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

#[cfg(test)]
mod record_tests {
    use super::*;

    fn object(id: &str, offset: &str) -> SceneObject {
        SceneObject {
            id: id.into(),
            kind: "transform".into(),
            position: [1.0, 2.0, 3.0],
            scale: [1.0, 1.0, 1.0],
            rotation: [0.0; 3],
            record_offset: offset.into(),
            field_offsets: Default::default(),
            shape: 120,
            deleted: false,
            new_from: None,
            props: Vec::new(),
        }
    }

    #[test]
    fn duplicates_and_deletes_become_ops_and_moves_stay_float_edits() {
        let original = vec![object("a", "0x928"), object("b", "0x9A0")];
        let mut objects = original.clone();
        objects[0].field_offsets.position = ["0x928".into(), "0x92C".into(), "0x930".into()];
        objects[0].position[0] = 9.0; // moved
        let mut copy = objects[0].clone();
        copy.id = "new_1".into();
        copy.new_from = Some("0x928".into());
        objects.push(copy);
        objects[1].deleted = true;
        let ops = ops_between(&objects, &original);
        assert_eq!(ops.len(), 2);
        assert_eq!(ops[0]["op"], "duplicate");
        assert_eq!(ops[0]["offset"], "0x928");
        assert_eq!(ops[0]["set"]["position"][0], 9.0);
        assert_eq!(ops[1]["op"], "delete");
        assert_eq!(ops[1]["offset"], "0x9A0");
        // only the retail record that is still there and moved yields float edits
        let edits = edits_between(&objects, &original);
        assert_eq!(edits, vec![("0x928".to_string(), 9.0)]);
        // all three differences show up as changed nodes
        assert_eq!(changed_between(&objects, &original), vec![0, 1, 2]);
    }

    #[test]
    fn edited_properties_become_typed_edits_and_duplicates_carry_them() {
        let prop = |value| Prop {
            name: "entity id".into(),
            offset: "0xF5C".into(),
            ty: "u16".into(),
            value,
            editable: true,
            hint: String::new(),
        };
        let mut a = object("a", "0xF00");
        a.kind = "actor".into();
        a.shape = 100;
        a.props = vec![prop(58)];
        let original = vec![a.clone()];
        let mut objects = original.clone();
        objects[0].props[0].value = 108; // swap the NPC for a spider
        assert_eq!(prop_edits_between(&objects, &original), vec![("0xF5C".to_string(), "u16".to_string(), 108)]);
        assert_eq!(changed_between(&objects, &original), vec![0]);
        let mut copy = objects[0].clone();
        copy.id = "new_1".into();
        copy.new_from = Some("0xF00".into());
        objects.push(copy);
        let ops = ops_between(&objects, &original);
        assert_eq!(ops[0]["set"]["props"]["entity id"], 108);
        assert_eq!(ops[0]["shape"], 100);
    }
}
