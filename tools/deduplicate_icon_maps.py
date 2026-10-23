#!/usr/bin/env python3
"""tools/deduplicate_icon_maps.py - Consolidates duplicate UI map icons into Shared_UI_Icons.

Dragon Quest XI 3DS packs identical UI map icons across 330+ map packages.
This script extracts the 10 canonical unique icon textures, places them in
game_textures/by_category/Shared_UI_Icons/, generates a manifest mapping all
references, and prunes the 2,200+ redundant duplicate files.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEXTURES_DIR = PROJECT_ROOT / "game_textures"
SHARED_ICONS_DIR = TEXTURES_DIR / "by_category" / "Shared_UI_Icons"


def deduplicate_icon_maps() -> tuple[int, int]:
    SHARED_ICONS_DIR.mkdir(parents=True, exist_ok=True)

    png_files = list(TEXTURES_DIR.rglob("*icon_map*.png"))
    # Exclude anything already in Shared_UI_Icons
    png_files = [p for p in png_files if "Shared_UI_Icons" not in str(p)]

    print(f"Scanning {len(png_files)} icon_map PNG files across map packages...")

    by_hash: dict[str, list[Path]] = {}
    for p in png_files:
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        by_hash.setdefault(h, []).append(p)

    print(f"Identified {len(by_hash)} unique icon textures by SHA-256.")

    canonical_map: dict[str, str] = {}
    manifest_refs: dict[str, dict] = {}

    for h, files in by_hash.items():
        # Pick the most common / clean name for this hash
        names = [f.name for f in files]
        best_name = max(set(names), key=names.count)
        canonical_dest = SHARED_ICONS_DIR / best_name
        
        # Copy canonical PNG and meta.json
        sample_file = files[0]
        shutil.copy2(sample_file, canonical_dest)
        sample_meta = sample_file.with_suffix(".meta.json")
        if sample_meta.exists():
            shutil.copy2(sample_meta, canonical_dest.with_suffix(".meta.json"))

        canonical_map[h] = best_name

        for f in files:
            rel = str(f.relative_to(TEXTURES_DIR)).replace("\\", "/")
            manifest_refs[rel] = {
                "canonical_name": best_name,
                "shared_icon_path": f"by_category/Shared_UI_Icons/{best_name}",
                "sha256": h,
            }

    # Write manifest
    manifest_path = SHARED_ICONS_DIR / "shared_ui_icons.json"
    manifest_data = {
        "description": "Dragon Quest XI (3DS) Shared Map Icons Manifest",
        "unique_textures_count": len(by_hash),
        "total_pruned_duplicates": len(png_files),
        "canonical_textures": list(canonical_map.values()),
        "references": manifest_refs,
    }
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    print(f"Saved shared icons manifest to {manifest_path}")

    # Prune duplicate files
    pruned_count = 0
    for f in png_files:
        meta = f.with_suffix(".meta.json")
        try:
            f.unlink()
            pruned_count += 1
            if meta.exists():
                meta.unlink()
                pruned_count += 1
        except Exception as err:
            print(f"  [ERROR] Deleting {f}: {err}")

    print(f"Pruning complete! Removed {pruned_count} redundant duplicate icon files.")
    return len(by_hash), pruned_count


if __name__ == "__main__":
    deduplicate_icon_maps()
