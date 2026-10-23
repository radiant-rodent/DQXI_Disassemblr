"""Squirrel script index (game_scripts/<area>/script.nut)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .. import utils

_FUNC_RE = re.compile(r"^\s*function '([^']+)'\(([^)]*)\)")


@dataclass
class Script:
    area: str
    path: Path
    size_bytes: int

    @property
    def name(self) -> str:
        return self.area


class ScriptIndex:
    def __init__(self) -> None:
        self.items: list[Script] = []
        self.ready = False
        self._cache: dict[str, str] = {}

    def ensure(self) -> "ScriptIndex":
        if self.ready:
            return self
        root = utils.SCRIPTS_DIR
        items: list[Script] = []
        if root.exists():
            for nut in root.rglob("*.nut"):
                if nut.name.endswith(".decompiled.nut"):  # shown via the disassembly's sibling
                    continue
                rel = nut.relative_to(root)
                area = rel.parts[0] if rel.parts else nut.stem
                try:
                    size = nut.stat().st_size
                except OSError:
                    size = 0
                items.append(Script(area=area, path=nut, size_bytes=size))
        items.sort(key=lambda s: s.area.lower())
        self.items = items
        self.ready = True
        return self

    def search(self, query: str = "") -> list[Script]:
        self.ensure()
        q = (query or "").strip().lower()
        if not q:
            return list(self.items)
        return [s for s in self.items if q in s.area.lower()]

    def text(self, script: Script) -> str:
        key = str(script.path)
        if key not in self._cache:
            if len(self._cache) > 40:
                self._cache.clear()
            self._cache[key] = utils.safe_read_text(script.path)
        return self._cache[key]

    def outline(self, script: Script) -> list[tuple[str, str, str]]:
        """(function name, args, comment line) for each function in the disassembly."""
        out = []
        for line in self.text(script).splitlines():
            m = _FUNC_RE.match(line)
            if m:
                comment = ""
                line_idx = line
                if "/*" in line_idx and "*/" in line_idx:
                    comment = line_idx.split("/*", 1)[1].split("*/", 1)[0].strip()
                out.append((m.group(1), m.group(2), comment))
        return out
