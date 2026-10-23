#!/usr/bin/env python3
"""Pixel-level audit of every model texture against the SPICA reference reader.

For every BCH under `game_data/` this checks three things:

1. **decoder** - `BchParser.extract_textures()` produces the same image (size and
   pixels) as SPICA for every embedded texture.
2. **export** - the PNG next to the exported model in `game_assets/models/` is the
   same image (catches stale files left behind by older exports).
3. **assignment** - every texture the model's `.mtl` references is one SPICA says
   the source draws use (`material_map.json.gz`).

The SPICA reference images come from `tools/spica_ref` (a tiny C# wrapper around
the vendored `third_party/SPICA` reader). Build and dump them once with:

    dotnet build tools/spica_ref -c Release
    tools/spica_ref/bin/Release/net9.0/SpicaRef.exe textures build/all_bch.txt build/spica_ref .

`--dump` does both steps for you. Output: `audit/MODEL_TEXTURE_AUDIT.json`.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA = ROOT / "game_data"
MODELS = ROOT / "game_assets" / "models"
REF = ROOT / "build" / "spica_ref"
LIST = ROOT / "build" / "all_bch.txt"
SPICA_EXE = ROOT / "tools" / "spica_ref" / "bin" / "Release" / "net9.0" / "SpicaRef.exe"
REPORT = ROOT / "audit" / "MODEL_TEXTURE_AUDIT.json"

# 5/6-bit channels are expanded slightly differently (x*255//31 vs bit replication),
# so allow a few levels of difference per channel.
TOLERANCE = 4


def dump_reference() -> None:
    srcs = sorted((DATA / "packs").rglob("*.bch")) + sorted((DATA / "romfs").rglob("*.bch"))
    LIST.parent.mkdir(parents=True, exist_ok=True)
    LIST.write_text("\n".join(p.relative_to(ROOT).as_posix() for p in srcs), encoding="utf-8")
    subprocess.run(["dotnet", "build", str(ROOT / "tools" / "spica_ref"), "-c", "Release"], check=True)
    subprocess.run([str(SPICA_EXE), "textures", str(LIST), str(REF), str(ROOT)], check=True, cwd=ROOT)


def max_diff(a: np.ndarray, b: np.ndarray) -> int:
    if a.shape != b.shape:
        return 999
    a = a.astype(np.int16)
    b = b.astype(np.int16)
    # fully transparent texels carry no visible colour
    visible = (a[..., 3] > 0) | (b[..., 3] > 0)
    d = np.abs(a - b)
    d[..., :3] *= visible[..., None]
    return int(d.max()) if d.size else 0


def rgba(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("RGBA"))


def check_one(rel: str, ref_entries: list[dict]) -> dict:
    from tools.model_tool import BchParser

    src = ROOT / rel
    out: dict = {"source": rel, "decoder": [], "export": [], "assignment": []}
    ref_dir = REF / rel[:-4]
    try:
        ours = {name: np.asarray(img.convert("RGBA")) for name, img in BchParser(src.read_bytes(), source_path=src).extract_textures()}
    except Exception as exc:  # pragma: no cover - reported, not fatal
        out["decoder"].append({"texture": "*", "problem": f"parser error: {exc}"})
        ours = {}
    for entry in ref_entries:
        name = entry["name"]
        if entry.get("cube"):
            continue
        ref_png = ref_dir / f"{name}.png"
        if not ref_png.is_file():
            continue
        ref = rgba(ref_png)
        mine = ours.get(name)
        if mine is None:
            out["decoder"].append({"texture": name, "format": entry["format"], "problem": "not extracted"})
        else:
            d = max_diff(mine, ref)
            if d > TOLERANCE:
                out["decoder"].append({"texture": name, "format": entry["format"], "max_diff": d,
                                       "ours": list(mine.shape[1::-1]), "spica": [entry["width"], entry["height"]]})
        exported = MODELS / Path(rel).parent.relative_to("game_data") / src.stem / f"{name}.png"
        if exported.is_file():
            d = max_diff(rgba(exported), ref)
            if d > TOLERANCE:
                out["export"].append({"texture": name, "format": entry["format"], "max_diff": d,
                                      "file": exported.relative_to(ROOT).as_posix()})
    return out


def check_assignment(manifest: dict[str, list[dict]]) -> list[dict]:
    from tools.model_tool import draw_texture

    bad = []
    for mtl in sorted(MODELS.rglob("*.mtl")):
        rel = mtl.relative_to(MODELS)
        key = f"game_data/{rel.parent.parent.as_posix()}/{rel.parent.name}.bch"
        entries = manifest.get(key)
        if entries is None:
            continue
        expected = {draw_texture(e) for e in entries}
        # layered faces are baked into "<skin unit texture>_composite" (model_tool._bake_layered_faces)
        expected |= {f"{e[t]}_composite" for e in entries for t in ("tex0", "tex1", "tex2") if e.get(t)}
        used = {Path(x).stem for x in re.findall(r"^\s*map_Kd\s+(.+?)\s*$", mtl.read_text(encoding="utf-8", errors="replace"), re.M)}
        unexpected = sorted(t for t in used if t and t not in expected)
        if unexpected:
            bad.append({"mtl": mtl.relative_to(ROOT).as_posix(), "unexpected": unexpected, "expected": sorted(expected)})
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", action="store_true", help="(re)build SpicaRef and dump reference textures first")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0, help="only check the first N BCH files")
    ap.add_argument("--filter", default="", help="only check sources containing this substring")
    args = ap.parse_args()

    if args.dump or not (REF / "index.json").is_file():
        dump_reference()
    index: dict[str, list[dict]] = json.loads((REF / "index.json").read_text(encoding="utf-8"))
    items = [(k, v) for k, v in sorted(index.items()) if v and args.filter in k]
    if args.limit:
        items = items[: args.limit]

    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(check_one, k, v) for k, v in items]
        for i, fut in enumerate(futures, 1):
            results.append(fut.result())
            if i % 1000 == 0:
                print(f"  {i}/{len(items)} BCH checked")

    with gzip.open(MODELS / "material_map.json.gz", "rt", encoding="utf-8") as f:
        assignment = check_assignment(json.load(f))

    decoder = [r for r in results if r["decoder"]]
    export = [r for r in results if r["export"]]
    textures = sum(len(v) for _, v in items)
    report = {
        "bch_checked": len(items),
        "textures_checked": textures,
        "decoder_mismatch_bch": len(decoder),
        "decoder_mismatch_textures": sum(len(r["decoder"]) for r in decoder),
        "stale_export_bch": len(export),
        "stale_export_textures": sum(len(r["export"]) for r in export),
        "assignment_mismatch_models": len(assignment),
        "decoder": [{"source": r["source"], "textures": r["decoder"]} for r in decoder],
        "export": [{"source": r["source"], "textures": r["export"]} for r in export],
        "assignment": assignment,
    }
    report["ok"] = not decoder and not export and not assignment
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"BCH={len(items)} textures={textures} decoder_mismatch={report['decoder_mismatch_textures']} "
          f"stale_exports={report['stale_export_textures']} assignment_mismatch={len(assignment)}")
    print(f"{'OK' if report['ok'] else 'FAIL'} -> {REPORT.relative_to(ROOT)}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
