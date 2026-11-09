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
    # the bytes the pack was parsed from (still BLZ-compressed for a PACA)
    orig: bytes = b""

    @staticmethod
    def is_pack(data: bytes) -> bool:
        return data[:4] in (b"PACK", b"PACA")

    @classmethod
    def parse(cls, data: bytes) -> "Pack":
        orig = bytes(data)
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
        # keep the file as it arrived (PACA: still BLZ-compressed); an unchanged
        # rebuild must return these exact bytes, not this encoder's re-compression
        p.orig = orig
        return p

    def build(self) -> bytes:
        """Serialise the pack.

        When no member changed and the original leaves room for an in-place
        overwrite, the original bytes are returned verbatim: an unchanged
        round-trip is byte-identical for PACK and for PACA (a BLZ re-encode of
        an untouched stream is close to, but not byte-equal to, the original,
        so the original must be preserved).
        """
        uncompressed = self._build_in_place()
        if uncompressed is not None and self.orig and self.orig[:4] in (b"PACK", b"PACA"):
            plain = blz.decompress(self.orig) if self.orig[:4] == b"PACA" else self.orig
            if uncompressed == plain:
                return self.orig
        if uncompressed is None:
            uncompressed = self._build_relayout()
        if self.compressed:
            return _compress_paca(uncompressed)
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
        """Lays the members out afresh (needed when a member changes size).

        Members keep the payload alignment they had in the retail pack (up to
        0x80 bytes).  Textures and SARC layouts are read in place by the GPU/DMA
        and the game returns null textures — and later crashes entering a battle
        — when a payload moves off its 0x80 boundary, so the padding is applied
        to the *payload* start (entry header length included), not to the entry.
        """
        count = len(self.entries)
        hsize = 0x18 + count * 12
        while hsize % 4:
            hsize += 1

        body = bytearray()
        offs = []
        for e in self.entries:
            while (hsize + len(body) + len(e.raw_header)) % e.align:
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


def _compress_paca(uncompressed: bytes) -> bytes:
    """Encode a PACK buffer as a PACA file the console accepts.

    Retail PACA is ``"PACA" + u32 decompressed size + BLZ(the rest of the PACK)``:
    the 8-byte prefix is stored literally so the loader can recognise the magic
    before it decompresses anything.  Compressing the whole buffer instead (the
    old behaviour) sometimes lets the BLZ stream start inside the magic, which
    produces a file whose first four bytes are no longer ``PACA`` — the game
    then treats it as an uncompressed PACK and fails.  Compressing only
    ``buffer[8:]`` and keeping the prefix literal reproduces the retail layout;
    the reference translation project builds its packs the same way.
    """
    compressed = blz.compress(uncompressed[8:], allow_overlap=True)
    out = b"PACA" + struct.pack("<I", len(uncompressed)) + compressed
    if blz.decompress(out) != uncompressed:
        raise ValueError("PACA recompression does not decompress to the pack")
    return out


def audit(root: Path, limit: int | None = None) -> dict:
    """Parse and rebuild every PACK/PACA under ``root`` and compare the bytes.

    This is the modder-facing form of the promise "an unchanged pack round-trips
    exactly": useful before a bulk edit and as a slow, exhaustive regression on a
    machine with the extracted tree.  Returns a JSON-able summary.
    """
    packs = sorted(Path(root).rglob("*.pack"))
    if limit:
        packs = packs[:limit]
    bad: list[dict] = []
    compressed = 0
    for path in packs:
        raw = path.read_bytes()
        try:
            p = Pack.parse(raw)
            compressed += int(p.compressed)
            rebuilt = p.build()
        except Exception as exc:                       # noqa: BLE001 - report, do not stop
            bad.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
            continue
        if rebuilt != raw:
            bad.append({"path": str(path), "error": "rebuild differs",
                        "bytes": len(raw), "rebuilt_bytes": len(rebuilt)})
    return {"root": str(root), "packs": len(packs), "compressed": compressed,
            "identical": len(packs) - len(bad), "bad": bad}


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="PACK/PACA round-trip audit")
    ap.add_argument("root", nargs="?", default="game_data/romfs",
                    help="directory to scan (default: game_data/romfs)")
    ap.add_argument("--limit", type=int, help="only the first N packs (quick check)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    report = audit(Path(args.root), args.limit)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['identical']:,} / {report['packs']:,} packs round-trip "
              f"byte-identically ({report['compressed']:,} PACA)")
        for item in report["bad"][:20]:
            print(f"  BAD {item['path']}: {item['error']}")
    return 0 if not report["bad"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
