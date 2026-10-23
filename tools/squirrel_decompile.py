#!/usr/bin/env python3
"""tools/squirrel_decompile.py - Squirrel bytecode (.cnut) -> readable pseudo-source.

Built on tools/sqbin.py. The game's scripts use the Squirrel 2.2 instruction set
(ARITH/CMP with an operator byte, PREPCALLK, NEWSLOTA, vargc/vargv), so the
patterns recognised here are the ones the Squirrel 2.2 compiler emits:

* expressions are rebuilt symbolically from register writes (constants, locals,
  member/index access, calls, arithmetic, comparisons, &&/||, ?:, table literals,
  closures), locals are named from the local-variable info;
* control flow is structured into if/else, while/for (backward jumps), switch,
  break/continue and return;
* anything that does not fit is emitted as a clearly marked ``ASM FALLBACK``
  comment block holding the raw instructions, so the output is never wrong, only
  less pretty. ``$rN`` names a VM register whose value could not be expressed.

The output is READ-ONLY pseudo-source: there is no compiler back to bytecode.
Edit ``script.nut`` (the assembly listing) and rebuild as before.

Usage:
    python tools/squirrel_decompile.py <file.cnut>          # print to stdout
    python tools/squirrel_decompile.py --all                # every script + audit report
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import sqbin  # noqa: E402
from tools.sqbin import OP, OPS, OT_BOOL, OT_FLOAT, OT_INTEGER, OT_NULL, OT_STRING  # noqa: E402

DATA_DIR = PROJECT_ROOT / "game_data"
ASSETS_DIR = PROJECT_ROOT / "game_assets"
AUDIT_DIR = PROJECT_ROOT / "audit"
SUFFIX = ".decompiled.nut"
IND = "    "
NOREG = 0xFF

KEYWORDS = {
    "while", "do", "if", "else", "break", "continue", "return", "null", "function", "local", "for",
    "foreach", "in", "typeof", "delegate", "clone", "switch", "case", "default", "this", "parent",
    "class", "extends", "constructor", "instanceof", "yield", "try", "catch", "throw", "resume",
    "true", "false", "static", "vargc", "vargv", "enum", "const", "__LINE__", "__FILE__",
}
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Operator precedence (higher binds tighter).
P_ASSIGN, P_TERN, P_OR, P_AND, P_BOR, P_BXOR, P_BAND, P_EQ, P_REL, P_SHIFT, P_ADD, P_MUL, P_UNARY, P_POST, P_PRIM = range(1, 16)
BIN_PREC = {
    "||": P_OR, "&&": P_AND, "|": P_BOR, "^": P_BXOR, "&": P_BAND, "==": P_EQ, "!=": P_EQ,
    "<": P_REL, "<=": P_REL, ">": P_REL, ">=": P_REL, "in": P_REL, "instanceof": P_REL,
    "<<": P_SHIFT, ">>": P_SHIFT, ">>>": P_SHIFT, "+": P_ADD, "-": P_ADD, "*": P_MUL, "/": P_MUL, "%": P_MUL,
}
CMP_OPS = {0: ">", 2: ">=", 3: "<", 4: "<="}
BW_OPS = {0: "&", 2: "|", 3: "^", 4: "<<", 5: ">>", 6: ">>>"}
JUMPS = {OP["JMP"], OP["JZ"], OP["JNZ"], OP["AND"], OP["OR"]}


class Unstructured(Exception):
    """Raised when a region does not match a known compiler pattern."""


def is_ident(s) -> bool:
    return isinstance(s, str) and bool(_IDENT.match(s)) and s not in KEYWORDS


def fmt_float(v: float) -> str:
    bits = struct.pack("<f", v)
    for p in range(1, 10):
        s = f"{v:.{p}g}"
        if struct.pack("<f", float(s)) == bits:
            break
    if "e" not in s and "." not in s and "inf" not in s and "nan" not in s:
        s += ".0"
    return s


_ESC = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t", "\0": "\\0", "\a": "\\a",
        "\b": "\\b", "\v": "\\v", "\f": "\\f"}


def fmt_string(s: str) -> str:
    return '"' + "".join(_ESC.get(c, c if c >= " " or c in _ESC else f"\\x{ord(c):02x}") for c in s) + '"'


def fmt_obj(o: sqbin.Obj) -> str:
    if o.type == OT_STRING:
        return fmt_string(o.value)
    if o.type == OT_INTEGER:
        return str(o.value)
    if o.type == OT_FLOAT:
        return fmt_float(o.value)
    if o.type == OT_BOOL:
        return "true" if o.value else "false"
    return "null"


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

class E:
    prec = P_PRIM
    se = False       # has a side effect (must be emitted exactly once, in order)
    simple = False   # may be re-read any number of times (constants, locals)
    seq = 0

    def r(self, d: "FuncDecomp", ind: str) -> str:
        raise NotImplementedError

    def kids(self):
        return ()


def wrap(e: E, d, ind, need: int) -> str:
    s = e.r(d, ind)
    return f"({s})" if e.prec < need else s


class Const(E):
    simple = True

    def __init__(self, text, value=None, kind=None):
        self.text, self.value, self.kind = text, value, kind

    def r(self, d, ind):
        return self.text


def const_of(o: sqbin.Obj) -> Const:
    return Const(fmt_obj(o), o.value, o.type)


class Name(E):
    simple = True

    def __init__(self, name):
        self.name = name

    def r(self, d, ind):
        return self.name


class Reg(E):
    """A VM register the decompiler could not express (or materialised on purpose)."""
    simple = True

    def __init__(self, n, defined=False):
        self.n, self.defined = n, defined

    def r(self, d, ind):
        return f"$r{self.n}"


class Root(E):
    simple = True

    def r(self, d, ind):
        return "::"


class Member(E):
    prec = P_POST

    def __init__(self, obj: E, key: E, bare_ok=True):
        self.obj, self.key, self.bare_ok = obj, key, bare_ok

    def kids(self):
        return (self.obj, self.key)

    def r(self, d, ind):
        k = self.key
        ident = isinstance(k, Const) and k.kind == OT_STRING and is_ident(k.value)
        if ident and isinstance(self.obj, Root):
            return "::" + k.value
        if ident and self.bare_ok and isinstance(self.obj, Name) and self.obj.name == "this":
            return k.value
        o = wrap(self.obj, d, ind, P_POST)
        return f"{o}.{k.value}" if ident else f"{o}[{k.r(d, ind)}]"


class ThisArg(E):
    """Second result of PREPCALL(K): the object a method is called on."""

    def __init__(self, obj):
        self.obj = obj
        self.prec = obj.prec

    def kids(self):
        return (self.obj,)

    def r(self, d, ind):
        return self.obj.r(d, ind)


class Call(E):
    prec = P_POST
    se = True

    def __init__(self, fn, this, args):
        self.fn, self.this, self.args = fn, this, args

    def kids(self):
        return (self.fn, self.this, *self.args)

    def r(self, d, ind):
        args = ", ".join(a.r(d, ind) for a in self.args)
        fn, this = self.fn, self.this
        if isinstance(this, ThisArg) and isinstance(fn, Member) and fn.obj is this.obj:
            return f"{wrap(fn, d, ind, P_POST)}({args})"
        if isinstance(this, Name) and this.name == "this":
            return f"{wrap(fn, d, ind, P_POST)}({args})"
        allargs = ", ".join(a.r(d, ind) for a in (this, *self.args))
        return f"{wrap(fn, d, ind, P_POST)}.call({allargs})"


class Unary(E):
    prec = P_UNARY

    def __init__(self, op, e, se=False):
        self.op, self.e, self.se = op, e, se

    def kids(self):
        return (self.e,)

    def r(self, d, ind):
        s = wrap(self.e, d, ind, P_UNARY)
        if self.op[-1].isalpha():
            return f"{self.op} {s}"
        if s.startswith(self.op[0]) and self.op in "-+":
            s = f"({s})"
        return self.op + s


class Postfix(E):
    prec = P_POST
    se = True

    def __init__(self, op, e):
        self.op, self.e = op, e

    def kids(self):
        return (self.e,)

    def r(self, d, ind):
        return wrap(self.e, d, ind, P_POST) + self.op


class Bin(E):
    def __init__(self, op, a, b, se=False):
        self.op, self.a, self.b = op, a, b
        self.prec = BIN_PREC.get(op, P_ASSIGN)
        self.se = se or a.se or b.se

    def kids(self):
        return (self.a, self.b)

    def r(self, d, ind):
        if self.prec == P_ASSIGN:  # delegate and friends: always parenthesise operands
            return f"{wrap(self.a, d, ind, P_TERN)} {self.op} {wrap(self.b, d, ind, P_TERN)}"
        assoc = self.op in ("&&", "||") and isinstance(self.b, Bin) and self.b.op == self.op
        return f"{wrap(self.a, d, ind, self.prec)} {self.op} {wrap(self.b, d, ind, self.prec + (0 if assoc else 1))}"


class Delegate(E):
    """Squirrel 2.2 `delegate parent : table` (sets table's delegate, yields table)."""
    prec = P_ASSIGN
    se = True

    def __init__(self, parent, table):
        self.parent, self.table = parent, table

    def kids(self):
        return (self.parent, self.table)

    def r(self, d, ind):
        return f"delegate {wrap(self.parent, d, ind, P_TERN)} : {wrap(self.table, d, ind, P_TERN)}"


class Tern(E):
    prec = P_TERN

    def __init__(self, c, a, b):
        self.c, self.a, self.b = c, a, b
        self.se = c.se or a.se or b.se

    def kids(self):
        return (self.c, self.a, self.b)

    def r(self, d, ind):
        return f"{wrap(self.c, d, ind, P_OR)} ? {wrap(self.a, d, ind, P_TERN)} : {wrap(self.b, d, ind, P_TERN)}"


class Vargc(E):
    def r(self, d, ind):
        return "vargc"


class Vargv(E):
    prec = P_POST

    def __init__(self, idx):
        self.idx = idx

    def kids(self):
        return (self.idx,)

    def r(self, d, ind):
        return f"vargv[{self.idx.r(d, ind)}]"


class Closure(E):
    def __init__(self, index):
        self.index = index

    def r(self, d, ind):
        return d.render_closure(self.index, ind, None)


class Table(E):
    def __init__(self):
        self.items: list[tuple[E, E]] = []

    def kids(self):
        return tuple(x for kv in self.items for x in kv)

    def r(self, d, ind):
        if not self.items:
            return "{}"
        inner = ind + IND
        lines = ["{"]
        for k, v in self.items:
            key = k.value if isinstance(k, Const) and k.kind == OT_STRING and is_ident(k.value) else None
            if key and isinstance(v, Closure) and d.closure_name(v.index) == key:
                lines.append(inner + d.render_closure(v.index, inner, key))
            elif key:
                lines.append(f"{inner}{key} = {v.r(d, inner)},")
            else:
                lines.append(f"{inner}[{k.r(d, inner)}] = {v.r(d, inner)},")
        lines.append(ind + "}")
        return "\n".join(lines)


class Array(E):
    def __init__(self):
        self.items: list[E] = []

    def kids(self):
        return tuple(self.items)

    def r(self, d, ind):
        return "[" + ", ".join(x.r(d, ind) for x in self.items) + "]"


# ---------------------------------------------------------------------------
# Statements: tuples (kind, ...)
#   ("expr", e) ("local", name, e|None) ("assign", lhs_e, op, rhs_e) ("return", e|None)
#   ("if", cond, then, else) ("while", cond, body) ("for", init, cond, incr, body)
#   ("switch", subj, [(case_e|None, body)]) ("break",) ("continue",)
#   ("asm", lo, hi, reason) ("comment", text)
# ---------------------------------------------------------------------------


class State:
    """Pending expression per temp register."""
    __slots__ = ("regs",)

    def __init__(self, regs=None):
        self.regs: dict[int, E] = dict(regs or {})

    def copy(self):
        return State(self.regs)


def insn_regs(i: sqbin.Insn):
    """(reads, writes) register sets for one instruction; None reads = unknown op."""
    o, a0, a1, a2, a3 = i.op, i.arg0, i.arg1, i.arg2, i.arg3
    n = OPS[o] if o < len(OPS) else "?"
    if n in ("LOAD", "LOADINT", "LOADFLOAT", "LOADBOOL", "LOADROOTTABLE", "NEWTABLE", "NEWARRAY", "VARGC",
             "CLOSURE", "LOADFREEVAR"):
        return (), (a0,)
    if n == "DLOAD":
        return (), (a0, a2)
    if n in ("MOVE", "GETVARGV", "GETPARENT", "NEG", "NOT", "BWNOT", "TYPEOF", "CLONE"):
        return (a1,), (a0,)
    if n == "GETK":
        return (a2,), (a0,)
    if n == "DMOVE":
        return (a1, a3), (a0, a2)
    if n == "PREPCALL":
        return (a1, a2), (a0, a3)
    if n == "PREPCALLK":
        return (a2,), (a0, a3)
    if n in ("GET", "DELETE", "EXISTS", "INSTANCEOF", "DELEGATE", "ARITH", "BITW", "CMP"):
        return (a1, a2), (a0,)
    if n in ("CALL", "TAILCALL"):
        return (a1, *range(a2, a2 + a3)), (a0,)
    if n in ("SET", "NEWSLOT"):
        return (a1, a2, a3), (a0,)
    if n == "NEWSLOTA":
        return (a1, a2, a3), ()
    if n in ("EQ", "NE"):
        return ((a2,) if a3 else (a2, a1)), (a0,)
    if n == "RETURN":
        return ((a1,) if a0 != NOREG else ()), ()
    if n == "LOADNULLS":
        return (), tuple(range(a0, a0 + a1))
    if n in ("JZ", "JNZ"):
        return (a0,), ()
    if n == "JMP":
        return (), ()
    if n in ("AND", "OR"):
        return (a2,), (a0,)
    if n == "APPENDARRAY":
        return ((a0,) if a3 else (a0, a1)), ()
    if n == "COMPARITHL":
        return (a1, a2), (a0, a1)
    if n in ("INCL", "PINCL"):
        return (a1,), (a0, a1)
    if n in ("INC", "PINC"):
        return (a1, a2), (a0,)
    if n == "COMPARITH":
        return (a1 >> 16, a1 & 0xFFFF, a2), (a0,)
    return None, None


class FuncDecomp:
    def __init__(self, f: sqbin.Func):
        self.f = f
        self.ins = f.instructions
        self.n = len(self.ins)
        self.lits = f.literals
        self.locals = [(n.value, p, a, b) for n, p, a, b in f.localvarinfos]
        self.nparams = len(f.parameters)
        self.children: dict[int, FuncDecomp] = {}
        self.seq = 0
        self.declared: set[int] = {k for k, (_, p, a, _) in enumerate(self.locals) if p < self.nparams and a == 0}
        self.starts: dict[int, list[int]] = {}
        for k, (_, p, a, _) in enumerate(self.locals):
            if k not in self.declared:
                self.starts.setdefault(a, []).append(k)
        # jumps
        self.target: dict[int, int] = {}
        self.incoming: dict[int, list[int]] = {}
        self.loop_back: dict[int, int] = {}
        for pc, i in enumerate(self.ins):
            if i.op in JUMPS:
                t = pc + 1 + i.arg1
                self.target[pc] = t
                self.incoming.setdefault(t, []).append(pc)
                if i.op == OP["JMP"] and t <= pc:
                    self.loop_back[t] = max(self.loop_back.get(t, -1), pc)
        self.stmts = None

    # ---- naming --------------------------------------------------------------
    def local_at(self, reg: int, pc: int):
        best = None
        for k, (name, p, a, b) in enumerate(self.locals):
            if p == reg and a <= pc <= b and (best is None or a > self.locals[best][2]):
                best = k
        return best

    def live_names(self, pc: int) -> set:
        return {name for name, p, a, b in self.locals if a <= pc <= b and name != "this"}

    def closure_name(self, idx):
        fn = self.f.functions[idx].name
        return fn.value if fn.type == OT_STRING else None

    def child(self, idx) -> "FuncDecomp":
        if idx not in self.children:
            self.children[idx] = FuncDecomp(self.f.functions[idx])
            self.children[idx].decompile()
        return self.children[idx]

    # ---- register reads / writes ----------------------------------------------
    def new(self, e: E) -> E:
        self.seq += 1
        e.seq = self.seq
        return e

    def read(self, st: State, r: int, pc: int, consume=True) -> E:
        k = self.local_at(r, pc)
        if k is not None:
            return Name(self.locals[k][0])
        e = st.regs.get(r)
        if e is None:
            return Reg(r)
        if consume and not isinstance(e, Reg):
            del st.regs[r]
        return e

    def live_after(self, r: int, pc: int, inclusive=False, limit=4000) -> bool:
        """Is temp register r read (before being overwritten) on some path after pc?

        inclusive=True also counts a read by the instruction at pc itself."""
        stack, seen = [(pc, not inclusive)], set()
        while stack and limit > 0:
            k, first = stack.pop()
            while 0 <= k < self.n and limit > 0:
                limit -= 1
                if not first:
                    if k in seen:
                        break
                    seen.add(k)
                i = self.ins[k]
                rd, wr = insn_regs(i)
                if rd is None:
                    return True
                if not first and r in rd:
                    return True
                if r in wr and i.op not in (OP["AND"], OP["OR"]):
                    break
                first = False
                if i.op == OP["RETURN"]:
                    break
                if i.op in JUMPS:
                    t = self.target[k]
                    if i.op == OP["JMP"]:
                        k = t
                        continue
                    if not (i.op in (OP["AND"], OP["OR"]) and i.arg0 == r):  # &&/|| writes r when it jumps
                        stack.append((t, False))
                k += 1
        return limit <= 0

    def write(self, st: State, r: int, e: E, pc: int, out: list):
        k = self.local_at(r, pc)
        if k is not None and (k in self.declared or self.locals[k][2] <= pc):
            self.emit(st, out, pc, ("assign", Name(self.locals[k][0]), "=", e))
            return
        old = st.regs.get(r)
        if old is not None and old.se:
            self.flush(st, out, pc, upto=old.seq)
        st.regs[r] = e

    def flush(self, st: State, out: list, pc: int, upto=None, pure=False, regs=None, inclusive=False):
        """Emit pending side-effect expressions (in evaluation order) as statements.

        With pure=True, pending side-effect-free expressions that are still read
        later are materialised into $rN as well."""
        items = sorted(st.regs.items(), key=lambda kv: kv[1].seq)
        for r, e in items:
            if regs is not None and r not in regs:
                continue
            if e.simple and not isinstance(e, Reg):
                continue
            if isinstance(e, Reg):
                continue
            if upto is not None and e.seq > upto:
                continue
            if e.se:
                if self.live_after(r, pc, inclusive):
                    out.append(("assign", Reg(r, True), "=", e))
                    st.regs[r] = Reg(r, True)
                else:
                    out.append(("expr", e))
                    del st.regs[r]
            elif pure and not isinstance(e, ThisArg):
                if self.live_after(r, pc, inclusive):
                    out.append(("assign", Reg(r, True), "=", e))
                    st.regs[r] = Reg(r, True)
                else:
                    del st.regs[r]

    def emit(self, st: State, out: list, pc: int, stmt):
        self.flush(st, out, pc, pure=True)
        out.append(stmt)

    def declare(self, st: State, pc: int, out: list, block_end=False):
        for k in self.starts.get(pc, ()):
            if k in self.declared:
                continue
            name, slot, start, stop = self.locals[k]
            if (start > stop) != block_end:
                # start > stop: a local declared as the last statement of a block; the
                # compiler closes its scope before it opens, so declare it at the block end
                continue
            self.declared.add(k)
            e = st.regs.pop(slot, None)
            if e is None and start > stop:
                continue
            if e is None:
                out.append(("comment", f"local {name} (slot {slot}) starts here; its initial value was set in bytecode above"))
                continue
            if isinstance(e, Const) and e.kind == OT_NULL and e.text == "null":
                e = None
            self.emit(st, out, pc, ("local", name, e))

    # ---- structuring ---------------------------------------------------------
    def decompile(self):
        out: list = []
        st = State()
        try:
            self.block(0, self.n, st, out, None, None, top=True)
            self.flush(st, out, self.n - 1)
        except Unstructured as exc:
            out = [("asm", 0, self.n, str(exc) or "unstructured")]
        self.stmts = self.prettify(out)
        return self.stmts

    def block(self, start, end, st, out, brk, cont, skip_head=None, top=False):
        pc = start
        while pc < end:
            self.declare(st, pc, out)
            back = self.loop_back.get(pc)
            if back is not None and pc != skip_head and back < end:
                pc = self.guard(self.do_loop, pc, back + 1, st, out, brk, cont)
                continue
            i = self.ins[pc]
            name = OPS[i.op] if i.op < len(OPS) else "?"
            if name == "JZ" or name == "JNZ":
                pc = self.guard(self.do_if, pc, None, st, out, brk, cont, end)
            elif name in ("AND", "OR"):
                pc = self.guard(self.do_andor, pc, self.target[pc], st, out, brk, cont, end)
            elif name == "JMP":
                t = self.target[pc]
                if t == pc + 1:
                    pc += 1
                elif t == brk:
                    self.flush(st, out, pc, pure=True)
                    out.append(("break",))
                    pc += 1
                elif t == cont:
                    self.flush(st, out, pc, pure=True)
                    out.append(("continue",))
                    pc += 1
                elif pc < t <= end and all(pc < s < t for x in range(pc + 1, t) for s in self.incoming.get(x, ())):
                    # skips dead code only (e.g. the fall-through jump after a switch case's break)
                    pc = t
                else:
                    pc = self.fallback(pc, pc + 1, st, out, brk, cont, end, "unmatched jump")
            elif name in ("EQ", "NE") and self.is_switch(pc, st):
                pc = self.guard(self.do_switch, pc, None, st, out, brk, cont, end)
            elif name == "RETURN":
                if top and pc == self.n - 1 and i.arg0 == NOREG:
                    pc += 1
                    continue
                val = self.read(st, i.arg1, pc) if i.arg0 != NOREG else None
                self.emit(st, out, pc, ("return", val))
                pc += 1
            else:
                try:
                    self.simple(i, pc, st, out)
                    pc += 1
                except Unstructured as exc:
                    pc = self.fallback(pc, pc + 1, st, out, brk, cont, end, str(exc))
        self.declare(st, pc, out, block_end=True)
        return pc

    def guard(self, fn, pc, hi, st, out, brk, cont, end=None):
        """Run a structuring handler; on failure emit its region as an ASM block."""
        saved_regs, saved_decl, saved_len = dict(st.regs), set(self.declared), len(out)
        try:
            return fn(pc, st, out, brk, cont, end) if end is not None else fn(pc, st, out, brk, cont)
        except Unstructured as exc:
            st.regs = saved_regs
            self.declared = saved_decl
            del out[saved_len:]
            if hi is None:
                hi = getattr(exc, "hi", None) or pc + 1
            return self.fallback(pc, hi, st, out, brk, cont, end if end is not None else self.n, str(exc))

    def fallback(self, lo, hi, st, out, brk, cont, end, reason):
        hi = max(hi, lo + 1)
        exits = {brk, cont, end}
        changed = True
        while changed:
            changed = False
            for k in range(lo, hi):
                t = self.target.get(k)
                if t is None or t in exits or lo <= t <= hi:
                    continue
                if t < lo or t > end:
                    raise Unstructured(f"{reason}; jump at {k} leaves region")
                hi, changed = t, True
            for t in range(lo + 1, hi):
                for s in self.incoming.get(t, ()):
                    if not lo <= s < hi:
                        if s < lo or s >= end:
                            raise Unstructured(f"{reason}; jump into region at {t}")
                        hi, changed = s + 1, True
        hi = min(hi, end)
        regs_read = set()
        for k in range(lo, hi):
            rd, _ = insn_regs(self.ins[k])
            regs_read.update(rd if rd is not None else range(256))
        self.flush(st, out, lo, pure=True)
        for r, e in sorted(st.regs.items(), key=lambda kv: kv[1].seq):
            if r in regs_read and not isinstance(e, Reg):
                out.append(("assign", Reg(r, True), "=", e))
        out.append(("asm", lo, hi, reason))
        st.regs.clear()
        for k, (_, p, a, b) in enumerate(self.locals):
            if lo < a <= hi:
                self.declared.add(k)
        return hi

    def sub(self, lo, hi, st, brk, cont, skip_head=None):
        out: list = []
        pc = self.block(lo, hi, st, out, brk, cont, skip_head)
        if pc != hi:
            raise Unstructured("region overran")
        return out

    def do_if(self, pc, st, out, brk, cont, end):
        i = self.ins[pc]
        t = self.target[pc]
        cond = self.read(st, i.arg0, pc)
        if i.op == OP["JNZ"]:
            cond = Unary("!", cond)
        self.flush(st, out, pc)
        if t == brk or t == cont:
            stmt = ("break",) if t == brk else ("continue",)
            out.append(("if", Unary("!", cond), [stmt], []))
            return pc + 1
        if not pc < t <= end:
            raise Unstructured("conditional jump leaves region")
        else_lo = else_hi = t
        then_hi = t
        j = t - 1
        if j > pc and self.ins[j].op == OP["JMP"]:
            e = self.target[j]
            if t < e <= end:  # a jump to t itself is a no-op (an inner if's empty else)
                then_hi, else_hi = j, e
        st1, st2 = st.copy(), st.copy()
        then = self.sub(pc + 1, then_hi, st1, brk, cont)
        els = self.sub(else_lo, else_hi, st2, brk, cont) if else_hi > else_lo else []
        diff = {r for r in set(st1.regs) | set(st2.regs) if st1.regs.get(r) is not st2.regs.get(r)}
        if not then and not els and len(diff) == 1:
            (r,) = diff
            a, b = st1.regs.get(r), st2.regs.get(r)
            # a ?: only when its value is used; `if (c) f(); else g();` stays an if/else
            if a is not None and b is not None and else_hi > else_lo and self.local_at(r, pc) is None \
                    and self.live_after(r, else_hi, inclusive=True):
                st.regs = {k: v for k, v in st1.regs.items() if k not in diff}
                st.regs[r] = self.new(Tern(cond, a, b))
                return else_hi
        self.flush(st1, then, then_hi, inclusive=True)
        self.flush(st2, els, else_hi, inclusive=True)
        merged = {}
        for r in diff:
            if self.local_at(r, pc) is None and self.live_after(r, else_hi, inclusive=True):
                for s, body in ((st1, then), (st2, els)):
                    if r in s.regs and not isinstance(s.regs[r], Reg):
                        body.append(("assign", Reg(r, True), "=", s.regs[r]))
                merged[r] = Reg(r, True)
        st.regs = {k: v for k, v in st1.regs.items() if k not in diff and st2.regs.get(k) is v}
        st.regs.update(merged)
        out.append(("if", cond, then, els))
        return else_hi

    def do_andor(self, pc, st, out, brk, cont, end):
        i = self.ins[pc]
        t = self.target[pc]
        if not pc < t <= end:
            raise Unstructured("&&/|| jump leaves region")
        first = self.read(st, i.arg2, pc, consume=False)
        st1 = st.copy()
        st1.regs.pop(i.arg2, None)
        st1.regs.pop(i.arg0, None)
        stmts = self.sub(pc + 1, t, st1, brk, cont)
        second = st1.regs.get(i.arg0)
        if stmts or second is None or self.local_at(i.arg0, pc) is not None:
            raise Unstructured("&&/|| operand is not a pure expression")
        keep = {k: v for k, v in st1.regs.items() if st.regs.get(k) is v and k != i.arg0}
        st.regs = keep
        st.regs[i.arg0] = self.new(Bin("&&" if i.op == OP["AND"] else "||", first, second))
        return t

    def do_loop(self, h, st, out, brk, cont):
        j = self.loop_back[h]
        x = j + 1
        self.flush(st, out, h, pure=True)
        # condition: straight-line code from h up to a JZ that exits the loop
        cond, body_lo = None, h
        k = h
        while k < j:
            op = self.ins[k].op
            if op in (OP["JZ"], OP["JNZ"]):
                if self.target[k] == x:
                    st1 = State()
                    try:
                        pre = self.sub(h, k, st1, None, None, skip_head=h)
                    except Unstructured:
                        pre = ["fail"]
                    if not pre:
                        cond = self.read(st1, self.ins[k].arg0, k)
                        if op == OP["JNZ"]:
                            cond = Unary("!", cond)
                        body_lo = k + 1
                break
            if op in (OP["JMP"], OP["RETURN"]) or (op in (OP["AND"], OP["OR"]) and self.target[k] > j):
                break
            if op in (OP["AND"], OP["OR"]):
                k = self.target[k]
                continue
            k += 1
        # for-loop increment: forward jumps from the body to a straight-line tail before the back edge
        incr_lo = None
        for s in range(body_lo, j):
            t = self.target.get(s)
            if self.ins[s].op != OP["JMP"] or t is None or not s < t < j:
                continue
            if any(self.ins[q].op in (OP["JZ"], OP["JNZ"]) for q in self.incoming.get(s + 1, ())):
                continue  # the jump over an else branch, not a continue
            tail_plain = all(q not in self.target and self.ins[q].op != OP["RETURN"] for q in range(t, j))
            if tail_plain and (incr_lo is None or t > incr_lo):
                incr_lo = t
        st.regs.clear()
        if incr_lo is not None:
            body = self.sub(body_lo, incr_lo, State(), x, incr_lo, skip_head=h)
            st2 = State()
            incr = self.sub(incr_lo, j, st2, None, None)
            self.flush(st2, incr, j, inclusive=True)
            if len(incr) != 1 or incr[0][0] not in ("expr", "assign"):
                raise Unstructured("for-loop increment is not a single expression")
            out.append(("for", None, cond, incr[0], body))
        else:
            st3 = State()
            body = self.sub(body_lo, j, st3, x, h, skip_head=h)
            self.flush(st3, body, j, inclusive=True)
            out.append(("while", cond if cond is not None else Const("true"), body))
        st.regs.clear()
        return x

    def is_switch(self, pc, st):
        i = self.ins[pc]
        if i.op != OP["EQ"] or i.arg3 or i.arg0 != i.arg1 or i.arg2 == i.arg0:
            return False
        if pc + 1 >= self.n or self.ins[pc + 1].op != OP["JZ"] or self.ins[pc + 1].arg0 != i.arg0:
            return False
        return self.local_at(i.arg2, pc) is None and i.arg2 < i.arg0

    def do_switch(self, pc, st, out, brk, cont, end):
        x = self.ins[pc].arg2
        subj = st.regs.pop(x, None)
        if subj is None:
            raise Unstructured("switch subject unknown")
        trg = self.ins[pc].arg0
        first_val = self.read(st, trg, pc)
        self.flush(st, out, pc)
        # case chain: (value, eq_pc, body_lo, next_cond_lo)
        cases = []
        eq, val = pc, first_val
        while True:
            jz = eq + 1
            nxt = self.target[jz]
            if not jz < nxt <= end:
                raise Unstructured("switch case jump leaves region")
            nexteq = None
            if self.ins[nxt - 1].op == OP["JMP"] and nxt - 1 > jz:
                k = nxt
                while k < end and self.target.get(k) is None and self.ins[k].op != OP["RETURN"]:
                    ins = self.ins[k]
                    if ins.op == OP["EQ"] and ins.arg0 == ins.arg1 and ins.arg2 == x and k + 1 < end \
                            and self.ins[k + 1].op == OP["JZ"] and self.target[nxt - 1] == k + 2:
                        nexteq = k
                        break
                    k += 1
            cases.append((val, jz + 1, nxt - 1 if nexteq is not None else nxt))
            if nexteq is None:
                last_next = nxt
                break
            st1 = State()
            pre = self.sub(nxt, nexteq, st1, None, None)
            if pre or self.ins[nexteq].arg0 not in st1.regs:
                raise Unstructured("switch case value is not a pure expression")
            val = st1.regs[self.ins[nexteq].arg0]
            eq = nexteq
        sw_end = last_next
        for k in range(pc, last_next):
            t = self.target.get(k)
            if t is not None and self.ins[k].op == OP["JMP"] and last_next < t <= end:
                sw_end = max(sw_end, t)
        arms = []
        for val, lo, hi in cases:
            arms.append((val, self.case_body(lo, hi, sw_end, cont)))
        if sw_end > last_next:
            arms.append((None, self.case_body(last_next, sw_end, sw_end, cont)))
        out.append(("switch", subj, arms))
        st.regs.clear()
        return sw_end

    def case_body(self, lo, hi, sw_end, cont):
        st = State()
        body = self.sub(lo, hi, st, sw_end, cont)
        self.flush(st, body, hi, inclusive=True)
        return body

    # ---- straight-line instructions ------------------------------------------
    def simple(self, i: sqbin.Insn, pc: int, st: State, out: list):
        name = OPS[i.op] if i.op < len(OPS) else "?"
        a0, a1, a2, a3 = i.arg0, i.arg1, i.arg2, i.arg3
        rd = lambda r: self.read(st, r, pc)  # noqa: E731
        lit = lambda k: const_of(self.lits[k]) if 0 <= k < len(self.lits) else Const(f"$lit{k}")  # noqa: E731
        put = lambda r, e: self.write(st, r, self.new(e), pc, out)  # noqa: E731
        if name == "LOAD":
            put(a0, lit(a1))
        elif name == "LOADINT":
            put(a0, Const(str(a1), a1, OT_INTEGER))
        elif name == "LOADFLOAT":
            put(a0, Const(fmt_float(struct.unpack("<f", struct.pack("<i", a1))[0])))
        elif name == "LOADBOOL":
            put(a0, Const("true" if a1 else "false"))
        elif name == "DLOAD":
            put(a0, lit(a1))
            put(a2, lit(a3))
        elif name == "LOADNULLS":
            for r in range(a0, a0 + a1):
                put(r, Const("null", None, OT_NULL))
        elif name == "LOADROOTTABLE":
            put(a0, Root())
        elif name == "MOVE":
            put(a0, rd(a1))
        elif name == "DMOVE":
            v1, v3 = rd(a1), rd(a3)
            put(a0, v1)
            put(a2, v3)
        elif name == "GETK":
            obj = rd(a2)
            put(a0, Member(obj, lit(a1), lit(a1).value not in self.live_names(pc)))
        elif name == "GET":
            key, obj = rd(a2), rd(a1)
            put(a0, Member(obj, key, False))
        elif name in ("PREPCALLK", "PREPCALL"):
            key = lit(a1) if name == "PREPCALLK" else rd(a1)
            obj = rd(a2)
            bare = isinstance(key, Const) and key.value not in self.live_names(pc)
            this = self.new(ThisArg(obj))
            put(a0, Member(obj, key, bare))
            put(a3, this)
        elif name in ("CALL", "TAILCALL"):
            fn = rd(a1)
            this = rd(a2) if a3 > 0 else Const("null")
            args = [rd(r) for r in range(a2 + 1, a2 + a3)]
            e = self.new(Call(fn, this, args))
            if a0 == NOREG:
                self.emit(st, out, pc, ("expr", e))
            else:
                self.write(st, a0, e, pc, out)
        elif name in ("SET", "NEWSLOT"):
            val, key, obj = rd(a3), rd(a2), rd(a1)
            lhs = Member(obj, key, isinstance(key, Const) and key.value not in self.live_names(pc))
            if name == "NEWSLOT" and isinstance(val, Closure) and isinstance(obj, Name) and obj.name == "this" \
                    and isinstance(key, Const) and key.value == self.closure_name(val.index) and is_ident(key.value):
                self.emit(st, out, pc, ("funcdecl", val.index))
            else:
                self.emit(st, out, pc, ("assign", lhs, "=" if name == "SET" else "<-", val))
            if a0 != a3:
                self.write(st, a0, self.new(lhs), pc, out)
        elif name == "NEWSLOTA":
            tbl = st.regs.get(a1)
            if isinstance(tbl, Table) and self.local_at(a1, pc) is None and not (a0 & 2):
                val, key = rd(a3), rd(a2)
                tbl.items.append((key, val))
            else:
                raise Unstructured("NEWSLOTA on a non-literal")
        elif name == "NEWTABLE":
            put(a0, Table())
        elif name == "NEWARRAY":
            put(a0, Array())
        elif name == "APPENDARRAY":
            arr = st.regs.get(a0)
            if not isinstance(arr, Array):
                raise Unstructured("APPENDARRAY on a non-literal")
            arr.items.append(lit(a1) if a3 else rd(a1))
        elif name in ("EQ", "NE"):
            b = lit(a1) if a3 else rd(a1)
            a = rd(a2)
            put(a0, Bin("==" if name == "EQ" else "!=", a, b))
        elif name == "ARITH":
            b, a = rd(a1), rd(a2)
            put(a0, Bin(chr(a3), a, b))
        elif name == "BITW":
            if a3 not in BW_OPS:
                raise Unstructured("unknown bitwise op")
            b, a = rd(a1), rd(a2)
            put(a0, Bin(BW_OPS[a3], a, b))
        elif name == "CMP":
            if a3 not in CMP_OPS:
                raise Unstructured("unknown compare op")
            b, a = rd(a1), rd(a2)
            put(a0, Bin(CMP_OPS[a3], a, b))
        elif name in ("NEG", "NOT", "BWNOT", "TYPEOF", "CLONE"):
            op = {"NEG": "-", "NOT": "!", "BWNOT": "~", "TYPEOF": "typeof", "CLONE": "clone"}[name]
            v = rd(a1)
            if name == "NEG" and isinstance(v, Const) and v.kind == OT_INTEGER:
                put(a0, Const(f"-{v.text}" if not v.text.startswith("-") else f"-({v.text})", -v.value, OT_INTEGER))
            else:
                put(a0, Unary(op, v))
        elif name == "VARGC":
            put(a0, Vargc())
        elif name == "GETVARGV":
            put(a0, Vargv(rd(a1)))
        elif name == "CLOSURE":
            if not 0 <= a1 < len(self.f.functions):
                raise Unstructured("bad closure index")
            put(a0, Closure(a1))
        elif name == "DELEGATE":
            tbl, parent = rd(a1), rd(a2)
            put(a0, Delegate(parent, tbl))
        elif name == "EXISTS":
            obj, key = rd(a1), rd(a2)
            put(a0, Bin("in", key, obj))
        elif name == "INSTANCEOF":
            a, b = rd(a1), rd(a2)
            put(a0, Bin("instanceof", a, b))
        elif name == "DELETE":
            obj, key = rd(a1), rd(a2)
            put(a0, Unary("delete", Member(obj, key, False), se=True))
        elif name in ("INCL", "PINCL"):
            k = self.local_at(a1, pc)
            if k is None:
                raise Unstructured("increment of a non-local")
            delta = struct.unpack("b", bytes([a3 & 0xFF]))[0]
            var = Name(self.locals[k][0])
            if delta in (1, -1):
                op = "++" if delta == 1 else "--"
                e = Unary(op, var, se=True) if name == "INCL" else Postfix(op, var)
            elif name == "INCL":
                e = Bin("+=", var, Const(str(delta)), se=True)
            else:
                raise Unstructured("post-increment by a step other than 1")
            self.write(st, a0, self.new(e), pc, out)
        elif name == "COMPARITHL":
            k = self.local_at(a1, pc)
            if k is None:
                raise Unstructured("compound assignment to a non-local")
            val = rd(a2)
            self.emit(st, out, pc, ("assign", Name(self.locals[k][0]), chr(a3) + "=", val))
            self.write(st, a0, self.new(Name(self.locals[k][0])), pc, out)
        else:
            raise Unstructured(f"unsupported opcode {name}")

    # ---- cosmetics -----------------------------------------------------------
    def prettify(self, stmts):
        """Turn `x = init; while (c) { ...; x++; }` into a for loop (only when no continue)."""
        res = []
        for s in stmts:
            s = self.prettify_inner(s)
            if s[0] == "while" and res and s[2] and s[1] is not None:
                prev, last = res[-1], s[2][-1]
                var = prev[1] if prev[0] == "local" else (prev[1].name if prev[0] == "assign" and isinstance(prev[1], Name) and prev[2] == "=" else None)
                inc_var = None
                if last[0] == "expr" and isinstance(last[1], (Unary, Postfix)) and last[1].op in ("++", "--") and isinstance(last[1].e, Name):
                    inc_var = last[1].e.name
                elif last[0] == "assign" and isinstance(last[1], Name) and last[2] in ("+=", "-="):
                    inc_var = last[1].name
                if var and var == inc_var and not has_continue(s[2]):
                    res[-1] = ("for", prev, s[1], last, s[2][:-1])
                    continue
            res.append(s)
        return res

    def prettify_inner(self, s):
        k = s[0]
        if k == "if":
            return ("if", s[1], self.prettify(s[2]), self.prettify(s[3]))
        if k == "while":
            return ("while", s[1], self.prettify(s[2]))
        if k == "for":
            return ("for", s[1], s[2], s[3], self.prettify(s[4]))
        if k == "switch":
            return ("switch", s[1], [(v, self.prettify(b)) for v, b in s[2]])
        return s

    # ---- rendering -----------------------------------------------------------
    def params(self):
        ps = [p.value for p in self.f.parameters[1:]]
        if self.f.varparams:
            ps.append("...")
        return ", ".join(ps)

    def render_closure(self, idx, ind, name):
        c = self.child(idx)
        head = f"function {name}({c.params()})" if name else f"function ({c.params()})"
        body = c.render_block(c.stmts, ind + IND)
        return head + " {\n" + body + ind + "}" if body else head + " {}"

    def render_block(self, stmts, ind) -> str:
        return "".join(self.render_stmt(s, ind) for s in stmts)

    def render_stmt(self, s, ind) -> str:
        k = s[0]
        if k == "expr":
            return f"{ind}{s[1].r(self, ind)};\n"
        if k == "local":
            return f"{ind}local {s[1]};\n" if s[2] is None else f"{ind}local {s[1]} = {s[2].r(self, ind)};\n"
        if k == "assign":
            return f"{ind}{s[1].r(self, ind)} {s[2]} {s[3].r(self, ind)};\n"
        if k == "funcdecl":
            return f"{ind}{self.render_closure(s[1], ind, self.closure_name(s[1]))}\n"
        if k == "return":
            return f"{ind}return;\n" if s[1] is None else f"{ind}return {s[1].r(self, ind)};\n"
        if k in ("break", "continue"):
            return f"{ind}{k};\n"
        if k == "comment":
            return f"{ind}// {s[1]}\n"
        if k == "if":
            text = f"{ind}if ({s[1].r(self, ind)}) {{\n{self.render_block(s[2], ind + IND)}{ind}}}"
            els = s[3]
            while els:
                if len(els) == 1 and els[0][0] == "if":
                    e = els[0]
                    text += f" else if ({e[1].r(self, ind)}) {{\n{self.render_block(e[2], ind + IND)}{ind}}}"
                    els = e[3]
                else:
                    text += f" else {{\n{self.render_block(els, ind + IND)}{ind}}}"
                    break
            return text + "\n"
        if k == "while":
            return f"{ind}while ({s[1].r(self, ind)}) {{\n{self.render_block(s[2], ind + IND)}{ind}}}\n"
        if k == "for":
            init = self.render_stmt(s[1], "").strip().rstrip(";") if s[1] else ""
            cond = s[2].r(self, ind) if s[2] is not None else ""
            incr = self.render_stmt(s[3], "").strip().rstrip(";")
            return f"{ind}for ({init}; {cond}; {incr}) {{\n{self.render_block(s[4], ind + IND)}{ind}}}\n"
        if k == "switch":
            text = f"{ind}switch ({s[1].r(self, ind)}) {{\n"
            for v, body in s[2]:
                label = "default:" if v is None else f"case {v.r(self, ind)}:"
                text += f"{ind}{IND}{label}\n{self.render_block(body, ind + IND * 2)}"
            return text + f"{ind}}}\n"
        if k == "asm":
            return self.render_asm(s[1], s[2], s[3], ind)
        raise ValueError(k)

    def render_asm(self, lo, hi, reason, ind) -> str:
        lines = [f"{ind}// ---- ASM FALLBACK pc {lo}..{hi - 1} ({reason}) ----"]
        for k in range(lo, hi):
            i = self.ins[k]
            note = ""
            if k in self.target:
                note = f"  -> pc {self.target[k]}"
            elif i.op in (OP["LOAD"], OP["PREPCALLK"], OP["GETK"]) and 0 <= i.arg1 < len(self.lits):
                note = f"  ; {fmt_obj(self.lits[i.arg1])}"
            elif i.op == OP["CLOSURE"] and 0 <= i.arg1 < len(self.f.functions):
                note = f"  ; closure {self.closure_name(i.arg1)}"
            lines.append(f"{ind}// [{k:4d}] {i!r}{note}")
        lines.append(f"{ind}// ---- END ASM ----")
        for k in range(lo, hi):
            i = self.ins[k]
            if i.op == OP["CLOSURE"] and 0 <= i.arg1 < len(self.f.functions):
                lines.append(f"{ind}// closure {i.arg1} used above:")
                lines.append(ind + "/* " + self.render_closure(i.arg1, ind, self.closure_name(i.arg1)).replace("*/", "* /") + " */")
        return "\n".join(lines) + "\n"


def has_continue(stmts) -> bool:
    for s in stmts:
        if s[0] == "continue":
            return True
        if s[0] == "if" and (has_continue(s[2]) or has_continue(s[3])):
            return True
        if s[0] == "switch" and any(has_continue(b) for _, b in s[2]):
            return True
    return False


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def _walk_exprs(e, acc):
    if isinstance(e, E):
        if isinstance(e, Reg) and not e.defined:
            acc["unresolved_regs"] += 1
        if isinstance(e, Reg) and e.defined:
            acc["materialised_regs"] += 1
        for kid in e.kids():
            _walk_exprs(kid, acc)


def _walk_stmts(d: FuncDecomp, stmts, acc, asm_pcs):
    for s in stmts:
        if s[0] == "asm":
            acc["fallback_blocks"] += 1
            asm_pcs.update(range(s[1], s[2]))
            continue
        for part in s[1:]:
            if isinstance(part, list):
                if part and isinstance(part[0], tuple) and len(part[0]) == 2 and not isinstance(part[0][0], str):
                    for v, body in part:
                        _walk_exprs(v, acc)
                        _walk_stmts(d, body, acc, asm_pcs)
                else:
                    _walk_stmts(d, part, acc, asm_pcs)
            elif isinstance(part, tuple):
                _walk_stmts(d, [part], acc, asm_pcs)
            else:
                _walk_exprs(part, acc)


def func_stats(d: FuncDecomp) -> dict:
    acc = Counter()
    asm_pcs: set = set()
    _walk_stmts(d, d.stmts, acc, asm_pcs)
    ops_total, ops_fallback = Counter(), Counter()
    for pc, i in enumerate(d.ins):
        n = OPS[i.op] if i.op < len(OPS) else str(i.op)
        ops_total[n] += 1
        if pc in asm_pcs:
            ops_fallback[n] += 1
    return {
        "name": d.f.name.value if d.f.name.type == OT_STRING else None,
        "instructions": d.n,
        "fallback_blocks": acc["fallback_blocks"],
        "fallback_instructions": len(asm_pcs),
        "unresolved_regs": acc["unresolved_regs"],
        "materialised_regs": acc["materialised_regs"],
        "ops_total": ops_total,
        "ops_fallback": ops_fallback,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def decompile_func(f: sqbin.Func) -> tuple[str, list[dict]]:
    """Decompile a parsed script's root function; returns (text, per-function stats)."""
    d = FuncDecomp(f)
    d.decompile()
    text = d.render_block(d.stmts, "")
    stats = []

    def collect(x: FuncDecomp):
        stats.append(func_stats(x))
        for idx in range(len(x.f.functions)):
            collect(x.child(idx))

    collect(d)
    return text, stats


def header(source: str) -> str:
    return (
        f"// {source} - decompiled by tools/squirrel_decompile.py\n"
        "// READ-ONLY pseudo-source reconstructed from Squirrel 2.2 bytecode. It is NOT compiled back:\n"
        "// edit script.nut (the assembly listing) to change the game.\n"
        "// $rN = VM register the decompiler could not name; 'ASM FALLBACK' blocks hold raw bytecode\n"
        "// for regions it could not structure (pc numbers match script.nut).\n\n"
    )


def decompile_bytes(data: bytes, source: str = "script.cnut") -> tuple[str, list[dict]]:
    text, stats = decompile_func(sqbin.parse(data))
    return header(source) + text, stats


def _work(src: str) -> dict:
    src_p = Path(src)
    rel = src_p.relative_to(DATA_DIR)
    out = (ASSETS_DIR / "scripts" / rel).with_suffix("").with_suffix(SUFFIX)
    try:
        text, stats = decompile_bytes(src_p.read_bytes(), rel.as_posix())
    except Exception as exc:  # pragma: no cover - reported in the audit
        return {"source": rel.as_posix(), "error": f"{type(exc).__name__}: {exc}"}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    return {"source": rel.as_posix(), "output": out.relative_to(PROJECT_ROOT).as_posix(), "functions": stats}


def decompile_all(workers: int = 8) -> dict:
    srcs = sorted(str(p) for p in (DATA_DIR / "packs").rglob("*.cnut"))
    print(f"Decompiling {len(srcs)} scripts...")
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_work, srcs, chunksize=8))
    return write_report(rows)


