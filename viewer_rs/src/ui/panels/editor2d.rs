//! Level Editor 2D view: the level as it looks in the game's 2D mode (the 16-bit style view chosen at the priest).
//!
//! Data comes from `python tools/map2d.py export`:
//! * `game_assets/textures/2d_maps/<background>_<time>.png`: the rendered tile map (CHIP container + tile sheets),
//! * `game_assets/maps/<level>/scene2d.json`: the `level2d.bxon` objects, positions in 8 px units,
//! * `game_assets/textures/2d_sprites/<sprite>.png (tools/export_bch_assets.py)` + `game_assets/maps/sprites2d.json`: each region character's
//!   sprite sheet (npc_list word 10 -> res_model2d, word 12 = variant).
//!
//! Editing: drag an object (whole 8 px cells), Delete, Ctrl+D duplicate, field values in the Inspector, undo/redo.
//! The changes go into the `level2d` section of `editor_projects/<level>.json`; Save to mod applies them with
//! `tools/map2d.py apply_level2d` (u16 field writes + the append-only record tool) and stages
//! `mod/romfs/level2d/<level>.pack`. Move, duplicate and delete are emulator-proven (tools/emu/map2d_probe.py).

use std::collections::HashMap;
use std::path::Path;

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::ui::panels::editor2d_map::{paint_chip, paint_tile, CollGrid, TileMap, BLOCKED, EMPTY};

/// The eight ways a square tile can be placed (chip orientation 0..7).
const ORIENTATIONS: [&str; 8] = ["as drawn", "turned left", "upside down", "turned right", "mirrored", "flipped", "transposed", "anti-transposed"];

/// What the pointer does in the 2D view.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Tool2D {
    /// select and move actors, gimmicks, triggers, points
    Objects,
    /// paint, pick, select and move map tiles
    Tiles,
    /// paint the walk grid (blocked / walkable cells)
    Collision,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
enum TileTool {
    Paint,
    Erase,
    Pick,
    Select,
}

/// One undo step.
#[derive(Clone)]
enum Step {
    Objects(Vec<Obj2D>),
    /// (index in the map's ids, old chip, new chip)
    Tiles(Vec<(usize, u16, u16)>),
    /// (grid, cell, old flags, new flags)
    Cells(Vec<(usize, usize, u8, u8)>),
}

#[derive(Clone, Debug, Default)]
pub struct Obj2D {
    pub kind: String,
    pub x: f32,
    pub y: f32,
    pub w: f32,
    pub h: f32,
    pub entity_id: Option<i64>,
    pub facing: Option<i64>,
    pub destination_map: Option<i64>,
    pub locator: Option<i64>,
    pub group: i64,
    pub array: String,
    pub index: i64,
    pub record_offset: String,
    pub has_position: bool,
    /// editable u16 fields: (name, offset inside the record)
    pub fields: Vec<(String, u32)>,
    /// gimmicks (chest, pot, door, bookshelf, sparkly spot ...): what it is
    pub label: String,
    /// gimmick sprite sheet (2d_sprites), when it has one
    pub sprite: Option<String>,
    /// row of fieldcmn/fixed_drop_param (what a chest / pot / drawer holds; 65535 = nothing)
    pub drop_row: Option<i64>,
    /// sparkly spots: row of fieldcmn/glitter_drop_param and the item of that row (None = random materials)
    pub glitter_row: Option<i64>,
    pub glitter_item: Option<i64>,
    /// removed in the editor (retail records only; new ones are simply dropped)
    pub deleted: bool,
    /// a new record: the retail record it is a copy of
    pub new_from: Option<String>,
}

impl Obj2D {
    pub fn get(&self, name: &str) -> i64 {
        match name {
            "x" => self.x as i64,
            "y" => self.y as i64,
            "w" => self.w as i64,
            "h" => self.h as i64,
            "entity_id" => self.entity_id.unwrap_or(0),
            "drop_row" => self.drop_row.unwrap_or(0xFFFF),
            _ => 0,
        }
    }

    pub fn set(&mut self, name: &str, value: i64) {
        let value = value.clamp(0, 0xFFFF);
        match name {
            "x" => self.x = value as f32,
            "y" => self.y = value as f32,
            "w" => self.w = value.max(1) as f32,
            "h" => self.h = value.max(1) as f32,
            "entity_id" => self.entity_id = Some(value),
            "drop_row" => self.drop_row = Some(value),
            _ => {}
        }
    }

    fn to_json(&self) -> serde_json::Value {
        serde_json::json!({
            "kind": self.kind, "x": self.x as i64, "y": self.y as i64, "w": self.w as i64, "h": self.h as i64,
            "entity_id": self.entity_id, "facing": self.facing, "destination_map": self.destination_map, "locator": self.locator,
            "group": self.group, "array": self.array, "index": self.index, "record_offset": self.record_offset,
            "fields": self.fields.iter().map(|(n, o)| (n.clone(), *o)).collect::<std::collections::BTreeMap<_, _>>(),
            "deleted": self.deleted, "new_from": self.new_from,
            "label": self.label, "sprite": self.sprite, "drop_row": self.drop_row,
            "glitter_row": self.glitter_row, "glitter_item": self.glitter_item,
        })
    }
}

#[derive(Default)]
struct Doc2D {
    level: String,
    background: Option<String>,
    times: Vec<String>,
    width: f32,
    height: f32,
    objects: Vec<Obj2D>,
}

pub struct View2D {
    /// show the 2D view instead of the 3D viewport
    pub on: bool,
    pub time: String,
    doc: Option<Doc2D>,
    loaded_for: String,
    map_tex: Option<egui::TextureHandle>,
    map_key: String,
    sprites: HashMap<String, Option<egui::TextureHandle>>,
    sprite_table: Option<HashMap<i32, Vec<String>>>,
    zoom: f32,
    pan: egui::Vec2,
    fit: bool,
    pub selected: Option<usize>,
    pub show_actors: bool,
    pub show_triggers: bool,
    pub show_points: bool,
    pub show_labels: bool,
    /// level group (container) filter: None = all
    pub group: Option<i64>,
    /// retail objects as exported (what the edits are measured against)
    original: Vec<Obj2D>,
    undo: Vec<Step>,
    redo: Vec<Step>,
    pub tool: Tool2D,
    pub show_gimmicks: bool,
    pub show_collision: bool,
    /// the editable tile map (None: not exported yet, the rendered PNG is shown instead)
    tiles: Option<TileMap>,
    grids: Vec<CollGrid>,
    /// active tile layer
    layer: usize,
    tile_tool: TileTool,
    /// brush: width in cells, the chips row by row, and whether they are ground (16 px) chips
    stamp: (usize, Vec<u16>),
    stamp_base: bool,
    /// selected cells of the active layer: x, y, w, h
    sel: Option<[usize; 4]>,
    sel_anchor: Option<(usize, usize)>,
    /// moving the selection: where inside it the pointer grabbed
    moving: Option<(usize, usize)>,
    hover_cell: Option<(usize, usize)>,
    /// pointer (map pixels) of the previous frame while painting: strokes are filled in between
    last_paint: Option<egui::Vec2>,
    stroke_tiles: Vec<(usize, u16, u16)>,
    stroke_cells: Vec<(usize, usize, u8, u8)>,
    show_grid: bool,
    palette_open: bool,
    palette: Option<(String, bool, Vec<u16>)>,
    /// palette shows every tile of the sheet (new tiles for the map) instead of the tiles the map uses
    palette_sheet: bool,
    /// orientation (0..7) of tiles picked from the whole sheet
    palette_orientation: u8,
    /// collision grid to paint into (None = the first grid under the pointer)
    coll_grid: Option<usize>,
    coll_value: u8,
    /// object being dragged: (index, its cell when the drag started, snapshot for undo)
    drag: Option<(usize, egui::Pos2, Vec<Obj2D>)>,
    /// set when something changed this frame (the editor marks the level dirty)
    edited: bool,
    /// screen rects of the drawn objects (last frame), to start a drag on the selected one
    last_hits: Vec<(usize, egui::Rect)>,
    drag_accum: egui::Vec2,
    /// other objects that move with the selection (the copies of a character in other level groups)
    pub follow: Vec<usize>,
}

impl Default for View2D {
    fn default() -> Self {
        Self {
            // DQXI_EDITOR_2D=1 opens levels in the 2D view (like DQXI_EDITOR_MAP / _SELECT for scripted checks)
            on: std::env::var("DQXI_EDITOR_2D").is_ok_and(|v| v == "1"),
            time: "daytime".into(),
            doc: None,
            loaded_for: String::new(),
            map_tex: None,
            map_key: String::new(),
            sprites: HashMap::new(),
            sprite_table: None,
            zoom: 1.0,
            pan: egui::Vec2::ZERO,
            fit: true,
            selected: None,
            show_actors: true,
            show_triggers: true,
            show_points: false,
            show_labels: false,
            group: None,
            original: Vec::new(),
            undo: Vec::new(),
            redo: Vec::new(),
            tool: match std::env::var("DQXI_EDITOR_2D_TOOL").as_deref() {
                Ok("tiles") => Tool2D::Tiles,
                Ok("collision") => Tool2D::Collision,
                _ => Tool2D::Objects,
            },
            show_gimmicks: true,
            show_collision: false,
            tiles: None,
            grids: Vec::new(),
            layer: 0,
            tile_tool: TileTool::Paint,
            stamp: (1, vec![0]),
            stamp_base: true,
            sel: None,
            sel_anchor: None,
            moving: None,
            hover_cell: None,
            last_paint: None,
            stroke_tiles: Vec::new(),
            stroke_cells: Vec::new(),
            show_grid: true,
            palette_open: true,
            palette: None,
            palette_sheet: false,
            palette_orientation: 0,
            coll_grid: None,
            coll_value: BLOCKED,
            drag: None,
            edited: false,
            last_hits: Vec::new(),
            drag_accum: egui::Vec2::ZERO,
            follow: Vec::new(),
        }
    }
}

fn num(v: &serde_json::Value, k: &str) -> Option<i64> {
    v.get(k).and_then(|x| x.as_i64())
}

