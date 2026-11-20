#!/usr/bin/env python3
"""Readable names for every decoded level: writes ``game_assets/maps/level_labels.json``.

The game only names places per area (``b011`` = Cobblestone, ``syscmn/level_area``); single rooms such as
``b011_105a`` have no name of their own. This tool builds a label from what the level contains:

* place name (``game_assets/maps/area_names.json``, exact code first, then the 4-letter group);
* the named characters who stand in it (speaker strings of ``param/region/rNNN/npc_ie``, translated through the
  3DS_Translate workspace ``project.db`` when it is present), e.g. "Dunstan, Gemma";
* the levels whose exits lead into it ("door from b011_001a");
* the variant letter: ``b``/``c``/``d`` levels are overlays of the ``a`` room (same place, other actors). They
  usually have no geometry of their own; the editor borrows the sibling's (all 555 sampled actors of such
  variants lie inside the ``a`` room's bounds);
* ``empty``: no objects and no 3D room at all (358 levels, e.g. every ``c002_*`` level is a 108-byte stub).

    python tools/level_labels.py
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "game_assets" / "maps"
OUT = MAPS / "level_labels.json"
BANKS = ROOT / "game_assets" / "text" / "banks" / "param" / "region"
DB = Path(r"..\3DS_Translate\workspace\project.db")

RUBY = re.compile(r"\{ruby:([^|}]*)\|[^}]*\}")


def plain(text: str) -> str:
    return RUBY.sub(r"\1", text).strip()


def english_names(jp: set[str]) -> dict[str, str]:
    if not DB.is_file() or not jp:
        return {}
    out: dict[str, str] = {}
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        for name in jp:
            row = con.execute(
                "select translation from source where plain=? and translation is not null and translation != '' limit 1",
                (name,),
            ).fetchone()
            if row:
                out[name] = " ".join(row[0].split())
    finally:
        con.close()
    return out


def room_name(level: str) -> str:
    """Town rooms: 0xx are the outdoor areas, 1xx the building interiors their doors lead into (b011_001a has doors
    into all 15 houses b011_101a..115a). Elsewhere the number is just kept."""
    sub = level[5:8]
    if level[0] == "b" and sub.isdigit():
        n = int(sub)
        if n < 100:
            return f"outdoors {n}"
        if n < 200:
            return f"interior {n - 100}"
    return f"area {sub}" if sub.isdigit() else level


def background_obj(level: str, bch: str | None) -> bool:
    if not bch:
        return False
    rel = Path(bch.replace("\\", "/"))
    try:
        rel = rel.relative_to("game_data")
    except ValueError:
        return False
    folder = ROOT / "game_assets" / "models" / rel.with_suffix("")
    return any(
        (folder / name).is_file() for name in (f"{rel.stem}.obj", f"Map_{level}.obj", f"Map_{level}_cs.obj")
    )


def main() -> int:
    areas = json.loads((MAPS / "area_names.json").read_text(encoding="utf-8"))
    entity = json.loads((MAPS / "entity_models.json").read_text(encoding="utf-8"))
    regions = entity.get("level_regions", {})
    map_names: list[str] = entity.get("maps", [])
    talks = json.loads((MAPS / "npc_talks.json").read_text(encoding="utf-8"))

    # speaker of every region character: talk[N] in the bank location == character id N
    speakers: dict[tuple[int, int], str] = {}
    for bank in BANKS.glob("r*/npc_ie.json"):
        region = int(bank.parent.name[1:])
        for e in json.loads(bank.read_text(encoding="utf-8")).get("entries", []):
            if e.get("role") != "speaker":
                continue
            m = re.match(r"talk\[(\d+)\]", e.get("location", ""))
            if m:
                speakers.setdefault((region, int(m.group(1))), plain(e["text"]))
    english = english_names(set(speakers.values()))

    scenes: dict[str, dict] = {}
    for path in sorted(MAPS.glob("*/scene.json")):
        scenes[path.parent.name] = json.loads(path.read_text(encoding="utf-8"))

    own_geo = {m: background_obj(m, s.get("background_bch")) for m, s in scenes.items()}

    # exits: who leads into whom
    entered_from: dict[str, list[str]] = defaultdict(list)
    for m, s in scenes.items():
        for o in s.get("objects", []):
            if o.get("kind") != "exit":
                continue
            dest = next((p["value"] for p in o.get("props", []) if p["name"] == "destination map"), None)
            if dest is not None and 0 <= dest < len(map_names):
                target = map_names[dest]
                if target and target != m and m not in entered_from[target]:
                    entered_from[target].append(m)

    out: dict[str, dict] = {}
    for m, s in scenes.items():
        group = m[:4]
        place = areas.get(m) or areas.get(group) or f"unnamed area {group}"
        variant = m[-1] if m[-1].isalpha() else ""
        geometry = m if own_geo[m] else None
        if geometry is None:
            for letter in "abcd":
                sib = m[:-1] + letter
                if sib != m and own_geo.get(sib):
                    geometry = sib
                    break
        region = regions.get(m, -1)
        chars = talks.get("regions", {}).get(str(region + 1), {}).get("characters", {})
        kinds: Counter = Counter()
        names: list[str] = []
        for o in s.get("objects", []):
            kinds[o.get("kind")] += 1
            if o.get("kind") != "actor":
                continue
            p = {x["name"]: x["value"] for x in o.get("props", [])}
            ident = p.get("entity id")
            if ident is not None and chars.get(str(ident), {}).get("talks"):
                kinds["npc"] += 1
            name = speakers.get((region + 1, ident)) if ident is not None else None
            if name:
                name = english.get(name, name)
                if name not in names:
                    names.append(name)
        objects = sum(v for k, v in kinds.items() if k != "npc")
        empty = objects == 0 and geometry is None

        detail: list[str] = []
        if names:
            detail.append(", ".join(names[:3]) + (" +" if len(names) > 3 else ""))
        sources = entered_from.get(m, [])
        if sources:
            shown = [room_name(src) if src[:4] == group else f"{areas.get(src[:4], src[:4])} {room_name(src)}" for src in sources]
            shown = list(dict.fromkeys(shown))
            detail.append("door from " + ", ".join(shown[:2]) + (" +" if len(shown) > 2 else ""))
        if variant and variant != "a":
            detail.append(f"variant {variant} of {m[:-1]}a")
        if empty:
            summary = "empty stub (no objects, no 3D room)"
        else:
            bits = []
            if geometry == m:
                bits.append("3D room")
            elif geometry:
                bits.append(f"room of {geometry}")
            else:
                bits.append("no 3D room (2D mode / script only)")
            if kinds["npc"]:
                bits.append(f"{kinds['npc']} talking NPC" + ("s" if kinds["npc"] != 1 else ""))
            other = kinds["actor"] - kinds["npc"]
            if other:
                bits.append(f"{other} other actor" + ("s" if other != 1 else ""))
            if kinds["exit"]:
                bits.append(f"{kinds['exit']} exit" + ("s" if kinds["exit"] != 1 else ""))
            summary = ", ".join(bits)
        title = f"{place} \u00b7 {room_name(m)}{variant if variant not in ("", "a") else ""}" + (f" \u00b7 {detail[0]}" if detail else "")
        out[m] = {
            "title": title,
            "place": place,
            "group": f"{group} \u00b7 {areas.get(group) or place}",
            "details": detail,
            "summary": summary,
            "geometry": geometry,
            "empty": empty,
            "characters": names,
            "entered_from": sources,
        }

    OUT.write_text(json.dumps({"format": "DQXI_LEVEL_LABELS", "levels": out}, indent=1, ensure_ascii=False), encoding="utf-8")
    empty = sum(v["empty"] for v in out.values())
    borrowed = sum(1 for k, v in out.items() if v["geometry"] and v["geometry"] != k)
    named = sum(1 for v in out.values() if v["characters"])
    print(f"wrote {OUT}: {len(out)} levels, {empty} empty stubs, {borrowed} borrow a sibling's room, {named} with named characters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
