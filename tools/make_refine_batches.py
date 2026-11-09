#!/usr/bin/env python3
"""Build the second naming pass ("refine") batches for the low-confidence names.

After ``M1_merge_names`` the readable C carries ~8,500 confident names. Several
thousand functions still start with ``maybe_`` (or sit below confidence 0.5),
but many of them now live next to named callers/callees/vtable siblings, so a
second, evidence-aware naming pass can resolve them properly.

This tool does NOT name anything. It:

1. loads the merged catalog (``decomp/ghidra/functions_merged.jsonl``) and picks
   every entry whose final name starts with ``maybe_`` OR whose confidence is
   below 0.5 (data/label rows are excluded - they are not functions);
2. scores each candidate by how much *confident* context it has right now:
   distinct confident callers, distinct confident callees, vtable siblings
   (constants shared with confident functions whose evidence names that vtable)
   and readable string literals. The call graph and constants are read from the
   readable C tree (``decomp/readable``), calls are matched through the full
   function-name map, and ``func_XXXXXXXX`` mid-function targets are ignored;
3. groups the candidates by neighbourhood (strongest shared vtable, else the
   best confident call partner, else a 256 KiB address block), sorts by score
   (easiest wins first) and chunks each neighbourhood into ~150-function
   batches written to ``orchestration/naming/refine/batches/{{PREFIX}}_###.txt``;
4. renders one task file per batch from ``orchestration/naming/REFINE_TEMPLATE.md``
   and writes a machine-readable summary to
   ``orchestration/naming/refine/index.json`` plus the full scoring to
   ``orchestration/naming/refine/scores.jsonl``.

Usage:
    python tools/make_refine_batches.py                # generate everything
    python tools/make_refine_batches.py --dry-run      # print the stats only
    python tools/make_refine_batches.py --prefix R2     # a later refine round
    python tools/make_refine_batches.py --prefix R_redo --addresses redo.txt
"""
from __future__ import annotations

import os
import sys

# Windows/parallel-worker guard: another tool package ("tools/types" (renamed to tools/typedb)) shadows
# the stdlib "types" module for every script started inside tools/. Drop the
# script directory from sys.path before importing anything else here, so this
# tool keeps working regardless of what other tools put beside it.
_SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
_orig_path = list(sys.path)
_best_effort = []
for _p in _orig_path:
    try:
        if os.path.abspath(_p or os.getcwd()) != _SCRIPT_DIR:
            _best_effort.append(_p)
    except OSError:
        _best_effort.append(_p)
sys.path = _best_effort

import argparse
import collections
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# do NOT re-add tools/ to sys.path here: the parallel worker's "tools/types" (renamed to tools/typedb)
# package would shadow the stdlib "types" module for this whole process.

MERGED_JSONL = PROJECT_ROOT / "decomp" / "ghidra" / "functions_merged.jsonl"
READABLE_DIR = PROJECT_ROOT / "decomp" / "readable"
REFINE_DIR = PROJECT_ROOT / "orchestration" / "naming" / "refine"
BATCH_DIR = REFINE_DIR / "batches"
OUT_DIR = REFINE_DIR / "out"
TASK_DIR = PROJECT_ROOT / "orchestration" / "tasks"
TEMPLATE = PROJECT_ROOT / "orchestration" / "naming" / "REFINE_TEMPLATE.md"

CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
HEX8_RE = re.compile(r"0x[0-9A-F]{8}\b")
STR_RE = re.compile(r'"[^"\n]{2,}"')
VTABLE_FWD_RE = re.compile(r"\bvtables?\b[^.\n]{0,120}?0x([0-9A-Fa-f]{6,8})\b")
VTABLE_REV_RE = re.compile(r"0x([0-9A-Fa-f]{6,8})\b[^.\n]{0,120}?\bvtables?\b")
VTABLE_ANY_RE = re.compile(r"\b(?:vtb|vtbl|vtable[s]?)\b[^.\n]{0,120}?0x([0-9A-Fa-f]{6,8})")
FILE_SUFFIX_RE = re.compile(r"_([0-9A-Fa-f]{8})$")
NON_CALL_KEYWORDS = {
    "if", "while", "switch", "for", "return", "sizeof", "typeof", "enum",
    "struct", "union", "else", "do", "__attribute__", "defined", "case",
}

# score weights (documented also in the template)
WEIGHT_CALLER = 3
WEIGHT_CALLEE = 3
WEIGHT_VTABLE = 1     # per sibling, capped
WEIGHT_STRING = 1     # per distinct literal, capped
VTABLE_CAP = 5
STRING_CAP = 5
CONST_CAP = 5
WEIGHT_CONST = 1