fn parse_objects(list: &serde_json::Value) -> Vec<Obj2D> {
    list.as_array()
        .map(|a| {
            a.iter()
                .map(|o| {
                    let x = num(o, "x");
                    let y = num(o, "y");
                    Obj2D {
                        kind: o["kind"].as_str().unwrap_or("").to_string(),
                        x: x.unwrap_or(0) as f32,
                        y: y.unwrap_or(0) as f32,
                        w: num(o, "w").unwrap_or(1).max(1) as f32,
                        h: num(o, "h").unwrap_or(1).max(1) as f32,
                        entity_id: num(o, "entity_id"),
                        facing: num(o, "facing"),
                        destination_map: num(o, "destination_map"),
                        locator: num(o, "locator"),
                        group: num(o, "group").unwrap_or(0),
                        array: o["array"].as_str().unwrap_or("").to_string(),
                        index: num(o, "index").unwrap_or(0),
                        record_offset: o["record_offset"].as_str().unwrap_or("").to_string(),
                        has_position: x.is_some() && y.is_some(),
                        fields: o["fields"]
                            .as_object()
                            .map(|f| f.iter().filter_map(|(k, v)| Some((k.clone(), v.as_u64()? as u32))).collect())
                            .unwrap_or_default(),
                        label: o["label"].as_str().unwrap_or("").to_string(),
                        sprite: o["sprite"].as_str().filter(|s| !s.is_empty()).map(str::to_owned),
                        drop_row: num(o, "drop_row"),
                        glitter_row: num(o, "glitter_row"),
                        glitter_item: num(o, "glitter_item"),
                        deleted: o["deleted"].as_bool().unwrap_or(false),
                        new_from: o["new_from"].as_str().map(str::to_owned),
                    }
                })
                .collect()
        })
        .unwrap_or_default()
}

fn load_doc(root: &Path, level: &str) -> Option<(Doc2D, Vec<CollGrid>)> {
    let text = std::fs::read_to_string(root.join("game_assets/maps").join(level).join("scene2d.json")).ok()?;
    let v: serde_json::Value = serde_json::from_str(&text).ok()?;
    let map = &v["map"];
    let objects = parse_objects(&v["objects"]);
    let grids = CollGrid::parse(&v["collision"]);
    Some((Doc2D {
        level: level.to_string(),
        background: v["background"].as_str().map(str::to_owned),
        times: v["times"].as_array().map(|a| a.iter().filter_map(|t| t.as_str().map(str::to_owned)).collect()).unwrap_or_default(),
        width: map["width"].as_f64().unwrap_or(0.0) as f32,
        height: map["height"].as_f64().unwrap_or(0.0) as f32,
        objects,
    }, grids))
}

/// First frame of a gimmick sheet: four frames in a strip (pots, double doors), two side by side (chests, drawers,
/// wardrobes) or a single picture (doors, signs, books).
fn gimmick_frame(size: [usize; 2]) -> (egui::Rect, egui::Vec2) {
    let (w, h) = (size[0] as f32, size[1] as f32);
    let fw = if w >= 4.0 * h {
        w / 4.0
    } else if (w == h && w >= 32.0) || w == 2.0 * h {
        w / 2.0
    } else {
        w
    };
    (egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(fw / w, 1.0)), egui::vec2(fw, h))
}

/// What a gimmick holds, as text ("" when it holds nothing by itself).
fn gimmick_text(o: &Obj2D) -> String {
    if let Some(row) = o.drop_row {
        return crate::ui::panels::editor::drop_contents(row).unwrap_or_else(|| format!("drop row {row}"));
    }
    if let Some(row) = o.glitter_row {
        return match o.glitter_item {
            Some(item) => format!("{} (glitter row {row})", crate::ui::panels::editor::item_name(item as u32)),
            None => format!("random materials of the area (glitter row {row})"),
        };
    }
    String::new()
}

fn push_tile(stroke: &mut Vec<(usize, u16, u16)>, c: (usize, u16, u16)) {
    match stroke.iter_mut().find(|s| s.0 == c.0) {
        Some(s) => s.2 = c.2,
        None => stroke.push(c),
    }
}

fn load_sprite_table(root: &Path) -> HashMap<i32, Vec<String>> {
    std::fs::read_to_string(root.join("game_assets/maps/sprites2d.json"))
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .and_then(|v| v.get("npc_sprites").and_then(|o| o.as_object()).cloned())
        .map(|o| {
            o.into_iter()
                .filter_map(|(k, v)| {
                    let rows = v.as_array()?.iter().map(|s| s.as_str().unwrap_or("").to_string()).collect();
                    Some((k.parse().ok()?, rows))
                })
                .collect()
        })
        .unwrap_or_default()
}

fn load_texture(ctx: &egui::Context, path: &Path, key: &str) -> Option<egui::TextureHandle> {
    let image = crate::utils::decode_image(path, None).ok()?;
    // pixel art: no smoothing
    Some(ctx.load_texture(key, image, egui::TextureOptions::NEAREST))
}

/// First frame of a sprite sheet (UV rect, frame size in pixels). Most sheets are rows of 16x32 frames
/// (504 of 984 are 128x32); square sheets of 64 px and more hold 2x2 bigger frames.
fn first_frame(size: [usize; 2]) -> (egui::Rect, egui::Vec2) {
    let (w, h) = (size[0] as f32, size[1] as f32);
    let (fw, fh) = if h <= 32.0 {
        (16f32.min(w), h)
    } else if w <= 32.0 {
        (w, 32f32.min(h))
    } else {
        (w / (w / (h / 2.0)).max(1.0).round().max(1.0), h / 2.0)
    };
    let fw = fw.min(w).max(1.0);
    (egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(fw / w, fh / h)), egui::vec2(fw, fh))
}

impl View2D {
    pub fn has_data(root: &Path, level: &str) -> bool {
        root.join("game_assets/maps").join(level).join("scene2d.json").is_file()
    }

    fn ensure(&mut self, ctx: &egui::Context, root: &Path, level: &str) {
        if self.loaded_for != level {
            self.loaded_for = level.to_string();
            let (doc, grids) = match load_doc(root, level) {
                Some((d, g)) => (Some(d), g),
                None => (None, Vec::new()),
            };
            self.doc = doc;
            self.grids = grids;
            self.tiles = None;
            self.sel = None;
            self.moving = None;
            self.layer = 0;
            self.coll_grid = None;
            self.palette = None;
            self.stroke_tiles.clear();
            self.stroke_cells.clear();
            self.original = self.doc.as_ref().map(|d| d.objects.clone()).unwrap_or_default();
            self.undo.clear();
            self.redo.clear();
            self.drag = None;
            // 2D edits saved earlier in the level's project file
            let project = std::fs::read_to_string(root.join("editor_projects").join(format!("{level}.json")))
                .ok()
                .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
                .unwrap_or(serde_json::Value::Null);
            let saved = Some(parse_objects(&project["level2d"]["objects"])).filter(|o| !o.is_empty());
            if let (Some(doc), Some(mut saved)) = (self.doc.as_mut(), saved) {
                // projects saved before gimmicks were exported lack them: keep the retail ones
                let known: std::collections::HashSet<String> = saved.iter().filter(|o| o.new_from.is_none()).map(|o| o.record_offset.clone()).collect();
                saved.extend(doc.objects.iter().filter(|o| !known.contains(&o.record_offset)).cloned());
                doc.objects = saved;
            }
            // the editable tile map of the background, with the tile and collision edits saved in the project
            if let Some(bg) = self.doc.as_ref().and_then(|d| d.background.clone()) {
                self.tiles = TileMap::load(ctx, root, &bg, &self.time);
            }
            if let (Some(map), Some(list)) = (self.tiles.as_mut(), project["level2d"]["new_chips"].as_array()) {
                // tiles created in the editor come back in their saved order, so the saved chip ids fit again
                for c in list {
                    let get = |i: usize| c.get(i).and_then(|v| v.as_u64()).unwrap_or(0) as u8;
                    map.chips.push([get(0), get(1), get(2), get(3), get(4)]);
                }
            }
            if let (Some(map), Some(list)) = (self.tiles.as_mut(), project["level2d"]["tiles"].as_array()) {
                for t in list {
                    if let (Some(i), Some(v)) = (t["index"].as_u64(), t["value"].as_u64()) {
                        map.set_index(i as usize, v as u16);
                    }
                }
            }
            if let Some(list) = project["level2d"]["cells"].as_array() {
                for c in list {
                    if let (Some(g), Some(cell), Some(v)) = (c["grid"].as_u64(), c["cell"].as_u64(), c["value"].as_u64()) {
                        if let Some(grid) = self.grids.iter_mut().find(|x| x.index == g as usize) {
                            grid.set(cell as usize, v as u8);
                        }
                    }
                }
            }
            self.selected = std::env::var("DQXI_EDITOR_2D_SELECT").ok().and_then(|v| v.parse().ok());
            self.fit = true;
            self.group = None;
            if let Some(doc) = &self.doc {
                if !doc.times.contains(&self.time) {
                    self.time = doc.times.first().cloned().unwrap_or_else(|| "daytime".into());
                }
            }
        }
        if self.sprite_table.is_none() {
            self.sprite_table = Some(load_sprite_table(root));
        }
        let Some(doc) = &self.doc else { return };
        let Some(bg) = &doc.background else {
            self.map_tex = None;
            return;
        };
        let key = format!("{bg}_{}", self.time);
        if let Some(map) = self.tiles.as_mut() {
            map.set_time(ctx, root, &self.time);
            return;
        }
        if self.map_key != key {
            self.map_key = key.clone();
            self.map_tex = load_texture(ctx, &root.join("game_assets/textures/2d_maps").join(format!("{key}.png")), &format!("map2d/{key}"));
        }
    }

    fn sprite_name(&self, region: i32, id: i64) -> Option<&str> {
        let s = self.sprite_table.as_ref()?.get(&region)?.get(usize::try_from(id).ok()?)?;
        (!s.is_empty()).then_some(s.as_str())
    }

    fn sprite(&mut self, ctx: &egui::Context, root: &Path, name: &str) -> Option<egui::TextureHandle> {
        self.sprites
            .entry(name.to_string())
            .or_insert_with(|| {
                // one-texture sheets are <name>.png; a sheet with several textures is a folder <name>/<texture>.png
                let dir = root.join("game_assets/textures/2d_sprites");
                let path = [dir.join(format!("{name}.png")), dir.join(name).join(format!("{name}.png"))]
                    .into_iter()
                    .find(|p| p.is_file())
                    .or_else(|| {
                        let mut pngs: Vec<_> = std::fs::read_dir(dir.join(name)).ok()?.flatten().map(|e| e.path()).filter(|p| p.extension().is_some_and(|x| x == "png")).collect();
                        pngs.sort();
                        pngs.into_iter().next()
                    })?;
                load_texture(ctx, &path, &format!("sprite2d/{name}"))
            })
            .clone()
    }

    // -- editing ---------------------------------------------------------------------------------------------
    fn objects_mut(&mut self) -> Option<&mut Vec<Obj2D>> {
        self.doc.as_mut().map(|d| &mut d.objects)
    }

    fn snapshot(&mut self) {
        if let Some(objs) = self.doc.as_ref().map(|d| d.objects.clone()) {
            self.undo.push(Step::Objects(objs));
            self.redo.clear();
        }
        self.edited = true;
    }

