# X3_boot_tests — edits proven in the emulator + real-hardware gate

**Status: complete for the emulator proofs and the ARMv6K export gate.** No real 3DS/2DS was
available; §7 lists exactly what remains hardware-only. This report supersedes the earlier
version written by a concurrent run of the same lane: both passes' findings are folded in,
and the evidence table below is from the final run.

## 1. Starting point (what existed when the lane resumed)

- `tools/emu/` (A_emu_harness + A_emu_dedupe) could boot retail/modded ROMs to the title and
  report crash/hang, but nothing had been *played* past the title by this project.
- `tools/check_armv6k.py` did not exist; `tools/export_mod.py` had no instruction-set gate.
- The editors' tools (E1/E2/E3) existed, but none of their output had ever run in the game.
- **A concurrent worker was already running the same lane** and using the same emulator data
  root. Azahar's RPC port is compiled in; the two runs killed each other's emulator. All final
  runs below were done in exclusive windows (no other Azahar process).

## 2. What was built (final state)

| file | purpose |
|---|---|
| `tools/check_armv6k.py` | scans **changed** native words in the executable range (`.text` 0x100000-0x725000) for instructions a real 3DS cannot run (ARMv7 / VFPv3); skips PC-relative literal pools; exit 0/1/2. |
| `tools/export_mod.py` | runs the gate for every changed `mod/code/code.bin` **before writing any output**, refuses with exit 2, and records `armv6k` in `EXPORT_REPORT.json`. |
| `tools/emu/testhook.py` | test-only HID mailbox hook, ported from the translation project; drives the game through RAM writes and doubles as the native edit proof. |
| `tools/emu/textlog.py` | test-only pane-text logger + host recorder, ported/reduced (no English grammar pass). Records game time, pane name and text. |
| `tools/emu/memfix.py` | `reserve_tail` (ported) for a text-log ring at the end of the linear heap; kept for 3D/2way runs. |
| `tools/emu/extras.py` | **bug fix**: an empty LayeredFS overlay is not installed (Azahar crashes on an overlay directory with no files: `unmapped WriteBlock @ 0x0C1A8000`). |
| `tests/emu/run_cases.py` + `drive.py` + `fixtures.py` | the final 7-case runner used for §3. It detects a ring that lands outside the writable heap and falls back to screenshots + live-UI-heap scans. |
| `tests/emu/runner.py` (+`__main__.py`, `test_check_armv6k.py`) | the first pass's runner (`python -m tests.emu`), isolated emulator copy under `build/emu_test/root`, RPC-port guard. Kept as the quick boot/table/text/native pass. |
| `tests/emu/test_armv6k.py` | 8 fast unit tests for the gate + exporter refusal + IPS round-trip. |
| `docs/EXPORT.md` | §7.1 (first pass + findings), §8 "Verified in emulator" (final evidence + screenshots), §9 honest limits, §10 console checklist. |
| `docs/images/emu/*.png` | the 14 screenshots quoted in §8. `docs/images/x3/` keeps the first pass's shots. |

Both runners are opt-in: `tests/run_all.py` only discovers `tests/tier*`.

## 3. Evidence — 7/7 cases (final run)

`python tests/emu/run_cases.py` → `out/emu/x3/summary.json`, **`ok: true`**, 7/7 cases pass.
Each case's export report, result JSON, event log and screenshots are under
`out/emu/x3/<case>/`; the images are published to `docs/images/emu/`.

