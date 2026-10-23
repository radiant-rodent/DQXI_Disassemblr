#!/usr/bin/env python3
"""Convert every extracted DQXI asset into a standard, browsable format.

Sources are the files under ``game_data`` created by ``extract_game_data.py`` and
``extract_arcs.py``. Outputs go to ``game_assets`` and are never mixed with the
original bytes.

Families:
  textures  BFLIM -> PNG (+ metadata)
  layouts   BFLYT/BFLAN -> JSON
  models    BCH -> glTF 2.0 + OBJ (+ embedded textures)
  scripts   CNUT -> Squirrel disassembly
  tables    BXON -> JSON (string values + structural information)
  audio     BCSTM -> RIFF WAV; BCSAR members -> unpacked

Usage:
    python tools/convert_assets.py --all
    python tools/convert_assets.py --textures --layouts
    python tools/convert_assets.py --models --workers 8
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, r"..\reference project")

DATA_DIR = PROJECT_ROOT / "game_data"
ASSETS_DIR = PROJECT_ROOT / "game_assets"


def rel_safe(src: Path) -> Path:
    return src.relative_to(DATA_DIR)


def write_manifest(name: str, rows: list[dict], errors: list[dict]) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ASSETS_DIR / f"{name}_manifest.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (ASSETS_DIR / f"{name}_summary.json").write_text(json.dumps({
        "files": len(rows),
        "errors": errors[:200],
        "error_count": len(errors),
        "by_extension": dict(collections.Counter(
            (r.get("output_ext") or (r.get("output", "").rsplit(".", 1)[-1].lower() if "." in r.get("output", "") else "<none>"))
            for r in rows
        ).most_common()),
    }, indent=2), encoding="utf-8")


# --------------------------------------------------------------------------- textures
def convert_textures(workers: int) -> tuple[list[dict], list[dict]]:
    from tools.texture_tool import bflim_to_png

    srcs = sorted((DATA_DIR / "arcs").rglob("*.bflim"))
    out_root = ASSETS_DIR / "textures"
    rows, errors = [], []
    print(f"Converting {len(srcs):,} BFLIM textures...")
    started = time.time()

    def work(src: Path):
        rel = rel_safe(src)
        out = (out_root / rel).with_suffix(".png")
        info = bflim_to_png(src.read_bytes(), out)
        return {"source": str(rel), "output": str(out.relative_to(PROJECT_ROOT)), **info}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, s): s for s in srcs}
        for i, fut in enumerate(as_completed(futures), 1):
            s = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:
                errors.append({"source": str(rel_safe(s)), "error": str(exc)})
            if i % 250 == 0 or i == len(srcs):
                print(f"  {i}/{len(srcs)} textures ({i / max(time.time() - started, 1e-6):.0f}/s)")
    rows.sort(key=lambda r: r["source"])
    write_manifest("textures", rows, errors)
    return rows, errors


# --------------------------------------------------------------------------- layouts
def convert_layouts(workers: int) -> tuple[list[dict], list[dict]]:
    from tools.layout_tool import parse_bflan, parse_bflyt

    srcs = sorted((DATA_DIR / "arcs").rglob("*.bflyt")) + sorted((DATA_DIR / "arcs").rglob("*.bflan"))
    out_root = ASSETS_DIR / "layouts"
    rows, errors = [], []
    print(f"Converting {len(srcs):,} BFLYT/BFLAN files...")
    started = time.time()

    def work(src: Path):
        rel = rel_safe(src)
        out = (out_root / rel).with_suffix(rel.suffix + ".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        data = parse_bflyt(src.read_bytes()) if src.suffix.lower() == ".bflyt" else parse_bflan(src.read_bytes())
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"source": str(rel), "output": str(out.relative_to(PROJECT_ROOT)), "format": data.get("format")}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, s): s for s in srcs}
        for i, fut in enumerate(as_completed(futures), 1):
            s = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:
                errors.append({"source": str(rel_safe(s)), "error": str(exc)})
            if i % 250 == 0 or i == len(srcs):
                print(f"  {i}/{len(srcs)} layouts ({i / max(time.time() - started, 1e-6):.0f}/s)")
    rows.sort(key=lambda r: r["source"])
    write_manifest("layouts", rows, errors)
    return rows, errors


# --------------------------------------------------------------------------- scripts
def convert_scripts(workers: int) -> tuple[list[dict], list[dict]]:
    from tools import sqbin

    srcs = sorted((DATA_DIR / "packs").rglob("*.cnut"))
    out_root = ASSETS_DIR / "scripts"
    rows, errors = [], []
    print(f"Disassembling {len(srcs):,} CNUT scripts...")

    def work(src: Path):
        rel = rel_safe(src)
        out = (out_root / rel).with_suffix(".nut")
        out.parent.mkdir(parents=True, exist_ok=True)
        func = sqbin.parse(src.read_bytes())
        text = sqbin.disasm(func)
        out.write_text(text, encoding="utf-8")
        rebuilt = sqbin.build(sqbin.parse(src.read_bytes()))
        return {
            "source": str(rel),
            "output": str(out.relative_to(PROJECT_ROOT)),
            "roundtrip": rebuilt == src.read_bytes(),
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, s): s for s in srcs}
        for i, fut in enumerate(as_completed(futures), 1):
            s = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:
                errors.append({"source": str(rel_safe(s)), "error": str(exc)})
            if i % 100 == 0 or i == len(srcs):
                print(f"  {i}/{len(srcs)} scripts")
    rows.sort(key=lambda r: r["source"])
    write_manifest("scripts", rows, errors)
    return rows, errors


# --------------------------------------------------------------------------- tables
def convert_tables(workers: int) -> tuple[list[dict], list[dict]]:
    from tools import bxon
    from tools.bxon_struct import StructDecoder

    srcs = sorted((DATA_DIR / "packs").rglob("*.bxon"))
    out_root = ASSETS_DIR / "tables"
    rows, errors = [], []
    map_types = {"Level3DBin", "Level2DBin", "LevelDMapBin"}
    print(f"Decoding {len(srcs):,} BXON tables...")

    def work(src: Path):
        rel = rel_safe(src)
        out = (out_root / rel).with_suffix(".json")
        out.parent.mkdir(parents=True, exist_ok=True)
        raw = src.read_bytes()
        table = bxon.Bxon.parse(raw)
        if table.type_name in map_types:
            payload = table.to_json()
            mode = "string-index"
        else:
            payload = json.dumps(StructDecoder(raw).decode(), indent=2, ensure_ascii=False)
            mode = "structural"
        out.write_text(payload, encoding="utf-8")
        return {
            "source": str(rel),
            "output": str(out.relative_to(PROJECT_ROOT)),
            "type": table.type_name,
            "strings": len(table.strings),
            "mode": mode,
        }

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, s): s for s in srcs}
        for i, fut in enumerate(as_completed(futures), 1):
            s = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:
                errors.append({"source": str(rel_safe(s)), "error": str(exc)})
            if i % 250 == 0 or i == len(srcs):
                print(f"  {i}/{len(srcs)} tables")
    rows.sort(key=lambda r: r["source"])
    write_manifest("tables", rows, errors)
    return rows, errors


# --------------------------------------------------------------------------- audio
def convert_audio(workers: int) -> tuple[list[dict], list[dict]]:
    from tools.audio_tool import bcstm_to_wav, unpack_bcsar

    srcs = sorted((DATA_DIR / "romfs").rglob("*.bcstm"))
    out_root = ASSETS_DIR / "audio"
    rows, errors = [], []
    print(f"Decoding {len(srcs):,} BCSTM streams to WAV...")
    started = time.time()

    def work(src: Path):
        rel = rel_safe(src)
        out = (out_root / rel).with_suffix(".wav")
        out.parent.mkdir(parents=True, exist_ok=True)
        bcstm_to_wav(src.read_bytes(), out)
        return {"source": str(rel), "output": str(out.relative_to(PROJECT_ROOT)), "bytes": out.stat().st_size}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, s): s for s in srcs}
        for i, fut in enumerate(as_completed(futures), 1):
            s = futures[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:
                errors.append({"source": str(rel_safe(s)), "error": str(exc)})
            if i % 250 == 0 or i == len(srcs):
                print(f"  {i}/{len(srcs)} streams ({i / max(time.time() - started, 1e-6):.0f}/s)")
    rows.sort(key=lambda r: r["source"])
    write_manifest("audio", rows, errors)
    # Sound-project archives (BCSAR) are small; unpack them next to the streams so
    # the standard-format tree is self-contained.
    for bcsar in sorted((DATA_DIR / "romfs" / "sound").rglob("*.bcsar")):
        try:
            unpack_bcsar(bcsar.read_bytes(), out_root / "archives" / bcsar.stem)
        except Exception as exc:
            errors.append({"source": str(rel_safe(bcsar)), "error": str(exc)})
    return rows, errors


# --------------------------------------------------------------------------- models
def _convert_model(src: Path) -> dict | None:
    """One BCH -> OBJ + glTF. Module level so worker processes can run it."""
    from tools.model_tool import BchParser, export_to_gltf, export_to_obj

    rel = rel_safe(src)
    stem = src.stem
    target = ASSETS_DIR / "models" / rel.parent / stem
    parser = BchParser(src.read_bytes(), source_path=src)
    models = parser.parse_models(stem)
    meshes = sum(len(m.meshes) for m in models)
    if not any(m.meshes for m in models):
        return None
    target.mkdir(parents=True, exist_ok=True)
    for m in models:
        if m.meshes:
            export_to_obj(m, target / f"{stem}.obj")
            export_to_gltf(m, target / f"{stem}.gltf")
    return {
        "source": str(rel),
        "output": str(target.relative_to(PROJECT_ROOT)),
        "output_ext": "gltf",
        "models": len(models),
        "meshes": meshes,
        "vertices": sum(len(g.positions) for m in models for g in m.meshes),
        "triangles": sum(len(g.indices) // 3 for m in models for g in m.meshes),
    }


def _convert_model_batch(srcs: list[Path]) -> list[tuple[str, dict | None, str | None]]:
    out = []
    for src in srcs:
        try:
            out.append((str(src), _convert_model(src), None))
        except Exception as exc:  # reported per file, the batch goes on
            out.append((str(src), None, str(exc)))
    return out


def _warm_model_worker() -> None:
    # load the material/skin manifests once per process, not once per file
    from tools.model_tool import load_material_map, load_skin_map

    load_material_map()
    load_skin_map()


def convert_models(workers: int) -> tuple[list[dict], list[dict]]:
    srcs = sorted((DATA_DIR / "packs").rglob("*.bch")) + sorted((DATA_DIR / "romfs").rglob("*.bch"))
    rows, errors = [], []
    print(f"Converting {len(srcs):,} BCH model files...")
    started = time.time()

    # Parsing is pure Python, so threads would share one core (GIL): use processes.
    # Big files first and small batches, so no worker is left with a long tail.
    srcs.sort(key=lambda s: s.stat().st_size, reverse=True)
    batches = [srcs[i:i + 8] for i in range(0, len(srcs), 8)]
    done = 0
    with ProcessPoolExecutor(max_workers=workers, initializer=_warm_model_worker) as pool:
        for fut in as_completed([pool.submit(_convert_model_batch, b) for b in batches]):
            for src, row, error in fut.result():
                done += 1
                if row:
                    rows.append(row)
                if error and len(errors) < 500:
                    errors.append({"source": str(rel_safe(Path(src))), "error": error})
                if done % 250 == 0 or done == len(srcs):
                    print(f"  {done}/{len(srcs)} BCH ({done / max(time.time() - started, 1e-6):.0f}/s)")
    rows.sort(key=lambda r: r["source"])
    write_manifest("models", rows, errors)
    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("textures", "layouts", "scripts", "tables", "audio", "models"):
        parser.add_argument(f"--{name}", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 4))
    args = parser.parse_args()
    selected = [n for n in ("textures", "layouts", "scripts", "tables", "audio", "models") if getattr(args, n)]
    if args.all or not selected:
        selected = ["textures", "layouts", "scripts", "tables", "audio", "models"]

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    summary = {}
    for name in selected:
        fn = globals()[f"convert_{name}"]
        rows, errors = fn(args.workers)
        summary[name] = {"outputs": len(rows), "errors": len(errors)}
        print(f"  -> {name}: {len(rows):,} outputs, {len(errors)} errors\n")
    (ASSETS_DIR / "conversion_run.json").write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - started, 1),
        "families": summary,
    }, indent=2), encoding="utf-8")
    print(f"Conversion complete in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
