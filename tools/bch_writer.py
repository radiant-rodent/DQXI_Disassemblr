#!/usr/bin/env python3
"""Grow a retail BCH model: replace one draw call's vertex / index buffers with bigger ones (docs/MODEL_IMPORT.md).

A BCH is a header, string, command and raw-data sections followed by a relocation table. A draw call is a PICA command sequence:
register 0x203 = vertex buffer address, 0x227 = index buffer address, 0x228 = index count, 0x22F = draw. The address words hold
section-relative offsets; the relocation table lists each one with its target section (7 = raw data with 16-bit indices). Growing a mesh
therefore means: append the new buffers to the end of the raw-data section, repoint the two address words, change the count word and shift
the sections behind the raw data (header offsets).

    python -m tools.bch_writer list model.bch
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.model_tool import BchParser


def draw_calls(bch: bytes) -> list[dict]:
    """Every draw in command order, with the file offsets of its address and count words (raw, un-relocated)."""
    p = BchParser(bch)
    n = p.cmd_len // 4
    words = struct.unpack_from(f"<{n}I", bch, p.cmd_off)
    out = []
    state = {}
    i = 0
    while i + 1 < n:
        param, command = words[i], words[i + 1]
        pos = i
        i += 2
        reg = command & 0xFFFF
        extra = (command >> 20) & 0x7FF
        consecutive = command >> 31
        entries = []
        if consecutive:
            entries.append((reg, pos))
            for k in range(extra):
                if i < n:
                    entries.append((reg + 1 + k, i))
                    i += 1
        else:
            entries.append((reg, pos))
            i += extra
        for r, w in entries:
            if r in (0x203, 0x227, 0x228):
                state[r] = w
            elif r == 0x205:
                state["stride"] = (words[w] >> 16) & 0xFF
            elif r == 0x22F and 0x228 in state and 0x227 in state and 0x203 in state and words[state[0x228]] > 0:
                out.append({
                    "vbo_word": p.cmd_off + 4 * state[0x203],
                    "ibo_word": p.cmd_off + 4 * state[0x227],
                    "count_word": p.cmd_off + 4 * state[0x228],
                    "stride": state.get("stride", 0),
                    "indices": words[state[0x228]],
                })
        if i % 2:
            i += 1
    return out


def reloc_entries(bch: bytes) -> dict[int, tuple[int, int]]:
    """Location (file offset) -> (relocation entry offset, target section id) for every relocation entry."""
    p = BchParser(bch)
    out = {}
    for off in range(0, p.reloc_len, 4):
        e = p.reloc_off + off
        v = struct.unpack_from("<I", bch, e)[0]
        ptr = v & 0x1FFFFFF
        target = (v >> 25) & 0xF
        source = v >> 29
        base = p._section_base(source)
        if base is None:
            continue
        loc = (base & 0x7FFFFFFF) + (ptr << 2 if target != 1 else ptr)
        out[loc] = (e, target)
    return out


def grow_draw(bch: bytes, draw: int, vbo: bytes, indices: list[int]) -> bytes:
    """Replace draw call ``draw``'s vertex buffer and index list with new ones (any size) and return the new BCH.

    The buffers are appended to the raw-data section; if the draw used 8-bit indices and the new list needs more, its index pointer is
    retargeted to the 16-bit section (relocation target 7). Everything behind the raw data (extension data, relocation table) moves.
    """
    p = BchParser(bch)
    d = draw_calls(bch)[draw]
    rel = reloc_entries(bch)
    out = bytearray(bch)
    pad = (-p.data_len) % 4
    base = p.data_len + pad
    new_vbo_off = base
    new_ibo_off = base + len(vbo) + ((-len(vbo)) % 4)
    use16 = max(indices) > 255 or rel[d["ibo_word"]][1] == 7
    ibo = struct.pack(f"<{len(indices)}H", *indices) if use16 else bytes(indices)
    ibo += b"\0" * ((-len(ibo)) % 4)
    blob = b"\0" * pad + vbo + b"\0" * ((-len(vbo)) % 4) + ibo
    added = len(blob)
    insert_at = p.data_off + p.data_len
    out[insert_at:insert_at] = blob
    # header: sections behind the raw data move, the data length grows
    hdr = list(struct.unpack_from("<4sBBH6I6I", out, 0))
    names = ["magic", "bcomp", "fcomp", "ver", "hdr_off", "str_off", "cmd_off", "data_off", "data_ext_off", "reloc_off",
             "hdr_len", "str_len", "cmd_len", "data_len", "data_ext_len", "reloc_len"]
    h = dict(zip(names, hdr))
    h["data_len"] += added
    h["data_ext_off"] += added
    h["reloc_off"] += added
    struct.pack_into("<4sBBH6I6I", out, 0, *[h[n] for n in names])
    # draw call words
    struct.pack_into("<I", out, d["vbo_word"], new_vbo_off)
    struct.pack_into("<I", out, d["ibo_word"], new_ibo_off)
    struct.pack_into("<I", out, d["count_word"], len(indices))
    if use16 and rel[d["ibo_word"]][1] != 7:
        e = rel[d["ibo_word"]][0] + added          # the relocation table itself moved
        v = struct.unpack_from("<I", out, e)[0]
        struct.pack_into("<I", out, e, (v & ~(0xF << 25)) | (7 << 25))
    return bytes(out)


def main() -> int:
    bch = Path(sys.argv[2]).read_bytes()
    p = BchParser(bch)
    print(f"sections: hdr {p.hdr_off:#x}+{p.hdr_len:#x} str {p.str_off:#x} cmd {p.cmd_off:#x}+{p.cmd_len:#x} data {p.data_off:#x}+{p.data_len:#x} ext {p.data_ext_off:#x}+{p.data_ext_len:#x} reloc {p.reloc_off:#x}+{p.reloc_len:#x}")
    rel = reloc_entries(bch)
    for n, d in enumerate(draw_calls(bch)[:12]):
        r1 = rel.get(d["ibo_word"]); r2 = rel.get(d["vbo_word"])
        print(n, d, "ibo target", r1 and r1[1], "vbo target", r2 and r2[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
