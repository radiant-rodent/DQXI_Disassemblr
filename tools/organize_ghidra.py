#!/usr/bin/env python3
"""Organise the Ghidra export into a navigable, documented source tree.

Reads ``decomp/ghidra/functions.jsonl`` and writes:

  decomp/ghidra/by_subsystem/<Domain>/<name>_<addr>.c
  decomp/ghidra/functions.h
  decomp/ghidra/dqxi_types.h
  decomp/ghidra/functions_index.json
  decomp/ghidra/COVERAGE.md
  decomp/ghidra/README.md

The original flat export is preserved.  Files are hard-linked when possible so
the organised view does not double disk usage.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GHIDRA = PROJECT_ROOT / "decomp" / "ghidra"

DOMAINS = [
    ("Audio", ("audio", "sound", "bgm", "voice", "se_", "music", "stream")),
    ("Battle", ("battle", "enemy", "damage", "skill", "attack", "turn", "monster", "boss")),
    ("Camera", ("camera", "cam_", "fov", "shake")),
    ("Actors_and_Entities", ("actor", "player", "party", "npc", "entity", "character", "mount")),
    ("UI_and_Message", ("ui", "message", "window", "menu", "layout", "font", "text", "dialog", "icon")),
    ("Memory_and_Heaps", ("heap", "memory", "alloc", "free", "pool", "buddy")),
    ("Save_and_Persistence", ("save", "load", "record", "flag", "quest", "restore", "persist")),
    ("Field_and_World", ("map", "field", "level", "world", "area", "warp", "jump", "weather", "time")),
    ("Input", ("hid", "pad", "button", "touch", "input")),
    ("Kernel_and_System", ("thread", "mutex", "kernel", "svc", "event", "semaphore", "system", "init")),
    ("IO_and_Files", ("file", "rom", "fs", "asset", "archive", "pack", "stream")),
]


def domain_for(name: str) -> str:
    low = name.lower()
    for domain, keys in DOMAINS:
        if any(k in low for k in keys):
            return domain
    return "General_Procedures"


def link_or_copy(src: Path, dst: Path):
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=GHIDRA)
    args = ap.parse_args()
    root = args.root
    index = root / "functions.jsonl"
    if not index.is_file():
        print(f"missing {index}", file=sys.stderr)
        return 1

    records = []
    for line in index.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            if isinstance(rec.get("signature"), str):
                rec["signature"] = rec["signature"].replace("::", "_")
            records.append(rec)
    recovered_path = root / "missing_result.jsonl"
    if recovered_path.is_file():
        fixed = {}
        for line in recovered_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                fixed[r.get("address")] = r
        for rec in records:
            r = fixed.get(rec.get("address"))
            if not r:
                continue
            status = r.get("status")
            if status == "recovered":
                rec["status"] = "ok"
                rec["file"] = r.get("file")
                rec["name"] = r.get("name", rec.get("name"))
            elif status == "covered_by":
                rec["status"] = "covered_by"
                rec["container"] = r.get("container")
                rec["container_entry"] = r.get("container_entry")
            elif status in ("unrecovered", "created_no_decompile"):
                rec["status"] = "unrecovered"

    out = root / "by_subsystem"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    counts = Counter()
    ok = 0
    missing = 0
    failed = 0
    covered = 0
    prototypes = []
    for rec in records:
        name = rec.get("name") or "unknown"
        addr = rec.get("address", "0")
        domain = domain_for(name)
        counts[domain] += 1
        status = rec.get("status", "ok")
        if status == "ok":
            ok += 1
        elif status == "missing_function":
            missing += 1
        elif status == "covered_by":
            covered += 1
        else:
            failed += 1
        rel = rec.get("file")
        if rel:
            src = root / rel
            if src.is_file():
                safe = name.replace("/", "_").replace("\\", "_")
                dst = out / domain / f"{safe}_{addr}.c"
                dst.parent.mkdir(parents=True, exist_ok=True)
                link_or_copy(src, dst)
        sig = rec.get("signature")
        if sig:
            prototypes.append(f"/* {addr} {name} */\n{sig.replace('::', '_')};")

    (root / "functions.h").write_text(
        "/* Generated prototypes for the readable DQXI decompilation. */\n"
        "#pragma once\n#include \"dqxi_types.h\"\n\n" + "\n".join(prototypes) + "\n",
        encoding="utf-8",
    )
    (root / "dqxi_types.h").write_text(
        """/* Minimal CTR/ARM types used by the Ghidra-generated C.
 * These are presentation types, not a claim about the original compiler ABI.
 */
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>


