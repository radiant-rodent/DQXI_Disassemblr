#!/usr/bin/env python3
"""Export the game's BFFNT fonts as glyph-sheet PNGs plus a glyph map, for the editor.

    python tools/font_tool.py export            # every romfs/font/*.bffnt -> game_assets/fonts/
    python tools/font_tool.py export --font 2D9

Per font this writes ``<name>_sheet<N>.png`` (white glyphs, alpha = coverage) and
``<name>.font.json``::

    {"cell_w", "cell_h", "baseline", "cols", "rows", "sheet_w", "sheet_h", "sheets",
     "line_feed", "ascent", "height", "default": [left, glyph_w, char_w],
     "glyphs": {"<codepoint>": [glyph_index, left, glyph_w, char_w], ...}}

Glyph ``i`` sits on sheet ``i // (cols*rows)`` in cell (``i % cols``, ``i // cols % rows``);
cells are ``cell_w+1`` x ``cell_h+1`` pixels apart. Each cell already contains the glyph's left
bearing (ink spans columns ``0..left+glyph_w``), so a renderer draws the whole cell at the pen
position and advances by ``char_w``. The FFNT reader is the translation
project's ``dq11tool/bffnt.py`` (imported, not copied); sheets are decoded with
``tools/texture_tool.decode_tiled``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, "../3DS_Translate")

from dq11tool.bffnt import Bffnt  # noqa: E402
from tools.texture_tool import PICA_FORMATS, decode_tiled  # noqa: E402

FONTS_IN = ROOT / "game_data" / "romfs" / "font"
FONTS_OUT = ROOT / "game_assets" / "fonts"


def export(path: Path, out_dir: Path) -> dict:
    data = path.read_bytes()
    font = Bffnt.parse(data)
    s = font.sheet_info
    fmt = PICA_FORMATS[s["format"]]
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(s["sheets"]):
        start = s["data_off"] + i * s["sheet_size"]
        rgba = decode_tiled(data[start:start + s["sheet_size"]], s["sheet_w"], s["sheet_h"], fmt)
        rgba = np.asarray(rgba, dtype=np.uint8).copy()
        if fmt in ("A4", "A8"):
            rgba[..., :3] = 255  # alpha-only sheet: white glyphs, tinted by the text colour
        Image.fromarray(rgba, "RGBA").save(out_dir / f"{path.stem}_sheet{i}.png")
    glyphs = {}
    for cp, gi in sorted(font.cmap.items()):
        w = font.widths.get(gi, font.default_width)
        glyphs[str(cp)] = [gi, w.left, w.glyph_width, w.char_width]
    d = font.default_width
    meta = dict(
        name=path.stem, format=fmt, cell_w=s["cell_w"], cell_h=s["cell_h"], baseline=s["baseline"],
        cols=s["cols"], rows=s["rows"], sheet_w=s["sheet_w"], sheet_h=s["sheet_h"], sheets=s["sheets"],
        line_feed=font.line_feed, ascent=font.ascent, height=font.height, width=font.width,
        default=[d.left, d.glyph_width, d.char_width], glyphs=glyphs,
    )
    (out_dir / f"{path.stem}.font.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return meta


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="write glyph sheets + glyph map")
    ex.add_argument("--font", help="font stem, e.g. 2D9 (default: all)")
    ex.add_argument("--out", type=Path, default=FONTS_OUT)
    args = ap.parse_args()
    paths = sorted(FONTS_IN.glob("*.bffnt"))
    if args.font:
        paths = [p for p in paths if p.stem.lower() == args.font.lower()]
    if not paths:
        print(f"no fonts found in {FONTS_IN}")
        return 1
    for p in paths:
        m = export(p, args.out)
        print(f"{p.stem}: {len(m['glyphs'])} glyphs, {m['sheets']} sheet(s) {m['sheet_w']}x{m['sheet_h']} {m['format']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
