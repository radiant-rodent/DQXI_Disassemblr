from pathlib import Path
import struct
import json

data = Path("original/exefs/code.decompressed.bin").read_bytes()
TEXT_START = 0x00100000

# Let's inspect the block from 0x00249000 to 0x00255000
# Notice that each entry has:
# 4 bytes: Function pointer (0x0014xxxx - 0x0017xxxx, or 0x006xxxxx)
# N bytes: Null-terminated ASCII string (the function name)
# padding to 4 bytes

results = {}

off = 0x00249E00 - TEXT_START
end_off = 0x00255000 - TEXT_START

i = off
while i < end_off - 8:
    w = struct.unpack("<I", data[i:i+4])[0]
    # Check if w looks like a code pointer in text
    target = w & ~1
    if 0x00100000 <= target <= 0x0072403C:
        # Check if immediately followed by an ASCII string
        s_bytes = bytearray()
        j = i + 4
        while j < end_off and 0x20 <= data[j] <= 0x7E and len(s_bytes) < 64:
            s_bytes.append(data[j])
            j += 1
        if len(s_bytes) >= 3 and j < end_off and data[j] == 0:
            name = s_bytes.decode('ascii')
            # Check valid identifier
            if name.isidentifier():
                results[target] = name
                # Advance i to j + 1 aligned to 4
                rem = (j + 1) % 4
                i = (j + 1) + ((4 - rem) if rem != 0 else 0)
                continue
    i += 4

print(f"Extracted {len(results)} exact native function names from registration table!")
for addr in sorted(results.keys())[:50]:
    print(f"  0x{addr:08X} -> {results[addr]}")

with open("symbols_recovered.json", "w", encoding="utf-8") as f:
    json.dump({f"0x{k:08X}": v for k, v in results.items()}, f, indent=2)
