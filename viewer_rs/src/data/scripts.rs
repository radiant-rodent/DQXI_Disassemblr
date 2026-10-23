//! Squirrel script index (`game_scripts/<area>/script.nut`), plus the read-only
//! `script.decompiled.nut` pseudo-source written beside it by `tools/squirrel_decompile.py`.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use super::{file_size, walk_ext};
use crate::utils::{read_text, Dirs};

#[derive(Clone)]
pub struct Script {
    pub area: String,
    pub path: PathBuf,
    pub size: u64,
}

#[derive(Clone, Default)]
pub struct ScriptIndex {
    pub items: Vec<Script>,
    pub ready: bool,
    cache: HashMap<PathBuf, String>,
}

impl ScriptIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let mut items = Vec::new();
        for path in walk_ext(&dirs.scripts, &["nut"]) {
            if is_decompiled(&path) {
                continue;
            }
            let area = path
                .strip_prefix(&dirs.scripts)
                .ok()
                .and_then(|rel| rel.components().next().map(|c| c.as_os_str().to_string_lossy().into_owned()))
                .unwrap_or_default();
            items.push(Script {
                area,
                size: file_size(&path),
                path,
            });
        }
        items.sort_by(|a, b| a.area.cmp(&b.area));
        self.items = items;
        self.ready = true;
    }

    pub fn search(&self, query: &str) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        self.items
            .iter()
            .enumerate()
            .filter(|(_, s)| q.is_empty() || s.area.to_lowercase().contains(&q))
            .map(|(i, _)| i)
            .collect()
    }

    pub fn text(&mut self, path: &PathBuf) -> String {
        if let Some(text) = self.cache.get(path) {
            return text.clone();
        }
        let text = read_text(path).unwrap_or_else(|e| format!("// failed to read: {e}"));
        if self.cache.len() > 16 {
            self.cache.clear();
        }
        self.cache.insert(path.clone(), text.clone());
        text
    }

    /// `(name, args, comment)` for every `function name(...)` line of a decompiled file.
    pub fn outline_decompiled(&self, text: &str) -> Vec<(String, String, String)> {
        let mut out = Vec::new();
        for line in text.lines() {
            let Some(rest) = line.trim_start().strip_prefix("function ") else {
                continue;
            };
            let Some((name, tail)) = rest.split_once('(') else {
                continue;
            };
            let name = name.trim();
            if name.is_empty() {
                continue;
            }
            let args = tail.split_once(')').map(|(a, _)| a.to_string()).unwrap_or_default();
            out.push((name.to_string(), args, String::new()));
        }
        out
    }

    /// `(name, args, comment)` for every `function '...'` line.
    pub fn outline(&self, text: &str) -> Vec<(String, String, String)> {
        let mut out = Vec::new();
        for line in text.lines() {
            let trimmed = line.trim_start();
            let Some(rest) = trimmed.strip_prefix("function '") else {
                continue;
            };
            let Some((name, tail)) = rest.split_once('\'') else {
                continue;
            };
            let args = tail
                .strip_prefix('(')
                .and_then(|t| t.split_once(')').map(|(a, _)| a.to_string()))
                .unwrap_or_default();
            let comment = line
                .split_once("/*")
                .and_then(|(_, rest)| rest.split_once("*/").map(|(c, _)| c.trim().to_string()))
                .unwrap_or_default();
            out.push((name.to_string(), args, comment));
        }
        out
    }
}

/// `script.decompiled.nut` is a view of `script.nut`, not a separate script.
pub fn is_decompiled(path: &Path) -> bool {
    path.file_name()
        .and_then(|n| n.to_str())
        .is_some_and(|n| n.ends_with(".decompiled.nut"))
}

/// The decompiled sibling of a disassembly (`x.nut` -> `x.decompiled.nut`), if it exists.
pub fn decompiled_path(path: &Path) -> Option<PathBuf> {
    let stem = path.file_stem()?.to_str()?;
    let sibling = path.with_file_name(format!("{stem}.decompiled.nut"));
    sibling.is_file().then_some(sibling)
}
