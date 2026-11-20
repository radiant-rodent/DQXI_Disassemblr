//! Game versions (`versions/`, managed by `tools/game_version.py`): the retail game or a
//! patched one such as the English translation. Switching swaps the changed files on disk;
//! the editor only reads which version is active and what its patch changed in the code.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde_json::Value;

#[derive(Clone, Debug, Default)]
pub struct VersionInfo {
    pub name: String,
    pub label: String,
    pub installed: bool,
    /// the patch file changed since it was imported (`import <name>` again)
    pub outdated: bool,
    pub summary: String,
}

#[derive(Clone, Debug, Default)]
pub struct GameVersions {
    pub active: String,
    pub unfinished: Option<String>,
    pub list: Vec<VersionInfo>,
}

fn load(path: &Path) -> Option<Value> {
    let text = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&text).ok()
}

/// (size, mtime in whole seconds) of the patch file, recorded by the import as source_stamp
fn stamp(path: &Path) -> Option<(u64, u64)> {
    let m = std::fs::metadata(path).ok()?;
    let t = m.modified().ok()?.duration_since(std::time::UNIX_EPOCH).ok()?.as_secs();
    Some((m.len(), t))
}

impl GameVersions {
    pub fn read(root: &Path) -> Self {
        let dir = root.join("versions");
        let state = load(&dir.join("active.json")).unwrap_or(Value::Null);
        let active = std::env::var("DQXI_GAME_VERSION")
            .ok()
            .filter(|v| !v.is_empty())
            .or_else(|| state["active"].as_str().map(str::to_owned))
            .unwrap_or_else(|| "original".into());
        let mut list = vec![VersionInfo {
            name: "original".into(),
            label: "Original (retail Japanese)".into(),
            installed: true,
            outdated: false,
            summary: "the retail cartridge".into(),
        }];
        if let Ok(entries) = std::fs::read_dir(&dir) {
            let mut names: Vec<PathBuf> = entries.flatten().map(|e| e.path()).collect();
            names.sort();
            for path in names {
                let Some(m) = load(&path.join("version.json")) else { continue };
                let name = m["name"].as_str().unwrap_or_default().to_string();
                if name.is_empty() || name == "original" {
                    continue;
                }
                let code = &m["code"];
                let summary = format!(
                    "{} RomFS files, {} functions + {} code caves changed, imported {}",
                    m["romfs_changed"].as_array().map(|a| a.len()).unwrap_or(0),
                    code["functions"].as_u64().unwrap_or(0),
                    code["caves"].as_u64().unwrap_or(0),
                    m["imported_at"].as_str().unwrap_or("?")
                );
                let src = PathBuf::from(m["source"]["path"].as_str().unwrap_or_default());
                let recorded = (m["source"]["source_size"].as_u64(), m["source"]["source_mtime"].as_u64());
                let outdated = match (recorded, stamp(&src)) {
                    ((Some(size), Some(mtime)), Some((now_size, now_mtime))) => {
                        size != now_size || mtime != now_mtime
                    }
                    _ => false,
                };
                list.push(VersionInfo {
                    label: m["label"].as_str().unwrap_or(&name).to_string(),
                    name,
                    installed: true,
                    outdated,
                    summary,
                });
            }
        }
        // configured but not imported yet (versions/sources.json or the built-in English one)
        let mut sources = load(&dir.join("sources.json")).unwrap_or(Value::Null);
        if sources.get("en").is_none() {
            sources = serde_json::json!({"en": {"label": "English translation"}});
        }
        if let Some(obj) = sources.as_object() {
            for (name, cfg) in obj {
                if list.iter().any(|v| &v.name == name) {
                    continue;
                }
                list.push(VersionInfo {
                    name: name.clone(),
                    label: cfg["label"].as_str().unwrap_or(name).to_string(),
                    installed: false,
                    outdated: false,
                    summary: "not imported yet".into(),
                });
            }
        }
        GameVersions {
            active,
            unfinished: state["switching_to"].as_str().map(str::to_owned),
            list,
        }
    }

    pub fn label(&self, name: &str) -> String {
        self.list
            .iter()
            .find(|v| v.name == name)
            .map(|v| v.label.clone())
            .unwrap_or_else(|| name.to_string())
    }

    pub fn active_label(&self) -> String {
        self.label(&self.active)
    }

    pub fn is_patched(&self) -> bool {
        self.active != "original"
    }
}

/// What the active version's patch did to one function or code cave.
#[derive(Clone, Debug, Default)]
pub struct CodePatch {
    /// "modified", "hook" (branches into a code cave) or "cave" (code the patch added)
    pub kind: String,
    pub changed_bytes: u32,
    pub notes: Vec<String>,
    pub links: Vec<String>,
    pub original: Vec<String>,
    pub patched: Vec<String>,
}

#[derive(Clone, Debug, Default)]
pub struct CodeChanges {
    pub version: String,
    pub by_address: HashMap<u32, CodePatch>,
    /// code caves: (address, size, name, mode)
    pub caves: Vec<(u32, u32, String, String)>,
    pub data_runs: usize,
}

fn strings(v: &Value) -> Vec<String> {
    v.as_array()
        .map(|a| a.iter().filter_map(|s| s.as_str().map(str::to_owned)).collect())
        .unwrap_or_default()
}

impl CodeChanges {
    pub fn read(root: &Path, version: &str) -> Self {
        let mut out = CodeChanges { version: version.to_string(), ..Default::default() };
        if version == "original" {
            return out;
        }
        let Some(doc) = load(&root.join("versions").join(version).join("code_changes.json")) else {
            return out;
        };
        for f in doc["functions"].as_array().into_iter().flatten() {
            let Some(addr) = f["address"].as_u64() else { continue };
            let links = f["hooks"]
                .as_array()
                .into_iter()
                .flatten()
                .map(|h| {
                    format!(
                        "0x{:08X} branches to {} (0x{:08X})",
                        h["at"].as_u64().unwrap_or(0),
                        h["cave"].as_str().unwrap_or("?"),
                        h["target"].as_u64().unwrap_or(0)
                    )
                })
                .collect();
            out.by_address.insert(
                addr as u32,
                CodePatch {
                    kind: f["kind"].as_str().unwrap_or("modified").to_string(),
                    changed_bytes: f["changed_bytes"].as_u64().unwrap_or(0) as u32,
                    notes: strings(&f["notes"]),
                    links,
                    original: strings(&f["original"]),
                    patched: strings(&f["patched"]),
                },
            );
        }
        for c in doc["caves"].as_array().into_iter().flatten() {
            let Some(addr) = c["address"].as_u64() else { continue };
            let size = c["size"].as_u64().unwrap_or(0) as u32;
            let name = c["name"].as_str().unwrap_or("EN_cave").to_string();
            let mode = c["mode"].as_str().unwrap_or("arm").to_string();
            let links = c["called_from"]
                .as_array()
                .into_iter()
                .flatten()
                .map(|h| {
                    format!(
                        "called from {} at 0x{:08X}",
                        h["function"].as_str().unwrap_or("?"),
                        h["at"].as_u64().unwrap_or(0)
                    )
                })
                .collect();
            out.caves.push((addr as u32, size, name, mode));
            out.by_address.insert(
                addr as u32,
                CodePatch {
                    kind: "cave".into(),
                    changed_bytes: size,
                    notes: strings(&c["notes"]),
                    links,
                    original: Vec::new(),
                    patched: strings(&c["patched"]),
                },
            );
        }
        out.data_runs = doc["data"].as_array().map(|a| a.len()).unwrap_or(0);
        out
    }
}
