"""Parameter table index (game_tables/<category>/*.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .. import utils


@dataclass
class Table:
    category: str
    name: str
    path: Path
    size_bytes: int


class TableIndex:
    def __init__(self) -> None:
        self.items: list[Table] = []
        self.ready = False
        self._cache: dict[str, dict] = {}
        self._categories: dict[str, int] = {}

    def ensure(self) -> "TableIndex":
        if self.ready:
            return self
        root = utils.TABLES_DIR
        items: list[Table] = []
        if root.exists():
            for path in root.rglob("*.json"):
                rel = path.relative_to(root)
                category = rel.parts[0] if len(rel.parts) > 1 else "(root)"
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                items.append(Table(category=category, name=path.stem, path=path, size_bytes=size))
        items.sort(key=lambda t: (t.category.lower(), t.name.lower()))
        self.items = items
        self._categories = {}
        for t in items:
            self._categories[t.category] = self._categories.get(t.category, 0) + 1
        self.ready = True
        return self

    def categories(self) -> list[tuple[str, int]]:
        self.ensure()
        return sorted(self._categories.items(), key=lambda kv: kv[0].lower())

    def search(self, query: str = "", category: str | None = None) -> list[Table]:
        self.ensure()
        q = (query or "").strip().lower()
        out = []
        for t in self.items:
            if category and t.category != category:
                continue
            if q and q not in t.name.lower() and q not in t.category.lower():
                continue
            out.append(t)
        return out

    def load(self, table: Table | Path | str) -> dict:
        path = table.path if isinstance(table, Table) else Path(table)
        key = str(path)
        data = self._cache.get(key)
        if data is None:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - defensive
                data = {"error": f"failed to parse: {exc}"}
            if len(self._cache) > 60:
                self._cache.clear()
            self._cache[key] = data
        return data

    def summary(self, table: Table) -> str:
        try:
            data = self.load(table)
        except Exception:
            return "-"
        if not isinstance(data, dict):
            return type(data).__name__
        bits = []
        if "type" in data:
            bits.append(str(data["type"]))
        if "raw_size" in data:
            bits.append(f"{data['raw_size']} B binary")
        if data.get("strings_count") is not None:
            bits.append(f"{data['strings_count']} strings")
        for key, value in data.items():
            if key in ("type", "raw_size", "strings_count", "strings"):
                continue
            if isinstance(value, list):
                bits.append(f"{len(value)} x {key}")
        return ", ".join(bits) if bits else "(no scalar metadata)"
