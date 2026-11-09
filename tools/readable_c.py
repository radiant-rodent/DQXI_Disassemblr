#!/usr/bin/env python3
"""tools/readable_c.py - readability pass over the Ghidra C output.

Ghidra's output for this executable is correct but hard to read: 98% of the
functions are unnamed, locals are uVar1/iVar2, the object a method works on is
`param_1`, and every struct field is pointer arithmetic such as
`*(int *)(param_1 + 0x274)`. This pass rewrites each function into a read-only
pseudo-C view next to the original (decomp/readable/, same relative paths):

  * calls use the function's real name wherever one is known (symbols, Squirrel
    natives); every function gets a header listing its named callers/callees
  * a first argument used as an object becomes `self`, other params `argN`
  * `*(T *)(p + 0xNN)` becomes `p->f_NN` (nested chains included), and
    `(p + 0xNN)` on such a pointer `&p->f_NN`
  * Ghidra placeholder types become fixed-width ones (undefined4 -> u32, ...)
  * DAT_xxxxxxxx globals become g_xxxxxxxx
  * a temporary assigned once from a named call takes that call's name
    (iVar1 = GetActorID(0) -> actorId)

The second readability pass (S0_types_plan -> M2/M3) adds real data names. When
`orchestration/types/merged/` exists this module also:

  * prints `unit->targetUnit` instead of `self->f_1b4` (nested chains resolve
    through the pointed-to class taken from the merged header types);
  * prints `g_titleState` instead of `g_0047bdf8`, and the plain value of a
    literal that is not a data object (InitBss bounds become numbers);
  * uses the merged locals map to rename `iVar2`/`uStack_10`/`argN`;
  * declares a local that is used as an object pointer with its recovered class
    and types the `self` parameter (`Ui_GaugeWindow* self`).

Nothing here is compiled; the bit-matching build keeps using asm/ and src/.

Usage:
    python tools/readable_c.py                       # all functions (multi-process)
    python tools/readable_c.py --stats               # before/after noise counts only
    python tools/readable_c.py --maps DIR --out DIR  # alternate maps/output (demo)
    python tools/readable_c.py --limit 50            # smoke test
"""
from __future__ import annotations

import argparse
import json
import os
import re
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GHIDRA = ROOT / "decomp" / "ghidra"
OUT = ROOT / "decomp" / "readable"
INDEX = GHIDRA / "functions_merged.jsonl"
MAPS = ROOT / "orchestration" / "types" / "merged"
TYPES_DB = ROOT / "orchestration" / "types" / "structs.json"

