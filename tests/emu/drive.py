"""Drive one emulator proof: boot a mod, play into the save, look at what the game shows.

The boot sequence is the translation project's ``emutest/scenario.py`` one, reduced to what
this project needs: press A through the logos/title, stop at the first message window, press B
through the story recap until the field's place label appears, then B for the priest's
blessing.  Progress is read from the pane text logger (``tools/emu/textlog.py``), not from
fixed timings, so a slow shader compile cannot desynchronise the run.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from . import fixtures as F


def _textrec():
    from tools.emu import textlog
    return textlog


class Game:
    """One booted emulator + pane-text recorder, closed on context exit."""

    def __init__(self, name: str, mod: str | None, save: str = "user_citra",
                 gpu: str = "opengl", rom: Path | None = None):
        from tools.emu import extras
        self.name = name
        self.dir = F.OUT / name / "run"
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True)
        settings = {"frame_limit": "0"}
        # OpenGL by default: Vulkan crashes the emulator at boot on this machine's driver
        settings["graphics_api"] = {"vulkan": "2", "opengl": "1", "software": "0"}[gpu]
        self.emu = extras.make_emu(str(rom or F.RETAIL_ROM), mod=mod, save=save,
                                   workdir=str(self.dir / "emulator"), settings=settings)
        self.rec = None
        self.text_ok = False
        self.crash: str | None = None
        self.log: list[str] = []

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self):
        try:
            F.kill_emulators()
            self.emu.start()
        except Exception:
            self.emu.stop()          # never leave a half-started Azahar behind
            raise
        return self

    def __exit__(self, *exc):
        try:
            if self.rec:
                self.rec.stop()
        finally:
            self.emu.stop()
        return False

    def note(self, text: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {text}"
        self.log.append(line)
        print("   " + text, flush=True)

    def shot(self, tag: str) -> str:
        path = self.dir / f"{tag}.png"
        ok = self.emu.shot(str(path))
        if not ok:
            raise RuntimeError(f"screenshot failed: {path}")
        self.note(f"shot {tag}")
        return str(path)

    # -- text recorder -----------------------------------------------------
    def start_text(self) -> None:
        """Attach the pane-text recorder on its **own** RPC socket.

        The ring lives at the end of the UI heap, which the game declares as
        ``base + size``.  On this emulator profile that address is sometimes *outside the
        mapped linear heap* (the heap object's declared size reaches past the last mapped
        page).  Then the host cannot write the ring either, and the game's logger never gets a
        usable buffer.  Probe with a pattern first: a dead ring must not turn into a silent
        "the talk produced no text" failure, the cases fall back to screenshots.
        """
        from AzaharRPC import AzaharRPC
        rpc = AzaharRPC(timeout=2, retries=2)
        rec = _textrec().TextRecorder(rpc, self.emu, str(self.dir), shots=False)
        probe = b"X3RING\0\0"
        try:
            ring = _textrec().ring_address(rpc.read_memory)
            rpc.write_memory(ring, probe)
            ok = rpc.read_memory(ring, len(probe)) == probe
        except Exception as exc:                 # noqa: BLE001 - any RPC/heap problem
            self.note(f"text log unavailable: {exc}")
            ok = False
        if not ok:
            self.note("text log ring is outside the writable linear heap - screenshots only")
            self.text_ok = False
            return
        self.rec = rec
        self.text_ok = True
        self.rec.start()

    def events(self, since: int = 0) -> list[dict]:
        return [e for e in (self.rec.events[since:] if self.rec else []) if "seq" in e]

    def seen(self, name: str, since: int = 0) -> bool:
        """A text event for pane ``name``, skipping the burst that builds a layout."""
        ev = self.events(since)
        per_frame: dict[int, int] = {}
        for e in ev:
            per_frame[e["frame"]] = per_frame.get(e["frame"], 0) + 1
        return any(e.get("name") == name and per_frame[e["frame"]] < 12 for e in ev)

    def find(self, needle: str, since: int = 0) -> list[dict]:
        return [e for e in self.events(since)
                if needle in e.get("text", "") or needle in e.get("shown", "")]

    # -- play --------------------------------------------------------------
    def press(self, button: str, after: float = 1.0) -> None:
        if self.crash:
            return
        self.crash = self.emu.press(button, after=after) or self.emu.crashed()

    def press_watch(self, button: str, needle: str, gap: float = 1.2) -> bool:
        """Press, then poll fast so a message window is caught *before* the next press.

        The blind 1.4 s press loop can dismiss a prompt within the same second it appears
        (the recap question is a one-screen message).  This presses, then watches the pane log
        every 0.1 game-second and returns True as soon as ``needle`` is typed (partial text
        counts: the window is already on screen and the screenshot still shows the edit).
        """
        if self.crash:
            return False
        short = needle[:max(2, len(needle) // 3)]
        self.crash = self.emu.press(button, after=0.25) or self.emu.crashed()
        end = self.emu.game_time() + gap
        while not self.crash and self.emu.game_time() < end:
            if self.find(needle) or self.find(short):
                return True
            self.crash = self.emu.wait_game(self.emu.game_time() + 0.1)
        return bool(self.find(needle) or self.find(short))

    def wait(self, seconds: float) -> None:
        if not self.crash:
            self.crash = self.emu.wait_game(self.emu.game_time() + seconds)

    def boot_to_field(self) -> dict:
        """Title -> Continue -> slot 1 -> skip recap -> field (fixed game-second stages).

        This is the translation project's own boot (``azctl.py boot 1``): A through the
        title/Continue/save-select, B through the recap and the priest's blessing.  It does
        **not** read the text log, so it still works on boots where the log ring happens to
        land outside the mapped heap.
        """
        self.crash = self.emu.wait_game(6) or self.emu.crashed()
        self.start_text()
        end = self.emu.game_time() + 40
        while not self.crash and self.emu.game_time() < end:
            self.press("A", after=1.4)
        end = self.emu.game_time() + 25
        while not self.crash and self.emu.game_time() < end:
            self.press("B", after=0.8)
        self.wait(2.0)
        if self.text_ok:
            self.wait_idle(1.0, limit=8.0)
        self.after_boot = len(self.rec.events) if self.rec else 0
        return self.status()

    def wait_idle(self, quiet: float = 1.5, limit: float = 15.0) -> None:
        """Wait until no new pane text has arrived for ``quiet`` game seconds."""
        start = self.emu.game_time()
        last, stable = len(self.rec.events) if self.rec else 0, 0.0
        while not self.crash and stable < quiet and self.emu.game_time() - start < limit:
            self.crash = self.emu.wait_game(self.emu.game_time() + 0.25)
            now = len(self.rec.events) if self.rec else 0
            stable = 0.0 if now != last else stable + 0.25
            last = now

    def find_live(self, text: str) -> int | None:
        """First copy of ``text`` in the *live* UI heap (not the resource cache at 0x31/0x32)."""
        return self.emu.find_utf16(text, start=0x33000000, end=0x34000000)

    def wait_live(self, text: str, seconds: float = 6.0) -> int | None:
        """Poll for ``text`` in the live UI heap; the game types some lines out character by
        character, so a later, longer string is a reliable "this window is up" proof."""
        end = self.emu.game_time() + seconds
        while not self.crash and self.emu.game_time() < end:
            addr = self.find_live(text)
            if addr:
                return addr
            self.crash = self.emu.wait_game(self.emu.game_time() + 0.2)
        return self.find_live(text)

    def talk(self, settle: float = 4.0) -> list[dict]:
        """One A press starts the interaction; return the text it produced.

        Retries only when the text log is alive (a swallowed press is visible as "no text");
        without it the caller judges by screenshot, so pressing again would skip the window.
        """
        before = 0
        for _attempt in range(3):
            before = len(self.rec.events) if self.rec else 0
            self.press("A", after=0.6)
            if self.text_ok:
                end = self.emu.game_time() + settle
                while not self.crash and self.emu.game_time() < end:
                    if self.events(before):
                        break
                    self.crash = self.emu.wait_game(self.emu.game_time() + 0.1)
                if self.events(before):
                    break
                self.wait(1.5)
            else:
                self.wait(2.0)
                break
        self.wait(0.5)
        return self.events(before) if self.rec else []

    def status(self) -> dict:
        stats = self.emu.screen_stats() or {}
        return {
            "game_time": round(self.emu.game_time(), 2),
            "hook_alive": self.emu.hook_alive(),
            "text_log": self.text_ok,
            "crash": self.crash or self.emu.crashed(),
            "screen": {k: round(v, 1) if isinstance(v, float) else v
                       for k, v in stats.items()},
            "records": self.rec.count if self.rec else 0,
        }

    def finish(self, extra: dict | None = None) -> dict:
        result = {"case": self.name, "finished": F.stamp(), **self.status(),
                  "log": self.log}
        if isinstance(extra, dict):
            result.update(extra)
        F.json_dump(self.dir / "result.json", result)
        return result


# --------------------------------------------------------------------------- cases
def boot_to_title(rom: Path, mod: str | None, name: str, seconds: float = 120) -> dict:
    """`python -m tools.emu boot`: title-screen verdict + screenshot + JSON (retail-quality)."""
    F.kill_emulators()
    log = F.WORK / f"{name}_boot.log"
    shot = F.OUT / name / "title.png"
    args = ["-m", "tools.emu", "boot", str(rom), "--seconds", str(seconds), "--shot", str(shot)]
    if mod:
        args += ["--mod", str(mod)]
    rc, text = F.python(args, log=log)
    report = {}
    if shot.with_suffix(".json").is_file():
        report = json.loads(shot.with_suffix(".json").read_text(encoding="utf-8"))
    return {"case": name, "exit": rc, "report": report, "screenshot": str(shot)
            if shot.is_file() else None, "log": str(log), "output": text}


def case_empty() -> dict:
    """Empty mod: Luma folder and a rebuilt .3ds both reach the title screen."""
    ws = F.workspace("empty")
    rc_l, out_l, dir_l = F.export(ws, "empty", target="luma")
    rc_3, out_3, dir_3 = F.export(ws, "empty_3ds", target="3ds")
    result = {
        "luma_export": {"exit": rc_l, "out": str(dir_l)},
        "3ds_export": {"exit": rc_3, "out": str(dir_3)},
        "luma": boot_to_title(F.RETAIL_ROM, str(dir_l / "luma"), "empty_luma"),
        "3ds": boot_to_title(dir_3 / "3ds" / "DQXI_modded.3ds", None, "empty_3ds"),
    }
    F.json_dump(F.OUT / "empty" / "result.json", result)
    return result


def case_empty_save(movie: bool = True) -> dict:
    """The empty mod with a game save installed: title -> Continue -> field, using a movie.

    The empty mod has no test input hook (it is byte-identical to retail), so input must come
    from an Azahar input movie.  The movie is generated from game seconds:
    START opens the title menu, A picks "play", A loads slot 1, B closes the recap/blessing.
    """
    from tools.emu import extras
    ws = F.workspace("empty_save")
    rc, out, dir_l = F.export(ws, "empty_save", target="luma")
    movie_path = F.WORK / "empty_save.ctm"
    m = extras.new_movie()
    for spec in ("430:0.15:START", "445:0.15:A", "452:0.15:A",
                 "460:0.15:B", "467:0.15:B", "474:0.15:B"):
        m.spec(spec)
    m.write(str(movie_path))
    name = "empty_save"
    d = F.OUT / name / "run"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    e = extras.make_emu(str(F.RETAIL_ROM), mod=str(dir_l / "luma"), save="user_citra",
                        movie=str(movie_path), workdir=str(d / "emulator"),
                        settings={"frame_limit": "0"})
    shots = []
    try:
        e.start()
        for t in (440, 448, 458, 470, 485):
            if e.game_time() < t:
                e.wait_game(t)
            p = d / f"t{t}.png"
            if e.shot(str(p)):
                shots.append(str(p))
        stats = e.screen_stats() or {}
        crash = e.crashed()
        result = {"case": name, "exit_export": rc, "rom": str(F.RETAIL_ROM),
                  "mod": str(dir_l / "luma"), "movie": str(movie_path),
                  "game_time": round(e.game_time(), 2), "shots": shots,
                  "screen": stats, "crash": crash,
                  "note": "input movie, because the empty mod has no test input hook"}
    finally:
        e.stop()
    F.json_dump(d / "result.json", result)
    return result


def case_text(marker: str = "X3 TEXT EDIT OK 2468") -> dict:
    """One dialogue line (the save-load recap prompt) replaced through tools/text_tool."""
    ws = F.workspace("text")
    F.add_code(ws)
    edit = F.stage_text(ws, "ui/title/title_msg", {22: marker})
    rc, out, dir_l = F.export(ws, "text", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("text", str(F.luma_title_dir(dir_l))) as g:
        g.crash = g.emu.wait_game(6) or g.emu.crashed()
        g.start_text()
        # Detect the prompt in guest RAM, not only in the pane log: the log ring can land
        # outside the mapped linear heap on this profile, but the live pane copies are in the
        # normal 0x30000000 region and the RPC scanner reads them reliably.
        hit_addr = None
        for _ in range(120):
            if g.crash:
                break
            # only the dynamic UI heap: the edited bank is also cached in RAM from boot, so a
            # plain whole-RAM scan finds the *resource* while the logo is still playing
            hit_addr = g.emu.find_utf16(marker, start=0x33000000, end=0x34000000)
            if hit_addr:
                break
            g.press("A", after=1.2)
        g.shot("recap")
        hit = ([{"address": hit_addr, "text": marker}] if hit_addr else []) + g.find(marker)
        # continue into the field, so the run also proves the edit did not break the boot
        for _ in range(25):
            if g.crash or (g.text_ok and g.seen("txt_place")):
                break
            g.press("B", after=0.8)
        g.wait(1.0)
        g.shot("field")
        result = g.finish({"marker": marker, "edit": edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "marker_events": hit})
    return result


def case_script_source() -> dict:
    """Readable source tier: talking starts the book message instead of the church menu."""
    ws = F.workspace("script_src")
    F.add_code(ws)
    edit = F.stage_script(ws, "b011", "source")
    rc, out, dir_l = F.export(ws, "script_src", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("script_src", str(F.luma_title_dir(dir_l))) as g:
        g.boot_to_field()
        g.shot("field")
        ev = g.talk(settle=4.0)
        book = g.wait_live("巻きついた", 4.0)
        g.shot("talk")
        result = g.finish({"edit": edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "after_talk": ev[:40],
                           "text_after_talk": sum(1 for e in ev if e.get("text")),
                           "book_live": book,
                           "book_text": [e for e in ev if "この" in e.get("text", "")]})
    return result


def case_script_asm() -> dict:
    """Assembly tier: talking opens the shop menu (a different visible behaviour)."""
    ws = F.workspace("script_asm")
    F.add_code(ws)
    edit = F.stage_script(ws, "b011", "asm")
    rc, out, dir_l = F.export(ws, "script_asm", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("script_asm", str(F.luma_title_dir(dir_l)), gpu="opengl") as g:
        g.boot_to_field()
        g.shot("field")
        ev = g.talk(settle=4.0)
        shop_live = g.wait_live("かいにきた", 5.0)
        g.shot("shop")
        for i in range(2):
            g.press("DOWN", after=1.0)
            g.shot(f"shop_down{i + 1}")
        result = g.finish({"edit": edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "shop_live": shop_live,
                           "after_talk": ev[:60]})
    return result


def case_table(price: int = 1234567) -> dict:
    """Table edit visible in the shop: herb buy price 8 -> 1,234,567 + the shop record.

    The script edit (assembly tier) opens the shop, the fieldcmn shop record is made to sell
    the medicinal herb, and tools/table_edit changes its buy_price.  The shop screen then has
    to print the new number.
    """
    ws = F.workspace("table")
    F.add_code(ws)
    table_edit = F.stage_table(ws, "syscmn/item.json", "#0", "buy_price", price)
    shop_edit = F.stage_shop_pack(ws, shop=68, first_item=0)
    script_edit = F.stage_script(ws, "b011", "asm")
    rc, out, dir_l = F.export(ws, "table", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("table", str(F.luma_title_dir(dir_l)), gpu="opengl") as g:
        g.boot_to_field()
        g.shot("field")
        before = len(g.rec.events) if g.rec else 0
        g.talk(settle=4.0)
        g.shot("shop")
        # the shop's first menu is buy / sell / quit; the chosen mode then shows a greeting
        # message and, after that is acknowledged, the goods list
        g.press("A", after=2.0)
        g.wait(1.0)
        g.shot("shop_greeting")
        g.press("A", after=2.0)
        g.wait(1.0)
        price_addr = g.wait_live(str(price), 5.0)
        name_addr = g.wait_live("やくそう", 2.0)
        g.shot("shop_list")
        for i in range(3):
            g.press("DOWN", after=1.2)
            g.shot(f"shop_item{i + 1}")
        ev = g.events(before)
        price_hits = [e for e in ev if str(price) in e.get("text", "")]
        name_hits = [e for e in ev if "やくそう" in e.get("text", "")]
        # fall back to guest memory: the shop screen keeps the printed price in pane text
        result = g.finish({"price": price, "table_edit": table_edit, "shop_edit": shop_edit,
                           "script_edit": script_edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "after_talk": ev[:80],
                           "price_live": price_addr, "name_live": name_addr,
                           "price_events": price_hits, "herb_events": name_hits})
    return result


def case_text_grow(marker: str = "X5 GROWN TEXT LINE 2468 - longer than the retail slot") -> dict:
    """A dialogue line grown past its retail slot (BXON string relocation).

    Same screen and detector as ``case_text``; the only difference is that the new
    line is longer than the Japanese one it replaces, so ``tools.bxon`` has to
    move the string block, append it and repoint the table.  Finding the marker in
    the live UI heap proves the game accepted the relocated bank.
    """
    ws = F.workspace("text_grow")
    F.add_code(ws)
    edit = F.stage_text(ws, "ui/title/title_msg", {22: marker})
    if not edit.get("bank_size", 0) > edit.get("bank_original_size", 0):
        raise RuntimeError(f"the text edit did not grow the bank: {edit}")
    rc, out, dir_l = F.export(ws, "text_grow", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("text_grow", str(F.luma_title_dir(dir_l))) as g:
        g.crash = g.emu.wait_game(6) or g.emu.crashed()
        g.start_text()
        hit_addr = None
        for _ in range(120):
            if g.crash:
                break
            hit_addr = g.emu.find_utf16(marker, start=0x33000000, end=0x34000000)
            if hit_addr:
                break
            g.press("A", after=1.2)
        g.shot("recap")
        hit = ([{"address": hit_addr, "text": marker}] if hit_addr else []) + g.find(marker)
        for _ in range(25):
            if g.crash or (g.text_ok and g.seen("txt_place")):
                break
            g.press("B", after=0.8)
        g.wait(1.0)
        g.shot("field")
        result = g.finish({"marker": marker, "edit": edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "marker_events": hit})
    return result


def case_table_grow(price: int = 1987654) -> dict:
    """A grown item table visible in a shop: one added row, sold as the first good.

    ``tools.bxon_grow`` appends a row, the shop record points its first goods slot
    at that row's index, and the row's ``buy_price`` is a number that exists
    nowhere in the retail table.  The shop printing that number proves the game
    read the grown array (and not only a shifted copy of the retail rows).

    EXPECTED TO FAIL - research case only. Items are addressed by row index and 27
    functions reject an index >= 2875; the save keeps a 2880-bit per-item mask
    (orchestration/done/X6_item_table_growth.md). Use ``case_item_new`` instead.
    """
    ws = F.workspace("table_grow")
    # Growing items takes three consistent changes (tools.bxon_grow.grow_items): the item
    # table, item_kana_order.bxon and the engine's expected item count in code.bin. The new
    # row is appended (no retail index moves) with a fresh, unique id (retail ids are unique).
    table_edit = F.stage_item_grow(ws, price, item_id=2700)  # unused id inside the retail range
    shop_edit = F.stage_shop_pack(ws, shop=68, first_item=table_edit["new_row"])
    script_edit = F.stage_script(ws, "b011", "asm")
    rc, out, dir_l = F.export(ws, "table_grow", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("table_grow", str(F.luma_title_dir(dir_l)), gpu="opengl") as g:
        g.boot_to_field()
        g.shot("field")
        before = len(g.rec.events) if g.rec else 0
        g.talk(settle=4.0)
        g.shot("shop")
        g.press("A", after=2.0)
        g.wait(1.0)
        g.shot("shop_greeting")
        g.press("A", after=2.0)
        g.wait(1.0)
        price_addr = g.wait_live(str(price), 5.0)
        name_addr = g.wait_live("やくそう", 2.0)
        g.shot("shop_list")
        for i in range(3):
            g.press("DOWN", after=1.2)
            g.shot(f"shop_item{i + 1}")
        ev = g.events(before)
        price_hits = [e for e in ev if str(price) in e.get("text", "")]
        result = g.finish({"price": price, "table_edit": table_edit, "shop_edit": shop_edit,
                           "script_edit": script_edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "after_talk": ev[:80],
                           "price_live": price_addr, "name_live": name_addr,
                           "price_events": price_hits})
    return result


def case_item_new(price: int = 1357924) -> dict:
    """A new item in a placeholder row (``id == 0``), sold as the shop's first good.

    The item table keeps its retail row count, so none of the engine's per-item limits
    apply (contrast case_table_grow). The new row copies the herb with a fresh id and a
    price that exists nowhere in retail; the shop printing it proves the game uses the row.
    """
    ws = F.workspace("item_new")
    F.add_code(ws)
    name = "テストのやくそう"  # longer than the herb's name and found nowhere in retail
    item_edit = F.stage_item_placeholder(ws, price, item_id=2700, name=name)
    shop_edit = F.stage_shop_pack(ws, shop=68, first_item=item_edit["new_row"])
    script_edit = F.stage_script(ws, "b011", "asm")
    rc, out, dir_l = F.export(ws, "item_new", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("item_new", str(F.luma_title_dir(dir_l)), gpu="opengl") as g:
        g.boot_to_field()
        g.shot("field")
        g.talk(settle=4.0)
        g.press("A", after=2.0)
        g.wait(1.0)
        g.press("A", after=2.0)
        g.wait(1.0)
        price_addr = g.wait_live(str(price), 5.0)
        name_addr = g.wait_live(name, 2.0)
        g.shot("shop_list")
        result = g.finish({"price": price, "item_edit": item_edit, "shop_edit": shop_edit,
                           "name_live": name_addr,
                           "script_edit": script_edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "price_live": price_addr})
    return result


def case_native(code_ips_only: bool = True) -> dict:
    """Native code via code.ips: the test input hook, applied exactly as Luma does."""
    ws = F.workspace("native")
    F.add_code(ws)
    rc, out, dir_l = F.export(ws, "native", target="luma", code="ips")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    title_dir = F.luma_title_dir(dir_l)
    ips = (title_dir / "code.ips").read_bytes()
    applied = F.apply_code_ips(ips)
    equal = applied == F.test_code()
    if not equal:
        raise RuntimeError("code.ips does not reproduce the test executable")
    moddir = F.luma_code_bin_mod("native_as_luma", applied)
    with Game("native", str(moddir)) as g:
        g.boot_to_field()
        g.shot("field")
        hook = g.emu.hook_alive()
        ev = g.talk(settle=4.0)
        menu_live = g.wait_live("おいのり", 4.0)
        g.shot("talk")
        result = g.finish({"ips_bytes": len(ips), "ips_reproduces_code": equal,
                           "hook_alive": hook, "menu_live": menu_live,
                           "luma_export": {"exit": rc, "out": str(dir_l),
                                           "title_dir": str(title_dir)},
                           "after_talk": ev[:40]})
    return result


def case_script_load() -> dict:
    """Readable source tier at scene load: a new function started from OnBeginScene.

    This is the edit that used to crash at/near boot: the recompiled
    statement-position call stored its result in register -1, which this VM's
    resume path writes through.  The new function starts the game's own
    ``common.ShopEvent``; the case proves the pack loaded and the scene ran by
    finding the field's place label in the live UI heap (the shop menu itself is
    not asserted: a scene-load UI start is not guaranteed to be on screen by the
    time the save finishes loading).
    """
    ws = F.workspace("script_load")
    F.add_code(ws)
    edit = F.stage_script(ws, "b011", "source_load")
    rc, out, dir_l = F.export(ws, "script_load", target="luma", code="bin")
    if rc:
        raise RuntimeError(f"export failed:\n{out}")
    with Game("script_load", str(F.luma_title_dir(dir_l)), gpu="opengl") as g:
        g.crash = g.emu.wait_game(6) or g.emu.crashed()
        g.start_text()
        shop_live = None
        # A through the logos/title/Continue/save load.  Poll before every press:
        # the scene-load event opens the shop, and pressing A/B after that would
        # select a menu entry and hide the label the case asserts on.
        end = g.emu.game_time() + 45
        while not g.crash and g.emu.game_time() < end:
            shop_live = g.find_live("かいにきた")
            if shop_live:
                break
            g.press("A", after=1.4)
        # B through the story recap and the priest's blessing, still polling.
        end = g.emu.game_time() + 30
        while not g.crash and not shop_live and g.emu.game_time() < end:
            shop_live = g.find_live("かいにきた")
            if shop_live:
                break
            g.press("B", after=0.8)
        if not shop_live:
            shop_live = g.wait_live("かいにきた", 6.0)
        g.wait(1.0)
        shot = g.shot("scene_event")
        result = g.finish({"edit": edit,
                           "luma_export": {"exit": rc, "out": str(dir_l)},
                           "shop_live": shop_live,
                           "place_live": g.find_live("イシの村"),
                           "scene_shot": shot})
    return result


CASES = {
    "empty": case_empty,
    "empty_save": case_empty_save,
    "text": case_text,
    "script_src": case_script_source,
    "script_load": case_script_load,
    "script_asm": case_script_asm,
    "table": case_table,
    "text_grow": case_text_grow,
    "table_grow": case_table_grow,
    "item_new": case_item_new,
    "native": case_native,
}
