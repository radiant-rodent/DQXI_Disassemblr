#!/usr/bin/env python3
"""tools/disasm.py - Modular Disassembly Pipeline for Dragon Quest XI (3DS, CTR-P-BTZJ)

Disassembles the uncompressed CTR executable (code.bin / code.decompressed.bin)
into modular, relocatable GNU ARM assembly files:
- asm/start.s: Entry vector and reset jump table (0x00100000 - 0x00100024)
- asm/init.s: CRT runtime and InitBss (0x00100024 - 0x00100048)
- asm/text/: Modular slices of .text (0x00100048 - 0x0072403C)
- asm/rodata/: Modular slices of .rodata (0x00725000 - 0x0079AA18)
- asm/data/: Modular slices of .data (0x0079B000 - 0x007C2D24)
- asm/bss.s: BSS section allocation (0x007C3000 - 0x00839BC0)

Preserves ARM/Thumb modes (.arm, .thumb, .thumb_func), literal pools,
and instruction boundaries.

Usage:
    python tools/disasm.py [input_bin] [output_asm_dir]
"""

import argparse
import os
import struct
import sys
from pathlib import Path

try:
    import capstone
    HAS_CAPSTONE = True
except ImportError:
    HAS_CAPSTONE = False

# Memory Map Constants
TEXT_START = 0x00100000
TEXT_END = 0x0072403C
TEXT_SIZE = TEXT_END - TEXT_START  # 0x0062403C = 6,438,972 B
TEXT_PAGE_END = 0x00725000

RODATA_START = 0x00725000
RODATA_END = 0x0079AA18
RODATA_SIZE = RODATA_END - RODATA_START  # 0x00075A18 = 481,816 B
RODATA_PAGE_END = 0x0079B000

DATA_START = 0x0079B000
DATA_END = 0x007C2D24
DATA_SIZE = DATA_END - DATA_START  # 0x00027D24 = 163,108 B
DATA_PAGE_END = 0x007C3000

BSS_START = 0x007C3000
BSS_END = 0x00839BC0
BSS_SIZE = BSS_END - BSS_START  # 0x00076BC0 = 486,336 B

TOTAL_DECOMPRESSED_SIZE = 7090176  # 0x006C3000


def collect_known_modes_and_pools(data: bytes):
    """Scan data and rodata for function pointers and literal pools to identify ARM vs Thumb regions."""
    modes = {}  # addr -> 'arm' | 'thumb'
    literal_pools = set()

    # Rodata and Data slices in binary
    rodata_offset = 0x625000
    data_offset = 0x69B000

    # Pointers in rodata and data
    for off in range(rodata_offset, 0x6C2D24 - 3, 4):
        val = struct.unpack('<I', data[off:off+4])[0]
        addr = val & ~1
        if TEXT_START <= addr < TEXT_END:
            modes[addr] = 'thumb' if (val & 1) else 'arm'

    # Known CRT vectors
    modes[0x00100000] = 'arm'
    modes[0x00100024] = 'arm'
    modes[0x00100048] = 'arm'
    modes[0x00100050] = 'thumb'

    # Pre-scan ARM text for literal pools (ldr rN, [pc, #imm]) and ARM blx to Thumb
    text = data[:TEXT_SIZE]
    for off in range(0, len(text) - 3, 4):
        w = struct.unpack('<I', text[off:off+4])[0]
        pc = TEXT_START + off

        # ARM blx <imm> (opcode prefix 0xFA......)
        if (w & 0xFE000000) == 0xFA000000:
            imm24 = w & 0x00FFFFFF
            if imm24 & 0x00800000:
                imm24 -= 0x01000000
            h = (w >> 24) & 1
            target = pc + 8 + (imm24 << 2) + (h << 1)
            if TEXT_START <= target < TEXT_END:
                modes[target] = 'thumb'

        # ARM ldr rN, [pc, #imm]: (cond) 0101 1001 1111 (rt) (imm12)
        # Check ldr with positive offset from PC
        if (w & 0x0F7F0000) == 0x059F0000:
            u_bit = (w >> 23) & 1
            imm12 = w & 0x0FFF
            target = (pc + 8 + imm12) if u_bit else (pc + 8 - imm12)
            if TEXT_START <= target < TEXT_END:
                literal_pools.add(target)

    # Specific known literal pools in CRT startup
    literal_pools.add(0x00100040)
    literal_pools.add(0x00100044)

    return modes, literal_pools