TYPES = {
    "undefined8": "u64", "undefined4": "u32", "undefined2": "u16", "undefined1": "u8",
    "undefined": "u8", "ulonglong": "u64", "longlong": "s64", "uint": "u32", "ushort": "u16",
    "byte": "u8", "sbyte": "s8", "dword": "u32", "word": "u16", "qword": "u64",
}
TYPE_RX = re.compile(r"\b(" + "|".join(sorted(TYPES, key=len, reverse=True)) + r")\b")
UNNAMED_CALL = re.compile(r"\b(?:FUN|func|thunk_FUN)_([0-9A-Fa-f]{8})\b")
DAT = re.compile(r"\bDAT_([0-9a-fA-F]{8})\b")
GLOBAL = re.compile(r"\bg_([0-9a-fA-F]{8})\b")
TEMP = re.compile(r"\b(?:[a-z]{1,3}Var\d+|in_[a-z0-9]+|extraout_[a-z0-9_]+)\b")
PARAM = re.compile(r"\bparam_(\d+)\b")
# *(T *)(base + 0xNN) with base an identifier or an already rewritten chain
FIELD = re.compile(r"\*\((?:[A-Za-z_][\w ]*?)\s*\*+\s*\)\(([A-Za-z_]\w*(?:->f_[0-9a-f]+)*) \+ 0x([0-9a-f]+)\)")
FIELD0 = re.compile(r"\*\((?:[A-Za-z_][\w ]*?)\s*\*+\s*\)([A-Za-z_]\w*(?:->f_[0-9a-f]+)+)\b")
ADDR = re.compile(r"\(([A-Za-z_]\w*(?:->f_[0-9a-f]+)*) \+ 0x([0-9a-f]+)\)")
ADDR_ARG = re.compile(r"([(,]\s*)([A-Za-z_]\w*(?:->f_[0-9a-f]+)*) \+ 0x([0-9a-f]+)(?=\s*[,)])")
CHAIN = re.compile(r"\b([A-Za-z_]\w*)((?:->f_[0-9a-f]+)+)\b")
DECL_LINE = re.compile(r"^  ([A-Za-z_]\w*)\s+(\*+)\s*([A-Za-z_]\w*)\s*;$", re.M)
NOISE = {
    "unnamed calls": UNNAMED_CALL,
    "param_N": PARAM,
    "temporaries": TEMP,
    "placeholder types": TYPE_RX,
    "pointer arithmetic fields": re.compile(r"\*\([\w ]+\*+\)\(\w+ \+ 0x[0-9a-f]+\)"),
    "DAT_ globals": DAT,
    "unresolved fields (f_NNN)": re.compile(r"->f_[0-9a-f]+"),
    "unresolved globals (g_XXXXXXXX)": re.compile(r"\bg_[0-9a-f]{8}\b"),
}
C_KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long",
    "register", "restrict", "return", "short", "signed", "sizeof", "static", "struct",
    "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
    "self", "this", "new", "class", "delete",
}
SCALAR_TYPES = {"u8", "u16", "u32", "u64", "s8", "s16", "s32", "s64", "f32", "f64",
                "int", "uint", "char", "short", "long", "float", "double", "bool",
                "undefined", "code", "byte", "dword", "word", "qword", "size_t"}


# --------------------------------------------------------------------------- #
# maps (second pass)
# --------------------------------------------------------------------------- #
def load_maps(directory: Path | None = None) -> dict:
    """Load the merged type/global/local maps, or empty maps when absent."""
    directory = directory or MAPS
    maps = {"fields": {}, "globals": {}, "literals": {}, "locals": {},
            "functions": {}, "function_by_address": {}, "types": {}, "loaded": False}
    if not directory.is_dir():
        return maps
    fields_path = directory / "fields.json"
    globals_path = directory / "globals.json"
    locals_path = directory / "locals.json"
    functions_path = directory / "functions.json"
    try:
        if fields_path.is_file():
            data = json.loads(fields_path.read_text(encoding="utf-8"))
            maps["fields"] = data.get("classes") or {}
            maps["functions"] = data.get("functions") or {}
            maps["loaded"] = bool(maps["fields"])
        if functions_path.is_file():
            data = json.loads(functions_path.read_text(encoding="utf-8"))
            maps["functions"] = data.get("functions") or maps["functions"]
        if globals_path.is_file():
            data = json.loads(globals_path.read_text(encoding="utf-8"))
            maps["globals"] = data.get("globals") or {}
            for literal, address in (data.get("literals") or {}).items():
                entry = maps["globals"].get(address)
                if entry:
                    maps["literals"][int(literal, 16)] = entry
        if locals_path.is_file():
            data = json.loads(locals_path.read_text(encoding="utf-8"))
            maps["locals"] = data.get("functions") or {}
        for cls in maps["fields"].values():
            if cls.get("type"):
                maps["types"][cls["type"]] = cls
        maps["function_by_address"] = {}
        for entry in (maps.get("functions") or {}).values():
            if not isinstance(entry, dict):
                continue
            try:
                maps["function_by_address"][int(str(entry["address"]), 16)] = entry
            except (KeyError, TypeError, ValueError):
                continue
    except (OSError, ValueError):
        return {"fields": {}, "globals": {}, "literals": {}, "locals": {},
                "functions": {}, "function_by_address": {}, "types": {}, "loaded": False}
    return maps


