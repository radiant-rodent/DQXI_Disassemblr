"""Texture browser panel."""

from __future__ import annotations

from tkinter import ttk

from ... import theme, utils
from ..widgets import (ImagePane, KVTable, Panel, ThumbGrid, button, dim,
                       search_entry)


class TexturesPanel(Panel):
    key = "textures"
    title = "Textures"
    icon = "\u25a3"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._items: list = []
        self._debounce = utils.debounced(self, 220, lambda: self._refresh(reset_scroll=True))

        split = ttk.PanedWindow(self, orient="horizontal")
        split.grid(row=0, column=0, sticky="nsew")

        # -- left: filters + grid -----------------------------------------
        left = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(left, weight=3)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=0, column=0, sticky="ew")
        self.entry = search_entry(bar, width=26, placeholder="Search textures\u2026")
        self.entry.pack(side="left")
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())
        self.entry.bind("<Return>", lambda e: self._refresh(reset_scroll=True))

        self.pack_var = ttk.Combobox(bar, state="readonly", width=26, values=["All packs"])
        self.pack_var.current(0)
        self.pack_var.pack(side="left", padx=6)
        self.pack_var.bind("<<ComboboxSelected>>", lambda e: self._refresh(reset_scroll=True))

        self.thumb_var = ttk.Combobox(bar, state="readonly", width=7,
                                      values=["112 px", "148 px", "200 px", "256 px"])
        self.thumb_var.current(1)
        self.thumb_var.pack(side="left", padx=(0, 6))
        self.thumb_var.bind("<<ComboboxSelected>>", lambda e: self._set_thumb_size())

        self.count_label = dim(bar, "\u2026")
        self.count_label.pack(side="left", padx=6)

        hint = dim(left, "Click a tile to preview  \u00b7  thumbnails generate on demand")
        hint.grid(row=1, column=0, sticky="w", pady=(6, 4))

        self.grid = ThumbGrid(left, thumb_size=148, on_select=self._select,
                              label_lines=2)
        self.grid.grid(row=2, column=0, sticky="nsew")

        # -- right: preview + metadata -------------------------------------
        right = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(right, weight=2)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="No texture selected", style="H2.TLabel")
        self.name_label.pack(anchor="w")
        self.path_label = dim(head, "")
        self.path_label.pack(anchor="w")

        self.preview = ImagePane(right)
        self.preview.grid(row=1, column=0, sticky="nsew", pady=(6, 6))

        self.meta = KVTable(right, height=7, key_width=110)
        self.meta.grid(row=2, column=0, sticky="ew")

        actions = ttk.Frame(right, style="Panel.TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        button(actions, "Open externally", self._open_external).pack(side="left")
        button(actions, "Reveal file", self._reveal).pack(side="left", padx=6)
        button(actions, "Copy path", self._copy_path).pack(side="left")
        button(actions, "Reset zoom", self.preview.fit).pack(side="left", padx=6)

        self._ready = False

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._refresh()

    def set_filter(self, query: str | None = None, pack: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        if pack is not None:
            values = list(self.pack_var["values"])
            if pack in values:
                self.pack_var.set(pack)
        self._refresh(reset_scroll=True)

    def summary(self) -> str:
        return f"{len(self._items):,} textures"

    # ------------------------------------------------------------------
    def _set_thumb_size(self) -> None:
        size = int(self.thumb_var.get().split()[0])
        self.grid.set_items(self._items, thumb_size=size)

    def _refresh(self, reset_scroll: bool = False) -> None:
        index = self.app.textures.ensure()
        if not self._ready:
            packs = ["All packs"] + [f"{name}  ({count})" for name, count in index.packs()]
            self.pack_var.configure(values=packs)
            self._ready = True
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        pack_sel = self.pack_var.get()
        pack = None
        if pack_sel and not pack_sel.startswith("All packs"):
            pack = pack_sel.split("  (")[0]
        items = index.search(query, pack=pack)
        for item in items:
            item.label = item.name
            item.sublabel = f"{item.pack}  {item.dims}"
        self._items = items
        self.grid.set_items(items)
        self.count_label.configure(
            text=f"{len(items):,} shown \u00b7 {utils.human_size(index.total_bytes)} total")
        self.status(f"{len(items):,} textures")

    def _select(self, item) -> None:
        self.name_label.configure(text=item.name)
        self.path_label.configure(text=item.rel)
        self.preview.show(str(item.path))
        rows = [
            ("pack", item.pack),
            ("resolution", item.dims),
            ("format", item.fmt),
            ("file size", utils.human_size(item.size_bytes)),
            ("bflim size", utils.human_size(item.meta.get("bflim_size"))
             if item.meta.get("bflim_size") else "-"),
            ("alignment", str(item.meta.get("alignment", "-"))),
            ("flags", str(item.meta.get("flags", "-"))),
            ("path", str(item.path)),
        ]
        self.meta.set_rows(rows)
        self.status(f"{item.name}  \u00b7  {item.dims}  \u00b7  {utils.human_size(item.size_bytes)}")

    # ------------------------------------------------------------------
    def _current(self):
        if self.grid.selected is None:
            return None
        return self._items[self.grid.selected]

    def _open_external(self) -> None:
        item = self._current()
        if item:
            utils.open_external(item.path)

    def _reveal(self) -> None:
        item = self._current()
        if item:
            utils.reveal_in_explorer(item.path)

    def _copy_path(self) -> None:
        item = self._current()
        if item:
            utils.copy_to_clipboard(self, str(item.path))
            self.status("Path copied to clipboard")
