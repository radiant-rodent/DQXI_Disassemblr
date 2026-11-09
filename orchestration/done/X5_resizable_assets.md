# X5 resizable assets — closed by orchestrator (2026-10-26)

Audited what earlier tasks (E2/E4/X1/X4/X6 and the orchestrator) already deliver:

| Item | State | Evidence |
|---|---|---|
| PACK/PACA member of any size | done | `tools/patch_asset.py`, `export_mod.stage_member` (builds on the mod's own pack copy) |
| RomFS grow/add files (`3ds`, `cia`) | done | docs/EXPORT.md: Level-3 metadata + hash tables + IVFC rebuilt; `luma` replaces only |
| Text banks: longer strings | done, **emulator-proven** | `tests/emu/run_cases.py text_grow` PASS |
| Table text (names/descriptions) longer | done, **emulator-proven** | `table_edit set` appends + repoints; `item_new` PASS; DQXI Studio editor too |
| Table: more item records | **not supported by design** | 27 row-index bound checks + 2880-bit save mask (done/X6_item_table_growth.md); use `add-item` placeholders |
| BFLYT longer pane text | done (code-read, not emulator-proven) | `layout_tool.apply_pane_edits` grows `txt1` buffer |
| BFLYT new panes | **open** | → task X5b_layout_add_pane |
| BCLIM/BFLIM new dimensions | done (code-read) | `texture_tool png_to_bflim --allow-resize`; pane UVs unchanged (warned) |
| BCSTM different length | done (code-read) | `tools/bcstm_encode.py` PCM16 from WAV with template INFO |

Not verified here: grown BFLYT/BFLIM/BCSTM in the emulator, and anything on real hardware.

> Historical snapshot: the BFLYT-new-panes row was finished by X5b and true item growth was
> closed by X6 (supported via placeholder rows). The resumed section below is the current state.

---

# X5 resumed completion (2026-10-30)

This section records the resumed pass. X5 was already marked closed above, and X5b/X6
finished the two hard format questions (new panes; true item-table growth). What was
still missing was regression coverage, a proof of the RomFS *add-file* path for a new
top-level directory, an audit that the "unchanged = identical" promise holds for every
shipped PACK, and a final green run of the grown/added paths. Those are now done.

## Container level (PACK/PACA)

* Audited **all 13,469 PACK files** in `game_data/romfs` (2,656 MB): parse → `build()`
  → compare. **13,469 / 13,469 byte-identical**, including **1,377 PACA** streams (a BLZ
  re-encode is not byte-equal, so the builder returns the original bytes when nothing
  changed). Largest pack 6,609,628 B. The audit is repeatable: `python -m tools.pack
  [--limit N]` (documented in `docs/EDITING.md`).
* Growing a member re-lays the pack with each member's retail payload alignment
  (0x80 for textures/SARC data, 4 for the rest), updates the offset table + sizes and
  recompresses PACA when the input was compressed. New tests:
  `tests/test_resizable.py::PackGrowthTests` (unchanged PACK, unchanged PACA, grown
  member in a plain PACK with other members untouched, grown member in PACA with every
  member preserved).

## RomFS level (3ds/cia)

* New files work end-to-end. A real `--target 3ds --no-rom` export with two new paths
  (a root file and a **new top-level directory**) produced `out/3ds/romfs.bin`; the
  re-parse finds 21,252 entries, reads both new files with the exact bytes, still reads
  `/syscmn.pack` as `PACA`, and `romfs_hash.verify` is `ok=True`. The emitted image is
  `a011fb79…487a` (2.68 GB), report `out/EXPORT_REPORT.json`.
* **Bug found and fixed:** adding a new *top-level* directory wrote the new entry into
  the root directory's **sibling** field (the root entry is its own parent, so it was
  treated as a sibling of the new child). The directory was unreachable. `dir_for` in
  `tools/romfs_build.py` now excludes the parent itself from its children list.
  Proven on the real retail image (`/x5top/file.bin` + `/x5root.bin` both readable,
  IVFC `ok=True`) and by the synthetic tests.
* **Bug found and fixed earlier in this lane:** `build_patched_romfs` passed
  `{path,data}` dicts to `romfs_build.rebuild_metadata`, which expects `(path, data)`
  pairs (`KeyError: 0`). Fixed at the caller; `rebuild_metadata` also accepts dicts.
* Luma: a grown `syscmn.pack` (303,536 → 306,832 B) exports to LayeredFS and the file
  round-trips byte-identically. Luma still cannot mount a *new* path (LayeredFS
  semantics, not a tool limit); the exporter says so and points at `3ds`/`cia`.
* Tests: `tests/test_resizable.py::RomFsGrowthTests` builds a small synthetic RomFS and
  adds a root file, two files under one new directory and a file under a second new
  directory; all paths read back, retail bytes stay put, IVFC verifies. The existing
  `test_grown_member_is_appended_to_romfs` covers a grown pack on a synthetic image.

