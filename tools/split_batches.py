#!/usr/bin/env python3
"""Re-cut refine batches that have not started into smaller ones (default 50 functions, prefix R3).

    python tools/split_batches.py --dry-run                  # what would happen
    python tools/split_batches.py                            # retire untouched R2_* batches, write R3_* ones
    python tools/split_batches.py R2_030 R2_031 --size 40    # only these batches

Why: a 150-function batch takes 20-30 minutes, so a quota cut, a Vibe time limit or a crash loses (and
re-reads) a lot. The generator tools/make_refine_batches.py is NOT used because it rewrites scores.jsonl and
index.json wholesale, which the running workers and tools/fn.py read.

"Untouched" = no done report, no output JSON, no live lock, not RUNNING in state.json. Those batches' txt
files move to refine/batches/retired/ and their task files to orchestration/tasks_retired/ (outside the
dispatcher's scan); the new R3_* batches keep the members in the original order, so neighbourhoods stay
together. Rows are appended to scores.jsonl with the new batch id (the reader keeps the last row per address).
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORC = ROOT / "orchestration"
REFINE = ORC / "naming" / "refine"
BATCHES = REFINE / "batches"
TEMPLATE = ORC / "naming" / "REFINE_TEMPLATE.md"


def untouched(batch: str, state: dict) -> bool:
    if (ORC / "done" / f"{batch}.md").exists() or (REFINE / "out" / f"{batch}.json").exists():
        return False
    if (ORC / "locks" / f"{batch}.pid").exists() or state.get(batch) == "RUNNING":
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batches", nargs="*", help="batch ids to split (default: every untouched R2_* batch)")
    ap.add_argument("--size", type=int, default=50)
    ap.add_argument("--prefix", default="R3")
    ap.add_argument("--from-prefix", default="R2")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    try:
        state = json.loads((ORC / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    cand = a.batches or [p.stem for p in sorted(BATCHES.glob(f"{a.from_prefix}_*.txt"))]
    cand = [b for b in cand if (BATCHES / f"{b}.txt").exists() and untouched(b, state)]
    if not cand:
        print("no untouched batches")
        return 0
    header, rows = [], []
    for b in cand:
        for line in (BATCHES / f"{b}.txt").read_text(encoding="utf-8", errors="replace").splitlines():
            if re.match(r"^0x[0-9A-Fa-f]{8}\t", line):
                rows.append(line)
            elif line.startswith("# Columns") and not header:
                header.append(line)
    existing = [int(m.group(1)) for p in BATCHES.glob(f"{a.prefix}_*.txt")
                if (m := re.match(rf"{a.prefix}_(\d+)$", p.stem))]
    n0 = max(existing, default=0)
    chunks = [rows[i:i + a.size] for i in range(0, len(rows), a.size)]
    # a tiny last chunk joins the previous one instead of becoming a batch of 3
    if len(chunks) > 1 and len(chunks[-1]) < a.size // 4:
        chunks[-2].extend(chunks.pop())
    print(f"{len(cand)} untouched {a.from_prefix} batches, {len(rows)} functions -> {len(chunks)} {a.prefix} batches of <= {a.size + a.size // 4}")
    if a.dry_run:
        return 0

    template = TEMPLATE.read_text(encoding="utf-8")
    scores = {}
    sp = REFINE / "scores.jsonl"
    for line in sp.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            scores[r["address"].upper()] = r
    (BATCHES / "retired").mkdir(exist_ok=True)
    (ORC / "tasks_retired").mkdir(exist_ok=True)
    for b in cand:
        shutil.move(str(BATCHES / f"{b}.txt"), str(BATCHES / "retired" / f"{b}.txt"))
        t = ORC / "tasks" / f"{b}.md"
        if t.exists():
            shutil.move(str(t), str(ORC / "tasks_retired" / f"{b}.md"))
    new_scores = []
    for i, chunk in enumerate(chunks, n0 + 1):
        bid = f"{a.prefix}_{i:03d}"
        head = (f"# {bid} - refine these {len(chunk)} low-confidence (maybe_) functions\n"
                f"# round: {a.prefix} (re-split from the untouched {a.from_prefix} batches; "
                f"dependencies: M1b_merge_refined done)\n" + "\n".join(header) + "\n")
        (BATCHES / f"{bid}.txt").write_text(head + "\n".join(chunk) + "\n", encoding="utf-8")
        task = template.replace("{{BATCH}}", bid).replace("after: R1_refine_plan", "after: M1b_merge_refined")
        (ORC / "tasks" / f"{bid}.md").write_text(task, encoding="utf-8")
        for line in chunk:
            addr = line.split("\t", 1)[0][2:].upper()
            r = scores.get(addr)
            if r:
                new_scores.append(json.dumps({**r, "batch": bid}, ensure_ascii=False))
    with sp.open("a", encoding="utf-8") as f:
        f.write("\n".join(new_scores) + "\n")
    print(f"wrote {len(chunks)} batches ({a.prefix}_{n0 + 1:03d}..{a.prefix}_{n0 + len(chunks):03d}), "
          f"retired {len(cand)} {a.from_prefix} batches, appended {len(new_scores)} score rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
