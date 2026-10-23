"""UI layout index (game_layouts/<pack>/*.layout.json + *.anim.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .. import utils


@dataclass
class Layout:
    pack: str          # top level pack dir, e.g. "battle_2d"
    stem: str          # "battle_2d_lw.layout"
    path: Path
    kind: str          # "layout" | "anim"
    size_bytes: int


class LayoutIndex:
    def __init__(self) -> None:
        self.items: list[Layout] = []
        self.ready = False
        self._json_cache: dict[str, dict] = {}
        self._packs: dict[str, int] = {}

    def ensure(self) -> "LayoutIndex":
        if self.ready:
            return self
        root = utils.LAYOUTS_DIR
        items: list[Layout] = []
        if root.exists():
            for path in root.rglob("*.json"):
                rel = path.relative_to(root)
                pack = rel.parts[0] if len(rel.parts) > 1 else ""
                name = path.name
                if name.endswith(".anim.json"):
                    kind = "anim"
                elif name.endswith(".layout.json"):
                    kind = "layout"
                else:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                items.append(Layout(pack=pack, stem=name, path=path, kind=kind, size_bytes=size))
        items.sort(key=lambda l: (l.pack.lower(), l.kind, l.stem.lower()))
        self.items = items
        self._packs = {}
        for l in items:
            self._packs[l.pack] = self._packs.get(l.pack, 0) + 1
        self.ready = True
        return self

    def packs(self) -> list[tuple[str, int]]:
        self.ensure()
        return sorted(self._packs.items(), key=lambda kv: kv[0].lower())

    def search(self, query: str = "", pack: str | None = None, kind: str | None = None) -> list[Layout]:
        self.ensure()
        q = (query or "").strip().lower()
        out = []
        for l in self.items:
            if pack and l.pack != pack:
                continue
            if kind and l.kind != kind:
                continue
            if q and q not in l.stem.lower() and q not in l.pack.lower():
                continue
            out.append(l)
        return out

    def load(self, path: Path | str) -> dict:
        key = str(path)
        cached = self._json_cache.get(key)
        if cached is not None:
            return cached
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if len(self._json_cache) > 300:
            self._json_cache.clear()
        self._json_cache[key] = data
        return data

    def resolve_texture(self, name: str):
        """Resolve a BFLIM reference from a layout to an extracted texture."""
        from . import textures as tex_mod

        self._tex_index = getattr(self, "_tex_index", None) or tex_mod.TextureIndex().ensure()
        return self._tex_index.resolve(name)
