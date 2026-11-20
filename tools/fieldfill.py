#!/usr/bin/env python3
"""Second pass over struct fields whose name is still a guess (`maybe_`, confidence < 0.5).

    python tools/fieldfill.py --build          write orchestration/types/fgap/SF_###.json (+ tasks/SF_###.md)
    python tools/fieldfill.py --merge          fold orchestration/types/fgap_out/SF_###.json into types/out/S_###.json
    python tools/fieldfill.py SF_001 next      worker: show the next chunk (also: --add -, --todo, --check)

The first pass (S_*) named every field it saw, but 8,000 of them stay below 0.5 confidence. A worker re-reads the
evidence plus the methods that touch the field and either confirms a better name (confidence >= 0.5, no `maybe_`),
improves the guess (still < 0.5, `maybe_` kept) or leaves it. --merge only ever raises a field's confidence.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCHES = ROOT / "orchestration" / "types" / "batches"
OUT = ROOT / "orchestration" / "types" / "out"
FGAP = ROOT / "orchestration" / "types" / "fgap"
FGAP_OUT = ROOT / "orchestration" / "types" / "fgap_out"
TASKS = ROOT / "orchestration" / "tasks"
PER_BATCH = 110
NAME = re.compile(r"^(maybe_)?[a-z_][A-Za-z0-9_]*$")
KW = {"auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum", "extern",
      "float", "for", "goto", "if", "int", "long", "register", "return", "short", "signed", "sizeof", "static",
      "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "bool", "true", "false",
      "self", "this", "new", "class", "inline", "restrict"}
EVID = re.compile(r"0x[0-9A-Fa-f]{4,}|[A-Za-z]+_[A-Za-z0-9_]+|'[^']+'")

TASK_BODY = """\
Second pass over struct fields: re-examine {nf} fields (in {nc} class chunks) of `orchestration/types/fgap/{bid}.json`
whose names are still guesses (`maybe_`, confidence below 0.5).

## Rules (read once, then work)

1. Write only inside the project folder. Never touch `..\\3DS_Translate`. No downloads/installs.
   UTF-8 everywhere; `/dev/null`, never `nul`.
2. Do not explore: no README/docs/AGENT_LOG.md/`tools/*.py` reading, no git, no `--help`, no whole-tree searches,
   no build/tests, no own dump scripts. To check how a field is really used read the method it names:
   `python tools/fn.py 0xADDR` (current name, summary, callers/callees, body).
3. For each field the tool shows: the current guess with its confidence and evidence, the first-pass access
   evidence (C lines), constants, callees, and the names of the confident fields of the same class.
   Decide ONE of:
   * **confirm / better name**: you can say what the field holds and cite why -> name it (lowerCamelCase, no
     `maybe_`) with confidence 0.5-0.95. The `evidence` MUST cite at least one function name or address and what it
     does with the field (a bare "seems to be" is rejected). Never raise confidence just because the old guess
     sounds plausible: read the evidence or the method first.
   * **improve the guess**: a clearly better but still uncertain name -> keep `maybe_`, confidence below 0.5.
   * **leave it**: omit the field. That is fine; omit what you cannot justify.
