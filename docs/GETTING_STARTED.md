# Getting Started

This guide is for a developer who has never touched a 3DS game before. It explains what to run,
what each output means, and where to make a first safe edit.

## 0. Prerequisites

- Windows 10/11 (the scripts use PowerShell paths; Python itself is portable).
- Python 3.12 with `Pillow`, `numpy`, `capstone`.
- Rust toolchain (for the viewer/editor).
- A legally obtained `DQXI.3ds` cartridge image. The project expects the reference image at
  `..\reference project\DQXI.3ds` or `original/DQXI.3ds`.
- Optional: Ghidra 12.1.4 + JDK 21 only if you want to regenerate native code.

Check the baseline first:

```powershell
python tools/verify.py
python tests/run_all.py
cd viewer_rs; cargo test
```

## 1. Build the data tree

The full extraction is about 10 GB and takes several minutes.

```powershell
python tools/extract_game_data.py --all
python tools/extract_arcs.py
```

Result:

- `game_data/romfs/` — exact original files, including `.pack`/`.paca` containers.
- `game_data/packs/` — every archive member exploded.
- `game_data/arcs/` — every SARC member (`bflyt`, `bflan`, `bflim`).

If a command stops, fix the first reported file; do not silently skip it. The manifests in
`audit/` and `game_data/manifest.json` are the source of truth for coverage.

## 2. Convert to standard formats

```powershell
python tools/convert_assets.py --all
python tools/map_tool.py export --all
```

This writes `game_assets/`. The conversion is intentionally separated from extraction so you can
re-run one family without touching the originals:

```powershell
python tools/convert_assets.py --textures
python tools/convert_assets.py --models --workers 12   # one process per core; ~2.5 min for all 10,542 BCH
```

## 3. Explore

```powershell
run_viewer_rs.bat
```

The sidebar now indexes the complete converted library, not just the old curated samples.

## 4. Make a first safe edit

1. `run_editor.bat`
2. Search for `b001_101a` (Cobblestone area).
3. Select a cyan marker in the viewport.
4. Change its X position by +2.
5. Click **Save project** (writes `editor_projects/b001_101a.json`).
6. Click **Export BXON** (writes `game_assets/maps/b001_101a/level3d.patched.bxon`).
7. Build a modified ROM:

```powershell
python tools/patch_game.py --map b001_101a
```

The patched image is `build/DQXI_patched.3ds`.

## 5. Read the code

Start with:

- `decomp/ghidra/README.md`
- `decomp/ghidra/COVERAGE.md`
- `decomp/ghidra/by_subsystem/Memory_and_Heaps/` for a small, concrete subsystem
- `symbols.json` for recovered names

The old `decomp/functions/` tree is legacy pseudocode. Do not use it as the primary source.

## 6. When something looks wrong

- Check `audit/GAP_REPORT.md` and `audit/SOURCE_QUALITY.md`.
- Check the relevant `game_assets/*_summary.json` for conversion errors.
- Re-run the smallest family (one texture, one table, one map) rather than the whole pipeline.
- Never modify `..\reference project`; it is a read-only reference.

## 7. Optional: build a C source replacement

```powershell
python tools/setup_arm_toolchain.ps1
python tools/check_clean_c.py
python tools/build_c_replacement.py
python tools/build.py
```

`InitBss`, `GetTalkPartyNoIndex`, `GetTalkPartyPageSize`, and `GetTalkPartyYesIndex` are already replaced and bit-verified. See
`docs/SOURCE_REPLACEMENT.md` to add another function.
