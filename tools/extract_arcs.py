#!/usr/bin/env python3
"""Explode every SARC (``.arc``) member already extracted from DQXI PACK files.

DQXI's UI packs contain one SARC per pack.  The SARC holds ``blyt/*.bflyt``,
``anim/*.bflan``, ``timg/*.bflim`` and other NW4C resources.  This tool keeps the
original ``.arc`` bytes and writes the members to a browsable tree.

Usage:
    python tools/extract_arcs.py
"""
from __future__ import annotations

import argparse
import collections
import json
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, r"..\reference project")

from dq11tool.darc import Sarc

PACKS_DIR = PROJECT_ROOT / "game_data" / "packs"
ARCS_DIR = PROJECT_ROOT / "game_data" / "arcs"


def safe_rel(name: str) -> Path:
    p = Path(name.lstrip("/"))
    parts = [x for x in p.parts if x not in ("", ".", "..")]
    return Path(*parts) if parts else Path("unnamed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PACKS_DIR)
    parser.add_argument("--out", type=Path, default=ARCS_DIR)
    args = parser.parse_args()

    arcs = sorted(args.source.rglob("*.arc"))
    print(f"Found {len(arcs)} SARC archives under {args.source}")
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    errors = []
    started = time.time()
    for i, arc in enumerate(arcs, 1):
        rel = arc.relative_to(args.source)
        target = args.out / rel.with_suffix("")
        try:
            raw = arc.read_bytes()
            sarc = Sarc.parse(raw)
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            members = []
            for node in sarc.nodes:
                data = raw[sarc.data_offset + node.start:sarc.data_offset + node.end]
                out = target / safe_rel(node.name)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
                members.append({
                    "name": node.name,
                    "size": len(data),
                    "magic": data[:4].hex(),
                    "path": str(out.relative_to(PROJECT_ROOT)),
                })
            meta = {
                "source": str(arc.relative_to(PROJECT_ROOT)),
                "target": str(target.relative_to(PROJECT_ROOT)),
                "members": members,
            }
            (target / "_arc.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            records.append({"arc": str(rel), "members": len(members)})
        except Exception as exc:
            errors.append({"arc": str(rel), "error": str(exc)})
            print(f"  [ERROR] {rel}: {exc}")
        if i % 50 == 0 or i == len(arcs):
            print(f"  {i}/{len(arcs)} archives ({i / max(time.time() - started, 1e-6):.0f}/s)")

    ext = collections.Counter()
    for rec in records:
        target = args.out / Path(rec["arc"]).with_suffix("")
        for p in target.rglob("*"):
            if p.is_file() and p.name != "_arc.json":
                ext[p.suffix.lower() or "<none>"] += 1
    summary = {
        "archives": len(records),
        "errors": errors,
        "members": sum(r["members"] for r in records),
        "by_extension": dict(ext.most_common()),
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Exploded {summary['members']:,} SARC members; {len(errors)} errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
