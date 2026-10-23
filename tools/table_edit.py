#!/usr/bin/env python3
"""Read and edit game tables by row and field *name* instead of byte offset.

Field names come from `tools/table_schemas.json` (only fields with recorded
evidence are named). Edits are same-size scalar writes, so the patched table can
go straight back into its pack with `tools/patch_asset.py`.

    python tools/table_edit.py fields syscmn/item.json
    python tools/table_edit.py list syscmn/item.json --grep boomerang
    python tools/table_edit.py get syscmn/item.json "Medicinal herb" buy_price
    python tools/table_edit.py set syscmn/item.json "Medicinal herb" buy_price 5 --out build/item.bxon

Rows can be given as an index (`#12` or `12`), an English name (from the
translation workspace, when present) or the Japanese name.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "game_assets" / "tables" / "packs"
SOURCES = ROOT / "game_data" / "packs"
SCHEMAS = ROOT / "tools" / "table_schemas.json"
DB = Path(r"..\reference project\workspace\project.db")

SCALARS = {"u8": "<B", "u16": "<H", "u32": "<I", "s32": "<i", "f32": "<f"}
RUBY = re.compile("\x01(.*?)\x02.*?\x03", re.S)


def load_schema(table: str) -> dict:
    schemas = json.loads(SCHEMAS.read_text(encoding="utf-8"))
    if table not in schemas:
        known = ", ".join(k for k in schemas if not k.startswith("_"))
        raise SystemExit(f"no field names for {table} yet (known: {known})")
    return schemas[table]


def source_of(table: str) -> Path:
    return SOURCES / Path(table).with_suffix(".bxon")


def english_names() -> dict[str, str]:
    """Japanese plain text -> English, from the read-only translation workspace."""
    if not DB.is_file():
        return {}
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    rows = con.execute("select plain, translation from source where translation is not null").fetchall()
    con.close()
    return {plain: " ".join(t.split()) for plain, t in rows}


class Table:
    def __init__(self, table: str):
        self.name = table
        self.schema = load_schema(table)
        self.rows = json.loads((TABLES / table).read_text(encoding="utf-8"))["root"]
        self.source = source_of(table)
        self.raw = bytearray(self.source.read_bytes())
        self._english: dict[str, str] | None = None

    def field(self, name: str) -> dict:
        fields = self.schema["fields"]
        if name not in fields:
            raise SystemExit(f"unknown field {name!r}; known: {', '.join(fields)}")
        return fields[name]

    def address(self, row: int, field: dict) -> int:
        return int(self.rows[row]["$offset"], 16) + int(field["offset"], 16)

    def value(self, row: int, name: str):
        field = self.field(name)
        if field["type"] == "string":
            cell = self.rows[row].get(f"+0x{int(field['offset'], 16):02X}", {})
            if "$string" in cell:
                return RUBY.sub(r"\1", cell["$string"]).replace("\n", " ")
            preview = cell.get("$preview")
            return bytes.fromhex(preview).split(b"\0")[0].decode("ascii", "ignore") if preview else ""
        fmt = SCALARS[field["type"]]
        return struct.unpack_from(fmt, self.raw, self.address(row, field))[0]

    def label(self, row: int) -> str:
        key = self.schema.get("row_name")
        if not key:
            return f"#{row}"
        jp = self.value(row, key)
        if self._english is None:
            self._english = english_names()
        return self._english.get(jp.replace(" ", "\n"), self._english.get(jp, jp))

    def find(self, spec: str) -> int:
        text = spec.lstrip("#")
        if text.isdigit():
            return int(text)
        wanted = spec.casefold()
        for i in range(len(self.rows)):
            if wanted in (self.label(i).casefold(), str(self.value(i, self.schema["row_name"])).casefold()):
                return i
        raise SystemExit(f"no row named {spec!r}")

    def set(self, row: int, name: str, value: str) -> None:
        field = self.field(name)
        if field["type"] == "string":
            raise SystemExit("strings are read-only here: a longer string changes the file size")
        fmt = SCALARS[field["type"]]
        number = float(value) if field["type"] == "f32" else int(value, 0)
        struct.pack_into(fmt, self.raw, self.address(row, field), number)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fields", help="list named fields and their evidence")
    f.add_argument("table")
    ls = sub.add_parser("list", help="list rows with all named fields")
    ls.add_argument("table")
    ls.add_argument("--grep", default="", help="only rows whose name contains this")
    ls.add_argument("--limit", type=int, default=50)
    g = sub.add_parser("get", help="print one field of one row")
    g.add_argument("table")
    g.add_argument("row")
    g.add_argument("field")
    s = sub.add_parser("set", help="write one numeric field (same-size patch)")
    s.add_argument("table")
    s.add_argument("row")
    s.add_argument("field")
    s.add_argument("value")
    s.add_argument("--out", type=Path, required=True, help="patched .bxon to write")
    s.add_argument("--base", type=Path, help="start from this already patched .bxon (chain edits)")
    args = ap.parse_args()

    table = Table(args.table)
    if args.cmd == "fields":
        for name, spec in table.schema["fields"].items():
            print(f"{name:14} {spec['offset']:>5} {spec['type']:6} {spec['evidence']}")
    elif args.cmd == "list":
        names = list(table.schema["fields"])
        shown = 0
        for i in range(len(table.rows)):
            label = table.label(i)
            if args.grep.casefold() not in label.casefold():
                continue
            values = "  ".join(f"{n}={table.value(i, n)}" for n in names if n != table.schema.get("row_name"))
            print(f"#{i:<5} {label:32.32}  {values}")
            shown += 1
            if shown >= args.limit:
                break
    elif args.cmd == "get":
        print(table.value(table.find(args.row), args.field))
    else:
        if args.base:
            table.raw = bytearray(args.base.read_bytes())
        row = table.find(args.row)
        before = table.value(row, args.field)
        table.set(row, args.field, args.value)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(bytes(table.raw))
        print(f"{table.label(row)}: {args.field} {before} -> {table.value(row, args.field)}  ({args.out}, same size)")
        print(f"put it back with: python tools/patch_asset.py --pack <pack> --member {table.source.name} "
              f"--replacement {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
