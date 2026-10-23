"""Texture library index (game_textures/*/timg/*.png + *.meta.json)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .. import utils


@dataclass
class Texture:
    name: str                    # png stem, e.g. "b001_101a"
    path: Path                   # absolute png path
    pack: str                    # group directory, e.g. "b001_101a_2d"
    rel: str                     # path relative to game_textures
    size_bytes: int
    meta: dict = field(default_factory=dict)

    @property
    def width(self) -> int | None:
        return self.meta.get("width")

    @property
    def height(self) -> int | None:
        return self.meta.get("height")

    @property
    def fmt(self) -> str:
        return str(self.meta.get("format_name") or "-")

    @property
    def dims(self) -> str:
        w, h = self.width, self.height
        return f"{w}x{h}" if w and h else "-"


class TextureIndex:
    """Lazily-built catalogue of every extracted texture."""

    def __init__(self) -> None:
        self.items: list[Texture] = []
        self.ready = False
        self.by_stem: dict[str, list[Texture]] = {}
        self._packs: dict[str, int] = {}

    # -- construction -------------------------------------------------------
    def ensure(self) -> "TextureIndex":
        if self.ready:
            return self
        root = utils.TEXTURES_DIR
        items: list[Texture] = []
        if root.exists():
            for png in root.rglob("*.png"):
                pack = png.relative_to(root).parts[0] if png.relative_to(root).parts else ""
                meta = {}
                meta_path = png.with_name(png.stem + ".meta.json")
                if meta_path.exists():
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    except Exception:
                        meta = {}
                try:
                    size = png.stat().st_size
                except OSError:
                    size = 0
                items.append(Texture(
                    name=png.stem,
                    path=png,
                    pack=pack,
                    rel=str(png.relative_to(root)).replace("\\", "/"),
                    size_bytes=size,
                    meta=meta,
                ))
        items.sort(key=lambda t: (t.pack.lower(), t.name.lower()))
        self.items = items
        self.by_stem = {}
        self._packs = {}
        for t in items:
            self.by_stem.setdefault(t.name.lower(), []).append(t)
            self._packs[t.pack] = self._packs.get(t.pack, 0) + 1
        self.ready = True
        return self

    # -- queries ------------------------------------------------------------
    def packs(self) -> list[tuple[str, int]]:
        self.ensure()
        return sorted(self._packs.items(), key=lambda kv: kv[0].lower())

    def search(self, query: str = "", pack: str | None = None,
               limit: int | None = None) -> list[Texture]:
        self.ensure()
        q = (query or "").strip().lower()
        out: list[Texture] = []
        for t in self.items:
            if pack and t.pack != pack:
                continue
            if q and q not in t.name.lower() and q not in t.pack.lower():
                continue
            out.append(t)
            if limit and len(out) >= limit:
                break
        return out

    def resolve(self, name: str) -> Texture | None:
        """Best match for a texture reference such as ``background_2d.bflim``."""
        self.ensure()
        stem = Path(name).stem.lower()
        for cand in (stem, stem.rsplit("_", 1)[0]):
            hits = self.by_stem.get(cand)
            if hits:
                return hits[0]
        return None

    def find_in_pack(self, pack: str, name: str) -> Texture | None:
        self.ensure()
        stem = Path(name).stem.lower()
        for t in self.items:
            if t.pack == pack and t.name.lower() == stem:
                return t
        return None

    @property
    def total_bytes(self) -> int:
        self.ensure()
        return sum(t.size_bytes for t in self.items)
