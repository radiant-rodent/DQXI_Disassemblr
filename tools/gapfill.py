#!/usr/bin/env python3
"""Second pass for the local-variable batches: name what the V_* workers left out.

    python tools/gapfill.py --build            write orchestration/types/gap/VG_###.json (+ tasks/VG_###.md)
    python tools/gapfill.py --merge            fold orchestration/types/gap_out/VG_###.json into types/out/V_###.json
    python tools/gapfill.py VG_001 next        worker commands: identical to tools/batchview.py (next, --add -, --todo, --check)

A gap batch holds only functions that still have placeholder variables (iVar3, local_2c, param_2 ...) after the
V_* answers and the rule pass were merged. Each function lists only those variables, plus a note with the names
already used in that function. The worker answers in the V_* format; --merge copies the names into the original
V_* answer file, so apply.py / merge_names.py / progress.py see them like any other answer.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
BATCHES = ROOT / "orchestration" / "types" / "batches"
OUT = ROOT / "orchestration" / "types" / "out"
GAP = ROOT / "orchestration" / "types" / "gap"
GAP_OUT = ROOT / "orchestration" / "types" / "gap_out"
TASKS = ROOT / "orchestration" / "tasks"
LOCALS = ROOT / "orchestration" / "types" / "merged" / "locals.json"
PLACEHOLDER = re.compile(
    r"^(?:[a-z]{1,3}Var\d+|local_[0-9a-f]+|uStack_[0-9a-f]+|iStack_[0-9a-f]+|"
    r"in_[a-z0-9]+|extraout_[a-z0-9_]+|unaff_[a-z0-9]+|arg\d+|param_\d+)$")
PER_BATCH_VARS = 700
MAX_FUNCS = 170

TASK_BODY = """\
Second pass over the local variables of {nf} functions in `orchestration/types/gap/{bid}.json`. The first pass
(V_*) named only what it could justify; this pass names the rest.

## Rules (read once, then work)

1. Write only inside the project folder. Never touch `..\\3DS_Translate`. Never download or install
   anything. UTF-8 everywhere; `/dev/null`, never `nul`.
2. Do not explore: no README/docs/AGENT_LOG.md/`tools/*.py` reading, no git, no `--help`, no whole-tree searches, no
   build/tests, no own dump scripts. For a caller/callee only: `python tools/fn.py 0xADDR`.
3. Names are lowerCamelCase (`count`, `entryIndex`, `tmpResult`, `scratchBuf`). Single words are fine.
   **Name every variable that the tool lists.** The first pass already left out the hard ones, so here a vague but
   true name beats no name: loop index -> `index`/`i`, stack buffer passed to a call -> `buf`/`scratch`, return value
   kept in a temp -> `result`/`status`, a pointer to a field read -> `entryPtr`, a copy of a parameter -> its meaning.
   Use the body, the "hint", "calls", "fields" and "consts" columns. If you are unsure, still name it, give the
   entry confidence below 0.5 and prefix EVERY name of that entry with `maybe_` (`maybe_scratchBuf`).
   Only leave a variable out if you cannot say anything about it at all.
4. Never reuse a name that appears on the "already used names" note of the function, and no two variables of one
   function may share a name.
5. Do not rename a variable that is not in the "variables still to name" table.

## Workflow

```bash
python tools/gapfill.py {bid} next
```

prints the next functions (C body, a note with names already used, and the variables to name). Answer exactly
those functions, one JSON object each, and save with ONE call that also prints the next chunk:

```bash
python tools/gapfill.py {bid} --add - <<'EOF'
[ {{"address": "0x...", "function": "...", "params": {{"param_2": "count"}}, "locals": {{"iVar2": "index"}},
    "confidence": 0.6, "evidence": "short reason"}} ]
EOF
```

Nothing is saved if it reports a problem: fix the JSON and run the same call again. Repeat until it prints
"nothing left to name", then `python tools/gapfill.py {bid} --check`. Do not view a function twice.

