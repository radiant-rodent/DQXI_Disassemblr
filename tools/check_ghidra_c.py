#!/usr/bin/env python3
"""Syntax-check a sample of the Ghidra-generated C.

Ghidra output is not a hand-written port, but it should at least be valid C under a
presentation header. This catches malformed signatures, namespaced symbols, and missing
decompiler types without pretending the code is ready for ARM compilation.

Usage:
    python tools/check_ghidra_c.py
    python tools/check_ghidra_c.py --sample 300
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GHIDRA = ROOT / "decomp" / "ghidra"
AUDIT = ROOT / "audit"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=100)
    args = ap.parse_args()
    files = sorted(GHIDRA.glob("functions/*.c")) + sorted(GHIDRA.glob("recovered/*.c"))
    if not files:
        print("no generated C files", file=sys.stderr)
        return 1
    if len(files) > args.sample:
        random.seed(3)
        files = random.sample(files, args.sample)
    prelude = GHIDRA / "prelude.h"
    if not prelude.is_file():
        print("missing prelude.h; run tools/organize_ghidra.py", file=sys.stderr)
        return 1
    failures = []
    warnings = 0
    for i, path in enumerate(files, 1):
        r = subprocess.run(
            ["gcc", "-fsyntax-only", "-w", "-I", str(GHIDRA), "-include", str(prelude), str(path)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            failures.append({"file": str(path.relative_to(ROOT)), "error": r.stderr.splitlines()[:6]})
        warnings += r.stderr.count("warning:")
        if i % 25 == 0 or i == len(files):
            print(f"  checked {i}/{len(files)}  failures={len(failures)}")
    result = {
        "sample": len(files),
        "passed": len(files) - len(failures),
        "failed": len(failures),
        "warnings": warnings,
        "failures": failures[:80],
    }
    AUDIT.mkdir(exist_ok=True)
    (AUDIT / "DECOMPILE_SYNTAX.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Syntax check: {result['passed']}/{len(files)} passed, {result['failed']} failed, {warnings} warnings")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
