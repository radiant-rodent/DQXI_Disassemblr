# Worker brief: "Draconian Quest" text is cut off in 2D mode (church menu)

## Symptom
In 2D mode, at a church while Draconian Quest is active, the label "Draconian Quest" is cut off.

## Already established (2026-11-19, do not redo)
The cut-off is **not** caused by the project's recompilation. The project's English version (`en`) matches the
published patch (`..\3DS_Translate\docs\patch\DQXI_EN.dq11patch`) in every file:

* Native code: reassembling `asm/` with the English version active (`python tools/build.py`) reproduces the
  patch's decompressed `.code` exactly (SHA-256 `43c432b5956c6d6afe022adede6a863b5d9a932d8c98f62db3be516f9928ef08`,
  0 differences; build.py reports it as a bit-match of the `en` version).
* Data: an export of the English version with an empty mod (`python tools/export_mod.py --mod mod --out out/cmp_en
  --target luma --code bin`) holds 842 RomFS files, every one with the SHA-256 the patch records for its output file.
  Nothing else (no mod files, no extra code) is added.

So any cut-off the game shows here is in the patch itself (its text, layout or font width handling), and the same thing
would show in a game patched with the published .dq11patch. This was shown by byte comparison; the cut-off itself was
not re-observed in the emulator.

## Where to look
* The label is `ui/common_2d/church_text` row 11 (id 2), text `Draconian Quest` (bank font `3D12`, bank box width 300).
  Neighbouring labels: "Enable 3D", "Save Code". The longer messages are in `ui/common_2d/church_msg`
  (e.g. "Draconian Quest lifted!").
* The 2D mode church menu probably draws this label in a text pane that is narrower than in 3D mode, or with a different
  font than `3D12` (the patch ships changed fonts `2D14.bffnt`, `2D14SH.bffnt`, `2D9.bffnt`, `3D12.bffnt`, `3D14.bffnt`).
  Compare the pane width in the 2D church menu layout with the rendered width of the string in the font that pane uses.
* The patch changes these text-layout functions (list: `python -m tools.game_version functions`):
  `Ui_LayoutTextBox_CalculateTextMetrics` (hook), `Ui_TextElement_SetString` (hook), `Ui_TextBuffer_AppendChars`,
  `Ui_TextBuffer_WriteCharsAt`, `Save_SlotUi_BuildEntry`, `Text_FormatEntryWithMarker`. If the label is clipped by a
  fixed pane width, shortening the string (e.g. "Draconian Quest" to a shorter wording) or widening the pane in the
  layout are the two usual fixes.
* The viewer can open both versions: `python -m tools.game_version use original` / `use en` switches every file at once
  (switching also regenerates `game_assets/maps/npc_talks.json`).

## How to reproduce in the emulator
`python -m tools.emu.edit2d_probe`-style probes boot the 2D save `user_citra_2d` (Cobblestone church). A save with
Draconian Quest active is needed to see the entry; the save editor is `..\dqxi-3ds-save-editor`.