    /// Applies a step backwards (`back`) or forwards and returns the step that reverses it.
    fn apply_step(&mut self, step: Step, back: bool) -> Step {
        match step {
            Step::Objects(objs) => match self.doc.as_mut() {
                Some(doc) => {
                    let other = std::mem::replace(&mut doc.objects, objs);
                    self.selected = self.selected.filter(|i| *i < doc.objects.len());
                    Step::Objects(other)
                }
                None => Step::Objects(objs),
            },
            Step::Tiles(list) => {
                if let Some(map) = self.tiles.as_mut() {
                    for (i, old, new) in &list {
                        map.set_index(*i, if back { *old } else { *new });
                    }
                }
                Step::Tiles(list)
            }
            Step::Cells(list) => {
                for (g, cell, old, new) in &list {
                    if let Some(grid) = self.grids.get_mut(*g) {
                        grid.set(*cell, if back { *old } else { *new });
                    }
                }
                Step::Cells(list)
            }
        }
    }

    /// Ends a paint stroke: one undo step per stroke.
    fn commit_strokes(&mut self) {
        if !self.stroke_tiles.is_empty() {
            self.undo.push(Step::Tiles(std::mem::take(&mut self.stroke_tiles)));
            self.redo.clear();
            self.edited = true;
        }
        if !self.stroke_cells.is_empty() {
            self.undo.push(Step::Cells(std::mem::take(&mut self.stroke_cells)));
            self.redo.clear();
            self.edited = true;
        }
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }

    pub fn undo(&mut self) {
        if let Some(step) = self.undo.pop() {
            let other = self.apply_step(step, true);
            self.redo.push(other);
            self.edited = true;
        }
    }

    pub fn redo(&mut self) {
        if let Some(step) = self.redo.pop() {
            let other = self.apply_step(step, false);
            self.undo.push(other);
            self.edited = true;
        }
    }

    /// Takes the "something changed" flag (the editor marks the level dirty).
    pub fn take_edited(&mut self) -> bool {
        std::mem::take(&mut self.edited)
    }

    fn editable(o: &Obj2D) -> bool {
        !o.fields.is_empty()
    }

    pub fn duplicate_selected(&mut self) {
        let Some(i) = self.selected else { return };
        let Some(src) = self.doc.as_ref().and_then(|d| d.objects.get(i)).cloned() else { return };
        if !Self::editable(&src) || src.deleted {
            return;
        }
        self.snapshot();
        let mut copy = src.clone();
        copy.new_from = Some(src.new_from.clone().unwrap_or_else(|| src.record_offset.clone()));
        copy.record_offset = String::new();
        copy.x += 2.0;
        copy.y += 2.0;
        if let Some(objs) = self.objects_mut() {
            objs.push(copy);
            self.selected = Some(objs.len() - 1);
        }
    }

    pub fn delete_selected(&mut self) {
        let Some(i) = self.selected else { return };
        let Some(o) = self.doc.as_ref().and_then(|d| d.objects.get(i)).cloned() else { return };
        if !Self::editable(&o) {
            return;
        }
        self.snapshot();
        if let Some(objs) = self.objects_mut() {
            if o.new_from.is_some() {
                objs.remove(i);
            } else {
                objs[i].deleted = true;
            }
        }
        self.selected = None;
    }

    fn revert(&mut self, i: usize) {
        let Some(o) = self.doc.as_ref().and_then(|d| d.objects.get(i)).cloned() else { return };
        let Some(orig) = self.original.iter().find(|r| r.new_from.is_none() && r.record_offset == o.record_offset && o.new_from.is_none()).cloned() else { return };
        self.snapshot();
        if let Some(objs) = self.objects_mut() {
            objs[i] = orig;
        }
    }

    fn original_of(&self, o: &Obj2D) -> Option<&Obj2D> {
        if o.new_from.is_some() {
            return None;
        }
        self.original.iter().find(|r| r.record_offset == o.record_offset)
    }

    fn is_changed(&self, o: &Obj2D) -> bool {
        match self.original_of(o) {
            None => o.new_from.is_some(),
            Some(r) => o.deleted || o.fields.iter().any(|(n, _)| o.get(n) != r.get(n)),
        }
    }

    pub fn change_count(&self) -> usize {
        self.doc.as_ref().map(|d| d.objects.iter().filter(|o| self.is_changed(o)).count()).unwrap_or(0) + self.tile_changes() + self.cell_changes()
    }

    fn tile_changes(&self) -> usize {
        self.tiles.as_ref().map(TileMap::change_count).unwrap_or(0)
    }

    fn cell_changes(&self) -> usize {
        self.grids.iter().map(CollGrid::change_count).sum()
    }

    /// The `level2d` section of the project file (None when this view holds another level or nothing changed).
    pub fn project_section(&self, level: &str) -> Option<serde_json::Value> {
        let doc = self.doc.as_ref().filter(|d| d.level == level)?;
        let hex = |s: &str| i64::from_str_radix(s.trim_start_matches("0x"), 16).unwrap_or(0);
        let mut edits = Vec::new();
        let mut ops = Vec::new();
        for o in doc.objects.iter().filter(|o| !o.deleted && o.new_from.is_none()) {
            let Some(r) = self.original_of(o) else { continue };
            for (name, rel) in &o.fields {
                if o.get(name) != r.get(name) {
                    edits.push(serde_json::json!({"offset": format!("0x{:X}", hex(&o.record_offset) + *rel as i64), "value": o.get(name), "field": name}));
                }
            }
        }
        for o in doc.objects.iter().filter(|o| !o.deleted) {
            if let Some(src) = &o.new_from {
                let set: std::collections::BTreeMap<String, i64> = o.fields.iter().map(|(n, rel)| (rel.to_string(), o.get(n))).collect();
                ops.push(serde_json::json!({"op": "duplicate", "offset": src, "set": set}));
            }
        }
        for o in doc.objects.iter().filter(|o| o.deleted && o.new_from.is_none()) {
            ops.push(serde_json::json!({"op": "delete", "offset": o.record_offset}));
        }
        let (new_chips, remap) = self.tiles.as_ref().map(TileMap::new_chips).unwrap_or_default();
        let tiles: Vec<serde_json::Value> = self
            .tiles
            .as_ref()
            .map(|t| t.changed().into_iter().map(|(i, v)| serde_json::json!({"index": i, "value": remap.get(&v).copied().unwrap_or(v)})).collect())
            .unwrap_or_default();
        let cells: Vec<serde_json::Value> = self
            .grids
            .iter()
            .flat_map(|g| {
                g.flags.iter().zip(&g.original).enumerate().filter(|(_, (a, b))| a != b).map(move |(c, (a, _))| {
                    serde_json::json!({"offset": g.offset + 2 * c, "value": a, "grid": g.index, "cell": c})
                })
            })
            .collect();
        if edits.is_empty() && ops.is_empty() && tiles.is_empty() && cells.is_empty() {
            return Some(serde_json::Value::Null);
        }
        Some(serde_json::json!({
            "source": format!("game_data/packs/level2d/{level}/level2d.bxon"),
            "background": self.tiles.as_ref().map(|t| t.bg.clone()),
            "tiles": tiles,
            "new_chips": new_chips.iter().map(|c| c.to_vec()).collect::<Vec<_>>(),
            "cells": cells,
            "edits": edits,
            "ops": ops,
            "objects": doc.objects.iter().map(Obj2D::to_json).collect::<Vec<_>>(),
        }))
    }

    fn visible(&self, o: &Obj2D) -> bool {
        if o.deleted || self.group.is_some_and(|g| g != o.group) || !o.has_position {
            return false;
        }
        match o.kind.as_str() {
            "actor" => self.show_actors,
            "gimmick" => self.show_gimmicks,
            "trigger" => self.show_triggers,
            "point" => self.show_points,
            _ => false,
        }
    }
}

impl View2D {
    /// Options of the Tiles tool (second bar).
    fn tile_bar(&mut self, ui: &mut egui::Ui) {
        let ctx = ui.ctx().clone();
        let Some(map) = self.tiles.as_mut() else { return };
        self.layer = self.layer.min(map.layers.len().saturating_sub(1));
        let before = self.layer;
        let base = map.layers.get(self.layer).is_some_and(|l| l.base);
        let mut redraw = false;
        let mut copy = false;
        let mut clear = false;
        let mut revert = false;
        ui.horizontal_wrapped(|ui| {
            ui.label(theme::faint_label("Layer"));
            egui::ComboBox::from_id_salt("layer2d").selected_text(map.layer_name(self.layer)).show_ui(ui, |ui| {
                for i in 0..map.layers.len() {
                    ui.selectable_value(&mut self.layer, i, map.layer_name(i));
                }
            });
            let mut solo = map.solo.is_some();
            if ui.checkbox(&mut solo, "Only this layer").on_hover_text("Hide the other layers to see what is on this one").changed() || (solo && before != self.layer) {
                map.solo = solo.then_some(self.layer);
                redraw = true;
            }
            ui.separator();
            for (tool, label, tip) in [
                (TileTool::Paint, "Paint", "Drag to paint with the brush tile (or the copied block). Alt+click picks the tile under the pointer."),
                (TileTool::Erase, "Erase", "Drag to clear cells (overlay: empty; first ground layer: the plain ground tile)"),
                (TileTool::Pick, "Pick", "Click a cell to make its tile the brush"),
                (TileTool::Select, "Select / Move", "Drag a rectangle of cells; drag inside it to move those tiles; Delete clears them"),
            ] {
                ui.selectable_value(&mut self.tile_tool, tool, label).on_hover_text(tip);
            }
            ui.separator();
            ui.label(theme::faint_label("Brush"));
            let (r, _) = ui.allocate_exact_size(egui::vec2(22.0, 22.0), egui::Sense::hover());
            ui.painter().rect_filled(r, 2.0, egui::Color32::from_gray(30));
            match self.stamp.1.first() {
                Some(c) if *c != EMPTY => paint_chip(ui.painter(), map, *c, self.stamp_base, r.shrink(1.0), egui::Color32::WHITE),
                _ => {}
            }
            let rows = self.stamp.1.len() / self.stamp.0.max(1);
            ui.label(theme::mono(if self.stamp.1.len() == 1 {
                match self.stamp.1[0] {
                    EMPTY => "empty".to_string(),
                    c => format!("chip {c}"),
                }
            } else {
                format!("block {} x {rows}", self.stamp.0)
            }));
            if self.stamp_base != base {
                ui.label(egui::RichText::new(if base { "brush is an overlay tile: pick a ground tile" } else { "brush is a ground tile: pick an overlay tile" }).color(theme::WARN).size(11.0));
            }
            ui.toggle_value(&mut self.palette_open, "Palette").on_hover_text("Every tile of this layer's sheet; click one to paint with it");
            ui.checkbox(&mut self.show_grid, "Grid");
            if let Some(sel) = self.sel {
                ui.separator();
                ui.label(theme::faint_label(format!("selection {} x {}", sel[2], sel[3])));
                copy = ui.button("Copy to brush").on_hover_text("Paint copies of the selected block").clicked();
                clear = ui.button("Clear").on_hover_text("Delete key").clicked();
                if ui.button("Deselect").on_hover_text("Esc").clicked() {
                    self.sel = None;
                }
            }
            let n = map.change_count();
            if n > 0 {
                ui.separator();
                ui.label(egui::RichText::new(format!("{n} tile(s) changed")).color(theme::ACCENT).size(11.0));
                revert = ui.button("Revert tiles").on_hover_text("Back to the game's tiles (can be undone)").clicked();
            }
        });
        if redraw {
            map.redraw(&ctx);
        }
        if copy {
            self.copy_selection();
        }
        if clear {
            self.clear_selection();
        }
        if revert {
            if let Some(map) = self.tiles.as_mut() {
                let list: Vec<(usize, u16, u16)> = map.changed().into_iter().map(|(i, v)| (i, v, map.original[i])).collect();
                for (i, _, orig) in &list {
                    map.set_index(*i, *orig);
                }
                self.undo.push(Step::Tiles(list));
                self.redo.clear();
                self.edited = true;
            }
        }
    }

