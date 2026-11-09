#!/usr/bin/env python3
"""Name tiny wrappers, getters and constant-returners from the instructions, without a model.

Most of the still-unnamed native functions are real code, but a few classes of function have
their whole behaviour visible in two or three instructions: a field getter, a field setter, a
constant return, a pure forwarder, an empty stub, or an accessor-plus-field getter.  This tool
decodes those functions from the retail ``code.bin`` and proposes a *shape* name for them
(``Obj_GetU32At0x10``, ``ReturnsZero``, ``Ui_Object_DtorBaseThunk``, ...) with the decoded
instruction sequence as evidence.  It never guesses semantics: a function that does not match a
rule exactly is left alone.

Why a private decoder instead of the ``asm/`` text
--------------------------------------------------
``asm/text/*.s`` is a linear sweep: it switches ARM/Thumb only at known symbol entries, so a
handful of functions are disassembled in the wrong mode there (``0x00102B90`` is ARM
``push {r4,lr}`` but the sweep prints Thumb ``ands r0, r2``).  Ghidra's ``mode`` column in
``decomp/ghidra/functions.jsonl`` is wrong for about 150 functions in the other direction
(``0x00115410`` is ARM but the catalogue says Thumb).  Neither source is authoritative, so this
tool decodes the bytes itself and only accepts a function when **both** decoders agree on the
instruction boundaries and the mnemonic class of every instruction up to the return.  A function
where they disagree is skipped, never guessed.

Rules (each decoded from the instructions, never from Ghidra's C)
-----------------------------------------------------------------
1. field getter      ``ldr/ldrb/ldrh/ldrsh/ldrsb r0,[r0,#N]`` then return
                     -> ``Obj_GetU32At0xNN`` / ``GetU8At`` / ``GetU16At`` / ``GetS16At`` / ``GetS8At``
                     (``add r0,r0,#M`` before the load is folded into the offset)
2. field setter      ``str/strb/strh r1,[r0,#N]`` then return -> ``Obj_SetU32At0xNN``
3. constant return   ``mov/mvn/movw/movw+movt r0,#K`` or ``ldr r0,[pc,#imm]`` of a small literal
                     -> ``ReturnsZero`` / ``ReturnsTrue`` / ``ReturnsMinusOne`` / ``ReturnsConstant0xK``
4. pure forwarder    only argument moves, then ``b``/``bl`` to exactly one callee
                     -> ``<Callee>Thunk`` when the callee is confidently named, else ``Thunk_<ADDR>``
5. empty stub        ``bx lr`` / ``pop {..,pc}`` only -> ``Nop_<ADDR>`` or ``<Class>_NoOp``
6. accessor getter   ``bl <singleton accessor>`` then ``ldr r0,[r0,#N]`` -> ``<Accessor>_Field0xNN``

A class prefix (``Ui_Overlay_`` instead of ``Obj_``) is only used when at least three
confidently named functions in the same vtable group (``orchestration/naming/refine/scores.jsonl``)
share it.

Output is a refine overlay, ``orchestration/naming/refine/out/R_T01.json``, in the same entry
format as ``R_S01.json``; ``tools/merge_names.py`` merges it like any other R batch.

Usage
-----
    python tools/trivial_names.py                 # write the overlay
    python tools/trivial_names.py --check         # validate the overlay, write nothing
    python tools/trivial_names.py --report        # what is left: shape histogram of unnamed functions
    python tools/trivial_names.py --dry-run       # print the proposals, write nothing
"""
from __future__ import annotations

import argparse
import bisect
import collections
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_BIN = ROOT / "original" / "exefs" / "code.decompressed.bin"
FUNCTIONS = ROOT / "decomp" / "ghidra" / "functions.jsonl"
READABLE = ROOT / "decomp" / "readable" / "functions"
XREF = ROOT / "decomp" / "xref.json"
SCORES = ROOT / "orchestration" / "naming" / "refine" / "scores.jsonl"
NAMING_OUT = ROOT / "orchestration" / "naming" / "out"
REFINE_OUT = ROOT / "orchestration" / "naming" / "refine" / "out"
OUT = REFINE_OUT / "R_T01.json"
ASM_TEXT = ROOT / "asm" / "text"

BASE = 0x00100000            # virtual address of byte 0 of code.decompressed.bin
IMAGE_LO = 0x00100000        # .text
IMAGE_HI = 0x008398E4        # end of .bss
TEXT_LO = 0x00100000         # .text, the only range a ``bl`` can target
TEXT_HI = 0x0072403C
MAX_SCAN = 64                # bytes decoded per function; every rule fits in far less
PLACEHOLDER = re.compile(r"^(?:func_|FUN_|maybe_|thunk_|LAB_|DAT_|sub_|undefined)")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RESERVED = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else",
    "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long", "register",
    "restrict", "return", "short", "signed", "sizeof", "static", "struct", "switch", "typedef",
    "union", "unsigned", "void", "volatile", "while", "bool", "true", "false", "this", "class",
    "new", "delete",
}

# ---------------------------------------------------------------------------------------------
# instruction decoding
# ---------------------------------------------------------------------------------------------
# Only the forms the rules need are classified; everything else is ``other`` with the correct
# size, which is all the walk needs.  An unclassified instruction can never be part of a rule
# match, so an unknown encoding always means "leave this function alone".


def _sx(value: int, bits: int) -> int:
    sign = 1 << (bits - 1)
    return (value ^ sign) - sign


