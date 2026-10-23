//! Map / area dossiers: every asset family cross referenced by area id.

use std::collections::HashMap;
use std::path::PathBuf;

use super::{audio::AudioIndex, dialogues::DialogueDb, layouts::LayoutIndex, models::ModelIndex,
            scripts::ScriptIndex, textures::TextureIndex};
use crate::utils::Dirs;

/// Area id such as `b001_101a` extracted from an asset name.
pub fn area_of(name: &str) -> Option<String> {
    let mut base = name.trim().to_lowercase();
    base = base.rsplit('.').next_back().map(|s| s.to_string()).unwrap_or(base);
    for suffix in ["_2d", "_3d", "_cs", "_script", "_tcs", "_area"] {
        if let Some(stripped) = base.strip_suffix(suffix) {
            base = stripped.to_string();
        }
    }
    match parse_area(&base) {
        Some(area) => Some(area),
        None => {
            if let Some(rest) = base.strip_prefix("map_") {
                parse_area(rest)
            } else {
                None
            }
        }
    }
}

fn parse_area(base: &str) -> Option<String> {
    let bytes = base.as_bytes();
    if bytes.is_empty() || !bytes[0].is_ascii_alphabetic() {
        return None;
    }
    let rest = &base[1..];
    let rest = rest.strip_prefix('_').unwrap_or(rest);
    if rest.len() < 3 || !rest[..3].chars().all(|c| c.is_ascii_digit()) {
        return None;
    }
    let group = &rest[..3];
    if group == "000" {
        return None;
    }
    let letter = bytes[0] as char;
    let tail = &rest[3..];
    if let Some(tail) = tail.strip_prefix('_') {
        if tail.len() >= 3 && tail[..3].chars().all(|c| c.is_ascii_digit()) {
            let sub = &tail[..3];
            let suffix: String = tail[3..]
                .chars()
                .take_while(|c| c.is_ascii_lowercase())
                .collect();
            return Some(format!("{letter}{group}_{sub}{suffix}"));
        }
    }
    Some(format!("{letter}{group}"))
}

fn sort_key(area: &str) -> (char, u32, u32) {
    let letter = area.chars().next().unwrap_or('z');
    let mut parts = area[1..].split('_');
    let group = parts.next().and_then(|v| v.parse().ok()).unwrap_or(0);
    let sub = parts
        .next()
        .map(|v| v.chars().take(3).collect::<String>())
        .and_then(|v| v.parse().ok())
        .unwrap_or(0);
    (letter, group, sub)
}

#[derive(Clone, Default)]
pub struct AreaDossier {
    pub area: String,
    pub textures: Vec<String>,
    pub scripts: Vec<String>,
    pub audio: Vec<String>,
    pub layouts: Vec<String>,
    pub models: Vec<String>,
    pub level2d: Vec<(String, u64)>,
    pub level3d: Vec<(String, u64)>,
    pub dialogue_total: usize,
    pub dialogue_files: Vec<(String, usize)>,
}

impl AreaDossier {
    pub fn asset_count(&self) -> usize {
        self.textures.len()
            + self.scripts.len()
            + self.audio.len()
            + self.layouts.len()
            + self.models.len()
            + self.level2d.len()
            + self.level3d.len()
    }
}

#[derive(Default)]
pub struct AreaIndex {
    pub areas: Vec<String>,
    dossiers: HashMap<String, AreaDossier>,
    /// In-game place names by area code (`game_assets/maps/area_names.json`).
    names: HashMap<String, String>,
    pub ready: bool,
}