| Case | Edit (project tool) | Observation | Evidence |
|---|---|---|---|
| `empty` | empty `mod/` → Luma folder **and** 4 GiB `.3ds` (`export_mod.py`) | both reach the title menu (`outcome: title`, live menu strings in the UI heap); the image is validated `retail_identical: true` | `empty_luma_title.png`, `empty_3ds_title.png` |
| `empty_save` | same empty mod + `user_citra` save, **input movie** (no test hook) | title → Continue → save: the story-recap question is on screen | `empty_movie_save_prompt.png` |
| `text` | `ui/title/title_msg` entry 22 → `X3 TEXT EDIT OK 2468` (`text_tool.py`) | the message window shows the marker; the same UTF-16 string is found in the live UI heap at `0x33E0…` | `text_recap_prompt.png` |
| `table` | herb `buy_price` 8 → **1234567** (`table_edit.py`), shop record 68 copied over all records, first goods slot = herb row (`export_mod.stage_member`) | the shop goods list prints **やくそう 1234567G**; `1234567` is read back as a live pane string at `0x331C…` | `table_shop_list.png` |
| `script_src` | readable source: `b011.TrgRCommand` starts `IE_Z_M01_TAIJU` on talk (`script_build.py --tier source`) | talking to the priest shows the book message instead of the church menu | `script_source_book.png` |
| `script_asm` | annotated assembly: `TrgRCommand` starts `common.ShopEvent` (2 literals + 8 instructions, `--tier asm`) | talking opens the shop; the buy/sell/quit strings are live in the UI heap | `script_asm_shop.png` |
| `native` | test input hook exported as **`code.ips`** (897 B); IPS re-applied to retail | byte-for-byte equal to the test executable; booted via LayeredFS, `hook_alive: true` and a live RPC press opens the church menu (`おいのり` live at `0x33DB…`) | `native_code_ips_talk.png` |

### Findings worth keeping

