#!/usr/bin/env python3
"""One-shot naming: several functions per model call, no tools, no agent loop (pilot).

A refine batch worker needs ~80-120 model turns, every one re-reading the whole growing context. Here each call
carries FACTS + the pre-baked dossiers of N functions and answers with ONE JSON array. The call goes through the
Vibe CLI in WSL (its own key, never read here) with Vibe's system prompt replaced by a 1 KB one, one turn, and a
token/cost export so the real usage is measured.

    python tools/oneshot_names.py --pilot R3_050 --n 16      first N functions of that dossier that agents left as
                                                             maybe_ (kept_maybe), 8 per call, result next to scratch
    python tools/oneshot_names.py --show out/scratch/oneshot/pilot_R3_050.json     print previous vs new names
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORC = ROOT / "orchestration"
SCR = ROOT / "out" / "scratch" / "oneshot"
WSL_ROOT = "/mnt/<drive>/path/to/DQXI_Disassemblr"
VIBE = "~/.local/bin/vibe"
PER_CALL = 8

SYSTEM = """You are a reverse engineer naming functions of Dragon Quest XI (Nintendo 3DS, ARM, C++).
You are given hand-verified facts and, per function: its current (uncertain) name, earlier notes, callers, callees,
and its decompiled body. Decide each function from that material only. You have no tools and cannot look anything
up: answer with the JSON array and nothing else (no prose, no code fence). Never invent: when the evidence does not
support a confident name keep the maybe_ name and confidence below 0.5."""

TASK = """For EACH function below return one object, in the same order, exactly this shape:
{"address":"0x...","name":"Class_Verb","signature":"ret Name(type param,...)","params":{"param_1":"betterName"},
 "summary":"one or two sentences: what and why","confidence":0.0-1.0,"evidence":"what in the dossier supports it",
 "previous_name":"<current name>","previous_confidence":<number from SCORE/DOC or 0.4>,
 "change":"confirmed"|"corrected"|"kept_maybe"}
Rules: names are Class_Verb style identifiers; `confirmed` = the context supports the existing guess (drop maybe_,
confidence 0.5-0.7); `corrected` = better honest name; `kept_maybe` = still ambiguous (keep the maybe_ name,
confidence < 0.5). 0.7+ needs strong evidence (a named caller using it a specific way, a string, a constant).
Output ONLY the JSON array.

FUNCTIONS:
"""


def split_dossier(path):
    txt = path.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"\n={100}\n", txt)
    blocks = {}
    for p in parts:
        m = re.match(r"(0x[0-9A-Fa-f]{8})\s", p.strip())
        if m:
            blocks[m.group(1).upper().replace("0X", "0x")] = p.strip()
    return blocks


def one_call(tag, blocks):
    SCR.mkdir(parents=True, exist_ok=True)
    facts = (ORC / "naming" / "FACTS.md").read_text(encoding="utf-8")
    prompt = f"# Established facts\n{facts}\n\n{TASK}" + "\n\n".join(blocks)
    pf, sf, od = SCR / f"{tag}.prompt.txt", SCR / "system.txt", SCR / f"{tag}.export"
    pf.write_text(prompt, encoding="utf-8")
    sf.write_text(SYSTEM, encoding="utf-8")
    inner = (f"cd {WSL_ROOT} && exec bash {WSL_ROOT}/orchestration/sandbox_wsl.sh {WSL_ROOT} {VIBE} --workdir {WSL_ROOT} "
             f"-p --prompt-file {WSL_ROOT}/out/scratch/oneshot/{tag}.prompt.txt "
             f"--system-prompt-file {WSL_ROOT}/out/scratch/oneshot/system.txt "
             f"--output-dir {WSL_ROOT}/out/scratch/oneshot/{tag}.export "
             f"--enabled-tools zz_none --model ds-flash --max-turns 3 --time-limit 300 --output text")
    t0 = time.time()
    r = subprocess.run(["wsl.exe", "-d", "Ubuntu-22.04", "--", "bash", "-lc", inner], capture_output=True, timeout=420)
    out = r.stdout.replace(b"\x00", b"").decode("utf-8", "replace")
    return out, time.time() - t0, len(prompt)


def parse_json_array(text):
    a, b = text.find("["), text.rfind("]")
    if a < 0 or b < a:
        return None
    try:
        return json.loads(text[a:b + 1])
    except ValueError:
        return None


def export_usage(tag):
    for p in (SCR / f"{tag}.export").glob("export.json"):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return None
    return None


def pilot(batch, n):
    dossier = split_dossier(ORC / "naming" / "refine" / "dossiers" / f"{batch}.md")
    prev = json.loads((ORC / "naming" / "refine" / "out" / f"{batch}.json").read_text(encoding="utf-8"))
    hard = [e for e in prev if e.get("change") == "kept_maybe" and e["address"].upper().replace("0X", "0x") in dossier][:n]
    results, stats = [], []
    for i in range(0, len(hard), PER_CALL):
        chunk = hard[i:i + PER_CALL]
        tag = f"pilot_{batch}_{i // PER_CALL}"
        out, secs, plen = one_call(tag, [dossier[e["address"].upper().replace("0X", "0x")] for e in chunk])
        arr = parse_json_array(out)
        us = export_usage(tag) or {}
        stats.append({"tag": tag, "secs": round(secs), "prompt_chars": plen, "parsed": None if arr is None else len(arr),
                      "asked": len(chunk), "usage": {k: us.get(k) for k in ("token_usage", "cost", "stop_reason", "outcome") if k in us}})
        print(json.dumps(stats[-1]), flush=True)
        if arr is None:
            (SCR / f"{tag}.raw.txt").write_text(out, encoding="utf-8")
            continue
        by = {str(x.get("address", "")).upper().replace("0X", "0x"): x for x in arr if isinstance(x, dict)}
        for e in chunk:
            x = by.get(e["address"].upper().replace("0X", "0x"))
            if x:
                results.append({"address": e["address"], "agents_name": e["name"], "agents_conf": e.get("confidence"), "oneshot": x})
    (SCR / f"pilot_{batch}.json").write_text(json.dumps({"stats": stats, "results": results}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(results)} of {len(hard)} answered; written to out/scratch/oneshot/pilot_{batch}.json")


def show(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    ch = {}
    for r in d["results"]:
        o = r["oneshot"]
        ch[o.get("change")] = ch.get(o.get("change"), 0) + 1
        print(f"{r['address']}  agents: {r['agents_name']} ({r['agents_conf']})\n            one-shot: {o.get('name')} "
              f"({o.get('confidence')}, {o.get('change')})  {str(o.get('summary', ''))[:150]}")
    print(ch)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--pilot"]:
        pilot(a[1], int(a[a.index("--n") + 1]) if "--n" in a else 16)
    elif a[:1] == ["--show"]:
        show(a[1])
    else:
        sys.exit(__doc__)
