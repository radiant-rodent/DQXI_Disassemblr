//! Audio index: WAV streams + extracted BCSAR archives.

use std::path::PathBuf;

use super::{file_size, load_json, walk_dirs, walk_ext};
use crate::utils::{read_wav_info, Dirs, WavInfo};

#[derive(Clone)]
pub struct Stream {
    pub name: String,
    pub rel: String,
    pub path: PathBuf,
    pub size: u64,
    pub kind: String,
    pub duration: f32,
    pub rate: u32,
    pub channels: u16,
    pub frames: u32,
}

impl Stream {
    pub fn info(&self) -> WavInfo {
        WavInfo {
            channels: self.channels,
            rate: self.rate,
            frames: self.frames,
            width: 16,
            data_offset: 0,
            data_len: 0,
        }
    }

    pub fn duration_text(&self) -> String {
        if self.frames == 0 || self.rate == 0 {
            return "--:--".into();
        }
        let total = self.duration.floor() as u32;
        if total >= 3600 {
            format!("{}:{:02}:{:02}", total / 3600, (total / 60) % 60, total % 60)
        } else {
            format!("{}:{:02}", total / 60, total % 60)
        }
    }
}

#[derive(Clone)]
pub struct Archive {
    pub name: String,
    pub path: PathBuf,
    pub manifest: serde_json::Value,
    pub sections: Vec<(String, u64)>,
    pub total_bytes: u64,
}

#[derive(Clone, Default)]
pub struct AudioIndex {
    pub streams: Vec<Stream>,
    pub archives: Vec<Archive>,
    pub ready: bool,
}

impl AudioIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let streams_dir = dirs.audio.join("streams");
        let scan_dir = if streams_dir.exists() { streams_dir } else { dirs.audio.clone() };
        let mut streams: Vec<Stream> = Vec::new();
        if scan_dir.exists() {
            for wav in walk_ext(&scan_dir, &["wav"]) {
                let stem = wav.file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default();
                let stem = stem.strip_suffix(".dspadpcm").unwrap_or(&stem).to_string();
                let norm = wav.to_string_lossy().replace('\\', "/");
                let kind = if norm.contains("/sound/str/BGM_") || norm.contains("/music/") {
                    "OST"
                } else if norm.contains("/sound/str/ME") || norm.contains("/jingles/") {
                    "Jingle"
                } else if norm.contains("/streams/") {
                    "Stream"
                } else {
                    "Voice/SFX"
                };
                let info = read_wav_info(&wav).unwrap_or_default();
                streams.push(Stream {
                    name: stem,
                    rel: norm,
                    size: file_size(&wav),
                    path: wav,
                    kind: kind.to_string(),
                    duration: info.duration(),
                    rate: info.rate,
                    channels: info.channels,
                    frames: info.frames,
                });
            }
            streams.sort_by(|a, b| a.kind.cmp(&b.kind).then(a.name.to_lowercase().cmp(&b.name.to_lowercase())));
        }

        let mut archives = Vec::new();
        let arch_dir = if dirs.audio.join("archives").exists() {
            dirs.audio.join("archives")
        } else {
            dirs.root.join("game_audio/archives")
        };
        if arch_dir.exists() {
            for proj in walk_dirs(&arch_dir) {
                let name = proj.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default();
                let manifest = load_json(&proj.join("manifest.json")).unwrap_or(serde_json::Value::Null);
                let mut sections = Vec::new();
                let mut total = 0;
                if let Ok(entries) = std::fs::read_dir(&proj) {
                    for entry in entries.flatten() {
                        let path = entry.path();
                        if !path.is_file() || path.file_name().map(|n| n == "manifest.json").unwrap_or(false) {
                            continue;
                        }
                        let size = file_size(&path);
                        sections.push((
                            path.file_name().map(|n| n.to_string_lossy().into_owned()).unwrap_or_default(),
                            size,
                        ));
                        total += size;
                    }
                }
                sections.sort_by(|a, b| a.0.cmp(&b.0));
                archives.push(Archive {
                    name,
                    path: proj,
                    manifest,
                    sections,
                    total_bytes: total,
                });
            }
            archives.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
        }

        self.streams = streams;
        self.archives = archives;
        self.ready = true;
    }

    pub fn search_streams(&self, query: &str, kind: Option<&str>) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        self.streams
            .iter()
            .enumerate()
            .filter(|(_, s)| {
                kind.map(|k| s.kind == k).unwrap_or(true)
                    && (q.is_empty() || s.name.to_lowercase().contains(&q) || s.rel.to_lowercase().contains(&q))
            })
            .map(|(i, _)| i)
            .collect()
    }

    pub fn kind_count(&self, kind: &str) -> usize {
        self.streams.iter().filter(|s| s.kind == kind).count()
    }
}
