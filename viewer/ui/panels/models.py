"""3D model browser with a software-rendered viewport."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ... import theme, utils
from ...render import obj as obj_mod
from ...render.renderer3d import MeshViewer
from ..widgets import KVTable, Panel, TextViewer, button, dim, search_entry

WIRE_COLOR = theme.WIRE
CATALOG_PATH = utils.MODELS_DIR / "MODELS_CATALOG.md"


class ModelsPanel(Panel):
    key = "models"
    title = "Models"
    icon = "\u25c7"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._items: list = []
        self._mesh_cache: dict[str, object] = {}
        self._debounce = utils.debounced(self, 200, lambda: self._refresh())

        split = ttk.PanedWindow(self, orient="horizontal")
        split.grid(row=0, column=0, sticky="nsew")

        # -- left: model list ---------------------------------------------
        left = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(left, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(3, weight=1)

        ttk.Label(left, text="Model library", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=1, column=0, sticky="ew", pady=(6, 2))
        self.entry = search_entry(bar, width=18, placeholder="Search models\u2026")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())

        self.group_var = ttk.Combobox(left, state="readonly", values=["All categories"])
        self.group_var.current(0)
        self.group_var.grid(row=2, column=0, sticky="ew", pady=(0, 6))
        self.group_var.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        self.tree = ttk.Treeview(left, columns=("category", "size"), selectmode="browse")
        self.tree.heading("#0", text="Model")
        self.tree.heading("category", text="Category")
        self.tree.heading("size", text="OBJ")
        self.tree.column("#0", width=190)
        self.tree.column("category", width=110, stretch=False)
        self.tree.column("size", width=70, anchor="e", stretch=False)
        self.tree.tag_configure("odd", background=theme.BG_RAISED)
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=3, column=0, sticky="nsew")
        vbar.grid(row=3, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda e: self.viewer.reset())
        self.count_label = dim(left, "")
        self.count_label.grid(row=4, column=0, sticky="w", pady=(4, 0))

        # -- right: viewport / catalog ------------------------------------
        right = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(right, weight=3)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="No model selected", style="H2.TLabel")
        self.name_label.pack(side="left")
        self.stats_label = dim(head, "")
        self.stats_label.pack(side="left", padx=10)

        actions = ttk.Frame(right, style="Panel.TFrame", padding=(0, 6))
        actions.grid(row=1, column=0, sticky="ew")
        button(actions, "Reset view", lambda: self.viewer.reset()).pack(side="left")
        button(actions, "Fit", lambda: self.viewer.fit()).pack(side="left", padx=6)
        button(actions, "Reveal folder", self._reveal).pack(side="left")
        button(actions, "Copy path", self._copy_path).pack(side="left", padx=6)
        self.catalog_btn = button(actions, "Model catalog", self._show_catalog)
        self.catalog_btn.pack(side="right")

        self.nb = ttk.Notebook(right)
        self.nb.grid(row=2, column=0, sticky="nsew")

        self._build_viewport_tab()
        self._build_catalog_tab()

    # ------------------------------------------------------------------
    def _build_viewport_tab(self) -> None:
        tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(tab, text="Viewport")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(tab, bg=theme.BG_INPUT, highlightthickness=1,
                                highlightbackground=theme.BORDER)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.viewer = MeshViewer(self.canvas)

        controls = ttk.Frame(tab, style="Panel.TFrame")
        controls.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.wire_var = tk.BooleanVar(value=False)
        self.cull_var = tk.BooleanVar(value=False)
        self.flip_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="Wireframe", variable=self.wire_var,
                        command=self._apply_opts).pack(side="left")
        ttk.Checkbutton(controls, text="Backface cull", variable=self.cull_var,
                        command=self._apply_opts).pack(side="left", padx=8)
        ttk.Checkbutton(controls, text="Flip view Z", variable=self.flip_var,
                        command=self._apply_opts).pack(side="left", padx=8)

        self.meta = KVTable(tab, height=6, key_width=110)
        self.meta.grid(row=2, column=0, sticky="ew", pady=(6, 0))

        hint = dim(tab, "Drag: orbit  \u00b7  Right-drag: pan  \u00b7  Wheel: zoom  \u00b7  "
                        "Double-click: reset")
        hint.grid(row=3, column=0, sticky="w", pady=(4, 0))

    def _build_catalog_tab(self) -> None:
        tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(tab, text="Catalog")
        self.catalog_tab = tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        bar = ttk.Frame(tab, style="Panel.TFrame", padding=(0, 6))
        bar.grid(row=0, column=0, sticky="ew")
        self.catalog_info = dim(bar, "")
        self.catalog_info.pack(side="left")
        button(bar, "Reload", self._load_catalog).pack(side="right")
        button(bar, "Open file", lambda: utils.open_external(CATALOG_PATH)).pack(
            side="right", padx=6)

        self.catalog_view = TextViewer(tab, show_lines=False)
        self.catalog_view.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._refresh()
        self._load_catalog()

    def set_filter(self, query: str | None = None, category: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        if category is not None:
            values = list(self.group_var["values"])
            hit = next((v for v in values if v.startswith(category)), None) \
                if category else None
            self.group_var.set(hit or "All categories")
        self._refresh()
        # a jump from search / map dossiers should open the model immediately
        if query:
            needle = query.strip().lower()
            exact = next((m for m in self._items if m.name.lower() == needle), None)
            if exact is None and len(self._items) == 1:
                exact = self._items[0]
            if exact is not None:
                iid = str(exact.obj)
                self.tree.selection_set(iid)
                self.tree.see(iid)
                self._on_select()

    def summary(self) -> str:
        index = self.app.models
        if index.ready:
            cats = len(index.categories())
            return f"{len(self._items):,} models \u00b7 {cats} categories"
        return f"{len(self._items):,} models"

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        index = self.app.models.ensure()
        values = ["All categories"] + [f"{name}  ({count})" for name, count in index.categories()]
        self.group_var.configure(values=values)
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        cat_sel = self.group_var.get()
        category = None
        if cat_sel and not cat_sel.startswith("All categories"):
            category = cat_sel.split("  (")[0]
        self._items = index.search(query, category)
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(self._items):
            self.tree.insert("", "end", iid=str(item.obj), text=item.name,
                             values=(item.category, utils.human_size(item.size_bytes)),
                             tags=("odd",) if i % 2 else ())
        total = len(index.items)
        suffix = "" if len(self._items) == total else f" of {total:,}"
        self.count_label.configure(text=f"{len(self._items):,}{suffix} models")
        self.status(f"{len(self._items):,} models")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        path = sel[0]
        item = next((m for m in self._items if str(m.obj) == path), None)
        if item is None:
            return
        self.name_label.configure(text=item.name)
        self.stats_label.configure(text=f"{item.category}  \u00b7  {item.rel_dir}")
        cached = self._mesh_cache.get(path)
        if cached is not None:
            self._apply_mesh(item, cached)
            return
        self.status(f"Parsing {item.name}\u2026")
        self.canvas.delete("all")
        self.canvas.create_text(max(10, self.canvas.winfo_width() // 2),
                                max(10, self.canvas.winfo_height() // 2),
                                text="Loading mesh\u2026", fill=theme.TEXT_FAINT,
                                font=theme.F_BASE)

        def work():
            try:
                mesh = obj_mod.load_obj(item.obj, item.mtl)
            except Exception as exc:
                mesh = exc
            self.app.post(self._mesh_loaded, item, mesh)

        utils.submit(work)

    def _mesh_loaded(self, item, mesh) -> None:
        if isinstance(mesh, Exception):
            self.status(f"Failed to load {item.name}: {mesh}")
            return
        if len(self._mesh_cache) > 24:
            self._mesh_cache.clear()
        self._mesh_cache[str(item.obj)] = mesh
        if self.tree.selection() and self.tree.selection()[0] == str(item.obj):
            self._apply_mesh(item, mesh)

    def _apply_mesh(self, item, mesh) -> None:
        self.viewer.set_mesh(mesh)
        self._apply_opts()
        self.viewer.draw()
        s = mesh.stats()
        dims = s["dims"]
        self.stats_label.configure(
            text=f"{item.category}  \u00b7  {s['parts']:,} mesh{'es' if s['parts'] != 1 else ''}"
                 f"  \u00b7  {s['triangles']:,} tris  \u00b7  {s['vertices']:,} verts")
        rows = [
            ("category", item.category),
            ("meshes / objects", f"{s['parts']:,}"),
            ("triangles", f"{s['triangles']:,}"),
            ("vertices", f"{s['vertices']:,}"),
            ("dimensions", f"{dims[0]:.3f} x {dims[1]:.3f} x {dims[2]:.3f}"),
            ("material", mesh.material),
            ("sidecar files", ", ".join(item.sidecars) or "-"),
            ("directory", item.rel_dir),
        ]
        if self.viewer.last_total and self.viewer.last_drawn < self.viewer.last_total:
            rows.insert(5, ("drawn", f"{self.viewer.last_drawn:,} of "
                                     f"{self.viewer.last_total:,} triangles (nearest first)"))
        if s["nonfinite"] or s["outliers"]:
            rows.append(("data repair", f"{s['nonfinite']:,} non-finite and "
                                        f"{s['outliers']:,} stray vertices ignored "
                                        f"when framing"))
        self.meta.set_rows(rows)
        self.status(f"{item.name}  \u00b7  {s['triangles']:,} triangles  \u00b7  "
                    f"{s['vertices']:,} vertices")

    def _apply_opts(self) -> None:
        self.viewer.wireframe = bool(self.wire_var.get())
        self.viewer.cull = bool(self.cull_var.get())
        self.viewer.flip_z = bool(self.flip_var.get())
        self.viewer.draw()

    # ------------------------------------------------------------------
    def _load_catalog(self) -> None:
        if not CATALOG_PATH.exists():
            self.catalog_info.configure(text="MODELS_CATALOG.md not found")
            self.catalog_view.show("", "text")
            return
        try:
            text = utils.safe_read_text(CATALOG_PATH, max_bytes=4 * 1024 * 1024)
        except Exception as exc:
            self.catalog_info.configure(text=f"failed to read catalog: {exc}")
            return
        lines = text.count("\n") + 1
        count = self.app.models.ensure()
        self.catalog_info.configure(
            text=f"{CATALOG_PATH.name}  \u00b7  {lines:,} lines  \u00b7  "
                 f"{utils.human_size(CATALOG_PATH.stat().st_size)}  \u00b7  "
                 f"{len(count.items):,} models indexed")
        self.catalog_view.show(text, "text", header=f"# {CATALOG_PATH}")

    def _show_catalog(self) -> None:
        self._load_catalog()
        self.nb.select(self.catalog_tab)

    def _current(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return next((m for m in self._items if str(m.obj) == sel[0]), None)

    def _reveal(self) -> None:
        item = self._current()
        if item is not None:
            utils.reveal_in_explorer(item.directory)

    def _copy_path(self) -> None:
        item = self._current()
        if item is not None:
            utils.copy_to_clipboard(self, str(item.obj))
            self.status("Path copied")
