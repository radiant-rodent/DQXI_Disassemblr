#!/usr/bin/env python3
"""Rebuild the Level-3 metadata tables of a CTR RomFS so new files can be added.

The retail RomFS keeps files replaceable at any size (the exporter rewrites the
file entry's offset/size and appends grown data), but its metadata/hash tables
are sized for the retail tree, so a path that never existed cannot be mounted.
This module lays the tables out afresh:

  * the existing metadata bytes are kept as the head of the new tables, so
    every table offset that chains/pointers use stays valid;
  * new directories and files are appended and chained into the parents;
  * the -HT hash tables are recomputed, and the *unchanged* retail tree must
    reproduce them byte for byte — that is both a self-test of the name-hash
    model and a guard before anything is written;
  * the retail file data is not moved: new data is appended behind the retail
    Level-3 end, the relocated tables follow, the Level-3 header is repointed
    and the IVFC hash tree is rebuilt through tools/romfs_hash.

The RomFS name hash (3dbrew, SciresM's RomFS-Builder)::
    hash = parent_metadata_offset ^ 123456789
    for each UTF-16 unit:  hash = rotr32(hash, 5) ^ unit
Entry names are UTF-16LE in this game (most 3DS games use UTF-8).

Note for modders: the console only reads a new file when the game opens its
path, so an added file matters together with a native/script change.
"""
from __future__ import annotations

import struct
from pathlib import Path

from tools import romfs_hash

END_OF_CHAIN = 0xFFFFFFFF

DIR_ENTRY_FIXED = 0x18     # parent, sibling, child-dir, first-file, next-hash
FILE_ENTRY_FIXED = 0x20    # parent, sibling, u64 data offset, u64 size, next-hash


def calc_path_hash(name_bytes: bytes, parent_offset: int) -> int:
    h = parent_offset ^ 123456789
    for i in range(0, len(name_bytes), 2):
        h = ((h >> 5) | (h << 27)) & 0xFFFFFFFF
        h ^= name_bytes[i] | (name_bytes[i + 1] << 8)
    return h & 0xFFFFFFFF


def hash_table_entry_count(entries: int) -> int:
    count = entries
    if count < 3:
        count = 3
    elif count < 19:
        count |= 1
    else:
        while any(count % p == 0 for p in (2, 3, 5, 7, 11, 13, 17)):
            count += 1
    return count


def align16(x: int) -> int:
    return (x + 0xF) & ~0xF


class Level3:
    """Parsed Level-3 tables of a RomFS image (offsets measured from Level-3 start)."""

    def __init__(self, path: Path):
        with open(path, "rb") as f:
            head = f.read(romfs_hash.MASTER_OFF)
            self.ivfc = romfs_hash.parse_header(head)
            self.l3_start = self.ivfc["data_start"]       # absolute offset
            f.seek(self.l3_start)
            (self.header_size, self.dht_off, self.dht_len, self.dmt_off,
             self.dmt_len, self.fht_off, self.fht_len, self.fmt_off,
             self.fmt_len, self.data_off) = struct.unpack("<10I", f.read(40))
            f.seek(self.l3_start + self.dmt_off)
            self.dmt = f.read(self.dmt_len)
            f.seek(self.l3_start + self.fmt_off)
            self.fmt = f.read(self.fmt_len)

    def read_dirs(self) -> list[dict]:
        dirs, pos = [], 0
        while pos + DIR_ENTRY_FIXED <= len(self.dmt):
            parent, sib, child, first_file, next_hash, nlen = struct.unpack_from(
                "<6I", self.dmt, pos)
            name = self.dmt[pos + DIR_ENTRY_FIXED:pos + DIR_ENTRY_FIXED + nlen]
            dirs.append({"parent": parent, "sibling": sib, "child": child,
                         "first_file": first_file, "next": next_hash,
                         "name": name.decode("utf-16-le", "replace"), "off": pos})
            pos += DIR_ENTRY_FIXED + ((nlen + 3) & ~3)
        return dirs

    def read_files(self) -> list[dict]:
        files, pos = [], 0
        while pos + FILE_ENTRY_FIXED <= len(self.fmt):
            parent, sib, doff, dsize, next_hash, nlen = struct.unpack_from(
                "<IIQQII", self.fmt, pos)
            name = self.fmt[pos + FILE_ENTRY_FIXED:pos + FILE_ENTRY_FIXED + nlen]
            files.append({"parent": parent, "sibling": sib, "offset": doff,
                          "size": dsize, "next": next_hash,
                          "name": name.decode("utf-16-le", "replace"), "off": pos})
            pos += FILE_ENTRY_FIXED + ((nlen + 3) & ~3)
        return files


