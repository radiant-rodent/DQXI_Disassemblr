#!/usr/bin/env python3
"""Apply an edited level to a playable patched ROM.

Workflow:
  1. Rebuild ``level3d/<map>.pack`` from the original PACK plus the patched
     ``level3d.bxon`` exported by the editor.
  2. Patch the pack into a copy of ``original/romfs.bin``: over its old slot
     when it fits, appended at the end of the RomFS data when it grew.
  3. Build a modified source directory and invoke ``tools/repack_rom.py`` with
     ``--modified`` to produce ``build/DQXI_patched.3ds``.

The retail image and the reference translation workspace are never touched.

Usage:
    python tools/patch_game.py --map b001_101a
    python tools/patch_game.py --map b001_101a --no-rom
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import pack
from tools import romfs_hash
from tools.patch_asset import write_romfs_file

ROMFS_LEVEL3_OFFSET = 0x1000
ROMFS_DATA_OFFSET = 0x17E840
BUILD = PROJECT_ROOT / "build"
PATCH_INPUT = BUILD / "patched_input"


def hardlink_or_copy(src: Path, dst: Path) -> None:
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def rebuild_pack(original_pack: Path, patched_bxon: Path, out_pack: Path) -> bytes:
    p = pack.Pack.parse(original_pack.read_bytes())
    replaced = False
    for entry in p.entries:
        if entry.name == "level3d.bxon":
            entry.data = patched_bxon.read_bytes()
            replaced = True
    if not replaced:
        raise ValueError(f"{original_pack} has no level3d.bxon entry")
    built = p.build()
    out_pack.parent.mkdir(parents=True, exist_ok=True)
    out_pack.write_bytes(built)
    return built


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True)
    ap.add_argument("--no-rom", action="store_true", help="Only rebuild the PACK, do not repack the ROM")
    args = ap.parse_args()

    map_id = args.map
    original_pack = PROJECT_ROOT / "game_data" / "romfs" / "level3d" / f"{map_id}.pack"
    patched_bxon = PROJECT_ROOT / "game_assets" / "maps" / map_id / "level3d.patched.bxon"
    if not original_pack.is_file():
        print(f"missing original pack: {original_pack}", file=sys.stderr)
        return 1
    if not patched_bxon.is_file():
        print(f"missing patched bxon: {patched_bxon}", file=sys.stderr)
        return 1

    out_pack = BUILD / "patched" / "level3d" / f"{map_id}.pack"
    try:
        built = rebuild_pack(original_pack, patched_bxon, out_pack)
    except Exception as exc:
        print(f"pack rebuild failed: {exc}", file=sys.stderr)
        return 2

    manifest = json.loads((PROJECT_ROOT / "audit" / "romfs_manifest.json").read_text(encoding="utf-8"))
    rf = next((f for f in manifest["files"] if f["path"] == f"/level3d/{map_id}.pack"), None)
    if rf is None:
        print("map pack not found in RomFS manifest", file=sys.stderr)
        return 3
    data_offset = ROMFS_LEVEL3_OFFSET + ROMFS_DATA_OFFSET + rf["offset"]
    rom_absolute = 0x438000 + data_offset
    print(f"Patching RomFS at 0x{data_offset:X} (ROM absolute 0x{rom_absolute:X}, {len(built):,} bytes)")

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

    # Rebuild the IVFC hash tree so the modified image passes strict RomFS checks.
    print("Rebuilding RomFS IVFC hash tree...")
    hash_report = romfs_hash.rebuild(patched_romfs)
    check = romfs_hash.verify(patched_romfs)
    if not check["ok"]:
        print(f"RomFS hash verification failed: {check}", file=sys.stderr)
        return 4
    print(f"  hash tree OK ({hash_report['data_blocks']:,} data blocks)")

    if not args.no_rom:
        if PATCH_INPUT.exists():
            shutil.rmtree(PATCH_INPUT)
        PATCH_INPUT.mkdir(parents=True)
        for src in (PROJECT_ROOT / "original").rglob("*"):
            if src.is_file():
                rel = src.relative_to(PROJECT_ROOT / "original")
                if rel.as_posix() == "romfs.bin":
                    continue
                dst = PATCH_INPUT / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                hardlink_or_copy(src, dst)
        hardlink_or_copy(patched_romfs, PATCH_INPUT / "romfs.bin")
        out_rom = BUILD / "DQXI_patched.3ds"
        cmd = [
            sys.executable,
            str(PROJECT_ROOT / "tools" / "repack_rom.py"),
            "--in",
            str(PATCH_INPUT),
            "--out",
            str(out_rom),
            "--modified",
        ]
        print("Repacking modified cartridge...")
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            return result.returncode
        print(f"\nPatched ROM: {out_rom}")
        print("RomFS IVFC hashes were rebuilt and verified.")

    report = {
        "map": map_id,
        "original_pack": str(original_pack.relative_to(PROJECT_ROOT)),
        "patched_bxon": str(patched_bxon.relative_to(PROJECT_ROOT)),
        "patched_pack": str(out_pack.relative_to(PROJECT_ROOT)),
        "romfs_patch_offset": f"0x{data_offset:X}",
        "rom_absolute_offset": f"0x{rom_absolute:X}",
        "romfs_hashes": hash_report,
        "bytes": len(built),
        "relocated": placed["relocated"],
        "rom": str((BUILD / "DQXI_patched.3ds").relative_to(PROJECT_ROOT)) if not args.no_rom else None,
    }
    (BUILD / "PATCH_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
