"""Squirrel script browser (disassembled .nut files)."""

from __future__ import annotations

from tkinter import ttk

from ... import theme, utils
from ..widgets import Panel, TextViewer, button, dim, search_entry


class ScriptsPanel(Panel):
    key = "scripts"
    title = "Scripts"
    icon = "\u25b7"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._items: list = []
        self._current = None
        self._debounce = utils.debounced(self, 200, lambda: self._refresh())

        split = ttk.PanedWindow(self, orient="horizontal")
        split.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(left, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Script packs", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=1, column=0, sticky="ew", pady=6)
        self.entry = search_entry(bar, width=18, placeholder="Search area\u2026")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())

        self.tree = ttk.Treeview(left, columns=("size",), selectmode="browse")
        self.tree.heading("#0", text="Area")
        self.tree.heading("size", text="Size")
        self.tree.column("#0", width=210)
        self.tree.column("size", width=70, anchor="e", stretch=False)
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        vbar.grid(row=2, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.count_label = dim(left, "")
        self.count_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

        right = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(right, weight=4)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="Select a script", style="H2.TLabel")
        self.name_label.pack(anchor="w")
        self.info_label = dim(head, "")
        self.info_label.pack(anchor="w")

        bar2 = ttk.Frame(right, style="Panel.TFrame")
        bar2.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.filter_entry = search_entry(bar2, width=22, placeholder="Find in file\u2026")
        self.filter_entry.pack(side="left")
        button(bar2, "Find", self._find).pack(side="left", padx=6)
        button(bar2, "Next", lambda: self._find(next_hit=True)).pack(side="left")
        button(bar2, "Reveal file", self._reveal).pack(side="right")
        button(bar2, "Copy path", self._copy_path).pack(side="right", padx=6)

        split2 = ttk.PanedWindow(right, orient="horizontal")
        split2.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        self.viewer = TextViewer(split2, show_lines=True)
        split2.add(self.viewer, weight=4)
        funcs = ttk.Frame(split2, style="Panel.TFrame")
        split2.add(funcs, weight=1)
        funcs.columnconfigure(0, weight=1)
        funcs.rowconfigure(1, weight=1)
        dim(funcs, "Functions in this pack").grid(row=0, column=0, sticky="w", padx=(8, 0))
        self.func_tree = ttk.Treeview(funcs, columns=("args", "note"), selectmode="browse")
        self.func_tree.heading("#0", text="Function")
        self.func_tree.heading("args", text="Arguments")
        self.func_tree.heading("note", text="Notes")
        self.func_tree.column("#0", width=150)
        self.func_tree.column("args", width=110, stretch=False)
        self.func_tree.column("note", width=90, stretch=False)
        vf = ttk.Scrollbar(funcs, orient="vertical", command=self.func_tree.yview)
        self.func_tree.configure(yscrollcommand=vf.set)
        self.func_tree.grid(row=1, column=0, sticky="nsew", padx=(8, 0), pady=3)
        vf.grid(row=1, column=1, sticky="ns", pady=3)
        self.func_tree.bind("<<TreeviewSelect>>", self._func_selected)

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._refresh()

    def set_filter(self, query: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        self._refresh()

    def summary(self) -> str:
        return f"{len(self._items):,} scripts"

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        index = self.app.scripts.ensure()
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        self._items = index.search(query)
        self.tree.delete(*self.tree.get_children())
        for item in self._items:
            self.tree.insert("", "end", iid=item.area, text=item.area,
                             values=(utils.human_size(item.size_bytes),))
        self.count_label.configure(text=f"{len(self._items):,} packs")
        self.status(f"{len(self._items):,} script packs")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        area = sel[0]
        item = next((s for s in self._items if s.area == area), None)
        if item is None:
            return
        self._current = item
        index = self.app.scripts
        text = index.text(item)
        outline = index.outline(item)
        self.name_label.configure(text=area)
        self.info_label.configure(
            text=f"{len(text.splitlines()):,} lines  \u00b7  {len(outline):,} functions"
                 f"  \u00b7  {utils.human_size(item.size_bytes)}  \u00b7  {item.path}")
        self.viewer.show(text, "nut-asm", header=f"# {item.area}/script.nut (Squirrel 3.0 disassembly)")
        self.func_tree.delete(*self.func_tree.get_children())
        for i, (name, args, note) in enumerate(outline):
            self.func_tree.insert("", "end", iid=f"{i}:{name}", text=name,
                                  values=(utils.elide(args, 40), note))
        self.status(f"{area}  \u00b7  {len(outline):,} functions")

    def _func_selected(self, _event=None) -> None:
        sel = self.func_tree.selection()
        if not sel:
            return
        name = sel[0].split(":", 1)[1]
        pos = self.viewer.text.search(f"function '{name}'", "1.0", stopindex="end")
        if pos:
            self.viewer.text.see(pos)
            self.viewer.text.tag_remove("sel_reg", "1.0", "end")
            end = f"{pos} lineend"
            self.viewer.text.tag_add("sel_reg", pos, end)

    def _find(self, next_hit: bool = False) -> None:
        needle = self.filter_entry.get_value().strip()  # type: ignore[attr-defined]
        if not needle:
            return
        text = self.viewer.text
        start = text.index("insert")
        if not next_hit:
            start = "1.0"
        pos = text.search(needle, start, stopindex="end", nocase=True)
        if not pos:
            self.status(f"'{needle}' not found")
            return
        text.see(pos)
        text.mark_set("insert", f"{pos}+1c")
        text.tag_remove("find", "1.0", "end")
        text.tag_add("find", pos, f"{pos}+{len(needle)}c")
        self.status(f"found '{needle}' at {pos}")

    def _reveal(self) -> None:
        if self._current:
            utils.reveal_in_explorer(self._current.path)

    def _copy_path(self) -> None:
        if self._current:
            utils.copy_to_clipboard(self, str(self._current.path))
            self.status("Path copied")
