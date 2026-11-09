#!/usr/bin/env python3
"""Add rows to a BXON parameter table (items, shops, spells, enemies, ...).

Why this needs more than a byte patch
-------------------------------------
A BXON table is an array of fixed-size records followed by the blocks those
records point at (names, descriptions, icon ids, sub-arrays).  Every pointer is a
*self-relative* 32-bit value: ``target = field_position + value``.  Adding a row
means the array gets longer, so every block behind it moves — and every pointer
that crosses the moved region has to be corrected.

This tool inserts the new rows at the end of the array and shifts the rest of the
file by ``row_size`` bytes.  That is the layout with the smallest possible side
effects (one row of growth, not a copy of the whole string pool), and it keeps
the retail array at its old address, so anything that was pointing at a row (or
at the table's blocks) stays valid:

* rows live before the insertion point, so their positions do not change;
* a row pointer whose target lies behind the insertion point moves by ``delta``
  and is rewritten; a pointer to something in front of it is left alone;
* blocks behind the insertion point all move by the same ``delta``, so any
  pointer *between* them keeps its relative value — nothing to do;
* the string blocks of the new rows are copies of the row the modder duplicated,
  so editing the new row's name does not rename the original.

What the caller must supply
---------------------------
The list of pointer fields in a row.  A wrong list would move numeric data that
happens to look like a pointer, so it is **not** guessed from the bytes: it comes
from ``tools/table_schemas.json`` (every field of type ``string``) or from
``--pointer-offsets`` for a table that has no schema yet.  The row size is
cross-checked against the table's own array geometry.

Every result is re-parsed and compared with the original before it is returned:
all old rows must decode to the same numbers and the same strings, and the new
rows must decode to a copy of their source row.  If a check fails the tool raises
instead of writing a table the game would misread.

Usage
-----
    python -m tools.bxon_grow --table syscmn/item.json --rows 1 \\
        --set id=8190 --set buy_price=1999999 --out build/item_grown.bxon
    python -m tools.bxon_grow --table syscmn/item.json --rows 1 --save-mod
    python -m tools.bxon_grow --list
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bxon import MARK, Bxon  # noqa: E402

END_OF_CHAIN = 0xFFFFFFFF
ROOT_COUNT = 0x20
ROOT_POINTER = 0x24
M32 = 0xFFFFFFFF


def _align4(n: int) -> int:
    return (n + 3) & ~3


def _block_payload(data: bytes, start: int) -> bytes:
    """The bytes of the block that starts at ``start`` (up to the next MARK)."""
    nxt = data.find(MARK, start)
    end = len(data) if nxt < 0 else nxt
    return data[start:end]


def _root_geometry(data: bytes) -> tuple[int, int, int]:
    """(row count, array offset, array end) of the BXON root array."""
    if data[:4] != b"BXON":
        raise ValueError("not a BXON file")
    count, rel = struct.unpack_from("<II", data, ROOT_COUNT)
    if not count or not rel or count > 1_000_000:
        raise ValueError("this BXON has no root row array")
    root = (ROOT_POINTER + rel) & M32
    if root + 4 > len(data) or root % 4:
        raise ValueError(f"root array offset 0x{root:X} is not inside the file")
    nxt = data.find(MARK, root)
    end = len(data) if nxt < 0 else nxt
    return count, root, end


def pointer_offsets_from_schema(table: str) -> tuple[int, int, list[int]]:
    """(row size, pointer offsets) for a schema table, from table_schemas.json."""
    from tools.table_edit import Schemas

    spec = Schemas().get(table)
    if spec is None:
        raise ValueError(f"no schema for {table}; pass --pointer-offsets and --row-size")
    row_size = int(spec["row_size"])
    offsets = []
    for field in spec["fields"]:
        if field["type"] != "string":
            continue
        off = int(field["offset"])
        if off % 4:
            raise ValueError(f"{table}: string field {field['name']} at +{off} is not 4-byte aligned")
        offsets.append(off)
    return row_size, sorted(set(offsets))


def grow_table(data: bytes, row_size: int, pointer_offsets: list[int],
               rows: int = 1, source_row: int = -1, at: int = -1) -> bytes:
    """Return ``data`` with ``rows`` extra records inserted into the root array.

    ``at`` is the row index the new records are inserted before (``-1`` appends at
    the end).  Appending is the smallest change, but some tables end with empty
    placeholder rows that the engine may stop at, so a modder can insert before
    them with ``at``.
    """
    if rows < 1:
        raise ValueError("rows must be >= 1")
    if row_size <= 0 or row_size % 4:
        raise ValueError(f"row size {row_size} is not a positive multiple of 4")
    bad = [o for o in pointer_offsets if o % 4 or not 0 <= o <= row_size - 4]
    if bad:
        raise ValueError(
            f"pointer offsets {bad} are not 4-byte aligned fields of a {row_size}-byte row")

    count, root, end = _root_geometry(data)
    if end - root != count * row_size:
        raise ValueError(
            f"root array is {end - root:,} bytes for {count:,} rows, which is not "
            f"{row_size} bytes per row; the schema does not match this table")
    if source_row < 0:
        source_row += count
    if not 0 <= source_row < count:
        raise ValueError(f"source row {source_row} is outside 0..{count - 1}")
    if at == -1:
        at = count
    elif at < 0:
        raise ValueError(f"insert position {at} is invalid")
    if not 0 <= at <= count:
        raise ValueError(f"insert position {at} is outside 0..{count}")

    delta = rows * row_size
    src = root + source_row * row_size
    src_row = data[src:src + row_size]
    # The string/block region moves by ``delta`` whatever the insertion point.
    # A new row's field position depends on where it lands, so each pointer is
    # recomputed against that position (self-relative values).
    new_rows = bytearray()
    for i in range(rows):
        row_pos = root + (at + i) * row_size
        row = bytearray(src_row)
        for off in pointer_offsets:
            value = struct.unpack_from("<I", row, off)[0]
            if not value:
                continue
            target = (src + off + value) & M32
            moved = target + delta if target >= end else target
            struct.pack_into("<I", row, off, (moved - (row_pos + off)) & M32)
        new_rows += row

    # Build the new array first, then rewrite the pointers of the rows that moved.
    out = bytearray(data[:root])
    out += data[root:root + at * row_size]
    out += new_rows
    out += data[root + at * row_size:end]
    for r in range(count):
        new_r = r if r < at else r + rows
        old_pos = root + r * row_size
        pos = root + new_r * row_size
        for off in pointer_offsets:
            value = struct.unpack_from("<I", data, old_pos + off)[0]
            if not value:
                continue
            target = (old_pos + off + value) & M32
            moved = target + delta if target >= end else target
            struct.pack_into("<I", out, pos + off, (moved - (pos + off)) & M32)
    out += data[end:]
    struct.pack_into("<I", out, ROOT_COUNT, count + rows)
    grown = bytes(out)
    verify_growth(data, grown, row_size, pointer_offsets, rows, source_row, at=at)
    return grown


def verify_growth(old: bytes, new: bytes, row_size: int, pointer_offsets: list[int],
                  rows: int, source_row: int, edited_words: set[int] | None = None,
                  at: int = -1) -> dict:
    """Prove the grown table decodes to the old table plus the new rows.

    Raises ``ValueError`` on the first difference.  Returns a small summary for
    the CLI report.
    """
    old_count, old_root, old_end = _root_geometry(old)
    new_count, new_root, new_end = _root_geometry(new)
    if new_root != old_root:
        raise ValueError(f"the row array moved (0x{old_root:X} -> 0x{new_root:X})")
    if new_count != old_count + rows:
        raise ValueError(f"row count {new_count} != {old_count} + {rows}")
    if new_end - new_root != new_count * row_size:
        raise ValueError("the rebuilt root array is not (count + rows) * row_size bytes")
    if new_end != old_end + rows * row_size:
        raise ValueError("the array did not grow by exactly rows * row_size")
    if source_row < 0:
        source_row += old_count
    if at < 0:
        at = old_count

    def word(buf: bytes, pos: int) -> int:
        return struct.unpack_from("<I", buf, pos)[0]

    def block(buf: bytes, start: int) -> bytes:
        nxt = buf.find(MARK, start)
        return buf[start:len(buf) if nxt < 0 else nxt]

    def new_index(r: int) -> int:
        return r if r < at else r + rows

    # every old row: same numbers, same strings (the strings may have moved)
    for r in range(old_count):
        nr = new_index(r)
        for off in range(0, row_size, 4):
            o = word(old, old_root + r * row_size + off)
            n = word(new, new_root + nr * row_size + off)
            if off in pointer_offsets:
                ot = (old_root + r * row_size + off + o) if o else 0
                nt = (new_root + nr * row_size + off + n) if n else 0
                if bool(ot) != bool(nt):
                    raise ValueError(f"row {r} field +{off} lost its string")
                if not nt:
                    continue
                if nt + 2 > len(new):
                    raise ValueError(f"row {r} field +{off} points outside the file")
                if block(old, ot) != block(new, nt):
                    raise ValueError(f"row {r} field +{off} changed its string")
            elif o != n:
                raise ValueError(f"row {r} field +{off} changed {o} -> {n}")

    edited_words = edited_words or set()
    src_row_off = old_root + source_row * row_size
    for i in range(rows):
        row_pos = new_root + (at + i) * row_size
        for off in range(0, row_size, 4):
            n = word(new, row_pos + off)
            o = word(old, src_row_off + off)
            if off in pointer_offsets:
                nt = (row_pos + off + n) if n else 0
                ot = (src_row_off + off + o) if o else 0
                if bool(nt) != bool(ot):
                    raise ValueError(f"new row {i} field +{off} lost its string")
                if nt and block(new, nt) != block(old, ot):
                    raise ValueError(f"new row {i} field +{off} string differs from the source row")
            elif o != n and off not in edited_words:
                raise ValueError(f"new row {i} field +{off} was not copied from the source row")

    # the file behind the array must be the retail bytes, shifted as one piece
    if new[new_end:] != old[old_end:]:
        raise ValueError("data behind the row array changed; that is not a pure insertion")

    return {"rows_before": old_count, "rows_after": new_count,
            "bytes_before": len(old), "bytes_after": len(new)}


# --------------------------------------------------------------------------- CLI
def _tables() -> list[str]:
    from tools.table_edit import Schemas

    return Schemas().names()


# --------------------------------------------------------------------------- items
# The engine only accepts an item table whose row count matches a constant in code.
# Pack_LoadMasterTables (0x00120464) loads item.bxon and item_kana_order.bxon and attaches
# each one only if its BXON header count (+0x20) equals the word at 0x00120778 (retail
# 0xB3B = 2875). A grown table that fails the check is silently dropped and every item
# lookup fails (empty shop lists). grow_items makes those three changes consistently, and the
# shop list renders again with them (emulator, 2026-10-26) -- but it is NOT sufficient yet:
# the new row itself still shows blank, battlecmn/battle_item.bxon also has 2875 rows, and
# 0xB3B occurs 36 times in code.bin (per-item array bounds/sizes, possibly save layout).
# Until those are mapped (orchestration/tasks/X6_item_table_growth.md), add items by
# reusing the 71 placeholder rows (id == 0) instead of growing the table.
ITEM_COUNT_LITERAL = 0x00120778   # address of the expected-count word in code.bin
CODE_BASE = 0x00100000            # code.bin is loaded at this address
COUNT_FIELD = 0x20                # BXON header word holding the root array count


def grow_kana_order(data: bytes, new_rows: list[int]) -> bytes:
    """Append item row indices to item_kana_order.bxon (u16 per item, kana sort order).

    The array is the last thing in the file, so appending needs no pointer fixes; the new
    items sort after every retail item, which is what the in-game "sort by name" shows.
    """
    count, root, end = _root_geometry(data)
    if end - root != count * 2 or end != len(data):
        raise ValueError("item_kana_order.bxon is not a trailing u16 array of its count")
    out = bytearray(data)
    for row in new_rows:
        out += struct.pack("<H", row)
    struct.pack_into("<I", out, COUNT_FIELD, count + len(new_rows))
    return bytes(out)


def patch_item_count(code: bytes, old_count: int, new_count: int) -> bytes:
    """Set the engine's expected item count (the word at ITEM_COUNT_LITERAL)."""
    off = ITEM_COUNT_LITERAL - CODE_BASE
    current = struct.unpack_from("<I", code, off)[0]
    if current != old_count:
        raise ValueError(f"code.bin item count at {ITEM_COUNT_LITERAL:#x} is {current}, "
                         f"expected {old_count}; refusing to patch an unknown executable")
    out = bytearray(code)
    struct.pack_into("<I", out, off, new_count)
    return bytes(out)