    fn copy_selection(&mut self) {
        let (Some(map), Some([x, y, w, h])) = (self.tiles.as_ref(), self.sel) else { return };
        let mut chips = Vec::with_capacity(w * h);
        for dy in 0..h {
            for dx in 0..w {
                chips.push(map.get(self.layer, x + dx, y + dy));
            }
        }
        self.stamp = (w, chips);
        self.stamp_base = map.layers.get(self.layer).is_some_and(|l| l.base);
        self.tile_tool = TileTool::Paint;
    }

    fn clear_selection(&mut self) {
        let (Some(map), Some([x, y, w, h])) = (self.tiles.as_mut(), self.sel) else { return };
        let blank = map.blank(self.layer);
        for dy in 0..h {
            for dx in 0..w {
                if let Some(c) = map.set(self.layer, x + dx, y + dy, blank) {
                    push_tile(&mut self.stroke_tiles, c);
                }
            }
        }
        self.commit_strokes();
    }

    /// Options of the Collision tool (second bar).
    fn coll_bar(&mut self, ui: &mut egui::Ui) {
        let mut revert = false;
        ui.horizontal_wrapped(|ui| {
            ui.label(theme::faint_label("Paint"));
            ui.selectable_value(&mut self.coll_value, BLOCKED, "Blocked").on_hover_text("The player cannot enter the cell");
            ui.selectable_value(&mut self.coll_value, 0, "Walkable");
            ui.label(theme::faint_label("flags"));
            ui.add(egui::DragValue::new(&mut self.coll_value).range(0..=255).speed(0.2))
                .on_hover_text("The cell's flag byte: 1 = blocked. The game also uses 2, 4, 8, 16, 32, 64 and 128 (stairs, counters and the like; not decoded yet); paint such a value to copy a mark the level already has.");
            if self.grids.len() > 1 {
                ui.separator();
                let text = self.coll_grid.map(|g| format!("Grid {g}")).unwrap_or_else(|| "Grid under the pointer".into());
                egui::ComboBox::from_id_salt("grid2d").selected_text(text).show_ui(ui, |ui| {
                    ui.selectable_value(&mut self.coll_grid, None, "Grid under the pointer");
                    for (i, g) in self.grids.iter().enumerate() {
                        ui.selectable_value(&mut self.coll_grid, Some(i), format!("Grid {i}: {} x {} at ({}, {})", g.w, g.h, g.x, g.y));
                    }
                })
                .response
                .on_hover_text("A level with stairs, bridges or several floors has several walk grids; pick one to paint only into it");
            }
            let n = self.cell_changes();
            if n > 0 {
                ui.separator();
                ui.label(egui::RichText::new(format!("{n} cell(s) changed")).color(theme::ACCENT).size(11.0));
                revert = ui.button("Revert collision").on_hover_text("Back to the game's grid (can be undone)").clicked();
            }
            ui.label(theme::faint_label("red = blocked \u{b7} other colours = other marks \u{b7} drag to paint \u{b7} right-drag pans"));
        });
        if revert {
            let mut list = Vec::new();
            for (gi, g) in self.grids.iter_mut().enumerate() {
                for cell in 0..g.flags.len() {
                    let orig = g.original[cell];
                    if let Some((c, old, new)) = g.set(cell, orig) {
                        list.push((gi, c, old, new));
                    }
                }
            }
            if !list.is_empty() {
                self.undo.push(Step::Cells(list));
                self.redo.clear();
                self.edited = true;
            }
        }
    }

    /// Floating palette: every tile the layer's sheet is used with.
    fn palette_window(&mut self, ctx: &egui::Context, at: egui::Pos2) {
        if !self.palette_open || self.tool != Tool2D::Tiles {
            return;
        }
        let Some(map) = self.tiles.as_ref() else { return };
        let base = map.layers.get(self.layer).is_some_and(|l| l.base);
        if self.palette_sheet {
            self.sheet_window(ctx, at, base);
            return;
        }
        if !self.palette.as_ref().is_some_and(|(bg, b, _)| *bg == map.bg && *b == base) {
            self.palette = Some((map.bg.clone(), base, map.palette(base)));
        }
        let mut to_sheet = false;
        let chips: &[u16] = self.palette.as_ref().map(|p| p.2.as_slice()).unwrap_or(&[]);
        let current = (self.stamp.1.len() == 1 && self.stamp_base == base).then(|| self.stamp.1[0]);
        let mut open = true;
        let mut pick = None;
        egui::Window::new("Tile palette").open(&mut open).default_size([330.0, 420.0]).default_pos(at).show(ctx, |ui| {
            ui.horizontal(|ui| {
                let _ = ui.selectable_label(true, "Tiles in use");
                if ui.selectable_label(false, "Whole sheet").on_hover_text("Every tile of the sheet, in any orientation: also tiles this map does not use yet").clicked() {
                    to_sheet = true;
                }
            });
            ui.label(theme::faint_label(format!(
                "{} {} tiles of this map. Click one to paint with it; Alt+click in the map picks a tile there.",
                chips.len(),
                if base { "ground (16 px)" } else { "overlay (8 px)" }
            )));
            let cell = 34.0;
            let cols = ((ui.available_width() / cell).floor() as usize).max(1);
            let rows = chips.len().div_ceil(cols);
            ui.spacing_mut().item_spacing = egui::Vec2::ZERO;
            egui::ScrollArea::vertical().auto_shrink([false, false]).show_rows(ui, cell, rows, |ui, range| {
                for r in range {
                    ui.horizontal(|ui| {
                        for chip in chips.iter().skip(r * cols).take(cols) {
                            let (rect, resp) = ui.allocate_exact_size(egui::vec2(cell, cell), egui::Sense::click());
                            ui.painter().rect_filled(rect.shrink(1.0), 2.0, egui::Color32::from_gray(if resp.hovered() { 60 } else { 28 }));
                            paint_chip(ui.painter(), map, *chip, base, rect.shrink(3.0), egui::Color32::WHITE);
                            if current == Some(*chip) {
                                ui.painter().rect_stroke(rect.shrink(1.0), 2.0, egui::Stroke::new(2.0, theme::ACCENT), egui::StrokeKind::Inside);
                            }
                            if resp.clicked() {
                                pick = Some(*chip);
                            }
                            let e = map.chips[*chip as usize];
                            resp.on_hover_text(format!("chip {chip} \u{b7} sheet tile ({}, {}) \u{b7} orientation {} \u{b7} attribute {}", e[0], e[1], (e[4] & 0x0E) >> 1, e[2]));
                        }
                    });
                }
            });
        });
        if let Some(chip) = pick {
            self.stamp = (1, vec![chip]);
            self.stamp_base = base;
            self.tile_tool = TileTool::Paint;
        }
        self.palette_open = open;
        self.palette_sheet = to_sheet;
    }

    /// Palette of the whole tile sheet: any tile in any of the eight orientations. A combination the map has no chip
    /// for gets a new chip, which Save to mod appends to the map's chip table.
    fn sheet_window(&mut self, ctx: &egui::Context, at: egui::Pos2, base: bool) {
        let Some(map) = self.tiles.as_ref() else { return };
        let (cols, rows) = map.sheet_tiles(base);
        let orientation = self.palette_orientation;
        let mut new_orientation = orientation;
        let mut open = true;
        let mut pick: Option<(u8, u8)> = None;
        let mut to_used = false;
        let created = map.chips.len() - map.retail_chips;
        egui::Window::new("Tile palette").open(&mut open).default_size([330.0, 420.0]).default_pos(at).show(ctx, |ui| {
            ui.horizontal(|ui| {
                if ui.selectable_label(false, "Tiles in use").clicked() {
                    to_used = true;
                }
                let _ = ui.selectable_label(true, "Whole sheet");
            });
            ui.horizontal_wrapped(|ui| {
                ui.label(theme::faint_label("Placed"));
                egui::ComboBox::from_id_salt("sheet_orientation").selected_text(ORIENTATIONS[orientation as usize & 7]).show_ui(ui, |ui| {
                    for (i, name) in ORIENTATIONS.iter().enumerate() {
                        ui.selectable_value(&mut new_orientation, i as u8, *name);
                    }
                });
                ui.label(theme::faint_label(format!("{cols} x {rows} {} tiles", if base { "ground" } else { "overlay" })));
                if created > 0 {
                    ui.label(egui::RichText::new(format!("{created} new tile(s) made")).color(theme::ACCENT).size(11.0))
                        .on_hover_text("Only the new tiles the map actually uses are written on save");
                }
            });
            let cell = if base { 34.0 } else { 22.0 };
            ui.spacing_mut().item_spacing = egui::Vec2::ZERO;
            // rows as in the sheet, so neighbouring tiles stay together
            egui::ScrollArea::both().auto_shrink([false, false]).show_rows(ui, cell, rows, |ui, range| {
                for r in range {
                    ui.horizontal(|ui| {
                        for c in 0..cols {
                            let (rect, resp) = ui.allocate_exact_size(egui::vec2(cell, cell), egui::Sense::click());
                            if !ui.is_rect_visible(rect) {
                                continue;
                            }
                            ui.painter().rect_filled(rect.shrink(0.5), 0.0, egui::Color32::from_gray(if resp.hovered() { 70 } else { 26 }));
                            paint_tile(ui.painter(), map, c as u8, r as u8, orientation, base, rect.shrink(1.0), egui::Color32::WHITE);
                            if resp.clicked() {
                                pick = Some((c as u8, r as u8));
                            }
                            resp.on_hover_text(format!("sheet tile ({c}, {r}), {}", ORIENTATIONS[orientation as usize & 7]));
                        }
                    });
                }
            });
        });
        self.palette_orientation = new_orientation;
        if let Some((c, r)) = pick {
            if let Some(chip) = self.tiles.as_mut().and_then(|m| m.chip_for(c, r, orientation, base)) {
                self.stamp = (1, vec![chip]);
                self.stamp_base = base;
                self.tile_tool = TileTool::Paint;
                self.palette = None;
            }
        }
        self.palette_open = open;
        self.palette_sheet = !to_used;
    }

