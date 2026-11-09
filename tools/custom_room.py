#!/usr/bin/env python3
"""Build the demo mod "Cellar below the church": a custom room reached through an existing exit, with a custom
texture, generated collision, a monster, a chest holding a different item and an NPC who says new lines.

Everything here is made from pieces that are individually emulator-proven (docs/MODEL_IMPORT.md, docs/COLLISION.md,
docs/LEVEL_FORMAT.md, docs/GIMMICK_DECOMP.md, docs/DIALOGUE_FORMAT.md):

    python tools/custom_room.py build [--mod DIR] [--item N] [--line TEXT]

* slot            level_map row 114 = `b002_106a`; the house `b002_105a` is cloned into it (`new_map.clone`)
* room            `tools/assets/custom_room/full_room.obj` (all 27 draws) + `checker.png` over the wood texture
* collision       `rcb_tool.from_obj` on `open_walls.obj`: only the four walls are solid
* entrance        the church (`b002_101a`) exit now leads to map id 114
* chest           the house's gimmick (drop row 101) -> `fieldcmn/fixed_drop_param` row 101 = item `--item`
* monster         the house's class-0x300 actor gets another monster row of the region table
* NPC             the house's NPC (entity id 46, region 21) talks `--line` (all its text lines in `npc_ie`)
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ASSETS = Path(__file__).resolve().parent / "assets" / "custom_room"
import os

# CR_DONOR=church clones the Heliodor church (its camera follows the hero; the house's camera hides him behind the front wall)
if os.environ.get("CR_DONOR") == "church":
    DONOR, DONOR_ID, NPC_ID, NPC_OFFSET = "b002_101a", 109, 182, "0x152C"
else:
    DONOR, DONOR_ID, NPC_ID, NPC_OFFSET = "b002_105a", 113, 46, "0x1568"
DUP_POS = [0.0, 0.5, -3.0] if os.environ.get("CR_DONOR") == "church" else [-1.5, 0.0, -2.0]   # the extra NPC: in front of the arrival point
SLOT = "b002_106a"           # level_map row 114
SLOT_ID = 114
CHEST_ROW = 101              # drop row of the house's first gimmick


# floor footprint (x0, x1, z0, z1) of the room model: the donor's own collision stays in force, so the model has to sit inside it
FOOTPRINT = (-4.0, 5.0, -5.0, 5.0) if os.environ.get("CR_DONOR") == "church" else (-5.0, 5.0, -4.0, 4.0)


def room_obj(x0: float, x1: float, z0: float, z1: float, h: float = 3.0) -> str:
    """OBJ text of draw0: a floor and back / left / right walls (the front stays open so the camera sees in)."""
    quads = [
        [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)],        # floor
        [(x0, 0, z0), (x1, 0, z0), (x1, h, z0), (x0, h, z0)],        # back
        [(x0, 0, z0), (x0, 0, z1), (x0, h, z1), (x0, h, z0)],        # left
        [(x1, 0, z0), (x1, 0, z1), (x1, h, z1), (x1, h, z0)],        # right
    ]
    uv = [(0, 0), (3, 0), (3, 1), (0, 1)]
    out = ["o draw0"]
    for q in quads:
        out += [f"v {a} {b} {c}" for a, b, c in q]
    for _ in quads:
        out += [f"vt {u} {v}" for u, v in uv]
    for k in range(len(quads)):
        i = 4 * k + 1
        out.append(f"f {i}/{i} {i + 1}/{i + 1} {i + 2}/{i + 2} {i + 3}/{i + 3}")
        out.append(f"f {i + 3}/{i + 3} {i + 2}/{i + 2} {i + 1}/{i + 1} {i}/{i}")
    return chr(10).join(out)


def build_model(work: Path) -> Path:
    from tools import bch_texture_patch, bch_writer, model_import

    src = ROOT / "game_data" / "packs" / "3d" / "bg" / DONOR / f"{DONOR}.bch"
    raw = src.read_bytes()
    draws = len(bch_writer.draw_calls(raw))
    # draw0 = the room (full_room.obj's first group); every other draw becomes one tiny triangle far below the floor
    first = room_obj(*FOOTPRINT)
    # OBJ indices are global: the room's vertices come first, the dummies follow
    nv = sum(1 for ln in first.splitlines() if ln.startswith("v "))
    lines = [first]
    for d in range(1, draws):
        base = nv + 3 * (d - 1)
        lines += [f"o draw{d}", "v 0 -50 0", "v 0.01 -50 0", "v 0 -50 0.01", "vt 0 0", "vt 1 0", "vt 0 1", f"f {base + 1} {base + 2} {base + 3}"]
    obj = work / "room_all.obj"
    obj.write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    data, _info = model_import.import_scene(raw, obj, src)
    textures = bch_texture_patch.texture_infos(data)
    name = "tj_b002_wood01" if DONOR == "b002_105a" else textures[0]["name"]
    data = bch_texture_patch.replace_texture(data, name, ASSETS / "checker.png", allow_resize=True)
    out = work / "room.bch"
    out.write_bytes(data)
    return out


def build_collision(work: Path) -> Path:
    from tools import rcb_tool

    src = ROOT / "game_data" / "packs" / "3d" / "bg" / DONOR / f"{DONOR}_chit.rcb"
    out = work / f"{SLOT}_chit.rcb"
    out.write_bytes(rcb_tool.from_obj(src.read_bytes(), ASSETS / "open_walls.obj"))
    return out


def level_edits(raw: bytes, monster_row: int | None) -> bytes:
    """Edits of the cloned house level: the monster actor gets another row of the region table."""
    scene = json.loads((ROOT / "game_assets" / "maps" / DONOR / "scene.json").read_text(encoding="utf-8"))
    out = bytearray(raw)
    for obj in scene["objects"]:
        if obj["kind"] != "actor":
            continue
        props = {p["name"]: p for p in obj["props"]}
        if props["entity class"]["value"] == 0x300 and monster_row is not None:
            struct.pack_into("<H", out, int(props["entity id"]["offset"], 16), monster_row)
    return bytes(out)


def pick_monster_row(avoid: int) -> int | None:
    doc = json.loads((ROOT / "game_assets" / "maps" / "entity_models.json").read_text(encoding="utf-8"))
    rows = doc["npc_tables"].get("20", [])          # region 21 = key 20
    for i, name in enumerate(rows):
        if i != avoid and name[:1] == "m" and name[1:2].isdigit():
            return i
    return None


def edit_church_exit(work: Path) -> Path:
    from tools import level_records as lr

    lvl = bytearray((ROOT / "game_data" / "packs" / "level3d" / "b002_101a" / "level3d.bxon").read_bytes())
    level = lr.Level(bytes(lvl))
    for arr in level.arrays.values():
        if arr.esize == 24 and arr.parent is not None and arr.parent.esize == 1092:
            base = arr.parent.block + arr.parent_index * arr.parent.esize
            if arr.desc - base == 0x68:
                for n in range(arr.count):
                    b = arr.block + n * 24 + 0x0C
                    w = struct.unpack_from("<I", lvl, b)[0]
                    struct.pack_into("<I", lvl, b, (w & 0xFFFF0000) | SLOT_ID)
    out = work / "b002_101a.bxon"
    out.write_bytes(bytes(lvl))
    return out


def chest_table(work: Path, item: int) -> Path:
    raw = bytearray((ROOT / "game_data" / "packs" / "fieldcmn" / "fixed_drop_param.bxon").read_bytes())
    struct.pack_into("<HH", raw, 0x2C + 8 * CHEST_ROW, item, 1)
    out = work / "fixed_drop_param.bxon"
    out.write_bytes(bytes(raw))
    return out


def npc_dialogue(work: Path, line: str) -> Path:
    from tools import text_tool as T

    key = "param/region/r021/npc_ie"
    bank = T.import_bank(key)
    doc = T.read_bank_json(ROOT / "game_assets" / "text" / "banks" / f"{key}.json")
    talks = json.loads((ROOT / "game_assets" / "maps" / "npc_talks.json").read_text(encoding="utf-8"))
    mine = set()
    for talk in talks["regions"]["21"]["characters"][str(NPC_ID)]["talks"]:
        for variant in talk["variants"]:
            for ln in variant:
                if ln["e"] is not None:
                    mine.add(ln["e"])
    texts = {}
    for e in doc["entries"]:
        texts[int(e["offset"])] = line if e["id"] in mine else e["text"]
    out = work / "npc_ie.bxon"
    out.write_bytes(T.rebuild_bank(bank.data, texts))
    return out


def build(mod: Path, item: int = 2, line: str = "ようこそ　ちかしつへ！", work: Path | None = None) -> dict:
    from tools import new_map
    from tools.export_mod import stage_member
    from tools.patch_asset import rebuild_pack

    work = work or ROOT / "build" / "custom_room" / "work"
    work.mkdir(parents=True, exist_ok=True)
    mod = Path(mod)
    plain = os.environ.get("CR_PLAIN", "")      # "1" = bare clone, "model" = keep the donor model, "coll" = keep the donor collision (bisecting)
    bch = None if plain in ("1", "model") else build_model(work)
    written = new_map.clone(DONOR, SLOT, mod, bch)
    if plain not in ("1", "coll"):
        chit = build_collision(work)
        pk = mod / "romfs" / "3d" / "bg" / f"{SLOT}.pack"
        rebuild_pack(pk, f"{SLOT}_chit.rcb", chit, pk)
    # the cloned level itself: the monster gets another row
    base = (ROOT / "game_data" / "packs" / "level3d" / DONOR / "level3d.bxon").read_bytes()
    avoid = None
    scene = json.loads((ROOT / "game_assets" / "maps" / DONOR / "scene.json").read_text(encoding="utf-8"))
    for obj in scene["objects"]:
        if obj["kind"] == "actor":
            props = {q["name"]: q for q in obj["props"]}
            if props["entity class"]["value"] == 0x300:
                avoid = props["entity id"]["value"]

    skip = set(filter(None, os.environ.get("CR_SKIP", "").split(",")))
    monster = None if "monster" in skip else pick_monster_row(avoid if avoid is not None else -1)
    edited = work / "level3d.bxon"
    from tools import level_records

    patched = level_edits(base, monster)
    # an extra copy of the NPC next to the arrival point, inside the strip the house camera shows (emulator-proven: appended actor records)
    if "dup" not in skip:
        patched, _ = level_records.apply_ops(patched, [{"op": "duplicate", "offset": NPC_OFFSET, "set": {"position": DUP_POS, "props": {"entity id": int(os.environ.get("CR_DUPID", NPC_ID))}}}])
    edited.write_bytes(patched)
    stage_member(f"level3d/{SLOT}.pack", "level3d.bxon", edited, mod, work_dir=work / "staged")
    # the slot's level_map row takes the house's parameters (layers, region, ...) but keeps its own level name
    lm = bytearray((ROOT / "game_data" / "packs" / "syscmn" / "level_map.bxon").read_bytes())
    src_row, dst_row = 0x2C + DONOR_ID * 28, 0x2C + SLOT_ID * 28
    own = struct.unpack_from("<I", lm, dst_row)[0]
    lm[dst_row:dst_row + 28] = lm[src_row:src_row + 28]
    struct.pack_into("<I", lm, dst_row, own)
    lmf = work / "level_map.bxon"
    lmf.write_bytes(bytes(lm))
    if "lm" not in skip:
        stage_member("syscmn.pack", "level_map.bxon", lmf, mod, work_dir=work / "staged")
    stage_member("level3d/b002_101a.pack", "level3d.bxon", edit_church_exit(work), mod, work_dir=work / "staged")
    if "chest" not in skip:
        stage_member("fieldcmn.pack", "fixed_drop_param.bxon", chest_table(work, item), mod, work_dir=work / "staged")
    if "text" not in skip:
        stage_member("param/region/r021.pack", "npc_ie.bxon", npc_dialogue(work, line), mod, work_dir=work / "staged")
    return {"slot": SLOT, "map_id": SLOT_ID, "monster_row": monster, "chest_item": item, "files": [str(w) for w in written]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--mod", type=Path, default=ROOT / "build" / "custom_room" / "mod")
    ap.add_argument("--item", type=int, default=2, help="item id the chest holds")
    ap.add_argument("--line", default="ようこそ　ちかしつへ！")
    a = ap.parse_args()
    info = build(a.mod, a.item, a.line)
    print(json.dumps(info, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