- **`shop.bxon` stores item *row indices*, not the item table's `id` field.** Putting `2332`
  (the herb's `id`) in a shop slot sold a different item; row `0` is the herb. This is now
  documented in `tests/emu/fixtures.py:stage_shop_pack`.
- **Scripted message text is glyph-encoded, not UTF-16.** The pane-text log and a UTF-16 RAM
  scan can read UI text (menu labels, the recap prompt) exactly, but a book/NPC message is
  logged as mojibake and cannot be found by a UTF-16 scan. The script-source case therefore
  asserts on the screenshot (the window changes the screen) and is verified visually.
- **The text-log ring is not always usable.** It sits at `UI heap base + size`; on this
  profile that address is sometimes outside the writable linear heap (host writes do not
  stick, the game's logger writes nothing). The runner probes it with a pattern and falls back
  to screenshots + live-UI-heap scans, so a dead logger cannot fake a result.
- **An empty LayeredFS overlay crashes Azahar**, not the game; `install_mod` now skips it.
- **Source-tier scripts need a boot test.** The first pass found that adding a function or
  starting an event from `OnBeginScene` can produce a pack that crashes at/near boot; only
  edits that recompile `TrgRCommand` (like the one used here) were stable. Assembly tier is
  byte-exact.

## 4. ARMv6K / VFPv2 gate

- Test build (hook + logger): **215 changed words, 0 forbidden instructions**.
- A deliberate `vmov.f32 s0, #1.0` at `0x724D00`: `tools/check_armv6k.py` exits **1** and names
  the instruction; `tools/export_mod.py` exits **2**, prints the address/rule, and writes **no
  `out/.../luma`**.
- Covered patterns: VFP immediates, `movw/movt`, `ubfx/sbfx`, `bfi/bfc`, `sdiv/udiv`, `mls`,
  `rbit`, `ldrd/strd` with T, fixed-point `vcvt`; literal-pool words are reported as data and
  skipped.

## 5. Test results (this session)

```text
python tests/run_all.py
Tier 1: 70/70  Tier 2: 70/70  Tier 3: 14/14  Tier 4: 69/69
TOTALS: 223/223 SUCCESS (exit 0)

python tools/verify_project.py
OVERALL: PASS -> audit/PROJECT_VERIFICATION.json

python -m unittest tests.emu.test_armv6k
Ran 8 tests ... OK

python -m unittest tests.emu.test_check_armv6k
Ran 5 tests ... OK

python tests/emu/run_cases.py            (and --summary-only)
empty PASS  empty_save PASS  text PASS  script_src PASS
script_asm PASS  table PASS  native PASS   (7/7, exit 0)
```

`out/emu/x3/summary.json` records the environment (retail ROM/code hashes, test-code hash,
emulator path, harness path).

## 6. Decisions taken (orchestrator not available)

1. **Test-only code is never exported.** The HID hook and pane logger are applied to a copy of
   the retail executable per run; the release `mod/` workspace is untouched. The same
   `export_mod.py` path (and its ARMv6K gate) is used, so the test proves the real pipeline.
2. **Prove the IPS chain, not "the IPS booted".** Azahar cannot load `code.ips`; the runner
   applies the IPS to retail exactly as Luma does, checks byte equality with the test
   executable, and boots that via LayeredFS.
3. **Judge on what the game shows.** The strongest assertions are the screenshot plus a live
   UI-heap string (`find_utf16` restricted to `0x33000000-0x34000000`, so the resource cache
   at `0x31/0x32` cannot produce a false positive).
4. **Two runners are kept.** `python -m tests.emu` (first pass, isolated emulator copy, RPC-port
   guard) is quick; `python tests/emu/run_cases.py` produced the final 7-case evidence. Both
   share the same test-only modules and are documented in `tests/emu/README.md`.
5. **Empty-overlay fix in `extras.py`.** Skipping it is correct (nothing to overlay) and avoids
   an Azahar crash; the export still reports zero changes and the `.3ds` is retail-identical.
6. **Fixed-piece test data is generated, not shipped.** Shop/text edits are regenerated from
   the retail tables each run (`tests/emu/fixtures.py`), so the test cannot rot into a stale
   binary.

## 7. Open problems / NOT verified

1. **No real 3DS/2DS.** The console may reject an export that Azahar accepts (signature checks,
   Luma version, memory). §10 of `docs/EXPORT.md` is the checklist to run.
2. **Luma's own IPS application was not observed.** The IPS is proven to reproduce the
   executable; Luma applying it at boot is a console-only step.
3. **Source-tier scripts are not generally safe.** Recompiling only `TrgRCommand` is stable;
   added functions / load-time `StartEvent` crashed in the first pass. Do not ship a
   source-tier script without a boot test.
4. **The text proof is a UI prompt, not an NPC dialogue line.** The recap prompt is UI text
   (UTF-16); scripted NPC lines are glyph-encoded, so the message-window proof for dialogue is
   the script-source screenshot. A glyph decoder for the text log is still missing.
5. **The text-log ring is profile-dependent** (see §3). 3D/2way runs should use
   `memfix.reserve_tail` and get their own stability pass.
6. **Concurrent emulator lanes still collide.** The RPC port is fixed; the first pass's runner
   refuses when it sees the port in use, the final runner does not reserve it. Serialize or add
   a configurable port.
7. **Azahar on this host crashes occasionally** (~one run in several, in the NVIDIA driver,
   also with the retail ROM). The final runner retries; every observed failure was an emulator
   exit, never a guest fault in the edited data.
8. **The empty-mod save-load case ends at the recap prompt** (the emulator crashed before the
   B presses). It proves the save was loaded on the empty mod; the field itself is shown in the
   other cases.

## 8. Suggested follow-up tasks

1. **Console pass** with `out/luma` for the four edits and the §10 checklist, especially Luma's
   `code.ips` and the Old-2DS UI heap.
2. **Serialise emulator lanes**: a lock file or configurable RPC port.
3. **Glyph decoder for scripted message text** so the text log can assert NPC lines directly.
4. **Shop/table follow-up**: a generic shop editor (the row-index discovery is now known) and a
   shop screen in the table UI test path.
5. **Source-tier safety**: add a boot gate to `script_build.py pack` or fix the compiler for
   added functions; assembly tier is the safe fallback.
6. **3D/2way pass** with `memfix.reserve_tail` and a stability check.
7. **Visible asset test** (texture/model replacement) with a screenshot assertion; the text
   path is covered, assets are not.
