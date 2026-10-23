#!/usr/bin/env python3
"""Audit every exported model's texture references against the BCH manifest.

The material manifest (`game_assets/models/material_map.json.gz`) records the
expected diffuse texture for every source draw. This verifier walks every
exported `.mtl`, derives the source BCH path, and reports:

- textures referenced by the model that are not in the source manifest
- missing texture files
- unreadable/empty texture files

It intentionally allows *missing* manifest entries after deduplication: layered
quads are collapsed and their second/third textures are not exported.

Output: `audit/MODEL_TEXTURE_VERIFICATION.json`
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.model_tool import draw_texture

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "game_assets" / "models"
MAP_FILE = ASSETS / "material_map.json.gz"
REPORT = ROOT / "audit" / "MODEL_TEXTURE_VERIFICATION.json"


def load_manifest() -> dict[str, list[dict]]:
    with gzip.open(MAP_FILE, "rt", encoding="utf-8") as f:
        return json.load(f)


def source_key(mtl: Path) -> str:
    rel = mtl.relative_to(ASSETS).as_posix()
    # <category>/.../<stem>/<stem>.mtl -> game_data/<category>/.../<stem>.bch
    p = Path(rel)
    return f"game_data/{p.parent.parent.as_posix()}/{p.parent.name}.bch"


def expected_textures(manifest: dict, mtl: Path) -> set[str] | None:
    entries = manifest.get(source_key(mtl))
    if entries is None:
        return None
    expected = {draw_texture(e) for e in entries if e.get("tex0") or e.get("tex1")}
    # layered faces are baked into "<skin unit texture>_composite" (model_tool._bake_layered_faces)
    return expected | {f"{e[t]}_composite" for e in entries for t in ("tex0", "tex1", "tex2") if e.get(t)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-report", type=int, default=200)
    args = ap.parse_args()
    if not MAP_FILE.is_file():
        print(f"missing {MAP_FILE}", file=sys.stderr)
        return 1
    manifest = load_manifest()
    total = 0
    bad = []
    missing_files = []
    no_source = []
    for mtl in sorted(ASSETS.rglob("*.mtl")):
        total += 1
        expected = expected_textures(manifest, mtl)
        if expected is None:
            no_source.append(str(mtl.relative_to(ROOT)))
            continue
        text = mtl.read_text(encoding="utf-8", errors="replace")
        used = {Path(x).stem for x in re.findall(r"^\s*map_Kd\s+(.+?)\s*$", text, re.MULTILINE)}
        unexpected = sorted(t for t in used if t and t not in expected)
        if unexpected:
            bad.append({
                "model": mtl.parent.name,
                "mtl": str(mtl.relative_to(ROOT)),
                "unexpected": unexpected,
                "expected": sorted(expected),
            })
        for name in used:
            png = mtl.parent / f"{name}.png"
            if not png.is_file() or png.stat().st_size == 0:
                missing_files.append(str(png.relative_to(ROOT)))
    report = {
        "models": total,
        "manifest_entries": len(manifest),
        "unexpected_texture_models": bad,
        "unexpected_texture_count": len(bad),
        "missing_texture_files": missing_files,
        "missing_texture_file_count": len(missing_files),
        "no_source_entry": no_source,
        "ok": not bad and not missing_files,
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"models={total} manifest={len(manifest)} unexpected_models={len(bad)} missing_files={len(missing_files)} no_source={len(no_source)}")
    for item in bad[: args.max_report]:
        print(f"  UNEXPECTED {item['mtl']}: {item['unexpected']}")
    for path in missing_files[: args.max_report]:
        print(f"  MISSING {path}")
    print(f"{'OK' if report['ok'] else 'FAIL'} -> {REPORT}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
