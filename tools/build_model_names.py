#!/usr/bin/env python3
"""Build a model-id -> in-game-name index.

Sources:
- `game_assets/tables/packs/gamecmn/enemy_base.json` (monster model code + name)
- `game_assets/tables/packs/syscmn/item.json` (weapons, shields, armour, ...):
  item `+0x24` holds two rows of `res_model3d` (low half: field model such as
  `w1003`, high half: battle model such as `w1603`) and the low byte of `+0x28`
  is the colour variant (0 -> `a`, 1 -> `b`, ...). So item ほのおのブーメラン
  maps to `w1003b` and `w1603b`.
- the translation workspace `project.db` (English translations, read-only),
  matched on the Japanese plain text
- known playable-character model families
- `game_assets/tables/packs/syscmn/level_area.json` (area code -> place name),
  written to `game_assets/maps/area_names.json`

The result is `game_assets/models/model_names.json`, used by the viewer and by
asset reports. Names that are not available are simply omitted; a model shared
by several items keeps the first (lowest item id) name.
"""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "game_assets/tables/packs"
ENEMY = TABLES / "gamecmn/enemy_base.json"
ITEM = TABLES / "syscmn/item.json"
RES_MODEL3D = TABLES / "gamecmn/res_model3d.json"
MODELS = ROOT / "game_assets/models/packs/3d/model"
DB = Path(r"..\reference project\workspace\project.db")
OUT = ROOT / "game_assets/models/model_names.json"
LEVEL_AREA = TABLES / "syscmn/level_area.json"
AREA_OUT = ROOT / "game_assets/maps/area_names.json"

# Only families verified by rendering the model. Other cha* models are story
# NPCs whose names are not in any table we decode yet.
CHARACTERS = {
    "cha01000a": "The Luminary",
}

RUBY = re.compile("\x01(.*?)\x02.*?\x03", re.S)


def clean_name(text: str) -> str:
    text = text.replace("{noun}", "").replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", text).strip()


def plain_jp(text: str) -> str:
    """Item strings carry furigana as \\x01base\\x02reading\\x03; keep the base."""
    return RUBY.sub(r"\1", text)


def preview_string(cell: dict) -> str:
    preview = cell.get("$preview") if isinstance(cell, dict) else None
    if not preview:
        return ""
    try:
        return bytes.fromhex(preview).split(b"\0")[0].decode("ascii", "ignore").strip("@")
    except ValueError:
        return ""


def jp_translations() -> dict[str, str]:
    """Japanese plain text -> English, for item names."""
    out: dict[str, str] = {}
    if not DB.is_file():
        return out
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    for plain, translation in con.execute(
        "select s.plain, s.translation from entry e join source s on s.id=e.source_id "
        "where e.entry='item.bxon' and s.translation is not null"
    ):
        out.setdefault(plain, clean_name(translation))
    con.close()
    return out


def enemy_names(names: dict[str, str]) -> int:
    data = json.loads(ENEMY.read_text(encoding="utf-8"))
    root = data.get("root", [])
    translations: dict[int, str] = {}
    if DB.is_file():
        con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
        for seq, translation in con.execute(
            "select e.seq, s.translation from entry e join source s on s.id=e.source_id "
            "where e.entry='enemy_base.bxon' and s.translation is not null order by e.seq"
        ):
            translations[int(seq)] = clean_name(translation)
        con.close()
    base_seq = min(translations) if translations else 0
    added = 0
    for index, entry in enumerate(root):
        code = preview_string(entry.get("+0x10", {})).lower()
        name = translations.get(base_seq + index)
        if code and name and code not in names:
            names[code] = name
            added += 1
    return added


def item_names(names: dict[str, str]) -> int:
    if not ITEM.is_file() or not RES_MODEL3D.is_file():
        return 0
    codes = [preview_string(e.get("+0x00", {})).lower()
             for e in json.loads(RES_MODEL3D.read_text(encoding="utf-8"))["root"]]
    english = jp_translations()
    exported = {p.name.lower() for p in MODELS.iterdir()} if MODELS.is_dir() else set()
    added = 0
    for entry in json.loads(ITEM.read_text(encoding="utf-8"))["root"]:
        jp = plain_jp(entry.get("+0x00", {}).get("$string", ""))
        name = english.get(jp) or clean_name(jp)
        models = entry.get("+0x24", {}).get("u32")
        if not name or models is None or models == 0xFFFFFFFF:
            continue
        variant = chr(ord("a") + (entry.get("+0x28", {}).get("u32", 0) & 0xFF))
        for row in (models & 0xFFFF, models >> 16):
            if row >= len(codes) or not codes[row]:
                continue
            code = codes[row]
            key = f"{code}{variant}" if f"{code}{variant}" in exported else code
            if key not in names:
                names[key] = name
                added += 1
    return added


def area_names() -> dict[str, str]:
    """Area code (f001, b001, p206, ...) -> place name, from `level_area`."""
    if not LEVEL_AREA.is_file():
        return {}
    english: dict[str, str] = {}
    if DB.is_file():
        con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
        for plain, translation in con.execute(
            "select s.plain, s.translation from entry e join source s on s.id=e.source_id "
            "where e.entry='level_area.bxon' and s.translation is not null"
        ):
            english.setdefault(plain, clean_name(translation))
        con.close()
    out: dict[str, str] = {}
    for entry in json.loads(LEVEL_AREA.read_text(encoding="utf-8"))["root"]:
        code = preview_string(entry.get("+0x10", {})).lower()
        jp = plain_jp(entry.get("+0x0C", {}).get("$string", "") if isinstance(entry.get("+0x0C"), dict) else "")
        name = english.get(jp) or clean_name(jp)
        if code and name:
            out.setdefault(code, name)
    return out


def main() -> int:
    names: dict[str, str] = dict(CHARACTERS)
    enemies = enemy_names(names)
    items = item_names(names)
    # exported folders carry detail suffixes (cha01000a_h / _l): inherit the base name
    if MODELS.is_dir():
        for folder in MODELS.iterdir():
            stem = folder.name.lower()
            base = re.sub(r"_[hl]$", "", stem)
            if base != stem and base in names:
                names.setdefault(stem, names[base])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(names.items())), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}: {len(names)} names ({enemies} monsters, {items} item models)")
    areas = area_names()
    AREA_OUT.parent.mkdir(parents=True, exist_ok=True)
    AREA_OUT.write_text(json.dumps(dict(sorted(areas.items())), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {AREA_OUT}: {len(areas)} area names")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
