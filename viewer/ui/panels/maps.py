"""Map / area browser: one dossier per game area with every related asset."""

from __future__ import annotations

from tkinter import ttk

from ... import theme, utils
from ...data import areas as areas_mod
from ..widgets import KVTable, Panel, ThumbGrid, button, dim, search_entry


class MapsPanel(Panel):
    key = "maps"
    title = "Maps"
    icon = "\u25f1"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._current_area: str | None = None
        self._dossier = None
        self._debounce = utils.debounced(self, 200, lambda: self._refresh())

        split = ttk.PanedWindow(self, orient="horizontal")
        split.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(left, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Game areas", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=1, column=0, sticky="ew", pady=6)
        self.entry = search_entry(bar, width=18, placeholder="Search areas\u2026")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())

        self.tree = ttk.Treeview(left, selectmode="browse")
        self.tree.heading("#0", text="Area")
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        vbar.grid(row=2, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.count_label = dim(left, "")
        self.count_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

        right = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(right, weight=3)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="Select an area", style="H2.TLabel")
        self.name_label.pack(anchor="w")
        self.info_label = dim(head, "")
        self.info_label.pack(anchor="w")

        actions = ttk.Frame(right, style="Panel.TFrame", padding=(0, 6))
        actions.grid(row=1, column=0, sticky="ew")
        button(actions, "Show in Textures", lambda: self._jump("textures")).pack(side="left")
        button(actions, "Show in Models", lambda: self._jump("models")).pack(side="left", padx=6)
        button(actions, "Show in Scripts", lambda: self._jump("scripts")).pack(side="left")
        button(actions, "Show in Dialogues", lambda: self._jump("dialogues")).pack(side="left", padx=6)
        button(actions, "Show in Audio", lambda: self._jump("audio")).pack(side="left")

        self.nb = ttk.Notebook(right)
        self.nb.grid(row=2, column=0, sticky="nsew")

        tex_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(tex_tab, text="Textures")
        tex_tab.columnconfigure(0, weight=1)
        tex_tab.rowconfigure(1, weight=1)
        self.tex_hint = dim(tex_tab, "")
        self.tex_hint.grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.tex_grid = ThumbGrid(tex_tab, thumb_size=118, on_select=self._tex_selected,
                                  on_activate=self._tex_open, label_lines=1)
        self.tex_grid.grid(row=1, column=0, sticky="nsew")

        script_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(script_tab, text="Scripts")
        script_tab.columnconfigure(0, weight=1)
        script_tab.rowconfigure(0, weight=1)
        self.script_tree = ttk.Treeview(script_tab, selectmode="browse")
        self.script_tree.heading("#0", text="Script pack")
        self.script_tree.grid(row=0, column=0, sticky="nsew")
        vs = ttk.Scrollbar(script_tab, orient="vertical", command=self.script_tree.yview)
        self.script_tree.configure(yscrollcommand=vs.set)
        vs.grid(row=0, column=1, sticky="ns")
        self.script_tree.bind("<Double-1>", lambda e: self._jump("scripts"))

        model_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(model_tab, text="3D models")
        model_tab.columnconfigure(0, weight=1)
        model_tab.rowconfigure(1, weight=1)
        self.model_hint = dim(model_tab, "")
        self.model_hint.grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.model_tree = ttk.Treeview(model_tab, columns=("category", "size"),
                                       selectmode="browse")
        self.model_tree.heading("#0", text="Model")
        self.model_tree.heading("category", text="Category")
        self.model_tree.heading("size", text="OBJ")
        self.model_tree.column("#0", width=280)
        self.model_tree.column("category", width=110, stretch=False)
        self.model_tree.column("size", width=80, anchor="e", stretch=False)
        self.model_tree.grid(row=1, column=0, sticky="nsew")
        vm = ttk.Scrollbar(model_tab, orient="vertical", command=self.model_tree.yview)
        self.model_tree.configure(yscrollcommand=vm.set)
        vm.grid(row=1, column=1, sticky="ns")
        self.model_tree.bind("<Double-1>", lambda e: self._jump("models"))

        dlg_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(dlg_tab, text="Dialogues")
        dlg_tab.columnconfigure(0, weight=1)
        dlg_tab.rowconfigure(1, weight=1)
        self.dlg_label = dim(dlg_tab, "")
        self.dlg_label.grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.dlg_tree = ttk.Treeview(dlg_tab, columns=("entries",), selectmode="browse")
        self.dlg_tree.heading("#0", text="ROM file")
        self.dlg_tree.heading("entries", text="Text entries")
        self.dlg_tree.column("#0", width=320)
        self.dlg_tree.column("entries", width=100, anchor="e", stretch=False)
        vd = ttk.Scrollbar(dlg_tab, orient="vertical", command=self.dlg_tree.yview)
        self.dlg_tree.configure(yscrollcommand=vd.set)
        self.dlg_tree.grid(row=1, column=0, sticky="nsew")
        vd.grid(row=1, column=1, sticky="ns")
        self.dlg_tree.bind("<Double-1>", lambda e: self._jump("dialogues"))

        level_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(level_tab, text="Level packs")
        level_tab.columnconfigure(0, weight=1)
        level_tab.rowconfigure(1, weight=1)
        self.level_label = dim(level_tab, "")
        self.level_label.grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.level_tree = ttk.Treeview(level_tab, columns=("size", "kind"), selectmode="browse")
        self.level_tree.heading("#0", text="Pack")
        self.level_tree.heading("size", text="Size")
        self.level_tree.heading("kind", text="Category")
        self.level_tree.column("#0", width=260)
        self.level_tree.column("size", width=100, anchor="e", stretch=False)
        self.level_tree.column("kind", width=120, stretch=False)
        vl = ttk.Scrollbar(level_tab, orient="vertical", command=self.level_tree.yview)
        self.level_tree.configure(yscrollcommand=vl.set)
        self.level_tree.grid(row=1, column=0, sticky="nsew")
        vl.grid(row=1, column=1, sticky="ns")

        audio_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(audio_tab, text="Audio")
        audio_tab.columnconfigure(0, weight=1)
        audio_tab.rowconfigure(0, weight=1)
        self.audio_tree = ttk.Treeview(audio_tab, selectmode="browse")
        self.audio_tree.heading("#0", text="Stream")
        self.audio_tree.grid(row=0, column=0, sticky="nsew")
        va = ttk.Scrollbar(audio_tab, orient="vertical", command=self.audio_tree.yview)
        self.audio_tree.configure(yscrollcommand=va.set)
        va.grid(row=0, column=1, sticky="ns")
        self.audio_tree.bind("<Double-1>", lambda e: self._jump("audio"))

        layout_tab = ttk.Frame(self.nb, style="Panel.TFrame")
        self.nb.add(layout_tab, text="UI packs")
        layout_tab.columnconfigure(0, weight=1)
        layout_tab.rowconfigure(0, weight=1)
        self.layout_tree = ttk.Treeview(layout_tab, selectmode="browse")
        self.layout_tree.heading("#0", text="Layout pack")
        self.layout_tree.grid(row=0, column=0, sticky="nsew")
        vl2 = ttk.Scrollbar(layout_tab, orient="vertical", command=self.layout_tree.yview)
        self.layout_tree.configure(yscrollcommand=vl2.set)
        vl2.grid(row=0, column=1, sticky="ns")
        self.layout_tree.bind("<Double-1>", lambda e: self._jump("layouts"))

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._refresh()

    def set_filter(self, query: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        self._refresh()
        # auto-select single match
        children = self.tree.get_children()
        if len(children) == 1:
            area_children = self.tree.get_children(children[0])
            if len(area_children) == 1:
                self.tree.selection_set(area_children[0])
                self.tree.see(area_children[0])

    def summary(self) -> str:
        index = self.app.areas
        return f"{len(index.areas):,} areas" if index.ready else ""

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        index = self.app.areas
        index.ensure(self.app.textures, self.app.scripts, self.app.audio,
                     self.app.layouts, self.app.dialogues, self.app.models)
        query = self.entry.get_value().strip().lower()  # type: ignore[attr-defined]
        self.tree.delete(*self.tree.get_children())
        buckets: dict[str, list[str]] = {}
        for area in index.all_areas():
            if query and query not in area:
                continue
            letter = area[0].upper()
            buckets.setdefault(letter, []).append(area)
        shown = 0
        for letter in sorted(buckets):
            parent = self.tree.insert("", "end", text=f"{letter} \u2014 {len(buckets[letter])} areas",
                                      open=query != "" or len(buckets) == 1)
            for area in buckets[letter]:
                dossier = index.dossier(area)
                self.tree.insert(parent, "end", iid=area, text=area,
                                 values=(f"{dossier.asset_count} assets",))
                shown += 1
        self.count_label.configure(text=f"{shown:,} areas")
        self.status(f"{shown:,} map areas")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        area = sel[0]
        if not area or area.startswith("\u2014") or area[0].isupper() and "areas" in area:
            return
        self._current_area = area
        index = self.app.areas
        dossier = index.dossier(area)
        index.refresh_dialogues(self.app.dialogues, dossier)
        self._dossier = dossier
        self.name_label.configure(text=area)
        self.info_label.configure(
            text=f"{len(dossier.textures)} texture packs  \u00b7  "
                 f"{len(dossier.models)} 3D models  \u00b7  "
                 f"{len(dossier.scripts)} script packs  \u00b7  "
                 f"{len(dossier.audio)} audio streams"
                 f"  \u00b7  {dossier.dialogue_total:,} text entries  \u00b7  "
                 f"{len(dossier.level3d) + len(dossier.level2d)} level packs")
        self._fill_textures(dossier)
        self._fill_models(dossier)
        self._fill_scripts(dossier)
        self._fill_dialogues(dossier)
        self._fill_levels(dossier)
        self._fill_audio(dossier)
        self._fill_layouts(dossier)
        self.status(f"{area}  \u00b7  {dossier.asset_count} assets  \u00b7  "
                    f"{dossier.dialogue_total:,} text entries")

    # ------------------------------------------------------------------
    def _fill_textures(self, dossier) -> None:
        tex_index = self.app.textures.ensure()
        items = []
        for pack in dossier.textures:
            items.extend(tex_index.search("", pack=pack))
            if len(items) >= 300:
                break
        for item in items:
            item.label = item.name
            item.sublabel = item.pack
        self.tex_hint.configure(
            text=f"{len(items)} texture items from packs: {', '.join(dossier.textures) or '-'}"
                 + ("  (first 300 shown)" if len(items) >= 300 else ""))
        self.tex_grid.set_items(items)

    def _fill_scripts(self, dossier) -> None:
        self.script_tree.delete(*self.script_tree.get_children())
        for name in dossier.scripts:
            self.script_tree.insert("", "end", text=name)

    def _fill_models(self, dossier) -> None:
        self.model_tree.delete(*self.model_tree.get_children())
        index = self.app.models.ensure()
        found = [model for model in (index.get(name) for name in dossier.models)
                 if model is not None]
        for model in found:
            self.model_tree.insert("", "end", iid=model.name, text=model.name,
                                   values=(model.category, utils.human_size(model.size_bytes)))
        if found:
            self.model_hint.configure(
                text=f"{len(found)} extracted 3D scene mesh{'es' if len(found) != 1 else ''}"
                     f"  \u00b7  double-click to open in the model viewer")
        else:
            self.model_hint.configure(
                text="No extracted 3D model is named after this area")

    def _fill_dialogues(self, dossier) -> None:
        self.dlg_label.configure(
            text=f"{dossier.dialogue_total:,} text entries reference this area")
        self.dlg_tree.delete(*self.dlg_tree.get_children())
        for file, count in dossier.dialogue_files:
            self.dlg_tree.insert("", "end", iid=file, text=file, values=(f"{count:,}",))

    def _fill_levels(self, dossier) -> None:
        self.level_tree.delete(*self.level_tree.get_children())
        available = utils.LEVEL3D_DIR.exists() or utils.LEVEL2D_DIR.exists()
        self.level_label.configure(
            text=("Level geometry packs found in the reference workspace"
                  if available else
                  "Reference workspace not found - level packs unavailable"))
        for name, size in dossier.level3d:
            self.level_tree.insert("", "end", text=name, values=(utils.human_size(size), "level3d"))
        for name, size in dossier.level2d:
            self.level_tree.insert("", "end", text=name, values=(utils.human_size(size), "level2d"))

    def _fill_audio(self, dossier) -> None:
        self.audio_tree.delete(*self.audio_tree.get_children())
        for name in dossier.audio:
            self.audio_tree.insert("", "end", text=name)

    def _fill_layouts(self, dossier) -> None:
        self.layout_tree.delete(*self.layout_tree.get_children())
        for name in dossier.layouts:
            self.layout_tree.insert("", "end", text=name)

    # ------------------------------------------------------------------
    def _jump(self, section: str) -> None:
        area = self._current_area
        if not area:
            return
        if section == "textures":
            pack = self.tex_grid.items[self.tex_grid.selected].pack if (
                self.tex_grid.selected is not None and self.tex_grid.items) else None
            self.app.show_section("textures", query=area if not pack else "", pack=pack)
        elif section == "models":
            sel = self.model_tree.selection()
            name = sel[0] if sel else (self._dossier.models[0] if (
                self._dossier is not None and self._dossier.models) else "")
            if name:
                self.app.show_section("models", query=name)
            else:
                self.app.show_section("models")
        elif section == "scripts":
            self.app.show_section("scripts", query=area)
        elif section == "dialogues":
            sel = self.dlg_tree.selection()
            file_filter = sel[0] if sel else area
            self.app.show_section("dialogues", query="", file=file_filter)
        elif section == "audio":
            self.app.show_section("audio", query=area)
        elif section == "layouts":
            self.app.show_section("layouts", query=area)

    def _tex_selected(self, item) -> None:
        self.status(f"{item.name}  \u00b7  {item.pack}")

    def _tex_open(self, item) -> None:
        self.app.show_section("textures", pack=item.pack)