def class_by_type(maps: dict, type_name: str) -> str | None:
    cls = maps["types"].get(type_name)
    return cls.get("type") if cls else None


_DEFAULT_MAPS: dict | None = None


def default_maps() -> dict:
    """Maps used when a caller (e.g. merge_names.py) does not pass them."""
    global _DEFAULT_MAPS
    if _DEFAULT_MAPS is None:
        _DEFAULT_MAPS = load_maps()
    return _DEFAULT_MAPS


def rewrite_global_refs(text: str, maps: dict) -> str:
    """Replace `g_00123456` literal slots by the real object name.

    This export labels the literal-pool *slot*; the literal's value is either the
    address of a named data object or a plain number.  Named objects print as
    `g_name` (array/address use) or `g_name` after dereference; a plain number
    prints as hex so `InitBss` reads `0x008398E4` instead of a fake global.
    """
    literals = maps["literals"]
    if not literals:
        return text

    def name_for(lit: int) -> dict | None:
        return literals.get(lit)

    # `*(T *)g_LIT` / `**g_LIT` -> the object itself (header type is authoritative)
    def deref(m: re.Match) -> str:
        lit = int(m.group("lit"), 16)
        entry = name_for(lit)
        if entry:
            return entry["name"]
        return m.group(0)

    text = re.sub(r"\*+\s*(?:\(\s*[A-Za-z_]\w*\s*\*+\s*\)\s*)?g_(?P<lit>[0-9a-f]{8})\b", deref, text)

    def bare(m: re.Match) -> str:
        lit = int(m.group(1), 16)
        entry = name_for(lit)
        if entry:
            if entry.get("is_array") or entry.get("access") == "deref":
                return entry["name"]
            return "&" + entry["name"]
        return m.group(0)

    return GLOBAL.sub(bare, text)


def resolve_number_literals(text: str) -> str:
    """Show the value of a `.text` literal that is not a data object."""
    # `&g_LIT` would leave a dangling `&` once the literal becomes a number.
    pattern = re.compile(r"(&\s*)?g_([0-9a-f]{8})\b")

    def one(m: re.Match) -> str:
        literal = int(m.group(2), 16)
        if section_of(literal) != "text":
            return m.group(0)
        try:
            value = word_at(literal)
        except OSError:
            return m.group(0)
        if value is None:
            return m.group(0)
        return f"0x{value:08X}"
    return pattern.sub(one, text)


_IMAGE: bytes | None = None


def image() -> bytes:
    global _IMAGE
    if _IMAGE is None:
        _IMAGE = (ROOT / "original" / "exefs" / "code.decompressed.bin").read_bytes()
    return _IMAGE


def word_at(address: int) -> int | None:
    offset = address - 0x00100000
    data = image()
    if 0 <= offset <= len(data) - 4:
        import struct as _struct
        return _struct.unpack_from("<I", data, offset)[0]
    return None


def section_of(address: int | None) -> str:
    if address is None:
        return "outside"
    if 0x00100000 <= address < 0x0072403C:
        return "text"
    if 0x00725000 <= address < 0x0079AA18:
        return "rodata"
    if 0x0079B000 <= address < 0x007C2D24:
        return "data"
    if 0x007C3000 <= address < 0x00839BC0:
        return "bss"
    return "outside"


def rewrite_chain(match: re.Match, cls: str | None, var_class: dict[str, str],
                  maps: dict) -> str:
    base, chain = match.group(1), match.group(2)
    current = cls if base in ("self", "this") else var_class.get(base)
    if not current or current not in maps["fields"]:
        return match.group(0)
    resolved = []
    changed = False
    for off_text in re.findall(r"->f_([0-9a-f]+)", chain):
        if not current:
            resolved.append(f"->f_{off_text}")
            continue
        fields = maps["fields"].get(current, {}).get("fields") or {}
        field = fields.get(str(int(off_text, 16)))
        if not field:
            resolved.append(f"->f_{off_text}")
            current = None
            continue
        resolved.append("->" + field["name"])
        changed = True
        current = field.get("type_class")
    return base + "".join(resolved) if changed else match.group(0)


