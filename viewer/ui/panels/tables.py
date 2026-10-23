"""BXON parameter table browser."""

from __future__ import annotations

import json
from tkinter import ttk

from ... import theme, utils
from ..widgets import JsonTree, KVTable, Panel, TextViewer, button, dim, search_entry


class TablesPanel(Panel):
    key = "tables"
    title = "Tables"
    icon = "\u25a4"

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
        left.rowconfigure(4, weight=1)

        ttk.Label(left, text="Parameter tables", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        self.cat_var = ttk.Combobox(left, state="readonly", values=["All categories"])
        self.cat_var.current(0)
        self.cat_var.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        self.cat_var.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=2, column=0, sticky="ew")
        self.entry = search_entry(bar, width=16, placeholder="Search tables\u2026")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())

        self.tree = ttk.Treeview(left, columns=("size",), selectmode="browse")
        self.tree.heading("#0", text="Table")
        self.tree.heading("size", text="Size")
        self.tree.column("#0", width=230)
        self.tree.column("size", width=70, anchor="e", stretch=False)
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=4, column=0, sticky="nsew", pady=(6, 0))
        vbar.grid(row=4, column=1, sticky="ns", pady=(6, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.count_label = dim(left, "")
        self.count_label.grid(row=5, column=0, sticky="w", pady=(4, 0))

        right = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(right, weight=3)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="Select a table", style="H2.TLabel")
        self.name_label.pack(anchor="w")
        self.info_label = dim(head, "")
        self.info_label.pack(anchor="w")

        nb = ttk.Notebook(right)
        nb.grid(row=1, column=0, sticky="nsew", pady=(6, 0))

        tree_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(tree_tab, text="Structure")
        tree_tab.columnconfigure(0, weight=1)
        tree_tab.rowconfigure(0, weight=1)
        self.json_tree = JsonTree(tree_tab)
        self.json_tree.grid(row=0, column=0, sticky="nsew")

        raw_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(raw_tab, text="Raw JSON")
        raw_tab.columnconfigure(0, weight=1)
        raw_tab.rowconfigure(1, weight=1)
        raw_bar = ttk.Frame(raw_tab, style="Panel.TFrame", padding=(0, 6))
        raw_bar.grid(row=0, column=0, sticky="ew")
        button(raw_bar, "Reveal file", self._reveal).pack(side="left")
        button(raw_bar, "Copy path", self._copy_path).pack(side="left", padx=6)
        self.raw = TextViewer(raw_tab, show_lines=False)
        self.raw.grid(row=1, column=0, sticky="nsew")

        info_tab = ttk.Frame(nb, style="Panel.TFrame")
        nb.add(info_tab, text="Summary")
        info_tab.columnconfigure(0, weight=1)
        info_tab.rowconfigure(0, weight=1)
        self.kv = KVTable(info_tab, height=14, key_width=150)
        self.kv.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._refresh()

    def set_filter(self, query: str | None = None, category: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        if category:
            values = list(self.cat_var["values"])
            if category in values:
                self.cat_var.set(category)
        self._refresh()

    def summary(self) -> str:
        return f"{len(self._items):,} tables"

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        index = self.app.tables.ensure()
        values = ["All categories"] + [f"{name}  ({count})" for name, count in index.categories()]
        self.cat_var.configure(values=values)
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        cat_sel = self.cat_var.get()
        category = None if not cat_sel or cat_sel.startswith("All") else cat_sel.split("  (")[0]
        self._items = index.search(query, category)
        self.tree.delete(*self.tree.get_children())
        for item in self._items:
            self.tree.insert("", "end", iid=str(item.path), text=item.name,
                             values=(utils.human_size(item.size_bytes),))
        self.count_label.configure(text=f"{len(self._items):,} tables")
        self.status(f"{len(self._items):,} parameter tables")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        item = next((t for t in self._items if str(t.path) == sel[0]), None)
        if item is None:
            return
        self._current = item
        index = self.app.tables
        data = index.load(item)
        self.name_label.configure(text=item.name)
        self.info_label.configure(
            text=f"{item.category}  \u00b7  {utils.human_size(item.size_bytes)}  \u00b7  {index.summary(item)}")
        self.json_tree.show(data)
        self.raw.show(json.dumps(data, indent=2, ensure_ascii=False), "json",
                      header=f"# {item.path}")
        rows = [("category", item.category), ("file", str(item.path)),
                ("size", utils.human_size(item.size_bytes))]
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    rows.append((key, f"{type(value).__name__} with {len(value)} entries"))
                else:
                    rows.append((key, utils.elide(str(value), 120)))
        self.kv.set_rows(rows)
        self.status(f"{item.name}  \u00b7  {index.summary(item)}")

    def _reveal(self) -> None:
        if self._current:
            utils.reveal_in_explorer(self._current.path)

    def _copy_path(self) -> None:
        if self._current:
            utils.copy_to_clipboard(self, str(self._current.path))
            self.status("Path copied")
