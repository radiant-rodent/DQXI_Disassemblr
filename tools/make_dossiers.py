#!/usr/bin/env python3
"""Pre-bake the dossiers of a refine batch, so a worker starts with zero tool calls for context.

    python tools/make_dossiers.py R3_004            # -> orchestration/naming/refine/dossiers/R3_004.md
    python tools/make_dossiers.py R3_004 R3_005     # several batches
    python tools/make_dossiers.py --all-pending     # every refine batch without a done report

Each function gets the output of ``tools/fn.py`` (current name, doc, callers/callees with names, vtable
neighbours, trimmed body) in batch order, with a header line per function and an index at the top.
The dispatcher runs this before it starts a refine task, so the names are as fresh as the last merge.
Measured on 88 worker runs: 86 % of the time was model turns, and 55 minutes went into searches that
this file makes unnecessary.
"""
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BATCHES = ROOT / "orchestration" / "naming" / "refine" / "batches"
OUT = ROOT / "orchestration" / "naming" / "refine" / "dossiers"


def make(batch: str) -> Path:
    txt = BATCHES / f"{batch}.txt"
    addrs = []
    for line in txt.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^(0x[0-9A-Fa-f]{8})\t", line)
        if m:
            addrs.append(m.group(1))
    OUT.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "fn.py"), *addrs, "-b", "40", "--max", "8"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
    body = r.stdout
    head = (f"# Dossiers for {batch} ({len(addrs)} functions), generated {time.strftime('%Y-%m-%d %H:%M')}\n"
            "# One block per function, in batch order (highest context score first). Names are those at\n"
            "# generation time; run `python tools/fn.py 0xADDR [--asm 40]` for a live view or more detail.\n"
            "# Read it in chunks of about 10 functions; decide each one before moving on.\n\n"
            "INDEX: " + " ".join(a[2:] for a in addrs) + "\n")
    path = OUT / f"{batch}.md"
    path.write_text(head + body, encoding="utf-8")
    return path


def main() -> int:
    args = sys.argv[1:]
    if args == ["--all-pending"]:
        done = {p.stem for p in (ROOT / "orchestration" / "done").glob("*.md")}
        args = [p.stem for p in sorted(BATCHES.glob("R*_*.txt")) if p.stem not in done]
    if not args:
        print(__doc__)
        return 1
    for b in args:
        p = make(b)
        print(f"{b}: {p.relative_to(ROOT).as_posix()} ({p.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