    /// Pointer handling of the Tiles tool. `m` = pointer in map pixels.
    fn tile_input(&mut self, m: egui::Vec2, down: bool, pressed: bool, released: bool, alt: bool) {
        let Some(map) = self.tiles.as_mut() else { return };
        if map.layers.is_empty() {
            return;
        }
        let layer = self.layer.min(map.layers.len() - 1);
        let base = map.layers[layer].base;
        let cell = map.cell_at(layer, m.x, m.y);
        self.hover_cell = cell;
        if alt || self.tile_tool == TileTool::Pick {
            if let (true, Some((cx, cy))) = (pressed, cell) {
                self.stamp = (1, vec![map.get(layer, cx, cy)]);
                self.stamp_base = base;
                if self.tile_tool == TileTool::Pick {
                    self.tile_tool = TileTool::Paint;
                }
            }
        } else {
            match self.tile_tool {
                TileTool::Paint => {
                    if let (true, true, Some((cx, cy))) = (down, self.stamp_base == base, cell) {
                        let w = self.stamp.0.max(1);
                        for (k, chip) in self.stamp.1.iter().enumerate() {
                            if let Some(c) = map.set(layer, cx + k % w, cy + k / w, *chip) {
                                push_tile(&mut self.stroke_tiles, c);
                            }
                        }
                    }
                }
                TileTool::Erase => {
                    if let (true, Some((cx, cy))) = (down, cell) {
                        let blank = map.blank(layer);
                        if let Some(c) = map.set(layer, cx, cy, blank) {
                            push_tile(&mut self.stroke_tiles, c);
                        }
                    }
                }
                TileTool::Select => {
                    if pressed {
                        match cell {
                            Some((cx, cy)) => {
                                let inside = self.sel.is_some_and(|s| cx >= s[0] && cy >= s[1] && cx < s[0] + s[2] && cy < s[1] + s[3]);
                                if let (true, Some(s)) = (inside, self.sel) {
                                    self.moving = Some((cx - s[0], cy - s[1]));
                                } else {
                                    self.moving = None;
                                    self.sel_anchor = Some((cx, cy));
                                    self.sel = Some([cx, cy, 1, 1]);
                                }
                            }
                            None => self.sel = None,
                        }
                    } else if let (true, None, Some((ax, ay)), Some((cx, cy))) = (down, self.moving, self.sel_anchor, cell) {
                        self.sel = Some([ax.min(cx), ay.min(cy), ax.abs_diff(cx) + 1, ay.abs_diff(cy) + 1]);
                    }
                }
                TileTool::Pick => {}
            }
        }
        if released {
            if let (Some((gx, gy)), Some([x, y, w, h]), Some((cx, cy))) = (self.moving.take(), self.sel, cell) {
                let (nx, ny) = (cx.saturating_sub(gx), cy.saturating_sub(gy));
                if (nx, ny) != (x, y) {
                    // lift the block, clear where it was, put it down at the new place
                    let mut block = Vec::with_capacity(w * h);
                    for dy in 0..h {
                        for dx in 0..w {
                            block.push(map.get(layer, x + dx, y + dy));
                        }
                    }
                    let blank = map.blank(layer);
                    for dy in 0..h {
                        for dx in 0..w {
                            if let Some(c) = map.set(layer, x + dx, y + dy, blank) {
                                push_tile(&mut self.stroke_tiles, c);
                            }
                        }
                    }
                    for (k, chip) in block.iter().enumerate() {
                        if let Some(c) = map.set(layer, nx + k % w, ny + k / w, *chip) {
                            push_tile(&mut self.stroke_tiles, c);
                        }
                    }
                    self.sel = Some([nx, ny, w, h]);
                }
            }
            self.moving = None;
            self.sel_anchor = None;
            self.commit_strokes();
        }
    }

    /// Grid and cell under a map cell for the Collision tool.
    fn coll_pick(&self, cx: i64, cy: i64) -> Option<(usize, usize)> {
        match self.coll_grid {
            Some(g) => self.grids.get(g).and_then(|grid| grid.cell_at(cx, cy)).map(|c| (g, c)),
            None => self.grids.iter().enumerate().find_map(|(g, grid)| grid.cell_at(cx, cy).map(|c| (g, c))),
        }
    }

    fn coll_input(&mut self, m: egui::Vec2, down: bool, released: bool) {
        let (cx, cy) = ((m.x / 8.0).floor() as i64, (m.y / 8.0).floor() as i64);
        if down {
            if let Some((g, cell)) = self.coll_pick(cx, cy) {
                let value = self.coll_value;
                if let Some((c, old, new)) = self.grids[g].set(cell, value) {
                    match self.stroke_cells.iter_mut().find(|s| s.0 == g && s.1 == c) {
                        Some(s) => s.3 = new,
                        None => self.stroke_cells.push((g, c, old, new)),
                    }
                }
            }
        }
        if released {
            self.commit_strokes();
        }
    }
}

