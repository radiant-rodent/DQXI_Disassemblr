#!/usr/bin/env python3
"""tools/recompile_game.py - Master One-Step Full Game Recompiler for Dragon Quest XI (3DS)

Executes the entire end-to-end rebuild and bit-matching verification pipeline:
1. Reassembles modular native assembly sources (.text, .rodata, .data, .bss) into build/code.bin.
2. Compresses ExeFS executable via CTR-SDK BLZ engine into build/code.compressed.bin.
3. Recompiles all containers and repacks the complete 4 GB cartridge ROM into build/DQXI.3ds.
4. Executes cryptographic SHA-256 verification asserting 100% byte-for-byte fidelity with the retail game.

Usage:
    python tools/recompile_game.py
"""

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ORIGINAL_ROM = PROJECT_ROOT / "original" / "DQXI.3ds"
if not ORIGINAL_ROM.is_file():
    ORIGINAL_ROM = Path(r"..\reference project\DQXI.3ds")

BUILD_DIR = PROJECT_ROOT / "build"
BUILD_CODE_BIN = BUILD_DIR / "code.bin"
BUILD_CODE_COMPRESSED = BUILD_DIR / "code.compressed.bin"
BUILD_ROM = BUILD_DIR / "DQXI.3ds"

# Authoritative Bit-Matching Targets
EXPECTED_ROM_SHA256 = "0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74"
EXPECTED_ROM_SIZE = 4294967296

EXPECTED_UNCOMPRESSED_SHA256 = "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8"
EXPECTED_UNCOMPRESSED_SIZE = 7090176

EXPECTED_COMPRESSED_SHA256 = "ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f"
EXPECTED_COMPRESSED_SIZE = 3920924


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(2 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main():
    start_time = time.time()
    print("=" * 80)
    print(" DRAGON QUEST XI (3DS) - MASTER FULL-GAME RECOMPILATION PIPELINE")
    print("=" * 80)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Reassemble Native Executable
    print("\n[Step 1/3] Assembling & Linking Native ARM Executable (code.bin)...")
    res1 = subprocess.run([sys.executable, str(PROJECT_ROOT / "tools" / "build.py")], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    if res1.returncode != 0:
        print(res1.stdout)
        sys.stderr.write(f"Error in build.py:\n{res1.stderr}\n")
        return 1

    actual_code_sha = sha256_file(BUILD_CODE_BIN)
    actual_code_comp_sha = sha256_file(BUILD_CODE_COMPRESSED)

    if actual_code_sha != EXPECTED_UNCOMPRESSED_SHA256:
        sys.stderr.write(f"Mismatch in code.bin! Expected {EXPECTED_UNCOMPRESSED_SHA256}, got {actual_code_sha}\n")
        return 2

    if actual_code_comp_sha != EXPECTED_COMPRESSED_SHA256:
        sys.stderr.write(f"Mismatch in compressed code! Expected {EXPECTED_COMPRESSED_SHA256}, got {actual_code_comp_sha}\n")
        return 3

    print(f"  [PASS] Uncompressed code.bin: 7,090,176 B | SHA-256: {actual_code_sha}")
    print(f"  [PASS] Compressed ExeFS .code: 3,920,924 B | SHA-256: {actual_code_comp_sha}")

    # Step 2: Repack Full Cartridge ROM (DQXI.3ds)
    print("\n[Step 2/3] Repacking Full 4 GB Cartridge ROM (DQXI.3ds)...")
    res2 = subprocess.run([sys.executable, str(PROJECT_ROOT / "tools" / "repack_rom.py"), str(PROJECT_ROOT / "original"), str(BUILD_ROM)], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    if res2.returncode != 0:
        print(res2.stdout)
        sys.stderr.write(f"Error in repack_rom.py:\n{res2.stderr}\n")
        return 4

    actual_rom_size = BUILD_ROM.stat().st_size
    actual_rom_sha = sha256_file(BUILD_ROM)

    if actual_rom_size != EXPECTED_ROM_SIZE:
        sys.stderr.write(f"ROM size mismatch! Expected {EXPECTED_ROM_SIZE}, got {actual_rom_size}\n")
        return 5

    if actual_rom_sha != EXPECTED_ROM_SHA256:
        sys.stderr.write(f"ROM hash mismatch! Expected {EXPECTED_ROM_SHA256}, got {actual_rom_sha}\n")
        return 6

    print(f"  [PASS] Cartridge ROM: 4,294,967,296 B | SHA-256: {actual_rom_sha}")

    # Step 3: Run Full Manifest Verification
    print("\n[Step 3/3] Executing Cryptographic Manifest Verification...")
    res3 = subprocess.run([sys.executable, str(PROJECT_ROOT / "tools" / "verify.py")], cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    if res3.returncode != 0:
        print(res3.stdout)
        sys.stderr.write(f"Error in verify.py:\n{res3.stderr}\n")
        return 7

    print("  [PASS] All 16 container partitions and repacked ROM verified.")

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f" FULL GAME RECOMPILATION COMPLETE - 100% BIT-MATCHING VERIFIED (Time: {elapsed:.1f}s)")
    print("=" * 80)
    print("Summary of Recompiled Game Artifacts:")
    print(f"  - Rebuilt ROM:      {BUILD_ROM} (4,294,967,296 bytes)")
    print(f"  - Executable:       {BUILD_CODE_BIN} (7,090,176 bytes)")
    print(f"  - ExeFS Code:       {BUILD_CODE_COMPRESSED} (3,920,924 bytes)")
    print(f"  - Difference Delta: Exactly 0 bytes (0 non-overlapping token violations)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