class Code:
    """The retail executable, addressed by virtual address."""

    def __init__(self, data: bytes):
        self.data = data

    @classmethod
    def from_file(cls, path: Path) -> "Code":
        return cls(path.read_bytes())

    def u16(self, addr: int) -> int:
        return struct.unpack_from("<H", self.data, addr - BASE)[0]

    def u32(self, addr: int) -> int:
        return struct.unpack_from("<I", self.data, addr - BASE)[0]


def decode_arm(code: Code, addr: int) -> dict:
    w = code.u32(addr)
    cond = w >> 28
    ins = {"addr": addr, "size": 4, "raw": w, "cond": cond, "kind": "other"}
    if (w & 0x0FFFFFF0) == 0x012FFF10:
        ins.update(kind="bx", rm=w & 0xF)
        return ins
    if (w & 0x0FFFFFF0) == 0x012FFF30:
        ins.update(kind="blx", rm=w & 0xF)
        return ins
    if (w & 0x0E000000) == 0x0A000000:                       # B / BL / B<cond>
        target = (addr + 8 + _sx(w & 0xFFFFFF, 24) * 4) & 0xFFFFFFFF
        if cond != 0xE:
            ins.update(kind="bcond", target=target)
        elif w & 0x01000000:
            ins.update(kind="bl", target=target)
        else:
            ins.update(kind="b", target=target)
        return ins
    if (w & 0x0FEF0FF0) == 0x01A00000:                       # MOV rd, rm
        ins.update(kind="mov", rd=(w >> 12) & 0xF, rm=w & 0xF, imm=None)
        return ins
    if (w & 0x0FE00000) == 0x03A00000:                       # MOV rd, #imm8
        ins.update(kind="mov", rd=(w >> 12) & 0xF, rm=None, imm=w & 0xFF)
        return ins
    if (w & 0x0FE00000) == 0x03E00000:                       # MVN rd, #imm8
        ins.update(kind="mvn", rd=(w >> 12) & 0xF, imm=w & 0xFF)
        return ins
    if (w & 0x0FF00000) == 0x03000000:                       # MOVW
        ins.update(kind="movw", rd=(w >> 12) & 0xF, imm=((w >> 4) & 0xF000) | (w & 0xFFF))
        return ins
    if (w & 0x0FF00000) == 0x03400000:                       # MOVT
        ins.update(kind="movt", rd=(w >> 12) & 0xF, imm=((w >> 4) & 0xF000) | (w & 0xFFF))
        return ins
    if (w & 0x0F200000) == 0x05000000:                       # LDR/STR/LDRB/STRB, imm, P=1 W=0
        load = (w >> 20) & 1
        byte = (w >> 22) & 1
        up = (w >> 23) & 1
        imm = w & 0xFFF
        ins.update(kind=("ldr" if load else "str") + ("b" if byte else ""),
                   rd=(w >> 12) & 0xF, rn=(w >> 16) & 0xF, imm=imm if up else -imm)
        if ins["rn"] == 15:
            ins["literal"] = (addr + 8 + (imm if up else -imm)) & 0xFFFFFFFF
        return ins
    if (w & 0x0E000090) == 0x00000090 and (w & 0x60):        # LDRH/STRH/LDRSH/LDRSB, imm
        load = (w >> 20) & 1
        up = (w >> 23) & 1
        signed = (w >> 6) & 1
        half = (w >> 5) & 1
        if (w >> 24) & 1 and not (w >> 21) & 1 and (w >> 22) & 1:
            # bits 7-4 are 1 S H 1: S selects the signed form, H the halfword form.  A store
            # with S set is STRD, not STRH, so it is not in the table.
            kind = {(1, 0, 1): "ldrh", (1, 1, 1): "ldrsh", (1, 1, 0): "ldrsb",
                    (0, 0, 1): "strh"}.get((load, signed, half))
            if kind:
                imm = ((w >> 4) & 0xF0) | (w & 0xF)
                ins.update(kind=kind, rd=(w >> 12) & 0xF, rn=(w >> 16) & 0xF,
                           imm=imm if up else -imm)
                return ins
    if (w & 0xFFFF0000) == 0xE92D0000:
        ins.update(kind="push", reglist=w & 0xFFFF)
        return ins
    if (w & 0xFFFF0000) == 0xE8BD0000:
        ins.update(kind="pop", reglist=w & 0xFFFF)
        return ins
    if (w & 0x0FEF0000) == 0x028F0000:                       # ADD rd, pc, #imm
        ins.update(kind="add", rd=(w >> 12) & 0xF, rn=15, imm=w & 0xFFF)
        return ins
    if (w & 0x0FE00000) == 0x02800000:                       # ADD rd, rn, #imm
        ins.update(kind="add", rd=(w >> 12) & 0xF, rn=(w >> 16) & 0xF, imm=w & 0xFFF)
        return ins
    if (w & 0x0FE00000) == 0x02400000:                       # SUB rd, rn, #imm
        ins.update(kind="sub", rd=(w >> 12) & 0xF, rn=(w >> 16) & 0xF, imm=w & 0xFFF)
        return ins
    if (w & 0x0FF0F000) == 0x03500000:                       # CMP rn, #imm
        ins.update(kind="cmp", rn=(w >> 16) & 0xF, imm=w & 0xFF)
        return ins
    if w == 0xE1A00000:
        ins.update(kind="nop")
        return ins
    return ins


