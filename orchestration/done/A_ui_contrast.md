# A_ui_contrast — readable filled buttons in DQXI Studio

**Status: fixed, built, unit-tested and looked at in the running editor. The final full test suite is
green (223/223); two earlier runs were noisy because other lanes were writing shared files at the
same time — details under "Test results".**

## The bug

`egui::Button::fill` overrides the background fill but not the label colour. The theme is
`Visuals::dark()`, whose button label is near-white, so any button filled with a light theme colour
got white ink on a light fill:

| Control | File:line | Fill | Ink | Contrast |
|---|---|---|---|---|
| Header `▶ Play` | `viewer_rs/src/app.rs:580` | `theme::ACCENT` `#e8b84b` | theme button ink (light) | **1.84:1** |
| Playtest `▶ Play` | `viewer_rs/src/ui/panels/playtest.rs:650` | `theme::ACCENT` `#e8b84b` | theme button ink (light) | **1.84:1** |

WCAG AA for body text is 4.5:1, so both were well below it. These are the "couple of yellow buttons"
from the report. `theme::accent_button` already used a dark label but was dead code and hard-coded
`#16181d` without a contrast check, so it could not be trusted for other fills.

### Audit of every other filled surface

I checked every `Button::fill`, `Frame::fill`, `painter.rect_filled`, `RichText::background_color`
and `selectable_label` in `viewer_rs/src` (grep for `.fill(`, `rect_filled`, `background_color`,
`selectable_label`, `Button::new`, `WARN`/`OK`/`ACCENT`/`INFO`):

| Place | Background | Ink | Ratio | Verdict |
|---|---|---|---|---|
| `app.rs` sidebar section buttons (selected) | `BG_SELECT` | `ACCENT` | 6.56:1 | OK, left alone |
| `app.rs` sidebar section buttons (idle) | `BG_PANEL` | `TEXT_DIM` | 6.78:1 | OK |
| `ui/panels/tables.rs:1073` dirty-cell highlight | `BG_SELECT` | `ACCENT` / `TEXT` | 6.56 / 9.87:1 | OK |
| `ui/panels/dialogues.rs:1501,1538` message-box + variable chips | `#0c0d12` / `#232a36` | `TEXT` / `TEXT_DIM` | 5.62:1 (chip) | OK |
| `ui/panels/layouts.rs:536` pane overlays | colour at 12 % alpha over dark base | light text | dark | OK |
| `ui/panels/overview.rs:46` cards | `BG_RAISED` / `BG_HOVER` | `ACCENT` / `TEXT_DIM` / `TEXT_FAINT` | 8.64 / 6.20:1 | OK |
| `ui/panels/playtest.rs` pre-flight `OK`/`WARN`/`ERROR` tags, `MODIFIED`/`ADDED`/`CODE` tags, summary lines | **no fill** — coloured text on the panel | — | — | not a filled control |
| `ui/panels/audio.rs` filters (`OST (155)` etc.) | `BG_SELECT` when selected | `ACCENT` | 6.56:1 | OK, no change needed |
| `ui/panels/audio.rs` transport (`▶ Play`, `■ Stop`, ±10 s) | default dark button | `TEXT` | ~14:1 | OK, no change needed |
| `ui/panels/mod.rs` | no widgets, registry only | — | — | nothing to fix |

So `audio.rs` contains **no light filled button**; its Play control is a normal dark button. `OK`,
`WARN`, `ERR`, `INFO`, `ACCENT` are only used as *text* colours there — that was already readable
and is now covered by the unit test anyway.

## The fix

`viewer_rs/src/theme.rs` gained one small section (lines 34-96) and five tests (lines 190-271):

```rust
pub const ON_LIGHT: Color32 = Color32::from_rgb(0x11, 0x11, 0x11); // dark ink
pub const ON_DARK:  Color32 = Color32::WHITE;
pub fn relative_luminance(color: Color32) -> f32;   // WCAG 2.x
pub fn contrast_ratio(a: Color32, b: Color32) -> f32;
pub fn text_on(fill: Color32) -> Color32;           // better of #111 / white
pub fn filled_button(text: impl Into<String>, fill: Color32) -> egui::Button<'static>;
```

* `filled_button` pins the label colour derived from the fill and then calls `.fill(fill)`, so the
  same button is readable in inactive, hovered and pressed states (egui applies the explicit fill in
  every state; the explicit text colour never changes).
* Hover/pressed feedback is unchanged in kind: egui still swaps the frame stroke per widget state
  (dark → light grey → lighter grey) and shows the pointing-hand cursor; the hover tooltip works.
