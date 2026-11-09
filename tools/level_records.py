#!/usr/bin/env python3
"""Add, duplicate and delete records in a level3d.bxon without moving any existing data.

A BXON file is a sequence of allocations, each introduced by a ``&&&&`` marker.
Arrays are described by a (count, self-relative pointer) pair whose target block is
exactly ``count * element_size`` bytes (see ``tools/bxon_struct.py``).  Growing an
array in place would shift every block behind it and force every pointer that
crosses the gap to be rewritten, which is only safe with a full schema.  This tool
does not do that.  To change an array it

1. copies the array block to the *end* of the file, with the element appended or
   removed,
2. rewrites the array's descriptor (count and pointer) to the new block,
3. re-computes the self-relative pointers *inside the copied elements* (their own
   position changed), and deep-copies the child arrays of a new element so the copy
   does not share mutable data with the original.

The old block stays where it was, unreferenced.  Nothing else in the file moves, so
no other pointer needs fixing and the indices of the other records do not change
when a record is appended.

The unit that is copied or removed for a record R:

* R's own array when it holds more than one element (e.g. six 120-byte transforms),
* otherwise the enclosing element of the parent array (a 96-byte wrapper that owns a
  one-element array holding a 68-byte placement), because that is what the level
  data treats as one object.

Verification.  The decoder in ``bxon_struct`` recognises a pointer by a heuristic: any
word whose self-relative target is a block start.  In bytes that were just written, a
small number can accidentally satisfy that.  So the result is decoded again with the
pointers this tool wrote (and none of the heuristic guesses in the new region), and the
tree must equal the old tree with exactly the intended array change.  Existing bytes may
change only in the rewritten descriptor.  If a check fails the operation raises and
nothing is written.

    python -m tools.level_records b001_101a duplicate 0xF18
    python -m tools.level_records b001_101a delete 0x928
    python -m tools.level_records --selftest            # every level, every record
"""
from __future__ import annotations

import argparse
import copy
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bxon_struct import StructDecoder  # noqa: E402

MARK = b"&&&&"
M32 = 0xFFFFFFFF
MAX_WRAPPER = 256  # element size above which a record is a container, not a wrapper


class RecordError(Exception):
    pass


class GuidedDecoder(StructDecoder):
    """A structural decoder that trusts only known pointers in the bytes this tool appended.

    ``base_len`` is the length of the original file.  A word in the appended region is a
    pointer only if it is in ``known``; a word in the original region may not point into the
    appended region unless it is in ``known`` (that is how a rewritten descriptor reaches its
    new block).  Everywhere else the stock heuristic applies.
    """

    def __init__(self, data: bytes, known: set[int], base_len: int):
        self.known = known
        self.base_len = base_len  # needed by _find_blocks, which the base constructor calls
        super().__init__(data)

    def _find_blocks(self):
        """Every ``&&&&`` at a 4-aligned offset starts a block.

        The stock scan jumps ``find()`` hits by four bytes, so a stray ``&&`` at the end of the
        previous block (``&&&&&&``) hides the real, aligned marker behind it.
        """
        from tools.bxon_struct import Block

        data = self.data
        starts = [p + 4 for p in range(0x20, len(data) - 3, 4) if data[p : p + 4] == MARK]
        for i, start in enumerate(starts):
            end = (starts[i + 1] - 4) if i + 1 < len(starts) else len(data)
            if start < self.base_len:
                # aligning the first appended marker pads the original last block; keep its original size
                end = min(end, self.base_len)
            self.blocks[start] = Block(start, start - 4, end, data)

    def _target(self, field: int, value: int):
        if field in self.known:
            return super()._target(field, value)
        if field >= self.base_len:
            return None
        target = super()._target(field, value)
        if target is not None and target >= self.base_len:
            return None
        return target