def is_named(row: dict) -> bool:
    return bool(row.get("name")) and not row.get("name", "").startswith("maybe_")


def is_context(row: dict) -> bool:
    """A readable, already-named function usable as confident context.

    Seed names (e.g. the CTR-SDK exports) carry no confidence value in the
    merged catalog; every low-confidence non-`maybe_` name was left as written
    by the merge, so being named is the whole test.
    """
    return is_named(row) and row.get("symbol_type") not in ("label", "data")


def is_candidate(row: dict) -> bool:
    """A function this refine pass re-names.

    anything called `maybe_`, plus named-but-low-confidence leftovers
    (confidence < 0.5); data/label pseudo-symbol rows are never candidates.
    """
    if row.get("symbol_type") in ("label", "data"):
        return False
    if row.get("name", "").startswith("maybe_"):
        return True
    conf = row.get("confidence")
    return conf is not None and 0.0 + conf < 0.5


def load_functions() -> list[dict]:
    if not MERGED_JSONL.is_file():
        print(f"missing {MERGED_JSONL}; run tools/merge_names.py first", file=sys.stderr)
        raise SystemExit(1)
    rows: list[dict] = []
    for line in MERGED_JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        row["address_int"] = int(row["address"], 16)
        rows.append(row)
    # rows are address-sorted; tolerate unsorted input anyway
    rows.sort(key=lambda r: r["address_int"])
    return rows


def readable_paths(rows: list[dict]) -> dict[int, Path]:
    """address -> readable C file, via the ``<name>_<8hex>.c`` suffix scheme."""
    suffixes: dict[int, Path] = {}
    for sub in ("functions", "recovered"):
        d = READABLE_DIR / sub
        if not d.is_dir():
            continue
        for path in d.iterdir():
            m = FILE_SUFFIX_RE.search(path.stem)
            if m:
                suffixes[int(m.group(1), 16)] = path
    out: dict[int, Path] = {}
    for row in rows:
        rel = row.get("file") or ""
        m = FILE_SUFFIX_RE.search(Path(rel).stem)
        if m:
            p = suffixes.get(int(m.group(1), 16))
            if p is not None:
                out[row["address_int"]] = p
    return out


def load_symbols_confident_names() -> set[str]:
    """Confident function-name set from symbols.json (fallback view)."""
    path = PROJECT_ROOT / "symbols.json"
    names: set[str] = set()
    if path.is_file():
        for sym in json.loads(path.read_text(encoding="utf-8")).get("symbols", []):
            if sym.get("type", "function") == "function":
                names.add(sym["name"])
    return names


def strip_doc_comment(text: str) -> str:
    """Drop the leading /* */ header so the scanned text is only code."""
    end = text.find("*/")
    if text.lstrip().startswith("/*") and end != -1:
        return text[end + 2:]
    return text


def vtable_evidence(text: str) -> set[int]:
    """vtable addresses mentioned in a row's evidence/summary text."""
    found: set[int] = set()
    for rx in (VTABLE_FWD_RE, VTABLE_REV_RE, VTABLE_ANY_RE):
        for m in rx.finditer(text):
            v = int(m.group(1), 16)
            if v >= 0x00100000:
                found.add(v)
    return found