* `accent_button` now delegates to `filled_button(label, ACCENT)` — same look, one implementation.
* Header Play (`app.rs:580`) and Playtest Play (`playtest.rs:648-651`) now call
  `theme::filled_button("▶ Play", theme::ACCENT)`. No other behaviour, spacing or enabled logic was
  touched.
* The theme has **only a dark mode** (`apply` uses `Visuals::dark()`), so there is no light variant
  to test. `text_on` depends only on the fill, so the rule would still hold if a light visuals set
  were added later.

### Result

* `#111` on `ACCENT`: **10.24:1** (was 1.84:1).
* `#111` on `WARN`: 8.76:1, `OK`: 9.17:1, `ERR`: 5.97:1, `INFO`: 8.43:1.
* White on the one genuinely dark fill `ACCENT_DIM` (`#8a6d2b`): 4.88:1.
* Disabled Play (egui fades the whole painter via `Ui::disable()` while an export runs) measures
  ≈ 3.43:1 in that state. Disabled controls are exempt from WCAG 1.4.3, and the surrounding
  "Export running…" label + spinner carry the meaning; I did not change the disable behaviour.

## Files changed

| File | Change |
|---|---|
| `viewer_rs/src/theme.rs` | new contrast helpers + `filled_button`, `accent_button` now delegates, 5 unit tests |
| `viewer_rs/src/app.rs` | header Play button uses `theme::filled_button` (2 lines, shared file, minimal) |
| `viewer_rs/src/ui/panels/playtest.rs` | Playtest Play button uses `theme::filled_button` (3 lines) |
| `game_assets/maps/b001_101a/level3d.patched.bxon` | **restored only** to the documented smoke edit from `editor_projects/b001_101a.json` after a concurrent test run clobbered it to a no-op (see test results); no content of mine |
| `orchestration/done/A_ui_contrast.md` | this report |
| `AGENT_LOG.md` | one entry (`A_ui_contrast`, Entry 188). A concurrent lane appended a second Entry 188 immediately afterwards; I renumbered that later heading to 189 (its content is untouched) so the log stays sequential. |

Nothing in `..\3DS_Translate` was read into or modified (this is desktop UI work). No
downloads, no installs, no emulator run.

## Test results

```
cd viewer_rs; cargo test
running 76 tests
test result: ok. 75 passed; 0 failed; 1 ignored
```

New tests in `theme::contrast_tests`:

* `every_fill_gets_aa_readable_text` — 20 theme colours used as fills, each asserted `>= 4.5:1`
  against `text_on(fill)` (this is the regression guard: white on `ACCENT` fails it at 1.84).
* `light_fills_use_dark_ink` / `dark_fills_use_white_ink` — pins the *choice*, not just the ratio.
* `luminance_and_ratio_match_known_values` — black/white = 21.0, identical = 1.0, and
  `contrast_ratio(WHITE, ACCENT) < 2.0` (the reported bug).
* `body_and_accent_text_read_against_the_panels` — normal text pairs `TEXT`/`TEXT_DIM`/`ACCENT` on
  `BG_PANEL`/`BG_SELECT` are still AA.

```
cd viewer_rs; cargo build --release
Finished `release` profile [optimized] target(s) in 28.48s   (exit 0)
```

```
python tools/verify_project.py
OVERALL: PASS -> audit/PROJECT_VERIFICATION.json
```

`python tests/run_all.py` — three runs were needed because other lanes were actively writing
files in this workspace at the same time. The final run is green:

```
Tier 1: Feature Coverage           | 70  | 70 | 0 | 0 | 2.96   | PASS
Tier 2: Boundary & Corner Cases    | 70  | 70 | 0 | 0 | 7.90   | PASS
Tier 3: Pairwise Combinations      | 14  | 14 | 0 | 0 | 3.17   | PASS
Tier 4: Real-World Scenarios       | 69  | 69 | 0 | 0 | 201.55 | PASS
TOTALS                             | 223 | 223| 0 | 0 | 215.57 | SUCCESS
ALL TEST TIERS COMPLETED SUCCESSFULLY (Exit Code 0)
```

Two earlier runs were noisy, both from concurrent lanes, neither from viewer code:

1. **Run 1** (223 tests, 2 failures) — `test_layout_bflyt_bflan_json_roundtrip` and
   `test_scenario_8_layouts_roundtrip` failed in `blyt/win_text_2d.bflyt`. `tools/layout_tool.py`
   has mtime 22:35:32, i.e. the concurrently running `E4_assets` lane was writing it while my suite
   ran (suite started 22:34:57). Both tests pass individually immediately afterwards; I did not
   touch them or weaken any check.