/// The central area while the 2D view is on.
pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui, level: &str, region: i32) {
    let root = app.dirs.root.clone();
    let ctx = ui.ctx().clone();
    let view = &mut app.panels.editor.view2d;
    view.ensure(&ctx, &root, level);

    let Some(doc) = view.doc.as_ref() else {
        ui.centered_and_justified(|ui| {
            ui.label(theme::dim_label("No 2D data for this level. Run: python tools/map2d.py export"));
        });
        return;
    };
    let times = doc.times.clone();
    let groups: Vec<i64> = {
        let mut g: Vec<i64> = doc.objects.iter().map(|o| o.group).collect();
        g.sort();
        g.dedup();
        g
    };
    let counts = |k: &str| doc.objects.iter().filter(|o| o.kind == k).count();
    let (n_actors, n_gimmicks, n_triggers, n_points, n_exits) = (counts("actor"), counts("gimmick"), counts("trigger"), counts("point"), counts("exit"));
    let background = doc.background.clone();
    let (map_w, map_h) = (doc.width, doc.height);
    let has_tiles = view.tiles.is_some();
    let has_grids = !view.grids.is_empty();
    if (view.tool == Tool2D::Tiles && !has_tiles) || (view.tool == Tool2D::Collision && !has_grids) {
        view.tool = Tool2D::Objects;
    }

    // view bar
    egui::Frame::new().fill(theme::BG_RAISED).inner_margin(egui::Margin::symmetric(8, 3)).show(ui, |ui| {
        ui.horizontal_wrapped(|ui| {
            ui.label(egui::RichText::new("2D mode").strong().color(theme::ACCENT));
            ui.separator();
            ui.selectable_value(&mut view.tool, Tool2D::Objects, "Objects").on_hover_text("Select, move, duplicate and delete actors, chests, pots, doors, triggers ...");
            ui.add_enabled_ui(has_tiles, |ui| {
                ui.selectable_value(&mut view.tool, Tool2D::Tiles, "Tiles")
                    .on_hover_text("Paint, pick, select and move the map's tiles, layer by layer")
                    .on_disabled_hover_text("No tile data for this map. Run: python tools/map2d.py export");
            });
            ui.add_enabled_ui(has_grids, |ui| {
                ui.selectable_value(&mut view.tool, Tool2D::Collision, "Collision")
                    .on_hover_text("Paint where the player can walk (the level's walk grid)")
                    .on_disabled_hover_text("This level has no walk grid (leveldmap.bxon), or run: python tools/map2d.py export");
            });
            ui.separator();
            if times.len() > 1 {
                egui::ComboBox::from_id_salt("time2d").selected_text(view.time.clone()).show_ui(ui, |ui| {
                    for t in &times {
                        ui.selectable_value(&mut view.time, t.clone(), t);
                    }
                });
            }
            ui.checkbox(&mut view.show_actors, format!("Actors ({n_actors})"));
            ui.checkbox(&mut view.show_gimmicks, format!("Interactables ({n_gimmicks})")).on_hover_text("Chests, pots, drawers, wardrobes, doors, signboards, books and bookshelves, sparkly spots");
            ui.checkbox(&mut view.show_triggers, format!("Triggers ({n_triggers})"));
            ui.checkbox(&mut view.show_points, format!("Points ({n_points})"));
            if has_grids {
                ui.checkbox(&mut view.show_collision, "Collision").on_hover_text("Show the walk grid: red = blocked");
            }
            ui.checkbox(&mut view.show_labels, "Labels").on_hover_text("Actor ids and what each chest / pot / spot holds");
            if groups.len() > 1 {
                let text = view.group.map(|g| format!("Group {g}")).unwrap_or_else(|| "All groups".into());
                egui::ComboBox::from_id_salt("group2d").selected_text(text).show_ui(ui, |ui| {
                    ui.selectable_value(&mut view.group, None, "All groups");
                    for g in &groups {
                        ui.selectable_value(&mut view.group, Some(*g), format!("Group {g}"));
                    }
                })
                .response
                .on_hover_text("level2d containers: the area script switches level groups on and off by story state, like the 3D level groups");
            }
            if ui.button("Fit").clicked() {
                view.fit = true;
            }
            ui.separator();
            if ui.add_enabled(view.can_undo(), egui::Button::new("Undo")).on_hover_text("Ctrl+Z").clicked() {
                view.undo();
            }
            if ui.add_enabled(view.can_redo(), egui::Button::new("Redo")).on_hover_text("Ctrl+Y").clicked() {
                view.redo();
            }
            let changes = view.change_count();
            if changes > 0 {
                ui.label(egui::RichText::new(format!("\u{25cf} {changes} 2D change(s)")).color(theme::ACCENT).size(11.0))
                    .on_hover_text("Objects, tiles and collision cells. Saved with the level (Save / Save to mod in the toolbar)");
            }
            ui.label(theme::faint_label(format!("{:.0}%", view.zoom * 100.0)));
            if n_exits > 0 {
                ui.label(theme::faint_label(format!("{n_exits} exits (no position, see Inspector list)")));
            }
            if let Some(bg) = background.as_deref().filter(|b| *b != level) {
                ui.label(theme::faint_label(format!("map of {bg}"))).on_hover_text("This level draws another level's 2D map: tile changes show in every level that shares it");
            }
        });
        match view.tool {
            Tool2D::Tiles => view.tile_bar(ui),
            Tool2D::Collision => view.coll_bar(ui),
            Tool2D::Objects => {}
        }
    });
    let (rect, response) = ui.allocate_exact_size(ui.available_size(), egui::Sense::click_and_drag());
    view.palette_window(&ctx, rect.left_top() + egui::vec2(12.0, 12.0));
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 0.0, egui::Color32::from_gray(12));
    if map_w <= 0.0 {
        painter.text(rect.center(), egui::Align2::CENTER_CENTER, "This level has 2D objects but no 2D map", egui::FontId::proportional(14.0), theme::TEXT_DIM);
    }
    let size = egui::vec2(map_w.max(1.0), map_h.max(1.0));
    if view.fit {
        view.fit = false;
        // frame the used part of the map: objects, else the whole map
        let mut lo = egui::pos2(f32::MAX, f32::MAX);
        let mut hi = egui::pos2(f32::MIN, f32::MIN);
        for o in view.doc.as_ref().map(|d| d.objects.clone()).unwrap_or_default().iter().filter(|o| o.has_position && !o.deleted) {
            lo = lo.min(egui::pos2(o.x * 8.0, o.y * 8.0));
            hi = hi.max(egui::pos2((o.x + o.w) * 8.0, (o.y + o.h) * 8.0));
        }
        let frame = if lo.x < hi.x { egui::Rect::from_min_max(lo, hi).expand(96.0) } else { egui::Rect::from_min_size(egui::Pos2::ZERO, size) };
        let frame = frame.intersect(egui::Rect::from_min_size(egui::Pos2::ZERO, size));
        view.zoom = (rect.width() / frame.width()).min(rect.height() / frame.height()).clamp(0.1, 8.0);
        view.pan = (rect.center() - rect.min) - frame.center().to_vec2() * view.zoom;
    }
    let objects_tool = view.tool == Tool2D::Objects;
    // keys: Delete, Ctrl+D duplicate, Esc deselect (the 3D shortcuts are off while the 2D view is on)
    if !ui.ctx().egui_wants_keyboard_input() {
        let (del, dup, esc) = ui.input(|i| {
            (
                i.key_pressed(egui::Key::Delete),
                i.modifiers.command && i.key_pressed(egui::Key::D),
                i.key_pressed(egui::Key::Escape),
            )
        });
        if objects_tool {
            if del {
                view.delete_selected();
            }
            if dup {
                view.duplicate_selected();
            }
            if esc {
                view.selected = None;
            }
        } else if view.tool == Tool2D::Tiles {
            if del {
                view.clear_selection();
            }
            if esc {
                view.sel = None;
            }
        }
    }
    // right or middle drag always pans
    if response.dragged_by(egui::PointerButton::Secondary) || response.dragged_by(egui::PointerButton::Middle) {
        view.pan += response.drag_delta();
    }
    // Objects tool: a drag that starts on the selected object moves it (whole cells); any other drag pans
    if objects_tool && response.drag_started_by(egui::PointerButton::Primary) {
        // grab the selected object when it is under the pointer (objects of other level groups often stand on the
        // same cell), else the topmost object there, which becomes the selection
        let press = ui.input(|i| i.pointer.press_origin()).or(response.interact_pointer_pos());
        let under = press.map(|p| under_pointer(&view.last_hits, p)).unwrap_or_default();
        let grab = view.selected.filter(|i| under.contains(i)).or_else(|| under.first().copied());
        if let Some(i) = grab {
            let start = view.doc.as_ref().and_then(|d| d.objects.get(i)).filter(|o| View2D::editable(o) && !o.deleted).map(|o| egui::pos2(o.x, o.y));
            if let Some(start) = start {
                if view.selected != Some(i) {
                    view.follow.clear();
                }
                view.selected = Some(i);
                let snap = view.doc.as_ref().map(|d| d.objects.clone()).unwrap_or_default();
                view.drag = Some((i, start, snap));
                view.drag_accum = egui::Vec2::ZERO;
            }
        }
    }
    if objects_tool && response.dragged_by(egui::PointerButton::Primary) {
        if let Some((i, start, snap)) = view.drag.clone() {
            view.drag_accum += response.drag_delta();
            let cells = view.drag_accum / (view.zoom * 8.0);
            let (dx, dy) = (cells.x.round().max(-start.x), cells.y.round().max(-start.y));
            let follow = view.follow.clone();
            if let Some(objs) = view.objects_mut() {
                for j in std::iter::once(i).chain(follow.into_iter().filter(|j| *j != i)) {
                    if let (Some(o), Some(s0)) = (objs.get_mut(j), snap.get(j)) {
                        o.x = (s0.x + dx).max(0.0);
                        o.y = (s0.y + dy).max(0.0);
                    }
                }
            }
        } else {
            view.pan += response.drag_delta();
        }
    }
    if response.drag_stopped() {
        if let Some((i, start, snap)) = view.drag.take() {
            let moved = view.doc.as_ref().and_then(|d| d.objects.get(i)).is_some_and(|o| o.x != start.x || o.y != start.y);
            if moved {
                view.undo.push(Step::Objects(snap));
                view.redo.clear();
                view.edited = true;
            }
        }
    }
    if let Some(pos) = response.hover_pos() {
        let scroll = ui.input(|i| i.smooth_scroll_delta.y);
        if scroll != 0.0 {
            let old = view.zoom;
            view.zoom = (view.zoom * (scroll * 0.0025).exp()).clamp(0.1, 12.0);
            let anchor = pos - rect.min - view.pan;
            view.pan -= anchor * (view.zoom / old - 1.0);
        }
    }
    let (zoom, origin) = (view.zoom, rect.min + view.pan);
    let to_screen = |p: egui::Pos2| origin + p.to_vec2() * zoom;

    // Tiles / Collision tool: the left button paints
    if !objects_tool {
        let (primary_down, pressed, released, alt) = ui.input(|i| (i.pointer.primary_down(), i.pointer.primary_pressed(), i.pointer.primary_released(), i.modifiers.alt));
        let pointer = response.interact_pointer_pos().or(response.hover_pos());
        match pointer {
            Some(p) => {
                let m = (p - origin) / zoom;
                let down = primary_down && response.is_pointer_button_down_on();
                let pressed = pressed && response.is_pointer_button_down_on();
                // a fast drag skips cells between two frames: walk the line from the last pointer position
                let from = view.last_paint.filter(|_| down && !pressed).unwrap_or(m);
                let steps = (((m - from).length() / 4.0).ceil() as usize).clamp(1, 400);
                for k in 1..=steps {
                    let at = from + (m - from) * (k as f32 / steps as f32);
                    let last = k == steps;
                    match view.tool {
                        Tool2D::Tiles => view.tile_input(at, down, pressed && k == 1, released && last, alt),
                        _ => view.coll_input(at, down, released && last),
                    }
                }
                view.last_paint = down.then_some(m);
            }
            None => {
                view.hover_cell = None;
                if released {
                    view.moving = None;
                    view.sel_anchor = None;
                    view.commit_strokes();
                }
            }
        }
    }

    let map_tex = view.tiles.as_ref().and_then(|t| t.tex.as_ref().map(|t| t.id())).or(view.map_tex.as_ref().map(|t| t.id()));
    if let Some(tex) = map_tex {
        painter.image(tex, egui::Rect::from_min_size(origin, size * zoom), egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(1.0, 1.0)), egui::Color32::WHITE);
    }

    // walk grid
    if view.show_collision || view.tool == Tool2D::Collision {
        let active = view.coll_grid;
        let editing = view.tool == Tool2D::Collision;
        for (gi, g) in view.grids.iter_mut().enumerate() {
            let r = egui::Rect::from_min_size(to_screen(egui::pos2(g.x as f32 * 8.0, g.y as f32 * 8.0)), egui::vec2(g.w as f32, g.h as f32) * 8.0 * zoom);
            let dim = editing && active.is_some_and(|a| a != gi);
            let tex = g.texture(&ctx, level);
            painter.image(tex, r, egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(1.0, 1.0)), if dim { egui::Color32::from_white_alpha(70) } else { egui::Color32::WHITE });
            if editing {
                let stroke = if active == Some(gi) { egui::Stroke::new(2.0, theme::ACCENT) } else { egui::Stroke::new(1.0, egui::Color32::from_white_alpha(70)) };
                painter.rect_stroke(r, 0.0, stroke, egui::StrokeKind::Outside);
            }
        }
    }

    // tile grid, selection and brush preview
    if view.tool == Tool2D::Tiles {
        if let Some(map) = view.tiles.as_ref() {
            let layer = view.layer.min(map.layers.len().saturating_sub(1));
            let g = map.geom(layer);
            let step = g.cell as f32 * zoom;
            let cell_rect = |cx: usize, cy: usize, w: usize, h: usize| {
                egui::Rect::from_min_size(to_screen(egui::pos2(((g.ox + cx) * g.cell) as f32, ((g.oy + cy) * g.cell) as f32)), egui::vec2(w as f32, h as f32) * step)
            };
            if view.show_grid && step >= 8.0 && g.cols > 0 {
                let area = cell_rect(0, 0, g.cols, g.rows);
                let line = egui::Stroke::new(1.0, egui::Color32::from_white_alpha(22));
                let first_x = (((rect.left() - area.left()) / step).floor().max(0.0)) as usize;
                let last_x = ((((rect.right() - area.left()) / step).ceil()).max(0.0) as usize).min(g.cols);
                for cx in first_x..=last_x {
                    let x = area.left() + cx as f32 * step;
                    painter.line_segment([egui::pos2(x, area.top().max(rect.top())), egui::pos2(x, area.bottom().min(rect.bottom()))], line);
                }
                let first_y = (((rect.top() - area.top()) / step).floor().max(0.0)) as usize;
                let last_y = ((((rect.bottom() - area.top()) / step).ceil()).max(0.0) as usize).min(g.rows);
                for cy in first_y..=last_y {
                    let y = area.top() + cy as f32 * step;
                    painter.line_segment([egui::pos2(area.left().max(rect.left()), y), egui::pos2(area.right().min(rect.right()), y)], line);
                }
            }
            if let Some([x, y, w, h]) = view.sel {
                let r = cell_rect(x, y, w, h);
                painter.rect_filled(r, 0.0, egui::Color32::from_rgba_unmultiplied(232, 184, 75, 30));
                painter.rect_stroke(r, 0.0, egui::Stroke::new(2.0, theme::ACCENT), egui::StrokeKind::Outside);
                if let (Some((gx, gy)), Some((cx, cy))) = (view.moving, view.hover_cell) {
                    let ghost = cell_rect(cx.saturating_sub(gx), cy.saturating_sub(gy), w, h);
                    painter.rect_stroke(ghost, 0.0, egui::Stroke::new(2.0, egui::Color32::WHITE), egui::StrokeKind::Outside);
                }
            }
            if let Some((cx, cy)) = view.hover_cell.filter(|_| response.hovered()) {
                let base = map.layers.get(layer).is_some_and(|l| l.base);
                match view.tile_tool {
                    TileTool::Paint if view.stamp_base == base => {
                        let w = view.stamp.0.max(1);
                        for (k, chip) in view.stamp.1.iter().enumerate() {
                            if *chip != EMPTY {
                                paint_chip(&painter, map, *chip, base, cell_rect(cx + k % w, cy + k / w, 1, 1), egui::Color32::from_white_alpha(190));
                            }
                        }
                        painter.rect_stroke(cell_rect(cx, cy, w, view.stamp.1.len() / w), 0.0, egui::Stroke::new(1.5, egui::Color32::WHITE), egui::StrokeKind::Outside);
                    }
                    TileTool::Select => {}
                    _ => {
                        painter.rect_stroke(cell_rect(cx, cy, 1, 1), 0.0, egui::Stroke::new(1.5, egui::Color32::WHITE), egui::StrokeKind::Outside);
                    }
                }
            }
        }
    }

    // objects: triggers, points and gimmicks under actors; remember screen rects for picking
    let objects = view.doc.as_ref().map(|d| d.objects.clone()).unwrap_or_default();
    let mut hits: Vec<(usize, egui::Rect)> = Vec::new();
    let selected = view.selected;
    for pass in 0..2 {
        for (i, o) in objects.iter().enumerate() {
            if !view.visible(o) || (pass == 0) == (o.kind == "actor") {
                continue;
            }
            let sel = selected == Some(i);
            let changed = view.is_changed(o);
            let cell = egui::pos2(o.x * 8.0, o.y * 8.0);
            let r = match o.kind.as_str() {
                "trigger" => {
                    let r = egui::Rect::from_min_size(to_screen(cell), egui::vec2(o.w * 8.0, o.h * 8.0) * zoom);
                    painter.rect_filled(r, 0.0, egui::Color32::from_rgba_unmultiplied(80, 200, 255, if sel { 90 } else { 40 }));
                    painter.rect_stroke(r, 0.0, egui::Stroke::new(if sel { 2.0 } else { 1.0 }, egui::Color32::from_rgb(80, 200, 255)), egui::StrokeKind::Inside);
                    r
                }
                "point" => {
                    let c = to_screen(cell + egui::vec2(4.0, 4.0));
                    painter.circle_filled(c, (2.5 * zoom).clamp(2.0, 6.0), egui::Color32::from_rgb(255, 210, 80));
                    if sel {
                        painter.circle_stroke(c, (5.0 * zoom).clamp(5.0, 12.0), egui::Stroke::new(2.0, egui::Color32::WHITE));
                    }
                    egui::Rect::from_center_size(c, egui::vec2(10.0, 10.0))
                }
                "gimmick" => {
                    // like an actor: the sprite stands on its cell
                    let tex = o.sprite.as_deref().and_then(|s| view.sprite(&ctx, &root, s));
                    // A door record carries its footprint (2 cells for a door, 4 for a double door, 8 for a gate: the
                    // (w, h) pairs at +0x04 / +0x06), and the picture is centred on that footprint, not on the first cell.
                    let span = match o.label.as_str() {
                        "Door" => 2.0,
                        "Double door" => 4.0,
                        "Gate" => 8.0,
                        _ => 1.0,
                    };
                    let foot = cell + egui::vec2(span * 4.0, 8.0);
                    let r = match &tex {
                        Some(tex) => {
                            let (uv, frame) = gimmick_frame(tex.size());
                            let r = egui::Rect::from_min_size(to_screen(foot - egui::vec2(frame.x / 2.0, frame.y)), frame * zoom);
                            painter.image(tex.id(), r, uv, egui::Color32::WHITE);
                            r
                        }
                        None => {
                            // no sprite of its own (bookshelf, sparkly spot): a marker on the cell
                            let c = to_screen(cell + egui::vec2(4.0, 4.0));
                            let rad = (5.0 * zoom).clamp(5.0, 14.0);
                            if o.glitter_row.is_some() {
                                // a four-point sparkle: two crossed diamonds
                                let gold = egui::Color32::from_rgb(255, 236, 110);
                                let (long, short) = (rad * 1.4, rad * 0.4);
                                painter.add(egui::Shape::convex_polygon(
                                    vec![c + egui::vec2(0.0, -long), c + egui::vec2(short, 0.0), c + egui::vec2(0.0, long), c + egui::vec2(-short, 0.0)],
                                    gold,
                                    egui::Stroke::NONE,
                                ));
                                painter.add(egui::Shape::convex_polygon(
                                    vec![c + egui::vec2(-long, 0.0), c + egui::vec2(0.0, -short), c + egui::vec2(long, 0.0), c + egui::vec2(0.0, short)],
                                    gold,
                                    egui::Stroke::NONE,
                                ));
                            } else {
                                let b = egui::Rect::from_center_size(c, egui::vec2(rad * 1.8, rad * 1.8));
                                painter.rect_filled(b, 2.0, egui::Color32::from_rgba_unmultiplied(110, 150, 255, 150));
                                painter.rect_stroke(b, 2.0, egui::Stroke::new(1.0, egui::Color32::from_rgb(170, 200, 255)), egui::StrokeKind::Inside);
                            }
                            egui::Rect::from_center_size(c, egui::vec2(rad * 2.4, rad * 2.4))
                        }
                    };
                    if sel {
                        painter.rect_stroke(r.expand(2.0), 2.0, egui::Stroke::new(2.0, theme::ACCENT), egui::StrokeKind::Outside);
                    }
                    if changed {
                        painter.circle_filled(r.right_top(), 3.5, theme::ACCENT);
                    }
                    if view.show_labels || sel {
                        let text = gimmick_text(o);
                        let text = if text.is_empty() { o.label.clone() } else { format!("{}: {text}", o.label) };
                        let pos = r.center_top() - egui::vec2(0.0, 2.0);
                        let galley = painter.layout_no_wrap(text, egui::FontId::proportional(11.0), egui::Color32::WHITE);
                        let bg = egui::Rect::from_min_size(pos - egui::vec2(galley.size().x / 2.0, galley.size().y), galley.size()).expand(2.0);
                        painter.rect_filled(bg, 3.0, egui::Color32::from_black_alpha(190));
                        painter.galley(bg.min + egui::vec2(2.0, 2.0), galley, egui::Color32::WHITE);
                    }
                    r
                }
                _ => {
                    // actor: sprite's first frame standing on its cell (feet at the cell's bottom edge)
                    let sprite = o.entity_id.and_then(|id| view.sprite_name(region, id)).map(str::to_owned);
                    let tex = sprite.as_deref().and_then(|s| view.sprite(&ctx, &root, s));
                    let foot = cell + egui::vec2(4.0, 8.0);
                    let r = match &tex {
                        Some(tex) => {
                            let (uv, frame) = first_frame(tex.size());
                            let r = egui::Rect::from_min_size(to_screen(foot - egui::vec2(frame.x / 2.0, frame.y)), frame * zoom);
                            painter.image(tex.id(), r, uv, egui::Color32::WHITE);
                            r
                        }
                        None => {
                            let r = egui::Rect::from_min_size(to_screen(foot - egui::vec2(6.0, 16.0)), egui::vec2(12.0, 16.0) * zoom);
                            painter.rect_filled(r, 2.0, egui::Color32::from_rgba_unmultiplied(255, 120, 60, 160));
                            r
                        }
                    };
                    if sel {
                        painter.rect_stroke(r.expand(2.0), 2.0, egui::Stroke::new(2.0, theme::ACCENT), egui::StrokeKind::Outside);
                    }
                    if changed {
                        painter.circle_filled(r.right_top(), 3.5, theme::ACCENT);
                    }
                    if view.show_labels {
                        painter.text(r.center_bottom() + egui::vec2(0.0, 2.0), egui::Align2::CENTER_TOP, format!("#{}", o.entity_id.unwrap_or(-1)), egui::FontId::monospace(10.0), egui::Color32::WHITE);
                    }
                    r
                }
            };
            hits.push((i, r));
        }
    }

    view.last_hits = hits.clone();
    if objects_tool && response.clicked() {
        // clicking again on stacked objects cycles through them
        let under = response.interact_pointer_pos().map(|p| under_pointer(&hits, p)).unwrap_or_default();
        view.selected = match view.selected.and_then(|s| under.iter().position(|i| *i == s)) {
            Some(k) => under.get((k + 1) % under.len()).copied(),
            None => under.first().copied(),
        };
        view.follow.clear();
    }
    if let Some(p) = response.hover_pos() {
        if objects_tool {
            if let Some((i, _)) = hits.iter().rev().find(|(_, r)| r.contains(p)) {
                let o = &objects[*i];
                response.clone().on_hover_text(describe(o, view.sprite_name(region, o.entity_id.unwrap_or(-1))));
            }
        }
        let m = (p - origin) / zoom;
        let (cx, cy) = ((m.x / 8.0).floor(), (m.y / 8.0).floor());
        let text = match view.tool {
            Tool2D::Objects => format!("cell {cx}, {cy}  (8 px)  \u{b7}  drag: move the object under the pointer, else pan  \u{b7}  wheel: zoom  \u{b7}  click: select"),
            Tool2D::Tiles => {
                let what = match (view.tiles.as_ref(), view.hover_cell) {
                    (Some(map), Some((tx, ty))) => {
                        let layer = view.layer.min(map.layers.len().saturating_sub(1));
                        match map.get(layer, tx, ty) {
                            EMPTY => format!("{} cell {tx}, {ty}: empty", map.layer_name(layer)),
                            c => format!("{} cell {tx}, {ty}: chip {c}", map.layer_name(layer)),
                        }
                    }
                    _ => "outside this layer".to_string(),
                };
                format!("{what}  \u{b7}  left: {}  \u{b7}  Alt+click: pick  \u{b7}  right-drag: pan  \u{b7}  wheel: zoom", match view.tile_tool {
                    TileTool::Paint => "paint",
                    TileTool::Erase => "erase",
                    TileTool::Pick => "pick",
                    TileTool::Select => "select / move",
                })
            }
            Tool2D::Collision => match view.coll_pick(cx as i64, cy as i64) {
                Some((g, cell)) => {
                    let grid = &view.grids[g];
                    let zone = grid.zones.get(cell).copied().unwrap_or(0xFF);
                    format!(
                        "cell {cx}, {cy}  \u{b7}  grid {g}  \u{b7}  flags {}{}{}  \u{b7}  left: paint  \u{b7}  right-drag: pan",
                        grid.flags[cell],
                        if grid.flags[cell] & BLOCKED != 0 { " (blocked)" } else { " (walkable)" },
                        if zone == 0xFF { String::new() } else { format!("  \u{b7}  zone {zone}") }
                    )
                }
                None => format!("cell {cx}, {cy}  \u{b7}  no walk grid here"),
            },
        };
        let galley = painter.layout_no_wrap(text, egui::FontId::proportional(11.0), theme::TEXT_DIM);
        let pos = rect.left_bottom() + egui::vec2(8.0, -6.0 - galley.size().y);
        painter.rect_filled(egui::Rect::from_min_size(pos, galley.size()).expand(3.0), 3.0, egui::Color32::from_black_alpha(170));
        painter.galley(pos, galley, theme::TEXT_DIM);
    }
}