class _NoSeen:
    """Disables the decoder's de-duplication of repeated blocks.

    The stock decoder prints a block only the first time it meets it and a ``$ref`` stub
    afterwards.  A deep copy turns shared blocks into separate ones, so before/after trees only
    compare equal when every occurrence is expanded.
    """

    def __contains__(self, _key) -> bool:
        return False

    def add(self, _key) -> None:
        pass


# ---------------------------------------------------------------------------
# structure walk
# ---------------------------------------------------------------------------
class Array:
    """One array descriptor: count at ``desc``, self-relative pointer at ``desc + 4``."""

    def __init__(self, desc: int, block: int, count: int, esize: int, parent: "Array | None", parent_index: int):
        self.desc = desc
        self.block = block
        self.count = count
        self.esize = esize
        self.parent = parent
        self.parent_index = parent_index  # index of the parent's element that owns this descriptor

    def contains(self, offset: int) -> bool:
        return self.block <= offset < self.block + self.count * self.esize

    def element_of(self, offset: int) -> int:
        return (offset - self.block) // self.esize


class Level:
    def __init__(self, raw: bytes):
        self.raw = bytearray(raw)
        self.base_len = len(raw)
        self.known: set[int] = set()
        self.redirect: dict[int, int] = {}
        # byte ranges created by the last duplicate (the new element and its cloned child blocks)
        self.new_ranges: list[tuple[int, int]] = []
        self.refresh()

    # -- reading -----------------------------------------------------------
    def decoder(self, no_seen: bool = False) -> GuidedDecoder:
        dec = GuidedDecoder(bytes(self.raw), self.known, self.base_len)
        if no_seen:
            dec._seen = _NoSeen()
        return dec

    def refresh(self) -> None:
        self.dec = self.decoder()
        self.arrays: dict[int, Array] = {}
        count = struct.unpack_from("<I", self.raw, 0x20)[0]
        ptr = struct.unpack_from("<I", self.raw, 0x24)[0]
        block = self.dec._target(0x24, ptr)
        if block is None or not count:
            raise RecordError("this BXON has no root array")
        size = self.dec.blocks[block].size
        esize = size // count if size % count == 0 else size
        self._visit(Array(0x20, block, count if size % count == 0 else 1, esize, None, 0))

    def _visit(self, arr: Array) -> None:
        if arr.desc in self.arrays:
            return
        self.arrays[arr.desc] = arr
        for i in range(arr.count):
            base = arr.block + i * arr.esize
            off = 0
            while off + 4 <= arr.esize:
                sub = self.dec._array_descriptor(base, off) if off + 8 <= arr.esize else None
                if sub is not None:
                    target, count, esize = sub
                    self._visit(Array(base + off, target, count, esize, arr, i))
                    off += 8
                    continue
                off += 4

    def pointer_fields(self, base: int, size: int) -> list[tuple[int, int, str, tuple[int, int] | None]]:
        """(offset, target block, kind, (count, esize) for arrays) for every pointer in one element."""
        out = []
        off = 0
        while off + 4 <= size:
            sub = self.dec._array_descriptor(base, off) if off + 8 <= size else None
            if sub is not None:
                target, count, esize = sub
                out.append((off, target, "array", (count, esize)))
                off += 8
                continue
            v = struct.unpack_from("<I", self.raw, base + off)[0]
            target = self.dec._target(base + off, v)
            if target is not None:
                out.append((off, target, "ref", None))
            off += 4
        return out

    def resolve(self, offset: int) -> int:
        seen = 0
        while offset in self.redirect and seen < 64:
            offset = self.redirect[offset]
            seen += 1
        return offset

    def array_of(self, offset: int) -> Array:
        best = None
        for arr in self.arrays.values():
            if arr.contains(offset) and (best is None or arr.esize < best.esize):
                best = arr
        if best is None:
            raise RecordError(f"offset 0x{offset:X} is not inside any live array of this level")
        return best

    def unit_for(self, offset: int) -> tuple[Array, int]:
        """The (array, element index) that is copied or removed for the record at ``offset``."""
        offset = self.resolve(offset)
        arr = self.array_of(offset)
        # A one-element array that sits inside a small wrapper record (a 96-byte wrapper owning a 68-byte
        # placement) is copied together with its wrapper. Never go up to a layer *container* (1,092 bytes):
        # duplicating a whole container crashes the game while the field loads (emulator, 2026-11-02),
        # while appending a record to its own array works.
        if arr.count == 1 and arr.parent is not None and arr.parent.esize <= MAX_WRAPPER:
            return arr.parent, arr.parent_index
        return arr, arr.element_of(offset)

    # -- allocation ---------------------------------------------------------
    def _append_block(self, payload: bytes) -> int:
        while len(self.raw) % 4:
            self.raw.append(0)
        self.raw += MARK
        start = len(self.raw)
        self.raw += payload
        return start

    def _fix_pointers(self, src_base: int, esize: int, dst_base: int, deep: bool) -> None:
        """The element copied from ``src_base`` to ``dst_base`` keeps its pointers' targets.

        ``deep`` also copies the child arrays, so a duplicate does not share them.
        """
        for off, target, kind, geom in self.pointer_fields(src_base, esize):
            new_target = target
            if deep and kind == "array":
                count, child_esize = geom
                new_target = self._clone_array_block(target, count, child_esize)
            field = dst_base + off + (4 if kind == "array" else 0)
            struct.pack_into("<I", self.raw, field, (new_target - field) & M32)
            self.known.add(field)

    def _clone_array_block(self, block: int, count: int, esize: int) -> int:
        payload = bytes(self.raw[block : block + count * esize])
        new_block = self._append_block(payload)
        self.new_ranges.append((new_block, new_block + len(payload)))
        for i in range(count):
            self._fix_pointers(block + i * esize, esize, new_block + i * esize, deep=True)
        return new_block

    # -- array rewrite ---------------------------------------------------------
    def _rewrite(self, arr: Array, order: list[tuple[str, int]]) -> int:
        """Copy ``arr`` to the end of the file with the elements in ``order``.

        ``order`` items are ("keep", old index) or ("copy", old index) (a deep copy).
        Returns the new block address.
        """
        payload = b"".join(bytes(self.raw[arr.block + i * arr.esize : arr.block + (i + 1) * arr.esize]) for _, i in order)
        new_block = self._append_block(payload)
        for j, (mode, i) in enumerate(order):
            src = arr.block + i * arr.esize
            dst = new_block + j * arr.esize
            self._fix_pointers(src, arr.esize, dst, deep=(mode == "copy"))
            if mode == "keep":
                self.redirect[src] = dst
        struct.pack_into("<I", self.raw, arr.desc, len(order))
        struct.pack_into("<I", self.raw, arr.desc + 4, (new_block - (arr.desc + 4)) & M32)
        self.known.add(arr.desc + 4)
        return new_block

    # -- public operations ----------------------------------------------------------
    def duplicate(self, offset: int) -> int:
        """Append a deep copy of the unit that owns the record at ``offset``; returns its element address."""
        arr, index = self.unit_for(offset)
        if arr.esize > MAX_WRAPPER * 2:
            raise RecordError("refusing to duplicate a whole layer container: the game crashes on it")
        order = [("keep", i) for i in range(arr.count)] + [("copy", index)]
        self.new_ranges = []
        new_block = self._rewrite(arr, order)
        element = new_block + arr.count * arr.esize
        self.new_ranges.append((element, element + arr.esize))
        return element

    def delete(self, offset: int) -> None:
        arr, index = self.unit_for(offset)
        if arr.count <= 1:
            raise RecordError("cannot delete the only element of an array")
        order = [("keep", i) for i in range(arr.count) if i != index]
        self._rewrite(arr, order)

    def finish(self) -> bytes:
        self.refresh()
        return bytes(self.raw)


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
def normalise(node):
    """The decoded tree without any file offsets, for before/after comparison."""
    if isinstance(node, dict):
        if "$array" in node:
            items = node["items"]
            items = items if isinstance(items, list) else [items]
            return ("A", tuple(normalise(i) for i in items))
        if "$string" in node:
            return ("S", node["$string"])
        if "$ref" in node and "$size" in node and "$count" not in node:
            return ("R", node["$size"], node.get("$preview"))
        if "$ref" in node:
            return ("RR", node.get("$count"), node.get("$size"))
        return tuple((k, normalise(v)) for k, v in node.items() if not k.startswith("$"))
    if isinstance(node, list):
        return tuple(normalise(i) for i in node)
    return node


