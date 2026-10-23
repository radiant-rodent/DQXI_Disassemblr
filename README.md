# Dragon Quest XI (3DS) — Disassembly, Asset Library & Level Editor

This workspace turns the retail **Dragon Quest XI: Echoes of an Elusive Age** 3DS
cartridge (`CTR-P-BTZJ`) into a readable, editable project:

- a verified bit-matching ARM disassembly and build pipeline;
- a Ghidra-generated high-level C view of the native executable;
- a complete RomFS/archive extraction tree;
- standard-format conversions of textures, models, layouts, scripts, tables and audio;
- a Rust viewer with a working level editor for map environments and placement records.

> **This repository contains the tools, viewer and documentation only.** It does not include
> any game files, extracted assets, disassembly, Ghidra output or build products. Those are
> generated from your own copy of the game (`DQXI.3ds`) with the tools here. The
> disassembly and reconstructed C sources are not part of this copy.

The retail ROM and the reference translation workspace are treated as read-only. All generated
data lives in `game_data/`, `game_assets/`, `decomp/`, and `build/`.

> This is a reverse-engineering/modding project. You need your own legally obtained copy of the
> game. No game data is redistributed by the code in this repository.

---

## Quick start

```powershell
# 1. Extract the complete RomFS and every PACK/PACA member
python tools/extract_game_data.py --all

# 2. Explode the SARC UI archives (BFLYT/BFLAN/BFLIM)
python tools/extract_arcs.py

# 3. Convert assets to standard formats (this takes a while and several GB)
python tools/convert_assets.py --all

# 4. Decode every level3d map into an editable scene
python tools/map_tool.py export --all

# 5. Rebuild the readable native-code index
python tools/organize_ghidra.py

# 6. Open the editor
run_editor.bat
```

`run_editor.bat` opens the Rust application directly in **Level Editor**. `run_viewer_rs.bat`
opens the same application in the project browser.

### Verify the retail baseline

```powershell
python tools/verify.py          # manifest + bit-matching ROM
python tests/run_all.py         # existing end-to-end tests
cd viewer_rs; cargo test        # editor/viewer unit tests
```

The original `DQXI.3ds` SHA-256 is
`0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74`.

---

## What is where

| Path | Contents |
|---|---|
| `original/` | Decrypted retail containers, ExeFS, `romfs.bin`, baseline hashes |
| `asm/` | Complete modular ARM/Thumb disassembly, annotated with original bytes |
| `build/` | Reassembled `code.bin`, compressed `.code`, retail/patched ROMs |
| `decomp/ghidra/` | **Readable native C** from Ghidra: 18,748 functions, organised by subsystem |
| `decomp/functions/` | Legacy register-level pseudo-C (kept only for comparison) |
| `game_data/romfs/` | Exact RomFS tree, including original `.pack`/`.paca` files |
| `game_data/packs/` | Every PACK/PACA member exploded by its stored name |
| `game_data/arcs/` | Every SARC member exploded (`bflyt`, `bflan`, `bflim`, …) |
| `game_assets/textures/` | 3,486 BFLIM → PNG with metadata sidecars |
| `game_assets/models/` | 4,779 BCH models → glTF 2.0 + OBJ + embedded textures |
| `game_assets/layouts/` | 7,232 BFLYT/BFLAN → structured JSON |
| `game_assets/scripts/` | 769 Squirrel CNUT scripts → readable disassembly |
| `game_assets/tables/` | 5,929 BXON tables → structural JSON |
| `game_assets/audio/` | 5,877 BCSTM streams → 16-bit PCM WAV |
| `game_assets/maps/` | 1,196 decoded Level3D scenes + structural dumps |
| `audit/` | Forensic inventory, pack manifests, quality/gap reports |
| `viewer_rs/` | Rust/egui project browser and level editor |
| `tools/` | Extraction, conversion, patching, Ghidra and build tools |
| `docs/` | Task-oriented guides; [`docs/EDITING.md`](docs/EDITING.md) is the edit-and-write-back cheat sheet |

### Status at a glance

| Area | Source | Converted / accounted for |
|---|---:|---:|
| RomFS files | 21,250 | 21,250 exact copies |
| PACK/PACA archives | 13,469 | 13,469 exploded, 0 errors |
| PACK members | 21,273 | 21,273 |
| SARC archives | 398 | 398 exploded, 10,718 members |
| BFLIM textures | 3,486 | 3,486 PNG |
| BFLYT + BFLAN | 4,394 + 2,838 | 7,232 JSON |
| BCH models | 10,542 | 4,779 with meshes exported (others are texture/background-only or empty) |
| CNUT scripts | 769 | 769 `.nut` |
| BXON tables | 5,929 | 5,929 JSON |
| BCSTM streams | 5,877 | 5,877 WAV |
| Level3D maps | 1,196 | 1,196 editable scenes, 5,022 placement candidates |
| Native entry points | 18,787 | 18,748 decompiled + 38 covered + 1 unresolved |

