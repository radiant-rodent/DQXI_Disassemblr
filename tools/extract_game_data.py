#!/usr/bin/env python3
"""Extract the complete DQXI 3DS RomFS and every PACK/PACA member.

Layout produced:

    game_data/
      romfs/                 # exact RomFS tree, files byte-for-byte as shipped
      packs/<pack path>/     # every PACK/PACA entry exploded by its stored name
      manifest.json          # machine-readable inventory
      README.md              # what this tree is, and how to rebuild it

The original `.pack` files are always kept in ``game_data/romfs``.  The exploded
copies are for browsing/editing; a later patch step re-encodes a PACK from its
exploded directory.

Usage:
    python tools/extract_game_data.py --all
    python tools/extract_game_data.py --raw
    python tools/extract_game_data.py --packs --workers 8
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import pack as pack_tool

DATA_DIR = PROJECT_ROOT / "game_data"
ROMFS_DIR = DATA_DIR / "romfs"
PACK_DIR = DATA_DIR / "packs"
READ_LOCK = threading.Lock()
REFERENCE_ROM = Path(r"..\reference project\DQXI.3ds")
LOCAL_ROM = PROJECT_ROOT / "original" / "DQXI.3ds"


def rom_path() -> Path:
    if LOCAL_ROM.is_file():
        return LOCAL_ROM
    if REFERENCE_ROM.is_file():
        return REFERENCE_ROM
    raise FileNotFoundError("DQXI.3ds not found")


def open_romfs():
    sys.path.insert(0, r"..\reference project")
    from dq11tool.ctr.formats import open_image

    f, _ncsd, ncch = open_image(str(rom_path()))
    romfs = ncch.romfs()
    if romfs is None:
        f.close()
        raise RuntimeError("retail image has no RomFS")
    return f, romfs


def safe_rel(path: str) -> Path:
    """Turn an archive path into a relative path that cannot escape the output root."""
    p = Path(path.lstrip("/"))
    parts = [x for x in p.parts if x not in ("", ".", "..")]
    return Path(*parts) if parts else Path("unnamed")


def extract_raw(romfs) -> dict:
    """Write the exact RomFS tree and return per-file records."""
    ROMFS_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    files = list(romfs.files)
    started = time.time()
    print(f"Extracting {len(files)} RomFS files to {ROMFS_DIR} ...")
    for i, rf in enumerate(files, 1):
        rel = safe_rel(rf.path)
        out = ROMFS_DIR / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(romfs.read_file(rf))
        records.append({"path": rf.path, "size": rf.size, "extracted": str(out.relative_to(PROJECT_ROOT))})
        if i % 2000 == 0 or i == len(files):
            print(f"  {i}/{len(files)} files ({i / max(time.time() - started, 1e-6):.0f}/s)")
    return {"files": records, "bytes": sum(r["size"] for r in records)}


def extract_one_pack(romfs, rf) -> tuple[dict, list[dict]]:
    """Extract one pack. Returns (pack record, member records)."""
    # RomFs wraps one shared file object, so reads must be serialized even when
    # parsing/writing runs in parallel.
    with READ_LOCK:
        data = romfs.read_file(rf)
    p = pack_tool.Pack.parse(data)
    rel = safe_rel(rf.path)
    stem = rel.with_suffix("") if rel.suffix.lower() == ".pack" else rel / "_pack"
    target = PACK_DIR / stem
    members = []
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for e in p.entries:
        member_rel = safe_rel(e.name)
        out = target / member_rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(e.data)
        members.append({
            "pack": rf.path,
            "name": e.name,
            "size": len(e.data),
            "flags": e.flags,
            "header_size": e.header_size,
            "align": e.align,
            "extracted": str(out.relative_to(PROJECT_ROOT)),
            "magic": e.data[:4].hex(),
        })
    meta = {
        "path": rf.path,
        "size": rf.size,
        "compressed": p.compressed,
        "target": str(target.relative_to(PROJECT_ROOT)),
        "members": len(p.entries),
    }
    (target / "_pack.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta, members


def extract_packs(romfs, workers: int) -> tuple[list[dict], list[dict]]:
    PACK_DIR.mkdir(parents=True, exist_ok=True)
    packs = [rf for rf in romfs.files if rf.path.endswith(".pack")]
    print(f"Exploding {len(packs)} PACK/PACA archives to {PACK_DIR} with {workers} workers ...")
    pack_records: list[dict] = []
    member_records: list[dict] = []
    started = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(extract_one_pack, romfs, rf): rf for rf in packs}
        for i, fut in enumerate(as_completed(futures), 1):
            rf = futures[fut]
            try:
                meta, members = fut.result()
                pack_records.append(meta)
                member_records.extend(members)
            except Exception as exc:
                pack_records.append({"path": rf.path, "size": rf.size, "error": str(exc)})
                print(f"  [ERROR] {rf.path}: {exc}")
            if i % 500 == 0 or i == len(packs):
                print(f"  {i}/{len(packs)} packs ({i / max(time.time() - started, 1e-6):.0f}/s)")
    pack_records.sort(key=lambda x: x["path"])
    member_records.sort(key=lambda x: (x["pack"], x["name"]))
    return pack_records, member_records


def write_docs(manifest: dict) -> None:
    ex = manifest.get("member_extensions", {})
    lines = [
        "# DQXI 3DS Extracted Game Data",
        "",
        "This directory is the single browsable home for the game's data.",
        "",
        "| Directory | Contents |",
        "|---|---|",
        "| `romfs/` | Exact RomFS tree. Original `.pack`/`.paca` containers are preserved byte-for-byte. |",
        "| `packs/` | Every archive member exploded by its stored name, ready to inspect or edit. |",
        "",
        "## Counts",
        "",
        f"- RomFS files: **{manifest.get('romfs_files', 0):,}**",
        f"- RomFS bytes: **{manifest.get('romfs_bytes', 0):,}**",
        f"- PACK/PACA archives: **{manifest.get('packs', 0):,}**",
        f"- Exploded members: **{manifest.get('members', 0):,}**",
        f"- Member bytes: **{manifest.get('member_bytes', 0):,}**",
        "",
        "## Member Types",
        "",
        "| Extension | Files |",
        "|---|---:|",
    ]
    for ext, count in sorted(ex.items(), key=lambda kv: -kv[1]):
        lines.append(f"| `.{ext}` | {count:,} |" if ext != "<none>" else f"| *(no extension)* | {count:,} |")
    lines += [
        "",
        "## Rebuilding",
        "",
        "`game_data/romfs/` is the authoritative source for the repacker. To change an archive,",
        "edit `game_data/packs/<archive>/...` and run the patch/rebuild command (see the project",
        "README). Never edit the retail ROM or the reference translation workspace.",
    ]
    (DATA_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", action="store_true", help="Extract the exact RomFS tree")
    parser.add_argument("--packs", action="store_true", help="Explode every PACK/PACA archive")
    parser.add_argument("--all", action="store_true", help="Do both (default if no flags)")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    args = parser.parse_args()
    do_raw = args.raw or args.all or not (args.raw or args.packs or args.all)
    do_packs = args.packs or args.all or not (args.raw or args.packs or args.all)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    f, romfs = open_romfs()
    try:
        raw = extract_raw(romfs) if do_raw else None
        packs = members = None
        if do_packs:
            packs, members = extract_packs(romfs, args.workers)
        manifest_path = DATA_DIR / "manifest.json"
        previous = {}
        if manifest_path.is_file():
            try:
                previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                previous = {}
        exts = collections.Counter(
            (m["name"].rsplit(".", 1)[-1].lower() if "." in m["name"] else "<none>")
            for m in (members or previous.get("member_records", []))
        )
        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_image": str(rom_path()),
            "romfs_files": len(raw["files"]) if raw else previous.get("romfs_files", 0),
            "romfs_bytes": raw["bytes"] if raw else previous.get("romfs_bytes", 0),
            "packs": len(packs) if packs is not None else previous.get("packs", 0),
            "members": len(members) if members is not None else previous.get("members", 0),
            "member_bytes": sum(m["size"] for m in members) if members is not None else previous.get("member_bytes", 0),
            "member_extensions": dict(exts) if exts else previous.get("member_extensions", {}),
            "raw_records": raw["files"] if raw else previous.get("raw_records", []),
            "pack_records": packs if packs is not None else previous.get("pack_records", []),
            "member_records": members if members is not None else previous.get("member_records", []),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        write_docs(manifest)
        print(f"\nWrote {manifest_path}")
        print(f"Wrote {DATA_DIR / 'README.md'}")
        return 0
    finally:
        f.close()


if __name__ == "__main__":
    raise SystemExit(main())
