#!/usr/bin/env python3
"""
tools/repack_rom.py - Dragon Quest XI 3DS ROM Bit-Matching Repacker

Assembles a complete, byte-for-byte matching cartridge image (.3ds / NCSD)
from extracted baseline containers in original/:
- Rebuilds ExeFS (with optional custom code.bin compilation via tools/blz.py)
- Reassembles NCCH 0 (ExHeader, Logo, Plain, ExeFS, Gap, RomFS)
- Integrates secondary partitions (Manual, Update N3DS, Update O3DS)
- Appends exact 1,572,806,656 bytes of 0xFF cartridge trailing padding
- Verifies output ROM size (4,294,967,296 bytes) and cryptographic SHA-256

With --modified the RomFS may differ in size from retail (a grown file appended
by tools/patch_asset.py): the NCCH header's RomFS size, content size, hash
region size and RomFS superblock hash, the NCSD partition table and the card
info "filled size" are updated, the following partitions move by the size
difference, and the trailing 0xFF padding shrinks so the image stays 4 GiB.
The retail RSA signatures over the NCSD/NCCH headers cannot be regenerated.

Usage:
    python tools/repack_rom.py [orig_dir] [out_rom]
    python tools/repack_rom.py [--in <dir>] [--out <path>] [--code <path>]
"""

import argparse
import hashlib
import json
import os
import struct
import sys

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import blz

DEFAULT_ORIG_DIR = os.path.abspath(os.path.join(_TOOLS_DIR, "..", "original"))
DEFAULT_OUT_ROM = os.path.abspath(os.path.join(_TOOLS_DIR, "..", "build", "DQXI.3ds"))
TARGET_ROM_SHA256 = "0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74"
TARGET_ROM_SIZE = 4294967296
RETAIL_ROMFS_SIZE = 2679185408
MEDIA_UNIT = 0x200
CHUNK_SIZE = 16 * 1024 * 1024  # 16 MB


def copy_stream(src_path: str, dst_f, hasher, expected_size: int = None):
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"Required component file missing: {src_path}")
    written = 0
    with open(src_path, "rb") as sf:
        while chunk := sf.read(CHUNK_SIZE):
            dst_f.write(chunk)
            hasher.update(chunk)
            written += len(chunk)
    if expected_size is not None and written != expected_size:
        raise ValueError(f"Size mismatch in {src_path}: expected {expected_size}, got {written}")
    return written


def read_component(path: str, expected_size: int) -> bytes:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required component file missing: {path}")
    with open(path, "rb") as f:
        data = f.read()
    if len(data) != expected_size:
        raise ValueError(f"Size mismatch in {path}: expected {expected_size}, got {len(data)}")
    return data


