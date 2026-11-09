//! Squirrel script index (`game_assets/scripts/packs/script/<area>/script.nut`), the read-only
//! `script.decompiled.nut` pseudo-source beside it, and the generated
//! `game_assets/scripts/script_index.json` (function list, native calls, callers).
//!
//! The `.nut` file the game ships is a disassembly listing; `script.decompiled.nut`
//! is the readable form written by `tools/squirrel_decompile.py`. Both are
//! editable in DQXI Studio and both are built back to `script.cnut` by
//! `tools/script_build.py`.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use serde::Deserialize;

use super::{file_size, walk_ext};
use crate::utils::{read_text, Dirs};

#[derive(Clone)]
pub struct Script {
    /// PACK / area name, e.g. `a_010` or `a_010_cs_050x`.
    pub area: String,
    /// The editable disassembly listing (`script.nut`).
    pub path: PathBuf,
    pub size: u64,
}

impl Script {
    /// Tree group: cutscene packs sit under their chapter (`a_010_cs_050x` -> `a_010`).
    pub fn group(&self) -> &str {
        group_of(&self.area)
    }

    /// The readable pseudo-source, when `tools/squirrel_decompile.py --all` ran.
    pub fn source_path(&self) -> Option<PathBuf> {
        decompiled_path(&self.path)
    }
}

/// Tree grouping: `a_010_cs_050x` belongs to `a_010`; a plain area is its own group.
pub fn group_of(area: &str) -> &str {
    area.split_once("_cs_").map(|(g, _)| g).unwrap_or(area)
}

// ---------------------------------------------------------------------------
// script_index.json (written by `python tools/script_build.py index`)
// ---------------------------------------------------------------------------

#[derive(Clone, Default, Debug, Deserialize)]
#[serde(default)]
pub struct NativeInfo {
    pub address: String,
    pub summary: String,
    pub documented_as: String,
}

#[derive(Clone, Default, Debug, Deserialize)]
#[serde(default)]
pub struct FuncMeta {
    pub name: String,
    pub params: String,
    pub line: usize,
}

#[derive(Clone, Default, Debug, Deserialize)]
#[serde(default)]
pub struct AreaMeta {
    pub lines: usize,
    pub functions: Vec<FuncMeta>,
    pub natives: Vec<String>,
    pub pack: String,
    pub category: String,
    pub title: String,
    pub description: String,
    pub source: String,
}

impl AreaMeta {
    /// Human-readable name (`Cobblestone_Prologue_Departure`) or the raw area name.
    pub fn display(&self) -> &str {
        if self.title.is_empty() {
            ""
        } else {
            &self.title
        }
    }
}

#[derive(Clone, Default, Debug, Deserialize)]
#[serde(default)]
pub struct Xref {
    pub script: String,
    pub caller: String,
}

#[derive(Clone, Default, Debug, Deserialize)]
#[serde(default)]
pub struct XrefInfo {
    pub count: usize,
    pub defined_in: usize,
    pub callers: Vec<Xref>,
}

#[derive(Clone, Default, Debug, Deserialize)]
#[serde(default)]
pub struct ScriptMeta {
    pub generated: String,
    pub areas: usize,
    pub functions: usize,
    pub natives: HashMap<String, NativeInfo>,
    pub scripts: HashMap<String, AreaMeta>,
    pub xrefs: HashMap<String, XrefInfo>,
}

impl ScriptMeta {
    pub fn load(path: &Path) -> Option<Self> {
        let text = std::fs::read_to_string(path).ok()?;
        serde_json::from_str(&text).ok()
    }
}

