#!/usr/bin/env python3
"""Turn a ``mod/`` workspace into something a real Nintendo 3DS/2DS can run.

Targets
-------
``luma``
    ``out/luma/titles/<TitleID>/romfs/`` containing **only the changed files**
    (Luma3DS LayeredFS), plus ``code.ips`` (or a full ``code.bin``) when the
    native executable changed.  This is the recommended path for CFW consoles:
    copy the ``luma`` folder to the SD card root, enable *game patching*.

``3ds``
    A complete, rebuilt 4 GiB ``.3ds`` image with the patched RomFS and the
    recompressed native code.  The NCCH/RomFS/ExeFS hashes, content size,
    NCSD partition table and card-info filled size are updated by
    ``tools/repack_rom.py``.  The output is validated by re-parsing it.

``cia``
    An installable CIA built from the rebuilt ``.3ds`` (``tools/ctr_cia.py``,
    ported from the DQXI translation project).  Contents are stored
    unencrypted and the signatures are blank ("fakesigned"), so installing
    needs a CFW console with signature patches (Luma3DS) and an installer
    such as FBI.  The file re-parses and every content hash matches; see
    ``docs/EXPORT.md`` for the install steps and the limits.

Mod workspace (``mod/``)
------------------------
::

    mod/
      mod.json                 {"name": ..., "version": ..., "author": ...}
      romfs/<path>             replacement files, paths exactly as in RomFS
                               (leading slash omitted), e.g.
                               mod/romfs/level3d/b001_101a.pack
      code/code.bin            optional full, uncompressed replacement for the
                               native executable (must stay 7,090,176 bytes;
                               the ExHeader code-set sizes are not rewritten)

The RomFS holds PACK archives, not loose tables or models, so every asset edit
becomes the *pack that contains it*: a changed item table is
``mod/romfs/syscmn.pack``, not ``mod/romfs/item.bxon``.  ``--stage-table`` and
``--stage-pack`` do that repack for you (see below).

Run it with no arguments to export ``mod/`` to ``out/``.  Use ``--no-rom`` to
stop after the validated ``out/3ds/romfs.bin`` (useful for quick checks).

Every output is re-parsed and checked:
  * RomFS IVFC Level 1/2 + master SHA-256 hashes;
  * NCCH ExeFS superblock hash and every ExeFS index hash;
  * NCCH RomFS superblock hash and content size;
  * ExHeader, logo and plain-region hashes where the header stores one;
  * NCSD partition table bounds and the 4 GiB image size;
  * an empty mod must reproduce the retail ``.3ds`` byte-for-byte;
  * CIA header, certificate chain, ticket/TMD and every content SHA-256.

Usage
-----
    python tools/export_mod.py --target luma
    python tools/export_mod.py --target 3ds
    python tools/export_mod.py --target cia
    python tools/export_mod.py --target all --mod mod --out out
    python tools/export_mod.py --target 3ds --no-rom
    python tools/export_mod.py --stage-table syscmn/item.json --replacement build/item.bxon
    python tools/export_mod.py --stage-pack syscmn.pack --member item.bxon --replacement build/item.bxon
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import blz, romfs_hash  # noqa: E402
from tools import romfs_build  # noqa: E402
from tools.patch_asset import write_romfs_file  # noqa: E402

ORIGINAL_DIR = PROJECT_ROOT / "original"
ORIGINAL_ROMFS = ORIGINAL_DIR / "romfs.bin"
ORIGINAL_ROM = ORIGINAL_DIR / "DQXI.3ds"
NCCH0_HEADER = ORIGINAL_DIR / "ncch0_header.bin"
EXHEADER = ORIGINAL_DIR / "exheader.bin"
RETAIL_CODE = ORIGINAL_DIR / "exefs" / "code.decompressed.bin"
DEFAULT_MOD_DIR = PROJECT_ROOT / "mod"
DEFAULT_OUT_DIR = PROJECT_ROOT / "out"

RETAIL_ROM_SHA256 = "0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74"
RETAIL_ROMFS_SHA256 = "8c108be136c23c57749fba24443038b71a30ffddf66f028d05f9252d1c4822bc"
RETAIL_CODE_SHA256 = "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8"
RETAIL_CODE_SIZE = 7_090_176             # uncompressed .text+.rodata+.data
TARGET_ROM_SIZE = 4_294_967_296
MEDIA_UNIT = 0x200
NCCH0_OFFSET = 0x4000
CHUNK = 16 * 1024 * 1024

CHANGE_RUN_GAP = 8          # merge IPS records separated by fewer unchanged bytes
IPS_MAX_RECORD = 0xFFFF


class ExportError(RuntimeError):
    """A mod/fixture problem that the user can fix."""


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk: int = CHUNK) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def sha256_region(f, offset: int, size: int) -> str:
    """SHA-256 of ``size`` bytes at absolute ``offset`` of an open file."""
    h = hashlib.sha256()
    f.seek(offset)
    left = size
    while left > 0:
        block = f.read(min(CHUNK, left))
        if not block:
            raise ExportError(f"unexpected end of file at 0x{offset + size - left:X}")
        h.update(block)
        left -= len(block)
    return h.hexdigest()


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def u64(data: bytes, off: int) -> int:
    return struct.unpack_from("<Q", data, off)[0]


def posix(path: Path) -> str:
    return path.as_posix()


# --------------------------------------------------------------------------- #
# mod workspace
# --------------------------------------------------------------------------- #
def load_mod(mod_dir: Path) -> dict:
    """Read ``mod/mod.json`` and enumerate the RomFS replacements / code file.

    The workspace may be empty (or absent): that is the "empty mod" used to
    prove that exporting changes nothing.
    """
    mod_dir = Path(mod_dir)
    meta = {"name": "", "version": "", "author": "", "description": ""}
    meta_file = mod_dir / "mod.json"
    if meta_file.is_file():
        try:
            raw = json.loads(meta_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ExportError(f"cannot read {meta_file}: {exc}") from exc
        if not isinstance(raw, dict):
            raise ExportError("mod/mod.json must contain a JSON object")
        for key in meta:
            value = raw.get(key, "")
            if value is None:
                value = ""
            if isinstance(value, (int, float)):
                value = str(value)
            if not isinstance(value, str):
                raise ExportError(f"mod.json field {key!r} must be a string")
            meta[key] = value.strip()
        unknown = sorted(set(raw) - set(meta) - {"title_id"})
        if unknown:
            print(f"  note: ignoring unknown mod.json keys: {', '.join(unknown)}")
    elif mod_dir.is_dir():
        print("  note: mod/mod.json is missing; export still works, metadata is empty")

    romfs_root = mod_dir / "romfs"
    mod_files: list[dict] = []
    if romfs_root.is_dir():
        for src in sorted(romfs_root.rglob("*")):
            if src.is_file():
                rel = src.relative_to(romfs_root)
                mod_files.append({"path": "/" + posix(rel), "source": src, "rel": rel})

    code_file = mod_dir / "code" / "code.bin"
    code = {"path": code_file, "changed": False, "size": 0, "sha256": None}
    if code_file.is_file():
        size = code_file.stat().st_size
        if size != RETAIL_CODE_SIZE:
            raise ExportError(
                f"mod/code/code.bin is {size:,} bytes; a native replacement must keep the "
                f"retail decompressed size ({RETAIL_CODE_SIZE:,}) because the ExHeader "
                "code-set sizes are not rewritten.  Rebuild code.bin from asm/ or "
                "src/ without adding/removing sections."
            )
        digest = sha256_file(code_file)
        code.update(changed=digest != RETAIL_CODE_SHA256, size=size, sha256=digest)

    return {"dir": mod_dir, **meta, "romfs_files": mod_files, "code": code}


# --------------------------------------------------------------------------- #
# staging edits into mod/romfs
# --------------------------------------------------------------------------- #
# Tables and models do not live in the RomFS on their own: they are members of
# a PACK.  So a "table edit" becomes a *pack replacement* in mod/romfs/<pack>.
# These helpers do that one step so the editor tools only have to drop the
# rebuilt member somewhere and call us.
def stage_member(pack_path: str, member: str, replacement: Path, mod_dir: Path,
                 work_dir: Path | None = None) -> dict:
    """Rebuild ``<pack_path>`` with ``member`` replaced and store it in ``mod/romfs``."""
    from tools.patch_asset import rebuild_pack          # local: keeps --help fast

    pack_rel = pack_path.replace("\\", "/").lstrip("/")
    original_pack = PROJECT_ROOT / "game_data" / "romfs" / pack_rel
    if not original_pack.is_file():
        raise ExportError(f"no retail pack at game_data/romfs/{pack_rel}")
    replacement = Path(replacement)
    if not replacement.is_file():
        raise ExportError(f"replacement file not found: {replacement}")

    built_out = Path(work_dir or PROJECT_ROOT / "build" / "staged") / pack_rel
    target = Path(mod_dir) / "romfs" / pack_rel
    # Build on the mod's copy when it already has this pack, so a second member edit in the
    # same pack (e.g. item.bxon and item_kana_order.bxon in syscmn.pack) keeps the first one.
    base = target if target.is_file() else original_pack
    built = rebuild_pack(base, member, replacement, built_out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(built)
    return {
        "pack": "/" + pack_rel,
        "member": member,
        "replacement": str(replacement),
        "mod_file": str(target),
        "size": len(built),
        "original_size": original_pack.stat().st_size,
        "sha256": sha256_bytes(built),
    }


def schema_pack_for(table: str) -> tuple[str, str]:
    """RomFS pack and member name that hold a table, from tools/table_schemas.json.

    ``table`` is the schema key used by the table editor, e.g. ``syscmn/item.json``.
    """
    schemas_file = PROJECT_ROOT / "tools" / "table_schemas.json"
    try:
        tables = json.loads(schemas_file.read_text(encoding="utf-8"))["tables"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        raise ExportError(f"cannot read {schemas_file}: {exc}") from exc
    entry = tables.get(table.replace("\\", "/").lstrip("/"))
    if entry is None:
        known = ", ".join(sorted(tables)[:6])
        raise ExportError(f"{table} is not in tools/table_schemas.json (known: {known}, ...)")
    pack = entry.get("pack")
    if not pack:
        raise ExportError(f"{table} has no 'pack' entry in tools/table_schemas.json")
    member = Path(table).name            # syscmn/item.json -> item.bxon
    member = member[:-5] + ".bxon" if member.endswith(".json") else member
    return pack, member


def stage_table(table: str, replacement: Path, mod_dir: Path, work_dir: Path | None = None) -> dict:
    """Put an edited table (a rebuilt .bxon) into the mod workspace as its pack."""
    pack, member = schema_pack_for(table)
    info = stage_member(pack, member, replacement, mod_dir, work_dir)
    info["table"] = table
    return info


# --------------------------------------------------------------------------- #
# RomFS reader (level-3 metadata tables)
# --------------------------------------------------------------------------- #
# Level-3 header ("<10I"): size, dir-hash off/len, dir-meta off/len,
# file-hash off/len, file-meta off/len, file-data off.  Note the order: the
# *directory* tables come first, then the file tables.  Dragon Quest XI stores
# entry names as UTF-16LE (most 3DS games use UTF-8), so names must not be
# decoded as ASCII.
DIR_ENTRY_FIXED = 0x14        # parent, sibling, first-subdir, first-file, unused
FILE_ENTRY_FIXED = 0x1C       # parent, sibling, data offset, data size, unused
END_OF_CHAIN = 0xFFFFFFFF


class RomFsIndex:
    """Read the RomFS file table and file bytes from a raw image.

    ``base`` is the absolute offset of the IVFC header inside the opened file
    (0 for ``romfs.bin``, the NCCH RomFS offset plus 0x4000 inside a ``.3ds``).
    Offsets inside the RomFS metadata are relative to the Level-3 start.
    """

    def __init__(self, path: Path, base: int = 0):
        self.path = Path(path)
        self.base = base
        with open(self.path, "rb") as f:
            f.seek(base)
            head = f.read(romfs_hash.MASTER_OFF)
            self.info = romfs_hash.parse_header(head)
            self.level3 = self.info["data_start"]
            f.seek(base + self.level3)
            hdr = struct.unpack("<10I", f.read(40))
        (self.header_size, _dir_hash_off, _dir_hash_len,
         self.dir_meta_off, self.dir_meta_len,
         _file_hash_off, _file_hash_len,
         self.file_meta_off, self.file_meta_len,
         self.file_data_off) = hdr
        if self.header_size != 0x28:
            raise ExportError(f"{self.path}: unexpected RomFS header size {self.header_size:#x}")
        self.files: dict[str, dict] = {}
        with open(self.path, "rb") as f:
            f.seek(base + self.level3 + self.dir_meta_off)
            dirs = f.read(self.dir_meta_len)
            f.seek(base + self.level3 + self.file_meta_off)
            files = f.read(self.file_meta_len)
        if not dirs or not files:
            raise ExportError(f"{self.path}: empty RomFS metadata tables")
        self._walk(dirs, files)

    def _walk(self, dirs: bytes, files: bytes) -> None:
        def name(table: bytes, off: int, fixed: int) -> str:
            n = u32(table, off + fixed)
            raw = table[off + fixed + 4:off + fixed + 4 + n]
            try:
                return raw.decode("utf-16-le")
            except UnicodeDecodeError as exc:
                raise ExportError(f"{self.path}: bad RomFS entry name at 0x{off:X}: {exc}") from exc

        def children(d_off: int, prefix: str) -> None:
            # Directory entry: parent, sibling, first-subdir, first-file, unused,
            # then name length and the UTF-16 name.
            f_off = u32(dirs, d_off + 0x0C)
            while f_off != END_OF_CHAIN:
                entry_name = name(files, f_off, FILE_ENTRY_FIXED)
                path = f"{prefix}/{entry_name}"
                self.files[path] = {
                    "offset": u64(files, f_off + 0x08),
                    "size": u64(files, f_off + 0x10),
                    "entry_offset": self.file_meta_off + f_off,
                    "parent": d_off,
                }
                f_off = u32(files, f_off + 0x04)
            d = u32(dirs, d_off + 0x08)
            while d != END_OF_CHAIN:
                children(d, f"{prefix}/{name(dirs, d, DIR_ENTRY_FIXED)}")
                d = u32(dirs, d + 0x04)

        children(0, "")
        if not self.files:
            raise ExportError(f"{self.path}: RomFS file table is empty")

    @property
    def data_start(self) -> int:
        """Absolute offset of the first file's bytes."""
        return self.base + self.level3 + self.file_data_off

    def read(self, path: str) -> bytes:
        entry = self.files[path]
        with open(self.path, "rb") as f:
            f.seek(self.data_start + entry["offset"])
            data = f.read(entry["size"])
        if len(data) != entry["size"]:
            raise ExportError(f"short read for RomFS file {path}")
        return data


