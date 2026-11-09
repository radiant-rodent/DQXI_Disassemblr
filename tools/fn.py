#!/usr/bin/env python3
"""One-call dossier for a native function: name, summary, callers, callees, vtable neighbours, body.

    python tools/fn.py 0x0011CB38                  # dossier (body trimmed to 60 lines)
    python tools/fn.py 0x0011CB38 0x0011CB60 -b 0  # several, without the body
    python tools/fn.py 0x0011CB38 --asm 40         # also the first 40 assembly lines
    python tools/fn.py 0x0011CB38 --max 30         # list up to 30 callers / callees
    python tools/fn.py --find Camera_              # functions whose current name contains the text

Uses decomp/xref.json (python tools/xref.py rebuilds it in ~1 s) and the CURRENT names from
decomp/readable/functions/, so it answers in well under a second. Use it instead of walking asm/
or decomp/ with os.walk / grep -r (each such search took 1-6 minutes in worker runs).
Calls through registers (vtable slots) are not in the call graph; the vtable neighbours come from
orchestration/naming/refine/scores.jsonl.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READABLE = ROOT / "decomp" / "readable" / "functions"
NAMED = re.compile(r"^(?!func_|FUN_|maybe_)")


def norm(a: str) -> str:
    return a.upper().replace("0X", "").zfill(8)


def load_names() -> dict[str, tuple[str, Path]]:
    names = {}
    for p in READABLE.glob("*.c"):
        m = re.match(r"^(.*)_([0-9a-fA-F]{8})\.c$", p.name)
        if m:
            names[m.group(2).upper()] = (m.group(1), p)
    return names


def label(names, a: str) -> str:
    n = names.get(a)
    return f"{a} {n[0] if n else '?'}"


def pick(names, addrs: list[str], limit: int) -> tuple[list[str], int]:
    """Named neighbours first (their names are the evidence), then the rest."""
    ordered = sorted(addrs, key=lambda a: (not NAMED.match(names.get(a, ("func_",))[0]), a))
    return ordered[:limit], len(addrs)


def header_and_body(path: Path, body_lines: int) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    head, _, body = text.partition("*/")
    head = re.sub(r"\s*\n\s*\*\s?", " ", head.replace("/*", "")).strip()
    lines = [l for l in body.splitlines() if l.strip()
             and not re.match(r"^\s+(u8|u16|u32|s8|s16|s32|int|short|char|bool|float|undefined\w*|code)\s*\*?\s*\w+(\s*\[\w+\])?;$", l)]
    if body_lines and len(lines) > body_lines:
        lines = lines[:body_lines] + [f"  ... ({len(lines) - body_lines} more lines; use -b 0 to hide, -b 400 for more)"]
    return head, "\n".join(lines) if body_lines else ""


def asm_lines(addr: str, count: int) -> str:
    files = sorted((ROOT / "asm").glob("text/text_*.s"))
    starts = [(int(re.search(r"text_([0-9A-Fa-f]+)\.s", f.name).group(1), 16), f) for f in files]
    target = int(addr, 16)
    cand = [f for s, f in starts if s <= target]
    for f in reversed(cand[-2:]):
        out, on = [], False
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if not on and f"/* 0x{addr}:" in line.upper().replace("/* 0X", "/* 0x"):
                on = True
            if on:
                out.append(line.rstrip())
                if len(out) >= count:
                    break
        if out:
            return "\n".join(out)
    return "(asm not found)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("addr", nargs="*")
    ap.add_argument("-b", "--body", type=int, default=60, help="lines of C body (0 = none)")
    ap.add_argument("--asm", type=int, default=0, help="also print N assembly lines")
    ap.add_argument("--max", type=int, default=12, help="max callers / callees listed")
    ap.add_argument("--find", help="list functions whose current name contains this text")
    a = ap.parse_args()
    names = load_names()
    if a.find:
        q = a.find.lower()
        hits = sorted((addr, n[0]) for addr, n in names.items() if q in n[0].lower())
        for addr, n in hits[:200]:
            print(addr, n)
        print(f"{len(hits)} match(es)" + (" (first 200 shown)" if len(hits) > 200 else ""))
        return 0
    xref = json.loads((ROOT / "decomp" / "xref.json").read_text(encoding="utf-8")) if (ROOT / "decomp" / "xref.json").exists() else {}
    if not xref:
        print("decomp/xref.json missing: run  python tools/xref.py  first", file=sys.stderr)
    scores = {}
    sp = ROOT / "orchestration" / "naming" / "refine" / "scores.jsonl"
    if sp.exists():
        for line in sp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                scores[r["address"].upper()] = r
    for raw in a.addr:
        addr = norm(raw)
        n = names.get(addr)
        print("=" * 100)
        if not n:
            print(f"0x{addr}: no readable file found")
            continue
        name, path = n
        head, body = header_and_body(path, a.body)
        s = scores.get(addr)
        print(f"0x{addr}  {name}   ({path.relative_to(ROOT).as_posix()})")
        print("DOC:", head[:700])
        if s:
            print(f"SCORE: conf={s.get('confidence')} batch={s.get('batch')} vtable={s.get('vtable')} "
                  f"siblings={s.get('vtable_siblings')} strings={s.get('strings')} consts={s.get('shared_constants')}")
            print("NEIGHBOURS:", str(s.get("neighbour_names", ""))[:400])
        x = xref.get(addr, {"callers": [], "callees": []})
        for key in ("callers", "callees"):
            shown, total = pick(names, x[key], a.max)
            named = sum(1 for c in x[key] if NAMED.match(names.get(c, ("func_",))[0]))
            print(f"{key.upper()} ({total}, {named} named; named listed first):")
            for c in shown:
                print("   ", label(names, c))
        if body:
            print("-" * 100)
            print(body)
        if a.asm:
            print("-" * 100)
            print(asm_lines(addr, a.asm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
