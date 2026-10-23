"""BFLYT layout preview rendering onto a Tk canvas."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass
from typing import Callable

from PIL import Image, ImageTk

from .. import theme

TYPE_COLORS = {
    "pan1": "#6db3f2",
    "pic1": "#c3e88d",
    "txt1": theme.ACCENT,
    "wnd1": "#c792ea",
    "prt1": "#8892a6",
}
FALLBACK_COLOR = "#8892a6"

TEXTURE_CACHE_LIMIT = 400


@dataclass
class PreviewOptions:
    show_textures: bool = True
    show_labels: bool = False
    flip_y: str = "auto"          # "auto" | True | False
    show_bounds: bool = True


def pane_box(pane: dict, y_up: bool) -> tuple[float, float, float, float]:
    t = pane.get("translate") or [0.0, 0.0, 0.0]
    s = pane.get("size") or [0.0, 0.0]
    x, y = float(t[0]), float(t[1])
    w, h = float(s[0]), float(s[1])
    if y_up:
        return (x, y - h, x + w, y)
    return (x, y, x + w, y + h)


def _fit_error(boxes: list[tuple[float, float, float, float]], w: float, h: float) -> float:
    if not boxes:
        return 0.0
    xs0 = min(b[0] for b in boxes)
    ys0 = min(b[1] for b in boxes)
    xs1 = max(b[2] for b in boxes)
    ys1 = max(b[3] for b in boxes)
    bw, bh = xs1 - xs0, ys1 - ys0
    if bw <= 0 or bh <= 0:
        return 0.0
    aspect_err = abs((bw / bh) - (w / h)) / (w / h)
    overflow = max(0.0, bw - w) / w + max(0.0, bh - h) / h
    return aspect_err + overflow


def choose_y_up(panes: list[dict], layout_w: float, layout_h: float) -> bool:
    """Pick the translation convention that fits the layout rectangle best."""
    up = _fit_error([pane_box(p, True) for p in panes], layout_w, layout_h)
    down = _fit_error([pane_box(p, False) for p in panes], layout_w, layout_h)
    return up <= down


def resolve_pane_texture(pane: dict, layout: dict, resolver: Callable[[str], object | None]):
    """Find the extracted texture used by a picture pane (name prefix match)."""
    if resolver is None:
        return None
    name = (pane.get("name") or "").lower()
    if not name:
        return None
    textures = layout.get("textures") or []
    candidates = [t for t in textures if t.lower().startswith(name)]
    if not candidates:
        candidates = [t for t in textures if name in t.lower()]
    for cand in candidates:
        hit = resolver(cand)
        if hit is not None:
            return hit
    return None


class LayoutPreview:
    """Draws BFLYT layout panes into a canvas and supports hit-testing."""

    def __init__(self, canvas: tk.Canvas):
        self.canvas = canvas
        self._img_cache: dict[tuple, ImageTk.PhotoImage] = {}
        self.layout: dict | None = None
        self.boxes: list[tuple[dict, tuple[float, float, float, float]]] = []
        self.scale = 1.0
        self.selected: str | None = None

    # ------------------------------------------------------------------
    def clear(self) -> None:
        self.canvas.delete("all")
        self.layout = None
        self.boxes = []

    def _cached_image(self, path: str, size: tuple[int, int]) -> ImageTk.PhotoImage | None:
        key = (path, size)
        img = self._img_cache.get(key)
        if img is not None:
            return img
        try:
            src = Image.open(path)
            src.load()
        except Exception:
            return None
        if src.width < 1 or src.height < 1:
            return None
        resample = Image.NEAREST if size[0] > src.width else Image.LANCZOS
        img = src.convert("RGBA").resize((max(1, size[0]), max(1, size[1])), resample)
        photo = ImageTk.PhotoImage(img)
        if len(self._img_cache) > TEXTURE_CACHE_LIMIT:
            self._img_cache.clear()
        self._img_cache[key] = photo
        return photo

    # ------------------------------------------------------------------
    def render(self, layout: dict, opts: PreviewOptions = PreviewOptions(),
               resolver: Callable[[str], object | None] | None = None) -> list[tuple[dict, tuple]]:
        c = self.canvas
        c.delete("all")
        self.layout = layout
        self.boxes = []
        cw, ch = c.winfo_width(), c.winfo_height()
        if cw < 10 or ch < 10:
            return []

        lay = layout.get("layout") or {}
        lw = float(lay.get("width") or 320.0)
        lh = float(lay.get("height") or 240.0)
        panes = [p for p in (layout.get("panes") or []) if p.get("name") or p.get("type")]

        if opts.flip_y == "auto":
            y_up = choose_y_up(panes, lw, lh) if panes else True
        else:
            y_up = bool(opts.flip_y)

        raw = [(p, pane_box(p, y_up)) for p in panes]
        if raw:
            bx0 = min(b[1][0] for b in raw)
            by0 = min(b[1][1] for b in raw)
            bx1 = max(b[1][2] for b in raw)
            by1 = max(b[1][3] for b in raw)
        else:
            bx0, by0, bx1, by1 = 0.0, 0.0, lw, lh
        bw = max(1.0, bx1 - bx0)
        bh = max(1.0, by1 - by0)
        pad = 16
        scale = min((cw - pad * 2) / bw, (ch - pad * 2) / bh)
        if not math.isfinite(scale) or scale <= 0:
            scale = 1.0
        ox = (cw - bw * scale) * 0.5 - bx0 * scale
        oy = (ch - bh * scale) * 0.5 - by0 * scale
        self.scale = scale

        def sx(x: float) -> float:
            return ox + x * scale

        def sy(y: float) -> float:
            return oy + y * scale

        # layout frame
        c.create_rectangle(sx(bx0 - 1), sy(by0 - 1), sx(bx1 + 1), sy(by1 + 1),
                           outline=theme.BORDER_LIGHT, dash=(3, 3))
        if opts.show_bounds:
            c.create_rectangle(sx(0), sy(0), sx(lw), sy(lh), outline=theme.ACCENT_DIM)
            c.create_text(sx(0) + 4, sy(0) + 10, anchor="w",
                          text=f"layout {int(lw)}x{int(lh)}" + (" (y-up)" if y_up else " (y-down)"),
                          fill=theme.TEXT_FAINT, font=theme.F_TINY)

        for pane, box in raw:
            x0, y0 = sx(box[0]), sy(box[1])
            x1, y1 = sx(box[2]), sy(box[3])
            if x1 - x0 < 0.5:
                x1 = x0 + 0.5
            if y1 - y0 < 0.5:
                y1 = y0 + 0.5
            ptype = (pane.get("type") or "pan1").lower()
            color = TYPE_COLORS.get(ptype, FALLBACK_COLOR)
            self.boxes.append((pane, (x0, y0, x1, y1)))

            if ptype == "pic1" and opts.show_textures and resolver is not None:
                tex = resolve_pane_texture(pane, layout, resolver)
                if tex is not None:
                    photo = self._cached_image(str(tex.path), (int(round(x1 - x0)), int(round(y1 - y0))))
                    if photo is not None:
                        c.create_image(x0, y0, anchor="nw", image=photo)
                        if opts.show_labels:
                            c.create_rectangle(x0, y0, x1, y1, outline=color, dash=(2, 2))
                        continue
                c.create_rectangle(x0, y0, x1, y1, fill=_blend(color, 0.18),
                                   outline=_blend(color, 0.8), dash=(4, 3))
            elif ptype == "txt1":
                c.create_rectangle(x0, y0, x1, y1, fill=_blend(color, 0.10),
                                   outline=_blend(color, 0.55))
                text = pane.get("text") or ""
                if text:
                    size = pane.get("font_size") or [11, 11]
                    px = max(7, min(22, int(float(size[0]) * scale)))
                    c.create_text(x0 + 2, y0 + 2, anchor="nw", text=text,
                                  fill=theme.JP_TEXT, font=theme.jp_font(px),
                                  width=max(20, int(x1 - x0)))
            elif ptype == "pan1":
                c.create_rectangle(x0, y0, x1, y1, fill=_blend(color, 0.05),
                                   outline=_blend(color, 0.35))
            elif ptype == "wnd1":
                c.create_rectangle(x0, y0, x1, y1, fill=_blend(color, 0.12),
                                   outline=_blend(color, 0.8), width=2)
            else:  # prt1 and friends
                c.create_rectangle(x0, y0, x1, y1, fill=_blend(color, 0.08),
                                   outline=_blend(color, 0.5), dash=(1, 2))

            if opts.show_labels or (x1 - x0) * (y1 - y0) > 4200:
                label = pane.get("name") or ptype
                c.create_text(x0 + 3, y0 + 3, anchor="nw", text=_fit_label(label, x1 - x0),
                              fill=theme.TEXT_DIM, font=theme.F_TINY)

        self._highlight()
        return self.boxes

    # ------------------------------------------------------------------
    def select(self, pane_name: str | None) -> None:
        self.selected = pane_name
        self._highlight()

    def _highlight(self) -> None:
        self.canvas.delete("hl")
        if not self.selected:
            return
        for pane, (x0, y0, x1, y1) in self.boxes:
            if pane.get("name") == self.selected:
                self.canvas.create_rectangle(x0 - 2, y0 - 2, x1 + 2, y1 + 2,
                                             outline=theme.ACCENT, width=2, tags="hl")
                break

    def hit_test(self, x: float, y: float) -> dict | None:
        best = None
        best_area = None
        for pane, (x0, y0, x1, y1) in self.boxes:
            if x0 <= x <= x1 and y0 <= y <= y1:
                area = (x1 - x0) * (y1 - y0)
                if best_area is None or area < best_area:
                    best, best_area = pane, area
        return best


def _blend(color: str, alpha: float) -> str:
    """Blend a hex colour towards the panel background."""
    try:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        br = int(theme.BG_PANEL[1:3], 16)
        bg = int(theme.BG_PANEL[3:5], 16)
        bb = int(theme.BG_PANEL[5:7], 16)
        return "#%02x%02x%02x" % (
            int(br + (r - br) * alpha),
            int(bg + (g - bg) * alpha),
            int(bb + (b - bb) * alpha),
        )
    except Exception:
        return color


def _fit_label(text: str, width: float) -> str:
    max_chars = max(4, int(width / 6.2))
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "\u2026"
