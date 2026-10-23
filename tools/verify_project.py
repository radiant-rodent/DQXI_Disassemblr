#!/usr/bin/env python3
"""One-shot end-to-end verification of the generated project.

Fast checks are read-only and reconcile:
  * bit-matching executable output;
  * asset counts and the last asset verification;
  * readable native-code coverage;
  * decoded map/scene counts;
  * the patched-ROM report and editor binary.

Use ``--hash-rom`` to also re-hash the 4 GB baseline and patched images.

Usage:
    python tools/verify_project.py
    python tools/verify_project.py --hash-rom
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPECTED_CODE = "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8"
EXPECTED_ROM = "0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def count(root: Path, pattern: str) -> int:
    return sum(1 for _ in root.rglob(pattern)) if root.exists() else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hash-rom", action="store_true")
    args = ap.parse_args()
    checks = []
    ok = True

    def check(name: str, condition: bool, detail: str):
        nonlocal ok
        checks.append({"check": name, "ok": bool(condition), "detail": detail})
        if not condition:
            ok = False

    code = ROOT / "build" / "code.bin"
    if code.is_file():
        check("code.bin size", code.stat().st_size == 7_090_176, f"{code.stat().st_size} bytes")
        check("code.bin hash", sha256(code) == EXPECTED_CODE, sha256(code))
    else:
        check("code.bin exists", False, str(code))

    av_path = ROOT / "audit" / "ASSET_VERIFICATION.json"
    if av_path.is_file():
        av = json.loads(av_path.read_text(encoding="utf-8"))
        check("asset verification", av.get("ok") is True, "audit/ASSET_VERIFICATION.json")
        for group, entry in av.get("groups", {}).items():
            check(f"assets {group}", entry["files"] >= (entry.get("expected") or 0), str(entry))
    else:
        check("asset verification file", False, str(av_path))

    model_textures = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_model_textures.py")],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    check(
        "model texture manifest",
        model_textures.returncode == 0,
        (model_textures.stdout.strip().splitlines() or ["no output"])[0],
    )

    dec_path = ROOT / "decomp" / "ghidra" / "functions_index.json"
    if dec_path.is_file():
        dec = json.loads(dec_path.read_text(encoding="utf-8"))
        check("native entry points", dec.get("total_discovered") == 18787, str(dec.get("total_discovered")))
        check("native decompiled", dec.get("decompiled_count", 0) >= 18748, str(dec.get("decompiled_count")))
    else:
        check("native index", False, str(dec_path))

    maps = count(ROOT / "game_assets" / "maps", "scene.json")
    check("decoded maps", maps == 1196, str(maps))

    report = ROOT / "build" / "PATCH_REPORT.json"
    if report.is_file():
        r = json.loads(report.read_text(encoding="utf-8"))
        check("patch report", bool(r.get("rom")), r.get("rom", "missing"))
        check("patched ROM exists", (ROOT / r["rom"]).is_file(), r.get("rom", ""))
    else:
        check("patch report", False, str(report))

    editor = ROOT / "viewer_rs" / "target" / "release" / "viewer_rs.exe"
    check("editor binary", editor.is_file(), str(editor))

    repl = ROOT / "build" / "replacement_report.json"
    if repl.is_file():
        rr = json.loads(repl.read_text(encoding="utf-8"))
        check("C source replacement", all(r.get("ok") for r in rr), str(rr))
    else:
        check("C source replacement", False, "build/replacement_report.json missing")

    if args.hash_rom:
        for name, expected in [("build/DQXI.3ds", EXPECTED_ROM), ("build/DQXI_patched.3ds", None)]:
            p = ROOT / name
            if p.is_file():
                got = sha256(p)
                check(name, expected is None or got == expected, got)
            else:
                check(name, False, "missing")

    (ROOT / "audit" / "PROJECT_VERIFICATION.json").write_text(json.dumps({
        "ok": ok,
        "checks": checks,
    }, indent=2), encoding="utf-8")
    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['check']}: {c['detail']}")
    print(f"\nOVERALL: {'PASS' if ok else 'FAIL'} -> audit/PROJECT_VERIFICATION.json")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
