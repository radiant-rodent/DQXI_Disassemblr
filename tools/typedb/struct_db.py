#!/usr/bin/env python3
"""Recover candidate structs/classes from the Ghidra export (evidence first).

Nothing in this file guesses a *name*.  It only observes:

* which function names share a class prefix (``Ui_GaugeWindow_InitPanes`` ->
  class ``Ui_GaugeWindow``) or a recovered parameter type (``UiGaugeWindow``);
* which byte offsets a function touches on its object pointer (``param_1``,
  an alias, or the object a constructor returns);
* the width and kind of each access from the Ghidra cast
  (``*(undefined1 *)`` = 1 byte, ``(code **)`` = function pointer, ...);
* constructors (a store of a vtable pointer at offset 0, calls of a base
  constructor with the same object);
* allocation sizes (``Mem_Alloc*(0x1A0, ...)``);
* vtable contents, resolved through the retail image (the literal-pool word is
  the vtable address, and every slot is a real function address in ``.text``);
* readable-C lines that touch each field, so an ``S_###`` worker sees how the
  field is used instead of only an offset.

The result is ``orchestration/types/structs.json``.  It is a *hypothesis list*:
every entry carries the functions and code lines that justify it, and a
confidence for the layout (not for a name - names come from the S batches).

Usage:
    python tools/typedb/struct_db.py                 # full run
    python tools/typedb/struct_db.py --limit 400     # quick smoke test
    python tools/typedb/struct_db.py --stats         # print, write nothing
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
    BATCH_DIR, GHIDRA, OUT_DIR, READABLE, ROOT, TYPES_DIR, camel_type, c_string,
    hex_addr, is_text_pointer, load_rows, name_tokens, pointer_array, raw_path,
    readable_path, role_of, section_of, strip_comments, strip_maybe, subsystem_of,
    type_width, word_at, write_json,
)

# --------------------------------------------------------------------------- #
# type vocabulary
# --------------------------------------------------------------------------- #
TYPE_DECL = re.compile(r"typedef\s+struct\s+(\w+)\s+\w+\s*;")
SIG_TYPE = re.compile(r"\b([A-Z][A-Za-z0-9_]*)\s*\*")

CLASS_VERBS = {
    "Init", "Initialize", "Create", "Delete", "Destroy", "Update", "Draw", "Render",
    "Exec", "Execute", "Setup", "Reset", "Load", "Save", "Find", "Get", "Set", "Alloc",
    "Free", "Read", "Write", "Parse", "Build", "Make", "Check", "Is", "Has", "Can",
    "Convert", "Apply", "Start", "Stop", "Play", "On", "Do", "Calc", "Compute", "Copy",
    "Move", "Add", "Remove", "Insert", "Sort", "Search", "Open", "Close", "Begin", "End",
    "Bind", "Unbind", "Register", "Unregister", "Dispatch", "Notify", "Handle", "Process",
    "Print", "Format", "Compare", "Test", "Validate", "Clamp", "Lerp", "Rotate", "Scale",
}
CLASS_WORDS = {
    "Window", "Widget", "Actor", "Object", "Manager", "List", "Row", "Panel", "Scene",
    "Unit", "Gauge", "State", "Data", "Table", "Header", "Context", "Buffer", "Entry",
    "Node", "Item", "Action", "Effect", "Model", "Mesh", "Sprite", "Camera", "Message",
    "Menu", "Layout", "Anim", "Frame", "Group", "Set", "Slot", "Cell", "Info", "Screen",
    "Renderer", "Controller", "Resource", "File", "Reader", "Writer", "Cache", "Queue",
    "Array", "String", "Command", "Cmd", "Task", "Job", "Pool", "Map", "Field", "Area",
    "Zone", "Record", "Param", "Handle", "Ref", "Ptr", "Part", "Overlay", "Cursor",
    "Text", "Widget", "Voice", "Marker", "Path", "Track", "Tween", "Root", "Owner",
    "Element", "Component", "System", "Service", "Factory", "Builder", "Iterator",
}


def type_vocabulary(rows: list[dict]) -> tuple[set[str], dict[str, str]]:
    """Known struct type names and a normalised (no underscores) lookup.

    Sources: ``include/recovered_types.h`` (M1's 992 opaque typedefs) and every
    capitalised pointer type in the merged signatures.  Both are evidence that a
    naming worker already thought the type existed; this module never invents a
    type merely because a function name has three tokens.
    """
    names: set[str] = set()
    recovered = ROOT / "include" / "recovered_types.h"
    if recovered.is_file():
        names.update(TYPE_DECL.findall(recovered.read_text(encoding="utf-8")))
    for row in rows:
        names.update(SIG_TYPE.findall(row.get("signature") or ""))
    names.discard("void")
    normalised = {name.replace("_", ""): name for name in sorted(names, key=len, reverse=True)}
    return names, normalised


def classlike(token: str) -> bool:
    """Heuristic for a class word such as ``GaugeWindow`` / ``SceneObject``.

    A bare verb (``InitPanes``, ``Bind``) is not a class.  CamelCase with an
    internal capital or a known noun suffix is.  Verbs are rejected by prefix so
    that ``Field_InitActorColorTable`` and ``Ui_SetColorPalette`` stay free
    functions instead of becoming one-function "classes".
    """
    if not token or token[0].islower():
        return False
    if token in CLASS_WORDS:
        return True
    if token in CLASS_VERBS:
        return False
    if any(token.startswith(verb) for verb in CLASS_VERBS if len(verb) >= 3):
        return False
    if re.match(r"^[A-Z][a-zA-Z0-9]*[A-Z]", token):
        return True
    return any(token.endswith(word) and len(token) > len(word) for word in CLASS_WORDS)


def class_for_name(name: str, types: set[str], normalised: dict[str, str]) -> dict | None:
    """The class a recovered function name belongs to, with evidence source."""
    tokens = name_tokens(name)
    if len(tokens) < 3:
        return None
    # The longest prefix that matches a recovered type wins, so
    # Battle_Action_SpecialMove_* becomes one class, not Battle_Action_*.
    for k in range(min(5, len(tokens) - 1), 1, -1):
        under = "_".join(tokens[:k])
        joined = "".join(tokens[:k])
        if under in types:
            return {"class": under, "type": under, "prefix": k, "source": "type"}
        if joined in types:
            return {"class": under, "type": joined, "prefix": k, "source": "type"}
        if joined in normalised:
            return {"class": under, "type": normalised[joined], "prefix": k, "source": "type"}
    # Fall back to a class-looking second token.  This is how Ui_GaugeWindow_*
    # recovers Ui_GaugeWindow when no signature happened to mention the type.
    if classlike(tokens[1]):
        return {"class": "_".join(tokens[:2]), "type": camel_type(*tokens[:2]),
                "prefix": 2, "source": "name"}
    return None


# --------------------------------------------------------------------------- #
# parsing one function
# --------------------------------------------------------------------------- #
CAST_OFF = re.compile(
    r"\(\s*([A-Za-z_]\w*)\s*(\*+)\s*\)\s*\(\s*(\(int\)\s*)?([A-Za-z_]\w*)\s*\+\s*(0x[0-9a-f]+)\s*\)"
)
CAST_DEREF0 = re.compile(r"\*\s*\(\s*([A-Za-z_]\w*)\s*(\*+)\s*\)\s*([A-Za-z_]\w*)\b(?!\s*\+)")
INDEX = re.compile(r"\b([A-Za-z_]\w*)\s*\[\s*(0x[0-9a-f]+|\d+)\s*\]")
ADDR = re.compile(r"\b([A-Za-z_]\w*)\s*\+\s*(0x[0-9a-f]+)")
CALL_START = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
DECL = re.compile(
    r"^\s{2}([A-Za-z_]\w*)\s*((?:\*\s*)*)([A-Za-z_]\w*)\s*(?:\[\s*(\d+)\s*\])?\s*;",
    re.M,
)
DAT_WORD = re.compile(r"\bDAT_([0-9a-fA-F]{8})\b")
RETURN_PTR = re.compile(r"\breturn\s+([A-Za-z_]\w*)\s*;")
ASSIGN_ALIAS = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*\([^)]*\)\s*(param_\d+)\s*;")
ASSIGN_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*\(?[^;=]*?\)?\s*([A-Za-z_]\w*)\s*\(")
IDENT_VALUE = re.compile(r"^[A-Za-z_]\w*$")
ALLOC_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*\(?[^;=]*?\)?\s*([A-Za-z_]\w*)\s*\(\s*(0x[0-9a-f]+|\d+)")
CONTROL = {"if", "while", "for", "switch", "return", "sizeof", "do", "else"}


def parse_signature(text: str) -> tuple[str, list[dict]]:
    """Return (return type text, parameters) from a Ghidra/readable C header."""
    head = text.split("{", 1)[0]
    m = re.search(r"([A-Za-z_][\w \t*]*?)\b([A-Za-z_]\w*)\s*\(([^;]*)\)\s*$", head.strip(), re.S)
    if not m:
        return "", []
    params: list[dict] = []
    raw = m.group(3).strip()
    if raw and raw != "void":
        depth = 0
        current = ""
        for ch in raw:                      # split on top-level commas only
            if ch == "(":
                depth += 1
            elif ch == ")":
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
        out.append({
            "name": pm.group(2),
            "type": ptype,
            "pointer": "*" in ptype,
            "width": type_width(re.sub(r"[*\s]", "", ptype)) if "*" not in ptype else 4,
        })
    return m.group(1).strip(), out


def split_args(arg_text: str) -> list[str]:
    """Split a call argument list on top-level commas."""
    out, depth, current = [], 0, ""
    for ch in arg_text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        out.append(current.strip())
    return out


def call_sites(code: str) -> list[tuple[str, list[str], int]]:
    """Every ``Callee(args)`` with balanced parentheses and its start offset."""
    found: list[tuple[str, list[str], int]] = []
    for m in CALL_START.finditer(code):
        callee = m.group(1)
        if callee in CONTROL:
            continue
        pos, depth = m.end() - 1, 0
        for i in range(pos, min(len(code), pos + 2000)):
            if code[i] == "(":
                depth += 1
            elif code[i] == ")":
                depth -= 1
                if depth == 0:
                    found.append((callee, split_args(code[pos + 1:i]), m.start()))
                    break
    return found


def access_is_write(code: str, end: int) -> bool:
    tail = code[end:end + 6]
    return bool(re.match(r"\s*(?:[-+*/%&|^]?=)(?!=)", tail))


def access_constant(code: str, end: int) -> str | None:
    tail = code[end:end + 60]
    m = re.match(r"\s*(?:[+\-*/%&|^]?=)\s*([^,;){}\n]{1,40})", tail)
    if not m:
        return None
    value = m.group(1).strip().rstrip(")")
    if value and len(value) <= 40:
        return value
    return None


def line_of(text: str, position: int) -> str:
    start = text.rfind("\n", 0, position) + 1
    end = text.find("\n", position)
    return text[start:end if end >= 0 else len(text)].strip()


def parse_function(row: dict, text: str, cls: dict | None) -> dict:
    """All field/vtable/allocation observations for one function."""
    code = strip_comments(text)
    return_type, params = parse_signature(text)
    param_names = [p["name"] for p in params]
    role = role_of(row["name"])
    declared: dict[str, dict] = {}
    for m in DECL.finditer(code):
        base, stars, var, array = m.group(1), m.group(2), m.group(3), m.group(4)
        declared[var] = {
            "type": base,
            "stars": stars.count("*"),
            "width": type_width(base),
            "array": int(array) if array else None,
        }
    param_map = {p["name"]: p for p in params}

    def element_width(base: str) -> int:
        """Bytes added by ``base + 1`` in the Ghidra C.

        Ghidra scales pointer arithmetic by the declared element type:
        ``undefined4 *p; p + 0x15`` is byte offset 0x54, while
        ``int p; p + 0x15`` is byte offset 0x15.  An explicit ``(int)p + 0x15``
        is always byte arithmetic.  Getting this wrong shifts every field of a
        constructor by a factor of four, so it is deliberate, not cosmetic.
        """
        info = declared.get(base)
        if info and info["stars"] >= 1:
            return max(1, info["width"])
        param = param_map.get(base)
        if param and param["pointer"]:
            return max(1, param["width"])
        return 1
    # self candidates -------------------------------------------------------
    self_bases: set[str] = set()
    primary = param_names[0] if param_names else None
    pointer_use = primary is not None and bool(
        re.search(rf"\b{re.escape(primary)}\s*\+", code)
        or re.search(rf"\b{re.escape(primary)}\s*\[", code)
        or re.search(rf"\(\s*\w+\s*\*+\s*\)\s*{re.escape(primary)}\b", code)
    )
    if primary and cls and pointer_use:
        self_bases.add(primary)
    for m in ASSIGN_ALIAS.finditer(code):
        if m.group(2) in self_bases or m.group(2) == primary:
            self_bases.add(m.group(1))
    # In a constructor the object is usually the returned variable, allocated or
    # produced by a base ctor, so it is not param_1 at all.
    if cls and role == "ctor":
        for var in RETURN_PTR.findall(code):
            if declared.get(var, {}).get("stars", 0) >= 1:
                self_bases.add(var)
        for m in ASSIGN_CALL.finditer(code):
            var, callee = m.group(1), m.group(2)
            callee_cls = class_for_name(callee, cls["_types"], cls["_normalised"])
            if declared.get(var, {}).get("stars", 0) >= 1 and (
                callee_cls and callee_cls["class"] in ({cls["class"]} | set(cls.get("bases", {})))
                or re.search(r"(?i)alloc", callee)
            ):
                self_bases.add(var)
            # `obj = (T *)Base_Ctor();` followed by `*obj = vtable;` (or any
            # offset-0 store) is constructor chaining: the local is the very
            # object under construction, not a subobject.  Subobject ctors are
            # instead stored into one of *our* fields and never written through
            # at offset 0.
            if (declared.get(var, {}).get("stars", 0) >= 1 and callee_cls
                    and role_of(callee) == "ctor"
                    and re.search(rf"\*\s*{re.escape(var)}\s*=", code)):
                self_bases.add(var)
        # A pointer variable that receives a text-pointer/vtable value at offset 0
        # is the constructed object even if Ghidra lost the return statement.
        assigned_vars = {m.group(1) for m in ASSIGN_CALL.finditer(code)}
        for m in re.finditer(r"\*\s*([A-Za-z_]\w*)\s*=\s*(?:DAT_|&?g_|[A-Za-z_]\w*\s*;)", code):
            var = m.group(1)
            if var in assigned_vars and declared.get(var, {}).get("stars", 0) >= 1:
                self_bases.add(var)
    # Last resort for a constructor whose allocation/return Ghidra truncated:
    # the pointer local that receives most field traffic is the new object.
    # Restrict this to constructors so an ordinary method never steals a child
    # pointer and reports its fields as its own.
    if cls and role == "ctor" and not self_bases:
        traffic: collections.Counter = collections.Counter()
        for m in CAST_OFF.finditer(code):
            if m.group(4) in declared and declared[m.group(4)]["stars"] >= 1:
                traffic[m.group(4)] += 2
        for m in INDEX.finditer(code):
            if m.group(1) in declared and declared[m.group(1)]["stars"] >= 1:
                traffic[m.group(1)] += 2
        if traffic:
            self_bases.add(traffic.most_common(1)[0][0])
    fields: dict[int, dict] = collections.defaultdict(lambda: {
        "sizes": collections.Counter(), "reads": 0, "writes": 0,
        "functions": set(), "constants": collections.Counter(),
        "callees": collections.Counter(), "pointers": False, "fnptr": False,
        "array": False, "addr": False, "raw_lines": [], "float": False,
    })
    vtables: set[int] = set()
    allocations: list[dict] = []

    def touch(off: int, width: int, write: bool, *, pointer=False, fnptr=False,
              array=False, const=None, raw="", addr=False, float_hint=False) -> None:
        field = fields[off]
        field["sizes"][max(1, width)] += 1
        field["reads" if not write else "writes"] += 1
        field["functions"].add(row["name"])
        field["pointers"] = field["pointers"] or pointer
        field["fnptr"] = field["fnptr"] or fnptr
        field["array"] = field["array"] or array
        field["addr"] = field["addr"] or addr
        field["float"] = field["float"] or float_hint
        if const:
            field["constants"][const] += 1
        if raw and len(field["raw_lines"]) < 8:
            field["raw_lines"].append(raw[:200])

    # typed offset accesses ------------------------------------------------
    for m in CAST_OFF.finditer(code):
        base_type, stars, int_cast, base, off_text = m.groups()
        if base not in self_bases:
            continue
        off = int(off_text, 16) * (1 if int_cast else element_width(base))
        prefix = code[max(0, m.start() - 3):m.start()]
        deref = prefix.count("*")
        is_ptr = len(stars) >= 2
        is_fn = base_type == "code" and (len(stars) >= 2 or deref >= 2)
        width = 4 if (is_ptr or is_fn) else type_width(base_type)
        end = m.end()
        write = access_is_write(code, end)
        const = access_constant(code, end) if write else None
        float_hint = bool(re.search(r"\bfloat\b", code[max(0, m.start() - 40):m.start()])
                          or re.search(r"\bfloat\b", code[end:end + 40]))
        touch(off, width, write, pointer=is_ptr, fnptr=is_fn, const=const,
              raw=line_of(code, m.start()), float_hint=float_hint)
        if off == 0 and const:
            for dat in DAT_WORD.findall(const):
                vt = word_at(int(dat, 16))
                if vt is not None and section_of(vt) in ("rodata", "data") and len(pointer_array(vt, 2)) >= 2:
                    vtables.add(vt)
        if is_ptr:
            # The next expression may reveal the pointed-to object's field.
            tail = code[end:end + 120]
            if re.match(r"\s*\+\s*0x[0-9a-f]+", tail):
                fields[off]["callees"]["+offset"] += 1
        if const:
            for ptr in re.findall(r"(?:DAT_|g_)([0-9a-fA-F]{8})", const):
                value = int(ptr, 16)
                field = fields[off]
                field.setdefault("pointer_values", collections.Counter())[hex_addr(value)] += 1

    # array-index accesses on a self pointer -------------------------------
    for m in INDEX.finditer(code):
        base, idx_text = m.group(1), m.group(2)
        if base not in self_bases:
            continue
        width = declared.get(base, {}).get("width", 4)
        idx = int(idx_text, 16) if idx_text.lower().startswith("0x") else int(idx_text)
        end = m.end()
        write = access_is_write(code, end)
        const = access_constant(code, end) if write else None
        touch(idx * max(1, width), width, write, const=const, raw=line_of(code, m.start()))
        if idx == 0 and const:
            for dat in DAT_WORD.findall(const):
                vt = word_at(int(dat, 16))
                if vt is not None and section_of(vt) in ("rodata", "data") and len(pointer_array(vt, 2)) >= 2:
                    vtables.add(vt)

    # direct dereference of offset 0 ---------------------------------------
    for m in CAST_DEREF0.finditer(code):
        base_type, stars, base = m.groups()
        if base not in self_bases:
            continue
        is_ptr = len(stars) >= 2
        width = 4 if is_ptr else type_width(base_type)
        write = access_is_write(code, m.end())
        const = access_constant(code, m.end()) if write else None
        touch(0, width, write, pointer=is_ptr, const=const, raw=line_of(code, m.start()))
        if const:
            for dat in DAT_WORD.findall(const):
                vt = word_at(int(dat, 16))
                if vt is not None and section_of(vt) in ("rodata", "data") and len(pointer_array(vt, 2)) >= 2:
                    vtables.add(vt)

    # addresses of subobjects passed to a call ------------------------------
    typed_spans = [(m.start(), m.end()) for m in CAST_OFF.finditer(code)]
    for m in ADDR.finditer(code):
        base, off_text = m.group(1), m.group(2)
        if base not in self_bases:
            continue
        if any(start <= m.start() < end for start, end in typed_spans):
            continue
        int_cast = bool(re.search(r"\(int\)\s*$", code[max(0, m.start() - 8):m.start()]))
        off = int(off_text, 16) * (1 if int_cast else element_width(base))
        if off == 0:
            continue
        before = code[max(0, m.start() - 160):m.start()]
        calls = [c for c in CALL_START.finditer(before) if c.group(1) not in CONTROL]
        callee = calls[-1].group(1) if calls else None
        field = fields[off]
        field["addr"] = True
        field["functions"].add(row["name"])
        if callee:
            field["callees"][callee] += 1
        if len(field["raw_lines"]) < 8:
            field["raw_lines"].append(line_of(code, m.start())[:200])

    # bare offset-0 stores (`*self = vtable;`, `self[0] = vtable;`) ----------
    # Ghidra often loads the vtable into a temporary and reuses that temporary
    # for a later constant, so resolve the *nearest preceding* assignment.
    const_assignments: list[tuple[int, str, str]] = []
    for m in re.finditer(
            r"\b([A-Za-z_]\w*)\s*=\s*(?:\([^)]*\)\s*)?(DAT_[0-9a-fA-F]{8}|PTR_[0-9a-fA-F]{8})\s*;",
            code):
        const_assignments.append((m.start(), m.group(1), m.group(2)))

    def resolve_value(value: str, position: int) -> str:
        if not IDENT_VALUE.match(value):
            return value
        best: tuple[int, str] | None = None
        for pos, var, val in const_assignments:
            if var == value and pos < position and (best is None or pos > best[0]):
                best = (pos, val)
        return best[1] if best else value

    for base in self_bases:
        for m in re.finditer(rf"\*\s*{re.escape(base)}\s*=\s*([^;]+);", code):
            value = m.group(1).strip()
            resolved = resolve_value(value, m.start())
            touch(0, 4, True, const=resolved, raw=line_of(code, m.start()))
            for dat in DAT_WORD.findall(resolved):
                vt = word_at(int(dat, 16))
                if vt is not None and section_of(vt) in ("rodata", "data") and len(pointer_array(vt, 2)) >= 2:
                    vtables.add(vt)
        for m in re.finditer(rf"\b{re.escape(base)}\s*\[\s*(?:0|0x0)\s*\]\s*=\s*([^;]+);", code):
            value = m.group(1).strip()
            resolved = resolve_value(value, m.start())
            touch(0, 4, True, const=resolved, raw=line_of(code, m.start()))
            for dat in DAT_WORD.findall(resolved):
                vt = word_at(int(dat, 16))
                if vt is not None and section_of(vt) in ("rodata", "data") and len(pointer_array(vt, 2)) >= 2:
                    vtables.add(vt)

    # allocation sizes ------------------------------------------------------
    for m in ALLOC_CALL.finditer(code):
        var, callee, size_text = m.groups()
        size = int(size_text, 16) if size_text.lower().startswith("0x") else int(size_text)
        if 8 <= size <= 0x200000 and re.search(r"(?i)alloc|malloc|calloc|new|reserve", callee):
            allocations.append({"var": var, "size": size, "callee": callee})

    # calls (base ctor detection and subobject typing) ----------------------
    calls: list[dict] = []
    for callee, args, start in call_sites(code):
        matching_arg = None
        for i, a in enumerate(args):
            for base in self_bases:
                if re.search(rf"\b{re.escape(base)}\b", a):
                    matching_arg = i
                    break
            if matching_arg is not None:
                break
        if matching_arg is not None:
            calls.append({"callee": callee, "args": args, "start": start,
                          "self_arg": matching_arg})
    # Constructor chaining also happens through the return value:
    #   obj = (T *)Base_Ctor(); *obj = vtable;  -> obj is the same object.
    assigned_calls = [
        {"var": m.group(1), "callee": m.group(2)}
        for m in ASSIGN_CALL.finditer(code)
    ]

    return {
        "fields": {off: field for off, field in fields.items()},
        "vtables": sorted(vtables),
        "allocations": allocations,
        "self_bases": sorted(self_bases),
        "calls": calls,
        "assigned_calls": assigned_calls,
        "role": role,
        "params": params,
        "return_type": return_type,
    }


# --------------------------------------------------------------------------- #
# readable evidence
# --------------------------------------------------------------------------- #
FIELD_IN_READABLE = re.compile(r"->f_([0-9a-f]+)")


def readable_evidence(rows: list[dict], wanted: set[int]) -> dict[int, dict[int, list[str]]]:
    """offset -> example readable-C lines, per function address."""
    jobs = [(row, readable_path(row)) for row in rows if row["_address"] in wanted]

    def one(job):
        row, path = job
        if path is None:
            return row["_address"], {}
        text = path.read_text(encoding="utf-8", errors="replace")
        body = strip_comments(text)
        found: dict[int, list[str]] = collections.defaultdict(list)
        for m in FIELD_IN_READABLE.finditer(body):
            off = int(m.group(1), 16)
            line = line_of(body, m.start())
            if line and line not in found[off] and len(found[off]) < 6:
                found[off].append(line[:220])
        return row["_address"], dict(found)

    out: dict[int, dict[int, list[str]]] = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for address, found in pool.map(one, jobs, chunksize=32):
            out[address] = found
    return out


# --------------------------------------------------------------------------- #
# vtable scan
# --------------------------------------------------------------------------- #
def scan_vtables(rows: list[dict]) -> list[dict]:
    """Pointer arrays in .rodata/.data that look like C++ vtables.

    A vtable is a run of >=4 consecutive words that all point into ``.text``.
    Runs whose slots mostly share one class prefix are reported as that class's
    vtable; the rest stay ``pointer_table`` (callback/jump tables) and are left
    for the G batches.
    """
    by_addr = {row["_address"]: row for row in rows}
    runs: list[dict] = []
    upper = 0x00839BC0
    addr = 0x00725000
    while addr < upper:
        if section_of(addr) in ("rodata", "data") and is_text_pointer(word_at(addr)):
            slots = pointer_array(addr)
            if len(slots) >= 4:
                names = [by_addr.get(s, {}).get("name", "") for s in slots]
                classes = collections.Counter()
                for name in names:
                    tokens = name_tokens(name) if name else []
                    if len(tokens) >= 2:
                        classes["_".join(tokens[:2])] += 1
                dominant, count = ("", 0)
                if classes:
                    dominant, count = classes.most_common(1)[0]
                runs.append({
                    "address": addr,
                    "slots": slots,
                    "slot_count": len(slots),
                    "dominant_class": dominant if count >= 2 else "",
                    "dominant_share": round(count / max(1, len(slots)), 3),
                    "kind": "vtable" if count >= 2 and count >= len(slots) * 0.3 else "pointer_table",
                    "slot_names": names,
                })
                addr += 4 * len(slots)
                continue
        addr += 4
    return runs


# --------------------------------------------------------------------------- #
# main build
# --------------------------------------------------------------------------- #
def build(limit: int | None = None, workers: int = 12) -> dict:
    rows = load_rows()
    if limit:
        rows = rows[:limit]
    types, normalised = type_vocabulary(rows)
    # Calls in the raw Ghidra text use FUN_<address>; map them back to the M1
    # readable name so a call can be attributed to a class.
    name_by_address = {row["_address"]: row["name"] for row in rows}

    def resolved_name(name: str) -> str:
        m = re.match(r"^FUN_([0-9A-Fa-f]{8})$", name)
        if m:
            return name_by_address.get(int(m.group(1), 16), name)
        return name

    # 1. class per function name
    for row in rows:
        cls = class_for_name(row["name"], types, normalised)
        if cls:
            cls["_types"], cls["_normalised"] = types, normalised
            cls["_resolve"] = resolved_name
        row["_class"] = cls

    # 2. parse source
    def one(row):
        path = raw_path(row)
        if path is None or not path.is_file():
            return row, None
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return row, None
        return row, parse_function(row, text, row.get("_class"))

    observations: dict[int, dict] = {}
    failed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for row, parsed in pool.map(one, rows, chunksize=32):
            if parsed is None:
                failed += 1
                continue
            observations[row["_address"]] = parsed

    # 3. evidence from readable C for functions in a class
    class_addrs = {row["_address"] for row in rows if row.get("_class")}
    evidence = readable_evidence(rows, class_addrs)

    # 4. aggregate classes
    classes: dict[str, dict] = {}
    # Calls in the raw Ghidra text use FUN_<address>; map them back to the M1
    # readable name so a call can be attributed to a class.
    name_by_address = {row["_address"]: row["name"] for row in rows}

    def resolved_name(name: str) -> str:
        m = re.match(r"^FUN_([0-9A-Fa-f]{8})$", name)
        if m:
            return name_by_address.get(int(m.group(1), 16), name)
        return name

    for row in rows:
        cls = row.get("_class")
        if not cls:
            continue
        entry = classes.setdefault(cls["class"], {
            "class": cls["class"], "type": cls["type"],
            "subsystem": subsystem_of(row["name"]),
            "source": cls["source"], "functions": [], "fields": {},
            "bases": collections.Counter(), "vtable_evidence": {
                "ctor_store": set(), "slot_match": set()},
            "alloc_sizes": collections.Counter(), "vtables": set(),
            "has_self": False, "readable_lines": {},
        })
        entry["functions"].append(row["name"])
        parsed = observations.get(row["_address"])
        if not parsed:
            continue
        if parsed["self_bases"]:
            entry["has_self"] = True
        entry["readable_lines"].update(evidence.get(row["_address"], {}))
        for off, field in parsed["fields"].items():
            target = entry["fields"].setdefault(off, {
                "offset": off, "sizes": collections.Counter(), "reads": 0, "writes": 0,
                "functions": set(), "constants": collections.Counter(),
                "callees": collections.Counter(), "pointers": False, "fnptr": False,
                "array": False, "addr": False, "float": False,
                "raw_lines": [], "readable": [], "pointer_values": collections.Counter(),
            })
            target["sizes"].update(field["sizes"])
            target["reads"] += field["reads"]
            target["writes"] += field["writes"]
            target["functions"].update(field["functions"])
            target["constants"].update(field["constants"])
            target["callees"].update(field["callees"])
            target["pointer_values"].update(field.get("pointer_values") or {})
            for flag in ("pointers", "fnptr", "array", "addr", "float"):
                target[flag] = target[flag] or field[flag]
            for line in field["raw_lines"]:
                if len(target["raw_lines"]) < 8 and line not in target["raw_lines"]:
                    target["raw_lines"].append(line)
        for vt in parsed["vtables"]:
            entry["vtable_evidence"]["ctor_store"].add(vt)
        entry["alloc_sizes"].update(
            alloc["size"] for alloc in parsed["allocations"]
            if alloc["var"] in parsed["self_bases"])
        for call in parsed["calls"]:
            callee_name = resolved_name(call["callee"])
            callee_cls = class_for_name(callee_name, types, normalised)
            callee_role = role_of(callee_name)
            if callee_cls and callee_cls["class"] != cls["class"] and callee_role == "ctor":
                entry["bases"][callee_cls["class"]] += 1
            # a subobject's class is a good type guess for the field at that offset
            arg = call["args"][call["self_arg"]] if call["self_arg"] < len(call["args"]) else ""
            off_match = re.search(r"0x([0-9a-f]+)", arg)
            if off_match and "+" in arg and callee_cls and callee_cls["class"] != cls["class"]:
                off = int(off_match.group(1), 16)
                if off in entry["fields"]:
                    entry["fields"][off]["callees"][callee_cls["class"] + "*"] += 1
        # obj = (T *)Base_Ctor(); *obj = vtable; is the usual constructor chain
        if parsed["role"] == "ctor":
            for ac in parsed.get("assigned_calls", []):
                if ac["var"] not in parsed["self_bases"]:
                    continue
                callee_cls = class_for_name(resolved_name(ac["callee"]), types, normalised)
                if (callee_cls and callee_cls["class"] != cls["class"]
                        and role_of(resolved_name(ac["callee"])) == "ctor"):
                    entry["bases"][callee_cls["class"]] += 2

    # 5. vtables: resolve, name slots, attach to classes
    vtable_runs = scan_vtables(rows)
    runs_by_addr = {run["address"]: run for run in vtable_runs}
    for entry in classes.values():
        for vt in entry["vtable_evidence"]["ctor_store"]:
            entry["vtables"].add(vt)
        if entry["class"] in {run["dominant_class"] for run in vtable_runs}:
            best = max((run for run in vtable_runs if run["dominant_class"] == entry["class"]),
                       key=lambda run: (run["slot_count"], -run["address"]))
            entry["vtables"].add(best["address"])
            entry["vtable_evidence"]["slot_match"].add(best["address"])

    # a vtable whose slots agree on a class creates/reinforces that class
    for run in vtable_runs:
        cls_name = run["dominant_class"]
        if not cls_name:
            continue
        if cls_name not in classes:
            tokens = cls_name.split("_")
            classes[cls_name] = {
                "class": cls_name, "type": camel_type(*tokens), "subsystem": subsystem_of(cls_name),
                "source": "vtable", "functions": [], "fields": {},
                "bases": collections.Counter(),
                "vtable_evidence": {"ctor_store": set(), "slot_match": {run["address"]}},
                "alloc_sizes": collections.Counter(), "vtables": {run["address"]},
                "has_self": False, "readable_lines": {},
            }
        classes[cls_name]["vtables"].add(run["address"])

    # 6. finalise each class
    by_name = {row["name"]: row for row in rows}
    out_classes = []
    for entry in classes.values():
        fields = []
        size_min = 0
        size_strong = 0
        for off in sorted(entry["fields"]):
            field = entry["fields"][off]
            width = max(field["sizes"]) if field["sizes"] else 4
            size_min = max(size_min, off + width)
            # A single access at a very large offset is usually a mis-typed
            # `param_1` (a helper that works on a different object or a global
            # buffer), not a 200 KiB window.  It stays in the evidence so the
            # S worker can judge it, but it must not set the class size.
            weak = off > 0x4000 and len(field["functions"]) == 1
            if not weak:
                size_strong = max(size_strong, off + width)
            lines = entry["readable_lines"].get(off) or []
            for line in field["raw_lines"]:
                if len(lines) < 6 and line not in lines:
                    lines.append(line)
            type_guess, type_conf = guess_type(field, width, entry["class"])
            if off == 0 and entry["vtables"]:
                type_guess, type_conf = "void*", 0.85
            fields.append({
                "offset": off,
                "offset_hex": f"0x{off:x}",
                "size": width,
                "sizes_seen": sorted(field["sizes"]),
                "type_guess": type_guess,
                "confidence": round(type_conf, 2),
                "is_vtable": off == 0 and bool(entry["vtables"]),
                "weak": weak,
                "is_pointer": bool(field["pointers"]),
                "is_function_pointer": bool(field["fnptr"]),
                "is_array": bool(field["array"]),
                "address_taken": bool(field["addr"]),
                "float_hint": bool(field["float"]),
                "reads": field["reads"],
                "writes": field["writes"],
                "functions": sorted(field["functions"])[:20],
                "constants": [c for c, _ in field["constants"].most_common(6)],
                "callees": [c for c, _ in field["callees"].most_common(6)],
                "pointer_values": [p for p, _ in field["pointer_values"].most_common(6)],
                "evidence": lines[:6],
            })
        # allocation evidence: the class's ctors or a caller that allocates then ctors
        alloc = entry["alloc_sizes"].most_common(1)
        size_alloc = alloc[0][0] if alloc else None
        if size_alloc is not None and size_alloc < size_strong:
            size_alloc = None
        size_strong = max(size_strong, 4)
        size = size_alloc or ((size_strong + 3) // 4 * 4)
        size_source = "allocation" if size_alloc else "max_strong_field+width"
        base = None
        if entry["bases"]:
            base = entry["bases"].most_common(1)[0][0]
        vtables = []
        for vt in sorted(entry["vtables"]):
            run = runs_by_addr.get(vt)
            if run is None:
                slots = pointer_array(vt, 64)
                run = {"address": vt, "slots": slots, "slot_count": len(slots),
                       "slot_names": [by_name.get(s, {}).get("name", "") for s in slots]}
            vtables.append({
                "address": hex_addr(run["address"]),
                "slot_count": run["slot_count"],
                "slots": [{"index": i, "address": hex_addr(s), "name": n}
                          for i, (s, n) in enumerate(zip(run["slots"], run["slot_names"]))],
            })
        funcs = []
        for name in sorted(set(entry["functions"])):
            row = by_name.get(name)
            funcs.append({
                "name": name,
                "address": hex_addr(row["_address"]) if row else None,
                "role": role_of(name),
                "readable": row.get("file") if row else None,
            })
        out_classes.append({
            "class": entry["class"],
            "type": entry["type"],
            "subsystem": entry["subsystem"],
            "source": entry["source"],
            "base": base,
            "bases_seen": {k: v for k, v in entry["bases"].most_common(4)},
            "size": size,
            "size_min": size_min,
            "size_strong": size_strong,
            "size_alloc": size_alloc,
            "size_source": size_source,
            "weak_field_count": sum(1 for f in fields if f["weak"]),
            "field_count": len(fields),
            "has_self": entry["has_self"],
            "vtable": vtables[0]["address"] if vtables else None,
            "vtables": vtables,
            "function_count": len(funcs),
            "functions": funcs,
            "fields": fields,
        })
    out_classes.sort(key=lambda c: (c["subsystem"], c["class"]))

    # 7. classes that are only namespaces (no fields): keep them, but mark them
    namespace = [c["class"] for c in out_classes if not c["fields"]]

    stats = {
        "classes": len(out_classes),
        "classes_with_fields": sum(1 for c in out_classes if c["fields"]),
        "namespace_classes": len(namespace),
        "fields": sum(len(c["fields"]) for c in out_classes),
        "functions_in_classes": sum(c["function_count"] for c in out_classes),
        "functions_parsed": len(observations),
        "functions_unreadable": failed,
        "vtables": len([run for run in vtable_runs if run["kind"] == "vtable"]),
        "pointer_tables": len([run for run in vtable_runs if run["kind"] == "pointer_table"]),
        "classes_by_subsystem": dict(collections.Counter(c["subsystem"] for c in out_classes)),
        "fields_by_width": dict(collections.Counter(
            f["size"] for c in out_classes for f in c["fields"])),
        "classes_with_vtable": sum(1 for c in out_classes if c["vtables"]),
        "classes_with_base": sum(1 for c in out_classes if c["base"]),
    }
    return {
        "generated_by": "tools/typedb/struct_db.py",
        "method": (
            "Field offsets/widths are parsed from the raw Ghidra C. Classes come from "
            "recovered parameter types (include/recovered_types.h, merged signatures) or a "
            "class-looking name prefix; vtable slots are resolved by reading the retail "
            "image. Fields are evidence, not names - S batches name them."
        ),
        "stats": stats,
        "classes": out_classes,
        "pointer_tables": [
            {"address": hex_addr(run["address"]), "slot_count": run["slot_count"],
             "slot_names": [n for n in run["slot_names"] if n][:16]}
            for run in vtable_runs if run["kind"] == "pointer_table"
        ],
        "_namespace_classes": namespace,
    }


def guess_type(field: dict, width: int, cls: str) -> tuple[str, float]:
    """Conservative C type guess for a field (never a made-up struct name)."""
    if field["fnptr"]:
        return "void (*)(void)", 0.7
    if field["pointers"]:
        for callee, _ in field["callees"].most_common(2):
            if callee.endswith("*"):
                return callee, 0.55
        return "void*", 0.6
    for callee, _ in field["callees"].most_common(2):
        if callee.endswith("*"):
            return callee, 0.5
    if field["float"] and width == 4:
        return "f32", 0.55
    if width == 8:
        return "u64", 0.8
    if width == 4:
        return "u32", 0.8
    if width == 2:
        return "u16", 0.8
    return "u8", 0.8


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, help="parse only the first N functions (smoke test)")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--stats", action="store_true", help="print statistics, write nothing")
    args = ap.parse_args()

    result = build(limit=args.limit, workers=args.workers)
    print(json.dumps(result["stats"], indent=1))
    if args.stats:
        return 0
    TYPES_DIR.mkdir(parents=True, exist_ok=True)
    out = TYPES_DIR / "structs.json"
    write_json(out, result)
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.0f} KiB)")
    print(f"  next: python tools/typedb/inventory.py   (globals + locals)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
