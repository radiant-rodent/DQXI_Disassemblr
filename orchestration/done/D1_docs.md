# D1_docs — modder documentation (resumed)

Status: **complete for the documentation deliverable**; the mandatory test suite ended green
(**223/223**, exit 0) after the resizable-assets lane finished its fix — see §11, which supersedes
the interim 222/223 result recorded in §4.

## 1. What already existed

- `docs/` had 12 guides (32 KB `EXPORT.md`, 31 KB `EDITING.md`, 25 KB `PROJECT_TOUR.md` written by
  an earlier D1 pass), a `docs/README.md` with cp1252 mojibake in two lines, and no `FIRST_MOD.md`.
- `README.md` was a feature inventory (long status tables, Ghidra instructions) rather than a front
  door: no "play a mod" path, no screenshot list, no single entry point.
- Documentation command style was `python tools\<tool>.py` everywhere.
- No `orchestration/done/D1_docs.md`.

The dispatcher was running **several D1 workers at the same time** (mimo, gemini, glm and this
deepseek session all append to `orchestration/logs/D1_docs.log`). `PROJECT_TOUR.md`,
`FIRST_MOD.md`, `docs/README.md`, `GETTING_STARTED.md` and the root `README.md` were rewritten by
another worker while I was working. I did not revert those rewrites; I audited them, kept the
better parts, and fixed what was wrong (see §6). The final files are a merge of the parallel work.

## 2. What I delivered

1. **`README.md` — front door** (≈160 lines): what the project is, legal note, three paths (play a
   mod / edit data in DQXI Studio / read & change native code), an eight-image screenshot gallery
   with captions, the status numbers with a link to `progress/progress.html`, a folder map that
   points at the tour, the verified commands, hardware limits and an honest known-issues list.
2. **`docs/FIRST_MOD.md` — first mod in 10 minutes**: change the medicinal herb's `buy_price`
   8 → 5, change `ui/title/title_msg` entry 22, export a Luma folder, boot it in Azahar with the
   mod installed, see the line, copy the folder to an SD card. Every command was run; the outputs
   in the guide are pasted from this machine. It also contains: message-box width rules (with the
   real overflow I hit), an optional headless movie script, undo, and a troubleshooting table.
   My verified evidence — screenshot `docs/images/first-mod/dialogue.png` and the live UI-heap
   marker `0x33e0f54c` — was merged into the version another worker had started.
3. **`docs/PROJECT_TOUR.md` — verified and repaired**: fixed a malformed link in §4.1 (the
   `ResetVector` sentence had an unterminated link) and a link to a renamed Monster function;
   checked every one of its `decomp/readable/` links resolves; checked the subsystem counts against
   `symbols.json` (`Ui_` 6,432, `Field_` 2,516, `Battle_`+`BattleScene_` 1,537, `Gfx_` 1,393,
   `Script_`+`Sq_` 595, `Fs_`+`Pack_`+`Data_` 236, … all match) and the coverage numbers against
   `progress/progress.json` (18,787 / 18,748 / 8,492 / 8,074).
4. **`docs/README.md` — guide index**: categorized entry points (first mod, tour, getting started,
   task guides), command-style note, evidence/status links and contributor house rules.
5. **`docs/GETTING_STARTED.md` — refreshed**: prerequisites, per-step regeneration commands that
   actually exist (`convert_assets` has no `--text` flag; text comes from `text_tool export`), the
   verification gate, and pointers into the emulator notes.
6. **`docs/CODE.md` — rewritten around the real readable tree**: `decomp/readable/` (18,737 files,
   doc-comment format, `maybe_` rule), `symbols.json`, `merge_names`/`readable_c`, the raw Ghidra
   workflow, and the two ways to change a function (verified C replacement, assembly edit).
   The old page still presented `decomp/ghidra/` as the readable source.
