#!/usr/bin/env python3
"""tools/layout_tool.py - Universal NW4C BFLYT Layout & BFLAN Animation Decompiler & Re-encoder.

Disassembles NW4C FLYT layout archives (.bflyt) and FLAN animation panes (.bflan)
into structured, human-readable and editable JSON in game_layouts/, and provides
a full JSON-to-binary re-encoder with verified lossless round-trip support.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
if "../3DS_Translate" not in sys.path:
    sys.path.insert(0, "../3DS_Translate")

from tools import pack

LAYOUTS_OUT = PROJECT_ROOT / "game_layouts"


@dataclass
class SarcNode:
    hash: int
    attrs: int
    start: int
    end: int
    name: str


class Sarc:
    def __init__(self, raw: bytes, data_offset: int, nodes: list[SarcNode]):
        self.raw = raw
        self.data_offset = data_offset
        self.nodes = nodes

    @classmethod
    def parse(cls, data: bytes) -> "Sarc":
        if data[:4] != b"SARC":
            raise ValueError("not SARC")
        hsize, bom, fsize, doff, ver = struct.unpack_from("<HHIIH", data, 4)
        p = hsize
        fh, count, mult = struct.unpack_from("<HHI", data, p + 4)
        nodes_off = p + fh
        sfnt = nodes_off + count * 16
        names_off = sfnt + struct.unpack_from("<H", data, sfnt + 4)[0]
        nodes = []
        for i in range(count):
            h, attrs, s, e = struct.unpack_from("<IIII", data, nodes_off + i * 16)
            name = ""
            if attrs & 0x01000000:
                no = names_off + (attrs & 0xFFFF) * 4
                name = data[no:data.index(b"\0", no)].decode("utf-8", "replace")
            nodes.append(SarcNode(h, attrs, s, e, name))
        return cls(data, doff, nodes)

    @property
    def files(self) -> dict[str, bytes]:
        return {n.name: self.raw[self.data_offset + n.start:self.data_offset + n.end] for n in self.nodes}


def parse_bflyt(data: bytes) -> dict:
    """Parses NW4C BFLYT binary into structured dictionary."""
    if data[:4] != b"FLYT":
        raise ValueError("Invalid BFLYT header (expected FLYT)")

    bom, hsize, version, fsize, nsec = struct.unpack_from("<HHIIH", data, 4)
    p = hsize
    sections_raw = []
    for _ in range(nsec):
        m, sz = struct.unpack_from("<4sI", data, p)
        sections_raw.append((m, data[p:p + sz]))
        p += sz

    layout_info = {}
    textures = []
    fonts = []
    panes = []
    hierarchy = []

    for m, sec in sections_raw:
        magic_str = m.decode("ascii", "replace")
        if m == b"lyt1":
            origin, = struct.unpack_from("<B", sec, 8)
            w, h = struct.unpack_from("<ff", sec, 12)
            layout_info = {"origin": origin, "width": w, "height": h}
        elif m == b"txl1":
            cnt, = struct.unpack_from("<H", sec, 8)
            for i in range(cnt):
                o, = struct.unpack_from("<I", sec, 12 + i * 4)
                s_pos = 12 + o
                end = sec.find(b"\0", s_pos)
                textures.append(sec[s_pos:end].decode("ascii", "replace"))
        elif m == b"fnl1":
            cnt, = struct.unpack_from("<H", sec, 8)
            for i in range(cnt):
                o, = struct.unpack_from("<I", sec, 12 + i * 4)
                s_pos = 12 + o
                end = sec.find(b"\0", s_pos)
                fonts.append(sec[s_pos:end].decode("ascii", "replace"))
        elif m in (b"pan1", b"pic1", b"txt1", b"wnd1", b"bnd1", b"prt1"):
            name = sec[0x0C:0x24].split(b"\0", 1)[0].decode("ascii", "replace")
            user_data = sec[0x24:0x2C].rstrip(b"\0").decode("ascii", "replace")
            tx, ty, tz = struct.unpack_from("<fff", sec, 0x2C)
            rx, ry, rz = struct.unpack_from("<fff", sec, 0x38)
            sx, sy = struct.unpack_from("<ff", sec, 0x44)
            w, h = struct.unpack_from("<ff", sec, 0x4C)

            pane_dict = {
                "type": magic_str,
                "name": name,
                "user_data": user_data,
                "translate": [tx, ty, tz],
                "rotate": [rx, ry, rz],
                "scale": [sx, sy],
                "size": [w, h],
                "raw_header_hex": sec[:0x54].hex(),
            }

            if m == b"txt1":
                buf_bytes, str_bytes, mat_idx, font_idx = struct.unpack_from("<HHHH", sec, 0x54)
                pos_align, flags = struct.unpack_from("<BB", sec, 0x5C)
                italic, = struct.unpack_from("<f", sec, 0x60)
                toff, = struct.unpack_from("<I", sec, 0x64)
                col_top, col_bot = struct.unpack_from("<II", sec, 0x68)
                fsx, fsy = struct.unpack_from("<ff", sec, 0x70)
                cspace, lspace = struct.unpack_from("<ff", sec, 0x78)
                tid_off, = struct.unpack_from("<I", sec, 0x80)

                raw_text = sec[toff:toff + max(str_bytes - 2, 0)]
                text_str = raw_text.decode("utf-16-le", "replace")
                text_id = ""
                if tid_off:
                    e = sec.find(b"\0", tid_off)
                    text_id = sec[tid_off:e].decode("ascii", "replace")

                pane_dict.update({
                    "text": text_str,
                    "text_id": text_id,
                    "buffer_bytes": buf_bytes,
                    "font_index": font_idx,
                    "font_size": [fsx, fsy],
                    "char_space": cspace,
                    "line_space": lspace,
                    "colors": [f"0x{col_top:08X}", f"0x{col_bot:08X}"],
                })

            panes.append(pane_dict)
        elif m == b"pas1":
            hierarchy.append({"action": "push"})
        elif m == b"pae1":
            hierarchy.append({"action": "pop"})

    return {
        "format": "BFLYT",
        "version": f"0x{version:08X}",
        "raw_size": len(data),
        "layout": layout_info,
        "textures": textures,
        "fonts": fonts,
        "panes_count": len(panes),
        "panes": panes,
        "raw_sections": [
            {"magic": m.decode("ascii", "replace"), "size": len(s), "payload_hex": s[8:].hex()}
            for m, s in sections_raw
        ],
    }


PANE_MAGICS = ("pan1", "pic1", "txt1", "wnd1", "bnd1", "prt1")
# Offsets are inside the section payload (the 8-byte section header excluded),
# i.e. the parser's 0x2C/0x38/0x44/0x4C offsets minus 8.
_PANE_FIELDS = (("translate", 0x24), ("rotate", 0x30), ("scale", 0x3C), ("size", 0x44))


def apply_pane_edits(d: dict) -> list[str]:
    """Writes edited pane values from ``d["panes"]`` into ``d["raw_sections"]``.

    BFLYT stores panes as fixed-size sections, so the binary can only be
    rebuilt from the raw section payloads. Edits made in the JSON pane list
    (translate/rotate/scale/size, and same-capacity text) are applied here in
    place; unchanged JSON therefore rebuilds byte-identically. Returns warnings.
    """
    raw = d.get("raw_sections")
    panes = d.get("panes")
    if not raw or not panes:
        return []
    sections = [s for s in raw if s.get("magic") in PANE_MAGICS]
    if len(sections) != len(panes):
        return [
            f"{len(panes)} panes in JSON but {len(sections)} pane sections in the file; "
            "pane edits were not written"
        ]
    warnings: list[str] = []
    for pane, section in zip(panes, sections):
        payload = bytearray(bytes.fromhex(section["payload_hex"]))
        for key, offset in _PANE_FIELDS:
            values = pane.get(key)
            if not isinstance(values, list) or len(values) < 2:
                continue
            if offset + 12 > len(payload):
                continue
            if key == "scale" or key == "size":
                struct.pack_into("<ff", payload, offset, float(values[0]), float(values[1]))
            else:
                struct.pack_into("<fff", payload, offset, *(float(v) for v in values[:3]))
        if section.get("magic") == "txt1" and isinstance(pane.get("text"), str):
            old_off = struct.unpack_from("<I", payload, 0x5C)[0]
            buffer_bytes = struct.unpack_from("<H", payload, 0x4C)[0]
            capacity = max(0, buffer_bytes - 2)
            encoded = pane["text"].encode("utf-16-le")
            # NW4C string offsets are relative to the section start; the payload
            # we are editing starts 8 bytes later (after the section header).
            text_pos = old_off - 8 if old_off >= 8 else old_off
            if len(encoded) > capacity:
                # A longer string needs a longer buffer.  The text buffer is
                # followed only by the pane's text id (an ASCII name), so the
                # section can be extended in place: the id moves by the size
                # difference and its offset field is corrected.  Sections after
                # this one are concatenated without absolute offsets, and
                # build_bflyt recomputes the section and file sizes, so nothing
                # else needs patching.
                if not old_off or text_pos + buffer_bytes > len(payload):
                    raise ValueError(
                        f"pane {pane.get('name')!r}: text is {len(encoded) // 2} characters, "
                        f"the layout reserves {max(capacity, 0) // 2}, and the section does not "
                        "describe a text buffer this tool can grow")
                new_buffer = (len(encoded) + 2 + 3) & ~3
                delta = new_buffer - buffer_bytes
                if delta <= 0:
                    raise ValueError(
                        f"pane {pane.get('name')!r}: cannot grow the text buffer "
                        f"({buffer_bytes} -> {new_buffer} bytes)")
                tid_off = struct.unpack_from("<I", payload, 0x78)[0]
                if tid_off >= old_off + buffer_bytes:
                    tid_off += delta
                grown = bytearray(payload[:text_pos])
                grown += encoded + b"\x00\x00"
                while len(grown) % 4:
                    grown += b"\x00"
                grown += payload[text_pos + buffer_bytes:]
                struct.pack_into("<I", grown, 0x78, tid_off)
                struct.pack_into("<H", grown, 0x4C, new_buffer)
                struct.pack_into("<H", grown, 0x4E, len(encoded) + 2)
                payload = grown
                warnings.append(
                    f"pane {pane.get('name')!r}: text grown from {capacity // 2} to "
                    f"{len(encoded) // 2} characters (+{delta} bytes); the layout is no "
                    "longer the retail size")
            elif old_off and text_pos + capacity <= len(payload):
                new_text = encoded + bytes(capacity - len(encoded))
                if payload[text_pos:text_pos + capacity] != new_text:
                    payload[text_pos:text_pos + capacity] = new_text
                    struct.pack_into("<H", payload, 0x4E, len(encoded) + 2)
        section["payload_hex"] = payload.hex()
    return warnings


def complete(doc: dict, original: bytes) -> dict:
    """Returns ``doc`` with ``raw_sections``, taking them from the original BFLYT if missing.

    A hand-trimmed JSON may carry only the readable pane list; building from it alone
    would write a header-only file. The pane edits (transform, size, text)
    are laid over the parsed original instead. Pane names must match in order.
    """
    if "raw_sections" in doc:
        return doc
    base = parse_bflyt(original)
    panes = doc.get("panes", [])
    if [p.get("name") for p in panes] != [p["name"] for p in base["panes"]]:
        raise ValueError("pane list differs from the original layout; add panes with "
                         "`layout_tool add-pane` on the .bflyt so the JSON carries raw sections")
    for edited, pane in zip(panes, base["panes"]):
        for key in ("translate", "rotate", "scale", "size", "text"):
            if key in edited and key in pane:
                pane[key] = edited[key]
    return base


def add_pane(d: dict, source: str, new_name: str) -> dict:
    """Copies pane ``source`` under ``new_name`` as its next sibling; returns a new document.

    The copy (plus the ``usd1`` user data that follows it, if any) is inserted after the
    source's whole child block, so it gets the same parent. Children are not copied, because
    the game finds panes by name and copied children would clash. BFLYT keeps no pane count;
    ``build_bflyt`` recomputes the section count and file size. Groups, ``cnt1`` and
    animations do not list the new pane, so it is static and always shown.
    """
    raw_name = new_name.encode("ascii")
    if not raw_name or len(raw_name) > 23:
        raise ValueError(f"pane name {new_name!r} must be 1-23 ASCII characters")
    sections = [dict(s) for s in d["raw_sections"]]
    panes = [dict(p) for p in d["panes"]]
    if any(p["name"] == new_name for p in panes):
        raise ValueError(f"pane {new_name!r} already exists")
    pane_rows = [i for i, s in enumerate(sections) if s["magic"] in PANE_MAGICS]
    matches = [k for k, i in enumerate(pane_rows) if panes[k]["name"] == source]
    if not matches:
        raise ValueError(f"no pane named {source!r}")
    if len(pane_rows) != len(panes):
        raise ValueError("pane list and pane sections disagree; re-parse the binary first")
    src = pane_rows[matches[0]]
    copied = [dict(sections[src])]
    end = src + 1
    if end < len(sections) and sections[end]["magic"] == "usd1":
        copied.append(dict(sections[end]))
        end += 1
    if end < len(sections) and sections[end]["magic"] == "pas1":
        depth = 0
        while end < len(sections):
            depth += {"pas1": 1, "pae1": -1}.get(sections[end]["magic"], 0)
            end += 1
            if depth == 0:
                break
    payload = bytearray(bytes.fromhex(copied[0]["payload_hex"]))
    payload[0x04:0x1C] = raw_name.ljust(24, b"\0")  # name at section +0x0C
    copied[0]["payload_hex"] = payload.hex()
    pane = dict(panes[matches[0]])
    pane["name"] = new_name
    pane["raw_header_hex"] = (bytes.fromhex(pane["raw_header_hex"])[:0x0C] + raw_name.ljust(24, b"\0")
                              + bytes.fromhex(pane["raw_header_hex"])[0x24:]).hex()
    insert_pane = sum(1 for i in pane_rows if i < end)
    out = dict(d)
    out["raw_sections"] = sections[:end] + copied + sections[end:]
    out["panes"] = panes[:insert_pane] + [pane] + panes[insert_pane:]
    out["panes_count"] = len(out["panes"])
    return out


def build_bflyt(d: dict) -> bytes:
    """Rebuilds BFLYT binary from structured dictionary."""
    warnings = apply_pane_edits(d)
    if warnings:
        d = dict(d)
        d["_warnings"] = warnings
    out_sections = []

    # If raw_sections is preserved, rebuild exactly
    if "raw_sections" in d:
        for s in d["raw_sections"]:
            magic = s["magic"].encode("ascii").ljust(4, b" ")
            payload = bytes.fromhex(s["payload_hex"])
            total_sz = len(payload) + 8
            sec_bytes = magic + struct.pack("<I", total_sz) + payload
            out_sections.append(sec_bytes)

    body = b"".join(out_sections)
    hsize = 0x14
    total_len = hsize + len(body)
    version = int(d.get("version", "0x07020100"), 16)
    nsec = len(out_sections)

    hdr = b"FLYT" + struct.pack("<HHIIH2x", 0xFEFF, hsize, version, total_len, nsec)
    return hdr + body


def parse_bflan(data: bytes) -> dict:
    """Parses NW4C BFLAN animation binary into structured dictionary."""
    if data[:4] != b"FLAN":
        raise ValueError("Invalid BFLAN header (expected FLAN)")

    bom, hsize, version, fsize, nsec = struct.unpack_from("<HHIIH", data, 4)
    p = hsize
    sections_raw = []
    for _ in range(nsec):
        m, sz = struct.unpack_from("<4sI", data, p)
        sections_raw.append((m, data[p:p + sz]))
        p += sz

    tags = []
    anim_info = {}

    for m, sec in sections_raw:
        if m == b"pat1":
            count, = struct.unpack_from("<H", sec, 8)
            for i in range(min(count, (len(sec) - 12) // 4)):
                o, = struct.unpack_from("<I", sec, 12 + i * 4)
                sp = o
                if sp < len(sec):
                    end = sec.find(b"\0", sp)
                    if end == -1:
                        end = len(sec)
                    tag_name = sec[sp:end].decode("ascii", "replace")
                    s_frame = 0
                    e_frame = 0
                    if 0x14 + 4 <= len(sec):
                        s_frame, e_frame = struct.unpack_from("<HH", sec, 0x14)
                    tags.append({"name": tag_name, "start": s_frame, "end": e_frame})

        elif m == b"pai1":
            frame_cnt, = struct.unpack_from("<H", sec, 8)
            flags, = struct.unpack_from("<B", sec, 10)
            anim_info = {"frames": frame_cnt, "flags": flags}

    return {
        "format": "BFLAN",
        "version": f"0x{version:08X}",
        "raw_size": len(data),
        "anim": anim_info,
        "tags": tags,
        "raw_sections": [
            {"magic": m.decode("ascii", "replace"), "size": len(s), "payload_hex": s[8:].hex()}
            for m, s in sections_raw
        ],
    }


def build_bflan(d: dict) -> bytes:
    """Rebuilds BFLAN binary from structured dictionary."""
    out_sections = []
    if "raw_sections" in d:
        for s in d["raw_sections"]:
            magic = s["magic"].encode("ascii").ljust(4, b" ")
            payload = bytes.fromhex(s["payload_hex"])
            total_sz = len(payload) + 8
            sec_bytes = magic + struct.pack("<I", total_sz) + payload
            out_sections.append(sec_bytes)

    body = b"".join(out_sections)
    hsize = 0x14
    total_len = hsize + len(body)
    version = int(d.get("version", "0x07020100"), 16)
    nsec = len(out_sections)

    hdr = b"FLAN" + struct.pack("<HHIIH2x", 0xFEFF, hsize, version, total_len, nsec)
    return hdr + body


def read_romfs():
    sys.path.insert(0, "../3DS_Translate")
    from dq11tool.ctr.formats import open_image
    f, ncsd, ncch = open_image(r"..\3DS_Translate\DQXI.3ds")
    return f, ncch.romfs()


def batch_extract(out_dir: Path, limit: int | None = None) -> tuple[int, int]:
    """Disassembles all NW4C layouts and animations from RomFS UI packs into structured JSON."""
    out_dir.mkdir(parents=True, exist_ok=True)
    f, romfs = read_romfs()

    ui_packs = [rf for rf in romfs.files if rf.path.startswith("/ui/") and rf.path.endswith(".pack")]
    if limit:
        ui_packs = ui_packs[:limit]

    print(f"Batch disassembling UI layouts from {len(ui_packs)} packs into {out_dir}...")
    total_lyt = 0
    total_lan = 0

    for i, rf in enumerate(ui_packs):
        pack_name = Path(rf.path).stem
        pdata = romfs.read_file(rf)
        if not pack.Pack.is_pack(pdata):
            continue

        p = pack.Pack.parse(pdata)
        pack_dir = out_dir / pack_name
        for e in p.entries:
            if e.name.endswith(".arc") and e.data[:4] == b"SARC":
                arc = Sarc.parse(e.data)
                for node in arc.nodes:
                    if node.name.endswith(".bflyt"):
                        d = parse_bflyt(arc.files[node.name])
                        json_path = pack_dir / (Path(node.name).stem + ".layout.json")
                        json_path.parent.mkdir(parents=True, exist_ok=True)
                        json_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
                        total_lyt += 1
                    elif node.name.endswith(".bflan") or node.name.endswith(".anim"):
                        d = parse_bflan(arc.files[node.name])
                        json_path = pack_dir / (Path(node.name).stem + ".anim.json")
                        json_path.parent.mkdir(parents=True, exist_ok=True)
                        json_path.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
                        total_lan += 1

        if (i + 1) % 50 == 0 or i + 1 == len(ui_packs):
            print(f"  [{i+1}/{len(ui_packs)}] Processed {pack_name} (Disassembled {total_lyt} layouts, {total_lan} animations)")

    f.close()
    print(f"Disassembly complete! Disassembled {total_lyt} BFLYT layouts and {total_lan} BFLAN animations.")
    return total_lyt, total_lan


def verify_roundtrip(sample_limit: int = 50) -> tuple[int, int]:
    """Tests bit-matching round-trip re-encoding from JSON back to BFLYT/BFLAN."""
    f, romfs = read_romfs()
    ui_packs = [rf for rf in romfs.files if rf.path.startswith("/ui/") and rf.path.endswith(".pack")]

    tested = 0
    passed = 0

    print(f"Verifying lossless round-trip on first {sample_limit} BFLYT/BFLAN assets...")

    for rf in ui_packs:
        if tested >= sample_limit:
            break
        pdata = romfs.read_file(rf)
        if not pack.Pack.is_pack(pdata):
            continue
        p = pack.Pack.parse(pdata)
        for e in p.entries:
            if tested >= sample_limit:
                break
            if e.name.endswith(".arc") and e.data[:4] == b"SARC":
                arc = Sarc.parse(e.data)
                for node in arc.nodes:
                    if tested >= sample_limit:
                        break
                    raw = arc.files[node.name]
                    if node.name.endswith(".bflyt"):
                        d = parse_bflyt(raw)
                        rebuilt = build_bflyt(d)
                        tested += 1
                        if rebuilt == raw:
                            passed += 1
                        else:
                            print(f"  [MISMATCH] {node.name}: len {len(rebuilt)} vs {len(raw)}")
                    elif node.name.endswith(".bflan"):
                        d = parse_bflan(raw)
                        rebuilt = build_bflan(d)
                        tested += 1
                        if rebuilt == raw:
                            passed += 1
                        else:
                            print(f"  [MISMATCH] {node.name}: len {len(rebuilt)} vs {len(raw)}")

    f.close()
    pct = (passed / tested * 100) if tested > 0 else 0
    print(f"Round-trip validation: {passed}/{tested} passed bit-matching ({pct:.1f}%)")
    return passed, tested


def main():
    parser = argparse.ArgumentParser(description="DQXI 3DS NW4C BFLYT Layout & BFLAN Animation Tool")
    sub = parser.add_subparsers(dest="command")

    ext_p = sub.add_parser("extract", help="Batch disassemble layouts & animations to JSON")
    ext_p.add_argument("--limit", type=int, default=None, help="Limit number of packs to process")
    ext_p.add_argument("--out", type=Path, default=LAYOUTS_OUT, help="Target output directory")

    reb_p = sub.add_parser("rebuild", help="Re-encode JSON to BFLYT or BFLAN binary")
    reb_p.add_argument("json", type=Path, help="Input JSON file")
    reb_p.add_argument("--out", type=Path, required=True, help="Output binary file")

    ver_p = sub.add_parser("verify", help="Verify lossless round-trip re-encoding")
    ver_p.add_argument("--limit", type=int, default=50, help="Number of assets to test")

    add_p = sub.add_parser("add-pane", help="Copy a pane under a new name (BFLYT or layout JSON)")
    add_p.add_argument("input", type=Path, help=".bflyt or .layout.json")
    add_p.add_argument("--copy", required=True, help="name of the pane to copy")
    add_p.add_argument("--name", required=True, help="name of the new pane (1-23 ASCII chars)")
    add_p.add_argument("--out", type=Path, required=True, help=".bflyt or .json to write")
    add_p.add_argument("--base", type=Path, help="original .bflyt, needed for an exported JSON")

    args = parser.parse_args()

    if args.command == "add-pane":
        raw = args.input.read_bytes()
        d = parse_bflyt(raw) if raw[:4] == b"FLYT" else json.loads(raw.decode("utf-8"))
        if "raw_sections" not in d:
            if not args.base:
                parser.error("this JSON has no raw sections; pass --base <original .bflyt>")
            d = complete(d, args.base.read_bytes())
        d = add_pane(d, args.copy, args.name)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        if args.out.suffix == ".json":
            args.out.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        else:
            args.out.write_bytes(build_bflyt(d))
        print(f"added pane {args.name!r} (copy of {args.copy!r}) -> {args.out}")
        return 0

    if args.command == "extract":
        lyt, lan = batch_extract(args.out, args.limit)
        return 0 if (lyt + lan) > 0 else 1
    elif args.command == "rebuild":
        d = json.loads(args.json.read_text(encoding="utf-8"))
        fmt = d.get("format", "")
        if fmt == "BFLYT":
            b = build_bflyt(d)
        elif fmt == "BFLAN":
            b = build_bflan(d)
        else:
            raise ValueError(f"Unknown format in JSON: {fmt}")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(b)
        print(f"Rebuilt binary saved to {args.out} ({len(b)} bytes)")
        return 0
    elif args.command == "verify":
        passed, tested = verify_roundtrip(args.limit)
        return 0 if passed == tested and tested > 0 else 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
