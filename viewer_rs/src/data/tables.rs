//! Parameter tables: the structural index of `game_assets/tables/**`, the field
//! schemas from `tools/table_schemas.json`, and an editable BXON document.
//!
//! Two layers live here:
//!
//! * [`TableIndex`] - which tables exist, grouped by RomFS pack. The `Structure`,
//!   `Raw JSON` and `Summary` tabs read the converted JSON through it.
//! * [`TableDoc`] - one table opened for editing. It holds the *original BXON
//!   bytes* (from `game_data/packs`) and writes scalar fields straight into
//!   them, so a saved table keeps its length and the game file stays valid.
//!
//! The BXON layout is not guessed per field: the root array's element count and
//! stride come from the file header, and every named field is an offset inside
//! a row. Sub-word fields (`u8`, `u16`) are read out of the containing 32-bit
//! word, which is why any byte offset works.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use super::{file_size, walk_ext};
use crate::utils::Dirs;

/// Block delimiter between allocations in a BXON file.
const MARK: &[u8] = b"&&&&";

// ---------------------------------------------------------------------------
// schema
// ---------------------------------------------------------------------------
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FieldType {
    U8,
    U16,
    U32,
    S32,
    F32,
    Text,
}

impl FieldType {
    pub fn parse(text: &str) -> FieldType {
        match text {
            "u8" => FieldType::U8,
            "u16" => FieldType::U16,
            "u32" => FieldType::U32,
            "s32" => FieldType::S32,
            "f32" => FieldType::F32,
            _ => FieldType::Text,
        }
    }

    pub fn width(self) -> usize {
        match self {
            FieldType::U8 => 1,
            FieldType::U16 => 2,
            FieldType::U32 | FieldType::S32 | FieldType::F32 | FieldType::Text => 4,
        }
    }

    pub fn name(self) -> &'static str {
        match self {
            FieldType::U8 => "u8",
            FieldType::U16 => "u16",
            FieldType::U32 => "u32",
            FieldType::S32 => "s32",
            FieldType::F32 => "f32",
            FieldType::Text => "text",
        }
    }

    pub fn is_text(self) -> bool {
        self == FieldType::Text
    }
}

/// Where a field's value comes from, for the "id - name" dropdowns.
#[derive(Clone, Debug)]
pub struct Reference {
    pub table: String,
    pub field: String,
}

#[derive(Clone, Debug)]
pub struct Field {
    pub name: String,
    pub offset: usize,
    pub ty: FieldType,
    pub read_only: bool,
    /// Accepted range, from the schema. `f32` fields use the float bounds.
    pub range: Option<(f64, f64)>,
    pub labels: Vec<(i64, String)>,
    pub reference: Option<Reference>,
    pub confidence: String,
    pub why: String,
}

#[derive(Clone, Debug, Default)]
pub struct Schema {
    pub title: String,
    pub category: String,
    pub type_name: String,
    pub row_size: usize,
    pub pack: String,
    pub label: Option<String>,
    pub id: Option<String>,
    pub note: String,
    pub fields: Vec<Field>,
}

impl Schema {
    pub fn field(&self, name: &str) -> Option<&Field> {
        self.fields.iter().find(|f| f.name == name)
    }

    fn from_json(value: &serde_json::Value) -> Option<Schema> {
        let map = value.as_object()?;
        let text = |key: &str| {
            map.get(key)
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string()
        };
        let mut fields = Vec::new();
        for entry in map.get("fields")?.as_array()? {
            let count = entry
                .get("count")
                .and_then(|v| v.as_u64())
                .unwrap_or(1)
                .max(1) as usize;
            let name = entry.get("name")?.as_str()?.to_string();
            let ty = FieldType::parse(entry.get("type")?.as_str()?);
            let offset = entry.get("offset")?.as_u64()? as usize;
            let range = entry.get("range").and_then(|v| v.as_array()).and_then(|a| {
                Some((
                    a.first()?.as_f64()?,
                    a.get(1)?.as_f64()?,
                ))
            });
            let labels = entry
                .get("enum")
                .and_then(|v| v.as_object())
                .map(|o| {
                    let mut pairs: Vec<(i64, String)> = o
                        .iter()
                        .filter_map(|(k, v)| Some((k.parse().ok()?, v.as_str()?.to_string())))
                        .collect();
                    pairs.sort_by_key(|(k, _)| *k);
                    pairs
                })
                .unwrap_or_default();
            let reference = entry.get("ref").and_then(|v| {
                Some(Reference {
                    table: v.get("table")?.as_str()?.to_string(),
                    field: v
                        .get("field")
                        .and_then(|f| f.as_str())
                        .unwrap_or("id")
                        .to_string(),
                })
            });
            let read_only = entry
                .get("read_only")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            let confidence = entry
                .get("confidence")
                .and_then(|v| v.as_str())
                .unwrap_or("inferred")
                .to_string();
            let why = entry
                .get("why")
                .and_then(|v| v.as_str())
                .unwrap_or_default()
                .to_string();
            for i in 0..count {
                let field_name = if count == 1 {
                    name.clone()
                } else if ty == FieldType::U8 {
                    format!("{name}_{i:02x}")
                } else {
                    format!("{name}_{:02}", i + 1)
                };
                fields.push(Field {
                    name: field_name,
                    offset: offset + i * ty.width(),
                    ty,
                    read_only,
                    range,
                    labels: labels.clone(),
                    reference: reference.clone(),
                    confidence: confidence.clone(),
                    why: why.clone(),
                });
            }
        }
        fields.sort_by_key(|f| (f.offset, f.ty.width()));
        Some(Schema {
            title: text("title"),
            category: text("category"),
            type_name: text("type"),
            row_size: map.get("row_size").and_then(|v| v.as_u64()).unwrap_or(0) as usize,
            pack: text("pack"),
            label: map.get("label").and_then(|v| v.as_str()).map(str::to_string),
            id: map.get("id").and_then(|v| v.as_str()).map(str::to_string),
            note: text("note"),
            fields,
        })
    }
}

/// `tools/table_schemas.json`: exact table keys plus wildcard patterns (the
/// per-character level curves all share one layout).
#[derive(Clone, Default)]
pub struct SchemaSet {
    exact: HashMap<String, Schema>,
    patterns: Vec<(String, Schema)>,
    pub loaded: bool,
}

