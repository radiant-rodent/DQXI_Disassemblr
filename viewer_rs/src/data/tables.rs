//! Parameter table index (`game_tables/<category>/*.json`).

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use super::{file_size, load_json, walk_ext};
use crate::utils::Dirs;

#[derive(Clone)]
pub struct Table {
    pub category: String,
    pub name: String,
    pub path: PathBuf,
    pub size: u64,
}

#[derive(Clone, Default)]
pub struct TableIndex {
    pub items: Vec<Table>,
    pub ready: bool,
    categories: Vec<(String, usize)>,
    cache: HashMap<PathBuf, serde_json::Value>,
}

impl TableIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let mut items = Vec::new();
        for path in walk_ext(&dirs.tables, &["json"]) {
            let category = path
                .strip_prefix(&dirs.tables)
                .ok()
                .and_then(|rel| {
                    let parts: Vec<_> = rel.components().collect();
                    if parts.len() > 2
                        && (parts[0].as_os_str() == "packs" || parts[0].as_os_str() == "romfs")
                    {
                        Some(parts[1].as_os_str().to_string_lossy().into_owned())
                    } else if parts.len() > 1 {
                        Some(parts[0].as_os_str().to_string_lossy().into_owned())
                    } else {
                        None
                    }
                })
                .unwrap_or_else(|| "root".into());
            items.push(Table {
                name: path.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default(),
                category,
                size: file_size(&path),
                path,
            });
        }
        items.sort_by(|a, b| {
            a.category
                .to_lowercase()
                .cmp(&b.category.to_lowercase())
                .then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
        });
        let mut counts: HashMap<String, usize> = HashMap::new();
        for t in &items {
            *counts.entry(t.category.clone()).or_insert(0) += 1;
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

    pub fn search(&self, query: &str, category: Option<&str>) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        self.items
            .iter()
            .enumerate()
            .filter(|(_, t)| {
                category.map(|c| t.category == c).unwrap_or(true)
                    && (q.is_empty()
                        || t.name.to_lowercase().contains(&q)
                        || t.category.to_lowercase().contains(&q))
            })
            .map(|(i, _)| i)
            .collect()
    }

    pub fn load(&mut self, path: &Path) -> Option<serde_json::Value> {
        if let Some(v) = self.cache.get(path) {
            return Some(v.clone());
        }
        let value = load_json(path)?;
        if self.cache.len() > 12 {
            self.cache.clear();
        }
        self.cache.insert(path.to_path_buf(), value.clone());
        Some(value)
    }

    /// One line describing the top-level shape of a table.
    pub fn summary(&mut self, index: usize) -> String {
        let Some(table) = self.items.get(index) else {
            return "-".into();
        };
        let path = table.path.clone();
        let Some(value) = self.load(&path) else {
            return "unreadable".into();
        };
        let Some(map) = value.as_object() else {
            return match value {
                serde_json::Value::Array(a) => format!("array of {}", a.len()),
                _ => "scalar".into(),
            };
        };
        let mut bits = Vec::new();
        for (key, value) in map {
            match value {
                serde_json::Value::Array(a) => bits.push(format!("{key}: {} items", a.len())),
                serde_json::Value::Object(o) => bits.push(format!("{key}: {} fields", o.len())),
                other => bits.push(format!("{key}: {}", crate::utils::elide(&other.to_string(), 24))),
            }
            if bits.len() >= 4 {
                break;
            }
        }
        if bits.is_empty() {
            "empty".into()
        } else {
            bits.join("  \u{b7}  ")
        }
    }
}
