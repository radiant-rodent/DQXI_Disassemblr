import struct
from pathlib import Path

CODE_BIN = Path("original/exefs/code.decompressed.bin")
with open(CODE_BIN, "rb") as f:
    data = f.read()

TEXT_START = 0x00100000

# Look around 0x00248000 to 0x00260000
# Search for pointers to strings in this range
found_bindings = []

# Scan memory for pairs of (char* name, void* func_ptr)
for off in range(0, len(data) - 16, 4):
    vaddr = TEXT_START + off
    p_name, p_func = struct.unpack("<II", data[off:off+8])
    if TEXT_START <= p_name < TEXT_START + len(data) and TEXT_START <= p_func < TEXT_START + len(data):
        # Check if p_name points to a printable null-terminated C string
        name_off = p_name - TEXT_START
        # Check string
        s_bytes = bytearray()
        i = name_off
        while i < len(data) and data[i] != 0 and len(s_bytes) < 64:
            if 0x20 <= data[i] <= 0x7E:
                s_bytes.append(data[i])
            else:
                break
            i += 1
        if len(s_bytes) >= 4 and i < len(data) and data[i] == 0:
            name = s_bytes.decode('ascii')
            # Check if func_ptr is code (odd or 4-byte aligned)
            target = p_func & ~1
            if TEXT_START <= target < 0x0072403C:
                found_bindings.append((vaddr, name, p_func, target))

print(f"Found {len(found_bindings)} potential native function / string bindings!")
for b in found_bindings[:40]:
    print(f"  Table entry at 0x{b[0]:08X}: '{b[1]}' -> Func at 0x{b[3]:08X} (mode: {'thumb' if b[2]&1 else 'arm'})")
