"""Emulator harness for the DQ XI (3DS) decompilation project.

This package is a thin wrapper.  The actual harness -- ``az.py`` (portable Azahar control,
input movies, memory/screenshots, saves, crash detection) and ``azctl.py`` (step-by-step
session) -- is the user's, in ``..\\3DS_Translate\\emutest``, and is imported
unchanged.  See ``tools/emu/extras.py`` for what this project adds (mod install, title-screen
evidence, framebuffer statistics, the boot verdict) and for the data-root layout.

    from tools.emu import make_emu
    with make_emu("build/DQXI.3ds") as emu:
        emu.wait_game(30)
        emu.shot("out.png")

Command line:  ``python -m tools.emu --help``
"""
from .extras import (  # noqa: F401
    DATA_ROOT,
    DEFAULT_ROM,
    EmuError,
    HARNESS,
    MODS,
    RUNS,
    SAVES,
    install_mod,
    load,
    make_emu,
    mod_installed,
    new_movie,
    resolve_mod,
)

__all__ = [
    "DATA_ROOT", "DEFAULT_ROM", "EmuError", "HARNESS", "MODS", "RUNS", "SAVES",
    "install_mod", "load", "make_emu", "mod_installed", "new_movie", "resolve_mod",
]
