#!/usr/bin/env python3
"""Read and rebuild Nintendo SARC archives (`.arc`) without changing names.

DQXI's UI packs hold one SARC whose members are the BFLYT/BFLAN/BFLIM files.
The other asset tools patch the files extracted from that archive; this module
puts a replacement back into the archive. A same-size replacement is a byte
copy at the node's data offset; any other size rebuilds the SFAT/SFNT tables
with the original node order, hashes and names, so the game still finds every
member.

A same-size replacement is a byte copy at the node's data offset and is
byte-identical for an unchanged file (see ``tests/test_asset_replace.py``).
A rebuild after a size change closes the retail archive's inter-member
alignment gaps, so it is smaller but parses to the same members.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

SARC_HEADER_SIZE = 0x14
DEFAULT_HASH_KEY = 0x65


@dataclass
class Node:
    hash: int
    attrs: int
    start: int
    end: int
    name: str


class SarcArchive:
    def __init__(self, raw: bytes, data_offset: int, nodes: list[Node]):
        self.raw = raw
        self.data_offset = data_offset
        self.nodes = nodes

    @classmethod
    def parse(cls, data: bytes) -> "SarcArchive":
        if data[:4] != b"SARC":
            raise ValueError("not a SARC archive")
        hsize, _bom, _fsize, doff, _ver = struct.unpack_from("<HHIIH", data, 4)
        p = hsize
        fh, count, _mult = struct.unpack_from("<HHI", data, p + 4)
        nodes_off = p + fh
        sfnt = nodes_off + count * 16
        names_off = sfnt + struct.unpack_from("<H", data, sfnt + 4)[0]
        nodes = []
        for i in range(count):
            h, attrs, start, end = struct.unpack_from("<IIII", data, nodes_off + i * 16)
            name = ""
            if attrs & 0x01000000:
                no = names_off + (attrs & 0xFFFF) * 4
                name = data[no:data.index(b"\0", no)].decode("utf-8", "replace")
            nodes.append(Node(h, attrs, start, end, name))
        return cls(data, doff, nodes)

    def member(self, name: str) -> bytes:
        node = next((n for n in self.nodes if n.name.lower() == name.lower()), None)
        if node is None:
            names = ", ".join(n.name for n in self.nodes[:20])
            raise KeyError(f"no member {name!r}; first members: {names}")
        return self.raw[self.data_offset + node.start:self.data_offset + node.end]

    def replace(self, name: str, payload: bytes) -> bytes:
        return replace_member(self.raw, name, payload)


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def build_sarc(raw: bytes, replacements: dict[str, bytes] | None = None) -> bytes:
    """Rebuilds a SARC, replacing named members (all others keep their bytes)."""
    replacements = {k.lower(): v for k, v in (replacements or {}).items()}
    archive = SarcArchive.parse(raw)
    hsize = struct.unpack_from("<H", raw, 4)[0]
    if hsize < SARC_HEADER_SIZE or hsize > len(raw):
        raise ValueError(f"unsupported SARC header size 0x{hsize:X}")

    names = bytearray()
    attrs: list[int] = []
    for node in archive.nodes:
        if node.attrs & 0x01000000 or node.name:
            offset = len(names)
            if offset % 4:
                raise ValueError("internal error: SARC name table is not 4-byte aligned")
            names += node.name.encode("utf-8") + b"\0"
            while len(names) % 4:
                names.append(0)
            attrs.append((node.attrs & 0xFF000000) | (offset // 4))
        else:
            attrs.append(node.attrs & 0xFF000000)

    sfat = bytearray(b"SFAT" + struct.pack("<HHI", 0x0C, len(archive.nodes), DEFAULT_HASH_KEY))
    entries = bytearray()
    body = bytearray()
    for node, attr in zip(archive.nodes, attrs):
        payload = replacements.get(node.name.lower())
        if payload is None:
            payload = archive.raw[archive.data_offset + node.start:archive.data_offset + node.end]
        while len(body) % 4:
            body.append(0)
        start = len(body)
        body += payload
        entries += struct.pack("<IIII", node.hash, attr, start, len(body))

    sfnt = bytearray(b"SFNT" + struct.pack("<HH", 0x08, 0))
    sfnt += names
    head_end = hsize + len(sfat) + len(entries) + len(sfnt)
    data_offset = _align(head_end, 0x80)

    out = bytearray(raw[:hsize])
    total = data_offset + len(body)
    struct.pack_into("<I", out, 0x08, total)
    struct.pack_into("<I", out, 0x0C, data_offset)
    out += sfat + entries + sfnt
    out += bytes(data_offset - len(out))
    out += body
    return bytes(out)


def replace_member(raw: bytes, name: str, payload: bytes) -> bytes:
    archive = SarcArchive.parse(raw)
    node = next((n for n in archive.nodes if n.name.lower() == name.lower()), None)
    if node is None:
        names = ", ".join(n.name for n in archive.nodes[:20])
        raise KeyError(f"no member {name!r}; first members: {names}")
    start = archive.data_offset + node.start
    end = archive.data_offset + node.end
    if len(payload) == end - start:
        out = bytearray(raw)
        out[start:end] = payload
        return bytes(out)
    return build_sarc(raw, {name: payload})


def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("arc", type=Path)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--member")
    ap.add_argument("--replacement", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    raw = args.arc.read_bytes()
    archive = SarcArchive.parse(raw)
    if args.list:
        for n in archive.nodes:
            print(f"{n.name:56s} {n.end - n.start:>10} @ 0x{archive.data_offset + n.start:X}")
        return 0
    if not (args.member and args.replacement and args.out):
        ap.error("--member, --replacement and --out are required unless --list is used")
    out = replace_member(raw, args.member, args.replacement.read_bytes())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(out)
    print(f"wrote {args.out} ({len(raw)} -> {len(out)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
