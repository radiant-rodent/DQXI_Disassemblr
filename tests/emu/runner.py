"""Opt-in emulator tests: prove that the project's edits run in the game.

These tests are **not** part of ``python tests/run_all.py``.  They launch the portable
Azahar emulator, take several minutes, and need exclusive use of its fixed RPC port
(45987).  Run them by hand:

    python -m tests.emu                 # fastest useful set (boot, table, text, native, arm)
    python -m tests.emu --case all      # + the two script tiers and the scene-load case (long)
    python -m tests.emu --case script
    python -m tests.emu --case script_load   # source tier: new function started at scene load
    python -m tests.emu --list

The runner refuses to start while another Azahar is using the RPC port.  Use
``DQ11_EMUTEST`` to point at a separate data root if another worker is testing; the emulator
binary is copied once per root by ``python -m tools.emu setup`` (this runner never downloads
anything).

Everything is recorded under ``out/emu/tests/<case>/``: screenshots, ``events.jsonl`` (text
log), the patch/pack used, and ``report.json`` with the assertions and observed values.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
BUILD = ROOT / "build" / "emu_test"
OUT = ROOT / "out" / "emu" / "tests"
REFERENCE_SAVES = Path(r"..\3DS_Translate\_emutest\saves")
RETAIL_CODE = ROOT / "original" / "exefs" / "code.decompressed.bin"
RETAIL_ROM = ROOT / "build" / "DQXI.3ds"
SAVE_2D = "user_citra_2d"


# --------------------------------------------------------------------------- environment
def load_emu_modules():
    """Import the project's emulator wrapper and the harness (sets paths from the env)."""
    sys.path.insert(0, str(ROOT))
    from tools.emu import extras, textlog                      # noqa: E402
    extras.load()
    return extras, textlog


def ensure_saves(extras) -> None:
    """Copy the proven game saves from the reference checkout if this root lacks them."""
    need = ("user_citra_2d", "user_citra", "user_citra_3d")
    for name in need:
        dst = Path(extras.SAVES) / name
        if dst.is_dir():
            continue
        src = REFERENCE_SAVES / name
        if not src.is_dir():
            raise SystemExit(f"no save {name!r} in {extras.SAVES} and no reference copy at {src}")
        # Copy the children, not the folder itself (avoids saves/<name>/<name>/ on re-runs).
        dst.mkdir(parents=True)
        for child in src.iterdir():
            if child.is_dir():
                shutil.copytree(child, dst / child.name)
            else:
                shutil.copy2(child, dst / child.name)
        print(f"  save {name}: copied from the reference checkout")


def rpc_port_in_use() -> bool:
    """UDP 45987 is Azahar's fixed RPC port; two emulators cannot run at once."""
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "UDP"], capture_output=True,
                             text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return any(":45987" in line for line in out.splitlines())