---

## Native code

The old `decomp/functions/` files are **not** the readable source. They are register-level
pseudo-C and many do not compile. The readable tree is:

```
decomp/ghidra/
├── functions/              # flat Ghidra export, one .c per entry point
├── recovered/              # entry points recovered in a second pass
├── by_subsystem/           # navigation view grouped by domain
├── functions_merged.jsonl  # address, name, mode, status, signature, source file
├── functions_index.json    # catalog used by the viewer
├── functions.h             # generated prototypes
└── dqxi_types.h            # presentation typedefs
```

Read `decomp/ghidra/README.md` and `decomp/ghidra/COVERAGE.md` first. Unknown callees still
carry Ghidra names such as `FUN_0055E928`; use the index or `symbols.json` to resolve them.
Struct recovery is intentionally ongoing: treat field offsets as hypotheses until checked
against call sites.

### Re-running the decompiler

Ghidra 12.1.4 and JDK 21 are used locally. The one-time import is:

```powershell
$env:JAVA_HOME = "<your-tools-folder>\jdk-21.0.12.1+1"
$ghidra = "<your-tools-folder>\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat"

& $ghidra decomp/ghidra_project DQXI `
  -import original/exefs/code.decompressed.bin `
  -processor ARM:LE:32:v6 -cspec default `
  -loader BinaryLoader -loader-baseAddr 0x00100000 -overwrite
```

Then export and organise:

```powershell
& $ghidra decomp/ghidra_project DQXI -process code.decompressed.bin -noanalysis `
  -scriptPath tools/ghidra_scripts `
  -postScript ExportDQXI.java . .\decomp\ghidra
