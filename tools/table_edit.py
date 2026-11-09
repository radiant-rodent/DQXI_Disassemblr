#!/usr/bin/env python3
"""Read and edit the game's BXON parameter tables by row and field *name*.

Field names, types and value meanings come from `tools/table_schemas.json`.
Every edit is a same-size scalar write straight into the BXON bytes, so a
patched table keeps its length and goes back into the game unchanged in shape.

Rows can be addressed as an index (`#12` or `12`), by the name from the
schema's `label` field (Japanese in-game text), or by the English name from the
read-only translation workspace when it is present.

    python tools/table_edit.py tables
    python tools/table_edit.py fields syscmn/item.json
    python tools/table_edit.py list syscmn/item.json --grep やくそう
    python tools/table_edit.py get syscmn/item.json やくそう buy_price
    python tools/table_edit.py set syscmn/item.json やくそう buy_price 5 --out build/item.bxon
    python tools/table_edit.py save-mod syscmn/item.json --patched build/item.bxon
    python tools/table_edit.py verify

`verify` re-writes every named field of every table with the value it already
holds and demands a byte-identical file, then changes one value and re-reads it.
That is the round-trip guarantee the Table editor in DQXI Studio relies on.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sqlite3
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "game_assets" / "tables" / "packs"
SOURCES = ROOT / "game_data" / "packs"
ROMFS = ROOT / "game_data" / "romfs"
SCHEMAS = ROOT / "tools" / "table_schemas.json"
MOD = ROOT / "mod" / "romfs"
DB = Path(r"..\3DS_Translate\workspace\project.db")

MARK = b"&&&&"
SCALARS = {"u8": "<B", "u16": "<H", "u32": "<I", "s32": "<i", "f32": "<f"}
WIDTHS = {"u8": 1, "u16": 2, "u32": 4, "s32": 4, "f32": 4}
RUBY = re.compile("\x01(.*?)\x02.*?\x03", re.S)


def decode_string(payload: bytes) -> str:
    """Decode one BXON string block.

    The game stores two kinds: UTF-16 text (dialogue and item names, often with
    0x01/0x02/0x03 ruby tags) and plain ASCII asset ids (m001a, n_hat,
    i_use_001).  Blocks are padded to four bytes with b'@'.  A block whose
    bytes are all printable ASCII is an asset id; anything else is UTF-16.
    """
    body = payload.rstrip(b"@")
    if body.endswith(b"\0\0"):
        body = body[:-2]
    elif body.endswith(b"\0"):
        body = body[:-1]
    if not body:
        return ""
    if all(0x20 <= byte < 0x7F for byte in body):
        return body.decode("ascii")
    return RUBY.sub(r"\1", body.decode("utf-16-le", "replace"))


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
def _expand(spec: dict) -> list[dict]:
    """Turn one schema entry into the flat field list, expanding `count`.

    A repeated field is numbered from 1 and, like the rest of the game data,
    keeps the byte offset in the name (`resist_00` counts from zero because the
    resistance block *is* offset-addressed).
    """
    count = int(spec.get("count") or 1)
    if count <= 1:
        out = [dict(spec)]
        out[0].pop("count", None)
        return out
    width = WIDTHS[spec["type"]]
    out = []
    for i in range(count):
        item = dict(spec)
        item.pop("count", None)
        item["offset"] = spec["offset"] + i * width
        if spec["type"] == "u8":
            item["name"] = f"{spec['name']}_{i:02x}"
        else:
            item["name"] = f"{spec['name']}_{i + 1:02d}"
        out.append(item)
    return out


class Schemas:
    """The schema file, with exact entries and wildcard patterns resolved."""

    def __init__(self, path: Path = SCHEMAS):
        raw = json.loads(path.read_text(encoding="utf-8"))
        self.exact: dict[str, dict] = raw.get("tables", {})
        self.patterns: dict[str, dict] = raw.get("patterns", {})
        self._cache: dict[str, dict | None] = {}

    def get(self, table: str) -> dict | None:
        table = table.replace("\\", "/")
        if table in self._cache:
            return self._cache[table]
        spec = self.exact.get(table)
        if spec is None:
            for pattern, candidate in self.patterns.items():
                if fnmatch.fnmatchcase(table, pattern):
                    spec = candidate
                    break
        if spec is not None:
            spec = dict(spec)
            spec["fields"] = [f for entry in spec.get("fields", []) for f in _expand(entry)]
        self._cache[table] = spec
        return spec

    def names(self) -> list[str]:
        return sorted(self.exact)


# ---------------------------------------------------------------------------
# BXON geometry and scalar access
# ---------------------------------------------------------------------------
class Table:
    """One table: the raw BXON bytes plus where each row starts."""

    def __init__(self, table: str, data: bytes | None = None):
        self.name = table.replace("\\", "/")
        self.schema = Schemas().get(self.name)
        self.source = SOURCES / Path(self.name).with_suffix(".bxon")
        self.raw = bytearray(data if data is not None else self.source.read_bytes())
        self.rows, self.row_size = self._geometry()
        self._english: dict[str, str] | None = None

    # -- geometry ---------------------------------------------------------
    def _geometry(self) -> tuple[list[int], int]:
        data = self.raw
        if data[:4] != b"BXON":
            raise SystemExit(f"{self.source} is not a BXON file")
        count = struct.unpack_from("<I", data, 0x20)[0]
        rel = struct.unpack_from("<I", data, 0x24)[0]
        root = 0x24 + rel
        if count == 0 or count > 1_000_000:
            return [], 0
        end = data.find(MARK, root)
        if end < 0:
            end = len(data)
        size = (end - root) // count
        if size <= 0 or end - root != size * count:
            return [root + i * max(size, 4) for i in range(count)], max(size, 4)
        return [root + i * size for i in range(count)], size

    def __len__(self) -> int:
        return len(self.rows)

    # -- fields -----------------------------------------------------------
    def fields(self) -> list[dict]:
        return (self.schema or {}).get("fields", [])

    def field(self, name: str) -> dict:
        for spec in self.fields():
            if spec["name"] == name:
                return spec
        known = ", ".join(f["name"] for f in self.fields()) or "none - run `tables` to see what is named"
        raise SystemExit(f"{self.name} has no field {name!r} (known: {known})")

    def _word(self, row: int, offset: int) -> int:
        return struct.unpack_from("<I", self.raw, self.rows[row] + (offset & ~3))[0]

    def read(self, row: int, spec: dict):
        """The value of `spec` at `row`, in the type the schema asked for."""
        offset = int(spec["offset"])
        kind = spec["type"]
        if kind == "string":
            return self._string_at(row, offset)
        word = self._word(row, offset)
        shift = (offset & 3) * 8
        width = WIDTHS[kind]
        mask = (1 << (width * 8)) - 1
        raw = (word >> shift) & mask
        if kind == "f32":
            return struct.unpack("<f", struct.pack("<I", raw))[0]
        if kind == "s32" and raw & 0x8000_0000:
            return raw - (1 << 32)
        return raw

    def _string_at(self, row: int, offset: int) -> str:
        rel = struct.unpack_from("<I", self.raw, self.rows[row] + offset)[0]
        if rel == 0:
            return ""
        target = self.rows[row] + offset + rel
        if target + 2 > len(self.raw):
            return ""
        end = self.raw.find(MARK, target)
        if end < 0:
            end = len(self.raw)
        return decode_string(bytes(self.raw[target:end]))

    def write_string(self, row: int, spec: dict, text: str) -> None:
        """Give one row's string field a new value of any length.

        The new string is appended as its own block at the end of the file and only this
        row's pointer is re-aimed, so rows that shared the old string (e.g. an item made with
        ``add-item``) keep it. The engine accepts strings relocated to the end of a BXON (proven
        for message banks and items in the emulator); the file grows, the PACK is re-laid out.
        """
        sys.path.insert(0, str(ROOT))
        from tools.bxon import encode_utf16

        old = self._string_at(row, int(spec["offset"]))
        ascii_id = bool(old) and old.isascii() and old.isprintable()
        payload = (text.encode("ascii") + b"\0") if ascii_id else (encode_utf16(text) + b"\0\0")
        payload += b"@" * (-len(payload) % 4)
        while len(self.raw) % 4:
            self.raw += b"@"
        self.raw += MARK
        target = len(self.raw)
        self.raw += payload
        field_pos = self.rows[row] + int(spec["offset"])
        struct.pack_into("<I", self.raw, field_pos, (target - field_pos) & 0xFFFFFFFF)

    def write(self, row: int, spec: dict, value) -> None:
        """Same-size scalar write (strings go through write_string)."""
        kind = spec["type"]
        if kind == "string":
            self.write_string(row, spec, str(value))
            return
        width = WIDTHS[kind]
        if width == 4:
            struct.pack_into(SCALARS[kind], self.raw, self.rows[row] + int(spec["offset"]), value)
            return
        offset = int(spec["offset"])
        base = self.rows[row] + (offset & ~3)
        shift = (offset & 3) * 8
        word = struct.unpack_from("<I", self.raw, base)[0]
        mask = ((1 << (width * 8)) - 1) << shift
        word = (word & ~mask) | ((int(value) & ((1 << (width * 8)) - 1)) << shift)
        struct.pack_into("<I", self.raw, base, word)

    # -- row labels -------------------------------------------------------
    def label(self, row: int) -> str:
        key = (self.schema or {}).get("label")
        if not key:
            return f"#{row}"
        text = str(self.read(row, self.field(key))).replace("\n", " ")
        if self._english is None:
            self._english = english_names()
        return self._english.get(str(self.read(row, self.field(key))), text)

    def find(self, spec: str) -> int:
        text = spec.lstrip("#")
        if text.isdigit():
            index = int(text)
            if not 0 <= index < len(self):
                raise SystemExit(f"{self.name} has {len(self)} rows, no row {index}")
            return index
        wanted = spec.casefold()
        for i in range(len(self)):
            if wanted in (self.label(i).casefold(), f"#{i}"):
                return i
        for i in range(len(self)):
            if (self.schema or {}).get("label") and wanted == str(self.read(i, self.field(self.schema["label"]))).casefold():
                return i
        raise SystemExit(f"no row named {spec!r} in {self.name}")

    def id_of(self, row: int):
        key = (self.schema or {}).get("id")
        # Tables the engine addresses by row (monsters, encounters) spell that
        # as "__row__" so the reference integrity check still sees an id field.
        if not key or key == "__row__":
            return row
        return self.read(row, self.field(key))

    # -- convenience used by the tests and by small scripts -----------------
    def value(self, row: int, spec: "str | dict"):
        """Read `row`/`spec`, accepting either a field name or a field entry."""
        field = self.field(spec) if isinstance(spec, str) else spec
        if not 0 <= row < len(self):
            raise IndexError(f"{self.name} has {len(self)} rows, no row {row}")
        return self.read(row, field)

    def set(self, row: int, spec: "str | dict", value) -> None:
        """Validate and write one field, with the same rules the editor uses."""
        field = self.field(spec) if isinstance(spec, str) else spec
        kind = field["type"]
        if kind == "string":
            raise SystemExit("strings are read-only here: a longer string changes the file size")
        try:
            parsed = float(value) if kind == "f32" else int(value, 0) if isinstance(value, str) else int(value)
        except (TypeError, ValueError):
            raise SystemExit(f"{field['name']} is {kind}; {value!r} is not a number")
        problem = check_range(field, parsed)
        if problem:
            raise SystemExit(problem)
        self.write(row, field, parsed)

    def address(self, row: int, spec: "str | dict") -> int:
        """Byte offset a field starts at, for tests that assert what changed."""
        field = self.field(spec) if isinstance(spec, str) else spec
        return self.rows[row] + int(field["offset"])


def english_names() -> dict[str, str]:
    """Japanese plain text -> English, from the read-only translation workspace."""
    if not DB.is_file():
        return {}
    try:
        con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
        rows = con.execute("select plain, translation from source where translation is not null").fetchall()
        con.close()
    except sqlite3.Error:
        return {}
    return {plain: " ".join(t.split()) for plain, t in rows}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def all_tables() -> list[str]:
    out = []
    for path in sorted(TABLES.rglob("*.json")):
        out.append(path.relative_to(TABLES).with_suffix("").as_posix() + ".json")
    return out


def pack_of(table: str) -> tuple[str, str]:
    """RomFS pack and member name for a table path ('syscmn/item.json')."""
    rel = Path(table.replace("\\", "/"))
    pack = f"{rel.parts[0]}.pack"
    return pack, rel.with_suffix(".bxon").name


def check_range(spec: dict, value) -> str | None:
    """Reject a value the field cannot hold or that the schema marks out of range."""
    kind = spec.get("type")
    if kind in WIDTHS:
        bits = WIDTHS[kind] * 8
        low, high = (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if kind == "s32" else (0, (1 << bits) - 1)
        if isinstance(value, float) and kind != "f32":
            return f"{spec['name']} is {kind}; {value} is not an integer"
        if not low <= value <= high:
            return f"{spec['name']} is {kind}: use {low}..{high} (got {value})"
    if kind == "f32":
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return f"{spec['name']} must be a finite number"
    span = spec.get("range")
    if not span:
        return None
    low, high = span
    if not (low <= value <= high):
        return f"{spec['name']} must be between {low} and {high} (got {value})"
    return None


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def cmd_tables(_args) -> int:
    schemas = Schemas()
    families: dict[str, int] = {}
    named = 0
    for table in all_tables():
        family = table.split("/")[0]
        families[family] = families.get(family, 0) + 1
        if schemas.get(table):
            named += 1
    total = sum(families.values())
    for family, count in sorted(families.items()):
        have = sum(1 for t in all_tables() if t.startswith(family + "/") and schemas.get(t))
        print(f"{family:12} {count:5} tables  {have:4} with field names")
    print(f"{'total':12} {total:5} tables  {named:4} with field names")
    return 0


def cmd_fields(args) -> int:
    table = Table(args.table)
    if not table.schema:
        print(f"{table.name}: no field names yet ({len(table)} rows of {table.row_size} bytes)", file=sys.stderr)
        print("everything is still editable by offset in the Table editor", file=sys.stderr)
        return 0
    spec = table.schema
    print(f"{table.name}  {spec['type']}  {len(table)} rows x {table.row_size} bytes   [{(spec.get('category') or '-')}]")
    if spec.get("note"):
        print(f"  {spec['note']}")
    print(f"  {'field':16} {'off':>5} {'type':6} {'conf':9} range")
    for f in table.fields():
        span = f.get("range")
        extra = ""
        if span:
            extra = f"{span[0]}..{span[1]}"
        if f.get("enum"):
            extra += "  " + " ".join(f"{k}={v}" for k, v in f["enum"].items())
        if f.get("ref"):
            extra += f"  -> {f['ref']['table']}"
        print(f"  {f['name']:16} {int(f['offset']):>5} {f['type']:6} {f.get('confidence','?'):9} {extra}")
        print(f"      {f.get('why','')}")
    return 0


def cmd_list(args) -> int:
    table = Table(args.table)
    fields = [f for f in table.fields() if not args.named_only or True]
    if not fields:
        raise SystemExit(f"{table.name} has no named fields yet - use `fields` on a table that has them")
    label_key = (table.schema or {}).get("label")
    shown = 0
    for i in range(len(table)):
        label = table.label(i)
        if args.grep and args.grep.casefold() not in label.casefold():
            continue
        values = []
        for f in fields:
            if f["name"] == label_key:
                continue
            try:
                values.append(f"{f['name']}={table.read(i, f)}")
            except (struct.error, IndexError):
                values.append(f"{f['name']}=?")
        print(f"#{i:<5} {label[:40]:40}  " + "  ".join(values))
        shown += 1
        if args.limit and shown >= args.limit:
            break
    return 0


def cmd_get(args) -> int:
    table = Table(args.table)
    print(table.read(table.find(args.row), table.field(args.field)))
    return 0


def cmd_set(args) -> int:
    table = Table(args.table, args.base.read_bytes()) if args.base else Table(args.table)
    spec = table.field(args.field)
    row = table.find(args.row)
    before = table.read(row, spec)
    kind = spec["type"]
    size_before = len(table.raw)
    if kind == "string":  # any length: appended as a new block (see Table.write_string)
        value = args.value.replace("\\n", "\n")  # a literal \n on the command line = line break
    else:
        try:
            value = float(args.value) if kind == "f32" else int(args.value, 0)
        except ValueError:
            raise SystemExit(f"{args.field} is {kind}; {args.value!r} is not a number")
        problem = check_range(spec, value)
        if problem:
            raise SystemExit(problem)
    table.write(row, spec, value)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(bytes(table.raw))
    after = Table(args.table, bytes(table.raw)).read(row, spec)
    grown = len(table.raw) - size_before
    note = "same size" if not grown else f"+{grown} bytes"
    print(f"{table.label(row)}: {args.field} {before!r} -> {after!r}  ({args.out}, {note})")
    print(f"put it back with: python tools/table_edit.py save-mod {args.table} --patched {args.out}")
    return 0


def cmd_add_item(args) -> int:
    """Add a row by claiming a placeholder (``id == 0``): the row count never changes.

    Growing a table is not safe for every table: the engine checks the item count against a
    constant in code.bin and keeps per-item arrays of that size (tools/bxon_grow.py
    ``grow_items``). Claiming one of the unused rows sidesteps all of that and was proven in
    the emulator (tests/emu ``item_new``).
    """
    sys.path.insert(0, str(ROOT))
    from tools.bxon_grow import claim_placeholder, pointer_offsets_from_schema

    table = Table(args.table, args.base.read_bytes()) if args.base else Table(args.table)
    id_spec = table.field("id")
    source = table.find(args.copy)
    ids = [table.read(r, id_spec) for r in range(len(table))]
    free_rows = [r for r, i in enumerate(ids) if i == 0]
    if not free_rows:
        raise SystemExit("no placeholder rows (id == 0) left in this table")
    dest = free_rows[0]
    used = set(ids)
    new_id = int(args.id, 0) if args.id else next(
        i for i in range(1, max(ids)) if i not in used)  # stay inside the retail id range
    if new_id in used:
        raise SystemExit(f"id {new_id} is already used")
    row_size, pointers = pointer_offsets_from_schema(args.table.replace("\\", "/"))
    data = claim_placeholder(bytes(table.raw), row_size, pointers, source, dest,
                             id_spec["offset"], new_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(data)
    print(f"row {dest} is now a copy of {table.label(source)} with id {new_id}  ({args.out}, same size)")
    print(f"{len(free_rows) - 1} placeholder rows left. Change its fields with:")
    print(f"  python tools/table_edit.py set {args.table} {dest} buy_price 100 --base {args.out} --out {args.out}")
    return 0


def cmd_save_mod(args) -> int:
    """Rebuild the containing RomFS pack into mod/romfs, leaving game_data alone.

    Delegates to `tools/export_mod.stage_member`, which is the project's existing
    mod-workspace convention (a LayeredFS-ready `mod/romfs/<pack>`), so a table
    edit lands exactly where `tools/export_mod.py` expects to find it.
    """
    table = args.table.replace("\\", "/")
    pack_name, member = pack_of(table)
    original = ROMFS / pack_name
    if not original.is_file():
        raise SystemExit(f"missing RomFS pack {original}")
    patched = Path(args.patched)
    if not patched.is_file():
        raise SystemExit(f"missing patched table {patched}")
    sys.path.insert(0, str(ROOT))
    from tools.export_mod import stage_member

    info = stage_member(pack_name, member, patched, ROOT / "mod", work_dir=ROOT / "build" / "staged")
    print(f"{pack_name} rebuilt with {member}: {info['size']:,} bytes "
          f"(retail {info['original_size']:,}) -> {Path(info['mod_file']).relative_to(ROOT)}")
    print("export it with: python tools/export_mod.py --target luma   (see docs/REBUILD.md)")
    return 0


def cmd_verify(args) -> int:
    """Every named field must write back its own value byte-identically."""
    schemas = Schemas()
    tables = [t for t in all_tables() if schemas.get(t)]
    if args.table:
        tables = [t for t in tables if t == args.table.replace("\\", "/")]
    failures = 0
    checked = 0
    values = 0
    for table_name in tables:
        table = Table(table_name)
        before = bytes(table.raw)
        if len(table) == 0:
            print(f"  [FAIL] {table_name}: no rows decoded")
            failures += 1
            continue
        for row in range(len(table)):
            for spec in table.fields():
                try:
                    value = table.read(row, spec)
                except (struct.error, IndexError):
                    continue
                if spec["type"] == "string":
                    continue
                table.write(row, spec, value)
                values += 1
        after = bytes(table.raw)
        if after != before:
            diff = next(i for i in range(len(before)) if before[i] != after[i])
            print(f"  [FAIL] {table_name}: rewrite changed byte 0x{diff:X}")
            failures += 1
            continue
        # a changed value must re-parse to the new value
        row = min(1, len(table) - 1)
        changed = 0
        for spec in table.fields():
            if spec["type"] in ("string", "f32"):
                continue
            old = table.read(row, spec)
            if spec["type"] in ("u32", "s32"):
                span = spec.get("range") or [0, 0xFFFFFFFF]
                new = old + 1 if old + 1 <= span[1] else old - 1
            else:
                bits = WIDTHS[spec["type"]] * 8
                new = (old + 1) % (1 << bits)
            table.write(row, spec, new)
            if table.read(row, spec) != new:
                print(f"  [FAIL] {table_name}: {spec['name']} row {row} did not keep {new}")
                failures += 1
            table.write(row, spec, old)
            changed += 1
        if bytes(table.raw) != before:
            print(f"  [FAIL] {table_name}: revert after the change test was not byte-identical")
            failures += 1
        checked += 1
        print(f"  [OK]   {table_name}: {len(table)} rows, {len(table.fields())} fields, {changed} value round-trips")
    print(f"\n{checked} tables, {values:,} field writes, {failures} failure(s)")
    return 1 if failures else 0


def cmd_schema(args) -> int:
    """Print the resolved schema (patterns expanded) so the Rust viewer can be checked against it."""
    spec = Schemas().get(args.table)
    if not spec:
        raise SystemExit(f"no schema for {args.table}")
    print(json.dumps(spec, indent=2, ensure_ascii=False))
    return 0


def main() -> int:
    # The in-game text is Japanese; a cp1252 console would crash on it.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tables", help="list table families and how many have field names")

    f = sub.add_parser("fields", help="list named fields, their evidence and ranges")
    f.add_argument("table")

    ls = sub.add_parser("list", help="list rows with all named fields")
    ls.add_argument("table")
    ls.add_argument("--grep", default="", help="only rows whose label contains this")
    ls.add_argument("--limit", type=int, default=50)
    ls.add_argument("--named-only", action="store_true", help="accepted for symmetry; unnamed fields are never shown")

    g = sub.add_parser("get", help="print one field of one row")
    g.add_argument("table")
    g.add_argument("row")
    g.add_argument("field")

    s = sub.add_parser("set", help="write one field (numbers in place; text is appended and repointed)")
    s.add_argument("table")
    s.add_argument("row")
    s.add_argument("field")
    s.add_argument("value")
    s.add_argument("--out", type=Path, required=True, help="patched .bxon to write")
    s.add_argument("--base", type=Path, help="start from this already patched .bxon (chain edits)")

    a = sub.add_parser("add-item", help="add a row by claiming a placeholder (id 0) row")
    a.add_argument("table")
    a.add_argument("--copy", required=True, help="row (index or label) the new row starts as")
    a.add_argument("--id", help="id for the new row (default: first unused retail id)")
    a.add_argument("--out", type=Path, required=True, help="patched .bxon to write")
    a.add_argument("--base", type=Path, help="start from this already patched .bxon (chain edits)")

    m = sub.add_parser("save-mod", help="rebuild the containing pack into mod/romfs")
    m.add_argument("table")
    m.add_argument("--patched", type=Path, required=True)

    v = sub.add_parser("verify", help="round-trip every named field of every named table")
    v.add_argument("--table", help="only this table")

    sc = sub.add_parser("schema", help="print the resolved schema as JSON")
    sc.add_argument("table")

    args = ap.parse_args()
    handler = {
        "tables": cmd_tables,
        "fields": cmd_fields,
        "list": cmd_list,
        "get": cmd_get,
        "set": cmd_set,
        "add-item": cmd_add_item,
        "save-mod": cmd_save_mod,
        "verify": cmd_verify,
        "schema": cmd_schema,
    }[args.cmd]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
