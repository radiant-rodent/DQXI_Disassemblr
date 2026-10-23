#!/usr/bin/env python3
"""
tools/verify.py - Cryptographic Verification Suite for Dragon Quest XI Disassembly Project

Validates SHA-256 integrity of all extracted containers, executables, partitions,
and repacked ROM artifacts against verified cryptographic baselines.

Usage:
    python tools/verify.py
    python tools/verify.py [manifest_path]
    python tools/verify.py --all
"""

import argparse
import hashlib
import os
import sys

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_TOOLS_DIR, ".."))
DEFAULT_MANIFEST = os.path.join(_PROJECT_ROOT, "original", "hashes.sha256")
DEFAULT_REPACKED_ROM = os.path.join(_PROJECT_ROOT, "build", "DQXI.3ds")

TARGET_ROM_SHA256 = "0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74"
TARGET_ROM_SIZE = 4294967296
CHUNK_SIZE = 16 * 1024 * 1024


def sha256_file(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_manifest(manifest_path: str) -> bool:
    if not os.path.exists(manifest_path):
        print(f"Error: manifest file '{manifest_path}' does not exist.", file=sys.stderr)
        return False

    base_dir = os.path.dirname(manifest_path)
    all_passed = True
    total_checked = 0

    print("=" * 80)
    print(f"Verifying Manifest: {manifest_path}")
    print("=" * 80)

    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue

        expected_hash, rel_path = parts[0], parts[1].strip()
        target_path = os.path.join(base_dir, rel_path)

        if not os.path.exists(target_path):
            print(f"  [MISSING] {rel_path}")
            all_passed = False
            total_checked += 1
            continue

        file_size = os.path.getsize(target_path)
        actual_hash = sha256_file(target_path)
        if actual_hash.lower() == expected_hash.lower():
            print(f"  [PASS] {rel_path} ({file_size:,} B)")
        else:
            print(f"  [FAIL] {rel_path} ({file_size:,} B)")
            print(f"         Expected: {expected_hash}")
            print(f"         Actual:   {actual_hash}")
            all_passed = False
        total_checked += 1

    print("-" * 80)
    print(f"Manifest Verification: {total_checked} files checked, Status: {'PASS' if all_passed else 'FAIL'}")
    return all_passed


def verify_repacked_rom(rom_path: str) -> bool:
    if not os.path.exists(rom_path):
        print(f"  [NOT FOUND] Repacked ROM '{rom_path}' not found", file=sys.stderr)
        return False

    print("-" * 80)
    print(f"Verifying Repacked ROM: {rom_path}")
    size = os.path.getsize(rom_path)
    print(f"  File size: {size:,} bytes")
    if size != TARGET_ROM_SIZE:
        print(f"  [FAIL] Size mismatch: expected {TARGET_ROM_SIZE:,}, got {size:,}", file=sys.stderr)
        return False

    digest = sha256_file(rom_path)
    print(f"  SHA-256:   {digest}")
    if digest.lower() == TARGET_ROM_SHA256.lower():
        print("  [PASS] Bit-matching repacked ROM verified!")
        return True
    else:
        print(f"  [FAIL] Hash mismatch!\n         Expected: {TARGET_ROM_SHA256}\n         Actual:   {digest}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Cryptographic baseline verification suite")
    parser.add_argument("manifest", nargs="?", default=None, help="Path to manifest file")
    parser.add_argument("--manifest", dest="opt_manifest", default=None, help="Path to manifest file")
    parser.add_argument("--rom", default=None, help="Path to repacked ROM file to verify")
    args = parser.parse_args()

    manifest_path = args.opt_manifest or args.manifest or DEFAULT_MANIFEST

    if args.rom is not None:
        if not os.path.exists(args.rom):
            print(f"Error: repacked ROM '{args.rom}' not found", file=sys.stderr)
            sys.exit(1)
        rom_path = args.rom
        check_rom = True
    else:
        rom_path = DEFAULT_REPACKED_ROM
        check_rom = os.path.exists(rom_path)

    manifest_ok = verify_manifest(manifest_path)
    rom_ok = True
    if check_rom:
        rom_ok = verify_repacked_rom(rom_path)

    overall_ok = manifest_ok and rom_ok
    print("=" * 80)
    if overall_ok:
        print("OVERALL VERIFICATION: PASS")
        sys.exit(0)
    else:
        print("OVERALL VERIFICATION: FAIL", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
