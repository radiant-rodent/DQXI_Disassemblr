"""Run task files through cheap OpenCode workers.

Usage:
    python orchestration/dispatch.py [--jobs N] [--only GLOB] [--dry]

Each task is orchestration/tasks/<id>.md with a front-matter block:
    ---
    lane: editor          # tasks in the same lane run one at a time (shared files)
    after: P0_regen       # comma list of task ids that must be DONE first
    ---
State lives in orchestration/state.json; logs in orchestration/logs/<id>.log.
A worker marks success by writing orchestration/done/<id>.md (its report).
Free model first, paid Go model as fallback.
"""
import argparse, fnmatch, json, os, re, shutil, subprocess, sys, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORC = ROOT / "orchestration"
OC = Path(os.environ["APPDATA"]) / "ai.opencode.desktop/cli/2.1.3-x64/opencode-cli.exe"
# Free OpenCode models do the work; tasks are spread across them so no single free quota runs dry.
FREE = ["opencode/deepseek-v4.1-flash-free", "opencode/glm-5.3-flash-free", "opencode/mimo-v2.6-flash-free"]
# Fallback when the free ones are rate-limited or fail: Gemini 3.8 Flash on the user's Vertex AI
# project (billed to their Google Cloud credit), driven by orchestration/vertex_agent.py through the
# google-genai SDK — Vertex is not an OpenCode provider here.
VERTEX = "vertex:gemini-3.8-flash"
# Vertex is out of the pool: its runner escaped the project (2026-10-26), see vertex_agent.py.
MODELS = FREE + ["opencode-go/deepseek-v4.1-flash"]
# Antigravity CLI `agy` (Google sign-in, Gemini subscription quota, no API key) joins the pool when
# installed. "agy" uses its default model, "agy:<model>" a specific one (list them with `agy models`).
# A task can pick its own order with "models: agy, opencode-go/deepseek-v4.1-flash".
AGY = None if os.environ.get("DQXI_NO_AGY") else shutil.which("agy") or next(  # Gemini subscription
    (str(p) for p in [Path(os.environ.get("LOCALAPPDATA", "")) / "agy/bin/agy.exe"] if p.is_file()), None)
GEMINI = "agy:gemini-3.8-flash-high"
if AGY:  # Gemini works alongside DeepSeek: tasks alternate which one they start on
    MODELS.append(GEMINI)
launches = 0
# Model policy (user, 2026-10-30): Gemini through Antigravity first - 3.8 Flash for the bulk
# naming/typing batches, Argon for the difficult tasks (merges, features) - then the free OpenCode
# models once the Gemini quota is used up. The paid OpenCode Go model is NOT used (month's quota
# nearly spent); when everything is over its limit the dispatcher waits instead.
FLASH = "agy:gemini-3.8-flash-high"
ARGON = "agy:gemini-4-argon-high"
PAID_OFF = True  # bulk batches never use the paid model
GO_DEEPSEEK = "opencode-go/deepseek-v4.1-flash"
# user, 11-01: Argon for lead tasks (one at a time), Flash for batches; when that Gemini
# quota is used up the dispatcher stops (no free OpenCode, no paid Go)
GO_WHEN_VIBE_FULL = True  # user 11-05 ("Allow Go now"): Go DeepSeek takes tasks while the Vibe slots are full
GEMINI_ONLY = False  # 11-05: the pool is Vibe + Flash + free OpenCode again (see policy_models)
# user, 11-05: Mistral Vibe CLI (installed in WSL Ubuntu-22.04) driving DeepSeek v4.1 Flash
# (model alias "ds-flash" in ~/.vibe/config.toml); the key lives in ~/.vibe/.env, never read here.
VIBE = "vibe:ds-flash"
VIBE_DISTRO = "Ubuntu-22.04"
VIBE_MAX = 3          # concurrent Vibe workers (11-05: 7 at once -> Mistral 429 "not enough capacity")
VIBE_TIME_LIMIT = 25 * 60  # seconds; a Vibe request can hang without an error (R3_080: 18 min silent); the run is interrupted and retried elsewhere
active_vibe = 0
ARGON_MAX = 1         # user: only one Argon worker at a time
active_argon = 0
VIBE_BIN = "~/.local/bin/vibe"
WSL_ROOT = "/mnt/<drive>/path/to/DQXI_Disassemblr"
quota_out = set()  # models whose quota ran out during this run


