#!/usr/bin/env python3
"""Dump, edit and rebuild every player-visible text bank of DQXI (3DS).

Where the text lives
--------------------
All dialog/message/UI text is stored as UTF-16LE strings inside BXON files,
which are members of the RomFS PACK archives (``game_data/packs/<pack>/...``).
The root object type in the BXON header (bytes 0x0C..0x20) says what a bank is:

    CharacterIEData       NPC / book talk lines (npc_ie, book_ie, script ie)
    TalkPartyContent2     party chat utterances
    TextBlock             scripted messages (script_message, cs_text)
    BattleText            battle messages and action names
    UIText, UIMessage     menus, help, shop/church/inn messages, credits, ...

The tool writes one JSON file per bank under ``game_assets/text/banks`` plus a
flat ``text.csv`` (UTF-8 with BOM, open it in Excel/LibreOffice), and can put an
edited bank back into ``mod/romfs`` for a LayeredFS export.

Text format
-----------
Strings are UTF-16LE with these codes (see ``tags`` for the full table):

    U+0001 base U+0002 reading U+0003   furigana        -> {ruby:base|reading}
    U+0004 + slot                       message argument -> {PLAYER}, {NAME}, ...
    U+000D                              wait for button  -> {CR}
    U+001F                              next message box -> {PAGE} (tool-only)

A literal ``{`` or ``}`` in the text is written ``{{`` / ``}}``.

Commands
--------
    python tools/text_tool.py banks [--grep TEXT]
    python tools/text_tool.py export [--only KEY ...] [--no-csv]
    python tools/text_tool.py import --bank KEY --json FILE [--out FILE]
    python tools/text_tool.py save-mod --bank KEY --json FILE
    python tools/text_tool.py verify [--bank KEY] [--limit N]
    python tools/text_tool.py tags

``verify`` re-encodes every string of every bank from its dumped form and
demands a byte-identical file - that is the guarantee the editor relies on.
"""
from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.bxon import MARK, Bxon  # noqa: E402
from tools.bxon import decode_utf16 as _legacy_decode  # noqa: E402
from tools.bxon import encode_utf16 as _legacy_encode  # noqa: E402

PACKS = ROOT / "game_data" / "packs"
TEXT_DIR = ROOT / "game_assets" / "text"
BANKS_DIR = TEXT_DIR / "banks"
MOD_DIR = ROOT / "mod"
BUILD_DIR = ROOT / "build" / "text_edits"

# ---------------------------------------------------------------------------
# bank families
# ---------------------------------------------------------------------------
# type name -> (category, font, textbox width in px, lines per box, what it is)
# Dialogue fonts/widths come from the reference translation tool (gamefont.py:
# win_talk_3d text pane 350x66, text starts 10 px inside -> 321 px usable, 3 lines;
# MENU_FONT 3D12 for menus, credit2D for the staff roll).
KINDS: dict[str, tuple[str, str, int, int, str]] = {
    "CharacterIEData": ("NPC dialogue", "3D14", 321, 3, "NPC and book talk lines"),
    "TalkPartyContent2": ("Party chat", "3D14", 321, 3, "party chat utterances"),
    "TextBlock": ("Script messages", "3D14", 321, 3, "scripted / cutscene messages"),
    "BattleText": ("Battle text", "3D14", 321, 3, "battle messages and action names"),
    "UIText": ("UI text", "3D12", 300, 2, "menu labels and help text"),
    "UIMessage": ("Menu messages", "3D12", 300, 2, "shop, church, inn, system messages"),
    "UIStoryFlagRelation": ("Story summaries", "3D12", 300, 3, "story guide / recap text"),
    "ChurchMsg": ("Church messages", "3D14", 321, 3, "priest talk"),
    "ShopMsg": ("Shop messages", "3D14", 321, 3, "shop keeper talk"),
    "InnMsg": ("Inn messages", "3D14", 321, 3, "inn keeper talk"),
    "BankMsg": ("Bank messages", "3D14", 321, 3, "bank teller talk"),
    "CasinoMsg": ("Casino messages", "3D14", 321, 3, "casino dealer talk"),
    "SavePointMsg": ("Save point messages", "3D14", 321, 3, "save point talk"),
    "JewelShopMsg": ("Jewel shop messages", "3D14", 321, 3, "jewellery shop talk"),
    "SerenHintMessage": ("Serena hints", "3D14", 321, 3, "Serena's hint messages"),
    "ItemFailureMessage": ("Item failure messages", "3D14", 321, 3, "'can't use that here'"),
    "CreditTextData": ("Credits", "credit2D", 400, 30, "staff roll"),
    "DummyPlayerMessage": ("Dummy player messages", "3D12", 300, 2, "placeholder player messages"),
}

