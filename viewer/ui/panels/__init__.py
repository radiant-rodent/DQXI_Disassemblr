"""Navigable panels, listed in sidebar order."""

from __future__ import annotations

from .audio import AudioPanel
from .code import CodePanel
from .dialogues import DialoguesPanel
from .layouts import LayoutsPanel
from .maps import MapsPanel
from .models import ModelsPanel
from .overview import OverviewPanel
from .scripts import ScriptsPanel
from .search import SearchPanel
from .tables import TablesPanel
from .textures import TexturesPanel

PANELS = [
    OverviewPanel,
    SearchPanel,
    TexturesPanel,
    ModelsPanel,
    LayoutsPanel,
    ScriptsPanel,
    TablesPanel,
    AudioPanel,
    CodePanel,
    DialoguesPanel,
    MapsPanel,
]

BY_KEY = {panel.key: panel for panel in PANELS}

__all__ = [
    "PANELS",
    "BY_KEY",
    "AudioPanel",
    "CodePanel",
    "DialoguesPanel",
    "LayoutsPanel",
    "MapsPanel",
    "ModelsPanel",
    "OverviewPanel",
    "ScriptsPanel",
    "SearchPanel",
    "TablesPanel",
    "TexturesPanel",
]
