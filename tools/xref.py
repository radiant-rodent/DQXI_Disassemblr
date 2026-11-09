#!/usr/bin/env python3
"""Build decomp/xref.json: who calls whom, from the ARM assembly (static, rebuilt in seconds).

    python tools/xref.py            # writes decomp/xref.json

Workers used to rediscover callers by walking asm/ or decomp/ with os.walk / grep -r (425 such
searches in 88 Gemini runs = 55 minutes of tool time, plus the model turns around each one).
`tools/fn.py` reads this file instead.  Only direct branches are covered (``bl #0x...`` calls,
and plain ``b #0x...`` tail jumps to another function's first instruction); calls through
registers (vtable slots) are not visible here.
"""
import bisect
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRANCH = re.compile(r"/\* 0x([0-9A-Fa-f]{8}): [0-9a-fA-F]+ \*/\s+(bl[a-z]{0,2}|b(?:eq|ne|cs|cc|mi|pl|vs|vc|hi|ls|ge|lt|gt|le)?)\s+#0x([0-9a-fA-F]+)")


def main() -> int:
    t0 = time.time()
    funcs = []
    for line in (ROOT / "decomp" / "ghidra" / "functions.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            funcs.append((int(r["address"], 16), int(r.get("size") or 0)))
    funcs.sort()
    starts = [a for a, _ in funcs]
    start_set = set(starts)

    def owner(addr: int):
        i = bisect.bisect_right(starts, addr) - 1
        if i < 0:
            return None
        a, size = funcs[i]
        return a if addr < a + max(size, 4) else None

    callees: dict[int, set] = {}
    callers: dict[int, set] = {}
    files = sorted((ROOT / "asm").glob("text/*.s")) + [p for p in (ROOT / "asm" / "init.s", ROOT / "asm" / "start.s") if p.exists()]
    n_edges = 0
    for path in files:
        for m in BRANCH.finditer(path.read_text(encoding="utf-8", errors="replace")):
            pc, mnem, target = int(m.group(1), 16), m.group(2), int(m.group(3), 16)
            src = owner(pc)
            if src is None:
                continue
            if mnem.startswith("bl"):
                tgt = owner(target)
                if tgt is None:
                    continue
            else:  # plain branch: only a jump to the first instruction of another function
                if target not in start_set or target == src:
                    continue
                tgt = target
            if tgt == src:
                continue
            if tgt not in callees.setdefault(src, set()):
                callees[src].add(tgt)
                callers.setdefault(tgt, set()).add(src)
                n_edges += 1
    out = {f"{a:08X}": {"callers": sorted(f"{c:08X}" for c in callers.get(a, ())),
                         "callees": sorted(f"{c:08X}" for c in callees.get(a, ()))}
           for a, _ in funcs if a in callers or a in callees}
    (ROOT / "decomp" / "xref.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"xref: {len(funcs)} functions, {n_edges} call edges, {len(out)} functions with edges, "
          f"{len(files)} asm files, {time.time() - t0:.1f}s -> decomp/xref.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
