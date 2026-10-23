"""DQXI Explorer - main application window.

A read-only, game-editor-flavoured desktop browser over every extracted
Dragon Quest XI (3DS) asset: textures, models, UI layouts, scripts, tables,
audio, decompiled code, dialogues and map dossiers.
"""

from __future__ import annotations

import json
import os
import queue
import tkinter as tk
from tkinter import ttk

from . import theme, utils
from .data.areas import AreaIndex
from .data.audio import AudioIndex
from .data.code import CodeIndex
from .data.dialogues import DialogueDB
from .data.layouts import LayoutIndex
from .data.models import ModelIndex
from .data.scripts import ScriptIndex
from .data.tables import TableIndex
from .data.textures import TextureIndex
from .ui.panels import BY_KEY, PANELS
from .ui.widgets import dim, search_entry

SETTINGS_PATH = utils.APP_DIR / "settings.json"
DEFAULT_GEOMETRY = "1500x940"


class App(tk.Tk):
    """Main window: sidebar navigation, header search, status bar."""

    autostart_preload = os.environ.get("DQXI_VIEWER_NO_PRELOAD") != "1"

    def __init__(self) -> None:
        super().__init__()
        self.title("DQXI Explorer \u2014 Dragon Quest XI (3DS) project browser")
        self.configure(bg=theme.BG)
        self.minsize(1180, 720)
        self._restore_geometry()
        theme.apply_theme(self)
        self._apply_icon()

        # -- data layer (all lazy, all read-only) ---------------------------
        self.textures = TextureIndex()
        self.models = ModelIndex()
        self.layouts = LayoutIndex()
        self.scripts = ScriptIndex()
        self.tables = TableIndex()
        self.audio = AudioIndex()
        self.code = CodeIndex()
        self.dialogues = DialogueDB()
        self.areas = AreaIndex()

        # -- ui state --------------------------------------------------------
        self._panels: dict[str, ttk.Frame] = {}
        self._nav_buttons: dict[str, ttk.Button] = {}
        self._current = ""
        self._closing = False
        self._preload_queue: queue.Queue = queue.Queue()
        self._preload_steps: list[tuple[str, object]] = []
        self.bridge = utils.UiBridge(self)     # thread-safe callbacks into Tk

        self._build_header()
        self._build_body()
        self._build_statusbar()

        # -- shortcuts -------------------------------------------------------
        self.bind("<Control-f>", lambda e: self._focus_search())
        self.bind("<F5>", lambda e: self.refresh_current())
        self.bind("<Escape>", lambda e: self._clear_search())
        for index, cls in enumerate(PANELS[:10]):
            digit = str(index + 1) if index < 9 else "0"
            self.bind(f"<Control-Key-{digit}>",
                      lambda _e, key=cls.key: self.show_section(key))
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.show_section("overview")
        if self.autostart_preload:
            self.after(250, self._start_preload)
        else:
            self._set_index_label("indexes load on demand")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        head = ttk.Frame(self, style="Status.TFrame", padding=(14, 8))
        head.grid(row=0, column=0, sticky="ew")
        head.columnconfigure(1, weight=1)

        brand = ttk.Frame(head, style="Status.TFrame")
        brand.grid(row=0, column=0, sticky="w", padx=(0, 16))
        ttk.Label(brand, text="DQXI Explorer", style="StatusAccent.TLabel",
                  font=theme.F_H2).pack(anchor="w")
        ttk.Label(brand, text="read-only project browser", style="Status.TLabel",
                  font=theme.F_TINY).pack(anchor="w")

        self.search_box = search_entry(head, width=54, placeholder="Search everything\u2026  (Ctrl+F)")
        self.search_box.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.search_box.bind("<Return>", lambda e: self._global_search())

        ttk.Button(head, text="Search", style="Tool.TButton",
                   command=self._global_search).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(head, text="Project folder", style="Tool.TButton",
                   command=lambda: utils.reveal_in_explorer(utils.PROJECT_ROOT)
                   ).grid(row=0, column=3)

    def _build_body(self) -> None:
        body = ttk.Frame(self, style="TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # -- sidebar ---------------------------------------------------------
        side = ttk.Frame(body, style="Panel.TFrame", width=220)
        side.grid(row=0, column=0, sticky="nsw")
        side.grid_propagate(False)
        side.columnconfigure(0, weight=1)
        side.rowconfigure(3, weight=1)          # flexible spacer between nav and footer

        logo = ttk.Frame(side, style="Panel.TFrame", padding=(16, 14, 12, 10))
        logo.grid(row=0, column=0, sticky="ew")
        ttk.Label(logo, text="DQXI", style="Title.TLabel").pack(anchor="w")
        dim(logo, "Dragon Quest XI \u00b7 3DS").pack(anchor="w")
        ttk.Separator(side, orient="horizontal").grid(row=1, column=0, sticky="ew")

        nav = ttk.Frame(side, style="Panel.TFrame")
        nav.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        nav.columnconfigure(0, weight=1)
        for cls in PANELS:
            btn = ttk.Button(nav, text=f"  {cls.icon}   {cls.title}", style="Nav.TButton",
                             command=lambda key=cls.key: self.show_section(key))
            btn.grid(row=len(self._nav_buttons), column=0, sticky="ew")
            self._nav_buttons[cls.key] = btn

        foot = ttk.Frame(side, style="Panel.TFrame", padding=(14, 8, 12, 12))
        foot.grid(row=4, column=0, sticky="sew")
        foot.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(foot, mode="determinate", maximum=100, value=0)
        self.progress.grid(row=0, column=0, sticky="ew")
        self.index_label = dim(foot, "starting\u2026")
        self.index_label.configure(wraplength=190, justify="left")
        self.index_label.grid(row=1, column=0, sticky="w", pady=(6, 0))

        # -- panel host -------------------------------------------------------
        self.content = ttk.Frame(body, style="TFrame")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, style="Status.TFrame", padding=(12, 5))
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(bar, text="Ready", style="Status.TLabel", anchor="w")
        self.status_label.grid(row=0, column=0, sticky="ew")
        self.section_label = ttk.Label(bar, text="", style="StatusAccent.TLabel", anchor="e")
        self.section_label.grid(row=0, column=1, sticky="e")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _ensure_panel(self, name: str) -> ttk.Frame | None:
        panel = self._panels.get(name)
        if panel is None:
            cls = BY_KEY.get(name)
            if cls is None:
                return None
            panel = cls(self.content, self)
            # unbound call: some panels expose an attribute named ``grid`` (thumbnail grid)
            ttk.Frame.grid(panel, row=0, column=0, sticky="nsew")
            self._panels[name] = panel
        return panel

    def show_section(self, name: str, **filters) -> None:
        """Raise a section, run first-show hooks and pass optional filters."""
        panel = self._ensure_panel(name)
        if panel is None:
            return
        previous = self._panels.get(self._current)
        if previous is not None and previous is not panel:
            hide = getattr(previous, "on_hide", None)
            if callable(hide):
                try:
                    hide()
                except Exception:
                    pass
        self._current = name
        panel.tkraise()
        try:
            panel.on_show()
        except Exception as exc:  # pragma: no cover - defensive
            self.set_status(f"{name} failed to open: {exc}")
        if filters:
            try:
                panel.set_filter(**filters)
            except TypeError as exc:
                self.set_status(f"{name} does not accept these filters: {exc}")
        self._select_nav(name)
        self._update_section_label(name)

    def _select_nav(self, name: str) -> None:
        for key, btn in self._nav_buttons.items():
            btn.configure(style="NavSel.TButton" if key == name else "Nav.TButton")

    def _update_section_label(self, name: str) -> None:
        cls = BY_KEY.get(name)
        title = cls.title if cls else name
        summary = ""
        panel = self._panels.get(name)
        if panel is not None:
            try:
                summary = panel.summary()
            except Exception:
                summary = ""
        self.section_label.configure(text=f"{title}  \u00b7  {summary}" if summary else title)

    def refresh_current(self) -> None:
        panel = self._panels.get(self._current)
        if panel is None:
            return
        refresh = getattr(panel, "_refresh", None)
        if callable(refresh):
            try:
                refresh()
            except Exception as exc:
                self.set_status(f"Refresh failed: {exc}")
            self._update_section_label(self._current)

    # ------------------------------------------------------------------
    # Header search + status
    # ------------------------------------------------------------------
    def _global_search(self) -> None:
        query = self.search_box.get_value().strip()  # type: ignore[attr-defined]
        self.show_section("search", query=query)

    def _focus_search(self) -> None:
        self.search_box.focus_set()
        try:
            self.search_box.select_range(0, "end")
        except tk.TclError:
            pass

    def _clear_search(self) -> None:
        self.search_box.set_value("")  # type: ignore[attr-defined]

    def set_status(self, text: str) -> None:
        try:
            self.status_label.configure(text=text)
        except tk.TclError:
            pass

    def post(self, fn, *args, **kwargs) -> None:
        """Run *fn* on the Tk main thread (safe to call from worker threads)."""
        self.bridge.post(fn, *args, **kwargs)

    def _set_index_label(self, text: str) -> None:
        try:
            self.index_label.configure(text=text)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------
    # Background index preload
    # ------------------------------------------------------------------
    def _start_preload(self) -> None:
        self._preload_steps = [
            ("textures", lambda: self.textures.ensure()),
            ("models", lambda: self.models.ensure()),
            ("layouts", lambda: self.layouts.ensure()),
            ("scripts", lambda: self.scripts.ensure()),
            ("tables", lambda: self.tables.ensure()),
            ("audio", lambda: self.audio.ensure()),
            ("decompiled code", lambda: self.code.ensure()),
            ("dialogues", lambda: self.dialogues.stats()),
            ("map areas", lambda: self.areas.ensure(self.textures, self.scripts,
                                                    self.audio, self.layouts,
                                                    self.dialogues, self.models)),
        ]
        self.progress.configure(value=0)
        self.set_status("Building indexes in the background\u2026")
        utils.start_thread(self._preload_worker, name="dqxi-preload")
        self.after(120, self._preload_poll)

    def _preload_worker(self) -> None:
        total = len(self._preload_steps)
        for i, (label, fn) in enumerate(self._preload_steps, start=1):
            self._preload_queue.put(("step", label, i, total))
            try:
                fn()
            except Exception as exc:
                self._preload_queue.put(("error", f"{label}: {exc}"))
        self._preload_queue.put(("done", "", total, total))

    def _preload_poll(self) -> None:
        done = False
        try:
            while True:
                kind, label, i, total = self._preload_queue.get_nowait()
                if kind == "step":
                    self.progress.configure(value=(i - 1) / max(1, total) * 100)
                    self._set_index_label(f"indexing {label}\u2026\n({i} / {total})")
                    self.set_status(f"Indexing {label}\u2026 ({i} / {total})")
                elif kind == "error":
                    self.set_status(f"Index warning \u2014 {label}")
                elif kind == "done":
                    done = True
        except queue.Empty:
            pass
        if done:
            self.progress.configure(value=100)
            self._set_index_label(self._index_summary())
            self.set_status("Ready")
            self._update_section_label(self._current)
            return
        if not self._closing:
            self.after(120, self._preload_poll)

    def _index_summary(self) -> str:
        bits = []
        for label, idx, attr in (("textures", self.textures, "items"),
                                 ("meshes", self.models, "items"),
                                 ("layouts", self.layouts, "items"),
                                 ("scripts", self.scripts, "items"),
                                 ("tables", self.tables, "items"),
                                 ("funcs", self.code, "functions")):
            if getattr(idx, "ready", False):
                bits.append(f"{utils.human_count(len(getattr(idx, attr)))} {label}")
        if self.dialogues.available():
            st = self.dialogues.stats()
            if st.sources:
                bits.append(f"{utils.human_count(st.sources)} dialogues")
        if self.areas.ready:
            bits.append(f"{utils.human_count(len(self.areas.areas))} areas")
        if not bits:
            return "indexes not built yet"
        lines = [" \u00b7 ".join(bits[:3]), " \u00b7 ".join(bits[3:])]
        return "\n".join(line for line in lines if line)

    # ------------------------------------------------------------------
    # Window plumbing
    # ------------------------------------------------------------------
    def _restore_geometry(self) -> None:
        geometry = ""
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            geometry = str(data.get("geometry") or "")
        except Exception:
            geometry = ""
        self.geometry(geometry or DEFAULT_GEOMETRY)

    def _apply_icon(self) -> None:
        try:
            from PIL import Image, ImageDraw, ImageTk

            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.rounded_rectangle((2, 2, size - 3, size - 3), radius=14,
                                   fill="#171a21", outline=theme.ACCENT, width=3)
            draw.polygon([(32, 13), (51, 32), (32, 51), (13, 32)],
                         outline=theme.ACCENT, width=3)
            draw.polygon([(32, 22), (42, 32), (32, 42), (22, 32)], fill=theme.ACCENT)
            self._icon = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._icon)
        except Exception:  # pragma: no cover - icon is cosmetic
            pass

    def on_close(self) -> None:
        self._closing = True
        try:
            SETTINGS_PATH.write_text(json.dumps({"geometry": self.geometry()}),
                                     encoding="utf-8")
        except Exception:
            pass
        for panel in list(self._panels.values()):
            hide = getattr(panel, "on_hide", None)
            if callable(hide):
                try:
                    hide()
                except Exception:
                    pass
        try:
            self.destroy()
        except tk.TclError:
            pass


def main() -> int:
    app = App()
    app.mainloop()
    return 0
