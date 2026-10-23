"""Overview / dashboard panel."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk

from ... import theme, utils
from ..widgets import Panel, button, dim


class OverviewPanel(Panel):
    key = "overview"
    title = "Overview"
    icon = "\u25a0"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._built = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        head = ttk.Frame(self, style="TFrame")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 4))
        ttk.Label(head, text="Dragon Quest XI (3DS) \u2014 Project Explorer",
                  style="Title.TLabel").pack(anchor="w")
        dim(head, "Read-only visual browser for every extracted asset, script, table and "
                  "decompiled function.").pack(anchor="w", pady=(2, 0))

        self.cards = ttk.Frame(self, style="TFrame")
        self.cards.grid(row=1, column=0, sticky="ew", padx=24, pady=18)

        self.footer = ttk.Frame(self, style="TFrame")
        self.footer.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 20))

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._build_cards()
        self._build_footer()

    def on_show(self) -> None:
        first = not self._shown_once
        super().on_show()
        if not first:
            # indexes may have finished building since the last visit
            self._build_cards()
            self._build_footer()

    def _card(self, parent, col: int, title: str, value: str, subtitle: str,
              command=None) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=(16, 12))
        card.grid(row=0, column=col, sticky="nsew", padx=(0, 12))
        parent.columnconfigure(col, weight=1)
        ttk.Label(card, text=title.upper(), style="CardDim.TLabel").pack(anchor="w")
        value_label = ttk.Label(card, text=value, style="Card.TLabel",
                                font=(theme.FONT_FAMILY, 20, "bold"))
        value_label.pack(anchor="w", pady=(2, 0))
        ttk.Label(card, text=subtitle, style="CardDim.TLabel").pack(anchor="w")
        if command is not None:
            card.bind("<Button-1>", lambda e: command())
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e: command())
            card.configure(cursor="hand2")
            value_label.configure(foreground=theme.ACCENT)

    def _build_cards(self) -> None:
        for child in self.cards.winfo_children():
            child.destroy()
        app = self.app
        stats = [
            ("Textures", utils.human_count(len(app.textures.items)) if app.textures.ready else "\u2026",
             "PNG + metadata", lambda: app.show_section("textures")),
            ("Models", utils.human_count(len(app.models.items)) if app.models.ready else "\u2026",
             "OBJ / glTF meshes", lambda: app.show_section("models")),
            ("Layouts", utils.human_count(len(app.layouts.items)) if app.layouts.ready else "\u2026",
             "BFLYT / BFLAN JSON", lambda: app.show_section("layouts")),
            ("Scripts", utils.human_count(len(app.scripts.items)) if app.scripts.ready else "\u2026",
             "Squirrel disassembly", lambda: app.show_section("scripts")),
            ("Tables", utils.human_count(len(app.tables.items)) if app.tables.ready else "\u2026",
             "BXON parameter JSON", lambda: app.show_section("tables")),
        ]
        for i, (title, value, subtitle, cmd) in enumerate(stats):
            self._card(self.cards, i, title, value, subtitle, cmd)

    def _build_footer(self) -> None:
        for child in self.footer.winfo_children():
            child.destroy()
        app = self.app
        left = ttk.Frame(self.footer, style="TFrame")
        left.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Quick actions", style="H1.TLabel").pack(anchor="w")
        row = ttk.Frame(left, style="TFrame")
        row.pack(anchor="w", pady=(8, 16))
        button(row, "Browse textures", lambda: app.show_section("textures")).pack(side="left")
        button(row, "View 3D models", lambda: app.show_section("models")).pack(side="left", padx=6)
        button(row, "Preview UI layouts", lambda: app.show_section("layouts")).pack(side="left", padx=6)
        button(row, "Read dialogues", lambda: app.show_section("dialogues")).pack(side="left", padx=6)
        button(row, "Look at a map", lambda: app.show_section("maps")).pack(side="left", padx=6)

        ttk.Label(left, text="Project state", style="H1.TLabel").pack(anchor="w", pady=(10, 6))
        info = ttk.Frame(left, style="Card.TFrame", padding=14)
        info.pack(fill="x")
        rows = self._project_rows()
        for key, value in rows:
            line = ttk.Frame(info, style="Card.TFrame")
            line.pack(fill="x", pady=1)
            ttk.Label(line, text=key, style="CardDim.TLabel", width=24, anchor="w").pack(side="left")
            ttk.Label(line, text=value, style="Card.TLabel", anchor="w").pack(side="left")

        right = ttk.Frame(self.footer, style="TFrame")
        right.pack(side="left", fill="both", expand=True, padx=(28, 0))
        ttk.Label(right, text="Counts", style="H1.TLabel").pack(anchor="w")
        table = ttk.Frame(right, style="Card.TFrame", padding=14)
        table.pack(fill="x", pady=(6, 0))
        for key, value in self._count_rows():
            line = ttk.Frame(table, style="Card.TFrame")
            line.pack(fill="x", pady=1)
            ttk.Label(line, text=key, style="CardDim.TLabel", width=26, anchor="w").pack(side="left")
            ttk.Label(line, text=value, style="Card.TLabel").pack(side="left")

    def _project_rows(self) -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        meta = utils.ORIGINAL_DIR / "metadata.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text(encoding="utf-8"))
                for key in ("title_id", "product_code", "title", "region", "size_bytes"):
                    if key in data:
                        rows.append((key, str(data[key])))
            except Exception:
                pass
        hashes = utils.ORIGINAL_DIR / "hashes.sha256"
        rows.append(("baseline hashes", "present" if hashes.exists() else "missing"))
        build_code = utils.BUILD_DIR / "code.bin"
        rows.append(("built code.bin", utils.human_size(build_code.stat().st_size)
                     if build_code.exists() else "not built"))
        for label, path in (("romfs.bin", utils.ORIGINAL_DIR / "romfs.bin"),
                            ("DQXI.3ds (reference)", utils.REFERENCE_ROOT / "DQXI.3ds")):
            rows.append((label, utils.human_size(path.stat().st_size) if path.exists() else "absent"))
        rows.append(("dialogue database", "found" if utils.DIALOGUE_DB.exists() else "missing"))
        rows.append(("project root", str(utils.PROJECT_ROOT)))
        return rows

    def _count_rows(self) -> list[tuple[str, str]]:
        app = self.app
        out: list[tuple[str, str]] = []
        try:
            out.append(("texture packs", utils.human_count(len(app.textures.packs()))))
        except Exception:
            pass
        for label, index in (("models", app.models), ("layouts", app.layouts),
                             ("scripts", app.scripts), ("tables", app.tables)):
            try:
                index.ensure()
                out.append((label, utils.human_count(len(index.items))))
            except Exception:
                out.append((label, "\u2026"))
        try:
            app.audio.ensure()
            out.append(("audio streams", utils.human_count(len(app.audio.streams))))
            out.append(("sound archives", utils.human_count(len(app.audio.archives))))
        except Exception:
            pass
        try:
            app.code.ensure()
            out.append(("decompiled functions", utils.human_count(len(app.code.functions))))
        except Exception:
            pass
        try:
            st = app.dialogues.stats()
            out.append(("dialogue entries", utils.human_count(st.sources)))
            out.append(("PC text rows", utils.human_count(st.pc_rows)))
        except Exception:
            pass
        try:
            app.areas.ensure(app.textures, app.scripts, app.audio, app.layouts,
                             app.dialogues, app.models)
            out.append(("map areas", utils.human_count(len(app.areas.areas))))
        except Exception:
            pass
        return out
