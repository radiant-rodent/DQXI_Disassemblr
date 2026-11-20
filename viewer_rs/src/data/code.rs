//! Decompiled code index (`decomp/functions_index.json`) plus source trees.

use std::collections::HashMap;
use std::path::PathBuf;

use super::{file_size, rel_string, walk_ext};
use crate::data::versions::{CodeChanges, GameVersions};
use crate::utils::{read_text, Dirs};

#[derive(Clone)]
pub struct Function {
    pub address: u32,
    pub name: String,
    pub size: u32,
    pub mode: String,
    pub file: PathBuf,
    pub status: String,
    /// what the active game version's patch did here ("modified", "hook", "cave"), if anything
    pub patch: Option<String>,
}

impl Function {
    pub fn addr_hex(&self) -> String {
        format!("0x{:08X}", self.address)
    }
    pub fn end(&self) -> u32 {
        self.address + self.size.max(1)
    }
}

/// Files under `dir` with the given extensions, as (path relative to `root`, path, size), sorted.
/// Takes the file type and size from the directory entry itself - on Windows that costs no extra
/// stat per file, which is what made a 56,000-file scan take ten seconds.
fn walk_sized(dir: &std::path::Path, root: &std::path::Path, exts: &[&str]) -> Vec<(String, PathBuf, u64)> {
    let mut out = Vec::new();
    let mut stack = vec![dir.to_path_buf()];
    while let Some(current) = stack.pop() {
        let Ok(entries) = std::fs::read_dir(&current) else { continue };
        for entry in entries.flatten() {
            let Ok(kind) = entry.file_type() else { continue };
            let path = entry.path();
            if kind.is_dir() {
                stack.push(path);
            } else if path
                .extension()
                .and_then(|e| e.to_str())
                .is_some_and(|ext| exts.iter().any(|e| e.eq_ignore_ascii_case(ext)))
            {
                let size = entry.metadata().map(|m| m.len()).unwrap_or(0);
                out.push((rel_string(&path, root), path, size));
            }
        }
    }
    out.sort_by(|a, b| a.1.cmp(&b.1));
    out
}

#[derive(Default)]
pub struct CodeIndex {
    pub functions: Vec<Function>,
    pub total_discovered: usize,
    pub decompiled_count: usize,
    pub ready: bool,
    addresses: Vec<u32>,
    cache: HashMap<PathBuf, String>,
    groups: Vec<(String, Vec<(String, PathBuf, u64)>)>,
    groups_ready: bool,
    /// the active game version's code patch (empty for the retail game)
    pub changes: CodeChanges,
    pub version_label: String,
}

pub fn parse_addr(text: &str) -> Option<u32> {
    let t = text.trim().trim_start_matches("0x").trim_start_matches('#').trim_start_matches('$');
    if t.len() < 4 || !t.chars().all(|c| c.is_ascii_hexdigit()) {
        return None;
    }
    u32::from_str_radix(t, 16).ok()
}

