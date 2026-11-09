//! Read-only access to the translation workspace dialogue database.
//!
//! The database lives in the reference project; it is always opened
//! `SQLITE_OPEN_READ_ONLY` so the translation project can never be modified.

use std::path::PathBuf;

use rusqlite::{Connection, OpenFlags};

#[derive(Clone, Debug)]
pub struct DialogueRow {
    pub id: i64,
    pub jp: String,
    pub en: String,
    pub status: i64,
    pub origin: String,
    pub chars: i64,
}

impl DialogueRow {
    pub fn status_text(&self) -> &'static str {
        match self.status {
            0 => "untranslated",
            1 => "translated",
            2 => "reviewed",
            _ => "?",
        }
    }
}

#[derive(Clone, Debug, Default)]
pub struct DialogueStats {
    pub sources: usize,
    pub entries: usize,
    pub pc_rows: usize,
    pub untranslated: usize,
    pub translated: usize,
    pub reviewed: usize,
    pub by_file: Vec<(String, usize)>,
    pub by_category: Vec<(String, usize)>,
}

#[derive(Clone, Debug, Default)]
pub struct Location {
    pub kind: String,
    pub file: String,
    pub entry: String,
    pub member: String,
    pub loc: Option<i64>,
    pub category: String,
}

#[derive(Clone, Debug, Default)]
pub struct PcRow {
    pub id: i64,
    pub file: String,
    pub key: String,
    pub jp: String,
    pub en: String,
}

#[derive(Default)]
pub struct DialogueDb {
    pub path: PathBuf,
    conn: Option<Connection>,
    stats: Option<DialogueStats>,
}

fn escape_like(text: &str) -> String {
    text.replace('\\', "\\\\").replace('%', "\\%").replace('_', "\\_")
}

impl DialogueDb {
    pub fn new(path: PathBuf) -> Self {
        Self {
            path,
            conn: None,
            stats: None,
        }
    }

    pub fn available(&self) -> bool {
        self.path.exists()
    }

    fn conn(&mut self) -> Option<&Connection> {
        if self.conn.is_none() {
            if !self.available() {
                return None;
            }
            let conn = Connection::open_with_flags(
                &self.path,
                OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_URI,
            )
            .ok()?;
            self.conn = Some(conn);
        }
        self.conn.as_ref()
    }

