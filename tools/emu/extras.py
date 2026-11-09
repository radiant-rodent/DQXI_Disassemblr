"""This project's additions on top of the translation project's emulator harness.

The harness itself (``az.py``, ``azctl.py``, ``setup_azahar.py``) lives in
``..\\3DS_Translate\\emutest`` and is imported unchanged; there is exactly one
copy of it on this machine.  ``az.py`` takes its paths from the environment, so this module:

  * points ``DQ11_EMUTEST`` at **this project's** data root (``third_party/emutest``) and
    ``DQ11_ROM`` at ``build/DQXI.3ds`` *before* importing it, so our runs never read or write
    the translation project's ``_emutest/`` config, saves or logs;
  * puts the harness directory on ``sys.path`` so plain ``import az`` works.

What is added here (everything else comes from the user's harness):

  * ``install_mod`` / ``resolve_mod`` / ``mod_installed`` -- LayeredFS mods via
    ``<data root>/azahar/user/load/mods/<TitleID>/{romfs,exefs/code.bin}``;
  * ``screen_stats`` -- cheap framebuffer statistics (liveness + title-background heuristic);
  * ``find_utf16_*`` / ``title_evidence`` -- UTF-16LE guest-RAM scans and the title-screen
    proof used by ``boot`` (live pane copies, not merely loaded resource text);
  * ``setup_main`` -- one-time data-root setup that still runs the user's ``setup_azahar.py``;
  * ``ctl_main`` -- the step-by-step session commands (``azctl``'s, plus memory and evidence).

The data root layout is exactly what ``az.py`` expects::

    third_party/emutest/azahar/       portable emulator (one copy, see setup_main)
    third_party/emutest/azahar/user/  its config, sdmc and logs
    third_party/emutest/saves/        game-save snapshots ("save states")
    third_party/emutest/runs/         screenshots, JSON reports, ctl session state
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))                 # <repo>/tools/emu
REPO = os.path.dirname(os.path.dirname(HERE))                     # <repo>

# Machine-local emulator data root.  ``az.py`` reads this variable at import time.
DATA_ROOT = os.path.abspath(os.environ.get("DQ11_EMUTEST")
                            or os.path.join(REPO, "third_party", "emutest"))
DEFAULT_ROM = os.path.join(REPO, "build", "DQXI.3ds")
# The one harness checkout; override only if the translation project moves.
HARNESS = os.path.abspath(os.environ.get("DQXI_EMUTEST_SRC")
                         or r"..\3DS_Translate\emutest")

os.environ["DQ11_EMUTEST"] = DATA_ROOT
os.environ.setdefault("DQ11_ROM", DEFAULT_ROM)

TITLE = 0x0004000000199200
TITLE_HEX = f"{TITLE:016X}"                       # 0004000000199200
AZAHAR = os.path.join(DATA_ROOT, "azahar")
EXE = os.path.join(AZAHAR, "azahar.exe")
USER = os.path.join(AZAHAR, "user")
INI = os.path.join(USER, "config", "qt-config.ini")
MODS = os.path.join(USER, "load", "mods", TITLE_HEX)
SAVES = os.path.join(DATA_ROOT, "saves")
RUNS = os.path.join(DATA_ROOT, "runs")
CTL_DIR = os.path.join(RUNS, "ctl")
SESSION = os.path.join(CTL_DIR, "session.json")


class EmuError(RuntimeError):
    """Harness error with a message a modder can act on."""


def printable(text: str) -> str:
    """Return ``text`` if the console can encode it, else its escaped form.

    The title-proof strings are Japanese and a Windows console usually runs a cp1252 code
    page, where printing them raises ``UnicodeEncodeError`` and would turn a successful boot
    into exit code 1.  The JSON report always keeps the real characters; this only protects
    the console line.
    """
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        text.encode(enc)
    except (UnicodeEncodeError, LookupError):
        return text.encode("unicode_escape").decode("ascii")
    return text


_LOADED = None


@contextlib.contextmanager
def _no_bytecode():
    """Never write ``__pycache__`` into the read-only harness checkout.

    Importing ``az``/``azctl``/``setup_azahar`` from ``..\\3DS_Translate`` would
    otherwise drop ``.pyc`` files into that project, which must stay untouched.
    """
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        yield
    finally:
        sys.dont_write_bytecode = old


def load():
    """Import and cache the user's ``az`` and ``azctl`` modules.

    Raises ``EmuError`` (not ImportError) when the harness checkout is missing, so the CLI can
    print one actionable line instead of a traceback.
    """
    global _LOADED
    if _LOADED is not None:
        return _LOADED
    if not os.path.isfile(os.path.join(HARNESS, "az.py")):
        raise EmuError(
            f"the emulator harness was not found at {HARNESS}.\n"
            "This project uses the translation project's harness unchanged; set "
            "DQXI_EMUTEST_SRC if it lives elsewhere.")
    if HARNESS not in sys.path:
        sys.path.insert(0, HARNESS)
    with _no_bytecode():
        import az        # noqa: E402  (path is set up immediately above)
        import azctl     # noqa: E402
    _fix_rpc_udp_reset()
    _LOADED = (az, azctl)
    return _LOADED


def _disable_udp_connreset(sock: socket.socket) -> None:
    # Python's socket.ioctl only knows three codes, so call WSAIoctl directly.
    import ctypes
    from ctypes import wintypes
    SIO_UDP_CONNRESET = 0x9800000C
    off = wintypes.BOOL(False)
    returned = wintypes.DWORD()
    ctypes.windll.ws2_32.WSAIoctl(ctypes.c_size_t(sock.fileno()), wintypes.DWORD(SIO_UDP_CONNRESET),
                                  ctypes.byref(off), ctypes.sizeof(off), None, 0,
                                  ctypes.byref(returned), None, None)


def _fix_rpc_udp_reset():
    """Stop Windows from failing RPC reads with WinError 10054.

    On Windows a UDP socket that once sent to a closed port (e.g. while Azahar was still
    starting) reports WSAECONNRESET on a later recv, even though the emulator is fine; test
    runs then die with "connection forcibly closed".  Disabling SIO_UDP_CONNRESET on the RPC
    socket turns that into a normal timeout/retry.  az.py imports ``AzaharRPC`` lazily, so
    importing it here first (from our Azahar copy) makes az.py use this patched class.
    """
    if sys.platform != "win32":
        return
    scripting = os.path.join(AZAHAR, "scripting")
    if not os.path.isfile(os.path.join(scripting, "AzaharRPC.py")):
        return
    if scripting not in sys.path:
        sys.path.insert(0, scripting)
    with _no_bytecode():
        import AzaharRPC  # noqa: E402
    cls = AzaharRPC.AzaharRPC
    if getattr(cls, "_dqxi_connreset_fixed", False):
        return
    original = cls.__init__

    def __init__(self, *a, **kw):
        original(self, *a, **kw)
        _disable_udp_connreset(self.socket)

    cls.__init__ = __init__
    cls._dqxi_connreset_fixed = True


# ---------------------------------------------------------------------------- LayeredFS mods
def resolve_mod(mod: str) -> str:
    """Return the directory that contains ``romfs/`` and/or ``exefs/`` for a mod.

    Accepted layouts (all of the ones this project produces/consumes):
      * ``out/luma``                     -> ``titles/<TitleID>/romfs``
      * ``out/luma/titles/<TitleID>``    -> ``romfs/`` + ``code.bin``
      * any directory with ``romfs/``    -> Azahar/Luma LayeredFS root
      * ``.../romfs`` itself             -> treated as RomFS payload only
      * ``mod/`` with ``romfs/`` + ``code/`` (project workspace; see mod/README.md)
    """
    p = os.path.abspath(mod)
    if not os.path.isdir(p):
        raise EmuError(f"mod folder not found: {p}")

    def title_dir(base):
        for cand in (os.path.join(base, "titles", TITLE_HEX),
                     os.path.join(base, "titles", TITLE_HEX.lower()),
                     os.path.join(base, TITLE_HEX),
                     os.path.join(base, TITLE_HEX.lower())):
            if os.path.isdir(cand):
                return cand
        return None

    if os.path.basename(p).lower() == "romfs":
        return os.path.dirname(p)
    if os.path.isdir(os.path.join(p, "romfs")) or os.path.isdir(os.path.join(p, "exefs")):
        return p
    t = title_dir(p)
    if t:
        return t
    # out/luma with a titles/ folder but not our title: be explicit rather than silently empty
    if os.path.isdir(os.path.join(p, "titles")):
        raise EmuError(f"{p}/titles does not contain title {TITLE_HEX}")
    raise EmuError(f"cannot find romfs/ or titles/{TITLE_HEX}/ in {p}")


def install_mod(mod: str | None) -> dict:
    """Install a Luma/Azahar mod folder into ``user/load/mods/<TitleID>/``.

    ``None`` (or an empty string) removes the previously installed mod, so a plain retail boot
    never inherits an old experiment.
    """
    if os.path.isdir(MODS):
        shutil.rmtree(MODS)
    if not mod:
        return {"installed": False, "files": 0, "bytes": 0, "dest": MODS}
    src = resolve_mod(mod)
    # Reject Luma patch files before copying anything: Azahar needs a decompressed code.bin,
    # and a half-installed mod would confuse the next boot.
    for name in ("code.ips", "code.bps"):
        if os.path.isfile(os.path.join(src, name)):
            raise EmuError(f"{os.path.join(src, name)} is a patch file; Azahar LayeredFS needs "
                           f"a decompressed exefs/code.bin (Luma applies {name} itself). "
                           f"Export/replace with a rebuilt code.bin instead.")
    os.makedirs(MODS, exist_ok=True)
    files = nbytes = 0
    for sub in ("romfs", "exefs"):
        d = os.path.join(src, sub)
        if os.path.isdir(d):
            shutil.copytree(d, os.path.join(MODS, sub))
            for root, _dirs, names in os.walk(d):
                for n in names:
                    files += 1
                    nbytes += os.path.getsize(os.path.join(root, n))
    # Luma keeps the executable next to romfs/ as code.bin; Azahar wants exefs/code.bin.
    code = os.path.join(src, "code.bin")
    if os.path.isfile(code):
        os.makedirs(os.path.join(MODS, "exefs"), exist_ok=True)
        shutil.copy2(code, os.path.join(MODS, "exefs", "code.bin"))
        files += 1
        nbytes += os.path.getsize(code)
    if files == 0:
        # An empty export (mod/ with no changes) must behave like retail.  Azahar's
        # LayeredFS does not like an empty overlay directory (observed: unmapped
        # WriteBlock at 0x0C1A8000), and there is nothing to overlay anyway.
        shutil.rmtree(MODS, ignore_errors=True)
        return {"installed": False, "files": 0, "bytes": 0, "dest": MODS,
                "source": src, "skipped": "empty mod (no files to overlay)"}
    return {"installed": True, "files": files, "bytes": nbytes, "dest": MODS, "source": src}


def mod_installed() -> bool:
    return os.path.isdir(MODS) and any(os.scandir(MODS))


# ------------------------------------------------------------------ evidence (mixin)
class _Evidence:
    """Title-screen proof and framebuffer statistics; mixed into the user's ``Azahar``.

    Only reads through ``self.rpc``, which both ``az.Azahar`` and ``azctl.Session`` provide.
    """

    # The retail title menu (ui/title.pack:title_text.bxon) contains these strings.  They are
    # loaded when the title UI starts; their UTF-16 copy in guest RAM is our "title screen"
    # proof.  On an Old 3DS the title UI data lives at 0x30000000 (the 0x08000000 linear-heap
    # alias holds neither the title layout nor its text table).  Japanese is used on purpose:
    # the rebuilt ROM is retail-identical, and a modded Japanese ROM still keeps these source
    # strings unless a translation replaces the table.
    TITLE_TEXTS = ("冒険の書をつくる", "ふっかつのじゅもん", "プレゼントコード入力",
                   "冒険をする", "中断した冒険をする")
    TITLE_SCAN = (0x30000000, 0x34000000)       # title/UI region on Old 3DS

    def screen_rgb(self):
        """(width, height, RGB888 bytes) of the framebuffer; no PNG encode round-trip."""
        try:
            return self.rpc.screenshot_raw()
        except Exception:
            return None

    def screen_stats(self):
        """Cheap liveness/visual statistics of the current framebuffer."""
        s = self.screen_rgb()
        if not s:
            return None
        w, h, data = s
        n = len(data) // 3
        step = max(1, n // 20000)
        rs = gs = bs = 0
        nonblack = 0
        samples = 0
        for i in range(0, n, step):
            j = i * 3
            r, g, b = data[j], data[j + 1], data[j + 2]
            rs += r
            gs += g
            bs += b
            if max(r, g, b) > 8:
                nonblack += 1
            samples += 1
        return {"width": w, "height": h,
                "mean": (rs + gs + bs) / (3 * samples),
                "r": rs / samples, "g": gs / samples, "b": bs / samples,
                "nonblack": nonblack / samples, "pixels_sampled": samples}

    def find_utf16_many(self, texts, start: int | None = None, end: int | None = None,
                        chunk: int = 0x8000) -> dict[str, int]:
        """One pass over guest RAM: ``{text: first_address}`` for every UTF-16LE match.

        Reads in 32 KiB RPC chunks (the protocol maximum) and keeps a small overlap so a
        string straddling two chunks is still found. Unmapped chunks are skipped; Azahar logs
        them as ``ReadBlock`` lines, which the crash detector deliberately ignores.
        """
        found: dict[str, int] = {}
        for text, addrs in self.find_utf16_all(texts, start, end, chunk).items():
            if addrs:
                found[text] = addrs[0]
        return found

    def find_utf16_all(self, texts, start: int | None = None, end: int | None = None,
                       chunk: int = 0x8000) -> dict[str, list[int]]:
        """Every UTF-16LE occurrence of each text in one pass (addresses in order)."""
        if start is None:
            start = self.TITLE_SCAN[0]
        if end is None:
            end = self.TITLE_SCAN[1]
        needles = {t: t.encode("utf-16-le") for t in texts}
        found: dict[str, list[int]] = {t: [] for t in needles}
        a = start
        prev = b""
        maxlen = max((len(n) for n in needles.values()), default=2)
        while a < end:
            size = min(chunk, end - a)
            try:
                data = self.rpc.read_memory(a, size)
            except Exception:
                data = None
            if data:
                buf = prev + data
                for t, needle in needles.items():
                    pos = 0
                    while True:
                        i = buf.find(needle, pos)
                        if i < 0:
                            break
                        addr = a - len(prev) + i
                        if not found[t] or found[t][-1] != addr:
                            found[t].append(addr)
                        pos = i + 1
                prev = buf[-(maxlen - 1):]
            else:
                prev = b""
            a += size
        return found

    def find_utf16(self, text: str, start: int | None = None, end: int | None = None,
                   chunk: int = 0x8000) -> int | None:
        """First guest address containing ``text`` as UTF-16LE, or None."""
        return self.find_utf16_many((text,), start, end, chunk).get(text)

    def title_evidence(self, need: int = 2, dynamic_from: int = 0x33000000) -> dict | None:
        """Title-menu proof: at least ``need`` menu strings copied into the *dynamic* UI heap.

        The title.pack text table sits in guest RAM from boot (around 0x31E/0x320), so merely
        finding the strings is not enough - the opening movie is still playing at that point.
        When the menu is actually built, its pane buffers receive extra copies at
        0x33D...-0x33E... (Old 3DS, this profile).  Requiring those copies proves the title
        layout is live, not just its resource file.  Returns ``{text: [addresses]}``.
        """
        found = self.find_utf16_all(self.TITLE_TEXTS)
        live = {t: [a for a in addrs if a >= dynamic_from] for t, addrs in found.items()}
        live = {t: addrs for t, addrs in live.items() if addrs}
        return live if len(live) >= need else None

    def title_screen_visual(self, stats: dict | None = None) -> bool:
        """Fallback for translations that replace the Japanese menu strings: the title menu is
        the only full-screen warm parchment (bright orange, bottom screen bordered) in the
        boot sequence.  Used by ``boot`` only after the automatic START press."""
        s = stats or self.screen_stats()
        return bool(s and s["nonblack"] > 0.80 and s["r"] > 150 and s["r"] - s["b"] > 70)


# ------------------------------------------------------------------------- emulator class
_CLASSES = None


def _classes():
    """Build (Emu, Session) on the user's classes; cached because import happens lazily."""
    global _CLASSES
    if _CLASSES is None:
        az, azctl = load()

        class Emu(_Evidence, az.Azahar):
            """The user's ``Azahar`` plus LayeredFS mod installation.

            Everything else (movie input, saves, RPC, crash detection) is inherited unchanged.
            """

            def __init__(self, rom: str = DEFAULT_ROM, mod: str | None = None, **kw):
                self.mod = mod
                super().__init__(os.path.abspath(rom), **kw)

            def start(self):
                if not os.path.isfile(EXE):
                    raise EmuError("portable Azahar is missing; run `python -m tools.emu setup`")
                if not os.path.isfile(self.rom):
                    raise EmuError(f"ROM not found: {self.rom}")
                if self.save not in (None, "__keep__") \
                        and not os.path.isdir(os.path.join(SAVES, self.save)):
                    raise EmuError(f"no game save named {self.save!r} in {SAVES}")
                # Azahar reads user/load/mods at process start, so install before launching.
                install_mod(self.mod)
                return super().start()

        class Session(_Evidence, azctl.Session):
            """The user's attach-to-running-session class plus the evidence helpers."""

        _CLASSES = (Emu, Session)
    return _CLASSES


