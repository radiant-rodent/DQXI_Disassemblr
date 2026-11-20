#!/usr/bin/env python3
"""Emulator proof for the Level Editor's "add things" tools, in the Heliodor church (save ``user_heliodor``).

* **Add menu** (`tools/level_records.py` op ``import``): the church `b002_101a` has no chest at all; two treasure
  chests are copied in from the donor level next to the place the hero stands (into the active level group).
* **Dialogue structure** (`tools/npc_ie_edit.py`): character 182 of region 21 gets ONE new conversation whose line
  asks Yes / No, with the two answer blocks. The area script's scene-start event (the love-letter event, made
  unconditional as in docs/GIMMICK_DECOMP.md) shows it: `IEMessageSetup(182)`, the question, then the block of the
  answer. Every message on screen goes to the text log (events.jsonl).

    python -m tools.emu.add_probe [--answer yes|no]

Output: out/emu/probe/<name>/ (field.png, act*.png, events.jsonl, report.json).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.emu import level_probe as P  # noqa: E402

LEVEL = "b002_101a"
REGION, CHAR = 21, 182
NL = "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--answer", default="yes", choices=["yes", "no"])
    ap.add_argument("--no-dialogue", action="store_true")
    ap.add_argument("--open-chest", action="store_true", help="no dialogue; chests beside the hero, walk right and press A")
    ap.add_argument("--kinds", default="", help="no dialogue; import these donor kinds instead of chests, as title@x,z;title@x,z "
                    "(titles of game_assets/maps/donors.json); then walk right / left and press A")
    ap.add_argument("--step", action="store_true", help="tools/event_actions.py adds 'give item 2512' to the Yes branch; "
                    "the script shows the block 【もっている】 whenever the party holds the item (before and after)")
    sys.stdout.reconfigure(encoding="utf-8")
    a = ap.parse_args()
    if a.kinds:
        a.open_chest = True
    if a.open_chest:
        a.no_dialogue = True
    from tests.emu import runner as R
    from tools import level_records, npc_ie_edit, text_tool
    from tools.export_mod import stage_member

    name = f"add_{a.answer}_{int(time.time()) % 100000}"
    out = P.OUT / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    ws = R.workspace("probe_" + name, R.build_test_code(textlog=True), True)

    # 1. two chests into the church (anchor: the priest record of the active level group 11)
    donors = json.loads((ROOT / "game_assets" / "maps" / "donors.json").read_text(encoding="utf8"))["donors"]
    chest = next(d for d in donors if d["title"] == "Treasure chest")
    raw = (ROOT / "game_data" / "packs" / "level3d" / LEVEL / "level3d.bxon").read_bytes()
    ops = [{"op": "import", "donor": chest["level"], "offset": chest["object"]["record_offset"], "anchor": "0x152C", "shape": 100,
            "set": {"position": pos, "props": {"drop row": row}}} for pos, row in ((([1.3, 0.0, -3.5], 12), ([-1.3, 0.0, -3.5], 13)) if a.open_chest else (([1.5, 0.0, -2.5], 12), ([-1.5, 0.0, -2.5], 13)))]
    if a.kinds:
        ops = []
        for part in a.kinds.split(";"):
            title, at = part.split("@")
            x, z = (float(v) for v in at.split(","))
            d = next(d for d in donors if d["title"] == title)
            ops.append({"op": "import", "donor": d["level"], "offset": d["object"]["record_offset"], "anchor": "0x152C", "shape": d["object"]["shape"],
                        "set": {"position": [x, 0.0, z]}})
    level, results = level_records.apply_ops(raw, ops)
    f = out / "level3d.bxon"
    f.write_bytes(level)
    stage_member(f"level3d/{LEVEL}.pack", "level3d.bxon", f, ws, work_dir=out / "staged")
    print("chests:", results)

    if not a.no_dialogue:
        # 2. character 182: one conversation that asks, plus the answer blocks
        line = lambda text, kind=0: {"speaker": "", "text": text, "kind": kind, "b8": 0, "b9": 255, "b11": 0, "child_n": 0, "child": "", "tail": 0}
        model = {"talks": [{"group": 0, "min": 0, "time": 15, "first": 0, "redirect": 0x4000FFFF, "variants": [
            {"label": None, "lines": [line("「あたらしい　かいわ　だよ。", 1),
                                      line("「てつだって　くれるかい？", 3)]},
            {"label": "【はいの場合】", "lines": [line("「はい　を　えらんだね。")]},
            {"label": "【いいえの場合】", "lines": [line("「いいえ　を　えらんだね。")]},
            {"label": "【もっている】", "lines": [line("「てがみを　もっているね。")]},
        ]}]}
        bank = npc_ie_edit.bank_path(REGION).read_bytes()
        built = npc_ie_edit.apply(text_tool.rebuild_bank(bank, {}), {str(CHAR): model})
        f = out / "npc_ie.bxon"
        f.write_bytes(built)
        stage_member(f"param/region/r{REGION:03d}.pack", "npc_ie.bxon", f, ws, work_dir=out / "staged")
        # 3. the scene-start event shows it
        src = (ROOT / "game_assets" / "scripts" / "packs" / "script" / "b002" / "script.decompiled.nut").read_text(encoding="utf-8")
        a1 = "        local is_has_loveletter = GetItemNumInParty(2512) != 0;" + NL
        assert a1 in src
        edited = src.replace(a1, "        local is_has_loveletter = true;" + NL, 1)
        f0 = "    function IE_Z_A_030_M02_0155_A030_F05() {" + NL
        f1 = "        BookIDMessageSetup(58);" + NL
        has = ["        if (GetItemNumInParty(2512) != 0) {", "            IEChangeBlock(\"【もっている】\");", "            MessageLoop(-1);", "        }"]
        inner = NL.join([
            "        StartFadeInDefault();", "        WaitAllFade();", "        WaitFrame(180);",
            f"        IEMessageSetup({CHAR});"] + (has if a.step else []) + ["        local result = MessageLoop(-1);",
            "        if (result == 0) {", "            IEChangeBlock(\"【はいの場合】\");", "            MessageLoop(-1);",
            "        } else {", "            IEChangeBlock(\"【いいえの場合】\");", "            MessageLoop(-1);", "        }"] + (has if a.step else []) + [
            "        MessageEnd();", "        return;"]) + NL
        assert f0 + f1 in edited
        edited = edited.replace(f0 + f1, f0 + inner + f1, 1)
        nut = out / "b002_add.nut"
        nut.write_text(edited, encoding="utf-8")
        if a.step:
            # the Level Editor's answer-step tool itself, on this source: Yes gives the item
            from tools import event_actions
            event_actions.EDITS = out / "event_edits"
            event_actions.EDITS.mkdir()
            (event_actions.EDITS / "b002.nut").write_text(edited, encoding="utf-8")
            shown = event_actions.edit("b002", "IE_Z_A_030_M02_0155_A030_F05",
                                       [{"branch": "yes", "op": "add", "code": "AutoAddItemInParty(2512, 1);"}], False, None)
            print("answer steps:", [x["text"] for x in shown["yes"]])
            nut = event_actions.EDITS / "b002.nut"
        proc = subprocess.run([sys.executable, "tools/script_build.py", "pack", str(nut), "--area", "b002", "--tier", "source", "--mod", str(ws)],
                              cwd=ROOT, capture_output=True, text=True, timeout=600)
        print("script build", proc.returncode, proc.stderr[-200:])
        if proc.returncode:
            return 1
    R.export(ws, out / "export", "bin")
    # advance the texts; at the question A = Yes (cursor on the first answer), DOWN then A = No
    actions = [("A", 3, 1.2)] * 8
    if a.open_chest:
        actions = [("B", 3, 1.0)] * 2 + [("WALK:R", 0.12, 0.5)] + [("A", 3, 1.5)] * 4 + [("WALK:L", 0.5, 0.5)] + [("A", 3, 1.5)] * 4
    if a.answer == "no":
        # A and DOWN in turn: whichever A brings the question up, the DOWN after it moves the cursor to No
        actions = [("A", 3, 1.5), ("DOWN", 3, 0.8)] * 6
    if a.kinds:
        # the hero stands at about (0, -3.5) facing the priest: turn south with a tiny step, then A (put the things
        # at his feet / just south of him)
        actions = [("B", 3, 1.0)] * 2 + [("WALK:D", 0.06, 0.5)] + [("A", 3, 1.5)] * 6
    if not a.open_chest:
        actions += [("A", 3, 1.2)] * 8
    rep = P.run_probe(name, out / "export" / "luma", actions=actions, save="user_heliodor")
    print(json.dumps({k: rep.get(k) for k in ("name", "ok", "crash")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