def grow_items(item: bytes, kana: bytes, code: bytes, rows: int = 1,
               source_row: int = 0) -> tuple[bytes, bytes, bytes, list[int]]:
    """Append ``rows`` copies of ``source_row`` to the item table, consistently.

    Returns (item.bxon, item_kana_order.bxon, code.bin, new row indices). Give the new rows a
    fresh ``id`` afterwards: retail ids are unique.
    """
    row_size, pointers = pointer_offsets_from_schema("syscmn/item.json")
    count = _root_geometry(item)[0]
    grown = grow_table(item, row_size, pointers, rows=rows, source_row=source_row, at=-1)
    new_rows = list(range(count, count + rows))
    return (grown, grow_kana_order(kana, new_rows),
            patch_item_count(code, count, count + rows), new_rows)


def claim_placeholder(data: bytes, row_size: int, pointer_offsets: list[int], source_row: int,
                      dest_row: int, id_offset: int, new_id: int) -> bytes:
    """Turn an unused row (``id == 0``) into a copy of ``source_row`` with a new id.

    This adds an item without changing the row count, so none of the engine's per-item
    limits (see grow_items) are touched. Pointer fields are self-relative, so they are
    re-aimed at the source row's targets instead of being copied as raw numbers; the new
    item therefore starts with the source item's name/description/icon strings.
    """
    count, root, end = _root_geometry(data)
    for row in (source_row, dest_row):
        if not 0 <= row < count:
            raise ValueError(f"row {row} is outside the table (0..{count - 1})")
    src = root + source_row * row_size
    dst = root + dest_row * row_size
    if struct.unpack_from("<H", data, dst + id_offset)[0] != 0:
        raise ValueError(f"row {dest_row} is not a placeholder (id != 0)")
    out = bytearray(data)
    out[dst:dst + row_size] = data[src:src + row_size]
    for off in pointer_offsets:
        value = struct.unpack_from("<i", data, src + off)[0]
        if value:
            struct.pack_into("<i", out, dst + off, src + off + value - (dst + off))
    struct.pack_into("<H", out, dst + id_offset, new_id)
    return bytes(out)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", help="schema table key, e.g. syscmn/item.json")
    ap.add_argument("--rows", type=int, default=1, help="how many rows to add (default 1)")
    ap.add_argument("--from-row", type=int, default=-1,
                    help="row to copy (default: the last row)")
    ap.add_argument("--at", type=int, default=-1,
                    help="insert the new rows before this row index (default: append; use it "
                         "to insert before trailing empty placeholder rows)")
    ap.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE",
                    help="set a numeric field of every new row (repeatable)")
    ap.add_argument("--pointer-offsets", metavar="N[,N...]",
                    help="row-relative offsets of the string pointers (schema tables infer this)")
    ap.add_argument("--row-size", type=int, help="row size in bytes (schema tables infer this)")
    ap.add_argument("--out", type=Path, help="write the grown BXON here")
    ap.add_argument("--save-mod", action="store_true",
                    help="also rebuild the containing PACK into mod/romfs")
    ap.add_argument("--list", action="store_true", help="list tables that have a schema")
    args = ap.parse_args(argv)

    if args.list:
        for name in _tables():
            row_size, offsets = pointer_offsets_from_schema(name)
            print(f"{name:40} {row_size:4} bytes/row  string pointers at "
                  + ", ".join(f"+{o}" for o in offsets))
        return 0
    if not args.table:
        ap.error("--table is required (or use --list)")

    from tools.table_edit import Table

    table = Table(args.table)
    if args.pointer_offsets:
        pointer_offsets = sorted({int(x) for x in args.pointer_offsets.split(",")})
        row_size = args.row_size or table.row_size
    else:
        row_size, pointer_offsets = pointer_offsets_from_schema(args.table)
        if args.row_size and args.row_size != row_size:
            ap.error(f"--row-size {args.row_size} contradicts the schema ({row_size})")

    before = bytes(table.raw)
    source_row = args.from_row
    if source_row == -1:
        # "append a row" should duplicate a real record, not the empty
        # placeholder rows that several tables (items, enemy slots) end with.
        label = (table.schema or {}).get("label")
        if label:
            try:
                spec = table.field(label)
                source_row = next((i for i in range(len(table) - 1, -1, -1)
                                   if str(table.read(i, spec)).strip()), -1)
            except Exception:                   # noqa: BLE001 - fall back to the last row
                source_row = -1
    grown = grow_table(before, row_size, pointer_offsets, rows=args.rows,
                       source_row=source_row, at=args.at)
    edited_words: set[int] = set()

    if args.set:
        from tools.table_edit import check_range

        editable = Table(args.table, grown)
        first_new = args.at if args.at >= 0 else len(editable) - args.rows
        rows_to_edit = range(first_new, first_new + args.rows)
        for spec in args.set:
            if "=" not in spec:
                ap.error(f"--set wants FIELD=VALUE, got {spec!r}")
            name, _, value = spec.partition("=")
            field = editable.field(name.strip())
            kind = field["type"]
            if kind == "string":
                ap.error(f"{name} is a string field; edit the text bank / use tools/text_tool.py")
            try:
                number = float(value) if kind == "f32" else int(value.strip(), 0)
            except ValueError:
                ap.error(f"{name} is {kind}; {value!r} is not a number")
            problem = check_range(field, number)
            if problem:
                ap.error(problem)
            for row in rows_to_edit:
                editable.write(row, field, number)
            edited_words.add(int(field["offset"]) & ~3)
        grown = bytes(editable.raw)

    summary = verify_growth(before, grown, row_size, pointer_offsets, args.rows,
                            source_row, edited_words=edited_words, at=args.at)
    parsed = Bxon.parse(grown)
    print(f"{args.table}: {summary['rows_before']} -> {summary['rows_after']} rows, "
          f"{summary['bytes_before']:,} -> {summary['bytes_after']:,} bytes, "
          f"{len(parsed.strings)} string blocks re-parse")
    added = Table(args.table, grown)
    first_new = args.at if args.at >= 0 else len(added) - args.rows
    label = (added.schema or {}).get("label")
    if label:
        try:
            spec = added.field(label)
            value = added.read(first_new, spec)
            print(f"  new row {first_new}: {value!r}")
        except Exception:                       # noqa: BLE001 - a label is only a nicety
            pass

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(grown)
        print(f"  wrote {args.out}")
    if args.save_mod:
        from tools.export_mod import stage_member
        from tools.table_edit import pack_of

        pack, member = pack_of(args.table)
        work = ROOT / "build" / "staged" / "bxon_grow"
        tmp = work / member
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(grown)
        info = stage_member(pack, member, tmp, ROOT / "mod", work_dir=work)
        print(f"  staged {member} in {pack}: {info['original_size']:,} -> {info['size']:,} bytes")
        print(f"  -> {Path(info['mod_file']).relative_to(ROOT)}")
        print("  export with: python tools/export_mod.py --target 3ds   "
              "(a grown pack may not fit its RomFS slot, so Luma only works if it does)")
    if not args.out and not args.save_mod:
        print("  (no --out / --save-mod: nothing written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
