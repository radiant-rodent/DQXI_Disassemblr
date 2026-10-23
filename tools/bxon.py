#!/usr/bin/env python3
"""tools/bxon.py - BXON Binary Object/Table format parser, dumper, re-encoder, and builder.

BXON contains serialized game parameter and text databases (monsters, spells,
items, shops, area entities, dialogue catalogs).

Supports:
- Structural reference graph resolution for relative 32-bit pointers
- In-place string replacement and dynamic allocation / relocation
- Fresh BXON table construction from schemas/strings
- JSON table export and re-encoding back to bit-matching binary
- Automated round-trip validation
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

MARK = b"&&&&"

_TEXT_RANGES = (
    (0x20, 0x7F), (0xA0, 0x100),            # ASCII, Latin-1
    (0x2000, 0x2070), (0x2100, 0x27C0),     # punctuation, letterlike, arrows, shapes, dingbats
    (0x3000, 0x3100), (0x3200, 0x3400),     # CJK symbols, kana, enclosed/compat CJK
    (0x4E00, 0xA000),                       # CJK unified ideographs
    (0xE000, 0xF000),                       # private use (game icons)
    (0xFF00, 0xFFF0),                       # full/half width forms
)


def is_text_char(o: int) -> bool:
    for a, b in _TEXT_RANGES:
        if a <= o < b:
            return True
    return False


def valid_text(s: str) -> bool:
    """Heuristic: check whether text looks like valid game dialogue or parameters."""
    printable = 0
    i = 0
    while i < len(s):
        o = ord(s[i])
        if o == 0x04:  # variable placeholder: 0x04 + 1 parameter char
            i += 2
            continue
        if o in (0x01, 0x02, 0x03, 0x09, 0x0A, 0x0D):
            pass
        elif o < 0x20 or not is_text_char(o):
            return False
        else:
            printable += 1
        i += 1
    return printable > 0


def decode_utf16(raw: bytes) -> str:
    """Decode UTF-16LE payload handling control tags."""
    try:
        s = raw.decode("utf-16-le")
    except UnicodeDecodeError:
        return raw.decode("latin-1", "replace")

    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\x01":
            j = s.find("\x02", i + 1)
            k = s.find("\x03", j + 1) if j != -1 else -1
            if j != -1 and k != -1:
                out.append("{ruby:" + s[i + 1:j] + "|" + s[j + 1:k] + "}")
                i = k + 1
                continue
        if ch == "\x04" and i + 1 < n:
            out.append("{v:%X}" % ord(s[i + 1]))
            i += 2
            continue
        if ch == "\r":
            out.append("{CR}")
        elif ch == "\x1f":
            out.append("{PAGE}")
        elif ord(ch) < 0x20 and ch not in ("\n", "\t"):
            out.append("{c%02X}" % ord(ch))
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def encode_utf16(text: str) -> bytes:
    """Encode string with control tags back into binary UTF-16LE."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "{" and "}" in text[i:]:
            end = text.find("}", i)
            tag = text[i + 1:end]
            if tag.startswith("ruby:"):
                parts = tag[5:].split("|", 1)
                if len(parts) == 2:
                    out.extend(["\x01", parts[0], "\x02", parts[1], "\x03"])
                    i = end + 1
                    continue
            elif tag.startswith("v:"):
                try:
                    val = int(tag[2:], 16)
                    out.extend(["\x04", chr(val)])
                    i = end + 1
                    continue
                except ValueError:
                    pass
            elif tag == "CR":
                out.append("\r")
                i = end + 1
                continue
            elif tag == "PAGE":
                out.append("\x1f")
                i = end + 1
                continue
            elif tag.startswith("c") and len(tag) == 3:
                try:
                    val = int(tag[1:], 16)
                    out.append(chr(val))
                    i = end + 1
                    continue
                except ValueError:
                    pass
        out.append(text[i])
        i += 1
    return "".join(out).encode("utf-16-le", errors="surrogatepass")


def _as_string(payload: bytes, at_eof: bool = False) -> bytes | None:
    if len(payload) < 4 or (len(payload) % 4 and not at_eof):
        return None
    body = payload.rstrip(b"@")
    if len(body) % 2:
        body += b"@"
    if len(body) < 2 or body[-2:] != b"\0\0":
        return None
    if len(payload) - len(body) > 2:
        return None
    content = body[:-2]
    if len(content) % 2:
        return None
    for i in range(0, len(content), 2):
        if content[i] == 0 and content[i + 1] == 0:
            return None
    if not content:
        return None
    try:
        s = content.decode("utf-16-le")
    except UnicodeDecodeError:
        return None
    return content if valid_text(s) else None