impl CodeIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        let modern = dirs.decomp.join("ghidra").join("functions_merged.jsonl");
        let modern = if modern.is_file() {
            modern
        } else {
            dirs.decomp.join("ghidra").join("functions.jsonl")
        };
        if modern.is_file() {
            self.ensure_ghidra(dirs, &modern);
            return;
        }
        let index = dirs.decomp.join("functions_index.json");
        let mut functions = Vec::new();
        if let Some(value) = super::load_json(&index) {
            self.total_discovered = value.get("total_discovered").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
            self.decompiled_count = value.get("decompiled_count").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
            if let Some(items) = value.get("functions").and_then(|v| v.as_array()) {
                for raw in items {
                    let address = raw
                        .get("address")
                        .and_then(|v| v.as_str())
                        .and_then(parse_addr)
                        .or_else(|| raw.get("address").and_then(|v| v.as_u64()).map(|v| v as u32));
                    let Some(address) = address else { continue };
                    let name = raw
                        .get("name")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string())
                        .unwrap_or_else(|| format!("func_{address:08X}"));
                    let rel = raw
                        .get("file")
                        .or_else(|| raw.get("source"))
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    functions.push(Function {
                        address,
                        name,
                        size: raw.get("size").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
                        mode: raw
                            .get("mode")
                            .and_then(|v| v.as_str())
                            .unwrap_or("arm")
                            .to_string(),
                        file: if rel.is_empty() { PathBuf::new() } else { dirs.root.join(rel) },
                        status: "ok".to_string(),
                        patch: None,
                    });
                }
            }
            functions.sort_by_key(|f| f.address);
        }
        self.addresses = functions.iter().map(|f| f.address).collect();
        if self.decompiled_count == 0 {
            self.decompiled_count = functions.len();
        }
        if self.total_discovered == 0 {
            self.total_discovered = functions.len();
        }
        self.functions = functions;
        self.apply_version(dirs);
        self.ready = true;
    }

    /// Marks the functions the active game version's patch changed and adds its code caves.
    fn apply_version(&mut self, dirs: &Dirs) {
        let versions = GameVersions::read(&dirs.root);
        self.version_label = versions.active_label();
        self.changes = CodeChanges::read(&dirs.root, &versions.active);
        if self.changes.by_address.is_empty() {
            return;
        }
        for f in &mut self.functions {
            if let Some(p) = self.changes.by_address.get(&f.address) {
                f.patch = Some(p.kind.clone());
            }
        }
        for (address, size, name, mode) in self.changes.caves.clone() {
            if self.functions.iter().any(|f| f.address == address) {
                continue;
            }
            self.functions.push(Function {
                address,
                name,
                size,
                mode,
                file: PathBuf::new(),
                status: "cave".into(),
                patch: Some("cave".into()),
            });
        }
        self.functions.sort_by_key(|f| f.address);
        self.addresses = self.functions.iter().map(|f| f.address).collect();
    }

    pub fn patch_of(&self, index: usize) -> Option<&crate::data::versions::CodePatch> {
        let f = self.functions.get(index)?;
        self.changes.by_address.get(&f.address)
    }

    pub fn patched_count(&self) -> usize {
        self.functions.iter().filter(|f| f.patch.is_some()).count()
    }

    fn ensure_ghidra(&mut self, dirs: &Dirs, path: &std::path::Path) {
        let base = dirs.decomp.join("ghidra");
        let mut functions = Vec::new();
        if let Ok(text) = std::fs::read_to_string(path) {
            for line in text.lines() {
                let Ok(value) = serde_json::from_str::<serde_json::Value>(line) else { continue };
                let address = value
                    .get("address")
                    .and_then(|v| v.as_str())
                    .and_then(parse_addr)
                    .or_else(|| value.get("address").and_then(|v| v.as_u64()).map(|v| v as u32));
                let Some(address) = address else { continue };
                let name = value
                    .get("name")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| format!("func_{address:08X}"));
                let rel = value.get("file").and_then(|v| v.as_str()).unwrap_or("");
                let status = value.get("status").and_then(|v| v.as_str()).unwrap_or("ok");
                functions.push(Function {
                    address,
                    name,
                    size: value.get("size").and_then(|v| v.as_u64()).unwrap_or(0) as u32,
                    mode: value.get("mode").and_then(|v| v.as_str()).unwrap_or("arm").to_string(),
                    file: if rel.is_empty() {
                        PathBuf::new()
                    } else {
                        base.join(rel)
                    },
                    status: status.to_string(),
                    patch: None,
                });
            }
        }
        functions.sort_by_key(|f| f.address);
        self.addresses = functions.iter().map(|f| f.address).collect();
        self.total_discovered = functions.len();
        self.decompiled_count = functions.iter().filter(|f| f.status == "ok").count();
        self.functions = functions;
        self.apply_version(dirs);
        self.ready = true;
    }

    pub fn search(&self, query: &str, mode: Option<&str>, limit: usize) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        if let Some(addr) = parse_addr(query) {
            let idx = match self.addresses.binary_search(&addr) {
                Ok(i) => i,
                Err(i) => i.saturating_sub(1),
            };
            let mut out = Vec::new();
            if let Some(f) = self.functions.get(idx) {
                if addr < f.end() {
                    out.push(idx);
                }
            }
            let from = idx.saturating_sub(12);
            let to = (idx + 40).min(self.functions.len());
            for i in from..to {
                if !out.contains(&i) {
                    out.push(i);
                }
            }
            return out;
        }
        let mut out = Vec::new();
        for (i, f) in self.functions.iter().enumerate() {
            if let Some(mode) = mode {
                if mode == "patched" {
                    if f.patch.is_none() {
                        continue;
                    }
                } else if f.mode != mode {
                    continue;
                }
            }
            if !q.is_empty()
                && !f.name.to_lowercase().contains(&q)
                && !f.addr_hex().to_lowercase().contains(&q)
            {
                continue;
            }
            out.push(i);
            if out.len() >= limit {
                break;
            }
        }
        out
    }

    pub fn text(&mut self, index: usize) -> String {
        let Some(func) = self.functions.get(index) else {
            return String::new();
        };
        let path = func.file.clone();
        if let Some(text) = self.cache.get(&path) {
            return text.clone();
        }
        let text = read_text(&path).unwrap_or_else(|e| format!("// failed to read {path:?}: {e}"));
        if self.cache.len() > 12 {
            self.cache.clear();
        }
        self.cache.insert(path, text.clone());
        text
    }

    /// Source trees shown in the "Sources & assembly" tab.
    pub fn source_groups(&mut self, dirs: &Dirs) -> &[(String, Vec<(String, PathBuf, u64)>)] {
        if self.groups_ready {
            return &self.groups;
        }
        let mut groups = Vec::new();
        let ghidra_dir = dirs.decomp.join("ghidra");
        let readable_dir = dirs.decomp.join("readable");
        for (label, dir, exts) in [
            ("Readable C (decomp/readable/)", &readable_dir, vec!["c"]),
            ("Ghidra C (decomp/ghidra/)", &ghidra_dir, vec!["c", "h"]),
            ("Lifted C (src/)", &dirs.src, vec!["c", "h"]),
            ("Headers (include/)", &dirs.root.join("include"), vec!["h"]),
            ("Assembly (asm/)", &dirs.asm, vec!["s"]),
            ("Tools (tools/)", &dirs.root.join("tools"), vec!["py", "md"]),
        ] {
            groups.push((label.to_string(), walk_sized(dir, &dirs.root, &exts)));
        }
        self.groups = groups;
        self.groups_ready = true;
        &self.groups
    }
}
