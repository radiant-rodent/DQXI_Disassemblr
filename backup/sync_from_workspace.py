#!/usr/bin/env python3
"""Copy the project's own work (names, types, docs, tools) from the live workspace
into this git clone, then commit and push it as radiant-rodent.

    python backup/sync_from_workspace.py              # copy, commit, push
    python backup/sync_from_workspace.py --dry-run    # only show what would change
    python backup/sync_from_workspace.py --no-push    # commit locally only

Design rules
  * ALLOWLIST, not blocklist: only the paths in INCLUDE are ever copied. A new
    folder in the workspace is NOT published until it is added here.
  * Hard guards on top of the allowlist: forbidden extensions, forbidden path
    prefixes, ROM container magic bytes, and a per-file size cap. Any hit aborts
    the whole run before git is touched.
  * Never disturbs the running workers: the workspace is only *read*. Files
    modified in the last HOLD_SECONDS, or JSON that does not parse (half-written),
    keep their previously committed version and are reported as "held".
  * Deletions are mirrored only inside the allowlisted paths; repo-only files
    (backup/, RESTORE.md, .gitignore, .gitattributes, LICENSE) are never touched.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = Path(os.environ.get("DQXI_WORKSPACE", r"."))

HOLD_SECONDS = 120
MAX_FILE_BYTES = 45 * 1024 * 1024        # GitHub warns at 50 MB, refuses at 100 MB
MAX_SNAPSHOT_BYTES = 400 * 1024 * 1024    # sanity cap on the whole published tree

# --- what is published -------------------------------------------------------------
# (path, kind) where kind is "file" or "tree" (recursive). Paths are workspace-relative.
INCLUDE = [
    # top level
    ("README.md", "file"), ("sections.ld", "file"), ("DQXI_Viewer.pyw", "file"),
    ("run_editor.bat", "file"), ("run_export.bat", "file"), ("run_progress.bat", "file"),
    ("run_viewer.bat", "file"), ("run_viewer_rs.bat", "file"),
    # THE MAPPINGS: function names, signatures, summaries, params, confidence
    ("symbols.json", "file"),
    ("symbols_recovered.json", "file"),
    ("decomp/native_names.json", "file"),
    ("decomp/function_seed.tsv", "file"),
    ("decomp/ghidra/functions.jsonl", "file"),          # baseline catalogue (no C bodies)
    ("decomp/ghidra/functions_merged.jsonl", "file"),   # merged names/summaries/evidence
    ("decomp/ghidra/functions_index.json", "file"),
    ("decomp/ghidra/missing_result.jsonl", "file"),
    ("decomp/ghidra/dqxi_types.h", "file"),
    ("decomp/ghidra/prelude.h", "file"),
    ("decomp/ghidra/README.md", "file"),
    ("decomp/ghidra/COVERAGE.md", "file"),
    # worker proposals = the source of truth merge_names rebuilds everything from
    ("orchestration/naming", "tree"),
    ("orchestration/types/README.md", "file"),
    ("orchestration/types/out", "tree"),
    ("orchestration/types/merged", "tree"),
    ("orchestration/types/merged_demo", "tree"),
    ("orchestration/types/samples", "tree"),
    # orchestration itself (plan, rules, dispatcher, task files, reports)
    ("orchestration/PLAN.md", "file"), ("orchestration/WORKER_RULES.md", "file"),
    ("orchestration/dispatch.py", "file"), ("orchestration/live.py", "file"),
    ("orchestration/vertex_agent.py", "file"),
    ("orchestration/tasks", "tree"), ("orchestration/tasks_retired", "tree"),
    ("orchestration/done", "tree"),
    # hand-written code, headers, tools, docs, editor
    ("src", "tree"), ("include", "tree"),
    ("tools", "tree"), ("tests", "tree"), ("docs", "tree"),
    ("viewer", "tree"), ("viewer_rs", "tree"),
    ("editor_projects", "tree"),
    ("progress", "tree"),
    ("third_party/SPICA", "tree"),
]

# Excluded inside the allowlisted trees (fnmatch on the workspace-relative posix path).
EXCLUDE_GLOBS = [
    "*/__pycache__/*", "*.pyc",
    "viewer_rs/target/*", "*/bin/*", "*/obj/*",
    "orchestration/naming/refine/dossiers/*",   # contain decompiled code excerpts; regenerable
    "orchestration/naming/refine/tmp/*",
    "orchestration/naming/refine/scores.jsonl",  # regenerable
    "orchestration/naming/refine/index.json",    # regenerable
    "progress/map.html", "progress/tasks.html",  # multi-MB generated pages
    "third_party/SPICA/*.dll", "third_party/SPICA/*.zip",  # upstream binaries, not needed
]

# --- hard guards (abort the run) ---------------------------------------------------
FORBIDDEN_EXT = {
    ".3ds", ".cci", ".cia", ".cxi", ".app", ".ncch", ".bin", ".code", ".bch", ".bxon",
    ".bcstm", ".bcwav", ".bcsar", ".pack", ".paca", ".arc", ".sarc", ".nut", ".nutbin",
    ".bclim", ".bflim", ".bcfnt", ".bflyt", ".bclyt", ".ctpk", ".exe", ".dll", ".pdb",
    ".zip", ".7z", ".rar", ".gz", ".xz", ".iso", ".sav", ".wav", ".ogg", ".dds", ".ktx",
}
FORBIDDEN_PREFIX = (
    "asm/", "original/", "build/", "out/", "mod/", "audit/", "game_",
    "decomp/readable/", "decomp/functions/", "decomp/by_subsystem/",
    "decomp/ghidra/functions/", "decomp/ghidra/recovered/", "decomp/ghidra/by_subsystem/",
    "decomp/ghidra_project/", "third_party/emutest/", "orchestration/logs/",
)
ROM_MAGIC = (b"NCSD", b"NCCH", b"SARC", b"BCH\x00", b"CGFX", b"CSTM", b"CWAV", b"RIFF")

REPO_ONLY = {"backup", "RESTORE.md", ".gitignore", ".gitattributes", "LICENSE", ".git"}


def rel(p: Path, base: Path) -> str:
    return p.relative_to(base).as_posix()


def excluded(r: str) -> bool:
    # match against "/<path>" so "*/bin/*" also hits a top-level bin/ and plain
    # globs ("progress/map.html") are anchored at the workspace root
    return any(fnmatch.fnmatch("/" + r, g if g.startswith("*") else "/" + g) for g in EXCLUDE_GLOBS)


def collect() -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path, kind in INCLUDE:
        src = WORKSPACE / path
        if not src.exists():
            print(f"  [skip] not in workspace: {path}")
            continue
        if kind == "file":
            files[path] = src
            continue
        for dirpath, dirnames, filenames in os.walk(src):
            d = Path(dirpath)
            dirnames[:] = [n for n in dirnames if n not in ("__pycache__", "target", ".git")]
            for name in filenames:
                p = d / name
                r = rel(p, WORKSPACE)
                if not excluded(r):
                    files[r] = p
    return files


def guard(r: str, p: Path) -> str | None:
    low = r.lower()
    if Path(low).suffix in FORBIDDEN_EXT:
        return f"forbidden extension: {r}"
    if low.startswith(FORBIDDEN_PREFIX):
        return f"forbidden path: {r}"
    size = p.stat().st_size
    if size > MAX_FILE_BYTES:
        return f"too large ({size / 2**20:.1f} MB > {MAX_FILE_BYTES / 2**20:.0f} MB): {r}"
    with open(p, "rb") as f:
        head = f.read(0x110)
    if head[:4] in ROM_MAGIC or head[0x100:0x104] in (b"NCSD", b"NCCH"):
        return f"looks like a game container (magic bytes): {r}"
    return None


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def json_ok(p: Path) -> bool:
    try:
        text = p.read_text(encoding="utf-8")
        if p.suffix == ".jsonl":
            for line in text.splitlines():
                if line.strip():
                    json.loads(line)
        else:
            json.loads(text)
        return True
    except Exception:
        return False


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], check=check, text=True, capture_output=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("-m", "--message", default=None)
    args = ap.parse_args()

    # identity check: never commit as anyone but radiant-rodent
    name = git("config", "user.name").stdout.strip()
    email = git("config", "user.email").stdout.strip()
    if name != "radiant-rodent" or email != "radiant-rodent@users.noreply.github.com":
        print(f"ABORT: repo identity is {name} <{email}>, expected radiant-rodent noreply")
        return 2

    print(f"workspace: {WORKSPACE}\nrepo:      {REPO}")
    files = collect()

    problems = [msg for r, p in files.items() if (msg := guard(r, p))]
    if problems:
        print("ABORT: guard failures (nothing was copied):")
        for m in problems:
            print("  ", m)
        return 3
    total = sum(p.stat().st_size for p in files.values())
    if total > MAX_SNAPSHOT_BYTES:
        print(f"ABORT: snapshot is {total / 2**20:.0f} MB > {MAX_SNAPSHOT_BYTES / 2**20:.0f} MB cap")
        return 3

    now = time.time()
    added = changed = held = deleted = 0
    held_list = []
    for r, src in sorted(files.items()):
        dst = REPO / r
        if dst.exists() and dst.stat().st_size == src.stat().st_size and sha(dst) == sha(src):
            continue
        if now - src.stat().st_mtime < HOLD_SECONDS or (src.suffix in (".json", ".jsonl") and not json_ok(src)):
            held += 1
            held_list.append(r)
            continue
        if dst.exists():
            changed += 1
        else:
            added += 1
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(dst.name + ".synctmp")
            shutil.copy2(src, tmp)
            os.replace(tmp, dst)

    # mirror deletions inside the managed paths only
    managed_roots = [p for p, _ in INCLUDE]
    tracked = git("ls-files", "-z").stdout.split("\0")
    for r in tracked:
        if not r or r.split("/")[0] in REPO_ONLY:
            continue
        in_scope = any(r == m or r.startswith(m.rstrip("/") + "/") for m in managed_roots)
        if not in_scope or excluded(r):
            continue
        if r not in files and not (WORKSPACE / r).exists():
            deleted += 1
            if not args.dry_run:
                (REPO / r).unlink(missing_ok=True)

    print(f"files in snapshot {len(files):,} ({total / 2**20:.1f} MB)")
    print(f"added {added}, changed {changed}, deleted {deleted}, held {held}")
    for r in held_list[:20]:
        print(f"  [held: being written or invalid JSON] {r}")
    if args.dry_run:
        return 0

    git("add", "-A")
    if not git("status", "--porcelain").stdout.strip():
        print("nothing to commit")
        return 0
    msg = args.message or f"Backup snapshot {datetime.now():%Y-%m-%d %H:%M}: +{added} ~{changed} -{deleted}"
    git("commit", "-q", "-m", msg)
    print(git("log", "-1", "--format=%h %an <%ae> %s").stdout.strip())
    if not args.no_push:
        r = git("push", "-q", "origin", "HEAD", check=False)
        print("pushed" if r.returncode == 0 else f"PUSH FAILED:\n{r.stderr}")
        return r.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
