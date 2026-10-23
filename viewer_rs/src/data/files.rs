//! Raw extracted-data browser (`game_data/romfs`).

use std::path::PathBuf;

use super::{file_size, rel_string, walk_all};
use crate::utils::Dirs;

#[derive(Clone)]
pub struct RawFile {
    pub path: PathBuf,
    pub rel: String,
    pub size: u64,
    pub ext: String,
    pub kind: String,
}

#[derive(Default)]
pub struct FileIndex {
    pub items: Vec<RawFile>,
    pub ready: bool,
    pub total_bytes: u64,
    kinds: Vec<(String, usize)>,
}

impl FileIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let mut items = Vec::new();
        for path in walk_all(&dirs.raw) {
            let ext = path
                .extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_lowercase();
            let kind = match ext.as_str() {
                "pack" | "paca" => "archive",
                "bch" => "model",
                "bxon" => "table",
                "cnut" => "script",
                "bflim" => "texture",
                "bflyt" | "bflan" => "layout",
                "bcstm" | "bcsar" | "bcgrp" => "audio",
                "arc" => "sarc",
                "bffnt" => "font",
                "moflex" => "movie",
                _ => "raw",
            };
            items.push(RawFile {
                rel: rel_string(&path, &dirs.raw),
                size: file_size(&path),
                ext,
                kind: kind.to_string(),
                path,
            });
        }
        items.sort_by(|a, b| a.rel.to_lowercase().cmp(&b.rel.to_lowercase()));
        self.total_bytes = items.iter().map(|f| f.size).sum();
        let mut counts: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
        for f in &items {
            *counts.entry(f.kind.clone()).or_insert(0) += 1;
        }
        let mut kinds: Vec<(String, usize)> = counts.into_iter().collect();
        kinds.sort_by(|a, b| a.0.cmp(&b.0));
        self.kinds = kinds;
        self.items = items;
        self.ready = true;
    }

    pub fn kinds(&self) -> &[(String, usize)] {
        &self.kinds
    }

    pub fn search(&self, query: &str, kind: Option<&str>, limit: usize) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        let mut out = Vec::new();
        for (i, f) in self.items.iter().enumerate() {
            if kind.map(|k| f.kind != k).unwrap_or(false) {
                continue;
            }
            if !q.is_empty() && !f.rel.to_lowercase().contains(&q) {
                continue;
            }
            out.push(i);
            if out.len() >= limit {
                break;
            }
        }
        out
    }
}