typedef uint8_t  undefined1;
typedef uint16_t undefined2;
typedef uint32_t undefined4;
typedef uint64_t undefined8;
typedef uint8_t  undefined;
typedef uint8_t  byte;
typedef uint16_t ushort;
typedef uint32_t uint;
typedef uint64_t ulong;
typedef uint8_t  code;
typedef int32_t  int3;
typedef uint32_t uint3;
typedef uint64_t uint4;
typedef int64_t  longlong;
typedef uint64_t ulonglong;
typedef float    float4;
typedef uint16_t wchar16;
typedef uint32_t wchar32;

#ifndef NULL
#define NULL ((void*)0)
#endif
""",
        encoding="utf-8",
    )
    (root / "prelude.h").write_text(
        '#pragma once\n#include "dqxi_types.h"\n#include "functions.h"\n', encoding="utf-8"
    )

    index_json = {
        "total_discovered": len(records),
        "decompiled_count": ok,
        "missing_count": missing,
        "covered_by_container_count": covered,
        "failed_count": failed,
        "parser": "ghidra",
        "functions": [
            {
                "address": r.get("address"),
                "name": r.get("name"),
                "mode": r.get("mode", "arm"),
                "size": r.get("size", 0),
                "status": r.get("status"),
                "file": r.get("file"),
            }
            for r in records
        ],
    }
    (root / "functions_index.json").write_text(json.dumps(index_json, indent=2), encoding="utf-8")
    with open(root / "functions_merged.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    lines = [
        "# Readable Native Decompilation (Ghidra)",
        "",
        "This directory is the human-readable native-code view. It is generated from the retail",
        "executable with Ghidra's ARMv6 decompiler, not from the old register-level pseudo-C.",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Entry points | {len(records):,} |",
        f"| Decompiled | {ok:,} |",
        f"| Covered by a containing function | {covered:,} |",
        f"| Unrecovered | {missing + failed:,} |",
        "",
        "## Subsystems",
        "",
        "| Directory | Functions |",
        "|---|---:|",
    ]
    for domain, count in counts.most_common():
        lines.append(f"| `{domain}` | {count:,} |")
    lines += [
        "",
        "## How to read a function",
        "",
        "1. Search `functions_index.json` or the `by_subsystem` tree by name or address.",
        "2. Open the `.c` file. Ghidra names unknown callees `FUN_<address>`; use the index to resolve them.",
        "3. `dqxi_types.h` supplies the decompiler's `undefined*` types. Real struct recovery is an",
        "   ongoing task; see the function comments and cross-references before assuming a layout.",
        "4. Signatures and address metadata are in `functions.jsonl`; `functions.h` contains prototypes.",
        "",
        "## Reproduce",
        "",
        "```powershell",
        "analyzeHeadless decomp/ghidra_project DQXI -process code.decompressed.bin -noanalysis \\",
        "  -scriptPath tools/ghidra_scripts \\",
        "  -postScript ExportDQXI.java . .\\decomp\\ghidra",
        "python tools/organize_ghidra.py",
        "```",
        "",
        "## Known limitation",
        "",
        "A small set of entry points could not be turned into Ghidra functions because the retail",
        "binary contains overlapping/jump-table code. They are listed in `functions.jsonl` with",
        "`status` = `missing_function`; the original annotated assembly remains the ground truth",
        "for those addresses.",
    ]
    (root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "COVERAGE.md").write_text(
        "\n".join([
            "# Ghidra Export Coverage",
            "",
            f"- Entry points: **{len(records):,}**",
            f"- Decompiled: **{ok:,}** ({100.0 * ok / max(1, len(records)):.2f}%)",
            f"- Covered by a containing decompiled function: **{covered:,}**",
            f"- Unrecovered: **{missing + failed:,}**",
            "",
            "The missing list is retained in `functions.jsonl`. Entries with `covered_by` are addresses",
            "inside a larger recovered function (jump-table/label entry points); the containing function",
            "covers their code. `unrecovered` entries need a second pass.",
        ]) + "\n",
        encoding="utf-8",
    )
    print(f"Organised {len(records)} functions: {ok} decompiled, {missing} missing, {failed} failed")
    print(f"Wrote {root / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