    pub fn stats(&mut self) -> DialogueStats {
        if let Some(stats) = &self.stats {
            return stats.clone();
        }
        let mut stats = DialogueStats::default();
        if let Some(conn) = self.conn() {
            let count = |sql: &str| -> usize {
                conn.query_row(sql, [], |row| row.get::<_, i64>(0))
                    .map(|v| v as usize)
                    .unwrap_or(0)
            };
            stats.sources = count("SELECT COUNT(*) FROM source");
            stats.entries = count("SELECT COUNT(*) FROM entry");
            stats.pc_rows = count("SELECT COUNT(*) FROM pc_text");
            if let Ok(mut stmt) = conn.prepare("SELECT status, COUNT(*) FROM source GROUP BY status") {
                if let Ok(rows) = stmt.query_map([], |row| {
                    Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?))
                }) {
                    for row in rows.flatten() {
                        match row.0 {
                            0 => stats.untranslated = row.1 as usize,
                            1 => stats.translated = row.1 as usize,
                            2 => stats.reviewed = row.1 as usize,
                            _ => {}
                        }
                    }
                }
            }
            if let Ok(mut stmt) = conn
                .prepare("SELECT file, COUNT(*) FROM entry GROUP BY file ORDER BY 2 DESC LIMIT 400")
            {
                if let Ok(rows) = stmt.query_map([], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)? as usize))
                }) {
                    stats.by_file = rows.flatten().collect();
                }
            }
            if let Ok(mut stmt) = conn
                .prepare("SELECT category, COUNT(*) FROM entry GROUP BY category ORDER BY 2 DESC LIMIT 200")
            {
                if let Ok(rows) = stmt.query_map([], |row| {
                    Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)? as usize))
                }) {
                    stats.by_category = rows.flatten().collect();
                }
            }
        }
        self.stats = Some(stats.clone());
        stats
    }

    pub fn search_sources(
        &mut self,
        query: &str,
        file_filter: Option<&str>,
        status: Option<i64>,
        origin: Option<&str>,
        offset: usize,
        limit: usize,
    ) -> Vec<DialogueRow> {
        let Some(conn) = self.conn() else { return Vec::new() };
        let mut where_parts: Vec<String> = Vec::new();
        let mut params: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
        let q = query.trim();
        if !q.is_empty() {
            let like = format!("%{}%", escape_like(q));
            where_parts.push(
                r"(s.text LIKE ? ESCAPE '\' OR s.translation LIKE ? ESCAPE '\' OR s.plain LIKE ? ESCAPE '\')"
                    .into(),
            );
            params.push(Box::new(like.clone()));
            params.push(Box::new(like.clone()));
            params.push(Box::new(like));
        }
        if let Some(file) = file_filter {
            where_parts
                .push(r"s.id IN (SELECT source_id FROM entry WHERE file LIKE ? ESCAPE '\')".into());
            params.push(Box::new(format!("%{}%", escape_like(file))));
        }
        if let Some(status) = status {
            where_parts.push("s.status = ?".into());
            params.push(Box::new(status));
        }
        if let Some(origin) = origin {
            where_parts.push("s.origin = ?".into());
            params.push(Box::new(origin.to_string()));
        }
        let mut sql =
            "SELECT s.id, s.text, s.translation, s.status, s.origin, s.chars FROM source s".to_string();
        if !where_parts.is_empty() {
            sql.push_str(" WHERE ");
            sql.push_str(&where_parts.join(" AND "));
        }
        sql.push_str(" ORDER BY s.id LIMIT ? OFFSET ?");
        params.push(Box::new(limit as i64));
        params.push(Box::new(offset as i64));
        let refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|p| p.as_ref()).collect();
        let Ok(mut stmt) = conn.prepare(&sql) else { return Vec::new() };
        let rows = stmt.query_map(refs.as_slice(), |row| {
            Ok(DialogueRow {
                id: row.get(0)?,
                jp: row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                en: row.get::<_, Option<String>>(2)?.unwrap_or_default(),
                status: row.get::<_, Option<i64>>(3)?.unwrap_or(0),
                origin: row.get::<_, Option<String>>(4)?.unwrap_or_default(),
                chars: row.get::<_, Option<i64>>(5)?.unwrap_or(0),
            })
        });
        rows.map(|r| r.flatten().collect()).unwrap_or_default()
    }

    pub fn count_sources(
        &mut self,
        query: &str,
        file_filter: Option<&str>,
        status: Option<i64>,
        origin: Option<&str>,
    ) -> usize {
        let Some(conn) = self.conn() else { return 0 };
        let mut where_parts: Vec<String> = Vec::new();
        let mut params: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();
        let q = query.trim();
        if !q.is_empty() {
            let like = format!("%{}%", escape_like(q));
            where_parts.push(
                r"(s.text LIKE ? ESCAPE '\' OR s.translation LIKE ? ESCAPE '\' OR s.plain LIKE ? ESCAPE '\')"
                    .into(),
            );
            params.push(Box::new(like.clone()));
            params.push(Box::new(like.clone()));
            params.push(Box::new(like));
        }
        if let Some(file) = file_filter {
            where_parts
                .push(r"s.id IN (SELECT source_id FROM entry WHERE file LIKE ? ESCAPE '\')".into());
            params.push(Box::new(format!("%{}%", escape_like(file))));
        }
        if let Some(status) = status {
            where_parts.push("s.status = ?".into());
            params.push(Box::new(status));
        }
        if let Some(origin) = origin {
            where_parts.push("s.origin = ?".into());
            params.push(Box::new(origin.to_string()));
        }
        let mut sql = "SELECT COUNT(*) FROM source s".to_string();
        if !where_parts.is_empty() {
            sql.push_str(" WHERE ");
            sql.push_str(&where_parts.join(" AND "));
        }
        let refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|p| p.as_ref()).collect();
        conn.query_row(&sql, refs.as_slice(), |row| row.get::<_, i64>(0))
            .map(|v| v as usize)
            .unwrap_or(0)
    }

    pub fn search_pc(&mut self, query: &str, offset: usize, limit: usize) -> Vec<PcRow> {
        let Some(conn) = self.conn() else { return Vec::new() };
        let q = query.trim();
        let map = |row: &rusqlite::Row<'_>| {
            Ok(PcRow {
                id: row.get(0)?,
                file: row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                key: row.get::<_, Option<String>>(2)?.unwrap_or_default(),
                jp: row.get::<_, Option<String>>(3)?.unwrap_or_default(),
                en: row.get::<_, Option<String>>(4)?.unwrap_or_default(),
            })
        };
        if q.is_empty() {
            let Ok(mut stmt) =
                conn.prepare("SELECT id, file, key, jp, en FROM pc_text ORDER BY id LIMIT ? OFFSET ?")
            else {
                return Vec::new();
            };
            stmt.query_map([limit as i64, offset as i64], map)
                .map(|rows| rows.flatten().collect())
                .unwrap_or_default()
        } else {
            let like = format!("%{}%", escape_like(q));
            let Ok(mut stmt) = conn.prepare(
                r"SELECT id, file, key, jp, en FROM pc_text WHERE jp LIKE ? ESCAPE '\' OR en LIKE ? ESCAPE '\' ORDER BY id LIMIT ? OFFSET ?",
            ) else {
                return Vec::new();
            };
            stmt.query_map(rusqlite::params![like, like, limit as i64, offset as i64], map)
                .map(|rows| rows.flatten().collect())
                .unwrap_or_default()
        }
    }

    pub fn locations(&mut self, source_id: i64) -> Vec<Location> {
        let Some(conn) = self.conn() else { return Vec::new() };
        let Ok(mut stmt) = conn.prepare(
            "SELECT kind, file, entry, member, loc, category FROM entry WHERE source_id = ? ORDER BY id LIMIT 60",
        ) else {
            return Vec::new();
        };
        stmt.query_map([source_id], |row| {
            Ok(Location {
                kind: row.get::<_, Option<String>>(0)?.unwrap_or_default(),
                file: row.get::<_, Option<String>>(1)?.unwrap_or_default(),
                entry: row.get::<_, Option<String>>(2)?.unwrap_or_default(),
                member: row.get::<_, Option<String>>(3)?.unwrap_or_default(),
                loc: row.get::<_, Option<i64>>(4)?,
                category: row.get::<_, Option<String>>(5)?.unwrap_or_default(),
            })
        })
        .map(|rows| rows.flatten().collect())
        .unwrap_or_default()
    }

    /// `layout_packs` metadata declared by the translation project.
    pub fn layout_packs(&mut self) -> Vec<String> {
        let Some(conn) = self.conn() else { return Vec::new() };
        let Ok(value) = conn.query_row("SELECT value FROM meta WHERE key='layout_packs'", [], |row| {
            row.get::<_, String>(0)
        }) else {
            return Vec::new();
        };
        serde_json::from_str::<Vec<String>>(&value).unwrap_or_default()
    }
}

