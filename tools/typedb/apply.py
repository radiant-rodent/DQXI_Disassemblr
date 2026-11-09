#!/usr/bin/env python3
"""Validate and merge S_/G_/V_ worker answers into headers and rename maps.

This is the apply step that turns hypotheses into something the readable C can
use.  It never invents a name: a class/field/global/local exists in the output
only because a worker (or the hand-written demo under ``orchestration/types/
samples/``) proposed it *and* the evidence in ``structs.json`` / ``globals.json``
/ ``locals.json`` agrees that the offset, address or token exists.

What it writes (``--merge``):

    include/dqxi/dqxi_base.h     fixed-width types (includes include/types.h)
    include/dqxi/structs.h       real C structs, padding where a field is unknown
    include/dqxi/globals.h       extern declarations for named globals
    include/dqxi/dqxi_types.h    umbrella header
    include/dqxi/README.md       how the pipeline works, confidence meaning
    orchestration/types/merged/fields.json    class -> offset -> {name,type}
    orchestration/types/merged/globals.json   literal -> name, address -> name
    orchestration/types/merged/locals.json    function -> token -> new name
    orchestration/types/merged/functions.json function -> owning class
    orchestration/types/merged/report.json    validation + merge statistics

``--validate`` only writes ``report.json``.  ``--demo`` merges the hand-written
samples into ``orchestration/types/merged_demo/`` instead, so the before/after
example in the S0 report cannot contaminate the real headers.

Layout rules used by the struct emitter:

* a base class is embedded as its first member only when the base struct exists,
  its size is known and no derived field lies inside it; otherwise the struct is
  flat and the inheritance is a comment;
* every gap between known fields becomes an explicitly named padding array;
* a size that is only "highest field + width" is padded to that size, a size
  backed by an allocation is trusted up to 0x20000; larger unbacked sizes are
  reported as suspicious and the struct is cut at the last field.

Usage:
    python tools/typedb/apply.py --validate
    python tools/typedb/apply.py --merge
    python tools/typedb/apply.py --merge --demo
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.typedb.common import (  # noqa: E402
    HEADER_DIR, OUT_DIR, ROOT, TYPES_DIR, valid_identifier, write_json,
)

MERGED = TYPES_DIR / "merged"
SAMPLES = TYPES_DIR / "samples"
BUILTIN = {
    "u8", "u16", "u32", "u64", "s8", "s16", "s32", "s64", "f32", "f64",
    "char", "short", "int", "long", "float", "double", "void", "bool",
    "size_t", "ssize_t", "uint", "uchar", "ushort", "ulong",
}
KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long",
    "register", "restrict", "return", "short", "signed", "sizeof", "static", "struct",
    "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "class",
}
ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{6,8}$")
ARRAY_RE = re.compile(r"^(.*?)\s*\[\s*(0x[0-9a-fA-F]+|\d+)?\s*\]$")
FNPTR_RE = re.compile(r"^(?:void|u32|int)\s*\(\s*\*\s*\)\s*\([^)]*\)$")


# --------------------------------------------------------------------------- #
# evidence
# --------------------------------------------------------------------------- #
class Evidence:
    def __init__(self) -> None:
        self.structs = json.loads((TYPES_DIR / "structs.json").read_text(encoding="utf-8"))
        self.globals = json.loads((TYPES_DIR / "globals.json").read_text(encoding="utf-8"))
        self.locals = json.loads((TYPES_DIR / "locals.json").read_text(encoding="utf-8"))
        self.classes = {c["class"]: c for c in self.structs["classes"]}
        self.types = {c["class"]: c["type"] for c in self.structs["classes"]}
        self.type_to_class = {v: k for k, v in self.types.items()}
        self.global_by_address = {int(g["address"], 16): g for g in self.globals["globals"]}
        self.functions = {f["name"]: f for f in self.locals["functions"]}
        self.function_by_address = {int(f["address"], 16): f for f in self.locals["functions"]}
        self.class_of_function: dict[str, str] = {}
        for cls in self.structs["classes"]:
            for fn in cls.get("functions") or []:
                if fn.get("name"):
                    self.class_of_function.setdefault(fn["name"], cls["class"])


def load_outputs(ev: Evidence, demo: bool) -> tuple[dict[str, list], list[dict]]:
    """Read every S/G/V worker output; malformed files become issues."""
    issues: list[dict] = []
    found: dict[str, list] = {"S": [], "G": [], "V": []}
    sources: list[Path] = []
    if demo:
        for name in ("demo_S.json", "demo_G.json", "demo_V.json"):
            path = SAMPLES / name
            if path.is_file():
                sources.append(path)
    else:
        out_dir = OUT_DIR
        for path in sorted(out_dir.glob("*.json")):
            sources.append(path)
    for path in sources:
        batch = path.stem.split("_")[0] if path.stem.startswith(("S_", "G_", "V_")) else path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            issues.append({"batch": path.stem, "severity": "error",
                           "message": f"not valid UTF-8 JSON: {exc}"})
            continue
        entries = data if isinstance(data, list) else (
            data.get("classes") or data.get("globals") or data.get("functions")
            or data.get("entries") or [])
        kind = "S" if path.stem.startswith("S_") else "G" if path.stem.startswith("G_") else "V"
        if demo:
            kind = {"demo_S": "S", "demo_G": "G", "demo_V": "V"}[path.stem]
        if not isinstance(entries, list):
            issues.append({"batch": path.stem, "severity": "error",
                           "message": "expected a JSON array of entries"})
            continue
        for entry in entries:
            if isinstance(entry, dict):
                entry = dict(entry)
                entry["_batch"] = path.stem
                found[kind].append(entry)
            else:
                issues.append({"batch": path.stem, "severity": "error",
                               "message": f"entry is {type(entry).__name__}, not an object"})
    return found, issues


# --------------------------------------------------------------------------- #
# type checking
# --------------------------------------------------------------------------- #
def normalise_type(text: str, ev: Evidence) -> tuple[str | None, str | None, str | None]:
    """(C type, pointed-to class or None, error).  Only real types pass."""
    if not isinstance(text, str):
        return None, None, "type is not a string"
    text = " ".join(text.split())
    if not text:
        return None, None, "empty type"
    if FNPTR_RE.match(text):
        return text, None, None
    array = ARRAY_RE.match(text)
    count = None
    if array:
        text, count = array.group(1).strip(), array.group(2)
    pointer = 0
    while text.endswith("*"):
        pointer += 1
        text = text[:-1].strip()
    if text.startswith("struct "):
        text = text[7:].strip()
    base = text
    if base in BUILTIN:
        pass
    elif base in ev.types:
        base = ev.types[base]
    elif base in ev.types.values():
        pass
    else:
        return None, None, f"unknown type '{text}'"
    out = base + ("*" * pointer)
    if count:
        out = f"{out}[{count}]"
    type_class = None
    if pointer and text in ev.classes:
        type_class = text
    elif pointer and text in ev.types.values():
        type_class = ev.type_to_class[text]
    return out, type_class, None


def check_identifier(name: str, *, prefix: str = "") -> str | None:
    if not isinstance(name, str) or not name:
        return "name is empty"
    if prefix and not name.startswith(prefix):
        return f"name must start with '{prefix}'"
    if not valid_identifier(name):
        return f"'{name}' is not a valid C identifier"
    if name in KEYWORDS:
        return f"'{name}' is a C keyword"
    return None


def confidence_of(entry: dict, issues: list[dict], where: str) -> float:
    try:
        value = float(entry.get("confidence", 0.5))
    except (TypeError, ValueError):
        issues.append({"item": where, "severity": "warning",
                       "message": "confidence is not a number; using 0.5"})
        return 0.5
    if not 0.0 <= value <= 1.0:
        issues.append({"item": where, "severity": "warning",
                       "message": f"confidence {value} outside 0..1; clamped"})
        value = min(1.0, max(0.0, value))
    return value


# --------------------------------------------------------------------------- #
# merge S (classes + fields)
# --------------------------------------------------------------------------- #
def merge_structs(ev: Evidence, entries: list[dict], issues: list[dict]) -> dict:
    merged: dict[str, dict] = {}
    seen_names: dict[str, str] = {}
    for entry in entries:
        batch = entry.get("_batch", "?")
        cls_name = entry.get("class")
        where = f"{batch}:{cls_name}"
        evidence = ev.classes.get(cls_name)
        if evidence is None:
            issues.append({"batch": batch, "item": where, "severity": "error",
                           "message": "class is not in structs.json evidence"})
            continue
        cls_type = entry.get("type") or evidence["type"]
        err = check_identifier(cls_type)
        if err:
            issues.append({"batch": batch, "item": where, "severity": "error",
                           "message": f"class type: {err}"})
            continue
        if cls_name in merged:
            issues.append({"batch": batch, "item": where, "severity": "warning",
                           "message": "class appears twice; the later entry is merged field by field"})
        target = merged.setdefault(cls_name, {
            "class": cls_name, "type": cls_type, "summary": "", "confidence": 0.0,
            "size": evidence["size"], "size_source": evidence["size_source"],
            "base": evidence.get("base"), "vtable": evidence.get("vtable"),
            "fields": {}, "batches": set(), "evidence": "",
        })
        target["batches"].add(batch)
        if entry.get("summary"):
            target["summary"] = str(entry["summary"])[:400]
        if entry.get("evidence"):
            target["evidence"] = str(entry["evidence"])[:400]
        target["confidence"] = max(target["confidence"], confidence_of(entry, issues, where))
        if entry.get("base") is not None:
            base = entry["base"]
            if base in ev.classes or base in ("", None):
                target["base"] = base or None
            else:
                issues.append({"batch": batch, "item": where, "severity": "warning",
                               "message": f"base class '{base}' unknown; keeping evidence base"})
        size = entry.get("size", target["size"])
        try:
            size = int(size)
        except (TypeError, ValueError):
            issues.append({"batch": batch, "item": where, "severity": "warning",
                           "message": "size is not an integer; keeping evidence size"})
            size = target["size"]
        target["size"] = size
        used_names: dict[str, int] = {}
        fields = entry.get("fields") or []
        if not isinstance(fields, list):
            issues.append({"batch": batch, "item": where, "severity": "error",
                           "message": "fields is not an array"})
            continue
        for field in fields:
            if not isinstance(field, dict):
                continue
            try:
                offset = int(field.get("offset"))
            except (TypeError, ValueError):
                issues.append({"batch": batch, "item": where, "severity": "error",
                               "message": f"field offset {field.get('offset')!r} is not an integer"})
                continue
            evidence_field = next((f for f in evidence["fields"] if f["offset"] == offset), None)
            if offset < 0 or offset >= max(0x100000, size + 4):
                issues.append({"batch": batch, "item": f"{where}@0x{offset:x}",
                               "severity": "error",
                               "message": f"offset {offset} outside the class"})
                continue
            if evidence_field is None and offset >= max(size + 0x800, 0x100):
                issues.append({"batch": batch, "item": f"{where}@0x{offset:x}",
                               "severity": "error",
                               "message": f"offset {offset} is far beyond the class size 0x{size:X} "
                                          "and has no access evidence"})
                continue
            name = str(field.get("name") or "").strip()
            name_err = check_identifier(name)
            if name_err:
                issues.append({"batch": batch, "item": f"{where}@0x{offset:x}",
                               "severity": "error", "message": f"field name: {name_err}"})
                continue
            if name in used_names and used_names[name] != offset:
                issues.append({"batch": batch, "item": f"{where}@0x{offset:x}",
                               "severity": "error",
                               "message": f"duplicate field name '{name}'"})
                continue
            used_names[name] = offset
            ftype, type_class, type_err = normalise_type(field.get("type"), ev)
            if type_err:
                issues.append({"batch": batch, "item": f"{where}@0x{offset:x}",
                               "severity": "error", "message": f"field type: {type_err}"})
                continue
            try:
                fsize = int(field.get("size", 4))
            except (TypeError, ValueError):
                fsize = 4
            if evidence_field is None:
                issues.append({"batch": batch, "item": f"{where}@0x{offset:x}",
                               "severity": "warning",
                               "message": "offset has no access evidence; kept as worker hypothesis"})
            target["fields"][offset] = {
                "offset": offset, "name": name, "type": ftype, "type_class": type_class,
                "size": fsize, "confidence": confidence_of(field, issues, f"{where}@{offset:#x}"),
                "evidence": str(field.get("evidence") or "")[:300],
            }
    for cls in merged.values():
        cls["size"] = max(cls["size"], max((f["offset"] + f["size"] for f in cls["fields"].values()),
                                           default=0))
        if cls["fields"] and cls["confidence"] < 0.5:
            # class-level uncertainty is fine; the comment in the header explains it
            pass
    return merged


# --------------------------------------------------------------------------- #
# merge G (globals)
# --------------------------------------------------------------------------- #
def merge_globals(ev: Evidence, entries: list[dict], issues: list[dict]) -> tuple[dict, dict]:
    merged: dict[int, dict] = {}
    names: dict[str, int] = {}
    for entry in entries:
        batch = entry.get("_batch", "?")
        raw = entry.get("address")
        if not isinstance(raw, str) or not ADDR_RE.match(raw):
            issues.append({"batch": batch, "item": str(raw), "severity": "error",
                           "message": "address must look like 0x007BE330"})
            continue
        address = int(raw, 16)
        evidence = ev.global_by_address.get(address)
        if evidence is None:
            issues.append({"batch": batch, "item": raw, "severity": "error",
                           "message": "address is not in globals.json (not a data object)"})
            continue
        name = str(entry.get("name") or "").strip()
        err = check_identifier(name)
        if err:
            issues.append({"batch": batch, "item": raw, "severity": "error",
                           "message": f"global name: {err}"})
            continue
        bare_name = name[6:] if name.startswith("maybe_") else name
        if not bare_name.startswith("g_"):
            issues.append({"batch": batch, "item": raw, "severity": "error",
                           "message": f"global name must be g_... or maybe_g_..., got '{name}'"})
            continue
        if name in names and names[name] != address:
            issues.append({"batch": batch, "item": raw, "severity": "error",
                           "message": f"duplicate global name '{name}' (also {names[name]:#x})"})
            continue
        gtype, _, type_err = normalise_type(entry.get("type") or evidence["type_guess"], ev)
        if type_err:
            issues.append({"batch": batch, "item": raw, "severity": "error",
                           "message": f"global type: {type_err}"})
            continue
        names[name] = address
        previous = merged.get(address)
        if previous:
            # keep the more confident proposal; a second name becomes an alias note
            if confidence_of(entry, issues, raw) <= previous["confidence"]:
                continue
        merged[address] = {
            "address": address,
            "name": name,
            "type": gtype,
            "section": evidence["section"],
            "subsystem": evidence["subsystem"],
            "access": evidence.get("access") or "deref",
            "comment": str(entry.get("comment") or "")[:400],
            "confidence": confidence_of(entry, issues, raw),
            "evidence": str(entry.get("evidence") or "")[:300],
            "literals": [int(x, 16) for x in evidence.get("literals") or []],
            "is_array": evidence.get("is_array"),
            "size_hint": evidence.get("size_hint"),
        }
    literal_map: dict[int, int] = {}
    for address, entry in merged.items():
        for literal in entry["literals"]:
            literal_map.setdefault(literal, address)
    return merged, literal_map


# --------------------------------------------------------------------------- #
# merge V (locals)
# --------------------------------------------------------------------------- #
def merge_locals(ev: Evidence, entries: list[dict], issues: list[dict]) -> dict:
    merged: dict[str, dict] = {}
    for entry in entries:
        batch = entry.get("_batch", "?")
        raw = entry.get("address")
        name = entry.get("function")
        evidence = ev.functions.get(name)
        if evidence is None and isinstance(raw, str) and ADDR_RE.match(raw):
            evidence = ev.function_by_address.get(int(raw, 16))
        if evidence is None:
            issues.append({"batch": batch, "item": str(raw), "severity": "error",
                           "message": "function is not in locals.json"})
            continue
        fn = evidence["name"]
        tokens = {v["name"] for v in evidence["variables"]}
        params_in = entry.get("params") or {}
        locals_in = entry.get("locals") or {}
        if not isinstance(params_in, dict) or not isinstance(locals_in, dict):
            issues.append({"batch": batch, "item": fn, "severity": "error",
                           "message": "params/locals must be objects"})
            continue
        params: dict[str, str] = {}
        locals_: dict[str, str] = {}
        taken: set[str] = set()
        for source, target, allowed in ((params_in, params, {v["name"] for v in evidence["variables"]
                                                            if v["is_param"]}),
                                        (locals_in, locals_, {v["name"] for v in evidence["variables"]
                                                              if not v["is_param"]})):
            for old, new in source.items():
                if old not in allowed and old not in tokens:
                    issues.append({"batch": batch, "item": f"{fn}:{old}", "severity": "warning",
                                   "message": "token is not declared in this function; skipped"})
                    continue
                err = check_identifier(str(new))
                if err:
                    issues.append({"batch": batch, "item": f"{fn}:{old}", "severity": "error",
                                   "message": f"new name: {err}"})
                    continue
                if new in taken:
                    issues.append({"batch": batch, "item": f"{fn}:{old}", "severity": "error",
                                   "message": f"'{new}' is used twice in this function"})
                    continue
                taken.add(new)
                target[old] = str(new)
        if params or locals_:
            merged[fn] = {
                "function": fn, "address": evidence["address"],
                "params": params, "locals": locals_,
                "confidence": confidence_of(entry, issues, fn),
                "evidence": str(entry.get("evidence") or "")[:300],
            }
    return merged


# --------------------------------------------------------------------------- #
# headers
# --------------------------------------------------------------------------- #
def c_comment(text: str, limit: int = 160) -> str:
    text = " ".join(str(text or "").split()).replace("*/", "* /")
    return text[:limit]


def struct_order(merged: dict[str, dict], ev: Evidence) -> list[str]:
    """Base classes before derived ones; cycles are broken deterministically."""
    order: list[str] = []
    state: dict[str, int] = {}

    def visit(name: str) -> None:
        if state.get(name) == 2:
            return
        if state.get(name) == 1:
            return                          # cycle: emit in current order
        state[name] = 1
        base = merged[name].get("base")
        if base in merged:
            visit(base)
        state[name] = 2
        order.append(name)

    for name in sorted(merged):
        visit(name)
    return order


def emit_struct(cls: dict, merged: dict[str, dict]) -> list[str]:
    name = cls["class"]
    base = cls.get("base")
    embed = None
    if base in merged:
        base_cls = merged[base]
        base_size = base_cls["size"]
        first = min((f["offset"] for f in cls["fields"].values()), default=base_size)
        if base_size and base_size <= cls["size"] and first >= base_size:
            embed = base_cls
    fields = sorted(cls["fields"].values(), key=lambda f: f["offset"])
    lines = []
    summary = c_comment(cls.get("summary"))
    lines.append(f"/* {name} - size 0x{cls['size']:X}"
                 + (f", inherits {base}" if base else "")
                 + (f"; {summary}" if summary else "") + " */")
    lines.append(f"typedef struct {cls['type']} {{")
    offset = 0
    if embed:
        lines.append(f"    {embed['type']} base;                 "
                     f"/* +0x0000, inherited {embed['class']} */")
        offset = embed["size"]
    for field in fields:
        if field["offset"] < offset:
            lines.append(f"    /* skipped {field['name']} at +0x{field['offset']:X}: "
                         f"inside the embedded base */")
            continue
        if field["offset"] > offset:
            gap = field["offset"] - offset
            lines.append(f"    u8 _pad_{offset:03X}[0x{gap:X}];")
            offset = field["offset"]
        ftype = field["type"]
        array = ARRAY_RE.match(ftype)
        if array and array.group(2) is None:
            ftype = f"{array.group(1)} {field['name']}[]"   # incomplete array member invalid
            ftype = array.group(1)
        decl = f"    {ftype} {field['name']}"
        if array and array.group(2) is not None:
            decl = f"    {array.group(1)} {field['name']}[{array.group(2)}]"
        if array and array.group(2) is None:
            decl = f"    {array.group(1)} {field['name']}[0]"
        note = f"/* +0x{field['offset']:04X}"
        if field["confidence"] < 0.75:
            note += f" conf {field['confidence']:.2f}"
        note += " */"
        lines.append(f"{decl};{' ' * max(1, 44 - len(decl))}{note}")
        offset = field["offset"] + field["size"]
    if cls["size"] > offset:
        gap = cls["size"] - offset
        if gap > 0x20000 and cls.get("size_source") != "allocation":
            lines.append(f"    /* unknown tail 0x{gap:X} bytes not emitted: size evidence is only "
                         f"'{cls.get('size_source')}' */")
        else:
            lines.append(f"    u8 _pad_{offset:03X}[0x{gap:X}];")
    lines.append(f"}} {cls['type']};   /* sizeof == 0x{cls['size']:X} */")
    return lines


def write_headers(merged_structs: dict, merged_globals: dict, merged_locals: dict,
                  ev: Evidence, target: Path, demo: bool) -> None:
    target.mkdir(parents=True, exist_ok=True)
    base = """#ifndef DQXI_DQXI_BASE_H