def policy_models(tid, lane=""):
    """Model pool (user, 2026-11-05): Mistral Vibe (DeepSeek v4.1 Flash) and Gemini 3.8 Flash share
    the work, then the free OpenCode models, with OpenCode Go DeepSeek v4.1 Flash as the last
    fallback. Argon is not in the pool (not named in the 11-05 instruction)."""
    if GEMINI_ONLY:  # kept for the 11-01 behaviour: lead tasks on Argon, batches on Flash, then stop
        return [FLASH] if tid.startswith(("N_", "R_", "G_", "S_", "V_")) else [ARGON]
    base = [VIBE] + ([FLASH] if AGY else []) + list(FREE) + [GO_DEEPSEEK]
    # 11-09: the harder work (lead tasks, merges, S_ class/field typing) tries Argon first
    hard = tid.startswith("S_") or not re.match(r"(N|R\d*|G|S|V)_", tid)
    return ([ARGON] + base) if (hard and AGY) else base

# OpenRouter: FREE models only (user's rule). Active once the key is stored with `opencode auth login`.
OPENROUTER_FREE = [
    "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "openrouter/thinkingmachines/inkling:free",
    "openrouter/google/gemma-4-31b-it:free",
    "openrouter/cohere/north-mini-code:free",
    "openrouter/xingchen-agi/xing4.0-29b-a4b:free",
    "openrouter/recursive/flint-v1.0:free",
]
assert all(m.endswith(":free") for m in OPENROUTER_FREE), "only free OpenRouter models allowed"
try:
    _auth = json.loads((Path.home() / ".local/share/opencode/auth.json").read_text())
except (OSError, ValueError):
    _auth = {}
# Terminals started before `setx OPENROUTER_API_KEY` don't have it; read the saved user variable
# from the registry so the dispatcher (and the opencode workers it starts) still get the key.
if not os.environ.get("OPENROUTER_API_KEY") and sys.platform == "win32":
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as _k:
            os.environ["OPENROUTER_API_KEY"] = winreg.QueryValueEx(_k, "OPENROUTER_API_KEY")[0]
    except OSError:
        pass
# bulk naming/typing batches: queued after feature tasks and started on free OpenRouter models
BULK = ("N_", "R_", "R2_", "R3_", "G_", "S_", "V_")
# OpenRouter is out of the pool (user, 2026-10-27); flip back to the check below to re-enable.
OR_ON = False  # bool("openrouter" in _auth or os.environ.get("OPENROUTER_API_KEY"))
if OR_ON:  # key via opencode login or env var
    MODELS.extend(OPENROUTER_FREE)
# priority for every task: free OpenCode, free OpenRouter, Gemini subscription, paid Go last
MODELS.sort(key=lambda m: (m.startswith("opencode-go/"), m.startswith("agy"), m.startswith("openrouter/")))
LIMIT_MARKERS = ("usage limit", "quota exceeded", "resource_exhausted", "rate limit", "429",
                 "limit exceeded", "limit reached", "rate_limit_exceeded", "too many requests")


VIBE_NOTE = """

# Environment note (you run inside WSL Ubuntu, the project is at /mnt/<drive>/path/to/DQXI_Disassemblr)
- The commands in this brief are written for Windows PowerShell. Pure-Python tools (typedb/apply.py,
  check_refine.py, merge_names.py, progress.py) also run with `python3` in WSL. Anything that needs the
  Windows toolchain or Windows-only Python packages (tools/build.py, tests/run_all.py, cargo, texture
  tools) must be run as: cmd.exe /c "cd /d . && python tools\\build.py".
- Use forward slashes in file paths. Do not edit files outside the paths the task says it owns.
"""


_vibe_ps = (0.0, 0)


