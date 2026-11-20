#!/usr/bin/env python3
"""Worker helper for the local-variable batches (V_*): read a chunk, save a chunk, check the whole file.

Why this exists: in 87 logged worker runs the model spent a third of its tool calls writing its own
"dump this function" scripts, re-reading the same functions and rewriting the whole answer JSON.
One call here shows several functions with everything needed to name their variables; one call saves them.

    python tools/batchview.py V_021 next           show the next functions that still need names
    python tools/batchview.py V_021 --add - <<'EOF'   save this chunk (JSON on stdin), then show the next one
    [ {...}, {...} ]
    EOF
    python tools/batchview.py V_021 0:6            show functions 0..5 (body + variables table)
    python tools/batchview.py V_021 --todo         functions that have no answer yet (index ranges)
    python tools/batchview.py V_021 --add chunk.json   check + merge a chunk of answers into
                                                   orchestration/types/out/V_021.json
    python tools/batchview.py V_021 --check        validate the answer file the way the merge does

The answer format is the one in the task: a list of
{"address","function","params":{token:name},"locals":{token:name},"confidence","evidence"}.
"""
import json
import keyword
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCHES = ROOT / "orchestration" / "types" / "batches"
OUT = ROOT / "orchestration" / "types" / "out"
C_KEYWORDS = set(keyword.kwlist) | {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum",
    "extern", "float", "for", "goto", "if", "int", "long", "register", "return", "short", "signed",
    "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while",
    "bool", "true", "false", "NULL"}
NAME = re.compile(r"^(maybe_)?[a-z_][A-Za-z0-9_]*$")
MAX_BODY_LINES = 140
BUDGET = 22000   # characters printed per call (about 6-7k tokens)