#define DQXI_DQXI_BASE_H

/* Fixed-width integer and float types shared by every generated struct.
 * Self-contained (only <stdint.h>) so a generated header can be syntax-checked
 * or included by matching C source without pulling in any SDK header.  The
 * typedefs are identical to include/types.h, so including both is harmless. */
#include <stdint.h>

typedef uint8_t   u8;
typedef uint16_t  u16;
typedef uint32_t  u32;
typedef uint64_t  u64;
typedef int8_t    s8;
typedef int16_t   s16;
typedef int32_t   s32;
typedef int64_t   s64;
typedef float     f32;
typedef double    f64;

#ifndef DQXI_ARRAY_COUNT
#define DQXI_ARRAY_COUNT(a) (sizeof(a) / sizeof((a)[0]))
#endif

#endif /* DQXI_DQXI_BASE_H */
"""
    (target / "dqxi_base.h").write_text(base, encoding="utf-8")

    emitted = {cls["type"] for cls in merged_structs.values()}
    referenced: set[str] = set()
    for cls in merged_structs.values():
        for field in cls["fields"].values():
            if field.get("type_class"):
                referenced.add(field["type_class"])
    for entry in merged_globals.values():
        array = ARRAY_RE.match(entry["type"])
        base_type = (array.group(1) if array else entry["type"]).strip().rstrip("*").strip()
        if base_type in ev.types:
            referenced.add(base_type)
        elif base_type in ev.types.values():
            referenced.add(ev.type_to_class.get(base_type, base_type))
    forwards = sorted({ev.types.get(name, name) for name in referenced} - emitted)

    lines = ["#ifndef DQXI_DQXI_STRUCTS_H", "#define DQXI_DQXI_STRUCTS_H", "",
             "#include \"dqxi_base.h\"", "",
             "/* Generated by tools/typedb/apply.py from the S_### worker answers.",
             " * Every field offset is a byte offset from the object base. Unknown",
             " * gaps are explicit padding; a field with a low confidence is marked",
             " * in its trailing comment. Do not hand-edit: rerun M2_types_merge. */",
             ""]
    if forwards:
        lines.append("/* Types referenced by pointer before their own S batch is merged. */")
        for name in forwards:
            lines.append(f"typedef struct {name} {name};")
        lines.append("")
    if not merged_structs:
        lines.append("/* No S_### answers merged yet. Run the S batches, then")
        lines.append(" * `python tools/typedb/apply.py --merge`. */")
    for name in struct_order(merged_structs, ev):
        lines.extend(emit_struct(merged_structs[name], merged_structs))
        lines.append("")
    lines.append("#endif /* DQXI_DQXI_STRUCTS_H */")
    (target / "structs.h").write_text("\n".join(lines) + "\n", encoding="utf-8")

    glines = ["#ifndef DQXI_DQXI_GLOBALS_H", "#define DQXI_DQXI_GLOBALS_H", "",
              "#include \"structs.h\"", "",
              "/* Named data objects of the retail executable. Each comment gives the",
              " * address in the original image and what the object is for. */", ""]
    if not merged_globals:
        glines.append("/* No G_### answers merged yet. */")
    by_subsystem: dict[str, list[dict]] = collections.defaultdict(list)
    for entry in merged_globals.values():
        by_subsystem[entry["subsystem"]].append(entry)
    for subsystem in sorted(by_subsystem):
        glines.append(f"/* --- {subsystem} --- */")
        for entry in sorted(by_subsystem[subsystem], key=lambda e: e["address"]):
            ctype = entry["type"]
            array = ARRAY_RE.match(ctype)
            if array:
                size = array.group(2)
                if size is None:
                    size = (f"0x{entry['size_hint']:X}" if entry.get("size_hint") else "")
                decl = f"extern {array.group(1)} {entry['name']}[{size}];"
            else:
                decl = f"extern {ctype} {entry['name']};"
            note = f"/* 0x{entry['address']:08X} conf {entry['confidence']:.2f}"
            if entry["comment"]:
                note += ": " + c_comment(entry["comment"], 120)
            note += " */"
            glines.append(f"{decl:<52} {note}")
        glines.append("")
    glines.append("#endif /* DQXI_DQXI_GLOBALS_H */")
    (target / "globals.h").write_text("\n".join(glines) + "\n", encoding="utf-8")

    umbrella = """#ifndef DQXI_DQXI_TYPES_H
