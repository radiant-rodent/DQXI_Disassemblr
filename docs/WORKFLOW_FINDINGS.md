# Why the worker pipeline was slow, and what was changed (2026-11-05)

Measured from `orchestration/logs/` (342 tasks, 1,547 attempts) by `out/scratch/analyze_runs.py` and
`analyze_steps.py`. Numbers are from that day; re-run the scripts to refresh them.

## 1. Models: most attempts were wasted on models with no quota

| model | attempts | finished a batch | notes |
|---|---|---|---|
| OpenCode Go DeepSeek 4.1 Flash (paid) | 379 | 187 (49 %) | carried about two thirds of all finished batches |
| Gemini 3.8 Flash (agy) | 269 | 78 (29 %) | 5-hour quota windows; "Resets in 4h" |
| OpenCode free DeepSeek / MiMo / GLM | 786 | 14 (2 %) | 570 attempts failed in under a minute: "Free usage limit reached" |
| Mistral Vibe DeepSeek (WSL) | 5 | 1 | see 4 |
| OpenRouter free models | ~80 | 10 | removed on request |

* The free OpenCode models are effectively out of quota. The dispatcher kept launching them
  (every 10 minutes, from eight threads at once), and each failed attempt used up part of a task's
  four-attempt budget.
* A task that fails mid-batch resumes from the partial JSON, so little work is lost, but every resume
  re-reads the whole context.

## 2. Inside a run, the time goes to model turns and to searching

From 88 completed Gemini runs: **86 % of the time is model turns** (about 125 turns per run, 6.7 s each),
13 % is tools. Of the tool time, **425 whole-tree searches** (`os.walk` / `grep -r` over `asm/` and
`decomp/`, mostly to find callers) took **55 minutes**, up to 340 s each, and each one cost extra turns
around it. Workers also wrote their own caller-search scripts again and again
(`out/scratch/*/callers.py`, `ctx.py`). Full `tests/run_all.py` runs by naming workers: 6 calls, 10 minutes.

## 3. Progress that was invisible

* `R2_*` batches finished but `tools/merge_names.py` only read `R_*.json`: coverage did not move
  (52 % -> 69 % once merged).
* `G_036`, `G_041` had complete output but no done report (quota ran out first).
* The board showed Vibe workers as "not started": the WSL child overwrote the log header from byte 0.
* Duplicate global name between two workers broke type validation.

## 4. Vibe (Mistral)

Works, but Mistral answers `429 Not enough capacity` when many run at once (7 did), and the Vibe SDK
retries forever. Output is buffered, so a healthy run looks silent until it ends.

## What changed

| problem | fix |
|---|---|
| searching the trees | `tools/xref.py` builds `decomp/xref.json` (60,057 call edges, 1.2 s); `tools/fn.py ADDR` prints a dossier in 0.5 s; rule 14 in `WORKER_RULES.md` and the Tools section of `naming/FACTS.md` (pasted into every bulk prompt) tell workers to use it |
| full test runs | rule 5: naming/typing/refine batches skip `tests/run_all.py` |
| dead models probed forever | `orchestration/quota.json` keeps pauses across restarts; the provider's "Resets in XhYm" is parsed; otherwise 10 min doubling to 3 h; concurrent failures count once; success resets |
| paid Go used by accident | Go only when no other model is available; busy Vibe slots wait instead |
| Mistral overload | `VIBE_MAX = 3`, slot reserved atomically, counted from `ps` in WSL so a dispatcher restart cannot double them, 40-minute `--time-limit` |
| invisible finished work | `merge_names.py` reads `R*_*.json` (R2 after R); dispatcher merges and `check_refine`-checks `R2_` too; `tools/pipeline_check.py` lists orphan outputs, stale locks, unread output kinds, done-but-failing batches |
| silent Vibe logs / board | Vibe output goes through a pump thread into the log; `live.py` recognises old logs; `STATUS` line every 5 minutes in the dispatcher output |

## Not done yet (ideas, in order of expected gain)

1. **Pre-baked dossiers.** Generate each batch's `fn.py` output into a file next to the batch, so a worker
   starts with zero tool calls for context (turns are 86 % of the time).
2. **Script the trivial cases.** Many unnamed functions are 5-30 instruction wrappers and getters;
   a rule-based pass (return of a field, call-through, constant return) could name them without a model.
3. **Smaller refine batches** (about 50 instead of 150) so a quota cut or the 40-minute Vibe limit
   loses less and failures are cheaper.
4. **One owner for merges.** Today the dispatcher, K1/K2 and M1b can all run `merge_names.py`; a lock
   file around it would remove the possibility of two merges at once.

## Result: idea 2 (script the trivial cases) — tried, and the premise was wrong

`tools/trivial_names.py` (T1_trivial_wrappers) decodes every unnamed function from the bytes, requires
`asm/text` to agree instruction by instruction, and applies six rules (field getter, field setter,
constant return, pure forwarder, empty stub, accessor + field). It runs in 30 s and produced **18 names,
all pure forwarders**; rules 1, 2, 3, 5 and 6 matched nothing.

The reason is measurable: the shapes are in the binary in the thousands (496 `ldr r0,[r0,#N]; bx lr`,
489 `str r1,[r0,#N]; bx lr`, 2,321 `mov r0,#imm; bx lr`) but **not one of them starts a function** — the
compiler inlined all of them. At function granularity the remaining trivial work is a different class:
**247 × `push {r4,lr}; bl <dtor>; pop {r4,lr}; b 0x0010F6CC`** (deleting-destructor thunks), which the
brief's one-callee rule deliberately excludes. That is the next rule to write, and it needs `0x0010F6CC`
named first.

Two side findings worth keeping:

* **Mode traps.** `0x00102B90` is printed as Thumb `ands r0,r2` by the sweep but is ARM `push {r4,lr}`;
  `0x00115410` is Thumb per Ghidra but ARM `ldr fp,[pc,#0x514]`. 487 unnamed functions hit such a
  disagreement. Decoding the bytes and cross-checking against `asm/text` catches them; trusting either
  disassembler alone does not.
* **A report mode must not write.** `--report` originally rewrote the batch file, which after a merge
  silently replaces the merged record with a post-merge regeneration. It now writes nothing.

Cost: one worker run, about 30 s per full-binary pass, 39 unit tests. Gain: 18 names and a census that
says where the remaining trivial work is. The general lesson for the dispatcher: before spending a
worker on "the many tiny functions", measure how many of them are functions at all.

## Vibe hangs without an error (2026-11-05, R3_080)
A Vibe session can stop on an unanswered model `completion` request: the session journal (~/.vibe/logs/session/unified/<id>/journal/*.jsonl, task named in its first line) stays silent and ends on a request record while the process sleeps with an open connection. No 429 is logged. Healthy sessions write every second. Mitigation: VIBE_TIME_LIMIT is now 25 minutes (takes effect at the next dispatcher restart); to rescue one earlier, kill its vibe-rs process in WSL and the dispatcher retries the task on the next model.
