"""Reusable Tk widgets: virtualised thumbnail grid, source viewer, JSON tree..."""

from __future__ import annotations

import json
import math
import queue
import re
import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable

from PIL import Image, ImageTk

from .. import theme, utils

THUMBS = utils.ThumbCache(size=176)

# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def label(parent, text: str, style: str = "TLabel", **kw) -> ttk.Label:
    return ttk.Label(parent, text=text, style=style, **kw)


def h2(parent, text: str) -> ttk.Label:
    return ttk.Label(parent, text=text, style="H2.TLabel")


def dim(parent, text: str) -> ttk.Label:
    return ttk.Label(parent, text=text, style="PanelDim.TLabel")


def toolbar(parent) -> ttk.Frame:
    bar = ttk.Frame(parent, style="Panel.TFrame")
    return bar


def button(parent, text: str, command=None, style: str = "Tool.TButton") -> ttk.Button:
    return ttk.Button(parent, text=text, command=command, style=style)


def search_entry(parent, width: int = 28, placeholder: str = "Search...") -> ttk.Entry:
    entry = ttk.Entry(parent, width=width)
    _install_placeholder(entry, placeholder)
    return entry


def _install_placeholder(entry: ttk.Entry, text: str) -> None:
    state = {"placeholder": text, "active": False}

    def show_placeholder():
        if not entry.get():
            state["active"] = True
            entry.insert(0, text)
            entry.configure(foreground=theme.TEXT_FAINT)

    def clear_placeholder(_event=None):
        if state["active"]:
            entry.delete(0, "end")
            entry.configure(foreground=theme.TEXT)
            state["active"] = False

    def on_focus_in(_event):
        clear_placeholder()

    def on_focus_out(_event):
        show_placeholder()

    def set_text(value: str):
        state["active"] = False
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)
            entry.configure(foreground=theme.TEXT)
        else:
            show_placeholder()

    entry.get_value = lambda: "" if state["active"] else entry.get()  # type: ignore[attr-defined]
    entry.set_value = set_text  # type: ignore[attr-defined]
    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    show_placeholder()


# ---------------------------------------------------------------------------
# Panel base class
# ---------------------------------------------------------------------------
class Panel(ttk.Frame):
    """Base class for a navigable section."""

    key = "panel"
    title = "Panel"
    icon = "?"

    def __init__(self, parent, app):
        super().__init__(parent, style="TFrame")
        self.app = app
        self._shown_once = False

    # API ------------------------------------------------------------------
    def on_show(self) -> None:
        if not self._shown_once:
            self._shown_once = True
            self.first_show()

    def first_show(self) -> None:  # pragma: no cover - overridden
        pass

    def set_filter(self, **kwargs) -> None:  # pragma: no cover - overridden
        pass

    def status(self, text: str) -> None:
        self.app.set_status(text)

    def summary(self) -> str:
        return ""


# ---------------------------------------------------------------------------
# Simple key/value metadata table
# ---------------------------------------------------------------------------
class KVTable(ttk.Frame):
    """Compact two-column table for metadata."""

    def __init__(self, parent, height: int = 10, key_width: int = 120):
        super().__init__(parent, style="Panel.TFrame")
        self.tree = ttk.Treeview(self, columns=("value",), show="tree", height=height,
                                 selectmode="browse")
        self.tree.column("#0", width=key_width, stretch=False)
        self.tree.column("value", width=10, stretch=True)
        vbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tree.tag_configure("odd", background=theme.BG_RAISED)

    def set_rows(self, rows: list[tuple[str, str]]) -> None:
        self.tree.delete(*self.tree.get_children())
        for i, (key, value) in enumerate(rows):
            self.tree.insert("", "end", text=str(key), values=(str(value),),
                             tags=("odd",) if i % 2 else ())