def repack_rom(orig_dir: str, out_rom_path: str, custom_code_path: str = None, allow_modified: bool = False):
    if not os.path.exists(orig_dir):
        raise FileNotFoundError(f"Input original directory not found: {orig_dir}")

    # Upfront validation of ncch0_header.bin
    ncch0_path = os.path.join(orig_dir, "ncch0_header.bin")
    if not os.path.exists(ncch0_path):
        raise FileNotFoundError(f"Required component file missing: {ncch0_path}")
    with open(ncch0_path, "rb") as f:
        ncch0_hdr = bytearray(f.read())
    if len(ncch0_hdr) != 0x200:
        raise ValueError(f"Size mismatch in {ncch0_path}: expected 512, got {len(ncch0_hdr)}")
    if ncch0_hdr[0x100:0x104] != b"NCCH":
        raise ValueError(f"Invalid NCCH magic in {ncch0_path}")

    ncsd_hdr = bytearray(read_component(os.path.join(orig_dir, "ncsd_header.bin"), 0x200))
    card_info = bytearray(read_component(os.path.join(orig_dir, "card_info.bin"), 0x3E00))

    romfs_path = os.path.join(orig_dir, "romfs.bin")
    if not os.path.exists(romfs_path):
        raise FileNotFoundError(f"Required component file missing: {romfs_path}")
    romfs_size = os.path.getsize(romfs_path)
    if not allow_modified and romfs_size != RETAIL_ROMFS_SIZE:
        raise ValueError(f"Size mismatch in {romfs_path}: expected {RETAIL_ROMFS_SIZE}, got {romfs_size}")
    if romfs_size % MEDIA_UNIT:
        raise ValueError(f"RomFS size {romfs_size} is not a multiple of the 0x200 media unit")

    # RomFS fields of the NCCH header; for the retail RomFS these come out unchanged
    with open(romfs_path, "rb") as f:
        ivfc = f.read(0x60)
        master_size = struct.unpack_from("<I", ivfc, 8)[0]
        hash_region = (0x60 + master_size + MEDIA_UNIT - 1) // MEDIA_UNIT
        f.seek(0)
        superblock = hashlib.sha256(f.read(hash_region * MEDIA_UNIT)).digest()
    romfs_mu = struct.unpack_from("<I", ncch0_hdr, 0x1B0)[0]
    old_content_mu = struct.unpack_from("<I", ncch0_hdr, 0x104)[0]
    content_mu = romfs_mu + romfs_size // MEDIA_UNIT
    struct.pack_into("<I", ncch0_hdr, 0x104, content_mu)
    struct.pack_into("<II", ncch0_hdr, 0x1B4, romfs_size // MEDIA_UNIT, hash_region)
    ncch0_hdr[0x1E0:0x200] = superblock

    # NCSD partition table: partition 0 resized, the others moved along
    shift = content_mu - old_content_mu
    if shift:
        struct.pack_into("<I", ncsd_hdr, 0x124, content_mu)
        used_mu = 0
        for i in range(8):
            off, size = struct.unpack_from("<II", ncsd_hdr, 0x120 + i * 8)
            if size and i:
                off += shift
                struct.pack_into("<I", ncsd_hdr, 0x120 + i * 8, off)
            used_mu = max(used_mu, off + size)
        # card info header 0x300 (0x100 into card_info.bin): filled size of the cartridge
        struct.pack_into("<I", card_info, 0x100, used_mu * MEDIA_UNIT)

    metadata_path = os.path.join(orig_dir, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as mf:
            metadata = json.load(mf)
    else:
        metadata = None

    os.makedirs(os.path.dirname(os.path.abspath(out_rom_path)), exist_ok=True)
    print(f"Repacking ROM from '{orig_dir}' -> '{out_rom_path}'...")

    # Determine ExeFS components
    exefs_dir = os.path.join(orig_dir, "exefs")
    banner_path = os.path.join(exefs_dir, "banner")
    icon_path = os.path.join(exefs_dir, "icon")

    with open(banner_path, "rb") as f:
        banner_data = f.read()
    with open(icon_path, "rb") as f:
        icon_data = f.read()

    # Determine code data
    if custom_code_path:
        print(f"  Using custom executable from: {custom_code_path}")
        with open(custom_code_path, "rb") as f:
            code_bytes = f.read()
        # If uncompressed, compress with BLZ
        if len(code_bytes) > 4000000:
            print("  Compressing executable with CTR-SDK BLZ codec...")
            comp_code = blz.compress(code_bytes)
        else:
            comp_code = code_bytes
    else:
        code_comp_path = os.path.join(exefs_dir, ".code")
        if not os.path.exists(code_comp_path):
            code_comp_path = os.path.join(exefs_dir, "code.bin")
        with open(code_comp_path, "rb") as f:
            comp_code = f.read()

    # Rebuild ExeFS
    code_size = len(comp_code)
    code_pad_len = ((code_size + 0x1FF) & ~0x1FF) - code_size
    code_pad = b"\x00" * code_pad_len

    banner_offset = code_size + code_pad_len
    banner_size = len(banner_data)
    banner_pad_len = ((banner_size + 0x1FF) & ~0x1FF) - banner_size
    banner_pad = b"\x00" * banner_pad_len

    icon_offset = banner_offset + banner_size + banner_pad_len
    icon_size = len(icon_data)
    icon_pad_len = ((icon_size + 0x1FF) & ~0x1FF) - icon_size
    icon_pad = b"\x00" * icon_pad_len

    # Rebuild ExeFS header
    exefs_hdr = bytearray(0x200)
    # Entry 0: .code
    exefs_hdr[0:8] = b".code\x00\x00\x00"
    struct.pack_into("<II", exefs_hdr, 8, 0, code_size)
    # Entry 1: banner
    exefs_hdr[16:24] = b"banner\x00\x00"
    struct.pack_into("<II", exefs_hdr, 24, banner_offset, banner_size)
    # Entry 2: icon
    exefs_hdr[32:40] = b"icon\x00\x00\x00\x00"
    struct.pack_into("<II", exefs_hdr, 40, icon_offset, icon_size)

    # Hashes in reverse order
    exefs_hdr[0x1E0:0x200] = hashlib.sha256(comp_code).digest()
    exefs_hdr[0x1C0:0x1E0] = hashlib.sha256(banner_data).digest()
    exefs_hdr[0x1A0:0x1C0] = hashlib.sha256(icon_data).digest()

    exefs_hdr_bytes = bytes(exefs_hdr)

    # Update NCCH 0 ExeFS superblock hash if custom code was provided
    if custom_code_path:
        ncch0_hdr[0x1C0:0x1E0] = hashlib.sha256(exefs_hdr_bytes).digest()

    hasher = hashlib.sha256()

    with open(out_rom_path, "wb") as out_f:
        # 1. NCSD Header (0x0..0x200)
        print("  Writing NCSD header...")
        out_f.write(ncsd_hdr)
        hasher.update(ncsd_hdr)

        # 2. Card Info (0x200..0x4000)
        print("  Writing Card Info / Device Info...")
        out_f.write(card_info)
        hasher.update(card_info)

        # 3. NCCH 0 Header (0x4000..0x4200)
        print("  Writing NCCH 0 header...")
        out_f.write(ncch0_hdr)
        hasher.update(ncch0_hdr)

        # 4. Extended Header (0x4200..0x4A00)
        print("  Writing Extended Header...")
        copy_stream(os.path.join(orig_dir, "exheader.bin"), out_f, hasher, 0x800)

        # 5. Logo Region (0x4A00..0x6A00)
        print("  Writing Logo Region...")
        copy_stream(os.path.join(orig_dir, "logo.bin"), out_f, hasher, 0x2000)

        # 6. Plain Region (0x6A00..0x6C00)
        print("  Writing Plain Region...")
        copy_stream(os.path.join(orig_dir, "plain.bin"), out_f, hasher, 0x200)

        # 7. ExeFS Region (0x6C00..0x437E00)
        print("  Writing ExeFS payloads...")
        out_f.write(exefs_hdr_bytes)
        hasher.update(exefs_hdr_bytes)

        out_f.write(comp_code)
        hasher.update(comp_code)
        out_f.write(code_pad)
        hasher.update(code_pad)

        out_f.write(banner_data)
        hasher.update(banner_data)
        out_f.write(banner_pad)
        hasher.update(banner_pad)

        out_f.write(icon_data)
        hasher.update(icon_data)
        out_f.write(icon_pad)
        hasher.update(icon_pad)

        # 8. ExeFS-RomFS Gap (0x437E00..0x438000, 512 bytes of 0x00)
        gap_bytes = b"\x00" * 0x200
        out_f.write(gap_bytes)
        hasher.update(gap_bytes)

        # 9. RomFS (retail: 0x438000..0x9FF4A000, 2,679,185,408 bytes)
        print(f"  Streaming RomFS container ({romfs_size / 1e9:.2f} GB)...")
        copy_stream(romfs_path, out_f, hasher, romfs_size)

        # 10. Secondary Partitions
        print("  Writing secondary partitions (Manual, Update N3DS, Update O3DS)...")
        copy_stream(os.path.join(orig_dir, "partitions", "manual.ncch"), out_f, hasher, 1507328)
        copy_stream(os.path.join(orig_dir, "partitions", "update_n3ds.ncch"), out_f, hasher, 3653632)
        copy_stream(os.path.join(orig_dir, "partitions", "update_o3ds.ncch"), out_f, hasher, 33390592)

        # 11. Cartridge Trailing Padding (retail: 1,572,806,656 bytes of 0xFF)
        rem_pad = TARGET_ROM_SIZE - out_f.tell()
        if rem_pad < 0:
            raise ValueError(f"RomFS grew past the 4 GiB cartridge by {-rem_pad:,} bytes")
        print(f"  Appending cartridge trailing padding ({rem_pad / 2**30:.2f} GiB of 0xFF)...")
        pad_block = b"\xFF" * (4 * 1024 * 1024)  # 4 MB block
        while rem_pad > 0:
            take = min(rem_pad, len(pad_block))
            out_f.write(pad_block[:take])
            hasher.update(pad_block[:take])
            rem_pad -= take

    final_size = os.path.getsize(out_rom_path)
    final_sha256 = hasher.hexdigest()

    print("\nRepacking Summary:")
    print(f"  ROM Output Path: {out_rom_path}")
    print(f"  Total ROM Size:  {final_size:,} bytes (Expected: {TARGET_ROM_SIZE:,})")
    print(f"  SHA-256 Digest:  {final_sha256}")

    if final_size != TARGET_ROM_SIZE:
        raise ValueError(f"Output ROM size mismatch: {final_size} != {TARGET_ROM_SIZE}")

    if not custom_code_path and not allow_modified:
        if final_sha256 != TARGET_ROM_SHA256:
            raise ValueError(f"Repacked ROM SHA-256 mismatch!\nExpected: {TARGET_ROM_SHA256}\nComputed: {final_sha256}")
        print("  Result: 100% BIT-MATCHING SUCCESS!")
    else:
        print("  Result: Custom/modified ROM repacked successfully!")


def main():
    parser = argparse.ArgumentParser(description="Dragon Quest XI 3DS ROM Repacker")
    parser.add_argument("pos_in", nargs="?", default=None, help="Directory containing extracted components")
    parser.add_argument("pos_out", nargs="?", default=None, help="Path for repacked .3ds ROM")
    parser.add_argument("--in", dest="opt_in", default=None, help="Directory containing extracted components")
    parser.add_argument("--out", dest="opt_out", default=None, help="Path for repacked .3ds ROM")
    parser.add_argument("--code", dest="code", default=None, help="Optional custom code.bin to inject")
    parser.add_argument("--modified", action="store_true", help="Allow a non-retail output ROM (for asset/level mods)")
    args = parser.parse_args()

    orig_dir = args.opt_in or args.pos_in or DEFAULT_ORIG_DIR
    out_rom = args.opt_out or args.pos_out or DEFAULT_OUT_ROM

    try:
        repack_rom(orig_dir, out_rom, args.code, args.modified)
        sys.exit(0)
    except Exception as e:
        print(f"Error repacking ROM: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