python tools/organize_ghidra.py
```

The bit-matching assembly remains the canonical safety net. `tools/build.py` still reassembles
`asm/` into the retail `code.bin`; the readable C is a parallel, human-facing view while the
source-replacement build path is completed.

---

## Level editor

Open `run_editor.bat`, or set `DQXI_START_SECTION=editor` and run the viewer.

1. Pick a map id on the left (for example `b001_101a`).
2. The viewport loads the converted environment mesh (`game_assets/models/packs/3d/bg/...`).
3. Cyan/gold markers show the placement records recovered from `level3d.bxon`.
4. Select an object, edit position/scale/rotation, use Undo/Redo.
5. **Save project** writes `editor_projects/<map>.json`.
6. **Export BXON** writes a same-size patched `game_assets/maps/<map>/level3d.patched.bxon`.
7. Rebuild a playable ROM:

```powershell
python tools/patch_game.py --map b001_101a
```

The patcher rebuilds the PACK, patches the same-size data into a copy of `romfs.bin`, rebuilds
and verifies the RomFS IVFC hash tree, and invokes the modified-ROM repacker. Same-size edits
therefore pass strict RomFS hash checks. Size-changing edits still need a full RomFS rebuild.

The current editor is deliberately honest about what is known: the 68-byte records expose a
position, size and type marker; the 120-byte records also expose a rotation triple. The semantic
name of every record type is not fully recovered yet. See `docs/EDITOR.md` for the data model and
how to extend it.

---

## Editing assets

All conversions are one-way plus a round-trip helper where the format supports it:

- textures: `python tools/texture_tool.py rebuild PNG --orig BFLIM --out OUT.bflim`
- BCH model textures: `python tools/bch_texture_patch.py --bch model.bch --texture NAME --png new.png --out patched.bch`
- audio: `python tools/bcstm_encode.py --template original.bcstm --wav new.wav --out patched.bcstm`
- layouts: `python tools/layout_tool.py rebuild JSON --out OUT.bflyt`
- tables: string-table JSON can be rebuilt bit-identically with `Bxon.build_from_json`; a general
  semantic object-graph writer is still on the roadmap.
- scripts: `.nut` text assembly and `sqbin.py` round-trip are available.
- levels: editor → patched BXON → `tools/patch_game.py`.

Do not edit `game_data/romfs` in place if you want to keep a pristine baseline. Work in
`game_assets/` or `editor_projects/` and feed the patch tools.

---

## Tests and audits

```powershell
python tools/audit_project.py --packs     # rebuild the forensic manifests
python tools/verify.py                    # baseline container hashes
python tests/run_all.py                  # existing 187-test suite
python -m unittest discover -s tests/tier5_challenger
cd viewer_rs; cargo test
```

`audit/GAP_REPORT.md` is the starting point for what is genuinely present. It is intentionally
more skeptical than the older milestone reports.

---

## Known limitations

- The readable C is decompiler output, not a hand-verified source port. Type and struct recovery
  is incomplete; some functions contain Ghidra artifacts.
- 4,779 of 10,542 BCH files produce meshes; the rest are background textures, rigs or empty
  resources. The conversion manifest records every source file and every error.
- BXON numeric schemas are inferred structurally, not from original headers. Field names are
  path-based until a schema is confirmed.
- RomFS IVFC hashes are rebuilt for same-size patches; size-changing edits still need a full RomFS rebuild.
- The editor edits recovered transforms and placement records, not arbitrary scripted events yet.
- BCH embedded textures can be replaced in place (PNG → ETC1/ETC1A4, base mip). ETC1 is lossy;
  uncompressed BFLIM formats round-trip bit-exactly. Topology/material re-encoding is not yet
  implemented beyond same-size position and texture payload edits.
- BCSTM replacement writes PCM16 using an existing stream as the template; DSP-ADPCM re-encoding
  is not implemented.

---

## Reference project

`..\reference project` is used read-only for container parsing and translation research.
The baseline modifications/untracked files in that workspace predate this project; tests in
`tests/tier1_features/test_feature_14_reference_git.py` enforce that no new changes are made.

### One-shot project verification

```powershell
python tools/verify_project.py
python tools/verify_project.py --hash-rom   # also re-hashes the 4 GB images
```

This reconciles the native build, asset counts, readable-code coverage, decoded maps, editor
binary, and patched-ROM report. The JSON evidence is `audit/PROJECT_VERIFICATION.json`.
python -m unittest tests.test_asset_roundtrip -v   # 7 local round-trip checks

> The older `game_textures/`, `game_models/`, `game_layouts/`, `game_scripts/`,
> `game_tables/`, and `game_audio/` folders are legacy curated views. The complete
> standard-format library is `game_assets/`; the viewer prefers it automatically.

The checked-in smoke edit (`b001_101a`, move one placement +2 on X) produced
`build/DQXI_patched.3ds` with SHA-256
`97712a2dbfde2993812f3859c7b3a8bd5865e8064519c5a101a260c749e5088f`; its RomFS
IVFC tree verifies with zero bad hashes.

### Verified source replacement
`src/replacements/InitBss.c` and three `GetTalkParty*` wrappers compile with ARMv6K GCC to the
exact retail bytes (36 + 16 + 16 + 16). Run `python tools/build_c_replacement.py` then
`python tools/build.py`; the full executable still bit-matches. See `docs/SOURCE_REPLACEMENT.md`.

### OST and audio

The **Audio** section defaults to **OST (155)**. **Jingles (37)**, **Voices/SFX**, and **All**
are separate filters. Columns are sortable by name, length or size. Full catalog:
`game_assets/audio/AUDIO_CATALOG.md`; see `docs/AUDIO.md`.

> Model texture assignment is structural: BCH relocation/model tables are parsed, mesh material
> indices are resolved, and material names are matched to embedded textures. The viewport loads
> OBJ material groups/UVs and draws each group with its MTL texture. Exact duplicate geometry
> (layered torch/fire/light quads) is collapsed so static exports do not contain repeated objects.
> See `docs/ASSETS.md`.

> Import either `.gltf` or `.obj` from a model folder, not both. They are two representations of
> the same model; importing both makes every model appear twice. Layered BCH quads (torch, fire,
> light, alpha passes) are deduplicated in the static export.

> Per-draw material texture assignment is backed by
> `game_assets/models/material_map.json.gz`, generated from the BCH material tables. It maps each
> draw to the material's primary `Texture0` (with a cubemap/environment fallback to `Texture1`).

> `tools/model_patch.py` supports both same-size vertex-position edits and triangle-index
> (topology) edits from an edited OBJ; a no-op edit is byte-identical, including layered copies.

> `tools/model_material.py` edits a material's diffuse RGBA in place, and `tools/model_patch.py
> --indices` rewrites triangle topology when the index count is unchanged. Texture replacement and
> all BCH edits remain same-size, so PACK/ROM patching stays valid.