def make_emu(rom: str | None = None, mod: str | None = None, **kw):
    """Create the project's ``Azahar`` (a drop-in replacement for ``az.Azahar``)."""
    Emu, _ = _classes()
    return Emu(rom or DEFAULT_ROM, mod=mod, **kw)


def new_movie():
    """A fresh input movie (``az.Movie``), for callers that do not import ``az`` themselves."""
    az, _ = load()
    return az.Movie()


# -------------------------------------------------------------------------------- setup
def _adopt_legacy_layout():
    """Move the pre-dedupe data folders into the layout ``az.py`` expects (no re-copy).

    Before this task the emulator lived in ``third_party/azahar`` with ``saves/`` and
    ``runs/`` *inside* it.  ``az.py`` wants ``<data root>/azahar`` + ``<data root>/saves`` +
    ``<data root>/runs``, so rename (same volume, instant) instead of restructuring paths in
    code - the harness code stays untouched.
    """
    legacy = os.path.join(REPO, "third_party", "azahar")
    if os.path.isdir(legacy) and not os.path.isdir(AZAHAR):
        os.makedirs(DATA_ROOT, exist_ok=True)
        os.rename(legacy, AZAHAR)
        print(f"moved {legacy} -> {AZAHAR} (layout for az.py)")
    for name in ("saves", "runs"):
        src = os.path.join(AZAHAR, name)
        dst = os.path.join(DATA_ROOT, name)
        if os.path.isdir(src) and not os.path.isdir(dst):
            os.rename(src, dst)
            print(f"moved {src} -> {dst}")


