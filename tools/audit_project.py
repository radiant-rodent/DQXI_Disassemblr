#!/usr/bin/env python3
"""Build a forensic inventory of the DQXI 3DS ROM and this project.

The audit is intentionally independent of the generated asset folders: it reads
the retail image, optionally walks every PACK/PACA archive, and records what is
actually present.  Results are written to ``audit/`` so later extraction work can
be checked against a stable baseline.

Usage:
    python tools/audit_project.py
    python tools/audit_project.py --packs
    python tools/audit_project.py --packs --jobs 8
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import struct
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
AUDIT_DIR = PROJECT_ROOT / "audit"
REFERENCE_ROM = Path(r"..\3DS_Translate\DQXI.3ds")
LOCAL_ROM = PROJECT_ROOT / "original" / "DQXI.3ds"

TEXT_START = 0x00100000
TEXT_END = 0x0072403C


def rom_path() -> Path:
    if LOCAL_ROM.is_file():
        return LOCAL_ROM
    if REFERENCE_ROM.is_file():
        return REFERENCE_ROM
    raise FileNotFoundError("DQXI.3ds not found in original/ or the reference workspace")


def open_romfs():
    """Open the retail image through the read-only reference reader."""
    sys.path.insert(0, r"..\3DS_Translate")
    from dq11tool.ctr.formats import open_image

    f, _ncsd, ncch = open_image(str(rom_path()))
    romfs = ncch.romfs()
    if romfs is None:
        f.close()
        raise RuntimeError("retail image has no RomFS")
    return f, romfs


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def scan_native_functions(binary: Path) -> dict:
    """Count ARM/Thumb entry-point prologues with the same rule as the disassembler."""
    data = binary.read_bytes()
    text = data[: TEXT_END - TEXT_START]
    arm = 0
    thumb = 0
    seen = set()
    for off in range(0, len(text) - 3, 4):
        w = struct.unpack_from("<I", text, off)[0]
        if (w & 0xFFFF4000) == 0xE92D4000:
            arm += 1
            seen.add(TEXT_START + off)
    for off in range(0, len(text) - 1, 2):
        h = struct.unpack_from("<H", text, off)[0]
        if (h & 0xFF00) == 0xB500:
            addr = TEXT_START + off
            if addr not in seen:
                thumb += 1
                seen.add(addr)
    return {
        "binary": str(binary),
        "size": len(data),
        "text_size": len(text),
        "arm_prologues": arm,
        "thumb_prologues": thumb,
        "unique_entry_points": len(seen) + 3,  # three CRT entry points are not prologues
        "sha256": sha256_file(binary),
    }


def classify_file(path: str, first16: bytes) -> str:
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    magic = first16[:4]
    if magic in (b"PACK", b"PACA"):
        return "pack"
    if magic == b"CSTM":
        return "audio_stream"
    if magic == b"CSAR":
        return "audio_archive"
    if magic == b"BCH\x00":
        return "bch_model"
    if magic == b"FLIM":
        return "bflim_texture"
    if magic == b"FLYT":
        return "bflyt_layout"
    if magic == b"FLAN":
        return "bflan_animation"
    if magic == b"CNUT":
        return "cnut_script"
    if magic == b"BXON":
        return "bxon_table"
    return ext or "unknown"


def read_pack_worker(args: tuple[str, str]) -> dict:
    """Parse one PACK/PACA file and return its member list (called in a process)."""
    path, abs_path = args
    try:
        from tools import pack

        data = Path(abs_path).read_bytes()
        p = pack.Pack.parse(data)
        members = []
        for e in p.entries:
            members.append({
                "name": e.name,
                "size": len(e.data),
                "flags": e.flags,
                "magic": e.data[:4].hex(),
            })
        return {"path": path, "ok": True, "compressed": p.compressed, "members": members}
    except Exception as exc:  # audit must continue past individual corrupt packs
        return {"path": path, "ok": False, "error": str(exc), "members": []}


def walk_packs(romfs, files, jobs: int) -> tuple[list[dict], list[dict]]:
    """Parse every PACK/PACA on the RomFS, returning per-pack and flat member records."""
    jobs_list = []
    for rf in files:
        if rf.path.endswith(".pack"):
            jobs_list.append((rf.path, str(rom_path())))
    # The worker needs a path to the file, not the whole 4 GB image, so use a
    # temporary raw RomFS view only when the source is already extracted.
    # Instead, route through a small helper that receives bytes; this keeps the
    # audit correct for both original/romfs.bin and the reference image.
    del jobs_list

    pack_records = []
    members_flat = []
    total = sum(1 for rf in files if rf.path.endswith(".pack"))
    started = time.time()
    print(f"Parsing {total} pack archives with {jobs} workers...")

    # Packs are small relative to the image, so read and parse in batches in
    # this process.  The parser is fast and avoids pickling gigabytes of data.
    from tools import pack as pack_tool

    for i, rf in enumerate((x for x in files if x.path.endswith(".pack")), 1):
        try:
            data = romfs.read_file(rf)
            p = pack_tool.Pack.parse(data)
            rec = {
                "path": rf.path,
                "size": rf.size,
                "compressed": p.compressed,
                "members": [
                    {
                        "name": e.name,
                        "size": len(e.data),
                        "flags": e.flags,
                        "magic": e.data[:4].hex(),
                    }
                    for e in p.entries
                ],
            }
            pack_records.append(rec)
            for m in rec["members"]:
                members_flat.append({"pack": rf.path, **m})
        except Exception as exc:
            pack_records.append({"path": rf.path, "size": rf.size, "ok": False, "error": str(exc), "members": []})
        if i % 500 == 0 or i == total:
            rate = i / max(time.time() - started, 1e-6)
            print(f"  {i}/{total} packs ({rate:.1f}/s)")
    return pack_records, members_flat


def inventory_current_outputs() -> dict:
    """Count generated artifacts without trusting their labels."""
    # The readable tree and the standard-format library are the real outputs;
    # the old game_models/game_textures/... folders are legacy curated views and
    # stay empty after a clean regeneration.  Counting those made the gap report
    # claim nothing had been converted.
    groups = {
        "decomp/ghidra/functions": PROJECT_ROOT / "decomp" / "ghidra" / "functions",
        "decomp/ghidra/recovered": PROJECT_ROOT / "decomp" / "ghidra" / "recovered",
        "decomp/ghidra/by_subsystem": PROJECT_ROOT / "decomp" / "ghidra" / "by_subsystem",
        "decomp/readable": PROJECT_ROOT / "decomp" / "readable",
        "decomp/functions (legacy)": PROJECT_ROOT / "decomp" / "functions",
        "src": PROJECT_ROOT / "src",
        "game_assets/models": PROJECT_ROOT / "game_assets" / "models",
        "game_assets/textures": PROJECT_ROOT / "game_assets" / "textures",
        "game_assets/layouts": PROJECT_ROOT / "game_assets" / "layouts",
        "game_assets/scripts": PROJECT_ROOT / "game_assets" / "scripts",
        "game_assets/tables": PROJECT_ROOT / "game_assets" / "tables",
        "game_assets/audio": PROJECT_ROOT / "game_assets" / "audio",
        "game_assets/maps": PROJECT_ROOT / "game_assets" / "maps",
    }
    out = {}
    for label, root in groups.items():
        info = {"path": str(root), "exists": root.exists(), "files": 0, "bytes": 0, "by_ext": {}}
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file():
                    ext = p.suffix.lower() or "<none>"
                    info["files"] += 1
                    info["bytes"] += p.stat().st_size
                    info["by_ext"][ext] = info["by_ext"].get(ext, 0) + 1
        out[label] = info
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packs", action="store_true", help="Parse every PACK/PACA and inventory members")
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 4))
    args = parser.parse_args()

    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    src = rom_path()
    print(f"Reading retail image: {src}")
    f, romfs = open_romfs()
    try:
        files = list(romfs.files)
        total_bytes = sum(x.size for x in files)
        by_ext = collections.Counter()
        by_top = collections.Counter()
        magic_counts = collections.Counter()
        records = []
        for i, rf in enumerate(files, 1):
            head = romfs.read_file(rf, 0, min(16, rf.size))
            ext = rf.path.rsplit(".", 1)[-1].lower() if "." in rf.path else ""
            top = rf.path.strip("/").split("/", 1)[0]
            by_ext[ext] += 1
            by_top[top] += 1
            kind = classify_file(rf.path, head)
            magic_counts[kind] += 1
            records.append({
                "path": rf.path,
                "size": rf.size,
                "offset": rf.offset,
                "extension": ext,
                "top": top,
                "magic": head[:4].hex(),
                "kind": kind,
            })
            if i % 5000 == 0:
                print(f"  {i}/{len(files)} RomFS files")

        manifest = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_image": str(src),
            "source_image_sha256": sha256_file(src),
            "romfs_file_count": len(files),
            "romfs_total_bytes": total_bytes,
            "by_extension": dict(by_ext.most_common()),
            "by_top_directory": dict(by_top.most_common()),
            "by_kind": dict(magic_counts.most_common()),
            "files": records,
        }
        (AUDIT_DIR / "romfs_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        code = PROJECT_ROOT / "original" / "exefs" / "code.decompressed.bin"
        native = scan_native_functions(code) if code.is_file() else {"error": "missing code.decompressed.bin"}
        outputs = inventory_current_outputs()
        baseline = {
            "generated_at": manifest["generated_at"],
            "native": native,
            "outputs": outputs,
        }
        (AUDIT_DIR / "baseline.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")

        if args.packs:
            packs, members = walk_packs(romfs, files, args.jobs)
            (AUDIT_DIR / "pack_manifest.json").write_text(json.dumps(packs, indent=2), encoding="utf-8")
            with open(AUDIT_DIR / "pack_members.jsonl", "w", encoding="utf-8") as out:
                for m in members:
                    out.write(json.dumps(m) + "\n")
            member_ext = collections.Counter(
                (m["name"].rsplit(".", 1)[-1].lower() if "." in m["name"] else "<none>")
                for m in members
            )
            (AUDIT_DIR / "pack_summary.json").write_text(json.dumps({
                "packs": len(packs),
                "members": len(members),
                "member_bytes": sum(m["size"] for m in members),
                "by_extension": dict(member_ext.most_common()),
                "errors": [p for p in packs if not p.get("ok", True)][:100],
            }, indent=2), encoding="utf-8")

        # Human-readable summary that can be cited by later work.
        lines = [
            "# DQXI 3DS Project Audit",
            "",
            f"- Source image: `{src}`",
            f"- Image SHA-256: `{manifest['source_image_sha256']}`",
            f"- RomFS files: **{len(files):,}**",
            f"- RomFS bytes: **{total_bytes:,}**",
            f"- Native entry points: **{native.get('unique_entry_points', 'unknown')}**",
            "",
            "## RomFS Top-Level Directories",
            "",
            "| Directory | Files |",
            "|---|---:|",
        ]
        for name, count in by_top.most_common(30):
            lines.append(f"| `{name}/` | {count:,} |")
        lines += ["", "## RomFS File Kinds", "", "| Kind | Files |", "|---|---:|"]
        for name, count in magic_counts.most_common(30):
            lines.append(f"| `{name}` | {count:,} |")
        lines += ["", "## Current Generated Outputs", "", "| Group | Files | MiB |", "|---|---:|---:|"]
        for name, info in outputs.items():
            lines.append(f"| `{name}` | {info['files']:,} | {info['bytes'] / 1024 / 1024:.1f} |")

        pack_summary_path = AUDIT_DIR / "pack_summary.json"
        if pack_summary_path.is_file():
            ps = json.loads(pack_summary_path.read_text(encoding="utf-8"))
            lines += [
                "",
                "## Archive Members (PACK/PACA)",
                "",
                f"- Archives: **{ps.get('packs', 0):,}**",
                f"- Members: **{ps.get('members', 0):,}**",
                f"- Member bytes: **{ps.get('member_bytes', 0):,}**",
                f"- Parse errors: **{len(ps.get('errors', [])):,}**",
                "",
                "| Extension | Members |",
                "|---|---:|",
            ]
            # pack_summary.json calls this field by_extension; accept the older
            # member_extensions spelling too so the counts never silently read 0.
            ext_counts = ps.get("member_extensions") or ps.get("by_extension", {})
            for ext, count in list(ext_counts.items())[:30]:
                lines.append(f"| `.${ext}` | {count:,} |")
            bch_src = ext_counts.get("bch", 0) + magic_counts.get("bch_model", 0)
            bxon_src = ext_counts.get("bxon", 0)
            cnut_src = ext_counts.get("cnut", 0)
            bcstm_src = magic_counts.get("audio_stream", 0)
            bch_out = outputs.get("game_assets/models", {}).get("by_ext", {}).get(".gltf", 0)
            bxon_out = outputs.get("game_assets/tables", {}).get("by_ext", {}).get(".json", 0)
            # game_assets/scripts holds the assembly listing (script.nut) and the
            # readable decompile (script.decompiled.nut); only the first is the
            # one-to-one conversion of a CNUT source file.
            cnut_all = outputs.get("game_assets/scripts", {}).get("by_ext", {}).get(".nut", 0)
            cnut_readable = sum(1 for _ in (PROJECT_ROOT / "game_assets" / "scripts").rglob("*.decompiled.nut"))
            cnut_out = max(0, cnut_all - cnut_readable)
            wav_out = outputs.get("game_assets/audio", {}).get("by_ext", {}).get(".wav", 0)
            lines += [
                "",
                "### Coverage Examples",
                "",
                "| Asset family | Source count | Current converted count | Coverage |",
                "|---|---:|---:|---:|",
                f"| BCH models | {bch_src:,} | {bch_out:,} glTF | {100 * bch_out / max(1, bch_src):.1f}% |",
                f"| BXON tables | {bxon_src:,} | {bxon_out:,} JSON | {100 * bxon_out / max(1, bxon_src):.1f}% |",
                f"| CNUT scripts | {cnut_src:,} | {cnut_out:,} `.nut` | {100 * cnut_out / max(1, cnut_src):.1f}% |",
                f"| BCSTM streams | {bcstm_src:,} | {wav_out:,} WAV | {100 * wav_out / max(1, bcstm_src):.1f}% |",
            ]

        lines += [
            "",
            "## Initial Gap Assessment",
            "",
            "The audit deliberately separates *inventory* from *conversion*. A non-zero file count in an output",
            "folder does not prove that every RomFS source was converted, that duplicate copies are absent, or that",
            "the output is editable. Later extraction reports must reconcile against the manifests in this folder.",
        ]
        (AUDIT_DIR / "GAP_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

        print(f"\nWrote {AUDIT_DIR / 'romfs_manifest.json'}")
        print(f"Wrote {AUDIT_DIR / 'baseline.json'}")
        print(f"Wrote {AUDIT_DIR / 'GAP_REPORT.md'}")
        if args.packs:
            print(f"Wrote {AUDIT_DIR / 'pack_manifest.json'}")
            print(f"Wrote {AUDIT_DIR / 'pack_members.jsonl'}")
        return 0
    finally:
        f.close()


if __name__ == "__main__":
    raise SystemExit(main())