2. **Run 2** (223 tests, 1 error) — `test_scenario_9_mod_export.test_level_patch_can_be_staged_into_the_mod_workspace`
   errored because `game_assets/maps/b001_101a/level3d.patched.bxon` had been replaced with a
   byte-identical copy of the retail file, so the exporter correctly reported "unchanged: not
   copied". Cause: `tests/test_asset_roundtrip.py::test_map_noop_patch_roundtrip` writes that
   **shared, checked-in fixture** in place and restores a snapshot it read at start; two test suites
   overlapping (mine and another lane's) makes that read-restore racy, and the no-op version won.
   I restored the fixture from its canonical source, `editor_projects/b001_101a.json` (the
   documented "+2 on X" smoke edit, 6 float edits):
   `python tools/map_tool.py patch editor_projects/b001_101a.json` → hash `A214F426…6358`.
   The scenario-9 test then passes (`Ran 1 test in 93.292s / OK`) and Run 3 is green.
   I did **not** change the test or the export tool; the test-isolation bug is listed under
   follow-ups.


## Visual check (running editor)

I started `viewer_rs/target/release/viewer_rs.exe` (project's own binary), waited for the indexes,
and captured the window with a desktop screenshot (PowerShell + `CopyFromScreen`), then closed it.

* Playtest panel (`DQXI_START_SECTION=playtest`): both Play buttons — header and inside the
  Export & Play card — now show **dark ink on amber** and are clearly legible; the rest of the
  panel is unchanged. Screenshot: `%TEMP%\opencode\dqxi_playtest2.png`.
* Hover state: pointer over the Playtest Play button, tooltip shown, border lightened, **label still
  dark and legible**. Screenshot: `%TEMP%\opencode\dqxi_playtest_hover.png`.
* Audio panel (`DQXI_START_SECTION=audio`, a second fixed panel): filters, transport buttons and the
  header Play all legible; nothing to fix there (no light fills). Screenshot:
  `%TEMP%\opencode\dqxi_audio2.png`.

Screenshots are machine-local in `%TEMP%\opencode\` and not committed. A few desktop pixels bleed
through the rounded/shadow edge of the captured window rectangle (a `CopyFromScreen` artefact of the
restored window) — this is outside the client area and unrelated to the UI.

## Open problems / not verified

* **Disabled Play during a running job** is faded by `Ui::disable()` to ≈ 3.43:1. WCAG-exempt, and
  deliberately unchanged because changing it would change the enable/disable behaviour I do not own.
  A follow-up could render a dedicated disabled variant instead of the global alpha fade.
* **Only the dark theme exists.** The light/dark assertion matrix asked for by the task collapses to
  one mode; if a light `Visuals` is added, re-run `every_fill_gets_aa_readable_text` (it needs no
  change) and check the panel fills against the new base colour.
* **No HiDPI or alternate-font check.** Screenshots were taken at the default 1560×940 window on this
  1080p desktop; sub-pixel rendering of the 11-13 px labels was not measured.
* **`theme::accent_button` is still unused** (pre-existing dead-code warning). It now delegates to
  the tested helper, so it is safe if a future panel picks it up.
* I did **not** add hover "fill darkening": `Button::fill` is fixed per state by design, and the
  existing stroke/cursor feedback was kept to avoid changing the look beyond readability. If a
  stronger hover is wanted, `filled_button` is the single place to add it.
* A concurrent `E4_assets` worker is still active in this workspace, so other lanes' file writes can
  still make a single suite run noisy (see the two intermediate runs above).

## Suggested follow-ups

1. **Fix the shared-fixture race in `tests/test_asset_roundtrip.py`.** `test_map_noop_patch_roundtrip`
   writes `game_assets/maps/b001_101a/level3d.patched.bxon` in place and restores a snapshot; two
   concurrent test runs (normal on this multi-agent workspace) can leave it as the no-op copy and
   make `test_scenario_9_mod_export` fail. Point `patch_project` at a temp output dir (e.g. an
   `--out` option or a monkeypatched `map_tool.OUT_DIR`) instead of the shared path.
2. **UI style lint:** a tiny crate test (or a `docs/UI_STYLE.md` rule) that any new
   `Button::new(..).fill(theme::X)` goes through `theme::filled_button`. The contrast test covers the
   palette, not future call sites.
3. **Disabled variant:** `filled_button` could take an `enabled` flag and paint a solid dimmed fill
   plus readable ink instead of relying on the global opacity fade (needs a small behaviour review
   with the Playtest owner).
4. **Selected chips:** if filter chips ever move from `selectable_label` to a saturated
   accent/green fill, use `filled_button` — `text_on` already handles `OK`/`INFO`/`WARN`.
5. **Light theme (optional):** if DQXI Studio gains one, extend `apply` and add the same fills test
   against it (the helper is already mode-independent).