// ===========================================================================
// Game text banks
// ===========================================================================
//
// `tools/text_tool.py export` writes one JSON per bank under
// `game_assets/text/banks/` plus `index.json`. Every bank is a BXON table whose
// UTF-16 strings are the player-visible text; the tool renders control codes
// as readable tags (`{PLAYER}`, `{CR}`, `{ruby:base|reading}`, ...), and this
// module measures that tagged text with the game's own BFFNT glyph widths.

use std::collections::HashMap;
use std::path::Path;

use serde::{Deserialize, Serialize};

/// Message-argument slots (U+0004 + one byte). The names are the uses seen in
/// the shipped text; a slot is reused for different things in different lines,
/// so only 1..3 have a stable meaning (`{PLAYER}`, `{NAME}`, `{TARGET}`).
pub const ARG_NAMES: &[(&str, u8)] = &[
    ("PLAYER", 0x1),
    ("NAME", 0x2),
    ("TARGET", 0x3),
    ("PARTY3", 0x4),
    ("ITEM", 0x5),
    ("ITEM2", 0x6),
    ("ITEM3", 0x7),
    ("NUMBER", 0x8),
    ("NUMBER2", 0x9),
    ("NUMBER3", 0xA),
    ("NUMBER4", 0xB),
    ("NUMBER5", 0xC),
    ("NUMBER6", 0xD),
    ("NUMBER7", 0xE),
    ("NUMBER8", 0xF),
];

/// Formatting switches that bracket the small-print note of a message.
/// Their renderer effect is not decoded; they are kept explicit on purpose.
pub const FORMAT_CODES: [u8; 2] = [0x64, 0x66];

/// One visible piece of a tagged string.
#[derive(Clone, Debug, PartialEq)]
pub enum Piece {
    Text(char),
    Var(u8),
    /// `{CR}`: wait for the player to press a button; not a line break.
    Cr,
    Newline,
    Page,
}

