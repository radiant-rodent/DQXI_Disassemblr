#!/usr/bin/env python3
"""Name local variables and parameters by rule, without a model (V_* batches).

Reads each batch in orchestration/types/batches/V_*.json and the *current* readable C of every function
(after M2 the bodies carry real field names, so `iVar2 = self->targetUnit;` is evidence for `targetUnit`).
Rules, all high precision, nothing is guessed from thin air:

  field     the first assignment is `tok = [(cast)] [&]base->realField;`           -> realField   (0.65)
  callee    the first assignment is `tok = [(cast)] Class_GetThing(...);` with a
            real (not maybe_/func_/FUN_) callee name                               -> thing       (0.60)
  class     a pointer variable whose declared type is a named class (not `self`)   -> typeName    (0.55)
  loop      hint `loop counter` on an int                                          -> i, j, k     (0.70)
  result    hint `return value` (one per function)                                 -> result      (0.55)

Names are made unique inside a function and must not clash with any identifier used in the body.

    python tools/locals_by_rule.py --stats               coverage per rule over all batches, writes nothing
    python tools/locals_by_rule.py --sample 12           print example decisions
    python tools/locals_by_rule.py --apply               write answers (source: "rules") for every batch that
                                                          has no answer file yet and is not claimed or running
    python tools/locals_by_rule.py --apply V_030 V_031   only these batches
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import batchview  # noqa: E402  (body_of, C_KEYWORDS, NAME, load helpers)

ORC = ROOT / "orchestration"
PLACEHOLDER = re.compile(r"^(?:[a-z]{1,4}Var\d+|[a-z]{1,3}Stack_?[0-9a-fA-F]+|local_[0-9a-fA-F]+|arg\d+|param_\d+|in_\w+|extraout_\w+|unaff_\w+)$")
CALLEE_BAD = re.compile(r"^(?:maybe_|func_|FUN_|CONCAT|SUB|ZEXT|SEXT|CARRY|SBORROW|__|thunk_|Unrecovered|halt_)")
GETTERS = ("Get", "Find", "Lookup", "Create", "New", "Make", "Acquire", "Fetch", "Query", "Resolve", "Load", "Open")
GENERIC = {"Work", "Data", "Core", "Instance", "Info", "Record", "Object", "Entry", "Table", "Manager", "Ptr", "Pointer", "Handle", "Context"}
BOOLISH = ("Is", "Has", "Can", "Should")
HEXISH = re.compile(r"[0-9A-Fa-f]*\d[0-9A-Fa-f]{2,}$")
ASSIGN = re.compile(r"^\s*(\w+)\s*=\s*(.+?);\s*$")


def lower_camel(s):
    parts = [p for p in re.split(r"_+", s) if p]
    if not parts:
        return ""
    s = "".join(p[:1].upper() + p[1:] if i else p for i, p in enumerate(parts))
    return s[:1].lower() + s[1:]


def real_field(n):
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9]{2,}$", n)) and not n.startswith(("f_", "maybe", "unknown")) \
        and not HEXISH.search(n) and n not in batchview.C_KEYWORDS and not re.match(r"^(f|u|i|s|b|p|d)[A-Z]?\d", n)


def name_from_callee(callee):
    if CALLEE_BAD.match(callee) or not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", callee):
        return None
    cls, _, member = callee.partition("_")
    if not member:
        cls, member = "", callee
    if re.search(r"_\d+$", member):  # Mem_AllocAligned_2: a numbered variant, no name worth taking
        return None
    member = member.replace("_", "")
    for b in BOOLISH:
        if member.startswith(b) and len(member) > len(b) and member[len(b)].isupper():
            return lower_camel(member)
    for g in sorted(GETTERS, key=len, reverse=True):
        if member.startswith(g) and len(member) > len(g) and member[len(g)].isupper():
            rest = member[len(g):]
            if rest in GENERIC and cls:
                return lower_camel(cls) + rest
            return lower_camel(rest)
        if member == g and cls:
            return lower_camel(cls)
    return None  # a verb we do not understand (Update, Draw, Init...): no guess


def type_name(v):
    t = (v.get("type") or "").strip()
    if (v.get("stars") or 0) >= 1 and re.match(r"^[A-Z][A-Za-z0-9]{3,}$", t):
        return lower_camel(t)
    return None


def decide(fn):
    """-> ({token: (name, rule, conf, why)}, ...) for one function"""
    body = batchview.body_of(fn)
    variables = [v for v in fn.get("variables", []) if PLACEHOLDER.match(v["name"])]
    first = {}
    for line in body.splitlines():
        m = ASSIGN.match(line)
        if m and m.group(1) in {v["name"] for v in variables} and m.group(1) not in first:
            first[m.group(1)] = m.group(2)
    used_idents = set(re.findall(r"(?<![\w>.])([A-Za-z_]\w*)", body))
    out, taken = {}, set()
    loop_names = iter(["i", "j", "k", "l", "m"])
    result_done = False
    for v in variables:
        tok, hint = v["name"], v.get("hint") or ""
        cand = None
        expr = first.get(tok, "")
        m = re.match(r"^(?:\([^()]*\)\s*)*&?\(?\*?\(?\w+\)?(?:->\w+)*->(\w+)\)?$", expr)
        if m and real_field(m.group(1)):
            cand = (lower_camel(m.group(1)), "field", 0.65, f"{tok} = {expr}")
        if not cand:
            m = re.match(r"^(?:\([^()]*\)\s*)*([A-Za-z_]\w*)\(", expr)
            if m:
                n = name_from_callee(m.group(1))
                if n and len(n) >= 3:
                    cand = (n, "callee", 0.60, f"{tok} = {m.group(1)}(...)")
        if not cand and hint == "loop counter" and re.match(r"^(?:[iu]Var|local_|[iu]Stack)", tok) and v.get("type") in ("int", "uint", "u32", "s32", "short", "u16", "u8") and not v.get("is_param"):
            cand = (next(loop_names), "loop", 0.70, "hint: loop counter")
        if not cand and hint == "return value" and not result_done and not v.get("is_param"):
            cand = ("result", "result", 0.55, "hint: return value")
            result_done = True
        if not cand and tok != "self":
            n = type_name(v)
            if n and (v.get("is_param") or "object/struct pointer" in hint):
                cand = (n, "class", 0.55, f"declared type {v.get('type')}*")
        if not cand:
            continue
        name, rule, conf, why = cand
        if not batchview.NAME.match(name) or name in batchview.C_KEYWORDS or len(name) < 1:
            continue
        base, n = name, 2
        while name in taken or (name in used_idents and rule != "loop"):
            name = f"{base}{n}"
            n += 1
        taken.add(name)
        out[tok] = (name, rule, conf, why, bool(v.get("is_param")))
    return out


def entry_for(fn, decisions):
    params = {t: d[0] for t, d in decisions.items() if d[4]}
    locals_ = {t: d[0] for t, d in decisions.items() if not d[4]}
    why = "; ".join(f"{t}->{d[0]} ({d[1]}: {d[3]})" for t, d in list(decisions.items())[:6])
    return {"address": fn["address"], "function": fn["name"], "params": params, "locals": locals_,
            "confidence": round(min(d[2] for d in decisions.values()), 2),
            "evidence": ("rules: " + why)[:300], "source": "rules"}


def batches(only):
    for p in sorted((ORC / "types" / "batches").glob("V_*.json")):
        if not only or p.stem in only:
            yield p.stem, json.loads(p.read_text(encoding="utf-8"))


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    mode = args[0]
    sample_n = int(args[1]) if mode == "--sample" and len(args) > 1 else 0
    only = set(a for a in args[1:] if a.startswith("V_"))
    by_rule, total_vars, named_vars, funcs_hit, funcs = collections.Counter(), 0, 0, 0, 0
    samples = []
    written = skipped = 0
    for bid, b in batches(only):
        entries = []
        for fn in b["functions"]:
            funcs += 1
            total_vars += sum(1 for v in fn.get("variables", []) if PLACEHOLDER.match(v["name"]))
            d = decide(fn)
            if not d:
                continue
            funcs_hit += 1
            named_vars += len(d)
            for t, x in d.items():
                by_rule[x[1]] += 1
                if len(samples) < 4000:
                    samples.append((fn["name"], t, x))
            entries.append(entry_for(fn, d))
        if mode == "--apply":
            out = ORC / "types" / "out" / f"{bid}.json"
            if out.exists() or (ORC / "done" / f"{bid}.md").exists() or (ORC / "claims" / bid).exists() \
                    or (ORC / "locks" / f"{bid}.pid").exists() or (ORC / "logs" / f"{bid}.log").exists():
                skipped += 1
                continue
            batchview.write_atomic(out, entries)
            written += 1
    print(f"functions {funcs}, with at least one rule name {funcs_hit}")
    print(f"placeholder variables {total_vars}, named by rule {named_vars} ({100 * named_vars / max(total_vars, 1):.1f}%)")
    for r, n in by_rule.most_common():
        print(f"  {n:7d}  {r}")
    if mode == "--apply":
        print(f"batches written {written}, skipped (already answered, claimed, running or started) {skipped}")
    if sample_n:
        import random
        random.seed(1)
        for fn, t, x in random.sample(samples, min(sample_n * 4, len(samples)))[:sample_n * 4]:
            print(f"  {fn[:42]:42} {t:12} -> {x[0]:24} [{x[1]}] {x[3][:70]}")


if __name__ == "__main__":
    main()