def rewrite_fields(text: str, func: dict | None, maps: dict) -> str:
    """Resolve `->f_NNN` chains using the class layout and field pointer types."""
    if not maps["fields"]:
        return text
    cls = None
    if func:
        cls = maps["functions"].get(func["name"], {}).get("class")
    var_class: dict[str, str] = {}
    for base_type, stars, var in DECL_LINE.findall(text):
        if stars and base_type in maps["types"]:
            var_class[var] = maps["types"][base_type].get("type")
    # Ghidra often declares an object pointer as `int iVar4` and then writes
    # `iVar4->f_430`.  If every offset used through the variable exists in the
    # function's own class, it really is that object pointer.
    if cls:
        for var, count in collections_counter(re.findall(r"\b([A-Za-z_]\w*)->f_", text)).items():
            if var in var_class:
                continue
            offsets = {int(x, 16) for x in re.findall(rf"\b{re.escape(var)}->f_([0-9a-f]+)", text)}
            fields = maps["fields"].get(cls, {}).get("fields") or {}
            if offsets and all(str(off) in fields for off in offsets):
                var_class[var] = cls
    text = CHAIN.sub(lambda m: rewrite_chain(m, cls, var_class, maps), text)
    # declare those recovered object pointers with their real class
    def redeclare(m: re.Match) -> str:
        base_type, stars, var = m.group(1), m.group(2), m.group(3)
        if stars or base_type not in SCALAR_TYPES:
            return m.group(0)
        cls_name = var_class.get(var)
        if not cls_name:
            return m.group(0)
        return f"  {cls_name} *{var};"
    return DECL_LINE.sub(redeclare, text)


def collections_counter(values):
    out: dict[str, int] = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return out


def split_code_comment(text: str):
    """Yield (is_code, chunk) so renames never touch comments or strings."""
    token = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    position = 0
    for match in token.finditer(text):
        if match.start() > position:
            yield True, text[position:match.start()]
        yield False, match.group(0)
        position = match.end()
    if position < len(text):
        yield True, text[position:]


def apply_local_map(text: str, mapping: dict, function: dict | None = None) -> str:
    """Rename whole tokens from a V_### map outside comments and strings."""
    if not mapping:
        return text
    taken = set(re.findall(r"\b[A-Za-z_]\w*\b", text))
    rename = {}
    for old, new in mapping.items():
        if old not in taken:
            continue
        if not re.fullmatch(r"[A-Za-z_]\w*", str(new)) or new in C_KEYWORDS:
            continue
        if new in taken and new != old:
            continue
        rename[old] = str(new)
    if not rename:
        return text
    out = []
    for is_code, chunk in split_code_comment(text):
        if is_code:
            for old, new in rename.items():
                chunk = re.sub(rf"\b{re.escape(old)}\b", new, chunk)
        out.append(chunk)
    return "".join(out)


def retype_self(text: str, func: dict, maps: dict) -> str:
    """Type the first parameter (`self`) with the recovered class, if scalar."""
    if not maps["functions"] or not func:
        return text
    cls = maps["functions"].get(func["name"], {}).get("class")
    if not cls:
        return text
    type_name = maps["fields"].get(cls, {}).get("type")
    if not type_name:
        return text
    comment = re.match(r"/\*.*?\*/", text, re.S)
    prefix_end = comment.end() if comment else 0
    code_text = text[prefix_end:]
    head, sep, body = code_text.partition("{")
    if not sep:
        return text
    m = re.search(r"(\()\s*([A-Za-z_]\w*)\s+(\*+\s*)?(self|param_1)\b", head)
    if not m:
        return text
    base_type, stars = m.group(2), (m.group(3) or "").strip()
    if stars or base_type not in SCALAR_TYPES or base_type in maps["types"]:
        return text
    new_head = head[:m.start(2)] + f"{type_name} *" + head[m.start(4):]
    new_code = new_head + sep + body
    if comment:
        signature = " ".join(new_head.split())
        prefix = text[:prefix_end]
        # keep the doc header in sync so the reader sees the same prototype
        prefix = re.sub(r" \* Signature: [^\n]*",
                        " * Signature: " + signature.replace("\\", "\\\\"), prefix)
        return prefix + new_code
    return new_code