def decode_thumb(code: Code, addr: int) -> dict:
    hw = code.u16(addr)
    ins = {"addr": addr, "size": 2, "raw": hw, "kind": "other"}
    if (hw >> 11) in (0b11101, 0b11110, 0b11111):            # 32-bit Thumb-2
        hw2 = code.u16(addr + 2)
        ins["size"] = 4
        ins["raw"] = (hw << 16) | hw2
        wide = {
            0xF8D0: ("ldr", 0), 0xF8C0: ("str", 0), 0xF890: ("ldrb", 0), 0xF880: ("strb", 0),
            0xF8B0: ("ldrh", 0), 0xF8A0: ("strh", 0), 0xF9B0: ("ldrsh", 0), 0xF990: ("ldrsb", 0),
        }
        if (hw & 0xFFF0) in wide:
            kind, _ = wide[hw & 0xFFF0]
            ins.update(kind=kind, rd=(hw2 >> 12) & 0xF, rn=hw & 0xF, imm=hw2 & 0xFFF)
            return ins
        if (hw & 0xFB00) == 0xF200 and not (hw2 & 0x8000):   # MOVW
            ins.update(kind="movw", rd=(hw2 >> 8) & 0xF,
                       imm=(((hw >> 10) & 1) << 11) | (((hw2 >> 12) & 7) << 8) | (hw2 & 0xFF))
            return ins
        if (hw & 0xFB00) == 0xF2C0 and not (hw2 & 0x8000):   # MOVT
            ins.update(kind="movt", rd=(hw2 >> 8) & 0xF,
                       imm=(((hw >> 10) & 1) << 11) | (((hw2 >> 12) & 7) << 8) | (hw2 & 0xFF))
            return ins
        if (hw & 0xF800) == 0xF000 and (hw2 & 0xD000) in (0xD000, 0x9000):   # BL / B.W
            s = (hw >> 10) & 1
            i1 = 1 - (((hw2 >> 13) & 1) ^ s)
            i2 = 1 - (((hw2 >> 11) & 1) ^ s)
            imm = (s << 24) | (i1 << 23) | (i2 << 22) | ((hw & 0x3FF) << 12) | ((hw2 & 0x7FF) << 1)
            ins.update(kind="bl" if (hw2 & 0xD000) == 0xD000 else "b",
                       target=(addr + 4 + _sx(imm, 25)) & 0xFFFFFFFF)
            return ins
        if (hw & 0xFF7F) == 0xEA4F and (hw2 & 0x00F0) == 0:  # MOV.W rd, rm
            ins.update(kind="mov", rd=(hw2 >> 8) & 0xF, rm=hw2 & 0xF, imm=None)
            return ins
        return ins
    if (hw & 0xFE00) == 0xB400:
        ins.update(kind="push", reglist=(hw & 0xFF) | (0x4000 if hw & 0x100 else 0))
        return ins
    if (hw & 0xFE00) == 0xBC00:
        ins.update(kind="pop", reglist=(hw & 0xFF) | (0x8000 if hw & 0x100 else 0))
        return ins
    if (hw & 0xFF87) == 0x4700:
        ins.update(kind="bx", rm=(hw >> 3) & 0xF)
        return ins
    if (hw & 0xFF87) == 0x4780:
        ins.update(kind="blx", rm=(hw >> 3) & 0xF)
        return ins
    if (hw & 0xF800) == 0x2000:
        ins.update(kind="mov", rd=(hw >> 8) & 7, rm=None, imm=hw & 0xFF)
        return ins
    if (hw & 0xF800) == 0x2800:
        ins.update(kind="cmp", rn=(hw >> 8) & 7, imm=hw & 0xFF)
        return ins
    if (hw & 0xFF00) == 0x4600:
        ins.update(kind="mov", rd=((hw >> 4) & 8) | (hw & 7), rm=(hw >> 3) & 0xF, imm=None)
        return ins
    if (hw & 0xF800) == 0x6800:
        ins.update(kind="ldr", rd=hw & 7, rn=(hw >> 3) & 7, imm=((hw >> 6) & 0x1F) * 4)
        return ins
    if (hw & 0xF800) == 0x6000:
        ins.update(kind="str", rd=hw & 7, rn=(hw >> 3) & 7, imm=((hw >> 6) & 0x1F) * 4)
        return ins
    if (hw & 0xF800) == 0x7800:
        ins.update(kind="ldrb", rd=hw & 7, rn=(hw >> 3) & 7, imm=(hw >> 6) & 0x1F)
        return ins
    if (hw & 0xF800) == 0x7000:
        ins.update(kind="strb", rd=hw & 7, rn=(hw >> 3) & 7, imm=(hw >> 6) & 0x1F)
        return ins
    if (hw & 0xF800) == 0x8800:
        ins.update(kind="ldrh", rd=hw & 7, rn=(hw >> 3) & 7, imm=((hw >> 6) & 0x1F) * 2)
        return ins
    if (hw & 0xF800) == 0x8000:
        ins.update(kind="strh", rd=hw & 7, rn=(hw >> 3) & 7, imm=((hw >> 6) & 0x1F) * 2)
        return ins
    if (hw & 0xFE00) == 0x5E00:
        ins.update(kind="ldrsh", rd=hw & 7, rn=(hw >> 3) & 7, rm=(hw >> 6) & 7)
        return ins
    if (hw & 0xFE00) == 0x5600:
        ins.update(kind="ldrsb", rd=hw & 7, rn=(hw >> 3) & 7, rm=(hw >> 6) & 7)
        return ins
    if (hw & 0xF800) == 0x4800:
        ins.update(kind="ldr", rd=(hw >> 8) & 7, rn=15, imm=None,
                   literal=((addr + 4) & ~3) + (hw & 0xFF) * 4)
        return ins
    if (hw & 0xF800) == 0xE000:
        ins.update(kind="b", target=(addr + 4 + _sx(hw & 0x7FF, 11) * 2) & 0xFFFFFFFF)
        return ins
    if (hw & 0xF000) == 0xD000:
        ins.update(kind="bcond", cond=(hw >> 8) & 0xF,
                   target=(addr + 4 + _sx(hw & 0xFF, 8) * 2) & 0xFFFFFFFF)
        return ins
    if (hw & 0xF800) == 0x1C00:
        ins.update(kind="add", rd=hw & 7, rn=(hw >> 3) & 7, imm=(hw >> 6) & 7)
        return ins
    if (hw & 0xF800) == 0x1E00:
        ins.update(kind="sub", rd=hw & 7, rn=(hw >> 3) & 7, imm=(hw >> 6) & 7)
        return ins
    if hw == 0xBF00:
        ins.update(kind="nop")
        return ins
    return ins