def score_candidates(
    rows: list[dict],
    paths: dict[int, Path],
) -> tuple[list[dict], dict[int, set[int]], dict[int, set[int]]]:
    """Score every maybe_/low-confidence candidate; return (scored, callers, callees).

    ``callers``/``callees`` map address -> set of addresses across the WHOLE
    function catalog, so neighbours of adjacent naming passes reuse the edges.
    """
    by_name = {r["name"]: r["address_int"] for r in rows if r.get("name")}
    confident = set()
    for r in rows:
        if is_context(r):
            confident.add(r["address_int"])

    callers: dict[int, set[int]] = collections.defaultdict(set)
    callees: dict[int, set[int]] = collections.defaultdict(set)
    bodies: dict[int, str] = {}

    for row in rows:
        addr = row["address_int"]
        path = paths.get(addr)
        if path is None or not path.is_file():
            continue
        body = strip_doc_comment(path.read_text(encoding="utf-8", errors="replace"))
        bodies[addr] = body
        for name in CALL_RE.findall(body):
            if name in NON_CALL_KEYWORDS:
                continue
            target = by_name.get(name)
            if target is not None and target != addr:
                callees[addr].add(target)
                callers[target].add(addr)

    # confident functions that document a vtable: constant -> set of owner addresses
    vtable_owners: dict[int, set[int]] = collections.defaultdict(set)
    # how many confident rows' evidence/summary mention each 8-hex constant
    const_mentions: dict[int, int] = collections.Counter()
    for row in rows:
        if not is_context(row):
            continue
        text = (row.get("evidence") or "") + " " + (row.get("summary") or "")
        for v in vtable_evidence(text):
            vtable_owners[v].add(row["address_int"])
        for hex8 in HEX8_RE.findall(text):
            const_mentions[int(hex8, 16)] += 1

    batch_of = {r["address_int"]: r for r in rows}
    scored: list[dict] = []
    for row in rows:
        if not is_candidate(row):
            continue
        if row.get("symbol_type") in ("label", "data"):
            continue  # not functions: naming them again would waste a slot
        addr = row["address_int"]
        body = bodies.get(addr, "")
        conf_callees = sorted(c & confident for c in [callees.get(addr, set())])
        conf_callers = sorted(c & confident for c in [callers.get(addr, set())])
        const_addrs = {int(hex8, 16) for hex8 in HEX8_RE.findall(body)}
        own_vtables = vtable_evidence((row.get("evidence") or "") + " " + (row.get("summary") or ""))
        sibling_vtables: list[tuple[int, set[int]]] = []
        for v in own_vtables:
            owners = vtable_owners.get(v)
            if owners:
                sibling_vtables.append((v, owners))
        for v in const_addrs:
            owners = vtable_owners.get(v)
            if owners and all(v != s[0] for s in sibling_vtables):
                sibling_vtables.append((v, owners))
        strings = set(STR_RE.findall(body))
        shared_constants = {v for v in const_addrs if const_mentions.get(v)}
        functions_only_conf = {batch_of[a]["name"] for a in conf_callees[0] if a in batch_of}
        functions_conf = {batch_of[a]["name"] for a in conf_callers[0]} | functions_only_conf

        score = (
            WEIGHT_CALLER * len(conf_callers[0])
            + WEIGHT_CALLEE * len(conf_callees[0])
            + WEIGHT_VTABLE * min(sum(len(o) for _, o in sibling_vtables), VTABLE_CAP)
            + WEIGHT_STRING * min(len(strings), STRING_CAP)
            + WEIGHT_CONST * min(len(shared_constants), CONST_CAP)
        )
        vtable_sibling_names: list[str] = sorted(
            {batch_of[a]["name"] for _, owners in sibling_vtables for a in owners})[:6]
        best_vtable = max(sibling_vtables, key=lambda s: len(s[1])) if sibling_vtables else None
        # partner: the confident neighbour (caller or callee) with most total edges
        # (the function most worth reading the candidate next to)
        def partner_weight(other: int) -> tuple[int, int]:
            mutual = len(callees.get(other, set()) & {addr}) + len(
                callers.get(other, set()) & {addr})
            return (-mutual, abs(other - addr))

        confident_partner_pool = sorted(conf_callers[0] | conf_callees[0],
                                        key=partner_weight)
        if not confident_partner_pool:
            confident_partner_pool = sorted(callers.get(addr, set()) & confident
                                            | callees.get(addr, set()) & confident)
        best_partner = confident_partner_pool[0] if confident_partner_pool else None
        cluster = (
            f"vt:{best_vtable[0]:08X}" if best_vtable is not None
            else (f"nb:{best_partner:08X}" if best_partner is not None
                  else f"blk:{addr & ~0x3FFFF:08X}")
        )
        neighbour_names = ", ".join(sorted(functions_conf) + vtable_sibling_names)[:220]
        scored.append({
            "address_int": addr,
            "address": row["address"],
            "name": row["name"],
            "confidence": row.get("confidence"),
            "signature": row.get("signature"),
            "summary": row.get("summary"),
            "size": row.get("size"),
            "readable": (str(paths[addr].relative_to(PROJECT_ROOT).as_posix())
                         if addr in paths else "decomp/ghidra/functions_index.json"),
            "batch": row.get("batch"),
            "score": score,
            "callers_conf": len(conf_callers[0]),
            "callees_conf": len(conf_callees[0]),
            "vtable_siblings": min(sum(len(o) for _, o in sibling_vtables), VTABLE_CAP),
            "vtable": None if best_vtable is None else f"0x{best_vtable[0]:08X}",
            "strings": len(strings),
            "shared_constants": len(shared_constants),
            "cluster": cluster,
            "neighbour_names": neighbour_names,
        })
        scored[-1]["_conf_callers"] = sorted(conf_callers[0])
        scored[-1]["_conf_callees"] = sorted(conf_callees[0])
    return scored, callers, callees


