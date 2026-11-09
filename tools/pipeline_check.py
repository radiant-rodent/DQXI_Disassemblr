#!/usr/bin/env python3
"""Find work that is finished but invisible, before it costs another debugging session.

    python tools/pipeline_check.py          # prints WARN lines; exit 1 if there are any

Checks (each one was a real problem on 2026-11-05):
  * a worker output file exists but the task has no done report and no live worker
    (quota ran out before the report: G_036/G_041 sat for days)
  * an output file kind that tools/merge_names.py or tools/typedb/apply.py does not read
    (R2_* batches were finished but never merged, so the coverage did not move)
  * stale lock files (dead pid)
  * a refine output that fails tools/check_refine.py although its task is marked done
"""
import ctypes
import glob
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORC = ROOT / "orchestration"


def alive(pid: int) -> bool:
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(h)
    return code.value == 259


def main() -> int:
    warn = []
    done = {p.stem for p in (ORC / "done").glob("*.md")}
    live = set()
    for lock in (ORC / "locks").glob("*.pid"):
        try:
            ok = alive(int(lock.read_text().strip()))
        except (OSError, ValueError):
            ok = False
        if ok:
            live.add(lock.stem)
        elif lock.stem != "dispatcher":
            warn.append(f"stale lock {lock.name} (pid not running)")
    outputs = [(p, p.stem) for pat in ("naming/out/*.json", "naming/refine/out/*.json", "types/out/*.json")
               for p in sorted(ORC.glob(pat))]
    for p, tid in outputs:
        if re.match(r"R_[A-Z]\d+$", tid):  # sweep overlays (R_K01, R_S01) have no task
            continue
        if tid not in done and tid not in live:
            warn.append(f"output without report and no live worker: {p.relative_to(ROOT).as_posix()} "
                        f"(mark the task done after validating, or let the dispatcher re-run it)")
    merge_src = (ROOT / "tools" / "merge_names.py").read_text(encoding="utf-8")
    for p, tid in outputs:
        if p.parent.name == "out" and "refine" in p.as_posix():
            if not re.match(r"R\d*_", tid):
                warn.append(f"{tid}: refine output name not matched by merge_names (glob R*_*.json)")
            elif tid.startswith("R2_") and 'R*_*.json' not in merge_src:
                warn.append("merge_names.py does not read R2_* outputs")
    for p, tid in outputs:
        if "refine" in p.as_posix() and tid in done and re.match(r"R\d*_\d+$", tid):
            r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_refine.py"), tid],
                               capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode:
                warn.append(f"{tid} is marked done but fails check_refine: {r.stdout.strip().splitlines()[0][:120]}")
    for w in warn:
        print("WARN", w)
    print(f"pipeline_check: {len(warn)} warning(s); {len(done)} done reports, {len(outputs)} output files, {len(live)} live workers")
    return 1 if warn else 0


if __name__ == "__main__":
    sys.exit(main())
