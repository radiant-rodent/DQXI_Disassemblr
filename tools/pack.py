#!/usr/bin/env python3
"""tools/pack.py - DQXI 3DS PACK / PACA archive format parser and builder.

PACK layout (little endian):
  0x00 "PACK"
  0x04 u32 total size
  0x08 u16 version (0x0100)   0x0A u16 BOM (0xFEFF)
  0x0C u16 entry count        0x0E u16 header size (0x18)
  0x10 u32 unknown (alignment/flags)   0x14 u32 hash
  0x18 u32[count] entry offsets
       u32[count*2] name hashes
  entries: u16 entry header size, u16 flags, u32 data size, name (NUL padded), data
           entries are 4-byte aligned

PACA = "PACA" + u32 decompressed size + BLZ-compressed remainder of the PACK file.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from . import blz

MAX_ALIGN = 0x80


@dataclass
class PackEntry:
    name: str
    data: bytes
    flags: int
    header_size: int
    raw_header: bytes
    align: int = 4
    payload_offset: int = 0


@dataclass
class Pack:
    compressed: bool
    header: bytes
    hashes: bytes
    entries: list[PackEntry] = field(default_factory=list)
    tail: bytes = b""
    # the parsed (decompressed) pack, so same-size edits keep the exact layout
    raw: bytes = b""

    @staticmethod
    def is_pack(data: bytes) -> bool:
        return data[:4] in (b"PACK", b"PACA")

    @classmethod
    def parse(cls, data: bytes) -> "Pack":
        magic = data[:4]
        compressed = magic == b"PACA"
        if compressed:
            data = blz.decompress(data)
        elif magic != b"PACK":
            raise ValueError("not a pack")
        total, = struct.unpack_from("<I", data, 4)
        count, hsize = struct.unpack_from("<HH", data, 0x0C)
        offs = struct.unpack_from(f"<{count}I", data, 0x18)
        hashes = data[0x18 + 4 * count: 0x18 + 12 * count]
        p = cls(compressed, data[8:0x18], hashes)

        for i, off in enumerate(offs):
            esize, flags, dsize = struct.unpack_from("<HHI", data, off)
            raw_h = data[off:off + esize]
            name = raw_h[8:].split(b"\0", 1)[0].decode("ascii", "replace")
            pld_start = off + esize
            nxt = offs[i + 1] if i + 1 < count else total
            pld_bytes = nxt - pld_start
            align = 4
            if dsize and pld_bytes >= dsize:
                for a in (128, 64, 32, 16, 8):
                    if pld_start % a == 0:
                        align = a
                        break
            p.entries.append(PackEntry(name, data[pld_start:pld_start + dsize], flags, esize, raw_h, align, pld_start))
        if total < len(data):
            p.tail = data[total:]
        p.raw = bytes(data)
        return p

    def build(self) -> bytes:
        uncompressed = self._build_in_place() or self._build_relayout()
        if self.compressed:
            return blz.compress(uncompressed, allow_overlap=True)
        return uncompressed

    def _build_in_place(self) -> bytes | None:
        """Same member sizes: overwrite payloads in the original buffer (exact layout)."""
        if not self.raw:
            return None
        out = bytearray(self.raw)
        for e in self.entries:
            end = e.payload_offset + len(e.data)
            original_len = struct.unpack_from("<I", out, e.payload_offset - e.header_size + 4)[0]
            if not e.payload_offset or len(e.data) != original_len or end > len(out):
                return None
            out[e.payload_offset:end] = e.data
        return bytes(out)

    def _build_relayout(self) -> bytes:
        """Lays the members out afresh (needed when a member changes size)."""
        count = len(self.entries)
        hsize = 0x18 + count * 12
        while hsize % 4:
            hsize += 1

        body = bytearray()
        offs = []
        for e in self.entries:
            while (hsize + len(body)) % e.align:
                body.append(0)
            offs.append(hsize + len(body))
            raw = bytearray(e.raw_header)
            struct.pack_into("<I", raw, 4, len(e.data))
            body += raw
            body += e.data

        total = hsize + len(body)
        # a compressed pack's decompressed stream keeps the "PACA" magic in its
        # own header; BLZ leaves that prefix uncompressed
        magic = b"PACA" if self.compressed else b"PACK"
        hdr = bytearray(magic) + struct.pack("<I", total) + self.header[:4]
        header = bytearray(self.header)
        struct.pack_into("<HH", header, 4, count, 0x18)
        hdr += header[4:16]
        hdr += struct.pack(f"<{count}I", *offs)
        hdr += self.hashes[:count * 8]
        while len(hdr) < hsize:
            hdr.append(0)

        return bytes(hdr + body + self.tail)