def kill_test_emulators(extras) -> None:
    """Stop only *our* portable azahar (matched by full path), then wait for it to go."""
    exe = str(Path(extras.EXE))
    ps = (f"Get-CimInstance Win32_Process -Filter \"Name='azahar.exe'\" | "
          f"Where-Object {{ $_.ExecutablePath -eq '{exe}' }} | "
          f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    for _ in range(20):
        if not rpc_port_in_use():
            return
        time.sleep(0.25)


# --------------------------------------------------------------------------- code builds
def build_test_code(textlog: bool, path: Path | None = None) -> Path:
    """Retail code + the test-only input hook (+ text logger), cached in build/emu_test."""
    from tools.emu import testhook
    path = path or (BUILD / ("code_hook_textlog.bin" if textlog else "code_hook.bin"))
    if path.is_file():
        return path
    code = RETAIL_CODE.read_bytes()
    code = testhook.apply(code)
    if textlog:
        from tools.emu import textlog as tl
        code = tl.apply(code)
    BUILD.mkdir(parents=True, exist_ok=True)
    path.write_bytes(code)
    return path


def workspace(name: str, code: Path, textlog: bool) -> Path:
    ws = BUILD / f"ws_{name}"
    shutil.rmtree(ws, ignore_errors=True)
    (ws / "code").mkdir(parents=True)
    shutil.copyfile(code, ws / "code" / "code.bin")
    (ws / "mod.json").write_text(json.dumps({
        "name": f"X3 {name}", "version": "0.0", "author": "tests/emu",
        "description": "emulator test build (never export this as a release)"},
        indent=1), encoding="utf-8")
    return ws


def export(ws: Path, out: Path, code_mode: str) -> dict:
    """Run the real exporter (validates, checks ARMv6K, writes Luma/.3ds)."""
    shutil.rmtree(out, ignore_errors=True)
    cmd = [sys.executable, str(ROOT / "tools" / "export_mod.py"), "--mod", str(ws),
           "--out", str(out), "--target", "luma", "--code", code_mode]
    print("  $", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"export failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    return json.loads((out / "EXPORT_REPORT.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- emulator use
class Run:
    """One emulator session with the helper gestures used by all cases."""

    def __init__(self, extras, mod: Path, save: str = SAVE_2D, out: Path | None = None):
        self.extras = extras
        self.mod = mod
        self.out = out
        self.save = save
        self.emu = None
        self.rec = None
        self.rpc = None
        self.az = extras.load()[0]

    def __enter__(self):
        kill_test_emulators(self.extras)
        if rpc_port_in_use():
            raise RuntimeError("another Azahar is using RPC port 45987; wait for it to finish "
                               "or use a separate DQ11_EMUTEST root (do not kill another "
                               "worker's emulator)")
        # OpenGL: Vulkan crashes Azahar at boot on this machine's driver
        self.emu = self.extras.make_emu(str(RETAIL_ROM), mod=str(self.mod), save=self.save,
                                        workdir=str(self.out or (BUILD / "run")),
                                        settings={"graphics_api": "1"})
        self.emu.start()
        return self

    def __exit__(self, *exc):
        try:
            if self.rec:
                self.rec.stop()
        except Exception:
            pass
        try:
            if self.emu:
                self.emu.stop()
        except Exception:
            pass
        kill_test_emulators(self.extras)

    def tap(self, button: str, frames: int = 2, settle: float = 1.0):
        """Queue a pulse through the test input hook; does not wait for consumption.

        ``Azahar.press`` waits until the game has read the pulse, which times out during a
        long load (the RPC server is synchronous).  Writing the mailbox directly is the same
        mechanism and survives a loading screen.
        """
        mask = self.az.BTN[button]
        self.emu.write(self.az.Azahar.MAILBOX + 20, struct.pack("<II", mask, frames))
        time.sleep(settle)

    def wait_title(self, timeout: float = 180.0) -> bool:
        """Wait for the live title menu.  Ignores the early frame the game preloads the
        strings into the UI heap (game time below 500s: still the logo/movie)."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.emu.game_time() > 500 and self.emu.title_evidence():
                return True
            time.sleep(0.5)
        return False

    def wait_game(self, target: float, timeout: float = 240.0) -> bool:
        """Wait until the guest clock reaches ``target`` (no UI detection)."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.emu.game_time() >= target:
                return True
            time.sleep(0.5)
        return False

    def start_textlog(self):
        from AzaharRPC import AzaharRPC
        self.rpc = AzaharRPC(timeout=5, retries=3)
        from tools.emu import textlog
        self.rec = textlog.TextRecorder(self.rpc, self.emu, str(self.out), shots=True)
        self.rec.start()
        return self.rec

    def load_save(self, rec=None):
        """Title -> Continue -> slot 1 -> recap 'No' -> field (the 2D Cobblestone save)."""
        self.tap("A", settle=2.0)           # Continue
        self.tap("A", settle=6.0)           # slot 1
        if rec:
            t0 = time.time()
            while time.time() - t0 < 40 and not rec.find("あらすじ"):
                time.sleep(0.5)
            self.tap("B", settle=2.0)       # no recap
            t0 = time.time()
            while time.time() - t0 < 40 and not any(
                    e.get("name") == "txt_place" for e in rec.events):
                time.sleep(0.5)
        else:
            time.sleep(20)
        for _ in range(4):                  # clear the blessing / menu windows
            self.tap("B", settle=1.2)

    def shot(self, name: str) -> Path:
        path = Path(self.out) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        self.emu.shot(str(path))
        return path


# --------------------------------------------------------------------------- cases
def case_boot(extras, textlog, full: bool = False) -> dict:
    """Empty mod: Luma export (and optionally the full .3ds) boots to the title."""
    out = OUT / "boot"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    ws = BUILD / "ws_empty"
    shutil.rmtree(ws, ignore_errors=True)
    ws.mkdir(parents=True)
    (ws / "mod.json").write_text(json.dumps({"name": "empty", "version": "0.0",
                                             "author": "tests/emu"}), encoding="utf-8")
    report = {"case": "boot", "targets": {}}

    luma = export(ws, out / "luma_export", "ips")
    report["targets"]["luma"] = {"export": luma["targets"]["luma"],
                                 "romfs_changes": luma["romfs_changes"]}
    print("  booting retail + the empty Luma overlay (empty overlays are skipped) ...")
    proc = subprocess.run([sys.executable, "-m", "tools.emu", "boot", str(RETAIL_ROM),
                           "--mod", str(out / "luma_export" / "luma"), "--seconds", "150",
                           "--shot", str(out / "luma_title.png")],
                          cwd=ROOT, capture_output=True, text=True, timeout=300)
    report["targets"]["luma"].update(exit=proc.returncode,
                                     title=(proc.returncode == 0),
                                     log=proc.stdout.strip().splitlines()[-6:])
    if full:
        cmd = [sys.executable, str(ROOT / "tools" / "export_mod.py"), "--mod", str(ws),
               "--out", str(out / "3ds_export"), "--target", "3ds"]
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        image = out / "3ds_export" / "3ds" / "DQXI_modded.3ds"
        boot = subprocess.run([sys.executable, "-m", "tools.emu", "boot", str(image),
                               "--seconds", "150", "--shot", str(out / "3ds_title.png")],
                              cwd=ROOT, capture_output=True, text=True, timeout=300)
        report["targets"]["3ds"] = {"export_exit": p.returncode, "image": str(image),
                                    "size": image.stat().st_size if image.is_file() else 0,
                                    "exit": boot.returncode, "title": boot.returncode == 0,
                                    "log": boot.stdout.strip().splitlines()[-6:]}
    ok = report["targets"]["luma"]["title"] and (
        not full or report["targets"]["3ds"]["title"])
    report["ok"] = ok
    return report


def _scan_memory(emu, needle: bytes, ranges=((0x30000000, 0x34000000),)):
    found = []
    for start, end in ranges:
        a = start
        while a < end:
            data = emu.read(a, 0x8000)
            if data:
                i = data.find(needle)
                while i >= 0:
                    found.append(a + i)
                    i = data.find(needle, i + 1)
            a += 0x8000
    return found


def case_table(extras, textlog) -> dict:
    """Edit the herb's buy price; read the exact patched row out of the running game."""
    from tools.table_edit import Table
    from tools.export_mod import stage_table
    out = OUT / "table"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    code = build_test_code(textlog=True)
    ws = workspace("table", code, True)
    table = Table("syscmn/item.json")
    row = table.find("やくそう")
    spec = table.field("buy_price")
    before = table.read(row, spec)
    value = 1234567
    table.write(row, spec, value)
    bxon = BUILD / "table_item.bxon"
    bxon.write_bytes(bytes(table.raw))
    stage_table("syscmn/item.json", bxon, ws)
    report = {"case": "table", "table": table.name, "row": row, "field": spec["name"],
              "before": before, "after": value}
    export(ws, out / "export", "bin")
    with Run(extras, out / "export" / "luma", out=out) as run:
        if not run.wait_title():
            raise RuntimeError("title screen not reached")
        run.load_save()
        run.shot("field.png")
        root = table.rows[row]
        patched_row = bytes(table.raw)[root:root + table.row_size]
        needle = patched_row[0x0e:0x30]          # id..group: no pointers, exact values
        found = _scan_memory(run.emu, needle)
        report["addresses"] = [f"0x{a:08X}" for a in found]
        if found:
            at = found[0] - 0x0e
            back = run.emu.read(at, table.row_size)
            report["row_matches"] = back == patched_row
            report["price_in_ram"] = int.from_bytes(back[0x18:0x1c], "little")
        report["ok"] = bool(found) and report.get("row_matches") and \
            report.get("price_in_ram") == value
    return report


def case_text(extras, textlog) -> dict:
    """Replace the load-game recap line; see it in the message window + text log."""
    from tools import text_tool
    from tools.export_mod import stage_member
    from pathlib import Path
    out = OUT / "text"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    code = build_test_code(textlog=True)
    ws = workspace("text", code, True)
    bank = text_tool.import_bank("ui/title/title_msg")
    doc = text_tool.read_bank_json(ROOT / "game_assets/text/banks/ui/title/title_msg.json")
    marker = "X3 TEXT EDIT OK"
    for entry in doc["entries"]:
        if entry["location"] == "row[22].1[2]":
            entry["text"] = marker
            break
    built = text_tool.rebuild_bank(bank.data, text_tool.texts_from_json(doc, bank))
    bxon = BUILD / "title_msg.bxon"
    bxon.write_bytes(built)
    stage_member(bank.pack, bank.member, bxon, ws)
    report = {"case": "text", "bank": bank.key, "location": "row[22].1[2]",
              "marker": marker}
    export(ws, out / "export", "bin")
    with Run(extras, out / "export" / "luma", out=out) as run:
        if not run.wait_title():
            raise RuntimeError("title screen not reached")
        rec = run.start_textlog()
        run.tap("A", settle=2.0)
        run.tap("A", settle=6.0)
        t0 = time.time()
        hits = []
        while time.time() - t0 < 40:
            hits = rec.find(marker)
            if hits:
                break
            time.sleep(0.5)
        run.shot("recap_with_marker.png")
        rec.stop()
        report["text_events"] = hits[-3:]
        report["ok"] = bool(hits) and any(marker in e.get("text", "") for e in hits)
    return report


def _script_build_and_export(name: str, source: Path, tier: str) -> Path:
    code = build_test_code(textlog=True)
    ws = workspace(name, code, True)
    cmd = [sys.executable, str(ROOT / "tools" / "script_build.py"), "pack", str(source),
           "--area", "b011", "--tier", tier, "--mod", str(ws)]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"script build failed:\n{proc.stdout}\n{proc.stderr}")
    out = OUT / name
    shutil.rmtree(out, ignore_errors=True)
    export(ws, out / "export", "bin")
    return out / "export" / "luma"


def _talk_case(extras, name: str, mod: Path) -> dict:
    out = OUT / name
    with Run(extras, mod, out=out) as run:
        if not run.wait_title():
            raise RuntimeError("title screen not reached")
        rec = run.start_textlog()
        run.load_save(rec)
        run.shot("ready.png")
        before = len(rec.events)
        run.tap("A", settle=3.0)
        run.shot("after_a.png")
        new = [e for e in rec.events[before:] if "text" in e]
        rec.stop()
        return {"new_text": new, "ready": "ready.png", "after": "after_a.png"}


def case_script(extras, textlog, with_source: bool = True) -> dict:
    """Assembly tier: type comparisons changed, talking no longer opens the priest talk.

    Source tier: a recompiled talk handler that opens the church UI directly (this proves the
    source build executes; the blank box is expected for a call outside the event context).
    """
    out = OUT / "script"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    report = {"case": "script"}

    # Baseline: unchanged b011 pack from the cartridge.
    code = build_test_code(textlog=True)
    ws = workspace("script_baseline", code, True)
    (ws / "romfs" / "script").mkdir(parents=True)
    shutil.copyfile(ROOT / "game_data/romfs/script/b011.pack",
                    ws / "romfs/script/b011.pack")
    export(ws, out / "baseline_export", "bin")
    base = _talk_case(extras, "script_baseline", out / "baseline_export" / "luma")
    greeting = [e for e in base["new_text"] if "頼もしき" in e.get("text", "")]
    report["baseline"] = {"greeting": bool(greeting), "events": len(base["new_text"])}

    # Assembly tier: byte-exact listing; change the two type compares.
    listing = (ROOT / "game_assets/scripts/packs/script/b011/script.nut").read_text(
        encoding="utf-8")
    i = listing.index("function 'TrgRCommand'")
    j = listing.find("function '", i + 10)
    block = listing[i:j]
    block = block.replace("LOADINT      5     16", "LOADINT      5     17", 1)
    block = block.replace("LOADINT      5     10", "LOADINT      5     11", 1)
    asm = BUILD / "b011_types.nut"
    asm.write_text(listing[:i] + block + listing[j:], encoding="utf-8")
    mod = _script_build_and_export("script_asm", asm, "asm")
    a = _talk_case(extras, "script_asm", mod)
    report["assembly"] = {"greeting": any("頼もしき" in e.get("text", "")
                                          for e in a["new_text"]),
                          "events": len(a["new_text"]),
                          "screenshots": [a["ready"], a["after"]]}

    # Source tier: recompile only TrgRCommand; it opens StartUI(24, target) directly.
    src = (ROOT / "game_assets/scripts/packs/script/b011/script.decompiled.nut").read_text(
        encoding="utf-8")
    needle = "    function TrgRCommand(type) {\n"
    add = (needle +
           "        // X3 test: open the church service menu directly on talk. Test only.\n"
           "        if (type == 10) {\n"
           "            StartUI(24, GetTargetActorID());\n"
           "            return;\n"
           "        }\n")
    source = BUILD / "b011_source.nut"
    source.write_text(src.replace(needle, add, 1), encoding="utf-8")
    report["source"] = {"built": False}
    if with_source:
        mod = _script_build_and_export("script_source", source, "source")
        s = _talk_case(extras, "script_source", mod)
        report["source"] = {"built": True, "greeting": any(
            "頼もしき" in e.get("text", "") for e in s["new_text"]),
            "events": len(s["new_text"]), "screenshots": [s["ready"], s["after"]]}

    report["ok"] = (report["baseline"]["greeting"]
                    and not report["assembly"]["greeting"]
                    and report["assembly"]["events"] == 0
                    and (not with_source or (report["source"]["built"]
                                             and not report["source"]["greeting"])))
    return report


def _load_field_without_extra_taps(run, rec, shot_name: str) -> dict:
    """Title -> Continue -> slot 1 -> field, stopping as soon as the field is live.

    ``Run.load_save`` ends with four B presses to clear the blessing windows; this
    case must not press B after the field loads, because the scripted event it is
    looking for opens a menu. Every wait is generous: on a loaded host Azahar can
    run below real time, and a fixed sleep lands on the wrong screen.
    """
    run.tap("A", settle=4.0)             # Continue
    time.sleep(8.0)                      # save-slot list
    run.tap("A", settle=4.0)             # slot 1
    if rec is not None:
        t0 = time.time()
        while time.time() - t0 < 150 and not rec.find("あらすじ"):
            time.sleep(1.0)
    else:
        time.sleep(40)
    run.tap("B", settle=3.0)             # "no" to the story recap
    if rec is not None:
        t0 = time.time()
        while time.time() - t0 < 150 and not any(e.get("name") == "txt_place"
                                                for e in rec.events):
            time.sleep(1.0)
    else:
        time.sleep(40)
    # let the scene's OnBeginScene event open its menu
    time.sleep(8.0)
    path = run.shot(shot_name)
    return {"screenshot": str(path), "game_time": round(run.emu.game_time(), 1)}


def _wait_emulator_free(timeout: float = 900.0, stable: float = 20.0) -> bool:
    """Wait until the fixed RPC port has been free for ``stable`` seconds.

    Azahar's RPC port (45987) is compiled in, so two instances cannot run at once -
    and a second root's emulator is *not* ours to kill. Other lanes start runs with
    only a few seconds between them, so a single free check is not enough.
    """
    t0 = time.time()
    free_since = None
    while time.time() - t0 < timeout:
        if rpc_port_in_use():
            free_since = None
        elif free_since is None:
            free_since = time.time()
        elif time.time() - free_since >= stable:
            return True
        time.sleep(5)
    return False


def _wait_title_alive(run, timeout: float) -> tuple[bool, str | None]:
    """Reach the title menu, noticing our own emulator process dying.

    Without input the retail build stays on the opening-movie logo card, so press
    START once the movie is over (the same press the ``tools.emu boot`` movie makes
    at 430 game seconds).
    """
    t0 = time.time()
    pressed = False
    while time.time() - t0 < timeout:
        if run.emu.proc.poll() is not None:
            return False, f"emulator exited ({run.emu.proc.returncode})"
        game_time = run.emu.game_time()
        if not pressed and game_time > 430:
            run.tap("START", settle=1.0)
            pressed = True
            continue
        if game_time > 500 and run.emu.title_evidence():
            return True, None
        time.sleep(1.0)
    return False, "title screen not reached"


def case_script_load(extras, textlog) -> dict:
    """Source tier at scene load: add a function and start it from OnBeginScene.

    This is the edit that used to crash the field load. It compiles a *new*
    function and calls it from ``OnBeginScene``, so the module prototype and the
    scene hook are recompiled; before the compiler fix, statement-position calls
    in the recompiled functions stored their result in register -1 and the game
    crashed while the save loaded, with no script error.

    The new function opens the shop menu in its own event thread
    (``StartUI(2, -1)`` / ``WaitMenu()`` / ``EndUI(2)``, the body of the game's own
    ``common.ShopEvent``), so the proof is positive: the field loads, the game keeps
    running, and the shop menu's labels are live in the dynamic UI heap. Every step up
    to the pack uses the real tools (``script_build.py pack --tier source`` +
    ``export_mod.py``).
    """
    from pathlib import Path

    out = OUT / "script_load"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)

    src = (ROOT / "game_assets/scripts/packs/script/b011/script.decompiled.nut").read_text(
        encoding="utf-8")
    old = (
        "    function OnBeginScene() {\n"
        "        if (IsSetupLocationCS()) {\n"
        "            StartEvent(LocationCS2Way);\n"
        "        }\n"
        "    }\n"
    )
    new = (
        "    function X3SceneEvent() {\n"
        "        // Test-only: open the shop menu when this field finishes loading.\n"
        "        WaitFrame(30);\n"
        "        StartUI(2, -1);\n"
        "        WaitMenu();\n"
        "        EndUI(2);\n"
        "    }\n"
        "    function OnBeginScene() {\n"
        "        StartEvent(X3SceneEvent);\n"
        "        if (IsSetupLocationCS()) {\n"
        "            StartEvent(LocationCS2Way);\n"
        "        }\n"
        "    }\n"
    )
    edited = src.replace(old, new, 1)
    if edited == src:
        raise RuntimeError("b011 source layout changed; update the scene-load edit")
    source = BUILD / "b011_scene_load.nut"
    source.write_text(edited, encoding="utf-8")

    mod = _script_build_and_export("script_load", source, "source")
    report = {"case": "script_load", "edit": "new function started from OnBeginScene",
              "source": str(source), "attempts": []}

    # Azahar on this host dies at startup now and then (NVIDIA driver, also with the
    # retail ROM), and other lanes kill each other's emulator on the fixed RPC port;
    # retry the boot before blaming the pack.
    for attempt in range(5):
        try:
            if not _wait_emulator_free(900):
                report["attempts"].append({"attempt": attempt + 1,
                                           "error": "RPC port 45987 stayed busy for 15 min"})
                break
            with Run(extras, mod, out=out) as run:
                # A loaded machine can run the emulator below 3x real time; the title
                # menu is only live after the opening movie (~500 game seconds).
                titled, why = _wait_title_alive(run, 420)
                if not titled:
                    report["attempts"].append({"attempt": attempt + 1,
                                               "error": why,
                                               "game_time": round(run.emu.game_time(), 1),
                                               "crash": run.emu.crashed(),
                                               "log": run.emu.log(tail=4000)
                                                       .strip().splitlines()[-6:]})
                    if attempt < 4:
                        time.sleep(5)
                        continue
                    break
                rec = None
                try:
                    rec = run.start_textlog()
                except Exception as exc:          # the ring is profile-dependent
                    report["textlog"] = f"unavailable: {exc}"
                evidence = _load_field_without_extra_taps(run, rec, "field_after_load.png")
                report.update(evidence)
                try:
                    labels = ["かいにきた", "かいもの", "うる"]
                    found = run.emu.find_utf16_many(labels, start=0x33000000,
                                                    end=0x34000000)
                    report["menu_labels"] = [{"text": t, "address": f"0x{a:08X}"}
                                             for t, a in found.items()]
                except Exception as exc:
                    report["menu_labels"] = []
                    report["menu_probe_error"] = str(exc)
                report["hook_alive"] = bool(run.emu.hook_alive())
                if rec is not None:
                    report["recent_text"] = [e.get("text", "") for e in rec.events[-8:]]
                # the clock must still be alive: a crash would freeze or kill it
                t_before = run.emu.game_time()
                time.sleep(3.0)
                report["clock_advanced"] = run.emu.game_time() > t_before + 0.5
                report["crash"] = run.emu.crashed()
                run.shot("field_stable.png")
            break
        except RuntimeError as exc:
            if attempt == 4:
                raise
            report["attempts"].append({"attempt": attempt + 1, "error": str(exc)})
            time.sleep(5)

    report["ok"] = (bool(report.get("menu_labels")) and report.get("clock_advanced", False)
                    and not report.get("crash"))
    return report