def _find_azahar_source(explicit: str | None) -> str | None:
    for cand in (explicit,
                 os.environ.get("DQXI_AZAHAR_SRC"),
                 os.path.join(REPO, "third_party", "azahar"),       # pre-dedupe location
                 r"..\3DS_Translate\_emutest\azahar",
                 r"C:\azahar"):
        if cand and os.path.isfile(os.path.join(cand, "azahar.exe")):
            return cand
    return None


def setup_main(argv=None) -> int:
    """One-time setup: adopt the existing emulator, then run the user's setup script.

    The profile logic (``az.SETTINGS``), the default ``qt-config.ini`` generation and the
    ``code_jp.bin`` extraction are the translation project's ``setup_azahar.py``.  This
    wrapper only fixes the data-root layout and, on a fresh machine, places a single copy of
    the emulator into it (never a second one next to the harness).
    """
    ap = argparse.ArgumentParser(prog="python -m tools.emu setup", description=__doc__)
    ap.add_argument("--source", help="Azahar install directory containing azahar.exe")
    ap.add_argument("--check", action="store_true", help="report state, change nothing")
    a = ap.parse_args(argv)

    if a.check:
        ok = os.path.isfile(EXE) and os.path.isfile(INI)
        print(f"data root: {DATA_ROOT}")
        print(f"emulator:  {EXE} {'(present)' if os.path.isfile(EXE) else '(MISSING)'}")
        print(f"config:    {INI} {'(present)' if os.path.isfile(INI) else '(MISSING)'}")
        print(f"saves:     {SAVES}")
        print(f"runs:      {RUNS}")
        return 0 if ok else 1

    _adopt_legacy_layout()
    os.makedirs(DATA_ROOT, exist_ok=True)
    os.makedirs(SAVES, exist_ok=True)
    os.makedirs(RUNS, exist_ok=True)
    os.makedirs(os.path.join(USER, "load", "mods"), exist_ok=True)

    if not os.path.isfile(EXE):
        src = _find_azahar_source(a.source)
        if not src:
            print("BLOCKED: no Azahar install found.", file=sys.stderr)
            print("Pass one with --source (a folder containing azahar.exe).", file=sys.stderr)
            return 2
        # One copy into our own data root.  user/ is excluded: another project's profile must
        # never leak into our runs (their setup_azahar.py would copy it verbatim).
        print(f"installing Azahar from {src} -> {AZAHAR} (once, ~320 MB)")
        shutil.copytree(src, AZAHAR, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("user", "saves", "runs", "__pycache__"))

    # Now the emulator exists, so the user's az.py can import AzaharRPC.  Both the import and
    # the run stay inside _no_bytecode(): setup_azahar imports dq11tool from the read-only
    # translation checkout to extract code_jp.bin.
    with _no_bytecode():
        load()
        import setup_azahar      # the translation project's script, used unchanged
        setup_azahar.main(AZAHAR)   # skips its copy step (AZ exists); applies the test profile
    os.makedirs(os.path.join(USER, "load", "mods"), exist_ok=True)
    marker = os.path.join(USER, "DQXI_EMU_PROFILE.txt")
    with open(marker, "w", encoding="utf-8") as fp:
        fp.write("DQXI_Disassemblr emulator data root\n"
                 "emulator binary copied once by tools/emu/extras.py:setup_main;\n"
                 "harness code (az.py, azctl.py, setup_azahar.py) used from\n"
                 f"{HARNESS}\n")
    print("ready:", EXE)
    print("user:  ", USER)
    print("saves: ", SAVES)
    print("runs:  ", RUNS)
    return 0


