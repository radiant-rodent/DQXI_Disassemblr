#!/usr/bin/env python3
"""What an answer does: add and remove steps in the Yes / No branches of a talk event, without hand-editing script.

An NPC's event (area script, `script.decompiled.nut`) asks through `local result = MessageLoop(target_id);` and
branches with `if (result == 0) { yes } else { no }`. This tool works on that shape only:

    python tools/event_actions.py show --area b002 --event IE_C01_001_A080_F08
        JSON: {"asks", "has_no", "yes": [{"text", "plain", "editable"}], "no": [...], "edited": bool}
    python tools/event_actions.py edit --area b002 --event IE_... --json ops.json [--stage] [--mod DIR]
        ops: [{"branch": "yes" | "no", "op": "add", "code": "SetGlobalGameFlag(6, 1);"},
              {"branch": "yes", "op": "remove", "index": 2}]          index = position in the branch's list
        The edited source is kept in build/event_edits/<area>.nut (later edits build on it) and compiled with
        tools/script_build.py to prove it builds; --stage also packs it into the mod.
    python tools/event_actions.py reset --area b002        drop the edited source of an area

Only single-line statements directly inside a branch can be removed; `IEChangeBlock` / `MessageLoop` lines are the
dialogue itself and stay. Steps are added at the end of the branch. The Scripts editor works on its own copy of an
area's script: the one staged last wins, so use one of the two for an area.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.npc_talk import _describe  # noqa: E402

EDITS = ROOT / "build" / "event_edits"
ALLOWED = re.compile(r"^(SetGlobalGameFlag|SetScenarioFlag|SetQuestFlag|SetLevelGroupEnable|AutoAddItemInParty)\((\d+), (\d+|true|false)\);$")
DIALOGUE = re.compile(r"^(IEChangeBlock|MessageLoop|Message|MessageEnd|WaitMessage\w*)\(")


def source(area: str) -> Path:
    edited = EDITS / f"{area}.nut"
    if edited.exists():
        return edited
    return ROOT / "game_assets" / "scripts" / "packs" / "script" / area / "script.decompiled.nut"


def locate(lines: list[str], event: str) -> dict:
    """Line ranges of the event's Yes / No branches: {"yes": (first, end), "no": (first, end) | None, "indent"}."""
    head = re.compile(r"^    function (\w+)\(")
    start = next((i for i, l in enumerate(lines) if (m := head.match(l)) and m.group(1) == event), None)
    if start is None:
        raise SystemExit(f"event {event} is not in this script")
    i = start + 1
    while i < len(lines) and not head.match(lines[i]):
        text = lines[i].strip()
        if text == "if (result == 0) {":
            indent = len(lines[i]) - len(lines[i].lstrip())
            yes_first = i + 1
            j = yes_first
            while j < len(lines) and not (len(lines[j]) - len(lines[j].lstrip()) == indent and lines[j].strip().startswith("}")):
                j += 1
            if j >= len(lines):
                break
            if lines[j].strip() == "} else {":
                k = j + 1
                while k < len(lines) and not (len(lines[k]) - len(lines[k].lstrip()) == indent and lines[k].strip() == "}"):
                    k += 1
                return {"yes": (yes_first, j), "no": (j + 1, k), "indent": indent, "start": start}
            return {"yes": (yes_first, j), "no": None, "indent": indent, "start": start}
        i += 1
    return {"yes": None, "no": None, "indent": 0, "start": start}


def steps(lines: list[str], span, indent: int) -> list[dict]:
    """The statements directly inside a branch (nested blocks count as one read-only step per line)."""
    out = []
    if span is None:
        return out
    for i in range(span[0], span[1]):
        raw = lines[i]
        text = raw.strip()
        if not text:
            continue
        direct = len(raw) - len(raw.lstrip()) == indent + 4
        single = direct and text.endswith(";") and not text.startswith(("if ", "local ", "return", "}"))
        plain = _describe(text)
        block = re.search(r'IEChangeBlock\("([^"]*)"\)', text)
        if block:
            plain = f"say block {block.group(1)}"
        elif DIALOGUE.match(text):
            plain = None
        if plain is None and not block:
            continue  # message plumbing
        out.append({"line": i, "text": text, "plain": plain, "editable": bool(single and not DIALOGUE.match(text) and not block)})
    return out


