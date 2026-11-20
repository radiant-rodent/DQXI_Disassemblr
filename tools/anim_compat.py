"""Which skeletal animations work on which rig -> game_assets/animations/compat.json.

Pipeline (re-run after a game data change):

    python tools/anim_compat.py lists            # build/anim_compat/models.txt + animfiles.txt
    tools/spica_ref/bin/Release/net9.0/SpicaRef.exe compat build/anim_compat/models.txt \
        build/anim_compat/animfiles.txt build/anim_compat/compat_full.json
    python tools/anim_compat.py write            # -> game_assets/animations/compat.json

`SpicaRef compat` poses every distinct skeleton with every animation whose tracks are (>= 90 %) bones of
that skeleton, using the same DQXI pose rules as the viewer (tools/spica_ref/Compat.cs, Compat.Evaluate).
Per pair it reports
  joint  - worst relative change of a skinned bone segment's length (parent -> bone) over 5 frames,
  dir    - p90 angle (deg) between the posed body segments and the same animation on its reference rig
           (the rig it fits best: its own family), -1 when fewer than 3 segments are shared,
  mesh   - p98 triangle-edge stretch (only used to drop exploding poses).
An animation works on a rig when it fits about as well as on its reference rig (joint - ref_joint <= 0.15)
and points the limbs the same way (dir <= 20 deg). Own-family animations legitimately stretch (squash,
weapons, props), so the comparison is always against the reference rig, never against zero.

compat.json:
  {"version": 1, "rule": "...",
   "models":    {"<model stem>": <skeleton index>},
   "skeletons": [{"models": [...], "sets": {"<set>": "*" | ["<anim>", ...]}}]}
A set is a motion folder name under 3d/motion (e.g. pc001_001_fld) or "cs/<path>" for cutscene and other
animation BCH; "*" means every skeletal animation in it works.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "build" / "anim_compat"
OUT = ROOT / "game_assets" / "animations" / "compat.json"
PACKS = ROOT / "game_data" / "packs"

MAX_DJOINT = 0.15
MAX_DIR = 20.0
MAX_MESH = 20.0
RULE = f"joint - ref_joint <= {MAX_DJOINT} and dir <= {MAX_DIR} deg (or unknown) and mesh <= {MAX_MESH}"


def set_name(bch: str) -> str:
    p = Path(bch).as_posix()
    if "/3d/motion/" in p:
        return p.split("/3d/motion/")[1].split("/")[0]
    try:
        rel = Path(bch).resolve().relative_to(PACKS.resolve()).as_posix()
    except ValueError:
        rel = Path(bch).name
    return "cs/" + rel[:-4] if rel.lower().endswith(".bch") else "cs/" + rel


def works(row) -> bool:
    _fi, _ai, mesh, joint, _cov, direc, ref_joint, is_ref = row
    if is_ref:
        return mesh <= MAX_MESH
    return mesh <= MAX_MESH and joint - ref_joint <= MAX_DJOINT and (direc < 0 or direc <= MAX_DIR)


def lists() -> None:
    """Model BCH with a skeleton and BCH with skeletal animations, from SpicaRef skeletons."""
    sk = WORK / "skeletons.json"
    if not sk.is_file():
        sys.exit(f"run first: SpicaRef skeletons build/anim_compat/list.txt {sk.relative_to(ROOT)}")
    d = json.loads(sk.read_text())
    models = [k for k, v in d.items() if v.get("bones") and len(v["bones"]) >= 2]
    anims = [k for k, v in d.items() if v.get("anims")]
    (WORK / "models.txt").write_text("\n".join(models))
    (WORK / "animfiles.txt").write_text("\n".join(anims))
    print(f"{len(models)} rigged models, {len(anims)} animation BCH")


def write(src: Path) -> None:
    d = json.loads(src.read_text())
    files, names = d["anim_files"], d["anim_names"]
    sets_total: dict[str, int] = defaultdict(int)
    for fi, f in enumerate(files):
        sets_total[set_name(f)] += len(names[fi] or [])
    out_models: dict[str, int] = {}
    out_skels = []
    pairs = ok_pairs = 0
    for si, s in enumerate(d["skeletons"]):
        good: dict[str, set[str]] = defaultdict(set)
        for row in s["results"]:
            pairs += 1
            if works(row):
                ok_pairs += 1
                fi, ai = row[0], row[1]
                good[set_name(files[fi])].add(names[fi][ai])
        sets = {k: ("*" if len(v) == sets_total[k] else sorted(v)) for k, v in sorted(good.items())}
        stems = sorted({Path(m).stem for m in s["models"]})
        for m in stems:
            out_models[m] = si
        out_skels.append({"models": stems, "bones": s["bones"], "sets": sets})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"version": 1, "rule": RULE, "models": out_models, "skeletons": out_skels},
                              separators=(",", ":")))
    with_any = sum(1 for s in out_skels if s["sets"])
    print(f"{pairs} scored pairs, {ok_pairs} work; {len(out_models)} models / {len(out_skels)} skeletons, "
          f"{with_any} skeletons with at least one working animation -> {OUT.relative_to(ROOT)} "
          f"({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "write"
    if cmd == "lists":
        lists()
    elif cmd == "write":
        write(Path(sys.argv[2]) if len(sys.argv) > 2 else WORK / "compat_full.json")
    else:
        sys.exit(__doc__)
