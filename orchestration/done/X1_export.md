# X1_export — mod workspace → real 3DS/2DS (resumed)

**Status: completed (boot-tested in Citra; no real hardware — see §9).**

Resumed a stopped worker. What already existed: a ~1000-line, never-executed
`tools/export_mod.py` (written 13:28, no output, no docs, no tests, no `mod/`), the P0-era
`tools/repack_rom.py`, `tools/patch_game.py`, `tools/recompile_game.py`, and
`orchestration/logs/X1_export.log` containing nothing but a `Read PLAN.md`. So: the pipeline
existed as source text only; nothing had ever been exported. It is now running, validated,
documented and tested.

---

## 1. Why it never ran — four real bugs in the RomFS/NCCH parsing

The exporter's own validation layer was wrong, which is also why nothing could be produced at all:

1. **Signature prefix ignored.** This cartridge's NCSD/NCCH headers keep the 0x100-byte RSA
   signature in front of the header fields, but `read_title_id`, `parse_ncsd` and `parse_ncch`
   looked for the magic at offset 0 (`NCSD`/`NCCH` live at 0x100) and read the program ID from
   `0x118` of the *file* instead of the header block. Title ID now comes out as
   `0004000000199200` (DQXI's real title ID) instead of an exception.
2. **RomFS level-3 header field order was wrong.** It is
   `size, dir-hash off/len, dir-meta off/len, file-hash off/len, file-meta off/len, data off` —
   the *directory* tables come before the file tables. The old code read the file hash table
   (0x14 C0 bytes of bucket u32s) as if it were the directory metadata, then walked garbage.
3. **Directory entry layout was wrong.** A directory entry is
   `parent, sibling, first-subdir(+0x08), first-file(+0x0C), unused`, chain-terminated by
   `0xFFFFFFFF`; the old code had 0x08/0x0C swapped and used 0 instead of `0xFFFFFFFF`.
4. **Names are UTF-16LE, not UTF-8.** Most 3DS RomFS images use UTF-8; this one does not. An ASCII
   reader silently loses every one of the 21,250 paths. Names are now decoded as UTF-16LE with a
   clear error on malformed data.

Plus two more in the validation layer: ExeFS entry offsets are relative to the *end* of the
0x200-byte ExeFS header (not the region start), and the ExeFS/NCSD magic checks had the same
signature-prefix mistake. The RomFS reader is now itself covered by tests against the extracted
`game_data/romfs` tree.

---

## 2. The `mod/` convention (defined here; editors were not yet writing it)

Coordinated check: `grep` over `viewer_rs/src` found **no** `mod/` usage, and the E1/E2/E3 tasks
(`orchestration/tasks/E1_tables.md`, `E2_text.md`, `E3_scripts.md`) only say "save into the mod
workspace (`mod/romfs/...`)" without defining it. No done report exists for E1/E2/E3 and
`tools/table_edit.py` is stale against the current format-2 `tools/table_schemas.json`. So the
convention is defined by this task and documented in `docs/EXPORT.md`:

```
mod/
├── mod.json          {"name","version","author","description"}   (copy mod.example.json)
├── romfs/<path>      replacement files, path exactly as in the cartridge RomFS
└── code/code.bin     full decompressed executable (7,090,176 B), optional
```

Decisions recorded:

- **`mod/romfs/` mirrors the RomFS, so it holds PACKs, not loose assets.** The item table is a
  member of `syscmn.pack`, so an edited table is staged as `mod/romfs/syscmn.pack`. This is the
  one place where the E1/E2 wording ("save the patched BXON into mod/romfs") does not literally
  work: a bare `mod/romfs/item.bxon` is not a RomFS path and would be rejected.
  To make the editors' job trivial, `export_mod.py` gained two staging commands:
  - `--stage-table syscmn/item.json --replacement build/item.bxon` (pack + member name come from
    `table_schemas.json`'s new `pack` field),
  - `--stage-pack <pack> --member <member> --replacement <file>` (anything else).
  Both rebuild the pack with the already-tested `tools/patch_asset.rebuild_pack` (handles `PACA`
  compression and size changes) and write it into `mod/romfs/`.
- **`tools/patch_game.py --stage-mod`** gives the level editor the same one-liner: it rebuilds
  `level3d/<map>.pack` into `mod/romfs/level3d/<map>.pack` instead of a 4 GiB ROM.
- **`mod/` ships empty.** An empty mod must reproduce the retail image byte for byte; that is the
  pipeline's honesty check, so the default checkout exports the unmodified game.
  `mod/mod.example.json` is the metadata template; a missing `mod.json` is a warning, not an error.
- **Only existing RomFS files can be replaced.** Luma LayeredFS resolves paths and the RomFS
  rebuild reuses the retail file table, which has no free space. This is refused with an
  explanation rather than producing a cartridge that cannot find the file.

---

## 3. Files

**New**
- `mod/README.md`, `mod/mod.example.json`, `mod/romfs/`, `mod/code/` — the workspace itself.
- `docs/EXPORT.md` — convention, staging recipes, targets, SD-card/Godmode9 install steps,
  validation matrix, troubleshooting, "what is not verified".
- `run_export.bat` — asks for the target (`luma` / `3ds` / `all` / `check` / `cia`), shows what the
  mod contains, runs the exporter, explains where the results are.
- `tests/tier4_real_world/test_scenario_9_mod_export.py` — 16 tests (see §6).

**Changed**
- `tools/export_mod.py` — the four parser fixes above, `read_title_id`/`parse_ncsd`/`parse_ncch`/
  `validate_exefs` corrections, `--stage-table` / `--stage-pack`, UTF-16 name handling, dead-code
  cleanup in `inspect_ips`, docs in the module docstring.
- `tools/repack_rom.py` — new `--romfs <image>` (embed an externally built, already validated
  RomFS instead of rewriting `original/romfs.bin`), and a guard that stops with a clear message if
  a recompressed `.code` would move the ExeFS/RomFS boundary instead of writing a broken image.
- `tools/patch_game.py` — new `--stage-mod [DIR]` (level patch → `mod/romfs/level3d/<map>.pack`);
  partial runs (`--no-rom`, `--stage-mod`) now write `build/PATCH_REPORT.partial.json` so they no
  longer clobber the `build/PATCH_REPORT.json` that `tools/verify_project.py` reads.
- `docs/README.md`, `README.md` — additive pointers to `docs/EXPORT.md` (one line each).
- `AGENT_LOG.md` — Entry 48.

`tools/recompile_game.py` needed no change: it is the baseline ("does `asm/` still reassemble to
the retail ROM") pipeline, not part of the mod path; `docs/EXPORT.md` says so.

---

## 4. Targets and what each one is

| Target | Output | Notes |
|---|---|---|
| `luma` | `out/luma/titles/0004000000199200/romfs/<changed files only>`, plus `code.ips` (or `code.bin` with `--code bin`) | Recommended on hardware. Copy the contents of `out/luma` to the SD root, enable "Enable game patching" in Luma3DS (SELECT at boot). |
| `3ds` | `out/3ds/romfs.bin` + `out/3ds/DQXI_modded.3ds` (4,294,967,296 B) | Full NCSD rebuild via `repack_rom.py`; flashcart / Godmode9. |
| `cia` | `out/cia/BLOCKED.md`, exit code 3 | **BLOCKED** — see §8. |
| `--no-rom` | `out/3ds/romfs.bin` only | Fast check: patched RomFS + IVFC rebuild + per-file verification. |

Title ID is read from the cartridge (`original/ncch0_header.bin`, program ID at `0x118`), not
hard-coded. `code.ips` is a plain IPS diff against `original/exefs/code.decompressed.bin`; a
one-byte native edit produces a 14-byte patch, and the exporter re-applies its own patch to prove
it reproduces `mod/code/code.bin`.

For a modified RomFS, `repack_rom.py` recomputes: NCCH RomFS size, content size, RomFS hash-region
size, RomFS superblock SHA-256, NCSD partition 0 size, the offsets of partitions 1/6/7, the
card-info "filled size", and the trailing 0xFF padding (so the image stays exactly 4 GiB).

---

## 5. Validation performed on every export

Re-parsed from the written files, never trusted from the writer:

| Check | Evidence in `out/EXPORT_REPORT.json` |
|---|---|
| NCSD magic, partition bounds/overlap, 4 GiB size | `partitions`, `used_bytes`, `trailing_padding` |
| NCCH magic, content size vs partition 0, ExHeader + logo SHA-256 | `exheader_hash_ok`, `logo_hash_ok`, `content_size` |
| Every ExeFS entry hash + ExeFS superblock SHA-256 | `exefs.all_hashes_ok`, `exefs.superblock_ok` |
| `.code` decompresses to 7,090,176 B with the requested SHA-256 | `code_uncompressed_size`, `code_uncompressed_sha256` |
| NCCH RomFS superblock SHA-256 | `romfs_superblock_ok` |
| All three IVFC levels (648,986 data blocks, 5,071 level-1 blocks, 40 master blocks) | `ivfc.bad_level2/1/master == 0` |
| Image RomFS bytes == validated `out/3ds/romfs.bin` | `romfs_sha256` |
| Every modified file present in the rebuilt RomFS with the exact bytes | `mod_files[]` |
| Empty mod ⇒ image SHA-256 == retail | `expect_retail` check, `retail_identical` |
| Luma folder holds exactly the changed files, bytes round-trip, never both `code.bin`+`code.ips` | `build_luma` assertions |
| `code.ips` reproduces `mod/code/code.bin` | `inspect_ips` |

Manual end-to-end runs (all PASS, timings on this machine):

- empty mod → `--target 3ds`: `0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74`
  (= retail), 4,294,967,296 B, full re-parse OK (~26 s).
- one item-table scalar (row 0 `buy_price` 0 → 1234, and later 2 scalars) → clear Luma folder,
  rebuilt image SHA `c76a0c79…`, IVFC 0 bad blocks, modified pack found in the image RomFS (~33 s).
- one native byte changed at `0x6C2D80` (inside the image's end-of-`.data` alignment padding, so it
  cannot crash the game) → `code.ips` 14 B; rebuilt image decompresses to the exact
  `94a5a68e96decad787770d4923e4c0ad342a7e829f38d43e9f4943b34416d2b8` requested code, ExeFS
  hashes and superblock OK (~26 s).
- `run_export.bat check` with a staged table: prints the workspace, rebuilds and validates
  `out/3ds/romfs.bin`, explains where the results are.
- **boot smoke test in Citra Nightly 1917** (found on this machine at
  `%LOCALAPPDATA%\Citra\nightly-mingw\citra.exe`): `out/3ds/DQXI_modded.3ds` loads as
  "DRAGON QUEST XI" (Program ID 0004000000199200), the window reports **FPS: 30 (100%)**, the game
  runs 120+ s of service calls (FS/APT/Y2R/DSP), a 4 KB region at 0x1F000000 changes every sample
  (video/GPU active), and Citra's RPC memory reader returns bytes at `0x00100000` that match
  `original/exefs/code.decompressed.bin` exactly at 0x0, 0x100000, 0x300000 and 0x600000 (1 KB
  each) — i.e. the emulator's own BLZ decompressor accepted the `.code` we embedded.
  Control: Azahar 2126.2 stalls at ~3.4 s on both the *retail* and the modded image because its
  fresh user dir has no DQXI save data (same log, same last line, both ~idle) — an environment
  problem, not an export defect. A title-screen screenshot was not captured (Qt/OpenGL window
  capture returns black, `Ctrl+P` did not reach the window in this session).

---

## 6. Tests

`tests/tier4_real_world/test_scenario_9_mod_export.py` (16 tests, all pass). They run the real
exporter, not mocks:

- `TestRomFsIndex` (3): the UTF-16 RomFS reader finds all 21,250 files, paths/sizes/bytes match
  `game_data/romfs`, and `/2dcmn.pack` proves names are not being decoded as ASCII.
- staging (2): `schema_pack_for("syscmn/item.json") == ("syscmn.pack", "item.bxon")`; the staged
  pack holds the edited value and no loose `.bxon` appears in `mod/romfs`.
- Luma (2): only `syscmn.pack` is in the LayeredFS folder with byte-identical content, no
  `code.ips`/`code.bin` when the native image is unchanged; the title folder is the cartridge's
  program ID.
- `.3ds` (2 + 1): full-size image, not retail-identical, ExeFS/ExHeader/logo/RomFS-superblock/IVFC
  all OK, retail code still inside; an independent re-parse of the image finds the edited pack,
  keeps a neighbouring file untouched (`/gamecmn.pack` byte-equal), and the embedded `romfs.bin`
  hash matches the report; the report records the change and the mod metadata.
- empty mod (1): export produces a **byte-identical** retail `.3ds`.
- native code (1): three changed bytes → small `code.ips` that re-applies to exactly
  `mod/code/code.bin`.
- level editor (1): `patch_game.py --stage-mod` lands the map pack in `mod/romfs/level3d/` and it
  comes out in the Luma export.
- refusals (3): a new RomFS path, a wrong-size `code.bin`, and `--target cia` (exit 3, no fake
  `.cia`, `BLOCKED.md` present).

Results (final run):

```
python tests/run_all.py
Tier 1:  70 run / 70 pass    Tier 2: 70 / 70
Tier 3:  14 / 14             Tier 4: 62 / 62  (my 16 included; 110 s of the 125 s total)
TOTALS: 216 / 216 pass, 0 fail, 0 skip -> SUCCESS   (threshold >= 161)

python tools/verify_project.py      -> OVERALL: PASS (audit/PROJECT_VERIFICATION.json)
python tools/verify.py              -> PASS: 16 manifest files + bit-matching repacked ROM
```

Tier 4 got slower (23 s → 125 s) because two of the new tests write and re-read a real 4 GiB image.
That is deliberate: "empty mod exports the retail ROM bit-for-bit" cannot be proven without it.

---

## 7. What the modder sees

- `run_export.bat` in the project root, one question, then `out/…` + `out/EXPORT_REPORT.json`.
- `docs/EXPORT.md`: workspace rules, "first mod in five minutes" using real commands
  (`bxon_patch.py` → `--stage-table` → `--target luma`), installation on SD card / Godmode9,
  a troubleshooting table keyed by the exact error messages the tools print.
- Every message names the file and the fix, e.g.
  `mod file /my_own.pack is not in the retail RomFS. This exporter only replaces existing files: adding files would need the RomFS directory/file metadata tables rebuilt (they have no free space).`
- No `FUN_xxxx`/`param_1` anywhere in the new user-facing code; comments explain *why*
  (signature prefix, UTF-16 names, field order, why signatures cannot be regenerated).

---

## 8. BLOCKED — CIA

`--target cia` is intentionally blocked and writes `out/cia/BLOCKED.md` + exit code 3.
Reasons (also in `docs/EXPORT.md`): no CIA builder exists (`makerom`/`3dstool`/`bannertool` are
absent from `third_party/` and the machine, and this task may not download software); a CIA needs
a ticket with an encrypted title key and a signed certificate chain, which a cartridge dump does
not contain; `original/` is a *decrypted* dump, so NCCH content would have to be re-encrypted with
that key; and there is no console/emulator/CIA installer here to demonstrate installability.
Producing an unverifiable "installable" file would be dishonest, so none is produced.

---

## 9. Not verified / open problems (honest list)

1. **No real console.** No 3DS/2DS was available. The rebuilt image *was* boot-tested in Citra
   Nightly 1917: it loads, runs at 30 fps (100%) for 120+ s, GPU output updates, and the mapped
   `.code` equals the retail executable at four sampled offsets (so the emulator's BLZ
   decompressor accepted our stream). What that does **not** prove: reaching the title screen was
   not seen (no screenshot possible — Qt/OpenGL capture returns black and the `Ctrl+P` hotkey did
   not reach the window in this session), and the modified item value was never exercised in-game
   (that needs gameplay, not boot).
2. **RSA signatures are stale** in the rebuilt `.3ds` (impossible without Nintendo's private key).
   Fine under CFW/flashcarts that skip signature checks; a signature-enforcing loader will refuse
   it. Luma LayeredFS sidesteps the issue, which is why it is the recommended target.
3. **RomFS files cannot be added**, only replaced (retail metadata tables have no free space).
4. **ExeFS growth is refused, not handled.** If a future `code.bin` recompresses to a different
   layout size, `repack_rom.py` raises instead of moving the RomFS. Luma `code.ips` has no such
   limit.
5. **`--target 3ds` was not tested with an ExeFS-relayout case** (by construction it refuses).
6. **Luma's actual patch loading is untested here** (needs a console); the folder layout, title ID
   and `code.ips` semantics follow Luma3DS's documented LayeredFS rules.
7. Other workers' state: `tools/table_edit.py` is broken against `tools/table_schemas.json`
   format 2 (`load_schema` still expects the old shape; `list` also crashes on a cp1252 console
   when printing Japanese), and no E1/E2/E3 done report exists. My staging path deliberately does
   not depend on `table_edit.py` (it uses the schema + `patch_asset.rebuild_pack`), but the editor
   tool itself still needs E1 to finish. Also, during this session another agent added
   `tests/tier4_real_world/test_scenario_10_table_editor.py` and one run of `patch_game.py`
   transiently lost `build/patched_input/partitions/*` — consistent with a concurrent worker
   using the same `build/` scratch directory. A retry succeeded; worth serialising `build/` use.
8. `README.md` still quotes `97712a2d…` for the checked-in smoke edit's patched ROM; rebuilding it
   today gives `0bdbb7bb…` (the checked-in `level3d.patched.bxon` has been re-exported since).
   Not fixed here because it is a shared file and the number may change again with E-tasks.

---

## 10. Suggested follow-ups

1. **X2_playtest** — run `out/3ds/DQXI_modded.3ds` in Citra/Azahar and drive it with input so a
   real screen can be verified. Useful facts found during X1: Citra Nightly 1917 lives at
   `%LOCALAPPDATA%\Citra\nightly-mingw\citra.exe` and has a **working RPC server**
   (`scripting/citra.py`, UDP 45987) for memory reads — that is how the `.code` mapping was
   verified here; its window reports `FPS: 30 (100%)`. Azahar 2126.2 (in
   `%TEMP%\opencode\azahar\...`) stalls at boot with a fresh user dir (no save data) for *both*
   retail and modded images, so it needs Citra's populated `%APPDATA%\Citra` or a first-run fix
   before it is useful. Screenshot capture of the Qt/OpenGL window failed (`PrintWindow` → black);
   screen pixels can instead be read from FCRAM via RPC (0x1F000000 was live) once the right
   framebuffer address/format is identified.
2. **E1/E2/E3** — wire their "Save to mod" buttons to `export_mod.py --stage-table`
   (`--stage-pack` for anything not in the schema) and fix `table_edit.py` for schema format 2.
3. **Editor button** — add an "Export mod" action in `viewer_rs` that shells out to
   `run_export.bat` (or `export_mod.py --target luma`) and shows `out/EXPORT_REPORT.json`.
4. **CIA** — only if a builder appears on the machine: `makerom`/`3dstool` + a title key/ticket
   source would be needed; otherwise keep it documented as blocked.
5. **RomFS growth** — if adding files becomes desirable, the directory/file metadata tables (and
   the level-3 data offset) need a rebuild path; today's answer is "replace, don't add".