/// Split a tagged string into what the game actually draws / does.
///
/// Unknown tags are an error: a typo in the editor must not silently become
/// literal text in the game.
pub fn pieces(tagged: &str) -> Result<Vec<Piece>, String> {
    let chars: Vec<char> = tagged.chars().collect();
    let mut out = Vec::new();
    let mut i = 0;
    while i < chars.len() {
        let c = chars[i];
        if c == '{' {
            if chars.get(i + 1) == Some(&'{') {
                out.push(Piece::Text('{'));
                i += 2;
                continue;
            }
            let Some(close) = chars[i + 1..].iter().position(|&x| x == '}') else {
                return Err(format!("unclosed tag at character {i}"));
            };
            let end = i + 1 + close;
            let tag: String = chars[i + 1..end].iter().collect();
            if let Some(body) = tag.strip_prefix("ruby:") {
                let Some((base, _reading)) = body.split_once('|') else {
                    return Err(format!("ruby tag needs base|reading: {{{tag}}}"));
                };
                for ch in base.chars() {
                    out.push(Piece::Text(ch));
                }
            } else if let Some(slot) = tag.strip_prefix("v:") {
                let slot = u8::from_str_radix(slot, 16)
                    .map_err(|_| format!("bad argument tag {{{tag}}}"))?;
                out.push(Piece::Var(slot));
            } else if let Some(slot) = tag.strip_prefix("FMT:") {
                let slot = u8::from_str_radix(slot, 16)
                    .map_err(|_| format!("bad format tag {{{tag}}}"))?;
                out.push(Piece::Var(slot));
            } else if let Some((_, slot)) = ARG_NAMES.iter().find(|(name, _)| *name == tag) {
                out.push(Piece::Var(*slot));
            } else if tag == "CR" {
                // a button wait, not a line break
                out.push(Piece::Cr);
            } else if tag == "PAGE" {
                out.push(Piece::Page);
            } else if tag.len() == 3 && tag.starts_with('c') {
                u8::from_str_radix(&tag[1..], 16)
                    .map_err(|_| format!("bad control tag {{{tag}}}"))?;
            } else {
                return Err(format!("unknown tag {{{tag}}}"));
            }
            i = end + 1;
            continue;
        }
        if c == '}' {
            if chars.get(i + 1) == Some(&'}') {
                out.push(Piece::Text('}'));
                i += 2;
                continue;
            }
            return Err(format!("a literal '}}' must be written '}}}}' (character {i})"));
        }
        out.push(if c == '\n' { Piece::Newline } else { Piece::Text(c) });
        i += 1;
    }
    Ok(out)
}

/// Tagged text -> raw game string (U+0004 codes, ruby markers, CR, PAGE).
pub fn encode_tagged(tagged: &str) -> Result<String, String> {
    let mut out = String::new();
    for piece in pieces(tagged)? {
        match piece {
            Piece::Text(c) => out.push(c),
            Piece::Var(slot) => {
                out.push('\u{4}');
                out.push(char::from(slot));
            }
            Piece::Newline => out.push('\n'),
            Piece::Page => out.push('\u{1f}'),
            Piece::Cr => out.push('\r'),
        }
    }
    Ok(out)
}

/// Plain reading of a tagged string, for search results and list columns.
pub fn plain_text(tagged: &str) -> String {
    let mut out = String::new();
    let Ok(list) = pieces(tagged) else {
        return tagged.to_string();
    };
    for piece in list {
        match piece {
            Piece::Text(c) => out.push(c),
            Piece::Var(_) => out.push('\u{ff0a}'), // ＊ like the reference tool
            Piece::Cr | Piece::Newline | Piece::Page => out.push(' '),
        }
    }
    out
}

/// Tags used by a string, in order (for the editor's tag summary).
pub fn tags_of(tagged: &str) -> Vec<String> {
    let mut out = Vec::new();
    let chars: Vec<char> = tagged.chars().collect();
    let mut i = 0;
    while i < chars.len() {
        if chars[i] == '{' {
            if chars.get(i + 1) == Some(&'{') {
                i += 2;
                continue;
            }
            if let Some(close) = chars[i + 1..].iter().position(|&x| x == '}') {
                let end = i + 1 + close;
                out.push(chars[i + 1..end].iter().collect());
                i = end + 1;
                continue;
            }
        }
        i += 1;
    }
    out
}

// ---------------------------------------------------------------------------
// BFFNT: the game's own font metrics
// ---------------------------------------------------------------------------
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct GlyphWidth {
    pub left: i8,
    pub glyph: u8,
    pub advance: u8,
}

/// Read-only view of a 3DS BFFNT font: character map + per-glyph advance.
///
/// Layout follows the reference translation tool's `bffnt.py` (FINF header,
/// CWDH width chain, CMAP character maps). Widths are the game's pixels at
/// font size 1:1, which is exactly what the message window uses.
#[derive(Clone, Debug, Default)]
pub struct GlyphFont {
    pub name: String,
    pub line_feed: u16,
    pub height: u8,
    pub width: u8,
    pub ascent: u8,
    pub default_width: GlyphWidth,
    cmap: HashMap<u32, u16>,
    widths: HashMap<u16, GlyphWidth>,
}