def disassemble_text_slice(text_slice: bytes, start_addr: int, modes: dict, literal_pools: set, cs_arm, cs_thumb):
    """Disassemble a contiguous slice of .text machine code into assembly lines."""
    lines = []
    off = 0
    pc = start_addr
    slice_len = len(text_slice)
    current_mode = modes.get(pc, 'arm')

    while off < slice_len:
        addr = pc

        # Check if known symbol entry updates mode
        if addr in modes:
            new_mode = modes[addr]
            if new_mode != current_mode:
                current_mode = new_mode
                lines.append(f"    .{current_mode}")
                if current_mode == 'thumb':
                    lines.append("    .thumb_func")

        # Check literal pool hit
        if addr in literal_pools and off + 4 <= slice_len:
            val = struct.unpack('<I', text_slice[off:off+4])[0]
            hex_str = text_slice[off:off+4].hex()
            lines.append(f"    /* 0x{addr:08X}: {hex_str} */  .word   0x{val:08X}")
            off += 4
            pc += 4
            continue

        if current_mode == 'arm':
            # Check 4-byte boundary
            chunk = text_slice[off:off+4]
            if len(chunk) < 4:
                # Trailing bytes
                for b in chunk:
                    lines.append(f"    /* 0x{pc:08X}: {b:02x} */  .byte   0x{b:02X}")
                    off += 1
                    pc += 1
                break

            # Check inline state toggle: add ip, pc, #1; bx ip
            if chunk == bytes.fromhex('01c08fe2') and off + 8 <= slice_len and text_slice[off+4:off+8] == bytes.fromhex('1cff2fe1'):
                lines.append(f"    /* 0x{addr:08X}: 01c08fe2 */  add     ip, pc, #1")
                lines.append(f"    /* 0x{addr+4:08X}: 1cff2fe1 */  bx      ip")
                off += 8
                pc += 8
                current_mode = 'thumb'
                lines.append("    .thumb")
                lines.append("    .thumb_func")
                continue

            # Try ARM disassembly
            instrs = list(cs_arm.disasm_lite(chunk, addr)) if cs_arm else []
            if instrs:
                _, size, mnem, op_str = instrs[0]
                lines.append(f"    /* 0x{addr:08X}: {chunk.hex()} */  {mnem:<8} {op_str}")
                off += size
                pc += size
            else:
                # If ARM fails, try Thumb if aligned
                t_instrs = list(cs_thumb.disasm_lite(chunk, addr)) if cs_thumb else []
                if t_instrs:
                    current_mode = 'thumb'
                    lines.append("    .thumb")
                    lines.append("    .thumb_func")
                    _, size, mnem, op_str = t_instrs[0]
                    sz_bytes = text_slice[off:off+size]
                    lines.append(f"    /* 0x{addr:08X}: {sz_bytes.hex()} */  {mnem:<8} {op_str}")
                    off += size
                    pc += size
                else:
                    # Raw data word
                    val = struct.unpack('<I', chunk)[0]
                    lines.append(f"    /* 0x{addr:08X}: {chunk.hex()} */  .word   0x{val:08X}")
                    off += 4
                    pc += 4
        else:
            # Thumb mode
            chunk = text_slice[off:off+4]
            if len(chunk) < 2:
                for b in chunk:
                    lines.append(f"    /* 0x{pc:08X}: {b:02x} */  .byte   0x{b:02X}")
                    off += 1
                    pc += 1
                break

            instrs = list(cs_thumb.disasm_lite(chunk, addr)) if cs_thumb else []
            if instrs:
                _, size, mnem, op_str = instrs[0]
                sz_bytes = text_slice[off:off+size]
                lines.append(f"    /* 0x{addr:08X}: {sz_bytes.hex()} */  {mnem:<8} {op_str}")
                off += size
                pc += size
            else:
                # Check if 4-byte aligned and maybe ARM
                if (addr % 4 == 0) and len(chunk) >= 4:
                    arm_try = list(cs_arm.disasm_lite(chunk, addr)) if cs_arm else []
                    if arm_try:
                        current_mode = 'arm'
                        lines.append("    .arm")
                        _, size, mnem, op_str = arm_try[0]
                        lines.append(f"    /* 0x{addr:08X}: {chunk.hex()} */  {mnem:<8} {op_str}")
                        off += size
                        pc += size
                        continue

                # 2-byte data / padding
                chunk2 = text_slice[off:off+2]
                val = struct.unpack('<H', chunk2)[0]
                lines.append(f"    /* 0x{addr:08X}: {chunk2.hex()} */  .short  0x{val:04X}")
                off += 2
                pc += 2

    return lines


