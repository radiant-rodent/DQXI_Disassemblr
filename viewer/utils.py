"""Shared helpers: project paths, formatting, thumbnail cache, background work."""

from __future__ import annotations

import hashlib
import os
import queue
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

# ---------------------------------------------------------------------------
# Project discovery
# ---------------------------------------------------------------------------
_MARKERS = ("game_textures", "game_models", "decomp", "tools")


def _detect_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if all((parent / m).exists() for m in _MARKERS):
            return parent
    # fall back to two levels up from this file (viewer/utils.py -> project)
    return here.parents[1]


PROJECT_ROOT: Path = _detect_root()

# data roots --------------------------------------------------------------
TEXTURES_DIR = PROJECT_ROOT / "game_textures"
MODELS_DIR = PROJECT_ROOT / "game_models"
LAYOUTS_DIR = PROJECT_ROOT / "game_layouts"
SCRIPTS_DIR = PROJECT_ROOT / "game_scripts"
TABLES_DIR = PROJECT_ROOT / "game_tables"
AUDIO_DIR = PROJECT_ROOT / "game_audio"
DECOMP_DIR = PROJECT_ROOT / "decomp"
SRC_DIR = PROJECT_ROOT / "src"
INCLUDE_DIR = PROJECT_ROOT / "include"
ASM_DIR = PROJECT_ROOT / "asm"
TOOLS_DIR = PROJECT_ROOT / "tools"
TESTS_DIR = PROJECT_ROOT / "tests"
BUILD_DIR = PROJECT_ROOT / "build"
ORIGINAL_DIR = PROJECT_ROOT / "original"

# read-only reference (translation workspace) ------------------------------
REFERENCE_ROOT = Path(r"..\reference project")
DIALOGUE_DB = REFERENCE_ROOT / "workspace" / "project.db"
LEVEL2D_DIR = REFERENCE_ROOT / "workspace" / "extracted" / "romfs" / "level2d"
LEVEL3D_DIR = REFERENCE_ROOT / "workspace" / "extracted" / "romfs" / "level3d"

APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local")) / "DQXI_Explorer"
THUMB_DIR = APP_DIR / "thumbs"
THUMB_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def human_size(n: int | float | None) -> str:
    if n is None:
        return "-"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(n)} B"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


def human_count(n: int) -> str:
    return f"{n:,}"


def elide(s: str, width: int) -> str:
    s = s.replace("\n", " ").replace("\r", " ")
    if len(s) <= width:
        return s
    return s[: max(0, width - 1)] + "\u2026"


_HEX_ADDR = re.compile(r"^\s*(?:0x|#|\$)?([0-9a-fA-F]{4,16})\s*$")


def parse_addr(text: str) -> int | None:
    m = _HEX_ADDR.match(text or "")
    if not m:
        return None
    try:
        return int(m.group(1), 16)
    except ValueError:
        return None


def fmt_addr(v: int) -> str:
    return f"0x{v:08X}"


# ---------------------------------------------------------------------------
# Thumbnails
# ---------------------------------------------------------------------------
class ThumbCache:
    """Disk + memory cache of square thumbnails for image files."""

    def __init__(self, size: int = 144, mem_limit: int = 700):
        self.size = size
        self.mem_limit = mem_limit
        self._mem: dict[str, Image.Image] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def _mem_get(self, key: str) -> Image.Image | None:
        with self._lock:
            img = self._mem.get(key)
            if img is not None:
                try:
                    self._order.remove(key)
                except ValueError:
                    pass
                self._order.append(key)
            return img

    def _mem_put(self, key: str, img: Image.Image) -> None:
        with self._lock:
            self._mem[key] = img
            self._order.append(key)
            while len(self._order) > self.mem_limit:
                old = self._order.pop(0)
                self._mem.pop(old, None)

    @staticmethod
    def _key(path: str, size: int) -> str:
        try:
            st = os.stat(path)
            sig = f"{path}|{st.st_mtime_ns}|{st.st_size}|{size}"
        except OSError:
            sig = f"{path}|missing|{size}"
        return hashlib.sha1(sig.encode("utf-8", "replace")).hexdigest()[:20]

    def get(self, path: str | Path, size: int | None = None) -> Image.Image | None:
        path = str(path)
        size = int(size or self.size)
        key = self._key(path, size)
        img = self._mem_get(key)
        if img is not None:
            return img
        cache_file = THUMB_DIR / f"{key}.png"
        if cache_file.exists():
            try:
                img = Image.open(cache_file)
                img.load()
                self._mem_put(key, img)
                return img
            except Exception:
                try:
                    cache_file.unlink()
                except OSError:
                    pass
        # decode from source
        try:
            img = Image.open(path)
            img.load()
        except Exception:
            return None
        thumb = img.copy()
        thumb.thumbnail((size, size), Image.LANCZOS)
        if thumb.mode not in ("RGB", "RGBA"):
            thumb = thumb.convert("RGBA")
        self._mem_put(key, thumb)
        try:
            tmp = cache_file.with_suffix(".tmp")
            thumb.save(tmp, "PNG")
            os.replace(tmp, cache_file)
        except Exception:
            pass
        return thumb


IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


# ---------------------------------------------------------------------------
# Background execution
# ---------------------------------------------------------------------------
_EXECUTOR = ThreadPoolExecutor(max_workers=6, thread_name_prefix="dqxi-bg")


def submit(fn, *args, **kwargs):
    """Run work on the shared thread pool."""
    return _EXECUTOR.submit(fn, *args, **kwargs)


def start_thread(fn, *args, daemon: bool = True, name: str | None = None, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=daemon, name=name)
    t.start()
    return t


def debounced(widget, delay_ms: int, fn):
    """Return a callable that debounces *fn* per widget using after()."""
    state = {"id": None}

    def call(*args, **kwargs):
        if state["id"] is not None:
            try:
                widget.after_cancel(state["id"])
            except Exception:
                pass
        def run():
            state["id"] = None
            fn(*args, **kwargs)
        state["id"] = widget.after(delay_ms, run)

    return call


class UiBridge:
    """Schedule callbacks from worker threads onto the Tk main thread.

    ``widget.after()`` must only be called from the thread that owns the Tk
    interpreter (this Python/Tcl build raises ``RuntimeError: main thread is
    not in main loop`` otherwise), so worker threads hand functions over in a
    queue and a main-thread poll loop runs them.
    """

    def __init__(self, widget, interval_ms: int = 60):
        self._widget = widget
        self._interval = interval_ms
        self._queue: queue.Queue = queue.Queue()
        self._schedule()

    def post(self, fn, *args, **kwargs) -> None:
        """Run *fn* on the main thread at the next poll tick."""
        self._queue.put((fn, args, kwargs))

    # -- internals ----------------------------------------------------------
    def _schedule(self) -> None:
        try:
            self._widget.after(self._interval, self._pump)
        except Exception:
            pass

    def _pump(self) -> None:
        try:
            while True:
                fn, args, kwargs = self._queue.get_nowait()
                try:
                    fn(*args, **kwargs)
                except Exception:
                    pass
        except queue.Empty:
            pass
        self._schedule()



# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------
def reveal_in_explorer(path: str | Path) -> None:
    """Open the native file browser at *path* (read-only convenience)."""
    path = Path(path)
    if not path.exists():
        return
    try:
        if os.name == "nt":
            if path.is_dir():
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                os.system(f'explorer /select,"{path}"')
        else:
            os.startfile(str(path.parent))  # type: ignore[attr-defined]
    except Exception:
        pass


def open_external(path: str | Path) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def copy_to_clipboard(widget, text: str) -> None:
    try:
        widget.clipboard_clear()
        widget.clipboard_append(text)
    except Exception:
        pass


def safe_read_text(path: str | Path, max_bytes: int = 64 * 1024 * 1024) -> str:
    """Read a text file tolerating encodings and huge sizes."""
    data = Path(path).read_bytes()
    if len(data) > max_bytes:
        data = data[:max_bytes]
    for enc in ("utf-8-sig", "utf-8", "cp932", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def json_short(value, limit: int = 90) -> str:
    import json

    try:
        s = json.dumps(value, ensure_ascii=False)
    except Exception:
        s = str(value)
    return elide(s, limit)
