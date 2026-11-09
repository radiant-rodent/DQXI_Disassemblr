#!/usr/bin/env python3
"""Export what an NPC says: `game_assets/maps/npc_talks.json`.

Talk text of a region lives in `param/region/rNNN/npc_ie.bxon` (CharacterIEData). Layout (decoded from
`Text_ResolveMessageEntry`, docs/DIALOGUE_FORMAT.md):

    root[ ] 24-byte rows          one per *region character id* (the npc_list row, = the actor's entity id)
      +8  talks_n, +12 -> talks
    talk 16 bytes                 one conditional conversation of that character
      +0 variants_n, +4 -> variants   (played in turn when the NPC is talked to again)
      +8  u32: byte0 flag group, byte1 minimum value of that group, byte2 time-of-day mask
                (1 morning, 2 day, 4 evening, 8 night), byte3 first-time page
      +12 u32: byte0 redirect group (0xFF = none), byte1 redirect index, byte2 redirect mask
    variant 12 bytes              lines_n, -> 28-byte line records, +8 offset of the variant
    line 28 bytes                 +0x10 speaker string, +0x14 text string

Alongside it records which events the area script starts when that character is addressed
(`TrgRCommand` -> `rg_id == N` -> `StartEvent(...)`), since those replace the default talk.

    python tools/npc_talk.py            writes game_assets/maps/npc_talks.json
    python tools/npc_talk.py set-cond --region 21 --json edits.json   stage edited conversation conditions
"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "game_assets" / "maps" / "npc_talks.json"


def u32(d: bytes, o: int) -> int:
    return struct.unpack_from("<I", d, o)[0]


def rel(d: bytes, o: int):
    v = u32(d, o)
    return None if v == 0 else o + v


def parse_region(region: int):
    key = f"param/region/r{region:03d}/npc_ie"
    bank_json = ROOT / "game_assets" / "text" / "banks" / f"{key}.json"
    bxon = ROOT / "game_data" / "packs" / "param" / "region" / f"r{region:03d}" / "npc_ie.bxon"
    if not bank_json.exists() or not bxon.exists():
        return None
    doc = json.loads(bank_json.read_text(encoding="utf8"))
    by_offset: dict[tuple[int, str], int] = {}
    for e in doc["entries"]:
        by_offset[(e["offset"], e["role"])] = e["id"]
    d = bxon.read_bytes()
    count, relptr = u32(d, 0x20), u32(d, 0x24)
    root = 0x24 + relptr
    characters: dict[str, dict] = {}
    for i in range(min(count, 0x1000)):
        entry = root + 24 * i
        if entry + 16 > len(d):
            break
        talks_n = u32(d, entry + 8)
        talks_at = rel(d, entry + 12)
        if not talks_n or talks_at is None:
            continue
        talks = []
        for t in range(min(talks_n, 0x1000)):
            tk = talks_at + 16 * t
            variants_n = u32(d, tk)
            variants_at = rel(d, tk + 4)
            cond = u32(d, tk + 8)
            redir = u32(d, tk + 12)
            variants = []
            if variants_n and variants_at is not None:
                for v in range(min(variants_n, 0x1000)):
                    vr = variants_at + 12 * v
                    lines_n = u32(d, vr)
                    lines_at = rel(d, vr + 4)
                    lines = []
                    if lines_n and lines_at is not None:
                        for k in range(min(lines_n, 0x10000)):
                            rec = lines_at + 28 * k
                            sp = rel(d, rec + 0x10)
                            tx = rel(d, rec + 0x14)
                            lines.append({
                                "s": by_offset.get((sp, "speaker")) if sp is not None else None,
                                "e": by_offset.get((tx, "text")) if tx is not None else None,
                            })
                    variants.append(lines)
            talk = {
                "t": t,
                "group": cond & 0xFF,
                "min": (cond >> 8) & 0xFF,
                "time": (cond >> 16) & 0xFF,
                "first": (cond >> 24) & 0xFF,
                "variants": variants,
            }
            if (redir & 0xFF) != 0xFF:
                talk["redirect"] = {"group": redir & 0xFF, "index": (redir >> 8) & 0xFF, "mask": (redir >> 16) & 0xFF}
            talks.append(talk)
        characters[str(i)] = {"talks": talks}
    return {"bank": key, "characters": characters}


RG = re.compile(r"rg_id == (\d+)")
REGION = re.compile(r"IsRegion\((\d+)\)")
START = re.compile(r"StartEvent\((\w+)\)")


def script_events(area: str):
    path = ROOT / "game_assets" / "scripts" / "packs" / "script" / area / "script.decompiled.nut"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf8", errors="replace").splitlines()
    start = next((i for i, l in enumerate(lines) if "function TrgRCommand" in l), None)
    if start is None:
        return []
    out = []
    i = start + 1
    while i < len(lines) and not re.match(r"    function ", lines[i]):
        m = RG.search(lines[i])
        if m:
            rg = int(m.group(1))
            region = REGION.search(lines[i])
            for j in range(i + 1, min(i + 14, len(lines))):
                if RG.search(lines[j]):
                    break
                s = START.search(lines[j])
                if s:
                    out.append({"rg_id": rg, "region": int(region.group(1)) if region else None, "event": s.group(1)})
                    break
        i += 1
    return out


def set_conditions(region: int, edits_file: Path) -> int:
    """Stage conversation condition edits of `region`: remember them (build/npc_conditions) and rebuild the bank
    through text_tool.save-mod, which applies them after the text edits."""
    import subprocess
    sys.path.insert(0, str(ROOT))
    from tools import text_tool as T

    key = f"param/region/r{region:03d}/npc_ie"
    edits = json.loads(edits_file.read_text(encoding="utf8"))
    T.CONDITION_DIR.mkdir(parents=True, exist_ok=True)
    (T.CONDITION_DIR / (key.replace("/", "_") + ".json")).write_text(json.dumps(edits), encoding="utf8")
    text_json = T.BUILD_DIR / f"{key}.json"
    if not text_json.exists():
        text_json = ROOT / "game_assets" / "text" / "banks" / f"{key}.json"
    proc = subprocess.run([sys.executable, str(ROOT / "tools" / "text_tool.py"), "save-mod", "--bank", key, "--json", str(text_json)],
                          cwd=ROOT, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "set-cond":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--region", type=int, required=True)
        ap.add_argument("--json", type=Path, required=True)
        a = ap.parse_args()
        return set_conditions(a.region, a.json)
    regions = {}
    for r in range(1, 26):
        got = parse_region(r)
        if got:
            regions[str(r)] = got
    areas = {}
    base = ROOT / "game_assets" / "scripts" / "packs" / "script"
    for p in sorted(base.iterdir()):
        ev = script_events(p.name)
        if ev:
            areas[p.name] = ev
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"regions": regions, "area_events": areas}, separators=(",", ":")), encoding="utf8")
    chars = sum(len(r["characters"]) for r in regions.values())
    print(f"{len(regions)} regions, {chars} characters with talk, {sum(len(v) for v in areas.values())} area event hooks -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
