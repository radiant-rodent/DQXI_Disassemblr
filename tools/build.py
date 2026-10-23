#!/usr/bin/env python3
"""tools/build.py - Automated Reassembly & Linking Pipeline for Dragon Quest XI (3DS)

Assembles modular assembly files (.s) and object files (.o) into the bit-matching
CTR executable:
1. Assembles modular sources from asm/ (start.s, init.s, text/*.s, rodata/*.s, data/*.s).
2. Applies CTR linker layout and page padding defined in sections.ld:
   - .text:   0x00100000 - 0x0072403C (6,438,972 B) + 4,036 B tail padding (to 0x00725000)
   - .rodata: 0x00725000 - 0x0079AA18 (481,816 B)   + 1,512 B tail padding (to 0x0079B000)
   - .data:   0x0079B000 - 0x007C2D24 (163,108 B)   +   732 B tail padding (to 0x007C3000)
   - .bss:    0x007C3000 - 0x00839BC0 (486,336 B in RAM)
3. Outputs build/code.bin (7,090,176 bytes, SHA-256: dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8).
4. Automatically runs tools/blz.py to generate build/code.compressed.bin
   (3,920,924 bytes, SHA-256: ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f).

Usage:
    python tools/build.py [options]
"""

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

# Keystone assembler engine
try:
    import keystone
    HAS_KEYSTONE = True
except ImportError:
    HAS_KEYSTONE = False

_TAG_REGEX = re.compile(r'/\*\s*0x[0-9a-fA-F]+:\s*([0-9a-fA-F]+)\s*\*/')

# Authoritative Baselines
EXPECTED_UNCOMPRESSED_SHA256 = "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8"
EXPECTED_UNCOMPRESSED_SIZE = 7090176  # 0x006C3000

EXPECTED_COMPRESSED_SHA256 = "ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f"
EXPECTED_COMPRESSED_SIZE = 3920924

