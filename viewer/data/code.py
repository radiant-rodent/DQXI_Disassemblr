"""Code index: decompiled function catalogue plus source trees."""

from __future__ import annotations

import bisect
import json
from dataclasses import dataclass
from pathlib import Path

from .. import utils


@dataclass
class Function:
    address: int
    name: str
    size: int
    mode: str
    file: Path

    @property
    def addr_hex(self) -> str:
        return f"0x{self.address:08X}"

    @property
    def end(self) -> int:
        return self.address + max(1, self.size)


class CodeIndex:
    """Loads decomp/functions_index.json and provides lookups."""

    def __init__(self) -> None:
        self.functions: list[Function] = []
        self.total_discovered = 0
        self.decompiled_count = 0
        self.ready = False
        self._sorted: list[int] = []
        self._text_cache: dict[str, str] = {}

    def ensure(self) -> "CodeIndex":
        if self.ready:
            return self
        index_path = utils.DECOMP_DIR / "functions_index.json"
        funcs: list[Function] = []
        if index_path.exists():
            try:
                data = json.loads(index_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
            self.total_discovered = int(data.get("total_discovered") or 0)
            self.decompiled_count = int(data.get("decompiled_count") or 0)
            for raw in data.get("functions", []):
                try:
                    address = int(str(raw.get("address", "0")), 16)
                except ValueError:
                    continue
                rel = raw.get("file") or raw.get("source") or ""
                funcs.append(Function(
                    address=address,
                    name=raw.get("name") or f"func_{address:08X}",
                    size=int(raw.get("size") or 0),
                    mode=raw.get("mode") or "arm",
                    file=(utils.PROJECT_ROOT / rel) if rel else Path(),
                ))
            funcs.sort(key=lambda f: f.address)
        self.functions = funcs
        self._sorted = [f.address for f in funcs]
        self.decompiled_count = self.decompiled_count or len(funcs)
        self.total_discovered = self.total_discovered or len(funcs)
        self.ready = True
        return self

    # -- lookups ------------------------------------------------------------
    def search(self, query: str = "", mode: str | None = None,
               limit: int = 1500) -> list[Function]:
        self.ensure()
        q = (query or "").strip().lower()
        addr = utils.parse_addr(query)
        out: list[Function] = []
        if addr is not None:
            idx = bisect.bisect_right(self._sorted, addr) - 1
            if idx >= 0 and addr < self.functions[idx].end:
                out.append(self.functions[idx])
            # nearby functions
            for f in self.functions[max(0, idx - 12): idx + 40]:
                if f not in out:
                    out.append(f)
            return out
        for f in self.functions:
            if mode and f.mode != mode:
                continue
            if q and q not in f.name.lower() and q not in f.addr_hex.lower():
                continue
            out.append(f)
            if len(out) >= limit:
                break
        return out

    def containing(self, address: int) -> Function | None:
        self.ensure()
        idx = bisect.bisect_right(self._sorted, address) - 1
        if idx >= 0:
            f = self.functions[idx]
            if address < f.end:
                return f
        return None

    def get_by_name(self, name: str) -> Function | None:
        self.ensure()
        target = name.strip().lower()
        for f in self.functions:
            if f.name.lower() == target:
                return f
        return None

    def text(self, func: Function) -> str:
        key = str(func.file)
        cached = self._text_cache.get(key)
        if cached is None:
            try:
                cached = utils.safe_read_text(func.file, max_bytes=4 * 1024 * 1024)
            except Exception as exc:
                cached = f"// failed to read {func.file}: {exc}"
            if len(self._text_cache) > 80:
                self._text_cache.clear()
            self._text_cache[key] = cached
        return cached

    # -- source trees -------------------------------------------------------
    @staticmethod
    def _walk(root: Path, patterns: tuple[str, ...], label: str) -> list[tuple[str, Path, int]]:
        out: list[tuple[str, Path, int]] = []
        if not root.exists():
            return out
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if patterns and not any(path.match(p) for p in patterns):
                continue
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            rel = str(path.relative_to(utils.PROJECT_ROOT)).replace("\\", "/")
            out.append((rel, path, size))
        return out

    def source_groups(self) -> dict[str, list[tuple[str, Path, int]]]:
        """Grouped source trees for the code browser."""
        return {
            "Lifted C (src/)": self._walk(utils.SRC_DIR, ("*.c", "*.h"), "src"),
            "Headers (include/)": self._walk(utils.INCLUDE_DIR, ("*.h",), "include"),
            "Assembly (asm/)": self._walk(utils.ASM_DIR, ("*.s",), "asm"),
            "Tools (tools/)": self._walk(utils.TOOLS_DIR, ("*.py", "*.md"), "tools"),
            "Tests (tests/)": self._walk(utils.TESTS_DIR, ("*.py",), "tests"),
        }

    def count_lines(self, path: Path) -> int:
        try:
            with open(path, "rb") as fh:
                return sum(1 for _ in fh)
        except OSError:
            return 0
