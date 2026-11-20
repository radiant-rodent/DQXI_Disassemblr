#!/usr/bin/env python3
"""Export every BCH file that has no 3D mesh: images and animations, organised by what they are.

``tools/convert_assets.py --models`` writes OBJ/glTF only for BCH files that contain meshes (4,779 of 10,542).
The other 5,763 hold no geometry at all (checked with the BCH content table):

* image-only BCH (3,764): UI icons/art packed as BCH, the 2D mode's character sprites and map tile sheets,
  2D battle enemies/backgrounds/effects, 2D effect sheets, weather overlays;
* animation-only BCH (1,998): character motions (``3d/motion``), cutscene animations (``3d/cs``: skeletons,
  camera paths, visibility and material tracks), a battle camera;
* a couple of scene-setup files (lights, fog, shaders).

Outputs, grouped so the editor shows a handful of packs instead of thousands of folders:

    game_assets/textures/ui/<ui folder>/...           UI images; join the UI pack of the same name (Textures panel)
    game_assets/textures/2d_sprites/                  2D-mode character sprite sheets
    game_assets/textures/2d_tilesets/<map>/           raw 2D map tile sheets (rendered maps: tools/map2d.py -> 2d_maps)
    game_assets/textures/2d_battle_enemies/           2D battle enemy sprites
    game_assets/textures/2d_battle_backgrounds/       2D battle backgrounds
    game_assets/textures/2d_battle_effects/           2D battle effect sheets (parts_effect)
    game_assets/textures/2d_battle_enemy_anims/       per-enemy 2D animation sheets
    game_assets/textures/2d_battle_common/            shared 2D battle sheets
    game_assets/textures/2d_effects/                  field 2D effect sheets (effect2d)
    game_assets/textures/2d_weather/                  weather overlays
    game_assets/textures/2d_common/                   2dcmn
    game_assets/textures/misc_bch/                    the few remaining image BCH (syscmn, gamecmn)
    game_assets/animations/motions/<set>.json         character motion sets (3d/motion/<set>/motion_*.bch)
    game_assets/animations/cutscenes/<kind>/<id>.json cutscene animation (scenario, combination, skill, item)
    game_assets/animations/battle/, misc/             the rest
    game_assets/bch_index.json                        every BCH source: what it contains and where it went

One PNG per texture: ``<pack>/<bch name>.png`` when the BCH holds one texture, else ``<pack>/<bch name>/<texture>.png``,
with a ``.meta.json`` (size, source) next to it. Animations are SPICA's decoded keyframe curves as JSON
(``tools/spica_ref anims``): per animation its frames, looping flag and per-target curves (interpolation, keys
``[frame, value, in-slope, out-slope]``, or per-frame quaternion / matrix / bool tracks).

    python tools/export_bch_assets.py              (about a minute with 8 workers)
"""
from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "game_data"
TEX = ROOT / "game_assets" / "textures"
ANIM = ROOT / "game_assets" / "animations"
INDEX = ROOT / "game_assets" / "bch_index.json"
SPICA = ROOT / "tools" / "spica_ref" / "bin" / "Release" / "net9.0" / "SpicaRef.exe"

# H3D content table order (BCH header dictionaries)
SECTIONS = ["models", "materials", "shaders", "textures", "luts", "lights", "cameras", "fogs", "skeletal_anims",
            "material_anims", "visibility_anims", "light_anims", "camera_anims", "fog_anims", "scenes"]
ANIM_SECTIONS = {"lights", "cameras", "fogs", "skeletal_anims", "material_anims", "visibility_anims",
                 "light_anims", "camera_anims", "fog_anims", "scenes"}

TWO_D_BATTLE = {
    "enemy": "2d_battle_enemies",
    "background": "2d_battle_backgrounds",
    "bg": "2d_battle_backgrounds",
    "parts_effect": "2d_battle_effects",
    "enemy_anim": "2d_battle_enemy_anims",
    "common": "2d_battle_common",
}


def rel_of(path: Path) -> str:
    return path.relative_to(DATA).as_posix()


