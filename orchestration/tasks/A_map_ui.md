---
lane: progress
---
Make the native-code coverage map readable. User feedback on the current `progress/progress.svg`:
"half the screen is white and the map is hard to read". Causes: fixed ~836 px width (opened
directly, the rest of the browser window is white), 4 px cells, and 18,518 of 18,787 functions in
one "General_Procedures" block, so the map is one big grey wall.

Owns: `tools/progress.py` (coverage map + its page only), `progress/`.

1. New page `progress/map.html` (linked in the nav of every page, and make the "Coverage map"
   link go there): dark background on the whole page, map fills the window width
   (responsive, no white area), works from 375 px to 4K.
2. Layout: split functions into labelled rows by address range (e.g. one row per 0x10000 bytes,
   label `0x0012xxxx`), cell size scales with width; subsystem blocks stay, but unknown-subsystem
   functions are grouped by address range instead of one giant block. Optionally size cells by
   function size (toggle).
3. Hover tooltip per cell: address, name, size, state, subsystem, summary (if any). Click opens
   the readable C file (`decomp/readable/...`) in a new tab if the board server serves it —
   `orchestration/live.py` serves `/progress/*` only; add a read-only `/decomp/readable/*` route
   there (text/plain), restricted to that folder.
4. Filters: state checkboxes (unnamed/proposed/named/documented/matching), search box by
   name/address that highlights matching cells, legend with counts.
5. Embed the data as JSON in map.html and draw with a <canvas> (18k+ cells; must stay fast).
   No external libraries or network.
6. Keep `progress.svg` (for badges/README) but make it width="100%" with a dark background rect
   and the same XML-safe entities (no `&middot;`/`&ndash;` in SVG — use `&#183;` / `&#8211;`).
Verify: run `python tools/progress.py`, check map.html parses, and that the SVGs parse with
`xml.dom.minidom`. Report what you checked.
