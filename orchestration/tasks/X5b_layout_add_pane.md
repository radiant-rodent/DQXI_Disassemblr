---
lane: export
---
Let modders add a NEW pane to a BFLYT layout (copy an existing pane under a new name).

Read first: `orchestration/done/X5_resizable_assets.md`, `tools/layout_tool.py` (`parse_bflyt`,
`apply_pane_edits`, `build_bflyt`), docs/EDITING.md layouts section.

Owns: `tools/layout_tool.py`, its tests, docs/EDITING.md (layouts section).

1. Add `python tools/layout_tool.py add-pane <in.bflyt> --copy <pane name> --name <new name>
   --out <out.bflyt>`: duplicate the pane section (and its `pas1`/`pae1` children if any) right
   after the source pane inside the same parent, give it the new 24-byte name, and update any
   pane-count / group (`grp1`) data that lists panes. Section offsets are relative, so
   `build_bflyt` recomputes file size and section count.
2. Unchanged layouts must still round-trip byte-identically (`layout_tool verify`).
3. Test: add a pane to one small layout, re-parse it, assert the new pane is listed and every
   other pane is unchanged. Add the test to `tests/` so `python tests/run_all.py` runs it.
4. Optional: prove it in the emulator with `tests/emu` (a moved copy of a visible text pane).
