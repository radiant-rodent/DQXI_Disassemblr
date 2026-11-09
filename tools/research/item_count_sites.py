"""List every code.bin literal 0xB3B (item count, 2875) and the function that loads it.

Usage: python tools/research/item_count_sites.py .   (findings: orchestration/done/X6_item_table_growth.md)
"""
import json, struct, bisect, sys
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
root = sys.argv[1] if len(sys.argv) > 1 else '.'
code = open(root + '/original/exefs/code.decompressed.bin', 'rb').read()
BASE = 0x100000
syms = sorted((int(s['address'], 16), s['name'], s.get('size', 0)) for s in json.load(open(root + '/symbols.json', encoding='utf-8'))['symbols'] if s.get('type') == 'function')
addrs = [a for a, _, _ in syms]
def func(a):
    i = bisect.bisect_right(addrs, a) - 1
    return syms[i][1] if i >= 0 else '?'
md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
lits = [BASE + o for o in range(0, len(code) - 3, 4) if struct.unpack_from('<I', code, o)[0] in (0xB3B,)]
print(len(lits), 'literal words')
for L in lits:
    users = []
    for A in range(max(BASE, L - 4096), L, 4):
        w = struct.unpack_from('<I', code, A - BASE)[0]
        # LDR Rt,[PC,#+-imm12]  cond 0101 U001 1111 Rt imm12
        if (w & 0x0F7F0000) == 0x051F0000:
            imm = w & 0xFFF
            tgt = A + 8 + (imm if w & 0x00800000 else -imm)
            if tgt == L:
                users.append(A)
    for A in users:
        ins = list(md.disasm(code[A - BASE:A - BASE + 40], A))
        txt = ' ; '.join(f'{i.mnemonic} {i.op_str}' for i in ins[:8])
        print(f'{L:#x} <- {A:#x} {func(A)}: {txt}')
    if not users:
        print(f'{L:#x} no ARM pc-load ({func(L)})')
