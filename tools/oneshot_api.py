#!/usr/bin/env python3
"""One-shot naming through the Mistral API (no agent loop, no tools): the R4 round.

Each call = FACTS + the pre-baked dossiers of 8 functions -> one JSON array. Model: DeepSeek V4.1 Flash as hosted
by Mistral (`deepseek-v4-1-flash-1017`, the model behind Vibe's `ds-flash` alias), billed to the API credit.
The API key is read from the environment variable MISTRAL_API_KEY (or the Windows user variable of the same name);
it is never printed, logged or written anywhere.

    python tools/oneshot_api.py --ping                      one tiny call: checks key, model id and prices
    python tools/oneshot_api.py R4_001 R4_002               run these batches (skips batches that already pass)
    python tools/oneshot_api.py --all --max-usd 8 --jobs 4  every R4 batch, stop when the estimate passes $8

Output goes to orchestration/naming/refine/out/<batch>.json in the refine format, is normalised and checked with
tools/check_refine.py (the same gate as the agent rounds); flagged entries get one retry with the checker's complaint,
then are downgraded to an honest `maybe_` (confidence 0.4). Merge afterwards with tools/merge_names.py.
"""
import concurrent.futures as cf
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import check_refine  # noqa: E402
import make_dossiers  # noqa: E402
import oneshot_names as base  # noqa: E402  (SYSTEM, TASK, split_dossier, parse_json_array)

ORC = ROOT / "orchestration"
REFINE = ORC / "naming" / "refine"
LOG = REFINE / "oneshot_log.jsonl"
URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "deepseek-v4-1-flash-1017"
PRICE_IN, PRICE_CACHED, PRICE_OUT = 0.30, 0.007, 1.20   # USD per million tokens (docs.mistral.ai/inference/pricing)
PER_CALL = 8
_lock = threading.Lock()
_spent = 0.0


def api_key():
    k = os.environ.get("MISTRAL_API_KEY", "")
    if not k and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
                k = winreg.QueryValueEx(h, "MISTRAL_API_KEY")[0]
        except OSError:
            k = ""
    if not k:
        sys.exit("MISTRAL_API_KEY is not set (user environment variable). Set it once, e.g.  setx MISTRAL_API_KEY <your key>"
                 "  and start a new terminal.")
    return k