def show(area: str, event: str) -> dict:
    path = source(area)
    lines = path.read_text(encoding="utf8", errors="replace").splitlines()
    loc = locate(lines, event)
    return {
        "area": area, "event": event, "asks": loc["yes"] is not None, "has_no": loc["no"] is not None,
        "yes": steps(lines, loc["yes"], loc["indent"]), "no": steps(lines, loc["no"], loc["indent"]),
        "edited": path.parent == EDITS, "line": loc["start"] + 1,
    }


def compile_check(area: str, src: Path, stage: bool, mod: Path | None) -> tuple[bool, str]:
    cmd = [sys.executable, str(ROOT / "tools" / "script_build.py"), "pack" if stage else "compile", str(src), "--area", area, "--tier", "source", "--json"]
    if stage:
        cmd += ["--mod", str(mod or ROOT / "mod")]
    else:
        cmd += ["-o", str(EDITS / f"{area}.cnut")]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf8", errors="replace")
    last = next((l for l in reversed(proc.stdout.splitlines()) if l.strip().startswith("{")), "")
    try:
        result = json.loads(last)
    except ValueError:
        result = {}
    ok = proc.returncode == 0 and (result.get("ok", True) is not False)
    detail = "; ".join(str(e.get("message", e)) if isinstance(e, dict) else str(e) for e in (result.get("errors") or [])[:3])
    return ok, detail or (proc.stderr.strip().splitlines()[-1] if not ok and proc.stderr.strip() else "")


def edit(area: str, event: str, ops: list[dict], stage: bool, mod: Path | None) -> dict:
    path = source(area)
    lines = path.read_text(encoding="utf8", errors="replace").splitlines()
    for op in ops:
        loc = locate(lines, event)
        span = loc[op["branch"]]
        if span is None:
            raise SystemExit(f"this event has no {op['branch']} branch to edit")
        if op["op"] == "add":
            code = op["code"].strip()
            if not ALLOWED.match(code):
                raise SystemExit(f"not a step this tool adds: {code}")
            lines.insert(span[1], " " * (loc["indent"] + 4) + code)
        elif op["op"] == "remove":
            listed = steps(lines, span, loc["indent"])
            step = listed[int(op["index"])]
            if not step["editable"]:
                raise SystemExit("that step is part of the dialogue or a nested block; edit it in the script editor")
            del lines[step["line"]]
        else:
            raise SystemExit(f"unknown operation {op['op']!r}")
    EDITS.mkdir(parents=True, exist_ok=True)
    out = EDITS / f"{area}.nut"
    previous = out.read_text(encoding="utf8") if out.exists() else None
    out.write_text("\n".join(lines) + "\n", encoding="utf8")
    ok, detail = compile_check(area, out, stage, mod)
    if not ok:
        # an edit that does not build is not kept
        if previous is None:
            out.unlink()
        else:
            out.write_text(previous, encoding="utf8")
        raise SystemExit(f"the script does not build with this change: {detail}")
    result = show(area, event)
    result["staged"] = stage
    return result


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("show", "edit"):
        p = sub.add_parser(name)
        p.add_argument("--area", required=True)
        p.add_argument("--event", required=True)
        if name == "edit":
            p.add_argument("--json", type=Path, required=True)
            p.add_argument("--stage", action="store_true")
            p.add_argument("--mod", type=Path)
    r = sub.add_parser("reset")
    r.add_argument("--area", required=True)
    a = ap.parse_args()
    if a.cmd == "show":
        print(json.dumps(show(a.area, a.event), ensure_ascii=False))
    elif a.cmd == "edit":
        ops = json.loads(a.json.read_text(encoding="utf8"))
        print(json.dumps(edit(a.area, a.event, ops, a.stage, a.mod), ensure_ascii=False))
    else:
        for ext in ("nut", "cnut"):
            f = EDITS / f"{a.area}.{ext}"
            if f.exists():
                f.unlink()
        print(json.dumps({"reset": a.area}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
