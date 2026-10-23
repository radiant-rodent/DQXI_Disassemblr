"""Read-only access to the translation workspace dialogue database.

The database lives in the (read-only) reference project
``..\\reference project\\workspace\\project.db``.  Everything here
opens with ``mode=ro`` so the translation project can never be modified.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from .. import utils

STATUS_LABELS = {0: "untranslated", 1: "translated", 2: "reviewed"}


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@dataclass
class DialogueRow:
    id: int
    jp: str
    en: str
    status: int
    origin: str
    chars: int = 0

    @property
    def status_text(self) -> str:
        return STATUS_LABELS.get(self.status, str(self.status))


@dataclass
class DialogueStats:
    sources: int = 0
    entries: int = 0
    pc_rows: int = 0
    untranslated: int = 0
    translated: int = 0
    reviewed: int = 0
    by_origin: dict = field(default_factory=dict)
    by_category: dict = field(default_factory=dict)
    by_file: dict = field(default_factory=dict)
    glossary: list = field(default_factory=list)


class DialogueDB:
    """Thin, defensive wrapper over the SQLite project database."""

    def __init__(self) -> None:
        self.path = utils.DIALOGUE_DB
        self._con: sqlite3.Connection | None = None
        self._stats: DialogueStats | None = None

    # -- availability -------------------------------------------------------
    def available(self) -> bool:
        return self.path.exists()

    def _connect(self) -> sqlite3.Connection | None:
        if self._con is not None:
            return self._con
        if not self.available():
            return None
        try:
            uri = self.path.as_uri() + "?mode=ro"
            con = sqlite3.connect(uri, uri=True, check_same_thread=False)
            con.row_factory = sqlite3.Row
            self._con = con
            return con
        except Exception:
            return None

    # -- stats --------------------------------------------------------------
    def stats(self) -> DialogueStats:
        if self._stats is not None:
            return self._stats
        st = DialogueStats()
        con = self._connect()
        if con is None:
            self._stats = st
            return st
        try:
            st.sources = con.execute("SELECT COUNT(*) FROM source").fetchone()[0]
            st.entries = con.execute("SELECT COUNT(*) FROM entry").fetchone()[0]
            st.pc_rows = con.execute("SELECT COUNT(*) FROM pc_text").fetchone()[0]
            rows = con.execute(
                "SELECT status, COUNT(*) FROM source GROUP BY status").fetchall()
            for status, count in rows:
                if status == 0:
                    st.untranslated += count
                elif status == 1:
                    st.translated += count
                elif status == 2:
                    st.reviewed += count
            for origin, count in con.execute(
                    "SELECT origin, COUNT(*) FROM source GROUP BY origin"):
                st.by_origin[str(origin)] = count
            for cat, count in con.execute(
                    "SELECT category, COUNT(*) FROM entry GROUP BY category ORDER BY 2 DESC"):
                st.by_category[str(cat)] = count
            for f, count in con.execute(
                    "SELECT file, COUNT(*) FROM entry GROUP BY file ORDER BY 2 DESC LIMIT 400"):
                st.by_file[str(f)] = count
            row = con.execute("SELECT value FROM meta WHERE key='glossary'").fetchone()
            if row:
                try:
                    st.glossary = json.loads(row[0])
                except Exception:
                    st.glossary = []
        except Exception:
            pass
        self._stats = st
        return st

    # -- queries ------------------------------------------------------------
    def search_sources(self, query: str = "", file_filter: str | None = None,
                       status: int | None = None, origin: str | None = None,
                       offset: int = 0, limit: int = 300) -> list[DialogueRow]:
        con = self._connect()
        if con is None:
            return []
        where: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            where.append(r"(s.text LIKE ? ESCAPE '\' OR s.translation LIKE ? ESCAPE '\'"
                         r" OR s.plain LIKE ? ESCAPE '\')")
            params += [like, like, like]
        if file_filter:
            where.append(r"s.id IN (SELECT source_id FROM entry WHERE file LIKE ? ESCAPE '\')")
            params.append(f"%{_escape_like(file_filter)}%")
        if status is not None:
            where.append("s.status = ?")
            params.append(int(status))
        if origin:
            where.append("s.origin = ?")
            params.append(origin)
        sql = ("SELECT s.id, s.text, s.translation, s.status, s.origin, s.chars "
               "FROM source s")
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY s.id LIMIT ? OFFSET ?"
        params += [int(limit), int(offset)]
        try:
            rows = con.execute(sql, params).fetchall()
        except Exception:
            return []
        return [DialogueRow(id=r["id"], jp=r["text"] or "", en=r["translation"] or "",
                            status=int(r["status"] or 0), origin=str(r["origin"] or ""),
                            chars=int(r["chars"] or 0)) for r in rows]

    def count_sources(self, query: str = "", file_filter: str | None = None,
                      status: int | None = None, origin: str | None = None) -> int:
        con = self._connect()
        if con is None:
            return 0
        where: list[str] = []
        params: list = []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            where.append(r"(s.text LIKE ? ESCAPE '\' OR s.translation LIKE ? ESCAPE '\'"
                         r" OR s.plain LIKE ? ESCAPE '\')")
            params += [like, like, like]
        if file_filter:
            where.append(r"s.id IN (SELECT source_id FROM entry WHERE file LIKE ? ESCAPE '\')")
            params.append(f"%{_escape_like(file_filter)}%")
        if status is not None:
            where.append("s.status = ?")
            params.append(int(status))
        if origin:
            where.append("s.origin = ?")
            params.append(origin)
        sql = "SELECT COUNT(*) FROM source s"
        if where:
            sql += " WHERE " + " AND ".join(where)
        try:
            return int(con.execute(sql, params).fetchone()[0])
        except Exception:
            return 0

    def search_pc(self, query: str = "", offset: int = 0, limit: int = 300) -> list[dict]:
        con = self._connect()
        if con is None:
            return []
        q = (query or "").strip()
        if q:
            like = f"%{_escape_like(q)}%"
            sql = ("SELECT id, file, key, jp, en FROM pc_text "
                   r"WHERE jp LIKE ? ESCAPE '\' OR en LIKE ? ESCAPE '\' "
                   "ORDER BY id LIMIT ? OFFSET ?")
            params = [like, like, int(limit), int(offset)]
        else:
            sql = "SELECT id, file, key, jp, en FROM pc_text ORDER BY id LIMIT ? OFFSET ?"
            params = [int(limit), int(offset)]
        try:
            return [dict(r) for r in con.execute(sql, params).fetchall()]
        except Exception:
            return []

    def locations(self, source_id: int) -> list[dict]:
        con = self._connect()
        if con is None:
            return []
        try:
            rows = con.execute(
                "SELECT kind, file, entry, member, loc, category, context, label "
                "FROM entry WHERE source_id = ? ORDER BY id LIMIT 60", (int(source_id),)
            ).fetchall()
        except Exception:
            return []
        return [dict(r) for r in rows]

    def file_list(self) -> list[tuple[str, int]]:
        st = self.stats()
        return sorted(st.by_file.items(), key=lambda kv: kv[0].lower())

    def category_list(self) -> list[tuple[str, int]]:
        st = self.stats()
        return sorted(st.by_category.items(), key=lambda kv: (-kv[1], kv[0]))

    def glossary(self) -> list[dict]:
        return self.stats().glossary