def decode(code: Code, addr: int, mode: str, length: int) -> list[dict]:
    """Decode ``length`` bytes; the walk always consumes whole instructions."""
    out, pc = [], addr
    while pc < addr + length:
        ins = decode_arm(code, pc) if mode == "arm" else decode_thumb(code, pc)
        # A conditional ARM instruction runs only for one flag state, so it is never part of a
        # plain getter/setter/return; classify it as unknown.
        if mode == "arm" and ins.get("cond", 0xE) != 0xE and ins["kind"] != "bcond":
            ins["kind"] = "other"
        out.append(ins)
        pc += ins["size"]
    return out


def is_terminal(ins: dict) -> bool:
    """An instruction after which the function cannot fall through to more of its own code."""
    kind = ins["kind"]
    if kind == "bx":
        return True
    if kind == "pop" and (ins["reglist"] & 0x8000):          # pop {..., pc}
        return True
    return kind in ("b", "blx")                              # tail call / computed jump


# ---------------------------------------------------------------------------------------------
# asm/text cross-check
# ---------------------------------------------------------------------------------------------
TEXT_LINE = re.compile(r"/\* 0x([0-9A-Fa-f]{8}): ([0-9a-fA-F]+) \*/\s+(\S+)")
# The mnemonic spellings the project's own disassembly may use for each classified kind.
KIND_MNEMONICS = {
    "ldr": {"ldr", "ldr.w"}, "str": {"str", "str.w"},
    "ldrb": {"ldrb", "ldrb.w"}, "strb": {"strb", "strb.w"},
    "ldrh": {"ldrh", "ldrh.w"}, "strh": {"strh", "strh.w"},
    "ldrsh": {"ldrsh", "ldrsh.w"}, "ldrsb": {"ldrsb", "ldrsb.w"},
    "mov": {"mov", "movs", "mov.w"}, "mvn": {"mvn", "mvns", "mvn.w"},
    "movw": {"movw"}, "movt": {"movt"},
    "b": {"b", "b.w"}, "bl": {"bl"}, "bx": {"bx"}, "blx": {"blx"},
    "push": {"push", "push.w"}, "pop": {"pop", "pop.w"},
    "add": {"add", "adds", "add.w"}, "sub": {"sub", "subs", "sub.w"},
    "cmp": {"cmp", "cmp.w"}, "nop": {"nop"},
}