def _hash_table(entries: list[dict], buckets: int) -> bytes:
    """Bucket table for ``entries``, with each entry's ``next`` field re-linked.

    Insertion order is the table order (every later entry becomes the chain
    head), which is exactly how the retail tables were built — the self-test in
    :func:`rebuild_metadata` checks that on the unchanged image.  Re-linking the
    ``next`` field is not optional: a new entry that simply becomes the head
    while keeping ``next = END_OF_CHAIN`` cuts any older entry that hashes to
    the same bucket out of its chain, so an existing path stops resolving
    (204 directories in 211 buckets collide in the retail tree, and so do 5,566
    file buckets, so this would break lookups immediately).
    """
    table = [END_OF_CHAIN] * buckets
    for e in entries:
        h = calc_path_hash(e["name"].encode("utf-16-le"), e["parent"])
        bucket = h % buckets
        e["next"] = table[bucket]          # prepend: new entry becomes the head
        table[bucket] = e["off"]
    return b"".join(struct.pack("<I", v) for v in table)


def _write_next_fields(table: bytearray, entries: list[dict], field: int) -> None:
    """Store each entry's recomputed ``next`` chain value at ``off + field``."""
    for e in entries:
        struct.pack_into("<I", table, e["off"] + field, e["next"] & 0xFFFFFFFF)