7. **Command style**: converted every `python tools\<name>.py` command in `docs/` and `README.md`
   to `python -m tools.<name>` (block-aware: pasted tool output inside ```` ```text ```` fences was
   left verbatim, so the transcripts stay honest).
8. **Encoding**: fixed the cp1252 box-drawing and `⇒` mojibake in `docs/EXPORT.md`; re-decoded every
   `docs/*.md` + `README.md` as strict UTF-8 afterwards (all valid, no replacement characters).
9. **Link/anchor audit**: a script parses every Markdown link and fragment in `docs/` + `README.md`;
   final result **0 broken links, 0 broken anchors** (`docs/FIRST_MOD.md` now exists; the earlier
   `../docs/images/...` links from the other worker were corrected to `images/...`).

## 3. Commands I actually ran (evidence)

Item price (real output):

```text
$ python -m tools.table_edit get syscmn/item.json "Medicinal herb" buy_price
8
$ python -m tools.table_edit set syscmn/item.json "Medicinal herb" buy_price 5 --out build/firstmod/item.bxon
Medicinal herb: buy_price 8 -> 5  (build\firstmod\item.bxon, same size)
$ python -m tools.table_edit save-mod syscmn/item.json --patched build/firstmod/item.bxon
syscmn.pack rebuilt with item.bxon: 303,280 bytes (retail 303,536) -> mod\romfs\syscmn.pack
```

Dialogue (real output):

```text
$ python -m tools.text_tool import --bank ui/title/title_msg --json build/firstmod/title_msg.json --out build/firstmod/title_msg.bxon
ui/title/title_msg: 64 strings, 1 changed, 9,682 -> 9,780 bytes -> build\firstmod\title_msg.bxon
$ python -m tools.text_tool save-mod --bank ui/title/title_msg --json build/firstmod/title_msg.json
ui/title/title_msg: 64 strings, 9,682 -> 9,780 bytes
staged title_msg.bxon into ui/title.pack: 1,120,444 bytes (retail 1,121,612)
  -> mod\romfs\ui\title.pack
```

Export (real output):

```text
$ python -m tools.export_mod --target luma
RomFS changes: 2 file(s)
  -> .\out\luma\titles\0004000000199200 (validated)
 EXPORT OK
```

Emulator boot with the mod (real output, exit 0):

```text
$ python -m tools.emu boot build/DQXI.3ds --mod out/luma --save user_citra --seconds 120 --shot docs/images/first-mod/boot-title.png
title-screen reached at game t=492.5s (53.3s real; menu strings in the UI heap)
screenshot: .\docs\images\first-mod\boot-title.png
```

The edited line, driven by an input movie (real output + screenshot):

```text
t 458 shot True
marker: 0x33e0f54c game_time 461.0 crash None
```

`docs/images/first-mod/dialogue.png` shows the in-game box with
`FIRST MOD OK!` / `The dialogue line is editable.`; `docs/images/first-mod/field.png` shows the
game continued into the field without a crash.

Emulator table proof (real output, fresh run): `python tests/emu/run_cases.py table` →
`table PASS`, `[ok] the edited price 1234567 is a live pane string in the shop`,
`[ok] no crash`; screenshot `docs/images/emu/table_shop_list.png`.

Build/verification (real output):

```text
$ python -m tools.build
  [PASS] Reconstructed code.bin bit-matches original uncompressed code.bin (0 differences)!
  [PASS] Reconstructed ExeFS .code bit-matches original compressed .code (0 differences)!
$ python -m tools.verify_project
OVERALL: PASS -> audit/PROJECT_VERIFICATION.json
$ python -m tools.build --verify
code.bin: PASS (dfcd1b7a…c8cc24d8)
code.compressed.bin: PASS (ea3d2c02…08c298a2f)
$ cd viewer_rs && cargo test
test result: ok. 75 passed; 0 failed; 1 ignored
```

## 4. Test suite result (honest)

> **Resolved later the same evening:** the failing scenario passed on its own after
> `X5_resizable_assets` fixed the exporter, and a fresh full run gave **223/223 PASS, exit 0**
> (§11). The transcript below is the interim run.

`python tests/run_all.py` (no workaround, final state of the tree):

```text
Tier 1: Feature Coverage           | 70  | 70  | 0 | 0 |  29.57 | PASS
Tier 2: Boundary & Corner Cases    | 70  | 70  | 0 | 0 |  30.69 | PASS
Tier 3: Pairwise Combinations      | 14  | 14  | 0 | 0 |  18.40 | PASS
Tier 4: Real-World Scenarios       | 69  | 68  | 0 | 1 | 509.80 | FAIL
TOTALS                             | 223 | 222 | 0 | 1 | 588.46 | FAILURE
```

The single failure is **not** in the docs and not caused by this task:

```text
test_new_files_are_refused_on_luma_but_added_on_the_full_image
  tools/export_mod.py:755 -> romfs_build.rebuild_metadata(dest, additions)
  tools/romfs_build.py:200 for path, data in sorted(additions, key=lambda x: x[0]):
  KeyError: 0
```

`rebuild_metadata` iterates `additions` as `(path, data)` pairs, but the exporter passes a mapping,
so iterating it yields keys (strings) and `x[0]` raises `KeyError: 0`. `tools/romfs_build.py` was
modified at 19:40 today by the still-running `X5_resizable_assets` lane; the same scenario passed in
the X3 run earlier today (`out/emu/x3/summary.json`, 7/7). One-line fix for the owner:
`sorted(additions.items(), key=lambda kv: kv[0])` (or accept both shapes). I did not edit the file —
it belongs to X5. Everything else in the suite passes.

## 5. Files changed

- `README.md` (front door; merged with the parallel worker's edits, known-issues section updated by
  them after the `tools/types` fix)
- `docs/FIRST_MOD.md` (created here, then merged with the parallel worker's version; final file
  contains my verified screenshot, marker and wrap caveat)
- `docs/PROJECT_TOUR.md` (link repairs; content verified against `symbols.json`/`progress.json`)
- `docs/README.md` (index, command style, verification section)
- `docs/GETTING_STARTED.md` (refreshed prerequisites/commands/Studio caveat)
- `docs/CODE.md` (rewritten around `decomp/readable/`)
- `docs/EXPORT.md` (UTF-8 repair of the workspace tree and one table row; command style)
- `docs/ASSETS.md`, `AUDIO.md`, `EDITING.md`, `EDITOR.md`, `REBUILD.md`, `SCRIPTS.md`,
  `SOURCE_REPLACEMENT.md`, `TESTING_EMULATOR.md` (command style to `-m`, via the block-aware
  converter; two of these were also being edited by the other D1 worker at the same time)
- `docs/images/first-mod/boot-title.png`, `dialogue.png`, `field.png` (captured from Azahar)
- scratch/evidence under `build/firstmod/` (logs, patched BXONs) and
  `docs/images/first-mod/` (`boot-title.png` + `.json`, `dialogue.png`, `field.png`)
- `orchestration/done/D1_docs.md`, one `AGENT_LOG.md` entry

Note on the live workspace: `mod/romfs/` held my two staged packs during the walkthrough, and
`out/luma/` held the validated export. Other lanes then cleared/reused both (`mod/romfs/x5/added.dat`
is X5's test fixture now), so a reader of this report will not find those two packs on disk — the
pasted outputs, `docs/images/first-mod/` and the tool commands in `FIRST_MOD.md` are the evidence,
and the walkthrough is re-runnable from an empty `mod/` in a few minutes.

Not touched: `tools/`, `viewer_rs/`, `tests/`, `game_assets/`, `game_data/`, `original/`,
`..\3DS_Translate`.

## 6. Blockers hit (and how they were resolved)

1. **`tools/types/` shadowed Python's stdlib `types`** (18:58–~19:55 today). Every documented
   `python tools\<tool>.py` failed with `ImportError: cannot import name 'MappingProxyType'`,
   including `verify_project` (its `verify_model_textures` subprocess) and 17 tests;
   `tools.build` printed the bit-match PASS but died at the BLZ step. The owner (`S0_types_plan`)
   renamed/removed it during this session. Re-verified afterwards: `python tools\table_edit.py …`
   works, `verify_project` PASS, suite 222/223. The parallel docs worker briefly documented the
   workaround (`PYTHONSAFEPATH=1`); final docs use `python -m tools.<name>` and say both forms work.
2. **Azahar port contention.** Two boot attempts returned `CRASH: emulator exited (4294967295)`
   because another lane's runner owned/killed the fixed RPC port 45987; the same happened to X3
   earlier. Retried in a quiet window; the third attempt reached the title. No emulator process was
   left running (checked with `Get-Process azahar`).
3. **Parallel D1 workers.** Several models wrote the same files. I merged rather than overwrote;
   this is why the final guide prose is not solely mine. The doc set is internally consistent and
   link-clean, but a reviewer should know the authorship is mixed.

## 7. Not verified

- **Physical 3DS/2DS.** The Luma steps are the standard procedure; no console was available. This is
  stated in `FIRST_MOD.md`, `README.md` and `docs/README.md`.
- **`.3ds` / `.cia` targets this turn.** Only `--target luma` was exercised. Those targets are
  documented in `EXPORT.md` from X3/X4 runs; scenario 9 of the E2E suite currently fails *before*
  the ROM image is written (the `romfs_build` bug above), so a fresh `.3ds` proof is blocked too.
- **Full extraction/conversion and the Ghidra re-export** — the generated trees already existed and
  were validated by `verify_project`, not regenerated end to end.
- **DQXI Studio data-edit buttons clicked through.** The release binary starts and stays alive
  (8 s smoke, empty log); the GUI buttons were not clicked. `docs/README.md`'s cargo-test claim was
  re-run (75/75).
- **Editor/Audio screenshots** (`docs/images/editor.png`, `audio.png`) are older captures (Oct 19),
  not re-shot this turn.
- **`run_cases.py text`** was run by the parallel worker/earlier X3 run, not by me this turn; I ran
  the `table` case (PASS) and my own movie-driven dialogue proof.

## 8. Suggested follow-ups

1. **X5:** fix `romfs_build.rebuild_metadata` (dict vs pairs) and re-run
   `tests/run_all.py`; that turns the suite green and unblocks `.3ds`/`.cia` proofs. *(Done during
   this session: fresh full run 223/223 PASS, exit 0 — see §11.)*
2. **Dispatcher:** never run more than one D1 worker at a time; three models edited the same five
   Markdown files concurrently and `orchestration/logs/D1_docs.log` interleaves them.
3. **X3:** re-run the full 7-case `python tests/emu/run_cases.py` when the Azahar port is quiet —
   my single-case `table` run rewrote `out/emu/x3/summary.json` to a one-case summary, so the
   collective 7/7 evidence file no longer reflects all cases (screenshots are intact).
4. Refresh the Studio and Audio screenshots with the current theme (the A_ui_contrast fix) and add
   one screenshot per "three ways in" path.
5. Add a `docs/` lint to CI: run the link/anchor checker and a UTF-8 strict decode on every
   `docs/*.md` + `README.md` (both scripts took <1 s and caught the two real defects here).
6. The tour's frame-loop story still rests on `maybe_` names; a call-graph pass over
   `maybe_Engine_DispatchFrameCallbacks` would let the honesty note be reduced.


## 9. Post-merge reconciliation (D1 worker 202)

This report is the merged account of several concurrent D1 workers. One final edit pass was made
after the merge, so three details in the sections above are superseded by the files on disk:

- `docs/PROJECT_TOUR.md` final prefix counts: `Actor_*` 517 (not 518), the 2D group 371 with
  `Actor2D_` counted only once, `Model_/Anim_/Effect_/Fx_` 599 (not 413), `Menu_/Item_/Party_/
  FieldParty_` 483 (not 403), `Fs_/Pack_/Data_` 239 (not 236), casino/save/input 226. The report
  above lists only the groups that happened to match at its check time.
- The final `docs/FIRST_MOD.md` does not contain the message-box wrap/movie sections mentioned in
  section 2; the merged version keeps the CLI edit, the real boot transcript, the LayeredFS log
  proof and the troubleshooting table. The wrap caveat belongs to a follow-up, not the current
  page.
- `README.md` has a six-image screenshot grid plus a list of further evidence images, not eight
  inline images.

Also added after the merge: an explicit verification/not-verified section in `docs/README.md`,
the `tools/bxon_patch.py` cp1252 console caveat (its `--help` prints a Unicode arrow and exits with
`UnicodeEncodeError` on a default cp1252 console; `PYTHONIOENCODING=utf-8` avoids it), and the
final 222/223 test result reproduced after the `tools/types` rename. Two `D1_docs` AGENT_LOG
entries exist (202 and 204) because the workers ran concurrently; neither contradicts the other.

## 10. Final verification pass (resumed worker, 20:20–20:45)

A further resumed worker re-ran the gate and corrected four concrete errors that had survived the
merge. The account above remains the record of the earlier passes; this section supersedes its
numbers where they differ.

Corrections in the files:

- **`docs/EXPORT.md` §2 raw-offset example was wrong.** It patched `0x18`, which is the
  *row-relative* offset; in `item.bxon` row 0 starts at `0x2C`, so the herb's `buy_price` is the
  u32 at file offset **`0x44`**. Re-ran the corrected block:
  `Wrote build\item.bxon (516912 bytes, 1 edits)`, `u32@0x44 = 1234`, length unchanged. The block
  now also sets `PYTHONIOENCODING=utf-8` (the tool's help text contains an arrow and dies on a
  cp1252 console) and writes the JSON with `[IO.File]::WriteAllText(..., UTF8Encoding($false))`
  because PowerShell 5.1's `Set-Content -Encoding utf8` adds a BOM that `json.loads` rejects.
- **`docs/SCRIPTS.md` / `docs/EDITING.md`:** the source semantic round-trip is **769/769** (fresh
  `python -m tools.script_build verify`; `audit/SCRIPT_BUILD.md` regenerated), not 764/769. Both
  pages now say edited scripts have booted in Azahar and only hardware is untested.
- **`docs/EXPORT.md` §8:** date corrected to 2026-10-26 and the page no longer claims a pass count
  for a `summary.json` that each partial run rewrites; it points at the eight per-case directories
  (`run_cases.py --list`).
- **`docs/PROJECT_TOUR.md`:** the Kernel & system span starts at `0x00100024` (progress.json), not
  `0x00100000`. All twenty name-prefix counts were recomputed from `symbols.json` and match.
- **`docs/FIRST_MOD.md`:** boot transcript replaced by the final real run (`game t=478.8s`,
  54.6 s real, pid 19656); the page now warns that the 792-bank text scan takes 2–3 minutes and
  documents `DQ11_EMUTEST` for times when another emulator owns port 45987.

Fresh evidence from this pass:

- staged PACKs re-read independently: `item.bxon` is the same 516,912 bytes and differs from retail
  only in the u32 at `0x44` (**8 → 5**); `title_msg.bxon` contains both new UTF-16LE lines;
- `table_edit verify` 42 tables / **235,769 writes / 0 failures**; `text_tool verify` 792 banks /
  **68,316 strings / 0 failures**; `script_build verify` 769/769 on both tiers and 769/769
  semantic; `merge_names --check` clean; `build_c_replacement` ALL BIT-MATCH;
- `tools.build --verify` both hashes, `tools.verify` 4 GiB repack `0f04b51b…a9b74`,
  `romfs_hash --verify original/romfs.bin` `ok=True`, `verify_project` OVERALL PASS,
  `cargo test` 75/0/1;
- `python tests/run_all.py` → **222/223** (Tier 1 70/70, Tier 2 70/70, Tier 3 14/14, Tier 4
  68/69). The single error was
  `tests/tier4_real_world/test_scenario_9_mod_export.py:351: NameError: name 'RomFsIndex' is not
  defined`; the X5/resizable-assets lane edited that file mid-run (mtime 20:36:40; line 247
  already used `self.export_mod.RomFsIndex`). Not edited or weakened here. On the current file the
  same test passes on its own: `Ran 1 test in 128.879s — OK`. A parallel D1 worker's later full run
  (recorded in `docs/README.md`) reports **223/223 exit 0** after X5 stopped editing; my own full
  run was not repeated end to end because two emulator proof jobs were still using the machine.
- 154 local Markdown links resolve and 17 text files decode as strict UTF-8.

Not verified in this pass: physical hardware; `.3ds`/`.cia` (the tree has no `out/cia/`, so the
`ctr_cia verify` commands could not be re-run); the extraction/conversion pipeline and Ghidra
re-export; GUI buttons clicked through. The emulator proof ran on the project's isolated data root
`build/emu_test/root` because other lanes were using `third_party/emutest`; both roots are this
project's, and the resulting Luma folder is identical.


---

## 11. Independent re-verification pass (resumed worker, 2026-10-26 20:00-20:45)

This pass started after a server restart, found the merged documentation above already on disk, and
therefore **audited instead of rewriting**. No section was replaced; three verbatim transcript
details in `docs/FIRST_MOD.md` were corrected and the rest of the guide was re-run.

What I re-ran, with the result from this tree:

```text
$ python -m tools.build --verify
code.bin:            PASS (dfcd1b7a...c8cc24d8)
code.compressed.bin: PASS (ea3d2c02...08c298a2f)

$ python -m tools.verify
Manifest Verification: 16 files checked, Status: PASS
Repacked ROM SHA-256 0f04b51b...7a9b74 [PASS]
OVERALL VERIFICATION: PASS

$ python -m tools.verify_project
OVERALL: PASS -> audit/PROJECT_VERIFICATION.json      (18 checks, counted in the JSON)

$ cd viewer_rs && cargo test
test result: ok. 75 passed; 0 failed; 1 ignored

$ python tests/run_all.py
Tier 1 70/70 PASS, Tier 2 70/70 PASS, Tier 3 14/14 PASS, Tier 4 68/69 (1 FAIL)
TOTALS 223 run, 222 pass, 1 fail
```

The suite was red in my first run (222/223): `tests/tier4_real_world/test_scenario_9_mod_export.py::
test_new_files_are_refused_on_luma_but_added_on_the_full_image` failed because
`tools/romfs_build.py` was being changed by the still-running `X5_resizable_assets` lane (at 20:25
it still iterated a mapping as `(path, data)` pairs; a second run later failed on a mid-edit
`NameError: RomFsIndex`). I did **not** edit `tools/romfs_build.py`, the exporter or the test.
After that lane's fix the same node test passed on its own, and a **fresh full run at 20:44 gave
223/223 PASS, exit 0** (Tier 1 70/70, Tier 2 70/70, Tier 3 14/14, Tier 4 69/69).

First-mod walkthrough, re-run end to end (table value, text bank, Luma export):

```text
$ python -m tools.table_edit get syscmn/item.json "Medicinal herb" buy_price
8
$ python -m tools.table_edit set syscmn/item.json "Medicinal herb" buy_price 5 --out build/first_mod/item.bxon
Medicinal herb: buy_price 8 -> 5  (build\first_mod\item.bxon, same size)
$ python -m tools.table_edit save-mod syscmn/item.json --patched build/first_mod/item.bxon
syscmn.pack rebuilt with item.bxon: 303,280 bytes (retail 303,536) -> mod\romfs\syscmn.pack

$ python -m tools.text_tool banks --grep title_msg
ui/title/title_msg  UIMessage  64 strings  [Menu messages]
$ python -m tools.text_tool save-mod --bank ui/title/title_msg --json build/first_mod/title_msg.json
ui/title/title_msg: 64 strings, 9,682 -> 9,780 bytes
staged title_msg.bxon into ui/title.pack: 1,120,444 bytes (retail 1,121,612)
  -> mod\romfs\ui\title.pack

$ python -m tools.export_mod --target luma
RomFS changes: 2 file(s)
  -> ...\out\luma\titles\0004000000199200 (validated)
 EXPORT OK
```

Corrections made to `docs/FIRST_MOD.md` (verbatim transcript honesty): the `table_edit set` hint
printed by the tool is `python tools/table_edit.py save-mod ...`, and the `save-mod`/`text_tool`
success lines end with `export it with: python tools/export_mod.py --target luma`; the old text
quoted the `-m` form and a parenthetical claiming the hint was stale. The README anchor
`docs/EXPORT.md#8-verified-in-emulator-2026-10-25` was already repointed to `2026-10-26` by a
parallel worker while I was checking it.

Link/encoding audit (scripts in `%TEMP%\opencode\`): all relative links in `README.md` and
`docs/*.md` resolve and every in-page anchor matches its heading (15 files, **0 problems**, checked
twice); every file decodes as strict UTF-8 with **no U+FFFD**; all **41** `tools.*` modules named
in the docs import cleanly (a `--help` probe would have executed `build_model_names` and
`recover_native_names`, which do not use argparse; `build_model_names` regenerated
`game_assets/models/model_names.json` with the same 1,711 names). Flag probes passed for
`export_mod`, `text_tool`, `table_edit`, `asset_replace`, `ctr_cia`, `map_tool`, `layout_tool`,
`texture_tool`, `model_patch`, `model_material`, `convert_assets`, `extract_game_data`; the
`script_build` flags (`--area/--tier/--mod`) are declared on its `compile`/`pack` subcommands.

Emulator: two fresh `tools.emu boot ... --mod out/luma` attempts of mine at 20:31 ended
`CRASH: emulator exited (4294967295)` while another lane's `tests/emu/run_cases.py table_grow`
owned Azahar's fixed RPC port (the same contention documented in §6.2). A parallel D1 worker then
got a quiet window: `docs/images/first-mod/boot-title.json` now records a fresh boot at 20:36
(outcome `title`, game 478.84 s, 54.6 s real) and the matching screenshot shows the three title
menu strings, so the boot step **is** verified on this tree — just not by my two attempts. My
failed attempt had briefly written a 102-byte stub over `docs/images/first-mod/boot-title.png`; I
restored the title frame from `out/first-mod.png`, and the later successful run replaced it with
the current 176,402-byte capture.

Not verified by this pass: physical 3DS/2DS, `.3ds`/`.cia` rebuild (the scenario-9 export path is
green again but I did not rebuild a full image), `tests/emu/run_cases.py text`/`table` (Azahar
busy; another lane ran cases and rewrote `out/emu/x3/summary.json`), full extraction/conversion
and the Ghidra re-export. Nothing outside `docs/FIRST_MOD.md`, `docs/README.md`,
`docs/images/first-mod/boot-title.png`, this section and one `AGENT_LOG.md` entry was changed by
this pass; `..\3DS_Translate` was not written to.