def load_batch(bid):
    p = BATCHES / f"{bid}.json"
    if not p.exists():
        sys.exit(f"no such batch: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def load_answers(bid):
    p = OUT / f"{bid}.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


_ADDR_INDEX = None


def _index():
    """address (8 hex digits, lower case) -> readable file; one directory scan, built on first use.
    Files are renamed when names are merged, and every file name ends in _<address>.c."""
    global _ADDR_INDEX
    if _ADDR_INDEX is None:
        import os
        _ADDR_INDEX = {}
        root = ROOT / "decomp" / "readable"
        for sub in os.scandir(root):
            if sub.is_dir():
                for f in os.scandir(sub.path):
                    m = re.search(r"_([0-9a-f]{8})\.c$", f.name)
                    if m:
                        _ADDR_INDEX[m.group(1)] = Path(f.path)
    return _ADDR_INDEX


def body_of(fn):
    p = ROOT / fn.get("readable", "")
    if not p.is_file():
        m = re.search(r"0x([0-9A-Fa-f]{8})", fn["address"])
        hit = _index().get(m.group(1).lower()) if m else None
        p = hit or p
    if not p.is_file():
        return "(readable C not found)"
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    # drop the long provenance comment (Recovered/Signature/Evidence/Source) the merges put on top
    for i, l in enumerate(lines[:40]):
        if l.strip() == "*/" and any(x.startswith(" * Recovered:") for x in lines[:i]):
            keep = [x for x in lines[:i] if not x.startswith((" * Recovered", " * Signature", " * Source", " * Evidence"))
                    and not x.startswith("/* Recovered entry")]
            lines = keep[:6] + [" */"] + lines[i + 1:]
            break
    if len(lines) > MAX_BODY_LINES:
        lines = lines[:MAX_BODY_LINES] + [f"/* ... {len(lines) - MAX_BODY_LINES} more lines: python tools/fn.py {fn['address']} */"]
    return "\n".join(lines)


def rule_entry(answers, address):
    """The answer for this function if it came only from tools/locals_by_rule.py, else None."""
    for x in answers:
        if x.get("address") == address and x.get("source") == "rules":
            return x
    return None


def remaining_vars(f, ruled):
    named = set((ruled or {}).get("params", {})) | set((ruled or {}).get("locals", {}))
    return [v for v in f.get("variables", []) if v["name"] not in named]


SHOWN = ROOT / "out" / "scratch"


def todo_indexes(bid):
    b = load_batch(bid)
    answers = load_answers(bid)
    by_addr = {x.get("address"): x for x in answers}
    out = []
    for i, f in enumerate(b["functions"]):
        a = by_addr.get(f["address"])
        if a is not None and a.get("source") != "rules":
            continue  # answered (or skipped) by a worker
        if a is not None and a.get("reviewed"):
            continue  # the rule pass named some, a worker looked and had nothing to add
        if remaining_vars(f, a):
            out.append(i)
    return out


def show(bid, spec):
    fns = load_batch(bid)["functions"]
    a, _, z = spec.partition(":")
    lo, hi = int(a or 0), int(z) if z else (int(a) + 1 if a else len(fns))
    show_idx(bid, list(range(lo, min(hi, len(fns)))))


def show_idx(bid, indexes):
    b = load_batch(bid)
    fns = b["functions"]
    answers = load_answers(bid)
    done = {x.get("address") for x in answers if x.get("source") != "rules"}
    used = 0
    shown = []
    for i in indexes:
        f = fns[i]
        size = len(body_of(f)) + 90 * len(f.get("variables", []))
        if used and used + size > BUDGET:  # stop at a size the model reads in one go: no head/tail needed
            print(f"\n[output limit reached; the rest comes with the next call]")
            break
        used += size
        shown.append(f["address"])
        mark = "  [already answered]" if f["address"] in done else ""
        print(f"\n######## [{i}] {f['name']}  {f['address']}  class={f.get('class')}{mark}")
        print(f.get("signature", ""))
        print(body_of(f))
        ruled = rule_entry(answers, f["address"])
        if ruled:
            pairs = {**ruled.get("params", {}), **ruled.get("locals", {})}
            print("--- already named by the rule pass (do NOT answer these): " + ", ".join(f"{t}->{n}" for t, n in pairs.items()))
        print("--- variables still to name (params are the PARAM rows)")
        for v in remaining_vars(f, ruled):
            bits = [f"{v['name']}", f"{v.get('type')}{'*' * (v.get('stars') or 0)}"]
            if v.get("is_param"):
                bits.append("PARAM")
            bits.append(f"r{v.get('reads')}/w{v.get('writes')}")
            if v.get("hint"):
                bits.append(f"hint: {v['hint']}")
            if v.get("calls"):
                bits.append("calls: " + ", ".join(v["calls"][:5]))
            if v.get("fields"):
                bits.append("fields: " + ",".join(v["fields"][:6]))
            if v.get("constants"):
                bits.append("consts: " + ",".join(map(str, v["constants"][:5])))
            print("  " + " | ".join(bits))
    d = SHOWN / bid
    d.mkdir(parents=True, exist_ok=True)
    (d / ".shown.json").write_text(json.dumps(shown), encoding="utf-8")


def next_chunk(bid, n=8):
    todo = todo_indexes(bid)
    if not todo:
        print(f"{bid}: nothing left to name. Run: python tools/batchview.py {bid} --check   then write the done report.")
        return
    print(f"{bid}: {len(todo)} functions still to do")
    show_idx(bid, todo[:n])


def check_entry(entry, fn):
    errs = []
    tokens = {v["name"] for v in fn.get("variables", [])}
    for key in ("params", "locals"):
        m = entry.get(key) or {}
        if not isinstance(m, dict):
            errs.append(f"{key} must be an object")
            continue
        for tok, new in m.items():
            if tok not in tokens:
                errs.append(f"{key}: token '{tok}' is not in the batch for this function")
            if not isinstance(new, str) or not NAME.match(new):
                errs.append(f"{key}: '{new}' is not lowerCamelCase")
            elif new.replace("maybe_", "", 1) in C_KEYWORDS:
                errs.append(f"{key}: '{new}' is a C keyword")
    names = [n for k in ("params", "locals") for n in (entry.get(k) or {}).values() if isinstance(n, str)]
    if len(names) != len(set(names)):
        errs.append("duplicate new names inside one function")
    conf = entry.get("confidence")
    if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
        errs.append("confidence must be a number 0..1")
    elif conf < 0.5 and "rules" not in str(entry.get("source", "")) and any(isinstance(n, str) and not n.startswith("maybe_") for n in names):
        errs.append("confidence < 0.5: every name must start with maybe_")
    if not entry.get("evidence"):
        errs.append("evidence is empty")
    return errs


def check_all(bid, entries):
    by_addr = {f["address"].lower(): f for f in load_batch(bid)["functions"]}
    bad = 0
    for e in entries:
        fn = by_addr.get(str(e.get("address", "")).lower())
        if fn is None:
            print(f"  {e.get('address')}: address is not in batch {bid}")
            bad += 1
            continue
        for err in check_entry(e, fn):
            print(f"  {e['address']} {fn['name']}: {err}")
            bad += 1
    return bad


def write_atomic(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    json.loads(path.read_text(encoding="utf-8"))  # strict re-read


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    bid, cmd = sys.argv[1], sys.argv[2]
    OUT.mkdir(parents=True, exist_ok=True)
    if cmd == "--todo":
        b = load_batch(bid)
        answers = load_answers(bid)
        done = {x.get("address") for x in answers if x.get("source") != "rules"}
        todo = todo_indexes(bid)
        runs, start = [], None
        for i in todo:
            if start is None:
                start = prev = i
            elif i == prev + 1:
                prev = i
            else:
                runs.append((start, prev + 1))
                start = prev = i
        if start is not None:
            runs.append((start, prev + 1))
        print(f"{bid}: {len(b['functions'])} functions, {len(done)} answered, {len(todo)} to do")
        print("to do (index ranges):", " ".join(f"{a}:{z}" for a, z in runs) or "none")
    elif cmd == "next":
        next_chunk(bid)
    elif cmd == "--add":
        raw = sys.stdin.read() if sys.argv[3] == "-" else Path(sys.argv[3]).read_text(encoding="utf-8")
        chunk = json.loads(raw)
        if isinstance(chunk, dict):
            chunk = [chunk]
        bad = check_all(bid, chunk)
        if bad:
            sys.exit(f"{bad} problem(s): fix the chunk and run --add again (nothing was saved)")
        cur = {x["address"]: x for x in load_answers(bid)}
        for x in chunk:
            old = cur.get(x["address"])
            if old is not None and old.get("source") == "rules":  # keep the rule names, add the worker's
                clash = set(old.get("locals", {}).values()) | set(old.get("params", {}).values())
                mine = {t: n for k in ("params", "locals") for t, n in (x.get(k) or {}).items()}
                bad_names = sorted(n for t, n in mine.items() if n in clash and t not in {**old.get("params", {}), **old.get("locals", {})})
                if bad_names:
                    sys.exit(f"{x['address']}: {', '.join(bad_names)} already used by the rule pass in this function; pick other names")
                x = {**x, "params": {**old.get("params", {}), **(x.get("params") or {})},
                     "locals": {**old.get("locals", {}), **(x.get("locals") or {})}, "source": "rules+model",
                     "evidence": (str(x.get("evidence", "")) + " | " + str(old.get("evidence", "")))[:300]}
            cur[x["address"]] = x
        # functions that were shown but not answered: the worker had nothing clear -> remember, do not show again
        try:
            shown = json.loads((SHOWN / bid / ".shown.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            shown = []
        answered_now = {x["address"] for x in chunk}
        skipped = 0
        by_addr_fn = {f["address"]: f for f in load_batch(bid)["functions"]}
        for addr in shown:
            if addr in answered_now:
                continue
            old = cur.get(addr)
            if old is None:
                cur[addr] = {"address": addr, "function": by_addr_fn[addr]["name"], "params": {}, "locals": {},
                             "confidence": 0.0, "evidence": "reviewed: nothing clear enough to name", "source": "model-skip"}
                skipped += 1
            elif old.get("source") == "rules":
                old["reviewed"] = True
                skipped += 1
        write_atomic(OUT / f"{bid}.json", list(cur.values()))
        print(f"saved: {len(chunk)} answered, {skipped} reviewed with nothing to add, {len(cur)} functions covered in total\n")
        if "--no-next" not in sys.argv:
            next_chunk(bid)
    elif cmd == "--check":
        ans = load_answers(bid)
        bad = check_all(bid, ans)
        print(f"{bid}: {len(ans)} answers, {bad} problem(s)")
        sys.exit(1 if bad else 0)
    else:
        show(bid, cmd)


if __name__ == "__main__":
    main()
