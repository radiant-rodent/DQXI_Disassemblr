"""Minimal coding agent on Gemini via Vertex AI (google-genai SDK), used by dispatch.py as a fallback.

    python orchestration/vertex_agent.py --model gemini-3.8-flash --prompt-file task.txt

Gives the model file and shell tools rooted at the project, prints every tool call (so the worker
board shows live progress), and keeps nudging it until orchestration/done/<task>.md exists or the
turn budget runs out. Quota errors are printed as RESOURCE_EXHAUSTED so the dispatcher parks Vertex.
"""
import argparse, os, shutil, subprocess, sys
from pathlib import Path

from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
PROJECT = os.environ.get("DQXI_VERTEX_PROJECT", "")
GIT_BASH = Path(r"C:\Program Files\Git\bin\bash.exe")
BASH = str(GIT_BASH) if GIT_BASH.is_file() else (shutil.which("bash") or "bash")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # the log is UTF-8, not the console codepage


def say(*a):
    print(*a, flush=True)


def _path(p):
    q = Path(p)
    return q if q.is_absolute() else ROOT / q


def read_file(path: str, offset: int = 0, limit: int = 400) -> str:
    """Read a text file (relative paths are from the project root). Returns lines offset..offset+limit."""
    say(f"→ read {path} [{offset}:{offset + limit}]")
    try:
        lines = _path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        return f"ERROR: {e}"
    return "\n".join(f"{i + 1}\t{l}" for i, l in enumerate(lines[offset:offset + limit], offset)) + \
        (f"\n... {len(lines)} lines total" if len(lines) > offset + limit else "")


def write_file(path: str, content: str) -> str:
    """Create or overwrite a file with content (UTF-8)."""
    say(f"← write {path} ({len(content)} chars)")
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return "ok"


def edit_file(path: str, old: str, new: str) -> str:
    """Replace the single exact occurrence of old with new in a file."""
    say(f"← edit {path}")
    p = _path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        return f"ERROR: old text found {text.count(old)} times, must be exactly once"
    p.write_text(text.replace(old, new), encoding="utf-8")
    return "ok"


def list_dir(path: str = ".") -> str:
    """List a directory (names, '/' suffix for folders), at most 500 entries."""
    say(f"→ ls {path}")
    try:
        items = sorted(_path(path).iterdir())
    except OSError as e:
        return f"ERROR: {e}"
    out = [i.name + ("/" if i.is_dir() else "") for i in items[:500]]
    return "\n".join(out) + (f"\n... {len(items)} entries" if len(items) > 500 else "")


def run_shell(command: str, timeout_seconds: int = 1800) -> str:
    """Run a bash command in the project root (Git Bash on Windows). Returns exit code and the last
    20,000 characters of combined output."""
    say(f"$ {command[:300]}")
    try:
        r = subprocess.run([BASH, "-lc", command], cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout_seconds)
        out = (r.stdout or "") + (r.stderr or "")
        return f"exit={r.returncode}\n{out[-20000:]}"
    except subprocess.TimeoutExpired:
        return f"ERROR: timed out after {timeout_seconds}s"


def main():
    # DISABLED 2026-10-26: workers ran shell commands inside WSL/Docker and wrote outside the project.
    # Re-enable only with DQXI_VERTEX_ENABLED=1 after the tools are sandboxed to the project root.
    if not os.environ.get("DQXI_VERTEX_ENABLED"):
        say("RESOURCE_EXHAUSTED quota exceeded: Vertex worker disabled until sandboxed")
        return 1
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.8-flash")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--done", help="report file whose existence means the task is finished")
    ap.add_argument("--turns", type=int, default=25)
    a = ap.parse_args()
    prompt = Path(a.prompt_file).read_text(encoding="utf-8")
    client = genai.Client(vertexai=True, project=PROJECT, location="global")
    chat = client.chats.create(model=a.model, config=types.GenerateContentConfig(
        tools=[read_file, write_file, edit_file, list_dir, run_shell],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=150),
        system_instruction="You are an autonomous software worker. Use the tools to do the task "
                           "completely; do not ask questions. Keep going until the report file is written."))
    message = prompt
    for turn in range(a.turns):
        try:
            reply = chat.send_message(message)
        except Exception as e:  # surface quota errors in words the dispatcher recognises
            text = str(e)
            say(("RESOURCE_EXHAUSTED quota exceeded: " if "429" in text or "RESOURCE_EXHAUSTED" in text
                 else "ERROR: ") + text[:500])
            return 1
        say(f"[turn {turn}] {(reply.text or '').strip()[:1500]}")
        if a.done and Path(a.done).exists():
            return 0
        message = ("Continue the task. If it is complete, write the report file now "
                   f"({a.done}). Do not stop early.")
    return 0 if a.done and Path(a.done).exists() else 2


if __name__ == "__main__":
    sys.exit(main())
