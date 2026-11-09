# E4_assets — asset replacement workflows in DQXI Studio

**Status: implemented, built, unit-tested and exercised end-to-end on the command line. No GUI
click-through of the new preview controls, no emulator boot, no real 3DS.**

## What now works

Every asset family has the same two controls in the Rust app, backed by one Python tool
(`tools/asset_replace.py`) so the editor and the tests use the same encoder:

- **Export…** copies the editable standard-format file (PNG + `.meta.json`, glTF/OBJ/MTL/PNG,
  WAV, layout JSON, map `scene.json`) to `build/exports/`.
- **Replace + preview** imports the edited file, encodes it back into the **retail 3DS format**,
  writes a decoded preview of what the console will actually read, and reports hardware limits.
- **Replace + save to mod** also stages the containing PACK (or the loose BCSTM) into
  `mod/romfs/`, ready for `tools/export_mod.py` (Luma LayeredFS / rebuilt `.3ds` / `.cia`).

| Family | Encoder | Hardware checks / warnings |
|---|---|---|
| Textures (BFLIM) | all BFLIM formats: RGBA8, RGB8, RGBA5551, RGB565, RGBA4, LA8, LA4, L8, A8, L4, A4, ETC1, ETC1A4 | dimension mismatch refused (`--allow-resize` opt-in), power-of-two padding, 2048 px maximum, VRAM estimate, mip count (only the base level is replaced), lossy ETC1/4-bit formats |
| Model textures (BCH) | the embedded texture's **PICA** format, including RGB565/RGBA4/RGBA8/L8/LA8/L4/A4/ETC1/ETC1A4 (previously ETC1-only) | size/dimension checks, mip chain stays retail, quantisation warnings, same BCH byte size |
| Model geometry (BCH) | same-size vertex positions or triangle indices | vertex/index count and order, bone-space conversion, non-finite OBJ values refused, duplicate layers preserved |
| Audio (BCSTM) | **DSP-ADPCM** (new `tools/dspadpcm_encode.py`, retail bandwidth) or PCM16 | channel count must match, resample warning, loop point preserved, growth warning for same-slot patches, lossy DSP note |
| UI layouts (BFLYT/BFLAN) | pane translate/rotate/scale/size and same-capacity text written into the raw sections | rebuilt size must match the retail layout; pane count/text overflow refused with a reason |
| Levels (Level3D) | placement float edits, **Save to mod** stages `mod/romfs/level3d/<map>.pack` | per-offset bounds/finite checks; unchanged project is byte-identical |

The old BCH texture path had a real bug: `texture_tool.encode_bflim` silently fell back to RGBA8
for ETC1/ETC1A4 and L4/A4, changing the format and size. That is fixed. `bch_texture_patch` now
supports every PICA texture format used by the game (verified: 7,086 ETC1, 2,251 ETC1A4, 263
RGB565, 45 RGBA4, 36 L8, 29 LA8, 28 L4, 6 RGBA5551, 1 LA4 in a 400-BCH sample), not only ETC1.

## Round-trip tests (new: `tests/test_asset_replace.py`, 22 cases)

- every uncompressed BFLIM format decodes → re-encodes **byte-identically** (ETC1 re-encodes to the
  same size and within a small pixel error);
- an exported PNG imported unchanged reproduces the retail BFLIM exactly, and the staged UI pack
  contains that exact SARC member;
- BCH RGB565/RGBA4/L8 textures exported to PNG and re-imported are **byte-identical**;
- OBJ position/index no-ops are byte-identical, including bone-placed/duplicate meshes;
- BFLYT JSON no-op is byte-identical, a pane translation lands in the binary, over-long text is
  refused, and same-size SARC replacement is byte-identical;
- DSP-ADPCM tone encode/decode error is bounded, an unmodified exported WAV re-encodes to the
  **same stream size**, and PCM16 stays lossless;
- map no-op is byte-identical and a one-value edit changes only those four bytes (the shared
  `b001_101a` smoke fixture is preserved);
- CLI failures return a JSON error instead of a traceback.

## Test / build evidence

| Command | Result |
|---|---|
| `python -m unittest tests.test_asset_replace -v` | **22 passed** |
| `python -m unittest tests.test_asset_roundtrip -v` | **38 passed, 1 skipped** (SPICA dump absent) |
| `python tests/run_all.py` | **223 / 223 passed** (Tier 4 69/69, 183 s) |
| `cd viewer_rs; cargo test` | **75 passed, 0 failed, 1 ignored** |
| `cd viewer_rs; cargo build --release` | **OK** (41 s) |
| `python tools/verify.py` | **PASS** (manifest 16/16 + bit-matching ROM) |
| `python tools/verify_project.py` | **OVERALL PASS** |
| release viewer started with `DQXI_START_SECTION=textures|models|audio|layouts|editor` | stayed alive 7–10 s per section, no panic |

One intermediate full-suite run failed 12 Tier-4 tests with `NameError: name 'magic' is not
defined` inside `tools/pack.py`. That file was being rewritten by a concurrent worker at that
moment (mtime 18:37:38); the failing tests passed individually as soon as the write finished and
the rerun above was green. No test or check was weakened.

