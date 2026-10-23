#!/usr/bin/env python3
"""Character facial expressions: catalogue them and bake faces for any pose.

The face texture itself never changes in game. Motion files in
`game_data/packs/3d/motion/` animate the face material's texture-coordinate
translations: unit 0 (`MaterialTexCoord0Trans`) slides the eye atlas, unit 1
(`MaterialTexCoord1Trans`) the mouth atlas. A *pose* is one (eyes, mouth) pair
of translations; the model export bakes the default pose ((0,0), (0,0)).

    # catalogue every face animation (needs tools/spica_ref built)
    python tools/face_expressions.py scan
    # bake one model's face for a pose, e.g. the "rest" mouth used by most animations
    python tools/face_expressions.py bake game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch \\
        --eyes 0,0 --mouth 0.5,0.75 --out face.png

`scan` writes `game_assets/models/face_expressions.json`:
- `animations`: motion file -> animation -> {"frames", "eyes": [[frame, u, v], ...], "mouth": [...]}
- `poses`: every distinct (eyes, mouth) pair at a key frame, with how often it occurs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

MOTION = ROOT / "game_data" / "packs" / "3d" / "motion"
SPICA_EXE = ROOT / "tools" / "spica_ref" / "bin" / "Release" / "net9.0" / "SpicaRef.exe"
OUT = ROOT / "game_assets" / "models" / "face_expressions.json"
FACE_MATERIAL = b"Face_high_MT"


def track(element: dict | None) -> list[list[float]]:
    """Merges separate X/Y key frames into [frame, u, v] rows (step lookup)."""
    if not element:
        return []
    xs, ys = element.get("x", []), element.get("y", [])

    def at(keys: list, frame: float) -> float:
        value = keys[0][1] if keys else 0.0
        for f, v in keys:
            if f <= frame:
                value = v
        return value

    frames = sorted({f for f, _ in xs} | {f for f, _ in ys}) or [0.0]
    return [[f, round(at(xs, f), 4), round(at(ys, f), 4)] for f in frames]


def scan() -> dict:
    if not SPICA_EXE.is_file():
        raise SystemExit("build tools/spica_ref first: dotnet build tools/spica_ref -c Release")
    animations: dict[str, dict] = {}
    poses: Counter = Counter()
    with tempfile.TemporaryDirectory() as td:
        for bch in sorted(MOTION.rglob("*.bch")):
            if FACE_MATERIAL not in bch.read_bytes():
                continue
            out = Path(td) / "anims.json"
            subprocess.run([str(SPICA_EXE), "matanims", str(bch), str(out)], check=True, capture_output=True)
            rel = bch.relative_to(ROOT).as_posix()
            for anim in json.loads(out.read_text(encoding="utf-8")):
                tracks = {e["target"]: e for e in anim["elements"] if e["material"] == "Face_high_MT"}
                eyes = track(tracks.get("MaterialTexCoord0Trans"))
                mouth = track(tracks.get("MaterialTexCoord1Trans"))
                if not eyes and not mouth:
                    continue
                animations.setdefault(rel, {})[anim["name"]] = {"frames": anim["frames"], "eyes": eyes, "mouth": mouth}
                for _, eu, ev in eyes or [[0, 0.0, 0.0]]:
                    for _, mu, mv in mouth or [[0, 0.0, 0.0]]:
                        poses[(eu, ev, mu, mv)] += 1
    data = {
        "animations": animations,
        "poses": [{"eyes": [k[0], k[1]], "mouth": [k[2], k[3]], "count": n} for k, n in poses.most_common()],
    }
    OUT.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {sum(len(v) for v in animations.values())} animations "
          f"in {len(animations)} motion files, {len(poses)} distinct poses")
    return data


def bake(bch: Path, eyes: tuple[float, float], mouth: tuple[float, float], out: Path) -> Path:
    from tools.model_tool import BchParser

    parser = BchParser(bch.read_bytes(), source_path=bch.resolve())
    parser.face_pose = (eyes, mouth)
    model = parser.parse_models(bch.stem)[0]
    composites = [(name, img) for name, img in model.textures if name.endswith("_composite")]
    if not composites:
        raise SystemExit(f"{bch} has no layered face material")
    composites[0][1].save(out)
    print(f"wrote {out} ({composites[0][0]}, eyes={eyes}, mouth={mouth})")
    return out


def pair(text: str) -> tuple[float, float]:
    u, v = (float(x) for x in text.split(","))
    return u, v


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan", help="catalogue face animations from the motion files")
    b = sub.add_parser("bake", help="bake one model's face for a pose")
    b.add_argument("bch", type=Path)
    b.add_argument("--eyes", type=pair, default=(0.0, 0.0), help="eye atlas translation u,v")
    b.add_argument("--mouth", type=pair, default=(0.0, 0.0), help="mouth atlas translation u,v")
    b.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.cmd == "scan":
        scan()
    else:
        bake(args.bch, args.eyes, args.mouth, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