def vibe_load():
    """Vibe workers running now: ours plus any left over from an earlier dispatcher (ps in WSL, cached 15 s)."""
    global _vibe_ps
    now = time.time()
    if now - _vibe_ps[0] > 15:
        try:
            r = subprocess.run(["wsl.exe", "-d", VIBE_DISTRO, "--", "bash", "-c",
                                "ps -eo args | grep -c '[v]ibe-rs --workdir'"], capture_output=True, timeout=30)
            n = int(r.stdout.replace(b"\x00", b"").decode("utf-8", "replace").strip() or 0)
        except (OSError, ValueError, subprocess.SubprocessError):
            n = 0
        _vibe_ps = (now, n)
    return active_vibe + max(0, _vibe_ps[1] - active_vibe)


def worker_cmd(model, tid, prompt):
    if model.startswith("agy"):
        # stream-json: events arrive as they happen (text mode prints only at the very end)
        cmd = [AGY, "-p", prompt, "--dangerously-skip-permissions", "--print-timeout", "240m",
               "--output-format", "stream-json"]
        return cmd + (["--model", model.split(":", 1)[1]] if ":" in model else [])
    if model.startswith("vibe:"):
        # headless Vibe in WSL; the prompt goes through a file (no quoting problems). The WSL note
        # tells the worker how to run the project's Python tools from there.
        pf = ORC / "logs" / f"{tid}.prompt.txt"
        pf.write_text(prompt + VIBE_NOTE, encoding="utf-8")
        inner = (f"cd {WSL_ROOT} && exec {VIBE_BIN} --workdir {WSL_ROOT} -p --prompt-file "
                 f"{WSL_ROOT}/orchestration/logs/{tid}.prompt.txt --auto-approve --trust --output streaming "
                 f"--model {model.split(':', 1)[1]} --max-turns 400 --time-limit {VIBE_TIME_LIMIT}")
        return ["wsl.exe", "-d", VIBE_DISTRO, "--", "bash", "-lc", inner]
    if model.startswith("vertex:"):
        pf = ORC / "logs" / f"{tid}.prompt.txt"
        pf.write_text(prompt, encoding="utf-8")
        return [sys.executable, "-u", str(ORC / "vertex_agent.py"), "--model", model.split(":", 1)[1],
                "--prompt-file", str(pf), "--done", str(ORC / "done" / f"{tid}.md")]
    # --standalone: a private server per run, so stopping the run really stops the session
    # (via the shared background service, sessions kept running after their run was killed)
    return [str(OC), "run", "--standalone", "--auto", "-m", model, "--title", tid, prompt]


PROGRESS = ROOT / "tools" / "progress.py"

lock = threading.Lock()
progress_lock = threading.Lock()
PAGE_REFRESH = 3 * 60  # seconds between progress-page rebuilds while workers run
last_page_refresh = 0.0
last_status = 0.0


