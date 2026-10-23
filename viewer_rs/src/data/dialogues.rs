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