# ---------------------------------------------------------------------------
# text codec (game bytes <-> readable tags)
# ---------------------------------------------------------------------------
RUBY_START, RUBY_MID, RUBY_END, VAR = "\x01", "\x02", "\x03", "\x04"
PAGE = "\x1f"

# U+0004 is followed by one character that names a message argument the game
# fills in at run time (native SetMessageArg* functions write the same slots).
# The names below are the uses seen in the shipped text; a slot is reused for
# different things in different lines, so only 1..3 have a stable meaning.
ARG_NAMES: dict[int, str] = {
    0x1: "PLAYER",   # hero name ("{PLAYER} obtained ..."); acting character in battle
    0x2: "NAME",     # battle: attacker / monster / party member name
    0x3: "TARGET",   # battle: the one being acted on
    0x4: "PARTY3",   # third name in three-member combo lines
    0x5: "ITEM",     # item / skill name (sometimes a suffix particle)
    0x6: "ITEM2",    # second item in "received X and Y"
    0x7: "ITEM3",    # third item
    0x8: "NUMBER",   # number: damage, EXP, level, stat value
    0x9: "NUMBER2",  # second number (gold, new level, next stat)
    0xA: "NUMBER3",
    0xB: "NUMBER4",
    0xC: "NUMBER5",
    0xD: "NUMBER6",
    0xE: "NUMBER7",
    0xF: "NUMBER8",
}
ARG_BY_NAME = {name: slot for slot, name in ARG_NAMES.items()}

# 0x64/0x66 wrap the small-print notes of a message ("{FMT:66}note{FMT:64}").
# Their exact renderer effect is not decoded, so they keep a readable but
# honest form instead of pretending to be a colour/size.
FORMAT_CODES = {0x64, 0x66}

_TAG_RE = r"\{[^{}]*\}"


def game_string(s: str) -> str:
    """Raw UTF-16 game string -> editable tags."""
    out: list[str] = []
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        o = ord(ch)
        if ch == RUBY_START:
            j = s.find(RUBY_MID, i + 1)
            k = s.find(RUBY_END, j + 1) if j != -1 else -1
            if j != -1 and k != -1:
                out.append("{ruby:" + s[i + 1:j] + "|" + s[j + 1:k] + "}")
                i = k + 1
                continue
        if ch == VAR and i + 1 < n:
            slot = ord(s[i + 1])
            if slot in ARG_NAMES:
                out.append("{" + ARG_NAMES[slot] + "}")
            elif slot in FORMAT_CODES:
                out.append("{FMT:%02X}" % slot)
            else:
                out.append("{v:%X}" % slot)
            i += 2
            continue
        if ch == "{":
            out.append("{{")
        elif ch == "}":
            out.append("}}")
        elif ch == "\r":
            out.append("{CR}")
        elif ch == PAGE:
            out.append("{PAGE}")
        elif o < 0x20 and ch != "\n":
            out.append("{c%02X}" % o)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def game_bytes(tagged: str) -> bytes:
    return game_raw(tagged).encode("utf-16-le", errors="surrogatepass")


def game_raw(tagged: str) -> str:
    """Editable tags -> raw game string; unknown tags are an error, not text."""
    out: list[str] = []
    i, n = 0, len(tagged)
    while i < n:
        if tagged.startswith("{{", i):
            out.append("{")
            i += 2
            continue
        if tagged.startswith("}}", i):
            out.append("}")
            i += 2
            continue
        if tagged[i] == "{" and "}" in tagged[i:]:
            end = tagged.find("}", i)
            tag = tagged[i + 1:end]
            if tag.startswith("ruby:"):
                body = tag[5:]
                if "|" not in body:
                    raise ValueError(f"bad ruby tag {{{tag}}} (use {{ruby:base|reading}})")
                base, reading = body.split("|", 1)
                out.extend([RUBY_START, base, RUBY_MID, reading, RUBY_END])
                i = end + 1
                continue
            if tag.startswith("v:"):
                slot = int(tag[2:], 16)
                out.extend([VAR, chr(slot)])
                i = end + 1
                continue
            if tag.startswith("FMT:"):
                slot = int(tag[4:], 16)
                if slot not in FORMAT_CODES:
                    raise ValueError(f"unknown format code {{{tag}}}")
                out.extend([VAR, chr(slot)])
                i = end + 1
                continue
            if tag in ARG_BY_NAME:
                out.extend([VAR, chr(ARG_BY_NAME[tag])])
                i = end + 1
                continue
            if tag == "CR":
                out.append("\r")
                i = end + 1
                continue
            if tag == "PAGE":
                out.append(PAGE)
                i = end + 1
                continue
            if len(tag) == 3 and tag[0] == "c":
                out.append(chr(int(tag[1:], 16)))
                i = end + 1
                continue
            raise ValueError(
                f"unknown tag {{{tag}}} (known: ruby:, v:N, {', '.join(ARG_NAMES.values())}, "
                "FMT:64/66, CR, PAGE, cXX; write {{ }} for a literal brace)")
        out.append(tagged[i])
        i += 1
    return "".join(out)