impl SchemaSet {
    pub fn load(&mut self, root: &Path) {
        let path = root.join("tools").join("table_schemas.json");
        self.loaded = true;
        let Ok(text) = std::fs::read_to_string(&path) else {
            return;
        };
        let Ok(value) = serde_json::from_str::<serde_json::Value>(&text) else {
            return;
        };
        if let Some(map) = value.get("tables").and_then(|v| v.as_object()) {
            for (key, spec) in map {
                if let Some(schema) = Schema::from_json(spec) {
                    self.exact.insert(key.clone(), schema);
                }
            }
        }
        if let Some(map) = value.get("patterns").and_then(|v| v.as_object()) {
            for (key, spec) in map {
                if let Some(schema) = Schema::from_json(spec) {
                    self.patterns.push((key.clone(), schema));
                }
            }
        }
    }

    pub fn get(&self, rel: &str) -> Option<&Schema> {
        let rel = rel.replace('\\', "/");
        if let Some(schema) = self.exact.get(&rel) {
            return Some(schema);
        }
        self.patterns
            .iter()
            .find(|(pattern, _)| glob_match(pattern, &rel))
            .map(|(_, schema)| schema)
    }

    /// Tables with a hand-written schema - the ones the editor can label.
    pub fn named(&self) -> usize {
        self.exact.len() + self.patterns.len()
    }
}

/// `*` matches any run of characters; used for `syscmn/player_param_*.json`.
pub fn glob_match(pattern: &str, text: &str) -> bool {
    let parts: Vec<&str> = pattern.split('*').collect();
    if parts.len() == 1 {
        return pattern == text;
    }
    let mut rest = text;
    for (i, part) in parts.iter().enumerate() {
        if part.is_empty() {
            continue;
        }
        if i == 0 {
            if !rest.starts_with(part) {
                return false;
            }
            rest = &rest[part.len()..];
        } else if i == parts.len() - 1 {
            return rest.ends_with(part);
        } else if let Some(pos) = rest.find(part) {
            rest = &rest[pos + part.len()..];
        } else {
            return false;
        }
    }
    true
}

// ---------------------------------------------------------------------------
// table index
// ---------------------------------------------------------------------------
#[derive(Clone)]
pub struct Table {
    pub category: String,
    pub name: String,
    /// Path relative to `game_assets/tables/packs`, e.g. `syscmn/item.json`.
    pub rel: String,
    pub path: PathBuf,
    pub size: u64,
}

#[derive(Clone, Default)]
pub struct TableIndex {
    pub items: Vec<Table>,
    pub ready: bool,
    pub schemas: SchemaSet,
    categories: Vec<(String, usize)>,
    cache: HashMap<PathBuf, serde_json::Value>,
    /// id -> label lists for the reference dropdowns, keyed by table path.
    refs: HashMap<String, Vec<(i64, String)>>,
}

