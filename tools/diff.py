#!/usr/bin/env python3
"""tools/diff.py - Visual Bytecode and Disassembly Diff Tool for Dragon Quest XI (3DS)

Compares reconstructed executable code against the original baseline:
- Supports symbol lookup (e.g. InitBss, InitHeaps) or hex virtual addresses (0x00100024).
- Disassembles matching and diverging instructions using Capstone.
- Highlights identical instructions (Green), discrepancies (Red), and relocations (Yellow).
- Computes exact match percentages and byte offsets.

Usage:
    python tools/diff.py [options] [target_symbol_or_address]
"""

import argparse
import json
import os
import struct
import sys
from pathlib import Path

try:
    import capstone
    HAS_CAPSTONE = True
except ImportError:
    HAS_CAPSTONE = False

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_CODE = PROJECT_ROOT / "build" / "code.bin"
ORIGINAL_CODE = PROJECT_ROOT / "original" / "exefs" / "code.decompressed.bin"
SYMBOLS_FILE = PROJECT_ROOT / "symbols.json"

TEXT_START = 0x00100000
TEXT_END = 0x0072403C

# Known default symbols if symbols.json is missing
DEFAULT_SYMBOLS = {
    "initbss": (0x00100024, 36, "arm"),
    "initheaps": (0x00102EF8, 0x100, "arm"),
    "heapalloc": (0x0055E928, 0x80, "arm"),
    "heapfree": (0x0055E808, 0x80, "arm"),
    "smallblockalloc": (0x006F1C9C, 0x100, "arm"),
}


