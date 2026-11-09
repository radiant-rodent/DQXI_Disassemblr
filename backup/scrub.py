#!/usr/bin/env python3
"""Remove machine paths and personal identifiers from text before it is published.

The actual private terms live in backup/private.local.json, which is git-ignored and
never published (see PRIVATE_TEMPLATE below). Without that file scrubbing refuses to run
(fail closed), so nothing is ever published unscrubbed.

    python backup/scrub.py --check [paths...]   # report hits (exit 1 if any)
    python backup/scrub.py --fix   [paths...]   # rewrite files in place

Separator style (\\ \\\\ /) is preserved, so JSON with escaped backslashes stays valid.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PRIVATE = REPO / "backup" / "private.local.json"
PRIVATE_TEMPLATE = {
    "windows_user": "<your windows user name>",
    "wsl_user": "<your wsl user name>",
    "projects_root": "<folder that holds this project and its siblings, e.g. D:\\\\stuff>",
    "workspace_name": "DQXI_Disassemblr",
    "replace_words": {"<save name / first name>": "Player"},
    "replace_literals": {"<cloud project id>": "<gcp-project>"},
    "leak_terms": ["<real name>", "<school>", "<email user>"],
}
SEP = r"(\\\\|\\|/)"


def _load() -> dict:
    if not PRIVATE.exists():
        PRIVATE.write_text(json.dumps(PRIVATE_TEMPLATE, indent=2) + "\n", encoding="utf-8")
        raise SystemExit(f"ABORT: fill in {PRIVATE} first (a template was written)")
    cfg = json.loads(PRIVATE.read_text(encoding="utf-8"))
    if any("<" in str(v) for v in (cfg["windows_user"], cfg["projects_root"])):
        raise SystemExit(f"ABORT: {PRIVATE} still holds template values")
    return cfg


def _path_rx(win_path: str) -> str:
    """'C:\\a\\b' -> regex matching C:\\a\\b, C:\\\\a\\\\b, C:/a/b and /c/a/b (case-insensitive)."""
    parts = [p for p in re.split(r"[\\/]+", win_path) if p]
    drive = parts[0].rstrip(":")
    head = rf"(?:{re.escape(drive)}:|/{re.escape(drive)})"
    rest = "".join((SEP if i == 0 else r"\1") + re.escape(p) for i, p in enumerate(parts[1:]))
    return "(?i)" + head + rest


def _build():
    cfg = _load()
    user, wsl = cfg["windows_user"], cfg["wsl_user"]
    root, ws = cfg["projects_root"], cfg["workspace_name"]
    u = re.escape(user)
    rules: list[tuple[re.Pattern, object]] = [
        (re.compile(rf"(?i)[a-z]:{SEP}Users\1{u}\1AppData\1Local"), "%LOCALAPPDATA%"),
        (re.compile(rf"(?i)[a-z]:{SEP}Users\1{u}\1AppData\1Roaming"), "%APPDATA%"),
        (re.compile(rf"(?i)[a-z]:{SEP}Users\1{u}\b"), "%USERPROFILE%"),
        (re.compile(rf"(?i)/c/Users/{u}\b"), "~"),
        (re.compile(rf"(?i)\bUsers{SEP}{u}\b"), lambda m: f"Users{m.group(1)}<user>"),
        (re.compile(rf"/home/{re.escape(wsl)}\b"), "~"),
    ]
    mnt = "/mnt/" + "/".join(p.rstrip(":").lower() for p in re.split(r"[\\/]+", root) if p)
    rules += [
        (re.compile("(?i)" + re.escape(f"{mnt}/{ws}")), f"/mnt/<drive>/path/to/{ws}"),
        (re.compile("(?i)" + re.escape(mnt + "/")), "/mnt/<drive>/path/to/"),
        (re.compile(_path_rx(root + "\\" + ws)), "."),
        # sibling projects: <root>\3DS_Translate -> ..\3DS_Translate (separator kept)
        (re.compile(_path_rx(root) + r"(?=\\|/)"), ".."),
    ]
    # whatever is left of the projects root (e.g. the bare root or its parent)
    first = [p for p in re.split(r"[\\/]+", root) if p][:2]
    rules.append((re.compile(_path_rx("\\".join(first)) + r"\b"), ".."))
    for lit, rep in cfg.get("replace_literals", {}).items():
        if lit.startswith("<"):
            continue
        rules.append((re.compile(re.escape(f'"{lit}"')), f'os.environ.get("DQXI_VERTEX_PROJECT", "")'))
        rules.append((re.compile(re.escape(lit)), rep))
    for word, rep in cfg.get("replace_words", {}).items():
        if not word.startswith("<"):
            rules.append((re.compile(rf"\b{re.escape(word)}\b"), rep))

    terms = [t for t in cfg.get("leak_terms", []) if not t.startswith("<")]
    terms += [w for w in cfg.get("replace_words", {}) if not w.startswith("<")]
    terms += [l for l in cfg.get("replace_literals", {}) if not l.startswith("<")]
    leak_rx = [rf"\b{re.escape(t)}\b" for t in terms]
    leak_rx += [rf"[a-z]:[\\/]+users[\\/]+{u}\b", r"/home/" + re.escape(wsl) + r"\b",
                _path_rx(root)[4:], r"@gmail\.com",
                r"AIza[0-9A-Za-z_-]{20,}", r"gh[opsu]_[A-Za-z0-9]{20,}", r"sk-[A-Za-z0-9]{20,}"]
    return rules, re.compile("(?i)" + "|".join(leak_rx))


RULES, LEAK = _build()


def _text(data: bytes) -> str | None:
    if b"\0" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def scrub_text(text: str) -> str:
    for pat, rep in RULES:
        text = pat.sub(rep, text)
    return text


def scrub_bytes(data: bytes) -> bytes:
    text = _text(data)
    if text is None:
        return data
    new = scrub_text(text)
    return data if new == text else new.encode("utf-8")


def leaks(data: bytes) -> list[str]:
    text = _text(data)
    if text is None:
        # binary: still look for ASCII/UTF-16 traces of the private terms
        text = data.decode("latin-1") + data.replace(b"\0", b"").decode("latin-1")
    return sorted({m.group(0) for m in LEAK.finditer(text)})


def main() -> int:
    fix = "--fix" in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--cached", "--others",
                              "--exclude-standard"], capture_output=True, text=True).stdout
        paths = [str(REPO / p) for p in out.split("\0") if p]
    bad = 0
    for p in map(Path, paths):
        data = p.read_bytes()
        new = scrub_bytes(data)
        if fix and new != data:
            p.write_bytes(new)
            print(f"scrubbed {p}")
        rest = leaks(new if fix else data)
        if rest:
            bad += 1
            print(f"LEAK {p}: {len(rest)} distinct hit(s)")
    print(f"{len(paths)} files checked, {bad} with remaining hits")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