impl TableIndex {
    pub fn ensure(&mut self, dirs: &Dirs) {
        if self.ready {
            return;
        }
        self.schemas.load(&dirs.root);
        let root = dirs.tables.clone();
        let base = root.join("packs");
        let mut items = Vec::new();
        for path in walk_ext(&root, &["json"]) {
            let rel = path
                .strip_prefix(&base)
                .unwrap_or(&path)
                .to_string_lossy()
                .replace('\\', "/");
            let category = rel
                .split('/')
                .next()
                .filter(|_| rel.contains('/'))
                .unwrap_or("root")
                .to_string();
            items.push(Table {
                name: path
                    .file_stem()
                    .map(|s| s.to_string_lossy().into_owned())
                    .unwrap_or_default(),
                category,
                rel,
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

    /// How many of the indexed tables have hand-written field names.
    pub fn named_tables(&self) -> usize {
        self.items
            .iter()
            .filter(|t| self.schema_for(&t.rel).is_some())
            .count()
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
                        || t.category.to_lowercase().contains(&q)
                        || t.rel.to_lowercase().contains(&q))
            })
            .map(|(i, _)| i)
            .collect()
    }

    pub fn schema_for(&self, rel: &str) -> Option<&Schema> {
        self.schemas.get(rel)
    }

    pub fn load(&mut self, path: &Path) -> Option<serde_json::Value> {
        if let Some(v) = self.cache.get(path) {
            return Some(v.clone());
        }
        let value = super::load_json(path)?;
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

    /// `(id, label)` pairs for a reference dropdown, decoded once and cached.
    ///
    /// A label is the referenced table's `label` field if it has one, so the
    /// item picker shows real item names instead of raw ids.
    pub fn reference_options(&mut self, dirs: &Dirs, table: &str) -> Vec<(i64, String)> {
        if let Some(hit) = self.refs.get(table) {
            return hit.clone();
        }
        let root = dirs.root.join("game_data").join("packs");
        let path = root.join(table).with_extension("bxon");
        let Some(schema) = self.schemas.get(table).cloned() else {
            return Vec::new();
        };
        let Some(doc) = TableDoc::open_bytes(table.to_string(), &path, None) else {
            return Vec::new();
        };
        // A table with no explicit `id` is keyed by its row index: the monster,
        // shop and encounter tables are addressed that way by the engine, so
        // falling back to "the first numeric column" picked the wrong value
        // (enemy_base.family_id instead of the row id).
        let id_field = schema
            .id
            .as_deref()
            .filter(|name| *name != "__row__")
            .and_then(|n| schema.field(n))
            .cloned();
        let label_field = schema
            .label
            .as_ref()
            .and_then(|n| schema.field(n))
            .cloned();
        let mut out = Vec::new();
        for row in 0..doc.row_count() {
            let id = match &id_field {
                Some(field) => match doc.value(row, field) {
                    Value::Int(v) => v,
                    Value::Float(v) => v as i64,
                    Value::Text(_) => row as i64,
                },
                None => row as i64,
            };
            let label = match &label_field {
                Some(field) => doc.text_value(row, field),
                None => format!("#{row}"),
            };
            out.push((id, label));
        }
        self.refs.insert(table.to_string(), out.clone());
        out
    }
}

// ---------------------------------------------------------------------------
// values
// ---------------------------------------------------------------------------
#[derive(Clone, Debug, PartialEq)]
pub enum Value {
    Int(i64),
    Float(f32),
    Text(String),
}

impl Value {
    pub fn display(&self) -> String {
        match self {
            Value::Int(v) => v.to_string(),
            Value::Float(v) => format!("{v:.4}"),
            Value::Text(t) => t.replace('\n', " "),
        }
    }
}

// ---------------------------------------------------------------------------
// editable document
// ---------------------------------------------------------------------------
/// One reversible byte write: a whole 32-bit word, because `u8`/`u16` fields
/// share it with their neighbours.
#[derive(Clone)]
struct Edit {
    pos: usize,
    old: Vec<u8>,
    new: Vec<u8>,
    /// Bytes appended by a relocated string; undo truncates them, redo re-appends.
    tail: Vec<u8>,
}

pub struct TableDoc {
    pub rel: String,
    pub schema: Option<Schema>,
    pub bytes: Vec<u8>,
    pristine: Vec<u8>,
    rows: Vec<usize>,
    pub row_size: usize,
    labels: Vec<String>,
    undo: Vec<Edit>,
    redo: Vec<Edit>,
    /// Generic columns for tables with no schema (`+0x00`, `+0x04`, ...).
    pub synthetic: Vec<Field>,
    pub error: Option<String>,
}

impl TableDoc {
    /// Open a table's original BXON. `fallback` is used when the file is absent
    /// (the editor shows the error instead of panicking).
    pub fn open(dirs: &Dirs, rel: &str) -> Option<TableDoc> {
        let path = dirs
            .root
            .join("game_data")
            .join("packs")
            .join(rel)
            .with_extension("bxon");
        let mut set = SchemaSet::default();
        set.load(&dirs.root);
        let schema = set.get(rel).cloned();
        TableDoc::open_bytes(rel.to_string(), &path, schema)
    }

    fn open_bytes(rel: String, path: &Path, schema: Option<Schema>) -> Option<TableDoc> {
        let bytes = std::fs::read(path).ok()?;
        let mut doc = TableDoc {
            rel,
            schema,
            pristine: bytes.clone(),
            bytes,
            rows: Vec::new(),
            row_size: 0,
            labels: Vec::new(),
            undo: Vec::new(),
            redo: Vec::new(),
            synthetic: Vec::new(),
            error: None,
        };
        doc.decode_layout();
        Some(doc)
    }

    fn u32_at(&self, pos: usize) -> u32 {
        let mut b = [0u8; 4];
        if pos + 4 <= self.bytes.len() {
            b.copy_from_slice(&self.bytes[pos..pos + 4]);
        }
        u32::from_le_bytes(b)
    }

    /// Reads the root array geometry: element count at 0x20, self-relative
    /// pointer at 0x24, block size from the next `&&&&` marker.
    fn decode_layout(&mut self) {
        if self.bytes.len() < 0x28 || &self.bytes[..4] != b"BXON" {
            self.error = Some("not a BXON file".into());
            return;
        }
        let count = self.u32_at(0x20) as usize;
        let rel = self.u32_at(0x24) as usize;
        let root = (0x24usize).wrapping_add(rel);
        if count == 0 || count > 1_000_000 || root >= self.bytes.len() {
            self.error = Some("this table has no row array (single record)".into());
            return;
        }
        let end = self
            .bytes
            .windows(4)
            .skip(root)
            .position(|w| w == MARK)
            .map(|p| root + p)
            .unwrap_or(self.bytes.len());
        let mut size = (end - root) / count;
        if size == 0 || root + size * count != end {
            // A trailing oddment still divides into equal rows in practice; fall
            // back to the schema's declared row size when it agrees.
            if let Some(schema) = &self.schema {
                if schema.row_size > 0 && root + schema.row_size * count <= end {
                    size = schema.row_size;
                }
            }
        }
        if size == 0 {
            self.error = Some("cannot work out the row size".into());
            return;
        }
        self.row_size = size;
        self.rows = (0..count).map(|i| root + i * size).collect();
        self.build_synthetic();
        self.labels = (0..self.rows.len()).map(|r| self.label(r)).collect();
    }

    fn build_synthetic(&mut self) {
        self.synthetic.clear();
        let ty = if self.row_size % 4 == 0 {
            FieldType::U32
        } else {
            FieldType::U8
        };
        self.set_generic_type(ty);
    }

    /// Words that look like string pointers on most rows. A schema-less table
    /// such as `syscmn/ngname.json` is nothing but pointers, and letting the raw
    /// grid rewrite one would corrupt the string pool - so those columns are
    /// shown but not editable.
    fn string_words(&self) -> std::collections::HashSet<usize> {
        if self.rows.is_empty() || self.row_size > 512 {
            return std::collections::HashSet::new();
        }
        let mut hits: HashMap<usize, usize> = HashMap::new();
        // Sampling keeps this cheap even for a 12 MB table with thousands of rows.
        let step = (self.rows.len() / 200).max(1);
        let mut sampled = 0usize;
        let mut row = 0;
        while row < self.rows.len() {
            sampled += 1;
            let base = self.rows[row];
            let mut offset = 0;
            while offset + 4 <= self.row_size {
                if self.looks_like_string(base + offset) {
                    *hits.entry(offset).or_insert(0) += 1;
                }
                offset += 4;
            }
            row += step;
        }
        let sampled = sampled.max(1);
        hits.into_iter()
            .filter(|(_, n)| *n * 2 > sampled)
            .map(|(off, _)| off)
            .collect()
    }

    fn looks_like_string(&self, pos: usize) -> bool {
        if pos + 8 > self.bytes.len() {
            return false;
        }
        let rel = self.u32_at(pos) as usize;
        if rel == 0 {
            return false;
        }
        let target = pos.wrapping_add(rel);
        if target + 4 > self.bytes.len() {
            return false;
        }
        // A game string is short; look no further than 512 bytes for its end.
        let limit = (target + 512).min(self.bytes.len());
        let end = self.bytes[target..limit]
            .windows(4)
            .position(|w| w == MARK)
            .map(|p| target + p)
            .unwrap_or(limit);
        if end <= target + 1 {
            return false;
        }
        let text = decode_string(&self.bytes[target..end]);
        !text.is_empty() && text.chars().all(|c| c == '\n' || !c.is_control())
    }

    /// Rebuild the generic columns for a schema-less table (u8/u16/u32/f32 view).
    pub fn set_generic_type(&mut self, ty: FieldType) {
        let step = ty.width();
        if step == 0 || self.row_size == 0 {
            return;
        }
        let string_words = if self.schema.is_some() {
            std::collections::HashSet::new()
        } else {
            self.string_words()
        };
        self.synthetic = (0..self.row_size / step)
            .map(|i| {
                let offset = i * step;
                let is_string = string_words.contains(&(offset & !3));
                Field {
                    name: format!("+0x{offset:02X}"),
                    offset,
                    ty,
                    read_only: is_string,
                    range: None,
                    labels: Vec::new(),
                    reference: None,
                    confidence: "raw".into(),
                    why: if is_string {
                        "string pointer - read-only, editing it would break the text pool".into()
                    } else {
                        "unnamed column - editable, its meaning is not identified".into()
                    },
                }
            })
            .collect();
    }

    pub fn row_count(&self) -> usize {
        self.rows.len()
    }

    pub fn fields(&self) -> &[Field] {
        match &self.schema {
            Some(schema) if !schema.fields.is_empty() => &schema.fields,
            _ => &self.synthetic,
        }
    }

    pub fn has_schema(&self) -> bool {
        self.schema.as_ref().is_some_and(|s| !s.fields.is_empty())
    }

    /// Raw bytes of a row field, for string decoding and the hex view.
    fn word(&self, row: usize, offset: usize) -> u32 {
        let base = self.rows[row] + (offset & !3);
        self.u32_at(base)
    }

    pub fn value(&self, row: usize, field: &Field) -> Value {
        if row >= self.rows.len() {
            return Value::Int(0);
        }
        if field.ty == FieldType::Text {
            return Value::Text(self.text_value(row, field));
        }
        let shift = (field.offset & 3) * 8;
        let mask: u32 = match field.ty.width() {
            1 => 0xFF,
            2 => 0xFFFF,
            _ => 0xFFFF_FFFF,
        };
        let raw = (self.word(row, field.offset) >> shift) & mask;
        match field.ty {
            FieldType::F32 => Value::Float(f32::from_bits(raw)),
            FieldType::S32 => Value::Int(raw as i32 as i64),
            _ => Value::Int(raw as i64),
        }
    }

    pub fn text_value(&self, row: usize, field: &Field) -> String {
        if row >= self.rows.len() {
            return String::new();
        }
        let pos = self.rows[row] + field.offset;
        if pos + 4 > self.bytes.len() {
            return String::new();
        }
        let rel = self.u32_at(pos) as usize;
        if rel == 0 {
            return String::new();
        }
        let target = pos.wrapping_add(rel);
        if target + 2 > self.bytes.len() {
            return String::new();
        }
        let end = self
            .bytes
            .windows(4)
            .skip(target)
            .position(|w| w == MARK)
            .map(|p| target + p)
            .unwrap_or(self.bytes.len());
        decode_string(&self.bytes[target..end])
    }

    /// Row label: the schema's `label` field, otherwise the row index.
    pub fn label(&self, row: usize) -> String {
        let Some(schema) = &self.schema else {
            return format!("#{row}");
        };
        let Some(field) = schema.label.as_ref().and_then(|n| schema.field(n)) else {
            return format!("#{row}");
        };
        let text = match self.value(row, field) {
            Value::Text(t) => t,
            other => other.display(),
        };
        text.replace('\n', " ")
    }

    pub fn labels(&self) -> &[String] {
        &self.labels
    }

    pub fn id_of(&self, row: usize) -> i64 {
        let Some(schema) = &self.schema else {
            return row as i64;
        };
        let key = schema.id.as_deref().filter(|name| *name != "__row__");
        match key.and_then(|n| schema.field(n)) {
            Some(field) => match self.value(row, field) {
                Value::Int(v) => v,
                Value::Float(v) => v as i64,
                Value::Text(_) => row as i64,
            },
            None => row as i64,
        }
    }

    /// Validate a proposed value for a field. `Ok` carries the value to write.
    pub fn validate(&self, field: &Field, text: &str) -> Result<Value, String> {
        if field.ty == FieldType::Text {
            // any length; a typed "\n" is a line break (item names often have one)
            return Ok(Value::Text(text.replace("\\n", "\n")));
        }
        let text = text.trim();
        if text.is_empty() {
            return Err("enter a value".into());
        }
        let value = if field.ty == FieldType::F32 {
            let v: f32 = text
                .parse()
                .map_err(|_| format!("{} is a float; {:?} is not a number", field.name, text))?;
            if !v.is_finite() {
                return Err("a float must be finite".into());
            }
            Value::Float(v)
        } else {
            let v: i64 = text
                .parse()
                .map_err(|_| format!("{} is an integer; {:?} is not a number", field.name, text))?;
            let bits = field.ty.width() * 8;
            let (min, max) = match field.ty {
                FieldType::S32 => (-(1i64 << 31), (1i64 << 31) - 1),
                _ => (0, (1i64 << bits) - 1),
            };
            if v < min || v > max {
                return Err(format!("{} is {}: use {min}..{max}", field.ty.name(), field.name));
            }
            Value::Int(v)
        };
        if let Some((low, high)) = field.range {
            let (v, low_ok) = match &value {
                Value::Float(v) => (*v as f64, *v as f64 >= low),
                Value::Int(v) => (*v as f64, *v as f64 >= low),
                Value::Text(_) => (0.0, true),
            };
            let high_ok = match &value {
                Value::Float(v) => (*v as f64) <= high,
                Value::Int(v) => (*v as f64) <= high,
                Value::Text(_) => true,
            };
            if !(low_ok && high_ok) {
                return Err(format!("{} must stay between {low} and {high} (got {v})", field.name));
            }
        }
        Ok(value)
    }

    /// Write a validated value. Returns the byte offset that changed.
    pub fn set(&mut self, row: usize, field: &Field, value: &Value) -> Result<usize, String> {
        if field.read_only {
            return Err(format!("{} is read-only in this editor", field.name));
        }
        if field.ty == FieldType::Text {
            let Value::Text(text) = value else {
                return Err("a text field takes text".into());
            };
            return self.set_text(row, field, text);
        }
        if row >= self.rows.len() {
            return Err("row out of range".into());
        }
        let pos = self.rows[row] + (field.offset & !3);
        if pos + 4 > self.bytes.len() {
            return Err("field is outside the file".into());
        }
        let mut old = [0u8; 4];
        old.copy_from_slice(&self.bytes[pos..pos + 4]);
        let shift = (field.offset & 3) * 8;
        let width = field.ty.width();
        let mask: u32 = if width == 4 { 0xFFFF_FFFF } else { ((1u32 << (width * 8)) - 1) << shift };
        let bits: u32 = match value {
            Value::Float(v) => v.to_bits(),
            Value::Int(v) => *v as u32,
            Value::Text(_) => return Err("text is not written".into()),
        };
        let word = u32::from_le_bytes(old);
        let word = if width == 4 {
            bits
        } else {
            (word & !mask) | ((bits << shift) & mask)
        };
        let new = word.to_le_bytes();
        if new == old {
            return Ok(pos);
        }
        self.bytes[pos..pos + 4].copy_from_slice(&new);
        self.undo.push(Edit { pos, old: old.to_vec(), new: new.to_vec(), tail: Vec::new() });
        self.redo.clear();
        self.refresh_labels();
        Ok(pos)
    }

    /// Give one row's string field new text of any length (twin of `Table.write_string` in
    /// tools/table_edit.py). The text is appended as its own block and only this row's pointer
    /// moves, so rows sharing the old string keep it. Undo restores the pointer; the appended
    /// block is then unused and harmless. Asset ids (plain ASCII) stay ASCII, text is UTF-16LE.
    fn set_text(&mut self, row: usize, field: &Field, text: &str) -> Result<usize, String> {
        if row >= self.rows.len() {
            return Err("row out of range".into());
        }
        let pos = self.rows[row] + field.offset;
        if pos + 4 > self.bytes.len() {
            return Err("field is outside the file".into());
        }
        let current = self.text_value(row, field);
        let ascii_id = !current.is_empty() && current.bytes().all(|b| (0x20..0x7F).contains(&b));
        let len_before = self.bytes.len();
        let mut payload: Vec<u8> = if ascii_id {
            if !text.is_ascii() {
                return Err(format!("{} holds an asset id; use plain ASCII", field.name));
            }
            let mut p = text.as_bytes().to_vec();
            p.push(0);
            p
        } else {
            let mut p: Vec<u8> = text.encode_utf16().flat_map(|u| u.to_le_bytes()).collect();
            p.extend_from_slice(&[0, 0]);
            p
        };
        while payload.len() % 4 != 0 {
            payload.push(b'@');
        }
        while self.bytes.len() % 4 != 0 {
            self.bytes.push(b'@');
        }
        self.bytes.extend_from_slice(MARK);
        let target = self.bytes.len();
        self.bytes.extend_from_slice(&payload);
        let mut old = [0u8; 4];
        old.copy_from_slice(&self.bytes[pos..pos + 4]);
        let new = (target.wrapping_sub(pos) as u32).to_le_bytes();
        self.bytes[pos..pos + 4].copy_from_slice(&new);
        let tail = self.bytes[len_before..].to_vec();
        self.undo.push(Edit { pos, old: old.to_vec(), new: new.to_vec(), tail });
        self.redo.clear();
        self.refresh_labels();
        Ok(pos)
    }

    /// The schema's id column, if the table has one.
    pub fn id_field(&self) -> Option<Field> {
        let name = self.schema.as_ref()?.id.clone()?;
        self.fields().iter().find(|f| f.name == name).cloned()
    }

    /// Rows whose id is 0: unused slots that [`Self::claim_row`] can turn into new entries.
    pub fn free_rows(&self) -> Vec<usize> {
        let Some(id) = self.id_field() else { return Vec::new() };
        (0..self.rows.len()).filter(|&r| self.value(r, &id) == Value::Int(0)).collect()
    }

    /// Add an entry without growing the table: the first free row (id 0) becomes a copy of
    /// `source` with the lowest unused id. String pointers are self-relative, so they are
    /// re-aimed at the source's strings rather than copied as numbers. Same rule as
    /// `tools/table_edit.py add-item`; growing the item table itself is not possible
    /// (orchestration/done/X6_item_table_growth.md). One undo step. Returns the new row.
    pub fn claim_row(&mut self, source: usize) -> Result<usize, String> {
        let id = self.id_field().ok_or("this table has no id column")?;
        if source >= self.rows.len() {
            return Err("row out of range".into());
        }
        let dest = *self.free_rows().first().ok_or("no free rows (id 0) left in this table")?;
        let used: std::collections::HashSet<i64> = (0..self.rows.len())
            .filter_map(|r| match self.value(r, &id) {
                Value::Int(v) => Some(v),
                _ => None,
            })
            .collect();
        let max = used.iter().copied().max().unwrap_or(0);
        let new_id = (1..max).find(|i| !used.contains(i)).ok_or("no unused id below the largest id")?;
        let (src, dst, size) = (self.rows[source], self.rows[dest], self.row_size);
        let old = self.bytes[dst..dst + size].to_vec();
        let mut row = self.bytes[src..src + size].to_vec();
        for field in self.fields().iter().filter(|f| f.ty == FieldType::Text && f.offset % 4 == 0) {
            let o = field.offset;
            let value = i32::from_le_bytes(row[o..o + 4].try_into().unwrap());
            if value != 0 {
                let target = (src + o) as i64 + value as i64;
                let rel = (target - (dst + o) as i64) as i32;
                row[o..o + 4].copy_from_slice(&rel.to_le_bytes());
            }
        }
        self.bytes[dst..dst + size].copy_from_slice(&row);
        self.undo.push(Edit { pos: dst, old, new: row, tail: Vec::new() });
        self.redo.clear();
        self.set(dest, &id, &Value::Int(new_id))?;
        // fold the id write into the row edit so the whole claim is one undo step
        let id_edit = self.undo.pop();
        if let (Some(id_edit), Some(row_edit)) = (id_edit, self.undo.last_mut()) {
            let at = id_edit.pos - row_edit.pos;
            row_edit.new[at..at + 4].copy_from_slice(&id_edit.new);
        }
        self.refresh_labels();
        Ok(dest)
    }

    /// Re-check every modified cell before a save.
    ///
    /// Every committed value already passed [`Self::validate`], but a save is the
    /// last point where a bad edit could reach the game file, so the whole set
    /// of dirty cells is validated again (schema ranges and the type limits).
    pub fn validation_error(&self) -> Option<String> {
        for row in 0..self.rows.len() {
            for field in self.fields() {
                if field.read_only || field.ty == FieldType::Text || !self.is_dirty(row, field) {
                    continue;
                }
                let text = match self.value(row, field) {
                    Value::Int(v) => v.to_string(),
                    Value::Float(v) => format!("{v}"),
                    Value::Text(t) => t,
                };
                if let Err(message) = self.validate(field, &text) {
                    return Some(format!("row {row}: {message}"));
                }
            }
        }
        None
    }

    pub fn is_dirty(&self, row: usize, field: &Field) -> bool {
        // A cell is modified when its bytes no longer match the pristine file.
        let pos = self.rows[row] + (field.offset & !3);
        pos + 4 <= self.pristine.len()
            && pos + 4 <= self.bytes.len()
            && self.bytes[pos..pos + 4] != self.pristine[pos..pos + 4]
    }

    pub fn edit_count(&self) -> usize {
        self.undo.len()
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }

    pub fn undo(&mut self) -> bool {
        let Some(edit) = self.undo.pop() else {
            return false;
        };
        let end = edit.pos + edit.old.len();
        if end <= self.bytes.len() {
            self.bytes[edit.pos..end].copy_from_slice(&edit.old);
        }
        let keep = self.bytes.len().saturating_sub(edit.tail.len());
        self.bytes.truncate(keep);
        self.redo.push(edit);
        self.refresh_labels();
        true
    }

    pub fn redo(&mut self) -> bool {
        let Some(edit) = self.redo.pop() else {
            return false;
        };
        self.bytes.extend_from_slice(&edit.tail);
        let end = edit.pos + edit.new.len();
        if end <= self.bytes.len() {
            self.bytes[edit.pos..end].copy_from_slice(&edit.new);
        }
        self.undo.push(edit);
        self.refresh_labels();
        true
    }

    pub fn has_changes(&self) -> bool {
        self.bytes != self.pristine
    }

    /// The current (possibly edited) BXON bytes.
    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }

    /// Throw away every edit and go back to the file as it is on disk.
    pub fn revert(&mut self) {
        self.bytes.copy_from_slice(&self.pristine);
        self.undo.clear();
        self.redo.clear();
        self.refresh_labels();
    }

    fn refresh_labels(&mut self) {
        if self.schema.is_some() {
            self.labels = (0..self.rows.len()).map(|r| self.label(r)).collect();
        }
    }
}

/// Decode one BXON string block.
///
/// The game stores two kinds: UTF-16 text (dialogue and item names, often with
/// `\x01 text \x02 reading \x03` ruby tags) and plain ASCII asset ids (`m001a`,
/// `n_hat`, `i_use_001`). Blocks are padded to four bytes with `@`. A block of
/// printable ASCII is an asset id; anything else is UTF-16.
pub fn decode_string(payload: &[u8]) -> String {
    let mut body = payload;
    while body.last() == Some(&b'@') {
        body = &body[..body.len() - 1];
    }
    if body.ends_with(&[0, 0]) {
        body = &body[..body.len() - 2];
    } else if body.last() == Some(&0) {
        body = &body[..body.len() - 1];
    }
    if body.is_empty() {
        return String::new();
    }
    if body.iter().all(|b| (0x20..0x7F).contains(b)) {
        return String::from_utf8_lossy(body).into_owned();
    }
    let units: Vec<u16> = body
        .chunks_exact(2)
        .map(|c| u16::from_le_bytes([c[0], c[1]]))
        .collect();
    strip_ruby(&String::from_utf16_lossy(&units))
}

/// Drop `\x01 kanji \x02 kana \x03` ruby annotations, keeping the kanji.
fn strip_ruby(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut chars = text.chars().peekable();
    while let Some(ch) = chars.next() {
        if ch == '\u{1}' {
            for inner in chars.by_ref() {
                if inner == '\u{2}' || inner == '\u{3}' {
                    break;
                }
                out.push(inner);
            }
            // skip the reading up to the closing marker
            for inner in chars.by_ref() {
                if inner == '\u{3}' {
                    break;
                }
            }
            continue;
        }
        out.push(ch);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn glob_patterns_match_character_files() {
        assert!(glob_match("syscmn/player_param_*.json", "syscmn/player_param_hero.json"));
        assert!(!glob_match("syscmn/player_param_*.json", "syscmn/item.json"));
        assert!(glob_match("a/*/b.json", "a/x/b.json"));
    }

    #[test]
    fn ascii_and_utf16_strings_decode() {
        assert_eq!(decode_string(b"m001a\0@@"), "m001a");
        assert_eq!(decode_string(b"i_use_001\0@@"), "i_use_001");
        let text: Vec<u8> = "やくそう".encode_utf16().flat_map(|u| u.to_le_bytes()).chain([0, 0]).collect();
        assert_eq!(decode_string(&text), "やくそう");
        assert_eq!(decode_string(b"\0@@@"), "");
    }

    #[test]
    fn ruby_markup_keeps_the_kanji() {
        let raw = "\u{1}上\u{2}じょう\u{3}やくそう";
        assert_eq!(strip_ruby(raw), "上やくそう");
    }

    fn dirs() -> Dirs {
        Dirs::detect()
    }

    /// The original table, or `None` when the game data is not extracted on this
    /// machine (the test then says so instead of failing the whole suite).
    fn doc(rel: &str) -> Option<TableDoc> {
        let dirs = dirs();
        let path = dirs
            .root
            .join("game_data")
            .join("packs")
            .join(rel)
            .with_extension("bxon");
        if !path.is_file() {
            eprintln!("skipping {rel}: {} is absent", path.display());
            return None;
        }
        let doc = TableDoc::open(&dirs, rel);
        assert!(doc.is_some(), "{rel} should open");
        doc
    }

    /// The item schema must describe the file, not the other way round: the
    /// Medicinal herb row has to read back as id 2332, buy 8, sell 4.
    #[test]
    fn item_rows_carry_the_documented_values() {
        let Some(doc) = doc("syscmn/item.json") else { return };
        let schema = doc.schema.clone().expect("schema for syscmn/item.json");
        let price = schema.field("buy_price").expect("buy_price").clone();
        let sell = schema.field("sell_price").expect("sell_price").clone();
        let id = schema.field("id").expect("id").clone();
        let name = schema.field("name").expect("name").clone();

        let herb = (0..doc.row_count())
            .find(|row| doc.text_value(*row, &name) == "やくそう")
            .expect("Medicinal herb row");
        assert_eq!(doc.value(herb, &id), Value::Int(2332));
        assert_eq!(doc.value(herb, &price), Value::Int(8));
        assert_eq!(doc.value(herb, &sell), Value::Int(4));

        // The sell/buy relationship holds for most priced rows, which is what
        // makes buy_price and sell_price trustworthy names.
        let mut priced = 0;
        let mut half = 0;
        for row in 0..doc.row_count() {
            if let (Value::Int(buy), Value::Int(gain)) = (doc.value(row, &price), doc.value(row, &sell)) {
                if buy > 0 && gain > 0 {
                    priced += 1;
                    if gain == buy / 2 {
                        half += 1;
                    }
                }
            }
        }
        assert!(priced > 500, "expected a few hundred priced items, got {priced}");
        assert!(
            half * 100 / priced >= 60,
            "sell_price should be buy_price/2 for most items ({half}/{priced})"
        );
    }

    /// The experience curve really is a curve: monotonic over all 99 levels.
    #[test]
    fn level_curve_is_monotonic() {
        let Some(doc) = doc("syscmn/player_param_hero.json") else { return };
        let schema = doc.schema.clone().expect("schema for the level curve");
        let exp = schema.field("exp_total").expect("exp_total").clone();
        let mut last = -1;
        for row in 0..doc.row_count() {
            let Value::Int(value) = doc.value(row, &exp) else {
                panic!("exp_total must be numeric at row {row}");
            };
            assert!(value > last, "exp_total goes backwards at row {row}: {value} after {last}");
            last = value;
        }
        assert_eq!(doc.row_count(), 99);
    }

    /// Editing one value must keep the file size and be exactly undoable.
    #[test]
    fn edit_is_same_size_and_undoable() {
        let Some(mut doc) = doc("syscmn/item.json") else { return };
        let schema = doc.schema.clone().expect("schema");
        let field = schema.field("buy_price").expect("buy_price").clone();
        let before = doc.bytes().to_vec();
        let old = doc.value(0, &field);

        let value = doc.validate(&field, "5").expect("5 is a legal price");
        doc.set(0, &field, &value).expect("write");
        assert_eq!(doc.bytes().len(), before.len(), "a table edit must not resize the file");
        assert_eq!(doc.value(0, &field), Value::Int(5));
        assert_ne!(doc.value(0, &field), old);
        assert!(doc.is_dirty(0, &field));
        assert!(doc.has_changes());

        assert!(doc.undo());
        assert_eq!(doc.bytes(), before.as_slice(), "undo must restore the exact bytes");
        assert!(!doc.has_changes());

        assert!(doc.redo());
        assert_eq!(doc.value(0, &field), Value::Int(5));
        doc.revert();
        assert_eq!(doc.bytes(), before.as_slice());
    }

    /// Renaming a row appends the new string and repoints only that row's field.
    #[test]
    fn text_edit_appends_and_undoes() {
        let Some(mut doc) = doc("syscmn/item.json") else { return };
        let schema = doc.schema.clone().expect("schema");
        let field = schema.fields.iter().find(|f| f.ty == FieldType::Text && !f.read_only).cloned().expect("item has a text field");
        let before = doc.bytes().to_vec();
        let other = doc.text_value(1, &field);

        let value = doc.validate(&field, "テストのやくそう").expect("text is legal");
        doc.set(0, &field, &value).expect("write");
        assert!(doc.bytes().len() > before.len());
        assert_eq!(doc.text_value(0, &field), "テストのやくそう");
        assert_eq!(doc.text_value(1, &field), other);
        assert!(doc.has_changes());

        assert!(doc.undo());
        assert_eq!(doc.bytes(), before.as_slice(), "undo must drop the appended string");
        assert!(!doc.has_changes());
        assert!(doc.redo());
        assert_eq!(doc.text_value(0, &field), "テストのやくそう");
    }

    /// Claiming a free row copies the source (strings re-aimed) and is one undo step.
    #[test]
    fn claim_row_adds_an_item_in_place() {
        let Some(mut doc) = doc("syscmn/item.json") else { return };
        let before = doc.bytes().to_vec();
        let name = doc.fields().iter().find(|f| f.name == "name").cloned().expect("name");
        let id = doc.id_field().expect("id column");
        let free = doc.free_rows().len();
        assert!(free > 0, "item.json has placeholder rows");
        let row = doc.claim_row(0).expect("claim");
        assert_eq!(doc.bytes().len(), before.len(), "claiming never grows the table");
        assert_eq!(doc.text_value(row, &name), doc.text_value(0, &name));
        assert_eq!(doc.free_rows().len(), free - 1);
        let Value::Int(new_id) = doc.value(row, &id) else { panic!("int id") };
        assert!(new_id > 0);
        assert_eq!((0..doc.row_count()).filter(|&r| doc.value(r, &id) == Value::Int(new_id)).count(), 1);
        assert!(doc.undo());
        assert_eq!(doc.bytes(), before.as_slice(), "one undo restores the row");
        assert!(doc.redo());
        assert_eq!(doc.value(row, &id), Value::Int(new_id));
    }

    /// Rewriting every named field of every named table with the value it already
    /// holds must leave the file byte-identical. This is the round-trip guarantee
    /// the editor depends on; the Python twin is `tools/table_edit.py verify`.
    #[test]
    fn every_named_field_round_trips_byte_identically() {
        let dirs = dirs();
        let mut set = SchemaSet::default();
        set.load(&dirs.root);
        assert!(set.loaded, "tools/table_schemas.json must load");
        assert!(set.named() >= 8, "expected several named tables, got {}", set.named());

        let mut checked = 0;
        for rel in set.exact.keys() {
            let Some(mut doc) = doc(rel) else { continue };
            let before = doc.bytes().to_vec();
            let fields = doc.fields().to_vec();
            assert!(!fields.is_empty(), "{rel} has a schema but no fields");
            assert_eq!(
                doc.row_size,
                doc.schema.as_ref().unwrap().row_size,
                "{rel}: the schema's row_size disagrees with the file"
            );
            for row in 0..doc.row_count() {
                for field in &fields {
                    if field.ty.is_text() || field.read_only {
                        continue;
                    }
                    let value = doc.value(row, field);
                    doc.set(row, field, &value)
                        .unwrap_or_else(|err| panic!("{rel} row {row} field {}: {err}", field.name));
                }
            }
            assert_eq!(
                doc.bytes(),
                before.as_slice(),
                "{rel} did not survive a rewrite-with-the-same-values round trip"
            );
            checked += 1;
        }
        assert!(checked >= 7, "only {checked} named tables were checked");
    }

    /// Equipment stats live in the item table; the forge's +0..+3 rows must
    /// expose the same attack/defence fields on every variant.
    #[test]
    fn equipment_rows_name_their_attack_and_defence() {
        let Some(doc) = doc("syscmn/item.json") else { return };
        let schema = doc.schema.clone().expect("item schema");
        let name = schema.field("name").expect("name").clone();
        let attack = schema.field("attack").expect("attack").clone();
        let defence = schema.field("defence").expect("defence").clone();
        let upgrade = schema.field("upgrade_level").expect("upgrade_level").clone();
        let row_named = |text: &str| {
            (0..doc.row_count())
                .find(|r| doc.text_value(*r, &name).replace('\n', "") == text)
                .unwrap_or_else(|| panic!("row {text}"))
        };
        let sword = row_named("てつのつるぎ");
        assert_eq!(doc.value(sword, &attack), Value::Int(20));
        assert_eq!(doc.value(sword, &upgrade), Value::Int(0));
        let armour = row_named("皮のよろい");
        assert_eq!(doc.value(armour, &defence), Value::Int(11));
        assert_eq!(doc.value(armour, &upgrade), Value::Int(0));
        // The four stone-sword rows are the same weapon at upgrade +0..+3.
        let stone = row_named("イシのつるぎ");
        let mut last = 0;
        for level in 0..4 {
            assert_eq!(doc.value(stone + level, &upgrade), Value::Int(level as i64));
            let Value::Int(power) = doc.value(stone + level, &attack) else {
                panic!("attack must be numeric");
            };
            assert!(power > last, "attack must rise with the upgrade level");
            last = power;
        }
    }

    /// Encounter slots point at enemy_base rows, so the dropdown can show the
    /// monster's name. Row 0 of the field-encounter table starts with a Slime.
    #[test]
    fn encounter_slots_reference_real_monsters() {
        let Some(encounters) = doc("gamecmn/encount_table.json") else { return };
        let Some(enemies) = doc("gamecmn/enemy_base.json") else { return };
        let schema = encounters.schema.clone().expect("encounter schema");
        let slot = schema.field("monster_01").expect("monster_01").clone();
        assert_eq!(encounters.value(0, &slot), Value::Int(3), "row 0 slot 1 is the Slime");
        let mut filled = 0;
        for row in 0..encounters.row_count() {
            let Value::Int(id) = encounters.value(row, &slot) else { panic!("numeric") };
            if id == 65535 {
                continue;
            }
            assert!((id as usize) < enemies.row_count(), "row {row}: monster {id} is not in enemy_base");
            filled += 1;
        }
        assert!(filled > 1000, "expected many filled encounter slots, got {filled}");
        let zone = schema.field("battle_zone").expect("battle_zone").clone();
        let Value::Int(zone) = encounters.value(0, &zone) else { panic!("battle_zone must be numeric") };
        assert!(zone < 2000);
    }

    /// The passive-skill effect is readable from the row's own text.
    #[test]
    fn passive_skill_rows_describe_their_effect() {
        let Some(doc) = doc("gamecmn/passive_skill.json") else { return };
        let schema = doc.schema.clone().expect("passive schema");
        let name = schema.field("name").expect("name").clone();
        let effect = schema.field("effect_id").expect("effect_id").clone();
        let value = schema.field("effect_value").expect("effect_value").clone();
        assert!(doc.text_value(0, &name).contains("みのまもり"));
        assert_eq!(doc.value(0, &effect), Value::Int(3), "3 is the defence stat");
        assert_eq!(doc.value(0, &value), Value::Int(10));
    }

    /// `"id": "__row__"` means the engine keys the table by row index. The
    /// encounter dropdown must therefore offer (3, "スライム"), not a random
    /// numeric column from enemy_base.
    #[test]
    fn row_keyed_references_show_monster_names() {
        let dirs = dirs();
        let mut index = TableIndex::default();
        index.schemas.load(&dirs.root);
        let options = index.reference_options(&dirs, "gamecmn/enemy_base.json");
        assert!(options.len() > 1000, "enemy_base should have a thousand rows");
        let (id, label) = options.iter().find(|(id, _)| *id == 3).expect("enemy id 3");
        assert_eq!(*id, 3);
        assert!(label.contains("スライム"), "enemy 3 should be a Slime, got {label}");
    }

    /// Validation runs again over every dirty cell at save time.
    #[test]
    fn save_validation_rejects_an_out_of_range_value() {
        let Some(mut doc) = doc("syscmn/item.json") else { return };
        let schema = doc.schema.clone().expect("schema");
        let price = schema.field("buy_price").expect("buy_price").clone();
        // Bypass `validate` on purpose: the save gate has to catch it too.
        doc.set(0, &price, &Value::Int(3_000_000)).expect("write");
        let error = doc.validation_error().expect("3,000,000 is outside the 0..2,000,000 range");
        assert!(error.contains("buy_price"), "{error}");
        doc.revert();
        assert!(doc.validation_error().is_none());
    }

    /// A table with no schema must still open and be editable by offset.
    #[test]
    fn unnamed_tables_stay_editable() {
        let Some(mut doc) = doc("gamecmn/quest_param.json") else { return };
        assert!(!doc.has_schema(), "quest_param.json is not meant to be named yet");
        let field = doc
            .fields()
            .iter()
            .find(|f| !f.read_only)
            .cloned()
            .expect("at least one editable raw column");
        let old = doc.value(0, &field);
        let new = match old {
            Value::Int(v) => Value::Int(v.wrapping_add(1) & 0xFFFF_FFFF),
            other => other,
        };
        doc.set(0, &field, &new).expect("generic write");
        assert!(doc.has_changes());
        doc.undo();
        assert!(!doc.has_changes());
    }

    /// A table that is nothing but string pointers must not offer to write them:
    /// a rewritten pointer corrupts the shared text pool.
    #[test]
    fn pointer_only_tables_are_read_only() {
        let Some(mut doc) = doc("syscmn/ngname.json") else { return };
        assert!(!doc.has_schema());
        assert!(
            doc.fields().iter().all(|f| f.read_only),
            "every column of ngname.json is a string pointer and must be read-only"
        );
        let field = doc.fields()[0].clone();
        assert!(doc.set(0, &field, &Value::Int(1)).is_err());
    }

    #[test]
    fn validation_rejects_out_of_range_and_bad_text() {
        let Some(doc) = doc("syscmn/item.json") else { return };
        let schema = doc.schema.clone().expect("schema");
        let price = schema.field("buy_price").expect("buy_price").clone();
        assert!(doc.validate(&price, "9999999999").is_err(), "10 billion is out of range");
        assert!(doc.validate(&price, "abc").is_err(), "text is not a price");
        assert!(doc.validate(&price, "8").is_ok());
        let group = schema.field("group").expect("group").clone();
        assert!(doc.validate(&group, "300").is_err(), "a u8 cannot hold 300");
    }
}