def load_names() -> dict[int, str]:
    names = {}
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if not re.match(r"^(func_|FUN_)", row["name"]):
            names[int(row["address"], 16)] = row["name"]
    return names


def camel(name: str) -> str:
    for prefix in ("Get", "get_"):
        if name.startswith(prefix) and len(name) > len(prefix) + 1:
            name = name[len(prefix):]
            break
    name = re.sub(r"_+([a-zA-Z0-9])", lambda m: m.group(1).upper(), name)
    out = name[0].lower() + name[1:]
    # ActorID -> actorId reads better as a variable
    return re.sub(r"ID\b", "Id", out)


def rewrite(text: str, names: dict[int, str], maps: dict | None = None,
            func: dict | None = None) -> str:
    if maps is None:
        maps = default_maps()
    if maps and maps.get("loaded") and func is None:
        m = re.search(r"Address:\s*([0-9a-fA-F]{8})", text) or \
            re.search(r"\bFUN_([0-9A-Fa-f]{8})\b", text)
        if m:
            func = maps.get("function_by_address", {}).get(int(m.group(1), 16))
    if not maps:
        maps = {"fields": {}, "globals": {}, "literals": {}, "locals": {},
                "functions": {}, "function_by_address": {}, "types": {}}

    def call(m: re.Match) -> str:
        addr = int(m.group(1), 16)
        return names.get(addr, f"func_{addr:08X}")

    text = UNNAMED_CALL.sub(call, text)
    text = DAT.sub(lambda m: f"g_{m.group(1).lower()}", text)
    text = TYPE_RX.sub(lambda m: TYPES[m.group(1)], text)

    # self: param_1 when it is used as an object (several field accesses)
    if len(re.findall(r"\(param_1 \+ 0x[0-9a-f]+\)", text)) >= 2:
        text = re.sub(r"\bparam_1\b", "self", text)
    text = PARAM.sub(lambda m: f"arg{m.group(1)}", text)

    # A method's first parameter is the object even when it is only passed by
    # address (`F(..., self + 0x4c, ...)`) and Ghidra never prints `self->`.
    func_cls = None
    if func:
        func_cls = (maps["functions"].get(func["name"]) or {}).get("class")
    first_param = None
    if func_cls:
        code_only = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        sig = code_only.split("{", 1)[0]
        sm = re.search(r"\(\s*[^,()]*?\b([A-Za-z_]\w*)\s*(?:,|\))", sig, re.S)
        if sm:
            first_param = sm.group(1)
        if first_param in ("arg1", "param_1"):
            text = re.sub(rf"\b{re.escape(first_param)}\b", "self", text)
            first_param = "self"

    # struct fields, innermost first, until stable
    for _ in range(8):
        new = FIELD.sub(lambda m: f"{m.group(1)}->f_{m.group(2)}", text)
        new = FIELD0.sub(lambda m: f"*{m.group(1)}", new)
        if new == text:
            break
        text = new
    objects = set(re.findall(r"\b([A-Za-z_]\w*)->f_", text))
    if first_param:
        objects.add(first_param)
    text = ADDR.sub(lambda m: f"&{m.group(1)}->f_{m.group(2)}" if m.group(1).split("->")[0] in objects else m.group(0), text)
    # the same inside argument lists, where Ghidra drops the parentheses: f(self + 0x254, ...)
    text = ADDR_ARG.sub(
        lambda m: f"{m.group(1)}&{m.group(2)}->f_{m.group(3)}" if m.group(2).split("->")[0] in objects else m.group(0), text)

    # second pass: real field names, global names, locals (no-op without maps)
    text = rewrite_fields(text, func, maps)
    if maps.get("literals"):
        text = rewrite_global_refs(text, maps)
        text = resolve_number_literals(text)
    if maps.get("locals") and func:
        entry = maps["locals"].get(func["name"]) or {}
        local_map = dict(entry.get("params") or {})
        local_map.update(entry.get("locals") or {})
        text = apply_local_map(text, local_map, func)
    if maps.get("functions") and func:
        text = retype_self(text, func, maps)

    # temporaries: name them by what they hold
    taken = set(re.findall(r"\b[A-Za-z_]\w*\b", text))

    def rename(var: str, new_name: str) -> None:
        nonlocal text
        if new_name in taken or not new_name.isidentifier():
            return
        taken.add(new_name)
        text = re.sub(rf"\b{var}\b", new_name, text)

    def assigned_once(var: str) -> bool:
        return len(re.findall(rf"(?<![=!<>])\b{var} = ", text)) == 1

    # ... from a named call: iVar1 = GetActorID(0) -> actorId
    for var, callee in re.findall(r"\b([a-z]{1,3}Var\d+) = (?:\([\w ]+\*?\))?([A-Z][A-Za-z0-9_]+)\(", text):
        if assigned_once(var) and not callee.startswith("func_"):
            rename(var, camel(callee))
    # ... the one value a function returns
    returned = set(re.findall(r"\breturn ([a-z]{1,3}Var\d+);", text))
    if len(returned) == 1:
        rename(returned.pop(), "result")
    # ... loop counters: incremented by one and compared inside a loop condition
    counters = [v for v in dict.fromkeys(re.findall(r"\b([a-z]{1,3}Var\d+) = \1 \+ 1;", text))
                if re.search(rf"(?:while|for) \([^;)]*\b{v}\b", text) or re.search(rf"\}} while \([^)]*\b{v}\b", text)]
    for var, short in zip(counters, ("i", "j", "k", "n", "m")):
        rename(var, short)
    # ... a field loaded once: iVar2 = self->f_274 -> f274
    for var, field in re.findall(r"\b([a-z]{1,3}Var\d+) = (?:\([\w ]+\*?\))?\w+(?:->f_[0-9a-f]+)*->f_([0-9a-f]+);", text):
        if assigned_once(var):
            rename(var, f"f{field}")
    return text


