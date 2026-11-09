"""Fixtures for the opt-in emulator tests: build one mod per proof, from the real tools.

Everything is staged into ``build/emu_test/x3/<case>/`` so the user's ``mod/`` workspace is
never touched.  The staging functions call the same library entry points as the CLIs
(``tools/export_mod.stage_member``, ``tools.text_tool.rebuild_bank``, ``tools.table_edit.Table``),
so a test exercises the code path a modder uses, not a copy of it.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.emu import testhook, textlog  # noqa: E402

WORK = REPO / "build" / "emu_test" / "x3"
OUT = REPO / "out" / "emu" / "x3"
RETAIL_CODE = REPO / "original" / "exefs" / "code.decompressed.bin"
RETAIL_ROM = REPO / "build" / "DQXI.3ds"
SCRIPTS = REPO / "game_assets" / "scripts" / "packs" / "script"

# The same test-only executable every case uses: the translation project's input hook plus the
# pane-text logger.  Both are emulator-only and never exported; both are ARMv6K/VFPv2-safe (the
# exporter checks the changed words again, see tools/check_armv6k.py).
TEST_CODE = WORK / "code_test.bin"


def sha256(path: Path | bytes) -> str:
    h = hashlib.sha256()
    if isinstance(path, (bytes, bytearray)):
        h.update(path)
    else:
        h.update(Path(path).read_bytes())
    return h.hexdigest()


def run(args: list[str], log: Path | None = None, timeout: int = 900) -> tuple[int, str]:
    """Run a project tool; keep the complete output for the report."""
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "w", encoding="utf-8") as fp:
            fp.write("$ " + " ".join(args) + "\n")
            fp.flush()
            p = subprocess.run(args, cwd=REPO, stdout=fp, stderr=subprocess.STDOUT,
                               timeout=timeout)
        text = log.read_text(encoding="utf-8", errors="replace")
    else:
        p = subprocess.run(args, cwd=REPO, capture_output=True, text=True, timeout=timeout)
        text = (p.stdout or "") + (p.stderr or "")
    return p.returncode, text


def python(args: list[str], log: Path | None = None, timeout: int = 900) -> tuple[int, str]:
    return run([sys.executable, *args], log=log, timeout=timeout)


# --------------------------------------------------------------------------- test executable
_TEST_SHA: str | None = None


def test_code() -> bytes:
    """Retail code + input hook + text log, built once per process (the patches are cheap)."""
    global _TEST_SHA
    if TEST_CODE.is_file():
        data = TEST_CODE.read_bytes()
        built = textlog.apply(testhook.apply(RETAIL_CODE.read_bytes()))
        if data == built:                 # cache is current: no stale experiment
            _TEST_SHA = sha256(data)
            return data
    code = textlog.apply(testhook.apply(RETAIL_CODE.read_bytes()))
    TEST_CODE.parent.mkdir(parents=True, exist_ok=True)
    TEST_CODE.write_bytes(code)
    _TEST_SHA = sha256(code)
    return code


def test_code_sha() -> str:
    test_code()          # ensure it exists
    return _TEST_SHA or sha256(TEST_CODE)


# --------------------------------------------------------------------------- workspaces
def workspace(name: str) -> Path:
    """A clean mod workspace (``mod.json`` + nothing else) under build/emu_test/x3/."""
    ws = WORK / name
    if ws.exists():
        shutil.rmtree(ws)
    (ws / "romfs").mkdir(parents=True)
    (ws / "code").mkdir()
    (ws / "mod.json").write_text(json.dumps({
        "name": f"X3 {name}",
        "version": "0.0",
        "author": "X3_boot_tests",
        "description": "emulator proof case; never exported to hardware",
    }, indent=2) + "\n", encoding="utf-8")
    return ws


def add_code(ws: Path, code: bytes | None = None) -> Path:
    src = ws / "code" / "code.bin"
    src.write_bytes(code if code is not None else test_code())
    return src


def export(ws: Path, name: str, target: str = "luma", code: str = "ips",
           extra: list[str] | None = None) -> tuple[int, str, Path]:
    """Run tools/export_mod.py for one workspace, as a modder would."""
    out = OUT / name
    if out.exists():
        shutil.rmtree(out)
    log = WORK / f"{name}_export.log"
    args = ["tools/export_mod.py", "--mod", str(ws), "--out", str(out),
            "--target", target, "--code", code]
    rc, text = python(args + (extra or []), log=log)
    return rc, text, out


def luma_title_dir(out: Path) -> Path:
    return out / "luma" / "titles" / "0004000000199200"


# --------------------------------------------------------------------------- tool edits
def stage_table(ws: Path, table: str, row: str, field: str, value: int) -> dict:
    """One numeric field, through tools.table_edit.Table + export_mod.stage_member."""
    from tools.table_edit import Table
    from tools.export_mod import stage_member

    t = Table(table)
    spec = t.field(field)
    r = t.find(row)
    before = t.read(r, spec)
    t.write(r, spec, value)
    after = Table(table, bytes(t.raw)).read(r, spec)
    out = WORK / ws.name / "edits" / Path(t.name).with_suffix(".bxon")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(t.raw))
    pack, member = pack_of_table(table)
    info = stage_member(pack, member, out, ws, work_dir=WORK / "staged")
    return {"table": table, "row": row, "field": field, "before": before,
            "after": after, **info}


def pack_of_table(table: str) -> tuple[str, str]:
    from tools.table_edit import pack_of
    return pack_of(table)


def stage_text(ws: Path, bank_key: str, new_texts: dict[int, str]) -> dict:
    """Replace strings in a text bank (tools.text_tool), staged as its RomFS pack."""
    from tools import text_tool
    from tools.export_mod import stage_member

    bank = text_tool.import_bank(bank_key)
    doc = bank.as_json()
    changed = []
    for entry in doc["entries"]:
        if entry["id"] in new_texts:
            changed.append({"id": entry["id"], "before": entry["text"],
                            "after": new_texts[entry["id"]]})
            entry["text"] = new_texts[entry["id"]]
    if not changed:
        raise ValueError(f"none of {sorted(new_texts)} is an entry of {bank_key}")
    texts = text_tool.texts_from_json(doc, bank)
    built = text_tool.rebuild_bank(bank.data, texts)
    out = WORK / ws.name / "edits" / f"{bank.member}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(built)
    info = stage_member(bank.pack, bank.member, out, ws, work_dir=WORK / "staged")
    return {"bank": bank_key, "changed": changed,
            "bank_original_size": len(bank.data), "bank_size": len(built), **info}


def stage_table_grow(ws: Path, table: str, field: str, value: int,
                     rows: int = 1, fields: dict | None = None,
                     source_row: int = -1, at: int = -1,
                     live_row: int = -1, live_value: int | None = None) -> dict:
    """Add rows through ``tools.bxon_grow`` and set numeric fields on the first new row.

    ``value`` goes into the *new* row, so finding it in the game proves the game read
    the grown array, not just a shifted copy of the retail records.  ``fields`` sets
    further numeric fields of the same row (for example a fresh ``id``).
    ``source_row`` is the retail row the new one is copied from (-1 = last non-empty).
    ``live_row``/``live_value`` also write a *retail* row in the same grown file; use
    them for engine systems that only index records they already knew about (the shop
    does: its stock ids go through a separate category table).
    """
    from tools.bxon_grow import grow_table, pointer_offsets_from_schema
    from tools.export_mod import stage_member
    from tools.table_edit import Table, pack_of

    source = REPO / "game_data" / "packs" / Path(table).with_suffix(".bxon")
    before = source.read_bytes()
    row_size, pointers = pointer_offsets_from_schema(table)
    grown = grow_table(before, row_size, pointers, rows=rows, source_row=source_row,
                       at=at)
    t = Table(table, grown)
    spec = t.field(field)
    first_new = at if at >= 0 else len(t) - rows
    t.write(first_new, spec, value)
    for name, number in (fields or {}).items():
        t.write(first_new, t.field(name), number)
    live_after = None
    if live_row >= 0 and live_value is not None:
        t.write(live_row, spec, live_value)
        live_after = Table(table, bytes(t.raw)).read(live_row, spec)
    after = Table(table, bytes(t.raw)).read(first_new, spec)
    out = WORK / ws.name / "edits" / Path(table).with_suffix(".bxon")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(t.raw))
    pack, member = pack_of(table)
    info = stage_member(pack, member, out, ws, work_dir=WORK / "staged")
    return {"table": table, "rows_before": len(t) - rows, "rows_after": len(t),
            "new_row": first_new, "field": field, "value": after,
            "live_row": live_row, "live_value": live_after,
            "original_size": len(before), "size": len(t.raw), **info}


def stage_item_grow(ws: Path, price: int, item_id: int, source_row: int = 0) -> dict:
    """Add one item row the way the engine accepts it, and stage everything into ``ws``.

    item.bxon gets the row (copy of ``source_row``, new ``id`` and ``buy_price``),
    item_kana_order.bxon gets its index, and the test code.bin gets the new expected item
    count (see tools/bxon_grow.py ``grow_items``).
    """
    from tools.bxon_grow import grow_items
    from tools.export_mod import stage_member
    from tools.table_edit import Table

    packs = REPO / "game_data" / "packs" / "syscmn"
    item, kana, code, rows = grow_items((packs / "item.bxon").read_bytes(),
                                        (packs / "item_kana_order.bxon").read_bytes(),
                                        test_code(), rows=1, source_row=source_row)
    t = Table("syscmn/item.json", item)
    new_row = rows[0]
    t.write(new_row, t.field("id"), item_id)
    t.write(new_row, t.field("buy_price"), price)
    edits = WORK / ws.name / "edits"
    edits.mkdir(parents=True, exist_ok=True)
    (edits / "item.bxon").write_bytes(bytes(t.raw))
    (edits / "item_kana_order.bxon").write_bytes(kana)
    stage_member("/syscmn.pack", "item.bxon", edits / "item.bxon", ws, work_dir=WORK / "staged")
    info = stage_member("/syscmn.pack", "item_kana_order.bxon", edits / "item_kana_order.bxon",
                        ws, work_dir=WORK / "staged")
    add_code(ws, code)
    return {"table": "syscmn/item.json", "rows_before": new_row, "rows_after": len(t),
            "new_row": new_row, "id": item_id, "value": price,
            "item_count_patched": len(t), **{"pack": info["pack"], "mod_file": info["mod_file"]}}


def stage_item_placeholder(ws: Path, price: int, item_id: int, dest_row: int = 2690,
                           source_row: int = 0, name: str | None = None) -> dict:
    """Add a new item by claiming a placeholder row (``id == 0``) - no row count change.

    The row becomes a copy of ``source_row`` (pointers re-aimed, so it shares the source's
    name strings) with a fresh ``id`` and ``buy_price``. See tools/bxon_grow.py
    ``claim_placeholder``.
    """
    from tools.bxon_grow import claim_placeholder, pointer_offsets_from_schema
    from tools.export_mod import stage_member
    from tools.table_edit import Table

    item = (REPO / "game_data" / "packs" / "syscmn" / "item.bxon").read_bytes()
    row_size, pointers = pointer_offsets_from_schema("syscmn/item.json")
    probe = Table("syscmn/item.json", item)
    claimed = claim_placeholder(item, row_size, pointers, source_row, dest_row,
                                probe.field("id")["offset"], item_id)
    t = Table("syscmn/item.json", claimed)
    t.write(dest_row, t.field("buy_price"), price)
    if name is not None:  # any length: appended string block (Table.write_string)
        t.write_string(dest_row, t.field("name"), name)
    out = WORK / ws.name / "edits" / "item.bxon"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(t.raw))
    info = stage_member("/syscmn.pack", "item.bxon", out, ws, work_dir=WORK / "staged")
    return {"table": "syscmn/item.json", "new_row": dest_row, "id": item_id, "value": price,
            "rows": len(t), "same_rows": len(t) == Table("syscmn/item.json", item).__len__(),
            "size": len(t.raw), "original_size": len(item), "name": name, "mod_file": info["mod_file"]}


def stage_shop_pack(ws: Path, shop: int = 68, first_item: int = 0) -> dict:
    """Copy one shop record over every record and put ``first_item`` first.

    ``fieldcmn.pack:shop.bxon``: 179 records of 52 bytes from 0x2C (u8 kind, u8, 23 u16
    **item row indices** - not the item table's ``id`` field; row 0 is the medicinal herb,
    confirmed in-game on 2026-10-25).  The game picks the record from the NPC talked to, so
    a test build copies the wanted shop over all of them (the translation project's
    shopparam.py does the same).
    """
    from tools.export_mod import stage_member
    d = bytearray((REPO / "game_data" / "packs" / "fieldcmn" / "shop.bxon").read_bytes())
    count, first, size = struct.unpack_from("<I", d, 0x20)[0], 0x2C, 52
    if not 0 <= shop < count:
        raise ValueError(f"shop {shop} not in 0..{count - 1}")
    rec = bytearray(d[first + shop * size:first + (shop + 1) * size])
    struct.pack_into("<H", rec, 2, first_item)          # first goods slot
    for k in range(count):
        d[first + k * size:first + (k + 1) * size] = rec
    out = WORK / ws.name / "edits" / "shop.bxon"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(d)
    info = stage_member("/fieldcmn.pack", "shop.bxon", out, ws, work_dir=WORK / "staged")
    return {"shop": shop, "first_item": first_item, "records": count, **info}


SOURCE_TALK_TO_BOOK = """
        // X3 emulator test: talking to any character starts the book message instead of the
        // area's own talk handlers.  Test-only; never exported to hardware.
        if (type == 10) {
            StartEvent(IE_Z_M01_TAIJU);
            return;
        }