# --------------------------------------------------------------------------- #
# Native-code diff / IPS
# --------------------------------------------------------------------------- #
def make_ips(original: bytes, patched: bytes) -> bytes:
    """A Luma3DS ``code.ips`` diff between two equal-length code images."""
    if len(original) != len(patched):
        raise ExportError("IPS patches need equal-length code images")
    out = bytearray(b"PATCH")
    n = len(original)
    i = 0
    records = 0
    while i < n:
        if original[i] == patched[i]:
            i += 1
            continue
        start = i
        last = i
        j = i + 1
        while j < n and j - start < IPS_MAX_RECORD:
            if original[j] != patched[j]:
                last = j
            elif j - last > CHANGE_RUN_GAP:
                break
            j += 1
        end = last + 1
        length = end - start
        out += start.to_bytes(3, "big")
        out += length.to_bytes(2, "big")
        out += patched[start:end]
        records += 1
        i = end
    if not records:
        raise ExportError("no code differences; refusing to write an empty IPS")
    out += b"EOF"
    return bytes(out)


def apply_ips(original: bytes, ips: bytes) -> bytes:
    """Apply an IPS patch; used to prove the exported patch reproduces the edit."""
    if ips[:5] != b"PATCH":
        raise ExportError("not an IPS patch (missing PATCH magic)")
    data = bytearray(original)
    pos = 5
    while pos < len(ips):
        if ips[pos:pos + 3] == b"EOF":
            return bytes(data)
        if pos + 5 > len(ips):
            raise ExportError("truncated IPS record header")
        offset = int.from_bytes(ips[pos:pos + 3], "big")
        size = int.from_bytes(ips[pos + 3:pos + 5], "big")
        pos += 5
        if size == 0:
            raise ExportError("RLE IPS records are not used by this exporter")
        if offset + size > len(data):
            raise ExportError("IPS record runs past the end of code.bin")
        data[offset:offset + size] = ips[pos:pos + size]
        pos += size
    raise ExportError("IPS patch has no EOF marker")


