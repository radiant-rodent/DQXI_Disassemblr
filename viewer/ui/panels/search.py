"""Global search: one query across every catalogue with jump-to-section."""

from __future__ import annotations

import queue
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from ... import theme, utils
from ..widgets import Panel, button, dim, search_entry

PER_SCOPE_LIMIT = 80

SCOPES = [
    ("all", "Everything"),
    ("areas", "Map areas"),
    ("textures", "Textures"),
    ("models", "Models"),
    ("layouts", "Layouts"),
    ("scripts", "Scripts"),
    ("tables", "Tables"),
    ("audio", "Audio"),
    ("code", "Code"),
    ("dialogues", "Dialogues"),
]
_SCOPE_TITLE = dict(SCOPES)

SCOPE_COLORS = {
    "areas": "#5ec98a",
    "textures": "#6db3f2",
    "models": "#c792ea",
    "layouts": "#c3e88d",
    "scripts": "#ffcb6b",
    "tables": "#89ddff",
    "audio": "#f78c6c",
    "code": "#82aaff",
    "dialogues": theme.ACCENT,
}


def _one_line(text: str) -> str:
    return " ".join((text or "").split())


@dataclass
class Hit:
    scope: str
    label: str
    detail: str
    payload: dict


class SearchPanel(Panel):
    key = "search"
    title = "Search"
    icon = "\u2315"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._hits: list[Hit] = []
        self._by_iid: dict[str, Hit] = {}
        self._queue: queue.Queue = queue.Queue()
        self._token = 0
        self._started = 0.0
        self._debounce = utils.debounced(self, 350, lambda: self._start_search())

        head = ttk.Frame(self, style="TFrame", padding=(12, 10, 12, 0))
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(1, weight=1)
        ttk.Label(head, text="Search", style="H1.TLabel").grid(row=0, column=0, sticky="w")
        self.summary_label = dim(head, "search textures, meshes, layouts, scripts, tables, "
                                       "audio, code, dialogues and map areas at once")
        self.summary_label.grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))

        bar = ttk.Frame(self, style="Panel.TFrame", padding=(12, 10, 12, 6))
        bar.grid(row=1, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        self.entry = search_entry(bar, width=48,
                                  placeholder="Search everything\u2026  e.g. b001, slime, 0x00100050")
        self.entry.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())
        self.entry.bind("<Return>", lambda e: self._start_search())

        ttk.Label(bar, text="in", style="PanelDim.TLabel").grid(row=1, column=0, sticky="w",
                                                                pady=(6, 0))
        self.scope_var = ttk.Combobox(bar, state="readonly", width=16,
                                      values=[label for _key, label in SCOPES])
        self.scope_var.current(0)
        self.scope_var.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        self.scope_var.bind("<<ComboboxSelected>>", lambda e: self._start_search())

        actions = ttk.Frame(bar, style="Panel.TFrame")
        actions.grid(row=1, column=2, sticky="e", pady=(6, 0))
        button(actions, "Search", self._start_search, style="Accent.TButton").pack(side="left")
        self.open_btn = button(actions, "Open result", self._open_selected)
        self.open_btn.pack(side="left", padx=6)

        self.tree = ttk.Treeview(self, columns=("detail",), selectmode="browse")
        self.tree.heading("#0", text="Result")
        self.tree.heading("detail", text="Details")
        self.tree.column("#0", width=340)
        self.tree.column("detail", width=760)
        vbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=2, column=0, sticky="nsew", padx=12, pady=(2, 4))
        vbar.grid(row=2, column=1, sticky="ns", padx=(0, 12), pady=(2, 4))
        self.tree.tag_configure("group", foreground=theme.TEXT_DIM, font=theme.F_BOLD)
        for scope, color in SCOPE_COLORS.items():
            self.tree.tag_configure(f"scope:{scope}", foreground=color)
        self.tree.bind("<Double-1>", lambda e: self._open_selected())
        self.tree.bind("<Return>", lambda e: self._open_selected())

        self.hint = dim(self, "Double-click a result (or press Enter) to open it in its section")
        self.hint.grid(row=3, column=0, sticky="w", padx=12, pady=(0, 10))

        self._poll()

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self.entry.focus_set()

    def set_filter(self, query: str | None = None, **_) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        self._start_search()

    def summary(self) -> str:
        return f"{len(self._hits):,} search hits" if self._hits else ""

    # ------------------------------------------------------------------
    def _start_search(self) -> None:
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        scope_label = self.scope_var.get()
        scope = next((key for key, label in SCOPES if label == scope_label), "all")
        self._token += 1
        token = self._token
        if not query:
            self._hits = []
            self.tree.delete(*self.tree.get_children())
            self.summary_label.configure(text="type a query to search every catalogue at once")
            self.status("Search cleared")
            return
        self._started = time.perf_counter()
        self.summary_label.configure(text=f"searching \u201c{query}\u201d\u2026")
        self.status(f"Searching \u201c{query}\u201d\u2026")
        utils.submit(self._work, token, query, scope)

    def _work(self, token: int, query: str, scope: str) -> None:
        try:
            hits, totals = self._collect(query, scope)
            error = None
        except Exception as exc:  # pragma: no cover - defensive
            hits, totals, error = [], {}, str(exc)
        self._queue.put((token, hits, totals, error))

    def _poll(self) -> None:
        try:
            while True:
                token, hits, totals, error = self._queue.get_nowait()
                if token == self._token:
                    self._populate(hits, totals, error)
        except queue.Empty:
            pass
        try:
            self.after(120, self._poll)
        except tk.TclError:  # window destroyed
            pass

    # ------------------------------------------------------------------
    def _collect(self, query: str, scope: str) -> tuple[list[Hit], dict[str, int]]:
        app = self.app
        q = query.strip()
        ql = q.lower()
        hits: list[Hit] = []
        totals: dict[str, int] = {}
        wanted = [key for key, _label in SCOPES if key != "all"] if scope == "all" else [scope]

        def add(scope_key: str, label: str, detail: str, **payload) -> None:
            hits.append(Hit(scope_key, label, detail, payload))

        if "areas" in wanted:
            index = app.areas.ensure(app.textures, app.scripts, app.audio,
                                     app.layouts, app.dialogues, app.models)
            names = [a for a in index.all_areas() if ql in a]
            totals["areas"] = len(names)
            for name in names[:PER_SCOPE_LIMIT]:
                dossier = index.dossier(name)
                add("areas", name,
                    f"{dossier.asset_count} assets \u00b7 {len(dossier.textures)} texture packs"
                    f" \u00b7 {len(dossier.models)} 3D models \u00b7 "
                    f"{len(dossier.scripts)} script packs",
                    area=name)

        if "textures" in wanted:
            index = app.textures.ensure()
            found = index.search(q)
            totals["textures"] = len(found)
            for tex in found[:PER_SCOPE_LIMIT]:
                add("textures", tex.name,
                    f"{tex.pack}  \u00b7  {tex.dims}  \u00b7  {utils.human_size(tex.size_bytes)}",
                    name=tex.name, pack=tex.pack)

        if "models" in wanted:
            index = app.models.ensure()
            found = index.search(q)
            totals["models"] = len(found)
            for model in found[:PER_SCOPE_LIMIT]:
                add("models", model.name,
                    f"{model.category}  \u00b7  {utils.human_size(model.size_bytes)}",
                    name=model.name, category=model.category)

        if "layouts" in wanted:
            index = app.layouts.ensure()
            found = index.search(q)
            totals["layouts"] = len(found)
            for lay in found[:PER_SCOPE_LIMIT]:
                add("layouts", lay.stem,
                    f"{lay.pack}  \u00b7  {lay.kind}  \u00b7  {utils.human_size(lay.size_bytes)}",
                    stem=lay.stem.replace(".layout.json", "").replace(".anim.json", ""),
                    pack=lay.pack)

        if "scripts" in wanted:
            index = app.scripts.ensure()
            found = index.search(q)
            totals["scripts"] = len(found)
            for script in found[:PER_SCOPE_LIMIT]:
                add("scripts", script.area,
                    f"{utils.human_size(script.size_bytes)}  \u00b7  {script.path.name}",
                    area=script.area)

        if "tables" in wanted:
            index = app.tables.ensure()
            found = index.search(q)
            totals["tables"] = len(found)
            for table in found[:PER_SCOPE_LIMIT]:
                add("tables", table.name,
                    f"{table.category}  \u00b7  {utils.human_size(table.size_bytes)}",
                    name=table.name, category=table.category)

        if "audio" in wanted:
            index = app.audio.ensure()
            found = index.search_streams(q)
            totals["audio"] = len(found)
            for stream in found[:PER_SCOPE_LIMIT]:
                add("audio", stream.name,
                    f"{stream.duration_text}  \u00b7  {utils.human_size(stream.size_bytes)}",
                    name=stream.name)

        if "code" in wanted:
            index = app.code.ensure()
            found = index.search(q, limit=1_000_000)
            totals["code"] = len(found)
            for func in found[:PER_SCOPE_LIMIT]:
                add("code", func.name,
                    f"{func.addr_hex}  \u00b7  {func.size:,} bytes  \u00b7  {func.mode}",
                    addr=func.addr_hex, name=func.name)

        if "dialogues" in wanted:
            db = app.dialogues
            if db.available():
                rows = db.search_sources(q, limit=PER_SCOPE_LIMIT)
                totals["dialogues"] = db.count_sources(q)
                for row in rows:
                    jp = _one_line(row.jp)
                    add("dialogues", f"#{row.id}",
                        f"{row.status_text}  \u00b7  {utils.elide(jp, 90)}",
                        query=jp[:64] or q)

        return hits, totals

    # ------------------------------------------------------------------
    def _populate(self, hits: list[Hit], totals: dict[str, int], error: str | None) -> None:
        tree = self.tree
        tree.delete(*tree.get_children())
        self._hits = list(hits)
        self._by_iid = {}
        if error:
            self.summary_label.configure(text=f"search failed: {error}")
            self.status(f"Search failed: {error}")
            return
        groups: dict[str, list[str]] = {}
        for i, hit in enumerate(self._hits):
            iid = f"h{i}"
            self._by_iid[iid] = hit
            groups.setdefault(hit.scope, []).append(iid)
        for scope, title in SCOPES:
            if scope == "all" or scope not in groups:
                continue
            total = totals.get(scope, len(groups[scope]))
            parent = tree.insert("", "end", tags=("group",),
                                 text=f"{title}  \u00b7  {total:,} matches",
                                 open=True)
            for iid in groups[scope]:
                hit = self._by_iid[iid]
                tree.insert(parent, "end", iid=iid, text=hit.label,
                            values=(hit.detail,), tags=(f"scope:{scope}",))
        elapsed = time.perf_counter() - self._started
        total = sum(totals.values())
        breakdown = "  \u00b7  ".join(f"{_SCOPE_TITLE.get(s, s)} {n:,}"
                                     for s, n in totals.items() if s != "areas" and n)
        self.summary_label.configure(
            text=f"{total:,} matches \u00b7 {len(self._hits):,} shown \u00b7 {elapsed:.2f} s"
                 + (f"   [{breakdown}]" if breakdown else ""))
        self.status(f"{total:,} search matches for \u201c{self.entry.get_value().strip()}\u201d")
        if self._hits:
            first = tree.get_children()
            if first:
                children = tree.get_children(first[0])
                if children:
                    tree.selection_set(children[0])

    # ------------------------------------------------------------------
    def _selected_hit(self) -> Hit | None:
        sel = self.tree.selection()
        if not sel:
            return None
        return self._by_iid.get(sel[0])

    def _open_selected(self) -> None:
        hit = self._selected_hit()
        if hit is None:
            self.status("Select a search result first")
            return
        app = self.app
        scope = hit.scope
        if scope == "areas":
            app.show_section("maps", query=hit.payload.get("area", ""))
        elif scope == "textures":
            app.show_section("textures", query=hit.payload.get("name", ""))
        elif scope == "models":
            app.show_section("models", query=hit.payload.get("name", ""))
        elif scope == "layouts":
            app.show_section("layouts", query=hit.payload.get("stem", ""))
        elif scope == "scripts":
            app.show_section("scripts", query=hit.payload.get("area", ""))
        elif scope == "tables":
            app.show_section("tables", query=hit.payload.get("name", ""))
        elif scope == "audio":
            app.show_section("audio", query=hit.payload.get("name", ""))
        elif scope == "code":
            app.show_section("code", query=hit.payload.get("addr", ""))
        elif scope == "dialogues":
            app.show_section("dialogues", query=hit.payload.get("query", ""))
        self.status(f"{hit.label}  \u00b7  opened in {_SCOPE_TITLE.get(scope, scope)}")
