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
        self.items = items;
        self.ready = true;
    }

    pub fn packs(&self) -> &[(String, usize)] {
        &self.packs
    }

    pub fn pack_of(&self, index: usize) -> &str {
        self.items.get(index).map(|t| t.pack.as_str()).unwrap_or("")
    }

    /// Indices matching the query/pack filter (query matches name or pack).
    pub fn search(&self, query: &str, pack: Option<&str>, limit: Option<usize>) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        let mut out = Vec::new();
        for (i, t) in self.items.iter().enumerate() {
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
