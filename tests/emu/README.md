# Emulator proof tests (opt-in)

These tests launch the portable Azahar and prove that edits made with the project's tools
actually run in the game. They are **not** discovered by `tests/run_all.py` (that runner only
scans `tests/tier*`); a full run needs exclusive use of Azahar's fixed RPC port.

```powershell
python -m tests.emu                 # boot, table, text, native (≈ 10 min)
python -m tests.emu --case script   # assembly + source script edits (≈ 6 min)
python -m tests.emu --case script_load   # source tier, new function at scene load (≈ 6 min)
python -m tests.emu --case all      # everything
python -m tests.emu --list

# a separate data root, so another worker's emulator does not collide on the RPC port:
$env:DQ11_EMUTEST = "C:\...\build\emu_test\root"
python -m tests.emu
```

The **full proof suite** (8 cases: empty Luma/.3ds, empty+save, table in a shop, text,
both script tiers, the scene-load source edit, native `code.ips`) is:

```powershell
python tests/emu/run_cases.py                 # all 7, ~10 minutes
python tests/emu/run_cases.py text table      # selected cases
python tests/emu/run_cases.py --list
```

It writes `out/emu/x3/<case>/` plus `out/emu/x3/summary.json` and publishes the screenshots
used in `docs/EXPORT.md` §8 to `docs/images/emu/`. The lighter `python -m tests.emu` runner is
kept for quick boot/table/text/native checks and writes `out/emu/tests/<case>/`.

Results (light runner) go to `out/emu/tests/<case>/`:

| file | what it is |
|---|---|
| `report.json` | assertions + observed values (addresses, text, exit codes) |
| `*.png` | screenshots of the relevant screen |
| `events.jsonl` | the text log (game time, pane name, text, screenshot) |
| `export/` | the Luma folder the emulator loaded (never a release; contains the test hook) |

## What each case proves

* **boot** — an empty `mod/` exports to an empty Luma folder (and optionally the 4 GiB `.3ds`)
  and still boots to the title. An empty overlay is deliberately not installed: Azahar's
  LayeredFS does not like an empty overlay directory, and there is nothing to overlay.
* **table** — `table_edit.py` changes the herb's `buy_price`; the exact 88-byte patched row is
  found in guest RAM after the save loads (`report.json` has the address and the value read
  back). This proves the pack reached the game, not just the exporter.
* **text** — `text_tool.py` replaces the load-game recap line with `X3 TEXT EDIT OK`; the
  message window screenshot and the text log both show it.
* **script** — baseline b011 talks to the priest; the **assembly** tier changes the `type ==
  10/16` comparisons so the talk does nothing (no greeting, no menu); the **source** tier
  recompiles `TrgRCommand` to call `StartUI` directly (the blank window is the expected result
  of a direct UI call outside the event context; it proves the recompiled function ran).
* **script_load** — the source tier adds a *new* function and starts it from `OnBeginScene`, the
  edit that used to crash while the save loaded (see
  `orchestration/done/E3b_script_compiler_fix.md`). The new function opens the shop menu **in its
  own event thread** (`WaitFrame(30); StartUI(2, -1); WaitMenu(); EndUI(2);`), so the case asserts
  a positive effect: the shop entry label (`かいにきた`) and the shopkeeper's line are live in the
  dynamic UI heap, the clock still advances and there is no crash. The `run_cases.py` variant
  starts the game's `common.ShopEvent` with a *nested* `StartEvent` instead and only asserts the
  field's place label — a nested event start replaces the thread slot, so its menu is not a
  reliable screen assertion.
* **native** — a real native change (the test-only HID input hook) is exported as `code.ips`
  and as `code.bin`; the IPS is re-applied and must reproduce the code.bin byte for byte, the
  emulator loads that code.bin, the hook word/cave are read back from guest RAM, and live
  input works.

## Test-only code

`build/emu_test/code_*.bin` is the retail executable plus:

* `tools/emu/testhook.py` — HID mailbox (ported from the translation project),
* `tools/emu/textlog.py` — pane-text ring logger (ported, adapted to a no-op grammar pass).

Neither is ever written to `mod/` or a release export. The tests build a throw-away workspace
under `build/emu_test/ws_*` and export it to `out/emu/tests/...`.

## Serialization

Azahar's RPC port is **45987**, compiled into the emulator; two instances cannot run at the
same time. The runner checks `netstat` before starting and refuses with a clear message. It
kills only the emulator at *this project's* path (never the user's own Azahar, never another
checkout's), and always stops it afterwards.

## Second runner: `run_cases.py` (final 8-case evidence)

`python tests/emu/run_cases.py` is the runner used for the results in `docs/EXPORT.md` §8. It
uses the project's `third_party/emutest` data root (not the isolated copy under
`build/emu_test/root`), writes to `out/emu/x3/<case>/`, and judges the cases on **what the
game draws** plus a live-UI-heap scan:

```powershell
python tests/emu/run_cases.py                # empty, empty_save, text, script_src, script_load, script_asm, table, native
python tests/emu/run_cases.py text table     # selected cases
python tests/emu/run_cases.py --summary-only # recompute checks from the saved result.json files
```

It is the only runner that shows the edited **shop price** in a shop (`table`), both script
tiers changing behaviour (`script_src` → book message, `script_asm` → shop menu), and the
**empty `.3ds` target** booting to the title. It retries a case when the emulator exits during
boot and publishes the documentation screenshots to `docs/images/emu/`.

The two runners share the same test-only code and the same rule: **never install an emulator
test build on a real console**. `python -m tests.emu` is the quicker boot/table/text/native
pass with an isolated emulator copy; `run_cases.py` is the full evidence run.