# Memory Map Segments
TEXT_SIZE = 0x0062403C    # 6,438,972 B
TEXT_PAD = 4036           # 0x00000FC4
RODATA_SIZE = 0x00075A18  # 481,816 B
RODATA_PAD = 1512         # 0x000005E8
DATA_SIZE = 0x00027D24    # 163,108 B
DATA_PAD = 732            # 0x000002DC


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hex digest of in-memory bytes."""
    return hashlib.sha256(data).hexdigest()


def assemble_file(file_path: Path, current_pc: int = 0x100000, ks_arm=None, ks_thumb=None) -> bytes:
    """Parse and assemble a single .s file into binary bytes."""
    chunks = []
    mode = 'arm'

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str or line_str.startswith("//") or line_str.startswith("@"):
                continue

            # First priority: extract exact instruction hex tag if present
            m = _TAG_REGEX.search(line)
            if m:
                data = bytes.fromhex(m.group(1))
                chunks.append(data)
                current_pc += len(data)
                continue

            # Check mode directives
            if line_str.startswith(".arm") or line_str.startswith(".code 32"):
                mode = 'arm'
                continue
            if line_str.startswith(".thumb") or line_str.startswith(".code 16"):
                mode = 'thumb'
                continue
            if line_str.startswith(".syntax") or line_str.startswith(".section") or line_str.startswith(".global") or line_str.startswith(".type") or line_str.startswith(".thumb_func") or line_str.startswith(".balign"):
                continue

            # Check label
            if line_str.endswith(":"):
                continue

            # Strip comments
            clean = line_str.split("/*")[0].split("@")[0].strip()
            if not clean:
                continue

            # Data directives
            if clean.startswith(".word"):
                parts = clean[5:].split(",")
                for p in parts:
                    val = int(p.strip(), 0)
                    chunks.append(struct.pack("<I", val & 0xFFFFFFFF))
                    current_pc += 4
                continue
            if clean.startswith(".short"):
                parts = clean[6:].split(",")
                for p in parts:
                    val = int(p.strip(), 0)
                    chunks.append(struct.pack("<H", val & 0xFFFF))
                    current_pc += 2
                continue
            if clean.startswith(".byte"):
                parts = clean[5:].split(",")
                for p in parts:
                    val = int(p.strip(), 0)
                    chunks.append(struct.pack("<B", val & 0xFF))
                    current_pc += 1
                continue
            if clean.startswith(".space") or clean.startswith(".fill"):
                parts = clean.split()
                length = int(parts[1].rstrip(","), 0)
                fill_val = int(parts[2], 0) if len(parts) > 2 else 0
                chunks.append(bytes([fill_val]) * length)
                current_pc += length
                continue

            # Assemble instruction using Keystone if available
            ks = ks_thumb if mode == 'thumb' else ks_arm
            if ks:
                try:
                    encoding, _ = ks.asm(clean, current_pc)
                    enc_bytes = bytes(encoding)
                    chunks.append(enc_bytes)
                    current_pc += len(enc_bytes)
                except Exception as e:
                    print(f"Warning: Keystone assembly failed on '{clean}' in {file_path.name}: {e}", file=sys.stderr)
            else:
                print(f"Warning: Unhandled assembly line without tag in {file_path.name}: '{clean}'", file=sys.stderr)

    return b"".join(chunks)


def build_pipeline(asm_dir: Path, out_dir: Path, verbose: bool = False) -> bool:
    """Execute complete assembly, linking, padding, and BLZ compression pipeline."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tools_dir = Path(__file__).resolve().parent
    blz_script = tools_dir / "blz.py"

    print("=" * 80)
    print(" DRAGON QUEST XI (3DS) - REASSEMBLY & LINKING PIPELINE")
    print("=" * 80)
    print(f"Assembly Source Directory: '{asm_dir}'")
    print(f"Build Output Directory:   '{out_dir}'")

    # Initialize Keystone if available
    ks_arm = None
    ks_thumb = None
    if HAS_KEYSTONE:
        try:
            ks_arm = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
            ks_thumb = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
        except Exception as e:
            if verbose:
                print(f"Keystone init note: {e}")

    # Step 1: Assemble .text
    print("\n[1/4] Assembling .text sections...")
    text_chunks = []

    # Check for progressive C object file replacement (M2 <-> M3 contract).
    # A real ARMv6K C compile writes build/replacements/init.bin; the older
    # build/init.o raw-tail path is kept for compatibility.
    init_bin = out_dir / "replacements" / "init.bin"
    init_obj = out_dir / "init.o"
    if init_bin.is_file():
        print(f"  Using compiled C replacement '{init_bin.relative_to(out_dir)}'")
        init_bytes = init_bin.read_bytes()
    elif init_obj.is_file():
        # Read text section from compiled object file if present
        print(f"  Replacing asm/init.s with compiled C object '{init_obj.name}'")
        with open(init_obj, "rb") as f:
            obj_data = f.read()
        # In M3, InitBss is 24 bytes + 8 bytes literal pool
        init_bytes = obj_data[-36:] if len(obj_data) >= 36 else obj_data
    else:
        init_file = asm_dir / "init.s"
        init_bytes = assemble_file(init_file, 0x00100024, ks_arm, ks_thumb)

    start_file = asm_dir / "start.s"
    if not start_file.is_file():
        print(f"Error: required entry assembly '{start_file}' not found.", file=sys.stderr)
        return False

    text_chunks.append(assemble_file(start_file, 0x00100000, ks_arm, ks_thumb))
    text_chunks.append(init_bytes)

    # Modular text slices in asm/text/
    text_files = sorted((asm_dir / "text").glob("*.s"))
    if not text_files:
        print(f"Error: no modular assembly files found in '{asm_dir / 'text'}'.", file=sys.stderr)
        return False

    for tf in text_files:
        if verbose:
            print(f"  Assembling {tf.name}...")
        text_chunks.append(assemble_file(tf, 0x00100048, ks_arm, ks_thumb))

    text_bytes = bytearray(b"".join(text_chunks))
    # Overlay every verified C replacement at its original address.
    report_path = out_dir / "replacement_report.json"
    if report_path.is_file():
        for item in json.loads(report_path.read_text(encoding="utf-8")):
            if not item.get("ok") or not item.get("output"):
                continue
            addr = int(item["address"], 16)
            rel = Path(item["output"])
            data_path = rel if rel.is_absolute() else Path(__file__).resolve().parent.parent / rel
            data = data_path.read_bytes()
            off = addr - 0x00100000
            if off < 0 or off + len(data) > len(text_bytes):
                print(f"Error: replacement {item['name']} is outside .text", file=sys.stderr)
                return False
            text_bytes[off:off + len(data)] = data
    text_bytes = bytes(text_bytes)
    print(f"  Total .text assembled: {len(text_bytes):,} bytes (Target: {TEXT_SIZE:,})")
    if len(text_bytes) != TEXT_SIZE:
        print(f"Error: .text size mismatch: expected {TEXT_SIZE}, got {len(text_bytes)}.", file=sys.stderr)
        return False

    # Step 2: Assemble .rodata
    print("\n[2/4] Assembling .rodata sections...")
    rodata_chunks = []
    rodata_files = sorted((asm_dir / "rodata").glob("*.s"))
    for rf in rodata_files:
        rodata_chunks.append(assemble_file(rf, 0x00725000, ks_arm, ks_thumb))

    rodata_bytes = b"".join(rodata_chunks)
    print(f"  Total .rodata assembled: {len(rodata_bytes):,} bytes (Target: {RODATA_SIZE:,})")
    if len(rodata_bytes) != RODATA_SIZE:
        print(f"Error: .rodata size mismatch: expected {RODATA_SIZE}, got {len(rodata_bytes)}.", file=sys.stderr)
        return False

    # Step 3: Assemble .data
    print("\n[3/4] Assembling .data sections...")
    data_chunks = []
    data_files = sorted((asm_dir / "data").glob("*.s"))
    for df in data_files:
        data_chunks.append(assemble_file(df, 0x0079B000, ks_arm, ks_thumb))

    data_bytes = b"".join(data_chunks)
    print(f"  Total .data assembled: {len(data_bytes):,} bytes (Target: {DATA_SIZE:,})")
    if len(data_bytes) != DATA_SIZE:
        print(f"Error: .data size mismatch: expected {DATA_SIZE}, got {len(data_bytes)}.", file=sys.stderr)
        return False

    # Step 4: Link segments and apply sections.ld page padding
    print("\n[4/4] Linking executable image per sections.ld memory map...")
    text_pad_bytes = b"\x00" * TEXT_PAD
    rodata_pad_bytes = b"\x00" * RODATA_PAD
    data_pad_bytes = b"\x00" * DATA_PAD

    code_bin = (
        text_bytes
        + text_pad_bytes
        + rodata_bytes
        + rodata_pad_bytes
        + data_bytes
        + data_pad_bytes
    )

    out_code_bin = out_dir / "code.bin"
    with open(out_code_bin, "wb") as f:
        f.write(code_bin)

    bin_size = len(code_bin)
    bin_hash = sha256_bytes(code_bin)
    print(f"  Generated '{out_code_bin.name}' ({bin_size:,} bytes)")
    print(f"  SHA-256: {bin_hash}")

    if bin_size != EXPECTED_UNCOMPRESSED_SIZE:
        print(f"Error: code.bin size mismatch: expected {EXPECTED_UNCOMPRESSED_SIZE}, got {bin_size}.", file=sys.stderr)
        return False

    if bin_hash.lower() != EXPECTED_UNCOMPRESSED_SHA256.lower():
        print(f"Error: code.bin SHA-256 mismatch!\n  Expected: {EXPECTED_UNCOMPRESSED_SHA256}\n  Got:      {bin_hash}", file=sys.stderr)
        return False

    print("  [PASS] Reconstructed code.bin bit-matches original uncompressed code.bin (0 differences)!")

    # Step 5: Automatically run CTR-SDK BLZ compression
    out_compressed_bin = out_dir / "code.compressed.bin"
    print(f"\nCompressing via CTR-SDK BLZ engine ('{out_compressed_bin.name}')...")

    if not blz_script.is_file():
        print(f"Error: BLZ compressor '{blz_script}' not found.", file=sys.stderr)
        return False

    res = subprocess.run(
        [sys.executable, str(blz_script), "-c", str(out_code_bin), str(out_compressed_bin)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"Error in BLZ compression:\n{res.stderr}", file=sys.stderr)
        return False

    compressed_size = os.path.getsize(out_compressed_bin)
    compressed_hash = sha256_file(out_compressed_bin)
    print(f"  Generated '{out_compressed_bin.name}' ({compressed_size:,} bytes)")
    print(f"  SHA-256: {compressed_hash}")

    if compressed_size != EXPECTED_COMPRESSED_SIZE:
        print(f"Error: compressed code size mismatch: expected {EXPECTED_COMPRESSED_SIZE}, got {compressed_size}.", file=sys.stderr)
        return False

    if compressed_hash.lower() != EXPECTED_COMPRESSED_SHA256.lower():
        print(f"Error: compressed code SHA-256 mismatch!\n  Expected: {EXPECTED_COMPRESSED_SHA256}\n  Got:      {compressed_hash}", file=sys.stderr)
        return False

    print("  [PASS] Reconstructed ExeFS .code bit-matches original compressed .code (0 differences)!")

    print("-" * 80)
    print("ALL ARTIFACTS VERIFIED SUCCESSFULLY (Exit Code 0)")
    print("-" * 80)
    return True


def clean_artifacts(out_dir: Path):
    """Remove built binaries."""
    for name in ["code.bin", "code.compressed.bin"]:
        p = out_dir / name
        if p.is_file():
            p.unlink()
            print(f"Removed '{p}'")


def verify_existing(out_dir: Path) -> bool:
    """Verify hashes of pre-existing build binaries."""
    code_bin = out_dir / "code.bin"
    comp_bin = out_dir / "code.compressed.bin"

    if not code_bin.is_file() or not comp_bin.is_file():
        print("Error: Build artifacts missing.", file=sys.stderr)
        return False

    h1 = sha256_file(code_bin)
    h2 = sha256_file(comp_bin)

    ok1 = (h1.lower() == EXPECTED_UNCOMPRESSED_SHA256.lower())
    ok2 = (h2.lower() == EXPECTED_COMPRESSED_SHA256.lower())

    print(f"code.bin:            {'PASS' if ok1 else 'FAIL'} ({h1})")
    print(f"code.compressed.bin: {'PASS' if ok2 else 'FAIL'} ({h2})")
    return ok1 and ok2


def main():
    parser = argparse.ArgumentParser(
        description="Automated Reassembly & Linking Pipeline for Dragon Quest XI (3DS)."
    )
    parser.add_argument(
        "--asm-dir",
        default="asm",
        help="Path to assembly source directory (default: asm)",
    )
    parser.add_argument(
        "--out-dir",
        default="build",
        help="Path to build output directory (default: build)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove build artifacts and exit",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify pre-existing build artifacts without rebuilding",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose assembly output",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    asm_dir = (project_root / args.asm_dir).resolve()
    out_dir = (project_root / args.out_dir).resolve()

    if args.clean:
        clean_artifacts(out_dir)
        sys.exit(0)

    if args.verify:
        success = verify_existing(out_dir)
        sys.exit(0 if success else 1)

    success = build_pipeline(asm_dir, out_dir, verbose=args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
