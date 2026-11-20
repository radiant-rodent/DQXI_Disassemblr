//! Texture library index (`game_textures/<pack>/timg/<name>.png`).

use std::collections::HashMap;
use std::path::PathBuf;

use super::{file_size, load_json, rel_string, walk_ext};
use crate::utils::Dirs;

#[derive(Clone)]
pub struct Texture {
    pub name: String,
    pub path: PathBuf,
    pub pack: String,
    /// "Group / Kind", e.g. "Battle / Monster pictures" - what the browser filters by.
    pub category: String,
    pub rel: String,
    pub size: u64,
    pub width: Option<u32>,
    pub height: Option<u32>,
    pub format: String,
    pub bflim_size: Option<u64>,
    pub alignment: Option<i64>,
    pub flags: Option<i64>,
}

impl Texture {
    pub fn dims(&self) -> String {
        match (self.width, self.height) {
            (Some(w), Some(h)) => format!("{w}x{h}"),
            _ => "-".into(),
        }
    }
}

#[derive(Clone, Default)]
pub struct TextureIndex {
    pub items: Vec<Texture>,
    pub ready: bool,
    pub total_bytes: u64,
    packs: Vec<(String, usize)>,
    categories: Vec<(String, usize)>,
    by_stem: HashMap<String, usize>,
    pack_index: HashMap<String, usize>,
}

impl TextureIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let mut items = Vec::new();
        for png in walk_ext(&dirs.textures, &["png"]) {
            let pack = png
                .strip_prefix(&dirs.textures)
                .ok()
                .and_then(pack_of_rel)
                .unwrap_or_default();
            let meta = png.with_file_name(format!(
                "{}.meta.json",
                png.file_stem().map(|s| s.to_string_lossy()).unwrap_or_default()
            ));
            let meta = load_json(&meta).unwrap_or(serde_json::Value::Null);
            let num = |v: &str| meta.get(v).and_then(|x| x.as_u64());
            let sint = |v: &str| meta.get(v).and_then(|x| x.as_i64());
            items.push(Texture {
                name: png.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default(),
                rel: rel_string(&png, &dirs.textures),
                size: file_size(&png),
                width: num("width").map(|v| v as u32),
                height: num("height").map(|v| v as u32),
                format: meta
                    .get("format_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("-")
                    .to_string(),
                bflim_size: num("bflim_size"),
                alignment: sint("alignment"),
                flags: sint("flags"),
                category: classify(&rel_string(&png, &dirs.textures), &pack),
                pack,
                path: png,
            });
        }
        items.sort_by(|a, b| {
            a.pack
                .to_lowercase()
                .cmp(&b.pack.to_lowercase())
                .then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
        });
        self.total_bytes = items.iter().map(|t| t.size).sum();
        let mut pack_map: HashMap<String, usize> = HashMap::new();
        self.by_stem.clear();
        for (i, t) in items.iter().enumerate() {
            *pack_map.entry(t.pack.clone()).or_insert(0) += 1;
            self.by_stem.entry(t.name.to_lowercase()).or_insert(i);
        }
        let mut packs: Vec<(String, usize)> = pack_map.into_iter().collect();
        packs.sort_by(|a, b| a.0.to_lowercase().cmp(&b.0.to_lowercase()));
        self.pack_index = packs
            .iter()
            .enumerate()
            .map(|(i, (name, _))| (name.clone(), i))
            .collect();
        self.packs = packs;
        let mut cats: HashMap<String, usize> = HashMap::new();
        for t in &items {
            *cats.entry(t.category.clone()).or_insert(0) += 1;
        }
        let mut categories: Vec<(String, usize)> = cats.into_iter().collect();
        categories.sort_by(|a, b| a.0.to_lowercase().cmp(&b.0.to_lowercase()));
        self.categories = categories;
        self.items = items;
        self.ready = true;
    }

    /// `("Group / Kind", count)` sorted by name, so a group's kinds sit together.
    pub fn categories(&self) -> &[(String, usize)] {
        &self.categories
    }

    pub fn packs(&self) -> &[(String, usize)] {
        &self.packs
    }

    pub fn pack_of(&self, index: usize) -> &str {
        self.items.get(index).map(|t| t.pack.as_str()).unwrap_or("")
    }

    /// Indices matching the query/pack filter (query matches name or pack).
    pub fn search(&self, query: &str, pack: Option<&str>, limit: Option<usize>) -> Vec<usize> {
        self.search_in(query, pack, None, limit)
    }

    /// Like `search`, also limited to one category (`"Group / Kind"`) or a whole group (`"Group"`).
    pub fn search_in(&self, query: &str, pack: Option<&str>, category: Option<&str>, limit: Option<usize>) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        let mut out = Vec::new();
        for (i, t) in self.items.iter().enumerate() {
            if let Some(cat) = category {
                let whole = t.category == cat;
                let in_group = t.category.split(" / ").next() == Some(cat);
                if !whole && !in_group {
                    continue;
                }
            }
            if let Some(pack) = pack {
                if t.pack != pack {
                    continue;
                }
            }
            if !q.is_empty() && !t.name.to_lowercase().contains(&q) && !t.pack.to_lowercase().contains(&q) {
                continue;
            }
            out.push(i);
            if let Some(limit) = limit {
                if out.len() >= limit {
                    break;
                }
            }
        }
        out
    }

    /// Resolve a BFLIM reference such as `background_2d.bflim`.
    pub fn resolve(&self, name: &str) -> Option<&Texture> {
        let stem = std::path::Path::new(name)
            .file_stem()
            .map(|s| s.to_string_lossy().to_lowercase())
            .unwrap_or_default();
        if let Some(i) = self.by_stem.get(&stem) {
            return self.items.get(*i);
        }
        if let Some((head, _)) = stem.rsplit_once('_') {
            if let Some(i) = self.by_stem.get(head) {
                return self.items.get(*i);
            }
        }
        None
    }
}