## Format level

| Format | Result |
|---|---|
| Text banks, longer strings | `bxon.Bxon.rebuild` relocates the string block, appends it and repoints the trusted refs; `text_grow` **PASS** in Azahar (grown line at `0x33E0…` in the live UI heap, no crash). |
| BXON tables, more records | `bxon_grow.grow_table` appends **or inserts at `--at N`**; every retail row is re-verified by value/string, and rows after an insert are shifted with their self-relative pointers corrected. For the item table specifically, true growth is **not usable by the game** (X6: 27 row-index bounds, 2875 attach check, 2880-bit save mask). `claim_placeholder`/`table_edit add-item` is the supported path and `item_new` **PASSES** in Azahar (new name + price in the shop). |
| BFLYT | Longer `txt1` text grows the section and re-encodes (`test_longer_text_grows_the_pane`); new panes via `layout_tool add-pane` (`test_added_pane_is_a_sibling…`). Not emulator-proven. |
| BFLIM/BFLIM | `texture_tool.encode_bflim` stores a different width/height and re-tiles; `test_texture_can_be_encoded_at_a_new_size` decodes the rebuilt file at 2×. Pane UVs stay retail → the game scales the image (warned). Not emulator-proven. |
| BCSTM | `build_bcstm_dsp`/`build_bcstm` with a different sample count re-parses and decodes; `test_audio_stream_can_change_length` builds 1,600 samples from a muted retail template and checks the decoded PCM length. Not emulator-proven. |

## Editor-side checks

`viewer_rs` no longer says added files are refused. The Playtest workspace validator now
marks a new RomFS path as a **warning** ("added by 3ds/cia, not mounted by Luma
LayeredFS") instead of an error, and the change/undo labels say the same. The tables panel
already offers `Add entry (copy row N)` for the placeholder path. `cargo test`: **85
passed, 0 failed, 2 ignored**.

## Tests / verification (this resumed pass)

| Command | Result |
|---|---|
| `python -m unittest tests.test_resizable -v` | **13 passed** (new module) |
| `python tests/run_all.py` | **384 run, 383 pass, 1 skip, 0 fail — SUCCESS** (Tier 1 70/70, Tier 2 70/70, Tier 3 14/14, Tier 4 69/69, Tier 5 40/40, tool unit 120/121 + 1 skip) |
| `python -m tools.build` | **PASS**: code.bin 0 differences, compressed .code 0 differences |
| `python -m tools.verify_project` | **OVERALL: PASS** (18 checks) |
| `python tests/emu/run_cases.py text_grow item_new --summary-only` | both **PASS** from the saved emulator results (text relocation; new item name+price live in a shop) |
| `cargo test` (`viewer_rs`) | **85 passed, 0 failed, 2 ignored** |
| 13,469-PACK audit | **0 differences** |

## Files changed in the resumed pass

- `tools/romfs_build.py` — root-directory linking fix; accept dict additions.
- `tools/pack.py` — repeatable `--limit`/`--json` round-trip audit of every PACK/PACA.
- `tools/export_mod.py` — pass `(path, data)` pairs to `rebuild_metadata`.
- `tools/bxon_grow.py` — `--at` insert position (with row shifting), `--set` applies to
  every added row, invalid negative positions refused.
- `tests/test_resizable.py` — new 13-test module (PACK/PACA, BXON append/insert/claim,
  text relocation, synthetic RomFS add, BFLIM resize, BCSTM length).
- `tests/emu/{drive,fixtures,run_cases}.py` — `text_grow`/`table_grow` cases, grow
  fixtures, UTF-8-safe runner output (shared with X3/X6; additive).
- `viewer_rs/src/ui/panels/playtest.rs` — new-path validation is a warning, not an error.
- `orchestration/done/X5_resizable_assets.md` — this section.
- `AGENT_LOG.md` — entry for this pass.

## What is still not verified / limits

- **No grown BFLYT/BFLIM/BCSTM was booted** in Azahar; only file-level re-parse/decode
  tests. The longer pane text and the added pane are code-read only.
- **No grown `.3ds`/`.cia` was booted** (the earlier X1 boot used a same-size edit).
  A grown RomFS file and two new paths pass the full re-parse/IVFC checks, but booting
  an image with an added file remains unproven on emulator and hardware. `cia` builds
  its content from the same `build_3ds` RomFS step, but no CIA with an added file was
  produced in this pass.
- **True item-table growth is not supported** by the retail engine (X6): use the 189
  placeholder rows. Other tables' appended rows still need a consumer that iterates the
  whole table; only the BXON/container level is proven for them.
- Adding a Row in the middle shifts later row indices; any other table or save that
  refers to those indices must be updated. Append (`--at` omitted) is the safe default.
- Real 3DS/2DS hardware was not available in this lane.
