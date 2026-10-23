#!/usr/bin/env python3
"""Patch a member inside any DQXI PACK and optionally rebuild a ROM.

This is the generic companion to `patch_game.py`:

  original pack -> replace one member -> rebuild the PACK
  -> patch a copy of romfs.bin -> rebuild IVFC hashes -> repack ROM

A same-size member is overwritten in place (exact original layout); a member of
a different size makes the PACK lay its members out afresh. Compressed packs
(PACA, e.g. syscmn.pack with the item tables) are decompressed, patched and
recompressed. A PACK that still fits its RomFS slot is written there (the file
entry's size is updated if it shrank); a larger one is appended at the end of
the RomFS data region, its file entry is pointed there and the IVFC hash levels
are moved behind the new data end (see `write_romfs_file`).

Usage:
    python tools/patch_asset.py --pack 3d/model/ani00000a_h.pack \
        --member ani00000a_h.bch --replacement build/model_patch_test/patched.bch --no-rom
    python tools/patch_asset.py --pack ... --member ... --replacement ... 
"""
from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import blz, pack
from tools import romfs_hash

ROMFS_LEVEL3_OFFSET = 0x1000
ROMFS_DATA_OFFSET = 0x17E840
BUILD = PROJECT_ROOT / "build"


def rebuild_pack(original_pack: Path, member: str, replacement: Path, out_pack: Path) -> bytes:
    original = original_pack.read_bytes()
    p = pack.Pack.parse(original)
    if p.compressed:
        return _rebuild_compressed(original, p, member, replacement, out_pack)
    raw = bytearray(original)
    data = replacement.read_bytes()
    entries = [e for e in p.entries if e.name == member]
    if not entries:
        raise ValueError(f"{original_pack} has no member {member!r}")
    if any(len(data) != len(e.data) for e in entries):
        built = _rebuild_resized(p, member, data)
    else:
        for entry in entries:
            raw[entry.payload_offset:entry.payload_offset + len(data)] = data
        built = bytes(raw)
        if len(built) != len(original):
            raise ValueError(f"patched PACK changed size ({len(built)} != {len(original)})")
    out_pack.parent.mkdir(parents=True, exist_ok=True)
    out_pack.write_bytes(built)
    return built


def _rebuild_resized(p, member: str, data: bytes) -> bytes:
    """A member changed size: lay the PACK out afresh and check it parses back."""
    for entry in p.entries:
        if entry.name == member:
            entry.data = data
    built = p.build()
    check = pack.Pack.parse(built)
    if [(e.name, e.data) for e in check.entries] != [(e.name, e.data) for e in p.entries]:
        raise ValueError("rebuilt PACK does not parse back to the patched members")
    return built


def _rebuild_compressed(original: bytes, p, member: str, replacement: Path, out_pack: Path) -> bytes:
    """PACA: patch the member inside the decompressed pack and recompress.

    The recompressed pack may come out smaller or larger than the original;
    main() then resizes or relocates the RomFS file entry.
    """
    data = replacement.read_bytes()
    entries = [e for e in p.entries if e.name == member]
    if not entries:
        raise ValueError(f"pack has no member {member!r}")
    if any(len(data) != len(e.data) for e in entries):
        built = _rebuild_resized(p, member, data)
        out_pack.parent.mkdir(parents=True, exist_ok=True)
        out_pack.write_bytes(built)
        return built
    plain = bytearray(blz.decompress(original))
    for entry in entries:
        plain[entry.payload_offset:entry.payload_offset + len(data)] = data
    # the decompressed stream already starts with "PACA" + size: BLZ keeps that
    # prefix uncompressed, so compress the whole buffer as-is
    built = blz.compress(bytes(plain), allow_overlap=True)
    if built[:4] != b"PACA":
        raise ValueError("recompressed pack lost its PACA magic")
    if blz.decompress(built) != bytes(plain):
        raise ValueError("recompressed pack does not decompress to the patched data")
    out_pack.parent.mkdir(parents=True, exist_ok=True)
    out_pack.write_bytes(built)
    return built


def _romfs_file_entry(f, file_offset: int) -> int:
    """Absolute position of the file metadata entry whose data starts at
    `file_offset` (relative to the level-3 file data)."""
    f.seek(ROMFS_LEVEL3_OFFSET)
    header = struct.unpack("<10I", f.read(40))
    meta_off, meta_len = header[7], header[8]
    f.seek(ROMFS_LEVEL3_OFFSET + meta_off)
    table = f.read(meta_len)
    pos = 0
    while pos + 0x20 <= len(table):
        data_offset = struct.unpack_from("<Q", table, pos + 8)[0]
        name_len = struct.unpack_from("<I", table, pos + 0x1C)[0]
        if data_offset == file_offset:
            return ROMFS_LEVEL3_OFFSET + meta_off + pos
        pos += 0x20 + ((name_len + 3) & ~3)
    raise ValueError(f"no RomFS file entry at data offset 0x{file_offset:X}")


def set_romfs_file_size(romfs: Path, file_offset: int, new_size: int) -> None:
    """Rewrites the size of the RomFS file whose data starts at `file_offset`
    (relative to the level-3 data region)."""
    with open(romfs, "r+b") as f:
        entry = _romfs_file_entry(f, file_offset)
        f.seek(entry + 0x10)
        f.write(struct.pack("<Q", new_size))