/// Sorts a texture into "Group / Kind" from where it was extracted. The folder names are the
/// game's own (`2d_battle_enemies`, `arcs/ui/poker_3d`, ...); this turns them into something a
/// person looks for: Battle, World (2D), Interface, Minigames, Items, Cutscenes, Effects.
pub fn classify(rel: &str, pack: &str) -> String {
    let parts: Vec<&str> = rel.split('/').collect();
    let top = parts.first().copied().unwrap_or("");
    // arcs/ui/<pack>/... and ui/<pack>/... both name the UI pack in the same slot
    let ui_pack = match top {
        "arcs" => parts.get(2).copied().unwrap_or(pack),
        "ui" => parts.get(1).copied().unwrap_or(pack),
        _ => "",
    };
    let pair = |g: &str, k: &str| format!("{g} / {k}");
    match top {
        "2d_battle_backgrounds" => pair("Battle", "Backgrounds"),
        "2d_battle_common" => pair("Battle", "Common patterns"),
        "2d_battle_effects" => pair("Battle", "Spell and hit effects"),
        "2d_battle_enemies" => pair("Battle", "Monster pictures"),
        "2d_battle_enemy_anims" => pair("Battle", "Monster animation sheets"),
        "2d_maps" => pair("World (2D)", "Map images"),
        "2d_sprites" => pair("World (2D)", "Character and object sprites"),
        "2d_tilesets" => pair("World (2D)", "Tilesets"),
        "2d_weather" => pair("Effects", "Weather"),
        "2d_effects" | "2d_common" => pair("Effects", "Field effects"),
        "misc_bch" => pair("Cutscenes", "Cutscene stills"),
        "arcs" | "ui" => match ui_pack {
            "map" => pair("Interface", "Town and world maps"),
            "title" | "logo_3d" | "logo_2d" => pair("Interface", "Title and logos"),
            "battle_2d" | "battle_3d" => pair("Battle", "Battle screen"),
            "common_2d" | "common_2way" | "common_3d" | "compactcommon" => pair("Interface", "Common menus and icons"),
            "panel_3d" => pair("Interface", "Skill panels"),
            "equip_3d" | "record_3d" | "stpass_3d" | "stamp_3d" | "present_3d" | "memories_3d" | "memories_2d" => {
                pair("Interface", "Menus and records")
            }
            "credit" | "credit_3d" => pair("Interface", "Credits"),
            "tutorial" => pair("Interface", "Tutorials"),
            "story" => pair("Interface", "Story chapter art"),
            "location" => pair("Interface", "Location banners"),
            "item" => pair("Items", "Item icons"),
            "image_cs" => pair("Cutscenes", "Cutscene images"),
            "smith_3d" => pair("Minigames", "Forging"),
            "poker_3d" | "casino_slot_3d" | "roulette_3d" | "horseRace_3d" => pair("Minigames", "Casino"),
            "dive_dugeon_2way" | "dive_dugeon_btl_2way" | "dive" => pair("Minigames", "Dive dungeon"),
            "training" => pair("Minigames", "Training"),
            _ => pair("Interface", "Other screens"),
        },
        _ => pair("Other", "Uncategorised"),
    }
}