# ---------------------------------------------------------------------------------- ctl
CTL_DOC = """drive a running Azahar session step by step (one command per call):

  python -m tools.emu ctl start [--rom PATH] [--mod DIR] [--save NAME] [--speed PCT]
  python -m tools.emu ctl start --boot 1        # title -> Continue -> slot 1 -> field
  python -m tools.emu ctl press A [B ...]
  python -m tools.emu ctl hold BTN SECONDS
  python -m tools.emu ctl walk U|D|L|R|UL|UR|DL|DR SECONDS
  python -m tools.emu ctl wait SECONDS
  python -m tools.emu ctl mash A SECONDS [EVERY]
  python -m tools.emu ctl shot [NAME]
  python -m tools.emu ctl status [--title]
  python -m tools.emu ctl title                  # scan guest RAM for the title menu strings
  python -m tools.emu ctl read 0xADDR SIZE       # read guest memory (hex + u32s)
  python -m tools.emu ctl write 0xADDR HEXBYTES
  python -m tools.emu ctl save NAME              # snapshot the game save (not emulator state)
  python -m tools.emu ctl load NAME              # install a snapshot for the next boot
  python -m tools.emu ctl frames                 # framebuffer statistics
  python -m tools.emu ctl seq "press A" "shot a" ...
  python -m tools.emu ctl stop

Live input (press/hold/walk/mash) needs a test build with the translation project's RPC
mailbox hook (offset 0x839F00).  A retail build can be booted, screenshotted, read and driven
by input movies (az.Movie / ctl start --movie)."""