/// Objects under a screen point, topmost first: actors (drawn last) before triggers/points, smaller rects first.
fn under_pointer(hits: &[(usize, egui::Rect)], p: egui::Pos2) -> Vec<usize> {
    let mut found: Vec<(usize, usize, f32)> = hits.iter().enumerate().filter(|(_, (_, r))| r.contains(p)).map(|(order, (i, r))| (order, *i, r.area())).collect();
    found.sort_by(|a, b| a.2.total_cmp(&b.2).then(b.0.cmp(&a.0)));
    found.into_iter().map(|(_, i, _)| i).collect()
}

fn describe(o: &Obj2D, sprite: Option<&str>) -> String {
    match o.kind.as_str() {
        "actor" => format!("Actor #{} at ({}, {}){}", o.entity_id.unwrap_or(-1), o.x, o.y, sprite.map(|s| format!("  \u{b7}  sprite {s}")).unwrap_or_default()),
        "trigger" => format!("Trigger at ({}, {}) size {} x {}", o.x, o.y, o.w, o.h),
        "gimmick" => {
            let text = gimmick_text(o);
            format!("{} at ({}, {}){}", o.label, o.x, o.y, if text.is_empty() { String::new() } else { format!("  \u{b7}  {text}") })
        }
        _ => format!("{} at ({}, {})", o.kind, o.x, o.y),
    }
}