def rebuild_metadata(dest: Path, additions: list[tuple[str, bytes]]) -> dict:
    """Extend the Level-3 tables of the RomFS image ``dest`` with new files.

    ``additions`` are ``(romfs path, data)`` with paths like ``/a/b/file.pack``;
    missing parent directories are created too.  The IVFC hash tree is rebuilt.
    Returns the placements plus verification.
    """
    l3 = Level3(dest)
    dirs = l3.read_dirs()
    files = l3.read_files()
    # Accept both ("/path", data) tuples and {"path", "data"} dicts, so callers
    # that already carry a change record do not have to translate it.
    if additions and not isinstance(additions[0], (tuple, list)):
        additions = [(a["path"], a["data"]) for a in additions]

    # Self-test: the name-hash model must reproduce the retail tables byte for
    # byte before this builder is allowed to invent anything.  The chain fields
    # are part of the model, so they are checked too.
    with open(dest, "rb") as f:
        f.seek(l3.l3_start + l3.dht_off)
        retail_dht = f.read(l3.dht_len)
        f.seek(l3.l3_start + l3.fht_off)
        retail_fht = f.read(l3.fht_len)
    retail_dir_next = {d["off"]: d["next"] for d in dirs}
    retail_file_next = {f["off"]: f["next"] for f in files}
    if _hash_table(dirs, l3.dht_len // 4) != retail_dht:
        raise RuntimeError("recomputed directory hash table does not match the "
                           "retail bytes (name-hash model wrong); refusing to add files")
    if any(d["next"] != retail_dir_next[d["off"]] for d in dirs):
        raise RuntimeError("recomputed directory chains do not match the retail "
                           "bytes (name-hash model wrong); refusing to add files")
    if _hash_table(files, l3.fht_len // 4) != retail_fht:
        raise RuntimeError("recomputed file hash table does not match the retail "
                           "bytes (name-hash model wrong); refusing to add files")
    if any(f["next"] != retail_file_next[f["off"]] for f in files):
        raise RuntimeError("recomputed file chains do not match the retail bytes "
                           "(name-hash model wrong); refusing to add files")

    def dir_for(dirpath: str) -> int:
        """Offset in the (about to be rebuilt) directory table of ``dirpath``;
        recursive parents are created on demand."""
        nonlocal new_dmt
        if dirpath in ("", "/"):
            return 0
        parts = [p for p in dirpath.strip("/").split("/") if p]
        parent = dir_for("/" + "/".join(parts[:-1]) if len(parts) > 1 else "")
        name = parts[-1]
        existing = next((d for d in dirs if d["parent"] == parent and d["name"] == name),
                        None)
        if existing is not None:
            return existing["off"]
        nlen = len(name) * 2
        off = len(new_dmt)
        new_dmt += struct.pack("<6I", parent, END_OF_CHAIN, END_OF_CHAIN,
                               END_OF_CHAIN, END_OF_CHAIN, nlen)
        new_dmt += name.encode("utf-16-le") + bytes((-(nlen)) % 4)
        dirs.append({"parent": parent, "sibling": END_OF_CHAIN, "child": END_OF_CHAIN,
                     "first_file": END_OF_CHAIN, "next": END_OF_CHAIN,
                     "name": name, "off": off})
        kids = sorted(d["off"] for d in dirs if d["parent"] == parent)
        # The root entry is its own parent (parent == off == 0), so it appears in
        # this list.  It is the directory being added to, not one of its siblings;
        # treating it as one writes the new child into the root's *sibling* field
        # and the new directory becomes unreachable.
        kids = [k for k in kids if k != parent]
        if len(kids) > 1:
            struct.pack_into("<I", new_dmt, kids[-2] + 4, off)   # old tail -> new
        else:
            struct.pack_into("<I", new_dmt, parent + 8, off)      # first child of parent
        return off

    new_fmt = bytearray(l3.fmt)
    new_dmt = bytearray(l3.dmt)
    placements: list[dict] = []
    data_pos = align16(l3.ivfc["data_size"] - l3.data_off)   # behind retail data

    for path, data in sorted(additions, key=lambda x: x[0]):
        dirpath, _, name = path.rstrip("/").rpartition("/")
        doff = dir_for(dirpath)
        nlen = len(name) * 2
        foff = len(new_fmt)
        new_fmt += struct.pack("<IIQQII", doff, END_OF_CHAIN, data_pos, len(data),
                               END_OF_CHAIN, nlen)
        new_fmt += name.encode("utf-16-le") + bytes((-(nlen)) % 4)
        first = struct.unpack_from("<I", new_dmt, doff + 0x0C)[0]
        struct.pack_into("<I", new_fmt, foff + 4, first)      # sibling chain
        struct.pack_into("<I", new_dmt, doff + 0x0C, foff)    # parent's first file
        files.append({"parent": doff, "sibling": END_OF_CHAIN, "offset": data_pos,
                      "size": len(data), "next": END_OF_CHAIN, "name": name,
                      "off": foff})
        placements.append({"path": path, "offset": data_pos,
                           "size": len(data), "payload": data})
        data_pos = align16(data_pos + len(data))
    if not placements:
        return {"placements": [], "ivfc": romfs_hash.verify(dest)}

    dht2 = _hash_table(dirs, hash_table_entry_count(len(dirs)))
    fht2 = _hash_table(files, hash_table_entry_count(len(files)))
    # The hash tables were just recomputed for the extended trees; store the new
    # chain heads in the entries themselves before freezing the metadata bytes.
    _write_next_fields(new_dmt, dirs, 0x10)   # dir entry: next hash before the name length
    _write_next_fields(new_fmt, files, 0x18)  # file entry: next hash before the name length
    dmt = bytes(new_dmt)
    fmt = bytes(new_fmt)
    blocks = (dht2, dmt, fht2, fmt)

    tables_start = l3.l3_start + l3.data_off + data_pos   # behind retail data
    abs_offsets = []
    pos = tables_start
    for blk in blocks:
        abs_offsets.append(pos)
        pos += len(blk)
    new_l3_len = pos - l3.l3_start

    romfs_hash.resize_data(dest, new_l3_len)
    with open(dest, "r+b") as f:
        for pl in placements:
            f.seek(l3.l3_start + l3.data_off + pl["offset"])
            f.write(pl["payload"])
        for off, blk in zip(abs_offsets, blocks):
            f.seek(off)
            f.write(blk)
        header = struct.pack("<10I", 0x28,
                             abs_offsets[0] - l3.l3_start, len(blocks[0]),
                             abs_offsets[1] - l3.l3_start, len(blocks[1]),
                             abs_offsets[2] - l3.l3_start, len(blocks[2]),
                             abs_offsets[3] - l3.l3_start, len(blocks[3]),
                             l3.data_off)
        f.seek(l3.l3_start)
        f.write(header)
    report = romfs_hash.rebuild(dest)
    check = romfs_hash.verify(dest)
    if not check["ok"]:
        raise RuntimeError(f"rebuilt RomFS failed IVFC verification: {check}")
    return {"placements": placements, "ivfc": check, "romfs_size": report["romfs_size"]}
