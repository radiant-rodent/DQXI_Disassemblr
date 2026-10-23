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

Nothing here is compiled; the bit-matching build keeps using asm/ and src/.

Usage:
    python tools/readable_c.py              # all functions (multi-process)
    python tools/readable_c.py --stats      # before/after noise counts only
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

TYPES = {
    "undefined8": "u64", "undefined4": "u32", "undefined2": "u16", "undefined1": "u8",
    "undefined": "u8", "ulonglong": "u64", "longlong": "s64", "uint": "u32", "ushort": "u16",
    "byte": "u8", "sbyte": "s8", "dword": "u32", "word": "u16", "qword": "u64",
}
TYPE_RX = re.compile(r"\b(" + "|".join(sorted(TYPES, key=len, reverse=True)) + r")\b")
UNNAMED_CALL = re.compile(r"\b(?:FUN|func|thunk_FUN)_([0-9A-Fa-f]{8})\b")
DAT = re.compile(r"\bDAT_([0-9a-fA-F]{8})\b")
TEMP = re.compile(r"\b(?:[a-z]{1,3}Var\d+|in_[a-z0-9]+|extraout_[a-z0-9_]+)\b")
PARAM = re.compile(r"\bparam_(\d+)\b")
# *(T *)(base + 0xNN) with base an identifier or an already rewritten chain
FIELD = re.compile(r"\*\((?:[A-Za-z_][\w ]*?)\s*\*+\s*\)\(([A-Za-z_]\w*(?:->f_[0-9a-f]+)*) \+ 0x([0-9a-f]+)\)")
FIELD0 = re.compile(r"\*\((?:[A-Za-z_][\w ]*?)\s*\*+\s*\)([A-Za-z_]\w*(?:->f_[0-9a-f]+)+)\b")
ADDR = re.compile(r"\(([A-Za-z_]\w*(?:->f_[0-9a-f]+)*) \+ 0x([0-9a-f]+)\)")
ADDR_ARG = re.compile(r"([(,]\s*)([A-Za-z_]\w*(?:->f_[0-9a-f]+)*) \+ 0x([0-9a-f]+)(?=\s*[,)])")
NOISE = {
    "unnamed calls": UNNAMED_CALL,
    "param_N": PARAM,
    "temporaries": TEMP,
    "placeholder types": TYPE_RX,
    "pointer arithmetic fields": re.compile(r"\*\([\w ]+\*+\)\(\w+ \+ 0x[0-9a-f]+\)"),
    "DAT_ globals": DAT,
}


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


def rewrite(text: str, names: dict[int, str]) -> str:
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

    # struct fields, innermost first, until stable
    for _ in range(8):
        new = FIELD.sub(lambda m: f"{m.group(1)}->f_{m.group(2)}", text)
        new = FIELD0.sub(lambda m: f"*{m.group(1)}", new)
        if new == text:
            break
        text = new
    objects = set(re.findall(r"\b([A-Za-z_]\w*)->f_", text))
    text = ADDR.sub(lambda m: f"&{m.group(1)}->f_{m.group(2)}" if m.group(1).split("->")[0] in objects else m.group(0), text)
    # the same inside argument lists, where Ghidra drops the parentheses: f(self + 0x254, ...)
    text = ADDR_ARG.sub(
        lambda m: f"{m.group(1)}&{m.group(2)}->f_{m.group(3)}" if m.group(2).split("->")[0] in objects else m.group(0), text)

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


def _work(args):
    rel, names, callers, callees = args
    src = GHIDRA / rel
    text = src.read_text(encoding="utf-8", errors="replace")
    out = rewrite(text, names)
    own = src.stem.rsplit("_", 1)[0]
    named_callers = sorted(c for c in callers.get(own, ()) if not c.startswith("func_"))
    header = [
        "/* Readable view (tools/readable_c.py) of " + rel.replace("\\", "/") + " - read-only pseudo-C.",
        " * self = first argument used as an object; f_XXX = field at offset 0xXXX;",
        " * func_XXXXXXXX = function not named yet; g_XXXXXXXX = global at that address.",
    ]
    if named_callers:
        header.append(" * Called by: " + ", ".join(named_callers[:12]) + (" ..." if len(named_callers) > 12 else ""))
    if callees.get(src.name):
        header.append(" * Calls: " + ", ".join(sorted(callees[src.name])[:12]))
    header.append(" */")
    dst = OUT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("\n".join(header) + "\n" + out, encoding="utf-8")
    return noise(text), noise(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stats", action="store_true", help="print before/after noise counts")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    names = load_names()
    files = sorted((GHIDRA / "functions").glob("*.c"))
    callers, callees = call_graph(files, names)
    jobs = [(str(f.relative_to(GHIDRA)), names, callers, callees) for f in files]
    before: dict[str, int] = {}
    after: dict[str, int] = {}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for b, a in pool.map(_work, jobs, chunksize=64):
            for k in b:
                before[k] = before.get(k, 0) + b[k]
                after[k] = after.get(k, 0) + a[k]
    print(f"wrote {len(files)} readable functions -> {OUT.relative_to(ROOT)}")
    report = {"functions": len(files), "named_functions": len(names), "before": before, "after": after}
    for k in before:
        print(f"  {k:26} {before[k]:8} -> {after[k]:8}")
    (ROOT / "audit" / "READABLE_C.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