def make_batches(scored: list[dict], batch_size: int) -> list[list[dict]]:
    """Pack whole neighbourhoods (clusters) into ~batch_size batches.

    Clusters are ordered so the easiest wins come first (highest member score).
    A cluster always stays contiguous in the batch stream; a cluster larger than
    the batch size is split over consecutive batches, and a new batch is started
    only when the next cluster would overflow. This keeps batches inside one
    neighbourhood group without exploding the count to thousands.
    """
    clusters: dict[str, list[dict]] = collections.defaultdict(list)
    for item in scored:
        clusters[item["cluster"]].append(item)
    ordered = sorted(
        clusters.values(),
        key=lambda members: (-max(m["score"] for m in members),
                             members[0]["address_int"]),
    )
    batches: list[list[dict]] = []
    current: list[dict] = []
    for members in ordered:
        ms = sorted(members, key=lambda m: (-m["score"], m["address_int"]))
        if len(current) + len(ms) > batch_size and current:
            batches.append(current)
            current = []
        if len(ms) > batch_size:
            for start in range(0, len(ms), batch_size):
                current = []
                batches.append(ms[start:start + batch_size])
        else:
            current.extend(ms)
    if current:
        batches.append(current)
    return [b for b in batches if b]


def batch_text(batch_id: str, members: list[dict], round_note: str) -> str:
    lines = [
        f"# {batch_id} - refine these {len(members)} low-confidence (maybe_) functions",
        f"# {round_note}",
        "# Columns: address<TAB>current maybe name<TAB>confidence<TAB>readable C path<TAB>context score",
        "# Score = 3*confident callers + 3*confident callees + vtable siblings + string",
        "# literals + shared constants (all capped). See tools/make_refine_batches.py.",
        "# The function's previous guess & evidence are in the readable file's header;",
        "# every candidate also keeps its original proposal batch id in",
        "# orchestration/naming/refine/index.json (prev_batch). Shared vtable",
        "# candidates live in the same cluster; constant-level neighbours are in",
        "# orchestration/naming/refine/scores.jsonl (neighbour_names).",
    ]
    rows = []
    for m in members:
        conf = m["confidence"]
        conf_text = "?" if conf is None else f"{0.0 + conf:.2f}"
        rows.append(
            f"0x{m['address_int']:08X}\t{m['name']}\t{conf_text}\t{m['readable']}\t{m['score']}"
        )
    return "\n".join(lines) + "\n" + "\n".join(rows) + "\n"


def clean_previous(prefix: str) -> None:
    """Remove previous round outputs with exactly this prefix.

    Windows: other processes (task board/observer) may briefly hold files, so
    retry unlink a few times before giving up.
    """
    import time

    def unlink(path: Path) -> None:
        for attempt in range(5):
            try:
                path.unlink()
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.5 * (attempt + 1))

    pat = re.compile(rf"^{re.escape(prefix)}_\d{{3,}}$")
    removed = 0
    if BATCH_DIR.is_dir():
        for p in BATCH_DIR.iterdir():
            if p.suffix in (".txt", ".json") and pat.match(p.stem):
                unlink(p)
                removed += 1
    if OUT_DIR.is_dir():
        for p in OUT_DIR.iterdir():
            if p.suffix == ".json" and pat.match(p.stem):
                unlink(p)
                removed += 1
    for p in TASK_DIR.glob(f"{prefix}_*.md"):
        if pat.match(p.stem):
            unlink(p)
            removed += 1
    if removed:
        print(f"cleaned {removed} previous {prefix}_### outputs")