4. Names are lowerCamelCase nouns that say what the field is (`targetActorId`, `animTimer`, `childList`).
   No two fields of one class may share a name (the tool checks against the class's existing names).
5. Answer only fields the tool printed.

## Workflow

```bash
python tools/fieldfill.py {bid} next
```

prints the next class chunks. Answer, one object per class, and save with ONE call that also prints the next chunk:

```bash
python tools/fieldfill.py {bid} --add - <<'EOF'
[ {{"class": "Field_SceneObject", "fields": [
   {{"offset": 4, "name": "nodeKey", "confidence": 0.6, "evidence": "ReleaseInstance (0x002B4DF4) uses it as the node hash key"}} ]}} ]
EOF
```

Nothing is saved if it reports a problem: fix the JSON and run the same call again. Repeat until it prints
"nothing left to review", then `python tools/fieldfill.py {bid} --check`. Do not view a chunk twice.

Finally write `orchestration/done/{bid}.md` (fields confirmed/improved/left, nothing else) and append ONE line
without opening the file:
`echo "## Entry - $(date +%F) ({bid}): batch finished, see orchestration/done/{bid}.md" >> AGENT_LOG.md`
"""


def load(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def build():
    FGAP.mkdir(parents=True, exist_ok=True)
    FGAP_OUT.mkdir(parents=True, exist_ok=True)
    chunks = []
    for bp in sorted(BATCHES.glob("S_*.json")):
        bid = bp.stem
        out = {o["class"]: o for o in load(OUT / f"{bid}.json", [])}
        for c in load(bp, {}).get("classes", []):
            o = out.get(c["class"]) or {}
            named = {f["offset"]: f for f in o.get("fields", []) if f.get("name")}
            todo, good = [], []
            for f in c["fields"]:
                n = named.get(f["offset"])
                if f.get("weak") or not n:
                    continue
                if str(n["name"]).startswith("maybe_") or float(n.get("confidence", 1)) < 0.5:
                    todo.append({"offset": f["offset"], "size": f.get("size"), "type_guess": f.get("type_guess"),
                                 "is_pointer": f.get("is_pointer"), "reads": f.get("reads"), "writes": f.get("writes"),
                                 "constants": (f.get("constants") or [])[:4], "callees": (f.get("callees") or [])[:4],
                                 "access_evidence": (f.get("evidence") or [])[:3],
                                 "current": {"name": n["name"], "type": n.get("type"), "confidence": n.get("confidence"),
                                             "evidence": str(n.get("evidence", ""))[:240]}})
                else:
                    good.append(f"+0x{f['offset']:x} {n['name']}")
            if not todo:
                continue
            chunks.append({"class": c["class"], "source_batch": bid, "base": c.get("base"), "size": c.get("size"),
                           "summary": str(o.get("summary", ""))[:300], "vtable": c.get("vtable"),
                           "methods": [(f["name"], f["address"]) for f in c.get("functions", [])[:14]],
                           "confident_fields": good[:40], "fields": todo})
    # split big classes, pack chunks into batches of about PER_BATCH fields
    parts = []
    for ch in chunks:
        fs = ch["fields"]
        for i in range(0, len(fs), PER_BATCH):
            parts.append({**ch, "fields": fs[i:i + PER_BATCH]})
    batches, cur, n = [], [], 0
    for p in parts:
        if cur and n + len(p["fields"]) > PER_BATCH:
            batches.append(cur); cur, n = [], 0
        cur.append(p); n += len(p["fields"])
    if cur:
        batches.append(cur)
    for old in FGAP.glob("SF_*.json"):
        old.unlink()
    for i, cs in enumerate(batches, 1):
        bid = f"SF_{i:03d}"
        (FGAP / f"{bid}.json").write_text(json.dumps({"batch": bid, "kind": "SF", "chunks": cs}, indent=1, ensure_ascii=False), encoding="utf-8")
        t = TASKS / f"{bid}.md"
        if not t.exists():
            t.write_text("---\nlane: S_fieldfill\n---\n" + TASK_BODY.format(bid=bid, nf=sum(len(c["fields"]) for c in cs), nc=len(cs)), encoding="utf-8")
    print(f"{len(chunks)} classes, {sum(len(c['fields']) for c in chunks)} fields -> {len(batches)} batches SF_001..SF_{len(batches):03d}")


# ---------------------------------------------------------------- worker side
def answers(bid):
    return load(FGAP_OUT / f"{bid}.json", [])


def todo_chunks(bid):
    b = load(FGAP / f"{bid}.json", {})
    done = {}
    for a in answers(bid):
        done.setdefault(a["class"], set()).update(a.get("_seen", []))
    out = []
    for i, ch in enumerate(b.get("chunks", [])):
        key = (ch["class"], ch["fields"][0]["offset"])
        if key not in {tuple(x) for a in answers(bid) for x in a.get("_chunks", [])}:
            out.append(i)
    return out


def show(bid, idxs):
    b = load(FGAP / f"{bid}.json", {})
    shown = []
    used = 0
    for i in idxs:
        ch = b["chunks"][i]
        txt = [f"\n######## [{i}] class {ch['class']}  base={ch.get('base')} size={ch.get('size')} vtable={ch.get('vtable')}"]
        if ch.get("summary"):
            txt.append("summary: " + ch["summary"])
        txt.append("methods: " + ", ".join(f"{n}@{a}" for n, a in ch["methods"]))
        txt.append("confident fields already in this class: " + (", ".join(ch["confident_fields"]) or "(none)"))
        txt.append("--- fields to review (current guess -> your answer)")
        for f in ch["fields"]:
            c = f["current"]
            txt.append(f"  +0x{f['offset']:x} ({f['offset']}) {f['type_guess']} size {f['size']}{' ptr' if f['is_pointer'] else ''} r{f['reads']}/w{f['writes']}"
                       f" | guess: {c['name']} ({c['confidence']}) | why: {c['evidence']}")
            if f["access_evidence"]:
                txt.append("      code: " + " ; ".join(f["access_evidence"]))
            if f["constants"] or f["callees"]:
                txt.append("      const: " + ",".join(map(str, f["constants"])) + "  callees: " + ",".join(f["callees"]))
        block = "\n".join(txt)
        if used and used + len(block) > 22000:
            print("\n[output limit reached; the rest comes with the next call]")
            break
        used += len(block)
        shown.append([ch["class"], ch["fields"][0]["offset"]])
        print(block)
    d = ROOT / "out" / "scratch" / bid
    d.mkdir(parents=True, exist_ok=True)
    (d / ".shown_fields.json").write_text(json.dumps(shown), encoding="utf-8")


def worker(bid, cmd):
    b = load(FGAP / f"{bid}.json", {})
    if not b:
        sys.exit(f"no such batch {bid}")
    if cmd == "next":
        t = todo_chunks(bid)
        if not t:
            print(f"{bid}: nothing left to review. Run: python tools/fieldfill.py {bid} --check   then write the done report.")
            return
        print(f"{bid}: {len(t)} class chunks still to review")
        show(bid, t)
    elif cmd == "--todo":
        print(f"{bid}: {len(todo_chunks(bid))} of {len(b['chunks'])} chunks to review")
    elif cmd == "--check":
        a = answers(bid)
        bad = 0
        for x in a:
            bad += len(problems(b, x))
        print(f"{bid}: {len(a)} answers, {bad} problem(s)")
        sys.exit(1 if bad else 0)
    elif cmd == "--add":
        raw = sys.stdin.read() if sys.argv[3] == "-" else Path(sys.argv[3]).read_text(encoding="utf-8")
        chunk = json.loads(raw)
        if isinstance(chunk, dict):
            chunk = [chunk]
        errs = []
        for x in chunk:
            errs += problems(b, x)
        if errs:
            sys.exit("\n".join(errs) + f"\n{len(errs)} problem(s): fix the JSON and run --add again (nothing was saved)")
        try:
            shown = json.loads((ROOT / "out" / "scratch" / bid / ".shown_fields.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            shown = []
        cur = answers(bid)
        for cls, off in shown:  # remember which chunks were reviewed (answered or not)
            mine = [x for x in chunk if x["class"] == cls]
            entry = {"class": cls, "fields": [f for x in mine for f in x.get("fields", [])], "_chunks": [[cls, off]]}
            cur.append(entry)
        FGAP_OUT.mkdir(parents=True, exist_ok=True)
        (FGAP_OUT / f"{bid}.json").write_text(json.dumps(cur, indent=1, ensure_ascii=False), encoding="utf-8")
        n = sum(len(x.get("fields", [])) for x in chunk)
        print(f"saved: {n} fields answered, {len(shown)} chunks reviewed in total {len(cur)}\n")
        if "--no-next" not in sys.argv:
            worker(bid, "next")
    else:
        sys.exit(__doc__)


def problems(b, x):
    errs = []
    chunks = [c for c in b["chunks"] if c["class"] == x.get("class")]
    if not chunks:
        return [f"class {x.get('class')} is not in this batch"]
    known = {f["offset"]: f for c in chunks for f in c["fields"]}
    taken = {n.split(" ", 1)[1] for c in chunks for n in c["confident_fields"]}
    seen = set()
    for f in x.get("fields", []):
        off = f.get("offset")
        name = f.get("name")
        where = f"{x['class']} +{off}"
        if off not in known:
            errs.append(f"  {where}: offset is not one of the fields to review"); continue
        if not isinstance(name, str) or not NAME.match(name) or name.replace("maybe_", "", 1) in KW:
            errs.append(f"  {where}: '{name}' is not a valid lowerCamelCase name (keywords incl. self/this are reserved)"); continue
        conf = f.get("confidence")
        if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
            errs.append(f"  {where}: confidence must be 0..1"); continue
        if conf < 0.5 and not name.startswith("maybe_"):
            errs.append(f"  {where}: confidence < 0.5 needs the maybe_ prefix")
        if conf >= 0.5 and name.startswith("maybe_"):
            errs.append(f"  {where}: confidence >= 0.5 must not start with maybe_")
        ev = str(f.get("evidence", ""))
        if conf >= 0.5 and (len(ev) < 25 or not EVID.search(ev)):
            errs.append(f"  {where}: evidence must name a function/address/string and what it does with the field")
        base = name.replace("maybe_", "", 1)
        if base in seen:
            errs.append(f"  {where}: duplicate name {base} in this class")
        seen.add(base)
        if base in taken:
            errs.append(f"  {where}: {base} is already used by another field of the class")
    return errs


def merge():
    per = {}
    for gp in sorted(FGAP_OUT.glob("SF_*.json")):
        src = {c["class"]: c["source_batch"] for c in load(FGAP / gp.name, {}).get("chunks", [])}
        for a in load(gp, []):
            sb = src.get(a["class"])
            if sb:
                per.setdefault(sb, {}).setdefault(a["class"], []).extend(a.get("fields", []))
    up = imp = skip = 0
    for sb, classes in sorted(per.items()):
        out = load(OUT / f"{sb}.json", [])
        for o in out:
            fs = classes.get(o["class"])
            if not fs:
                continue
            by = {f["offset"]: f for f in o.get("fields", [])}
            used = {f["name"].replace("maybe_", "", 1) for f in o.get("fields", []) if f.get("name")}
            for n in fs:
                f = by.get(n["offset"])
                if not f:
                    continue
                oldc = float(f.get("confidence", 0))
                if float(n["confidence"]) <= oldc:
                    skip += 1; continue
                nb = n["name"].replace("maybe_", "", 1)
                if nb in used and nb != f["name"].replace("maybe_", "", 1):
                    skip += 1; continue
                used.add(nb)
                if oldc < 0.5 <= float(n["confidence"]):
                    up += 1
                else:
                    imp += 1
                f["name"], f["confidence"], f["evidence"] = n["name"], n["confidence"], str(n["evidence"])[:300]
        (OUT / f"{sb}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"fields raised to >= 0.5: {up}, improved guesses: {imp}, skipped (not better / name clash): {skip}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--build"]:
        build()
    elif a == ["--merge"]:
        merge()
    elif len(a) >= 2:
        worker(a[0], a[1])
    else:
        sys.exit(__doc__)