def _is_string_block(payload: bytes) -> bool:
    body = payload.rstrip(b"@")
    if len(body) % 2:
        body += b"@"
    if len(body) < 2 or body[-2:] != b"\0\0" or len(payload) - len(body) > 3:
        return False
    for i in range(0, len(body) - 2, 2):
        if body[i] == 0 and body[i + 1] == 0:
            return False
    return True


def _structural_refs(n: int, words, block_size: dict[int, int], strings: dict,
                     stringish: set | None = None, ambiguous: set | None = None):
    def u32(p: int):
        if p < 0 or p + 4 > n or p & 3:
            return None
        return words[p >> 2]

    def rel(p: int):
        v = u32(p)
        if not v:
            return None
        return (p + v) & 0xFFFFFFFF

    stringish = stringish if stringish is not None else set(strings)
    ambiguous = ambiguous or set()
    refs: dict[int, list[int]] = {}
    queue: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int]] = set()

    def push_array(base: int, count: int):
        size = block_size.get(base)
        if size is None or count <= 0 or size % count or (size // count) % 4 or size == 0:
            return False
        queue.append((base, count, size // count))
        return True

    root_count, root_target = u32(0x20), rel(0x24)
    if root_count and root_target is not None:
        push_array(root_target, root_count)

    while queue:
        base, count, esize = queue.pop()
        if (base, esize) in seen:
            continue
        seen.add((base, esize))
        k = 0
        while k < esize:
            col = [base + i * esize + k for i in range(count)]
            if k + 8 <= esize:
                ok, targets = True, []
                for p in col:
                    c, v = u32(p), u32(p + 4)
                    if c == 0 and v == 0:
                        continue
                    if not c or not v or c > 0x100000:
                        ok = False
                        break
                    t = (p + 4 + v) & 0xFFFFFFFF
                    size = block_size.get(t)
                    if (t in stringish and t not in ambiguous) or size is None or size % c or (size // c) % 4 or size == 0:
                        ok = False
                        break
                    targets.append((t, c))
                if ok and targets:
                    for t, c in targets:
                        push_array(t, c)
                    k += 8
                    continue
            vals = [(p, rel(p)) for p in col]
            nonzero = [(p, t) for p, t in vals if t is not None]
            if nonzero and all(t in stringish for _, t in nonzero):
                for p, t in nonzero:
                    if t in strings:
                        refs.setdefault(t, []).append(p)
            elif nonzero and all(t in block_size and t not in stringish for _, t in nonzero):
                for _, t in nonzero:
                    push_array(t, 1)
            k += 4
    return refs, {base for base, _ in seen}


@dataclass
class BxonString:
    offset: int
    capacity: int
    raw: bytes
    refs: list[int] = field(default_factory=list)

    @property
    def text(self) -> str:
        return decode_utf16(self.raw)


@dataclass
class Bxon:
    data: bytes
    type_name: str
    strings: list[BxonString]
    skipped: list = field(default_factory=list)

    @classmethod
    def parse(cls, data: bytes) -> "Bxon":
        if data[:4] != b"BXON":
            raise ValueError("not BXON format")
        type_name = data[0x0C:0x20].split(b"\0", 1)[0].decode("ascii", "replace")
        n = len(data)

        starts = []
        pos = data.find(MARK, 0x20)
        while pos != -1:
            if pos % 4 == 0:
                starts.append(pos + 4)
                pos = data.find(MARK, pos + 4)
            else:
                pos = data.find(MARK, pos + 1)
        bounds = starts[1:] + [n + 4]

        strings: dict[int, BxonString] = {}
        for s, nxt in zip(starts, bounds):
            end = nxt - 4
            payload = data[s:end]
            st = _as_string(payload, at_eof=(end == n))
            if st is not None:
                strings[s] = BxonString(s, len(payload), st)

        words = struct.unpack_from(f"<{n // 4}I", data, 0)
        block_size = {s: (nxt - 4) - s for s, nxt in zip(starts, bounds)}
        block_starts = set(starts)

        def pointer_array(s: int) -> bool:
            size = block_size[s]
            if size == 0 or size % 4:
                return False
            return all(words[(s >> 2) + i] and ((s + 4 * i + words[(s >> 2) + i]) & 0xFFFFFFFF) in block_starts
                       for i in range(size // 4))

        stringish = {s for s, nxt in zip(starts, bounds) if s in strings or _is_string_block(data[s:nxt - 4])}
        ambiguous = {s for s in stringish if pointer_array(s)}
        refs, arrays = _structural_refs(n, words, block_size, strings, stringish, ambiguous)

        for base in arrays:
            strings.pop(base, None)
        for t, positions in refs.items():
            if t in strings:
                strings[t].refs.extend(sorted(set(positions)))

        return cls(data, type_name, sorted(strings.values(), key=lambda b: b.offset))

    def rebuild(self, replacements: dict[int, str]) -> bytes:
        """Replace strings in BXON table and return rebuilt binary bytes.

        If replacement fits in original block capacity, updates in place.
        If replacement is longer, relocates to end of file and updates relative pointers.
        """
        out = bytearray(self.data)
        by_off = {s.offset: s for s in self.strings}
        self.skipped = []
        free: list[list[int]] = []
        moved: list[tuple[BxonString, bytes]] = []

        def release(start: int, size: int):
            if size >= 4:
                free.append([start, size])

        for off, text in replacements.items():
            s = by_off.get(off)
            if s is None:
                self.skipped.append((off, "not a string in this file"))
                continue
            raw = encode_utf16(text)
            at_eof = (off + s.capacity == len(self.data))
            if at_eof:
                payload = raw + b"\0\0"
            else:
                payload = raw + b"\0\0"
                payload += b"@" * (-len(payload) % 4)

            if len(payload) > s.capacity and not s.refs:
                self.skipped.append((off, "too long for slot and no reference known"))
                continue

            if len(payload) <= s.capacity:
                out[off:off + s.capacity] = payload + b"@" * (s.capacity - len(payload))
                if s.capacity - len(payload) >= 8:
                    out[off + len(payload):off + len(payload) + 4] = MARK
                    release(off + len(payload) + 4, s.capacity - len(payload) - 4)
                continue

            if len(payload) % 4 != 0:
                payload += b"@" * (-len(payload) % 4)
            moved.append((s, payload))

        placed: dict[bytes, int] = {}
        for s, payload in sorted(moved, key=lambda m: -len(m[1])):
            new_off = placed.get(payload)
            if new_off is None:
                fit = [f for f in free if f[1] >= len(payload)]
                if fit:
                    f = min(fit, key=lambda f: f[1])
                    new_off = f[0]
                    rest = f[1] - len(payload)
                    out[new_off:new_off + f[1]] = payload + b"@" * rest
                    free.remove(f)
                    if rest >= 8:
                        out[new_off + len(payload):new_off + len(payload) + 4] = MARK
                        release(new_off + len(payload) + 4, rest - 4)
                else:
                    while len(out) % 4:
                        out += b"@"
                    out += MARK
                    new_off = len(out)
                    out += payload
                placed[payload] = new_off

            for r in s.refs:
                struct.pack_into("<I", out, r, (new_off - r) & 0xFFFFFFFF)

        return bytes(out)

    @classmethod
    def build_table(cls, type_name: str, strings: list[str]) -> bytes:
        """Construct a fresh valid BXON table with string pool from scratch."""
        thash = zlib.crc32(type_name.encode("ascii")) & 0xFFFFFFFF
        tname_bytes = type_name.encode("ascii")[:20].ljust(20, b"\0")
        header = b"BXON" + struct.pack("<II", 1, thash) + tname_bytes
        root = struct.pack("<II", len(strings), 8)

        payloads = []
        for s in strings:
            raw = encode_utf16(s) + b"\0\0"
            raw += b"@" * (-len(raw) % 4)
            payloads.append(raw)

        array_pos = 0x2C
        array_len = len(strings) * 4
        first_str_pos = array_pos + array_len
        while first_str_pos % 4 != 0:
            first_str_pos += 1

        str_offsets = []
        curr = first_str_pos
        str_data = bytearray()
        for p in payloads:
            str_data += MARK
            curr += 4
            str_offsets.append(curr)
            str_data += p
            curr += len(p)

        ptrs = bytearray()
        for i, off in enumerate(str_offsets):
            p_pos = array_pos + i * 4
            rel = (off - p_pos) & 0xFFFFFFFF
            ptrs += struct.pack("<I", rel)

        return bytes(header + root + MARK + ptrs + str_data)

    def to_dict(self) -> dict:
        return {
            "type": self.type_name,
            "raw_size": len(self.data),
            "strings_count": len(self.strings),
            "strings": [
                {
                    "offset": s.offset,
                    "capacity": s.capacity,
                    "text": s.text,
                    "refs": s.refs
                }
                for s in self.strings
            ]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def build_from_json(cls, json_input: str | dict, original_bxon: bytes | None = None) -> bytes:
        """Reconstruct a BXON binary table given JSON input and optional original data."""
        if isinstance(json_input, str):
            data = json.loads(json_input)
        else:
            data = json_input

        if original_bxon:
            bxon_obj = cls.parse(original_bxon)
            replacements = {
                item["offset"]: item["text"]
                for item in data.get("strings", [])
                if "offset" in item and "text" in item
            }
            return bxon_obj.rebuild(replacements)
        else:
            type_name = data.get("type", "GenericTable")
            strings = [item["text"] for item in data.get("strings", []) if "text" in item]
            return cls.build_table(type_name, strings)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_roundtrip(limit: int | None = None, romfs_image: str | Path | None = None) -> bool:
    """Verify bit-matching rebuild across RomFS core BXON tables."""
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    from tools import pack

    rom_path = str(romfs_image) if romfs_image else r"..\reference project\DQXI.3ds"
    f, ncsd, ncch = open_image(rom_path)
    romfs = ncch.romfs()

    core_packs = [
        "/battlecmn.pack",
        "/fieldcmn.pack",
        "/syscmn.pack",
        "/gamecmn.pack",
        "/divecmn.pack",
        "/2dcmn.pack",
    ]
    if limit:
        core_packs = core_packs[:limit]

    print(f"Verifying BXON tables across {len(core_packs)} core packs...")
    total_tables = 0
    all_ok = True

    for ppath in core_packs:
        rf = next((x for x in romfs.files if x.path == ppath), None)
        if not rf:
            continue
        p = pack.Pack.parse(romfs.read_file(rf))
        for entry in p.entries:
            if entry.name.endswith(".bxon"):
                total_tables += 1
                try:
                    table = Bxon.parse(entry.data)
                    # Test bit-matching rebuild with empty replacements
                    rebuilt = table.rebuild({})
                    if rebuilt != entry.data:
                        print(f"  [FAIL] Rebuild mismatch in {ppath}:{entry.name}")
                        all_ok = False
                        continue

                    # Test text replacement round-trip
                    text_repl = {s.offset: s.text for s in table.strings}
                    rebuilt_text = table.rebuild(text_repl)
                    if rebuilt_text != entry.data:
                        print(f"  [FAIL] Text rebuild mismatch in {ppath}:{entry.name}")
                        all_ok = False
                        continue

                    # Test JSON build
                    j = table.to_json()
                    rebuilt_json = Bxon.build_from_json(j, original_bxon=entry.data)
                    if rebuilt_json != entry.data:
                        print(f"  [FAIL] JSON rebuild mismatch in {ppath}:{entry.name}")
                        all_ok = False
                        continue

                except Exception as e:
                    print(f"  [ERROR] Exception processing {ppath}:{entry.name}: {e}")
                    all_ok = False

    f.close()
    status = "SUCCESS" if all_ok else "FAILURE"
    print(f"Verification {status}: Checked {total_tables} BXON tables. Bit-matching: {all_ok}")
    return all_ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DQXI BXON Binary Table Tool")
    parser.add_argument("--json", type=Path, help="Export .bxon to .json")
    parser.add_argument("--rebuild", type=Path, help="Rebuild .bxon from .json")
    parser.add_argument("--base", type=Path, help="Base .bxon file for rebuilding")
    parser.add_argument("-o", "--output", type=Path, help="Output file path")
    parser.add_argument("--verify", action="store_true", help="Verify roundtrip across core packs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of packs to verify")
    args = parser.parse_args()

    if args.verify:
        ok = verify_roundtrip(limit=args.limit)
        sys.exit(0 if ok else 1)

    if args.json:
        data = args.json.read_bytes()
        table = Bxon.parse(data)
        out_json = table.to_json()
        if args.output:
            args.output.write_text(out_json, encoding="utf-8")
        else:
            print(out_json)
        return

    if args.rebuild:
        json_data = args.rebuild.read_text(encoding="utf-8")
        base_data = args.base.read_bytes() if args.base else None
        bin_data = Bxon.build_from_json(json_data, original_bxon=base_data)
        out_path = args.output or args.rebuild.with_suffix(".bxon")
        out_path.write_bytes(bin_data)
        print(f"Rebuilt {len(bin_data)} bytes -> {out_path}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