def distribution(scored: list[dict]) -> dict:
    histogram = collections.Counter()
    for s in scored:
        if s["score"] == 0:
            bucket = "0"
        elif s["score"] < 6:
            bucket = "1-5"
        elif s["score"] < 12:
            bucket = "6-11"
        elif s["score"] < 21:
            bucket = "12-20"
        elif s["score"] < 40:
            bucket = "21-39"
        else:
            bucket = "40+"
        histogram[bucket] += 1
    order = ["0", "1-5", "6-11", "12-20", "21-39", "40+"]
    return {b: histogram[b] for b in order if histogram[b]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--batch-size", type=int, default=150, help="functions per batch (default 150)")
    ap.add_argument("--prefix", default="R", help="batch id prefix (R → R_###; later rounds use R2)")
    ap.add_argument("--dry-run", action="store_true", help="print stats, write nothing")
    ap.add_argument("--addresses", help="optional file with one 0x address per line: refine only these")
    args = ap.parse_args()

    rows = load_functions()
    paths = readable_paths(rows)
    scored, _callers, _callees = score_candidates(rows, paths)

    if args.addresses:
        wanted = set()
        for line in Path(args.addresses).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                wanted.add(int(line, 16))
        scored = [s for s in scored if s["address_int"] in wanted]

    conf_named = sum(1 for r in rows if is_context(r))
    names_maybe = sum(1 for r in rows if r.get("name", "").startswith("maybe_"))
    low_conf = sum(1 for r in rows if r.get("confidence") is not None and 0.0 + r["confidence"] < 0.5)

    print(f"catalog: {len(rows):,} rows, {conf_named:,} confident names")
    print(f"maybe_ named: {names_maybe:,}, confidence < 0.5: {low_conf:,}")
    print(f"refine candidates (functions): {len(scored):,}")
    print("score distribution:", distribution(scored))
    zero_ctx = sum(1 for s in scored if s["score"] == 0)
    with_vtable = sum(1 for s in scored if s["vtable_siblings"])
    print(f"  zero-context candidates: {zero_ctx:,}; with vtable siblings: {with_vtable:,}")
    clusters = collections.Counter(s["cluster"].split(":", 1)[0] for s in scored)
    print(f"  neighbourhood kinds: {dict(clusters)}")

    if args.dry_run:
        return 0

    batches = make_batches(scored, args.batch_size)
    TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    if not TEMPLATE.is_file():
        print(f"missing {TEMPLATE}; write the template first", file=sys.stderr)
        return 1
    template = TEMPLATE.read_text(encoding="utf-8")
    round_note = (f"round: {args.prefix} (dependencies: M1_merge_names done "
                  f"-> confident names available in the readable C)")

    clean_previous(args.prefix)
    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index = {
        "round": args.prefix,
        "generated_from": "decomp/ghidra/functions_merged.jsonl + decomp/readable/**",
        "candidates": len(scored),
        "batches": len(batches),
        "batch_size": args.batch_size,
        "score_distribution": distribution(scored),
        "batch_index": [],
        "members": {},
    }
    scores_lines = []
    for i, members in enumerate(batches, 1):
        batch_id = f"{args.prefix}_{i:03d}"
        (BATCH_DIR / f"{batch_id}.txt").write_text(
            batch_text(batch_id, members, round_note), encoding="utf-8")
        after_dep = "R1_refine_plan" if args.prefix == "R" else "M1b_merge_refined"
        rendered_task = template.replace("{{BATCH}}", batch_id)
        if "after: R1_refine_plan" in rendered_task and after_dep != "R1_refine_plan":
            rendered_task = rendered_task.replace("after: R1_refine_plan", f"after: {after_dep}")
        (TASK_DIR / f"{batch_id}.md").write_text(rendered_task, encoding="utf-8")
        index["batch_index"].append({
            "id": batch_id,
            "count": len(members),
            "first": members[0]["address"],
            "last": members[-1]["address"],
            "score_min": min(m["score"] for m in members),
            "score_max": max(m["score"] for m in members),
            "clusters": sorted({m["cluster"] for m in members})[:8],
        })
        for m in members:
            canon = f"0x{m['address_int']:08X}"
            index["members"][canon] = {
                "address": canon,
                "batch": batch_id,
                "name": m["name"],
                "confidence": m["confidence"],
                "prev_batch": m["batch"],
                "score": m["score"],
                "cluster": m["cluster"],
            }
            scores_lines.append(json.dumps({
                "address": m["address"],
                "name": m["name"],
                "confidence": m["confidence"],
                "prev_batch": m["batch"],
                "batch": batch_id,
                "score": m["score"],
                "callers_conf": m["callers_conf"],
                "callees_conf": m["callees_conf"],
                "vtable_siblings": m["vtable_siblings"],
                "vtable": m["vtable"],
                "strings": m["strings"],
                "shared_constants": m["shared_constants"],
                "cluster": m["cluster"],
                "neighbour_names": m["neighbour_names"],
                "readable": m["readable"],
            }, ensure_ascii=False))

    (REFINE_DIR / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False),
                                           encoding="utf-8")
    (REFINE_DIR / "scores.jsonl").write_text("\n".join(scores_lines) + "\n", encoding="utf-8")

    print(f"wrote {len(batches)} batch files  -> {BATCH_DIR.relative_to(PROJECT_ROOT)}")
    print(f"wrote {len(batches)} task files   -> {TASK_DIR.relative_to(PROJECT_ROOT)}")
    print(f"wrote index.json / scores.jsonl   -> {REFINE_DIR.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