def noise(text: str) -> dict[str, int]:
    return {k: len(rx.findall(text)) for k, rx in NOISE.items()}


def call_graph(files: list[Path], names: dict[int, str]) -> tuple[dict, dict]:
    by_name = {v: k for k, v in names.items()}
    callers: dict[str, set[str]] = {}
    callees: dict[str, set[str]] = {}
    for f in files:
        own = f.stem.rsplit("_", 1)[0]
        text = f.read_text(encoding="utf-8", errors="replace")
        body = text.split("{", 1)[1] if "{" in text else ""
        found = set()
        for m in UNNAMED_CALL.finditer(body):
            n = names.get(int(m.group(1), 16))
            if n:
                found.add(n)
        for n in re.findall(r"\b([A-Z][A-Za-z0-9_]{2,})\(", body):
            if n in by_name:
                found.add(n)
        found.discard(own)
        callees[f.name] = found
        for n in found:
            callers.setdefault(n, set()).add(own)
    return callers, callees


_CTX: dict = {}


def _init_context(names, callers, callees, maps, out_root, functions, functions_by_name):
    _CTX.update(names=names, callers=callers, callees=callees, maps=maps,
                out_root=out_root, functions=functions,
                functions_by_name=functions_by_name)


def _work(rel: str):
    names = _CTX["names"]
    callers = _CTX["callers"]
    callees = _CTX["callees"]
    maps = _CTX["maps"]
    src = GHIDRA / rel
    text = src.read_text(encoding="utf-8", errors="replace")
    func = None
    if maps.get("loaded"):
        m = re.search(r"_([0-9a-fA-F]{8})\.c$", src.name)
        if m:
            func = _CTX["functions"].get(int(m.group(1), 16))
        if func is None:
            func = _CTX["functions_by_name"].get(src.stem.rsplit("_", 1)[0])
    out = rewrite(text, names, maps, func)
    own = src.stem.rsplit("_", 1)[0]
    named_callers = sorted(c for c in callers.get(own, ()) if not c.startswith("func_"))
    header = [
        "/* Readable view (tools/readable_c.py) of " + rel.replace("\\", "/") + " - read-only pseudo-C.",
        " * self = first argument used as an object; f_XXX = field at offset 0xXXX;",
        " * func_XXXXXXXX = function not named yet; g_XXXXXXXX = global at that address.",
    ]
    if maps.get("loaded"):
        header.append(" * Typed view: field/global/local names from orchestration/types/merged "
                      "(M2_types_merge / M3_vars_merge); confidence is in include/dqxi/*.h.")
    if named_callers:
        header.append(" * Called by: " + ", ".join(named_callers[:12]) + (" ..." if len(named_callers) > 12 else ""))
    if callees.get(src.name):
        header.append(" * Calls: " + ", ".join(sorted(callees[src.name])[:12]))
    header.append(" */")
    dst = Path(_CTX["out_root"]) / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(header) + "\n" + out, encoding="utf-8")
    return noise(text), noise(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stats", action="store_true", help="print before/after noise counts")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--maps", type=Path, default=MAPS, help="merged type map directory")
    ap.add_argument("--out", type=Path, default=OUT, help="output tree (default decomp/readable)")
    ap.add_argument("--no-types", action="store_true", help="ignore the merged maps")
    ap.add_argument("--limit", type=int, help="process only the first N functions")
    args = ap.parse_args()

    maps = {"fields": {}, "globals": {}, "literals": {}, "locals": {},
            "functions": {}, "types": {}, "loaded": False} if args.no_types else load_maps(args.maps)
    names = load_names()
    functions_by_address: dict[int, dict] = {}
    functions_by_name: dict[str, dict] = {}
    for entry in (maps.get("functions") or {}).values():
        if not isinstance(entry, dict):
            continue
        try:
            functions_by_address[int(str(entry["address"]), 16)] = entry
        except (KeyError, TypeError, ValueError):
            continue
        functions_by_name[entry["name"]] = entry
    files = sorted((GHIDRA / "functions").glob("*.c"))
    # Entry points recovered in the second Ghidra pass (overlapping/jump-table
    # code) have their own tree; mirror it too so every decompiled function has a
    # readable view and the naming batches can link to it.
    recovered = GHIDRA / "recovered"
    if recovered.is_dir():
        files += sorted(recovered.glob("*.c"))
    if args.limit:
        files = files[:args.limit]
    callers, callees = call_graph(files, names)
    jobs = [str(f.relative_to(GHIDRA)) for f in files]
    before: dict[str, int] = {}
    after: dict[str, int] = {}
    with ProcessPoolExecutor(max_workers=args.workers, initializer=_init_context,
                             initargs=(names, callers, callees, maps, str(args.out),
                                       functions_by_address, functions_by_name)) as pool:
        for b, a in pool.map(_work, jobs, chunksize=64):
            for k in b:
                before[k] = before.get(k, 0) + b[k]
                after[k] = after.get(k, 0) + a[k]
    print(f"wrote {len(files)} readable functions -> {args.out}")
    if maps.get("loaded"):
        print(f"types: {len(maps['fields'])} classes, {len(maps['globals'])} globals, "
              f"{len(maps['locals'])} local maps from {args.maps}")
    report = {"functions": len(files), "named_functions": len(names),
              "typed": bool(maps.get("loaded")), "maps": str(args.maps),
              "before": before, "after": after}
    for k in before:
        print(f"  {k:32} {before[k]:8} -> {after[k]:8}")
    report_path = ROOT / "audit" / "READABLE_C.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