Command-line end-to-end runs for texture, model, model-texture, audio, layout and map produced
`ok: true`, staged packs under `mod/romfs/`, and were removed again afterwards (the `mod/` workspace
is back to its examples only). The staged `ui/battle_2d.pack` was reopened and its BFLIM/BFLYT
members compared with retail — identical for the no-op edits. The canonical `b001_101a` project
(6 float edits) was staged with `asset_replace.py` and then exported with
`tools/export_mod.py --target luma`; the Luma folder contains `level3d/b001_101a.pack` (24,960 B).

## Important process note (honesty)

While bulk-editing the panels I ran a shell replacement that opened the files for writing before
reading them; it truncated **all 15 `viewer_rs/src/ui/panels/*.rs` files to zero bytes**. I recovered
them from the local OpenCode session transcript (the recorded `write`/`edit` payloads and `read`
results): the six E4 panels were rebuilt from their pre-edit read plus the E4 edit history, the
final `playtest.rs` was replayed from the X2 session plus the `A_ui_contrast` button edit, and the
remaining panels were rebuilt from their last full read/write history. `cargo build`, `cargo test`
(75), the full Python suite and a startup smoke run of every section confirm the restored tree. I
believe the recovery is byte-faithful (sizes/features match the pre-truncation reads), but this was
an avoidable accident and the exact history is recorded here rather than hidden.

## BLOCKED

None. All required tools (Python 3.12, Pillow, NumPy, Rust/cargo) were already installed; no
emulator or real hardware was required for this lane.

## Files changed

- `tools/asset_replace.py` (new): Export/Replace/inspect orchestration, validation, previews, mod staging.
- `tools/sarc_tool.py` (new): SARC read/rebuild; same-size replacement is byte-identical.
- `tools/dspadpcm_encode.py` (new): DSP-ADPCM encoder (14 samples / 8-byte frame, predictor + shift search).
- `tools/texture_tool.py`: exact tiled encoder for every format, ETC1/ETC1A4 and L4/A4 in `encode_bflim`, mip count, replacement validation.
- `tools/bch_texture_patch.py`: all PICA formats, mip/quantisation warnings, strict dimensions, `--resize`.
- `tools/bcstm_encode.py`: `build_bcstm_dsp`, `--codec dspadpcm|pcm16` (default DSP-ADPCM).
- `tools/layout_tool.py`: pane transform/size/text write-back into raw BFLYT sections; unchanged JSON stays byte-identical.
- `viewer_rs/src/ui/asset_jobs.rs` (new) + registration in `ui/mod.rs`: shared background job, warnings, status, preview image loader.
- `viewer_rs/src/ui/panels/{textures,models,audio,layouts,editor}.rs`: Export/Replace/Save-to-mod UI, previews, hardware warnings. `maps.rs` unchanged (its dossier already links into the other panels).
- `tests/test_asset_replace.py` (new).
- `docs/EDITING.md`, `docs/ASSETS.md`, `README.md`: asset replacement workflows, limits, CLI, test commands.
- `AGENT_LOG.md`: this task's entry.

## Not verified / limits

- The new controls were not clicked through in the running GUI. The viewer was only smoke-started
  in each section; preview refresh (new egui texture key per replacement) and the background job
  status were exercised indirectly by the same Python commands the buttons invoke, not by a mouse.
- No emulator boot or real 3DS/2DS run of a replaced texture/model/audio/layout/map. Same-size edits
  follow the existing proven PACK/RomFS path; the DSP-ADPCM encoder and ETC1 encoder are validated
  by decode-level tests, not by the console's hardware decoder.
- DSP-ADPCM encoding is a greedy per-frame optimiser (~0.5 s per second of stereo audio). A
  five-minute track can take minutes; the UI stays responsive but the wait is real.
- Only the base mip is replaced; higher mips remain retail.
- Texture/layout/model replacement is same-size; new objects, extra vertices, extra panes, longer
  layout strings and dimension changes are deliberately refused.
- glTF geometry is export-only; the write-back format is OBJ (same vertex order as the BCH).
- Map editing still moves/edits recovered placement records; adding or deleting records is not
  implemented (the BXON record graph has no free-slot allocator).

## Suggested follow-ups

1. A UI smoke test that drives one Export→Replace→preview cycle per panel with `egui::Context`
   headless, or a small screenshot scenario like `A_ui_contrast` used.
2. A DSP-ADPCM encoder benchmark and, if needed, a vectorised/Cython-free faster search for
   full-length BGM replacement.
3. Mip-chain re-encoding for textures that actually use mips (currently base-level only).
4. glTF→BCH geometry import (matching vertex order, preserving skin/bone data).
5. Map record creation/deletion with a BXON free-slot allocator, so new placements can be added
   from the editor rather than only moved.
6. Add the same Export/Replace pair to the area dossier (`maps.rs`) as a shortcut, rather than
   going through the family panels.
