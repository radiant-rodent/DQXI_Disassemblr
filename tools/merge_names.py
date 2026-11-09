#!/usr/bin/env python3
"""Merge every naming proposal into the project's symbol files and readable C.

The N_### workers write ``orchestration/naming/out/N_###.json``. This tool is the
single place that turns those proposals into the artefacts a modder actually opens:

  * ``symbols.json`` / ``symbols_recovered.json`` - name, signature, summary, confidence
  * ``decomp/ghidra/functions_merged.jsonl`` and ``functions_index.json`` - the catalog
  * ``decomp/readable/`` - regenerated pseudo-C with real names, parameter names and a
    documentation comment per function (the bodies themselves are never edited)
  * ``include/recovered_types.h`` - opaque forward declarations for the struct/class
    types that several independent proposals agree on

Validation is deliberately strict but non-destructive: invalid C identifiers, unknown
addresses, duplicate names, mismatched signature names, malformed parameter maps and
non-canonical addresses are repaired and reported; nothing in ``asm/`` or ``src/`` is
touched, so the bit-matching build remains the canonical executable.

The second ("refine") pass lives in ``orchestration/naming/refine/out/R_*.json``. It is
overlaid on the first-pass proposals by address, so refined names win while untouched
addresses keep their M1 values. ``--refine`` makes that mode explicit; for backwards
compatibility with the M1 command line the overlay is also applied without the flag.
Every refined row keeps ``change``/``previous_name``/``previous_confidence`` so the
history stays auditable in the catalog and in ``symbols.json``.

Usage:
    python tools/merge_names.py                 # validate, merge, regenerate readable C
    python tools/merge_names.py --refine        # same, explicit M1b refine mode
    python tools/merge_names.py --check         # validate and print only, write nothing
    python tools/merge_names.py --no-readable   # symbol/index merge only (fast)
    python tools/merge_names.py --workers 8
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import textwrap
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMING = ROOT / "orchestration" / "naming" / "out"
REFINE = ROOT / "orchestration" / "naming" / "refine" / "out"
SYMBOLS = ROOT / "symbols.json"
RECOVERED = ROOT / "symbols_recovered.json"
GHIDRA = ROOT / "decomp" / "ghidra"
READABLE = ROOT / "decomp" / "readable"
INCLUDE = ROOT / "include"

sys.path.insert(0, str(ROOT / "tools"))
import readable_c  # noqa: E402  (the existing readability pass is reused, not copied)

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PLACEHOLDER = re.compile(r"^(?:maybe_|func_|FUN_|thunk_|LAB_|DAT_|sub_|undefined)")
RESERVED = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long",
    "register", "restrict", "return", "short", "signed", "sizeof", "static", "struct",
    "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "_Bool",
    "bool", "true", "false", "this", "class", "new", "delete",
}
# Parameters whose value is a description rather than an identifier. The first word is
# still useful (``controller (actor at f_28)`` -> ``controller``), but these words are not.
NOT_A_NAME = {"none", "n/a", "na", "null", "unused", "unknown", "in", "out", "arg", "a"}
PRIMITIVE_TYPES = {
    "void", "char", "short", "int", "long", "float", "double", "signed", "unsigned",
    "bool", "_Bool", "size_t", "ssize_t", "intptr_t", "uintptr_t", "ptrdiff_t",
    "wchar_t", "wint_t", "intmax_t", "uintmax_t", "time_t", "clock_t", "off_t",
    "char16_t", "char32_t",
    "int8_t", "int16_t", "int32_t", "int64_t", "uint8_t", "uint16_t", "uint32_t",
    "uint64_t", "u8", "u16", "u32", "u64", "s8", "s16", "s32", "s64", "f32", "f64",
    "uint", "ushort", "ulong", "undefined", "undefined1", "undefined2", "undefined4",
    "undefined8", "byte", "code", "int3", "uint3", "uint4", "longlong", "ulonglong",
    "float4", "wchar16", "wchar32", "FILE", "va_list", "BOOL", "DWORD", "HANDLE",
    "SQInteger", "SQBool", "SQFloat", "HSQUIRRELVM", "SqVM", "Result", "Handle",
}
SIG_RX = re.compile(
    r"^(?P<ret>.*?)\b(?P<fname>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<args>.*)\)\s*;?\s*$",
    re.S,
)
DATA_RX = re.compile(r"^(?P<type>.*?)\b(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;?$", re.S)


# --------------------------------------------------------------------------------------
# loading and validation
# --------------------------------------------------------------------------------------
def read_json(path: Path):
    """Read JSON, tolerating the cp1252 punctuation one old batch contains."""
    raw = path.read_bytes()
    try:
        return json.loads(raw.decode("utf-8")), "utf-8"
    except UnicodeDecodeError:
        return json.loads(raw.decode("cp1252")), "cp1252"


def norm_addr(value) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text.startswith("0x"):
        text = text[2:]
    text = text.lstrip("0") or "0"
    return int(text, 16)


def addr_key(value) -> str:
    return f"{norm_addr(value):08x}"


def addr_symbol(value) -> str:
    return f"0x{norm_addr(value):08X}"


def is_real_name(name: str | None) -> bool:
    return bool(name) and not PLACEHOLDER.match(str(name))


def split_top(text: str) -> list[str]:
    """Split a C parameter list on top-level commas only."""
    out, cur, depth = [], "", 0
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [p.strip() for p in out if p.strip()]


def split_param(param: str) -> tuple[str, str]:
    """``const char * name`` -> (``const char *``, ``name``).

    Returns an empty name for unnamed/primitive/variadic parameters. Function-pointer
    parameters are kept whole as a type; they are rare in the proposals.
    """
    param = param.strip()
    if not param or param == "void" or param == "...":
        return param, ""
    # Function pointer: int (*cmp)(const void*, const void*) -> type int (*)(...), name cmp.
    fp = re.match(r"^(.*?\(\s*\*\s*)([A-Za-z_]\w*)?\s*(\)\s*\(.*\))$", param, re.S)
    if fp:
        name = fp.group(2) or ""
        type_part = fp.group(1).strip() + fp.group(3)
        return type_part, name
    if "(*" in param or "(*" in param.replace(" ", ""):
        return param, ""
    m = re.search(r"([A-Za-z_]\w*)\s*(\[[^\]]*\])?\s*$", param)
    if not m:
        return param, ""
    name = m.group(1)
    type_part = param[: m.start(1)].strip()
    if not type_part or name in RESERVED or name in PRIMITIVE_TYPES:
        return param, ""
    if m.group(2):
        type_part = (type_part + " " + m.group(2)).strip()
    return type_part, name


def generic_param(name: str) -> bool:
    return not name or bool(re.fullmatch(r"(?:arg|param_?|a|unused)\d*", name))


def clean_ident(raw, fallback: str, used: set[str]) -> str:
    """Turn a proposal's human-readable parameter description into a C identifier."""
    text = "" if raw is None else str(raw).strip()
    cand = None
    if IDENT.match(text) and text not in RESERVED and text not in NOT_A_NAME and not generic_param(text):
        cand = text
    else:
        m = re.match(r"[A-Za-z_]\w*", text)
        if (m and m.group(0) not in RESERVED and m.group(0).lower() not in NOT_A_NAME
                and not generic_param(m.group(0))):
            cand = m.group(0)
    if cand:
        if cand.isupper() and len(cand) > 2:  # SARC reader -> sarc reader
            cand = cand.lower()
        cand = re.sub(r"[^A-Za-z0-9_]", "_", cand).strip("_")
    if not cand or cand[0].isdigit() or cand in RESERVED:
        cand = re.sub(r"[^A-Za-z0-9_]", "_", fallback or "arg")
    if not cand or cand[0].isdigit():
        cand = "arg"
    base, n = cand, 2
    while cand in used:
        cand = f"{base}{n}"
        n += 1
    used.add(cand)
    return cand