def write_romfs_file(romfs: Path, file_offset: int, old_size: int, built: bytes) -> dict:
    """Puts `built` in place of the RomFS file at `file_offset` (size `old_size`).

    A file that fits is written over its old slot (the rest zeroed). A larger
    one is appended 16-byte aligned at the end of the level-3 data region: the
    data region grows, the hash levels move behind it, and the file entry gets
    the new data offset and size. The old slot is left as it was. Run
    `romfs_hash.rebuild` afterwards. Returns the file's new offset and size.
    """
    with open(romfs, "rb") as f:
        info = romfs_hash.parse_header(f.read(romfs_hash.MASTER_OFF))
        f.seek(info["data_start"])
        file_data = info["data_start"] + struct.unpack("<10I", f.read(40))[9]
    if len(built) <= old_size:
        with open(romfs, "r+b") as f:
            f.seek(file_data + file_offset)
            f.write(built + bytes(old_size - len(built)))
        if len(built) != old_size:
            set_romfs_file_size(romfs, file_offset, len(built))
        return {"offset": file_offset, "size": len(built), "relocated": False}

    data_end = info["data_start"] + info["data_size"]
    new_offset = romfs_hash.align(data_end - file_data, 0x10)
    romfs_hash.resize_data(romfs, file_data + new_offset + len(built) - info["data_start"])
    with open(romfs, "r+b") as f:
        f.seek(file_data + new_offset)
        f.write(built)
        entry = _romfs_file_entry(f, file_offset)
        f.seek(entry + 8)
        f.write(struct.pack("<QQ", new_offset, len(built)))
    return {"offset": new_offset, "size": len(built), "relocated": True}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", required=True, help="RomFS pack path, e.g. 3d/model/foo.pack")
    ap.add_argument("--member", required=True, help="member name inside the PACK")
    ap.add_argument("--replacement", required=True, type=Path)
    ap.add_argument("--no-rom", action="store_true")
    args = ap.parse_args()

    pack_rel = args.pack.replace("\\", "/").lstrip("/")
    original_pack = PROJECT_ROOT / "game_data" / "romfs" / pack_rel
    if not original_pack.is_file():
        print(f"missing original pack: {original_pack}", file=sys.stderr)
        return 1
    out_pack = BUILD / "patched" / "packs" / pack_rel
    try:
        built = rebuild_pack(original_pack, args.member, args.replacement, out_pack)
    except Exception as exc:
        print(f"pack rebuild failed: {exc}", file=sys.stderr)
        return 2

    manifest = json.loads((PROJECT_ROOT / "audit" / "romfs_manifest.json").read_text(encoding="utf-8"))
    rf = next((f for f in manifest["files"] if f["path"] == "/" + pack_rel), None)
    if rf is None:
        print("pack not found in RomFS manifest", file=sys.stderr)
        return 3
    data_offset = ROMFS_LEVEL3_OFFSET + ROMFS_DATA_OFFSET + rf["offset"]
    rom_absolute = 0x438000 + data_offset
    print(f"Patching {pack_rel}:{args.member} at RomFS 0x{data_offset:X} / ROM 0x{rom_absolute:X} ({len(built):,} bytes)")

    patched_romfs = BUILD / "patched" / "romfs.bin"
    patched_romfs.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROJECT_ROOT / "original" / "romfs.bin", patched_romfs)
    placed = write_romfs_file(patched_romfs, rf["offset"], rf["size"], built)
    if placed["relocated"]:
        data_offset = ROMFS_LEVEL3_OFFSET + ROMFS_DATA_OFFSET + placed["offset"]
        rom_absolute = 0x438000 + data_offset
        print(f"  PACK grew {rf['size']:,} -> {len(built):,} bytes: appended at RomFS 0x{data_offset:X}")
    elif len(built) != rf["size"]:
        print(f"  RomFS entry size {rf['size']:,} -> {len(built):,}")

    print("Rebuilding RomFS IVFC hash tree...")
    hash_report = romfs_hash.rebuild(patched_romfs)
    check = romfs_hash.verify(patched_romfs)
    if not check["ok"]:
        print(f"hash verification failed: {check}", file=sys.stderr)
        return 4
    print(f"  hash tree OK ({hash_report['data_blocks']:,} data blocks)")

    if not args.no_rom:
        patch_input = BUILD / "patched_input_asset"
        if patch_input.exists():
            shutil.rmtree(patch_input)
        for src in (PROJECT_ROOT / "original").rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(PROJECT_ROOT / "original")
            if rel.as_posix() == "romfs.bin":
                continue
            dst = patch_input / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                dst.hardlink_to(src)
            except OSError:
                shutil.copy2(src, dst)
        try:
            (patch_input / "romfs.bin").hardlink_to(patched_romfs)
        except OSError:
            shutil.copy2(patched_romfs, patch_input / "romfs.bin")
        out_rom = BUILD / "DQXI_asset_patched.3ds"
        cmd = [sys.executable, str(PROJECT_ROOT / "tools" / "repack_rom.py"),
               "--in", str(patch_input), "--out", str(out_rom), "--modified"]
        r = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if r.returncode != 0:
            return r.returncode
        print(f"Patched ROM: {out_rom}")

    report = {
        "pack": pack_rel,
        "member": args.member,
        "replacement": str(args.replacement),
        "patched_pack": str(out_pack.relative_to(PROJECT_ROOT)),
        "romfs_patch_offset": f"0x{data_offset:X}",
        "rom_absolute_offset": f"0x{rom_absolute:X}",
        "romfs_hashes": hash_report,
        "bytes": len(built),
        "relocated": placed["relocated"],
        "rom": str((BUILD / "DQXI_asset_patched.3ds").relative_to(PROJECT_ROOT)) if not args.no_rom else None,
    }
    (BUILD / "ASSET_PATCH_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
