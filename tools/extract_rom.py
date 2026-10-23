#!/usr/bin/env python3
"""
tools/extract_rom.py - Dragon Quest XI 3DS ROM Container Unpacker

Extracts decrypted DQXI.3ds cartridge image into original/ container artifacts:
- NCSD header & Card Info
- NCCH 0 (ExHeader, Logo, Plain, ExeFS, RomFS)
- ExeFS files (.code, code.bin, code.decompressed.bin, banner, icon)
- Partitions 1 (Manual), 6 (Update N3DS), 7 (Update O3DS)
- Generates baseline cryptographic hashes in original/hashes.sha256
- Generates layout metadata in original/metadata.json

Usage:
    python tools/extract_rom.py [rom_path] [out_dir]
    python tools/extract_rom.py [--rom <path>] [--out <dir>]
"""

import argparse
import hashlib
import json
import os
import struct
import sys

# Ensure tools/ directory is in sys.path so blz can be imported
_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import blz

DEFAULT_ROM_PATH = r"..\reference project\DQXI.3ds"
DEFAULT_OUT_DIR = os.path.abspath(os.path.join(_TOOLS_DIR, "..", "original"))

CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB


def sha256_file(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_slice(src_file, offset: int, size: int, dst_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
    src_file.seek(offset)
    hasher = hashlib.sha256()
    rem = size
    with open(dst_path, "wb") as out_f:
        while rem > 0:
            take = min(rem, CHUNK_SIZE)
            chunk = src_file.read(take)
            if not chunk:
                raise IOError(f"Unexpected EOF while reading {size} bytes from offset {hex(offset)}")
            out_f.write(chunk)
            hasher.update(chunk)
            rem -= len(chunk)
    return hasher.hexdigest()


def extract_rom(rom_path: str, out_dir: str):
    if not os.path.exists(rom_path):
        raise FileNotFoundError(f"ROM file not found: {rom_path}")

    rom_size = os.path.getsize(rom_path)
    print(f"Extracting ROM: {rom_path} (Size: {rom_size:,} bytes)")
    os.makedirs(out_dir, exist_ok=True)

    hashes = {}
    metadata = {
        "rom_size": rom_size,
        "ncsd_header_offset": 0,
        "ncsd_header_size": 0x200,
        "card_info_offset": 0x200,
        "card_info_size": 0x3E00,
        "ncch0_header_offset": 0x4000,
        "ncch0_header_size": 0x200,
        "exheader_offset": 0x4200,
        "exheader_size": 0x800,
        "logo_offset": 0x4A00,
        "logo_size": 0x2000,
        "plain_offset": 0x6A00,
        "plain_size": 0x200,
        "exefs_header_offset": 0x6C00,
        "exefs_header_size": 0x200,
        "exefs_files": {
            ".code": {"offset": 0, "size": 3920924, "pad": 484},
            "banner": {"offset": 3921408, "size": 458832, "pad": 432},
            "icon": {"offset": 4380672, "size": 14016, "pad": 320},
        },
        "exefs_total_size": 0x431200,
        "exefs_romfs_gap_offset": 0x00437E00,
        "exefs_romfs_gap_size": 0x200,
        "romfs_offset": 0x00438000,
        "romfs_size": 2679185408,
        "partitions": {
            "manual": {"offset": 0x9FF4A000, "size": 1507328},
            "update_n3ds": {"offset": 0xA00BA000, "size": 3653632},
            "update_o3ds": {"offset": 0xA0436000, "size": 33390592},
        },
        "trailing_padding": {
            "offset": 0xA240E000,
            "size": 1572806656,
            "byte": "0xFF",
        },
    }

    with open(rom_path, "rb") as rf:
        # 1. NCSD Header & Card Info
        print("  Extracting ncsd_header.bin...")
        hashes["ncsd_header.bin"] = extract_slice(rf, 0x0, 0x200, os.path.join(out_dir, "ncsd_header.bin"))

        print("  Extracting card_info.bin...")
        hashes["card_info.bin"] = extract_slice(rf, 0x200, 0x3E00, os.path.join(out_dir, "card_info.bin"))

        # 2. NCCH 0 Header
        print("  Extracting ncch0_header.bin...")
        hashes["ncch0_header.bin"] = extract_slice(rf, 0x4000, 0x200, os.path.join(out_dir, "ncch0_header.bin"))

        # 3. Extended Header
        print("  Extracting exheader.bin...")
        hashes["exheader.bin"] = extract_slice(rf, 0x4200, 0x800, os.path.join(out_dir, "exheader.bin"))

        # 4. Logo Region
        print("  Extracting logo.bin...")
        hashes["logo.bin"] = extract_slice(rf, 0x4A00, 0x2000, os.path.join(out_dir, "logo.bin"))

        # 5. Plain Region
        print("  Extracting plain.bin...")
        hashes["plain.bin"] = extract_slice(rf, 0x6A00, 0x200, os.path.join(out_dir, "plain.bin"))

        # 6. ExeFS Header
        print("  Extracting exefs/header.bin...")
        hashes["exefs/header.bin"] = extract_slice(rf, 0x6C00, 0x200, os.path.join(out_dir, "exefs", "header.bin"))

        # 7. ExeFS Payloads
        print("  Extracting exefs/.code...")
        hashes["exefs/.code"] = extract_slice(rf, 0x6E00, 3920924, os.path.join(out_dir, "exefs", ".code"))
        # Also mirror to code.bin for toolchain compatibility
        with open(os.path.join(out_dir, "exefs", ".code"), "rb") as code_src:
            with open(os.path.join(out_dir, "exefs", "code.bin"), "wb") as code_dst:
                code_dst.write(code_src.read())
        hashes["exefs/code.bin"] = hashes["exefs/.code"]

        print("  Extracting exefs/banner...")
        hashes["exefs/banner"] = extract_slice(rf, 0x6E00 + 3921408, 458832, os.path.join(out_dir, "exefs", "banner"))

        print("  Extracting exefs/icon...")
        hashes["exefs/icon"] = extract_slice(rf, 0x6E00 + 4380672, 14016, os.path.join(out_dir, "exefs", "icon"))

        # 8. Decompress ExeFS code
        print("  Decompressing exefs/.code -> exefs/code.decompressed.bin...")
        with open(os.path.join(out_dir, "exefs", ".code"), "rb") as code_in:
            comp_code = code_in.read()
        decomp_code = blz.decompress(comp_code)
        decomp_path = os.path.join(out_dir, "exefs", "code.decompressed.bin")
        with open(decomp_path, "wb") as decomp_out:
            decomp_out.write(decomp_code)
        hashes["exefs/code.decompressed.bin"] = hashlib.sha256(decomp_code).hexdigest()

        # 9. RomFS Region
        print("  Extracting romfs.bin (2.68 GB, streaming)...")
        hashes["romfs.bin"] = extract_slice(rf, 0x00438000, 2679185408, os.path.join(out_dir, "romfs.bin"))

        # 10. Secondary Partitions
        print("  Extracting partitions/manual.ncch...")
        hashes["partitions/manual.ncch"] = extract_slice(
            rf, 0x9FF4A000, 1507328, os.path.join(out_dir, "partitions", "manual.ncch")
        )

        print("  Extracting partitions/update_n3ds.ncch...")
        hashes["partitions/update_n3ds.ncch"] = extract_slice(
            rf, 0xA00BA000, 3653632, os.path.join(out_dir, "partitions", "update_n3ds.ncch")
        )

        print("  Extracting partitions/update_o3ds.ncch...")
        hashes["partitions/update_o3ds.ncch"] = extract_slice(
            rf, 0xA0436000, 33390592, os.path.join(out_dir, "partitions", "update_o3ds.ncch")
        )

    # Write hashes.sha256
    hash_manifest_path = os.path.join(out_dir, "hashes.sha256")
    with open(hash_manifest_path, "w", encoding="utf-8") as hf:
        for rel_path, digest in sorted(hashes.items()):
            hf.write(f"{digest}  {rel_path}\n")
    print(f"  Written {len(hashes)} cryptographic baseline hashes to {hash_manifest_path}")

    # Write metadata.json
    metadata_path = os.path.join(out_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as mf:
        json.dump(metadata, mf, indent=2)
    print(f"  Written extraction metadata to {metadata_path}")

    print("\nExtraction complete! All components successfully unpacked and fingerprinted.")


def main():
    parser = argparse.ArgumentParser(description="Dragon Quest XI 3DS ROM Unpacker")
    parser.add_argument("pos_rom", nargs="?", default=None, help="Path to input DQXI.3ds ROM")
    parser.add_argument("pos_out", nargs="?", default=None, help="Output destination directory")
    parser.add_argument("--rom", dest="opt_rom", default=None, help="Path to input DQXI.3ds ROM")
    parser.add_argument("--out", dest="opt_out", default=None, help="Output destination directory")
    args = parser.parse_args()

    rom_path = args.opt_rom or args.pos_rom or DEFAULT_ROM_PATH
    out_dir = args.opt_out or args.pos_out or DEFAULT_OUT_DIR

    try:
        extract_rom(rom_path, out_dir)
        sys.exit(0)
    except Exception as e:
        print(f"Error during ROM extraction: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