def _element_list(node):
    return node if isinstance(node, list) else [node]


def _expected_tree(old_root, arr: Array, op: str, index: int):
    """The old decoded tree with exactly the intended change applied to ``arr``."""
    expected = copy.deepcopy(old_root)
    chain = []
    cur = arr
    while cur is not None:
        chain.append(cur)
        cur = cur.parent
    chain.reverse()
    elems = _element_list(expected)
    field = None
    for a in chain[1:]:
        rec = elems[a.parent_index]
        base = int(rec["$offset"], 16)
        field = rec[f"+0x{a.desc - base:02X}"]
        elems = _element_list(field["items"])
    if op == "duplicate":
        elems.append(copy.deepcopy(elems[index]))
    else:
        elems.pop(index)
    if field is None:
        return elems
    field["items"] = elems if len(elems) != 1 else elems[0]
    field["count"] = len(elems)
    return expected


def _root_of(level: Level, raw: bytes, known: set[int]):
    dec = GuidedDecoder(raw, known, level.base_len)
    dec._seen = _NoSeen()
    return dec.decode()["root"]


def verify(before: bytes, after: bytes, level: Level, known_before: set[int], arr: Array, op: str, index: int) -> None:
    """The decoded tree must equal the old one with exactly the intended array change."""
    expected = _expected_tree(_root_of(level, before, known_before), arr, op, index)
    got = _root_of(level, after, level.known)
    if arr.parent is None:
        same = tuple(normalise(e) for e in expected) == tuple(normalise(e) for e in _element_list(got))
    else:
        same = normalise(expected) == normalise(got)
    if not same:
        raise RecordError(f"{op}: the rebuilt level does not decode to the expected tree")
    # nothing that was already in the file may change except the rewritten descriptor
    allowed = set(range(arr.desc, arr.desc + 8))
    for i in range(len(before)):
        if before[i] != after[i] and i not in allowed:
            raise RecordError(f"{op}: existing data was modified outside the array descriptor")


