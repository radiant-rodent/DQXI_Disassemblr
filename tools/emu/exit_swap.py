"""Set the destination map of every map-jump record (+0x68) of an area's levels, then walk out of the church."""
import os
import struct
import sys

os.chdir(r'.')
sys.path.insert(0, '.')
import tools.level_records as lr
from tools.emu import level_probe as P

area, dest = sys.argv[1], int(sys.argv[2], 0)
levels = sorted(d for d in os.listdir(P.LEVELS) if d.startswith(area + '_'))
out = {}
n = 0
for lv in levels:
    raw = bytearray((P.LEVELS / lv / 'level3d.bxon').read_bytes())
    L = lr.Level(bytes(raw))
    for arr in L.arrays.values():
        if arr.esize == 24 and arr.parent is not None and arr.parent.esize == 1092:
            base = arr.parent.block + arr.parent_index * arr.parent.esize
            if arr.desc - base == 0x68:
                for i in range(arr.count):
                    b = arr.block + i * 24 + 0x0C
                    w = struct.unpack_from('<I', raw, b)[0]
                    struct.pack_into('<I', raw, b, (w & 0xFFFF0000) | dest)
                    n += 1
    out[lv] = bytes(raw)
print(len(out), 'levels,', n, 'exit records set to map', dest)
name = f'exitswap_{area}_{dest}'
mod = P.build_mod(name, out)
actions = [('B', 3, 0.8)] * 6 + [('WALK:D', 1.5, 1.0)] * 5 + [('B', 3, 1.0)]
rep = P.run_probe(name, mod, actions=actions, save='user_heliodor')
print({k: rep.get(k) for k in ('ok', 'crash', 'action_shots')})