def clean_type(text: str) -> str:
    """Drop placeholder ``maybe_`` prefixes from a type spelling.

    Workers sometimes left a stale ``maybe_`` token in the return type (``void* maybe_ Name``)
    or prefixed a type with it. Neither is a valid C type, and the function name itself is
    handled separately, so strip it without touching anything else.
    """
    text = re.sub(r"\bmaybe_(?=[A-Za-z_])", "", str(text))
    text = re.sub(r"\bmaybe_\s*", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_signature(prop: dict):
    """Return (kind, return_type, param_types, param_names_from_signature, raw_params).

    kind is ``function``, ``data`` or ``broken``. The proposal's own name always wins;
    478 proposals carry a stale ``maybe_`` prefix (or none) in the signature text.
    """
    sig = str(prop.get("signature") or "").strip()
    name = prop["name"]
    if "(" not in sig or ")" not in sig:
        m = DATA_RX.match(sig)
        typ = (m.group("type").strip() if m else "") or "void*"
        typ = re.sub(r"^\s*/\*\s*data\s*\*/\s*", "", typ).strip()
        typ = re.sub(r"^extern\s+", "", typ).strip()
        typ = re.sub(r"\bconst\b", "const", typ)
        return "data", clean_type(typ) or "void*", [], [], []
    m = SIG_RX.match(sig)
    if not m:
        return "broken", "void", [], [], []
    prop["_sig_fname"] = m.group("fname")
    ret = re.sub(r"\s+", " ", m.group("ret")).strip()
    ret = clean_type(ret)
    if not ret:
        ret = "void"
    raw_params = split_top(m.group("args"))
    if raw_params and raw_params[0].strip() == "void" and len(raw_params) == 1:
        raw_params = []
    ptypes, pnames = [], []
    for raw in raw_params:
        typ, nm = split_param(raw)
        ptypes.append(clean_type(typ))
        pnames.append(nm)
    return "function", ret, ptypes, pnames, raw_params


def build_param_map(prop: dict, ptypes: list[str], pnames: list[str], issues: Counter):
    """Choose one valid identifier per parameter and map it onto the Ghidra body names."""
    n = len(ptypes)
    if n == 0:
        return [], {}, issues
    supplied = prop.get("params")
    if not isinstance(supplied, dict):
        # Some refine workers used the equivalent "param_names" spelling (R_K01).
        supplied = prop.get("param_names")
    if not isinstance(supplied, dict):
        supplied = {}
    pos: dict[int, tuple[str, object]] = {}
    leftovers: list[tuple[str, object]] = []
    for key, value in supplied.items():
        key = str(key)
        m = re.fullmatch(r"(?:param_|arg|a)(\d+)", key)
        if m and 1 <= int(m.group(1)) <= n:
            pos[int(m.group(1)) - 1] = (key, value)
            continue
        if key in pnames:
            pos[pnames.index(key)] = (key, value)
            continue
        if key == "self" and 0 not in pos:
            pos[0] = (key, value)
            continue
        leftovers.append((key, value))
    # Fully descriptive maps such as {"self":..., "ctx":..., "mode":...} are positional.
    free = [i for i in range(n) if i not in pos]
    if leftovers and len(leftovers) <= len(free):
        for idx, item in zip(free, leftovers):
            pos[idx] = item
    names, mapping, used = [], {}, set()
    for i in range(n):
        sig_name = pnames[i] if i < len(pnames) else ""
        sig_ok = bool(sig_name and IDENT.match(sig_name) and sig_name not in RESERVED
                      and not generic_param(sig_name))
        fallback = sig_name if sig_ok else f"arg{i + 1}"
        if i in pos:
            _raw_key, raw_value = pos[i]
            raw_ok = (isinstance(raw_value, str) and IDENT.match(raw_value.strip())
                      and raw_value.strip() not in RESERVED
                      and raw_value.strip().lower() not in NOT_A_NAME
                      and not generic_param(raw_value.strip()))
            if not raw_ok:
                issues["param_identifier_repaired"] += 1
            # A real identifier in the map wins (e.g. ctxOut); a prose description does
            # not override a good name already present in the signature (e.g. cmp).
            source = raw_value if raw_ok or not sig_ok else sig_name
            chosen = clean_ident(source, fallback, used)
        else:
            chosen = clean_ident(sig_name if sig_ok else None, fallback, used)
        if ptypes[i] == "...":
            names.append("")  # variadic tail: never give it a name
            continue
        names.append(chosen)
        # readable_c.rewrite emits `self` for param_1 when it looks like an object,
        # and `argN` for every other parameter.
        mapping[f"arg{i + 1}"] = chosen
        if i == 0:
            mapping["self"] = chosen
    if len(supplied) != n:
        issues["param_count_mismatch"] += 1
    return names, mapping, issues


def canonical_signature(ret: str, name: str, ptypes: list[str], pnames: list[str]) -> str:
    if not ptypes:
        params = "void"
    else:
        parts = []
        for typ, nm in zip(ptypes, pnames):
            typ = re.sub(r"\s+", " ", typ).strip()
            if typ and nm:
                if "(*)" in typ:
                    parts.append(typ.replace("(*)", f"(*{nm})", 1))
                else:
                    parts.append(f"{typ} {nm}")
            elif nm:
                parts.append(nm)
            else:
                parts.append(typ)
        params = ", ".join(parts)
    ret = re.sub(r"\s+", " ", ret).strip() or "void"
    return f"{ret} {name}({params})"


# --------------------------------------------------------------------------------------
# name allocation
# --------------------------------------------------------------------------------------
def allocate_names(props: list[dict], existing_names: dict[str, int]):
    """Return addr -> final name, plus the clash list.

    Rule: within a clash the higher-confidence proposal keeps the name; the others are
    suffixed ``_2``, ``_3``, ...  A name already used by a different address is always
    suffixed (there were no such cases in this dataset, but keep the rule explicit).
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for p in props:
        groups[p["name"]].append(p)
    final: dict[int, str] = {}
    clashes: list[dict] = []
    # name -> address. Keeping the owner makes the allocation idempotent: a suffix that
    # already belongs to this proposal is reused instead of escalating to _3 on a re-run.
    used: dict[str, int] = dict(existing_names)
    for name, group in groups.items():
        group.sort(key=lambda p: (-float(p["confidence"]), p["_addr"]))
        winner = group[0]
        owner = used.get(name)
        winner_ok = owner is None or owner == winner["_addr"]
        losers = group[1:] if winner_ok else group
        if winner_ok:
            final[winner["_addr"]] = name
            used[name] = winner["_addr"]
        for p in losers:
            suffix = 2
            while True:
                candidate = f"{name}_{suffix}"
                cand_owner = used.get(candidate)
                if ((cand_owner is None or cand_owner == p["_addr"])
                        and candidate not in groups):
                    break
                suffix += 1
            final[p["_addr"]] = candidate
            used[candidate] = p["_addr"]
            clashes.append({
                "address": addr_symbol(p["_addr"]),
                "original": name,
                "final": candidate,
                "confidence": p["confidence"],
                "kept_by": addr_symbol(winner["_addr"]) if winner_ok else None,
            })
    return final, clashes


# --------------------------------------------------------------------------------------
# symbol/index writes
# --------------------------------------------------------------------------------------
def merge_symbols(props: list[dict], index_by_addr: dict[int, dict]):
    data, _ = read_json(SYMBOLS)
    entries = data.setdefault("symbols", [])
    by_addr = {norm_addr(e["address"]): e for e in entries}
    for p in props:
        a = p["_addr"]
        e = by_addr.get(a)
        if e is None:
            e = {"address": addr_symbol(a)}
            entries.append(e)
            by_addr[a] = e
        row = index_by_addr.get(a, {})
        e.update({
            "address": addr_symbol(a),
            "name": p["_final_name"],
            "type": p["_type"],
            "mode": row.get("mode", p.get("mode", "arm")),
            "size": row.get("size", 0),
            "description": p["summary"],
            "source": p.get("_source", f"orchestration/naming/out/{p['_batch']}.json"),
            "signature": p["_signature"],
            "summary": p["summary"],
            "confidence": float(p["confidence"]),
            "batch": p["_batch"],
            "params": p["_param_names_map"],
            "evidence": p.get("evidence", ""),
        })
        if p.get("_refined"):
            e.update({k: p[k] for k in ("change", "previous_name", "previous_confidence") if k in p})
    entries.sort(key=lambda e: norm_addr(e["address"]))
    data["symbols"] = entries
    return data


def merge_recovered(props: list[dict]):
    data, _ = read_json(RECOVERED)
    out = {addr_symbol(norm_addr(k)): v for k, v in data.items()}
    for p in props:
        out[addr_symbol(p["_addr"])] = p["_final_name"]
    return {k: out[k] for k in sorted(out, key=norm_addr)}


def merge_jsonl(props_by_addr: dict[int, dict]):
    rows = []
    for line in (GHIDRA / "functions_merged.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        p = props_by_addr.get(norm_addr(row["address"]))
        if p:
            row.update({
                "name": p["_final_name"],
                "signature": p["_signature"],
                "summary": p["summary"],
                "confidence": float(p["confidence"]),
                "batch": p["_batch"],
                "params": p["_param_names_map"],
                "evidence": p.get("evidence", ""),
                "symbol_type": p["_type"],
            })
            if p.get("_refined"):
                # Keep the second-pass audit trail with the row it belongs to.
                for key in ("change", "previous_name", "previous_confidence"):
                    if key in p:
                        row[key] = p[key]
        elif re.search(r"\bparam_\d+\b", str(row.get("signature") or "")):
            # Seed rows never went through the proposal pipeline; still give their
            # unnamed parameters valid identifiers instead of Ghidra's param_N.
            row["signature"] = _normalize_signature(row["signature"])
        rows.append(row)
    return rows


def merge_index(props_by_addr: dict[int, dict], rows: list[dict]):
    data, _ = read_json(GHIDRA / "functions_index.json")
    functions = data.get("functions", [])
    row_by_addr = {norm_addr(r["address"]): r for r in rows}
    for f in functions:
        row = row_by_addr.get(norm_addr(f["address"]))
        if row:
            # Keep the catalog in step with functions_merged.jsonl for the seed names
            # too (one recovered entry had a name there but not in the index).
            f["name"] = row.get("name", f.get("name"))
            if row.get("signature"):
                f["signature"] = row["signature"]
            if row.get("summary"):
                f["summary"] = row["summary"]
        p = props_by_addr.get(norm_addr(f["address"]))
        if p:
            f.update({
                "name": p["_final_name"],
                "signature": p["_signature"],
                "summary": p["summary"],
                "confidence": float(p["confidence"]),
                "batch": p["_batch"],
            })
            if p.get("_refined"):
                for key in ("change", "previous_name", "previous_confidence"):
                    if key in p:
                        f[key] = p[key]
    named = sum(1 for f in functions if is_real_name(f.get("name")))
    documented = sum(1 for f in functions if is_real_name(f.get("name")) and f.get("summary"))
    data["functions"] = functions
    data["named_functions"] = named
    data["documented_functions"] = documented
    return data


# --------------------------------------------------------------------------------------
# readable C generation
# --------------------------------------------------------------------------------------
_NAMES: dict[int, str] = {}
_CALLERS: dict[str, set[str]] = {}
_CALLEES: dict[str, set[str]] = {}


def _worker_init(names, callers, callees):
    global _NAMES, _CALLERS, _CALLEES
    _NAMES, _CALLERS, _CALLEES = names, callers, callees


def _comment(lines: list[str]) -> str:
    out = ["/*"]
    for line in lines:
        line = _ascii(line)
        for part in textwrap.wrap(line, width=104, break_long_words=False,
                                  break_on_hyphens=False) or [""]:
            out.append(" * " + part.replace("*/", "* /"))
    out.append(" */")
    return "\n".join(out)


def _ascii(text: str) -> str:
    """Keep generated comments readable in every Windows editor/console."""
    table = {
        " \u2014 ": " - ", "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00a0": " ",
    }
    for src, dst in table.items():
        text = text.replace(src, dst)
    return text.encode("ascii", "replace").decode("ascii")


def _render(job: dict):
    src = GHIDRA / job["src_rel"]
    original = src.read_text(encoding="utf-8", errors="replace")
    before = readable_c.noise(original)
    text = readable_c.rewrite(original, _NAMES)
    # Ghidra occasionally emits func_0x00102820, which readable_c's address-only regex
    # does not see; resolve that spelling too.
    text = re.sub(
        r"\b(?:func|FUN|thunk_FUN)_0x([0-9A-Fa-f]{8})\b",
        lambda m: _NAMES.get(int(m.group(1), 16), m.group(0)),
        text,
    )
    # readable_c's field rewrite can consume the parenthesis of a call whose only
    # argument is `(ptr + 0xNN)`: `Foo(&self->f_60);` became `Foo&self->f_60;`.
    # Re-open and close the argument list around such a field address.
    text = re.sub(
        r"\b([A-Za-z_]\w*)&((?:[A-Za-z_]\w*->f_[0-9a-f]+)+)",
        r"\1(&\2)",
        text,
    )

    # Extract the signature from the Ghidra header as a fallback for old recovered
    # functions that never got one in functions_merged.jsonl.
    sig = (job.get("signature") or "").strip().rstrip(";").strip()
    if not sig:
        m = re.search(r"^ \* Signature:\s*(.+)$", original, re.M)
        if m:
            sig = m.group(1).strip().rstrip(";")
    if not sig:
        sig = f"void {job['name']}(void)"

    doc = _comment([
        f"{job['name']} — {job.get('summary') or 'no recovered summary yet'}",
        "",
        f"Recovered: {job.get('batch') or 'seed symbol'}, confidence "
        f"{float(job.get('confidence', 1.0)):.2f}, address 0x{job['addr']:08X} "
        f"({job.get('mode', 'arm')}, {job.get('size', 0)} bytes).",
        f"Signature: {sig}",
        f"Evidence: {job.get('evidence') or 'existing symbol / Ghidra export.'}",
        f"Source: {job['src_rel']} (Ghidra pseudocode; the body is unchanged).",
    ])
    doc = re.sub(r"\n \* \n", "\n *\n", doc)

    # Replace Ghidra's short header with the human-readable doc block.
    text, n = re.subn(
        r"/\*\n \* DQXI 3DS native function.*?\*/\n", lambda _m: doc + "\n", text,
        count=1, flags=re.S
    )
    if n == 0:
        # No header found: insert the doc after the readable_c banner.
        end = text.find("*/")
        if end != -1:
            text = text[: end + 2] + "\n" + doc + text[end + 2:]
        else:
            text = doc + "\n" + text

    # Replace the function definition with the typed, named signature.
    head, sep, body = text.partition("\n{")
    if sep:
        cut = head.rfind("*/")
        if cut != -1:
            head = head[: cut + 2] + "\n" + sig + "\n"
        else:
            head = sig + "\n"
        text = head + "{" + body

    # Rename the generic parameter names in the body. Collisions with existing locals are
    # left as argN rather than producing a wrong variable reference.
    body_start = text.find("\n{")
    body = text[body_start:] if body_start != -1 else text
    tokens = set(re.findall(r"\b[A-Za-z_]\w*\b", body))
    renames = []
    for src_name, target in sorted(job.get("param_map", {}).items()):
        if not target or src_name == target:
            continue
        if src_name in tokens and target in tokens and target not in (src_name, "self"):
            continue
        renames.append((src_name, target))
    for i, (src_name, target) in enumerate(renames):
        body = re.sub(rf"\b{re.escape(src_name)}\b", f"__PARAM_{i}__", body)
    for i, (_src_name, target) in enumerate(renames):
        body = body.replace(f"__PARAM_{i}__", target)
    text = (text[:body_start] if body_start != -1 else "") + body

    out = READABLE / job["out_rel"]
    out.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(5):
        try:
            out.write_text(text, encoding="utf-8")
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.2)
    return before, readable_c.noise(text)


def generate_readable(rows: list[dict], proposals: dict[int, dict], workers: int):
    """Regenerate decomp/readable from the updated catalog."""
    names = {
        norm_addr(r["address"]): r["name"]
        for r in rows
        if r.get("status") == "ok"
        and not re.match(r"^(?:func_|FUN_|thunk_|LAB_|DAT_|sub_|undefined)", str(r.get("name") or ""))
    }
    files = sorted((GHIDRA / "functions").glob("*.c")) + sorted((GHIDRA / "recovered").glob("*.c"))
    # symbols.json also holds names for covered_by entries that have no catalog row of
    # their own; let calls to them use the recovered name too.
    sym_data, _ = read_json(SYMBOLS)
    symbol_by_addr = {norm_addr(e["address"]): e for e in sym_data.get("symbols", [])}
    for addr, entry in symbol_by_addr.items():
        if addr not in names and is_real_name(entry.get("name")):
            names[addr] = entry["name"]
    callers, callees = readable_c.call_graph(files, names)

    # The index uses paths relative to decomp/ghidra; build the address for each file.
    row_by_file = {r["file"]: r for r in rows if r.get("file")}
    jobs = []
    skipped = 0
    for f in files:
        rel = str(f.relative_to(GHIDRA)).replace("\\", "/")
        row = row_by_file.get(rel)
        if not row:
            m = re.search(r"_([0-9a-fA-F]{8})\.c$", f.name)
            if not m:
                skipped += 1
                continue
            addr = int(m.group(1), 16)
            name = f.name.rsplit("_", 1)[0]
            row = {"address": f"{addr:08x}", "name": name, "status": "ok"}
        else:
            addr = norm_addr(row["address"])
        p = proposals.get(addr)
        if p and p["_type"] in ("data", "label"):
            skipped += 1
            continue
        symbol = symbol_by_addr.get(addr, {})
        name = p["_final_name"] if p else row.get("name") or f.stem
        sig = p["_signature"] if p else (row.get("signature") or symbol.get("signature") or "")
        sig = _normalize_signature(sig)
        param_map = p["_param_map"] if p else _signature_param_map(sig)
        summary = p["summary"] if p else (_existing_summary(row, p) or symbol.get("description", ""))
        evidence = p.get("evidence", "") if p else symbol.get("evidence", "")
        out_rel = f"{'recovered' if rel.startswith('recovered/') else 'functions'}/{name}_{addr:08x}.c"
        jobs.append({
            "src_rel": rel,
            "out_rel": out_rel,
            "addr": addr,
            "name": name,
            "signature": sig,
            "summary": summary,
            "evidence": evidence,
            "confidence": float(p["confidence"]) if p else 1.0,
            "batch": p["_batch"] if p else "",
            "mode": row.get("mode", "arm"),
            "size": row.get("size", 0),
            "param_map": param_map,
        })

    for sub in ("functions", "recovered"):
        d = READABLE / sub
        if d.is_dir():
            for old in d.glob("*.c"):
                try:
                    old.unlink()
                except PermissionError:
                    pass  # a scanner/editor holds it; retried after rendering
        else:
            d.mkdir(parents=True, exist_ok=True)

    before: Counter = Counter()
    after: Counter = Counter()
    if workers <= 1:
        _worker_init(names, callers, callees)
        for job in jobs:
            b, a = _render(job)
            before.update(b)
            after.update(a)
    else:
        with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init,
                                 initargs=(names, callers, callees)) as pool:
            for b, a in pool.map(_render, jobs, chunksize=64):
                before.update(b)
                after.update(a)
    return jobs, skipped, dict(before), dict(after)


def _signature_param_map(sig: str) -> dict[str, str]:
    m = SIG_RX.match(sig or "")
    if not m:
        return {}
    out = {}
    for i, raw in enumerate(split_top(m.group("args"))):
        _typ, nm = split_param(raw)
        if nm and not generic_param(nm):
            out[f"arg{i + 1}"] = nm
            if i == 0:
                out["self"] = nm
    return out


def _normalize_signature(sig: str) -> str:
    """Use readable types and non-placeholder parameter names in the definition line."""
    if not sig:
        return sig
    sig = readable_c.TYPE_RX.sub(lambda m: readable_c.TYPES[m.group(1)], sig)
    m = SIG_RX.match(sig)
    if not m:
        return sig
    raw = split_top(m.group("args"))
    if len(raw) == 1 and raw[0].strip() == "void":
        raw = []
    types, names = [], []
    for i, item in enumerate(raw):
        typ, nm = split_param(item)
        types.append(clean_type(typ))
        names.append(nm if nm and not generic_param(nm) else f"arg{i + 1}")
    return canonical_signature(clean_type(m.group("ret")) or "void", m.group("fname"), types, names)


def _existing_summary(row: dict, proposal: dict | None) -> str:
    if proposal:
        return proposal.get("summary", "")
    for key in ("summary", "description", "documentation", "comment", "doc"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


# --------------------------------------------------------------------------------------
# include/recovered_types.h
# --------------------------------------------------------------------------------------
def known_type_names() -> set[str]:
    known = set(PRIMITIVE_TYPES)
    paths = [p for p in sorted(INCLUDE.glob("*.h")) if p.name != "recovered_types.h"]
    paths += [GHIDRA / "dqxi_types.h", GHIDRA / "prelude.h"]
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        known.update(re.findall(r"\b(?:struct|enum|union)\s+([A-Za-z_]\w*)", text))
        known.update(re.findall(r"\btypedef\b[^;]*?\b([A-Za-z_]\w*)\s*;", text, re.S))
    return known


def base_type(_type: str) -> str | None:
    """Extract the user-defined base type from one parameter type."""
    text = re.sub(r"\b(?:const|volatile|struct|enum|union|signed|unsigned)\b", " ", _type)
    for token in re.findall(r"[A-Za-z_]\w*", text):
        if token in PRIMITIVE_TYPES:
            continue
        if token[0].isupper() or "_" in token:
            return token
    return None


def write_recovered_types(props: list[dict]) -> tuple[int, dict[str, int]]:
    counts: Counter = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for p in props:
        if p["_type"] != "function":
            continue
        for typ in p["_param_types"]:
            name = base_type(typ)
            if not name:
                continue
            counts[name] += 1
            if len(examples[name]) < 3:
                examples[name].append(p["_final_name"])
    known = known_type_names()
    wanted = {n: c for n, c in counts.items() if c >= 3 and n not in known and n not in RESERVED}
    lines = [
        "/* Recovered parameter types — generated by tools/merge_names.py.",
        " *",
        " * These are opaque forward declarations for struct/class types that appear in the",
        " * parameter lists of at least three independent naming proposals. They deliberately",
        " * do not claim a field layout: they give the recovered signatures and the readable C",
        " * a shared vocabulary while struct recovery continues.",
        " *",
        " * The number is how many named functions take the type; examples are function names.",
        " */",
        "#pragma once",
        "",
        "#ifndef DQXI_RECOVERED_TYPES_H",
        "#define DQXI_RECOVERED_TYPES_H",
        "",
    ]
    for name in sorted(wanted, key=lambda n: (-wanted[n], n)):
        lines.append(f"/* {wanted[name]:4d} use(s): {', '.join(examples[name])} */")
        lines.append(f"typedef struct {name} {name};")
        lines.append("")
    lines += ["#endif /* DQXI_RECOVERED_TYPES_H */", ""]
    path = INCLUDE / "recovered_types.h"
    path.write_text("\n".join(lines), encoding="utf-8")
    return len(wanted), wanted


def ensure_include() -> None:
    path = INCLUDE / "dqxi.h"
    text = path.read_text(encoding="utf-8")
    if '#include "recovered_types.h"' in text:
        return
    text = text.replace('#include "kernel.h"', '#include "kernel.h"\n#include "recovered_types.h"')
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def load_proposals():
    props, encodings, bad = [], Counter(), []
    for path in sorted(NAMING.glob("N_*.json")):
        data, enc = read_json(path)
        encodings[enc] += 1
        batch = path.stem
        if not isinstance(data, list):
            bad.append({"batch": batch, "reason": "top level is not a list"})
            continue
        for e in data:
            if not isinstance(e, dict):
                bad.append({"batch": batch, "reason": "entry is not an object"})
                continue
            try:
                addr = norm_addr(e["address"])
            except Exception:
                bad.append({"batch": batch, "reason": f"bad address {e.get('address')!r}"})
                continue
            name = str(e.get("name") or "").strip()
            if not IDENT.match(name) or name in RESERVED:
                bad.append({"batch": batch, "address": e.get("address"),
                            "reason": f"invalid C identifier {name!r}"})
                continue
            e = dict(e)
            e["name"] = name
            e["_addr"] = addr
            e["_batch"] = batch
            e["_encoding"] = enc
            props.append(e)
    refined = load_refined(props, encodings, bad)
    return props, encodings, bad, refined


def load_refined(props: list[dict], encodings: Counter, bad: list[dict]) -> Counter:
    """Overlay the second-pass (R_*) proposals on the first-pass ones, address by address.

    Every run starts again from all N_* files and then applies every R_* file, so the merge
    stays idempotent and later R batches can be added at any time. Rules (M1b):

    * an entry whose ``change`` is ``confirmed`` must be the previous name minus ``maybe_``;
      a violated entry is mechanically reclassified as ``corrected`` and counted;
    * ``confirmed`` below 0.5 confidence is refused and becomes ``kept_maybe``;
    * ``kept_maybe`` must keep confidence < 0.5 and the ``maybe_`` prefix (clamped if needed);
    * any surviving name below 0.5 keeps (or gets) the ``maybe_`` prefix;
    * ``_batch`` becomes the R batch; the original N batch stays in ``_n_batch`` for the
      coverage check, and the previous values stay on the row for audit.

    R_K01/R_S01 are scripted sweep overlays rather than batch files; they sort after
    ``R_###`` so they win when they deliberately correct an earlier batch entry.
    """
    stats: Counter = Counter()
    by_addr = {p["_addr"]: i for i, p in enumerate(props)}
    # R_* first, then the R2_* re-refinement round on top (a plain sort would put "R2_" before "R_")
    for path in sorted(REFINE.glob("R*_*.json"), key=lambda q: (int(re.match(r"R(\d*)_", q.stem).group(1) or 1), q.stem)):
        data, enc = read_json(path)
        encodings[enc] += 1
        if not isinstance(data, list):
            bad.append({"batch": path.stem, "reason": "top level is not a list"})
            continue
        for e in data:
            try:
                addr = norm_addr(e["address"])
                name = str(e.get("name") or "").strip()
                conf = float(e.get("confidence", 0))
            except Exception:
                bad.append({"batch": path.stem, "reason": f"bad entry {str(e)[:60]!r}"})
                continue
            if not IDENT.match(name) or name in RESERVED:
                bad.append({"batch": path.stem, "address": e.get("address"),
                            "reason": f"invalid C identifier {name!r}"})
                continue
            e = dict(e)
            change = str(e.get("change") or "")
            previous = str(e.get("previous_name") or "")

            # "confirmed" means exactly "the old guess was right": anything else is a
            # correction, even if the worker mislabelled it.
            if change == "confirmed":
                expected = previous[6:] if previous.startswith("maybe_") else previous
                if name != expected:
                    e["change"] = "corrected"
                    change = "corrected"
                    stats["confirmed_name_mismatch_as_corrected"] += 1

            # A kept_maybe row cannot claim confidence >= 0.5; honest rows never do.
            if change == "kept_maybe" and conf >= 0.5:
                conf = 0.49
                e["confidence"] = conf
                stats["kept_maybe_confidence_clamped"] += 1

            if conf < 0.5:
                if e.get("change") == "confirmed":
                    e["change"] = "kept_maybe"
                    change = "kept_maybe"
                    stats["confirmed_below_0.5_demoted"] += 1
                if not name.startswith("maybe_"):
                    name = "maybe_" + name
                    stats["maybe_prefix_added"] += 1
                    # keep the signature's function name in step with the name
                    if isinstance(e.get("signature"), str):
                        e["signature"] = e["signature"].replace(name[6:] + "(", name + "(", 1)

            i = by_addr.get(addr)
            old = props[i] if i is not None else {}
            # A refine entry may omit a field the R1 row already knew; keep the old value
            # instead of blanking the catalog. Params are special: a proposal that used the
            # `param_names` spelling must not inherit the stale `params` names from R1.
            for key in ("signature", "evidence", "summary"):
                if e.get(key) in (None, "") and old.get(key) not in (None, ""):
                    e[key] = old[key]
            if "params" not in e and "param_names" not in e:
                if old.get("params") not in (None, ""):
                    e["params"] = old["params"]
                elif old.get("param_names") not in (None, ""):
                    e["param_names"] = old["param_names"]
            e.update({
                "name": name,
                "_addr": addr,
                "_batch": path.stem,
                "_n_batch": old.get("_n_batch") or old.get("_batch", path.stem),
                "_encoding": enc,
                "_refined": True,
                "_source": f"orchestration/naming/refine/out/{path.name}",
            })
            e.setdefault("summary", old.get("summary", ""))
            stats[str(e.get("change", "unknown"))] += 1
            if i is None:
                by_addr[addr] = len(props)
                props.append(e)
                stats["not_in_first_pass"] += 1
            else:
                props[i] = e
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="validate and report only")
    ap.add_argument("--refine", action="store_true",
                    help="apply the R_* second-pass overlay (also the default; kept explicit for M1b)")
    ap.add_argument("--no-readable", action="store_true", help="skip decomp/readable regeneration")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    props, encodings, bad_props, refined = load_proposals()
    rows = [json.loads(line) for line in
            (GHIDRA / "functions_merged.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    index_by_addr = {norm_addr(r["address"]): r for r in rows}

    issues: Counter = Counter()
    for p in props:
        if str(p.get("address", "")).lower() != addr_symbol(p["_addr"]).lower():
            issues["address_reformatted"] += 1
        kind, ret, ptypes, pnames, _raw = parse_signature(p)
        p["_kind"] = kind
        p["_ret"] = ret
        p["_param_types"] = ptypes
        p["_sig_param_names"] = pnames
        if kind != "function":
            issues[f"signature_{kind}"] += 1
            p["_type"] = "data" if kind == "data" else "label"
            p["_param_names"] = []
            p["_param_map"] = {}
            if kind == "data":
                p["_signature"] = f"extern {ret} {p['name']};"
            else:
                p["_signature"] = f"void {p['name']}(void)"
        else:
            if p.get("_sig_fname") and p["_sig_fname"] != p["name"]:
                issues["signature_name_repaired"] += 1
            p["_type"] = "label" if "FalseEntry" in p["name"] else "function"
            names, mapping, issues = build_param_map(p, ptypes, pnames, issues)
            p["_param_names"] = names
            p["_param_map"] = mapping
            p["_signature"] = canonical_signature(ret, p["name"], ptypes, names)
            p["_param_names_map"] = {f"param_{i + 1}": n for i, n in enumerate(names)}
        p["_param_names_map"] = p.get("_param_names_map", {})
        if p["_addr"] not in index_by_addr:
            issues["address_not_in_index"] += 1

    # Names already in use by a seed symbol at a different address. Entries produced by
    # a previous run of this tool carry a "batch" field; ignore them so a rerun is
    # idempotent (otherwise the second run would suffix _2 to _3, _4, ...).
    existing_names: dict[str, int] = {}
    sym_data, _ = read_json(SYMBOLS)
    for e in sym_data.get("symbols", []):
        if is_real_name(e.get("name")) and not e.get("batch"):
            existing_names[e["name"]] = norm_addr(e["address"])
    for r in rows:
        if is_real_name(r.get("name")) and not r.get("batch"):
            existing_names.setdefault(r["name"], norm_addr(r["address"]))

    final, clashes = allocate_names(props, existing_names)
    for p in props:
        p["_final_name"] = final[p["_addr"]]
        if p["_final_name"] != p["name"]:
            if p["_type"] == "function":
                p["_signature"] = canonical_signature(
                    p["_ret"], p["_final_name"], p["_param_types"], p["_param_names"]
                )
            else:
                p["_signature"] = p["_signature"].replace(p["name"], p["_final_name"], 1)

    # Batch coverage: every address in the generated batch files must have a proposal.
    batch_missing = {}
    for path in sorted((ROOT / "orchestration" / "naming" / "batches").glob("N_*.txt")):
        wanted = set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#"):
                continue
            m = re.match(r"^(0x[0-9A-Fa-f]{8})\t", line)
            if m:
                wanted.add(norm_addr(m.group(1)))
        got = {p["_addr"] for p in props if p.get("_n_batch", p["_batch"]) == path.stem}
        if wanted - got:
            batch_missing[path.stem] = [addr_symbol(a) for a in sorted(wanted - got)]

    # Refine coverage: every address in an R_### batch file must have an R_* proposal.
    # R_K01/R_S01 are sweep overlays and have no batch file.
    refine_missing = {}
    refine_addrs = {p["_addr"] for p in props if p.get("_refined")}
    for path in sorted((ROOT / "orchestration" / "naming" / "refine" / "batches").glob("R*_*.txt")):
        wanted = set()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#"):
                continue
            m = re.match(r"^(0x[0-9A-Fa-f]{8})\t", line)
            if m:
                wanted.add(norm_addr(m.group(1)))
        if wanted - refine_addrs:
            refine_missing[path.stem] = [addr_symbol(a) for a in sorted(wanted - refine_addrs)]

    confidence = Counter(round(float(p["confidence"]), 1) for p in props)
    baseline_rows = [json.loads(line) for line in
                     (GHIDRA / "functions.jsonl").read_text(encoding="utf-8").splitlines()
                     if line.strip()]
    before_named = sum(1 for r in baseline_rows if is_real_name(r.get("name")))
    final_by_addr = {p["_addr"]: p["_final_name"] for p in props}

    def final_name(row: dict) -> str:
        return final_by_addr.get(norm_addr(row["address"]), str(row.get("name") or ""))

    after_named = sum(1 for r in rows if is_real_name(final_name(r)))
    before_maybe = sum(1 for r in rows if str(r.get("name", "")).startswith("maybe_"))
    after_maybe = sum(1 for r in rows if final_name(r).startswith("maybe_"))
    # The progress page already credits high-confidence proposals, so keep that number too.
    high_conf_named = sum(1 for p in props if is_real_name(p["_final_name"]) and float(p["confidence"]) >= 0.5)
    total = len(rows)
    skipped_readable = 0

    print("=" * 78)
    print("M1_merge_names — validation")
    print("=" * 78)
    print(f"proposals              {len(props):,} from {len({p['_batch'] for p in props})} batch(es)")
    print(f"encodings              {dict(encodings)}")
    print(f"bad proposal entries   {len(bad_props)}")
    print(f"unknown addresses      {issues['address_not_in_index']}")
    print(f"addresses reformatted  {issues['address_reformatted']} (e.g. N_049 had 0x2BB90C, not 0x002BB90C)")
    print(f"confidence histogram   {dict(sorted(confidence.items()))}")
    print(f"signature kinds        function={len(props) - issues['signature_data'] - issues['signature_broken']}, "
          f"data={issues['signature_data']}, broken={issues['signature_broken']}")
    print(f"signature names fixed  {issues['signature_name_repaired']} (stale maybe_/alias in the signature text)")
    print(f"param names repaired   {issues['param_identifier_repaired']} descriptive values -> C identifiers")
    print(f"param count mismatches {issues['param_count_mismatch']} function(s)")
    print(f"name clashes           {len(clashes)} (higher confidence kept the name)")
    print(f"batches missing        {batch_missing or 'none'}")
    print(f"refine batches missing {refine_missing or 'none'}")
    print(f"refined (R_*) entries  {sum(v for k, v in refined.items() if k in ('confirmed', 'corrected', 'kept_maybe', 'unknown')):,} {dict(refined)}")
    print(f"maybe_ before/after    {before_maybe:,} -> {after_maybe:,}")
    print(f"named before           {before_named:,} / {total:,} = {100.0 * before_named / total:.2f}% (M1 baseline)")
    print(f"named after            {after_named:,} / {total:,} = {100.0 * after_named / total:.2f}%")
    print(f"high-confidence named  {high_conf_named:,} (progress-page metric)")

    if args.check:
        return 0 if (not bad_props and not issues["address_not_in_index"]
                     and not batch_missing and not refine_missing) else 1

    # ---- write the catalog ---------------------------------------------------------
    symbols = merge_symbols(props, index_by_addr)
    recovered = merge_recovered(props)
    props_by_addr = {p["_addr"]: p for p in props}
    merged_rows = merge_jsonl(props_by_addr)
    index = merge_index(props_by_addr, merged_rows)

    SYMBOLS.write_text(json.dumps(symbols, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    RECOVERED.write_text(json.dumps(recovered, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    (GHIDRA / "functions_merged.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=True, separators=(",", ":")) for r in merged_rows) + "\n",
        encoding="utf-8",
    )
    (GHIDRA / "functions_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    n_types, type_counts = write_recovered_types(props)
    ensure_include()
    print(f"symbols.json           {len(symbols['symbols']):,} entries")
    print(f"symbols_recovered.json {len(recovered):,} entries")
    print(f"recovered_types.h      {n_types} new opaque type(s)")

    # ---- readable C -----------------------------------------------------------------
    if not args.no_readable:
        jobs, skipped_readable, before_noise, after_noise = generate_readable(
            merged_rows, props_by_addr, args.workers
        )
        print(f"readable C             {len(jobs):,} functions written, {skipped_readable} skipped")
        for key in sorted(before_noise, key=lambda k: -before_noise[k]):
            print(f"  {key:28} {before_noise[key]:8,} -> {after_noise.get(key, 0):8,}")

    print("\nDone. asm/ and src/ were not modified; run tools/build.py to re-check the bit-match.")
    return 0


LOCK_FILE = ROOT / "orchestration" / "locks" / "merge.lock"


def _pid_alive(pid: int) -> bool:
    import ctypes
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(h)
    return code.value == 259


def run_locked() -> int:
    """Only one writing merge at a time: the dispatcher, K1/K2, M1b and people all run this tool, and two
    merges rewriting decomp/readable at once corrupt each other. Waits up to 30 minutes for the other one;
    a lock whose process is gone (or older than an hour) is taken over. --check never writes, so no lock."""
    import time
    if "--check" in sys.argv:
        return main()
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + 30 * 60
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                owner = int(LOCK_FILE.read_text().strip() or 0)
                stale = not _pid_alive(owner) or time.time() - LOCK_FILE.stat().st_mtime > 3600
            except (OSError, ValueError):
                stale = True
            if stale:
                LOCK_FILE.unlink(missing_ok=True)
                continue
            if time.time() > deadline:
                print("merge lock held by another merge for 30 minutes; giving up", file=sys.stderr)
                return 2
            if int(time.time()) % 60 < 5:
                print(f"waiting for the other merge (pid {owner}) ...", flush=True)
            time.sleep(5)
    try:
        return main()
    finally:
        LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(run_locked())