fn le16(data: &[u8], at: usize) -> Option<u16> {
    let b = data.get(at..at + 2)?;
    Some(u16::from_le_bytes([b[0], b[1]]))
}

fn le32(data: &[u8], at: usize) -> Option<u32> {
    let b = data.get(at..at + 4)?;
    Some(u32::from_le_bytes([b[0], b[1], b[2], b[3]]))
}

impl GlyphFont {
    pub fn parse(name: &str, data: &[u8]) -> Option<GlyphFont> {
        let magic = data.get(0..4)?;
        if magic != b"FFNT".as_slice() && magic != b"CFNT".as_slice() {
            return None;
        }
        let hsize = le16(data, 6)? as usize;
        let p = hsize;
        if data.get(p..p + 4)? != b"FINF".as_slice() {
            return None;
        }
        let mut font = GlyphFont {
            name: name.to_string(),
            height: *data.get(p + 9)?,
            width: *data.get(p + 10)?,
            ascent: *data.get(p + 11)?,
            line_feed: le16(data, p + 12)?,
            ..Default::default()
        };
        font.default_width = GlyphWidth {
            left: *data.get(p + 16)? as i8,
            glyph: *data.get(p + 17)?,
            advance: *data.get(p + 18)?,
        };
        let ptr_width = le32(data, p + 24)?;
        let ptr_map = le32(data, p + 28)?;

        // CWDH chain: runs of glyph indices with 3-byte width records.
        let mut pw = ptr_width;
        let mut guard = 0;
        while pw != 0 && guard < 256 {
            guard += 1;
            let base = (pw as usize).checked_sub(8)?;
            let start = le16(data, base + 8)?;
            let end = le16(data, base + 10)?;
            let next = le32(data, base + 12)?;
            for gi in start..=end {
                let at = base + 0x10 + (gi - start) as usize * 3;
                let Some(b) = data.get(at..at + 3) else { break };
                font.widths.insert(
                    gi,
                    GlyphWidth {
                        left: b[0] as i8,
                        glyph: b[1],
                        advance: b[2],
                    },
                );
            }
            pw = next;
        }

        // CMAP chain: direct ranges, index tables and scanned ranges.
        let mut pm = ptr_map;
        let mut guard = 0;
        while pm != 0 && guard < 256 {
            guard += 1;
            let base = (pm as usize).checked_sub(8)?;
            let cstart = le16(data, base + 8)? as u32;
            let cend = le16(data, base + 10)? as u32;
            let method = le16(data, base + 12)?;
            let next = le32(data, base + 16)?;
            let body = base + 0x14;
            match method {
                0 => {
                    let off = le16(data, body)? as u32;
                    for c in cstart..=cend {
                        font.cmap.insert(c, (off + (c - cstart)) as u16);
                    }
                }
                1 => {
                    for c in cstart..=cend {
                        let at = body + (c - cstart) as usize * 2;
                        if let Some(gi) = le16(data, at) {
                            if gi != 0xFFFF {
                                font.cmap.insert(c, gi);
                            }
                        }
                    }
                }
                2 => {
                    let n = le16(data, body)? as usize;
                    for i in 0..n {
                        let at = body + 2 + i * 4;
                        if let (Some(c), Some(gi)) = (le16(data, at), le16(data, at + 2)) {
                            font.cmap.insert(c as u32, gi);
                        }
                    }
                }
                _ => {}
            }
            pm = next;
        }
        Some(font)
    }

    pub fn has(&self, ch: char) -> bool {
        self.cmap.contains_key(&(ch as u32))
    }

    /// Advance width in the game's pixels (its `charWidth` field).
    pub fn advance(&self, ch: char) -> u16 {
        match self.cmap.get(&(ch as u32)) {
            Some(gi) => self.widths.get(gi).unwrap_or(&self.default_width).advance as u16,
            None => self.default_width.advance as u16,
        }
    }

    /// Characters the font cannot draw, in first-seen order (for the warning).
    pub fn missing(&self, text: &str) -> Vec<char> {
        let mut out: Vec<char> = Vec::new();
        for piece in pieces(text).unwrap_or_default() {
            if let Piece::Text(c) = piece {
                if c != '\n' && !self.has(c) && !out.contains(&c) {
                    out.push(c);
                }
            }
        }
        out
    }
}

/// Widths of one tagged string in a font, split into message pages
/// (`{PAGE}`) and lines (`\n`; `{CR}` is a button wait, not a break).
#[derive(Clone, Debug, Default)]
pub struct Measure {
    pub pages: Vec<Vec<f32>>,
    pub missing: Vec<char>,
    /// UTF-16 units the encoded string occupies (the message window's buffer
    /// is 255 units; a longer message is cut off and shows blank).
    pub units: usize,
}