# --------------------------------------------------------------------------- #
# validation helpers
# --------------------------------------------------------------------------- #
def _verify_ivfc(f, base: int, label: str) -> dict:
    """Verify the three IVFC hash levels of the RomFS image at ``base``."""
    f.seek(base)
    info = romfs_hash.parse_header(f.read(romfs_hash.MASTER_OFF))
    block = info["block"]
    l2_blocks, l1_blocks, master_blocks = romfs_hash._counts(info)
    bad_l2 = _compare_hash_blocks(
        f, base + info["data_start"], l2_blocks, block,
        base + info["level2_start"], f"{label} RomFS Level-2")
    bad_l1 = _compare_hash_blocks(
        f, base + info["level2_start"], l1_blocks, block,
        base + info["level1_start"], f"{label} RomFS Level-1")
    bad_master = _compare_hash_blocks(
        f, base + info["level1_start"], master_blocks, block,
        base + romfs_hash.MASTER_OFF, f"{label} RomFS master")
    f.seek(0, os.SEEK_END)
    size_ok = f.tell() >= base + romfs_hash.total_size(info)
    return {
        "data_blocks": l2_blocks,
        "level1_blocks": l1_blocks,
        "master_blocks": master_blocks,
        "bad_level2": bad_l2,
        "bad_level1": bad_l1,
        "bad_master": bad_master,
        "size_ok": size_ok,
        "ok": (bad_l2 == bad_l1 == bad_master == 0) and size_ok,
    }


