#!/usr/bin/env python3
"""tools/disasm_tables.py - Disassemble BXON binary tables from RomFS into human-readable JSON.

Extracts and parses all .bxon tables across core packs (battle, field, system, UI)
into structured, human-readable JSON definitions in game_tables/<pack_name>/<table_name>.json
"""

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import pack, bxon

TABLES_OUT = PROJECT_ROOT / "game_tables"


def read_romfs():
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    f, ncsd, ncch = open_image(r"..\reference project\DQXI.3ds")
    romfs = ncch.romfs()
    return f, romfs


def main():
    parser = argparse.ArgumentParser(description="Disassemble DQXI 3DS BXON Tables into JSON")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of packs to process")
    parser.add_argument("--out", type=Path, default=TABLES_OUT, help="Output directory for JSON tables")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    f, romfs = read_romfs()

    # Core packs containing essential game parameter tables
    core_pack_paths = [
        "/battlecmn.pack",
        "/fieldcmn.pack",
        "/syscmn.pack",
        "/gamecmn.pack",
        "/divecmn.pack",
        "/2dcmn.pack",
    ]
    if args.limit:
        core_pack_paths = core_pack_paths[:args.limit]

    print(f"Disassembling parameter tables from {len(core_pack_paths)} packs into {args.out}...")
    total_tables = 0

    for path in core_pack_paths:
        rf = next((x for x in romfs.files if x.path == path), None)
        if not rf:
            continue
        pack_name = Path(path).stem
        pack_dir = args.out / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)

        data = romfs.read_file(rf)
        if not pack.Pack.is_pack(data):
            continue

        p = pack.Pack.parse(data)
        for entry in p.entries:
            if entry.name.endswith(".bxon"):
                try:
                    table = bxon.Bxon.parse(entry.data)
                    table_json = table.to_json()
                    out_path = pack_dir / (Path(entry.name).stem + ".json")
                    out_path.write_text(table_json, encoding="utf-8")
                    total_tables += 1
                except Exception as e:
                    err_path = pack_dir / (Path(entry.name).stem + ".error.txt")
                    err_path.write_text(f"Table parse error: {e}", encoding="utf-8")

        print(f"  [OK] Processed {pack_name} (Extracted {total_tables} tables)")

    f.close()
    print(f"Disassembly complete! Disassembled {total_tables} BXON tables into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