# ---------------------------------------------------------------------------
# operations on bytes
# ---------------------------------------------------------------------------
def apply_ops(raw: bytes, ops: list[dict]) -> tuple[bytes, list[dict]]:
    """Apply ``[{"op": "duplicate"|"delete", "offset": "0x..", "set": {...}, "shape": 68|120}]`` in order.

    Offsets are those of the *original* file: a record that an earlier operation moved is found
    again through the relocation map.  Returns the new bytes and, per operation, where the new
    data starts.
    """
    level = Level(raw)
    results: list[dict] = []
    for op in ops:
        kind = op["op"]
        offset = int(str(op["offset"]), 16)
        before = level.finish()
        known_before = set(level.known)
        arr, index = level.unit_for(offset)
        region_start = len(before)
        if kind == "duplicate":
            level.duplicate(offset)
        elif kind == "delete":
            masked = arr is not None and arr.esize == 100 and arr.count == 1
            if masked:
                # the only record of its array cannot be removed from the array; the game's ingest loop skips a record whose
                # layer-mask byte (+0x5F) is 0, which is a clean delete (emulator-proven on the Heliodor priest, docs/LEVEL_FORMAT.md)
                level.raw[arr.block + index * arr.esize + 0x5F] = 0
            else:
                level.delete(offset)
        else:
            raise RecordError(f"unknown operation {kind!r}")
        after = level.finish()
        if not (kind == "delete" and arr is not None and arr.esize == 100 and arr.count == 1):
            verify(before, after, level, known_before, arr, kind, index)
        if kind == "duplicate" and op.get("set"):
            level.raw = bytearray(_set_new_transform(level, after, region_start, op))
            after = level.finish()
        results.append({"op": kind, "source": f"0x{offset:X}", "new_region": [region_start, len(after)]})
    return level.finish(), results


