"""DQXI Explorer - visual dark theme definitions and ttk styling."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------------------
# Palette (dark, high-contrast, DQ-flavoured gold accent)
# ---------------------------------------------------------------------------
BG = "#111318"
BG_PANEL = "#171a21"
BG_RAISED = "#1e222b"
BG_INPUT = "#0d0f14"
BG_HOVER = "#242a35"
BG_SELECT = "#2e3648"
BORDER = "#2a2f3a"
BORDER_LIGHT = "#3a4150"

TEXT = "#e6e8ee"
TEXT_DIM = "#9aa2b1"
TEXT_FAINT = "#6b7383"
ACCENT = "#e8b84b"       # gold
ACCENT_DIM = "#8a6d2b"
ACCENT_TEXT = "#16181d"
INFO = "#6db3f2"
WARN = "#e8a33d"
ERR = "#e86a5b"
OK = "#5ec98a"
JP_TEXT = "#9fc7ff"      # colour used for Japanese source text
EN_TEXT = "#e6e8ee"

# canvas / 3d colours
GRID = "#22262f"
WIRE = "#8fa3c8"
OUTLINE = "#4a5468"

FONT_FAMILY = "Segoe UI"
MONO_FAMILY = "Consolas"

F_TINY = (FONT_FAMILY, 8)
F_SMALL = (FONT_FAMILY, 9)
F_BASE = (FONT_FAMILY, 10)
F_BOLD = (FONT_FAMILY, 10, "bold")
F_H2 = (FONT_FAMILY, 11, "bold")
F_H1 = (FONT_FAMILY, 13, "bold")
F_TITLE = (FONT_FAMILY, 17, "bold")
F_MONO = (MONO_FAMILY, 10)
F_MONO_SMALL = (MONO_FAMILY, 9)

_JP_CANDIDATES = ("Yu Gothic UI", "Meiryo UI", "Meiryo", "MS Gothic", "Noto Sans JP")


def jp_font(size: int = 10, bold: bool = False) -> tuple:
    """Best available Japanese-capable font family."""
    try:
        from tkinter import font as tkfont

        families = set(tkfont.families())
        for cand in _JP_CANDIDATES:
            if cand in families:
                return (cand, size, "bold") if bold else (cand, size)
    except Exception:
        pass
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


def apply_theme(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=BG)

    style.configure(".", background=BG, foreground=TEXT, font=F_BASE,
                    bordercolor=BORDER, darkcolor=BG_PANEL, lightcolor=BG_PANEL)
    style.configure("TFrame", background=BG)
    style.configure("Panel.TFrame", background=BG_PANEL)
    style.configure("Raised.TFrame", background=BG_RAISED)
    style.configure("Card.TFrame", background=BG_RAISED, relief="flat")
    style.configure("TLabel", background=BG, foreground=TEXT, font=F_BASE)
    style.configure("Panel.TLabel", background=BG_PANEL, foreground=TEXT)
    style.configure("Card.TLabel", background=BG_RAISED, foreground=TEXT)
    style.configure("CardDim.TLabel", background=BG_RAISED, foreground=TEXT_DIM, font=F_SMALL)
    style.configure("Dim.TLabel", background=BG, foreground=TEXT_DIM, font=F_SMALL)
    style.configure("PanelDim.TLabel", background=BG_PANEL, foreground=TEXT_DIM, font=F_SMALL)
    style.configure("Faint.TLabel", background=BG_PANEL, foreground=TEXT_FAINT, font=F_TINY)
    style.configure("H1.TLabel", background=BG, foreground=TEXT, font=F_H1)
    style.configure("H2.TLabel", background=BG_PANEL, foreground=TEXT, font=F_H2)
    style.configure("Title.TLabel", background=BG_PANEL, foreground=ACCENT, font=F_TITLE)
    style.configure("Mono.TLabel", background=BG_PANEL, foreground=TEXT, font=F_MONO)
    style.configure("Accent.TLabel", background=BG_PANEL, foreground=ACCENT, font=F_BOLD)
    style.configure("Jp.TLabel", background=BG_PANEL, foreground=JP_TEXT, font=jp_font(10))
    style.configure("JpBig.TLabel", background=BG_PANEL, foreground=JP_TEXT, font=jp_font(11, True))

    # Buttons ---------------------------------------------------------------
    style.configure("TButton", background=BG_RAISED, foreground=TEXT, font=F_SMALL,
                    borderwidth=1, focusthickness=0, padding=(10, 5), relief="flat")
    style.map("TButton",
              background=[("active", BG_HOVER), ("pressed", BG_SELECT), ("disabled", BG_PANEL)],
              foreground=[("disabled", TEXT_FAINT)])
    style.configure("Accent.TButton", background=ACCENT_DIM, foreground="#f4e5c0")
    style.map("Accent.TButton", background=[("active", ACCENT), ("pressed", ACCENT_DIM)],
              foreground=[("active", ACCENT_TEXT)])
    style.configure("Tool.TButton", padding=(7, 3), background=BG_RAISED, font=F_SMALL)
    style.configure("Nav.TButton", anchor="w", padding=(14, 9), font=F_BASE,
                    background=BG_PANEL, foreground=TEXT_DIM, relief="flat", borderwidth=0)
    style.map("Nav.TButton",
              background=[("active", BG_HOVER)],
              foreground=[("active", TEXT)])
    style.configure("NavSel.TButton", anchor="w", padding=(14, 9), font=F_BOLD,
                    background=BG_SELECT, foreground=ACCENT, relief="flat", borderwidth=0)
    style.map("NavSel.TButton",
              background=[("active", BG_SELECT)],
              foreground=[("active", ACCENT)])

    # Entries / combo -------------------------------------------------------
    style.configure("TEntry", fieldbackground=BG_INPUT, foreground=TEXT, insertcolor=ACCENT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, padding=5)
    style.map("TEntry", bordercolor=[("focus", ACCENT_DIM)])
    style.configure("TCombobox", fieldbackground=BG_INPUT, background=BG_RAISED,
                    foreground=TEXT, arrowcolor=TEXT_DIM, bordercolor=BORDER, padding=4)
    style.map("TCombobox",
              fieldbackground=[("readonly", BG_INPUT)],
              foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background", BG_RAISED)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_DIM)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.font", F_SMALL)

    # Treeview --------------------------------------------------------------
    style.configure("Treeview", background=BG_PANEL, fieldbackground=BG_PANEL,
                    foreground=TEXT, rowheight=22, font=F_SMALL, bordercolor=BORDER,
                    lightcolor=BORDER, darkcolor=BORDER)
    style.map("Treeview",
              background=[("selected", BG_SELECT)],
              foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", background=BG_RAISED, foreground=TEXT_DIM,
                    font=F_SMALL, relief="flat", padding=(6, 4))
    style.map("Treeview.Heading", background=[("active", BG_HOVER)])

    # Scrollbars ------------------------------------------------------------
    style.configure("Vertical.TScrollbar", background=BG_RAISED, troughcolor=BG_PANEL,
                    bordercolor=BG_PANEL, arrowcolor=TEXT_DIM, relief="flat", width=12)
    style.configure("Horizontal.TScrollbar", background=BG_RAISED, troughcolor=BG_PANEL,
                    bordercolor=BG_PANEL, arrowcolor=TEXT_DIM, relief="flat")
    style.map("Vertical.TScrollbar", background=[("active", BG_HOVER)])
    style.map("Horizontal.TScrollbar", background=[("active", BG_HOVER)])

    # Notebook / check / scale ---------------------------------------------
    style.configure("TNotebook", background=BG_PANEL, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG_PANEL, foreground=TEXT_DIM,
                    padding=(12, 6), font=F_SMALL)
    style.map("TNotebook.Tab",
              background=[("selected", BG_RAISED)],
              foreground=[("selected", ACCENT)])
    style.configure("TCheckbutton", background=BG_PANEL, foreground=TEXT, font=F_SMALL)
    style.map("TCheckbutton", background=[("active", BG_PANEL)],
              foreground=[("active", TEXT)])
    style.configure("TRadiobutton", background=BG_PANEL, foreground=TEXT, font=F_SMALL)
    style.map("TRadiobutton", background=[("active", BG_PANEL)])
    style.configure("TScale", background=BG_PANEL, troughcolor=BG_INPUT)
    style.configure("TProgressbar", background=ACCENT_DIM, troughcolor=BG_INPUT,
                    bordercolor=BG_PANEL, lightcolor=ACCENT_DIM, darkcolor=ACCENT_DIM)
    style.configure("TSeparator", background=BORDER)

    # Progress + status bar -------------------------------------------------
    style.configure("Status.TFrame", background=BG_RAISED)
    style.configure("Status.TLabel", background=BG_RAISED, foreground=TEXT_DIM, font=F_SMALL)
    style.configure("StatusAccent.TLabel", background=BG_RAISED, foreground=ACCENT, font=F_SMALL)

    return style


# ---------------------------------------------------------------------------
# Syntax colours
# ---------------------------------------------------------------------------
SYN = {
    "comment": "#6f7f95",
    "keyword": "#c792ea",
    "type": "#82aaff",
    "string": "#c3e88d",
    "number": "#f78c6c",
    "addr": "#e8b84b",
    "label": "#ffcb6b",
    "func": "#82aaff",
    "reg": "#89ddff",
    "instr": "#c792ea",
    "punctuation": "#8892a6",
    "key": "#9cc4ff",
    "value": "#c3e88d",
    "sel": "#4a5468",
    "find": "#7a5c15",
}