impl Measure {
    pub fn widths(&self) -> Vec<f32> {
        self.pages.iter().flatten().copied().collect()
    }

    pub fn max_width(&self) -> f32 {
        self.widths().into_iter().fold(0.0, f32::max)
    }

    pub fn line_count(&self) -> usize {
        self.pages.iter().map(|p| p.len()).sum()
    }
}

/// A runtime argument ({PLAYER}, {ITEM}, ...) is about eight half-width
/// characters wide in the reference tool's estimate.
pub fn var_width(font: &GlyphFont) -> f32 {
    font.advance('M') as f32 * 8.0 * 2.0 / 3.0
}

pub fn measure(tagged: &str, font: &GlyphFont) -> Measure {
    let mut pages: Vec<Vec<f32>> = vec![vec![0.0]];
    let var = var_width(font);
    for piece in pieces(tagged).unwrap_or_default() {
        match piece {
            Piece::Text('\n') | Piece::Newline => {
                if let Some(page) = pages.last_mut() {
                    page.push(0.0);
                }
            }
            Piece::Text(c) => {
                if let Some(page) = pages.last_mut() {
                    if let Some(last) = page.last_mut() {
                        *last += font.advance(c) as f32;
                    }
                }
            }
            Piece::Var(_) => {
                if let Some(last) = pages.last_mut().and_then(|p| p.last_mut()) {
                    *last += var;
                }
            }
            Piece::Cr => {}
            Piece::Page => pages.push(vec![0.0]),
        }
    }
    let units = encode_tagged(tagged)
        .map(|raw| raw.encode_utf16().count())
        .unwrap_or(0);
    Measure {
        pages,
        missing: font.missing(tagged),
        units,
    }
}

// ---------------------------------------------------------------------------
// exported text banks
// ---------------------------------------------------------------------------
#[derive(Clone, Debug, Default, Deserialize)]
pub struct BankMeta {
    pub key: String,
    pub pack: String,
    pub member: String,
    pub kind: String,
    pub category: String,
    pub scene: String,
    pub font: String,
    pub box_width: f32,
    pub box_lines: usize,
    pub count: usize,
    pub speakers: usize,
    pub file: String,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub struct TextEntry {
    pub id: usize,
    pub offset: u64,
    pub role: String,
    pub speaker: String,
    pub location: String,
    pub text: String,
}

#[derive(Clone, Debug, Default, Deserialize)]
pub struct TextBankDoc {
    pub bank: String,
    pub pack: String,
    pub member: String,
    pub kind: String,
    pub category: String,
    pub scene: String,
    pub font: String,
    pub box_width: f32,
    pub box_lines: usize,
    pub count: usize,
    #[serde(default)]
    pub speakers: Vec<String>,
    #[serde(default)]
    pub entries: Vec<TextEntry>,
}

#[derive(Clone, Debug, Deserialize)]
struct TextIndexFile {
    #[serde(default)]
    banks: Vec<BankMeta>,
    #[serde(default)]
    families: HashMap<String, usize>,
    #[serde(default)]
    entries: usize,
}

/// One full-text search hit. The snippet and speaker travel with it so the
/// result list does not have to read every hit's bank file.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TextHit {
    pub bank: usize,
    pub entry: usize,
    pub speaker: String,
    pub text: String,
}

/// Lazy view of `game_assets/text`: index + fonts loaded up front, bank files
/// parsed on first use and then cached.
#[derive(Default)]
pub struct TextIndex {
    pub dir: PathBuf,
    pub banks: Vec<BankMeta>,
    pub families: Vec<(String, usize)>,
    pub total_entries: usize,
    pub fonts: HashMap<String, GlyphFont>,
    entries: Vec<Option<TextBankDoc>>,
    pub error: Option<String>,
    pub loaded: bool,
}