def write_report(rows: list[dict]) -> dict:
    ops_total, ops_fallback = Counter(), Counter()
    funcs = full = with_fb = with_unres = 0
    insns = fb_insns = fb_blocks = unres = mat = 0
    scripts = []
    errors = [r for r in rows if "error" in r]
    for r in rows:
        if "error" in r:
            continue
        s_fb = s_unres = 0
        for fs in r["functions"]:
            funcs += 1
            insns += fs["instructions"]
            fb_insns += fs["fallback_instructions"]
            fb_blocks += fs["fallback_blocks"]
            unres += fs["unresolved_regs"]
            mat += fs["materialised_regs"]
            ops_total.update(fs["ops_total"])
            ops_fallback.update(fs["ops_fallback"])
            if fs["fallback_blocks"]:
                with_fb += 1
            if fs["unresolved_regs"]:
                with_unres += 1
            if not fs["fallback_blocks"] and not fs["unresolved_regs"]:
                full += 1
            s_fb += fs["fallback_blocks"]
            s_unres += fs["unresolved_regs"]
        scripts.append({
            "source": r["source"], "output": r["output"], "functions": len(r["functions"]),
            "fallback_blocks": s_fb, "unresolved_regs": s_unres,
            "fallback_functions": [fs["name"] for fs in r["functions"] if fs["fallback_blocks"]],
        })
    report = {
        "tool": "tools/squirrel_decompile.py",
        "scripts": len(rows),
        "scripts_ok": len(rows) - len(errors),
        "errors": errors,
        "functions": funcs,
        "functions_fully_structured": full,
        "functions_with_fallback": with_fb,
        "functions_with_unresolved_regs": with_unres,
        "instructions": insns,
        "fallback_instructions": fb_insns,
        "fallback_blocks": fb_blocks,
        "unresolved_register_reads": unres,
        "materialised_registers": mat,
        "per_opcode": {
            op: {"total": ops_total[op], "fallback": ops_fallback[op],
                 "structured_pct": round(100 * (1 - ops_fallback[op] / ops_total[op]), 3)}
            for op in sorted(ops_total, key=lambda o: -ops_total[o])
        },
        "per_script": scripts,
    }
    AUDIT_DIR.mkdir(exist_ok=True)
    (AUDIT_DIR / "SCRIPT_DECOMPILE.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (AUDIT_DIR / "SCRIPT_DECOMPILE.md").write_text(report_markdown(report), encoding="utf-8")
    print(f"{report['scripts_ok']}/{report['scripts']} scripts, {full}/{funcs} functions fully structured, "
          f"{fb_blocks} fallback blocks ({fb_insns}/{insns} instructions), {unres} unresolved register reads")
    print("  -> audit/SCRIPT_DECOMPILE.json, audit/SCRIPT_DECOMPILE.md")
    return report


def report_markdown(rep: dict) -> str:
    pct = lambda a, b: f"{100 * a / max(b, 1):.2f}%"  # noqa: E731
    lines = [
        "# Squirrel script decompilation coverage",
        "",
        "Generated by `python tools/squirrel_decompile.py --all`. Output: "
        "`game_assets/scripts/packs/script/<name>/script.decompiled.nut` (read-only pseudo-source).",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Scripts decompiled without exception | {rep['scripts_ok']} / {rep['scripts']} |",
        f"| Functions fully structured (no fallback, no `$rN`) | {rep['functions_fully_structured']} / {rep['functions']} ({pct(rep['functions_fully_structured'], rep['functions'])}) |",
        f"| Functions with an ASM fallback block | {rep['functions_with_fallback']} |",
        f"| Functions with unresolved `$rN` reads | {rep['functions_with_unresolved_regs']} |",
        f"| ASM fallback blocks | {rep['fallback_blocks']} |",
        f"| Instructions inside fallback blocks | {rep['fallback_instructions']} / {rep['instructions']} ({pct(rep['fallback_instructions'], rep['instructions'])}) |",
        f"| Unresolved register reads (`$rN` with no definition) | {rep['unresolved_register_reads']} |",
        f"| Materialised temporaries (`$rN = ...`) | {rep['materialised_registers']} |",
        "",
        "## Per opcode",
        "",
        "| Opcode | Total | In fallback | Structured |",
        "|---|---:|---:|---:|",
    ]
    for op, v in rep["per_opcode"].items():
        lines.append(f"| {op} | {v['total']:,} | {v['fallback']:,} | {v['structured_pct']}% |")
    fb = [s for s in rep["per_script"] if s["fallback_blocks"] or s["unresolved_regs"]]
    lines += ["", f"## Scripts with fallback blocks or unresolved registers ({len(fb)})", ""]
    if fb:
        lines += ["| Script | Fallback blocks | Unresolved regs | Functions with fallback |", "|---|---:|---:|---|"]
        for s in fb:
            lines.append(f"| {s['source']} | {s['fallback_blocks']} | {s['unresolved_regs']} | {', '.join(map(str, s['fallback_functions'])) or '-'} |")
    else:
        lines.append("None.")
    if rep["errors"]:
        lines += ["", "## Errors", ""] + [f"- {e['source']}: {e['error']}" for e in rep["errors"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Decompile DQXI Squirrel (.cnut) scripts to read-only pseudo-source")
    ap.add_argument("cnut", nargs="?", type=Path, help="single .cnut file to decompile")
    ap.add_argument("-o", "--output", type=Path, help="output file (default: stdout)")
    ap.add_argument("--all", action="store_true", help="decompile every game_data/packs/**/*.cnut + write audit report")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(argv)
    if args.all:
        rep = decompile_all(args.workers)
        return 0 if not rep["errors"] else 1
    if not args.cnut:
        ap.print_help()
        return 2
    text, _ = decompile_bytes(args.cnut.read_bytes(), args.cnut.name)
    if args.output:
        args.output.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