def texture_dir(rel: str) -> Path:
    """Output folder for the images of one BCH (see the module docstring)."""
    parts = rel.split("/")  # romfs|packs|arcs / ...
    tail = parts[1:]
    if tail[0] == "ui":
        # romfs/ui/item/x.bch, packs/ui/common_2d/x.bch -> textures/ui/<folder>/ (pack = <folder>)
        return TEX / "ui" / (tail[1] if len(tail) > 2 else "ui_bch")
    if tail[:2] == ["2d", "model"]:
        return TEX / "2d_sprites"
    if tail[:2] == ["2d", "bg"]:
        return TEX / "2d_tilesets"
    if tail[:2] == ["2d", "battle2"] and len(tail) > 2:
        return TEX / TWO_D_BATTLE.get(tail[2], "2d_battle_common")
    if tail[:2] == ["2d", "weather"]:
        return TEX / "2d_weather"
    if tail[0] == "effect2d":
        return TEX / "2d_effects"
    if tail[0].startswith("2dcmn"):
        return TEX / "2d_common"
    return TEX / "misc_bch"


def animation_path(rel: str) -> Path:
    parts = rel.split("/")
    tail = parts[1:]
    if tail[:2] == ["3d", "motion"]:
        # 3d/motion/<set>/motion_<x>.bch -> motions/<set>.json (one file per set)
        return ANIM / "motions" / f"{tail[2]}.json"
    if tail[:2] == ["3d", "cs"]:
        # 3d/cs/<kind>/<id>/<id>.bch -> cutscenes/<kind>/<id>.json;
        # 3d/cs/scenario/<scene>/<shot>/<shot>.bch -> cutscenes/scenario/<scene>/<shot>.json
        stem = Path(tail[-1]).stem
        dirs = tail[3:-1]
        if dirs and dirs[-1] == stem:
            dirs = dirs[:-1]
        return ANIM.joinpath("cutscenes", tail[2], *dirs, f"{stem}.json")
    if tail[0].startswith("battlecmn"):
        return ANIM / "battle" / f"{Path(tail[-1]).stem}.json"
    return ANIM / "misc" / f"{Path(tail[-1]).stem}.json"


def compact(node):
    """Smaller animation JSON with the same data: drop curve fields that hold their defaults (repeat modes "None",
    start/end equal to the first/last key, all-zero slopes -> [frame, value] keys, all-empty axes) and round
    floats to 5 decimals."""
    if isinstance(node, float):
        r = round(node, 5)
        return int(r) if r == int(r) else r
    if isinstance(node, list):
        out = [compact(v) for v in node]
        return out
    if not isinstance(node, dict):
        return node
    if "keys" in node and "interp" in node:
        keys = node["keys"]
        c = {"interp": node["interp"]}
        if node.get("pre") not in (None, "None"):
            c["pre"] = node["pre"]
        if node.get("post") not in (None, "None"):
            c["post"] = node["post"]
        if keys and (node.get("start") != keys[0][0] or node.get("end") != keys[-1][0]):
            c["start"], c["end"] = node.get("start"), node.get("end")
        if all(k[2] == 0 and k[3] == 0 for k in keys):
            keys = [k[:2] for k in keys]
        c["keys"] = compact(keys)
        return c
    out = {}
    for k, v in node.items():
        if isinstance(v, list) and v and all(x is None for x in v):
            continue  # an axis group without any curve
        out[k] = compact(v)
    return out


def sections(raw: bytes) -> dict[str, int]:
    """Entry count per BCH content-table section (0 when the header is not readable)."""
    from tools.model_tool import BchParser

    p = BchParser(raw)
    out = {}
    for i, name in enumerate(SECTIONS):
        try:
            _tree, count, _vals = struct.unpack_from("<3I", p.data, p.hdr_off + i * 12)
        except struct.error:
            count = 0
        out[name] = count if count < 100000 else 0
    return out


def export_textures(job: tuple[str, str]) -> tuple[str, list[str], str | None]:
    """One BCH -> PNGs. Returns (rel, outputs, error)."""
    from tools.model_tool import BchParser

    rel, out_dir = job
    src = DATA / rel
    try:
        textures = BchParser(src.read_bytes(), source_path=src).extract_textures()
    except Exception as exc:  # reported in the index, the export goes on
        return rel, [], f"{type(exc).__name__}: {exc}"
    if not textures:
        return rel, [], "no decodable texture"
    stem = src.stem
    base = Path(out_dir)
    outputs = []
    for name, img in textures:
        target = base / f"{stem}.png" if len(textures) == 1 else base / stem / f"{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        img.save(target)
        meta = {"width": img.width, "height": img.height, "format_name": "BCH texture", "texture": name, "source": rel}
        target.with_name(target.stem + ".meta.json").write_text(json.dumps(meta), encoding="utf-8")
        outputs.append(target.relative_to(ROOT).as_posix())
    return rel, outputs, None


