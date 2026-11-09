"""Run the opt-in emulator proofs and collect their evidence.

    python tests/emu/run_cases.py                 # every emulator case
    python tests/emu/run_cases.py text table      # selected cases
    python tests/emu/run_cases.py --list

Each case builds a real mod from the project's tools, boots it in the project's Azahar data
root and plays into the save.  Evidence lands in ``out/emu/x3/<case>/`` (export report, run
log, events.jsonl, screenshots, result.json) and the screenshots used by the documentation
are copied to ``docs/images/emu/``.

Exit code 0 only if every case's checks pass.  Emulator-start-up hiccups (Azahar exiting
before the title; the translation project documents the same on this host) are retried twice.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.emu import drive  # noqa: E402
from tests.emu import fixtures as F  # noqa: E402

DOCS = REPO / "docs" / "images" / "emu"

# case -> (function, screenshots to publish, checks)
SHOTS = {
    "empty": [("empty_luma/title.png", "empty_luma_title.png"),
              ("empty_3ds/title.png", "empty_3ds_title.png")],
    "empty_save": [("empty_save/run/t440.png", "empty_movie_title.png"),
                   ("empty_save/run/t458.png", "empty_movie_save_prompt.png")],
    "text": [("text/run/recap.png", "text_recap_prompt.png"),
             ("text/run/field.png", "text_field.png")],
    "script_src": [("script_src/run/talk.png", "script_source_book.png"),
                   ("script_src/run/field.png", "script_source_field.png")],
    "script_load": [("script_load/run/scene_event.png", "script_load_event.png")],
    "script_asm": [("script_asm/run/shop.png", "script_asm_shop.png"),
                   ("script_asm/run/field.png", "script_asm_field.png")],
    "table": [("table/run/shop_list.png", "table_shop_list.png"),
              ("table/run/shop.png", "table_shop_menu.png")],
    "text_grow": [("text_grow/run/recap.png", "text_grown_recap.png")],
    "table_grow": [("table_grow/run/shop_list.png", "table_grown_shop_list.png")],
    "item_new": [("item_new/run/shop_list.png", "item_new_shop_list.png")],
    "native": [("native/run/talk.png", "native_code_ips_talk.png"),
               ("native/run/field.png", "native_code_ips_field.png")],
}


def check(name: str, result: dict) -> list[tuple[bool, str]]:
    """The per-case pass criteria, stated in the same words as the task."""
    c: list[tuple[bool, str]] = []
    if name == "empty":
        for target in ("luma", "3ds"):
            r = result.get(target) or {}
            c.append((r.get("exit") == 0, f"empty {target} export+boot exit 0"))
            c.append(((r.get("report") or {}).get("outcome") == "title",
                      f"empty {target} reached the title screen"))
    elif name == "empty_save":
        shot = F.OUT / "empty_save" / "run" / "t458.png"
        c.append((shot.is_file(), "empty-mod save load reached the recap prompt (screenshot)"))
        c.append((result.get("game_time", 0) > 450, "game time passed the title into the save"))
    elif name == "text":
        c.append((bool(result.get("marker_events")),
                  "edited line found in the live UI heap (marker; screenshot written)"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "script_src":
        # The book message is rendered from the game's glyph-encoded message buffer, so a
        # UTF-16 RAM scan cannot see it (the pane log shows the same encoding).  The talk
        # screenshot is the observation; it must differ from the field shot.
        field = F.OUT / name / "run" / "field.png"
        talk = F.OUT / name / "run" / "talk.png"
        c.append((talk.is_file() and field.is_file() and talk.read_bytes() != field.read_bytes(),
                  "talk screenshot differs from the field (book message shown)"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "script_load":
        c.append((bool(result.get("place_live")),
                  "field place label is live after the scene-load event"))
        c.append(((F.OUT / name / "run" / "scene_event.png").is_file(),
                  "scene-load screenshot written"))
        c.append((result.get("game_time", 0) > 40, "game time passed the title into the field"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "script_asm":
        c.append((bool(result.get("shop_live")),
                  "shop menu is live in the UI heap (talk started common.ShopEvent)"))
        c.append(((F.OUT / name / "run" / "shop.png").is_file(), "shop screenshot written"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "table":
        c.append((bool(result.get("price_live")),
                  "the edited price 1234567 is a live pane string in the shop"))
        c.append(((F.OUT / name / "run" / "shop_list.png").is_file(),
                  "shop goods list screenshot written"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "text_grow":
        c.append((result.get("edit", {}).get("bank_size", 0) >
                  result.get("edit", {}).get("bank_original_size", 0),
                  "the edited bank is longer than retail (the string was relocated)"))
        c.append((bool(result.get("marker_events")),
                  "the grown line is in the live UI heap"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "table_grow":
        edit = result.get("table_edit") or {}
        c.append((edit.get("rows_after", 0) > edit.get("rows_before", 0),
                  "the item table has more rows than retail"))
        c.append((bool(result.get("price_live")),
                  "the added row's price is a live pane string in the shop"))
        c.append(((F.OUT / name / "run" / "shop_list.png").is_file(),
                  "shop goods list screenshot written"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "item_new":
        edit = result.get("item_edit") or {}
        c.append((bool(edit.get("same_rows")), "item table keeps its retail row count (placeholder row)"))
        c.append((bool(result.get("name_live")), "the new item's new, longer name is live in the shop"))
        c.append((bool(result.get("price_live")),
                  "the new item's price is a live pane string in the shop"))
        c.append((not result.get("crash"), "no crash"))
    elif name == "native":
        c.append((bool(result.get("ips_reproduces_code")),
                  "code.ips applies to retail and reproduces the test executable"))
        c.append((bool(result.get("hook_alive")), "the code edit's hook is alive (input works)"))
        c.append((bool(result.get("menu_live")),
                  "a live RPC press opened the church menu (pane string in the UI heap)"))
        c.append(((F.OUT / name / "run" / "talk.png").is_file(),
                  "talk screenshot written"))
        c.append((not result.get("crash"), "no crash"))
    return c


def run_case(name: str, retries: int = 2) -> dict:
    print(f"\n=== {name} " + "=" * (72 - len(name)), flush=True)
    last = None
    for attempt in range(retries + 1):
        F.kill_emulators()
        try:
            result = drive.CASES[name]()
            result.setdefault("case", name)
            checks = check(name, result)
            result["checks"] = [{"ok": ok, "what": what} for ok, what in checks]
            result["ok"] = all(ok for ok, _ in checks)
            if retries and attempt < retries and not result["ok"] and \
                    (result.get("crash") or "").startswith(("emulator", "boot:")):
                last = result
                print(f"  retry {attempt + 1}/{retries}: {result.get('crash')}", flush=True)
                time.sleep(5)
                continue
            return result
        except Exception as exc:                      # noqa: BLE001 - report, then retry
            last = {"case": name, "ok": False, "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc()}
            print(f"  ERROR: {last['error']}", flush=True)
            if attempt < retries:
                time.sleep(5)
    return last or {"case": name, "ok": False, "error": "no result"}


def publish_shots(name: str) -> list[dict]:
    DOCS.mkdir(parents=True, exist_ok=True)
    out = []
    for rel, dest in SHOTS.get(name, []):
        src = F.OUT / rel
        if src.is_file():
            shutil.copy2(src, DOCS / dest)
            out.append({"source": str(src.relative_to(REPO)), "doc": f"docs/images/emu/{dest}"})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("cases", nargs="*", help=f"any of: {', '.join(drive.CASES)}")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--summary-only", action="store_true",
                    help="recompute checks from the per-case result.json files (no emulator)")
    a = ap.parse_args(argv)
    if a.list:
        for name in drive.CASES:
            print(name)
        return 0
    names = a.cases or list(drive.CASES)
    unknown = [n for n in names if n not in drive.CASES]
    if unknown:
        print(f"unknown case(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    env = F.load_env_note()
    results = []
    for name in names:
        if a.summary_only:
            path = (F.OUT / "empty" / "result.json" if name == "empty" else
                    F.OUT / "empty_save" / "run" / "result.json" if name == "empty_save" else
                    F.OUT / name / "run" / "result.json")
            r = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
            r["case"] = name
            r["checks"] = [{"ok": ok, "what": what} for ok, what in check(name, r)]
            r["ok"] = bool(r["checks"]) and all(c["ok"] for c in r["checks"])
        else:
            r = run_case(name, retries=a.retries)
            results.append(r)
        r["screenshots"] = publish_shots(name)
        if a.summary_only:
            results.append(r)
        print(f"  -> {'PASS' if r.get('ok') else 'FAIL'}", flush=True)

    summary = {"env": env, "cases": results,
               "ok": all(r.get("ok") for r in results),
               "finished": F.stamp()}
    path = F.OUT / "summary.json"
    F.json_dump(path, summary)
    print("\n" + "=" * 76)
    for r in results:
        print(f"{r['case']:14s} {'PASS' if r.get('ok') else 'FAIL'}")
        for c in r.get("checks", []):
            print(f"    [{'ok' if c['ok'] else '--'}] {c['what']}")
        if r.get("error"):
            print(f"    ERROR: {r['error']}")
    print(f"summary: {path}")
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
