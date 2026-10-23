#!/usr/bin/env python3
"""tools/disasm_scripts.py - Disassemble all Squirrel scripts from RomFS into human-readable .nut source.

Disassembles all .cnut bytecode scripts inside RomFS packs into structured,
human-readable Squirrel scripts (.nut) with function trees, parameters,
local variable scopes, and literal strings.

Outputs to game_scripts/<pack_name>/<script_name>.nut
"""

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import blz, pack, sqbin

ROMFS_BIN = PROJECT_ROOT / "original" / "romfs.bin"
SCRIPTS_OUT = PROJECT_ROOT / "game_scripts"


def read_romfs_files(romfs_path: Path):
    """Parse RomFS IVFC filesystem to read files."""
    # Using the extraction utility or reference project open_image
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    f, ncsd, ncch = open_image(r"..\reference project\DQXI.3ds")
    romfs = ncch.romfs()
    return f, romfs


def main():
    parser = argparse.ArgumentParser(description="Disassemble DQXI 3DS Squirrel Scripts")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of script packs to process")
    parser.add_argument("--out", type=Path, default=SCRIPTS_OUT, help="Output directory for disassembled scripts")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    f, romfs = read_romfs_files(ROMFS_BIN)

    script_files = [x for x in romfs.files if x.path.startswith("/script/") and x.path.endswith(".pack")]
    if args.limit:
        script_files = script_files[:args.limit]

    print(f"Disassembling {len(script_files)} script packs into {args.out}...")
    total_scripts = 0

    for i, rf in enumerate(script_files):
        pack_name = Path(rf.path).stem
        pack_data = romfs.read_file(rf)
        if not pack.Pack.is_pack(pack_data):
            continue

        p = pack.Pack.parse(pack_data)
        pack_dir = args.out / pack_name
        pack_dir.mkdir(parents=True, exist_ok=True)

        for entry in p.entries:
            if entry.name.endswith(".cnut"):
                try:
                    func = sqbin.parse(entry.data)
                    disassembled_code = sqbin.disasm(func)
                    out_path = pack_dir / (Path(entry.name).stem + ".nut")
                    out_path.write_text(disassembled_code, encoding="utf-8")
                    total_scripts += 1
                except Exception as e:
                    # Write disassembly error notice
                    err_path = pack_dir / (Path(entry.name).stem + ".error.txt")
                    err_path.write_text(f"Disassembly error: {e}", encoding="utf-8")

        if (i + 1) % 10 == 0 or i + 1 == len(script_files):
            print(f"  [{i+1}/{len(script_files)}] Processed {pack_name} (Total scripts disassembled: {total_scripts})")

    f.close()
    print(f"Disassembly complete! Disassembled {total_scripts} scripts into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