def check_codec(s: str) -> None:
    """Raise if `s` cannot survive tags -> raw -> tags (lossy control codes)."""
    tagged = game_string(s)
    back = game_raw(tagged)
    if back != s:
        raise ValueError(f"codec is not reversible for {s!r}")
    if game_string(back) != tagged:
        raise ValueError(f"codec is not stable for {s!r}")


# ---------------------------------------------------------------------------
# BXON structure helpers
# ---------------------------------------------------------------------------
def u32(data: bytes, pos: int) -> int:
    return struct.unpack_from("<I", data, pos)[0]


def rel(data: bytes, pos: int) -> int | None:
    """Self-relative pointer at `pos` (0 means null)."""
    value = u32(data, pos)
    return (pos + value) & 0xFFFFFFFF if value else None


def block_end(data: bytes, start: int) -> int:
    """End offset of the block that starts at `start`."""
    pos = data.find(MARK, start)
    return len(data) if pos < 0 else pos


def string_offsets(data: bytes) -> set[int]:
    return {s.offset for s in Bxon.parse(data).strings}


def cstr(data: bytes, pos: int | None) -> str:
    """UTF-16 string stored at `pos`, decoded to tags (no NUL)."""
    if pos is None or pos + 2 > len(data):
        return ""
    end = pos
    while end + 2 <= len(data) and data[end:end + 2] != b"\0\0":
        end += 2
    return game_string(data[pos:end].decode("utf-16-le", errors="surrogatepass"))


@dataclass
class Found:
    """One string occurrence: where the engine points at it and what it is."""
    location: str
    pointer: int                 # byte offset of the self-relative pointer
    role: str = "text"           # text | speaker
    speaker: str = ""


def _walk_lines(data: bytes, count: int, root: int, label: str) -> dict[int, list[Found]]:
    """`root` holds `count` 28-byte line records (CharacterIEData / TextBlock).

    Line layout (verified against the reference translation tool, ietalk.py):
    +0x08 flags, +0x0C line index, +0x10 speaker string, +0x14 text string.
    """
    found: dict[int, list[Found]] = {}
    for line in range(min(count, 0x10000)):
        rec = root + 28 * line
        if rec + 28 > len(data):
            break
        location = f"{label}/line[{line}]"
        speaker_ptr = rel(data, rec + 0x10)
        text_ptr = rel(data, rec + 0x14)
        speaker = cstr(data, speaker_ptr)
        if text_ptr is not None:
            found.setdefault(text_ptr, []).append(
                Found(location, rec + 0x14, "text", speaker))
        if speaker_ptr is not None:
            found.setdefault(speaker_ptr, []).append(
                Found(location, rec + 0x10, "speaker", speaker))
    return found


def _walk_text_block(data: bytes) -> dict[int, list[Found]]:
    """TextBlock: root[] {line count, ptr -> line records, flags}; line = 28 bytes."""
    found: dict[int, list[Found]] = {}
    count, relptr = u32(data, 0x20), u32(data, 0x24)
    root = 0x24 + relptr
    for i in range(min(count, 0x10000)):
        row = root + 12 * i
        if row + 8 > len(data):
            break
        n = u32(data, row)
        lines = rel(data, row + 4)
        if not n or lines is None or n > 0x10000:
            continue
        found.update(_walk_lines(data, n, lines, f"block[{i}]"))
    return found


