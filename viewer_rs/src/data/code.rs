//! Decompiled code index (`decomp/functions_index.json`) plus source trees.

use std::collections::HashMap;
use std::path::PathBuf;

use super::{file_size, rel_string, walk_ext};
use crate::utils::{read_text, Dirs};

#[derive(Clone)]
pub struct Function {
    pub address: u32,
    pub name: String,
    pub size: u32,
    pub mode: String,
    pub file: PathBuf,
    pub status: String,
}

impl Function {
    pub fn addr_hex(&self) -> String {
        format!("0x{:08X}", self.address)
    }
    pub fn end(&self) -> u32 {
        self.address + self.size.max(1)
    }
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
        self.ready = true;
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
                });
            }
        }
        functions.sort_by_key(|f| f.address);
        self.addresses = functions.iter().map(|f| f.address).collect();
        self.total_discovered = functions.len();
        self.decompiled_count = functions.iter().filter(|f| f.status == "ok").count();
        self.functions = functions;
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
                if f.mode != mode {
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
            let mut files = Vec::new();
            for path in walk_ext(dir, &exts) {
                files.push((rel_string(&path, &dirs.root), path.clone(), file_size(&path)));
            }
            groups.push((label.to_string(), files));
        }
        self.groups = groups;
        self.groups_ready = true;
        &self.groups
    }
}