def chat(messages, key, max_tokens=9000):
    global _spent
    body = json.dumps({"model": MODEL, "messages": messages, "temperature": 0.2, "max_tokens": max_tokens}).encode()
    for attempt in range(6):
        req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                                              "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read().decode("utf-8"))
            u = d.get("usage", {})
            cached = (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0
            pin, pout = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
            cost = ((pin - cached) * PRICE_IN + cached * PRICE_CACHED + pout * PRICE_OUT) / 1e6
            with _lock:
                _spent += cost
            return d["choices"][0]["message"].get("content") or "", {"in": pin, "cached": cached, "out": pout, "usd": cost}
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(min(60, 5 * 2 ** attempt))
                continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(min(60, 5 * 2 ** attempt))
    raise RuntimeError("API unreachable after retries")


def rows_of(batch):
    rows = {}
    order = []
    for line in (REFINE / "batches" / f"{batch}.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("0x"):
            a, name, conf, path = line.split("\t")[:4]
            a = check_refine.norm(a)
            rows[a] = (name, float(conf) if conf.replace(".", "", 1).isdigit() else 0.4, path)
            order.append(a)
    return rows, order


def normalise(e, rows):
    a = check_refine.norm(e.get("address", ""))
    if a not in rows:
        return None
    prev, pconf, _ = rows[a]
    out = dict(e)
    out["address"] = a
    name = re.sub(r"\s+", "", str(e.get("name") or prev))
    try:
        conf = max(0.0, min(1.0, float(e.get("confidence"))))
    except (TypeError, ValueError):
        conf = 0.4
    change = e.get("change")
    if change == "kept_maybe":
        conf = min(conf, 0.45)
    if conf < 0.5 and not name.startswith("maybe_"):
        name = "maybe_" + name
    if conf >= 0.5 and name.startswith("maybe_"):
        name = name[len("maybe_"):]
    if change == "confirmed" and (conf < 0.5 or name != prev.removeprefix("maybe_")):
        change = "kept_maybe" if conf < 0.5 else "corrected"
    if change not in ("confirmed", "corrected", "kept_maybe"):
        change = "kept_maybe" if conf < 0.5 else "corrected"
    out.update({"name": name, "confidence": round(conf, 2), "change": change, "previous_name": prev,
                "previous_confidence": pconf, "summary": str(e.get("summary") or ""), "evidence": str(e.get("evidence") or ""),
                "params": e.get("params") if isinstance(e.get("params"), dict) else {}})
    return out


def ask(chunk_blocks, key, extra=""):
    facts = (ORC / "naming" / "FACTS.md").read_text(encoding="utf-8")
    user = f"# Established facts\n{facts}\n\n{base.TASK}" + "\n\n".join(chunk_blocks) + extra
    text, use = chat([{"role": "system", "content": base.SYSTEM}, {"role": "user", "content": user}], key)
    return base.parse_json_array(text), use


def run_batch(batch, key, max_usd):
    out = REFINE / "out" / f"{batch}.json"
    if out.exists() and not check_refine.check(batch):
        return {"batch": batch, "skipped": "already passes"}
    rows, order = rows_of(batch)
    make_dossiers.make(batch)
    dossier = base.split_dossier(REFINE / "dossiers" / f"{batch}.md")
    got, tokens = {}, {"in": 0, "cached": 0, "out": 0, "usd": 0.0}

    def do(addrs, extra=""):
        blocks = [dossier.get(a) or f"{a}: no dossier (no readable file); keep the current name {rows[a][0]}" for a in addrs]
        arr, use = ask(blocks, key, extra)
        for k in tokens:
            tokens[k] += use[k]
        for x in arr or []:
            n = normalise(x, rows) if isinstance(x, dict) else None
            if n:
                got[n["address"]] = n

    chunks = [order[i:i + PER_CALL] for i in range(0, len(order), PER_CALL)]
    for c in chunks:
        if _spent > max_usd:
            return {"batch": batch, "stopped": "budget"}
        do(c)
    for _ in range(2):                         # functions the model skipped: ask again, in small groups
        todo = [a for a in order if a not in got]
        for i in range(0, len(todo), 4):
            do(todo[i:i + 4])
    for a in order:                            # still nothing: keep the current name honestly
        if a not in got:
            prev, pconf, _ = rows[a]
            got[a] = {"address": a, "name": prev if prev.startswith("maybe_") else "maybe_" + prev, "confidence": 0.4, "change": "kept_maybe",
                      "previous_name": prev, "previous_confidence": pconf, "params": {}, "summary": "",
                      "evidence": "no answer from the one-shot call"}
    out.write_text(json.dumps([got[a] for a in order], indent=1, ensure_ascii=False), encoding="utf-8")
    errs = check_refine.check(batch)
    retried = 0
    if errs:                                    # one retry for the flagged entries, with the checker's complaint
        bad = sorted({a for e in errs for a in re.findall(r"0x[0-9A-F]{8}", e) if a in rows})
        for i in range(0, len(bad), 4):
            msg = "\n\nA validator rejected your earlier answer for these functions:\n" + "\n".join(
                e for e in errs if any(a in e for a in bad[i:i + 4]))[:1500] + "\nAnswer again; fix or justify in `evidence`."
            do(bad[i:i + 4], msg)
        retried = len(bad)
        out.write_text(json.dumps([got[a] for a in order], indent=1, ensure_ascii=False), encoding="utf-8")
        errs = check_refine.check(batch)
        if errs:                                # still flagged: downgrade those entries to an honest maybe_
            bad = {a for e in errs for a in re.findall(r"0x[0-9A-F]{8}", e) if a in got}
            for a in bad:
                prev, pconf, _ = rows[a]
                got[a].update({"name": prev if prev.startswith("maybe_") else "maybe_" + prev, "confidence": 0.4, "change": "kept_maybe",
                               "evidence": (got[a].get("evidence", "") + " | downgraded: validator flag not resolved")[:400]})
            out.write_text(json.dumps([got[a] for a in order], indent=1, ensure_ascii=False), encoding="utf-8")
            errs = check_refine.check(batch)
    counts = {}
    for a in order:
        counts[got[a]["change"]] = counts.get(got[a]["change"], 0) + 1
    rec = {"batch": batch, "functions": len(order), "changes": counts, "retried": retried, "check": "OK" if not errs else errs[:3],
           "tokens": tokens, "usd": round(tokens["usd"], 4), "model": MODEL, "time": time.strftime("%F %T")}
    with _lock, open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    max_usd = float(a[a.index("--max-usd") + 1]) if "--max-usd" in a else 8.0
    jobs = int(a[a.index("--jobs") + 1]) if "--jobs" in a else 4
    key = api_key()
    if "--ping" in a:
        text, use = chat([{"role": "user", "content": "Reply with the single word OK."}], key, max_tokens=200)
        print("reply:", text.strip()[:40], "| usage:", use)
        return
    if "--all" in a:
        batches = sorted(p.stem for p in (REFINE / "batches").glob("R4_*.txt"))
    else:
        batches = [x for x in a if re.match(r"R\d+_\d+$", x)]
    print(f"{len(batches)} batches, budget ${max_usd}, {jobs} parallel")
    with cf.ThreadPoolExecutor(max_workers=jobs) as ex:
        futs = {ex.submit(run_batch, b, key, max_usd): b for b in batches}
        for f in cf.as_completed(futs):
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                r = {"batch": futs[f], "error": str(e)[:200]}
            print(json.dumps(r, ensure_ascii=False)[:400], f"| spent ${_spent:.2f}", flush=True)
    print(f"done, estimated spend ${_spent:.2f}")


if __name__ == "__main__":
    main()
