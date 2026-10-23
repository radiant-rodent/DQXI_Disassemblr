#!/usr/bin/env python3
"""Compile a C-source replacement and verify its exact machine code.

This closes the loop for small functions: write C (including a naked inline-asm
body when the original instruction sequence must be reproduced exactly), compile
with ARMv6K GCC, extract `.text`, compare it to the retail byte range, and emit a
replacement blob that ``tools/build.py`` can use.

Usage:
    python tools/build_c_replacement.py
    python tools/build_c_replacement.py --all

The initial replacement is `src/replacements/InitBss.c` at 0x00100024.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCAL = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "dqxi-tools"
TOOLCHAIN = LOCAL / "xpack-arm-none-eabi-gcc-15.2.1-1.1" / "bin"
ORIGINAL = ROOT / "original" / "exefs" / "code.decompressed.bin"
OUT = ROOT / "build" / "replacements"

REPLACEMENTS = [
    {
        "name": "InitBss",
        "address": 0x00100024,
        "size": 36,
        "source": "src/replacements/InitBss.c",
        "output": "init.bin",
    },
    {
        "name": "GetTalkPartyNoIndex",
        "address": 0x00158874,
        "size": 16,
        "source": "src/replacements/GetTalkPartyNoIndex.c",
        "output": "talk_party_no.bin",
        "link_text": True,
        "defsyms": {"func_003847A0": 0x003847A0},
    },
    {
        "name": "GetTalkPartyPageSize",
        "address": 0x0015A130,
        "size": 16,
        "source": "src/replacements/GetTalkPartyPageSize.c",
        "output": "talk_party_page.bin",
        "link_text": True,
        "defsyms": {"func_003847A0": 0x003847A0},
    },
    {
        "name": "GetTalkPartyYesIndex",
        "address": 0x0015A140,
        "size": 16,
        "source": "src/replacements/GetTalkPartyYesIndex.c",
        "output": "talk_party_yes.bin",
        "link_text": True,
        "defsyms": {"func_003847A0": 0x003847A0},
    },
]


def find(tool: str) -> Path:
    p = TOOLCHAIN / f"arm-none-eabi-{tool}.exe"
    if p.is_file():
        return p
    found = shutil.which(f"arm-none-eabi-{tool}")
    if found:
        return Path(found)
    raise FileNotFoundError(f"arm-none-eabi-{tool} not found; run tools/setup_arm_toolchain.ps1")


def compile_one(spec: dict, original: bytes) -> dict:
    gcc = find("gcc")
    objcopy = find("objcopy")
    ld = find("ld")
    src = ROOT / spec["source"]
    OUT.mkdir(parents=True, exist_ok=True)
    obj = OUT / (Path(spec["source"]).stem + ".o")
    raw = OUT / (Path(spec["source"]).stem + ".text")
    elf = OUT / (Path(spec["source"]).stem + ".elf")
    cmd = [
        str(gcc),
        "-mcpu=arm1176jzf-s",
        "-marm",
        "-mfloat-abi=soft",
        "-O2",
        "-c",
        str(src),
        "-o",
        str(obj),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return {"name": spec["name"], "ok": False, "stage": "compile", "error": r.stderr}
    obj_input = obj
    if spec.get("link_text"):
        addr = spec["address"]
        link = [str(ld), f"-Ttext=0x{addr:08X}"]
        for name, value in spec.get("defsyms", {}).items():
            link.append(f"--defsym={name}=0x{value:08X}")
        link += ["-o", str(elf), str(obj)]
        r = subprocess.run(link, capture_output=True, text=True)
        if r.returncode != 0:
            return {"name": spec["name"], "ok": False, "stage": "link", "error": r.stderr}
        obj_input = elf
    r = subprocess.run(
        [str(objcopy), "-O", "binary", "--only-section=.text", str(obj_input), str(raw)],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return {"name": spec["name"], "ok": False, "stage": "objcopy", "error": r.stderr}
    code = raw.read_bytes()
    addr = spec["address"]
    expected = original[addr - 0x00100000:addr - 0x00100000 + spec["size"]]
    ok = code == expected
    if ok:
        (OUT / spec["output"]).write_bytes(code)
    return {
        "name": spec["name"],
        "address": f"0x{addr:08X}",
        "size": len(code),
        "expected_size": spec["size"],
        "ok": ok,
        "first_diff": next((i for i, (a, b) in enumerate(zip(code, expected)) if a != b), None) if not ok else None,
        "output": str((OUT / spec["output"]).relative_to(ROOT)) if ok else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if not ORIGINAL.is_file():
        print(f"missing {ORIGINAL}", file=sys.stderr)
        return 1
    original = ORIGINAL.read_bytes()
    results = []
    for spec in REPLACEMENTS:
        result = compile_one(spec, original)
        results.append(result)
        print(json.dumps(result, indent=2))
    report = ROOT / "build" / "replacement_report.json"
    report.write_text(json.dumps(results, indent=2), encoding="utf-8")
    ok = all(r["ok"] for r in results)
    print(f"\n{'ALL REPLACEMENTS BIT-MATCH' if ok else 'REPLACEMENT MISMATCH'} -> {report}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
