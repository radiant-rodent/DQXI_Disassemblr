//! UI layout index (`game_layouts/<pack>/*.layout.json` + `*.anim.json`).

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use super::{file_size, load_json, walk_ext};
use crate::utils::Dirs;

#[derive(Clone)]
pub struct Layout {
    pub pack: String,
    pub stem: String,
    pub path: PathBuf,
    pub kind: String,
    pub size: u64,
}

#[derive(Clone, Default)]
pub struct LayoutIndex {
    pub items: Vec<Layout>,
    pub ready: bool,
    packs: Vec<(String, usize)>,
    cache: HashMap<PathBuf, serde_json::Value>,
}

impl LayoutIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let mut items = Vec::new();
        for path in walk_ext(&dirs.layouts, &["json"]) {
            let name = path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
            let kind = if name.ends_with(".bflan.json") || name.ends_with(".anim.json") {
                "anim"
            } else if name.ends_with(".bflyt.json") || name.ends_with(".layout.json") {
                "layout"
            } else {
                continue;
            };
            let pack = path
                .strip_prefix(&dirs.layouts)
                .ok()
                .and_then(|rel| rel.components().next().map(|c| c.as_os_str().to_string_lossy().into_owned()))
                .unwrap_or_default();
            items.push(Layout {
                pack,
                stem: name,
                size: file_size(&path),
                kind: kind.into(),
                path,
            });
        }
        items.sort_by(|a, b| a.stem.cmp(&b.stem));
        let mut counts: HashMap<String, usize> = HashMap::new();
        for l in &items {
            *counts.entry(l.pack.clone()).or_insert(0) += 1;
        }
        let mut packs: Vec<(String, usize)> = counts.into_iter().collect();
        packs.sort_by(|a, b| a.0.to_lowercase().cmp(&b.0.to_lowercase()));
        self.packs = packs;
        self.items = items;
        self.ready = true;
    }

    pub fn packs(&self) -> &[(String, usize)] {
        &self.packs
    }

    pub fn search(&self, query: &str, pack: Option<&str>, kind: Option<&str>) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        self.items
            .iter()
            .enumerate()
            .filter(|(_, l)| {
                pack.map(|p| l.pack == p).unwrap_or(true)
                    && kind.map(|k| l.kind == k).unwrap_or(true)
                    && (q.is_empty()
                        || l.stem.to_lowercase().contains(&q)
                        || l.pack.to_lowercase().contains(&q))
            })
            .map(|(i, _)| i)
            .collect()
    }

    pub fn load(&mut self, path: &Path) -> Option<serde_json::Value> {
        if let Some(v) = self.cache.get(path) {
            return Some(v.clone());
        }
        let value = load_json(path)?;
        if self.cache.len() > 24 {
            self.cache.clear();
        }
        self.cache.insert(path.to_path_buf(), value.clone());
        Some(value)
    }
}
