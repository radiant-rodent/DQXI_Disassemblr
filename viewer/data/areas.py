"""Map / area dossier: cross-references every asset family by area id.

Area ids follow the game's naming, e.g. ``b001_101a`` (field), ``a_010``
(scenario), ``d012_004a`` (dungeon).  Each family is normalised down to the
area id so one screen can show "everything about this map".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import utils

# area id extracted from a name, letter + digits, optional _NNN and suffix
_AREA_RE = re.compile(r"^([a-z])_?(\d{3})(?:_(\d{3})([a-z]))?", re.IGNORECASE)


def area_of(name: str) -> str | None:
    """Normalise an asset name to an area id (lower case, e.g. ``b001_101a``)."""
    base = name.strip().lower()
    base = base.rsplit(".", 1)[0]
    base = re.sub(r"_(2d|3d|cs|script|tcs|area)$", "", base)
    m = _AREA_RE.match(base)
    if not m:
        # extracted 3D scene meshes are prefixed, e.g. "Map_b001_101a_cs"
        prefixed = re.sub(r"^map_", "", base)
        if prefixed == base:
            return None
        return area_of(prefixed)
    letter, group, sub, sub_suffix = m.groups()
    if group == "000":
        return None
    if sub:
        return f"{letter}{group}_{sub}{sub_suffix or ''}"
    return f"{letter}{group}"


def area_prefix(name: str) -> str | None:
    """Coarser fallback for grouping (``b001`` style ids)."""
    m = _AREA_RE.match(name.strip().lower())
    if not m:
        return None
    letter, group, _, _ = m.groups()
    if group == "000":
        return None
    return f"{letter}{group}"


def area_sort_key(area: str) -> tuple:
    m = _AREA_RE.match(area)
    if not m:
        return (area, 0, 0)
    letter, group, sub, _ = m.groups()
    return (letter, int(group), int(sub or 0))


@dataclass
class AreaDossier:
    area: str
    textures: list = field(default_factory=list)
    scripts: list = field(default_factory=list)
    audio: list = field(default_factory=list)
    layouts: list = field(default_factory=list)
    models: list = field(default_factory=list)    # extracted 3D scene meshes
    level2d: list = field(default_factory=list)   # (name, size)
    level3d: list = field(default_factory=list)
    dialogue_total: int = 0
    dialogue_files: list = field(default_factory=list)

    @property
    def asset_count(self) -> int:
        return (len(self.textures) + len(self.scripts) + len(self.audio) +
                len(self.layouts) + len(self.models) + len(self.level2d) +
                len(self.level3d))


class AreaIndex:
    def __init__(self) -> None:
        self.areas: list[str] = []
        self.ready = False
        self._dossiers: dict[str, AreaDossier] = {}

    def ensure(self, textures, scripts, audio, layouts, dialogues=None,
               models=None) -> "AreaIndex":
        if self.ready:
            return self
        buckets: dict[str, AreaDossier] = {}

        def bucket(area: str) -> AreaDossier:
            d = buckets.get(area)
            if d is None:
                d = AreaDossier(area=area)
                buckets[area] = d
            return d

        # textures: dirs such as b001_101a_2d
        for pack, _count in textures.packs():
            area = area_of(pack)
            if area:
                bucket(area).textures.append(pack)

        # 3D scene meshes: model dirs such as Map_b001_101a_cs
        if models is not None:
            try:
                for model in models.items:
                    area = area_of(model.name)
                    if area:
                        bucket(area).models.append(model.name)
            except Exception:
                pass

        # scripts: dirs such as b001, b001c, a_010_cs_010, world, common
        for script in scripts.items:
            area = area_of(script.area)
            if area:
                bucket(area).scripts.append(script.area)

        # audio streams: A_010_CS_040_01
        for stream in audio.streams:
            area = area_of(stream.name)
            if area:
                bucket(area).audio.append(stream.name)

        # level packs from the reference workspace (filenames only)
        for base_dir, target in ((utils.LEVEL2D_DIR, "level2d"), (utils.LEVEL3D_DIR, "level3d")):
            if base_dir.exists():
                for pack in base_dir.glob("*.pack"):
                    area = area_of(pack.name)
                    if not area:
                        continue
                    try:
                        size = pack.stat().st_size
                    except OSError:
                        size = 0
                    getattr(bucket(area), target).append((pack.stem, size))

        # layout packs declared in the reference database metadata
        if dialogues is not None:
            try:
                st = dialogues.stats()
                meta_con = None
                con = dialogues._connect()
                if con is not None:
                    row = con.execute("SELECT value FROM meta WHERE key='layout_packs'").fetchone()
                    if row:
                        for entry in json.loads(row[0]):
                            name = Path(entry).stem
                            area = area_of(name)
                            if area:
                                bucket(area).layouts.append(name)
            except Exception:
                pass

        self._dossiers = {a: d for a, d in buckets.items() if d.asset_count > 0}
        self.areas = sorted(self._dossiers, key=area_sort_key)
        self.ready = True
        return self

    # -- queries ------------------------------------------------------------
    def all_areas(self) -> list[str]:
        return list(self.areas)

    def dossier(self, area: str) -> AreaDossier:
        return self._dossiers.get(area, AreaDossier(area=area))

    def refresh_dialogues(self, dialogues, dossier: AreaDossier, limit_files: int = 40) -> None:
        """Fill dialogue counts for one dossier (lazy, called by the UI)."""
        con = dialogues._connect() if dialogues is not None else None
        if con is None:
            return
        try:
            area = dossier.area
            like = f"%{area}%"
            dossier.dialogue_total = int(con.execute(
                r"SELECT COUNT(*) FROM entry WHERE file LIKE ? ESCAPE '\'", (like,)
            ).fetchone()[0])
            rows = con.execute(
                "SELECT file, COUNT(*) c FROM entry "
                r"WHERE file LIKE ? ESCAPE '\' GROUP BY file ORDER BY c DESC LIMIT ?",
                (like, limit_files)).fetchall()
            dossier.dialogue_files = [(str(r[0]), int(r[1])) for r in rows]
        except Exception:
            pass
