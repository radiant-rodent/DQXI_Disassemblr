"""Binary-coded sweep of NPC ids: run j gives every NPC actor of the b002 levels an id whose pair-index has bit j set,
then walks out of the church and reads which cha models are in RAM. A model that appears in the runs with bits B
belongs to the pair whose index is B.  Usage: python npc_bits.py <run j | decode>"""
import json
import os
import struct
import sys

os.chdir(r'.')
sys.path.insert(0, '.')
import tools.level_records as lr
from tools.emu import level_probe as P

AREA = 'b002'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "out", "emu", "npc_bits")
os.makedirs(OUT, exist_ok=True)


def records(raw):
    L = lr.Level(bytes(raw))
    for arr in L.arrays.values():
        if arr.esize == 100 and arr.parent is not None and arr.parent.esize == 1092:
            base = arr.parent.block + arr.parent_index * arr.parent.esize
            if arr.desc - base == 0x1F0:
                for i in range(arr.count):
                    yield arr.block + i * 100


levels = sorted(d for d in os.listdir(P.LEVELS) if d.startswith(AREA + '_'))
raws = {lv: bytearray((P.LEVELS / lv / 'level3d.bxon').read_bytes()) for lv in levels}
pairs = set()
for lv, raw in raws.items():
    for b in records(raw):
        w = struct.unpack_from('<I', raw, b + 0x5C)[0]
        if (w >> 24) in (1, 2, 3):
            pairs.add(w)
pairs = sorted(pairs)
index = {p: i for i, p in enumerate(pairs)}
nbits = max(1, (len(pairs) - 1).bit_length())

if sys.argv[1] == 'info':
    print(len(pairs), 'pairs,', nbits, 'bits')
    sys.exit(0)

if sys.argv[1] == 'decode':
    runs = {}
    for j in range(nbits):
        f = os.path.join(OUT, f'run{j}.json')
        if os.path.exists(f):
            runs[j] = set(json.load(open(f)))
    base = set(json.load(open(os.path.join(OUT, 'base.json')))) if os.path.exists(os.path.join(OUT, 'base.json')) else set()
    allm = set().union(*runs.values()) - base
    table = {}
    for m in sorted(allm):
        i = sum(1 << j for j, s in runs.items() if m in s)
        table.setdefault(m, []).append(pairs[i] if i < len(pairs) else None)
    out = {f'0x{p:08X}': m for m, ps in table.items() for p in ps if p is not None}
    json.dump(out, open(os.path.join(OUT, 'table.json'), 'w'), indent=1)
    print(len(runs), 'runs;', len(out), 'ids resolved')
    sys.exit(0)

j = int(sys.argv[1])
group = [p for p in pairs if (index[p] >> j) & 1] if j >= 0 else [pairs[0]]
k = 0
out = {}
for lv, raw in raws.items():
    for b in records(raw):
        w = struct.unpack_from('<I', raw, b + 0x5C)[0]
        if (w >> 24) in (1, 2, 3):
            struct.pack_into('<I', raw, b + 0x5C, group[k % len(group)])
            k += 1
    out[lv] = bytes(raw)
name = f'npcbits_{j}' if j >= 0 else 'npcbits_base'
mod = P.build_mod(name, out)
actions = [('B', 3, 0.8)] * 6 + [('WALK:D', 1.5, 0.8)] * 4
rep = P.run_probe(name, mod, ram_regex=rb'cha\d{5}[a-z]?', actions=actions, save='user_heliodor')
names = rep.get('ram_names', [])
json.dump(names, open(os.path.join(OUT, f'run{j}.json' if j >= 0 else 'base.json'), 'w'))
print(j, len(names), names)
