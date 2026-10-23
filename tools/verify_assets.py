#!/usr/bin/env python3
"""Verify the converted asset tree against the source manifests.

This is deliberately independent of the conversion tools: it opens the generated
PNG/JSON/WAV/glTF files and checks their structure, then reconciles counts with
`game_data/manifest.json` and `game_data/arcs/summary.json`.

Usage:
    python tools/verify_assets.py
    python tools/verify_assets.py --sample 50
"""
from __future__ import annotations

import argparse
import json
import random
import struct
import sys
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS = PROJECT_ROOT / "game_assets"
AUDIT = PROJECT_ROOT / "audit"


def sample(paths: list[Path], n: int) -> list[Path]:
    if len(paths) <= n:
        return paths
    random.seed(1)
    return random.sample(paths, n)


def check_png(path: Path) -> str | None:
    try:
        from PIL import Image

        with Image.open(path) as img:
            img.verify()
        return None
    except Exception as exc:
        return str(exc)


def check_json(path: Path) -> str | None:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return None
    except Exception as exc:
        return str(exc)


def check_wav(path: Path) -> str | None:
    try:
        with wave.open(str(path), "rb") as w:
            if w.getnframes() <= 0:
                return "no audio frames"
            if w.getsampwidth() != 2:
                return f"unexpected sample width {w.getsampwidth()}"
        return None
    except Exception as exc:
        return str(exc)


def check_nut(path: Path) -> str | None:
    """Disassembled Squirrel script: UTF-8 text opening with a function header."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return str(exc)
    if not text.lower().startswith("function '"):
        return "missing 'function' header"
    if "{" not in text or "}" not in text:
        return "unbalanced function body"
    return None


def check_gltf(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("asset", {}).get("version") != "2.0":
            return "not glTF 2.0"
        buffers = data.get("buffers", [])
        if not buffers:
            return "no buffers"
        for b in buffers:
            uri = b.get("uri")
            if uri and not uri.startswith("data:"):
                p = path.parent / uri
                if not p.is_file():
                    return f"missing buffer {uri}"
                if p.stat().st_size != b.get("byteLength"):
                    return f"buffer size mismatch {uri}"
        for mesh in data.get("meshes", []):
            for prim in mesh.get("primitives", []):
                if "POSITION" not in prim.get("attributes", {}):
                    return "primitive without POSITION"
        return None
    except Exception as exc:
        return str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=100)
    args = ap.parse_args()

    manifest = json.loads((PROJECT_ROOT / "game_data" / "manifest.json").read_text(encoding="utf-8"))
    arcs = json.loads((PROJECT_ROOT / "game_data" / "arcs" / "summary.json").read_text(encoding="utf-8"))
    expected = {
        "textures": arcs.get("by_extension", {}).get(".bflim", 0),
        "layouts": arcs.get("by_extension", {}).get(".bflyt", 0) + arcs.get("by_extension", {}).get(".bflan", 0),
        "scripts": manifest.get("member_extensions", {}).get("cnut", 0),
        "tables": manifest.get("member_extensions", {}).get("bxon", 0),
        "audio": 5877,
        "maps": len(list((PROJECT_ROOT / "game_data" / "packs" / "level3d").glob("*/level3d.bxon"))),
        "models": 4779,
    }
    groups = {
        "textures": list((ASSETS / "textures").rglob("*.png")),
        "layouts": list((ASSETS / "layouts").rglob("*.json")),
        "models": list((ASSETS / "models").rglob("*.gltf")),
        "scripts": [p for p in (ASSETS / "scripts").rglob("*.nut") if not p.name.endswith(".decompiled.nut")],
        "tables": list((ASSETS / "tables").rglob("*.json")),
        "audio": list((ASSETS / "audio").rglob("*.wav")),
        "maps": list((ASSETS / "maps").glob("*/scene.json")),
    }
    checkers = {
        "textures": check_png,
        "layouts": check_json,
        "models": check_gltf,
        "tables": check_json,
        "maps": check_json,
        "audio": check_wav,
        "scripts": check_nut,
    }
    result = {"expected": expected, "groups": {}, "errors": []}
    for name, paths in groups.items():
        entry = {"files": len(paths), "expected": expected.get(name), "checked": 0, "errors": 0}
        checker = checkers.get(name)
        if checker:
            for path in sample(paths, args.sample):
                err = checker(path)
                entry["checked"] += 1
                if err:
                    entry["errors"] += 1
                    if len(result["errors"]) < 100:
                        result["errors"].append({"group": name, "file": str(path), "error": err})
        result["groups"][name] = entry
    result["ok"] = all(
        entry["errors"] == 0 and (entry["expected"] is None or entry["files"] >= entry["expected"])
        for entry in result["groups"].values()
    )
    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "ASSET_VERIFICATION.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for name, entry in result["groups"].items():
        print(f"{name:10} files={entry['files']:6} expected={entry['expected']} checked={entry['checked']:4} errors={entry['errors']}")
    print(f"OK={result['ok']}  ->  audit/ASSET_VERIFICATION.json")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