class AsmText:
    """Instruction boundaries and mnemonics from ``asm/text/*.s``, for the addresses we ask about."""

    def __init__(self, wanted: set[int]):
        self.lines: dict[int, tuple[int, str]] = {}
        for path in sorted(ASM_TEXT.glob("text_*.s")):
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                m = TEXT_LINE.search(line)
                if not m:
                    continue
                addr = int(m.group(1), 16)
                if addr in wanted:
                    self.lines[addr] = (len(m.group(2)) // 2, m.group(3))

    def agrees(self, instructions: list[dict]) -> bool:
        """True when the sweep decoded the same instruction boundaries and mnemonics."""
        for ins in instructions:
            entry = self.lines.get(ins["addr"])
            if entry is None:
                return False
            size, mnemonic = entry
            if size != ins["size"]:
                return False
            allowed = KIND_MNEMONICS.get(ins["kind"])
            if allowed is not None and mnemonic not in allowed:
                return False
        return True


# ---------------------------------------------------------------------------------------------
# project data
# ---------------------------------------------------------------------------------------------
def load_functions() -> list[dict]:
    rows = []
    for line in FUNCTIONS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("status") != "ok" or "size" not in row:
            continue
        row["addr"] = int(row["address"], 16)
        rows.append(row)
    rows.sort(key=lambda r: r["addr"])
    return rows


def load_current_names() -> dict[int, str]:
    """Current names as a modder sees them (``decomp/readable/functions/<name>_<addr>.c``)."""
    names = {}
    for path in READABLE.glob("*.c"):
        m = re.match(r"^(.*)_([0-9a-fA-F]{8})\.c$", path.name)
        if m:
            names[int(m.group(2), 16)] = m.group(1)
    return names


def load_proposal_confidence(exclude: Path | None = None) -> dict[int, float]:
    """Effective confidence per address after the N_* and R*_* overlays (same order as the merge).

    ``exclude`` is this tool's own output: without it a second run would see its own proposals as
    already confident and write an empty batch.
    """
    conf: dict[int, float] = {}
    for path in sorted(NAMING_OUT.glob("N_*.json")):
        for entry in _read_json(path):
            try:
                conf[int(str(entry["address"]), 16)] = float(entry.get("confidence", 0))
            except (KeyError, ValueError, TypeError):
                continue
    for path in sorted(REFINE_OUT.glob("R*_*.json"),
                       key=lambda q: (int(re.match(r"R(\d*)_", q.stem).group(1) or 1), q.stem)):
        if exclude is not None and path.resolve() == exclude.resolve():
            continue
        for entry in _read_json(path):
            try:
                conf[int(str(entry["address"]), 16)] = float(entry.get("confidence", 0))
            except (KeyError, ValueError, TypeError):
                continue
    return conf


def _read_json(path: Path) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def load_xref() -> dict[str, dict]:
    if not XREF.exists():
        return {}
    return json.loads(XREF.read_text(encoding="utf-8"))


def load_vtables() -> dict[int, str]:
    """address -> vtable group, from the refine scorer (evidence text that names a vtable)."""
    out = {}
    if not SCORES.exists():
        return out
    for line in SCORES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("vtable"):
            out[int(row["address"], 16)] = row["vtable"]
    return out


def is_confident(name: str | None) -> bool:
    return bool(name) and not PLACEHOLDER.match(str(name))


# ---------------------------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------------------------
class Analysis:
    """The decoded shape of one function, or the reason it was not decoded."""

    __slots__ = ("body", "terminal", "mode", "instructions", "reason")

    def __init__(self, body=None, terminal=None, mode=None, instructions=None, reason=""):
        self.body = body or []
        self.terminal = terminal
        self.mode = mode
        self.instructions = instructions or []
        self.reason = reason


def analyse(code: Code, text: AsmText, addr: int, declared_mode: str) -> Analysis:
    """Decode up to the first return and require the project's own disassembly to agree."""
    first_reason = ""
    for mode in (declared_mode, "thumb" if declared_mode == "arm" else "arm"):
        instructions = decode(code, addr, mode, MAX_SCAN)
        index = next((i for i, ins in enumerate(instructions) if is_terminal(ins)), None)
        if index is None:
            first_reason = first_reason or "no return within 64 bytes"
            continue
        upto = instructions[:index + 1]
        if not text.agrees(upto):
            first_reason = first_reason or "asm/text disagrees on the decode"
            continue
        body = instructions[:index]
        if body and body[0]["kind"] == "push":
            body = body[1:]
        return Analysis(body, instructions[index], mode, upto)
    return Analysis(reason=first_reason or "not decodable")


def fmt_ins(ins: dict) -> str:
    """One instruction as a modder reads it (AT&T-free, ARM syntax)."""
    kind = ins["kind"]
    if kind == "push":
        return f"push {reglist(ins['reglist'])}"
    if kind == "pop":
        return f"pop {reglist(ins['reglist'])}"
    if kind == "bx":
        return f"bx {reg_name(ins['rm'])}"
    if kind == "blx":
        return f"blx {reg_name(ins['rm'])}"
    if kind in ("b", "bl", "bcond"):
        return f"{kind} 0x{ins['target']:08X}"
    if kind in ("mov", "mvn"):
        if ins.get("imm") is not None:
            return f"{kind} r{ins['rd']}, #{ins['imm']}"
        return f"{kind} r{ins['rd']}, r{ins['rm']}"
    if kind in ("movw", "movt"):
        return f"{kind} r{ins['rd']}, #{ins['imm']}"
    if kind in ("ldr", "str", "ldrb", "strb", "ldrh", "strh", "ldrsh", "ldrsb"):
        if ins.get("rn") == 15:
            if ins.get("imm") is None:
                return f"{kind} r{ins['rd']}, [pc, =0x{ins['literal']:08X}]"
            return f"{kind} r{ins['rd']}, [pc, #0x{ins['imm']:X}]"
        if "imm" not in ins:
            return f"{kind} r{ins['rd']}, [r{ins['rn']}, r{ins['rm']}]"
        return f"{kind} r{ins['rd']}, [r{ins['rn']}, #0x{ins['imm']:X}]"
    if kind in ("add", "sub"):
        return f"{kind} r{ins['rd']}, r{ins['rn']}, #0x{ins['imm']:X}"
    if kind == "cmp":
        return f"cmp r{ins['rn']}, #0x{ins['imm']:X}"
    if kind == "nop":
        return "nop"
    return f".word 0x{ins['raw']:08X}"


def reg_name(n: int) -> str:
    return {13: "sp", 14: "lr", 15: "pc"}.get(n, f"r{n}")


def reglist(bits: int) -> str:
    names = [reg_name(i) for i in range(16) if bits & (1 << i)]
    return "{" + ", ".join(names) + "}"


def sequence(instructions: list[dict]) -> str:
    return "; ".join(fmt_ins(i) for i in instructions)


# ---------------------------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------------------------
LOAD_KINDS = {"ldr": "U32", "ldrb": "U8", "ldrh": "U16", "ldrsh": "S16", "ldrsb": "S8"}
STORE_KINDS = {"str": "U32", "strb": "U8", "strh": "U16"}
CONST_NAMES = {0: "ReturnsZero", 1: "ReturnsTrue", 0xFFFFFFFF: "ReturnsMinusOne"}


def looks_like_float(value: int) -> bool:
    """A bit pattern a compiler would emit for a float constant (1.0f .. ~1000.0f, either sign)."""
    exponent = (value >> 23) & 0xFF
    return 0x7F <= exponent <= 0x88 or 0x80 <= exponent <= 0x88 and value >> 31


def class_prefix(addr: int, vtables: dict[int, str], names: dict[int, str],
                 by_vtable: dict[str, list[int]]) -> tuple[str, list[str]]:
    """A class prefix shared by 3+ confidently named functions in the same vtable group."""
    group = vtables.get(addr)
    if not group:
        return "", []
    siblings = [a for a in by_vtable.get(group, []) if a != addr]
    confident = [names[a] for a in siblings if is_confident(names.get(a))]
    if len(confident) < 3:
        return "", []
    parts = [n.split("_") for n in confident]
    prefix: list[str] = []
    for i in range(min(len(p) for p in parts)):
        token = parts[0][i]
        if all(p[i] == token for p in parts):
            prefix.append(token)
        else:
            break
    if len(prefix) < 2:
        return "", []
    shared = sum(1 for n in confident if n.startswith("_".join(prefix) + "_"))
    if shared < 3:
        return "", []
    return "_".join(prefix), confident


def propose(addr: int, analysis: Analysis, ctx: dict) -> dict | None:
    """Turn a decoded shape into a proposal, or None when no rule matches exactly."""
    body, terminal = analysis.body, analysis.terminal
    names = ctx["names"]
    prefix, siblings = class_prefix(addr, ctx["vtables"], names, ctx["by_vtable"])
    cls = prefix or "Obj"
    evidence_tail = (f"decoded from code.bin as {analysis.mode}: "
                     f"{sequence(analysis.instructions)}; asm/text agrees on every instruction")

    # ---- rule 1: field getter -------------------------------------------------------------
    if len(body) == 1 and body[0]["kind"] in LOAD_KINDS:
        ins = body[0]
        if ins.get("rd") == 0 and ins.get("rn") == 0 and "imm" in ins:
            offset = ins["imm"]
            name = f"{cls}_Get{LOAD_KINDS[ins['kind']]}At0x{offset:X}"
            return entry(addr, name, f"u32 {name}(void* self)",
                         f"Returns the {LOAD_KINDS[ins['kind']]} field at offset 0x{offset:X} of "
                         f"the object in r0. The shape is certain; the field's meaning is not.",
                         0.5, evidence_tail, ctx, siblings)
    # ---- rule 1b: getter through an add (offset chain fully decoded) -----------------------
    if len(body) == 2 and body[0]["kind"] == "add" and body[1]["kind"] in LOAD_KINDS:
        add, ins = body[0], body[1]
        if (add.get("rd") == 0 and add.get("rn") == 0 and ins.get("rd") == 0
                and ins.get("rn") == 0 and "imm" in ins):
            offset = add["imm"] + ins["imm"]
            name = f"{cls}_Get{LOAD_KINDS[ins['kind']]}At0x{offset:X}"
            return entry(addr, name, f"u32 {name}(void* self)",
                         f"Returns the {LOAD_KINDS[ins['kind']]} field at offset 0x{offset:X} "
                         f"(0x{add['imm']:X} + 0x{ins['imm']:X}) of the object in r0.",
                         0.5, evidence_tail, ctx, siblings)
    # ---- rule 2: field setter -------------------------------------------------------------
    if len(body) == 1 and body[0]["kind"] in STORE_KINDS:
        ins = body[0]
        if ins.get("rd") == 1 and ins.get("rn") == 0 and "imm" in ins:
            offset = ins["imm"]
            name = f"{cls}_Set{STORE_KINDS[ins['kind']]}At0x{offset:X}"
            return entry(addr, name, f"void {name}(void* self, u32 value)",
                         f"Stores the second argument into the {STORE_KINDS[ins['kind']]} field at "
                         f"offset 0x{offset:X} of the object in r0 and returns nothing.",
                         0.5, evidence_tail, ctx, siblings)
    # ---- rule 3: constant return ----------------------------------------------------------
    value = constant_value(body, ctx["code"])
    if value is not None:
        name = CONST_NAMES.get(value, f"ReturnsConstant0x{value:X}")
        note = ""
        if value not in CONST_NAMES and looks_like_float(value):
            note = f" (0x{value:08X} is {struct.unpack('<f', struct.pack('<I', value))[0]!r} as a float)"
        return entry(addr, name, f"u32 {name}(void)",
                     f"Returns the constant 0x{value:X}{note} and does nothing else.",
                     0.5, evidence_tail, ctx, siblings)
    # ---- rule 4: pure forwarder -----------------------------------------------------------
    # ``b X`` is the terminal itself (a tail call leaves nothing behind it), ``bl X; bx lr``
    # keeps the call in the body.  Both forward every argument untouched to exactly one callee.
    forward = None
    if not body and terminal["kind"] == "b":
        # A tail call: the branch is the whole function.  The target must be a known function
        # start, otherwise this is a jump inside some other function and not a thunk.
        if terminal["target"] in ctx["function_addrs"]:
            forward = terminal
    elif len(body) == 1 and body[0]["kind"] == "bl":
        # A call followed by a return: ``bl`` always targets code, so any .text address counts
        # even when Ghidra never made a function out of it.
        if TEXT_LO <= body[0]["target"] < TEXT_HI:
            forward = body[0]
    if forward is not None:
        target = forward["target"]
        callee = names.get(target)
        if not (addr <= target < addr + ctx["size"][addr]):
            if is_confident(callee):
                name = f"{callee}Thunk"
                verb = "Tail-calls" if forward is terminal else "Calls"
                return entry(addr, name, thunk_signature(name, target, ctx),
                             f"{verb} {callee} (0x{target:08X}) with the arguments unchanged "
                             f"and returns its result.", 0.5, evidence_tail, ctx, siblings)
            # The callee has no confident name, so the thunk is named after the callee's
            # address (the convention the earlier batches already use: maybe_Thunk_Call63B368).
            verb = "Tail-calls" if forward is terminal else "Calls"
            return entry(addr, f"maybe_Thunk_Call{target:08X}", "void Thunk(void)",
                         f"{verb} the unnamed function at 0x{target:08X} with the arguments "
                         f"unchanged and returns its result. The callee has no confident name, "
                         f"so the thunk is named after the callee's address.",
                         0.45, evidence_tail, ctx, siblings, change="kept_maybe")
    # ---- rule 5: empty stub ---------------------------------------------------------------
    # Only a real return counts: ``push {r4,lr}; b somewhere`` is a tail call, not a no-op, and
    # is exactly what a wrong-mode decode of a normal function looks like.
    if not body and terminal["kind"] in ("bx", "pop"):
        if prefix:
            name = f"{prefix}_NoOp"
            summary = (f"Does nothing: returns immediately. Sits in the {prefix} vtable group, "
                       f"whose other slots are named {', '.join(siblings[:4])}.")
        else:
            name = f"Nop_{addr:08X}"
            summary = "Does nothing: returns immediately without touching any register or memory."
        return entry(addr, name, f"void {name}(void)", summary, 0.5, evidence_tail, ctx, siblings)
    # ---- rule 6: accessor + field ---------------------------------------------------------
    if len(body) == 2 and body[0]["kind"] == "bl" and body[1]["kind"] in LOAD_KINDS:
        call, ins = body[0], body[1]
        accessor = names.get(call["target"])
        if (is_confident(accessor) and ins.get("rd") == 0 and ins.get("rn") == 0
                and "imm" in ins):
            offset = ins["imm"]
            name = f"{accessor}_Field0x{offset:X}"
            return entry(addr, name, f"u32 {name}(void)",
                         f"Calls the singleton accessor {accessor} (0x{call['target']:08X}) and "
                         f"returns the {LOAD_KINDS[ins['kind']]} field at offset 0x{offset:X} of "
                         f"the object it returns.", 0.5, evidence_tail, ctx, siblings)
    return None


def constant_value(body: list[dict], code: Code) -> int | None:
    """The value a constant-returning body produces in r0, or None."""
    if len(body) == 1:
        ins = body[0]
        if ins["kind"] == "mov" and ins.get("rd") == 0 and ins.get("imm") is not None:
            return ins["imm"]
        if ins["kind"] == "mvn" and ins.get("rd") == 0:
            return (~ins["imm"]) & 0xFFFFFFFF
        if ins["kind"] == "movw" and ins.get("rd") == 0:
            return ins["imm"]
        if ins["kind"] == "ldr" and ins.get("rn") == 15 and "literal" in ins:
            value = code.u32(ins["literal"])
            # A literal that points into the image is a singleton/string address, not a constant.
            if value < IMAGE_LO or value > IMAGE_HI:
                return value
            return None
    if (len(body) == 2 and body[0]["kind"] == "movw" and body[1]["kind"] == "movt"
            and body[0].get("rd") == 0 and body[1].get("rd") == 0):
        return (body[1]["imm"] << 16) | body[0]["imm"]
    return None


def thunk_signature(name: str, target: int, ctx: dict) -> str:
    """The callee's own signature with the thunk's name, so the readable C stays consistent."""
    callee = ctx["by_addr"].get(target)
    signature = (callee or {}).get("signature") or ""
    m = re.match(r"^(.*?)\b([A-Za-z_]\w*)\s*\((.*)\)\s*;?\s*$", signature, re.S)
    if not m:
        return f"void {name}(void)"
    return f"{m.group(1).strip()} {name}({m.group(3)})"


def entry(addr: int, name: str, signature: str, summary: str, confidence: float,
          evidence: str, ctx: dict, siblings: list[str], change: str = "corrected") -> dict:
    previous = ctx["names"].get(addr) or ctx["by_addr"][addr]["name"]
    if siblings:
        evidence += f"; vtable group {ctx['vtables'][addr]} also holds {', '.join(siblings[:5])}"
    return {
        "address": f"0x{addr:08X}",
        "name": name,
        "signature": signature,
        "params": {},
        "summary": summary,
        "confidence": confidence,
        "evidence": evidence,
        "previous_name": previous,
        "previous_confidence": ctx["confidence"].get(addr, 0.0),
        "change": change,
    }


# ---------------------------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------------------------
def build_context() -> dict:
    functions = load_functions()
    names = load_current_names()
    by_addr = {r["addr"]: r for r in functions}
    for addr, row in by_addr.items():
        names.setdefault(addr, row["name"])
    vtables = load_vtables()
    by_vtable: dict[str, list[int]] = collections.defaultdict(list)
    for addr, group in vtables.items():
        by_vtable[group].append(addr)
    return {
        "code": Code.from_file(CODE_BIN),
        "functions": functions,
        "by_addr": by_addr,
        "function_addrs": set(by_addr),
        "size": {r["addr"]: r["size"] for r in functions},
        "names": names,
        "confidence": load_proposal_confidence(OUT),
        "xref": load_xref(),
        "vtables": vtables,
        "by_vtable": by_vtable,
    }


def candidates(ctx: dict) -> list[dict]:
    """Unnamed functions: no confident current name and no confident proposal."""
    out = []
    for row in ctx["functions"]:
        addr = row["addr"]
        if is_confident(ctx["names"].get(addr)):
            continue
        if ctx["confidence"].get(addr, 0.0) >= 0.5:
            continue
        out.append(row)
    return out


def run(ctx: dict, report: bool) -> tuple[list[dict], collections.Counter]:
    todo = candidates(ctx)
    wanted = set()
    for row in todo:
        wanted.update(range(row["addr"], row["addr"] + MAX_SCAN, 2))
    text = AsmText(wanted)
    proposals, stats = [], collections.Counter()
    shapes: collections.Counter = collections.Counter()
    for row in todo:
        analysis = analyse(ctx["code"], text, row["addr"], row["mode"])
        if not analysis.body and analysis.terminal is None:
            stats["skipped_" + analysis.reason.split()[0]] += 1
            continue
        proposal = propose(row["addr"], analysis, ctx)
        if proposal is None:
            stats["no_rule"] += 1
            shapes[" ".join(i["kind"] for i in analysis.body) or "<empty>"] += 1
            continue
        stats["named"] += 1
        proposals.append(proposal)
    dedupe(proposals)
    if report:
        print("shape histogram of the unnamed functions no rule matched (top 25):")
        for shape, count in shapes.most_common(25):
            print(f"  {count:5d}  {shape}")
    return proposals, stats


def dedupe(proposals: list[dict]) -> None:
    """Two identical thunks to the same callee are common (template copies); keep both names unique."""
    used: set[str] = set()
    for proposal in sorted(proposals, key=lambda p: int(p["address"], 16)):
        name = proposal["name"]
        if name in used:
            suffix = 2
            while f"{name}{suffix}" in used:
                suffix += 1
            new = f"{name}{suffix}"
            proposal["signature"] = proposal["signature"].replace(name + "(", new + "(", 1)
            proposal["summary"] += f" Same body as the other {name} in this batch."
            proposal["name"] = new
            name = new
        used.add(name)


def validate(proposals: list[dict], ctx: dict) -> list[str]:
    """Self-check: identifiers, maybe_ prefix, evidence, duplicates, addresses."""
    problems = []
    seen = set()
    for p in proposals:
        addr = int(p["address"], 16)
        name = p["name"]
        if not IDENT.match(name) or name in RESERVED:
            problems.append(f"{p['address']}: invalid C identifier {name!r}")
        if float(p["confidence"]) < 0.5 and not name.startswith("maybe_"):
            problems.append(f"{p['address']}: confidence {p['confidence']} needs maybe_")
        if float(p["confidence"]) >= 0.5 and name.startswith("maybe_"):
            problems.append(f"{p['address']}: maybe_ with confidence {p['confidence']}")
        if not p.get("evidence"):
            problems.append(f"{p['address']}: no evidence")
        if addr in seen:
            problems.append(f"{p['address']}: duplicate address")
        seen.add(addr)
        if addr not in ctx["by_addr"]:
            problems.append(f"{p['address']}: not a known function")
        if not p.get("summary"):
            problems.append(f"{p['address']}: no summary")
        if not p.get("previous_name"):
            problems.append(f"{p['address']}: no previous_name")
        if p.get("change") not in ("corrected", "confirmed", "kept_maybe"):
            problems.append(f"{p['address']}: bad change {p.get('change')!r}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate the existing overlay, write nothing")
    ap.add_argument("--dry-run", action="store_true", help="print the proposals, write nothing")
    ap.add_argument("--report", action="store_true",
                    help="print the unmatched shape histogram and write nothing")
    ap.add_argument("--out", default=str(OUT), help="output path (default R_T01.json)")
    args = ap.parse_args()

    if args.check:
        if not OUT.exists():
            print(f"{OUT.relative_to(ROOT)} does not exist", file=sys.stderr)
            return 1
        proposals = json.loads(OUT.read_text(encoding="utf-8"))
        ctx = build_context()
        problems = validate(proposals, ctx)
        by_rule = collections.Counter(rule_of(p) for p in proposals)
        print(f"{OUT.relative_to(ROOT)}: {len(proposals)} entries")
        for rule, count in sorted(by_rule.items()):
            print(f"  {rule:22} {count}")
        for problem in problems:
            print("  PROBLEM", problem)
        print("OK" if not problems else f"{len(problems)} problem(s)")
        return 0 if not problems else 1

    ctx = build_context()
    proposals, stats = run(ctx, args.report)
    problems = validate(proposals, ctx)
    by_rule = collections.Counter(rule_of(p) for p in proposals)
    print(f"candidates (unnamed, confidence < 0.5): {len(candidates(ctx)):,}")
    print(f"proposals: {len(proposals):,}")
    for rule, count in sorted(by_rule.items()):
        print(f"  {rule:22} {count}")
    print(f"left alone: {dict(stats)}")
    if problems:
        for problem in problems:
            print("PROBLEM", problem)
        return 1
    if args.dry_run:
        for p in proposals:
            print(f"{p['address']}  {p['name']:44} {p['confidence']}  {p['summary'][:90]}")
        return 0
    if args.report:
        # A report must not overwrite the batch: the merged file is the record of what was applied.
        return 0
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(proposals, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    # Re-read with a strict UTF-8 decode: a stray cp1252 byte once made a whole batch unreadable.
    json.loads(out.read_text(encoding="utf-8"))
    print(f"wrote {out.relative_to(ROOT)} ({len(proposals)} entries)")
    return 0


def rule_of(proposal: dict) -> str:
    """Which rule produced a proposal (read back from the name, for the report)."""
    name = proposal["name"].removeprefix("maybe_")
    if "_Get" in name and "At0x" in name:
        return "1 field getter"
    if "_Set" in name and "At0x" in name:
        return "2 field setter"
    if name.startswith("Returns"):
        return "3 constant return"
    if re.search(r"Thunk\d*$", name) or name.startswith("Thunk_") or "Thunk_Call" in name:
        return "4 pure forwarder"
    if name.endswith("_NoOp") or name.startswith("Nop_"):
        return "5 empty stub"
    if "_Field0x" in name:
        return "6 accessor getter"
    return "?"


if __name__ == "__main__":
    sys.exit(main())