impl TextIndex {
    /// Load the index and the fonts. Missing output is not an error: the panel
    /// then tells the user to run `python tools/text_tool.py export`.
    pub fn load(root: &Path) -> TextIndex {
        let dir = root.join("game_assets").join("text");
        let mut index = TextIndex {
            dir: dir.clone(),
            ..Default::default()
        };
        let font_dir = root.join("game_data").join("romfs").join("font");
        for name in ["3D14", "3D12", "2D14", "2D9", "credit2D", "credit2DSH"] {
            let path = font_dir.join(format!("{name}.bffnt"));
            if let Ok(bytes) = std::fs::read(&path) {
                if let Some(font) = GlyphFont::parse(name, &bytes) {
                    index.fonts.insert(name.to_string(), font);
                }
            }
        }
        let index_file = dir.join("index.json");
        let Some(text) = std::fs::read_to_string(&index_file).ok() else {
            index.error = Some(format!(
                "no {} - run `python tools/text_tool.py export`",
                index_file.display()
            ));
            return index;
        };
        match serde_json::from_str::<TextIndexFile>(&text) {
            Ok(file) => {
                index.banks = file.banks;
                index.total_entries = file.entries;
                index.families = file.families.into_iter().collect();
                index.families.sort_by(|a, b| b.1.cmp(&a.1));
                index.entries = (0..index.banks.len()).map(|_| None).collect();
                index.loaded = true;
            }
            Err(err) => {
                index.error = Some(format!("{}: {err}", index_file.display()));
            }
        }
        index
    }

    pub fn available(&self) -> bool {
        self.loaded && !self.banks.is_empty()
    }

    pub fn font(&self, name: &str) -> Option<&GlyphFont> {
        self.fonts.get(name)
    }

    /// Font of a bank; falls back to the dialogue font when the declared one
    /// could not be loaded (e.g. a fresh checkout without the RomFS).
    pub fn bank_font(&self, bank: usize) -> Option<&GlyphFont> {
        let name = self.banks.get(bank)?.font.as_str();
        self.fonts
            .get(name)
            .or_else(|| self.fonts.get("3D14"))
            .or_else(|| self.fonts.values().next())
    }

    pub fn ensure_bank(&mut self, bank: usize) -> Option<&TextBankDoc> {
        let meta = self.banks.get(bank)?.clone();
        if self.entries.get(bank).is_none() {
            return None;
        }
        if self.entries[bank].is_none() {
            let path = self.dir.join(&meta.file);
            let doc = std::fs::read_to_string(&path)
                .ok()
                .and_then(|text| serde_json::from_str::<TextBankDoc>(&text).ok());
            self.entries[bank] = doc;
        }
        self.entries[bank].as_ref()
    }

    pub fn ensure_all(&mut self) {
        for i in 0..self.banks.len() {
            self.ensure_bank(i);
        }
    }

    /// Replace the cached entries of a bank after a successful save, so the
    /// editor's "unsaved changes" count goes back to zero without re-reading
    /// the file (which is unchanged on disk anyway: edits live in the draft).
    pub fn set_bank_entries(&mut self, bank: usize, entries: Vec<TextEntry>) {
        if let Some(Some(doc)) = self.entries.get_mut(bank) {
            doc.count = entries.len();
            doc.entries = entries;
        }
    }

    pub fn bank_meta(&self, bank: usize) -> Option<&BankMeta> {
        self.banks.get(bank)
    }

    /// Cached entries of a bank, if its file has been read already.
    pub fn entries_for(&self, bank: usize) -> Option<&TextBankDoc> {
        self.entries.get(bank)?.as_ref()
    }

    /// Case-insensitive search over every bank, capped at `limit` hits.
    /// The needle is matched against the tagged text and the speaker.
    pub fn search(&mut self, needle: &str, limit: usize) -> Vec<TextHit> {
        let needle = needle.trim().to_lowercase();
        let mut hits = Vec::new();
        if needle.len() < 2 {
            return hits;
        }
        self.ensure_all();
        for (bank, slot) in self.entries.iter().enumerate() {
            let Some(doc) = slot else { continue };
            for (entry, row) in doc.entries.iter().enumerate() {
                if row.text.to_lowercase().contains(&needle)
                    || row.speaker.to_lowercase().contains(&needle)
                {
                    hits.push(TextHit {
                        bank,
                        entry,
                        speaker: row.speaker.clone(),
                        text: plain_text(&row.text),
                    });
                    if hits.len() >= limit {
                        return hits;
                    }
                }
            }
        }
        hits
    }

    /// The JSON document `tools/text_tool.py save-mod` expects, with edited
    /// entry texts. Offsets are kept, so the Python side can rebuild by offset.
    pub fn bank_document(&self, bank: usize, entries: &[TextEntry]) -> Option<serde_json::Value> {
        let meta = self.banks.get(bank)?;
        let mut speakers: Vec<String> = Vec::new();
        for row in entries {
            if row.role == "text" && !row.speaker.is_empty() && !speakers.contains(&row.speaker) {
                speakers.push(row.speaker.clone());
            }
        }
        speakers.sort();
        Some(serde_json::json!({
            "bank": meta.key,
            "pack": meta.pack,
            "member": meta.member,
            "kind": meta.kind,
            "category": meta.category,
            "scene": meta.scene,
            "font": meta.font,
            "box_width": meta.box_width,
            "box_lines": meta.box_lines,
            "source": format!("game_data/packs/{}.bxon", meta.key),
            "count": entries.len(),
            "speakers": speakers,
            "entries": entries,
        }))
    }
}