Finally write `orchestration/done/{bid}.md` (functions, variables named, what was left out and why; nothing else)
and append ONE line without opening the file:
`echo "## Entry - $(date +%F) ({bid}): batch finished, see orchestration/done/{bid}.md" >> AGENT_LOG.md`
"""


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def build():
    merged = (load_json(LOCALS, {}).get("functions") or {})
    by_addr_merged = {str(v.get("address", "")).lower(): v for v in merged.values()}
    GAP.mkdir(parents=True, exist_ok=True)
    GAP_OUT.mkdir(parents=True, exist_ok=True)
    cands = []  # (source batch, function record with only the missing variables)
    for bp in sorted(BATCHES.glob("V_*.json")):
        bid = bp.stem
        b = load_json(bp, {})
        out = {str(x.get("address", "")).lower(): x for x in load_json(OUT / f"{bid}.json", [])}
        for f in b.get("functions", []):
            a = str(f["address"]).lower()
            e = out.get(a) or {}
            m = by_addr_merged.get(a) or {}
            named = {}
            for src in (e, m):
                for key in ("params", "locals"):
                    named.update(src.get(key) or {})
            todo = [v for v in f.get("variables", []) if PLACEHOLDER.match(v["name"]) and v["name"] not in named]
            if not todo:
                continue
            rec = {k: f[k] for k in ("name", "address", "class", "role", "readable", "params", "fields_used") if k in f}
            used = sorted(set(named.values()) | {v["name"] for v in f.get("variables", []) if not PLACEHOLDER.match(v["name"])})
            rec["signature"] = f.get("signature", "") + ("\n/* already used names in this function: " + ", ".join(used) + " */" if used else "")
            rec["variables"] = todo
            rec["source_batch"] = bid
            cands.append(rec)
    batches, cur, nv = [], [], 0
    for rec in cands:
        if cur and (nv + len(rec["variables"]) > PER_BATCH_VARS or len(cur) >= MAX_FUNCS):
            batches.append(cur); cur, nv = [], 0
        cur.append(rec); nv += len(rec["variables"])
    if cur:
        batches.append(cur)
    for old in GAP.glob("VG_*.json"):
        old.unlink()
    for i, fns in enumerate(batches, 1):
        bid = f"VG_{i:03d}"
        (GAP / f"{bid}.json").write_text(json.dumps({"batch": bid, "kind": "VG", "functions": fns}, indent=1, ensure_ascii=False), encoding="utf-8")
        t = TASKS / f"{bid}.md"
        if not t.exists():
            t.write_text(f"---\nlane: V_gap\n---\n" + TASK_BODY.format(bid=bid, nf=len(fns)), encoding="utf-8")
    print(f"{len(cands)} functions, {sum(len(r['variables']) for r in cands)} variables -> {len(batches)} batches VG_001..VG_{len(batches):03d}")


def merge():
    PREFIX = re.compile(r"^maybe_")
    added = clash = fns = 0
    per = {}
    for gp in sorted(GAP_OUT.glob("VG_*.json")):
        for x in load_json(gp, []):
            if not (x.get("params") or x.get("locals")):
                continue
            src = next((f["source_batch"] for f in load_json(GAP / gp.name, {}).get("functions", []) if f["address"] == x["address"]), None)
            if src:
                per.setdefault(src, []).append(x)
    for bid, items in sorted(per.items()):
        cur = load_json(OUT / f"{bid}.json", [])
        idx = {str(e.get("address", "")).lower(): e for e in cur}
        for x in items:
            e = idx.get(str(x["address"]).lower())
            if e is None:
                e = {"address": x["address"], "function": x["function"], "params": {}, "locals": {}, "confidence": x.get("confidence", 0.5),
                     "evidence": str(x.get("evidence", ""))[:300], "source": "gapfill"}
                cur.append(e); idx[str(x["address"]).lower()] = e
            used = {PREFIX.sub("", n) for k in ("params", "locals") for n in (e.get(k) or {}).values()}
            fns += 1
            conf = x.get("confidence", 0.5)
            for key in ("params", "locals"):
                for tok, name in (x.get(key) or {}).items():
                    if tok in (e.get("params") or {}) or tok in (e.get("locals") or {}):
                        continue
                    base = PREFIX.sub("", name)
                    if base in used:
                        clash += 1; continue
                    if (conf < 0.5 or float(e.get("confidence", 1)) < 0.5) and not name.startswith("maybe_"):
                        name = "maybe_" + name
                    e.setdefault(key, {})[tok] = name
                    used.add(base); added += 1
            if e.get("source") != "gapfill":  # keep the first pass's confidence; gap names carry their own maybe_ prefixes
                e["evidence"] = (str(e.get("evidence", "")) + " | gap: " + str(x.get("evidence", "")))[:300]
        (OUT / f"{bid}.json").write_text(json.dumps(cur, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"merged {added} names in {fns} function answers ({clash} name clashes dropped) into {len(per)} V batches")


def worker_main():
    import batchview
    batchview.BATCHES = GAP
    batchview.OUT = GAP_OUT
    GAP_OUT.mkdir(parents=True, exist_ok=True)
    batchview.main()


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--build":
        build()
    elif len(sys.argv) == 2 and sys.argv[1] == "--merge":
        merge()
    else:
        worker_main()
