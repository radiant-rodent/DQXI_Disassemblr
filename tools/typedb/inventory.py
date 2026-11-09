#!/usr/bin/env python3
"""Collect evidence for globals (``G_###``) and local variables (``V_###``).

The struct/class recovery in :mod:`tools.typedb.struct_db` answers "what layout
does this object have".  This module answers the two remaining questions of the
readability pass:

* **globals** - which ``g_XXXXXXXX`` / ``DAT_XXXXXXXX`` address does which
  function use, in what width, and what does the value look like in the retail
  image (string, vtable, pointer, plain integer, array)?  That is what a ``G_###``
  worker needs to give the address a real name and type.
* **locals** - for every function, which variables exist, how are they used
  (loop counter, return value, object pointer, field holder, call result,
  argument to a specific call) and what type does the declaration have?  That is
  what a ``V_###`` worker needs to rename ``iVar2`` to ``partyCount``.

Nothing here invents a name.  Every record is an observation plus a confidence
for the *type guess only*; names come from the worker batches.

Outputs (both UTF-8, read back strictly):

    orchestration/types/globals.json   ({stats, globals:[...]})
    orchestration/types/locals.json    ({stats, functions:[...]})

Usage:
    python tools/typedb/inventory.py                # full run
    python tools/typedb/inventory.py --limit 300    # smoke test
    python tools/typedb/inventory.py --only globals # one half
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.typedb.common import (  # noqa: E402
    BSS, DATA, ROOT, RODATA, TEXT, TYPES_DIR, bytes_at, c_string, hex_addr,
    is_text_pointer, load_rows, pointer_array, readable_path, role_of,
    section_of, strip_comments, strip_maybe, subsystem_of, type_width, word_at,
)

# --------------------------------------------------------------------------- #
# patterns
# --------------------------------------------------------------------------- #
GLOBAL = re.compile(r"\b(?:g_|DAT_)([0-9a-fA-F]{8})\b")
G_CAST = re.compile(r"\(\s*([A-Za-z_]\w*)\s*(\*+)\s*\)\s*&?(?:g_|DAT_)[0-9a-fA-F]{8}")
G_DEREF = re.compile(r"(\*+)\s*(?:\(\s*[A-Za-z_]\w*\s*\*+\s*\)\s*)?(?:g_|DAT_)[0-9a-fA-F]{8}")
G_TAKE_ADDR = re.compile(r"&\s*(?:g_|DAT_)[0-9a-fA-F]{8}")
G_ARRAY = re.compile(r"(?:g_|DAT_)([0-9a-fA-F]{8})\s*\+\s*(0x[0-9a-f]+)")
G_INDEX = re.compile(r"(?:g_|DAT_)([0-9a-fA-F]{8})\s*\[\s*(0x[0-9a-f]+|\d+)\s*\]")
SIG_END = re.compile(r"\)\s*\{")
DECL = re.compile(r"^  ([A-Za-z_]\w*)\s+((?:\*\s*)*)\s*([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*;", re.M)
CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
FIELD = re.compile(r"\b([A-Za-z_]\w*)\s*(?:->f_([0-9a-f]+))")
OFFSET = re.compile(r"\(?\b([A-Za-z_]\w*)\s*\+\s*0x([0-9a-f]+)\b")
LOOP_INC = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*\1\s*\+\s*1\s*;")
CONST_COMPARE = re.compile(r"\b([A-Za-z_]\w*)\s*(?:==|!=|<=|>=|<<|>>|<|>)\s*(0x[0-9a-f]+|\d+)")
CONTROL = {"if", "while", "for", "switch", "return", "sizeof", "do", "else"}

PLACEHOLDER_VAR = re.compile(
    r"^(?:[a-z]{1,3}Var\d+|local_[0-9a-f]+|uStack_[0-9a-f]+|iStack_[0-9a-f]+|"
    r"in_[a-z0-9]+|extraout_[a-z0-9_]+|unaff_[a-z0-9]+|arg\d+|param_\d+|self)$"
)
NOISE_NAMES = {"self"}


# --------------------------------------------------------------------------- #
# global analysis
# --------------------------------------------------------------------------- #
# IMPORTANT: this export labels the *literal pool slot* in .text, not the data
# object.  `DAT_00160900` means "the 32-bit literal stored at 0x00160900", and
# that literal usually holds the address of the real global (0x007BE330).  A
# literal whose value is not a data address is a numeric/enum constant, not a
# variable, and is skipped here (readable_c.py renders it as a plain number).
_KIND_CACHE: dict[int, dict] = {}


def resolve_global(literal: int) -> int | None:
    """Real data address referenced by a Ghidra ``DAT_`` symbol, or None.

    * in ``.rodata``/``.data``/``.bss``: the symbol already is the object;
    * in ``.text``: it is a literal-pool slot - read the word and, when that word
      points into a data section, that is the object;
    * anything else (small integers, ``DAT_00000001``) is a constant.
    """
    section = section_of(literal)
    if section in ("rodata", "data", "bss"):
        return literal
    if section != "text":
        return None
    value = word_at(literal)
    if value is None:
        return None
    return value if section_of(value) in ("rodata", "data", "bss") else None


def global_kind(address: int) -> dict:
    """What the retail image says about a data address (never a name)."""
    if address in _KIND_CACHE:
        return _KIND_CACHE[address]
    section = section_of(address)
    info = {
        "section": section,
        "value": None,
        "string": None,
        "vtable": None,
        "pointee_string": None,
        "pointer": False,
    }
    word = word_at(address)
    if word is None:
        _KIND_CACHE[address] = info       # .bss: zero-initialised, no bytes
        return info
    info["value"] = hex_addr(word)
    if section in ("rodata", "data") and word == 0:
        info["value"] = "0x00000000"
    text = c_string(address)
    if text:
        info["string"] = text[:120]
        _KIND_CACHE[address] = info
        return info
    if is_text_pointer(word):
        slots = pointer_array(word, 4)
        if len(slots) >= 2:
            info["vtable"] = hex_addr(word)
        else:
            info["pointer"] = True
            info["value"] = hex_addr(word) + " (code)"
    elif section_of(word) in ("rodata", "data", "bss"):
        info["pointer"] = True
        pointee = c_string(word, 96)
        if pointee:
            info["pointee_string"] = pointee[:120]
        else:
            info["value"] = hex_addr(word) + " (data)"
    _KIND_CACHE[address] = info
    return info


IMMEDIATE_CAST = re.compile(r"\(\s*([A-Za-z_]\w*)\s*(\*+)\s*\)\s*$")


def classify_global(code: str, start: int, end: int) -> dict:
    """Width / access mode of one global reference.

    ``deref``  - the global itself is read/written (``*(u32 *)g_...``, ``*g_...``);
    ``address``- the address is used as a base (``g_... + 0x10``, ``g_...[i]``)
                 or loaded into a pointer variable.
    """
    before = code[max(0, start - 60):start]
    after = code[end:end + 70]
    cast = IMMEDIATE_CAST.search(before)
    deref = bool(re.search(r"\*+\s*$", before if not cast else before[:cast.start()]))
    addr_taken = bool(re.search(r"&\s*$", before if not cast else before[:cast.start()]))
    width = 4
    signed = False
    pointer = False
    if cast:
        base, stars = cast.group(1), cast.group(2)
        width = type_width(base)
        pointer = len(stars) >= 2
        signed = base in ("int", "short", "schar", "char", "ssize_t")
    elif deref:
        width = 1                     # Ghidra inferred a byte/char type
    if addr_taken or re.match(r"\s*(?:\+|\[)", after):
        deref = False                 # address of the object / element base
    mode = "deref" if deref else "address"
    return {"mode": mode, "width": width, "signed": signed, "pointer": pointer,
            "address_taken": addr_taken}


def scan_function_globals(row: dict, code: str) -> dict[int, dict]:
    """All real globals referenced in one readable function, with local evidence."""
    found: dict[int, dict] = {}
    for m in GLOBAL.finditer(code):
        literal = int(m.group(1), 16)
        address = resolve_global(literal)
        if address is None:
            continue
        guess = classify_global(code, m.start(), m.end())
        entry = found.setdefault(address, {
            "address": address, "uses": 0,
            "widths": collections.Counter(), "types": collections.Counter(),
            "literals": set(), "modes": collections.Counter(),
            "samples": [], "array_max": 0, "stores": [],
            "deref": False, "address_taken": False,
        })
        entry["uses"] += 1
        entry["deref"] = entry["deref"] or guess["mode"] == "deref"
        entry["address_taken"] = entry["address_taken"] or guess["address_taken"]
        entry["widths"][guess["width"]] += 1
        entry["modes"][guess["mode"]] += 1
        entry["literals"].add(literal)
        if guess["pointer"]:
            entry["types"]["void*"] += 1
        elif guess["signed"]:
            entry["types"]["s32" if guess["width"] == 4 else
                         {1: "s8", 2: "s16"}.get(guess["width"], "s32")] += 1
        else:
            entry["types"]["u32" if guess["width"] == 4 else
                         {1: "u8", 2: "u16", 8: "u64"}.get(guess["width"], "u32")] += 1
        arr = G_ARRAY.match(code, m.start())
        if arr and int(arr.group(2), 16) < 0x100000:
            entry["array_max"] = max(entry["array_max"], int(arr.group(2), 16) + 4)
        idx = G_INDEX.match(code, m.start())
        if idx:
            value = int(idx.group(2), 16) if idx.group(2).lower().startswith("0x") else int(idx.group(2))
            entry["array_max"] = max(entry["array_max"], value * 4 + 4)
        if len(entry["samples"]) < 3:
            line_start = code.rfind("\n", 0, m.start()) + 1
            line_end = code.find("\n", m.start())
            entry["samples"].append(code[line_start:line_end if line_end >= 0 else len(code)].strip()[:200])
        tail = code[m.end():m.end() + 60]
        store = re.match(r"\s*(?:\[[^\]]+\])?\s*=\s*([^;]{1,60});", tail)
        if store and len(entry["stores"]) < 3:
            entry["stores"].append(store.group(1).strip()[:80])
    return found


# --------------------------------------------------------------------------- #
# local variable analysis
# --------------------------------------------------------------------------- #
def parse_signature(text: str) -> tuple[str, str, list[dict]]:
    """Return (return type, function name, parameters) of the readable C."""
    head = text.split("{", 1)[0]
    head = strip_comments(head)
    m = re.search(r"([A-Za-z_][\w \t*]*?)\b([A-Za-z_]\w*)\s*\(([^;]*)\)\s*$", head.strip(), re.S)
    if not m:
        return "", "", []
    raw = m.group(3).strip()
    params: list[dict] = []
    if raw and raw != "void":
        depth, current = 0, ""
        for ch in raw:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
            if ch == "," and depth == 0:
                params.append(current)
                current = ""
            else:
                current += ch
        params.append(current)
    out = []
    for item in params:
        item = item.strip()
        pm = re.match(r"(.+?)\s*\b([A-Za-z_]\w*)\s*$", item)
        if not pm:
            continue
        ptype = pm.group(1).strip()
        out.append({"name": pm.group(2), "type": ptype, "pointer": "*" in ptype,
                    "width": 4 if "*" in ptype else type_width(re.sub(r"[*\s]", "", ptype))})
    return m.group(1).strip(), m.group(2), out


def enclosing_call(body: str, position: int, limit: int = 400) -> str | None:
    """Name of the call whose argument list contains ``position``, if any."""
    depth = 0
    i = position - 1
    stop = max(0, position - limit)
    while i > stop:
        ch = body[i]
        if ch == ")":
            depth += 1
        elif ch == "(":
            if depth == 0:
                m = re.search(r"([A-Za-z_]\w*)\s*$", body[max(0, i - 60):i])
                if m and m.group(1) not in CONTROL:
                    return m.group(1)
                return None
            depth -= 1
        elif ch == ";" and depth == 0:
            return None
        i -= 1
    return None


def var_usage(code: str, name: str, decl_span: tuple[int, int]) -> dict:
    """How a local/parameter is used: reads, writes, calls, fields, constants."""
    body = code[:decl_span[0]] + " " * (decl_span[1] - decl_span[0]) + code[decl_span[1]:]
    reads = writes = 0
    calls = collections.Counter()
    fields = collections.Counter()
    offsets = collections.Counter()
    constants = collections.Counter()
    assignments: list[str] = []
    # Whole-word match. A previous draft stored a literal backspace here
    # (an escaped word boundary written to disk as 0x08), which made every
    # variable look unused. It must stay a regex word boundary.
    token = re.compile(rf"\b{re.escape(name)}\b")
    for m in token.finditer(body):
        after = body[m.end():m.end() + 70]
        write = re.match(r"\s*(?:\[[^\]]*\])?\s*(?:[-+*/%&|^]?=)(?!=)", after)
        if write:
            writes += 1
            value = re.match(r"\s*[-+*/%&|^]?=\s*([^;]{1,60});", after)
            if value and len(assignments) < 3:
                assignments.append(value.group(1).strip()[:80])
        else:
            reads += 1
        fm = re.match(r"\s*->f_([0-9a-f]+)", after)
        if fm:
            fields[fm.group(1)] += 1
        om = re.match(r"\s*\+\s*0x([0-9a-f]+)", after)
        if om:
            offsets[om.group(1)] += 1
        cm = CONST_COMPARE.match(body, m.start())
        if cm:
            constants[cm.group(2)] += 1
        callee = enclosing_call(body, m.start())
        if callee and not write:
            calls[callee] += 1
    loop = bool(LOOP_INC.search(body) and re.search(
        rf"\b{re.escape(name)}\b", LOOP_INC.search(body).group(0)))
    pointer_use = bool(re.search(rf"\*\s*{re.escape(name)}\b|\b{re.escape(name)}\s*\[", body))
    returned = bool(re.search(rf"\breturn\s+{re.escape(name)}\s*;", body))
    hint = ""
    if loop:
        hint = "loop counter"
    elif returned and reads <= 2:
        hint = "return value"
    elif fields:
        hint = "object/struct pointer (fields at " + ", ".join(
            "0x" + f for f, _ in fields.most_common(4)) + ")"
    elif assignments:
        hint = "assigned from " + assignments[0]
    elif calls:
        hint = "argument to " + calls.most_common(1)[0][0]
    elif pointer_use:
        hint = "pointer"
    return {"reads": reads, "writes": writes, "hint": hint,
            "calls": [c for c, _ in calls.most_common(3)],
            "fields": [f for f, _ in fields.most_common(6)],
            "offsets": [f for f, _ in offsets.most_common(4)],
            "constants": [c for c, _ in constants.most_common(3)],
            "assignments": assignments}


def analyse_function(row: dict, cls: dict | None) -> dict | None:
    path = readable_path(row)
    if path is None:
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    code = strip_comments(text)
    return_type, fn_name, params = parse_signature(code)
    if not fn_name:
        return None
    decls = {}
    for m in DECL.finditer(code):
        base, stars, var, array = m.group(1), m.group(2), m.group(3), m.group(4)
        if var in decls:
            continue
        decls[var] = {
            "name": var,
            "type": base,
            "stars": stars.count("*"),
            "array": array,
            "decl_span": m.span(),
            "is_param": False,
        }
    variables = []
    param_names = {p["name"] for p in params}
    for p in params:
        variables.append({
            "name": p["name"],
            "type": p["type"].replace("*", "").strip(),
            "stars": p["type"].count("*"),
            "array": None,
            "is_param": True,
            "usage": var_usage(code, p["name"], (0, 0)),
        })
    for var, info in decls.items():
        if var in param_names:
            continue
        usage = var_usage(code, var, info["decl_span"])
        variables.append({
            "name": var,
            "type": info["type"],
            "stars": info["stars"],
            "array": info["array"],
            "is_param": False,
            "usage": usage,
        })
    # object pointer fields touched through any variable of this function
    fields = collections.Counter()
    for m in FIELD.finditer(code):
        fields[m.group(2)] += 1
    for m in OFFSET.finditer(code):
        fields[m.group(2)] += 1
    signature = " ".join(code.split("{", 1)[0].split())
    return {
        "name": row["name"],
        "address": hex_addr(row["_address"]),
        "file": row.get("file"),
        "readable": str(path.relative_to(ROOT)).replace("\\", "/"),
        "class": cls["class"] if cls else None,
        "class_type": cls["type"] if cls else None,
        "role": role_of(row["name"]),
        "return_type": return_type,
        "signature": signature,
        "params": [{"name": p["name"], "type": p["type"], "pointer": p["pointer"]} for p in params],
        "variables": variables,
        "fields_used": [[int(f, 16), n] for f, n in fields.most_common(24)],
        "call_count": len([m for m in CALL.finditer(code) if m.group(1) not in CONTROL]),
    }


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
def class_index(structs_path: Path) -> tuple[dict[str, dict], dict[int, dict]]:
    by_name: dict[str, dict] = {}
    by_address: dict[int, dict] = {}
    if not structs_path.is_file():
        return by_name, by_address
    data = json.loads(structs_path.read_text(encoding="utf-8"))
    for cls in data.get("classes") or []:
        by_name[cls["class"]] = {"class": cls["class"], "type": cls["type"]}
        for fn in cls.get("functions") or []:
            addr = fn.get("address")
            if addr:
                by_address[int(addr, 16)] = {"class": cls["class"], "type": cls["type"]}
    return by_name, by_address


def build(limit: int | None, only: str, workers: int = 12) -> tuple[dict, dict]:
    rows = load_rows()
    if limit:
        rows = rows[:limit]
    _, by_address = class_index(TYPES_DIR / "structs.json")

    def one(row):
        return row, analyse_function(row, by_address.get(row["_address"]))

    functions: list[dict] = []
    globals_found: dict[int, dict] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row, result in pool.map(one, rows, chunksize=32):
            if result is None:
                continue
            functions.append(result)
            path = readable_path(row)
            if path is None:
                continue
            code = strip_comments(path.read_text(encoding="utf-8", errors="replace"))
            subsystem = subsystem_of(row["name"])
            for address, entry in scan_function_globals(row, code).items():
                target = globals_found.setdefault(address, {
                    "address": address, "uses": 0,
                    "widths": collections.Counter(), "types": collections.Counter(),
                    "functions": set(), "subsystems": collections.Counter(),
                    "samples": [], "modes": collections.Counter(),
                    "literals": set(), "array_max": 0, "stores": [],
                    "kind": global_kind(address),
                })
                target["uses"] += entry["uses"]
                target["widths"].update(entry["widths"])
                target["types"].update(entry["types"])
                target["modes"].update(entry["modes"])
                target["literals"].update(entry["literals"])
                target["functions"].add(row["name"])
                target["subsystems"][subsystem] += 1
                target["array_max"] = max(target["array_max"], entry["array_max"])
                for sample in entry["samples"]:
                    if len(target["samples"]) < 4 and sample not in target["samples"]:
                        target["samples"].append(sample)
                for store in entry["stores"]:
                    if len(target["stores"]) < 4 and store not in target["stores"]:
                        target["stores"].append(store)

    globals_out = []
    for address in sorted(globals_found):
        entry = globals_found[address]
        kind = entry["kind"]
        widths = entry["widths"] or collections.Counter({4: 1})
        width = max(widths)
        type_guess = entry["types"].most_common(1)[0][0] if entry["types"] else "u32"
        if entry["array_max"] > 8:
            type_guess = {1: "u8", 2: "u16", 4: "u32"}.get(width, "u32")
            type_guess += f"[0x{entry['array_max']:X}]"
        if kind.get("string"):
            type_guess, width = "char[]", 1
        size_hint = None
        for sample in entry["samples"]:
            m = re.search(r"(?:memcpy|memset|Read|Write)\s*\([^;]*?(?:g_|DAT_)[0-9a-fA-F]{8}\s*,"
                          r"[^;]*?(0x[0-9a-f]+)", sample)
            if m:
                size_hint = int(m.group(1), 16)
                break
        comment = ""
        if kind.get("string"):
            comment = "string: " + json.dumps(kind["string"], ensure_ascii=False)
        elif kind.get("pointee_string"):
            comment = "pointer to string: " + json.dumps(kind["pointee_string"], ensure_ascii=False)
        elif kind.get("vtable"):
            comment = "vtable at " + kind["vtable"]
        elif kind.get("value") == "0x00000000":
            comment = "zero-initialised (no data bytes in the retail image)"
        conf = 0.55 if entry["array_max"] <= 8 else 0.45
        if kind.get("string") or kind.get("vtable"):
            conf = 0.8
        globals_out.append({
            "address": hex_addr(address),
            "section": kind.get("section") or section_of(address),
            "width": width,
            "type_guess": type_guess,
            "confidence": round(conf, 2),
            "subsystem": entry["subsystems"].most_common(1)[0][0],
            "use_count": entry["uses"],
            "function_count": len(entry["functions"]),
            "functions": sorted(entry["functions"])[:20],
            "initial_value": kind.get("value"),
            "string": kind.get("string"),
            "pointee_string": kind.get("pointee_string"),
            "vtable": kind.get("vtable"),
            "access": (entry["modes"].most_common(1)[0][0] if entry["modes"] else "deref"),
            "is_array": entry["array_max"] > 8,
            "array_bytes": entry["array_max"] or None,
            "size_hint": size_hint,
            "literals": [hex_addr(v) for v in sorted(entry["literals"])],
            "comment_hint": comment,
            "stores": entry["stores"],
            "samples": entry["samples"],
        })

    by_subsystem = collections.Counter(g["subsystem"] for g in globals_out)
    var_count = sum(len(f["variables"]) for f in functions)
    placeholder = sum(
        1 for f in functions for v in f["variables"]
        if PLACEHOLDER_VAR.match(v["name"]) and v["name"] not in NOISE_NAMES
    )
    stats = {
        "functions": len(functions),
        "globals": len(globals_out),
        "globals_by_subsystem": dict(by_subsystem),
        "globals_by_section": dict(collections.Counter(g["section"] for g in globals_out)),
        "globals_named_by_data": sum(1 for g in globals_out if g["string"] or g["vtable"]),
        "variables": var_count,
        "variables_placeholder": placeholder,
        "variables_per_function": round(var_count / max(1, len(functions)), 2),
        "functions_with_class": sum(1 for f in functions if f["class"]),
    }
    return (
        {"generated_by": "tools/typedb/inventory.py",
         "method": ("Global addresses, widths and initial values are read from the readable C "
                    "and the retail image; local variables come from the declaration block of "
                    "each readable function. Types are evidence-based guesses, names come from "
                    "the G_/V_ batch workers."),
         "stats": stats, "globals": globals_out},
        {"generated_by": "tools/typedb/inventory.py",
         "method": ("One record per readable function: parameters, local declarations and how "
                    "each variable is used (reads/writes, fields, calls, constants). V_ batch "
                    "workers rename these exact tokens."),
         "stats": stats, "functions": functions},
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, help="parse only the first N functions (smoke test)")
    ap.add_argument("--only", choices=("all", "globals", "locals"), default="all")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    globals_doc, locals_doc = build(args.limit, args.only, args.workers)
    stats = globals_doc["stats"]
    print(json.dumps(stats, indent=1))
    TYPES_DIR.mkdir(parents=True, exist_ok=True)
    if args.only in ("all", "globals"):
        out = TYPES_DIR / "globals.json"
        out.write_text(json.dumps(globals_doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        out.read_text(encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KiB)")
    if args.only in ("all", "locals"):
        out = TYPES_DIR / "locals.json"
        # compact separators: ~200k variables, pretty-printing would triple the file
        out.write_text(json.dumps(locals_doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                       encoding="utf-8")
        out.read_text(encoding="utf-8")
        print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KiB)")
    print("  next: python tools/typedb/make_batches.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