def _walk_party(data: bytes) -> dict[int, list[Found]]:
    """TalkPartyContent2: root[] {string count, ptr -> string pointers, flags}."""
    found: dict[int, list[Found]] = {}
    count, relptr = u32(data, 0x20), u32(data, 0x24)
    root = 0x24 + relptr
    for i in range(min(count, 0x10000)):
        row = root + 12 * i
        if row + 8 > len(data):
            break
        n = u32(data, row)
        arr = rel(data, row + 4)
        if not n or arr is None or n > 0x10000:
            continue
        for j in range(n):
            pos = arr + 4 * j
            if pos + 4 > len(data):
                break
            target = rel(data, pos)
            if target is not None:
                found.setdefault(target, []).append(
                    Found(f"utterance[{i}]/part[{j}]", pos))
    return found


def _walk_character_ie(data: bytes) -> dict[int, list[Found]]:
    """CharacterIEData: root[] -> talks[] -> variants[] -> 28-byte line records."""
    found: dict[int, list[Found]] = {}
    count, relptr = u32(data, 0x20), u32(data, 0x24)
    root = 0x24 + relptr
    for i in range(min(count, 0x1000)):
        entry = root + 24 * i
        if entry + 16 > len(data):
            break
        talks_n = u32(data, entry + 8)
        talks = rel(data, entry + 12)
        if not talks_n or talks is None:
            continue
        for t in range(min(talks_n, 0x1000)):
            talk = talks + 16 * t
            variants_n = u32(data, talk)
            variants = rel(data, talk + 4)
            if not variants_n or variants is None:
                continue
            for v in range(min(variants_n, 0x1000)):
                variant = variants + 12 * v
                lines_n = u32(data, variant)
                lines = rel(data, variant + 4)
                if not lines_n or lines is None:
                    continue
                found.update(_walk_lines(
                    data, lines_n, lines, f"talk[{i}]/variant[{t}]"))
    return found


