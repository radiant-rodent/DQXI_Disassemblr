#!/usr/bin/env python3
"""Add, remove and reorder conversations, blocks and lines of an NPC (`param/region/rNNN/npc_ie.bxon`).

The text tools can change a string but not the structure. This tool rewrites the whole talk tree of ONE character
at the end of the file and re-points the character's row at it. Nothing else in the file moves or changes, so every
other character, and every pointer outside the rewritten tree, stays byte-identical (the old tree stays where it
was, unreferenced). Layout written (same as the game's files, docs/DIALOGUE_FORMAT.md): every block is preceded by
the `&&&&` marker and starts on a 4-byte boundary (padding 0x40 like the originals), pointers are relative to their
own field.

    row +8 talks_n, +12 -> talks
    talk 16     variants_n, -> variants, condition word, redirect word
    variant 12  lines_n, -> lines, -> label (UTF-8) or 0
    line 28     child_n, -> child block (kept as found), +8 u8, +9 u8, +0x0A what follows (0 end, 1 next line,
                3 Yes / No question), +0x0C line number inside the conversation, -> speaker, -> text (UTF-16)

The model (JSON) of a character::

    {"talks": [{"group": 0, "min": 0, "time": 15, "first": 0, "redirect": 1090584575,
                "variants": [{"label": null,
                              "lines": [{"speaker": "", "text": "...", "kind": 0, "b8": 0, "b9": 255,
                                         "child": "", "child_n": 0, "tail": 0}]}]}]}

`kind` of a block's lines is written as given; `python -m tools.npc_ie_edit selftest` rebuilds every character of
every region from its own dump and checks that the dump comes out the same and all other characters are untouched.
Emulator-proven (tools/emu/add_probe.py, Heliodor church): a new conversation, its Yes / No question and the
answer block play in the game.

    python -m tools.npc_ie_edit dump --region 21 --char 16            the model as JSON
    python -m tools.npc_ie_edit selftest
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import text_tool as T  # noqa: E402

MARK = b"&&&&"
STRUCTURE_DIR = ROOT / "build" / "npc_structure"


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def rel(d, o):
    v = u32(d, o)
    return None if v == 0 else (o + v) & 0xFFFFFFFF


def bank_path(region: int) -> Path:
    return ROOT / "game_data" / "packs" / "param" / "region" / f"r{region:03d}" / "npc_ie.bxon"


def _utf8(d: bytes, at: int | None) -> str | None:
    if at is None or at >= len(d):
        return None
    end = d.find(b"\0", at)
    return d[at:end if end >= 0 else len(d)].decode("utf8", "replace") or None


def dump_char(d: bytes, char: int) -> dict:
    count, root = u32(d, 0x20), 0x24 + u32(d, 0x24)
    if not 0 <= char < count:
        raise ValueError(f"character {char} is not in this bank ({count} rows)")
    row = root + 24 * char
    talks_n, talks_at = u32(d, row + 8), rel(d, row + 12)
    talks = []
    for t in range(talks_n if talks_at is not None else 0):
        tk = talks_at + 16 * t
        cond, redirect = u32(d, tk + 8), u32(d, tk + 12)
        variants = []
        variants_at = rel(d, tk + 4)
        for v in range(u32(d, tk) if variants_at is not None else 0):
            vr = variants_at + 12 * v
            lines_at = rel(d, vr + 4)
            lines = []
            for k in range(u32(d, vr) if lines_at is not None else 0):
                r = lines_at + 28 * k
                child_n, child_at = u32(d, r), rel(d, r + 4)
                child = b""
                if child_at is not None:
                    # up to the next block; the 0x40 padding in front of that block is not part of it (the writer
                    # pads again), which also keeps a block at the very end of the file stable
                    child = d[child_at:T.block_end(d, child_at)].rstrip(b"@")
                lines.append({
                    "speaker": T.cstr(d, rel(d, r + 0x10)) if u32(d, r + 0x10) else "",
                    "text": T.cstr(d, rel(d, r + 0x14)) if u32(d, r + 0x14) else "",
                    "kind": d[r + 0x0A],
                    "b8": d[r + 8], "b9": d[r + 9], "b11": d[r + 0x0B],
                    "child_n": child_n, "child": child.hex(),
                    "tail": u32(d, r + 0x18),
                })
            variants.append({"label": _utf8(d, rel(d, vr + 8)), "lines": lines})
        talks.append({"group": cond & 0xFF, "min": (cond >> 8) & 0xFF, "time": (cond >> 16) & 0xFF, "first": cond >> 24,
                      "redirect": redirect, "variants": variants})
    return {"talks": talks}


class _Writer:
    """Appends blocks to the file; pointers are filled in once their target is known."""

    def __init__(self, data: bytes):
        self.out = bytearray(data)

    def block(self, payload: bytes) -> int:
        while len(self.out) % 4:
            self.out.append(0x40)
        self.out += MARK
        at = len(self.out)
        self.out += payload
        return at

    def point(self, field: int, target: int) -> None:
        struct.pack_into("<I", self.out, field, (target - field) & 0xFFFFFFFF)


def rebuild_char(data: bytes, char: int, model: dict) -> bytes:
    count, root = u32(data, 0x20), 0x24 + u32(data, 0x24)
    if not 0 <= char < count:
        raise ValueError(f"character {char} is not in this bank ({count} rows)")
    row = root + 24 * char
    w = _Writer(data)
    talks = model.get("talks") or []
    if len(talks) > 255:
        raise ValueError("more than 255 conversations")
    if not talks:
        struct.pack_into("<II", w.out, row + 8, 0, 0)
        return bytes(w.out)
    talks_at = w.block(bytes(16 * len(talks)))
    for t, talk in enumerate(talks):
        tk = talks_at + 16 * t
        variants = talk.get("variants") or []
        cond = (int(talk.get("group", 0)) & 0xFF) | ((int(talk.get("min", 0)) & 0xFF) << 8) | \
               ((int(talk.get("time", 15)) & 0xFF) << 16) | ((int(talk.get("first", 0)) & 0xFF) << 24)
        struct.pack_into("<IIII", w.out, tk, len(variants), 0, cond, int(talk.get("redirect", 0x4000FFFF)) & 0xFFFFFFFF)
        if not variants:
            continue
        variants_at = w.block(bytes(12 * len(variants)))
        w.point(tk + 4, variants_at)
        number = 0  # line numbers run through the whole conversation
        for v, variant in enumerate(variants):
            vr = variants_at + 12 * v
            lines = variant.get("lines") or []
            struct.pack_into("<I", w.out, vr, len(lines))
            if lines:
                lines_at = w.block(bytes(28 * len(lines)))
                w.point(vr + 4, lines_at)
                for k, line in enumerate(lines):
                    r = lines_at + 28 * k
                    struct.pack_into("<I", w.out, r, int(line.get("child_n", 0)))
                    w.out[r + 8] = int(line.get("b8", 0)) & 0xFF
                    w.out[r + 9] = int(line.get("b9", 0xFF)) & 0xFF
                    w.out[r + 0x0A] = int(line.get("kind", 0)) & 0xFF
                    w.out[r + 0x0B] = int(line.get("b11", 0)) & 0xFF
                    struct.pack_into("<I", w.out, r + 0x0C, number)
                    struct.pack_into("<I", w.out, r + 0x18, int(line.get("tail", 0)))
                    number += 1
                # the strings and child blocks of the lines follow the line array, in line order
                for k, line in enumerate(lines):
                    r = lines_at + 28 * k
                    child = bytes.fromhex(line.get("child") or "")
                    if child:
                        w.point(r + 4, w.block(child))
                    speaker = line.get("speaker") or ""
                    if speaker:
                        w.point(r + 0x10, w.block(T.game_bytes(speaker) + b"\0\0"))
                    w.point(r + 0x14, w.block(T.game_bytes(line.get("text") or "") + b"\0\0"))
            label = variant.get("label")
            if label:
                w.point(vr + 8, w.block(label.encode("utf8") + b"\0"))
    while len(w.out) % 4:
        w.out.append(0x40)
    struct.pack_into("<I", w.out, row + 8, len(talks))
    w.point(row + 12, talks_at)
    return bytes(w.out)


def apply(data: bytes, doc: dict) -> bytes:
    """`doc`: {"<character id>": model}. Applied one after another; each only appends."""
    for char, model in sorted(doc.items(), key=lambda kv: int(kv[0])):
        T.check_codec  # (strings are checked by game_bytes: an unknown tag raises)
        data = rebuild_char(data, int(char), model)
    return data


def pending(key: str) -> dict:
    path = STRUCTURE_DIR / (key.replace("/", "_") + ".json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def selftest() -> int:
    bad = 0
    total = 0
    for region in range(1, 26):
        path = bank_path(region)
        if not path.exists():
            continue
        d = path.read_bytes()
        count = u32(d, 0x20)
        before = [dump_char(d, c) for c in range(count)]
        # rebuild every 7th character with talks (and one neighbour check each), all into one file
        doc = {str(c): before[c] for c in range(count) if before[c]["talks"] and c % 7 == 0}
        try:
            out = apply(d, doc)
        except Exception as exc:
            print(f"r{region:03d}: {type(exc).__name__}: {exc}")
            bad += 1
            continue
        after = [dump_char(out, c) for c in range(count)]
        total += len(doc)
        if after != before:
            wrong = [c for c in range(count) if after[c] != before[c]]
            print(f"r{region:03d}: {len(wrong)} character(s) differ after the rebuild, first {wrong[:5]}")
            bad += 1
        if out[:len(d)] != d:
            diff = [i for i in range(len(d)) if out[i] != d[i]]
            root = 0x24 + u32(d, 0x24)
            outside = [i for i in diff if not any(root + 24 * int(c) + 8 <= i < root + 24 * int(c) + 16 for c in doc)]
            if outside:
                print(f"r{region:03d}: {len(outside)} byte(s) changed outside the rewritten rows, first 0x{outside[0]:X}")
                bad += 1
        # the text tool's own walk must still accept the file
        try:
            T._walk_for_kind(out, "CharacterIEData")
        except Exception as exc:
            print(f"r{region:03d}: text walk failed: {exc}")
            bad += 1
    print(f"rebuilt {total} characters in 25 regions: {'OK' if not bad else f'{bad} problem(s)'}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--region", type=int, required=True)
    d.add_argument("--char", type=int, required=True)
    sub.add_parser("selftest")
    a = ap.parse_args()
    if a.cmd == "selftest":
        return selftest()
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(dump_char(bank_path(a.region).read_bytes(), a.char), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