def refresh_progress(merge=False):
    """Regenerate progress/ after the task state changes; never fail the dispatcher.

    merge=True first folds the naming outputs into the readable C (tools/merge_names.py), so a
    finished naming batch shows up in the names and the coverage map, not just in the task list.
    """
    if not PROGRESS.is_file():
        return
    try:
        with progress_lock:
            if merge:
                subprocess.run([sys.executable, str(ROOT / "tools" / "merge_names.py")], cwd=ROOT,
                               timeout=1800, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([sys.executable, str(PROGRESS)], cwd=ROOT, timeout=600,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def load_state():
    p = ORC / "state.json"
    return json.loads(p.read_text()) if p.exists() else {}


def save_state(state):
    (ORC / "state.json").write_text(json.dumps(state, indent=2))


def parse(path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        head, text = text[3:].split("---", 1)
        for line in head.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.split("#")[0].strip()
    meta["after"] = [a.strip() for a in meta.get("after", "").split(",") if a.strip()]
    meta["lane"] = meta.get("lane") or path.stem
    return meta, text.strip()


def lock_file(tid):
    (ORC / "locks").mkdir(exist_ok=True)
    return ORC / "locks" / f"{tid}.pid"


def worker_alive(tid):
    # a worker from an earlier dispatcher may still be running this task: never start a second one
    try:
        pid = int(lock_file(tid).read_text())
    except (OSError, ValueError):
        return False
    import ctypes
    handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        lock_file(tid).unlink(missing_ok=True)
        return False
    code = ctypes.c_ulong()
    ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(handle)
    if code.value != 259:  # STILL_ACTIVE
        lock_file(tid).unlink(missing_ok=True)
        return False
    return True


blocked_until = {}  # model -> time it may be used again
LIMIT_BACKOFF = 10 * 60     # first pause; doubles on every further limit hit, up to LIMIT_BACKOFF_MAX
LIMIT_BACKOFF_MAX = 3 * 3600
QUOTA_FILE = ORC / "quota.json"   # survives dispatcher restarts (a fresh process used to re-probe dead models)
fail_streak = {}
RESET_IN = re.compile(r"Resets in (?:(\d+)h)?\s*(?:(\d+)m)?\s*(?:(\d+)s)?", re.I)


def load_quota():
    try:
        data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    now = time.time()
    for m, v in data.items():
        if v.get("until", 0) > now:
            blocked_until[m] = v["until"]
        fail_streak[m] = v.get("streak", 0)


def save_quota():
    QUOTA_FILE.write_text(json.dumps({m: {"until": blocked_until.get(m, 0), "streak": fail_streak.get(m, 0)}
                                      for m in set(blocked_until) | set(fail_streak)}, indent=1), encoding="utf-8")


def pause_seconds(model, output):
    """How long to leave a model alone: the reset time the provider names, else exponential backoff."""
    now = time.time()
    if blocked_until.get(model, 0) > now:  # another thread just hit the same limit: not a new failure
        return int(blocked_until[model] - now)
    streak = fail_streak.get(model, 0) + 1
    fail_streak[model] = streak
    m = RESET_IN.search(output)
    if m and any(m.groups()):
        h, mi, se = (int(g or 0) for g in m.groups())
        return min(h * 3600 + mi * 60 + se + 60, LIMIT_BACKOFF_MAX)
    return min(LIMIT_BACKOFF * 2 ** (streak - 1), LIMIT_BACKOFF_MAX)


def _pump(stream, log):
    """Copy a child's output into the log line by line (keeps the attempt header intact)."""
    try:
        for line in iter(stream.readline, b""):
            log.write(line.decode("utf-8", "replace"))
            log.flush()
    except (OSError, ValueError):
        pass


def check_output(tid):
    """Problems check_refine.py finds in a refine batch's output ("" = accepted or not a refine task)."""
    if not tid.startswith(("R_", "R2_", "R3_")) or not (ORC / "naming" / "refine" / "batches" / f"{tid}.txt").exists():
        return ""
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "check_refine.py"), tid], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return "" if r.returncode == 0 else r.stdout.strip()[-4000:]


def run_task(tid, body, state):
    # re-read rules and brief at launch, so edits made while the dispatcher runs take effect
    PREAMBLE = (ORC / "WORKER_RULES.md").read_text(encoding="utf-8")
    if re.match(r"R\d*_\d+$", tid) and (ORC / "naming" / "refine" / "batches" / f"{tid}.txt").exists():
        # pre-bake the batch's dossiers with the names as of the last merge (about a second)
        subprocess.run([sys.executable, str(ROOT / "tools" / "make_dossiers.py"), tid], cwd=ROOT,
                       capture_output=True, timeout=300)
    if tid.startswith(BULK):  # naming batches get the hand-verified facts (re-read every launch)
        PREAMBLE += "\n\n" + (ORC / "naming" / "FACTS.md").read_text(encoding="utf-8")
    meta, body = parse(ORC / "tasks" / f"{tid}.md")
    (ORC / "logs").mkdir(exist_ok=True)
    done = ORC / "done" / f"{tid}.md"
    prompt = f"{PREAMBLE}\n\n# YOUR TASK ({tid})\n\n{body}\n\nWhen finished, write your report to orchestration/done/{tid}.md."
    resume = (f"{PREAMBLE}\n\n# YOUR TASK ({tid}) — RESUMED\nA previous worker stopped before finishing. "
              f"Check what already exists, then complete:\n\n{body}\n\nWrite your report to orchestration/done/{tid}.md.")
    if (ORC / "logs" / f"{tid}.log").exists():  # interrupted by a dispatcher restart
        prompt = resume
    global launches, active_vibe, active_argon
    with lock:
        launches += 1
        # odd launches start on Gemini, even ones on DeepSeek (unless the task lists its own models)
        # launches rotate DeepSeek -> Gemini -> OpenRouter free (OpenRouter only for naming batches,
        # whose output M1_merge_names validates); a task's own "models:" line overrides this
        starts = list(FREE) + ([GEMINI] if AGY else []) + \
                 ([OPENROUTER_FREE[0]] if OPENROUTER_FREE[0] in MODELS and tid.startswith(BULK) else [])
        pools = [VIBE] + ([FLASH] if AGY else []) + [FREE[0]]
        start_on = pools[launches % len(pools)] if PAID_OFF and not GEMINI_ONLY else (
            None if PAID_OFF or meta.get("models") or (tid.startswith(BULK) and OR_ON)
            else starts[launches % len(starts)])
    attempt = 0
    while attempt < 4:
        default = (OPENROUTER_FREE[launches % len(OPENROUTER_FREE):] + OPENROUTER_FREE[:launches % len(OPENROUTER_FREE)]
                   + MODELS) if tid.startswith(BULK) and OR_ON else MODELS  # bulk batches: free OpenRouter first
        wanted = [m.strip() for m in meta.get("models", "").split(",") if m.strip()] or default
        if PAID_OFF:  # the policy replaces task model lines and keeps the paid Go model out
            wanted = policy_models(tid, meta.get("lane", ""))
        wanted = [m for m in wanted if not m.startswith("agy") or AGY] or MODELS  # agy missing: use the pool
        wanted = [m for m in wanted if not m.startswith("openrouter/") or OR_ON] or MODELS  # OpenRouter off
        free = [m for m in wanted if blocked_until.get(m, 0) < time.time()]
        with lock:  # one Argon worker at a time; extra hard tasks use the rest of the pool
            if active_argon >= ARGON_MAX and len(free) > 1:
                free = [m for m in free if m != ARGON]
        if ARGON in free:
            start_on = ARGON
        if PAID_OFF and not GEMINI_ONLY:
            nogo = [m for m in free if m != GO_DEEPSEEK]
            if nogo:  # something other than the paid model is still available
                with lock:
                    if vibe_load() >= VIBE_MAX:
                        nogo = [m for m in nogo if not m.startswith("vibe:")]
                if not nogo:  # only busy Vibe slots left
                    if GO_WHEN_VIBE_FULL and GO_DEEPSEEK in free:  # user 11-05: Go may fill the gap
                        free = [GO_DEEPSEEK]
                    else:  # wait for a Vibe slot rather than spend Go
                        time.sleep(30)
                        continue
                else:
                    free = nogo
            else:  # every free/subscription model is over its limit: Go is the last fallback
                free = [m for m in free if m == GO_DEEPSEEK] or free
        else:
            with lock:
                if vibe_load() >= VIBE_MAX and len(free) > 1:
                    free = [m for m in free if not m.startswith("vibe:")] or free
        first = free.index(start_on) if start_on in free else 0
        model = free[(first + attempt) % len(free)] if free else None  # a failure moves to the next model
        if model is None:  # every model is over its usage limit
            if GEMINI_ONLY:  # stop here: the task goes back to pending for the next run
                with lock:
                    quota_out.update(wanted)
                    state.pop(tid, None); save_state(state)
                print(time.strftime("%H:%M"), tid, "returned: quota used up for", ", ".join(wanted), flush=True)
                return
            time.sleep(60)
            continue
        if model == ARGON:  # reserve the single Argon slot; released in the finally below
            with lock:
                got = active_argon < ARGON_MAX
                if got:
                    active_argon += 1
            if not got:
                time.sleep(5)
                continue
        if model.startswith("vibe:"):  # reserve the slot now; released in the finally below
            with lock:
                reserved = vibe_load() < VIBE_MAX
                if reserved:
                    active_vibe += 1
            if not reserved:
                time.sleep(5)
                continue
        logfile = ORC / "logs" / f"{tid}.log"
        with open(logfile, "a", encoding="utf-8") as log:
            log.write(f"\n===== attempt {attempt} model {model} {time.ctime()} =====\n")
            log.flush()
            offset = log.tell()
            try:
                piped = model.startswith("vibe:")
                proc = subprocess.Popen(worker_cmd(model, tid, prompt), cwd=ROOT,
                                        stdout=subprocess.PIPE if piped else log, stderr=subprocess.STDOUT)
                pump = None
                if piped:  # append the child's output ourselves; see _pump
                    pump = threading.Thread(target=_pump, args=(proc.stdout, log), daemon=True)
                    pump.start()
                lock_file(tid).write_text(str(proc.pid))  # survives a dispatcher restart
                proc.wait(timeout=4 * 3600)
                if pump:
                    pump.join(10)
            except subprocess.TimeoutExpired:
                proc.kill()
                log.write("TIMEOUT\n")
            finally:
                lock_file(tid).unlink(missing_ok=True)
                if model.startswith("vibe:"):
                    with lock:
                        active_vibe -= 1
                if model == ARGON:
                    with lock:
                        active_argon -= 1
        problems = check_output(tid) if done.exists() else ""
        if problems and attempt < 3:  # output fails the checker: send it back to the worker
            done.unlink(missing_ok=True)
            with open(logfile, "a", encoding="utf-8") as log:
                log.write(f"\n===== CHECK FAILED =====\n{problems}\n")
            print(time.strftime("%H:%M"), tid, "failed check_refine, sent back", flush=True)
            prompt = (f"{PREAMBLE}\n\n# YOUR TASK ({tid}) - FIX REQUIRED\nYour output was checked by "
                      f"`python tools/check_refine.py {tid}` and has these problems:\n\n{problems}\n\n"
                      f"Fix only these entries in the output JSON (keep the rest), re-run the checker until "
                      f"it prints OK, then rewrite orchestration/done/{tid}.md.\n\nOriginal task:\n\n{body}")
            attempt += 1
            continue
        if done.exists():
            if problems:  # out of retries: accept, but keep the checker output with the report
                with open(done, "a", encoding="utf-8") as f:
                    f.write(f"\n\n## check_refine problems left after retries\n\n{problems}\n")
            with lock:
                state[tid] = "DONE"; save_state(state)
                if fail_streak.get(model):  # a model that delivers is no longer 'dead'
                    fail_streak[model] = 0
                    save_quota()
            refresh_progress(merge=tid.startswith(("N_", "R_", "R2_", "R3_")))
            return
        with open(logfile, encoding="utf-8", errors="replace") as log:
            log.seek(offset)
            output = log.read()
        if any(m in output[-1500:].lower() for m in LIMIT_MARKERS):  # only the final error, not worker text
            # rolling quota: park this model for a while; the run doesn't count as an attempt
            with lock:
                secs = pause_seconds(model, output[-1500:])
                blocked_until[model] = time.time() + secs
                save_quota()
            print(time.strftime("%H:%M"), model, f"over usage limit, paused {secs // 60} min", flush=True)
        else:
            attempt += 1
        prompt = resume  # a retry continues from where the worker stopped
    with lock:
        state[tid] = "FAILED"; save_state(state)
    refresh_progress()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--only", default="*")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    if not a.dry:  # one dispatcher at a time: two of them overwrite each other's state.json
        me = ORC / "locks" / "dispatcher.pid"
        me.parent.mkdir(exist_ok=True)
        if me.exists() and worker_alive("dispatcher"):
            print(f"another dispatcher is already running (pid {me.read_text().strip()}); "
                  "stop it first, or delete orchestration/locks/dispatcher.pid if it is gone")
            return 1
        me.write_text(str(os.getpid()))
    def scan():
        return {p.stem: parse(p) for p in sorted((ORC / "tasks").glob("*.md"))
                if fnmatch.fnmatch(p.stem, a.only)}

    def deps_done(tid):
        for pat in tasks[tid][0]["after"]:
            # a pattern like N_* waits for every matching task (tasks appear while running)
            for d in [t for t in all_ids if fnmatch.fnmatch(t, pat)] or ([pat] if "*" not in pat else []):
                if not (state.get(d) == "DONE" or (ORC / "done" / f"{d}.md").exists()):
                    return False
        return True

    load_quota()
    tasks = scan()
    state = load_state()
    for tid in tasks:
        if (ORC / "done" / f"{tid}.md").exists():
            state[tid] = "DONE"
        elif state.get(tid) in ("RUNNING", "FAILED"):  # interrupted run, or retry failures on restart
            del state[tid]
    running, busy_lanes = {}, set()
    if not a.dry:
        refresh_progress()  # once at dispatcher start, before any lane begins
    while True:
        with lock:
            tasks.update(scan())  # picks up new tasks and edited dependencies
            all_ids = [p.stem for p in (ORC / "tasks").glob("*.md")]
            for tid, th in list(running.items()):
                if not th.is_alive():
                    busy_lanes.discard(tasks[tid][0]["lane"]); del running[tid]
            for t in tasks:  # a report written by another dispatcher also counts
                if (ORC / "done" / f"{t}.md").exists() and state.get(t) != "DONE":
                    state[t] = "DONE"; save_state(state)
            # sorted, so tasks added later (e.g. A_* hotfixes) aren't queued behind the N_* batches
            pending = sorted((t for t in tasks if state.get(t) not in ("DONE", "FAILED", "RUNNING")),
                             key=lambda t: (t.startswith(BULK), not t.startswith(("N_", "R_")), t))  # features, then function naming, then types
            # orchestration/claims/<id> = someone is doing this task by hand (e.g. in Antigravity)
            ready = [t for t in pending if tasks[t][0]["lane"] not in busy_lanes and deps_done(t)
                     and not (ORC / "claims" / t).exists() and not worker_alive(t)]
            if GEMINI_ONLY:
                # one Argon (lead-task) worker at a time; nothing new on a model that ran out
                lead_busy = any(not r.startswith(BULK) for r in running)
                keep = []
                for t in ready:
                    if quota_out.issuperset(policy_models(t, tasks[t][0]["lane"])):
                        continue
                    if not t.startswith(BULK):
                        if lead_busy:
                            continue
                        lead_busy = True
                    keep.append(t)
                ready = keep
            if a.dry:
                print("ready:", ready); print("pending:", pending); return
            for tid in ready[: max(0, a.jobs - len(running))]:
                state[tid] = "RUNNING"; busy_lanes.add(tasks[tid][0]["lane"]); save_state(state)
                th = threading.Thread(target=run_task, args=(tid, tasks[tid][1], state), daemon=True)
                th.start(); running[tid] = th
                print(time.strftime("%H:%M"), "start", tid, flush=True)
        if not running and not ready:
            break  # nothing runnable left (remaining tasks wait on FAILED deps)
        # progress/tasks.html is otherwise only rebuilt when a task finishes, and a batch takes
        # 10-25 minutes; refresh it every few minutes while workers run (in the background,
        # a rebuild takes ~20 s; skipped while one is still going)
        global last_page_refresh, last_status
        if time.time() - last_status > 300:
            last_status = time.time()
            now = time.time()
            cooling = {m.split("/")[-1][:24]: int((u - now) / 60) for m, u in blocked_until.items() if u > now}
            print(time.strftime("%H:%M"), f"STATUS running={len(running)} done={sum(1 for v in state.values() if v == 'DONE')} "
                  f"vibe={vibe_load()} cooling_min={cooling}", flush=True)
        if running and time.time() - last_page_refresh > PAGE_REFRESH and not progress_lock.locked():
            last_page_refresh = time.time()
            threading.Thread(target=refresh_progress, daemon=True).start()
        time.sleep(20)
    print(json.dumps({t: state.get(t) for t in tasks}, indent=1))


if __name__ == "__main__":
    sys.exit(main())
