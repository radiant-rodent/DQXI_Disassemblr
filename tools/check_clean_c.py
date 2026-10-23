#!/usr/bin/env python3
"""Compile-check the clean subsystem C with an ARMv6K cross-compiler.

Locates ``arm-none-eabi-gcc`` on PATH or in the xPack install created by
``tools/setup_arm_toolchain.ps1``. This is a syntax/ABI smoke test, not a
bit-matching link.

Usage:
    python tools/check_clean_c.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "dqxi-tools"
CANDIDATES = [
    shutil.which("arm-none-eabi-gcc"),
    str(LOCAL / "xpack-arm-none-eabi-gcc-15.2.1-1.1" / "bin" / "arm-none-eabi-gcc.exe"),
]


def find_gcc() -> str | None:
    for c in CANDIDATES:
        if c and Path(c).is_file():
            return c
    return None


def main() -> int:
    gcc = find_gcc()
    if not gcc:
        print("arm-none-eabi-gcc not found; run tools/setup_arm_toolchain.ps1", file=sys.stderr)
        return 2
    sources = sorted((ROOT / "src").rglob("*.c"))
    failures = []
    for src in sources:
        cmd = [
            gcc,
            "-mcpu=arm1176jzf-s",
            "-marm",
            "-mfloat-abi=soft",
            "-fsyntax-only",
            "-I",
            str(ROOT / "include"),
            str(src),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            failures.append((src, r.stderr.splitlines()[:8]))
    for src in sources:
        print(f"[{'PASS' if all(f[0] != src for f in failures) else 'FAIL'}] {src.relative_to(ROOT)}")
    for src, err in failures:
        print(f"\n{src}:\n" + "\n".join(err), file=sys.stderr)
    print(f"\n{len(sources) - len(failures)}/{len(sources)} clean C files compile for ARMv6K")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