def load_symbol_table():
    symbols = dict(DEFAULT_SYMBOLS)
    if SYMBOLS_FILE.is_file():
        try:
            with open(SYMBOLS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for s in data.get("symbols", []):
                    name = s["name"].lower()
                    addr = int(s["address"], 16)
                    size = s.get("size", 64)
                    mode = s.get("mode", "arm")
                    symbols[name] = (addr, size, mode)
        except Exception:
            pass
    return symbols


def format_match_line(addr: int, orig_bytes: bytes, built_bytes: bytes, orig_disasm: str, built_disasm: str, is_match: bool) -> str:
    if not HAS_COLORAMA:
        status = "[MATCH]" if is_match else "[DIFF]"
        return f"{addr:08X}: {status:7s} | {orig_bytes.hex():8s} {orig_disasm:30s} | {built_bytes.hex():8s} {built_disasm}"

    if is_match:
        tag = f"{Fore.GREEN}[MATCH]{Style.RESET_ALL}"
        body = f"{orig_bytes.hex():8s}  {orig_disasm}"
        return f"  0x{addr:08X}: {tag}  {body}"
    else:
        tag = f"{Fore.RED}[DIFF]{Style.RESET_ALL}"
        return (
            f"  0x{addr:08X}: {tag}\n"
            f"    {Fore.RED}- Orig:  {orig_bytes.hex():8s}  {orig_disasm}{Style.RESET_ALL}\n"
            f"    {Fore.YELLOW}+ Built: {built_bytes.hex():8s}  {built_disasm}{Style.RESET_ALL}"
        )


def diff_range(orig_slice: bytes, built_slice: bytes, base_addr: int, mode: str = "arm") -> tuple[int, int, float, list[str]]:
    total = max(len(orig_slice), len(built_slice)) // 4
    if total == 0:
        return 0, 0, 100.0, []

    matched = 0
    lines = []

    cs_mode = capstone.CS_MODE_THUMB if mode == "thumb" else capstone.CS_MODE_ARM
    md = capstone.Cs(capstone.CS_ARCH_ARM, cs_mode) if HAS_CAPSTONE else None

    step = 2 if mode == "thumb" else 4
    limit = min(len(orig_slice), len(built_slice))
    total_steps = max(len(orig_slice), len(built_slice)) // step

    for offset in range(0, limit, step):
        addr = base_addr + offset
        ob = orig_slice[offset:offset+step]
        bb = built_slice[offset:offset+step]

        is_match = (ob == bb)
        if is_match:
            matched += 1

        orig_str = ""
        built_str = ""
        if md:
            orig_insns = list(md.disasm(ob, addr))
            orig_str = f"{orig_insns[0].mnemonic:8s} {orig_insns[0].op_str}" if orig_insns else f".word 0x{struct.unpack('<I', ob)[0]:08X}"
            built_insns = list(md.disasm(bb, addr))
            built_str = f"{built_insns[0].mnemonic:8s} {built_insns[0].op_str}" if built_insns else f".word 0x{struct.unpack('<I', bb)[0]:08X}"

        lines.append(format_match_line(addr, ob, bb, orig_str, built_str, is_match))

    pct = (matched / total_steps) * 100.0 if total_steps > 0 else 0.0
    return matched, total_steps, pct, lines


def main():
    parser = argparse.ArgumentParser(description="Dragon Quest XI 3DS Visual Bytecode Diff Tool")
    parser.add_argument("target", nargs="?", default="InitBss", help="Target symbol name or hex virtual address (e.g. InitBss, 0x00100024)")
    parser.add_argument("--len", "-l", type=lambda x: int(x, 0), default=None, help="Length in bytes to inspect")
    parser.add_argument("--mode", "-m", choices=["arm", "thumb"], default="arm", help="Disassembly mode (arm or thumb)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON summary")

    args = parser.parse_args()

    symbols = load_symbol_table()
    target_lower = args.target.lower()

    if target_lower in symbols:
        addr, default_len, mode = symbols[target_lower]
        length = args.len or default_len
    elif args.target.startswith("0x") or args.target.startswith("0X"):
        try:
            addr = int(args.target, 16)
            length = args.len or 64
            mode = args.mode
        except ValueError:
            sys.stderr.write(f"Error: Invalid hexadecimal address '{args.target}'\n")
            return 1
    else:
        sys.stderr.write(f"Error: Unknown symbol or invalid address '{args.target}'\n")
        return 2

    if addr < TEXT_START or addr >= 0x00839BC0:
        sys.stderr.write(f"Error: Address 0x{addr:08X} outside executable virtual range (0x{TEXT_START:08X}-0x00839BC0)\n")
        return 3

    if not ORIGINAL_CODE.is_file():
        sys.stderr.write(f"Error: Original decompressed executable not found at '{ORIGINAL_CODE}'\n")
        return 4

    if not BUILD_CODE.is_file():
        sys.stderr.write(f"Error: Reconstructed executable not found at '{BUILD_CODE}'. Run python tools/build.py first.\n")
        return 5

    file_offset = addr - TEXT_START
    with open(ORIGINAL_CODE, "rb") as f:
        f.seek(file_offset)
        orig_bytes = f.read(length)

    with open(BUILD_CODE, "rb") as f:
        f.seek(file_offset)
        built_bytes = f.read(length)

    matched, total, pct, lines = diff_range(orig_bytes, built_bytes, addr, mode)

    if args.json:
        result = {
            "target": args.target,
            "address": f"0x{addr:08X}",
            "length": length,
            "matched_instructions": matched,
            "total_instructions": total,
            "match_percentage": round(pct, 2),
            "bit_identical": (matched == total),
        }
        print(json.dumps(result, indent=2))
        return 0

    print("=" * 72)
    print(f" BYTECODE DIFF: {args.target} (0x{addr:08X}, length: {length} bytes)")
    print("=" * 72)
    for line in lines:
        print(line)
    print("-" * 72)
    status_str = "BIT-IDENTICAL MATCH" if (matched == total) else "DIFF DETECTED"
    print(f" Result: {status_str} ({matched}/{total} instructions, {pct:.1f}%)")
    print("=" * 72)

    return 0 if (matched == total) else 1


if __name__ == "__main__":
    sys.exit(main())
