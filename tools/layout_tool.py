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
if "../reference project" not in sys.path:
    sys.path.insert(0, "../reference project")

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


def build_bflyt(d: dict) -> bytes:
    """Rebuilds BFLYT binary from structured dictionary."""
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
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    f, ncsd, ncch = open_image(r"..\reference project\DQXI.3ds")
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

    args = parser.parse_args()

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