"""


def script_source(area: str = "b011") -> str:
    """The readable source with a guarded StartEvent inserted at the top of TrgRCommand."""
    text = (SCRIPTS / area / "script.decompiled.nut").read_text(encoding="utf-8")
    marker = "function TrgRCommand(type) {"
    if marker not in text:
        raise ValueError(f"{area}: TrgRCommand not found")
    return text.replace(marker, marker + SOURCE_TALK_TO_BOOK, 1)


SOURCE_SCENE_LOAD_EVENT = """\
    function X3SceneEvent() {
        // Previously crashing edit: new function + a statement-position call at
        // scene load. The shop event is the game's own StartUI(2)/WaitMenu()/EndUI(2)
        // pair, so the result is visible and unambiguous (the shop menu opens).
        StartEvent(common.ShopEvent);
    }
    function OnBeginScene() {
        StartEvent(X3SceneEvent);
"""


def script_source_load(area: str = "b011") -> str:
    """The readable source with a new function + StartEvent from OnBeginScene."""
    text = (SCRIPTS / area / "script.decompiled.nut").read_text(encoding="utf-8")
    marker = "    function OnBeginScene() {\n"
    if marker not in text:
        raise ValueError(f"{area}: OnBeginScene not found")
    return text.replace(marker, SOURCE_SCENE_LOAD_EVENT, 1)


ASM_SHOP_BODY = """\
    [   0] LOADINT      2     10   0   0
    [   1] EQ           2      2   1   0
    [   2] JZ           2      4   0   0
    [   3] PREPCALLK    2      5   0   3  // lit: 'StartEvent'
    [   4] GETK         4     16   0   0  // lit: 'common'
    [   5] GETK         4     17   4   0  // lit: 'ShopEvent'
    [   6] CALL         2      2   3   2
    [   7] RETURN     255      0   0   0
"""


def script_asm(area: str = "b011") -> str:
    """The annotated assembly with TrgRCommand's prologue replaced by a shop event.

    Talking to anyone starts ``common.ShopEvent`` (``StartUI(2, -1); WaitMenu(); EndUI(2)``),
    which is the game's own shop event, so the menu opens in a valid event context.  Same
    instruction count, so every relative jump in the 181-instruction function stays valid; the
    two new literals are appended to its literal table.  Non-talk trigger types return at once
    (this is a test build; it never ships).
    """
    text = (SCRIPTS / area / "script.nut").read_text(encoding="utf-8")
    start = text.index("  function 'TrgRCommand'")
    end = text.index("\n  }\n", start) + len("\n  }\n")
    block = text[start:end]

    lit_line = "    //   lit[15] = 0x08000010:'IE_C01_033_B090_F06'"
    if lit_line not in block:
        raise ValueError(f"{area}: unexpected literal table in TrgRCommand")
    block = block.replace(
        lit_line,
        lit_line + "\n    //   lit[16] = 0x08000010:'common'"
                  + "\n    //   lit[17] = 0x08000010:'ShopEvent'", 1)

    # replace ops 0..7 (the three prologue calls and the start of the type check)
    lines = block.split("\n")
    first = next(i for i, line in enumerate(lines)
                 if line.strip().startswith("[   0]"))
    lines[first:first + 8] = ASM_SHOP_BODY.rstrip("\n").split("\n")
    return text[:start] + "\n".join(lines) + text[end:]


def stage_script(ws: Path, area: str, tier: str) -> dict:
    """Compile one edited script and stage its RomFS pack (tools.script_build)."""
    from tools import script_build
    from tools.export_mod import stage_member

    original = (REPO / "game_data" / "packs" / "script" / area / "script.cnut").read_bytes()
    if tier == "source":
        text = script_source(area)
    elif tier == "source_load":
        text = script_source_load(area)
        tier = "source"
    elif tier == "asm":
        text = script_asm(area)
    else:
        raise ValueError(tier)
    data, info = script_build.build_text(text, original, tier)
    out = WORK / ws.name / "edits" / "script.cnut"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    stage = stage_member(f"script/{area}.pack", "script.cnut", out, ws,
                         work_dir=WORK / "staged")
    return {"area": area, "tier": tier, "compiled_size": len(data),
            "original_size": len(original), **info, **stage}


# --------------------------------------------------------------------------- native code
def apply_code_ips(ips: bytes) -> bytes:
    """Apply a Luma ``code.ips`` exactly as Luma does at boot."""
    from tools.export_mod import apply_ips
    return apply_ips(RETAIL_CODE.read_bytes(), ips)


def luma_code_bin_mod(name: str, code: bytes) -> Path:
    """The folder Azahar needs: a LayeredFS root with ``exefs/code.bin``.

    Luma itself applies ``code.ips`` to the retail executable at boot; this is the result.
    """
    root = WORK / name
    if root.exists():
        shutil.rmtree(root)
    (root / "exefs").mkdir(parents=True)
    (root / "exefs" / "code.bin").write_bytes(code)
    return root


# --------------------------------------------------------------------------- misc
def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def kill_emulators(wait: float = 3.0) -> None:
    """Stop this project's test Azahar and wait until it is really gone.

    ``az.kill_test_emulators`` (the harness's own) sends Stop-Process and returns immediately;
    starting the next instance before the old one has released the fixed RPC port makes the
    new one exit with code -1 a second or two after boot.  Only the portable test binary whose
    path is *this* data root is matched, never the user's own Azahar.
    """
    from tools.emu import extras
    ps = ("Get-Process azahar -ErrorAction SilentlyContinue | "
          f"Where-Object {{ $_.Path -eq '{str(extras.EXE).replace(chr(39), chr(39) * 2)}' }} | "
          "Stop-Process -Force")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
    end = time.time() + wait
    while time.time() < end:
        try:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq azahar.exe", "/NH"],
                                 capture_output=True, text=True).stdout
        except OSError:
            return
        if "azahar.exe" not in out.lower():
            return
        time.sleep(0.2)


def json_dump(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_env_note() -> dict:
    """What a reader needs to judge the run (hashes, tool versions, emulator)."""
    from tools.emu import extras
    return {
        "date": stamp(),
        "retail_rom": str(RETAIL_ROM), "retail_rom_sha256": sha256(RETAIL_ROM),
        "retail_code_sha256": sha256(RETAIL_CODE),
        "test_code_sha256": test_code_sha(),
        "emulator": str(extras.EXE),
        "data_root": str(extras.DATA_ROOT),
        "harness": str(extras.HARNESS),
        "python": sys.version,
    }
