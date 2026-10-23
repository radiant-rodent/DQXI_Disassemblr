"""Dialogue browser backed by the read-only translation database."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ... import theme, utils
from ..widgets import KVTable, Panel, TextViewer, button, dim, search_entry

PAGE = 250


class DialoguesPanel(Panel):
    key = "dialogues"
    title = "Dialogues"
    icon = "\u201c\u201d"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._rows: list = []
        self._page = 0
        self._total = 0
        self._pc_rows: list = []
        self._pc_page = 0
        self._pc_total = 0
        self._debounce = utils.debounced(self, 350, lambda: self._search(reset_page=True))

        head = ttk.Frame(self, style="TFrame", padding=(12, 10, 12, 0))
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="Dialogues", style="H1.TLabel").pack(side="left")
        self.stats_label = dim(head, "")
        self.stats_label.pack(side="left", padx=12)

        self.nb = ttk.Notebook(self)
        self.nb.grid(row=1, column=0, sticky="nsew", padx=12, pady=(8, 12))

        self._build_source_tab()
        self._build_pc_tab()

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        db = self.app.dialogues
        if not db.available():
            self.stats_label.configure(
                text=f"dialogue database not found at {db.path} \u2014 reading other sections still works")
            for tab in (self.source_tab, self.pc_tab):
                tab.winfo_children()
            return
        st = db.stats()
        self.stats_label.configure(
            text=f"{st.sources:,} source entries  \u00b7  {st.entries:,} locations  \u00b7  "
                 f"{st.reviewed:,} reviewed  \u00b7  {st.translated:,} translated  \u00b7  "
                 f"{st.untranslated:,} untranslated  \u00b7  {st.pc_rows:,} PC rows")
        files = ["All files"] + [f"{name}  ({count})" for name, count in db.file_list()[:400]]
        self.file_var.configure(values=files)
        self.file_var.current(0)
        self._search(reset_page=True)
        self._search_pc(reset_page=True)

    def set_filter(self, query: str | None = None, file: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        if file is not None:
            values = list(self.file_var["values"])
            hit = next((v for v in values if file.lower() in v.lower()),
                       "All files")
            self.file_var.set(hit)
            self.nb.select(0)
        if self._shown_once:
            self._search(reset_page=True)

    def summary(self) -> str:
        db = self.app.dialogues
        if not db.available():
            return "db missing"
        st = db.stats()
        return f"{st.sources:,} entries"

    # ------------------------------------------------------------------
    def _build_source_tab(self) -> None:
        tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(tab, text="Game dialogue (3DS)")
        self.source_tab = tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab, style="Panel.TFrame", padding=(10, 10, 10, 6))
        bar.grid(row=0, column=0, sticky="ew")
        self.entry = search_entry(bar, width=32, placeholder="Search Japanese or English text\u2026")
        self.entry.pack(side="left")
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())
        self.entry.bind("<Return>", lambda e: self._search(reset_page=True))

        self.file_var = ttk.Combobox(bar, state="readonly", width=26, values=["All files"])
        self.file_var.current(0)
        self.file_var.pack(side="left", padx=6)
        self.file_var.bind("<<ComboboxSelected>>", lambda e: self._search(reset_page=True))

        self.status_var = ttk.Combobox(bar, state="readonly", width=14,
                                       values=["All statuses", "untranslated", "translated",
                                               "reviewed"])
        self.status_var.current(0)
        self.status_var.pack(side="left", padx=(0, 6))
        self.status_var.bind("<<ComboboxSelected>>", lambda e: self._search(reset_page=True))

        self.origin_var = ttk.Combobox(bar, state="readonly", width=10,
                                       values=["All origins", "pc", "ai", "manual"])
        self.origin_var.current(0)
        self.origin_var.pack(side="left", padx=(0, 6))
        self.origin_var.bind("<<ComboboxSelected>>", lambda e: self._search(reset_page=True))

        page_bar = ttk.Frame(bar, style="Panel.TFrame")
        page_bar.pack(side="right")
        button(page_bar, "\u25c0 Prev", lambda: self._goto_page(self._page - 1)).pack(side="left")
        self.page_label = dim(page_bar, "0 / 0")
        self.page_label.pack(side="left", padx=8)
        button(page_bar, "Next \u25b6", lambda: self._goto_page(self._page + 1)).pack(side="left")

        split = ttk.PanedWindow(tab, orient="vertical")
        split.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        list_frame = ttk.Frame(split, style="Panel.TFrame")
        split.add(list_frame, weight=3)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(list_frame, columns=("status", "jp", "en"),
                                 selectmode="browse")
        self.tree.heading("#0", text="Source")
        self.tree.heading("status", text="Status")
        self.tree.heading("jp", text="Japanese")
        self.tree.heading("en", text="English translation")
        self.tree.column("#0", width=90, stretch=False)
        self.tree.column("status", width=100, stretch=False)
        self.tree.column("jp", width=430)
        self.tree.column("en", width=520)
        vbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._row_selected)

        detail = ttk.Frame(split, style="Panel.TFrame")
        split.add(detail, weight=2)
        detail.columnconfigure(0, weight=1)
        detail.columnconfigure(1, weight=1)
        detail.rowconfigure(1, weight=1)

        jp_head = ttk.Frame(detail, style="Panel.TFrame")
        jp_head.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=(8, 0))
        ttk.Label(jp_head, text="Japanese source", style="Accent.TLabel").pack(side="left")
        en_head = ttk.Frame(detail, style="Panel.TFrame")
        en_head.grid(row=0, column=1, sticky="ew", padx=(4, 10), pady=(8, 0))
        ttk.Label(en_head, text="English translation", style="Accent.TLabel").pack(side="left")
        button(en_head, "Copy JP", lambda: self._copy("jp")).pack(side="right")
        button(en_head, "Copy EN", lambda: self._copy("en")).pack(side="right", padx=6)

        self.jp_view = TextViewer(detail, show_lines=False)
        self.jp_view.text.configure(font=theme.jp_font(11))
        self.jp_view.grid(row=1, column=0, sticky="nsew", padx=(10, 4), pady=(4, 6))
        self.en_view = TextViewer(detail, show_lines=False)
        self.en_view.grid(row=1, column=1, sticky="nsew", padx=(4, 10), pady=(4, 6))

        loc_frame = ttk.Frame(detail, style="Panel.TFrame")
        loc_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 8))
        ttk.Label(loc_frame, text="Where it lives in the ROM", style="Accent.TLabel").pack(anchor="w")
        self.loc_tree = ttk.Treeview(loc_frame, columns=("file", "entry", "loc", "category"),
                                     selectmode="browse", height=5)
        self.loc_tree.heading("#0", text="Kind")
        self.loc_tree.heading("file", text="File")
        self.loc_tree.heading("entry", text="Entry")
        self.loc_tree.heading("loc", text="Offset")
        self.loc_tree.heading("category", text="Category")
        self.loc_tree.column("#0", width=70, stretch=False)
        self.loc_tree.column("file", width=260)
        self.loc_tree.column("entry", width=200)
        self.loc_tree.column("loc", width=80, stretch=False)
        self.loc_tree.column("category", width=160)
        self.loc_tree.pack(fill="x", pady=(2, 0))

    def _build_pc_tab(self) -> None:
        tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(tab, text="PC text (official English)")
        self.pc_tab = tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab, style="Panel.TFrame", padding=(10, 10, 10, 6))
        bar.grid(row=0, column=0, sticky="ew")
        self.pc_entry = search_entry(bar, width=32, placeholder="Search official PC text\u2026")
        self.pc_entry.pack(side="left")
        self.pc_entry.bind("<KeyRelease>", lambda e: self._pc_debounced())
        self.pc_entry.bind("<Return>", lambda e: self._search_pc(reset_page=True))
        self.pc_inline = dim(bar, "")
        self.pc_inline.pack(side="left", padx=8)
        page_bar = ttk.Frame(bar, style="Panel.TFrame")
        page_bar.pack(side="right")
        button(page_bar, "\u25c0 Prev", lambda: self._goto_pc_page(self._pc_page - 1)).pack(side="left")
        self.pc_page_label = dim(page_bar, "0 / 0")
        self.pc_page_label.pack(side="left", padx=8)
        button(page_bar, "Next \u25b6", lambda: self._goto_pc_page(self._pc_page + 1)).pack(side="left")

        split = ttk.PanedWindow(tab, orient="vertical")
        split.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        list_frame = ttk.Frame(split, style="Panel.TFrame")
        split.add(list_frame, weight=3)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.pc_tree = ttk.Treeview(list_frame, columns=("file", "jp", "en"), selectmode="browse")
        self.pc_tree.heading("#0", text="Key")
        self.pc_tree.heading("file", text="Table")
        self.pc_tree.heading("jp", text="Japanese")
        self.pc_tree.heading("en", text="PC English")
        self.pc_tree.column("#0", width=210, stretch=False)
        self.pc_tree.column("file", width=180, stretch=False)
        self.pc_tree.column("jp", width=420)
        self.pc_tree.column("en", width=520)
        vbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.pc_tree.yview)
        self.pc_tree.configure(yscrollcommand=vbar.set)
        self.pc_tree.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        self.pc_tree.bind("<<TreeviewSelect>>", self._pc_selected)

        detail = ttk.Frame(split, style="Panel.TFrame")
        split.add(detail, weight=2)
        detail.columnconfigure(0, weight=1)
        detail.columnconfigure(1, weight=1)
        detail.rowconfigure(1, weight=1)
        ttk.Label(detail, text="Japanese", style="Accent.TLabel").grid(
            row=0, column=0, sticky="w", padx=(10, 4), pady=(8, 0))
        ttk.Label(detail, text="Official English (PC)", style="Accent.TLabel").grid(
            row=0, column=1, sticky="w", padx=(4, 10), pady=(8, 0))
        self.pc_jp = TextViewer(detail, show_lines=False)
        self.pc_jp.text.configure(font=theme.jp_font(11))
        self.pc_jp.grid(row=1, column=0, sticky="nsew", padx=(10, 4), pady=(4, 6))
        self.pc_en = TextViewer(detail, show_lines=False)
        self.pc_en.grid(row=1, column=1, sticky="nsew", padx=(4, 10), pady=(4, 6))

    # ------------------------------------------------------------------
    def _pc_debounced(self) -> None:
        if not hasattr(self, "_pc_debounce"):
            self._pc_debounce = utils.debounced(self, 350, lambda: self._search_pc(reset_page=True))
        self._pc_debounce()

    # -- source tab -----------------------------------------------------
    def _filters(self):
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        file_sel = self.file_var.get()
        file_filter = None if file_sel.startswith("All files") else file_sel.split("  (")[0]
        status_map = {"All statuses": None, "untranslated": 0, "translated": 1, "reviewed": 2}
        status = status_map.get(self.status_var.get())
        origin = None if self.origin_var.get().startswith("All") else self.origin_var.get()
        return query, file_filter, status, origin

    def _search(self, reset_page: bool = False) -> None:
        db = self.app.dialogues
        if not db.available():
            return
        if reset_page:
            self._page = 0
        query, file_filter, status, origin = self._filters()
        self._total = db.count_sources(query, file_filter, status, origin)
        max_page = max(0, (self._total - 1) // PAGE)
        self._page = max(0, min(self._page, max_page))
        self._rows = db.search_sources(query, file_filter, status, origin,
                                       offset=self._page * PAGE, limit=PAGE)
        self.tree.delete(*self.tree.get_children())
        for row in self._rows:
            self.tree.insert("", "end", iid=str(row.id),
                             text=f"#{row.id}",
                             values=(f"{row.status_text} ({row.origin})",
                                     utils.elide(_clean(row.jp), 90),
                                     utils.elide(_clean(row.en), 100)))
        self.page_label.configure(
            text=f"page {self._page + 1} / {max_page + 1}  \u00b7  {self._total:,} entries")
        self.status(f"{self._total:,} dialogue entries match")

    def _goto_page(self, page: int) -> None:
        self._page = page
        self._search()

    def _row_selected(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        row = next((r for r in self._rows if str(r.id) == sel[0]), None)
        if row is None:
            return
        self.jp_view.show(row.jp, "text", header=f"# source {row.id}  \u00b7  "
                                                f"{row.status_text}  \u00b7  origin {row.origin}")
        self.en_view.show(row.en or "(not translated yet)", "text")
        self.loc_tree.delete(*self.loc_tree.get_children())
        for loc in self.app.dialogues.locations(row.id):
            value = loc.get("loc")
            display = f"0x{value:X}" if isinstance(value, int) else str(value or "-")
            self.loc_tree.insert("", "end", text=str(loc.get("kind") or "?"),
                                 values=(loc.get("file") or "-", loc.get("entry") or "-",
                                         display, loc.get("category") or "-"))
        self.status(f"source #{row.id} \u00b7 {row.status_text}")

    def _copy(self, which: str) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        row = next((r for r in self._rows if str(r.id) == sel[0]), None)
        if row is None:
            return
        utils.copy_to_clipboard(self, row.jp if which == "jp" else row.en)
        self.status(f"Copied {'Japanese' if which == 'jp' else 'English'} text")

    # -- pc tab ---------------------------------------------------------
    def _search_pc(self, reset_page: bool = False) -> None:
        db = self.app.dialogues
        if not db.available():
            return
        if reset_page:
            self._pc_page = 0
        query = self.pc_entry.get_value().strip()  # type: ignore[attr-defined]
        self._pc_rows = db.search_pc(query, offset=self._pc_page * PAGE, limit=PAGE)
        self.pc_tree.delete(*self.pc_tree.get_children())
        for row in self._pc_rows:
            self.pc_tree.insert("", "end", iid=str(row.get("id")), text=str(row.get("key") or ""),
                                values=(str(row.get("file") or ""),
                                        utils.elide(_clean(row.get("jp") or ""), 80),
                                        utils.elide(_clean(row.get("en") or ""), 90)))
        self.pc_inline.configure(text=f"{len(self._pc_rows):,} rows shown")
        self.pc_page_label.configure(text=f"page {self._pc_page + 1}")
        self.status(f"{len(self._pc_rows):,} PC text rows")

    def _goto_pc_page(self, page: int) -> None:
        self._pc_page = max(0, page)
        self._search_pc()

    def _pc_selected(self, _event=None) -> None:
        sel = self.pc_tree.selection()
        if not sel:
            return
        row = next((r for r in self._pc_rows if str(r.get("id")) == sel[0]), None)
        if row is None:
            return
        header = f"# {row.get('file')} :: {row.get('key')}"
        self.pc_jp.show(str(row.get("jp") or ""), "text", header=header)
        self.pc_en.show(str(row.get("en") or ""), "text", header=header)


def _clean(text: str) -> str:
    """Make control codes readable in one-line previews."""
    return (text.replace("\r", " ").replace("\n", " \u21b5 ")
            .replace("\u3000", " ").strip())
