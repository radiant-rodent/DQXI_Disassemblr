#!/usr/bin/env python3
"""Profile every array kind of every level3d.bxon: which container field (offset), element size, how many
levels and records use it, and a per-word guess (float / int / flags) with value ranges.

Used to decode what the records mean (docs/LEVEL_FORMAT.md). Writes build/level_kind_profiles.md.

    python tools/level_inventory.py
"""
import collections
import json
import math
import os
import struct
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, '.')
import tools.level_records as lr

root = 'game_data/packs/level3d'
levels = sorted(d for d in os.listdir(root) if os.path.isfile(f'{root}/{d}/level3d.bxon'))


def kind_key(arr):
    chain = []
    a = arr
    while a is not None:
        chain.append(a)
        a = a.parent
    out = []
    for a in reversed(chain):
        if a.parent is None:
            out.append('root')
        else:
            base = a.parent.block + a.parent_index * a.parent.esize
            out.append(f'+{a.desc - base:X}')
    return '/'.join(out) + f'[{arr.esize}]'


# per kind: per word offset -> list of values (sampled)
words = collections.defaultdict(lambda: collections.defaultdict(list))
ptr_words = collections.defaultdict(lambda: collections.defaultdict(int))
counts = collections.Counter()
examples = {}
for lv in levels:
    raw = open(f'{root}/{lv}/level3d.bxon', 'rb').read()
    try:
        L = lr.Level(raw)
    except Exception:
        continue
    for arr in L.arrays.values():
        k = kind_key(arr)
        counts[k] += arr.count
        for i in range(arr.count):
            base = arr.block + i * arr.esize
            ptrs = {o: kind for o, t, kind, g in L.pointer_fields(base, arr.esize)}
            skip = set()
            for o, kind in ptrs.items():
                ptr_words[k][o] += 1
                skip.add(o)
                if kind == 'array':
                    skip.add(o + 4)
            for off in range(0, arr.esize - 3, 4):
                if off in skip:
                    continue
                lst = words[k][off]
                if len(lst) < 400:
                    lst.append(struct.unpack_from('<I', raw, base + off)[0])
            if k not in examples:
                examples[k] = (lv, base, arr.esize, bytes(raw[base:base + arr.esize]).hex())


def classify(vals):
    n = len(vals)
    z = sum(1 for v in vals if v == 0)
    ff = sum(1 for v in vals if v == 0xFFFFFFFF)
    fl = []
    for v in vals:
        f = struct.unpack('<f', struct.pack('<I', v))[0]
        if math.isfinite(f) and v != 0 and 1e-4 < abs(f) < 1e6 and (v >> 23) & 0xFF not in (0,):
            fl.append(f)
    small = [v for v in vals if 0 < v < 0x10000]
    d = len(set(vals))
    parts = []
    if z: parts.append(f'0:{100*z//n}%')
    if ff: parts.append(f'-1:{100*ff//n}%')
    if len(fl) > n * 0.5:
        parts.append(f'float[{min(fl):.3g}..{max(fl):.3g}]')
    elif small and len(small) > n * 0.3:
        parts.append(f'int[{min(small)}..{max(small)}]')
    elif d > 1:
        parts.append('bits')
    parts.append(f'{d} distinct')
    return ' '.join(parts)


out = []
for k, c in counts.most_common(70):
    out.append(f'### {k}  ({c} records)')
    lv, base, es, hx = examples[k]
    out.append(f'example {lv} @0x{base:X}: {hx[:200]}')
    if ptr_words[k]:
        out.append('pointers: ' + ', '.join(f'+0x{o:X}' for o in sorted(ptr_words[k])))
    for off in sorted(words[k]):
        out.append(f'  +0x{off:02X}: {classify(words[k][off])}')
    out.append('')
open('build/level_kind_profiles.md', 'w', encoding='utf8').write('\n'.join(out))
print('written', len(out))