def case_native(extras, textlog) -> dict:
    """Native code edit: test hook in code.bin, proven by live input + code.ips round-trip."""
    from tools.export_mod import apply_ips, make_ips
    out = OUT / "native"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    code = build_test_code(textlog=True)
    ws = workspace("native", code, True)
    report = {"case": "native"}
    ips_export = export(ws, out / "ips_export", "ips")
    code_bin_export = export(ws, out / "bin_export", "bin")
    ips = (out / "ips_export" / "luma" / "titles" / "0004000000199200" / "code.ips").read_bytes()
    patched = (out / "bin_export" / "luma" / "titles" / "0004000000199200" / "code.bin").read_bytes()
    report["ips_bytes"] = len(ips)
    report["ips_reproduces_code_bin"] = apply_ips(RETAIL_CODE.read_bytes(), ips) == patched
    report["ips_report"] = ips_export.get("armv6k")
    with Run(extras, out / "bin_export" / "luma", out=out) as run:
        # The hook is installed from the first instruction, so no UI navigation is needed:
        # wait past the opening movie, then read the patched words back from guest RAM.
        if not run.wait_game(500):
            raise RuntimeError("game clock did not advance")
        run.tap("START", settle=2.0)
        run.tap("A", settle=3.0)
        ret = run.emu.read(0x11AD3C, 4)
        cave = run.emu.read(0x724F00, 16)
        report["return_word"] = ret.hex()
        report["cave"] = cave.hex()
        report["hook_alive"] = bool(run.emu.hook_alive())
        run.shot("live_input.png")
        report["game_time"] = round(run.emu.game_time(), 1)
    report["ok"] = (report["ips_reproduces_code_bin"] and report["hook_alive"]
                    and report["return_word"] == "6f2818eb"
                    and bool(report.get("ips_report", {}).get("ok")))
    return report