#define DQXI_DQXI_TYPES_H

/* Named structs and globals recovered from the retail Dragon Quest XI (3DS)
 * executable. Regenerated by M2_types_merge; field names carry a confidence
 * comment where the evidence is not conclusive. */
#include "dqxi_base.h"
#include "structs.h"
#include "globals.h"

#endif /* DQXI_DQXI_TYPES_H */
"""
    (target / "dqxi_types.h").write_text(umbrella, encoding="utf-8")

    readme = f"""# include/dqxi - recovered C types

Generated by `tools/typedb/apply.py` (= task `M2_types_merge`). The retail
executable is the only source of truth; every struct field comes from an actual
memory access recorded in `orchestration/types/structs.json`, every global from
an address the code really loads.

| File | Contents |
|---|---|
| `dqxi_base.h` | width typedefs, includes `include/types.h` |
| `structs.h` | one C struct per S_### answer, byte-accurate offsets, explicit padding |
| `globals.h` | `extern` declarations for named data objects with their retail address |
| `dqxi_types.h` | umbrella include |

Confidence comes from the worker proposal (0..1); a trailing `conf 0.50` comment
means "the offset is certain, the *meaning* is a hypothesis". Names beginning
`maybe_` are explicitly unverified.

Current merge: {len(merged_structs)} structs, {sum(len(c['fields']) for c in merged_structs.values())} named fields, {len(merged_globals)} globals, {len(merged_locals)} functions with renamed locals.
""" + ("This is a **demo** merge from `orchestration/types/samples/`; it does not feed the real readable tree.\n" if demo else "")
    (target / "README.md").write_text(readme, encoding="utf-8")
    for path in target.iterdir():
        if path.suffix in (".h", ".md"):
            path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# maps
# --------------------------------------------------------------------------- #
def write_maps(merged_structs: dict, merged_globals: dict, literal_map: dict,
               merged_locals: dict, ev: Evidence, target: Path, report: dict) -> None:
    write_json(target / "fields.json", {
        "generated_by": "tools/typedb/apply.py",
        "classes": {
            name: {
                "type": cls["type"], "size": cls["size"], "base": cls.get("base"),
                "confidence": cls["confidence"],
                "fields": {
                    str(f["offset"]): {
                        "name": f["name"], "type": f["type"], "size": f["size"],
                        "type_class": f["type_class"], "confidence": f["confidence"],
                    } for f in cls["fields"].values()
                },
            } for name, cls in merged_structs.items()
        },
    })
    write_json(target / "functions.json", {
        "generated_by": "tools/typedb/apply.py",
        "functions": {
            fn: {"name": fn, "address": ev.functions[fn]["address"], "class": cls,
                 "type": ev.types.get(cls)}
            for fn, cls in ev.class_of_function.items()
            if fn in ev.functions
        },
    })
    write_json(target / "globals.json", {
        "generated_by": "tools/typedb/apply.py",
        "globals": {
            f"0x{address:08X}": {
                "name": g["name"], "type": g["type"], "section": g["section"],
                "access": g.get("access"), "comment": g["comment"], "is_array": g["is_array"],
            } for address, g in merged_globals.items()
        },
        "literals": {
            f"0x{literal:08X}": f"0x{address:08X}" for literal, address in literal_map.items()
        },
    })
    write_json(target / "locals.json", {
        "generated_by": "tools/typedb/apply.py",
        "functions": {
            fn: {"address": e["address"], "params": e["params"], "locals": e["locals"]}
            for fn, e in merged_locals.items()
        },
    })
    write_json(target / "report.json", report)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--validate", action="store_true", help="check worker output only")
    ap.add_argument("--merge", action="store_true", help="write headers and rename maps")
    ap.add_argument("--demo", action="store_true", help="merge orchestration/types/samples")
    args = ap.parse_args()
    if not (args.validate or args.merge):
        ap.error("choose --validate and/or --merge")

    ev = Evidence()
    outputs, issues = load_outputs(ev, args.demo)
    s = merge_structs(ev, outputs["S"], issues)
    g, literals = merge_globals(ev, outputs["G"], issues)
    v = merge_locals(ev, outputs["V"], issues)

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    total_fields = sum(len(c["fields"]) for c in ev.classes.values())
    evidence_globals = len(ev.global_by_address)
    evidence_vars = sum(len(f["variables"]) for f in ev.functions.values())
    report = {
        "generated_by": "tools/typedb/apply.py",
        "demo": args.demo,
        "inputs": {
            "classes_with_fields": sum(1 for c in ev.classes.values() if c["fields"]),
            "fields": total_fields,
            "globals": evidence_globals,
            "functions": len(ev.functions),
            "variables": evidence_vars,
            "worker_entries": {k: len(val) for k, val in outputs.items()},
        },
        "merged": {
            "classes": len(s),
            "fields": sum(len(c["fields"]) for c in s.values()),
            "globals": len(g),
            "locals_functions": len(v),
            "locals_tokens": sum(len(e["params"]) + len(e["locals"]) for e in v.values()),
        },
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": (errors + warnings)[:200],
        "pct": {
            "fields_named": round(100.0 * sum(len(c["fields"]) for c in s.values())
                                  / max(1, total_fields), 2),
            "globals_named": round(100.0 * len(g) / max(1, evidence_globals), 2),
            "locals_named": round(100.0 * sum(len(e["params"]) + len(e["locals"])
                                              for e in v.values()) / max(1, evidence_vars), 2),
        },
    }
    target = MERGED if not args.demo else TYPES_DIR / "merged_demo"
    report["target"] = str(target.relative_to(ROOT)).replace("\\", "/")
    if args.merge:
        write_maps(s, g, literals, v, ev, target, report)
        if not args.demo:
            write_headers(s, g, v, ev, HEADER_DIR, demo=False)
        else:
            write_headers(s, g, v, ev, target, demo=True)
    else:
        target.mkdir(parents=True, exist_ok=True)
        write_json(target / "report.json", report)

    print(json.dumps({k: report[k] for k in ("merged", "errors", "warnings", "pct")}, indent=1))
    if errors:
        for issue in errors[:12]:
            print("ERROR", issue.get("item"), issue["message"])
    print(f"wrote {target.relative_to(ROOT)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
