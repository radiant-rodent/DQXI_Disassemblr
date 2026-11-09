"""Shared helpers for the DQXI type / struct / global recovery pipeline.

The pipeline is deliberately split into independent, re-runnable steps:

* :mod:`tools.typedb.struct_db`   - automated evidence collection (this is the
  "what does the executable actually do" half; it never invents names);
* :mod:`tools.typedb.make_batches` - turn that evidence into worker tasks;
* :mod:`tools.typedb.apply`       - validate and merge worker answers into the
  headers in ``include/dqxi/`` and into the readable-C rename maps.

Everything is plain Python 3.12 with no third-party dependencies.  All text and
JSON is written as UTF-8 and read back with a strict UTF-8 decode, because the
project has been burned once by a cp1252 byte in a naming batch.
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BINARY = ROOT / "original" / "exefs" / "code.decompressed.bin"
GHIDRA = ROOT / "decomp" / "ghidra"
RAW_FUNCTIONS = GHIDRA / "functions"
READABLE = ROOT / "decomp" / "readable"
INDEX = GHIDRA / "functions_merged.jsonl"
SYMBOLS = ROOT / "symbols.json"
TYPES_DIR = ROOT / "orchestration" / "types"
OUT_DIR = TYPES_DIR / "out"
BATCH_DIR = TYPES_DIR / "batches"
HEADER_DIR = ROOT / "include" / "dqxi"

# Section boundaries from include/dqxi.h.  The executable is loaded at
# 0x00100000 and code.decompressed.bin is exactly the text+rodata+data image.
TEXT = (0x00100000, 0x0072403C)
RODATA = (0x00725000, 0x0079AA18)
DATA = (0x0079B000, 0x007C2D24)
BSS = (0x007C3000, 0x00839BC0)

# First token of a recovered function name -> the subsystem used for grouping.
# This is intentionally a fixed table: a new subsystem should be a deliberate
# edit, not a side effect of a batch spelling a name differently.
SUBSYSTEM_ALIASES = {
    "Field2D": "Field",
    "FieldParty": "Field",
    "Battle2DUnit": "Battle",
    "BattleScene": "Battle",
    "Actor2D": "Actor",
    "ActorAction": "Actor",
    "Snd": "Sound",
    "Sq": "Script",
    "Msg": "Message",
    "Ui3D": "Ui",
    "Work": "Os",
    "Game": "Os",
    "Fx": "Gfx",
    "Effect": "Gfx",
}

# Ghidra/GCC base types seen in this executable.  Width in bytes on ARM32.
TYPE_WIDTHS = {
    "undefined8": 8, "longlong": 8, "ulonglong": 8, "double": 8, "s64": 8, "u64": 8,
    "undefined4": 4, "int": 4, "uint": 4, "float": 4, "code": 4, "undefined": 4,
    "size_t": 4, "ssize_t": 4, "s32": 4, "u32": 4, "bool": 4,
    "undefined2": 2, "short": 2, "ushort": 2, "wchar_t": 2, "s16": 2, "u16": 2,
    "undefined1": 1, "char": 1, "schar": 1, "uchar": 1, "byte": 1, "s8": 1, "u8": 1,
}

C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long",
    "register", "restrict", "return", "short", "signed", "sizeof", "static", "struct",
    "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "_Bool",
    "self", "this", "new", "class",
}

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Roles inferred from the last name token ("what this method is for").  Used for
# constructor / destructor detection, base-class inference and size evidence.
ROLE_CTOR = re.compile(
    r"^(_+)?(Ctor|Construct|Create|New|Alloc|Init|Setup|Reset|LoadFrom|InitFrom|InitPanes|InitBase)",
    re.I,
)
ROLE_DTOR = re.compile(r"^(_+)?(Dtor|Delete|Destroy|Free|Release|Teardown|Cleanup)", re.I)
ROLE_UPDATE = re.compile(r"^(_+)?(Update|Draw|Exec|Render|Tick|Apply|Advance|Process)", re.I)


# --------------------------------------------------------------------------- #
# binary image helpers
# --------------------------------------------------------------------------- #
_IMAGE: bytes | None = None


def image() -> bytes:
    """The decompressed retail code image, read once per process."""
    global _IMAGE
    if _IMAGE is None:
        _IMAGE = BINARY.read_bytes()
    return _IMAGE


def word_at(address: int) -> int | None:
    """32-bit little-endian word at a virtual address, or None outside the image."""
    offset = address - 0x00100000
    data = image()
    if 0 <= offset <= len(data) - 4:
        return struct.unpack_from("<I", data, offset)[0]
    return None


def bytes_at(address: int, size: int) -> bytes:
    offset = address - 0x00100000
    return image()[offset:offset + size] if offset >= 0 else b""


def section_of(address: int) -> str:
    if TEXT[0] <= address < TEXT[1]:
        return "text"
    if RODATA[0] <= address < RODATA[1]:
        return "rodata"
    if DATA[0] <= address < DATA[1]:
        return "data"
    if BSS[0] <= address < BSS[1]:
        return "bss"
    return "outside"


def is_text_pointer(value: int | None) -> bool:
    return value is not None and TEXT[0] <= value < TEXT[1]


def c_string(address: int, max_length: int = 96) -> str | None:
    """A printable NUL-terminated C string at address, else None.

    Used only to label a global by its content; the string bytes themselves stay
    in the original binary.
    """
    if section_of(address) not in ("rodata", "data", "bss"):
        return None
    raw = bytes_at(address, max_length)
    if not raw:
        return None
    end = raw.find(b"\0")
    if end < 4:                      # "@@@" style thunks and empty strings are noise
        return None
    text = raw[:end]
    if sum(1 for b in text if 32 <= b < 127 or b in (9, 10, 13)) / len(text) < 0.92:
        return None
    try:
        return text.decode("ascii")
    except UnicodeDecodeError:
        return None


def pointer_array(address: int, limit: int = 64) -> list[int]:
    """Consecutive text pointers starting at address (a vtable/jump table)."""
    out: list[int] = []
    for i in range(limit):
        w = word_at(address + 4 * i)
        if not is_text_pointer(w):
            break
        out.append(w)
    return out


# --------------------------------------------------------------------------- #
# names / grouping
# --------------------------------------------------------------------------- #
def strip_maybe(name: str) -> str:
    return name[6:] if name.startswith("maybe_") else name


def name_tokens(name: str) -> list[str]:
    """Tokens of a recovered name without the uncertainty prefix and clash suffix."""
    clean = strip_maybe(name)
    tokens = [t for t in clean.split("_") if t]
    while tokens and re.fullmatch(r"\d+", tokens[-1]) and len(tokens) > 2:
        tokens.pop()                  # M1's _2 / _3 clash suffix
    return tokens


def subsystem_of(name: str) -> str:
    tokens = name_tokens(name)
    if not tokens:
        return "Unknown"
    first = tokens[0]
    if first in SUBSYSTEM_ALIASES:
        return SUBSYSTEM_ALIASES[first]
    if first.islower():
        return "std" if first == "std" else "General"
    return first


def role_of(name: str) -> str:
    tokens = name_tokens(name)
    if len(tokens) < 2:
        return "method"
    last = tokens[-1]
    # Accept CtorB, InitPanes, InitFromDef, Delete_2 ...
    if ROLE_CTOR.match(last):
        return "ctor"
    if ROLE_DTOR.match(last):
        return "dtor"
    if ROLE_UPDATE.match(last):
        return "update"
    return "method"


def valid_identifier(text: str) -> bool:
    return bool(IDENT.match(text or "")) and text not in C_KEYWORDS


def camel_type(*tokens: str) -> str:
    """Ui + GaugeWindow -> UiGaugeWindow (the spelling M1 uses in signatures)."""
    return "".join(tokens)


# --------------------------------------------------------------------------- #
# index / file helpers
# --------------------------------------------------------------------------- #
def load_rows() -> list[dict]:
    """Rows of functions_merged.jsonl (one per entry point)."""
    rows: list[dict] = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            row = json.loads(line)
            row["_address"] = int(row["address"], 16)
            rows.append(row)
    return rows


def raw_path(row: dict) -> Path | None:
    rel = row.get("file")
    return GHIDRA / rel if rel else None


_READABLE_INDEX: dict[int, Path] | None = None


def readable_index() -> dict[int, Path]:
    """address -> readable C file, built once by walking ``decomp/readable``.

    ``functions_merged.jsonl`` still records the pre-M1 Ghidra file name
    (``FUN_00100050_00100050.c``) while M1 renamed the readable twin to
    ``std_ConstructArray_00100050.c``.  Looking up by the trailing address keeps
    the two trees connected without touching the merged index.
    """
    global _READABLE_INDEX
    if _READABLE_INDEX is None:
        index: dict[int, Path] = {}
        if READABLE.is_dir():
            for path in READABLE.rglob("*.c"):
                m = re.search(r"_([0-9a-fA-F]{8})\.c$", path.name)
                if m:
                    index.setdefault(int(m.group(1), 16), path)
        _READABLE_INDEX = index
    return _READABLE_INDEX


def readable_path(row: dict) -> Path | None:
    rel = row.get("file")
    if rel:
        path = READABLE / rel
        if path.is_file():
            return path
    return readable_index().get(row["_address"])


def strip_comments(text: str) -> str:
    """Remove C comments while preserving line breaks (keeps line numbers)."""
    def blank(match: re.Match) -> str:
        return "\n" * match.group(0).count("\n")
    text = re.sub(r"/\*.*?\*/", blank, text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def write_json(path: Path, value) -> None:
    """UTF-8 JSON, then strict read-back (rule 11 of WORKER_RULES)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=1, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    path.read_text(encoding="utf-8")      # raises if anything wrote a stray byte


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def type_width(type_name: str) -> int:
    """Width of a Ghidra base type; pointers are handled by the caller."""
    return TYPE_WIDTHS.get(type_name, 4)


def hex_addr(value: int) -> str:
    return f"0x{value:08X}"
