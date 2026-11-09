import os, sys, time, shutil, struct, json
os.chdir(r'.')
sys.path.insert(0, '.')
from pathlib import Path
from tests.emu import runner as R
from tools.emu import level_probe as P
from tools import custom_room as C
from tools.export_mod import stage_member
LV = 'd001_001a'
ROW = json.load(open('game_assets/maps/entity_models.json', encoding='utf8'))['maps'].index(LV)
C.SLOT_ID = ROW
name = 'dun_' + str(int(time.time()) % 100000)
out = P.OUT / name
shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
ws = R.workspace('probe_' + name, R.build_test_code(textlog=True), True)
work = out / 'work'; work.mkdir()
stage_member('level3d/b002_101a.pack', 'level3d.bxon', C.edit_church_exit(work), Path(ws), work_dir=work / 'staged')
if os.environ.get('GROUP'):
    scene = json.load(open(f'game_assets/maps/{LV}/scene.json', encoding='utf8'))
    raw = bytearray((P.LEVELS / LV / 'level3d.bxon').read_bytes())
    pos = [float(x) for x in os.environ.get('POS', '0,0,0').split(',')]
    n = 0
    for o in scene['objects']:
        if o['kind'] != 'symbol': continue
        pr = {p['name']: p for p in o['props']}
        struct.pack_into('<H', raw, int(pr['group']['offset'], 16), int(os.environ['GROUP']))
        if n == 0 and os.environ.get('POS'):
            off = int(o['record_offset'], 16)
            for k, v in enumerate(pos): struct.pack_into('<f', raw, off + 0x20 + 4 * k, v)
        n += 1
    e = work / 'lv.bxon'; e.write_bytes(bytes(raw))
    stage_member(f'level3d/{LV}.pack', 'level3d.bxon', e, Path(ws), work_dir=work / 'staged2')
R.export(ws, out / 'export', 'bin')
W = os.environ.get('W', 'D:1.5,D:1.5,D:1.5').split(',')
actions = [('B', 3, 0.8)] * 6 + [('WALK:' + w.split(':')[0], float(w.split(':')[1]), 1.2) for w in W]
rep = P.run_probe(name, out / 'export' / 'luma', actions=actions, save='user_heliodor')
print(name, {k: rep.get(k) for k in ('ok', 'crash')})
