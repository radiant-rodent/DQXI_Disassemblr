"""Decompiled code browser: function catalogue plus source trees."""

from __future__ import annotations

import os
from tkinter import ttk

from ... import theme, utils
from ..widgets import KVTable, Panel, TextViewer, button, dim, search_entry

LANG_BY_EXT = {".c": "c", ".h": "c", ".s": "asm", ".py": "py", ".json": "json",
               ".md": "text", ".txt": "text", ".nut": "nut-asm"}


class CodePanel(Panel):
    key = "code"
    title = "Code"
    icon = "\u2329\u232a"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._functions: list = []
        self._files: list = []
        self._current_func = None
        self._current_file = None
        self._debounce = utils.debounced(self, 250, lambda: self._search_functions())

        head = ttk.Frame(self, style="TFrame", padding=(12, 10, 12, 0))
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="Code", style="H1.TLabel").pack(side="left")
        self.stats_label = dim(head, "")
        self.stats_label.pack(side="left", padx=12)

        nb = ttk.Notebook(self)
        nb.grid(row=1, column=0, sticky="nsew", padx=12, pady=(8, 12))

        # --- functions tab -------------------------------------------------
        func_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(func_tab, text="Decompiled functions")
        func_tab.columnconfigure(0, weight=1)
        func_tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(func_tab, style="Panel.TFrame", padding=(10, 10, 10, 6))
        bar.grid(row=0, column=0, sticky="ew")
        self.entry = search_entry(bar, width=34, placeholder="Search name or paste 0x00100050\u2026")
        self.entry.pack(side="left")
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())
        self.entry.bind("<Return>", lambda e: self._search_functions())
        self.mode_var = ttk.Combobox(bar, state="readonly", width=8, values=["all", "arm", "thumb"])
        self.mode_var.current(0)
        self.mode_var.pack(side="left", padx=6)
        self.mode_var.bind("<<ComboboxSelected>>", lambda e: self._search_functions())
        self.count_label = dim(bar, "")
        self.count_label.pack(side="left", padx=8)
        button(bar, "Reveal file", self._reveal_func).pack(side="right")
        button(bar, "Copy address", self._copy_addr).pack(side="right", padx=6)

        split = ttk.PanedWindow(func_tab, orient="horizontal")
        split.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        left = ttk.Frame(split, style="Panel.TFrame")
        split.add(left, weight=2)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.func_tree = ttk.Treeview(left, columns=("addr", "size", "mode"), selectmode="browse")
        self.func_tree.heading("#0", text="Function")
        self.func_tree.heading("addr", text="Address")
        self.func_tree.heading("size", text="Bytes")
        self.func_tree.heading("mode", text="Mode")
        self.func_tree.column("#0", width=250)
        self.func_tree.column("addr", width=100, stretch=False)
        self.func_tree.column("size", width=60, anchor="e", stretch=False)
        self.func_tree.column("mode", width=60, stretch=False)
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.func_tree.yview)
        self.func_tree.configure(yscrollcommand=vbar.set)
        self.func_tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        self.func_tree.bind("<<TreeviewSelect>>", self._func_selected)

        right = ttk.Frame(split, style="Panel.TFrame")
        split.add(right, weight=4)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self.func_title = ttk.Label(right, text="Select a function", style="H2.TLabel")
        self.func_title.grid(row=0, column=0, sticky="w", padx=(8, 0))
        self.func_meta = dim(right, "")
        self.func_meta.grid(row=1, column=0, sticky="w", padx=(8, 0), pady=(0, 4))
        self.func_view = TextViewer(right, show_lines=True)
        self.func_view.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=(0, 0))

        # --- sources tab ---------------------------------------------------
        src_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(src_tab, text="Sources & assembly")
        src_tab.columnconfigure(0, weight=1)
        src_tab.rowconfigure(1, weight=1)

        bar2 = ttk.Frame(src_tab, style="Panel.TFrame", padding=(10, 10, 10, 6))
        bar2.grid(row=0, column=0, sticky="ew")
        ttk.Label(bar2, text="Group:", style="Panel.TLabel").pack(side="left")
        self.group_var = ttk.Combobox(bar2, state="readonly", width=22, values=[])
        self.group_var.pack(side="left", padx=6)
        self.group_var.bind("<<ComboboxSelected>>", lambda e: self._fill_files())
        button(bar2, "Reveal file", self._reveal_file).pack(side="right")
        button(bar2, "Copy path", self._copy_file_path).pack(side="right", padx=6)
        self.file_count = dim(bar2, "")
        self.file_count.pack(side="left", padx=8)

        split2 = ttk.PanedWindow(src_tab, orient="horizontal")
        split2.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        left2 = ttk.Frame(split2, style="Panel.TFrame")
        split2.add(left2, weight=1)
        left2.columnconfigure(0, weight=1)
        left2.rowconfigure(0, weight=1)
        self.file_tree = ttk.Treeview(left2, columns=("size",), selectmode="browse")
        self.file_tree.heading("#0", text="File")
        self.file_tree.heading("size", text="Size")
        self.file_tree.column("#0", width=260)
        self.file_tree.column("size", width=70, anchor="e", stretch=False)
        vbar2 = ttk.Scrollbar(left2, orient="vertical", command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=vbar2.set)
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        vbar2.grid(row=0, column=1, sticky="ns")
        self.file_tree.bind("<<TreeviewSelect>>", self._file_selected)

        right2 = ttk.Frame(split2, style="Panel.TFrame")
        split2.add(right2, weight=4)
        right2.columnconfigure(0, weight=1)
        right2.rowconfigure(2, weight=1)
        self.file_title = ttk.Label(right2, text="Select a file", style="H2.TLabel")
        self.file_title.grid(row=0, column=0, sticky="w", padx=(8, 0))
        self.file_meta = dim(right2, "")
        self.file_meta.grid(row=1, column=0, sticky="w", padx=(8, 0), pady=(0, 4))
        self.file_view = TextViewer(right2, show_lines=True)
        self.file_view.grid(row=2, column=0, sticky="nsew", padx=(8, 0))

        self._groups: dict = {}

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        index = self.app.code.ensure()
        self.stats_label.configure(
            text=f"{len(index.functions):,} functions catalogued  \u00b7  "
                 f"{index.total_discovered:,} discovered  \u00b7  {index.decompiled_count:,} lifted")
        self._search_functions()
        self._groups = index.source_groups()
        names = list(self._groups.keys())
        self.group_var.configure(values=names)
        if names:
            self.group_var.current(0)
            self._fill_files()

    def set_filter(self, query: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        if self._shown_once:
            self._search_functions()

    def summary(self) -> str:
        index = self.app.code
        if index.ready:
            return f"{len(index.functions):,} functions"
        return ""

    # ------------------------------------------------------------------
    def _search_functions(self) -> None:
        index = self.app.code.ensure()
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        mode = self.mode_var.get()
        mode = None if mode == "all" else mode
        self._functions = index.search(query, mode=mode)
        self.func_tree.delete(*self.func_tree.get_children())
        for f in self._functions[:4000]:
            self.func_tree.insert("", "end", iid=f.addr_hex, text=f.name,
                                  values=(f.addr_hex, f"{f.size:,}", f.mode))
        shown = min(len(self._functions), 4000)
        extra = "" if shown == len(self._functions) else " (type to narrow)"
        self.count_label.configure(text=f"{len(self._functions):,} matches{extra}")
        self.status(f"{len(self._functions):,} functions match")

    def _func_selected(self, _event=None) -> None:
        sel = self.func_tree.selection()
        if not sel:
            return
        addr = sel[0]
        func = next((f for f in self._functions if f.addr_hex == addr), None)
        if func is None:
            return
        self._current_func = func
        text = self.app.code.text(func)
        self.func_title.configure(text=f"{func.name}   {func.addr_hex}")
        self.func_meta.configure(
            text=f"{func.mode.upper()}  \u00b7  {func.size:,} bytes  \u00b7  "
                 f"0x{func.address:08X} \u2013 0x{func.end:08X}  \u00b7  {func.file.name}")
        self.func_view.show(text, "c", header=f"// {func.name} @ {func.addr_hex} ({func.mode})")
        self.status(f"{func.name} @ {func.addr_hex} \u00b7 {func.size:,} bytes \u00b7 {func.mode}")

    def _fill_files(self) -> None:
        group = self.group_var.get()
        self._files = self._groups.get(group, [])
        self.file_tree.delete(*self.file_tree.get_children())
        for rel, path, size in self._files:
            self.file_tree.insert("", "end", iid=str(path), text=rel,
                                  values=(utils.human_size(size),))
        self.file_count.configure(text=f"{len(self._files):,} files")

    def _file_selected(self, _event=None) -> None:
        sel = self.file_tree.selection()
        if not sel:
            return
        path = sel[0]
        entry = next((f for f in self._files if str(f[1]) == path), None)
        if entry is None:
            return
        rel, file_path, size = entry
        self._current_file = file_path
        try:
            content = utils.safe_read_text(file_path, max_bytes=32 * 1024 * 1024)
        except Exception as exc:
            content = f"// failed to read: {exc}"
        lines = content.count("\n") + 1
        lang = LANG_BY_EXT.get(file_path.suffix.lower(), "text")
        self.file_title.configure(text=file_path.name)
        self.file_meta.configure(
            text=f"{rel}  \u00b7  {lines:,} lines  \u00b7  {utils.human_size(size)}  \u00b7  {lang}")
        self.file_view.show(content, lang, header=f"# {rel}")
        self.status(f"{rel}  \u00b7  {lines:,} lines")

    # ------------------------------------------------------------------
    def _reveal_func(self) -> None:
        if self._current_func:
            utils.reveal_in_explorer(self._current_func.file)

    def _copy_addr(self) -> None:
        if self._current_func:
            utils.copy_to_clipboard(self, self._current_func.addr_hex)
            self.status("Address copied")

    def _reveal_file(self) -> None:
        if self._current_file:
            utils.reveal_in_explorer(self._current_file)

    def _copy_file_path(self) -> None:
        if self._current_file:
            utils.copy_to_clipboard(self, str(self._current_file))
            self.status("Path copied")