/// Pack a texture belongs to, from its path under the textures folder: the first folder below
/// the grouping folders (`arcs/ui/map/b001_101a_2d/...` -> `b001_101a_2d`,
/// `arcs/ui/battle_2d/...` -> `battle_2d`). Area names like `b001_101a_2d` are what the Maps
/// panel matches, so taking the top folder (`arcs`) left every map with no textures.
fn pack_of_rel(rel: &std::path::Path) -> Option<String> {
    let dirs: Vec<String> = rel
        .parent()?
        .components()
        .map(|c| c.as_os_str().to_string_lossy().into_owned())
        .collect();
    let skip = dirs
        .iter()
        .take(dirs.len().saturating_sub(1))
        .take_while(|d| matches!(d.to_lowercase().as_str(), "arcs" | "ui" | "map" | "maps" | "by_category"))
        .count();
    dirs.get(skip).cloned()
}

#[cfg(test)]
mod tests {
    use super::pack_of_rel;
    use std::path::Path;

    #[test]
    fn textures_sort_into_readable_categories() {
        use super::classify;
        assert_eq!(classify("2d_battle_enemies/enemy_l.png", "2d_battle_enemies"), "Battle / Monster pictures");
        assert_eq!(classify("arcs/ui/poker_3d/poker_3d/timg/a.png", "poker_3d"), "Minigames / Casino");
        assert_eq!(classify("ui/item/i_use_001.png", "item"), "Items / Item icons");
        assert_eq!(classify("arcs/ui/map/b001_101a_2d/x/timg/a.png", "b001_101a_2d"), "Interface / Town and world maps");
    }

    #[test]
    fn pack_is_the_folder_below_the_grouping_folders() {
        let p = |s: &str| pack_of_rel(Path::new(s)).unwrap_or_default();
        assert_eq!(p("arcs/ui/map/b001_101a_2d/b001_101a/timg/b001_101a.png"), "b001_101a_2d");
        assert_eq!(p("arcs/ui/battle_2d/battle_2d/timg/bg.png"), "battle_2d");
        assert_eq!(p("Shared_UI_Icons/icon.png"), "Shared_UI_Icons");
        assert_eq!(p("loose.png"), "");
    }

    /// Every exported map texture folder must end up attached to an area in the Maps panel.
    #[test]
    fn map_textures_attach_to_their_area() {
        let dirs = crate::utils::Dirs::detect();
        if !dirs.textures.join("arcs/ui/map").is_dir() {
            return; // no exported assets in this checkout
        }
        let mut index = super::TextureIndex::default();
        index.ensure(&dirs);
        let areas: std::collections::HashSet<String> =
            index.packs().iter().filter_map(|(p, _)| crate::data::areas::area_of(p)).collect();
        assert!(areas.contains("b001_101a"), "b001_101a has no texture pack");
        assert!(areas.len() > 100, "only {} areas have textures", areas.len());
    }
}