def _set_new_transform(level: Level, raw: bytes, region_start: int, op: dict) -> bytes:
    """Write position / scale / rotation (``op["set"]``) into the copied record of a duplicate."""
    from tools.map_tool import candidate_objects

    wanted = op["set"]
    shape = op.get("shape")
    struct_data = level.decoder().decode()
    def in_new_element(offset: int) -> bool:
        return any(a <= offset < b for a, b in level.new_ranges)

    found = [
        o for o in candidate_objects(struct_data, raw)
        if in_new_element(int(o["record_offset"], 16)) and (shape is None or o["shape"] == shape)
    ]
    if not found:
        raise RecordError("the duplicate has no record to place (no matching shape in the new region)")
    target = found[0]
    out = bytearray(raw)
    for key in ("position", "scale", "rotation"):
        values = wanted.get(key)
        offsets = target["field_offsets"].get(key)
        if values is None or offsets is None:
            continue
        for value, off in zip(values, offsets):
            struct.pack_into("<f", out, int(off, 16), float(value))
        if key == "position":
            for value, off in zip(values, target["field_offsets"].get("position_shadow", [])):
                struct.pack_into("<f", out, int(off, 16), float(value))
    # typed properties by name: {"props": {"entity id": 108}}
    wanted_props = wanted.get("props") or {}
    for prop in target.get("props", []):
        if prop["name"] in wanted_props and prop.get("editable", True):
            from tools.map_tool import write_edit

            write_edit(out, int(prop["offset"], 16), {"type": prop["type"], "value": wanted_props[prop["name"]]})
    return bytes(out)


def reset() -> None:
    """Kept for callers of the previous API; the relocation map now lives in each ``Level``."""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def selftest(limit_per_level: int = 4) -> int:
    from tools.map_tool import candidate_objects, DATA_DIR

    root = DATA_DIR / "packs" / "level3d"
    levels = sorted(p for p in root.iterdir() if (p / "level3d.bxon").is_file()) if root.is_dir() else []
    ok = bad = 0
    for lv in levels:
        raw = (lv / "level3d.bxon").read_bytes()
        objs = candidate_objects(StructDecoder(raw).decode(), raw)
        for obj in objs[:limit_per_level]:
            for op in ("duplicate", "delete"):
                try:
                    apply_ops(raw, [{"op": op, "offset": obj["record_offset"]}])
                    ok += 1
                except RecordError as e:
                    if "only element" in str(e):
                        continue
                    bad += 1
                    print(f"{lv.name} {op} {obj['record_offset']}: {e}")
    print(f"{ok} operations verified, {bad} refused")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("level", nargs="?")
    ap.add_argument("op", nargs="?", choices=["duplicate", "delete"])
    ap.add_argument("offset", nargs="?")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not (args.level and args.op and args.offset):
        ap.error("level, op and offset are required")
    from tools.map_tool import DATA_DIR

    src = DATA_DIR / "packs" / "level3d" / args.level / "level3d.bxon"
    data, _ = apply_ops(src.read_bytes(), [{"op": args.op, "offset": args.offset}])
    out = args.out or Path(f"{args.level}.{args.op}.bxon")
    out.write_bytes(data)
    print(f"{args.op} 0x{int(args.offset, 16):X}: {len(data) - src.stat().st_size:+d} bytes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