#[cfg(test)]
mod text_tests {
    use super::*;
    use std::path::PathBuf;

    fn root() -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .to_path_buf()
    }

    fn dialogue_font() -> Option<GlyphFont> {
        let data = std::fs::read(root().join("game_data/romfs/font/3D14.bffnt")).ok()?;
        GlyphFont::parse("3D14", &data)
    }

    #[test]
    fn tags_round_trip_to_game_codes() {
        let cases = [
            ("\u{4}\u{1}は", "{PLAYER}は"),
            ("{literal}", "{{literal}}"),
            ("line\r", "line{CR}"),
            ("a\u{1f}b", "a{PAGE}b"),
            ("x\u{4}\u{66}note\u{4}\u{64}", "x{FMT:66}note{FMT:64}"),
        ];
        for (raw, tagged) in cases {
            assert_eq!(encode_tagged(tagged).unwrap(), raw, "{tagged}");
        }
        assert!(encode_tagged("hello {BOGUS} world").is_err());
        assert!(encode_tagged("{ruby:no-reading}").is_err());
        assert_eq!(
            plain_text("{ruby:使|つか}う{CR}\n{PLAYER}"),
            "使う  \u{ff0a}"
        );
    }

    #[test]
    fn font_metrics_come_from_the_game_font() {
        let path = root().join("game_data/romfs/font/3D14.bffnt");
        if !path.exists() {
            return;
        }
        let font = dialogue_font().expect("3D14.bffnt must parse");
        assert!(
            font.has('A') && font.has('あ'),
            "dialogue font must cover Latin and kana"
        );
        assert!(font.advance('W') > font.advance('i'));
        assert!(font.advance('あ') > 0);
        assert_eq!(font.missing("ABC"), Vec::<char>::new());
    }

    #[test]
    fn measurement_uses_pages_and_flags_missing_glyphs() {
        let Some(font) = dialogue_font() else { return };
        let m = measure("abc\n{NAME}{PAGE}xyz", &font);
        assert_eq!(m.pages.len(), 2);
        assert_eq!(m.pages[0].len(), 2);
        assert!(m.max_width() > 0.0);
        assert!(m.units > 4);
        // a character no game font has (private use outside the icon range)
        let missing = font.missing("\u{10FFFD}");
        assert_eq!(missing, vec!['\u{10FFFD}']);
    }

    #[test]
    fn text_index_lists_banks_and_npc_speakers() {
        let mut index = TextIndex::load(&root());
        if !index.available() {
            return;
        }
        assert!(index.banks.len() > 700, "{} banks", index.banks.len());
        assert!(!index.fonts.is_empty(), "game fonts must load");
        let npc = index
            .banks
            .iter()
            .position(|b| b.key == "param/region/r001/npc_ie")
            .expect("npc bank");
        let doc = index.ensure_bank(npc).expect("bank file");
        assert_eq!(doc.font, "3D14");
        assert_eq!(doc.box_width as u32, 321);
        assert!(doc
            .entries
            .iter()
            .any(|e| e.speaker == "ダン" && e.location.starts_with("talk[")));
    }

    #[test]
    fn full_text_search_returns_ready_to_show_hits() {
        let mut index = TextIndex::load(&root());
        if !index.available() {
            return;
        }
        let hits = index.search("ヒヒーン", 5);
        assert!(!hits.is_empty(), "the horse lines must be searchable");
        assert!(hits[0].text.contains("ヒヒーン"), "{}", hits[0].text);
        let by_speaker = index.search("ゼッケンドルフ", 20);
        assert!(
            by_speaker.iter().any(|h| h.speaker == "ゼッケンドルフ"),
            "search must match speakers: {:?}",
            by_speaker.iter().map(|h| &h.speaker).collect::<Vec<_>>()
        );
    }

    #[test]
    fn every_exported_entry_uses_known_tags() {
        let mut index = TextIndex::load(&root());
        if !index.available() {
            return;
        }
        index.ensure_all();
        let mut checked = 0;
        for bank in 0..index.banks.len() {
            if let Some(doc) = index.ensure_bank(bank) {
                for entry in &doc.entries {
                    pieces(&entry.text).unwrap_or_else(|err| {
                        panic!("{} @0x{:X}: {err}", doc.bank, entry.offset)
                    });
                    checked += 1;
                }
            }
        }
        assert!(checked > 60_000, "{checked} entries");
    }
}