def classify(path: Path) -> tuple[str, dict[str, int]]:
    try:
        return rel_of(path), sections(path.read_bytes())
    except Exception:
        return rel_of(path), {}


def main() -> int:
    sources = sorted(p for sub in ("romfs", "arcs", "packs") for p in (DATA / sub).rglob("*.bch"))
    meshes = set()
    manifest = ROOT / "game_assets" / "models_manifest.jsonl"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            meshes.add(Path(row["source"]).as_posix().lower())
    print(f"{len(sources):,} BCH files, {len(meshes):,} already exported as 3D models")

    with ProcessPoolExecutor(max_workers=8) as pool:
        table = dict(pool.map(classify, sources, chunksize=64))

    index: dict[str, dict] = {}
    tex_jobs: list[tuple[str, str]] = []
    anim_pairs: list[tuple[str, Path]] = []
    for rel, sec in table.items():
        has_tex = sec.get("textures", 0) > 0
        has_anim = any(sec.get(k, 0) > 0 for k in ANIM_SECTIONS)
        # the model manifest stores paths relative to game_data
        if rel.lower() in meshes:
            kind = "model"
        elif has_tex and has_anim:
            kind = "textures+animations"
        elif has_tex:
            kind = "textures"
        elif has_anim:
            kind = "animations"
        else:
            kind = "empty"
        index[rel] = {"kind": kind, "contents": {k: v for k, v in sec.items() if v}, "outputs": []}
        if kind in ("textures", "textures+animations"):
            tex_jobs.append((rel, str(texture_dir(rel))))
        if kind in ("animations", "textures+animations"):
            anim_pairs.append((rel, animation_path(rel)))

    # images
    errors = 0
    with ProcessPoolExecutor(max_workers=8) as pool:
        for rel, outputs, error in pool.map(export_textures, tex_jobs, chunksize=16):
            index[rel]["outputs"] += outputs
            if error:
                index[rel]["error"] = error
                errors += 1
    print(f"images: {len(tex_jobs):,} BCH -> {sum(len(index[r]['outputs']) for r, _ in tex_jobs):,} PNG ({errors} without a decodable texture)")

    # animations: one SpicaRef run; several motion BCH of one set are merged by name below
    if anim_pairs:
        if not SPICA.is_file():
            raise SystemExit(f"{SPICA} missing: dotnet build tools/spica_ref -c Release")
        work = ROOT / "build" / "bch_anims"
        work.mkdir(parents=True, exist_ok=True)
        pairs_file = work / "pairs.txt"
        raw_dir = work / "raw"
        lines = []
        for n, (rel, _target) in enumerate(anim_pairs):
            lines.append(f"{DATA / rel}\t{raw_dir / f'{n:05d}.json'}")
        pairs_file.write_text("\n".join(lines), encoding="utf-8")
        run = subprocess.run([str(SPICA), "anims", str(pairs_file)], capture_output=True, text=True)
        print(run.stdout.strip().splitlines()[-1] if run.stdout.strip() else "SpicaRef: no output")
        if run.stderr.strip():
            print(run.stderr.strip()[:2000])
        merged: dict[Path, dict] = {}
        for n, (rel, target) in enumerate(anim_pairs):
            raw = raw_dir / f"{n:05d}.json"
            if not raw.is_file():
                index[rel]["error"] = "SpicaRef could not read the animations"
                continue
            doc = compact(json.loads(raw.read_text(encoding="utf-8")))
            doc["source"] = rel
            if target.name.endswith(".json") and target.parent.name == "motions":
                # a motion set (a000_btl) has one BCH per use (motion_btl.bch): keep them apart inside the set file
                merged.setdefault(target, {"format": "DQXI_MOTION_SET", "set": target.stem, "files": {}})["files"][Path(rel).stem] = doc
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
            index[rel]["outputs"].append(target.relative_to(ROOT).as_posix())
        for target, doc in merged.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
        print(f"animations: {len(anim_pairs):,} BCH -> {len({t for _, t in anim_pairs}):,} JSON files")

    from collections import Counter

    kinds = Counter(v["kind"] for v in index.values())
    done = Counter(v["kind"] for v in index.values() if v["outputs"] or v["kind"] == "model")
    INDEX.write_text(json.dumps({"format": "DQXI_BCH_INDEX", "kinds": dict(kinds), "exported": dict(done), "files": index}, indent=0),
                     encoding="utf-8")
    print("by kind:", dict(kinds), " exported:", dict(done))
    print(f"wrote {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
