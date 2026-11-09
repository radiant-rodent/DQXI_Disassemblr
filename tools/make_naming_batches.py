#!/usr/bin/env python3
"""Split the still-unnamed native functions into ~150-function naming batches.

Every entry point in the retail executable is discovered the same way the
disassembler and the Ghidra export discover them: by scanning ``.text`` for ARM
(``stmfd sp!, {..,lr}``) and Thumb (``push {..,lr}``) prologues. That gives the
canonical 18,787 addresses; naming one function is one batch line, so the
workers never have to guess which functions exist.

Two outputs are produced:

* ``decomp/function_seed.tsv`` - ``address<TAB>mode<TAB>name<TAB>size`` for the
  Ghidra export (``tools/ghidra_scripts/ExportDQXI.java``). Regenerate the
  readable C with it, then run this tool again for the batches.
* ``orchestration/naming/batches/N_###.txt`` plus
  ``orchestration/tasks/N_###.md`` - the P1 naming tasks. Functions are grouped
  by subsystem and call-graph locality: the call graph is read from the
  readable-C tree (``decomp/readable``), a subsystem label is propagated from
  the already-named functions through their callers/callees, and each subsystem
  is chunked by address so a batch stays inside one part of the program.

Usage:
    python tools/make_naming_batches.py --seeds-only   # only function_seed.tsv
    python tools/make_naming_batches.py                # seeds + batches
    python tools/make_naming_batches.py --batch-size 150 --dry-run
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from decompile_native import TEXT_END, find_function_prologues  # noqa: E402
from organize_ghidra import domain_for  # noqa: E402

BINARY = PROJECT_ROOT / "original" / "exefs" / "code.decompressed.bin"
SEED_FILE = PROJECT_ROOT / "decomp" / "function_seed.tsv"
GHIDRA_DIR = PROJECT_ROOT / "decomp" / "ghidra"
READABLE_DIR = PROJECT_ROOT / "decomp" / "readable"
NAMING_DIR = PROJECT_ROOT / "orchestration" / "naming"
BATCH_DIR = NAMING_DIR / "batches"
TASK_DIR = PROJECT_ROOT / "orchestration" / "tasks"
TEMPLATE = NAMING_DIR / "TEMPLATE.md"

UNNAMED = re.compile(r"^(?:FUN_|func_|thunk_FUN_)", re.IGNORECASE)
CALL_IN_TEXT = re.compile(r"\b(?:FUN|func|thunk_FUN)_([0-9A-Fa-f]{8})\b")
CANONICAL_SUBSYSTEMS = [
    "Battle", "Field_and_World", "UI_and_Message", "Actors_and_Entities", "Audio",
    "Camera", "Input", "Kernel_and_System", "Memory_and_Heaps", "Save_and_Persistence",
    "IO_and_Files", "General_Procedures", "Unknown",
]


def load_symbol_names() -> dict[int, str]:
    """Names that already exist in the project, lowest priority last."""
    names: dict[int, str] = {}
    recovered = PROJECT_ROOT / "symbols_recovered.json"
    if recovered.is_file():
        try:
            for addr, name in json.loads(recovered.read_text(encoding="utf-8")).items():
                names[int(addr, 16)] = name
        except (ValueError, json.JSONDecodeError):
            pass
    master = PROJECT_ROOT / "symbols.json"
    if master.is_file():
        try:
            data = json.loads(master.read_text(encoding="utf-8"))
            for sym in data.get("symbols", []):
                if sym.get("type", "function") in ("function", "thunk"):
                    names[int(sym["address"], 16)] = sym["name"]
        except (KeyError, ValueError, json.JSONDecodeError):
            pass
    index = GHIDRA_DIR / "functions_merged.jsonl"
    if index.is_file():
        for line in index.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                addr = int(row["address"], 16)
                name = row.get("name") or ""
            except (KeyError, ValueError, json.JSONDecodeError):
                continue
            if name and not UNNAMED.match(name):
                names[addr] = name
    return names


def discover_functions() -> list[dict]:
    """Every entry point with address, mode, size and the seed name."""
    data = BINARY.read_bytes()
    prologues = find_function_prologues(data[:TEXT_END - 0x00100000])
    names = load_symbol_names()
    out = []
    for i, (addr, mode) in enumerate(prologues):
        end = prologues[i + 1][0] if i + 1 < len(prologues) else TEXT_END
        out.append({
            "address": addr,
            "mode": mode,
            "size": max(1, end - addr),
            "name": names.get(addr, f"FUN_{addr:08X}"),
        })
    return out


def write_seeds(functions: list[dict]) -> int:
    SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"0x{f['address']:08X}\t{f['mode']}\t{f['name']}\t{f['size']}" for f in functions]
    SEED_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    named = sum(1 for f in functions if not UNNAMED.match(f["name"]))
    print(f"wrote {SEED_FILE.relative_to(PROJECT_ROOT)}: {len(functions):,} seeds "
          f"({named:,} already named, {len(functions) - named:,} unnamed)")
    return 0


def readable_paths() -> dict[int, Path]:
    """address -> the best C source that exists for it.

    Prefers the readability pass (``decomp/readable``), falls back to the raw
    Ghidra export (``decomp/ghidra``), and maps entry points that Ghidra only
    covered with a containing function to that container's source.
    """
    index = GHIDRA_DIR / "functions_merged.jsonl"
    out: dict[int, Path] = {}
    containers: dict[int, int] = {}
    if not index.is_file():
        return out
    for line in index.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            addr = int(row["address"], 16)
            rel = row.get("file")
            if rel:
                for candidate in (READABLE_DIR / rel, GHIDRA_DIR / rel):
                    if candidate.is_file():
                        out[addr] = candidate
                        break
            if row.get("status") == "covered_by" and row.get("container_entry"):
                containers[addr] = int(row["container_entry"], 16)
        except (KeyError, ValueError, json.JSONDecodeError):
            continue
    for addr, container in containers.items():
        if addr not in out and container in out:
            out[addr] = out[container]
    return out


def call_graph(functions: list[dict], paths: dict[int, Path]) -> dict[int, set[int]]:
    """Undirected adjacency (callee and caller are linked) from the readable C."""
    by_name = {f["name"]: f["address"] for f in functions if not UNNAMED.match(f["name"])}
    edges: dict[int, set[int]] = collections.defaultdict(set)
    known = {f["address"] for f in functions}
    for func in functions:
        addr = func["address"]
        path = paths.get(addr)
        if path is None or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in CALL_IN_TEXT.finditer(text):
            target = int(m.group(1), 16)
            if target in known and target != addr:
                edges[addr].add(target)
                edges[target].add(addr)
        header = text.split("*/", 1)[0]
        m = re.search(r"^\s*\*\s*Calls:\s*(.+)$", header, re.MULTILINE)
        if m:
            for name in m.group(1).split(","):
                target = by_name.get(name.strip())
                if target is not None and target != addr:
                    edges[addr].add(target)
                    edges[target].add(addr)
    return edges


def subsystem_labels(functions: list[dict], edges: dict[int, set[int]]) -> dict[int, str]:
    """Propagate a subsystem label from named functions to their unnamed neighbours.

    BFS from every named function that carries a real domain. Functions with no
    named reachable neighbour fall back to the domain of the closest named
    function by address (code layout is per module, so that is a good guess);
    failing that they are ``Unknown``.
    """
    labels: dict[int, str] = {}
    queue: collections.deque[int] = collections.deque()
    for func in functions:
        addr, name = func["address"], func["name"]
        if UNNAMED.match(name):
            continue
        domain = domain_for(name)
        if domain == "General_Procedures":
            continue
        labels[addr] = domain
        queue.append(addr)
    while queue:
        addr = queue.popleft()
        for nxt in edges.get(addr, ()):
            if nxt not in labels:
                labels[nxt] = labels[addr]
                queue.append(nxt)

    named = sorted((f["address"], domain_for(f["name"])) for f in functions
                   if not UNNAMED.match(f["name"]))
    named_addrs = [a for a, _ in named]
    import bisect
    for func in functions:
        addr = func["address"]
        if addr in labels:
            continue
        i = bisect.bisect_left(named_addrs, addr)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(named):
                dist = abs(named[j][0] - addr)
                if best is None or dist < best[0]:
                    best = (dist, named[j][1])
        labels[addr] = best[1] if best and best[0] <= 0x20000 else "Unknown"
    return labels


def make_batches(functions: list[dict], batch_size: int, dry_run: bool) -> dict:
    paths = readable_paths()
    if not paths:
        print("warning: decomp/ghidra/functions_merged.jsonl is missing; "
              "readable paths will be empty (run the Ghidra export first)", file=sys.stderr)
    edges = call_graph(functions, paths)
    labels = subsystem_labels(functions, edges)

    unnamed = [f for f in functions if UNNAMED.match(f["name"])]
    grouped: dict[str, list[dict]] = collections.defaultdict(list)
    for func in unnamed:
        grouped[labels.get(func["address"], "Unknown")].append(func)

    order = [s for s in CANONICAL_SUBSYSTEMS if s in grouped]
    order += sorted(s for s in grouped if s not in CANONICAL_SUBSYSTEMS)

    batches: list[dict] = []
    number = 0
    for subsystem in order:
        members = sorted(grouped[subsystem], key=lambda f: f["address"])
        for start in range(0, len(members), batch_size):
            number += 1
            batch_id = f"N_{number:03d}"
            chunk = members[start:start + batch_size]
            lines = [
                f"# {batch_id} - {subsystem} - {len(chunk)} unnamed functions",
                "# address\tsize\tC source (readable when available; a container file or",
                "# functions_index.json means Ghidra merged the entry point into another function)",
            ]
            for func in chunk:
                path = paths.get(func["address"])
                rel = (path.relative_to(PROJECT_ROOT).as_posix()
                       if path is not None else "decomp/ghidra/functions_index.json")
                lines.append(f"0x{func['address']:08X}\t0x{func['size']:X}\t{rel}")
            batches.append({
                "id": batch_id,
                "subsystem": subsystem,
                "count": len(chunk),
                "first": f"0x{chunk[0]['address']:08X}",
                "last": f"0x{chunk[-1]['address']:08X}",
                "text": "\n".join(lines) + "\n",
            })

    template = TEMPLATE.read_text(encoding="utf-8")
    summary = {
        "functions_total": len(functions),
        "functions_named": len(functions) - len(unnamed),
        "functions_unnamed": len(unnamed),
        "batch_size": batch_size,
        "batches": len(batches),
        "by_subsystem": {s: len(grouped[s]) for s in order},
        "batch_index": [{k: b[k] for k in ("id", "subsystem", "count", "first", "last")}
                        for b in batches],
    }
    print(f"{len(functions):,} entry points, {len(unnamed):,} unnamed -> {len(batches)} batches")
    for subsystem in order:
        print(f"  {subsystem:24} {len(grouped[subsystem]):6,} functions")
    if dry_run:
        return summary

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    for old in BATCH_DIR.glob("N_*.txt"):
        old.unlink()
    for b in batches:
        (BATCH_DIR / f"{b['id']}.txt").write_text(b["text"], encoding="utf-8")
        md = template.replace("{{BATCH}}", b["id"])
        (TASK_DIR / f"{b['id']}.md").write_text(md, encoding="utf-8")
    (NAMING_DIR / "out").mkdir(parents=True, exist_ok=True)
    (NAMING_DIR / "batches" / "index.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {len(batches)} batch files -> {BATCH_DIR.relative_to(PROJECT_ROOT)}")
    print(f"wrote {len(batches)} task files  -> {TASK_DIR.relative_to(PROJECT_ROOT)}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seeds-only", action="store_true", help="only write decomp/function_seed.tsv")
    ap.add_argument("--batch-size", type=int, default=150, help="functions per batch (default 150)")
    ap.add_argument("--dry-run", action="store_true", help="print the grouping, write nothing")
    args = ap.parse_args()

    if not BINARY.is_file():
        print(f"missing {BINARY}; extract the ROM first", file=sys.stderr)
        return 1
    functions = discover_functions()
    if not args.dry_run or not SEED_FILE.is_file():
        write_seeds(functions)
    if args.seeds_only:
        return 0
    make_batches(functions, args.batch_size, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