def _compare_hash_blocks(f, data_start: int, count: int, block: int,
                         table_start: int, label: str) -> int:
    f.seek(table_start)
    stored = f.read(count * 32)
    if len(stored) != count * 32:
        raise ExportError(f"{label}: truncated hash table")
    f.seek(data_start)
    bad = 0
    per_read = max(1, CHUNK // block)
    index = 0
    while index < count:
        take = min(count - index, per_read)
        buf = f.read(take * block)
        if len(buf) < take * block:
            buf += bytes(take * block - len(buf))
        for k in range(take):
            digest = hashlib.sha256(buf[k * block:(k + 1) * block]).digest()
            if digest != stored[(index + k) * 32:(index + k + 1) * 32]:
                bad += 1
        index += take
    return bad


def parse_ncsd(f) -> dict:
    f.seek(0)
    head = f.read(0x200)
    # The NCSD header is a 0x100-byte RSA signature followed by 0x100 bytes of
    # fields, so the magic is at 0x100 and the partition table starts at 0x120.
    if head[0x100:0x104] != b"NCSD":
        raise ExportError("output is not an NCSD (.3ds) image")
    partitions = []
    for i in range(8):
        off_mu, size_mu = struct.unpack_from("<II", head, 0x120 + i * 8)
        if size_mu:
            partitions.append({
                "index": i,
                "offset": off_mu * MEDIA_UNIT,
                "size": size_mu * MEDIA_UNIT,
            })
    return {"partitions": partitions, "media_size": u32(head, 0x104)}


def parse_ncch(f, offset: int) -> dict:
    f.seek(offset)
    head = f.read(0x200)
    # Signature occupies the first 0x100 bytes, then the NCCH header fields.
    if head[0x100:0x104] != b"NCCH":
        raise ExportError(f"no NCCH magic at 0x{offset + 0x100:X}")
    return {
        "offset": offset,
        "header": head,
        "content_size": u32(head, 0x104) * MEDIA_UNIT,
        "partition_id": u64(head, 0x108),
        "program_id": u64(head, 0x118),
        "logo_hash": head[0x130:0x150],
        "exheader_hash": head[0x160:0x180],
        "exheader_size": u32(head, 0x180),
        "plain_offset": u32(head, 0x190) * MEDIA_UNIT,
        "plain_size": u32(head, 0x194) * MEDIA_UNIT,
        "logo_offset": u32(head, 0x198) * MEDIA_UNIT,
        "logo_size": u32(head, 0x19C) * MEDIA_UNIT,
        "exefs_offset": u32(head, 0x1A0) * MEDIA_UNIT,
        "exefs_size": u32(head, 0x1A4) * MEDIA_UNIT,
        "exefs_hash_size": u32(head, 0x1A8) * MEDIA_UNIT,
        "romfs_offset": u32(head, 0x1B0) * MEDIA_UNIT,
        "romfs_size": u32(head, 0x1B4) * MEDIA_UNIT,
        "romfs_hash_size": u32(head, 0x1B8) * MEDIA_UNIT,
        "exefs_superblock": head[0x1C0:0x1E0],
        "romfs_superblock": head[0x1E0:0x200],
    }


def validate_exefs(f, ncch: dict) -> dict:
    base = ncch["offset"] + ncch["exefs_offset"]
    f.seek(base)
    head = f.read(0x200)
    if len(head) != 0x200:
        raise ExportError("truncated ExeFS header")
    entries = []
    for i in range(10):
        raw_name = head[i * 16:(i + 1) * 16]
        name = raw_name[:8].split(b"\0", 1)[0].decode("ascii", "replace")
        off, size = struct.unpack_from("<II", raw_name, 8)
        if not name or size == 0:
            continue
        # ExeFS entry offsets are relative to the end of the 0x200-byte header.
        if 0x200 + off + size > ncch["exefs_size"]:
            raise ExportError(f"ExeFS entry {name} runs past the ExeFS region")
        f.seek(base + 0x200 + off)
        data = f.read(size)
        if len(data) != size:
            raise ExportError(f"truncated ExeFS entry {name}")
        stored = head[0x1E0 - i * 0x20:0x200 - i * 0x20]
        entries.append({
            "name": name,
            "offset": off,
            "size": size,
            "sha256": sha256_bytes(data),
            "hash_ok": hashlib.sha256(data).digest() == stored,
        })
    superblock_hash = hashlib.sha256(head[:ncch["exefs_hash_size"]]).digest()
    return {
        "entries": entries,
        "all_hashes_ok": all(e["hash_ok"] for e in entries),
        "superblock_ok": superblock_hash == ncch["exefs_superblock"],
        "header_sha256": sha256_bytes(head),
    }


def validate_3ds(path: Path, expected_files: dict[str, bytes] | None = None,
                 code_sha256: str | None = None, expect_retail: bool = False,
                 romfs_copy: Path | None = None) -> dict:
    """Re-parse a rebuilt image and check every hash the console checks."""
    path = Path(path)
    size = path.stat().st_size
    if size != TARGET_ROM_SIZE:
        raise ExportError(f"{path.name}: size {size:,} != {TARGET_ROM_SIZE:,}")
    result: dict = {"path": str(path), "size": size, "sha256": sha256_file(path)}
    if expect_retail and result["sha256"] != RETAIL_ROM_SHA256:
        raise ExportError(
            f"{path.name}: an empty mod must reproduce the retail image; "
            f"got {result['sha256']}, expected {RETAIL_ROM_SHA256}")
    if not expect_retail and result["sha256"] == RETAIL_ROM_SHA256:
        raise ExportError(f"{path.name}: image is byte-identical to retail but the mod has changes")

    with open(path, "rb") as f:
        ncsd = parse_ncsd(f)
        result["partitions"] = ncsd["partitions"]
        if not ncsd["partitions"] or ncsd["partitions"][0]["index"] != 0:
            raise ExportError("NCSD partition 0 is missing")
        used = 0
        for part in ncsd["partitions"]:
            if part["offset"] < used:
                raise ExportError("NCSD partitions overlap")
            if part["offset"] + part["size"] > size:
                raise ExportError("NCSD partition runs past the end of the image")
            used = part["offset"] + part["size"]
        result["used_bytes"] = used
        result["trailing_padding"] = size - used

        ncch = parse_ncch(f, NCCH0_OFFSET)
        result["title_id"] = f"{ncch['program_id']:016X}"
        result["content_size"] = ncch["content_size"]
        if ncch["offset"] + ncch["content_size"] > size:
            raise ExportError("NCCH content size runs past the image")
        if ncch["content_size"] != ncsd["partitions"][0]["size"]:
            raise ExportError("NCCH content size disagrees with NCSD partition 0")

        # ExHeader (first 0x400 bytes) and logo hashes.
        f.seek(ncch["offset"] + 0x200)
        exheader = f.read(ncch["exheader_size"])
        result["exheader_hash_ok"] = hashlib.sha256(exheader).digest() == ncch["exheader_hash"]
        if not result["exheader_hash_ok"]:
            raise ExportError("NCCH ExHeader SHA-256 mismatch")
        f.seek(ncch["offset"] + ncch["logo_offset"])
        logo = f.read(ncch["logo_size"])
        result["logo_hash_ok"] = hashlib.sha256(logo).digest() == ncch["logo_hash"]
        if not result["logo_hash_ok"]:
            raise ExportError("NCCH logo SHA-256 mismatch")

        exefs = validate_exefs(f, ncch)
        result["exefs"] = exefs
        if not exefs["all_hashes_ok"]:
            raise ExportError("ExeFS entry SHA-256 mismatch")
        if not exefs["superblock_ok"]:
            raise ExportError("NCCH ExeFS superblock SHA-256 mismatch")

        # Native code round-trip (the ExeFS .code entry is BLZ compressed).
        code_entry = next((e for e in exefs["entries"] if e["name"] == ".code"), None)
        if code_entry is None:
            raise ExportError("ExeFS has no .code entry")
        f.seek(ncch["offset"] + ncch["exefs_offset"] + 0x200 + code_entry["offset"])
        packed_code = f.read(code_entry["size"])
        code_img = blz.decompress(packed_code)
        result["code_uncompressed_size"] = len(code_img)
        result["code_uncompressed_sha256"] = sha256_bytes(code_img)
        if len(code_img) != RETAIL_CODE_SIZE:
            raise ExportError("rebuilt code.bin changed the uncompressed code size")
        if code_sha256 is not None and result["code_uncompressed_sha256"] != code_sha256:
            raise ExportError("the rebuilt image does not contain the requested code.bin")

        # RomFS superblock (IVFC header + master hashes) and full IVFC tree.
        romfs_base = ncch["offset"] + ncch["romfs_offset"]
        if ncch["romfs_hash_size"] <= 0:
            raise ExportError("NCCH RomFS hash-region size is zero")
        sb = sha256_region(f, romfs_base, ncch["romfs_hash_size"])
        result["romfs_superblock_ok"] = bytes.fromhex(sb) == ncch["romfs_superblock"]
        if not result["romfs_superblock_ok"]:
            raise ExportError("NCCH RomFS superblock SHA-256 mismatch")
        result["ivfc"] = _verify_ivfc(f, romfs_base, path.name)
        if not result["ivfc"]["ok"]:
            raise ExportError(f"RomFS IVFC hashes are invalid: {result['ivfc']}")

        # The bytes placed in the image are exactly the validated romfs.bin.
        if romfs_copy is not None:
            romfs_copy_sha = sha256_file(romfs_copy)
            image_romfs_sha = sha256_region(f, romfs_base, ncch["romfs_size"])
            result["romfs_copy"] = str(romfs_copy)
            result["romfs_sha256"] = image_romfs_sha
            if image_romfs_sha != romfs_copy_sha:
                raise ExportError("image RomFS differs from the validated romfs.bin")

        # Modified files must be present with the exact expected bytes.
        if expected_files:
            index = RomFsIndex(path, romfs_base)
            found = []
            for romfs_path, data in sorted(expected_files.items()):
                if romfs_path not in index.files:
                    raise ExportError(f"rebuilt RomFS has no {romfs_path}")
                actual = index.read(romfs_path)
                if actual != data:
                    raise ExportError(f"rebuilt RomFS content mismatch for {romfs_path}")
                found.append({"path": romfs_path, "size": len(actual),
                              "sha256": sha256_bytes(actual)})
            result["mod_files"] = found
        result["ok"] = True
    return result


# --------------------------------------------------------------------------- #
# changes
# --------------------------------------------------------------------------- #
def collect_changes(mod: dict, index: RomFsIndex) -> list[dict]:
    changes = []
    for item in mod["romfs_files"]:
        path = item["path"]
        data = item["source"].read_bytes()
        entry = index.files.get(path)
        if entry is None:
            changes.append({
                "path": path,
                "rel": item["rel"],
                "size": len(data),
                "add": True,          # grows the Level-3 metadata tables
                "offset": None,
                "original_size": 0,
                "sha256": sha256_bytes(data),
                "data": data,
            })
            print(f"  new file: {path} (added to the RomFS tree)")
            continue
        with open(index.path, "rb") as f:
            f.seek(index.data_start + entry["offset"])
            original = f.read(entry["size"])
        if len(original) != entry["size"]:
            raise ExportError(f"short read for retail RomFS file {path}")
        if original == data:
            print(f"  unchanged: {path} (not copied)")
            continue
        changes.append({
            "path": path,
            "rel": item["rel"],
            "size": len(data),
            "original_size": entry["size"],
            "offset": entry["offset"],
            "sha256": sha256_bytes(data),
            "data": data,
        })
    return changes


def build_patched_romfs(changes: list[dict], dest: Path) -> dict:
    """Copy the retail RomFS, write the changed files and rebuild all IVFC hashes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_sha = sha256_file(ORIGINAL_ROMFS)
    if src_sha != RETAIL_ROMFS_SHA256:
        raise ExportError(f"original/romfs.bin hash {src_sha} is not the retail baseline")
    print(f"  copying original/romfs.bin ({ORIGINAL_ROMFS.stat().st_size / 1e9:.2f} GB) ...")
    shutil.copyfile(ORIGINAL_ROMFS, dest)

    placements = []
    for change in changes:
        if change.get("add"):
            continue
        placed = write_romfs_file(dest, change["offset"], change["original_size"], change["data"])
        placements.append({"path": change["path"], **placed})
        note = " (appended at the end of the RomFS)" if placed["relocated"] else ""
        print(f"  wrote {change['path']}: {change['original_size']:,} -> {len(change['data']):,} bytes{note}")

    # romfs_build.rebuild_metadata takes (romfs path, data) pairs; keep the
    # change dicts for the report/placement list below.
    additions = [(c["path"], c["data"]) for c in changes if c.get("add")]
    if additions:
        if any(not c.get("add") for c in changes):
            # A grown replacement moved the Level-3 end and zeroed the hash
            # levels, and the add-file rebuild re-checks the hash model against
            # the image it is given.  Put the tree's own hashes back first.
            print("  rebuilding RomFS IVFC hash tree for the grown files ...")
            romfs_hash.rebuild(dest)
        print(f"  adding {len(additions)} new file(s): rebuilding the Level-3 "
              "metadata/hash tables ...")
        try:
            rep = romfs_build.rebuild_metadata(dest, additions)
        except RuntimeError as exc:
            raise ExportError(f"RomFS add-file rebuild failed: {exc}") from exc
        placements += [{"path": p["path"], "offset": p["offset"],
                        "size": p["size"], "relocated": True}
                       for p in rep["placements"]]
    else:
        print("  rebuilding RomFS IVFC hash tree ...")
        report = romfs_hash.rebuild(dest)
        check = romfs_hash.verify(dest)
        if not check["ok"]:
            raise ExportError(f"patched RomFS failed verification: {check}")
        print(f"  IVFC OK ({report['data_blocks']:,} data blocks)")
    return {"placements": placements, "ivfc": rep["ivfc"] if additions else check}


def inspect_ips(ips: bytes, code: dict) -> dict:
    original = RETAIL_CODE.read_bytes()
    if len(original) != RETAIL_CODE_SIZE:
        raise ExportError("original/exefs/code.decompressed.bin is missing or has the wrong size")
    with open(code["path"], "rb") as f:
        patched_bytes = f.read()
    rebuilt = apply_ips(original, ips)
    if rebuilt != patched_bytes:
        raise ExportError("the generated code.ips does not reproduce mod/code/code.bin")
    diffs = sum(a != b for a, b in zip(original, patched_bytes, strict=True))
    return {"bytes": len(ips), "changed_bytes": diffs}


# --------------------------------------------------------------------------- #
# targets
# --------------------------------------------------------------------------- #
def build_luma(mod: dict, changes: list[dict], code: dict, out_dir: Path,
               title_id: str, code_mode: str) -> dict:
    root = out_dir / "luma"
    adds = [c["path"] for c in changes if c.get("add")]
    if adds:
        raise ExportError(
            "Luma3DS LayeredFS can only replace RomFS paths that already exist; "
            "it never mounts added ones.  New file(s) not supported on this "
            "target: " + ", ".join(adds[:8]) +
            ".  Export with --target 3ds or cia instead to add files.")
    if root.exists():
        shutil.rmtree(root)
    title_root = root / "titles" / title_id
    romfs_root = title_root / "romfs"
    romfs_root.mkdir(parents=True, exist_ok=True)

    written = []
    for change in changes:
        target = romfs_root / change["rel"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(change["data"])
        written.append({"path": change["path"], "file": str(target),
                        "size": len(change["data"]), "sha256": change["sha256"]})

    native = {"changed": code["changed"], "format": None, "file": None, "bytes": 0}
    if code["changed"]:
        if code_mode == "bin":
            target = title_root / "code.bin"
            shutil.copyfile(code["path"], target)
            native = {"changed": True, "format": "bin", "file": str(target),
                      "bytes": target.stat().st_size, "sha256": code["sha256"]}
        else:
            original = RETAIL_CODE.read_bytes()
            patched = Path(code["path"]).read_bytes()
            ips = make_ips(original, patched)
            target = title_root / "code.ips"
            target.write_bytes(ips)
            info = inspect_ips(ips, code)
            native = {"changed": True, "format": "ips", "file": str(target),
                      "bytes": len(ips), "sha256": sha256_bytes(ips),
                      "changed_bytes": info["changed_bytes"]}

    readme = root / "README.txt"
    name = mod["name"] or "unnamed mod"
    version = mod["version"] or "?"
    author = mod["author"] or "?"
    readme.write_text(
        f"{name} {version} by {author}\n"
        f"Exported for Luma3DS LayeredFS, title ID {title_id}.\n\n"
        "Installation:\n"
        "1. Copy the whole 'luma' folder to the root of your SD card and merge it.\n"
        f"   Result: /luma/titles/{title_id}/romfs/ and, if present, code.ips.\n"
        "2. Power on while holding SELECT, enable 'Enable game patching', press START.\n"
        "3. Launch Dragon Quest XI.\n\n"
        "code.ips/code.bin replace the *decompressed* native executable; never keep\n"
        "both files in the title folder.  LayeredFS cannot add new RomFS paths;\n"
        "only existing files are replaced here.  To add files use the full-image\n"
        "targets (out/3ds/DQXI_modded.3ds or the CIA), which rebuild the RomFS.\n",
        encoding="utf-8")

    # Re-parse the folder: every expected file must be there and nothing else.
    found = []
    for item in written:
        back = Path(item["file"]).read_bytes()
        if sha256_bytes(back) != item["sha256"]:
            raise ExportError(f"Luma output {item['file']} does not round-trip")
        found.append(item["path"])
    expected_set = set(found)
    actual_set = {"/" + posix(p.relative_to(romfs_root))
                  for p in romfs_root.rglob("*") if p.is_file()}
    if expected_set != actual_set:
        raise ExportError("Luma output contains files that are not in the change list")
    if (title_root / "code.bin").exists() and (title_root / "code.ips").exists():
        raise ExportError("Luma output has both code.bin and code.ips")
    if native["changed"] and native["format"] == "ips":
        inspect_ips((title_root / "code.ips").read_bytes(), code)

    return {
        "dir": str(root),
        "title_dir": str(title_root),
        "files": written,
        "code": native,
        "valid": True,
    }


def build_3ds(mod: dict, changes: list[dict], code: dict, out_dir: Path,
              title_id: str, no_rom: bool) -> dict:
    root = out_dir / "3ds"
    root.mkdir(parents=True, exist_ok=True)
    romfs_out = root / "romfs.bin"

    if changes:
        print("Building patched RomFS ...")
        build = build_patched_romfs(changes, romfs_out)
    else:
        print("No RomFS changes: copying the retail RomFS unchanged ...")
        shutil.copyfile(ORIGINAL_ROMFS, romfs_out)
        if sha256_file(romfs_out) != RETAIL_ROMFS_SHA256:
            raise ExportError("retail RomFS copy does not hash to the baseline")
        build = {"placements": [], "ivfc": None}

    result = {
        "romfs": str(romfs_out),
        "romfs_sha256": sha256_file(romfs_out),
        "placements": build["placements"],
        "rom": None,
        "retail_identical": not changes and not code["changed"],
    }
    if no_rom:
        if changes:
            index = RomFsIndex(romfs_out)
            for change in changes:
                if index.read(change["path"]) != change["data"]:
                    raise ExportError(f"patched romfs.bin does not contain {change['path']}")
        result["valid"] = True
        result["note"] = "--no-rom: only the validated out/3ds/romfs.bin was produced"
        return result

    out_rom = root / "DQXI_modded.3ds"
    cmd = [sys.executable, str(PROJECT_ROOT / "tools" / "repack_rom.py"),
           "--in", str(ORIGINAL_DIR), "--romfs", str(romfs_out), "--out", str(out_rom)]
    if changes:
        cmd.append("--modified")
    if code["changed"]:
        cmd += ["--code", str(code["path"])]
    print("Repacking cartridge ...")
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if proc.returncode != 0:
        raise ExportError("tools/repack_rom.py failed; see its output above")

    expected = {c["path"]: c["data"] for c in changes}
    code_sha = code["sha256"] if code["changed"] else RETAIL_CODE_SHA256
    validation = validate_3ds(
        out_rom, expected_files=expected, code_sha256=code_sha,
        expect_retail=result["retail_identical"], romfs_copy=romfs_out)
    result.update({
        "rom": str(out_rom),
        "rom_sha256": validation["sha256"],
        "rom_bytes": validation["size"],
        "validation": validation,
        "valid": True,
    })
    return result


CIA_README = """\
{name} {version} by {author}
Installable CIA for Dragon Quest XI (3DS), title ID {title_id}.

What this file is
-----------------
A CTR Importable Archive built from the same rebuilt .3ds image as the other
targets.  Contents are stored unencrypted and the ticket/TMD signatures are
blank ("fakesigned"), because Nintendo's private key is not available.  That is
normal for homebrew CIAs and is why installation needs custom firmware with
signature patches.

Installing
----------
1. A 3DS/2DS running Luma3DS (or another CFW that patches signature checks).
   The console must be able to run "unsigned" titles; plain OFW will refuse.
2. Copy DQXI_modded.cia to the SD card (any folder works).
3. Open FBI (or another CIA installer) -> "Titles" -> "Install CIA" and pick
   the file.  FBI verifies the TMD/ticket and writes the two contents.
4. The title appears on the home menu as Dragon Quest XI.  It uses the same
   title ID as the cartridge, so the console treats it as that game's SD title
   (an installed digital copy of the same title is replaced; the cartridge
   itself is untouched).

No developer unit, no makerom and no title key are involved: the certificate
chain and ticket layout are copied from a system-update CIA that ships inside
the cartridge itself.

Size: {size:,} bytes.  Built from: {rom}
"""


def build_cia(mod: dict, changes: list[dict], code: dict, out_dir: Path,
              title_id: str, image: dict | None = None) -> dict:
    """Package the rebuilt ``.3ds`` as an installable CIA.

    ``image`` is the result of :func:`build_3ds` when that target already ran in
    this export (``--target all``); otherwise the image is built here, because a
    CIA must describe the *patched* contents, not the retail cartridge.

    ``tools/ctr_cia.py`` re-parses the written file before returning: header,
    certificate chain, ticket/TMD hashes and every content SHA-256.
    """
    root = out_dir / "cia"
    root.mkdir(parents=True, exist_ok=True)
    # Older exports wrote a BLOCKED.md here; leaving it next to a real .cia
    # would tell the modder the opposite of what just happened.
    stale = root / "BLOCKED.md"
    if stale.exists():
        stale.unlink()

    if image is None:
        print("Building the .3ds image the CIA is made from ...")
        image = build_3ds(mod, changes, code, out_dir, title_id, no_rom=False)
    rom = Path(image["rom"])
    if not rom.is_file():
        raise ExportError(f"the .3ds image for the CIA is missing: {rom}")

    from tools import ctr_cia      # local import: only this target needs the CIA code

    cia_path = root / "DQXI_modded.cia"
    if cia_path.exists():
        cia_path.unlink()
    print(f"Building CIA from {rom.name} ({rom.stat().st_size / 1e9:.2f} GB) ...")
    shown: dict[str, int] = {}

    def progress(stage: str, done: int, total: int) -> None:
        pct = int(done * 100 / total) if total else 100
        last = shown.get(stage, -10)
        if pct >= last + 10 or pct == 100:
            shown[stage] = pct
            print(f"  {stage}: {pct}%")

    result = ctr_cia.build_cia(rom, cia_path, progress=progress)
    if not result["valid"] or result["problems"]:
        raise ExportError(f"the written CIA failed verification: {result['problems']}")

    (root / "README.txt").write_text(CIA_README.format(
        name=mod["name"] or "unnamed mod", version=mod["version"] or "?",
        author=mod["author"] or "?", title_id=title_id,
        size=result["size"], rom=rom.name), encoding="utf-8")

    return {
        "status": "ok",
        "dir": str(root),
        "cia": str(cia_path),
        "size": result["size"],
        "sha256": result["sha256"],
        "title_id": result["title_id"],
        "cert_size": result["cert_size"],
        "ticket_size": result["ticket_size"],
        "tmd_size": result["tmd_size"],
        "meta_size": result["meta_size"],
        "content_size": result["content_size"],
        "contents": result["contents"],
        "source_rom": str(rom),
        "source_rom_sha256": image["rom_sha256"],
        "signed": False,
        "note": "fakesigned CIA: contents are unencrypted, RSA signatures are blank; "
                "install on a Luma3DS console with FBI",
        "valid": True,
    }


# --------------------------------------------------------------------------- #
# driver
# --------------------------------------------------------------------------- #
def read_title_id() -> str:
    if not NCCH0_HEADER.is_file():
        raise ExportError(f"missing {NCCH0_HEADER}; run tools/extract_rom.py first")
    head = NCCH0_HEADER.read_bytes()
    # The 0x200-byte block at ROM offset 0x4000 starts with the 0x100-byte
    # RSA signature, so "NCCH" sits at 0x100 and the fields start there.
    # Field offsets below are relative to the block (== relative to the magic
    # once the signature is skipped), which is also how parse_ncch() reads the
    # header out of a full image.
    if head[0x100:0x104] != b"NCCH":
        raise ExportError("original/ncch0_header.bin has no NCCH magic at 0x100")
    program_id = u64(head, 0x118)
    if program_id >> 32 != 0x00040000:
        raise ExportError(f"unexpected NCCH program id {program_id:016X} (not a game title)")
    return f"{program_id:016X}"


def export(mod_dir: Path, out_dir: Path, target: str, code_mode: str,
           no_rom: bool) -> tuple[dict, int]:
    started = time.time()
    for needed in (ORIGINAL_ROMFS, RETAIL_CODE):
        if not needed.is_file():
            raise ExportError(f"missing {needed}; run tools/extract_rom.py first")
    if no_rom and target in ("cia", "all"):
        raise ExportError(
            "--no-rom cannot be combined with the CIA target: a CIA is made from the "
            "full .3ds image, not from romfs.bin alone.  Drop --no-rom (or use "
            "--target 3ds --no-rom for a RomFS-only check).")
    title_id = read_title_id()
    mod = load_mod(mod_dir)
    print(f"Mod: {mod['name'] or '(unnamed)'} {mod['version']} by {mod['author'] or '(unknown)'}")
    print(f"Title ID: {title_id}")

    index = RomFsIndex(ORIGINAL_ROMFS)
    changes = collect_changes(mod, index)
    print(f"RomFS changes: {len(changes)} file(s)")

    # A real 3DS/2DS is ARMv6K + VFPv2; Azahar also runs ARMv7/VFPv3, so an emulator boot
    # cannot prove a code cave is safe.  Check every changed instruction before writing
    # anything at all (the same rule applies to both the Luma and the .3ds target).
    arm_report = None
    if mod["code"]["changed"]:
        from tools.check_armv6k import check_code
        print("Checking changed native code for ARMv7 / VFPv3 instructions ...")
        arm = check_code(RETAIL_CODE.read_bytes(), Path(mod["code"]["path"]).read_bytes())
        real = [h for h in arm["hits"] if not h.get("data")]
        arm_report = {"changed_words": arm["changed_words"], "ok": arm["ok"],
                      "violations": [{"address": f"0x{h['address']:08X}",
                                      "word": f"0x{h['word']:08X}", "name": h["name"]}
                                     for h in real],
                      "literal_words_skipped": len(arm["hits"]) - len(real)}
        if not arm["ok"]:
            detail = "\n".join(f"  0x{h['address']:08X}  {h['word']:08X}  {h['name']}"
                               for h in real[:10])
            raise ExportError(
                "the edited code contains instructions a real 3DS/2DS cannot execute "
                f"({len(real)} changed instruction(s)):\n{detail}\n"
                "Azahar runs ARMv7/VFPv3, so it may look fine in the emulator and then crash "
                "on hardware with 'undefined instruction'. Use ARMv6K/VFPv2 code only "
                "(no movw/movt, ubfx/sbfx/bfi/bfc, sdiv/udiv, mls, rbit, VFP immediates, "
                "fixed-point vcvt).  Run tools/check_armv6k.py for the full list.")
        if arm["hits"]:
            print(f"  {arm['changed_words']} changed words; literal-pool words skipped: "
                  f"{len(arm['hits']) - len(real)}")
        print("  ARMv6K/VFPv2 check OK")

    report: dict = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "title_id": title_id,
        "mod": {
            "dir": str(mod_dir),
            "name": mod["name"],
            "version": mod["version"],
            "author": mod["author"],
            "description": mod["description"],
        },
        "code": {
            "changed": mod["code"]["changed"],
            "size": mod["code"]["size"],
            "sha256": mod["code"]["sha256"],
        },
        "armv6k": arm_report,
        "romfs_changes": [
            {"path": c["path"], "size": c["size"],
             "original_size": c["original_size"], "sha256": c["sha256"]}
            for c in changes
        ],
        "targets": {},
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    exit_code = 0
    try:
        built_image = None
        if target in ("luma", "all"):
            print("Exporting Luma3DS LayeredFS folder ...")
            report["targets"]["luma"] = build_luma(
                mod, changes, mod["code"], out_dir, title_id, code_mode)
            print(f"  -> {report['targets']['luma']['title_dir']} (validated)")
        if target in ("3ds", "all"):
            print("Exporting .3ds image ...")
            report["targets"]["3ds"] = build_3ds(
                mod, changes, mod["code"], out_dir, title_id, no_rom)
            if no_rom:
                print(f"  -> {report['targets']['3ds']['romfs']} (validated: {report['targets']['3ds']['romfs_sha256']})")
            else:
                built_image = report["targets"]["3ds"]
                print(f"  -> {built_image['rom']} (validated)")
        if target in ("cia", "all"):
            print("Exporting installable CIA ...")
            report["targets"]["cia"] = build_cia(
                mod, changes, mod["code"], out_dir, title_id, image=built_image)
            cia = report["targets"]["cia"]
            print(f"  -> {cia['cia']} ({cia['size']:,} bytes, validated)")
    finally:
        report["elapsed_seconds"] = round(time.time() - started, 1)
        report["ok"] = exit_code == 0
        report_path = out_dir / "EXPORT_REPORT.json"
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {report_path}")

    return report, exit_code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Export the mod/ workspace for a real 3DS/2DS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage\n-----", 1)[1] if "Usage\n-----" in __doc__ else None)
    ap.add_argument("--target", choices=["luma", "3ds", "cia", "all"], default="luma")
    ap.add_argument("--mod", type=Path, default=DEFAULT_MOD_DIR,
                    help="mod workspace (default: mod/)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR,
                    help="output folder (default: out/)")
    ap.add_argument("--code", choices=["ips", "bin"], default="ips",
                    help="native patch format for Luma: code.ips (small) or code.bin")
    ap.add_argument("--no-rom", action="store_true",
                    help="build only the validated out/3ds/romfs.bin, skip the 4 GiB repack")
    stage = ap.add_argument_group("staging an edit into mod/romfs")
    stage.add_argument("--stage-table", metavar="TABLE",
                       help="edited table schema key (e.g. syscmn/item.json): rebuild its "
                            "pack into --mod so the next export includes it")
    stage.add_argument("--stage-pack", metavar="PACK",
                       help="RomFS pack path (e.g. syscmn.pack): rebuild it with --member")
    stage.add_argument("--member", help="member name inside --stage-pack (e.g. item.bxon)")
    stage.add_argument("--replacement", type=Path,
                       help="rebuilt .bxon / .bch / ... to put into the pack")
    args = ap.parse_args(argv)

    print("=" * 78)
    print(" DQXI 3DS mod export")
    print("=" * 78)
    try:
        if args.stage_table or args.stage_pack:
            if args.replacement is None:
                raise ExportError("--stage-table/--stage-pack need --replacement")
            if args.stage_table:
                info = stage_table(args.stage_table, args.replacement, args.mod)
            else:
                if not args.member:
                    raise ExportError("--stage-pack needs --member")
                info = stage_member(args.stage_pack, args.member, args.replacement, args.mod)
            print(f"  staged {info.get('table', info['member'])} -> {info['mod_file']}")
            print(f"  pack {info['size']:,} bytes (retail {info['original_size']:,})")
            print("=" * 78)
            print(" STAGED OK — run the exporter again to build the mod")
            print("=" * 78)
            return 0
        report, exit_code = export(Path(args.mod), Path(args.out), args.target,
                                   args.code, args.no_rom)
    except ExportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130

    print("=" * 78)
    if exit_code == 0:
        print(" EXPORT OK")
    print("=" * 78)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