def format_data_section(raw_data: bytes, base_addr: int, section_name: str):
    """Format raw rodata or data section into structured .word directives."""
    lines = [
        f"    .syntax unified",
        f"    .section {section_name}",
        f"    .balign 4",
        "",
    ]
    off = 0
    total = len(raw_data)

    while off < total:
        addr = base_addr + off
        rem = total - off
        if rem >= 4:
            chunk = raw_data[off:off+4]
            val = struct.unpack('<I', chunk)[0]
            lines.append(f"    /* 0x{addr:08X}: {chunk.hex()} */  .word   0x{val:08X}")
            off += 4
        elif rem >= 2:
            chunk = raw_data[off:off+2]
            val = struct.unpack('<H', chunk)[0]
            lines.append(f"    /* 0x{addr:08X}: {chunk.hex()} */  .short  0x{val:04X}")
            off += 2
        else:
            b = raw_data[off]
            lines.append(f"    /* 0x{addr:08X}: {b:02x} */  .byte   0x{b:02X}")
            off += 1

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Disassemble Dragon Quest XI 3DS executable into modular assembly files."
    )
    parser.add_argument(
        "input_bin",
        nargs="?",
        default="original/exefs/code.decompressed.bin",
        help="Path to input decompressed code.bin (default: original/exefs/code.decompressed.bin)",
    )
    parser.add_argument(
        "output_asm_dir",
        nargs="?",
        default="asm",
        help="Path to output assembly directory (default: asm)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose disassembly logs",
    )
    args = parser.parse_args()

    # Validate input exists
    input_path = Path(args.input_bin).resolve()
    if not input_path.is_file():
        print(f"Error: input file '{args.input_bin}' does not exist.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_asm_dir).resolve()
    asm_text_dir = out_dir / "text"
    asm_rodata_dir = out_dir / "rodata"
    asm_data_dir = out_dir / "data"

    asm_text_dir.mkdir(parents=True, exist_ok=True)
    asm_rodata_dir.mkdir(parents=True, exist_ok=True)
    asm_data_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "rb") as f:
        data = f.read()

    if len(data) < TOTAL_DECOMPRESSED_SIZE:
        print(
            f"Error: input file '{input_path}' is {len(data)} bytes, expected at least {TOTAL_DECOMPRESSED_SIZE}.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Loaded '{input_path.name}' ({len(data):,} bytes)")
    print(f"Target assembly directory: '{out_dir}'")

    # Initialize Capstone engines
    cs_arm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM) if HAS_CAPSTONE else None
    cs_thumb = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB) if HAS_CAPSTONE else None

    # Step 1: Mode & Literal Pool Discovery
    print("Scanning symbol modes and literal pool boundaries...")
    modes, literal_pools = collect_known_modes_and_pools(data)
    print(f"  Identified {len(modes):,} symbol entry modes, {len(literal_pools):,} literal pool references.")

    # Step 2: asm/start.s (Reset vectors: 0x00100000 - 0x00100024)
    start_bytes = data[0x0:0x24]
    start_lines = [
        "    .syntax unified",
        "    .arm",
        "    .section .text.startup, \"ax\", %progbits",
        "    .global _start",
        "    .type _start, %function",
        "_start:",
    ]
    start_lines.extend(disassemble_text_slice(start_bytes, TEXT_START, modes, literal_pools, cs_arm, cs_thumb))
    start_file = out_dir / "start.s"
    with open(start_file, "w", encoding="utf-8") as f:
        f.write("\n".join(start_lines) + "\n")
    print(f"Generated '{start_file.relative_to(out_dir.parent)}'")

    # Step 3: asm/init.s (CRT InitBss: 0x00100024 - 0x00100048)
    init_bytes = data[0x24:0x48]
    init_lines = [
        "    .syntax unified",
        "    .arm",
        "    .section .text.init, \"ax\", %progbits",
        "    .global InitBss",
        "    .type InitBss, %function",
        "InitBss:",
    ]
    init_lines.extend(disassemble_text_slice(init_bytes, 0x00100024, modes, literal_pools, cs_arm, cs_thumb))
    init_file = out_dir / "init.s"
    with open(init_file, "w", encoding="utf-8") as f:
        f.write("\n".join(init_lines) + "\n")
    print(f"Generated '{init_file.relative_to(out_dir.parent)}'")

    # Step 4: asm/text/ modular slices (0x00100048 - 0x0072403C)
    text_data = data[0x48:TEXT_SIZE]
    slice_size = 0x40000  # 256 KB per slice
    curr_addr = 0x00100048
    slice_idx = 0

    while curr_addr < TEXT_END:
        end_addr = min(curr_addr + slice_size, TEXT_END)
        # Align end_addr to 4 bytes except last slice
        if end_addr != TEXT_END:
            end_addr = (end_addr // 4) * 4

        slice_start_off = curr_addr - TEXT_START
        slice_end_off = end_addr - TEXT_START
        curr_bytes = data[slice_start_off:slice_end_off]

        slice_name = f"text_{curr_addr:08X}.s"
        slice_file = asm_text_dir / slice_name

        s_lines = [
            f"    /* Section: .text, Range: 0x{curr_addr:08X} - 0x{end_addr:08X} */",
            f"    .syntax unified",
            f"    .section .text",
            f"    .balign 4",
            "",
            f"loc_{curr_addr:08X}:",
        ]
        s_lines.extend(disassemble_text_slice(curr_bytes, curr_addr, modes, literal_pools, cs_arm, cs_thumb))

        with open(slice_file, "w", encoding="utf-8") as f:
            f.write("\n".join(s_lines) + "\n")

        slice_idx += 1
        curr_addr = end_addr

    print(f"Generated {slice_idx} modular .text files in '{asm_text_dir.relative_to(out_dir.parent)}'")

    # Step 5: asm/rodata/ modular slices (0x00725000 - 0x0079AA18)
    rodata_slice_size = 0x20000  # 128 KB
    curr_addr = RODATA_START
    rodata_idx = 0

    while curr_addr < RODATA_END:
        end_addr = min(curr_addr + rodata_slice_size, RODATA_END)
        slice_start_off = 0x625000 + (curr_addr - RODATA_START)
        slice_end_off = 0x625000 + (end_addr - RODATA_START)
        curr_bytes = data[slice_start_off:slice_end_off]

        rodata_name = f"rodata_{curr_addr:08X}.s"
        rodata_file = asm_rodata_dir / rodata_name

        content = format_data_section(curr_bytes, curr_addr, ".rodata")
        with open(rodata_file, "w", encoding="utf-8") as f:
            f.write(content)

        rodata_idx += 1
        curr_addr = end_addr

    print(f"Generated {rodata_idx} modular .rodata files in '{asm_rodata_dir.relative_to(out_dir.parent)}'")

    # Step 6: asm/data/ modular slices (0x0079B000 - 0x007C2D24)
    data_slice_size = 0x10000  # 64 KB
    curr_addr = DATA_START
    data_idx = 0

    while curr_addr < DATA_END:
        end_addr = min(curr_addr + data_slice_size, DATA_END)
        slice_start_off = 0x69B000 + (curr_addr - DATA_START)
        slice_end_off = 0x69B000 + (end_addr - DATA_START)
        curr_bytes = data[slice_start_off:slice_end_off]

        data_name = f"data_{curr_addr:08X}.s"
        data_file = asm_data_dir / data_name

        content = format_data_section(curr_bytes, curr_addr, ".data")
        with open(data_file, "w", encoding="utf-8") as f:
            f.write(content)

        data_idx += 1
        curr_addr = end_addr

    print(f"Generated {data_idx} modular .data files in '{asm_data_dir.relative_to(out_dir.parent)}'")

    # Step 7: asm/bss.s (BSS allocation in RAM: 0x007C3000 - 0x00839BC0)
    bss_file = out_dir / "bss.s"
    bss_content = (
        "    /* Section: .bss (NOLOAD in RAM) */\n"
        "    .section .bss\n"
        "    .balign 4\n"
        "    .global __bss_start__\n"
        "    .global __bss_end__\n"
        f"    .space 0x{BSS_SIZE:06X}  /* {BSS_SIZE:,} bytes */\n"
    )
    with open(bss_file, "w", encoding="utf-8") as f:
        f.write(bss_content)
    print(f"Generated '{bss_file.relative_to(out_dir.parent)}'")

    print("\nDisassembly complete successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
