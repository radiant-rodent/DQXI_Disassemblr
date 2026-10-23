"""UI layout browser with rendered previews of BFLYT panes."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from ... import theme, utils
from ...render import layout_preview
from ..widgets import Panel, TextViewer, button, dim, search_entry


class LayoutsPanel(Panel):
    key = "layouts"
    title = "Layouts"
    icon = "\u25a6"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._items: list = []
        self._current = None
        self._debounce = utils.debounced(self, 200, lambda: self._refresh())

        split = ttk.PanedWindow(self, orient="horizontal")
        split.grid(row=0, column=0, sticky="nsew")

        # -- left ----------------------------------------------------------
        left = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(left, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(4, weight=1)

        ttk.Label(left, text="Layout packs", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        self.pack_var = ttk.Combobox(left, state="readonly", values=["All packs"])
        self.pack_var.current(0)
        self.pack_var.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        self.pack_var.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=2, column=0, sticky="ew")
        self.entry = search_entry(bar, width=16, placeholder="Search layouts\u2026")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())
        self.kind_var = ttk.Combobox(bar, state="readonly", width=8,
                                     values=["all", "layout", "anim"])
        self.kind_var.current(0)
        self.kind_var.pack(side="left", padx=(6, 0))
        self.kind_var.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        self.tree = ttk.Treeview(left, columns=("kind", "size"), selectmode="browse")
        self.tree.heading("#0", text="File")
        self.tree.heading("kind", text="Kind")
        self.tree.heading("size", text="Size")
        self.tree.column("#0", width=230)
        self.tree.column("kind", width=60, stretch=False)
        self.tree.column("size", width=70, anchor="e", stretch=False)
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=4, column=0, sticky="nsew", pady=(6, 0))
        vbar.grid(row=4, column=1, sticky="ns", pady=(6, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.count_label = dim(left, "")
        self.count_label.grid(row=5, column=0, sticky="w", pady=(4, 0))

        # -- right ---------------------------------------------------------
        right = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(right, weight=3)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="Select a layout", style="H2.TLabel")
        self.name_label.pack(anchor="w")
        self.info_label = dim(head, "")
        self.info_label.pack(anchor="w")

        nb = ttk.Notebook(right)
        nb.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

        # Preview tab ------------------------------------------------------
        preview_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(preview_tab, text="Preview")
        preview_tab.columnconfigure(0, weight=1)
        preview_tab.rowconfigure(1, weight=1)

        opts = ttk.Frame(preview_tab, style="Panel.TFrame", padding=(0, 6))
        opts.grid(row=0, column=0, sticky="ew")
        self.tex_var = tk.BooleanVar(value=True)
        self.label_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Show textures", variable=self.tex_var,
                        command=self._rerender).pack(side="left")
        ttk.Checkbutton(opts, text="Pane labels", variable=self.label_var,
                        command=self._rerender).pack(side="left", padx=8)
        dim(opts, "  Orientation:").pack(side="left", padx=(12, 4))
        self.flip_var = ttk.Combobox(opts, state="readonly", width=10,
                                     values=["auto", "y-up", "y-down"])
        self.flip_var.current(0)
        self.flip_var.pack(side="left")
        self.flip_var.bind("<<ComboboxSelected>>", lambda e: self._rerender())

        self.canvas = tk.Canvas(preview_tab, bg=theme.BG_INPUT, highlightthickness=1,
                                highlightbackground=theme.BORDER)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.preview = layout_preview.LayoutPreview(self.canvas)
        self.canvas.bind("<Button-1>", self._canvas_click)

        # Panes tab --------------------------------------------------------
        panes_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(panes_tab, text="Panes")
        panes_tab.columnconfigure(0, weight=1)
        panes_tab.rowconfigure(0, weight=1)
        self.pane_tree = ttk.Treeview(panes_tab, columns=("type", "pos", "size", "extra"),
                                      selectmode="browse")
        self.pane_tree.heading("#0", text="Pane")
        self.pane_tree.heading("type", text="Type")
        self.pane_tree.heading("pos", text="Translate")
        self.pane_tree.heading("size", text="Size")
        self.pane_tree.heading("extra", text="Text / detail")
        self.pane_tree.column("#0", width=220)
        self.pane_tree.column("type", width=60, stretch=False)
        self.pane_tree.column("pos", width=130, stretch=False)
        self.pane_tree.column("size", width=110, stretch=False)
        self.pane_tree.column("extra", width=320)
        vt = ttk.Scrollbar(panes_tab, orient="vertical", command=self.pane_tree.yview)
        self.pane_tree.configure(yscrollcommand=vt.set)
        self.pane_tree.grid(row=0, column=0, sticky="nsew")
        vt.grid(row=0, column=1, sticky="ns")
        self.pane_tree.bind("<<TreeviewSelect>>", self._pane_selected)

        # Raw tab ----------------------------------------------------------
        raw_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(raw_tab, text="Raw JSON")
        raw_tab.columnconfigure(0, weight=1)
        raw_tab.rowconfigure(1, weight=1)
        raw_bar = ttk.Frame(raw_tab, style="Panel.TFrame", padding=(0, 6))
        raw_bar.grid(row=0, column=0, sticky="ew")
        button(raw_bar, "Reveal file", self._reveal).pack(side="left")
        button(raw_bar, "Copy JSON", self._copy_json).pack(side="left", padx=6)
        button(raw_bar, "Copy path", self._copy_path).pack(side="left")
        self.raw = TextViewer(raw_tab, show_lines=False)
        self.raw.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._refresh()

    def set_filter(self, query: str | None = None, pack: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        if pack:
            values = list(self.pack_var["values"])
            if pack in values:
                self.pack_var.set(pack)
        self._refresh()

    def summary(self) -> str:
        return f"{len(self._items):,} files"

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        index = self.app.layouts.ensure()
        packs = ["All packs"] + [f"{name}  ({count})" for name, count in index.packs()]
        self.pack_var.configure(values=packs)
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        pack_sel = self.pack_var.get()
        pack = None if not pack_sel or pack_sel.startswith("All packs") else pack_sel.split("  (")[0]
        kind = self.kind_var.get()
        kind = None if kind == "all" else kind
        self._items = index.search(query, pack, kind)
        self.tree.delete(*self.tree.get_children())
        for item in self._items:
            self.tree.insert("", "end", iid=str(item.path),
                             text=item.stem.replace(".layout.json", "").replace(".anim.json", ""),
                             values=(item.kind, utils.human_size(item.size_bytes)))
        self.count_label.configure(text=f"{len(self._items):,} files")
        self.status(f"{len(self._items):,} layout files")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = next((l for l in self._items if str(l.path) == sel[0]), None)
        if item is None:
            return
        self._current = item
        try:
            data = self.app.layouts.load(item.path)
        except Exception as exc:
            self.name_label.configure(text=item.stem)
            self.info_label.configure(text=f"failed to parse: {exc}")
            return
        self.name_label.configure(text=item.stem.replace(".json", ""))
        if item.kind == "layout":
            lay = data.get("layout") or {}
            count = data.get("panes_count") or len(data.get("panes") or [])
            self.info_label.configure(
                text=f"{item.pack}  \u00b7  {int(lay.get('width', 0))}x{int(lay.get('height', 0))} px"
                     f"  \u00b7  {count} panes  \u00b7  {len(data.get('textures') or [])} texture refs"
                     f"  \u00b7  {utils.human_size(item.size_bytes)}")
            self._fill_panes(data)
        else:
            anim = data.get("anim") or {}
            self.info_label.configure(
                text=f"{item.pack}  \u00b7  BFLAN animation  \u00b7  {anim.get('frames', '?')} frames"
                     f"  \u00b7  {len(data.get('tags') or [])} tags  \u00b7  {utils.human_size(item.size_bytes)}")
            self._fill_panes(data)
        self.raw.show(json.dumps(data, indent=2, ensure_ascii=False), "json",
                      header=f"# {item.path}")
        self._rerender()

    # ------------------------------------------------------------------
    def _fill_panes(self, data: dict) -> None:
        self.pane_tree.delete(*self.pane_tree.get_children())
        panes = data.get("panes") or []
        if not panes:
            # animation files: list target names harvested from section payloads
            names = _ascii_strings_from_sections(data.get("raw_sections") or [])
            for name in names:
                self.pane_tree.insert("", "end", text=name, values=("anim target", "", "", ""))
            if not names:
                self.pane_tree.insert("", "end", text="(no pane data in animation file)",
                                      values=("", "", "", ""))
            return
        for pane in panes:
            pos = pane.get("translate") or [0, 0, 0]
            size = pane.get("size") or [0, 0]
            extra = pane.get("text") or pane.get("font_name") or ""
            self.pane_tree.insert(
                "", "end", iid=str(id(pane)), text=pane.get("name") or "(unnamed)",
                values=(pane.get("type", ""),
                        f"{pos[0]:.0f}, {pos[1]:.0f}",
                        f"{size[0]:.0f} x {size[1]:.0f}",
                        utils.elide(str(extra), 60)))

    def _pane_selected(self, _event=None) -> None:
        sel = self.pane_tree.selection()
        if not sel or not self._current:
            return
        pane_id = sel[0]
        pane = None
        for p in self._current_panes:
            if str(id(p)) == pane_id:
                pane = p
                break
        if pane is None:
            return
        self.preview.select(pane.get("name"))
        self.status(f"pane {pane.get('name')} \u00b7 type {pane.get('type')}")

    @property
    def _current_panes(self) -> list:
        if self._current is None:
            return []
        try:
            data = self.app.layouts.load(self._current.path)
            return data.get("panes") or []
        except Exception:
            return []

    def _canvas_click(self, event) -> None:
        pane = self.preview.hit_test(event.x, event.y)
        if pane is None:
            return
        for child in self.pane_tree.get_children():
            if self.pane_tree.item(child, "text") == pane.get("name"):
                self.pane_tree.selection_set(child)
                self.pane_tree.see(child)
                break
        self.status(f"pane {pane.get('name')} \u00b7 type {pane.get('type')}")

    # ------------------------------------------------------------------
    def _rerender(self) -> None:
        if self._current is None:
            return
        try:
            data = self.app.layouts.load(self._current.path)
        except Exception:
            return
        if not (data.get("panes")):
            self._render_anim_summary(data)
            return
        opts = layout_preview.PreviewOptions(
            show_textures=bool(self.tex_var.get()),
            show_labels=bool(self.label_var.get()),
            flip_y=("auto" if self.flip_var.get() == "auto"
                    else self.flip_var.get() == "y-up"),
        )
        self.preview.render(data, opts, resolver=self.app.textures.resolve)
        if self.preview.selected:
            self.preview.select(self.preview.selected)

    def _render_anim_summary(self, data: dict) -> None:
        c = self.canvas
        c.delete("all")
        anim = data.get("anim") or {}
        names = _ascii_strings_from_sections(data.get("raw_sections") or [])
        c.create_text(20, 18, anchor="nw", text="BFLAN animation",
                      fill=theme.ACCENT, font=theme.F_H2)
        info = [f"frames: {anim.get('frames', '?')}", f"flags: {anim.get('flags', '?')}",
                f"sections: {len(data.get('raw_sections') or [])}"]
        for i, line in enumerate(info):
            c.create_text(20, 48 + i * 18, anchor="nw", text=line,
                          fill=theme.TEXT_DIM, font=theme.F_BASE)
        if names:
            c.create_text(20, 120, anchor="nw",
                          text="animation targets (from binary payloads):",
                          fill=theme.TEXT_DIM, font=theme.F_SMALL)
            for i, name in enumerate(names[:24]):
                c.create_text(28, 140 + i * 15, anchor="nw", text=f"\u2022 {name}",
                              fill=theme.TEXT, font=theme.F_SMALL)

    # ------------------------------------------------------------------
    def _reveal(self) -> None:
        if self._current:
            utils.reveal_in_explorer(self._current.path)

    def _copy_path(self) -> None:
        if self._current:
            utils.copy_to_clipboard(self, str(self._current.path))
            self.status("Path copied")

    def _copy_json(self) -> None:
        if self._current:
            utils.copy_to_clipboard(self, self.raw._raw)
            self.status("JSON copied to clipboard")


def _ascii_strings_from_sections(sections: list) -> list[str]:
    """Harvest printable names embedded in raw BFLAN section payloads."""
    import re

    seen: list[str] = []
    for section in sections:
        payload = section.get("payload_hex") or ""
        try:
            raw = bytes.fromhex(payload)
        except ValueError:
            continue
        for match in re.finditer(rb"[ -~]{3,}", raw):
            text = match.group().decode("ascii")
            if text not in seen and not text.isdigit():
                seen.append(text)
    return seen[:60]