impl AreaIndex {
    pub fn ensure(
        &mut self,
        dirs: &Dirs,
        textures: &TextureIndex,
        scripts: &ScriptIndex,
        audio: &AudioIndex,
        layouts: &LayoutIndex,
        models: &ModelIndex,
        dialogues: &mut DialogueDb,
    ) {
        if self.ready {
            return;
        }
        let mut buckets: HashMap<String, AreaDossier> = HashMap::new();
        let mut push = |buckets: &mut HashMap<String, AreaDossier>, area: String| {
            buckets.entry(area.clone()).or_insert_with(|| AreaDossier {
                area,
                ..Default::default()
            });
        };

        for (pack, _) in textures.packs() {
            if let Some(area) = area_of(pack) {
                push(&mut buckets, area.clone());
                if let Some(d) = buckets.get_mut(&area) {
                    d.textures.push(pack.clone());
                }
            }
        }
        for script in &scripts.items {
            if let Some(area) = area_of(&script.area) {
                push(&mut buckets, area.clone());
                if let Some(d) = buckets.get_mut(&area) {
                    d.scripts.push(script.area.clone());
                }
            }
        }
        for stream in &audio.streams {
            if let Some(area) = area_of(&stream.name) {
                push(&mut buckets, area.clone());
                if let Some(d) = buckets.get_mut(&area) {
                    d.audio.push(stream.name.clone());
                }
            }
        }
        for model in &models.items {
            if let Some(area) = area_of(&model.name) {
                push(&mut buckets, area.clone());
                if let Some(d) = buckets.get_mut(&area) {
                    d.models.push(model.name.clone());
                }
            }
        }
        for (dir, is_3d) in [(&dirs.level2d, false), (&dirs.level3d, true)] {
            if let Ok(entries) = std::fs::read_dir(dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map(|e| e != "pack").unwrap_or(true) {
                        continue;
                    }
                    let stem = path.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
                    if let Some(area) = area_of(&stem) {
                        let size = super::file_size(&path);
                        push(&mut buckets, area.clone());
                        if let Some(d) = buckets.get_mut(&area) {
                            if is_3d {
                                d.level3d.push((stem, size));
                            } else {
                                d.level2d.push((stem, size));
                            }
                        }
                    }
                }
            }
        }
        for entry in dialogues.layout_packs() {
            let stem = std::path::Path::new(&entry)
                .file_stem()
                .map(|s| s.to_string_lossy().into_owned())
                .unwrap_or_default();
            if let Some(area) = area_of(&stem) {
                push(&mut buckets, area.clone());
                if let Some(d) = buckets.get_mut(&area) {
                    d.layouts.push(stem);
                }
            }
        }

        let mut areas: Vec<String> = buckets
            .into_iter()
            .filter(|(_, d)| d.asset_count() > 0)
            .map(|(area, d)| {
                self.dossiers.insert(area.clone(), d);
                area
            })
            .collect();
        areas.sort_by_key(|a| sort_key(a));
        self.areas = areas;
        self.names = std::fs::read_to_string(dirs.root.join("game_assets").join("maps").join("area_names.json"))
            .ok()
            .and_then(|text| serde_json::from_str(&text).ok())
            .unwrap_or_default();
        self.ready = true;
    }

    /// In-game name of an area: exact code first (`p206`), then its group
    /// (`b001_101a` -> `b001`).
    pub fn display_name(&self, area: &str) -> Option<&str> {
        let area = area.to_lowercase();
        self.names
            .get(&area)
            .or_else(|| area.split('_').next().and_then(|group| self.names.get(group)))
            .map(|s| s.as_str())
    }

    pub fn dossier(&self, area: &str) -> AreaDossier {
        self.dossiers
            .get(area)
            .cloned()
            .unwrap_or_else(|| AreaDossier {
                area: area.to_string(),
                ..Default::default()
            })
    }

    /// Dialogue counts referencing one area (called lazily by the UI).
    pub fn refresh_dialogues(&self, dialogues: &mut DialogueDb, dossier: &mut AreaDossier) {
        if dossier.dialogue_total > 0 {
            return;
        }
        let area = dossier.area.clone();
        let total = dialogues.count_sources("", Some(&area), None, None);
        dossier.dialogue_total = total;
        let prefix = area.split('_').next().unwrap_or(&area).to_string();
        let mut files: Vec<(String, usize)> = dialogues
            .stats()
            .by_file
            .into_iter()
            .filter(|(file, _)| file.to_lowercase().contains(&prefix))
            .collect();
        files.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
        files.truncate(40);
        dossier.dialogue_files = files;
    }
}

pub fn model_path(dirs: &Dirs, name: &str) -> Option<PathBuf> {
    let direct = dirs.models.join("by_category");
    if !direct.exists() {
        return None;
    }
    for category in std::fs::read_dir(&direct).ok()?.flatten() {
        let candidate = category.path().join(name);
        if candidate.join(format!("{name}.obj")).exists() {
            return Some(candidate);
        }
    }
    None
}