def _walk_generic(data: bytes, known: set[int]) -> dict[int, list[Found]]:
    """Every other bank: root[] rows whose words point at a string or at a small
    record block that holds the string pointers (shop/church/menu messages).

    `known` are the offsets of the BXON string blocks; a word is only accepted
    when its target is one of them, so numbers that happen to look like offsets
    are not mistaken for text.
    """
    found: dict[int, list[Found]] = {}
    count, relptr = u32(data, 0x20), u32(data, 0x24)
    root = 0x24 + relptr
    if not count or count > 0x100000 or root >= len(data):
        return found
    end = block_end(data, root)
    row_size = (end - root) // count if end > root else 0
    if row_size <= 0 or end - root != row_size * count or row_size % 4:
        # fall back to just the root pointer words
        row_size = 4
        count = min(count, (len(data) - root) // 4)
    for i in range(count):
        row = root + row_size * i
        for off in range(0, row_size, 4):
            pos = row + off
            if pos + 4 > len(data):
                break
            target = rel(data, pos)
            if target is None:
                continue
            if target in known:
                found.setdefault(target, []).append(Found(f"row[{i}].{off // 4}", pos))
                continue
            # A pointer to another block of the table: scan that block for the
            # string pointers it holds (one level; these tables never nest deeper).
            block_stop = block_end(data, target)
            if not (target <= block_stop <= len(data)) or (block_stop - target) % 4:
                continue
            for k, ptr in enumerate(range(target, block_stop, 4)):
                text_at = rel(data, ptr)
                if text_at is not None and text_at in known:
                    found.setdefault(text_at, []).append(
                        Found(f"row[{i}].{off // 4}[{k}]", ptr))
    return found


# ---------------------------------------------------------------------------
# bank model
# ---------------------------------------------------------------------------
@dataclass
class Entry:
    offset: int
    location: str
    role: str
    speaker: str
    text: str

    def as_json(self, index: int) -> dict:
        return {
            "id": index,
            "offset": self.offset,
            "role": self.role,
            "speaker": self.speaker,
            "location": self.location,
            "text": self.text,
        }


@dataclass
class Bank:
    key: str
    path: Path
    pack: str
    member: str
    kind: str
    data: bytes = field(default=b"")
    entries: list[Entry] = field(default_factory=list)

    @property
    def category(self) -> str:
        return KINDS[self.kind][0]

    @property
    def font(self) -> str:
        return KINDS[self.kind][1]

    @property
    def box_width(self) -> int:
        return KINDS[self.kind][2]

    @property
    def box_lines(self) -> int:
        return KINDS[self.kind][3]

    @property
    def scene(self) -> str:
        parts = Path(self.key).parts
        return parts[-2] if len(parts) > 1 else parts[0]

    @property
    def rel_json(self) -> str:
        return f"banks/{self.key}.json"

    def load(self) -> "Bank":
        self.data = self.path.read_bytes()
        self.entries = extract_entries(self.data, self.kind)
        return self

    def as_json(self) -> dict:
        speakers = sorted({e.speaker for e in self.entries if e.role == "text" and e.speaker})
        return {
            "bank": self.key,
            "pack": self.pack,
            "member": self.member,
            "kind": self.kind,
            "category": self.category,
            "scene": self.scene,
            "font": self.font,
            "box_width": self.box_width,
            "box_lines": self.box_lines,
            "source": f"game_data/packs/{self.key}.bxon",
            "count": len(self.entries),
            "speakers": speakers,
            "entries": [e.as_json(i) for i, e in enumerate(self.entries)],
        }

    def meta_json(self) -> dict:
        return {
            "key": self.key,
            "pack": self.pack,
            "member": self.member,
            "kind": self.kind,
            "category": self.category,
            "scene": self.scene,
            "font": self.font,
            "box_width": self.box_width,
            "box_lines": self.box_lines,
            "count": len(self.entries),
            "speakers": len({e.speaker for e in self.entries if e.role == "text" and e.speaker}),
            "file": self.rel_json,
        }


def _walk_for_kind(data: bytes, kind: str) -> dict[int, list[Found]]:
    known = string_offsets(data)
    if kind == "CharacterIEData":
        return _walk_character_ie(data)
    if kind == "TextBlock":
        return _walk_text_block(data)
    if kind == "TalkPartyContent2":
        return _walk_party(data)
    return _walk_generic(data, known)


def extract_entries(data: bytes, kind: str) -> list[Entry]:
    """Every string block of a bank, with speaker/location where the format has it."""
    bxon = Bxon.parse(data)
    found = _walk_for_kind(data, kind)

    entries: list[Entry] = []
    for s in bxon.strings:
        # BxonString.text already went through tools/bxon's own tag renderer;
        # start from the raw UTF-16 payload so our codec stays reversible.
        raw = s.raw.decode("utf-16-le", errors="surrogatepass")
        places = found.get(s.offset) or []
        text_places = [p for p in places if p.role == "text"]
        speaker_places = [p for p in places if p.role == "speaker"]
        if text_places:
            first = text_places[0]
            role = "text"
            speaker = first.speaker
            location = first.location
        elif speaker_places:
            first = speaker_places[0]
            role = "speaker"
            speaker = first.speaker
            location = first.location
        else:
            role = "text"
            speaker = ""
            location = f"text@0x{s.offset:X}"
        entries.append(Entry(s.offset, location, role, speaker, game_string(raw)))
    entries.sort(key=lambda e: e.offset)
    return entries


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------
_pack_cache: dict[Path, str] = {}


def pack_of(path: Path) -> str:
    """RomFS pack (relative path) that contains a bank file."""
    directory = path.parent
    if directory in _pack_cache:
        return _pack_cache[directory]
    current = directory
    while True:
        meta = current / "_pack.json"
        if meta.is_file():
            try:
                info = json.loads(meta.read_text(encoding="utf-8"))
                value = str(info.get("path", "")).lstrip("/")
            except (OSError, json.JSONDecodeError):
                value = ""
            _pack_cache[directory] = value
            return value
        if current == PACKS or current.parent == current:
            _pack_cache[directory] = ""
            return ""
        current = current.parent


def bxon_kind(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            head = f.read(0x20)
    except OSError:
        return ""
    if head[:4] != b"BXON":
        return ""
    return head[0x0C:0x20].split(b"\0", 1)[0].decode("ascii", "replace")


def all_banks(only: list[str] | None = None) -> list[Bank]:
    wanted = {o.replace("\\", "/").strip("/") for o in only} if only else None
    out: list[Bank] = []
    for path in sorted(PACKS.rglob("*.bxon")):
        kind = bxon_kind(path)
        if kind not in KINDS:
            continue
        key = path.relative_to(PACKS).with_suffix("").as_posix()
        if wanted is not None and key not in wanted:
            continue
        pack = pack_of(path)
        if not pack:
            continue
        out.append(Bank(key, path, pack, path.name, kind))
    return out


def import_bank(key: str) -> Bank:
    key = key.replace("\\", "/").strip("/").removesuffix(".json")
    path = PACKS / f"{key}.bxon"
    if not path.is_file():
        raise SystemExit(f"no text bank at game_data/packs/{key}.bxon")
    kind = bxon_kind(path)
    if kind not in KINDS:
        raise SystemExit(f"{key}.bxon is a {kind!r}, not a text bank")
    return Bank(key, path, pack_of(path), path.name, kind).load()


# ---------------------------------------------------------------------------
# rebuild
# ---------------------------------------------------------------------------
def rebuild_bank(data: bytes, texts: dict[int, str]) -> bytes:
    """Replace the strings at `texts` offsets and return the new BXON bytes.

    `tools/bxon.Bxon.rebuild` already implements same-size writes plus
    relocation for longer text and repointing every reference; it speaks its own
    tag dialect, so the raw game string is handed to it through the legacy
    decoder. The guard below proves that round trip is lossless for this string.

    Only pointer positions found by this module's structure walk are trusted:
    BXON also has numeric fields that happen to look like string pointers, and
    repointing one of those on a longer edit would corrupt the table.
    """
    kind = data[0x0C:0x20].split(b"\0", 1)[0].decode("ascii", "replace")
    found = _walk_for_kind(data, kind) if kind in KINDS else {}
    trusted: dict[int, list[int]] = {}
    for offset, places in found.items():
        trusted[offset] = sorted({p.pointer for p in places})

    bxon = Bxon.parse(data)
    by_offset = {s.offset: s for s in bxon.strings}
    for s in bxon.strings:
        s.refs = trusted.get(s.offset, [])
    replacements: dict[int, str] = {}
    for offset, tagged in texts.items():
        s = by_offset.get(offset)
        if s is None:
            raise ValueError(f"offset 0x{offset:X} is not a string of this bank")
        raw = game_bytes(tagged)
        legacy = _legacy_decode(raw)
        if _legacy_encode(legacy) != raw:
            raise ValueError(
                f"the text at 0x{offset:X} contains a control code the BXON writer "
                f"cannot reproduce: {tagged!r}")
        replacements[offset] = legacy
    built = bxon.rebuild(replacements)
    if bxon.skipped:
        detail = "; ".join(f"0x{off:X}: {why}" for off, why in bxon.skipped[:4])
        raise ValueError(f"{len(bxon.skipped)} string(s) could not be written ({detail})")
    return built


def read_bank_json(path: Path) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or "entries" not in doc:
        raise SystemExit(f"{path}: not a text bank file (no 'entries')")
    return doc


def texts_from_json(doc: dict, bank: Bank | None = None) -> dict[int, str]:
    seen: set[int] = set()
    texts: dict[int, str] = {}
    for i, entry in enumerate(doc["entries"]):
        try:
            offset = int(entry["offset"])
            text = str(entry["text"])
        except (KeyError, TypeError, ValueError):
            raise SystemExit(f"entry #{i} has no numeric offset / text")
        if offset in seen:
            raise SystemExit(f"offset 0x{offset:X} appears twice in the JSON")
        seen.add(offset)
        texts[offset] = text
    if bank is not None:
        known = {e.offset for e in bank.entries}
        unknown = sorted(set(texts) - known)
        if unknown:
            raise SystemExit(
                f"{len(unknown)} offset(s) are not strings of {bank.key}: " +
                ", ".join(f"0x{o:X}" for o in unknown[:5]))
        missing = sorted(known - set(texts))
        if missing:
            raise SystemExit(
                f"{len(missing)} string(s) of {bank.key} are missing from the JSON: " +
                ", ".join(f"0x{o:X}" for o in missing[:5]))
    return texts


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------
def _reconfigure() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def cmd_tags(_args) -> int:
    print(__doc__.split("Text format\n-----------\n", 1)[1].split("\nCommands", 1)[0])
    print("message argument slots:")
    for slot, name in ARG_NAMES.items():
        print(f"  {{v:{slot:X}}} = {{{name}}}")
    print("formatting switches (meaning undecoded, they bracket small-print notes):")
    print("  {FMT:66} ... {FMT:64}")
    return 0


def cmd_banks(args) -> int:
    banks = all_banks()
    needle = (args.grep or "").casefold()
    by_kind: dict[str, int] = {}
    shown = 0
    for bank in banks:
        if needle and needle not in bank.key.casefold():
            continue
        bank.load()
        by_kind[bank.kind] = by_kind.get(bank.kind, 0) + 1
        print(f"{bank.key:52} {bank.kind:20} {len(bank.entries):5} strings  "
              f"[{bank.category}]")
        shown += 1
        if args.limit and shown >= args.limit:
            break
    print(f"\n{shown} bank(s) shown, {len(banks)} text banks in total")
    for kind, n in sorted(by_kind.items()):
        print(f"  {kind:24} {n:4}")
    return 0


def cmd_export(args) -> int:
    banks = all_banks(args.only)
    if not banks:
        raise SystemExit("no text banks matched")
    BANKS_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    metas: list[dict] = []
    total = 0
    families: dict[str, int] = {}
    for bank in banks:
        bank.load()
        out = BANKS_DIR / f"{bank.key}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(bank.as_json(), ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
        metas.append(bank.meta_json())
        families[bank.category] = families.get(bank.category, 0) + 1
        total += len(bank.entries)
        for entry in bank.entries:
            rows.append({
                "bank": bank.key,
                "pack": bank.pack,
                "id": entry.offset,
                "role": entry.role,
                "speaker": entry.speaker,
                "location": entry.location,
                "text": entry.text,
            })
    index = {
        "generated_by": "tools/text_tool.py export",
        "source": "game_data/packs",
        "count": len(metas),
        "entries": total,
        "families": dict(sorted(families.items())),
        "banks": metas,
    }
    if args.only:
        print(f"exported {len(metas)} bank(s) / {total:,} strings to "
              f"{BANKS_DIR.relative_to(ROOT)} (index.json and text.csv left alone)")
        return 0
    # Drop bank files of families this tool no longer treats as text banks
    # (an old export must not leave orphans behind for the viewer).
    wanted = {meta["file"] for meta in metas}
    for stale in BANKS_DIR.rglob("*.json"):
        rel = stale.relative_to(TEXT_DIR).as_posix()
        if rel not in wanted:
            stale.unlink()
    (TEXT_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if not args.no_csv:
        with open(TEXT_DIR / "text.csv", "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["bank", "pack", "id", "role", "speaker", "location", "text"])
            writer.writeheader()
            writer.writerows(rows)
    _write_index_md(index)
    print(f"exported {len(metas)} banks / {total:,} strings to "
          f"{TEXT_DIR.relative_to(ROOT)} (JSON per bank"
          + ("" if args.no_csv else " + text.csv") + ")")
    for category, n in sorted(families.items()):
        print(f"  {category:28} {n:4} banks")
    return 0


def _write_index_md(index: dict) -> None:
    lines = [
        "# Text banks",
        "",
        "Generated by `python tools/text_tool.py export` - do not edit by hand.",
        "",
        f"{index['count']} banks, {index['entries']:,} strings. One editable JSON per bank",
        "in `banks/`; `text.csv` is the same data as a spreadsheet.",
        "",
        "| Category | Banks |",
        "|---|---:|",
    ]
    counts: dict[str, int] = {}
    sizes: dict[str, int] = {}
    for bank in index["banks"]:
        counts[bank["category"]] = counts.get(bank["category"], 0) + 1
        sizes[bank["category"]] = sizes.get(bank["category"], 0) + bank["count"]
    for category in sorted(counts):
        lines.append(f"| {category} | {counts[category]} ({sizes[category]:,} strings) |")
    lines += [
        "",
        "Open a bank in DQXI Studio (Dialogues section) or edit the JSON and run",
        "`python tools/text_tool.py import --bank KEY --json FILE`, then",
        "`save-mod`. Tags are listed by `python tools/text_tool.py tags`.",
        "",
    ]
    (TEXT_DIR / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def cmd_import(args) -> int:
    bank = import_bank(args.bank)
    doc = read_bank_json(args.json)
    if doc.get("bank") and doc["bank"] != bank.key:
        raise SystemExit(f"the JSON is for {doc['bank']}, not {bank.key}")
    texts = texts_from_json(doc, bank)
    built = rebuild_bank(bank.data, texts)
    out = args.out or (BUILD_DIR / f"{bank.key}.bxon")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(built)
    changed = sum(1 for e in bank.entries if game_raw(texts[e.offset]) != game_raw(e.text))
    print(f"{bank.key}: {len(texts)} strings, {changed} changed, "
          f"{len(bank.data):,} -> {len(built):,} bytes -> {out}")
    return 0


CONDITION_DIR = ROOT / "build" / "npc_conditions"


def patch_conditions(data: bytes, edits: list[dict]) -> bytes:
    """CharacterIEData: set the condition word (+8 of a 16-byte talk record) of the listed conversations.

    `edits` rows: {"char": id, "talk": index, "group", "min", "time", "first"} (docs/DIALOGUE_FORMAT.md).
    Records are found by walking the (possibly regrown) file, so this runs after `rebuild_bank`.
    """
    out = bytearray(data)
    count, relptr = u32(data, 0x20), u32(data, 0x24)
    root = 0x24 + relptr
    for e in edits:
        ch, t = int(e["char"]), int(e["talk"])
        if ch >= count:
            raise ValueError(f"character {ch} is not in this bank")
        entry = root + 24 * ch
        talks_n = u32(data, entry + 8)
        talks = rel(data, entry + 12)
        if t >= talks_n or talks is None:
            raise ValueError(f"character {ch} has no conversation {t}")
        word = (int(e["group"]) & 0xFF) | ((int(e["min"]) & 0xFF) << 8) | ((int(e["time"]) & 0xFF) << 16) | ((int(e.get("first", 0)) & 0xFF) << 24)
        struct.pack_into("<I", out, talks + 16 * t + 8, word)
    return bytes(out)


def pending_conditions(key: str) -> list[dict]:
    path = CONDITION_DIR / (key.replace("/", "_") + ".json")
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_save_mod(args) -> int:
    bank = import_bank(args.bank)
    doc = read_bank_json(args.json)
    texts = texts_from_json(doc, bank)
    built = rebuild_bank(bank.data, texts)
    edits = pending_conditions(bank.key)
    if edits:
        built = patch_conditions(built, edits)
        print(f"applied {len(edits)} conversation condition edit(s)")
    out = BUILD_DIR / f"{bank.key}.bxon"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(built)
    from tools.export_mod import stage_member

    info = stage_member(bank.pack, bank.member, out, MOD_DIR,
                        work_dir=ROOT / "build" / "staged" / "text")
    print(f"{bank.key}: {len(texts)} strings, {len(bank.data):,} -> {len(built):,} bytes")
    print(f"staged {bank.member} into {bank.pack}: {info['size']:,} bytes "
          f"(retail {info['original_size']:,})")
    print(f"  -> {Path(info['mod_file']).relative_to(ROOT)}")
    print("export it with: python tools/export_mod.py --target luma")
    return 0


def cmd_verify(args) -> int:
    banks = all_banks([args.bank] if args.bank else None)
    if args.limit:
        banks = banks[:args.limit]
    failures = 0
    strings = 0
    for bank in banks:
        bank.load()
        try:
            texts = {e.offset: e.text for e in bank.entries}
            raw_by_offset = {
                s.offset: s.raw.decode("utf-16-le", errors="surrogatepass")
                for s in Bxon.parse(bank.data).strings
            }
            for entry in bank.entries:
                raw = raw_by_offset[entry.offset]
                check_codec(raw)
                if game_raw(entry.text) != raw:
                    raise ValueError(f"tag round trip changed 0x{entry.offset:X}")
                strings += 1
            built = rebuild_bank(bank.data, texts)
            if built != bank.data:
                first = next(i for i in range(min(len(built), len(bank.data)))
                             if built[i] != bank.data[i])
                print(f"  [FAIL] {bank.key}: rebuild differs at 0x{first:X}")
                failures += 1
                continue
        except (ValueError, struct.error, IndexError) as exc:
            print(f"  [FAIL] {bank.key}: {exc}")
            failures += 1
    print(f"\n{len(banks)} banks, {strings:,} strings re-encoded, {failures} failure(s)")
    return 1 if failures else 0


def main() -> int:
    _reconfigure()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("tags", help="print the tag vocabulary")
    t.set_defaults(func=cmd_tags)

    b = sub.add_parser("banks", help="list text banks")
    b.add_argument("--grep", default="")
    b.add_argument("--limit", type=int, default=0)
    b.set_defaults(func=cmd_banks)

    e = sub.add_parser("export", help="dump every bank to game_assets/text")
    e.add_argument("--only", action="append", metavar="KEY",
                   help="only this bank key (repeatable)")
    e.add_argument("--no-csv", action="store_true")
    e.set_defaults(func=cmd_export)

    i = sub.add_parser("import", help="rebuild one bank from edited JSON")
    i.add_argument("--bank", required=True, metavar="KEY")
    i.add_argument("--json", required=True, type=Path)
    i.add_argument("--out", type=Path)
    i.set_defaults(func=cmd_import)

    s = sub.add_parser("save-mod", help="rebuild one bank and stage its pack in mod/romfs")
    s.add_argument("--bank", required=True, metavar="KEY")
    s.add_argument("--json", required=True, type=Path)
    s.set_defaults(func=cmd_save_mod)

    v = sub.add_parser("verify", help="every bank must rebuild byte-identically")
    v.add_argument("--bank", metavar="KEY")
    v.add_argument("--limit", type=int, default=0)
    v.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