# ---------------------------------------------------------------------------
# Thumbnail grid
# ---------------------------------------------------------------------------
class ThumbGrid(ttk.Frame):
    """Canvas-based virtualised grid of image thumbnails."""

    def __init__(self, parent, thumb_size: int = 148, on_select: Callable | None = None,
                 on_activate: Callable | None = None, label_lines: int = 1):
        super().__init__(parent, style="Panel.TFrame")
        self.thumb_size = thumb_size
        self.label_lines = label_lines
        self.on_select = on_select
        self.on_activate = on_activate

        self.canvas = tk.Canvas(self, bg=theme.BG_PANEL, highlightthickness=0, bd=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.items: list = []
        self.selected: int | None = None
        self._cols = 1
        self._cell_w = thumb_size + 16
        self._cell_h = thumb_size + 16 + 14 * label_lines
        self._photos: dict[int, ImageTk.PhotoImage] = {}
        self._pending: set[str] = set()
        self._queue: queue.Queue = queue.Queue()
        self._label_attr = "label"
        self._sub_attr = "sublabel"
        self._path_attr = "path"
        self._placeholder_fill = theme.BG_RAISED
        self._index_of_path: dict[str, list[int]] = {}

        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Double-Button-1>", self._on_double)
        self.canvas.bind("<Return>", lambda e: self._activate())
        self.canvas.bind("<Up>", lambda e: self._move(-self._cols))
        self.canvas.bind("<Down>", lambda e: self._move(self._cols))
        self.canvas.bind("<Left>", lambda e: self._move(-1))
        self.canvas.bind("<Right>", lambda e: self._move(1))
        self.canvas.configure(takefocus=True)
        self._poll()

    # -- public API ---------------------------------------------------------
    def set_items(self, items: Iterable, thumb_size: int | None = None,
                  label_attr: str = "label", sub_attr: str = "sublabel",
                  path_attr: str = "path") -> None:
        if thumb_size and thumb_size != self.thumb_size:
            self.thumb_size = thumb_size
        self.items = list(items)
        self._label_attr, self._sub_attr, self._path_attr = label_attr, sub_attr, path_attr
        self.selected = None
        self._photos.clear()
        self._index_of_path: dict[str, list[int]] = {}
        for i, item in enumerate(self.items):
            p = str(getattr(item, path_attr, ""))
            if p:
                self._index_of_path.setdefault(p, []).append(i)
        self.canvas.yview_moveto(0.0)
        self._layout()
        self._redraw()

    def select_index(self, index: int, scroll: bool = True) -> None:
        if index < 0 or index >= len(self.items):
            return
        self.selected = index
        if scroll:
            row = index // max(1, self._cols)
            total = max(1, math.ceil(len(self.items) / max(1, self._cols)))
            self.canvas.yview_moveto(max(0.0, (row - 1) / max(1, total - 1)) if total > 1 else 0.0)
        self._redraw()
        self.canvas.focus_set()
        if self.on_select:
            self.on_select(self.items[index])

    # -- internals ----------------------------------------------------------
    def _on_configure(self, _event=None) -> None:
        self._layout()
        self._redraw()

    def _layout(self) -> None:
        width = max(1, self.canvas.winfo_width())
        self._cols = max(1, width // self._cell_w)
        rows = max(1, math.ceil(len(self.items) / self._cols))
        self.canvas.configure(scrollregion=(0, 0, width, rows * self._cell_h))

    def _on_wheel(self, event) -> None:
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        self._redraw()

    def _on_click(self, event) -> None:
        self.canvas.focus_set()
        index = self._index_at(event.x, event.y)
        if index is not None:
            self.selected = index
            self._redraw()
            if self.on_select:
                self.on_select(self.items[index])

    def _on_double(self, event) -> None:
        index = self._index_at(event.x, event.y)
        if index is not None and self.on_activate:
            self.on_activate(self.items[index])

    def _move(self, delta: int) -> None:
        if not self.items:
            return
        index = (self.selected or 0) + delta
        index = max(0, min(len(self.items) - 1, index))
        self.select_index(index)

    def _activate(self) -> None:
        if self.selected is not None and self.on_activate:
            self.on_activate(self.items[self.selected])

    def _index_at(self, x: int, y: int) -> int | None:
        if not self.items:
            return None
        cx = int(x // self._cell_w)
        cy = int((self.canvas.canvasy(y)) // self._cell_h)
        if cx < 0 or cx >= self._cols or cy < 0:
            return None
        index = cy * self._cols + cx
        if 0 <= index < len(self.items):
            return index
        return None

    def _visible_range(self) -> tuple[int, int]:
        top = self.canvas.canvasy(0)
        bottom = top + self.canvas.winfo_height()
        first = max(0, int(top // self._cell_h) - 1)
        last = int(bottom // self._cell_h) + 2
        return first, last

    def _redraw(self) -> None:
        c = self.canvas
        c.delete("all")
        if not self.items:
            c.create_text(20, 24, anchor="nw", text="No items",
                          fill=theme.TEXT_FAINT, font=theme.F_BASE)
            return
        first, last = self._visible_range()
        cols = self._cols
        cw = self._cell_w
        chh = self._cell_h
        pad = 8
        for row in range(first, last + 1):
            for col in range(cols):
                index = row * cols + col
                if index >= len(self.items):
                    break
                item = self.items[index]
                x0 = col * cw + pad * 0.5
                y0 = row * chh + pad * 0.5
                x1 = x0 + cw - pad
                y1 = y0 + self.thumb_size + 8
                selected = index == self.selected
                photo = self._photos.get(index)
                path = str(getattr(item, self._path_attr, ""))
                if photo is not None:
                    c.create_image(x0 + (cw - pad) / 2, y0 + 4, anchor="n", image=photo)
                else:
                    c.create_rectangle(x0, y0 + 4, x1, y1, fill=self._placeholder_fill,
                                       outline=theme.BORDER)
                    c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="...",
                                  fill=theme.TEXT_FAINT, font=theme.F_SMALL)
                    self._request_thumb(index, path)
                c.create_rectangle(x0 - 2, y0, x1 + 2, y1 + 2,
                                   outline=theme.ACCENT if selected else theme.BG_PANEL,
                                   width=2)
                label_text = str(getattr(item, self._label_attr, "") or "")
                sub_text = str(getattr(item, self._sub_attr, "") or "")
                c.create_text(x0 + 2, y1 + 6, anchor="nw", text=utils.elide(label_text, 26),
                              fill=theme.TEXT if selected else theme.TEXT_DIM,
                              font=theme.F_SMALL)
                if self.label_lines > 1 and sub_text:
                    c.create_text(x0 + 2, y1 + 6 + 13, anchor="nw",
                                  text=utils.elide(sub_text, 28),
                                  fill=theme.TEXT_FAINT, font=theme.F_TINY)

    def _request_thumb(self, index: int, path: str) -> None:
        if not path or path in self._pending:
            return
        self._pending.add(path)
        size = self.thumb_size

        def work():
            try:
                img = THUMBS.get(path, size)
            except Exception:
                img = None
            self._queue.put((path, img))

        utils.submit(work)

    def _poll(self) -> None:
        dirty = False
        try:
            while True:
                path, img = self._queue.get_nowait()
                self._pending.discard(path)
                if img is not None:
                    photo = ImageTk.PhotoImage(img)
                    for i in self._index_of_path.get(path, ()):  # pre-computed lookup
                        self._photos[i] = photo
                        dirty = True
        except queue.Empty:
            pass
        if dirty:
            self._redraw()
        self.after(120, self._poll)


# ---------------------------------------------------------------------------
# Image viewer with zoom / pan
# ---------------------------------------------------------------------------
class ImagePane(ttk.Frame):
    """Single-image viewer with fit/zoom and panning."""

    def __init__(self, parent):
        super().__init__(parent, style="Panel.TFrame")
        self.canvas = tk.Canvas(self, bg=theme.BG_INPUT, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.status = ttk.Label(self, text="", style="PanelDim.TLabel", anchor="w")
        self.status.pack(fill="x", padx=6, pady=(2, 4))
        self._path: str | None = None
        self._image: Image.Image | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._zoom = 1.0
        self._offset = (0.0, 0.0)
        self._drag = None
        self._fit = True
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<MouseWheel>", self._wheel)
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._motion)
        self.canvas.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))
        self.canvas.bind("<Double-Button-1>", lambda e: self.fit())

    def clear(self) -> None:
        self._path = None
        self._image = None
        self._photo = None
        self.canvas.delete("all")
        self.status.configure(text="")

    def show(self, path: str) -> None:
        self._path = path
        try:
            img = Image.open(path)
            img.load()
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            self._image = img
        except Exception as exc:
            self._image = None
            self.status.configure(text=f"Failed to load: {exc}")
            self.canvas.delete("all")
            return
        self.fit()

    def fit(self) -> None:
        self._fit = True
        self._zoom = 1.0
        self._offset = (0.0, 0.0)
        self.redraw()

    def redraw(self) -> None:
        c = self.canvas
        c.delete("all")
        if self._image is None:
            return
        cw = max(1, c.winfo_width())
        ch = max(1, c.winfo_height())
        iw, ih = self._image.size
        if self._fit:
            scale = min((cw - 16) / iw, (ch - 16) / ih)
            scale = min(scale, 8.0)
        else:
            scale = self._zoom
        dw, dh = max(1, int(iw * scale)), max(1, int(ih * scale))
        resample = Image.NEAREST if scale >= 2 else Image.LANCZOS
        if dw * dh <= 40_000_000:
            img = self._image.resize((dw, dh), resample)
            self._photo = ImageTk.PhotoImage(img)
            x = cw / 2 + self._offset[0]
            y = ch / 2 + self._offset[1]
            # checkerboard behind transparency
            c.create_image(x, y, image=self._photo)
        self.status.configure(
            text=f"{iw} x {ih} px   |   {scale*100:.0f}%   |   {utils.human_size(_filesize(self._path))}")

    def _wheel(self, event) -> None:
        if self._image is None:
            return
        factor = 1.15 if event.delta > 0 else 1 / 1.15
        self._fit = False
        self._zoom = max(0.02, min(16.0, self._zoom * factor))
        self.redraw()

    def _press(self, event) -> None:
        self._drag = (event.x, event.y, self._offset)

    def _motion(self, event) -> None:
        if self._drag is None:
            return
        x0, y0, off = self._drag
        self._offset = (off[0] + event.x - x0, off[1] + event.y - y0)
        self._fit = False
        self.redraw()


def _filesize(path: str | None) -> int:
    if not path:
        return 0
    try:
        import os

        return os.path.getsize(path)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# Text viewer with syntax tagging + search
# ---------------------------------------------------------------------------
class TextViewer(ttk.Frame):
    """Read-only text viewer with line numbers and language tagging."""

    def __init__(self, parent, show_lines: bool = True, max_highlight_chars: int = 400_000):
        super().__init__(parent, style="Panel.TFrame")
        self.max_highlight_chars = max_highlight_chars
        self.text = tk.Text(self, wrap="none", bg=theme.BG_PANEL, fg=theme.TEXT,
                            insertbackground=theme.ACCENT, selectbackground=theme.BG_SELECT,
                            font=theme.F_MONO, padx=8, pady=6, undo=False, bd=0,
                            highlightthickness=0, tabs=("1c"))
        self.lines = tk.Text(self, width=6, wrap="none", bg=theme.BG_PANEL, fg=theme.TEXT_FAINT,
                             font=theme.F_MONO_SMALL, padx=4, pady=6, bd=0,
                             highlightthickness=0, takefocus=False)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self._on_scroll)
        self.hbar = ttk.Scrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(yscrollcommand=self._on_text_scroll, xscrollcommand=self.hbar.set)
        self.lines.configure(yscrollcommand=lambda *a: None)

        self.text.grid(row=0, column=1, sticky="nsew")
        self.lines.grid(row=0, column=0, sticky="ns")
        self.vbar.grid(row=0, column=2, sticky="ns")
        self.hbar.grid(row=1, column=1, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.show_lines = show_lines
        if not show_lines:
            self.lines.grid_remove()

        self._configure_tags()
        self.text.configure(state="disabled")
        self._language = "text"
        self._raw = ""
        self._search_hits = 0

    # -- tags ---------------------------------------------------------------
    def _configure_tags(self) -> None:
        t = self.text
        for name, color in theme.SYN.items():
            if name in ("sel", "find"):
                continue
            t.tag_configure(name, foreground=color)
        t.tag_configure("find", background=theme.SYN["find"], foreground="#ffffff")
        t.tag_configure("sel_reg", background=theme.SYN["sel"])
        t.tag_configure("header", foreground=theme.ACCENT, font=(theme.MONO_FAMILY, 10, "bold"))
        t.tag_configure("lineno", foreground=theme.TEXT_FAINT)

    # -- scrolling ----------------------------------------------------------
    def _on_text_scroll(self, first, last) -> None:
        self.vbar.set(first, last)
        self.lines.yview_moveto(float(first))

    def _on_scroll(self, *args) -> None:
        self.text.yview(*args)
        self.lines.yview(*args)

    # -- content ------------------------------------------------------------
    def show(self, content: str, language: str = "text", header: str = "") -> None:
        t = self.text
        t.configure(state="normal")
        t.delete("1.0", "end")
        self._raw = content
        self._language = language
        self._has_header = bool(header)
        if header:
            t.insert("end", header + "\n", ("header",))
        t.insert("end", content)
        lines = content.count("\n") + 2
        if self.show_lines:
            self.lines.configure(state="normal")
            self.lines.delete("1.0", "end")
            if lines <= 60000:
                self.lines.insert("end", "\n".join(str(i) for i in range(1, lines + 1)))
            else:
                self.lines.insert("end", "(no line numbers\nfor huge files)")
            self.lines.configure(state="disabled")
        self._apply_syntax(language)
        t.mark_set("insert", "1.0")
        t.see("1.0")
        t.configure(state="disabled")

    def clear(self) -> None:
        self.show("", "text")

    # -- syntax -------------------------------------------------------------
    def _apply_syntax(self, language: str) -> None:
        if language in ("text", "nut-asm"):
            if language == "nut-asm":
                self._tag_nut()
            return
        if len(self._raw) > self.max_highlight_chars:
            return
        if language in ("c", "h"):
            self._tag_c()
        elif language == "py":
            self._tag_c(python=True)
        elif language == "asm":
            self._tag_asm()
        elif language == "json":
            self._tag_json()

    def _tag_c(self, python: bool = False) -> None:
        t = self.text
        keywords = (r"\b(?:if|else|for|while|return|goto|switch|case|default|break|continue|"
                    r"struct|union|enum|typedef|static|const|volatile|extern|inline|void|sizeof|"
                    r"do|using|namespace|class|template|new|delete|nullptr|true|false|"
                    r"def|elif|import|from|as|with|lambda|None|True|False|not|and|or|in|is|"
                    r"pass|yield|raise|try|except|finally|global|assert|del|print)\b")
        types = (r"\b(?:u8|u16|u32|u64|s8|s16|s32|s64|f32|f64|int|long|short|char|float|"
                 r"double|unsigned|signed|size_t|bool|Result|str|bytes|list|dict|tuple|set|"
                 r"object|int8_t|uint8_t|int16_t|uint16_t|int32_t|uint32_t|int64_t|uint64_t)\b")
        pattern = re.compile(
            r"(?P<comment>/\*.*?\*/|//[^\n]*|#[^\n]*)"
            r"|(?P<string>\"[^\"\n]*\"|'[^'\n]*')"
            r"|(?P<addr>\b0x[0-9A-Fa-f]+\b)"
            r"|(?P<number>\b\d+\.?\d*[fFuUlL]*\b)"
            r"|(?P<keyword>" + keywords + r")"
            r"|(?P<type>" + types + r")"
            r"|(?P<label>^\s*label_[0-9A-Fa-f]+:)"
            r"|(?P<func>\b[A-Za-z_][A-Za-z0-9_]*(?=\())",
            re.DOTALL | re.MULTILINE)
        self._tag_stream(pattern)

    def _tag_asm(self) -> None:
        pattern = re.compile(
            r"(?P<comment>@[^\n]*|//[^\n]*|/\*.*?\*/)"
            r"|(?P<addr>\b0x[0-9A-Fa-f]+\b)"
            r"|(?P<label>^\s*[A-Za-z_.$][\w.$]*:)"
            r"|(?P<instr>^\s*[a-z]{2,}\b)"
            r"|(?P<number>\b\d+\b)",
            re.DOTALL | re.MULTILINE)
        self._tag_stream(pattern)

    def _tag_nut(self) -> None:
        pattern = re.compile(
            r"(?P<comment>//[^\n]*)"
            r"|(?P<literal>'[^']*')"
            r"|(?P<instr>\[[ \d]+\]\s+[A-Z][A-Z0-9_]+)"
            r"|(?P<number>\b\d+\b)"
            r"|(?P<label>function '[^']*')",
        )
        self._tag_stream(pattern)

    def _tag_json(self) -> None:
        pattern = re.compile(
            r'(?P<key>"[^"\n]*")(?=\s*:)'
            r'|(?P<string>"[^"\n]*")'
            r"|(?P<number>-?\b\d+\.?\d*(?:[eE][+-]?\d+)?\b)"
            r"|(?P<keyword>\b(?:true|false|null)\b)")
        self._tag_stream(pattern)

    def _tag_stream(self, pattern: re.Pattern) -> None:
        t = self.text
        base = "2.0" if getattr(self, "_has_header", False) else "1.0"
        for match in pattern.finditer(self._raw):
            group = match.lastgroup
            if group is None or group not in ("comment", "string", "addr", "number", "keyword",
                                              "type", "label", "func", "literal", "instr", "key"):
                continue
            start = f"{base}+{match.start()}c"
            end = f"{base}+{match.end()}c"
            try:
                t.tag_add(group, start, end)
            except tk.TclError:
                continue

    # -- search -------------------------------------------------------------
    def find(self, needle: str, case: bool = False) -> int:
        t = self.text
        t.tag_remove("find", "1.0", "end")
        if not needle:
            return 0
        count = tk.IntVar()
        index = "1.0"
        while True:
            index = t.search(needle, index, stopindex="end", nocase=not case, count=count)
            if not index:
                break
            end = f"{index}+{count.get()}c"
            t.tag_add("find", index, end)
            index = end
        hits = len(t.tag_ranges("find")) // 2
        if hits:
            first = t.tag_ranges("find")[0]
            t.see(first)
        return hits

    def goto_line(self, line: int) -> None:
        self.text.see(f"{line}.0")


# ---------------------------------------------------------------------------
# JSON tree
# ---------------------------------------------------------------------------
class JsonTree(ttk.Frame):
    """Lazy JSON tree with type-aware summarisation."""

    def __init__(self, parent, on_select: Callable | None = None):
        super().__init__(parent, style="Panel.TFrame")
        cols = ("value",)
        self.tree = ttk.Treeview(self, columns=cols, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Key")
        self.tree.heading("value", text="Value")
        self.tree.column("#0", width=320, stretch=False)
        self.tree.column("value", width=520, stretch=True)
        vbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.tree.tag_configure("container", foreground=theme.INFO)
        self.tree.tag_configure("string", foreground=theme.SYN["string"])
        self.tree.tag_configure("number", foreground=theme.SYN["number"])
        self.tree.tag_configure("bool", foreground=theme.SYN["keyword"])
        self.tree.tag_configure("null", foreground=theme.TEXT_FAINT)
        self.on_select = on_select
        self._root_data = None
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _summary(value) -> tuple[str, str]:
        if isinstance(value, dict):
            return f"{{{len(value)} fields}}", "container"
        if isinstance(value, list):
            return f"[{len(value)} items]", "container"
        if isinstance(value, str):
            return utils.elide(value, 160), "string"
        if isinstance(value, bool):
            return str(value).lower(), "bool"
        if value is None:
            return "null", "null"
        return str(value), "number"

    def show(self, data) -> None:
        self._root_data = data
        self.tree.delete(*self.tree.get_children())
        self._insert("", "ROOT", data)

    def _insert(self, parent_id: str, key: str, value, tag: str | None = None) -> None:
        summary, kind = self._summary(value)
        node = self.tree.insert(parent_id, "end", text=str(key), values=(summary,),
                                tags=(tag or kind,))
        if isinstance(value, (dict, list)):
            self.tree.insert(node, "end", text="loading...")
        return node

    def _on_open(self, _event=None) -> None:
        node = self.tree.focus()
        if not node:
            return
        children = self.tree.get_children(node)
        if len(children) != 1 or self.tree.item(children[0], "text") != "loading...":
            return
        self.tree.delete(children[0])
        path_keys = self._path(node)
        value = self._resolve(path_keys)
        if isinstance(value, dict):
            for key, item in value.items():
                self._insert(node, str(key), item)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                self._insert(node, f"[{i}]", item)

    def _parent(self, node: str) -> str:
        return self.tree.parent(node)

    def _path(self, node: str) -> list:
        keys: list = []
        current = node
        while current and self.tree.parent(current):
            text = self.tree.item(current, "text")
            if text.startswith("[") and text.endswith("]"):
                keys.append(int(text[1:-1]))
            else:
                keys.append(text)
            current = self.tree.parent(current)
        keys.reverse()
        return keys

    def _resolve(self, keys: list):
        value = self._root_data
        for key in keys:
            try:
                if isinstance(value, list):
                    value = value[key]
                elif isinstance(value, dict):
                    value = value[key]
                else:
                    return None
            except Exception:
                return None
        return value

    def _on_select(self, _event=None) -> None:
        if not self.on_select:
            return
        node = self.tree.focus()
        if not node:
            return
        self.on_select(self.tree.item(node, "text"), self.tree.item(node, "values"))
