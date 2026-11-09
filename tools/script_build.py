#!/usr/bin/env python3
"""tools/script_build.py - edit and rebuild Dragon Quest XI Squirrel scripts.

DQXI stores one compiled Squirrel script (``.cnut``) in each
``romfs/script/<area>.pack``.  There is no Squirrel compiler in ``third_party/``
and the game uses the **Squirrel 2.2 bytecode format** (``ARITH``/``CMP`` carry
an operator byte, ``JNZ``/``NEWSLOTA``/``vargc`` exist), so the reference
Squirrel 3.2 sources under ``../3DS_Translate/_emutest`` cannot
produce this format.  This tool therefore ships its own small compiler for the
subset the decompiler emits, plus the exact assembler in ``tools/sqbin.py``.

Two editing levels, both built back to a ``.cnut``:

``source``
    ``script.decompiled.nut`` - the readable pseudo-source written by
    ``tools/squirrel_decompile.py``.  It is parsed into an AST and compiled.
    Functions whose AST is unchanged are copied byte-for-byte from the original
    script, so saving an untouched file is byte-identical; a one-function edit
    only recompiles that function.
``asm``
    ``script.nut`` - the annotated disassembly.  Assembled by ``sqbin``; this is
    the bit-exact path and works for every script (769/769 at the time of
    writing).

Commands
--------
    python tools/script_build.py compile SRC --area a_010 [--tier auto] [-o OUT.cnut]
    python tools/script_build.py pack    SRC --area a_010 [--mod mod] [--json]
    python tools/script_build.py verify  [--limit N] [--no-reuse-check]
    python tools/script_build.py index   [--out game_assets/scripts/script_index.json]

``compile``/``pack`` take ``--area`` (the pack name, e.g. ``a_010``).  ``pack``
rebuilds ``game_data/romfs/script/<area>.pack`` with the new ``script.cnut`` and
writes it under ``mod/romfs`` - the same LayeredFS path the other editors use,
so ``run_export.bat`` turns it into something a real 3DS boots.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import sqbin  # noqa: E402
from tools.sqbin import OP, OPS, OT_BOOL, OT_FLOAT, OT_INTEGER, OT_NULL, OT_STRING, Obj  # noqa: E402

SCRIPTS_DIR = PROJECT_ROOT / "game_assets" / "scripts"
CNUT_DIR = PROJECT_ROOT / "game_data" / "packs" / "script"
ROMFS_SCRIPT_DIR = PROJECT_ROOT / "game_data" / "romfs" / "script"
DEFAULT_INDEX = SCRIPTS_DIR / "script_index.json"
MAX_STACK = 0xFF  # MAX_FUNC_STACKSIZE from sqopcodes.h; the VM asserts on more


# ---------------------------------------------------------------------------
# errors
# ---------------------------------------------------------------------------

class BuildError(Exception):
    """A source/assembly problem that is reported to the editor as a list."""

    def __init__(self, message: str, line: int | None = None):
        self.message = message
        self.line = line
        super().__init__(f"line {line}: {message}" if line else message)

    def text(self) -> str:
        return f"line {self.line}: {self.message}" if self.line else self.message


# ---------------------------------------------------------------------------
# lexer
# ---------------------------------------------------------------------------

KEYWORDS = {
    "while", "do", "if", "else", "break", "continue", "return", "null", "function", "local",
    "for", "foreach", "in", "typeof", "delegate", "clone", "switch", "case", "default", "this",
    "parent", "class", "extends", "constructor", "instanceof", "yield", "try", "catch", "throw",
    "resume", "true", "false", "static", "vargc", "vargv", "enum", "const",
}

# longest first so `>>>=` never lexes as `>>` + `>=`
OPERATORS = [
    ">>>=", "<<=", ">>=", "...", ">>>", "==", "!=", "<=", ">=", "&&", "||", "++", "--",
    "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<-", "::", "<<", ">>",
    "{", "}", "(", ")", "[", "]", ";", ",", ".", ":", "?", "~", "!", "+", "-", "*", "/",
    "%", "&", "|", "^", "<", ">", "=",
]
_OPERATOR_ORDER = sorted(OPERATORS, key=len, reverse=True)


@dataclass
class Tok:
    kind: str          # id | num | str | op | eof
    value: object
    line: int
    col: int
    pos: int           # byte/char offset in the text, for editor jumps


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.i = 0
        self.line = 1
        self.col = 1
        self.n = len(text)

    def _advance(self, count: int = 1) -> None:
        for _ in range(count):
            if self.i < self.n and self.text[self.i] == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
            self.i += 1

    def tokens(self) -> list[Tok]:
        out: list[Tok] = []
        while self.i < self.n:
            c = self.text[self.i]
            if c in " \t\r\n":
                self._advance()
                continue
            if c == "/" and self.i + 1 < self.n and self.text[self.i + 1] == "/":
                while self.i < self.n and self.text[self.i] != "\n":
                    self._advance()
                continue
            if c == "/" and self.i + 1 < self.n and self.text[self.i + 1] == "*":
                start = self.line
                self._advance(2)
                while self.i + 1 < self.n and not (self.text[self.i] == "*" and self.text[self.i + 1] == "/"):
                    self._advance()
                if self.i + 1 >= self.n:
                    raise BuildError("unterminated block comment", start)
                self._advance(2)
                continue
            line, col, pos = self.line, self.col, self.i
            if c.isalpha() or c == "_" or (c == "$" and self.i + 1 < self.n and self.text[self.i + 1].isdigit()):
                j = self.i + 1
                while j < self.n and (self.text[j].isalnum() or self.text[j] == "_"):
                    j += 1
                word = self.text[self.i:j]
                self._advance(j - self.i)
                out.append(Tok("kw" if word in KEYWORDS else "id", word, line, col, pos))
                continue
            if c.isdigit():
                j = self.i
                is_float = False
                if self.text.startswith(("0x", "0X"), j):
                    j += 2
                    while j < self.n and (self.text[j].isdigit() or self.text[j].lower() in "abcdef"):
                        j += 1
                    value: object = int(self.text[self.i:j], 16)
                else:
                    while j < self.n and (self.text[j].isdigit() or self.text[j] == "."):
                        if self.text[j] == ".":
                            is_float = True
                        j += 1
                    if j < self.n and self.text[j] in "eE":
                        is_float = True
                        j += 1
                        if j < self.n and self.text[j] in "+-":
                            j += 1
                        while j < self.n and self.text[j].isdigit():
                            j += 1
                    raw = self.text[self.i:j]
                    value = float(raw) if is_float else int(raw)
                self._advance(j - self.i)
                out.append(Tok("num", value, line, col, pos))
                continue
            if c == '"':
                j = self.i + 1
                buf: list[str] = []
                while j < self.n and self.text[j] != '"':
                    if self.text[j] == "\\" and j + 1 < self.n:
                        esc = self.text[j + 1]
                        simple = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "a": "\a", "b": "\b",
                                  "v": "\v", "f": "\f", "\\": "\\", '"': '"', "'": "'"}
                        if esc == "x" and j + 3 < self.n:
                            try:
                                buf.append(chr(int(self.text[j + 2:j + 4], 16)))
                                j += 4
                                continue
                            except ValueError:
                                pass
                        buf.append(simple.get(esc, esc))
                        j += 2
                        continue
                    if self.text[j] == "\n":
                        raise BuildError("unterminated string literal", line)
                    buf.append(self.text[j])
                    j += 1
                if j >= self.n:
                    raise BuildError("unterminated string literal", line)
                self._advance(j + 1 - self.i)
                out.append(Tok("str", "".join(buf), line, col, pos))
                continue
            for op in _OPERATOR_ORDER:
                if self.text.startswith(op, self.i):
                    self._advance(len(op))
                    out.append(Tok("op", op, line, col, pos))
                    break
            else:
                raise BuildError(f"unexpected character {c!r}", line)
        out.append(Tok("eof", None, self.line, self.col, self.i))
        return out


# ---------------------------------------------------------------------------
# AST
#
# `key()` is the structural fingerprint used for incremental reuse: two function
# nodes with the same key compile to the same bytecode, so an unchanged one can
# be copied from the original script instead of recompiled.
# ---------------------------------------------------------------------------

class Node:
    line: int = 0

    def key(self):  # pragma: no cover - overridden
        raise NotImplementedError


@dataclass
class EConst(Node):
    value: object
    type: int
    line: int = 0

    def key(self):
        if self.type == OT_FLOAT:
            return ("c", self.type, struct.pack("<f", float(self.value)))
        return ("c", self.type, self.value)


@dataclass
class EName(Node):
    name: str
    line: int = 0

    def key(self):
        return ("n", self.name)


@dataclass
class ERoot(Node):
    line: int = 0

    def key(self):
        return ("root",)


@dataclass
class EMember(Node):
    obj: Node
    key_expr: Node
    computed: bool
    line: int = 0

    def key(self):
        return ("m", self.obj.key(), self.key_expr.key(), self.computed)


@dataclass
class ECall(Node):
    callee: Node
    args: list[Node]
    line: int = 0

    def key(self):
        return ("call", self.callee.key(), tuple(a.key() for a in self.args))


@dataclass
class EUnary(Node):
    op: str
    expr: Node
    line: int = 0

    def key(self):
        return ("u", self.op, self.expr.key())


@dataclass
class EPostfix(Node):
    op: str
    expr: Node
    line: int = 0

    def key(self):
        return ("p", self.op, self.expr.key())


@dataclass
class EBin(Node):
    op: str
    left: Node
    right: Node
    line: int = 0

    def key(self):
        return ("b", self.op, self.left.key(), self.right.key())


@dataclass
class ETern(Node):
    cond: Node
    then: Node
    otherwise: Node
    line: int = 0

    def key(self):
        return ("?", self.cond.key(), self.then.key(), self.otherwise.key())


@dataclass
class EAssign(Node):
    target: Node
    op: str
    value: Node
    line: int = 0

    def key(self):
        return ("=", self.target.key(), self.op, self.value.key())


@dataclass
class ETable(Node):
    entries: list[tuple[Node | None, Node]]
    line: int = 0

    def key(self):
        return ("t", tuple((k.key() if k else None, v.key()) for k, v in self.entries))


@dataclass
class EArray(Node):
    items: list[Node]
    line: int = 0

    def key(self):
        return ("a", tuple(i.key() for i in self.items))


@dataclass
class EClosure(Node):
    func: "FuncNode"
    line: int = 0

    def key(self):
        return ("f", self.func.key())


@dataclass
class EDelegate(Node):
    parent: Node
    table: Node
    line: int = 0

    def key(self):
        return ("d", self.parent.key(), self.table.key())


@dataclass
class EVargc(Node):
    line: int = 0

    def key(self):
        return ("vargc",)


@dataclass
class EVargv(Node):
    index: Node
    line: int = 0

    def key(self):
        return ("vargv", self.index.key())


@dataclass
class FuncNode(Node):
    name: str | None
    params: list[str]
    varparams: bool
    body: list["Stmt"]
    line: int = 0

    def key(self):
        return ("fn", self.name, tuple(self.params), self.varparams, tuple(s.key() for s in self.body))


class Stmt:
    """Base for statements (a plain class: `line` stays a normal default field)."""

    line: int = 0

    def key(self):  # pragma: no cover - overridden
        raise NotImplementedError


@dataclass
class ExprStmt(Stmt):
    expr: Node
    line: int = 0

    def key(self):
        return ("expr", self.expr.key())


@dataclass
class LocalStmt(Stmt):
    name: str
    init: Node | None
    line: int = 0

    def key(self):
        return ("local", self.name, self.init.key() if self.init else None)


@dataclass
class AssignStmt(Stmt):
    assign: EAssign
    line: int = 0

    def key(self):
        return ("assignstmt", self.assign.key())


@dataclass
class IfStmt(Stmt):
    cond: Node
    then: list[Stmt]
    otherwise: list[Stmt]
    line: int = 0

    def key(self):
        return ("if", self.cond.key(), tuple(s.key() for s in self.then),
                tuple(s.key() for s in self.otherwise))


@dataclass
class WhileStmt(Stmt):
    cond: Node | None
    body: list[Stmt]
    line: int = 0

    def key(self):
        return ("while", self.cond.key() if self.cond else None, tuple(s.key() for s in self.body))


@dataclass
class ForStmt(Stmt):
    init: Stmt | None
    cond: Node | None
    incr: Stmt | None
    body: list[Stmt]
    line: int = 0

    def key(self):
        return ("for", self.init.key() if self.init else None, self.cond.key() if self.cond else None,
                self.incr.key() if self.incr else None, tuple(s.key() for s in self.body))


@dataclass
class SwitchStmt(Stmt):
    subject: Node
    arms: list[tuple[Node | None, list[Stmt]]]
    line: int = 0

    def key(self):
        return ("switch", self.subject.key(),
                tuple((v.key() if v else None, tuple(s.key() for s in body)) for v, body in self.arms))


@dataclass
class BreakStmt(Stmt):
    line: int = 0

    def key(self):
        return ("break",)


@dataclass
class ContinueStmt(Stmt):
    line: int = 0

    def key(self):
        return ("continue",)


@dataclass
class ReturnStmt(Stmt):
    value: Node | None
    line: int = 0

    def key(self):
        return ("return", self.value.key() if self.value else None)


@dataclass
class FuncDeclStmt(Stmt):
    func: FuncNode
    line: int = 0

    def key(self):
        return ("funcdecl", self.func.key())


@dataclass
class DelegateStmt(Stmt):
    expr: EDelegate
    line: int = 0

    def key(self):
        return ("delegatestmt", self.expr.key())


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------

ASSIGN_OPS = {"=", "<-", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", ">>>="}

_BIN_PREC = {
    "||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6,
    "<": 7, "<=": 7, ">": 7, ">=": 7, "in": 7, "instanceof": 7,
    "<<": 8, ">>": 8, ">>>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10,
}


class Parser:
    def __init__(self, text: str):
        self.toks = Lexer(text).tokens()
        self.i = 0

    # -- token helpers ------------------------------------------------------
    @property
    def tok(self) -> Tok:
        return self.toks[self.i]

    def peek(self, n: int = 1) -> Tok:
        return self.toks[min(self.i + n, len(self.toks) - 1)]

    def at(self, value: str) -> bool:
        return self.tok.value == value and self.tok.kind in ("op", "kw")

    def accept(self, value: str) -> bool:
        if self.at(value):
            self.i += 1
            return True
        return False

    def expect(self, value: str) -> Tok:
        if not self.at(value):
            raise BuildError(f"expected {value!r}, found {self.tok.value!r}", self.tok.line)
        t = self.tok
        self.i += 1
        return t

    def expect_id(self) -> Tok:
        if self.tok.kind != "id":
            raise BuildError(f"expected an identifier, found {self.tok.value!r}", self.tok.line)
        t = self.tok
        self.i += 1
        return t

    def optional_semi(self) -> None:
        self.accept(";")

    @staticmethod
    def as_stmt(expr: Node, line: int) -> Stmt:
        """Wrap an expression used in a for-init/increment as a statement."""
        if isinstance(expr, EAssign):
            return AssignStmt(expr, line)
        return ExprStmt(expr, line)

    # -- entry points -------------------------------------------------------
    def parse_module(self) -> FuncNode:
        body = self.parse_stmts(stop=None)
        if self.tok.kind != "eof":
            raise BuildError(f"unexpected {self.tok.value!r} after the script body", self.tok.line)
        return FuncNode(None, [], False, body, 1)

    def parse_block(self) -> list[Stmt]:
        self.expect("{")
        body = self.parse_stmts(stop="}")
        self.expect("}")
        return body

    def parse_stmts(self, stop: str | None) -> list[Stmt]:
        out: list[Stmt] = []
        while True:
            if stop is not None and self.at(stop):
                break
            if self.tok.kind == "eof":
                if stop is not None:
                    raise BuildError(f"expected {stop!r} before end of file", self.tok.line)
                break
            out.append(self.parse_stmt())
        return out

    def parse_stmt(self) -> Stmt:
        t = self.tok
        line = t.line
        if self.accept("{"):
            self.i -= 1
            # a bare block (the decompiler keeps braces on control bodies)
            body = self.parse_block()
            return IfStmt(EConst(True, OT_BOOL, line), body, [], line)
        if self.at("if"):
            self.i += 1
            self.expect("(")
            cond = self.parse_expr()
            self.expect(")")
            then = self.parse_stmt_body()
            otherwise: list[Stmt] = []
            if self.accept("else"):
                if self.at("if"):
                    otherwise = [self.parse_stmt()]
                else:
                    otherwise = self.parse_stmt_body()
            return IfStmt(cond, then, otherwise, line)
        if self.at("while"):
            self.i += 1
            self.expect("(")
            cond = self.parse_expr()
            self.expect(")")
            return WhileStmt(cond, self.parse_stmt_body(), line)
        if self.at("for"):
            self.i += 1
            self.expect("(")
            init: Stmt | None = None
            if not self.at(";"):
                if self.at("local"):
                    init = self.parse_local(consume_semi=False)
                else:
                    init = self.as_stmt(self.parse_assignment_expr(), line)
            self.expect(";")
            cond = None if self.at(";") else self.parse_expr()
            self.expect(";")
            incr: Stmt | None = None
            if not self.at(")"):
                incr = self.as_stmt(self.parse_assignment_expr(), line)
            self.expect(")")
            return ForStmt(init, cond, incr, self.parse_stmt_body(), line)
        if self.at("switch"):
            self.i += 1
            self.expect("(")
            subject = self.parse_expr()
            self.expect(")")
            self.expect("{")
            arms: list[tuple[Node | None, list[Stmt]]] = []
            while not self.at("}") and self.tok.kind != "eof":
                if self.accept("case"):
                    value = self.parse_expr()
                    self.expect(":")
                elif self.accept("default"):
                    value = None
                    self.expect(":")
                else:
                    raise BuildError(f"expected case/default, found {self.tok.value!r}", self.tok.line)
                body: list[Stmt] = []
                while not self.at("case") and not self.at("default") and not self.at("}") \
                        and self.tok.kind != "eof":
                    body.append(self.parse_stmt())
                arms.append((value, body))
            self.expect("}")
            return SwitchStmt(subject, arms, line)
        if self.at("break"):
            self.i += 1
            self.optional_semi()
            return BreakStmt(line)
        if self.at("continue"):
            self.i += 1
            self.optional_semi()
            return ContinueStmt(line)
        if self.at("return"):
            self.i += 1
            value = None if self.at(";") or self.at("}") else self.parse_expr()
            self.optional_semi()
            return ReturnStmt(value, line)
        if self.at("local"):
            return self.parse_local(consume_semi=True)
        if self.at("function") and self.peek().kind in ("id", "kw") and self.peek(2).value == "(":
            return FuncDeclStmt(self.parse_function(require_name=False), line)
        if self.at("delegate"):
            expr = self.parse_expr()
            self.optional_semi()
            return DelegateStmt(expr, line)
        expr = self.parse_assignment_expr()
        if isinstance(expr, EAssign):
            self.optional_semi()
            return AssignStmt(expr, line)
        self.optional_semi()
        return ExprStmt(expr, line)

    def parse_stmt_body(self) -> list[Stmt]:
        if self.at("{"):
            return self.parse_block()
        return [self.parse_stmt()]

    def parse_local(self, consume_semi: bool) -> LocalStmt:
        line = self.expect("local").line
        name = self.expect_id().value
        init = None
        if self.accept("="):
            init = self.parse_expr()
        if consume_semi:
            self.optional_semi()
        return LocalStmt(name, init, line)

    # -- expressions --------------------------------------------------------
    def parse_expr(self) -> Node:
        return self.parse_assignment_expr()

    def parse_assignment_expr(self) -> Node:
        left = self.parse_ternary()
        if self.tok.value in ASSIGN_OPS and self.tok.kind == "op":
            op = self.tok.value
            line = self.tok.line
            self.i += 1
            right = self.parse_assignment_expr()
            if not isinstance(left, (EName, EMember)):
                raise BuildError("assignment target must be a name or a table slot", line)
            return EAssign(left, op, right, line)
        return left

    def parse_ternary(self) -> Node:
        cond = self.parse_binary(1)
        if self.accept("?"):
            then = self.parse_assignment_expr()
            self.expect(":")
            otherwise = self.parse_assignment_expr()
            return ETern(cond, then, otherwise, cond.line)
        return cond

    def parse_binary(self, min_prec: int) -> Node:
        left = self.parse_unary()
        while True:
            tok = self.tok
            op = tok.value
            if tok.kind not in ("op", "kw") or op not in _BIN_PREC:
                break
            prec = _BIN_PREC[op]
            if prec < min_prec:
                break
            self.i += 1
            right = self.parse_binary(prec + 1)
            left = EBin(op, left, right, tok.line)
        return left

    def parse_unary(self) -> Node:
        tok = self.tok
        if tok.value in ("!", "-", "+", "~", "typeof", "clone", "delete") and \
                (tok.kind == "op" or tok.kind == "kw"):
            self.i += 1
            expr = self.parse_unary()
            return EUnary(tok.value, expr, tok.line)
        if tok.value in ("++", "--") and tok.kind == "op":
            self.i += 1
            return EUnary(tok.value, self.parse_unary(), tok.line)
        if tok.value == "delegate" and tok.kind == "kw":
            self.i += 1
            parent = self.parse_ternary()
            self.expect(":")
            table = self.parse_ternary()
            return EDelegate(parent, table, tok.line)
        return self.parse_postfix()

    def parse_postfix(self) -> Node:
        expr = self.parse_primary()
        while True:
            if self.accept("."):
                key = self.expect_id()
                expr = EMember(expr, EConst(key.value, OT_STRING, key.line), False, key.line)
            elif self.accept("["):
                index = self.parse_expr()
                self.expect("]")
                expr = EMember(expr, index, True, expr.line)
            elif self.accept("("):
                args: list[Node] = []
                if not self.at(")"):
                    while True:
                        args.append(self.parse_expr())
                        if not self.accept(","):
                            break
                self.expect(")")
                expr = ECall(expr, args, expr.line)
            elif self.tok.value in ("++", "--") and self.tok.kind == "op":
                op = self.tok.value
                self.i += 1
                expr = EPostfix(op, expr, expr.line)
            else:
                break
        return expr

    def parse_primary(self) -> Node:
        tok = self.tok
        line = tok.line
        if tok.kind == "num":
            self.i += 1
            if isinstance(tok.value, float):
                return EConst(tok.value, OT_FLOAT, line)
            return EConst(tok.value, OT_INTEGER, line)
        if tok.kind == "str":
            self.i += 1
            return EConst(tok.value, OT_STRING, line)
        if tok.value == "true":
            self.i += 1
            return EConst(True, OT_BOOL, line)
        if tok.value == "false":
            self.i += 1
            return EConst(False, OT_BOOL, line)
        if tok.value == "null":
            self.i += 1
            return EConst(None, OT_NULL, line)
        if tok.value == "this":
            self.i += 1
            return EName("this", line)
        if tok.value == "vargc":
            self.i += 1
            return EVargc(line)
        if tok.value == "vargv":
            self.i += 1
            self.expect("[")
            index = self.parse_expr()
            self.expect("]")
            return EVargv(index, line)
        if tok.value == "::" and tok.kind == "op":
            self.i += 1
            if self.tok.kind == "id":
                key = self.expect_id()
                return EMember(ERoot(line), EConst(key.value, OT_STRING, key.line), False, line)
            return ERoot(line)
        if tok.value == "function":
            return EClosure(self.parse_function(require_name=False), line)
        if tok.value == "{" and tok.kind == "op":
            return self.parse_table()
        if tok.value == "[" and tok.kind == "op":
            return self.parse_array()
        if tok.value == "(":
            self.i += 1
            expr = self.parse_expr()
            self.expect(")")
            return expr
        if tok.kind == "id":
            self.i += 1
            return EName(tok.value, line)
        raise BuildError(f"unexpected {tok.value!r} in an expression", line)

    def parse_table(self) -> ETable:
        line = self.expect("{").line
        entries: list[tuple[Node | None, Node]] = []
        while not self.at("}") and self.tok.kind != "eof":
            if self.at("function"):
                func = self.parse_function(require_name=False)
                key = EConst(func.name, OT_STRING, func.line) if func.name else None
                entries.append((key, EClosure(func, func.line)))
            elif self.accept("["):
                key = self.parse_expr()
                self.expect("]")
                self.expect("=")
                entries.append((key, self.parse_expr()))
            else:
                key = self.expect_id()
                self.expect("=")
                entries.append((EConst(key.value, OT_STRING, key.line), self.parse_expr()))
            # The decompiler writes function entries without a comma after the
            # closing brace (Squirrel allows it); a comma is optional everywhere.
            self.accept(",")
        self.expect("}")
        return ETable(entries, line)

    def parse_array(self) -> EArray:
        line = self.expect("[").line
        items: list[Node] = []
        while not self.at("]") and self.tok.kind != "eof":
            items.append(self.parse_expr())
            if not self.accept(","):
                break
        self.expect("]")
        return EArray(items, line)

    def parse_function(self, require_name: bool) -> FuncNode:
        line = self.expect("function").line
        name = None
        if self.tok.kind in ("id", "kw") and self.peek().value == "(":
            name = self.tok.value
            self.i += 1
        elif require_name:
            raise BuildError("expected a function name", line)
        self.expect("(")
        params: list[str] = []
        varparams = False
        while not self.at(")"):
            if self.accept("..."):
                varparams = True
                break
            params.append(self.expect_id().value)
            if not self.accept(","):
                break
        self.expect(")")
        body = self.parse_block()
        return FuncNode(name, params, varparams, body, line)


def parse_source(text: str) -> FuncNode:
    return Parser(text).parse_module()


# ---------------------------------------------------------------------------
# closures in emission order
# ---------------------------------------------------------------------------

def _expr_closures(e: Node, out: list[FuncNode]) -> None:
    """Append closure expressions in the order the compiler will emit CLOSURE."""
    if isinstance(e, EClosure):
        out.append(e.func)
        return
    if isinstance(e, (EConst, EName, ERoot, EVargc)):
        return
    if isinstance(e, EMember):
        _expr_closures(e.obj, out)
        if e.computed:
            _expr_closures(e.key_expr, out)
        return
    if isinstance(e, ECall):
        _expr_closures(e.callee, out)
        for a in e.args:
            _expr_closures(a, out)
        return
    if isinstance(e, (EUnary, EPostfix)):
        _expr_closures(e.expr, out)
        return
    if isinstance(e, EBin):
        _expr_closures(e.left, out)
        _expr_closures(e.right, out)
        return
    if isinstance(e, ETern):
        _expr_closures(e.cond, out)
        _expr_closures(e.then, out)
        _expr_closures(e.otherwise, out)
        return
    if isinstance(e, EAssign):
        _expr_closures(e.target, out)
        _expr_closures(e.value, out)
        return
    if isinstance(e, ETable):
        for k, v in e.entries:
            if k is not None:
                _expr_closures(k, out)
            _expr_closures(v, out)
        return
    if isinstance(e, EArray):
        for item in e.items:
            _expr_closures(item, out)
        return
    if isinstance(e, EDelegate):
        _expr_closures(e.parent, out)
        _expr_closures(e.table, out)
        return
    if isinstance(e, EVargv):
        _expr_closures(e.index, out)
        return
    raise BuildError(f"unhandled node in closure walk: {type(e).__name__}", getattr(e, "line", 0))


def _stmt_closures(s: Stmt, out: list[FuncNode]) -> None:
    if isinstance(s, (ExprStmt,)):
        _expr_closures(s.expr, out)
    elif isinstance(s, LocalStmt):
        if s.init is not None:
            _expr_closures(s.init, out)
    elif isinstance(s, AssignStmt):
        _expr_closures(s.assign, out)
    elif isinstance(s, IfStmt):
        _expr_closures(s.cond, out)
        for x in s.then:
            _stmt_closures(x, out)
        for x in s.otherwise:
            _stmt_closures(x, out)
    elif isinstance(s, WhileStmt):
        if s.cond is not None:
            _expr_closures(s.cond, out)
        for x in s.body:
            _stmt_closures(x, out)
    elif isinstance(s, ForStmt):
        if s.init is not None:
            _stmt_closures(s.init, out)
        if s.cond is not None:
            _expr_closures(s.cond, out)
        if s.incr is not None:
            _stmt_closures(s.incr, out)
        for x in s.body:
            _stmt_closures(x, out)
    elif isinstance(s, SwitchStmt):
        _expr_closures(s.subject, out)
        for value, body in s.arms:
            if value is not None:
                _expr_closures(value, out)
            for x in body:
                _stmt_closures(x, out)
    elif isinstance(s, ReturnStmt):
        if s.value is not None:
            _expr_closures(s.value, out)
    elif isinstance(s, FuncDeclStmt):
        out.append(s.func)
    elif isinstance(s, DelegateStmt):
        _expr_closures(s.expr, out)
    elif isinstance(s, (BreakStmt, ContinueStmt)):
        return
    else:
        raise BuildError(f"unhandled statement in closure walk: {type(s).__name__}", getattr(s, "line", 0))


def direct_closures(func: FuncNode) -> list[FuncNode]:
    out: list[FuncNode] = []
    for s in func.body:
        _stmt_closures(s, out)
    return out


# ---------------------------------------------------------------------------
# code generator
# ---------------------------------------------------------------------------

CMP_CODE = {">": 0, ">=": 2, "<": 3, "<=": 4}
BW_CODE = {"&": 0, "|": 2, "^": 3, "<<": 4, ">>": 5, ">>>": 6}


class CodeGen:
    def __init__(self, func: FuncNode, children: list[sqbin.Func], name: str | None,
                 sourcename: Obj):
        self.func = func
        self.children = children
        self.name = name
        self.sourcename = sourcename
        self.params = ["this"] + list(func.params)
        self.nparams = len(self.params)
        self.varparams = 1 if func.varparams else 0
        self.ins: list[sqbin.Insn] = []
        self.lits: list[Obj] = []
        self.lit_map: dict[tuple, int] = {}
        self.locals: list[list] = [[p, i, 0, -1] for i, p in enumerate(self.params)]
        self.lineinfos: list[tuple[int, int]] = []
        self.top = self.nparams
        self.max_top = self.nparams
        self.local_top = self.nparams
        self.scopes: list[tuple[int, int]] = []
        self.breaks: list[list[int]] = []
        self.continues: list[tuple[list[int], int]] = []
        self.line = func.line or 1
        self._last_line = 0

    # -- low level ----------------------------------------------------------
    def emit(self, op: int, a0: int = 0, a1: int = 0, a2: int = 0, a3: int = 0) -> int:
        pc = len(self.ins)
        self.ins.append(sqbin.Insn(op, a0 & 0xFF, a1, a2 & 0xFF, a3 & 0xFF))
        if self.line != self._last_line:
            self.lineinfos.append((self.line, pc))
            self._last_line = self.line
        return pc

    def patch(self, pc: int, target: int | None = None) -> None:
        target = len(self.ins) if target is None else target
        self.ins[pc].arg1 = target - (pc + 1)

    def alloc(self, count: int = 1) -> int:
        base = self.top
        self.top += count
        if self.top > MAX_STACK:
            raise BuildError(f"function needs {self.top} VM registers; the Squirrel VM allows {MAX_STACK}",
                             self.line)
        self.max_top = max(self.max_top, self.top)
        return base

    def lit(self, obj: Obj) -> int:
        key = (obj.type, struct.pack("<f", float(obj.value)) if obj.type == OT_FLOAT else
               (obj.value if obj.type != OT_BOOL else bool(obj.value)))
        if key in self.lit_map:
            return self.lit_map[key]
        index = len(self.lits)
        self.lits.append(obj)
        self.lit_map[key] = index
        return index

    def string_lit(self, value: str) -> int:
        return self.lit(Obj(OT_STRING, value))

    # -- scopes and locals ---------------------------------------------------
    def push_scope(self) -> None:
        self.scopes.append((self.local_top, self.top))

    def pop_scope(self) -> None:
        saved_local, saved_top = self.scopes.pop()
        end = max(0, len(self.ins) - 1)
        function_scope = not self.scopes
        for info in self.locals:
            if info[3] == -1 and info[1] >= saved_local:
                # A local declared as the last statement of a block gets
                # start > end, exactly like Squirrel's compiler: the
                # decompiler then folds it back in at the block's closing
                # brace. Function-scope locals are closed after the implicit
                # RETURN instead, so compile() fills them in.
                info[3] = -1 if function_scope else end
        self.local_top = saved_local
        self.top = saved_top
        self.top = min(self.top, self.local_top)

    def declare_local(self, name: str) -> int:
        slot = self.local_top
        self.local_top += 1
        self.top = max(self.top, self.local_top)
        self.max_top = max(self.max_top, self.top)
        if self.local_top > MAX_STACK:
            raise BuildError(f"too many live locals (slot {self.local_top})", self.line)
        # start is patched to the pc *after* the initializer: that is the
        # convention the decompiler uses to fold `local x = <expr>` back
        # together (see tools/squirrel_decompile.py, declare()).
        self.locals.append([name, slot, -1, -1])
        return slot

    def lookup(self, name: str) -> int | None:
        for info in reversed(self.locals):
            if info[0] == name and info[3] == -1:
                return info[1]
        return None

    # -- expressions ---------------------------------------------------------
    def gen(self, e: Node, dst: int | None = None) -> int:
        """Compile `e`, writing the result to `dst` when one is given.

        `dst` is how `local x = <expr>` keeps the initializer in x's own VM
        register: Squirrel's local-variable info records the pc *after* the
        initializer, and the decompiler folds the pending value back into a
        `local` declaration only if no MOVE through another register got in
        the way.
        """
        if isinstance(e, EConst):
            return self.gen_const(e, dst)
        if isinstance(e, EName):
            if e.name == "this":
                slot = 0
            else:
                slot = self.lookup(e.name)
                if slot is None:
                    slot = dst if dst is not None else self.alloc()
                    idx = self.string_lit(e.name)
                    self.emit(OP["GETK"], slot, idx, 0, 0)
                    return slot
            if dst is not None and dst != slot:
                self.emit(OP["MOVE"], dst, slot, 0, 0)
                return dst
            return slot
        if isinstance(e, ERoot):
            dst = dst if dst is not None else self.alloc()
            self.emit(OP["LOADROOTTABLE"], dst, 0, 0, 0)
            return dst
        if isinstance(e, EMember):
            obj = self.gen(e.obj)
            dst = dst if dst is not None else self.alloc()
            if e.computed:
                key = self.gen(e.key_expr)
                self.emit(OP["GET"], dst, obj, key, 0)
            else:
                idx = self.string_lit(self._key_name(e.key_expr))
                self.emit(OP["GETK"], dst, idx, obj, 0)
            return dst
        if isinstance(e, ECall):
            return self.gen_call(e, True, dst)
        if isinstance(e, EUnary):
            return self.gen_unary(e, dst)
        if isinstance(e, EPostfix):
            return self.gen_incdec(e.expr, e.op, post=True, dst=dst)
        if isinstance(e, EBin):
            return self.gen_bin(e, dst)
        if isinstance(e, ETern):
            return self.gen_tern(e, dst)
        if isinstance(e, EAssign):
            return self.gen_assign(e, dst)
        if isinstance(e, ETable):
            return self.gen_table(e, dst)
        if isinstance(e, EArray):
            return self.gen_array(e, dst)
        if isinstance(e, EClosure):
            return self.gen_closure(e, dst)
        if isinstance(e, EDelegate):
            parent = self.gen(e.parent)
            table = self.gen(e.table)
            dst = dst if dst is not None else parent
            self.emit(OP["DELEGATE"], dst, table, parent, 0)
            return dst
        if isinstance(e, EVargc):
            dst = dst if dst is not None else self.alloc()
            self.emit(OP["VARGC"], dst, 0, 0, 0)
            return dst
        if isinstance(e, EVargv):
            index = self.gen(e.index)
            dst = dst if dst is not None else self.alloc()
            self.emit(OP["GETVARGV"], dst, index, 0, 0)
            return dst
        raise BuildError(f"cannot compile expression {type(e).__name__}", getattr(e, "line", 0))

    def gen_into(self, e: Node, target: int) -> int:
        reg = self.gen(e, target)
        if reg != target:
            self.emit(OP["MOVE"], target, reg, 0, 0)
        return target

    def gen_const(self, e: EConst, dst: int | None = None) -> int:
        dst = dst if dst is not None else self.alloc()
        if e.type == OT_INTEGER:
            value = int(e.value)
            if not -(1 << 31) <= value < (1 << 31):
                idx = self.lit(Obj(OT_INTEGER, value))
                self.emit(OP["LOAD"], dst, idx, 0, 0)
            else:
                self.emit(OP["LOADINT"], dst, 0, 0, 0)
                self.ins[-1].arg1 = value   # signed 32-bit immediate in arg1
        elif e.type == OT_FLOAT:
            raw = struct.unpack("<i", struct.pack("<f", float(e.value)))[0]
            self.emit(OP["LOADFLOAT"], dst, raw, 0, 0)
        elif e.type == OT_BOOL:
            self.emit(OP["LOADBOOL"], dst, 1 if e.value else 0, 0, 0)
        elif e.type == OT_STRING:
            idx = self.string_lit(str(e.value))
            self.emit(OP["LOAD"], dst, idx, 0, 0)
        else:
            self.emit(OP["LOADNULLS"], dst, 1, 0, 0)
        return dst

    def _key_name(self, key: Node) -> str:
        if isinstance(key, EConst) and key.type == OT_STRING:
            return str(key.value)
        raise BuildError("a non-literal member name must use [ ]", key.line)

    def gen_call(self, e: ECall, want_value: bool, dst: int | None = None) -> int:
        if isinstance(e.callee, EMember):
            obj = self.gen(e.callee.obj)
            key_reg = 0
            key_lit = 0
            computed = e.callee.computed
            if computed:
                key_reg = self.gen(e.callee.key_expr)
            else:
                key_lit = self.string_lit(self._key_name(e.callee.key_expr))
            base = self.alloc(2 + len(e.args))
            fn, this = base, base + 1
            if computed:
                self.emit(OP["PREPCALL"], fn, key_reg, obj, this)
            else:
                self.emit(OP["PREPCALLK"], fn, key_lit, obj, this)
            for i, arg in enumerate(e.args):
                self.gen_into(arg, base + 2 + i)
            # The game's VM loads the CALL target byte *unsigned* (`Sq_VmExecute`), so
            # stock Squirrel's -1/0xFF discard is 255 here: the result would be stored
            # at STK(stackbase + 255), far outside the frame, and the same value would
            # be reused when the callee resumes (WaitMenu/MessageLoop). Emit a real
            # register instead. A discarded result goes to the lowest free temporary
            # (`local_top`, below the call frame): the next statement reuses that
            # register, so the decompiler sees the call as a finished statement
            # instead of a pending value.
            target = fn if want_value else self.local_top
            self.emit(OP["CALL"], target, fn, this, len(e.args) + 1)
            out = self._finish(dst, fn) if want_value else fn
            self.top = max(self.local_top, fn + 1)
            return out
        # A bare `f(...)` is a lookup on the script table (`this`), which is how
        # the game's compiler emitted free calls: PREPCALLK with obj = this.
        if isinstance(e.callee, EName) and e.callee.name != "this" and self.lookup(e.callee.name) is None:
            key_lit = self.string_lit(e.callee.name)
            base = self.alloc(2 + len(e.args))
            fn, this = base, base + 1
            self.emit(OP["PREPCALLK"], fn, key_lit, 0, this)
            for i, arg in enumerate(e.args):
                self.gen_into(arg, base + 2 + i)
            target = fn if want_value else self.local_top
            self.emit(OP["CALL"], target, fn, this, len(e.args) + 1)
            out = self._finish(dst, fn) if want_value else fn
            self.top = max(self.local_top, fn + 1)
            return out
        fn = self.gen(e.callee)
        base = self.alloc(1 + len(e.args))
        this = base
        # A call through a local closure still passes the current `this`, which
        # the game's compiler materialises with a MOVE (and which is why the
        # decompiler prints `func(x)` rather than `func.call(null, x)`).
        self.emit(OP["MOVE"], this, 0, 0, 0)
        for i, arg in enumerate(e.args):
            self.gen_into(arg, base + 1 + i)
        target = fn if want_value else self.local_top
        self.emit(OP["CALL"], target, fn, this, len(e.args) + 1)
        out = self._finish(dst, fn) if want_value else fn
        self.top = max(self.local_top, fn + 1)
        return out

    def _finish(self, dst: int | None, reg: int) -> int:
        """Move a computed result into `dst` when the caller asked for one."""
        if dst is not None and dst != reg:
            self.emit(OP["MOVE"], dst, reg, 0, 0)
            return dst
        return reg

    def gen_unary(self, e: EUnary, dst: int | None = None) -> int:
        if e.op in ("++", "--"):
            return self.gen_incdec(e.expr, e.op, post=False, dst=dst)
        if e.op == "delete":
            target = e.expr
            if not isinstance(target, EMember):
                raise BuildError("delete needs a table slot", e.line)
            obj = self.gen(target.obj)
            out = dst if dst is not None else self.alloc()
            if target.computed:
                key = self.gen(target.key_expr)
                self.emit(OP["DELETE"], out, obj, key, 0)
            else:
                idx = self.string_lit(self._key_name(target.key_expr))
                key = self.alloc()
                self.emit(OP["LOAD"], key, idx, 0, 0)
                self.emit(OP["DELETE"], out, obj, key, 0)
            return out
        if e.op == "+":
            return self.gen(e.expr, dst)
        src = self.gen(e.expr)
        out = dst if dst is not None else self.alloc()
        op = {"-": "NEG", "!": "NOT", "~": "BWNOT", "typeof": "TYPEOF", "clone": "CLONE"}.get(e.op)
        if op is None:
            raise BuildError(f"unsupported unary operator {e.op!r}", e.line)
        self.emit(OP[op], out, src, 0, 0)
        return out

    def gen_incdec(self, target: Node, op: str, post: bool, dst: int | None = None) -> int:
        delta = 1 if op == "++" else -1
        if isinstance(target, EName):
            slot = 0 if target.name == "this" else self.lookup(target.name)
            if slot is None:
                raise BuildError(f"{op}{target.name}: only local variables can be incremented", target.line)
            out = dst if dst is not None else self.alloc()
            name = "PINCL" if post else "INCL"
            self.emit(OP[name], out, slot, 0, delta & 0xFF)
            return out
        raise BuildError(f"{op} is only supported on local variables (decompiler output always is)",
                         target.line)

    def gen_bin(self, e: EBin, dst: int | None = None) -> int:
        if e.op in ("&&", "||"):
            out = dst if dst is not None else self.alloc()
            self.gen_into(e.left, out)
            pc = self.emit(OP["AND"] if e.op == "&&" else OP["OR"], out, 0, out, 0)
            self.gen_into(e.right, out)
            self.patch(pc)
            return out
        left = self.gen(e.left)
        right = self.gen(e.right)
        dst = dst if dst is not None else self.alloc()
        if e.op in ("==", "!="):
            self.emit(OP["EQ"] if e.op == "==" else OP["NE"], dst, right, left, 0)
        elif e.op in CMP_CODE:
            self.emit(OP["CMP"], dst, right, left, CMP_CODE[e.op])
        elif e.op in BW_CODE:
            self.emit(OP["BITW"], dst, right, left, BW_CODE[e.op])
        elif e.op in ("+", "-", "*", "/", "%"):
            self.emit(OP["ARITH"], dst, right, left, ord(e.op))
        elif e.op == "in":
            self.emit(OP["EXISTS"], dst, left, right, 0)
        elif e.op == "instanceof":
            self.emit(OP["INSTANCEOF"], dst, left, right, 0)
        else:
            raise BuildError(f"unsupported binary operator {e.op!r}", e.line)
        return dst

    def gen_tern(self, e: ETern, dst: int | None = None) -> int:
        dst = dst if dst is not None else self.alloc()
        cond = self.gen(e.cond)
        jz = self.emit(OP["JZ"], cond, 0, 0, 0)
        self.gen_into(e.then, dst)
        jmp = self.emit(OP["JMP"], 0, 0, 0, 0)
        self.patch(jz)
        self.gen_into(e.otherwise, dst)
        self.patch(jmp)
        return dst

    def gen_assign(self, e: EAssign, dst: int | None = None) -> int:
        target, op = e.target, e.op
        if isinstance(target, EName) and target.name != "this":
            slot = self.lookup(target.name)
            if slot is not None and op != "<-":
                if op == "=":
                    self.gen_into(e.value, slot)
                    return self._finish(dst, slot)
                # local x += v  ->  COMPARITHL dst, slot, v, operator
                value = self.gen(e.value)
                out = dst if dst is not None else self.alloc()
                self.emit(OP["COMPARITHL"], out, slot, value, ord(op[0]))
                return out
            if op == "<-":
                return self.gen_newslot(target.name, e.value, dst)
            # global: this.name = value
            key = self.alloc()
            idx = self.string_lit(target.name)
            self.emit(OP["LOAD"], key, idx, 0, 0)
            if op == "=":
                value = self.gen(e.value)
                out = dst if dst is not None else self.alloc()
                self.emit(OP["SET"], out, 0, key, value)
                return out
            # compound on a global: read, combine, write
            read = self.alloc()
            self.emit(OP["GETK"], read, idx, 0, 0)
            rhs = self.gen(e.value)
            comb = self.alloc()
            self._emit_compound(comb, read, rhs, op)
            out = dst if dst is not None else self.alloc()
            self.emit(OP["SET"], out, 0, key, comb)
            return out
        if isinstance(target, EMember):
            obj = self.gen(target.obj)
            if target.computed:
                key = self.gen(target.key_expr)
            else:
                idx = self.string_lit(self._key_name(target.key_expr))
                key = self.alloc()
                self.emit(OP["LOAD"], key, idx, 0, 0)
            if op in ("=", "<-"):
                value = self.gen(e.value)
                out = dst if dst is not None else self.alloc()
                self.emit(OP["NEWSLOT" if op == "<-" else "SET"], out, obj, key, value)
                return out
            read = self.alloc()
            self.emit(OP["GET"], read, obj, key, 0)
            rhs = self.gen(e.value)
            comb = self.alloc()
            self._emit_compound(comb, read, rhs, op)
            out = dst if dst is not None else self.alloc()
            self.emit(OP["SET"], out, obj, key, comb)
            return out
        if isinstance(target, ERoot):
            raise BuildError("cannot assign to ::", e.line)
        raise BuildError("unsupported assignment target", e.line)

    def _emit_compound(self, dst: int, left: int, right: int, op: str) -> None:
        base = op[:-1]
        if base in ("==", "!=") or base in CMP_CODE:
            raise BuildError(f"{op} is not assignable", self.line)
        if base in BW_CODE:
            self.emit(OP["BITW"], dst, right, left, BW_CODE[base])
        elif base in ("+", "-", "*", "/", "%"):
            self.emit(OP["ARITH"], dst, right, left, ord(base))
        else:
            raise BuildError(f"unsupported compound operator {op!r}", self.line)

    def gen_newslot(self, name: str, value_expr: Node, dst: int | None = None) -> int:
        key = self.alloc()
        idx = self.string_lit(name)
        self.emit(OP["LOAD"], key, idx, 0, 0)
        value = self.gen(value_expr)
        out = dst if dst is not None else self.alloc()
        self.emit(OP["NEWSLOT"], out, 0, key, value)
        return out

    def gen_table(self, e: ETable, dst: int | None = None) -> int:
        dst = dst if dst is not None else self.alloc()
        self.emit(OP["NEWTABLE"], dst, len(e.entries), 0, 0)
        for key_expr, value_expr in e.entries:
            if key_expr is None:
                raise BuildError("table entry without a key", e.line)
            key = self.gen(key_expr)
            value = self.gen(value_expr)
            self.emit(OP["NEWSLOTA"], 0, dst, key, value)
            # A table literal is one statement but can hold hundreds of
            # entries; the per-entry key/value registers die immediately.
            self.top = max(self.local_top, dst + 1)
        return dst

    def gen_array(self, e: EArray, dst: int | None = None) -> int:
        dst = dst if dst is not None else self.alloc()
        self.emit(OP["NEWARRAY"], dst, len(e.items), 0, 0)
        for item in e.items:
            value = self.gen(item)
            self.emit(OP["APPENDARRAY"], dst, value, 0, 0)
            self.top = max(self.local_top, dst + 1)
        return dst

    def gen_closure(self, e: EClosure, dst: int | None = None) -> int:
        # index of the closure among this function's direct children, in the
        # same order direct_closures() walks the AST
        index = self._closure_indices[id(e.func)]
        dst = dst if dst is not None else self.alloc()
        self.emit(OP["CLOSURE"], dst, index, 0, 0)
        return dst

    def gen_stmt(self, s: Stmt) -> None:
        self.line = s.line or self.line
        self._gen_stmt(s)
        # every temporary dies at the end of its statement; only locals survive
        self.top = self.local_top

    def _gen_stmt(self, s: Stmt) -> None:
        if isinstance(s, ExprStmt):
            if isinstance(s.expr, ECall):
                self.gen_call(s.expr, False)
            elif isinstance(s.expr, EAssign):
                self.gen_assign(s.expr)
            else:
                self.gen(s.expr)
        elif isinstance(s, LocalStmt):
            slot = self.declare_local(s.name)
            if s.init is None:
                self.emit(OP["LOADNULLS"], slot, 1, 0, 0)
            else:
                self.gen_into(s.init, slot)
            for info in reversed(self.locals):
                if info[1] == slot and info[2] == -1:
                    info[2] = len(self.ins)
                    break
        elif isinstance(s, AssignStmt):
            self.gen_assign(s.assign)
        elif isinstance(s, IfStmt):
            cond = self.gen(s.cond)
            jz = self.emit(OP["JZ"], cond, 0, 0, 0)
            self.push_scope()
            for x in s.then:
                self.gen_stmt(x)
            self.pop_scope()
            if s.otherwise:
                jmp = self.emit(OP["JMP"], 0, 0, 0, 0)
                self.patch(jz)
                self.push_scope()
                for x in s.otherwise:
                    self.gen_stmt(x)
                self.pop_scope()
                self.patch(jmp)
            else:
                self.patch(jz)
        elif isinstance(s, WhileStmt):
            start = len(self.ins)
            if s.cond is not None:
                cond = self.gen(s.cond)
                jz = self.emit(OP["JZ"], cond, 0, 0, 0)
            else:
                jz = None
            self.breaks.append([])
            self.continues.append(([], start))
            self.push_scope()
            for x in s.body:
                self.gen_stmt(x)
            self.pop_scope()
            self.emit(OP["JMP"], 0, 0, 0, 0)
            self.patch(len(self.ins) - 1, start)
            end = len(self.ins)
            if jz is not None:
                self.patch(jz, end)
            self._patch_breaks(end)
            pcs, _ = self.continues.pop()
            for pc in pcs:
                self.patch(pc, start)
            self.breaks.pop()
        elif isinstance(s, ForStmt):
            self.push_scope()
            if s.init is not None:
                self.gen_stmt(s.init)
            start = len(self.ins)
            jz = None
            if s.cond is not None:
                cond = self.gen(s.cond)
                jz = self.emit(OP["JZ"], cond, 0, 0, 0)
            self.breaks.append([])
            self.continues.append(([], -1))
            cont_pcs, _ = self.continues[-1]
            self.push_scope()
            for x in s.body:
                self.gen_stmt(x)
            self.pop_scope()
            incr_start = len(self.ins)
            if s.incr is not None:
                self.gen_stmt(s.incr)
            self.emit(OP["JMP"], 0, 0, 0, 0)
            self.patch(len(self.ins) - 1, start)
            end = len(self.ins)
            if jz is not None:
                self.patch(jz, end)
            self._patch_breaks(end)
            for pc in cont_pcs:
                self.patch(pc, incr_start)
            self.continues.pop()
            self.breaks.pop()
            self.pop_scope()
        elif isinstance(s, SwitchStmt):
            # The subject has to survive every case body, so pin it as a
            # pseudo-local instead of an ordinary temporary.
            subject_slot = self.local_top
            self.local_top += 1
            self.top = max(self.top, self.local_top)
            try:
                self.gen_into(s.subject, subject_slot)
                subject = subject_slot
                breaks: list[int] = []
                self.breaks.append(breaks)
                for value, body in s.arms:
                    if value is None:
                        self.push_scope()
                        for x in body:
                            self.gen_stmt(x)
                        self.pop_scope()
                        continue
                    reg = self.gen(value)
                    self.emit(OP["EQ"], reg, reg, subject, 0)
                    jz = self.emit(OP["JZ"], reg, 0, 0, 0)
                    self.push_scope()
                    for x in body:
                        self.gen_stmt(x)
                    self.pop_scope()
                    self.patch(jz)
                    jmp = self.emit(OP["JMP"], 0, 0, 0, 0)
                    breaks.append(jmp)
                end = len(self.ins)
                for pc in breaks:
                    self.patch(pc, end)
                self.breaks.pop()
            finally:
                self.local_top = subject_slot
                self.top = min(self.top, subject_slot)
        elif isinstance(s, ReturnStmt):
            if s.value is None:
                self.emit(OP["RETURN"], 0xFF, 0, 0, 0)
            else:
                value = self.gen(s.value)
                self.emit(OP["RETURN"], 1, value, 0, 0)
        elif isinstance(s, BreakStmt):
            if not self.breaks:
                raise BuildError("break outside a loop or switch", s.line)
            pc = self.emit(OP["JMP"], 0, 0, 0, 0)
            self.breaks[-1].append(pc)
        elif isinstance(s, ContinueStmt):
            if not self.continues:
                raise BuildError("continue outside a loop", s.line)
            pc = self.emit(OP["JMP"], 0, 0, 0, 0)
            self.continues[-1][0].append(pc)
        elif isinstance(s, FuncDeclStmt):
            key = self.alloc()
            idx = self.string_lit(s.func.name or "")
            self.emit(OP["LOAD"], key, idx, 0, 0)
            closure = self.gen_closure(EClosure(s.func, s.line))
            dst = self.alloc()
            self.emit(OP["NEWSLOT"], dst, 0, key, closure)
        elif isinstance(s, DelegateStmt):
            self.gen(s.expr)
        else:
            raise BuildError(f"cannot compile statement {type(s).__name__}", s.line)

    def _patch_breaks(self, end: int) -> None:
        for pc in self.breaks[-1]:
            self.patch(pc, end)
        self.breaks[-1].clear()

    # -- driver --------------------------------------------------------------
    def compile(self) -> sqbin.Func:
        # Map each closure node to its index without re-walking inside children.
        kids = direct_closures(self.func)
        self._closure_indices = {id(k): i for i, k in enumerate(kids)}
        if len(kids) != len(self.children):
            raise BuildError(f"{len(kids)} closures found but {len(self.children)} compiled", self.func.line)
        self.push_scope()
        for s in self.func.body:
            self.gen_stmt(s)
        self.pop_scope()
        self.emit(OP["RETURN"], 0xFF, 0, 0, 0)
        last = len(self.ins) - 1
        for info in self.locals:
            if info[3] == -1:
                info[3] = last
        out = sqbin.Func(
            sourcename=self.sourcename,
            name=Obj(OT_STRING, self.name) if self.name else Obj(OT_NULL),
            literals=self.lits,
            parameters=[Obj(OT_STRING, p) for p in self.params],
            outervalues=[],
            localvarinfos=[(Obj(OT_STRING, n), slot, start, end) for n, slot, start, end in self.locals],
            lineinfos=list(self.lineinfos),
            defaultparams=[],
            instructions=self.ins,
            functions=list(self.children),
            stacksize=max(self.max_top, self.nparams),
            bgenerator=0,
            varparams=self.varparams,
        )
        return out


# ---------------------------------------------------------------------------
# bytecode validation - the frame rules this VM needs, checked before writing
# ---------------------------------------------------------------------------
#
# `SQVM::StartCall` sizes a call frame as `stackbase + func->_stacksize` and the
# interpreter never bounds-checks a register operand. A CNUT that names a
# register >= stacksize therefore writes into the caller's frame or past the VM
# stack: the pack loads, then the scene crashes without a script error. Every
# retail function (8,960 of them, 769 packs) keeps every register operand below
# its stacksize, so that is the rule enforced here.
#
# The first `CALL` operand is the register that receives the return value.
# Stock Squirrel writes -1 (0xFF) there when the result is discarded, but this
# VM stores a *resumed* callee's result through that operand, so -1 becomes
# `STK(255)` - the compiler bug that crashed scene loads (orchestration/done/
# E3b_script_compiler_fix.md). Retail never emits it and neither may we.
#
# Operand map: ("r", i) is a register in arg[i]; ("n", base, count) is the
# register range arg[base] .. arg[base] + arg[count] - 1 (call arguments).

REGISTER_OPERANDS: dict[str, tuple] = {
    "LOAD": (("r", 0),),
    "LOADINT": (("r", 0),),
    "LOADFLOAT": (("r", 0),),
    "LOADBOOL": (("r", 0),),
    "DLOAD": (("r", 0), ("r", 2)),
    "TAILCALL": (("r", 0), ("r", 1), ("n", 2, 3)),
    "CALL": (("r", 0), ("r", 1), ("n", 2, 3)),
    "PREPCALL": (("r", 0), ("r", 1), ("r", 2), ("r", 3)),
    "PREPCALLK": (("r", 0), ("r", 2), ("r", 3)),
    "GETK": (("r", 0), ("r", 2)),
    "MOVE": (("r", 0), ("r", 1)),
    "NEWSLOT": (("r", 0), ("r", 1), ("r", 2), ("r", 3)),
    "NEWSLOTA": (("r", 1), ("r", 2), ("r", 3)),
    "DELETE": (("r", 0), ("r", 1), ("r", 2)),
    "SET": (("r", 0), ("r", 1), ("r", 2), ("r", 3)),
    "GET": (("r", 0), ("r", 1), ("r", 2)),
    "EQ": (("r", 0), ("r", 1), ("r", 2)),
    "NE": (("r", 0), ("r", 1), ("r", 2)),
    "ARITH": (("r", 0), ("r", 1), ("r", 2)),
    "BITW": (("r", 0), ("r", 1), ("r", 2)),
    "CMP": (("r", 0), ("r", 1), ("r", 2)),
    "RETURN": (("r", 1),),
    "LOADNULLS": (("r", 0),),
    "LOADROOTTABLE": (("r", 0),),
    "JNZ": (("r", 0),),
    "JZ": (("r", 0),),
    "LOADFREEVAR": (("r", 0),),
    "VARGC": (("r", 0),),
    "GETVARGV": (("r", 0), ("r", 1)),
    "NEWTABLE": (("r", 0),),
    "NEWARRAY": (("r", 0),),
    "APPENDARRAY": (("r", 0), ("r", 1)),
    "GETPARENT": (("r", 0), ("r", 1)),
    "COMPARITH": (("r", 0), ("r", 1), ("r", 2)),
    "COMPARITHL": (("r", 0), ("r", 2)),
    "INC": (("r", 0), ("r", 1)),
    "INCL": (("r", 0),),
    "PINC": (("r", 0), ("r", 1)),
    "PINCL": (("r", 0),),
    "EXISTS": (("r", 0), ("r", 1), ("r", 2)),
    "INSTANCEOF": (("r", 0), ("r", 1), ("r", 2)),
    "AND": (("r", 0), ("r", 2)),
    "OR": (("r", 0), ("r", 2)),
    "NEG": (("r", 0), ("r", 1)),
    "NOT": (("r", 0), ("r", 1)),
    "BWNOT": (("r", 0), ("r", 1)),
    "CLOSURE": (("r", 0),),
    "DELEGATE": (("r", 0), ("r", 1), ("r", 2)),
    "CLONE": (("r", 0), ("r", 1)),
    "TYPEOF": (("r", 0), ("r", 1)),
    "PUSHTRAP": (("r", 0),),
    "THROW": (("r", 0),),
    "CLASS": (("r", 0),),
    "DMOVE": (("r", 0), ("r", 1), ("r", 2), ("r", 3)),
    "YIELD": (("r", 0),),
    "RESUME": (("r", 0), ("r", 1)),
    "FOREACH": (("r", 0), ("r", 1), ("r", 2), ("r", 3)),
    "POSTFOREACH": (("r", 0), ("r", 1), ("r", 2), ("r", 3)),
}

# Instructions whose arg1 is a relative jump offset (target = pc + 1 + arg1).
JUMP_OPERANDS = {"JMP", "JZ", "JNZ", "AND", "OR", "PUSHTRAP"}
# Instructions whose arg1 is an index into the function's literal table.
LITERAL_OPERANDS = {"LOAD": (1,), "GETK": (1,), "PREPCALLK": (1,), "DLOAD": (1, 3)}


def _literals_in_range(fn: sqbin.Func, ins: sqbin.Insn, name: str) -> str | None:
    for index in LITERAL_OPERANDS.get(name, ()):
        value = (ins.arg0, ins.arg1, ins.arg2, ins.arg3)[index]
        if not 0 <= value < len(fn.literals):
            return f"literal index {value} is outside the table ({len(fn.literals)} entries)"
    return None


def _check_function(fn: sqbin.Func, path: str, problems: list[str]) -> None:
    name = fn.name.value if fn.name.type == OT_STRING else "<anonymous>"
    where = f"{path}/{name}" if path else name
    count = len(fn.instructions)
    if not len(fn.parameters) <= fn.stacksize <= MAX_STACK:
        problems.append(
            f"{where}: stack size {fn.stacksize} cannot hold {len(fn.parameters)} parameter(s) "
            f"or exceeds the VM limit of {MAX_STACK}")
    for pc, ins in enumerate(fn.instructions):
        op = OPS[ins.op] if ins.op < len(OPS) else f"opcode {ins.op}"
        args = (ins.arg0, ins.arg1, ins.arg2, ins.arg3)
        for spec in REGISTER_OPERANDS.get(op, ()):
            if spec[0] == "r":
                registers = (args[spec[1]],)
            else:
                nargs = args[spec[2]]
                registers = range(args[spec[1]], args[spec[1]] + nargs) if nargs > 0 else ()
            for reg in registers:
                if reg >= fn.stacksize:
                    if op == "CALL" and reg == 0xFF:
                        problems.append(
                            f"{where}: instruction {pc} CALL discards its result into register "
                            f"-1 (0xFF); this VM stores a resumed callee's value there and "
                            f"writes past the frame (stack {fn.stacksize})")
                    else:
                        problems.append(
                            f"{where}: instruction {pc} {op} uses register {reg} but the frame "
                            f"only has {fn.stacksize}")
        bad_literal = _literals_in_range(fn, ins, op)
        if bad_literal:
            problems.append(f"{where}: instruction {pc} {op}: {bad_literal}")
        if op == "CLOSURE" and not 0 <= ins.arg1 < len(fn.functions):
            problems.append(
                f"{where}: instruction {pc} CLOSURE refers to prototype {ins.arg1} but only "
                f"{len(fn.functions)} exist")
        if op in JUMP_OPERANDS:
            target = pc + 1 + ins.arg1
            if not 0 <= target <= count:
                problems.append(
                    f"{where}: instruction {pc} {op} jumps to {target}, outside 0..{count}")
    for var, slot, start, end in fn.localvarinfos:
        if slot >= fn.stacksize:
            problems.append(
                f"{where}: local '{var.value}' sits in register {slot}, outside the "
                f"{fn.stacksize}-register frame")
        # Retail has 19 locals whose start is one past their end (a `local`
        # declared as the last statement of a block) - that is the game
        # decompiler's convention, not a fault. Only ranges that leave the
        # instruction list are.
        if max(start, end) > count:
            problems.append(
                f"{where}: local '{var.value}' is live over instructions {start}..{end}, "
                f"outside 0..{count}")
    for line, pc in fn.lineinfos:
        if not 0 <= pc < max(count, 1):
            problems.append(
                f"{where}: line info for source line {line} points at instruction {pc}, "
                f"outside 0..{count - 1}")
    for kind, src, var in fn.outervalues:
        if kind not in (0, 1, 2):
            problems.append(f"{where}: outer value '{var.value}' has unknown kind {kind}")
    for child in fn.functions:
        _check_function(child, path, problems)


def validate_nut(func: sqbin.Func) -> list[str]:
    """Everything about `func` that would make the game's Squirrel VM misbehave.

    An empty list means the frame, literal, prototype, jump and line tables are
    all self-consistent. This is the check `source_build`/`assembly_build` run
    before a single byte reaches a pack.
    """
    problems: list[str] = []
    _check_function(func, "", problems)
    return problems


def require_valid(func: sqbin.Func, tier: str) -> None:
    """Refuse a build the VM would crash on, naming the construct."""
    problems = validate_nut(func)
    if not problems:
        return
    hint = ("This is a compiler bug for this construct: make the same edit in the "
            "annotated listing (script.nut, --tier asm) instead."
            if tier == "source" else
            "Fix the listed instruction(s) in the annotated listing.")
    more = f" (+{len(problems) - 1} more)" if len(problems) > 1 else ""
    raise BuildError(f"refusing to write a script the VM cannot run: {problems[0]}{more}. {hint}")


# ---------------------------------------------------------------------------
# tier selection and the two build paths
# ---------------------------------------------------------------------------

def looks_like_listing(text: str) -> bool:
    """The annotated disassembly starts lines with `[   0] OPCODE`."""
    return bool(re.search(r"^\s*\[\s*\d+\]\s+[A-Z]", text, re.MULTILINE))


def assembly_build(text: str) -> tuple[bytes, dict]:
    try:
        func = sqbin.assemble_nut(text)
        data = sqbin.build(func)
    except BuildError:
        raise
    except Exception as exc:  # sqbin raises ValueError/IndexError/...
        raise BuildError(f"assembly failed: {exc}") from exc
    # Prove the result parses and rebuilds before anyone writes it to a pack.
    reparsed = sqbin.parse(data)
    if sqbin.build(reparsed) != data:
        raise BuildError("assembled bytecode does not round-trip through the parser")
    require_valid(reparsed, "asm")
    return data, {"tier": "asm", "functions": sum(1 for _ in _walk_funcs(reparsed))}


def _walk_funcs(f: sqbin.Func):
    yield f
    for g in f.functions:
        yield from _walk_funcs(g)


def _clone_func(f: sqbin.Func) -> sqbin.Func:
    return copy.deepcopy(f)


def _unique_name_index(items, name_of) -> dict[str, int]:
    """name -> position, but only for names that occur exactly once."""
    seen: dict[str, int] = {}
    duplicated: set[str] = set()
    for i, item in enumerate(items):
        name = name_of(item)
        if name is None:
            continue
        if name in seen:
            duplicated.add(name)
        else:
            seen[name] = i
    return {name: i for name, i in seen.items() if name not in duplicated}


def _proto_name(func: sqbin.Func) -> str | None:
    return func.name.value if func.name.type == OT_STRING else None


def compile_function(node: FuncNode, orig_node: FuncNode | None, orig_func: sqbin.Func | None,
                     reuse: bool, report: list[dict], path: str) -> tuple[sqbin.Func, bool]:
    kids = direct_closures(node)
    kids_orig = direct_closures(orig_node) if orig_node is not None else []
    # Match children by unique name, not by position. Inserting one function
    # shifts every later index, and comparing the new list position i against
    # the original position i recompiles all of them for nothing - that is the
    # "13-15 recompiled functions" a one-function addition used to report, and
    # every avoidable recompile is another chance to hit a compiler gap.
    orig_by_name = _unique_name_index(kids_orig, lambda k: k.name)
    orig_funcs = orig_func.functions if orig_func is not None else []
    funcs_by_name = _unique_name_index(orig_funcs, _proto_name)
    child_protos: list[sqbin.Func] = []
    child_reports: list[bool] = []
    for i, kid in enumerate(kids):
        if kid.name is not None:
            # A function we have never seen (a new one) has no original to reuse.
            oi = orig_by_name.get(kid.name)
        else:
            oi = i if i < len(kids_orig) else None
        kid_orig_node = kids_orig[oi] if oi is not None else None
        if kid.name is not None:
            fi = funcs_by_name.get(kid.name)
        else:
            fi = i if i < len(orig_funcs) else None
        kid_orig_func = orig_funcs[fi] if fi is not None else None
        kid_name = f"{path}/{kid.name or f'<closure {i}>'}"
        proto, was_reused = compile_function(kid, kid_orig_node, kid_orig_func, reuse, report, kid_name)
        child_protos.append(proto)
        child_reports.append(was_reused)


    unchanged = reuse and orig_node is not None and orig_func is not None \
        and node.key() == orig_node.key()
    if unchanged:
        report.append({"function": path, "name": node.name, "reused": True})
        return _clone_func(orig_func), True

    name = node.name
    if name is None and orig_func is not None and orig_func.name.type == OT_STRING:
        name = orig_func.name.value
    sourcename = orig_func.sourcename if orig_func is not None else Obj(OT_STRING, "script.nut")
    gen = CodeGen(node, child_protos, name, sourcename)
    func = gen.compile()
    report.append({
        "function": path,
        "name": node.name,
        "reused": False,
        "instructions": len(func.instructions),
        "children": len(child_protos),
        "children_reused": sum(1 for x in child_reports if x),
    })
    return func, False


def source_build(text: str, original: bytes | None, reuse: bool = True) -> tuple[bytes, dict]:
    from tools import squirrel_decompile

    new_mod = parse_source(text)
    orig_mod = None
    orig_func = None
    if original is not None:
        orig_func = sqbin.parse(original)
        orig_text, _ = squirrel_decompile.decompile_bytes(original, "original.cnut")
        try:
            orig_mod = parse_source(orig_text)
        except BuildError as exc:
            if reuse:
                # The decompiler output is the only representation of the
                # original script; if it does not parse we cannot prove a
                # function is unchanged, so compile everything instead.
                orig_mod = None
                orig_func = None
            else:
                raise BuildError(f"the original script did not parse: {exc.text()}") from exc

    report: list[dict] = []
    func, _ = compile_function(new_mod, orig_mod, orig_func, reuse, report, "main")
    data = sqbin.build(func)
    if data[:2] != b"\xfa\xfa":
        raise BuildError("internal error: compiled stream has no CNUT header")
    # The game's VM does not bounds-check register operands, so a frame/literal/
    # prototype slip turns into a crash at scene load, not into a script error.
    require_valid(func, "source")
    return data, {
        "tier": "source",
        "functions": sum(1 for _ in _walk_funcs(func)),
        "reused": sum(1 for r in report if r["reused"]),
        "compiled": sum(1 for r in report if not r["reused"]),
        "functions_report": report,
    }


def build_text(text: str, original: bytes | None, tier: str = "auto", reuse: bool = True
               ) -> tuple[bytes, dict]:
    tier = tier.lower()
    if tier == "auto":
        tier = "asm" if looks_like_listing(text) else "source"
    if tier == "asm":
        return assembly_build(text)
    if tier == "source":
        return source_build(text, original, reuse)
    raise BuildError(f"unknown tier {tier!r}")


# ---------------------------------------------------------------------------
# pack staging
# ---------------------------------------------------------------------------

def area_paths(area: str) -> tuple[Path, str, str]:
    """(original .cnut, romfs pack path, member name) for one script area."""
    area = area.replace("\\", "/").strip("/")
    orig = CNUT_DIR / area / "script.cnut"
    if not orig.is_file():
        raise BuildError(f"no extracted script at {orig.relative_to(PROJECT_ROOT)} "
                         f"(run python tools/extract_game_data.py --all)")
    pack = ROMFS_SCRIPT_DIR / f"{area}.pack"
    if not pack.is_file():
        raise BuildError(f"no retail pack at {pack.relative_to(PROJECT_ROOT)}")
    return orig, f"script/{area}.pack", "script.cnut"


def save_to_mod(data: bytes, area: str, mod_dir: Path) -> dict:
    from tools.export_mod import stage_member

    orig, pack_rel, member = area_paths(area)
    out_dir = PROJECT_ROOT / "build" / "script_edits" / area.replace("/", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "script.cnut"
    out.write_bytes(data)
    info = stage_member(pack_rel, member, out, mod_dir,
                        work_dir=PROJECT_ROOT / "build" / "staged")
    return {"compiled_file": str(out.relative_to(PROJECT_ROOT)), **info}


# ---------------------------------------------------------------------------
# index: function tree, native calls and cross-references
# ---------------------------------------------------------------------------

CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
FUNC_RE = re.compile(r"^(\s*)function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)")
NON_CALLS = {"if", "while", "for", "switch", "function", "return", "typeof", "local", "delegate",
             "catch", "sizeof"}


def _strip_code(line: str) -> str:
    """Drop a trailing `//` comment, respecting simple string literals."""
    out: list[str] = []
    in_str = False
    escaped = False
    for c in line:
        if in_str:
            out.append(c)
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
            out.append(c)
            continue
        if c == "/" and out and out[-1] == "/":
            break
        out.append(c)
    return "".join(out)


def scan_decompiled(text: str) -> tuple[list[dict], list[str], dict[str, list[str]]]:
    """(functions, native-use names, calls-by-function) for one script."""
    lines = text.splitlines()
    funcs: list[dict] = []
    stack: list[tuple[str, int]] = []       # (function name, brace depth at entry)
    depth = 0
    calls: dict[str, list[str]] = {}
    native_hits: set[str] = set()
    current = "<top>"
    calls.setdefault(current, [])
    for index, raw in enumerate(lines):
        code = _strip_code(raw)
        m = FUNC_RE.match(code)
        if m:
            name = m.group(2)
            args = m.group(3).strip()
            funcs.append({"name": name, "params": args, "line": index + 1})
            stack.append((current, depth))
            current = name
            calls.setdefault(current, [])
        for cm in CALL_RE.finditer(code):
            name = cm.group(1)
            if name in NON_CALLS:
                continue
            calls.setdefault(current, []).append(name)
            if name in NATIVE_NAMES:
                native_hits.add(name)
        depth += code.count("{") - code.count("}")
        while stack and depth <= stack[-1][1] and not m:
            current, _ = stack.pop()
    return funcs, sorted(native_hits), calls


NATIVE_NAMES: set[str] = set()


def load_natives() -> dict[str, dict]:
    """Native engine functions the scripts can call, with their summaries.

    ``symbols.json`` has the real registered name (source
    ``native_engine_table``); ``orchestration/naming/out`` adds the human
    summary for the address when a worker has named it.
    """
    out: dict[str, dict] = {}
    symbols_file = PROJECT_ROOT / "symbols.json"
    try:
        symbols = json.loads(symbols_file.read_text(encoding="utf-8"))["symbols"]
    except (OSError, KeyError, json.JSONDecodeError):
        symbols = []
    by_addr: dict[str, str] = {}
    for entry in symbols:
        if entry.get("source") != "native_engine_table":
            continue
        name = entry.get("name")
        if not name:
            continue
        out[name] = {
            "address": entry.get("address"),
            "summary": entry.get("description") or "",
        }
        if entry.get("address"):
            by_addr[entry["address"].lower()] = name
    naming = PROJECT_ROOT / "orchestration" / "naming" / "out"
    if naming.is_dir():
        for path in sorted(naming.glob("N_*.json")):
            try:
                raw = path.read_bytes()
                try:
                    rows = json.loads(raw.decode("utf-8"))
                except UnicodeDecodeError:
                    rows = json.loads(raw.decode("cp1252"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                name = by_addr.get(str(row.get("address", "")).lower())
                if not name:
                    continue
                summary = row.get("summary") or ""
                if summary:
                    out[name]["summary"] = (
                        f"{summary} (native at {out[name]['address']}, source {row.get('name', '')})"
                    )
                    out[name]["documented_as"] = row.get("name")
    return out


def describe_area(area: str) -> tuple[str, str, str]:
    """(category, readable title, one-line description) for a script PACK.

    ``organize_scripts.resolve_readable_info`` already names every story
    chapter, boss, dungeon and map. It has no entry for the system packs or
    the ``c_``/``f_`` families, so those get an explicit, honest label here
    instead of ``System_c_010``.
    """
    from tools.organize_scripts import resolve_readable_info

    special = {
        "a000_area": ("System", "Area_Event_Framework",
                      "Per-map event entry points (StartEvent/TrgEvent wrappers) shared by every area"),
        "base": ("System", "Script_Base_Library",
                 "Thread/event runtime helpers used by the script packs"),
        "common": ("System", "Common_Scenario_Library",
                   "Scenario, quest and shop helpers shared by every chapter"),
        "c_com": ("System", "Cutscene_Common_Library",
                  "Helpers shared by the cutscene scripts"),
        "cs_viewer": ("System", "Cutscene_Viewer", "Cutscene viewer mode"),
        "camp": ("System", "Camp_System", "Camp menu script"),
        "dive": ("System", "Dive_Minigame", "Diving minigame script"),
        "past": ("System", "Past_World_System", "Past-world transition script"),
        "world": ("System", "World_Map_System", "World-map script"),
        "worldc": ("System", "World_Map_Common", "World-map common script"),
    }
    if area in special:
        category, title, description = special[area]
        return category, title, description
    if re.fullmatch(r"c_\d+(?:_\d+)?", area):
        return ("Cutscenes", f"Cutscene_Chapter_{area}",
                f"Cutscene chapter container {area} (its child packs hold the individual scenes)")
    if re.fullmatch(r"f\d{3}c?", area):
        return ("Fields", f"Field_Script_{area}", f"Overworld/field event script {area}")
    if re.fullmatch(r"p\d{3}", area):
        return ("General", f"Scene_Script_{area}", f"Standalone scene script pack {area}")
    if area.startswith("k_") and "_cs_" in area:
        return ("Cutscenes", f"Cutscene_{area}", f"Cutscene sequence {area}")
    return resolve_readable_info(area)


def build_index(out_path: Path = DEFAULT_INDEX) -> dict:
    global NATIVE_NAMES

    natives = load_natives()
    NATIVE_NAMES = set(natives)
    scripts: dict[str, dict] = {}
    defined: dict[str, set[str]] = {}
    callers: dict[str, list[dict]] = {}
    areas = sorted(p.parent.name for p in SCRIPTS_DIR.glob("packs/script/*/script.decompiled.nut"))
    for area in areas:
        text_path = SCRIPTS_DIR / "packs" / "script" / area / "script.decompiled.nut"
        text = text_path.read_text(encoding="utf-8", errors="replace")
        funcs, native_uses, calls = scan_decompiled(text)
        category, title, description = describe_area(area)
        scripts[area] = {
            "lines": text.count("\n") + 1,
            "functions": funcs,
            "natives": native_uses,
            "pack": f"script/{area}.pack",
            "category": category,
            "title": title,
            "description": description,
            "source": f"game_assets/scripts/packs/script/{area}/script.decompiled.nut",
        }
        for f in funcs:
            defined.setdefault(f["name"], set()).add(area)
        for caller, names in calls.items():
            for name in set(names):
                if name in caller:
                    continue
                callers.setdefault(name, []).append({"script": area, "caller": caller})
    xrefs = {}
    for name, rows in sorted(callers.items()):
        if name not in defined:
            continue        # not a script function: a native or a local variable call
        # StartEvent and friends are defined in most packs; the editor computes
        # the same-file callers itself, so only a sample is stored here.
        xrefs[name] = {
            "count": len(rows),
            "defined_in": len(defined[name]),
            "callers": rows[:20],
        }
    index = {
        "generated": time.strftime("%Y-%m-%d %H:%M"),
        "areas": len(scripts),
        "functions": sum(len(s["functions"]) for s in scripts.values()),
        "natives": natives,
        "scripts": scripts,
        "xrefs": xrefs,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return index


# ---------------------------------------------------------------------------
# verification over the whole corpus
# ---------------------------------------------------------------------------

def _semantic_key(node: Node):
    """AST fingerprint for verification, normalising `this.x` to `x`.

    Squirrel resolves a free name on the script table (`this`), so the compiler
    is free to emit GETK or GET for the same expression. The decompiler prints
    the two spellings in different places; they mean the same thing.
    """
    def norm(k):
        if not isinstance(k, tuple) or not k:
            return k
        if k[0] == "m" and k[1] == ("n", "this") and isinstance(k[2], tuple) \
                and k[2][:2] == ("c", OT_STRING):
            return ("n", k[2][2])
        return tuple(norm(x) for x in k)
    return norm(node.key())


def verify(limit: int | None = None) -> dict:
    from tools import squirrel_decompile

    paths = sorted(CNUT_DIR.rglob("script.cnut"))
    if limit:
        paths = paths[:limit]
    rows: list[dict] = []
    ok_asm = ok_source = ok_identical = ok_reuse = ok_semantic = 0
    failures: list[dict] = []
    start = time.time()
    for path in paths:
        area = path.parent.name
        rel = f"script/{area}"
        try:
            data = path.read_bytes()
            text_asm = sqbin.disasm(sqbin.parse(data))
            rebuilt, info = assembly_build(text_asm)
            asm_ok = rebuilt == data
            ok_asm += asm_ok

            src, _ = squirrel_decompile.decompile_bytes(data, rel)
            full, _ = source_build(src, data, reuse=False)
            source_ok = True
            try:
                sqbin.build(sqbin.parse(full))
            except Exception:
                source_ok = False
            ok_source += source_ok
            identical = full == data
            ok_identical += identical

            reuse_bytes, _ = source_build(src, data, reuse=True)
            reuse_ok = reuse_bytes == data
            ok_reuse += reuse_ok

            # Semantic check: compile from scratch, decompile that bytecode and
            # compare the AST with the one we compiled. This proves the
            # compiler's output means the same thing even when the original
            # register allocation/line table differ.
            semantic = False
            if source_ok:
                try:
                    back, _ = squirrel_decompile.decompile_bytes(full, rel)
                    semantic = _semantic_key(parse_source(back)) == _semantic_key(parse_source(src))
                except BuildError:
                    semantic = False
            ok_semantic += semantic
            rows.append({
                "area": area, "asm": asm_ok, "source": source_ok, "identical": identical,
                "reuse": reuse_ok, "semantic": semantic, "bytes": len(data),
            })
            if not (asm_ok and source_ok and reuse_ok and semantic):
                failures.append({
                    "area": area, "asm": asm_ok, "source": source_ok,
                    "identical": identical, "reuse": reuse_ok, "semantic": semantic,
                })
        except Exception as exc:
            failures.append({"area": area, "error": f"{type(exc).__name__}: {exc}"})
    report = {
        "scripts": len(paths),
        "assembly_identical": ok_asm,
        "source_parses_and_compiles": ok_source,
        "source_identical": ok_identical,
        "unchanged_reuse_identical": ok_reuse,
        "source_semantic_roundtrip": ok_semantic,
        "seconds": round(time.time() - start, 1),
        "failures": failures,
        "rows": rows,
    }
    return report


def write_verify_markdown(report: dict, out_path: Path) -> None:
    lines = [
        "# Squirrel script build coverage",
        "",
        "Generated by `python tools/script_build.py verify`. Two editing levels are measured: the",
        "annotated assembly listing (bit-exact) and the readable `.nut` source (compiled by",
        "`tools/script_build.py`).",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Scripts checked | {report['scripts']} |",
        f"| Assembly listing rebuilds identical bytes | {report['assembly_identical']} / {report['scripts']} |",
        f"| Source parses and compiles to valid CNUT | {report['source_parses_and_compiles']} / {report['scripts']} |",
        f"| Source compile is byte-identical to retail | {report['source_identical']} / {report['scripts']} |",
        f"| Unchanged source rebuilds identical bytes (incremental reuse) | {report['unchanged_reuse_identical']} / {report['scripts']} |",
        f"| Compiled source decompiles back to the same AST | {report['source_semantic_roundtrip']} / {report['scripts']} |",
        f"| Wall time | {report['seconds']} s |",
        "",
    ]
    if report["failures"]:
        lines.append("## Scripts that need attention")
        lines.append("")
        lines.append("| Area | asm | parses | identical | reuse | semantic | error |")
        lines.append("|---|---|---|---|---|---|---|")
        for row in report["failures"][:200]:
            lines.append(
                f"| {row.get('area')} | {row.get('asm')} | {row.get('source')} | "
                f"{row.get('identical')} | {row.get('reuse')} | {row.get('semantic')} | "
                f"{row.get('error', '')} |"
            )
    else:
        lines.append("No failures: every script round-trips through both levels.")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _emit_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def cmd_compile(args) -> int:
    src = Path(args.source)
    try:
        text = src.read_text(encoding="utf-8")
    except OSError as exc:
        _emit_json({"ok": False, "errors": [f"cannot read {src}: {exc}"]}) if args.json else None
        print(f"error: cannot read {src}: {exc}")
        return 2
    original = None
    if args.area:
        try:
            original = area_paths(args.area)[0].read_bytes()
        except BuildError as exc:
            print(f"error: {exc}")
            return 2
    try:
        data, info = build_text(text, original, args.tier, reuse=not args.no_reuse)
    except BuildError as exc:
        if args.json:
            _emit_json({"ok": False, "errors": [exc.text()], "tier": args.tier})
        else:
            print(f"error: {exc.text()}")
        return 1
    out = Path(args.output) if args.output else src.with_suffix(".cnut")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    if args.json:
        _emit_json({"ok": True, "tier": info["tier"], "bytes": len(data),
                    "output": str(out), **{k: v for k, v in info.items() if k != "functions_report"}})
    else:
        print(f"{info['tier']} build: {len(data)} bytes -> {out}")
        if info["tier"] == "source":
            print(f"  {info['reused']} functions reused, {info['compiled']} compiled")
    return 0


def cmd_pack(args) -> int:
    src = Path(args.source)
    try:
        text = src.read_text(encoding="utf-8")
    except OSError as exc:
        message = f"cannot read {src}: {exc}"
        _emit_json({"ok": False, "errors": [message]}) if args.json else print(f"error: {message}")
        return 2
    try:
        original, _, _ = area_paths(args.area)
        data, info = build_text(text, original.read_bytes(), args.tier, reuse=not args.no_reuse)
        info.update(save_to_mod(data, args.area, Path(args.mod)))
    except BuildError as exc:
        if args.json:
            _emit_json({"ok": False, "errors": [exc.text()], "tier": args.tier})
        else:
            print(f"error: {exc.text()}")
        return 1
    if args.json:
        _emit_json({"ok": True, "bytes": len(data), **{k: v for k, v in info.items() if k != "functions_report"}})
    else:
        print(f"{info['tier']} build: {len(data)} bytes")
        print(f"staged {info['pack']}:{info['member']} -> {info['mod_file']}")
    return 0


def cmd_verify(args) -> int:
    report = verify(args.limit)
    out = Path(args.report) if args.report else PROJECT_ROOT / "audit" / "SCRIPT_BUILD.md"
    write_verify_markdown(report, out)
    print(f"scripts: {report['scripts']}")
    print(f"  assembly identical:      {report['assembly_identical']}/{report['scripts']}")
    print(f"  source parses/compiles:  {report['source_parses_and_compiles']}/{report['scripts']}")
    print(f"  source byte-identical:   {report['source_identical']}/{report['scripts']}")
    print(f"  unchanged reuse exact:   {report['unchanged_reuse_identical']}/{report['scripts']}")
    print(f"  source semantic roundtrip:{report['source_semantic_roundtrip']}/{report['scripts']}")
    print(f"  report: {out}")
    if report["failures"]:
        print(f"  {len(report['failures'])} scripts need attention (see the report)")
    return 0 if not report["failures"] else 1


def cmd_index(args) -> int:
    out = Path(args.out) if args.out else DEFAULT_INDEX
    index = build_index(out)
    print(f"indexed {index['areas']} areas, {index['functions']} functions, "
          f"{len(index['natives'])} native calls, {len(index['xrefs'])} called names -> {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build DQXI Squirrel scripts from source or listing")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_build_args(p):
        p.add_argument("source", type=Path, help="edited .nut source or disassembly listing")
        p.add_argument("--area", required=True, help="script area / pack name, e.g. a_010")
        p.add_argument("--tier", default="auto", choices=["auto", "source", "asm"],
                       help="source = readable .nut, asm = annotated listing (default: detect)")
        p.add_argument("--no-reuse", action="store_true",
                       help="recompile every function instead of copying unchanged ones")
        p.add_argument("--json", action="store_true", help="machine-readable result for the editor")

    p_compile = sub.add_parser("compile", help="compile one script to .cnut")
    add_build_args(p_compile)
    p_compile.add_argument("-o", "--output", type=Path, help="output .cnut (default: beside the source)")
    p_compile.set_defaults(func=cmd_compile)

    p_pack = sub.add_parser("pack", help="compile one script and stage its RomFS pack in mod/romfs")
    add_build_args(p_pack)
    p_pack.add_argument("--mod", default=str(PROJECT_ROOT / "mod"), help="mod workspace root")
    p_pack.set_defaults(func=cmd_pack)

    p_verify = sub.add_parser("verify", help="round-trip every script and write audit/SCRIPT_BUILD.md")
    p_verify.add_argument("--limit", type=int, default=None)
    p_verify.add_argument("--report", type=Path, default=None)
    p_verify.set_defaults(func=cmd_verify)

    p_index = sub.add_parser("index", help="write game_assets/scripts/script_index.json for the editor")
    p_index.add_argument("--out", type=Path, default=None)
    p_index.set_defaults(func=cmd_index)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
