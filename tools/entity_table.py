#!/usr/bin/env python3
"""Resolve level actor ids to models: writes ``game_assets/maps/entity_models.json``.

An actor record in a level (container +0x1F0, docs/LEVEL_FORMAT.md) has an entity word at +0x5C =
``(class << 16) | id``. For class ``0x300`` the id is a row of ``gamecmn/enemy_base`` (checked in the
emulator: id 108 is row 108 -> model ``m043a`` -> "Jargon", the purple monster that appeared); the row's
``model`` field names the model and ``game_assets/models/model_names.json`` gives its English name.
Other classes (NPCs) are not resolved yet.

    python -m tools.entity_table
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "game_assets" / "maps" / "entity_models.json"


def build() -> dict:
    from tools.table_edit import Table

    names = json.loads((ROOT / "game_assets" / "models" / "model_names.json").read_text(encoding="utf-8"))
    table = Table("gamecmn/enemy_base.json")
    fields = table.fields()
    by_name = {f["name"] if isinstance(f, dict) else f.name: f for f in fields}
    monsters = []
    for row in range(len(table.rows) if hasattr(table, "rows") and not callable(table.rows) else 1043):
        try:
            model = table.read(row, by_name["model"])
            jp = table.read(row, by_name["name"])
        except Exception:
            break
        model = str(model or "")
        monsters.append({
            "id": row,
            "model": model,
            "name": names.get(model) or names.get(model + "_h") or "",
            "jp": str(jp or "").replace("\n", ""),
        })
    regions, tables = npc_tables(names)
    return {"format": "DQXI_ENTITY_MODELS", "monster_class": 0x300, "monsters": monsters, "maps": map_names(),
            "level_regions": regions, "npc_tables": tables, "fixed_drops": fixed_drops()}


def model_name_list() -> list[str]:
    """Every model name of ``gamecmn/res_model3d.bxon`` in file order (the order the region tables index)."""
    import re

    raw = (ROOT / "game_data" / "packs" / "gamecmn" / "res_model3d.bxon").read_bytes()
    first = raw.find(b"cha01100")
    return [m.group().decode() for m in re.finditer(rb"[a-z]{1,4}\d{3,5}[a-z]?", raw[first - 4:])]


def npc_tables(names: dict) -> tuple[dict, dict]:
    """How an actor id becomes a model (verified in the emulator, docs/LEVEL_FORMAT.md).

    The level's row in ``syscmn/level_map`` names its region in the low byte of the word at +4; the region's
    ``param/region/r<region+1>/npc_list.bxon`` (26-byte rows, 13 u16) has one row per actor id: word 7 indexes the
    model name list of ``res_model3d``, the low byte of word 9 is the model variant (0 = a, 1 = b, ...).
    """
    import struct

    lm = (ROOT / "game_data" / "packs" / "syscmn" / "level_map.bxon").read_bytes()
    regions: dict[str, int] = {}
    for i in range((len(lm) - 0x2C) // 28):
        base = 0x2C + i * 28
        at = (base + struct.unpack_from("<I", lm, base)[0]) & 0xFFFFFFFF
        name = lm[at:at + 24].split(b"\0")[0].decode("ascii", "replace") if at < len(lm) else ""
        if name:
            regions[name] = lm[base + 4]
    listing = model_name_list()
    tables: dict[str, list] = {}
    for path in sorted((ROOT / "game_data" / "packs" / "param" / "region").glob("r*/npc_list.bxon")):
        number = int(path.parent.name[1:])
        if number >= 900:
            continue
        raw = path.read_bytes()
        rows = []
        for k in range((len(raw) - 0x2C) // 26):
            w = struct.unpack_from("<13H", raw, 0x2C + k * 26)
            if w[7] >= len(listing):
                rows.append("")
                continue
            stem = listing[w[7]]
            model = stem + "abcdefgh"[(w[9] & 0xFF) % 8] if stem[0] in "cm" else stem
            rows.append(model)
        tables[str(number - 1)] = rows
    return regions, tables


def fixed_drops() -> list[list[int]]:
    """Rows of fieldcmn/fixed_drop_param.bxon (8 bytes: u16 item, u16 count): the contents a gimmick record's drop row points at."""
    import struct

    raw = (ROOT / "game_data" / "packs" / "fieldcmn" / "fixed_drop_param.bxon").read_bytes()
    return [list(struct.unpack_from("<HH", raw, 0x2C + 8 * i)) for i in range((len(raw) - 0x2C) // 8)]


def map_names() -> list[str]:
    """Level name of every map id: row i of syscmn/level_map.bxon (28-byte rows, name pointer at +0)."""
    import struct

    raw = (ROOT / "game_data" / "packs" / "syscmn" / "level_map.bxon").read_bytes()
    out = []
    for i in range((len(raw) - 0x2C) // 28):
        base = 0x2C + i * 28
        rel = struct.unpack_from("<I", raw, base)[0]
        at = (base + rel) & 0xFFFFFFFF
        out.append(raw[at:at + 24].split(b"\0")[0].decode("ascii", "replace") if at < len(raw) else "")
    return out


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    named = sum(1 for m in data["monsters"] if m["name"])
    print(f"{len(data['monsters'])} monster rows ({named} with an English name) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