#[derive(Clone, Default)]
pub struct ScriptIndex {
    pub items: Vec<Script>,
    /// True once the directory walk has finished (the metadata may still be absent).
    pub ready: bool,
    pub meta: Option<Arc<ScriptMeta>>,
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
            // Paths are game_assets/scripts/packs/script/<area>/script.nut;
            // the legacy tree is game_scripts/<area>/script.nut. In both cases
            // the PACK name is the parent directory.
            let area = path
                .parent()
                .and_then(|p| p.file_name())
                .map(|c| c.to_string_lossy().into_owned())
                .unwrap_or_default();
            if area.is_empty() {
                continue;
            }
            items.push(Script {
                area,
                size: file_size(&path),
                path,
            });
        }
        items.sort_by(|a, b| a.area.cmp(&b.area));
        self.items = items;
        self.meta = ScriptMeta::load(&dirs.scripts.join("script_index.json")).map(Arc::new);
        self.ready = true;
    }

    pub fn meta(&self) -> Option<&ScriptMeta> {
        self.meta.as_deref()
    }

    pub fn area_meta(&self, area: &str) -> Option<&AreaMeta> {
        self.meta.as_ref()?.scripts.get(area)
    }

    pub fn native(&self, name: &str) -> Option<&NativeInfo> {
        self.meta.as_ref()?.natives.get(name)
    }

    pub fn xrefs(&self, name: &str) -> Option<&XrefInfo> {
        self.meta.as_ref()?.xrefs.get(name)
    }

    pub fn search(&self, query: &str) -> Vec<usize> {
        let q = query.trim().to_lowercase();
        self.items
            .iter()
            .enumerate()
            .filter(|(_, s)| {
                if q.is_empty() {
                    return true;
                }
                if s.area.to_lowercase().contains(&q) {
                    return true;
                }
                // The generated index carries the human title/category/description;
                // searching "Cobblestone" should find a_010, not only the raw id.
                match self.area_meta(&s.area) {
                    Some(meta) => {
                        meta.title.to_lowercase().contains(&q)
                            || meta.category.to_lowercase().contains(&q)
                            || meta.description.to_lowercase().contains(&q)
                    }
                    None => false,
                }
            })
            .map(|(i, _)| i)
            .collect()
    }

    /// Group the filtered list for the tree: `(chapter, [indices])`.
    pub fn groups(&self, list: &[usize]) -> Vec<(String, Vec<usize>)> {
        let mut order: Vec<String> = Vec::new();
        let mut map: HashMap<String, Vec<usize>> = HashMap::new();
        for &index in list {
            let Some(script) = self.items.get(index) else { continue };
            let group = script.group().to_string();
            if !map.contains_key(&group) {
                order.push(group.clone());
            }
            map.entry(group).or_default().push(index);
        }
        order
            .into_iter()
            .filter_map(|group| map.remove(&group).map(|items| (group, items)))
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

    /// Re-read a file after an edit was discarded (Revert).
    pub fn forget(&mut self, path: &Path) {
        self.cache.remove(path);
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

/// Call sites of `target` inside one decompiled file: `(line, caller)`.
///
/// The caller is the innermost `function Name(...)` whose braces contain the
/// call. This is what the editor shows as "called by" for the selected
/// function; the generated index only has a sample of cross-area callers.
pub fn local_callers(text: &str, target: &str) -> Vec<(usize, String)> {
    let needle = format!("{target}(");
    let mut out = Vec::new();
    let mut stack: Vec<(String, i32)> = Vec::new();
    let mut depth = 0i32;
    let mut current = String::from("<top>");
    for (index, raw) in text.lines().enumerate() {
        let line = raw.split("//").next().unwrap_or("");
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("function ") {
            if let Some((name, _)) = rest.split_once('(') {
                let name = name.trim();
                if !name.is_empty() {
                    stack.push((current.clone(), depth));
                    current = name.to_string();
                }
            }
        }
        // A call is `target(` not preceded by an identifier character and not
        // the declaration we just opened.
        let mut from = 0usize;
        while let Some(at) = line[from..].find(&needle) {
            let at = from + at;
            let before = line[..at].chars().last();
            let is_decl = stack.last().is_some() && current == target && at < 64;
            if !before.is_some_and(|c| c.is_alphanumeric() || c == '_' || c == '.') && !is_decl {
                out.push((index + 1, current.clone()));
                break;
            }
            from = at + needle.len();
        }
        depth += line.matches('{').count() as i32 - line.matches('}').count() as i32;
        while let Some((previous, entry_depth)) = stack.last() {
            if depth > *entry_depth {
                break;
            }
            current = previous.clone();
            stack.pop();
        }
    }
    out
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

/// Original compiled script for an area (`game_data/packs/script/<area>/script.cnut`).
pub fn original_cnut(root: &Path, area: &str) -> PathBuf {
    root.join("game_data")
        .join("packs")
        .join("script")
        .join(area)
        .join("script.cnut")
}

/// RomFS pack that holds an area (`script/<area>.pack`).
pub fn pack_path(area: &str) -> String {
    format!("script/{area}.pack")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cutscene_packs_group_under_their_chapter() {
        assert_eq!(group_of("a_010_cs_050x"), "a_010");
        assert_eq!(group_of("a_010"), "a_010");
        assert_eq!(group_of("common"), "common");
    }

    #[test]
    fn local_callers_finds_the_innermost_function() {
        let text = r#"function A(this) {
    f();
    function B(this) {
        g(1);
    }
}
function C(this) {
    A(this);
}
"#;
        assert_eq!(local_callers(text, "A"), vec![(8, "C".to_string())]);
        assert_eq!(local_callers(text, "g"), vec![(4, "B".to_string())]);
    }

    #[test]
    fn search_matches_area_and_human_title() {
        let mut index = ScriptIndex::default();
        index.items = vec![
            Script { area: "a_010".into(), path: PathBuf::from("a_010/script.nut"), size: 1 },
            Script { area: "b001".into(), path: PathBuf::from("b001/script.nut"), size: 1 },
        ];
        let mut scripts = std::collections::HashMap::new();
        scripts.insert(
            "a_010".to_string(),
            AreaMeta {
                title: "Cobblestone_Prologue_Departure".into(),
                category: "Scenarios".into(),
                ..Default::default()
            },
        );
        index.meta = Some(Arc::new(ScriptMeta { scripts, ..Default::default() }));
        assert_eq!(index.search("a_010"), vec![0]);
        assert_eq!(index.search("cobblestone"), vec![0]);
        assert_eq!(index.search("scenarios"), vec![0]);
        assert_eq!(index.search("b001"), vec![1]);
        assert_eq!(index.search("nothing-here").len(), 0);
    }

    #[test]
    fn meta_parses_a_native_and_an_xref() {        let meta: ScriptMeta = serde_json::from_str(
            r#"{
                "generated": "now",
                "natives": {"RegistThread": {"address": "0x0014A778", "summary": "thread registry"}},
                "scripts": {"a_010": {"lines": 10, "functions": [{"name": "StartEvent", "params": "func", "line": 3}], "natives": ["RegistThread"]}},
                "xrefs": {"StartEvent": {"count": 2, "defined_in": 1, "callers": [{"script": "a_010", "caller": "OnBeginScene"}]}}
            }"#,
        )
        .expect("meta");
        assert_eq!(meta.natives["RegistThread"].address, "0x0014A778");
        assert_eq!(meta.scripts["a_010"].functions[0].name, "StartEvent");
        assert_eq!(meta.xrefs["StartEvent"].callers[0].caller, "OnBeginScene");
    }
}
