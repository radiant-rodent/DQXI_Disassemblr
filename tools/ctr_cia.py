#!/usr/bin/env python3
"""Build and verify installable (fakesigned) CIA containers for Nintendo 3DS.

Ported and adapted from ``..\\3DS_Translate\\dq11tool\\ctr\\cia.py``
and ``formats.py`` (credit to the Dragon Quest XI 3DS English translation project).

A CTR Importable Archive (.cia) contains:
  * Header (0x2020 bytes): section sizes, content mask
  * Certificate chain: genuine Nintendo CA certificates extracted from the
    cartridge update partition (partition 6 or 7)
  * Ticket: fakesigned ticket (blank RSA-2048 signature), zeroed title key
    (for unencrypted NCCH content), matching title ID (0004000000199200)
  * TMD (Title Metadata): fakesigned TMD with title ID, save data size from
    ExHeader, and SHA-256 chunk records for each content partition
  * Content partitions:
      Index 0: Game NCCH (partition 0)
      Index 1: Electronic manual CFA (partition 1, optional)
  * Meta: dependency list from ExHeader + SMDH icon from ExeFS

Installing on a real 3DS requires custom firmware (Luma3DS provides signature
patches) and FBI.

The result is byte-identical to the translation project's ``dq11tool.ctr.cia``
for the same input image (checked on ``build/DQXI_patched.3ds``: both
2,685,129,728 bytes, SHA-256 ``517d38cd…d5424d``), and the browser patcher's
JavaScript port produces the same layout.  Azahar installed the result through
its ``-i/--install`` option (exact TMD, both contents with matching SHA-256).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import os
import struct
import sys
import time
from pathlib import Path
from typing import Callable, Optional

ALIGN = 64
META_SIZE = 0x3AC0
MEDIA_UNIT = 0x200
BLOCK_SIZE = 8 * 1024 * 1024  # 8 MiB streaming chunk


def _align(x: int, a: int = ALIGN) -> int:
    return (x + a - 1) // a * a


class Window:
    """A read-only slice view of an open binary file."""

    def __init__(self, f, offset: int, size: int):
        self.f = f
        self.offset = offset
        self.size = size

    def read(self, off: int, size: int) -> bytes:
        if off < 0 or off + size > self.size:
            raise ValueError(f"read out of window: {off:#x}+{size:#x} > {self.size:#x}")
        self.f.seek(self.offset + off)
        return self.f.read(size)

    def sub(self, off: int, size: int) -> "Window":
        return Window(self.f, self.offset + off, size)


# --------------------------------------------------------------------------- #
# NCSD container
# --------------------------------------------------------------------------- #

@dataclasses.dataclass
class NcsdPartition:
    index: int
    offset: int  # absolute byte offset in file
    size: int    # byte size
    fs_type: int
    crypt_type: int
    partition_id: int


@dataclasses.dataclass
class Ncsd:
    header: bytes
    image_size: int
    media_id: int
    partitions: list[NcsdPartition]

    @classmethod
    def parse(cls, f) -> "Ncsd":
        f.seek(0)
        header = f.read(0x4000)
        if len(header) < 0x200 or header[0x100:0x104] != b"NCSD":
            raise ValueError("not an NCSD (.3ds/.cci) image")
        image_size = struct.unpack_from("<I", header, 0x104)[0] * MEDIA_UNIT
        media_id = struct.unpack_from("<Q", header, 0x108)[0]
        parts = []
        for i in range(8):
            off, size = struct.unpack_from("<II", header, 0x120 + i * 8)
            if size == 0:
                continue
            pid = struct.unpack_from("<Q", header, 0x190 + i * 8)[0]
            parts.append(NcsdPartition(
                i, off * MEDIA_UNIT, size * MEDIA_UNIT,
                header[0x110 + i], header[0x118 + i], pid
            ))
        return cls(header, image_size, media_id, parts)

    def partition(self, index: int) -> Optional[NcsdPartition]:
        for p in self.partitions:
            if p.index == index:
                return p
        return None


# --------------------------------------------------------------------------- #
# ExeFS container
# --------------------------------------------------------------------------- #

@dataclasses.dataclass
class ExeFsEntry:
    name: str
    offset: int  # relative to end of 0x200 header
    size: int


@dataclasses.dataclass
class ExeFs:
    win: Window
    entries: list[ExeFsEntry]

    @classmethod
    def parse(cls, win: Window) -> "ExeFs":
        h = win.read(0, 0x200)
        entries = []
        for i in range(10):
            raw = h[i * 16:(i + 1) * 16]
            name = raw[:8].rstrip(b"\0").decode("ascii", "replace")
            off, size = struct.unpack_from("<II", raw, 8)
            if name and size > 0:
                entries.append(ExeFsEntry(name, off, size))
        return cls(win, entries)

    def read(self, name: str) -> bytes:
        for e in self.entries:
            if e.name == name:
                return self.win.read(0x200 + e.offset, e.size)
        raise KeyError(name)


# --------------------------------------------------------------------------- #
# RomFS container
# --------------------------------------------------------------------------- #

@dataclasses.dataclass
class IvfcLevel:
    logical_offset: int
    size: int
    block_log2: int


@dataclasses.dataclass
class RomFsFile:
    path: str
    offset: int
    size: int


@dataclasses.dataclass
class RomFs:
    win: Window
    levels: list[IvfcLevel]
    level3_offset: int
    data_offset: int
    files: list[RomFsFile]

    @classmethod
    def parse(cls, win: Window) -> "RomFs":
        h = win.read(0, 0x60)
        if h[:4] != b"IVFC" or struct.unpack_from("<I", h, 4)[0] != 0x10000:
            raise ValueError("bad IVFC header in RomFS")
        mhs = struct.unpack_from("<I", h, 8)[0]
        levels = []
        for i in range(3):
            lo, sz, bl = struct.unpack_from("<QQI", h, 0x0C + i * 0x18)
            levels.append(IvfcLevel(lo, sz, bl))
        l3_off = _align(0x60 + mhs, 1 << levels[2].block_log2)
        l3 = win.sub(l3_off, levels[2].size)
        lh = l3.read(0, 0x28)
        (hdr_size, dht_off, dht_size, dmt_off, dmt_size,
         fht_off, fht_size, fmt_off, fmt_size, data_off) = struct.unpack("<10I", lh)
        dmt = l3.read(dmt_off, dmt_size)
        fmt = l3.read(fmt_off, fmt_size)
        files: list[RomFsFile] = []

        def name_at(buf: bytes, off: int, base: int) -> str:
            nlen = struct.unpack_from("<I", buf, off + base)[0]
            return buf[off + base + 4:off + base + 4 + nlen].decode("utf-16-le", "replace")

        def walk_dir(off: int, path: str):
            parent, sibling, child, first_file, nxt = struct.unpack_from("<5I", dmt, off)
            f_off = first_file
            while f_off != 0xFFFFFFFF:
                fp, fs, doff, dsize, fnext = struct.unpack_from("<IIQQI", fmt, f_off)
                fname = name_at(fmt, f_off, 0x1C)
                rf = RomFsFile(f"{path.rstrip('/')}/{fname}", doff, dsize)
                files.append(rf)
                f_off = fs
            c_off = child
            while c_off != 0xFFFFFFFF:
                cname = name_at(dmt, c_off, 0x14)
                walk_dir(c_off, f"{path.rstrip('/')}/{cname}")
                c_off = struct.unpack_from("<I", dmt, c_off + 4)[0]

        walk_dir(0, "/")
        return cls(win, levels, l3_off, data_off, files)

    def read_file(self, rf: RomFsFile) -> bytes:
        return self.win.read(self.level3_offset + self.data_offset + rf.offset, rf.size)


# --------------------------------------------------------------------------- #
# NCCH container
# --------------------------------------------------------------------------- #

@dataclasses.dataclass
class Ncch:
    win: Window
    header: bytes
    content_size: int
    partition_id: int
    program_id: int
    product_code: str
    exheader_size: int
    flags: bytes
    plain_offset: int
    plain_size: int
    logo_offset: int
    logo_size: int
    exefs_offset: int
    exefs_size: int
    romfs_offset: int
    romfs_size: int

    @classmethod
    def parse(cls, win: Window) -> "Ncch":
        h = win.read(0, 0x200)
        if h[0x100:0x104] != b"NCCH":
            raise ValueError("not an NCCH partition")
        u32 = lambda o: struct.unpack_from("<I", h, o)[0]
        return cls(
            win=win,
            header=h,
            content_size=u32(0x104) * MEDIA_UNIT,
            partition_id=struct.unpack_from("<Q", h, 0x108)[0],
            program_id=struct.unpack_from("<Q", h, 0x118)[0],
            product_code=h[0x150:0x160].rstrip(b"\0").decode("ascii", "replace"),
            exheader_size=u32(0x180),
            flags=h[0x188:0x190],
            plain_offset=u32(0x190) * MEDIA_UNIT,
            plain_size=u32(0x194) * MEDIA_UNIT,
            logo_offset=u32(0x198) * MEDIA_UNIT,
            logo_size=u32(0x19C) * MEDIA_UNIT,
            exefs_offset=u32(0x1A0) * MEDIA_UNIT,
            exefs_size=u32(0x1A4) * MEDIA_UNIT,
            romfs_offset=u32(0x1B0) * MEDIA_UNIT,
            romfs_size=u32(0x1B4) * MEDIA_UNIT,
        )

    def exheader(self) -> bytes:
        return self.win.read(0x200, 0x800 if self.exheader_size else 0)

    def exefs(self) -> Optional[ExeFs]:
        if not self.exefs_size:
            return None
        return ExeFs.parse(self.win.sub(self.exefs_offset, self.exefs_size))

    def romfs(self) -> Optional[RomFs]:
        if not self.romfs_size:
            return None
        return RomFs.parse(self.win.sub(self.romfs_offset, self.romfs_size))


# --------------------------------------------------------------------------- #
# CIA builder routines
# --------------------------------------------------------------------------- #

def _find_template_cia(f, ncsd: Ncsd) -> bytes:
    """Find a system update CIA in partition 7 or 6 to take the certificate chain and ticket layout."""
    for idx in (7, 6):
        p = ncsd.partition(idx)
        if not p:
            continue
        try:
            ncch = Ncch.parse(Window(f, p.offset, p.size))
            r = ncch.romfs()
            if not r:
                continue
            for x in r.files:
                if x.path.lower().endswith(".cia") and x.size < 16 << 20:
                    d = r.read_file(x)
                    if len(d) >= 0x20:
                        hs, typ, ver, cs, ts = struct.unpack_from("<IHHII", d, 0)
                        if hs == 0x2020 and cs and ts == 0x350:
                            return d
        except Exception:
            continue

    # Fallback: check original/partitions/ on disk if update partitions were trimmed
    project_root = Path(__file__).resolve().parent.parent
    for part_name in ("update_o3ds.ncch", "update_n3ds.ncch"):
        part_path = project_root / "original" / "partitions" / part_name
        if part_path.is_file():
            try:
                with open(part_path, "rb") as pf:
                    ncch = Ncch.parse(Window(pf, 0, part_path.stat().st_size))
                    r = ncch.romfs()
                    if r:
                        for x in r.files:
                            if x.path.lower().endswith(".cia") and x.size < 16 << 20:
                                d = r.read_file(x)
                                if len(d) >= 0x20:
                                    hs, typ, ver, cs, ts = struct.unpack_from("<IHHII", d, 0)
                                    if hs == 0x2020 and cs and ts == 0x350:
                                        return d
            except Exception:
                continue

    raise RuntimeError("no system CIA found in the update partition to take the certificate chain from")


def _ticket(template_ticket: bytes, title_id: int) -> bytes:
    """Build a fakesigned, unencrypted ticket for title_id."""
    t = bytearray(template_ticket)
    # Blank the RSA-2048 signature (0x100 bytes starting after 4-byte sig type)
    t[4:0x104] = b"\0" * 0x100
    # Zero title key at 0x1BF..0x1CF (contents are not encrypted)
    t[0x1BF:0x1CF] = b"\0" * 0x10
    # Ticket ID: 0x0004000000000000 | (lower 32 bits of title_id)
    struct.pack_into(">Q", t, 0x1D0, 0x0004000000000000 | (title_id & 0xFFFFFFFF))
    struct.pack_into(">I", t, 0x1D8, 0)             # Console ID (0 = not console-locked)
    struct.pack_into(">Q", t, 0x1DC, title_id)      # Title ID
    struct.pack_into(">H", t, 0x1E6, 0)             # Ticket title version
    t[0x1F0] = 0                                    # License type (permanent)
    t[0x1F1] = 0                                    # Common key index
    struct.pack_into(">I", t, 0x21C, 0)             # eShop account ID
    return bytes(t)


def _tmd(title_id: int, save_size: int, contents: list[tuple[int, int, int, bytes]]) -> bytes:
    """Build a fakesigned TMD (Title Metadata).

    contents: list of (content_index, type_flags, size_bytes, sha256_digest)
    """
    hdr = bytearray(0xC4)
    hdr[0:0x40] = b"Root-CA00000003-CP0000000b".ljust(0x40, b"\0")
    hdr[0x40] = 1                                    # TMD version
    struct.pack_into(">Q", hdr, 0x4C, title_id)      # Title ID
    struct.pack_into(">I", hdr, 0x54, 0x40)          # Title type: CTR (0x40)
    struct.pack_into("<I", hdr, 0x5A, save_size)     # Save data size (little-endian)
    struct.pack_into(">H", hdr, 0x9C, 0)             # Title version
    struct.pack_into(">H", hdr, 0x9E, len(contents)) # Number of contents
    struct.pack_into(">H", hdr, 0xA0, 0)             # Boot content index (0)

    chunks = bytearray()
    for i, (index, flags, size, digest) in enumerate(contents):
        # Content chunk record: content_id (u32), content_index (u16), flags (u16), size (u64)
        chunks += struct.pack(">IHHQ", i, index, flags, size) + digest

    # Content info records: 64 entries of 0x24 bytes (0x900 bytes total)
    info = bytearray(0x24 * 64)
    # First record covers the contents: index offset = 0, count = len(contents)
    struct.pack_into(">HH", info, 0, 0, len(contents))
    # Hash of chunk records
    info[4:0x24] = hashlib.sha256(chunks).digest()

    # TMD header stores SHA-256 of the content info records at 0xA4
    hdr[0xA4:0xC4] = hashlib.sha256(info).digest()

    # RSA-2048 SHA-256 signature block: type 0x00010004 + 0x100 zero bytes + 0x3C padding
    sig = struct.pack(">I", 0x00010004) + b"\0" * 0x100 + b"\0" * 0x3C
    return sig + bytes(hdr) + bytes(info) + bytes(chunks)


def _meta(exheader: bytes, icon: bytes) -> bytes:
    """Build the CIA metadata section (dependencies + core version + SMDH icon)."""
    m = bytearray(META_SIZE)
    if len(exheader) >= 0x1C0:
        m[0:0x180] = exheader[0x40:0x1C0]            # Dependency list from ExHeader
    struct.pack_into("<I", m, 0x300, 2)              # Core version = 2
    if icon:
        m[0x400:0x400 + min(len(icon), 0x36C0)] = icon[:0x36C0]
    return bytes(m)


def build_cia(src_path: str | Path, out_path: str | Path,
              progress: Optional[Callable[[str, int, int], None]] = None) -> dict:
    """Build an installable CIA from a decrypted .3ds image.

    Args:
        src_path: Path to the input .3ds image (must be decrypted).
        out_path: Destination path for the output .cia file.
        progress: Optional callback progress(stage_name, done_bytes, total_bytes).

    Returns:
        dict with metadata and verification details of the produced CIA.
    """
    src_path = str(src_path)
    out_path = str(out_path)
    progress = progress or (lambda *a: None)

    f = open(src_path, "rb")
    try:
        ncsd = Ncsd.parse(f)
        p0 = ncsd.partition(0)
        if not p0:
            raise ValueError("NCSD image has no partition 0 (game)")
        ncch = Ncch.parse(Window(f, p0.offset, p0.size))
        # The ticket we build has a zero title key and the content chunks are
        # marked "not encrypted".  That only describes an image whose NCCH is
        # already decrypted; feeding it an encrypted dump would produce a CIA
        # that installs garbage, so stop with a message the user can act on.
        if not ncch.flags[7] & 0x04:
            raise ValueError(
                f"{src_path} is not a decrypted image (NCCH flags "
                f"{ncch.flags.hex()}): the CIA builder writes unencrypted contents "
                "with a zero title key.  Dump/decrypt the cartridge first "
                "(GodMode9: 'Decrypt file' / 'NCSD image options').")
        title_id = ncch.program_id
        exheader = ncch.exheader()
        save_size = struct.unpack_from("<Q", exheader, 0x1C0)[0] if len(exheader) >= 0x1C8 else 0
        try:
            exefs = ncch.exefs()
            icon = exefs.read("icon") if exefs else b""
        except KeyError:
            icon = b""

        tpl = _find_template_cia(f, ncsd)
        hs, typ, ver, cs, ts = struct.unpack_from("<IHHII", tpl, 0)
        cert_off = _align(hs)
        certs = tpl[cert_off:cert_off + cs]
        tik_off = _align(cert_off + cs)
        ticket = _ticket(tpl[tik_off:tik_off + ts], title_id)

        parts = [(0, 0x0000, p0)]
        man = ncsd.partition(1)
        if man:
            parts.append((1, 0x4000, man))          # optional manual CFA
        total = sum(p.size for _, _, p in parts)

        # Pass 1: hash contents
        digests = []
        done = 0
        for index, flags, p in parts:
            h = hashlib.sha256()
            remaining, pos = p.size, p.offset
            while remaining:
                n = min(remaining, BLOCK_SIZE)
                f.seek(pos)
                chunk = f.read(n)
                if not chunk:
                    raise IOError(f"unexpected EOF reading partition {index}")
                h.update(chunk)
                pos += len(chunk)
                remaining -= len(chunk)
                done += len(chunk)
                progress("Hashing CIA contents", done, total)
            digests.append(h.digest())

        contents = [(index, flags, p.size, d) for (index, flags, p), d in zip(parts, digests)]
        tmd = _tmd(title_id, save_size, contents)
        meta = _meta(exheader, icon)
        content_size = sum(_align(p.size) for _, _, p in parts)

        header = bytearray(0x2020)
        struct.pack_into("<IHHIIIIQ", header, 0, 0x2020, 0, 0,
                         len(certs), len(ticket), len(tmd), len(meta), content_size)
        for index, _, _ in parts:
            header[0x20 + index // 8] |= 0x80 >> (index % 8)

        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "wb") as out:
            def put(data: bytes):
                out.write(data)
                pad = _align(out.tell()) - out.tell()
                if pad:
                    out.write(b"\0" * pad)

            put(bytes(header))
            put(certs)
            put(ticket)
            put(tmd)
            done = 0
            for index, flags, p in parts:
                remaining, pos = p.size, p.offset
                while remaining:
                    n = min(remaining, BLOCK_SIZE)
                    f.seek(pos)
                    chunk = f.read(n)
                    if not chunk:
                        raise IOError(f"unexpected EOF writing partition {index}")
                    out.write(chunk)
                    pos += len(chunk)
                    remaining -= len(chunk)
                    done += len(chunk)
                    progress("Writing CIA", done, total)
                pad = _align(out.tell()) - out.tell()
                if pad:
                    out.write(b"\0" * pad)
            put(meta)
    finally:
        f.close()

    # Structural verification of the written CIA
    problems = verify_cia(out_path)
    if problems:
        raise RuntimeError(f"built CIA failed verification: {'; '.join(problems)}")

    cia_stat = os.stat(out_path)
    with open(out_path, "rb") as fp:
        fp.seek(0)
        h = hashlib.sha256()
        while chunk := fp.read(BLOCK_SIZE):
            h.update(chunk)
        cia_sha256 = h.hexdigest()

    return {
        "path": out_path,
        "size": cia_stat.st_size,
        "sha256": cia_sha256,
        "title_id": f"{title_id:016X}",
        "cert_size": len(certs),
        "ticket_size": len(ticket),
        "tmd_size": len(tmd),
        "meta_size": len(meta),
        "content_size": content_size,
        "contents": [
            {"index": index, "flags": flags, "size": p.size, "sha256": d.hex()}
            for (index, flags, p), d in zip(parts, digests)
        ],
        "valid": True,
        "problems": [],
    }


def verify_cia(path: str | Path) -> list[str]:
    """Structural verification of a CIA container.

    Checks:
      - Header magic (0x2020) and section sizes
      - Ticket title ID vs TMD title ID
      - TMD content info records hash
      - TMD content chunk records hash
      - Each content partition: size, SHA-256 hash against TMD chunk, NCCH magic
      - Overall file size matches sum of aligned sections

    Returns:
        List of problem descriptions (empty if valid).
    """
    problems = []
    path = str(path)
    if not os.path.isfile(path):
        return [f"CIA file does not exist: {path}"]
    file_size = os.path.getsize(path)
    if file_size < 0x2020:
        return [f"CIA file is too small ({file_size} bytes)"]

    with open(path, "rb") as fp:
        h = fp.read(0x2020)
        hs, typ, ver, cs, ts, tms, ms, csz = struct.unpack_from("<IHHIIIIQ", h, 0)
        if hs != 0x2020:
            problems.append(f"unexpected CIA header size: 0x{hs:X} (expected 0x2020)")

        off = _align(hs)
        # Certificate chain
        fp.seek(off)
        certs = fp.read(cs)
        if len(certs) != cs:
            problems.append(f"truncated certificate chain ({len(certs)} != {cs})")
        if cs == 0:
            problems.append("certificate chain is empty")
        elif cs % ALIGN:
            problems.append(f"certificate chain size {cs} is not {ALIGN}-byte aligned")
        elif b"Root-CA" not in certs:
            # Every genuine Nintendo chain names a Root-CA issuer; a chain
            # without one was not copied from the update partition.
            problems.append("certificate chain has no Root-CA issuer name")

        # Ticket
        tik_off = off + _align(cs)
        fp.seek(tik_off)
        tik = fp.read(ts)
        if len(tik) != ts:
            problems.append(f"truncated ticket ({len(tik)} != {ts})")

        # TMD
        tmd_off = tik_off + _align(ts)
        fp.seek(tmd_off)
        tmd = fp.read(tms)
        if len(tmd) != tms:
            problems.append(f"truncated TMD ({len(tmd)} != {tms})")

        if len(tmd) >= 0x140 + 0xA0:
            n = struct.unpack_from(">H", tmd, 0x140 + 0x9E)[0]
            if len(tmd) < 0xB04 + 0x30 * n:
                problems.append("TMD is smaller than expected for stored content count")
            else:
                info = tmd[0x204:0xB04]
                chunks = tmd[0xB04:0xB04 + 0x30 * n]
                if hashlib.sha256(info).digest() != tmd[0x1E4:0x204]:
                    problems.append("TMD content info hash mismatch")
                if hashlib.sha256(chunks).digest() != info[4:0x24]:
                    problems.append("TMD chunk records hash mismatch")

                pos = tmd_off + _align(tms)
                for i in range(n):
                    cid, idx, flags, size = struct.unpack_from(">IHHQ", chunks, i * 0x30)
                    digest = chunks[i * 0x30 + 0x10:i * 0x30 + 0x30]
                    fp.seek(pos)
                    hh = hashlib.sha256()
                    remaining = size
                    while remaining:
                        b = fp.read(min(remaining, BLOCK_SIZE))
                        if not b:
                            problems.append(f"unexpected EOF reading content {i}")
                            break
                        hh.update(b)
                        remaining -= len(b)
                    if remaining == 0 and hh.digest() != digest:
                        problems.append(f"content {i} (index {idx}) hash mismatch")

                    fp.seek(pos)
                    ncch_hdr = fp.read(0x200)
                    if len(ncch_hdr) < 0x104 or ncch_hdr[0x100:0x104] != b"NCCH":
                        problems.append(f"content {i} (index {idx}) is not a valid NCCH")

                    pos += _align(size)

                expected_size = pos + _align(ms)
                if file_size != expected_size:
                    problems.append(f"file size mismatch: actual {file_size} != expected {expected_size}")

        if len(tik) >= 0x1E4 and len(tmd) >= 0x194:
            tik_tid = struct.unpack_from(">Q", tik, 0x1DC)[0]
            tmd_tid = struct.unpack_from(">Q", tmd, 0x18C)[0]
            if tik_tid != tmd_tid:
                problems.append(f"ticket and TMD title IDs differ ({tik_tid:016X} != {tmd_tid:016X})")

    return problems


def parse_cia(path: str | Path) -> dict:
    """Parse structural fields and metadata from a CIA file."""
    path = str(path)
    with open(path, "rb") as fp:
        h = fp.read(0x2020)
        hs, typ, ver, cs, ts, tms, ms, csz = struct.unpack_from("<IHHIIIIQ", h, 0)
        off = _align(hs)
        tik_off = off + _align(cs)
        fp.seek(tik_off)
        tik = fp.read(ts)
        tmd_off = tik_off + _align(ts)
        fp.seek(tmd_off)
        tmd = fp.read(tms)

        title_id = struct.unpack_from(">Q", tmd, 0x18C)[0] if len(tmd) >= 0x194 else 0
        n_contents = struct.unpack_from(">H", tmd, 0x140 + 0x9E)[0] if len(tmd) >= 0x1E0 else 0
        contents = []
        if len(tmd) >= 0xB04 + 0x30 * n_contents:
            chunks = tmd[0xB04:0xB04 + 0x30 * n_contents]
            for i in range(n_contents):
                cid, idx, flags, size = struct.unpack_from(">IHHQ", chunks, i * 0x30)
                digest = chunks[i * 0x30 + 0x10:i * 0x30 + 0x30]
                contents.append({
                    "id": cid,
                    "index": idx,
                    "flags": flags,
                    "size": size,
                    "sha256": digest.hex(),
                })

    problems = verify_cia(path)
    return {
        "header_size": hs,
        "type": typ,
        "version": ver,
        "cert_size": cs,
        "ticket_size": ts,
        "tmd_size": tms,
        "meta_size": ms,
        "content_size": csz,
        "title_id": f"{title_id:016X}",
        "num_contents": n_contents,
        "contents": contents,
        "valid": len(problems) == 0,
        "problems": problems,
    }


# --------------------------------------------------------------------------- #
# CLI entry point
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify a Nintendo 3DS CIA container.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser("build", help="Build a CIA from a .3ds image")
    build_p.add_argument("src", help="Source .3ds image")
    build_p.add_argument("out", help="Output .cia file")

    verify_p = subparsers.add_parser("verify", help="Verify CIA structure and content hashes")
    verify_p.add_argument("cia", help="CIA file to verify")

    info_p = subparsers.add_parser("info", help="Print CIA metadata and structure")
    info_p.add_argument("cia", help="CIA file to inspect")

    args = parser.parse_args(argv)

    if args.command == "build":
        t0 = time.time()
        print(f"Building CIA from {args.src} -> {args.out} ...")
        res = build_cia(args.src, args.out, progress=lambda msg, d, t: None)
        print(f"CIA built OK in {time.time() - t0:.1f}s ({res['size']} bytes, Title ID: {res['title_id']})")
        return 0

    elif args.command == "verify":
        probs = verify_cia(args.cia)
        if probs:
            print("CIA verification FAILED:")
            for p in probs:
                print(f"  * {p}")
            return 1
        print("CIA verification OK (all hashes and structures valid).")
        return 0

    elif args.command == "info":
        info = parse_cia(args.cia)
        print(f"CIA: {args.cia}")
        print(f"  Title ID:     {info['title_id']}")
        print(f"  Certs size:   {info['cert_size']} bytes")
        print(f"  Ticket size:  {info['ticket_size']} bytes")
        print(f"  TMD size:     {info['tmd_size']} bytes")
        print(f"  Meta size:    {info['meta_size']} bytes")
        print(f"  Contents:     {info['num_contents']}")
        for c in info["contents"]:
            print(f"    - Content {c['id']} (index {c['index']}): {c['size']} bytes, SHA: {c['sha256'][:16]}...")
        print(f"  Valid:        {info['valid']}")
        return 0 if info["valid"] else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
