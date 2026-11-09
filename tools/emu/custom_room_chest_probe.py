import os, sys, time, shutil, subprocess
os.chdir(r'.')
sys.path.insert(0, '.')
from pathlib import Path
from tests.emu import runner as R
from tools.emu import level_probe as P
from tools import custom_room as C
NL = chr(10)
name = 'crc_' + str(int(time.time()) % 100000)
out = P.OUT / name
shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
ws = R.workspace('probe_' + name, R.build_test_code(textlog=True), True)
print(C.build(Path(ws), item=int(os.environ.get('ITEM', '2')), work=out / 'work'))
src = Path('game_assets/scripts/packs/script/b002/script.decompiled.nut').read_text(encoding='utf-8')
a1 = "        local is_has_loveletter = GetItemNumInParty(2512) != 0;" + NL
assert a1 in src
edited = src.replace(a1, "        local is_has_loveletter = true;" + NL, 1)
f0 = "    function IE_Z_A_030_M02_0155_A030_F05() {" + NL
f1 = "        BookIDMessageSetup(58);" + NL
inner = NL.join(["        StartFadeInDefault();", "        WaitAllFade();", "        WaitFrame(240);", "        local m = GetLevelMapID();", f"        if (m == {os.environ.get("MAPC", C.SLOT_ID)}) {{",
                 "            IEMessageSetup(182);", "            MessageLoop(-1);", "            MessageEnd();", "            for (local i = 0; i < 40; i++) {", "                local a = GetGimmickActorID(i);", "                if (a >= 0) {", "                    GimmickItemGet(a);", "                    WaitFrame(30);", "                }", "            }", "        }", "        return;"]) + NL
assert f0 + f1 in edited
edited = edited.replace(f0 + f1, f0 + inner + f1, 1)
nut = out / 'b002_chest.nut'; nut.write_text(edited, encoding='utf-8')
proc = subprocess.run([sys.executable, 'tools/script_build.py', 'pack', str(nut), '--area', 'b002', '--tier', 'source', '--mod', str(ws)], capture_output=True, text=True, timeout=600)
print('script build', proc.returncode, proc.stderr[-200:])
if proc.returncode: sys.exit(1)
R.export(ws, out / 'export', 'bin')
W = os.environ.get('W', 'D:1.5,D:1.5,D:1.5').split(',')
actions = [('B', 3, 0.8)] * 6 + [('WALK:' + w.split(':')[0], float(w.split(':')[1]), 1.2) for w in W] + [('A', 2, 1.0)] * int(os.environ.get('NA', '14'))
rep = P.run_probe(name, out / 'export' / 'luma', actions=actions, save='user_heliodor')
print(name, {k: rep.get(k) for k in ('ok', 'crash')})