CASES = {
    "boot": case_boot,
    "table": case_table,
    "text": case_text,
    "script": case_script,
    "script_load": case_script_load,
    "native": case_native,
}
FAST = ("boot", "table", "text", "native")


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", action="append", choices=sorted(CASES) + ["all"],
                    help="case to run (repeatable; default: boot/table/text/native)")
    ap.add_argument("--full", action="store_true",
                    help="boot case also builds and boots the 4 GiB .3ds image")
    ap.add_argument("--no-source", action="store_true",
                    help="script case: skip the source-tier run (assembly still tested)")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for name in CASES:
            print(name)
        return 0
    chosen = a.case or list(FAST)
    if "all" in chosen:
        chosen = list(CASES)
    extras, textlog = load_emu_modules()
    OUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    ensure_saves(extras)
    print(f"data root: {extras.DATA_ROOT}")
    print(f"emulator:  {extras.EXE}")
    if rpc_port_in_use():
        print("WARNING: an Azahar is already using RPC port 45987.  Wait for it to finish; "
              "the runner will refuse to launch a second one.", file=sys.stderr)
    results = {}
    worst = 0
    for name in chosen:
        print(f"\n=== {name} ===", flush=True)
        try:
            if name == "boot":
                res = CASES[name](extras, textlog, full=a.full)
            elif name == "script":
                res = CASES[name](extras, textlog, with_source=not a.no_source)
            else:
                res = CASES[name](extras, textlog)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            res = {"case": name, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
        results[name] = res
        (OUT / name).mkdir(parents=True, exist_ok=True)
        (OUT / name / "report.json").write_text(
            json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  {'PASS' if res.get('ok') else 'FAIL'}")
        if not res.get("ok"):
            worst = 1
    (OUT / "SUMMARY.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nsummary: {OUT / 'SUMMARY.json'}")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
