//! Model library index (`game_models/by_category/<Category>/<Model>/<Model>.obj`).

use std::collections::HashMap;
use std::path::PathBuf;

use super::{file_size, rel_string, walk_all};
use crate::utils::Dirs;

#[derive(Clone)]
pub struct Model {
    pub name: String,
    pub display_name: Option<String>,
    pub category: String,
    pub obj: PathBuf,
    pub dir: PathBuf,
    pub rel_dir: String,
    pub size: u64,
    pub has_mtl: bool,
    pub has_gltf: bool,
    pub has_bin: bool,
}

impl Model {
    pub fn sidecars(&self) -> String {
        let mut parts = Vec::new();
        if self.has_mtl {
            parts.push("mtl");
        }
        if self.has_gltf {
            parts.push("gltf");
        }
        if self.has_bin {
            parts.push("bin");
        }
        if parts.is_empty() {
            "-".into()
        } else {
            parts.join(", ")
        }
    }
}

#[derive(Clone, Default)]
pub struct ModelIndex {
    pub items: Vec<Model>,
    pub ready: bool,
    pub total_bytes: u64,
    categories: Vec<(String, usize)>,
    by_name: HashMap<String, usize>,
}

impl ModelIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let mut items = Vec::new();
        let names: HashMap<String, String> = std::fs::read_to_string(dirs.models.join("model_names.json"))
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default();
        // one directory walk; sidecar checks are set lookups instead of three
        // `exists()` syscalls per model
        let files: std::collections::HashSet<PathBuf> = walk_all(&dirs.models).into_iter().collect();
        let mut objs: Vec<&PathBuf> = files
            .iter()
            .filter(|p| p.extension().is_some_and(|e| e.eq_ignore_ascii_case("obj")))
            .collect();
        objs.sort();
        for obj in objs {
            let obj = obj.clone();
            let rel = obj.strip_prefix(&dirs.models).unwrap_or(&obj);
            let parts: Vec<String> = rel
                .components()
                .map(|c| c.as_os_str().to_string_lossy().into_owned())
                .collect();
            let (name, category) = if parts.first().map(|p| p == "by_category").unwrap_or(false) {
                if parts.len() >= 3 {
                    (parts[parts.len() - 2].clone(), parts[parts.len() - 3].clone())
                } else {
                    (
                        obj.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default(),
                        parts.get(1).cloned().unwrap_or_default(),
                    )
                }
            } else if parts.len() >= 3 {
                // game_assets/models/packs/3d/<bg|model>/<asset>/<asset>/<asset>.obj
                let stem = obj.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
                let folder = parts.get(2).map(String::as_str).unwrap_or("");
                let category = category_of(&stem, folder);
                (stem, category)
            } else if parts.len() == 2 {
                (
                    obj.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default(),
                    parts[0].clone(),
                )
            } else {
                (
                    obj.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default(),
                    String::new(),
                )
            };
            let dir = obj.parent().map(|p| p.to_path_buf()).unwrap_or_default();
            let display_name = names.get(&name.to_lowercase()).cloned();
            items.push(Model {
                name,
                display_name,
                category,
                rel_dir: rel_string(&dir, &dirs.models),
                size: file_size(&obj),
                has_mtl: files.contains(&obj.with_extension("mtl")),
                has_gltf: files.contains(&obj.with_extension("gltf")),
                has_bin: files.contains(&obj.with_extension("bin")),
                dir,
                obj,
            });
        }
        items.sort_by(|a, b| {
            a.category
                .to_lowercase()
                .cmp(&b.category.to_lowercase())
                .then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
        });
        self.total_bytes = items.iter().map(|m| m.size).sum();
        let mut counts: HashMap<String, usize> = HashMap::new();
        self.by_name.clear();
        for (i, m) in items.iter().enumerate() {
            *counts.entry(m.category.clone()).or_insert(0) += 1;
            self.by_name.entry(m.name.to_lowercase()).or_insert(i);
        }
        let mut categories: Vec<(String, usize)> = counts.into_iter().collect();
        categories.sort_by(|a, b| a.0.to_lowercase().cmp(&b.0.to_lowercase()));
        self.categories = categories;
        self.items = items;
        self.ready = true;
    }

    pub fn categories(&self) -> &[(String, usize)] {
        &self.categories
    }

    pub fn get(&self, name: &str) -> Option<&Model> {
        self.by_name.get(&name.to_lowercase()).map(|i| &self.items[*i])
    }

    pub fn search(&self, query: &str, category: Option<&str>) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        self.items
            .iter()
            .enumerate()
            .filter(|(_, m)| {
                category.map(|c| m.category == c).unwrap_or(true)
                    && (q.is_empty()
                        || m.name.to_lowercase().contains(&q)
                        || m.display_name
                            .as_deref()
                            .map(|n| n.to_lowercase().contains(&q))
                            .unwrap_or(false)
                        || m.category.to_lowercase().contains(&q))
            })
            .map(|(i, _)| i)
            .collect()
    }
}

/// Library category from the game's file naming: maps live under `bg/`, models
/// are named by kind (cha = character, m = monster, w = weapon, ...).
pub fn category_of(stem: &str, folder: &str) -> String {
    if folder == "bg" {
        return "Maps".into();
    }
    let s = stem.to_ascii_lowercase();
    let digit_after = |prefix: &str| s.strip_prefix(prefix).and_then(|r| r.chars().next()).is_some_and(|c| c.is_ascii_digit());
    let category = if digit_after("cha") {
        "Characters"
    } else if digit_after("ccg") || digit_after("fcg") {
        "Cutscene models"
    } else if digit_after("ani") {
        "Animals"
    } else if digit_after("m") {
        "Monsters"
    } else if digit_after("w") {
        "Weapons"
    } else if digit_after("g") {
        "Props"
    } else if digit_after("r") {
        "Mounts"
    } else {
        "Other"
    };
    category.into()
}