def _print_state(s, crash=None):
    c = crash or s.crashed()
    print(f"t={s.game_time():.1f}s", ("CRASH: " + c) if c else "")


def ctl_main(argv) -> int:
    if not argv:
        print(CTL_DOC)
        return 2
    az, _ = load()
    cmd, args = argv[0], argv[1:]

    if cmd == "seq":
        shots = []
        for step in args:
            parts = step.split()
            ctl_main(parts)
            if parts[0] == "shot":
                shots.append(os.path.join(CTL_DIR, (parts[1] if len(parts) > 1 else "") + ".png"))
        if shots:
            az.sheet(shots, os.path.join(CTL_DIR, "seq.png"),
                     cols=min(4, len(shots)), scale=0.75)
        return 0

    os.makedirs(CTL_DIR, exist_ok=True)

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    if cmd == "start":
        rom = opt("--rom", DEFAULT_ROM)
        save, movie, mod = opt("--save"), opt("--movie"), opt("--mod")
        if save and not os.path.isdir(os.path.join(SAVES, save)):
            raise EmuError(f"no game save named {save!r} in {SAVES}")
        settings = {}
        if "--speed" in args:       # emulation speed in % (0 = unlimited); 100 for walking
            settings["frame_limit"] = opt("--speed")
        e = make_emu(rom, mod=mod, movie=movie, save=save, workdir=CTL_DIR, settings=settings)
        e.start()
        with open(SESSION, "w", encoding="utf-8") as fp:
            json.dump({"pid": e.proc.pid, "rom": os.path.abspath(rom),
                       "mod": os.path.abspath(mod) if mod else None}, fp)
        print("started pid", e.proc.pid, "rom", rom, "mod", mod or "(none)")
        if "--boot" in args:
            ctl_main(["boot", opt("--boot")])
        return 0

    _, Session = _classes()
    if not os.path.isfile(SESSION):
        raise EmuError("no session; run `python -m tools.emu ctl start` first")
    s = Session()
    c = None
    if cmd == "stop":
        subprocess.run(["taskkill", "/PID", str(s.pid), "/F"], capture_output=True)
        try:
            os.remove(SESSION)
        except OSError:
            pass
        print("stopped")
        return 0
    if cmd == "press":
        for b in args:
            c = s.press(b) or c
    elif cmd == "hold":
        c = s.hold(args[0], float(args[1]))
    elif cmd == "walk":
        c = s.walk(args[0], float(args[1]))
    elif cmd == "wait":
        c = s.wait_game(s.game_time() + float(args[0]))
    elif cmd == "mash":
        every = float(args[2]) if len(args) > 2 else 0.6
        end = s.game_time() + float(args[1])
        while s.game_time() < end and not c:
            c = s.press(args[0], after=every)
    elif cmd == "shot":
        name = args[0] if args else time.strftime("%H%M%S")
        p = os.path.join(CTL_DIR, name + ".png")
        s.shot(p)
        print(p)
        return 0
    elif cmd == "status":
        print("pid:", s.pid, "alive:", s.alive(), "hook alive:", s.hook_alive())
        print("mod installed:", mod_installed(), MODS)
        if "--title" in args:
            print("title evidence:", s.title_evidence() or "none")
    elif cmd == "title":
        ev = s.title_evidence()
        print("title-screen reached" if ev else "title screen not found")
        for text, addrs in (ev or {}).items():
            print(f"  {printable(text)!r} at 0x{addrs[0]:08X}")
        return 0 if ev else 1
    elif cmd == "read":
        addr, size = int(args[0], 0), int(args[1], 0)
        data = s.read(addr, size)
        if not data:
            print("read failed")
            return 1
        for off in range(0, len(data), 16):
            chunk = data[off:off + 16]
            hx = " ".join(f"{b:02x}" for b in chunk)
            asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            u32 = " ".join(f"{struct.unpack_from('<I', chunk, i)[0]:08x}"
                           for i in range(0, len(chunk) - 3, 4))
            print(f"{addr + off:08X}  {hx:<47}  {asc:<16}  {u32}")
        return 0
    elif cmd == "write":
        data = bytes.fromhex(args[1].replace(" ", ""))
        ok = s.write(int(args[0], 0), data)
        print("wrote" if ok else "write failed", len(data), "bytes")
        return 0 if ok else 1
    elif cmd == "save":
        print(az.export_save(args[0]))
        return 0
    elif cmd == "load":
        az.install_save(args[0])
        print("installed game save", args[0], "- restart the session to use it")
        return 0
    elif cmd == "frames":
        print(s.screen_stats())
        return 0
    elif cmd == "boot":
        # title -> Continue -> slot (cursor default) -> recap/greeting skipped with B
        # (state-tolerant: A only ever confirms, B closes the recap and the priest's lines)
        s.wait_game(6)
        while s.game_time() < 40 and not c:
            c = s.press("A", after=1.4)
        while s.game_time() < 65 and not c:
            c = s.press("B", after=0.8)
    else:
        print(f"unknown command {cmd!r}\n{CTL_DOC}")
        return 2
    _print_state(s, c)
    return 1 if (c or s.crashed()) else 0
