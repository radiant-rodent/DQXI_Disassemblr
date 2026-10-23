"""Model library index.

The current model export lives under ``game_models/by_category/<Category>/<Model>/``
with one OBJ (+ MTL/glTF/binary sidecars) per model, grouped into Characters,
Monsters, Weapons and Environments.  Older flat exports (``<group>/<mesh>.obj``)
are still understood so the panel keeps working with historical extractions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import utils


@dataclass
class Model:
    name: str        # model name, e.g. "Hero_TheLuminary" or "Slime"
    category: str    # "Characters" | "Monsters" | "Weapons" | "Environments"
    obj: Path
    mtl: Path | None
    gltf: Path | None
    bin: Path | None
    size_bytes: int
    textures: list[Path] = field(default_factory=list)

    @property
    def directory(self) -> Path:
        return self.obj.parent

    @property
    def rel_dir(self) -> str:
        try:
            return str(self.obj.parent.relative_to(utils.MODELS_DIR)).replace("\\", "/")
        except ValueError:
            return str(self.obj.parent)

    @property
    def sidecars(self) -> list[str]:
        out = []
        if self.mtl is not None:
            out.append("mtl")
        if self.gltf is not None:
            out.append("gltf")
        if self.bin is not None:
            out.append("bin")
        if self.textures:
            out.append(f"{len(self.textures)} png")
        return out


class ModelIndex:
    def __init__(self) -> None:
        self.items: list[Model] = []
        self.ready = False
        self._categories: dict[str, int] = {}
        self._by_name: dict[str, Model] = {}

    # -- construction -------------------------------------------------------
    def ensure(self) -> "ModelIndex":
        if self.ready:
            return self
        root = utils.MODELS_DIR
        items: list[Model] = []
        if root.exists():
            for obj in root.rglob("*.obj"):
                rel = obj.relative_to(root)
                name, category = _name_and_category(rel, obj)
                mtl = obj.with_suffix(".mtl")
                gltf = obj.with_suffix(".gltf")
                binc = obj.with_suffix(".bin")
                texs = list(obj.parent.glob("*.png"))
                try:
                    size = obj.stat().st_size
                except OSError:
                    size = 0
                items.append(Model(
                    name=name,
                    category=category,
                    obj=obj,
                    mtl=mtl if mtl.exists() else None,
                    gltf=gltf if gltf.exists() else None,
                    bin=binc if binc.exists() else None,
                    size_bytes=size,
                    textures=texs,
                ))
        items.sort(key=lambda m: (m.category.lower(), m.name.lower()))
        self.items = items
        self._categories = {}
        self._by_name = {}
        for m in items:
            self._categories[m.category] = self._categories.get(m.category, 0) + 1
            self._by_name.setdefault(m.name.lower(), m)
        self.ready = True
        return self

    # -- queries ------------------------------------------------------------
    def categories(self) -> list[tuple[str, int]]:
        self.ensure()
        return sorted(self._categories.items(), key=lambda kv: kv[0].lower())

    # alias kept for older callers
    def groups(self) -> list[tuple[str, int]]:
        return self.categories()

    def get(self, name: str) -> Model | None:
        self.ensure()
        return self._by_name.get((name or "").lower())

    def search(self, query: str = "", category: str | None = None) -> list[Model]:
        self.ensure()
        q = (query or "").strip().lower()
        out = []
        for m in self.items:
            if category and m.category != category:
                continue
            if q and q not in m.name.lower() and q not in m.category.lower():
                continue
            out.append(m)
        return out

    @property
    def total_bytes(self) -> int:
        self.ensure()
        return sum(m.size_bytes for m in self.items)


def _name_and_category(rel: Path, obj: Path) -> tuple[str, str]:
    """Derive (model name, category) from a path relative to game_models."""
    parts = rel.parts
    if len(parts) >= 3:
        return parts[-2], parts[-3]          # by_category/<Category>/<Model>/<file>.obj
    if len(parts) == 2:
        return obj.stem, parts[0]            # legacy <group>/<mesh>.obj
    return obj.stem, ""
