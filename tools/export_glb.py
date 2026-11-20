"""Export models as rigged glTF (.glb) for Blender: skeleton, skin weights, textures and the animations that
work on the rig (game_assets/animations/compat.json, see tools/anim_compat.py).

    python tools/export_glb.py cha01000a_h                 # own motion sets -> game_assets/blender/cha01000a_h.glb
    python tools/export_glb.py m043a_h --sets m043_fld,m043_btl
    python tools/export_glb.py cha01000a_h --all            # every working set (large!)
    python tools/export_glb.py m001a_h --cutscenes --outlines
    python tools/export_glb.py --list cha01000a_h           # which sets work on the rig

In Blender: File > Import > glTF 2.0, or the viewer's Models > animation row > "Rigged -> Blender" (exports
and opens it). The armature carries the game's joints, each mesh has one vertex group per joint (Weight
Paint mode shows them) and every clip becomes an action (Action editor / NLA). Alternate hand meshes carry
the custom property dqxi_hidden (the viewer's import hides them); outline shells are left out.

Default animation choice: the model family's own sets (cha01xxx -> pc001_*, m043x -> m043_*, ...), one
outfit/weapon variant per set kind; when the family has none, every fully working set (up to 12).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "tools" / "spica_ref" / "bin" / "Release" / "net9.0" / "SpicaRef.exe"
COMPAT = ROOT / "game_assets" / "animations" / "compat.json"
PACKS = ROOT / "game_data" / "packs"
OUT = ROOT / "game_assets" / "blender"


def motion_key(model: str) -> str | None:
    """Same naming rule as the viewer (viewer_rs/src/ui/panels/model_anim.rs)."""
    m = model.lower()
    for prefix, width, fmt in (("ani", 5, "a{:03}_"), ("cha", 2, "pc{:03}_"), ("m", 3, "m{:03}_"), ("r", 3, "r{:03}_")):
        if m.startswith(prefix):
            d = re.match(r"\d+", m[len(prefix):])
            if d and len(d.group()) >= width:
                return fmt.format(int(d.group()[:width]))
            return None
    return None


def model_bch(stem: str) -> Path:
    p = PACKS / "3d" / "model" / stem / f"{stem}.bch"
    if p.is_file():
        return p
    hits = list(PACKS.rglob(f"{stem}.bch"))
    if not hits:
        sys.exit(f"no BCH named {stem}.bch under game_data/packs")
    return hits[0]


def set_bch(name: str) -> Path | None:
    if name.startswith("cs/"):
        p = PACKS / f"{name[3:]}.bch"
        return p if p.is_file() else None
    d = PACKS / "3d" / "motion" / name
    return next(iter(sorted(d.glob("*.bch"))), None) if d.is_dir() else None


def default_sets(stem: str, sets: dict) -> list[str]:
    motion = [s for s in sets if not s.startswith("cs/")]
    key = motion_key(stem)
    fam = [s for s in motion if key and s.startswith(key)]
    if fam:
        # pc001_001_fld, pc001_002_fld, ... are the same clips per outfit/weapon: keep the first variant of each kind
        seen, out = set(), []
        for s in sorted(fam):
            kind = re.sub(r"_\d{3}(?=_)", "", s)
            if kind not in seen:
                seen.add(kind)
                out.append(s)
        return out
    return [s for s in sorted(motion) if sets[s] == "*"][:12]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="+", help="model stems, e.g. cha01000a_h")
    ap.add_argument("--sets", help="comma-separated motion sets (names from --list)")
    ap.add_argument("--with", dest="extra", help="comma-separated motion sets added to the default choice")
    ap.add_argument("--all", action="store_true", help="every set that works on the rig")
    ap.add_argument("--cutscenes", action="store_true", help="also the cutscene clips that work on the rig")
    ap.add_argument("--outlines", action="store_true", help="keep the black outline shells (*_Outline meshes)")
    ap.add_argument("--list", action="store_true", help="only list the working sets")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    if not COMPAT.is_file():
        sys.exit("game_assets/animations/compat.json missing: run tools/anim_compat.py (see its docstring)")
    if not EXE.is_file():
        sys.exit("build tools/spica_ref first: dotnet build tools/spica_ref -c Release")
    compat = json.loads(COMPAT.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    for stem in a.models:
        si = compat["models"].get(stem)
        sets = compat["skeletons"][si]["sets"] if si is not None else {}
        if a.list:
            print(f"{stem}: {len(sets)} working sets")
            for k, v in sets.items():
                print(f"   {k:40s} {'all clips' if v == '*' else f'{len(v)} clips'}")
            continue
        if a.sets:
            chosen = [s for s in a.sets.split(",") if s]
            bad = [s for s in chosen if s not in sets]
            if bad:
                sys.exit(f"{stem}: not working on this rig: {', '.join(bad)} (see --list)")
        elif a.all:
            chosen = [s for s in sets if not s.startswith("cs/")]
        else:
            chosen = default_sets(stem, sets)
        if a.extra:
            chosen += [s for s in a.extra.split(",") if s in sets and s not in chosen]
        if a.cutscenes:
            chosen += [s for s in sets if s.startswith("cs/") and s not in chosen]
        lines = []
        for s in chosen:
            bch = set_bch(s)
            if bch is None:
                print(f"   skip {s}: no BCH found")
                continue
            clips = sets[s]
            label = s.rsplit("/", 1)[-1]  # action names "<set>/<clip>": the same clip name occurs in many sets
            lines += [f"{bch}\t*\t{label}"] if clips == "*" else [f"{bch}\t{c}\t{label}" for c in clips]
        lst = a.out / f"{stem}.anims.txt"
        lst.write_text("\n".join(lines))
        out = a.out / f"{stem}.glb"
        cmd = [str(EXE), "gltf", str(model_bch(stem)), str(out), str(lst)] + (["--outlines"] if a.outlines else [])
        r = subprocess.run(cmd, capture_output=True, text=True)
        lst.unlink(missing_ok=True)
        msg = [l for l in r.stdout.splitlines() if "->" in l]
        if r.returncode != 0 or not out.is_file():
            sys.exit(f"{stem}: SpicaRef gltf failed\n{r.stderr[-2000:]}")
        try:
            import glb_face_composite
            face = glb_face_composite.apply(out)
        except Exception as e:  # the plain glb is still usable
            face = f"face composite skipped: {e}"
        if face:
            msg.append(face)
        print(f"{stem}: sets {', '.join(chosen) or '(none)'}\n   {"; ".join(msg[-2:])} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