/// Inspector part for the 2D view: the selected 2D object (and the level's exits, which have no position).
/// Returns the selected actor's entity id so the caller can show its Dialogue section.
pub fn inspector(app: &mut ViewerApp, ui: &mut egui::Ui, region: i32) -> Option<i64> {
    let root = app.dirs.root.clone();
    let ctx = ui.ctx().clone();
    let view = &mut app.panels.editor.view2d;
    let doc = view.doc.as_ref()?;
    let exits: Vec<Obj2D> = doc.objects.iter().filter(|o| o.kind == "exit").cloned().collect();
    let level = doc.level.clone();
    let picked = view.selected.and_then(|i| doc.objects.get(i)).cloned();
    let picked_index = view.selected;
    let mut actor = None;
    match view.tool {
        Tool2D::Tiles => {
            egui::CollapsingHeader::new(egui::RichText::new("Tiles").strong()).default_open(true).show(ui, |ui| {
                if let Some(map) = view.tiles.as_ref() {
                    ui.label(theme::faint_label(format!(
                        "{} x {} px \u{b7} {} layers \u{b7} {} chips. A chip is one tile of the sheet in one of 8 orientations; a cell holds a chip id.",
                        map.width,
                        map.height,
                        map.layers.len(),
                        map.chips.len()
                    )));
                    ui.label(theme::faint_label("Ground layers use 16 px tiles, overlay layers 8 px tiles with transparency. Save to mod writes the changed cells into 2d/bg/<map>.pack. The palette's Whole sheet tab offers every tile in any orientation; a combination the map lacks becomes a new chip, appended to the map's chip table on save (the file grows). Emulator-proven: changed cells and a new chip show in the game (tools/emu/edit2d_probe.py)."));
                    if map.bg != level {
                        ui.label(egui::RichText::new(format!("This level draws the map of {}: tile changes show in every level sharing it.", map.bg)).color(theme::WARN));
                    }
                }
            });
        }
        Tool2D::Collision => {
            egui::CollapsingHeader::new(egui::RichText::new("Collision (walk grid)").strong()).default_open(true).show(ui, |ui| {
                ui.label(theme::faint_label(format!(
                    "{} grid(s) of 8 px cells from level2d/<level>/leveldmap.bxon. Flag 1 = blocked. The same grids map each 2D cell to its place in the 3D level.",
                    view.grids.len()
                )));
                ui.label(theme::faint_label("Emulator-proven: a blocked row stops the hero in 2D mode (tools/emu/edit2d_probe.py). Flags other than 1 are not decoded."));
            });
        }
        Tool2D::Objects => {}
    }
    egui::CollapsingHeader::new(egui::RichText::new("2D object").strong()).default_open(true).show(ui, |ui| {
        let Some(o) = &picked else {
            ui.label(theme::faint_label("Objects tool: click an actor, chest, pot, door, trigger or point in the 2D view."));
            return;
        };
        let sprite = o.entity_id.and_then(|id| view.sprite_name(region, id)).map(str::to_owned);
        ui.label(egui::RichText::new(describe(o, None)).strong());
        if let (Some(i), true) = (picked_index, View2D::editable(o)) {
            let mut working = o.clone();
            ui.horizontal_wrapped(|ui| {
                for (name, _) in &o.fields {
                    let label = match name.as_str() {
                        "entity_id" => "entity id",
                        "drop_row" => "drop row",
                        other => other,
                    };
                    ui.label(theme::faint_label(label));
                    let mut v = working.get(name);
                    if ui.add(egui::DragValue::new(&mut v).range(0..=0xFFFF).speed(0.2)).changed() {
                        working.set(name, v);
                    }
                }
            });
            if working.fields.iter().any(|(n, _)| working.get(n) != o.get(n)) {
                let (dx, dy) = (working.x - o.x, working.y - o.y);
                let follow = view.follow.clone();
                view.snapshot();
                if let Some(objs) = view.objects_mut() {
                    if let Some(slot) = objs.get_mut(i) {
                        *slot = working;
                    }
                    for j in follow.into_iter().filter(|j| *j != i) {
                        if let Some(f) = objs.get_mut(j) {
                            f.x = (f.x + dx).max(0.0);
                            f.y = (f.y + dy).max(0.0);
                        }
                    }
                }
            }
            // copies of this character in other level groups (one record per story state, same spot)
            let copies: Vec<(usize, i64)> = view
                .doc
                .as_ref()
                .map(|d| {
                    d.objects
                        .iter()
                        .enumerate()
                        .filter(|(j, c)| {
                            *j != i && !c.deleted && c.kind == "actor" && o.kind == "actor" && c.entity_id == o.entity_id
                                && (c.x - o.x).abs() <= 1.0 && (c.y - o.y).abs() <= 1.0
                        })
                        .map(|(j, c)| (j, c.group))
                        .collect()
                })
                .unwrap_or_default();
            if !copies.is_empty() {
                egui::Frame::new().fill(theme::BG_RAISED).inner_margin(egui::Margin::same(6)).corner_radius(4.0).show(ui, |ui| {
                    let groups: Vec<String> = copies.iter().map(|(_, g)| g.to_string()).collect();
                    ui.label(egui::RichText::new(format!(
                        "{} other cop{} of this character here (group {})",
                        copies.len(),
                        if copies.len() == 1 { "y" } else { "ies" },
                        groups.join(", ")
                    )).color(theme::WARN));
                    ui.label(theme::faint_label(format!("One record per story state; this one is group {}. The area script enables the groups by story progress.", o.group)));
                    ui.horizontal_wrapped(|ui| {
                        for (j, g) in &copies {
                            if ui.small_button(format!("Select g{g}")).clicked() {
                                view.selected = Some(*j);
                                view.follow.clear();
                            }
                        }
                        let mut together = copies.iter().all(|(j, _)| view.follow.contains(j));
                        if ui.checkbox(&mut together, "Move copies together").on_hover_text("Dragging or editing x / y moves every story state of this character").changed() {
                            view.follow = if together { copies.iter().map(|(j, _)| *j).collect() } else { Vec::new() };
                        }
                    });
                });
            }
            ui.horizontal(|ui| {
                if ui.button("Duplicate").on_hover_text("Ctrl+D: a copy in the same array, 2 cells down-right").clicked() {
                    view.duplicate_selected();
                }
                if ui.button("Delete").on_hover_text("Delete key").clicked() {
                    view.delete_selected();
                }
                let changed = view.is_changed(o);
                if ui.add_enabled(changed && o.new_from.is_none(), egui::Button::new("Revert")).clicked() {
                    view.revert(i);
                }
            });
            if let Some(src) = &o.new_from {
                ui.label(theme::faint_label(format!("New record, a copy of {src}; Save to mod appends it to the same array.")));
            }
        }
        egui::Grid::new("obj2d").num_columns(2).striped(true).show(ui, |ui| {
            let mut row = |k: &str, v: String| {
                ui.label(theme::faint_label(k));
                ui.label(theme::mono(v));
                ui.end_row();
            };
            row("position", format!("{}, {}  (x8 px = {}, {})", o.x, o.y, o.x * 8.0, o.y * 8.0));
            if o.kind == "trigger" {
                row("size", format!("{} x {} cells", o.w, o.h));
            }
            if let Some(id) = o.entity_id {
                row("entity id", format!("{id}  (row of region {} npc_list)", region + 1));
            }
            if let Some(f) = o.facing {
                row("word +0x26", format!("{f:#06x}"));
            }
            if let Some(s) = &sprite {
                row("sprite", s.clone());
            }
            if o.kind == "gimmick" {
                row("kind", o.label.clone());
                if let Some(s) = &o.sprite {
                    row("sprite", s.clone());
                }
                let text = gimmick_text(o);
                if !text.is_empty() {
                    row("holds", text);
                }
            }
            row("group", o.group.to_string());
            row("record", format!("{} [{}] at {}", o.array, o.index, o.record_offset));
        });
        if let Some(s) = &sprite {
            if let Some(tex) = view.sprite(&ctx, &root, s) {
                let [w, h] = tex.size();
                let scale = (300.0 / w as f32).min(3.0);
                ui.add(egui::Image::new((tex.id(), egui::vec2(w as f32, h as f32) * scale)));
                ui.label(theme::faint_label("Whole sprite sheet (all frames). Also in Assets \u{203a} Textures, pack 2d_sprites."));
            }
        }
        if o.kind == "gimmick" {
            if o.drop_row.is_some() {
                ui.label(theme::faint_label("The drop row is a row of fieldcmn/fixed_drop_param (item + count), the same row the 3D record of this chest / pot carries: change both, or edit the row itself in Data > Tables. 65535 = nothing."));
            }
            if o.glitter_row.is_some() {
                ui.label(theme::faint_label("Sparkly spot: its id is a row of fieldcmn/glitter_drop_param, the same row as the level's 3D sparkly spot (which is emulator-proven)."));
            }
            if o.label == "Bookshelf" || o.label == "Book" {
                ui.label(theme::faint_label("What a shelf or book says comes from the region's book_ie text bank (Game text editor); which entry belongs to which shelf is not decoded yet."));
            }
        }
        if o.kind == "actor" {
            actor = o.entity_id;
        }
    });
    if !exits.is_empty() {
        egui::CollapsingHeader::new(egui::RichText::new(format!("2D exits ({})", exits.len()))).default_open(false).show(ui, |ui| {
            ui.label(theme::faint_label("Exit records of level2d (no position of their own; the trigger in front of the door starts them)."));
            for e in &exits {
                let dest = e.destination_map.unwrap_or(-1);
                let name = crate::ui::panels::editor::map_name(dest).unwrap_or_default();
                ui.label(theme::mono(format!("group {} \u{b7} map {dest} {name} \u{b7} locator {}", e.group, e.locator.unwrap_or(0))));
            }
        });
    }
    let _ = level;
    actor
}
