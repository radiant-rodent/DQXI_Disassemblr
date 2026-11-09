#!/usr/bin/env python3
"""Generate the human-facing progress tracker for the DQXI 3DS project.

The design follows AnyPS5's progress page: plain tables (implemented / total / %),
a per-function coverage map, shields-style SVG badges, a raw ``progress.json``,
a one-point-per-day ``history.html``, and a live worker board.

Everything is written into ``progress/`` and is plain HTML/SVG/JSON with **no
network access, no external CSS and no JavaScript**. The generator is deliberately
defensive: a missing generated tree (``decomp/``, ``game_assets/``, ``build/``)
must produce zeros and "not generated yet" text, never a traceback. The dispatcher
calls this after every finished task, so one stale file must not break the board.

Usage:
    python tools/progress.py
    python tools/progress.py --reset-features   # restore progress/features.json
"""
from __future__ import annotations

import argparse
import ast
import html
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORC = ROOT / "orchestration"
OUT = ROOT / "progress"
GHIDRA = ROOT / "decomp" / "ghidra"
GAME_ASSETS = ROOT / "game_assets"

# Same subsystem grouping as tools/organize_ghidra.py. Keep this list in sync so
# progress.html and progress.svg agree with decomp/ghidra/by_subsystem/COVERAGE.md.
DOMAINS = [
    ("Audio", ("audio", "sound", "bgm", "voice", "se_", "music", "stream")),
    ("Battle", ("battle", "enemy", "damage", "skill", "attack", "turn", "monster", "boss")),
    ("Camera", ("camera", "cam_", "fov", "shake")),
    ("Actors_and_Entities", ("actor", "player", "party", "npc", "entity", "character", "mount")),
    ("UI_and_Message", ("ui", "message", "window", "menu", "layout", "font", "text", "dialog", "icon")),
    ("Memory_and_Heaps", ("heap", "memory", "alloc", "free", "pool", "buddy")),
    ("Save_and_Persistence", ("save", "load", "record", "flag", "quest", "restore", "persist")),
    ("Field_and_World", ("map", "field", "level", "world", "area", "warp", "jump", "weather", "time")),
    ("Input", ("hid", "pad", "button", "touch", "input")),
    ("Kernel_and_System", ("thread", "mutex", "kernel", "svc", "event", "semaphore", "system", "init")),
    ("IO_and_Files", ("file", "rom", "fs", "asset", "archive", "pack", "stream")),
]
GENERAL = "General_Procedures"
DOMAIN_ORDER = [name for name, _ in DOMAINS] + [GENERAL]

# A name is only "real" when it is not one of the decompiler/seed placeholders.
GENERIC_NAME = re.compile(
    r"^(FUN_|func_|sub_|thunk_|LAB_|maybe_|unknown$|undefined|nullsub_|FUN_|DAT_|PTR_)", re.I
)
ADDRESS_RE = re.compile(r"(?:0x)?[0-9a-fA-F]{6,8}")  # Ghidra export omits the 0x
ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
EXPECTED_CODE = "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8"

# Documented baseline source counts (README / audit). Used only when the live
# game_data tree is absent; if the tree exists its extension counts win.
SOURCE_BASELINE = {
    "models": 10542,
    "textures": 3486,
    "layouts": 7232,
    "scripts": 769,
    "tables": 5929,
    "audio": 5877,
    "maps": 1196,
    "text": 0,
}
SOURCE_EXTS = {
    "models": (".bch",),
    "textures": (".bflim",),
    "layouts": (".bflyt", ".bflan"),
    "scripts": (".cnut",),
    "tables": (".bxon",),
    "audio": (".bcstm",),
    "maps": (".level3d",),
    "text": (".bmsg", ".btxt", ".bmbt"),
}
ASSET_FAMILIES = [
    ("models", "3D models (BCH)"),
    ("textures", "Textures (BFLIM)"),
    ("layouts", "UI layouts / animations (BFLYT/BFLAN)"),
    ("tables", "Data tables (BXON)"),
    ("audio", "Audio streams (BCSTM)"),
    ("maps", "Level maps (Level3D)"),
    ("text", "Dialogue / message text"),
]


# --------------------------------------------------------------------------- #
# small utilities
# --------------------------------------------------------------------------- #
def read_json(path: Path, default):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return default


def read_text(path: Path, limit: int | None = None) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read() if limit is None else f.read(limit)
    except OSError:
        return ""


def load_jsonl(path: Path) -> list[dict]:
    out: list[dict] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        out.append(item)
                except ValueError:
                    continue  # a worker may be writing the file right now
    except OSError:
        pass
    return out


def norm_addr(value) -> int | None:
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return None
    m = ADDRESS_RE.search(value)
    if not m:
        return None
    try:
        return int(m.group(0), 16)
    except ValueError:
        return None


def addr_str(value: int | None) -> str:
    return f"0x{value:08X}" if value else "?"


def pct(n: float, d: float) -> float:
    return (100.0 * n / d) if d else 0.0


def _as_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def pct_text(value: float | None) -> str:
    return "&mdash;" if value is None else f"{value:.1f}%"


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def domain_for(name: str) -> str:
    low = (name or "").lower()
    for domain, keys in DOMAINS:
        if any(k in low for k in keys):
            return domain
    return GENERAL


def is_real_name(name: str | None) -> bool:
    return bool(name) and not GENERIC_NAME.match(name.strip())


def by_address(items: list[dict]) -> list[dict]:
    return sorted(items, key=lambda r: (r.get("address") is None, r.get("address") or 0))


def timestamp() -> tuple[datetime, str]:
    now = datetime.now().astimezone()
    return now, now.strftime("%Y-%m-%d %H:%M:%S %Z")


# --------------------------------------------------------------------------- #
# editor feature checklist (progress/features.json is user-editable)
# --------------------------------------------------------------------------- #
DEFAULT_FEATURES = {
    "_comment": (
        "Human checklist for DQXI Studio. status = todo | partial | done. "
        "Weighted completion: done=1, partial=0.5. Edit freely; progress.py "
        "preserves this file and only creates it when missing."
    ),
    "groups": [
        {
            "name": "Viewer & editor",
            "features": [
                {"id": "asset_browser", "status": "done",
                 "title": "Browse every converted asset family",
                 "notes": "viewer_rs panels for models, textures, layouts, scripts, tables, audio, maps."},
                {"id": "native_code_browser", "status": "done",
                 "title": "Browse and search readable native C",
                 "notes": "Code panel reads decomp/ghidra; falls back to asm when the index is missing."},
                {"id": "level_editor_scene", "status": "done",
                 "title": "Load a level3d map with its environment mesh",
                 "notes": "Editor panel loads game_assets/maps/<id>/scene.json plus the converted OBJ/glTF."},
                {"id": "level_editor_transform", "status": "done",
                 "title": "Edit placement transforms with undo/redo",
                 "notes": "Position, scale and rotation edits; marker drag; undo/redo stacks."},
                {"id": "level_editor_save", "status": "done",
                 "title": "Save editor project and export a patched BXON",
                 "notes": "editor_projects/<map>.json and same-size level3d.patched.bxon."},
                {"id": "level_editor_rebuild", "status": "partial",
                 "title": "One-click rebuild of a playable ROM from the editor",
                 "notes": "tools/patch_game.py works from the CLI; the button is not in the UI yet."},
                {"id": "table_editor", "status": "todo",
                 "title": "Schema-driven table editor (items, monsters, spells, shops)",
                 "notes": "E1_tables. Current tables panel is a structural JSON viewer."},
                {"id": "text_editor", "status": "todo",
                 "title": "Message/dialogue text editor with font-glyph check",
                 "notes": "E2_text. The dialogue panel is read-only today."},
                {"id": "script_editor", "status": "partial",
                 "title": "Edit, recompile and validate Squirrel scripts",
                 "notes": "E3_scripts. Decompiled .nut and assembly text can be viewed/edited; no recompile path in the UI."},
                {"id": "asset_replace", "status": "partial",
                 "title": "Replace textures, models and audio from the UI with validation",
                 "notes": "E4_assets. texture_tool, model_patch, bch_texture_patch and bcstm_encode are CLI-only."},
                {"id": "playtest", "status": "todo",
                 "title": "Play button: export and launch Azahar/Citra",
                 "notes": "X2_playtest. No emulator launch path yet."},
            ],
        },
        {
            "name": "Native code readability",
            "features": [
                {"id": "readable_decomp", "status": "done",
                 "title": "Ghidra high-level C for every entry point",
                 "notes": "18,748 decompiled of 18,787; 38 covered by a containing function, 1 unresolved."},
                {"id": "symbol_naming", "status": "partial",
                 "title": "Name every native function",
                 "notes": "N_* naming batches propose Subsystem_VerbNoun names; ~460 names today."},
                {"id": "documentation", "status": "partial",
                 "title": "Summarise what each function does",
                 "notes": "Naming proposals carry one-line summaries; they still have to be merged into the C."},
                {"id": "c_source_replacement", "status": "partial",
                 "title": "Replace native code with bit-matching C source",
                 "notes": "4 verified replacements (InitBss + 3 GetTalkParty wrappers) of 18,787."},
                {"id": "naming_merge", "status": "todo",
                 "title": "Merge naming proposals into symbols and regenerate readable C",
                 "notes": "M1_merge_names."},
            ],
        },
        {
            "name": "Build & hardware export",
            "features": [
                {"id": "bitmatch", "status": "done",
                 "title": "Bit-matching reassembly of code.bin / .code / ROM",
                 "notes": "tools/build.py reproduces the retail SHA-256; the full test suite guards it."},
                {"id": "rom_patch", "status": "done",
                 "title": "Same-size ROM patch with verified RomFS IVFC hashes",
                 "notes": "tools/patch_game.py; size-changing edits still need a full RomFS rebuild."},
                {"id": "layeredfs_export", "status": "todo",
                 "title": "Luma3DS LayeredFS mod folder export",
                 "notes": "X1_export. Target layout: luma/titles/<TitleID>/romfs/ + code.bin/code.ips."},
                {"id": "full_rom_export", "status": "partial",
                 "title": "Rebuild a full playable .3ds from modified assets",
                 "notes": "repack_rom.py exists and is used by the patcher; size-changing edits are unproven."},
                {"id": "cia_export", "status": "todo",
                 "title": "Export a .cia for real hardware",
                 "notes": "No CIA builder in the tree yet."},
            ],
        },
        {
            "name": "Docs & onboarding",
            "features": [
                {"id": "docs", "status": "partial",
                 "title": "Task-oriented modding documentation",
                 "notes": "README, EDITING, EDITOR, ASSETS, AUDIO, CODE, REBUILD, SOURCE_REPLACEMENT exist."},
                {"id": "first_mod", "status": "todo",
                 "title": "\"First mod in 10 minutes\" guide",
                 "notes": "D1_docs; walkthrough for an item price and a line of dialogue."},
                {"id": "project_tour", "status": "todo",
                 "title": "In-editor project tour",
                 "notes": "D1_docs; guided tour of the viewer/editor."},
            ],
        },
    ],
}


def ensure_features(reset: bool = False) -> dict:
    """Create progress/features.json once; never overwrite a user edit."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "features.json"
    if reset or not path.is_file():
        path.write_text(json.dumps(DEFAULT_FEATURES, indent=2) + "\n", encoding="utf-8")
    data = read_json(path, DEFAULT_FEATURES)
    return data if isinstance(data, dict) else DEFAULT_FEATURES


# --------------------------------------------------------------------------- #
# native code
# --------------------------------------------------------------------------- #
SUMMARY_FIELD_KEYS = ("summary", "documentation", "comment", "description", "doc")
SUMMARY_RE = re.compile(
    r"(?i)\b(summary|purpose|what it does|behaviou?r|semantics)\b\s*[:\-]|@brief"
)
BOILERPLATE = (
    "dqxi 3ds native function",
    "regenerated by ghidra",
    "address:",
    "symbol:",
    "signature:",
)
BAD_COMMENT = ("warning:", "decompil", "ghidra", "unreachable", "thunk", "todo", "fixme")
_summary_cache: dict[str, bool] = {}


def c_file_has_summary(path: Path) -> bool:
    """True when a .c file carries a human summary beyond the export boilerplate."""
    key = str(path)
    if key in _summary_cache:
        return _summary_cache[key]
    text = read_text(path, 8000)
    found = False
    if text:
        if SUMMARY_RE.search(text):
            found = True
        else:
            lines = text.splitlines()
            header_end = -1
            if lines and lines[0].strip().startswith("/*"):
                for i, line in enumerate(lines[:24]):
                    if "*/" in line:
                        header_end = i
                        break
            for line in lines[header_end + 1:80]:
                s = line.strip()
                if not (s.startswith("//") or s.startswith("/*") or s.startswith("*")):
                    continue
                prose = re.sub(r"^[/\*\s]+", "", s).strip("* /").strip()
                low = prose.lower()
                if len(prose) < 30:
                    continue
                if any(b in low for b in BOILERPLATE) or any(b in low for b in BAD_COMMENT):
                    continue
                # A real sentence has several words, not a decompiler cast.
                if len(re.findall(r"[A-Za-z]{3,}", prose)) >= 4:
                    found = True
                    break
    _summary_cache[key] = found
    return found


def function_path(rec: dict) -> Path | None:
    rel = rec.get("file")
    if rel:
        p = Path(str(rel).replace("\\", "/"))
        candidates = []
        if p.is_absolute():
            candidates.append(p)
        else:
            candidates += [GHIDRA / p, ROOT / p, GHIDRA / "functions" / p.name]
        for c in candidates:
            if c.is_file():
                return c
    path = rec.get("_path")
    return Path(path) if path and Path(path).is_file() else None


READABLE = ROOT / "decomp" / "readable"
_readable_cache: dict[str, str] = {}


def readable_relpath(rec_file) -> str:
    """Relative path of the readable C twin (``decomp/readable/...``), or ``""``.

    ``functions_merged.jsonl`` stores paths relative to ``decomp/ghidra`` such as
    ``functions/ResetVector_00100000.c``; ``tools/readable_c.py`` mirrors that tree
    one-to-one under ``decomp/readable``. The map links there so a click opens the
    readable view rather than the raw Ghidra export.
    """
    if not rec_file:
        return ""
    rel = str(rec_file).replace("\\", "/").strip()
    if not rel:
        return ""
    if rel in _readable_cache:
        return _readable_cache[rel]

    ghidra = str(GHIDRA).replace("\\", "/").rstrip("/") + "/"
    readable = str(READABLE).replace("\\", "/").rstrip("/") + "/"
    for prefix in (ghidra, readable, "decomp/ghidra/", "decomp/readable/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break

    answer = ""
    target = READABLE / rel
    try:
        if target.is_file() and READABLE.resolve() in target.resolve().parents:
            answer = target.relative_to(READABLE).as_posix()
    except (OSError, ValueError):
        answer = ""
    _readable_cache[str(rec_file)] = answer
    return answer


def load_proposals() -> tuple[dict[int, dict], int]:
    """Read every orchestration/naming/out/*.json proposal, keyed by address."""
    proposals: dict[int, dict] = {}
    batches = 0
    out_dir = ORC / "naming" / "out"
    if not out_dir.is_dir():
        return proposals, batches
    for path in sorted(out_dir.glob("*.json")):
        data = read_json(path, None)
        if data is None:
            continue
        batches += 1
        entries = data if isinstance(data, list) else (
            data.get("proposals") or data.get("functions") or data.get("items") or []
        )
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            addr = norm_addr(entry.get("address") or entry.get("addr"))
            if addr is None:
                continue
            entry = dict(entry)
            entry["_batch"] = path.stem
            proposals[addr] = entry
    return proposals, batches


def load_verified_c() -> tuple[set[int], set[str], list[dict]]:
    """Verified C source replacements: build report first, audit snapshot second."""
    addresses: set[int] = set()
    names: set[str] = set()
    evidence: list[dict] = []

    report = read_json(ROOT / "build" / "replacement_report.json", None)
    if isinstance(report, dict):
        report = report.get("replacements") or report.get("results") or []
    if isinstance(report, list):
        for entry in report:
            if not isinstance(entry, dict) or not entry.get("ok"):
                continue
            addr = norm_addr(entry.get("address"))
            if addr:
                addresses.add(addr)
            if entry.get("name"):
                names.add(str(entry["name"]))
            evidence.append({"name": entry.get("name"), "address": addr_str(addr)})

    if not addresses:
        snapshot = read_json(ROOT / "audit" / "PROJECT_VERIFICATION.json", {})
        for check in snapshot.get("checks", []) if isinstance(snapshot, dict) else []:
            if check.get("check") != "C source replacement":
                continue
            detail = check.get("detail")
            entries = []
            if isinstance(detail, list):
                entries = detail
            elif isinstance(detail, str) and detail.lstrip().startswith("["):
                try:
                    entries = ast.literal_eval(detail)
                except (ValueError, SyntaxError):
                    entries = []
            for entry in entries:
                if not isinstance(entry, dict) or not entry.get("ok"):
                    continue
                addr = norm_addr(entry.get("address"))
                if addr:
                    addresses.add(addr)
                if entry.get("name"):
                    names.add(str(entry["name"]))
                evidence.append({"name": entry.get("name"), "address": addr_str(addr)})

    # Last resort: src/replacements/*.c files that explicitly claim verification.
    if not addresses:
        repl_dir = ROOT / "src" / "replacements"
        if repl_dir.is_dir():
            for path in repl_dir.glob("*.c"):
                text = read_text(path, 4000)
                if "verified" not in text.lower() and "bit-identical" not in text.lower():
                    continue
                m = ADDRESS_RE.search(text)
                if m:
                    addresses.add(int(m.group(0), 16))
                    names.add(path.stem)
                    evidence.append({"name": path.stem, "address": m.group(0)})

    return addresses, names, evidence


def records_from_by_subsystem(root: Path) -> list[dict]:
    """Fallback when functions.jsonl is absent but the organised tree exists."""
    records = []
    for domain_dir in sorted(root.iterdir()) if root.is_dir() else []:
        if not domain_dir.is_dir():
            continue
        for path in domain_dir.glob("*.c"):
            m = re.search(r"_([0-9a-fA-F]{6,8})\.c$", path.name)
            if not m:
                continue
            name = path.name[: m.start(1) - 1]
            records.append({
                "address": f"0x{m.group(1)}",
                "name": name,
                "status": "ok",
                "file": str(path),
                "_path": str(path),
                "_domain": domain_dir.name,
            })
    return records


def collect_native() -> dict:
    proposals, batches = load_proposals()
    verified_addrs, verified_names, verified_evidence = load_verified_c()

    records: list[dict] = []
    source = "none"
    for rel in ("decomp/ghidra/functions_merged.jsonl", "decomp/ghidra/functions.jsonl"):
        path = ROOT / rel
        if path.is_file():
            loaded = load_jsonl(path)
            if loaded:
                records = loaded
                source = rel
                break
    index = read_json(GHIDRA / "functions_index.json", {})
    if not records and isinstance(index, dict) and index.get("functions"):
        records = list(index["functions"])
        source = "decomp/ghidra/functions_index.json"
    if not records:
        records = records_from_by_subsystem(GHIDRA / "by_subsystem")
        if records:
            source = "decomp/ghidra/by_subsystem"

    # Deduplicate by address; the merged export wins over stale duplicates.
    unique: dict[int, dict] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        addr = norm_addr(rec.get("address") or rec.get("addr"))
        if addr is None:
            continue
        if addr not in unique:
            unique[addr] = rec

    functions: list[dict] = []
    for addr in sorted(unique):
        rec = unique[addr]
        record_name = str(rec.get("name") or "").strip()
        proposal = proposals.get(addr) or {}
        proposed_name = str(proposal.get("name") or "").strip()
        confidence = proposal.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else 1.0
        except (TypeError, ValueError):
            confidence = 1.0
        high_confidence = confidence >= 0.5

        # Prefer an already-merged real name over a proposal; otherwise take the
        # proposal when it is not a placeholder.
        if is_real_name(record_name):
            effective = record_name
        elif proposed_name and is_real_name(proposed_name) and high_confidence:
            effective = proposed_name
        else:
            effective = record_name or proposed_name

        named = is_real_name(record_name) or (
            bool(proposed_name) and is_real_name(proposed_name) and high_confidence
        )
        proposed = bool(proposed_name or proposal) and not named

        summary = ""
        for key in SUMMARY_FIELD_KEYS:
            if isinstance(rec.get(key), str) and rec[key].strip():
                summary = rec[key].strip()
                break
        if not summary and isinstance(proposal.get("summary"), str):
            summary = proposal["summary"].strip()
        has_summary = len(summary) >= 20
        documented = False
        if named:
            documented = has_summary
            if not documented:
                path = function_path(rec)
                documented = bool(path and c_file_has_summary(path))

        matching = (
            addr in verified_addrs
            or record_name in verified_names
            or effective in verified_names
            or proposed_name in verified_names
        )

        if matching:
            status = "matching"
        elif documented:
            status = "documented"
        elif named:
            status = "named"
        elif proposed:
            status = "proposed"
        else:
            status = "unnamed"

        functions.append({
            "address": addr,
            "addr": addr_str(addr),
            "name": effective or f"sub_{addr:08X}",
            "record_name": record_name,
            "proposal_name": proposed_name,
            "proposal_summary": summary,
            "summary": summary,
            "size": _as_int(rec.get("size")),
            "confidence": confidence if proposal else None,
            "domain": rec.get("_domain") or domain_for(effective or record_name),
            "status": status,
            "file": rec.get("file") or rec.get("_path"),
        })

    # Aggregate per subsystem.
    by_domain: dict[str, list[dict]] = {d: [] for d in DOMAIN_ORDER}
    for fn in functions:
        by_domain.setdefault(fn["domain"], []).append(fn)

    subsystems = []
    for domain in DOMAIN_ORDER:
        group = by_domain.get(domain, [])
        if not group:
            continue
        total = len(group)
        named = sum(1 for f in group if f["status"] in ("named", "documented", "matching"))
        proposed = sum(1 for f in group if f["status"] == "proposed")
        documented = sum(1 for f in group if f["status"] in ("documented", "matching"))
        matching = sum(1 for f in group if f["status"] == "matching")
        subsystems.append({
            "name": domain,
            "total": total,
            "named": named,
            "proposed": proposed,
            "documented": documented,
            "matching_c": matching,
            "pct_named": round(pct(named, total), 2),
            "pct_documented": round(pct(documented, total), 2),
            "first_address": addr_str(min(f["address"] for f in group)),
            "last_address": addr_str(max(f["address"] for f in group)),
        })

    total = len(functions)
    named_total = sum(1 for f in functions if f["status"] in ("named", "documented", "matching"))
    proposed_total = sum(1 for f in functions if f["status"] == "proposed")
    documented_total = sum(1 for f in functions if f["status"] in ("documented", "matching"))
    matching_total = sum(1 for f in functions if f["status"] == "matching")

    decompiled = sum(
        1 for r in unique.values()
        if str(r.get("status") or "ok") in ("ok", "recovered") or r.get("file")
    )
    covered = sum(1 for r in unique.values() if r.get("status") == "covered_by")
    unresolved = max(0, total - decompiled - covered)

    # No index at all? Fall back to the audit snapshots so the page still reports
    # the retail baseline instead of pretending nothing exists.
    notes = []
    if not functions:
        snapshot = read_json(ROOT / "audit" / "PROJECT_VERIFICATION.json", {})
        checks = snapshot.get("checks", []) if isinstance(snapshot, dict) else []
        values = {}
        for check in checks:
            values[str(check.get("check"))] = check.get("detail")

        def as_int(value, default):
            try:
                return int(str(value).split()[0])
            except (TypeError, ValueError, IndexError):
                return default

        readable = read_json(ROOT / "audit" / "READABLE_C.json", {})
        total = as_int(values.get("native entry points"), 18787)
        decompiled = as_int(values.get("native decompiled"), int(readable.get("functions") or 0))
        named_total = int(readable.get("named_functions") or 0)
        proposed_total = len(proposals)
        documented_total = 0
        matching_total = len(verified_addrs)
        covered = as_int(values.get("covered by container"), 0)
        unresolved = as_int(values.get("unresolved"), 0)
        # PROJECT_VERIFICATION.json does not carry covered/unresolved counters;
        # read the documented final report so "39 unresolved" is not invented.
        final_text = read_text(ROOT / "audit" / "FINAL_REPORT.md")
        if not covered:
            m = re.search(r"Covered by a containing function\s*\|\s*([\d,]+)", final_text)
            if m:
                covered = int(m.group(1).replace(",", ""))
        if not unresolved:
            m = re.search(r"Unresolved\s*\|\s*([\d,]+)", final_text)
            if m:
                unresolved = int(m.group(1).replace(",", ""))
        if not unresolved:
            unresolved = max(0, total - decompiled - covered)
        source = "audit fallback (decomp/ghidra not generated)"
        notes.append(
            "decomp/ghidra is missing; totals come from audit/PROJECT_VERIFICATION.json and "
            "audit/READABLE_C.json. Run P0_regen to get per-function data and the coverage map."
        )
        subsystems = []
        if total:
            subsystems.append({
                "name": "All native (per-function index pending)",
                "total": total,
                "named": named_total,
                "proposed": proposed_total,
                "documented": documented_total,
                "matching_c": matching_total,
                "pct_named": round(pct(named_total, total), 2),
                "pct_documented": round(pct(documented_total, total), 2),
                "first_address": "?",
                "last_address": "?",
            })

    high_confidence = 0
    for proposal in proposals.values():
        name = str(proposal.get("name") or "")
        if not name or name.lower().startswith("maybe_"):
            continue
        confidence = proposal.get("confidence")
        try:
            confidence = 1.0 if confidence is None else float(confidence)
        except (TypeError, ValueError):
            confidence = 1.0
        if confidence >= 0.5:
            high_confidence += 1

    return {
        "total": total,
        "named": named_total,
        "proposed": proposed_total,
        "documented": documented_total,
        "matching_c": matching_total,
        "decompiled": decompiled,
        "covered_by_container": covered,
        "unresolved": unresolved,
        "pct_named": round(pct(named_total, total), 2),
        "pct_documented": round(pct(documented_total, total), 2),
        "pct_matching_c": round(pct(matching_total, total), 2),
        "proposals": {
            "addresses": len(proposals),
            "high_confidence": high_confidence,
            "batches": batches,
            "vector": "orchestration/naming/out/*.json",
        },
        "verified_c": verified_evidence,
        "source": source,
        "subsystems": subsystems,
        "notes": notes,
        "_functions": functions,
    }


# --------------------------------------------------------------------------- #
# scripts
# --------------------------------------------------------------------------- #
def collect_scripts() -> dict:
    manifest = read_json(ROOT / "audit" / "SCRIPT_DECOMPILE.json", {})
    try:
        total = int(manifest.get("scripts") or 0)
    except (TypeError, ValueError):
        total = 0
    try:
        decompiled = int(manifest.get("scripts_ok") or 0)
    except (TypeError, ValueError):
        decompiled = 0
    try:
        functions = int(manifest.get("functions") or 0)
    except (TypeError, ValueError):
        functions = 0

    source = "audit/SCRIPT_DECOMPILE.json"
    scripts_root = GAME_ASSETS / "scripts"
    if scripts_root.is_dir():
        live_total = sum(1 for _ in scripts_root.rglob("script.cnut"))
        live_nut = sum(1 for _ in scripts_root.rglob("*.decompiled.nut"))
        if live_total:
            total = max(total, live_total)
        if live_nut:
            decompiled = live_nut
        source += " + game_assets/scripts"

    if not total:
        # Last resort: count the packed CNUT members described by audit.
        pack = read_json(ROOT / "audit" / "pack_summary.json", {})
        try:
            total = int((pack.get("by_extension") or {}).get("cnut") or 0)
        except (TypeError, ValueError):
            total = 0
        if total:
            source = "audit/pack_summary.json"

    recompile_verified = 0
    recompile_source = "not generated yet"
    for rel in ("audit/SCRIPT_RECOMPILE.json", "audit/SCRIPT_RECOMPILE_VERIFIED.json",
                "build/script_recompile.json"):
        path = ROOT / rel
        data = read_json(path, None)
        if data is None:
            continue
        entries = data if isinstance(data, list) else (
            data.get("scripts") or data.get("results") or data.get("entries") or []
        )
        count = 0
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and (entry.get("ok") or entry.get("verified")
                                            or entry.get("recompiled")):
                count += 1
        if count:
            recompile_verified = count
            recompile_source = rel
            break
    if not recompile_verified and scripts_root.is_dir():
        live = sum(1 for _ in scripts_root.rglob("*.recompiled.*"))
        if live:
            recompile_verified = live
            recompile_source = "game_assets/scripts/*.recompiled.*"

    return {
        "total": total,
        "decompiled": decompiled,
        "recompile_verified": recompile_verified,
        "functions": functions,
        "pct_decompiled": round(pct(decompiled, total), 2),
        "pct_recompiled": round(pct(recompile_verified, total), 2),
        "source": source,
        "recompile_source": recompile_source,
    }


# --------------------------------------------------------------------------- #
# assets
# --------------------------------------------------------------------------- #
def live_source_counts() -> Counter:
    """Count source extensions under the generated game_data tree (one walk)."""
    wanted = {ext for exts in SOURCE_EXTS.values() for ext in exts}
    counts: Counter = Counter()
    for sub in ("romfs", "arcs", "packs"):
        root = ROOT / "game_data" / sub
        if not root.is_dir():
            continue
        for _dirpath, _dirs, files in os.walk(root):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext in wanted:
                    counts[ext] += 1
    return counts


def live_output_counts() -> dict[str, Counter]:
    """Count converted outputs by top-level game_assets family and extension."""
    counts: dict[str, Counter] = {}
    if not GAME_ASSETS.is_dir():
        return counts
    for dirpath, _dirs, files in os.walk(GAME_ASSETS):
        rel = Path(dirpath).relative_to(GAME_ASSETS)
        family = rel.parts[0] if rel.parts else ""
        bucket = counts.setdefault(family, Counter())
        for name in files:
            low = name.lower()
            if low == "scene.json":
                bucket["scene.json"] += 1
            else:
                bucket[os.path.splitext(low)[1]] += 1
    return counts


def output_value(counts: dict[str, Counter], family: str) -> int:
    bucket = counts.get(family)
    if not bucket:
        return 0
    if family == "models":
        return bucket[".gltf"] or bucket[".obj"]
    if family == "maps":
        return bucket["scene.json"] or bucket[".level3d"]
    if family == "scripts":
        return bucket[".decompiled.nut"] or bucket[".nut"]
    if family == "layouts":
        return bucket[".json"]
    if family == "tables":
        return bucket[".json"]
    if family == "text":
        return bucket[".json"] or bucket[".txt"]
    if family == "textures":
        return bucket[".png"]
    if family == "audio":
        return bucket[".wav"]
    return sum(bucket.values())


# Round-trip support is a capability statement, not a claim that every file was
# tested: textures/models/audio/layouts/maps have same-size write-back tools;
# BXON has no general object-graph writer yet, so tables stay at 0 here.
ROUNDTRIP_CAPABLE = {"textures", "models", "layouts", "audio", "maps"}


def collect_assets() -> dict:
    audit = read_json(ROOT / "audit" / "ASSET_VERIFICATION.json", {})
    groups = audit.get("groups") if isinstance(audit, dict) else {}
    groups = groups if isinstance(groups, dict) else {}
    roundtrip = read_json(ROOT / "audit" / "ASSET_ROUNDTRIP.json", {})
    roundtrip_families = roundtrip.get("families") if isinstance(roundtrip, dict) else None
    roundtrip_families = roundtrip_families if isinstance(roundtrip_families, dict) else {}

    sources = live_source_counts()
    outputs = live_output_counts()

    families = []
    for key, label in ASSET_FAMILIES:
        live_source = sum(sources.get(ext, 0) for ext in SOURCE_EXTS.get(key, ()))
        source = live_source or SOURCE_BASELINE.get(key, 0)
        audit_group = groups.get(key) if isinstance(groups.get(key), dict) else {}
        try:
            audit_converted = int(audit_group.get("files") or 0)
        except (TypeError, ValueError):
            audit_converted = 0

        live_converted = output_value(outputs, key)
        converted = live_converted or audit_converted or SOURCE_BASELINE.get(key, 0) * 0

        manifest_editable = None
        entry = roundtrip_families.get(key)
        if isinstance(entry, dict):
            try:
                manifest_editable = int(entry.get("editable") or entry.get("roundtrip_ok") or 0)
            except (TypeError, ValueError):
                manifest_editable = None
        if manifest_editable is not None:
            editable = manifest_editable
        elif key in ROUNDTRIP_CAPABLE:
            editable = converted
        else:
            editable = 0

        families.append({
            "key": key,
            "label": label,
            "source": source,
            "converted": converted,
            "editable": editable,
            "pct_converted": round(pct(converted, source), 2),
            "pct_editable": round(pct(editable, source), 2),
        })

    source_total = sum(f["source"] for f in families)
    converted_total = sum(f["converted"] for f in families)
    editable_total = sum(f["editable"] for f in families)
    return {
        "families": families,
        "source_total": source_total,
        "converted_total": converted_total,
        "editable_total": editable_total,
        "pct_converted": round(pct(converted_total, source_total), 2),
        "pct_editable": round(pct(editable_total, source_total), 2),
        "source": ("live game_data tree" if any(sources.values())
                   else "audit baseline (game_data not generated)"),
        "roundtrip_manifest": bool(roundtrip_families),
    }


# --------------------------------------------------------------------------- #
# editor features
# --------------------------------------------------------------------------- #
def collect_editor(features: dict) -> dict:
    groups = features.get("groups")
    if not isinstance(groups, list):
        flat = features.get("features")
        groups = [{"name": "Features", "features": flat}] if isinstance(flat, list) else []

    out_groups = []
    done = partial = todo = total = 0
    for group in groups:
        if not isinstance(group, dict):
            continue
        items = []
        for item in group.get("features") or []:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "todo").lower()
            if status not in ("todo", "partial", "done"):
                status = "todo"
            total += 1
            if status == "done":
                done += 1
            elif status == "partial":
                partial += 1
            else:
                todo += 1
            items.append({
                "id": item.get("id") or item.get("title") or "feature",
                "title": item.get("title") or item.get("id") or "Untitled feature",
                "status": status,
                "notes": item.get("notes") or "",
            })
        if items:
            out_groups.append({"name": group.get("name") or "Features", "features": items})

    percent = pct(done + 0.5 * partial, total)
    return {
        "groups": out_groups,
        "done": done,
        "partial": partial,
        "todo": todo,
        "total": total,
        "percent": round(percent, 2),
    }


# --------------------------------------------------------------------------- #
# build health
# --------------------------------------------------------------------------- #
def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8 * 1024 * 1024):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def file_when(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return ""


def collect_build() -> dict:
    code = ROOT / "build" / "code.bin"
    bitmatch = {"status": "unknown", "label": "Not generated yet", "detail": "", "when": ""}
    if code.is_file():
        digest = sha256_file(code)
        bitmatch["when"] = file_when(code)
        if digest == EXPECTED_CODE:
            bitmatch.update(status="green", label="PASS (bit-matching)",
                            detail=f"code.bin sha256 {digest}")
        elif digest:
            bitmatch.update(status="red", label="FAIL (hash differs)",
                            detail=f"code.bin sha256 {digest}")
    else:
        snapshot = read_json(ROOT / "audit" / "PROJECT_VERIFICATION.json", {})
        for check in snapshot.get("checks", []) if isinstance(snapshot, dict) else []:
            if check.get("check") == "code.bin hash" and check.get("ok"):
                bitmatch.update(
                    status="stale",
                    label="Last verified green (artifact not present)",
                    detail=f"audit/PROJECT_VERIFICATION.json: {check.get('detail')}",
                    when=file_when(ROOT / "audit" / "PROJECT_VERIFICATION.json"),
                )
                break

    report = read_json(ROOT / "build" / "bit_match_report.json", None)
    if isinstance(report, dict) and bitmatch["status"] == "unknown":
        ok = report.get("ok", report.get("match"))
        if ok is not None:
            bitmatch.update(
                status="green" if ok else "red",
                label="PASS (bit_match_report.json)" if ok else "FAIL (bit_match_report.json)",
                detail=str(report.get("detail") or report.get("sha256") or ""),
                when=file_when(ROOT / "build" / "bit_match_report.json"),
            )

    # Tests: prefer a machine-readable report, then the documented final report.
    tests = {"status": "unknown", "label": "No test log found", "passed": None,
             "total": None, "when": "", "source": ""}
    for rel, passed_key, total_key in (
        ("build/test_report.json", "passed", "total"),
        ("audit/TEST_RESULTS.json", "passed", "total"),
    ):
        data = read_json(ROOT / rel, None)
        if isinstance(data, dict):
            try:
                passed = int(data.get(passed_key) or 0)
                whole = int(data.get(total_key) or 0)
            except (TypeError, ValueError):
                continue
            if whole:
                tests.update(
                    status="green" if passed == whole else "red",
                    label=f"{passed} / {whole} PASS" if passed == whole else f"{passed} / {whole} passed",
                    passed=passed, total=whole, when=file_when(ROOT / rel), source=rel,
                )
                break

    final_report = ROOT / "audit" / "FINAL_REPORT.md"
    final_text = read_text(final_report)
    if tests["status"] == "unknown" and final_text:
        m = re.search(r"tests/run_all\.py[^\n]*?(\d+)\s*/\s*(\d+)\s*PASS", final_text)
        if not m:
            m = re.search(r"(\d+)\s*/\s*(\d+)\s+PASS", final_text)
        if m:
            passed, whole = int(m.group(1)), int(m.group(2))
            date = re.search(r"(\d{4}-\d{2}-\d{2})", final_text[:200])
            tests.update(
                status="stale",
                label=f"Last documented: {passed} / {whole} PASS",
                passed=passed, total=whole,
                when=(date.group(1) if date else file_when(final_report)),
                source="audit/FINAL_REPORT.md (run tests/run_all.py to refresh)",
            )

    snapshot = read_json(ROOT / "audit" / "PROJECT_VERIFICATION.json", {})
    checks = snapshot.get("checks", []) if isinstance(snapshot, dict) else []
    failed = [c.get("check") for c in checks if isinstance(c, dict) and not c.get("ok")]
    verification = {
        "status": ("green" if checks and not failed else "red" if checks else "unknown"),
        "label": ("PASS (last run)" if checks and not failed else "FAIL" if checks else "Not run"),
        "detail": (f"{len(checks)} checks, {len(failed)} failed" if checks else ""),
        "failed": failed[:12],
        "when": file_when(ROOT / "audit" / "PROJECT_VERIFICATION.json"),
        "source": "audit/PROJECT_VERIFICATION.json",
    }

    return {"bitmatch": bitmatch, "tests": tests, "verification": verification}


# --------------------------------------------------------------------------- #
# types / globals / locals (S0_types_plan -> M2/M3 merges)
# --------------------------------------------------------------------------- #
TYPE_PLACEHOLDER_VAR_RE = re.compile(
    r"^(?:[a-z]{1,3}Var\d+|local_[0-9a-f]+|uStack_[0-9a-f]+|iStack_[0-9a-f]+|"
    r"in_[a-z0-9]+|extraout_[a-z0-9_]+|unaff_[a-z0-9]+|arg\d+|param_\d+)$"
)
RAW_TYPE_PLACEHOLDER_RE = re.compile(
    r"^(?:unknown(?:_.*)?|undefined\d*|DAT_[0-9a-fA-F]{6,8}|g_00[0-9a-fA-F]{6}|"
    r"f_[0-9a-fA-F]+|FUN_[0-9a-fA-F]{6,8}|sub_[0-9a-fA-F]{6,8})$",
    re.I,
)


def _parse_conf(value, default: float = 0.5) -> float:
    if value is None or isinstance(value, bool):
        return default
    try:
        conf = float(value)
    except (TypeError, ValueError):
        return 0.0
    if conf != conf or conf in (float("inf"), float("-inf")):
        return 0.0
    return min(1.0, max(0.0, conf))


def _parse_offset(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            off = int(s, 0)
            return off if off >= 0 else None
        except ValueError:
            return None
    return None


def _classify_type_name(name: str | None, confidence: float, *, extra_maybe: bool = False) -> str:
    """Classify a worker answer into 'named', 'guessed', 'unknown' or ''."""
    s = (name or "").strip()
    if not s:
        return ""
    if extra_maybe or s.lower().startswith("maybe_"):
        return "guessed"
    if RAW_TYPE_PLACEHOLDER_RE.match(s) or TYPE_PLACEHOLDER_VAR_RE.match(s):
        return "unknown"
    return "named" if confidence >= 0.5 else "guessed"


def _record_type_answer(bucket: dict, key, state: str, conf: float) -> None:
    if not state:
        return
    rank = {"named": 2, "guessed": 1, "unknown": 0}.get(state, -1)
    prev = bucket.get(key)
    if prev is None:
        bucket[key] = (state, conf)
        return
    prev_rank = {"named": 2, "guessed": 1, "unknown": 0}.get(prev[0], -1)
    if (rank, conf) > (prev_rank, prev[1]):
        bucket[key] = (state, conf)


def _count_vars_in_functions(functions: list) -> int:
    placeholders = 0
    non_self = 0
    all_vars = 0
    for fn in functions:
        if not isinstance(fn, dict):
            continue
        vlist = fn.get("variables")
        if not isinstance(vlist, list):
            continue
        for v in vlist:
            vname = str(v.get("name") if isinstance(v, dict) else (v or "")).strip()
            if not vname:
                continue
            all_vars += 1
            if vname != "self":
                non_self += 1
            if TYPE_PLACEHOLDER_VAR_RE.match(vname):
                placeholders += 1
    return placeholders or non_self or all_vars


def _summarize_kind(total: int, answers: dict, merged: int,
                    batch_kind: str, batches_done: int, batches_total: int) -> dict:
    answered = len(answers)
    named = sum(1 for state, _ in answers.values() if state == "named")
    guessed = sum(1 for state, _ in answers.values() if state == "guessed")
    return {
        "total": total,
        "answered": answered,
        "named": named,
        "guessed": guessed,
        "merged": merged,
        "pct_answered": round(pct(answered, total), 2),
        "pct_named": round(pct(named, total), 2),
        "pct_guessed": round(pct(guessed, total), 2),
        "pct_merged": round(pct(merged, total), 2),
        "batches": {
            "kind": batch_kind,
            "done": batches_done,
            "total": batches_total,
        },
    }


def collect_types(root: Path | None = None) -> dict:
    """Collect type-recovery progress across globals (G_*), classes/fields (S_*) and locals (V_*).

    Separates three distinct stages so live worker movement is always visible:
      * inputs to recover (`structs.json`, `globals.json`, `locals.json` and `batches/`);
      * worker answers (`orchestration/types/out/{G,S,V}_*.json`: `named` when not
        `maybe_` and confidence >= 0.5, `guessed` for `maybe_` or low-confidence);
      * merged headers & maps (`orchestration/types/merged/` and `include/dqxi/*.h`).

    Missing, partial or malformed files are counted in `malformed_files` and never crash.
    """
    base_root = root if root is not None else ROOT
    orc_dir = base_root / "orchestration"
    types_dir = orc_dir / "types"
    batches_dir = types_dir / "batches"
    out_dir = types_dir / "out"
    merged_dir = types_dir / "merged"
    done_dir = orc_dir / "done"
    tasks_dir = orc_dir / "tasks"
    headers_dir = base_root / "include" / "dqxi"

    malformed: list[str] = []

    def rel_label(path: Path) -> str:
        try:
            return path.relative_to(base_root).as_posix()
        except ValueError:
            return path.name

    def mark_malformed(path: Path) -> None:
        label = rel_label(path)
        if label not in malformed:
            malformed.append(label)

    def read_checked_json(path: Path, expected_types: tuple[type, ...]):
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            mark_malformed(path)
            return None
        if not isinstance(data, expected_types):
            mark_malformed(path)
            return None
        return data

    structs_doc = read_checked_json(types_dir / "structs.json", (dict,))
    globals_doc = read_checked_json(types_dir / "globals.json", (dict,))
    locals_doc = read_checked_json(types_dir / "locals.json", (dict,))
    index_doc = read_checked_json(batches_dir / "index.json", (dict,))
    report_doc = read_checked_json(merged_dir / "report.json", (dict,))

    report = report_doc if isinstance(report_doc, dict) else {}
    inputs = report.get("inputs") if isinstance(report.get("inputs"), dict) else {}

    # 1. Batch counts per kind (done = orchestration/done/<id>.md exists).
    batch_counts: dict[str, dict[str, int]] = {}
    for kind in ("G", "S", "V"):
        batch_ids: set[str] = set()
        if batches_dir.is_dir():
            batch_ids.update(p.stem for p in batches_dir.glob(f"{kind}_*.json"))
        if not batch_ids and isinstance(index_doc, dict):
            for entry in index_doc.get("batches") or []:
                if isinstance(entry, dict) and entry.get("kind") == kind and entry.get("id"):
                    batch_ids.add(str(entry["id"]))
        if not batch_ids and tasks_dir.is_dir():
            batch_ids.update(p.stem for p in tasks_dir.glob(f"{kind}_*.md"))
        b_done = sum(1 for bid in batch_ids if (done_dir / f"{bid}.md").is_file()) if done_dir.is_dir() else 0
        batch_counts[kind] = {"done": b_done, "total": len(batch_ids)}

    # 2. Totals (evidence databases first, batch files second, merge report last).
    globals_total = 0
    if isinstance(globals_doc, dict):
        g_list = globals_doc.get("globals")
        if isinstance(g_list, list) and g_list:
            globals_total = sum(1 for g in g_list if isinstance(g, dict))
        else:
            g_stats = globals_doc.get("stats") if isinstance(globals_doc.get("stats"), dict) else {}
            globals_total = _as_int(g_stats.get("globals"), 0)
    if globals_total == 0 and batches_dir.is_dir():
        for p in sorted(batches_dir.glob("G_*.json")):
            bdoc = read_checked_json(p, (dict,))
            if isinstance(bdoc, dict) and isinstance(bdoc.get("globals"), list):
                globals_total += sum(1 for g in bdoc["globals"] if isinstance(g, dict))
    if globals_total == 0:
        globals_total = _as_int(inputs.get("globals"), 0)

    classes_total = 0
    fields_total = 0
    if isinstance(structs_doc, dict):
        c_list = structs_doc.get("classes")
        s_stats = structs_doc.get("stats") if isinstance(structs_doc.get("stats"), dict) else {}
        if isinstance(c_list, list) and c_list:
            with_fields = [c for c in c_list if isinstance(c, dict) and c.get("fields")]
            classes_total = len(with_fields) if with_fields else sum(1 for c in c_list if isinstance(c, dict))
            fields_total = sum(
                len(c.get("fields") or [])
                for c in c_list
                if isinstance(c, dict) and isinstance(c.get("fields"), list)
            )
        else:
            classes_total = _as_int(s_stats.get("classes_with_fields") or s_stats.get("classes"), 0)
            fields_total = _as_int(s_stats.get("fields"), 0)
    if classes_total == 0 and fields_total == 0 and batches_dir.is_dir():
        for p in sorted(batches_dir.glob("S_*.json")):
            bdoc = read_checked_json(p, (dict,))
            if isinstance(bdoc, dict) and isinstance(bdoc.get("classes"), list):
                for c in bdoc["classes"]:
                    if isinstance(c, dict):
                        classes_total += 1
                        if isinstance(c.get("fields"), list):
                            fields_total += len(c["fields"])
    if classes_total == 0:
        classes_total = _as_int(inputs.get("classes_with_fields"), 0)
    if fields_total == 0:
        fields_total = _as_int(inputs.get("fields"), 0)

    locals_total = 0
    if isinstance(locals_doc, dict):
        l_stats = locals_doc.get("stats") if isinstance(locals_doc.get("stats"), dict) else {}
        if l_stats.get("variables_placeholder"):
            locals_total = _as_int(l_stats.get("variables_placeholder"), 0)
        elif isinstance(locals_doc.get("functions"), list) and locals_doc["functions"]:
            locals_total = _count_vars_in_functions(locals_doc["functions"])
        else:
            locals_total = _as_int(l_stats.get("variables"), 0)
    if locals_total == 0 and batches_dir.is_dir():
        for p in sorted(batches_dir.glob("V_*.json")):
            bdoc = read_checked_json(p, (dict,))
            if isinstance(bdoc, dict) and isinstance(bdoc.get("functions"), list):
                locals_total += _count_vars_in_functions(bdoc["functions"])
    if locals_total == 0:
        locals_total = _as_int(inputs.get("variables"), 0)

    # 3. Worker answers in orchestration/types/out/{G,S,V}_*.json (plus any stray *.json).
    g_answers: dict[str, tuple[str, float]] = {}
    c_answers: dict[str, tuple[str, float]] = {}
    f_answers: dict[tuple[str, int], tuple[str, float]] = {}
    v_answers: dict[tuple[str, str], tuple[str, float]] = {}

    if out_dir.is_dir():
        for path in sorted(out_dir.glob("*.json")):
            data = read_checked_json(path, (list, dict))
            if data is None:
                continue
            stem = path.stem
            kind = (
                "G" if stem.startswith("G_")
                else "S" if stem.startswith("S_")
                else "V" if stem.startswith("V_")
                else ""
            )
            entries = None
            if isinstance(data, list):
                entries = data
                if not kind:
                    first = next((x for x in entries if isinstance(x, dict)), None)
                    if first is not None:
                        if "fields" in first or "class" in first:
                            kind = "S"
                        elif "locals" in first or "params" in first or "function" in first:
                            kind = "V"
                        elif "address" in first and "name" in first:
                            kind = "G"
                    if not kind and entries:
                        mark_malformed(path)
                        continue
            elif isinstance(data, dict):
                if not kind:
                    if isinstance(data.get("classes"), list):
                        kind = "S"
                    elif isinstance(data.get("globals"), list):
                        kind = "G"
                    elif isinstance(data.get("functions"), list):
                        kind = "V"
                key_order = (
                    ("globals", "entries", "items") if kind == "G"
                    else ("classes", "structs", "entries", "items") if kind == "S"
                    else ("functions", "locals", "entries", "items") if kind == "V"
                    else ()
                )
                for k in key_order:
                    if isinstance(data.get(k), list):
                        entries = data[k]
                        break
                if entries is None:
                    mark_malformed(path)
                    continue

            if not entries or not kind:
                continue

            if kind == "G":
                for entry in entries:
                    if not isinstance(entry, dict):
                        mark_malformed(path)
                        continue
                    addr = norm_addr(entry.get("address") or entry.get("addr"))
                    name = str(entry.get("name") or "").strip()
                    if addr is None and not name:
                        continue
                    g_key = f"0x{addr:08X}" if addr is not None else name
                    conf = _parse_conf(entry.get("confidence"), 0.5)
                    state = _classify_type_name(name, conf)
                    _record_type_answer(g_answers, g_key, state, conf)
            elif kind == "S":
                for entry in entries:
                    if not isinstance(entry, dict):
                        mark_malformed(path)
                        continue
                    cls_name = str(entry.get("class") or entry.get("name") or "").strip()
                    if not cls_name:
                        continue
                    cls_type = str(entry.get("type") or "").strip()
                    raw_name = str(entry.get("name") or "").strip()
                    cls_conf = _parse_conf(entry.get("confidence"), 0.5)
                    extra_maybe = cls_type.lower().startswith("maybe_") or raw_name.lower().startswith("maybe_")
                    c_state = _classify_type_name(cls_name, cls_conf, extra_maybe=extra_maybe)
                    _record_type_answer(c_answers, cls_name, c_state, cls_conf)

                    fields_in = entry.get("fields")
                    if isinstance(fields_in, list):
                        for fld in fields_in:
                            if not isinstance(fld, dict):
                                mark_malformed(path)
                                continue
                            off = _parse_offset(fld.get("offset"))
                            fname = str(fld.get("name") or "").strip()
                            if off is None or not fname:
                                continue
                            fconf = _parse_conf(fld.get("confidence"), cls_conf)
                            f_state = _classify_type_name(fname, fconf)
                            _record_type_answer(f_answers, (cls_name, off), f_state, fconf)
            elif kind == "V":
                for entry in entries:
                    if not isinstance(entry, dict):
                        mark_malformed(path)
                        continue
                    fn_addr = norm_addr(entry.get("address") or entry.get("addr"))
                    fn_name = str(entry.get("function") or entry.get("name") or "").strip()
                    fn_key = f"0x{fn_addr:08X}" if fn_addr is not None else fn_name
                    if not fn_key:
                        continue
                    fn_conf = _parse_conf(entry.get("confidence"), 0.5)
                    maps = [entry[k] for k in ("params", "locals") if isinstance(entry.get(k), dict)]
                    if not maps and isinstance(entry.get("variables"), dict):
                        maps.append(entry["variables"])
                    for mp in maps:
                        for old_tok, new_val in mp.items():
                            old_s = str(old_tok).strip()
                            if not old_s:
                                continue
                            if isinstance(new_val, dict):
                                new_s = str(new_val.get("name") or "").strip()
                                v_conf = _parse_conf(new_val.get("confidence"), fn_conf)
                            elif isinstance(new_val, str):
                                new_s = new_val.strip()
                                v_conf = fn_conf
                            else:
                                continue
                            if not new_s or new_s == old_s:
                                continue
                            v_state = _classify_type_name(new_s, v_conf)
                            _record_type_answer(v_answers, (fn_key, old_s), v_state, v_conf)

    # 4. Merged results committed by M2_types_merge / M3_vars_merge
    #    (orchestration/types/merged/{fields,globals,locals}.json & include/dqxi/*.h).
    #    Note: `apply.py --validate` overwrites report.json without touching maps/headers,
    #    so only actual merged maps and headers count as merged here.
    fields_map = read_checked_json(merged_dir / "fields.json", (dict,))
    globals_map = read_checked_json(merged_dir / "globals.json", (dict,))
    locals_map = read_checked_json(merged_dir / "locals.json", (dict,))

    if isinstance(globals_map, dict) and isinstance(globals_map.get("globals"), dict):
        globals_merged = len(globals_map["globals"])
    else:
        gh_text = read_text(headers_dir / "globals.h")
        globals_merged = len(re.findall(r"^\s*extern\s+", gh_text, re.M)) if gh_text else 0

    if isinstance(fields_map, dict) and isinstance(fields_map.get("classes"), dict):
        cls_dict = fields_map["classes"]
        classes_merged = len(cls_dict)
        fields_merged = sum(
            len(c.get("fields") or {})
            for c in cls_dict.values()
            if isinstance(c, dict) and isinstance(c.get("fields"), dict)
        )
    else:
        sh_text = read_text(headers_dir / "structs.h")
        classes_merged = (
            len(re.findall(r"^\s*typedef\s+struct\s+\w+\s*\{", sh_text, re.M)) if sh_text else 0
        )
        fields_merged = (
            sum(1 for line in sh_text.splitlines() if "/* +0x" in line and "inherited " not in line)
            if sh_text else 0
        )

    if isinstance(locals_map, dict) and isinstance(locals_map.get("functions"), dict):
        fn_dict = locals_map["functions"]
        locals_merged = sum(
            (len(f["params"]) if isinstance(f.get("params"), dict) else 0)
            + (len(f["locals"]) if isinstance(f.get("locals"), dict) else 0)
            for f in fn_dict.values()
            if isinstance(f, dict)
        )
    else:
        locals_merged = 0

    globals_block = _summarize_kind(
        globals_total, g_answers, globals_merged,
        "G", batch_counts["G"]["done"], batch_counts["G"]["total"],
    )
    classes_block = _summarize_kind(
        classes_total, c_answers, classes_merged,
        "S", batch_counts["S"]["done"], batch_counts["S"]["total"],
    )
    fields_block = _summarize_kind(
        fields_total, f_answers, fields_merged,
        "S", batch_counts["S"]["done"], batch_counts["S"]["total"],
    )
    locals_block = _summarize_kind(
        locals_total, v_answers, locals_merged,
        "V", batch_counts["V"]["done"], batch_counts["V"]["total"],
    )

    all_blocks = (globals_block, classes_block, fields_block, locals_block)
    overall_total = sum(b["total"] for b in all_blocks)
    overall_answered = sum(b["answered"] for b in all_blocks)
    overall_named = sum(b["named"] for b in all_blocks)
    overall_guessed = sum(b["guessed"] for b in all_blocks)
    overall_merged = sum(b["merged"] for b in all_blocks)

    batches_done_all = sum(batch_counts[k]["done"] for k in ("G", "S", "V"))
    batches_total_all = sum(batch_counts[k]["total"] for k in ("G", "S", "V"))

    sources = []
    if types_dir.is_dir():
        sources.append("orchestration/types")
    if headers_dir.is_dir():
        sources.append("include/dqxi")
    source_str = " + ".join(sources) if sources else "not generated yet"

    return {
        "source": source_str,
        "globals": globals_block,
        "classes": classes_block,
        "fields": fields_block,
        "locals": locals_block,
        "batches": {
            "G": batch_counts["G"],
            "S": batch_counts["S"],
            "V": batch_counts["V"],
            "done": batches_done_all,
            "total": batches_total_all,
        },
        "total": overall_total,
        "answered": overall_answered,
        "named": overall_named,
        "guessed": overall_guessed,
        "merged": overall_merged,
        "pct_answered": round(pct(overall_answered, overall_total), 2),
        "pct_named": round(pct(overall_named, overall_total), 2),
        "pct_guessed": round(pct(overall_guessed, overall_total), 2),
        "pct_merged": round(pct(overall_merged, overall_total), 2),
        "classes_total": classes_block["total"],
        "classes_named": classes_block["named"],
        "fields_total": fields_block["total"],
        "fields_named": fields_block["named"],
        "globals_total": globals_block["total"],
        "globals_named": globals_block["named"],
        "locals_total": locals_block["total"],
        "locals_named": locals_block["named"],
        "pct_classes": classes_block["pct_named"],
        "pct_fields": fields_block["pct_named"],
        "pct_globals": globals_block["pct_named"],
        "pct_locals": locals_block["pct_named"],
        "malformed_files": len(malformed),
        "malformed": malformed[:50],
        "demo": bool(report.get("demo")),
        "when": file_when(merged_dir / "report.json"),
        "errors": _as_int(report.get("errors"), 0),
        "warnings": _as_int(report.get("warnings"), 0),
    }


def types_fallback() -> dict:
    zero_g = _summarize_kind(0, {}, 0, "G", 0, 0)
    zero_s = _summarize_kind(0, {}, 0, "S", 0, 0)
    zero_v = _summarize_kind(0, {}, 0, "V", 0, 0)
    return {
        "source": "unavailable",
        "globals": dict(zero_g),
        "classes": dict(zero_s),
        "fields": dict(zero_s),
        "locals": dict(zero_v),
        "batches": {
            "G": {"done": 0, "total": 0},
            "S": {"done": 0, "total": 0},
            "V": {"done": 0, "total": 0},
            "done": 0,
            "total": 0,
        },
        "total": 0, "answered": 0, "named": 0, "guessed": 0, "merged": 0,
        "pct_answered": 0.0, "pct_named": 0.0, "pct_guessed": 0.0, "pct_merged": 0.0,
        "classes_total": 0, "classes_named": 0,
        "fields_total": 0, "fields_named": 0,
        "globals_total": 0, "globals_named": 0,
        "locals_total": 0, "locals_named": 0,
        "pct_classes": 0.0, "pct_fields": 0.0, "pct_globals": 0.0, "pct_locals": 0.0,
        "malformed_files": 0, "malformed": [],
        "demo": False, "when": "", "errors": 0, "warnings": 0,
    }


# --------------------------------------------------------------------------- #
# HTML shell
# --------------------------------------------------------------------------- #
CSS = """
:root{
  --bg:#f6f7f9; --fg:#18202b; --muted:#5b6675; --card:#ffffff; --line:#d8dee7;
  --accent:#6d4aff; --blue:#2563eb; --green:#15803d; --amber:#b45309;
  --red:#b91c1c; --purple:#7e22ce; --chip:#eef1f6;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0d1117; --fg:#e6edf3; --muted:#9aa7b8; --card:#151b24; --line:#2a3442;
    --accent:#a78bfa; --blue:#60a5fa; --green:#4ade80; --amber:#fbbf24;
    --red:#f87171; --purple:#c084fc; --chip:#1c2531;
  }
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0 auto;max-width:1180px;padding:24px 20px 64px;background:var(--bg);color:var(--fg);
  font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Verdana,sans-serif}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}
h1{font-size:1.9rem;margin:.2em 0 .15em}
h2{font-size:1.35rem;margin:2.2em 0 .6em;padding-bottom:.25em;border-bottom:1px solid var(--line)}
h3{font-size:1.05rem;margin:1.4em 0 .4em}
p,li{color:var(--fg)}
.muted{color:var(--muted)}
.small{font-size:.86rem}
nav{display:flex;flex-wrap:wrap;gap:.35rem .9rem;margin:0 0 1.2rem;padding:.65rem .9rem;
  background:var(--card);border:1px solid var(--line);border-radius:10px}
nav a{font-weight:600}
nav .here{color:var(--fg);text-decoration:none;border-bottom:2px solid var(--accent)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:.8rem;margin:1rem 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.85rem 1rem}
.card .value{font-size:1.75rem;font-weight:700;line-height:1.15}
.card .label{font-weight:650}
.card .sub{color:var(--muted);font-size:.82rem;margin-top:.15rem}
.badge-row{display:flex;flex-wrap:wrap;gap:.6rem;align-items:center;margin:.6rem 0 0}
.badge-row img{height:20px;display:block}
table{border-collapse:collapse;width:100%;margin:.6rem 0 1rem;background:var(--card);
  border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:.93rem}
th,td{padding:.5rem .65rem;border-bottom:1px solid var(--line);text-align:right;
  font-variant-numeric:tabular-nums}
th{background:var(--chip);font-weight:650;color:var(--muted);text-transform:uppercase;
  font-size:.73rem;letter-spacing:.04em}
th:first-child,td:first-child{text-align:left}
tr:last-child td{border-bottom:none}
tr.total td{font-weight:700;background:var(--chip)}
.num{font-variant-numeric:tabular-nums}
.pct{font-weight:650}
.chip{display:inline-block;padding:.08rem .48rem;border-radius:999px;font-size:.75rem;
  font-weight:700;letter-spacing:.02em;white-space:nowrap}
.done{background:rgba(34,197,94,.16);color:var(--green)}
.partial{background:rgba(245,158,11,.18);color:var(--amber)}
.todo{background:rgba(148,163,184,.2);color:var(--muted)}
.running{background:rgba(37,99,235,.16);color:var(--blue)}
.failed{background:rgba(220,38,38,.16);color:var(--red)}
.pending{background:rgba(148,163,184,.2);color:var(--muted)}
.health{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:.8rem}
.health .card{border-left:4px solid var(--line)}
.health .green{border-left-color:var(--green)}
.health .red{border-left-color:var(--red)}
.health .stale,.health .unknown{border-left-color:var(--amber)}
.health .label{font-size:1.02rem}
details{border:1px solid var(--line);border-radius:9px;padding:.5rem .75rem;margin:.4rem 0;background:var(--card)}
summary{cursor:pointer;font-weight:650}
pre{white-space:pre-wrap;word-break:break-word;background:var(--chip);border-radius:8px;
  padding:.7rem .85rem;max-height:420px;overflow:auto;font:12px/1.45 ui-monospace,Consolas,monospace}
.map{width:100%;max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px;background:#0d1117}
.feature-title{font-weight:600}
.note{color:var(--muted);font-size:.84rem}
.overview-pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:.8rem;margin:1rem 0}
.card-head{display:flex;justify-content:space-between;align-items:baseline;gap:.6rem;flex-wrap:wrap}
.kind-list{display:flex;flex-direction:column;gap:.55rem;margin-top:.65rem}
.kind-row{display:flex;flex-direction:column;gap:.22rem}
.kind-top{display:flex;justify-content:space-between;align-items:baseline;gap:.5rem;flex-wrap:wrap;
  font-size:.87rem;font-variant-numeric:tabular-nums}
.kind-name{font-weight:600}
.kind-meta{color:var(--muted);font-size:.79rem}
.pbar{display:flex;height:8px;width:100%;background:var(--chip);border-radius:999px;overflow:hidden;
  border:1px solid var(--line)}
.pbar > span{display:block;height:100%}
.pbar .seg-named{background:var(--blue)}
.pbar .seg-guessed{background:var(--amber)}
.pbar .seg-doc{background:var(--green)}
.pbar .seg-match{background:var(--purple)}
.pbar-cell{min-width:110px}
.legend-inline{display:flex;flex-wrap:wrap;gap:.3rem .85rem;font-size:.78rem;color:var(--muted);margin-top:.6rem}
.dot{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:.28rem;vertical-align:-1px}
.dot-blue{background:var(--blue)}
.dot-amber{background:var(--amber)}
.dot-green{background:var(--green)}
hr{border:0;border-top:1px solid var(--line);margin:1.5rem 0}
ul{margin:.35rem 0 .8rem;padding-left:1.3rem}
li{margin:.18rem 0}
"""

NAV = [
    ("progress.html", "Overview"),
    ("map.html", "Coverage map"),
    ("progress.svg", "Coverage SVG"),
    ("history.html", "History"),
    ("tasks.html", "Worker board"),
    ("progress.json", "Raw JSON"),
]


def nav_html(active: str) -> str:
    parts = []
    for href, label in NAV:
        cls = ' class="here"' if href == active else ""
        parts.append(f'<a href="{href}"{cls}>{esc(label)}</a>')
    return '<nav aria-label="Progress pages">' + "".join(parts) + "</nav>"


def page_html(title: str, active: str, subtitle: str, body: str, refresh: int | None = None) -> str:
    meta = '<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">'
    if refresh:
        meta += f'\n<meta http-equiv="refresh" content="{refresh}">'
    return f"""<!doctype html>
<html lang="en">
<head>
{meta}
<meta name="color-scheme" content="light dark">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
{nav_html(active)}
<h1>{esc(title)}</h1>
<p class="muted">{subtitle}</p>
{body}
<hr>
<p class="small muted">Generated by <code>tools/progress.py</code>. Static HTML/SVG/JSON; the
<a href="map.html">coverage map</a> is one self-contained canvas page with embedded data &mdash;
no external scripts and no network access. Raw numbers: <a href="progress.json">progress.json</a>.</p>
</body>
</html>
"""


def kpi_card(label: str, value: str, sub: str = "") -> str:
    return (
        '<div class="card"><div class="label">' + esc(label) + "</div>"
        f'<div class="value">{value}</div>'
        f'<div class="sub">{sub}</div></div>'
    )


def status_chip(status: str) -> str:
    cls = status if status in ("done", "partial", "todo", "running", "failed", "pending") else "todo"
    return f'<span class="chip {cls}">{esc(status.upper())}</span>'


def health_card(title: str, entry: dict) -> str:
    status = str(entry.get("status") or "unknown")
    detail = esc(entry.get("detail") or "")
    when = esc(entry.get("when") or "")
    source = esc(entry.get("source") or "")
    extras = ""
    if entry.get("failed"):
        extras = '<div class="note">failed: ' + esc(", ".join(entry["failed"])) + "</div>"
    meta = " &middot; ".join(x for x in (when, source) if x)
    return (
        f'<div class="card {status}"><div class="label">{esc(title)}</div>'
        f'<div class="num">{esc(entry.get("label") or "unknown")}</div>'
        f'<div class="note">{detail}</div>{extras}'
        f'<div class="sub">{meta}</div></div>'
    )


# --------------------------------------------------------------------------- #
# progress.html
# --------------------------------------------------------------------------- #
def stacked_bar_html(primary: int, secondary: int, total: int, *,
                     primary_cls: str = "seg-named",
                     secondary_cls: str = "seg-guessed",
                     title: str = "") -> str:
    w_primary = min(100.0, max(0.0, pct(primary, total)))
    w_secondary = min(max(0.0, 100.0 - w_primary), max(0.0, pct(secondary, total)))
    segs = []
    if w_primary > 0:
        segs.append(f'<span class="{primary_cls}" style="width:{w_primary:.2f}%"></span>')
    if w_secondary > 0:
        segs.append(f'<span class="{secondary_cls}" style="width:{w_secondary:.2f}%"></span>')
    title_attr = f' title="{esc(title)}"' if title else ""
    return f'<div class="pbar"{title_attr}>{"".join(segs)}</div>'


def _type_kind_block(types: dict, key: str, batch_kind: str) -> dict:
    raw = types.get(key)
    if isinstance(raw, dict):
        return raw
    batches = types.get("batches") if isinstance(types.get("batches"), dict) else {}
    b_entry = batches.get(batch_kind)
    b_done = b_entry.get("done", 0) if isinstance(b_entry, dict) else 0
    b_tot = b_entry.get("total", 0) if isinstance(b_entry, dict) else _as_int(b_entry, 0)
    tot = _as_int(types.get(f"{key}_total"), 0)
    nmd = _as_int(types.get(f"{key}_named"), 0)
    return _summarize_kind(tot, {}, nmd, batch_kind, b_done, b_tot)


def html_progress(native: dict, scripts: dict, assets: dict, editor: dict,
                  build: dict, types: dict, stamp: str) -> str:
    func_series = [  # used by the KPI cards and the badge
        ("Named functions", native["pct_named"], f'{native["named"]:,} / {native["total"]:,}'),
        ("Documented", native["pct_documented"],
         f'{native["documented"]:,} / {native["total"]:,}'),
        ("Assets converted", assets["pct_converted"],
         f'{assets["converted_total"]:,} / {assets["source_total"]:,}'),
        ("Editor features", editor["percent"],
         f'{editor["done"]} done, {editor["partial"]} partial, {editor["todo"]} todo'),
    ]
    cards = "".join(kpi_card(label, f"{value:.1f}%", sub) for label, value, sub in func_series)

    proposals = native["proposals"]
    fn_total = native["total"]
    fn_card_html = (
        '<div class="card" id="functions-card">'
        '<div class="card-head"><div class="label"><a href="#native">Native functions</a></div>'
        f'<span class="kind-meta">batches {proposals["batches"]:,}</span></div>'
        f'<div class="value">{native["pct_named"]:.1f}%</div>'
        f'<div class="sub">{native["named"]:,} named + {native["proposed"]:,} proposed of '
        f'{fn_total:,} &middot; {native["matching_c"]:,} matching C</div>'
        '<div class="kind-list">'
        '<div class="kind-row"><div class="kind-top">'
        '<span class="kind-name">Functions</span>'
        f'<span><strong>{native["named"]:,}</strong>'
        + (f' <span class="kind-meta">(+{native["proposed"]:,} maybe_)</span>'
           if native["proposed"] else "")
        + f' / {fn_total:,} ({native["pct_named"]:.1f}%)</span></div>'
        + stacked_bar_html(
            native["named"], native["proposed"], fn_total,
            title=f'{native["named"]:,} named, {native["proposed"]:,} proposed of {fn_total:,}',
        )
        + '</div>'
        '<div class="kind-row"><div class="kind-top">'
        '<span class="kind-name">Documented</span>'
        f'<span><strong>{native["documented"]:,}</strong> / {fn_total:,} '
        f'({native["pct_documented"]:.1f}%)</span></div>'
        + stacked_bar_html(
            native["documented"], 0, fn_total, primary_cls="seg-doc",
            title=f'{native["documented"]:,} documented of {fn_total:,}',
        )
        + '</div>'
        '<div class="kind-row"><div class="kind-top">'
        '<span class="kind-name">Decompiled C</span>'
        f'<span><strong>{native["decompiled"]:,}</strong> / {fn_total:,} '
        f'({pct(native["decompiled"], fn_total):.1f}%)</span></div>'
        + stacked_bar_html(
            native["decompiled"], 0, fn_total,
            title=f'{native["decompiled"]:,} decompiled of {fn_total:,}',
        )
        + '</div>'
        '</div>'
        '<div class="legend-inline">'
        '<span><span class="dot dot-blue"></span>named (&ge;0.5)</span>'
        '<span><span class="dot dot-amber"></span>proposed (maybe_)</span>'
        '<span><span class="dot dot-green"></span>documented</span>'
        '</div>'
        '</div>'
    )

    type_rows_spec = [
        ("globals", "G", "Globals", "G_*", "real data objects (.rodata / .data / .bss)"),
        ("classes", "S", "Classes", "S_*", "object layouts with field evidence"),
        ("fields", "S", "Struct fields", "S_*", "real field names replacing f_XXXX"),
        ("locals", "V", "Locals", "V_*", "placeholder tokens (iVar2, local_44, argN)"),
    ]
    type_card_rows = []
    type_table_rows = []
    for key, bkind, label, prefix_label, note_txt in type_rows_spec:
        blk = _type_kind_block(types, key, bkind)
        b_info = blk.get("batches") if isinstance(blk.get("batches"), dict) else {}
        b_done = _as_int(b_info.get("done"), 0)
        b_tot = _as_int(b_info.get("total"), 0)
        bar = stacked_bar_html(
            blk["named"], blk["guessed"], blk["total"],
            title=(f'{label}: {blk["named"]:,} named, {blk["guessed"]:,} guessed, '
                   f'{blk["merged"]:,} merged of {blk["total"]:,}'),
        )
        guessed_meta = (
            f' <span class="kind-meta">(+{blk["guessed"]:,} maybe_)</span>'
            if blk["guessed"] else ""
        )
        merged_meta = f' &middot; <span class="kind-meta">{blk["merged"]:,} merged</span>'
        type_card_rows.append(
            '<div class="kind-row"><div class="kind-top">'
            f'<span><span class="kind-name">{esc(label)}</span> '
            f'<span class="kind-meta"><code>{esc(prefix_label)}</code> '
            f'batches {b_done:,}/{b_tot:,}</span></span>'
            f'<span><strong>{blk["named"]:,}</strong>{guessed_meta} / {blk["total"]:,} '
            f'({blk["pct_named"]:.1f}%){merged_meta}</span></div>'
            f'{bar}</div>'
        )
        type_table_rows.append(
            "<tr>"
            f'<td>{esc(label)} <code>({esc(prefix_label)})</code>'
            f'<div class="note">{esc(note_txt)}</div></td>'
            f'<td class="num">{blk["total"]:,}</td>'
            f'<td class="num">{blk["answered"]:,}</td>'
            f'<td class="num">{blk["named"]:,}</td>'
            f'<td class="num">{blk["guessed"]:,}</td>'
            f'<td class="num">{blk["merged"]:,}</td>'
            f'<td class="num pct">{blk["pct_named"]:.1f}%</td>'
            f'<td class="pbar-cell">{bar}</td>'
            f'<td class="num">{b_done:,} / {b_tot:,}</td>'
            "</tr>"
        )

    t_batches = types.get("batches") if isinstance(types.get("batches"), dict) else {}
    tb_done = _as_int(t_batches.get("done"), 0)
    tb_total = _as_int(t_batches.get("total"), 0)
    t_total = _as_int(types.get("total"), 0)
    t_answered = _as_int(types.get("answered"), 0)
    t_named = _as_int(types.get("named"), 0)
    t_guessed = _as_int(types.get("guessed"), 0)
    t_merged = _as_int(types.get("merged"), 0)
    t_pct_named = float(types.get("pct_named") or 0.0)
    t_malformed = _as_int(types.get("malformed_files"), 0)
    malformed_chip = (
        f' &middot; <span class="kind-meta">{t_malformed} malformed file(s) skipped</span>'
        if t_malformed else ""
    )

    types_card_html = (
        '<div class="card" id="data-types-card">'
        '<div class="card-head"><div class="label"><a href="#types">Data &amp; types</a></div>'
        f'<span class="kind-meta">batches {tb_done:,} / {tb_total:,} done</span></div>'
        f'<div class="value">{t_pct_named:.1f}%</div>'
        f'<div class="sub">{t_named:,} named + {t_guessed:,} guessed of {t_total:,} '
        f'&middot; {t_merged:,} merged into headers/maps{malformed_chip}</div>'
        f'<div class="kind-list">{"".join(type_card_rows)}</div>'
        '<div class="legend-inline">'
        '<span><span class="dot dot-blue"></span>named (&ge;0.5)</span>'
        '<span><span class="dot dot-amber"></span>guessed (maybe_)</span>'
        '<span>merged = in <code>include/dqxi</code> / <code>merged/</code></span>'
        '</div>'
        '</div>'
    )
    overview_pair = f'<div class="overview-pair">{fn_card_html}{types_card_html}</div>'

    # Native table.
    rows = []
    for row in native["subsystems"]:
        rows.append(
            "<tr>"
            f'<td>{esc(row["name"])}<div class="note">{esc(row["first_address"])} &ndash; {esc(row["last_address"])}</div></td>'
            f'<td class="num">{row["total"]:,}</td>'
            f'<td class="num">{row["named"]:,}</td>'
            f'<td class="num">{row["proposed"]:,}</td>'
            f'<td class="num">{row["documented"]:,}</td>'
            f'<td class="num">{row["matching_c"]:,}</td>'
            f'<td class="num pct">{row["pct_named"]:.1f}%</td>'
            f'<td class="num pct">{row["pct_documented"]:.1f}%</td>'
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="8" class="muted">No native index yet &mdash; run P0_regen.</td></tr>')
    rows.append(
        '<tr class="total">'
        f'<td>Total</td><td class="num">{native["total"]:,}</td>'
        f'<td class="num">{native["named"]:,}</td><td class="num">{native["proposed"]:,}</td>'
        f'<td class="num">{native["documented"]:,}</td><td class="num">{native["matching_c"]:,}</td>'
        f'<td class="num pct">{native["pct_named"]:.1f}%</td>'
        f'<td class="num pct">{native["pct_documented"]:.1f}%</td>'
        "</tr>"
    )
    native_notes = "".join(f'<li>{esc(n)}</li>' for n in native.get("notes", []))
    native_html = f"""
<h2 id="native">Native code</h2>
<p class="muted">Grouped exactly like <code>tools/organize_ghidra.py</code> /
<code>decomp/ghidra/by_subsystem/</code>; rows ordered by domain, functions by address.
Source: <code>{esc(native["source"])}</code>.</p>
<div class="grid">
  {kpi_card("Entry points", f'{native["total"]:,}', "retail functions / thunks")}
  {kpi_card("Decompiled C", f'{native["decompiled"]:,}', f'{native.get("covered_by_container", 0):,} covered, {native.get("unresolved", 0):,} unresolved')}
  {kpi_card("Named", f'{native["named"]:,}', f'{native["pct_named"]:.2f}% of all functions')}
  {kpi_card("Matching C", f'{native["matching_c"]:,}', "verified against retail bytes")}
</div>
<table>
<thead><tr><th>Subsystem</th><th>Total</th><th>Named</th><th>Proposed</th>
<th>Documented</th><th>Matching C</th><th>% named</th><th>% documented</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="small">Naming proposals: <strong>{proposals["addresses"]:,}</strong> addresses in
<strong>{proposals["batches"]}</strong> batch file(s), {proposals["high_confidence"]:,} high-confidence.
Verified C replacements: <strong>{native["matching_c"]:,}</strong>.</p>
<ul class="small">{native_notes}</ul>
<p><a href="map.html"><img class="map" src="progress.svg" alt="Native function coverage map (opens the interactive map)"></a></p>
<p class="note">Each cell is one native function: grey unnamed, amber proposed, blue named,
green documented, purple matching C. Open the <a href="map.html">interactive coverage map</a>
to hover a cell for its address, name, size and summary, filter by state, search, and jump to the
readable C. <a href="progress.svg">progress.svg</a> is the static version for README badges.</p>
"""

    # Types / globals / locals (S0_types_plan, worker out/*.json + M2/M3 merges).
    batch_parts = []
    for k in ("G", "S", "V"):
        bk = t_batches.get(k)
        if isinstance(bk, dict):
            batch_parts.append(f'{k} {bk.get("done", 0)}/{bk.get("total", 0)}')
        elif bk is not None:
            batch_parts.append(f"{k} {bk}")
    batch_note = ", ".join(batch_parts)
    type_table_rows.append(
        '<tr class="total">'
        f'<td>Total</td>'
        f'<td class="num">{t_total:,}</td>'
        f'<td class="num">{t_answered:,}</td>'
        f'<td class="num">{t_named:,}</td>'
        f'<td class="num">{t_guessed:,}</td>'
        f'<td class="num">{t_merged:,}</td>'
        f'<td class="num pct">{t_pct_named:.1f}%</td>'
        f'<td class="pbar-cell">{stacked_bar_html(t_named, t_guessed, t_total)}</td>'
        f'<td class="num">{tb_done:,} / {tb_total:,}</td>'
        "</tr>"
    )
    malformed_note = ""
    if t_malformed:
        bad_names = ", ".join(types.get("malformed") or [])
        malformed_note = (
            f' Malformed files skipped: <strong>{t_malformed:,}</strong>'
            + (f" (<code>{esc(bad_names)}</code>)." if bad_names else ".")
        )
    types_html = f"""
<h2 id="types">Data &amp; types</h2>
<p class="muted">Phase 2 readability: global variables (<code>G_###</code>), classes &amp; struct
fields (<code>S_###</code>) and local variables (<code>V_###</code>). Worker answers come live from
<code>orchestration/types/out/</code> (<strong>named</strong> = confidence &ge; 0.5 without
<code>maybe_</code>; <strong>guessed</strong> = <code>maybe_</code> or confidence &lt; 0.5);
<strong>merged</strong> counts what <code>M2_types_merge</code> / <code>M3_vars_merge</code> have
written into <code>include/dqxi/*.h</code> and <code>orchestration/types/merged/</code>.
Source: <code>{esc(types["source"])}</code>{f" (demo merge)" if types.get("demo") else ""}.</p>
<table>
<thead><tr><th>Kind</th><th>Total</th><th>Answered</th><th>Named</th><th>Guessed</th>
<th>Merged</th><th>% named</th><th>Progress</th><th>Batches</th></tr></thead>
<tbody>{''.join(type_table_rows)}</tbody></table>
<p class="small">Batches (done / total): <strong>{esc(batch_note or "not generated yet")}</strong>
({tb_done:,} / {tb_total:,} done). Last validation/merge report errors:
<strong>{types["errors"]:,}</strong>, warnings: <strong>{types["warnings"]:,}</strong>.{malformed_note}</p>
"""

    # Scripts.
    scripts_html = f"""
<h2 id="scripts">Scripts (Squirrel CNUT)</h2>
<table>
<thead><tr><th>Stage</th><th>Count</th><th>% of source</th><th>Evidence</th></tr></thead>
<tbody>
<tr><td>CNUT scripts in the game</td><td class="num">{scripts["total"]:,}</td>
    <td class="num">100.0%</td><td class="note">{esc(scripts["source"])}</td></tr>
<tr><td>Decompiled to readable <code>.nut</code></td><td class="num">{scripts["decompiled"]:,}</td>
    <td class="num pct">{scripts["pct_decompiled"]:.1f}%</td>
    <td class="note">{scripts["functions"]:,} Squirrel functions</td></tr>
<tr><td>Recompile-verified back to CNUT</td><td class="num">{scripts["recompile_verified"]:,}</td>
    <td class="num pct">{scripts["pct_recompiled"]:.1f}%</td>
    <td class="note">{esc(scripts["recompile_source"])}</td></tr>
</tbody></table>
"""

    # Assets.
    asset_rows = []
    for fam in assets["families"]:
        asset_rows.append(
            "<tr>"
            f'<td>{esc(fam["label"])}</td>'
            f'<td class="num">{fam["source"]:,}</td>'
            f'<td class="num">{fam["converted"]:,}</td>'
            f'<td class="num">{fam["editable"]:,}</td>'
            f'<td class="num pct">{fam["pct_converted"]:.1f}%</td>'
            f'<td class="num pct">{fam["pct_editable"]:.1f}%</td>'
            "</tr>"
        )
    asset_rows.append(
        '<tr class="total">'
        f'<td>Total</td><td class="num">{assets["source_total"]:,}</td>'
        f'<td class="num">{assets["converted_total"]:,}</td>'
        f'<td class="num">{assets["editable_total"]:,}</td>'
        f'<td class="num pct">{assets["pct_converted"]:.1f}%</td>'
        f'<td class="num pct">{assets["pct_editable"]:.1f}%</td></tr>'
    )
    assets_html = f"""
<h2 id="assets">Assets</h2>
<p class="muted">Source counts come from the <code>game_data/</code> tree when generated, else the
documented audit baseline. Converted counts come from <code>game_assets/</code> or
<code>audit/ASSET_VERIFICATION.json</code>. Round-trip-editable means a same-size write-back tool
exists; it is a capability count, not a per-file verification.</p>
<table>
<thead><tr><th>Family</th><th>Source</th><th>Converted</th><th>Round-trip editable</th>
<th>% converted</th><th>% editable</th></tr></thead>
<tbody>{''.join(asset_rows)}</tbody></table>
<p class="note">Source: {esc(assets["source"])}. Text is 0 until the E2 dialogue extractor produces
readable message files.</p>
"""

    # Editor checklist.
    feature_html = []
    for group in editor["groups"]:
        items = "".join(
            "<tr>"
            f'<td><span class="feature-title">{esc(item["title"])}</span>'
            f'<div class="note">{esc(item["notes"])}</div></td>'
            f'<td>{status_chip(item["status"])}</td>'
            "</tr>"
            for item in group["features"]
        )
        feature_html.append(f"<h3>{esc(group['name'])}</h3><table><tbody>{items}</tbody></table>")
    editor_html = f"""
<h2 id="editor">Editor features</h2>
<p class="muted">Checklist lives in <a href="features.json"><code>progress/features.json</code></a>
(edit it to update this page). Completion weights <strong>done = 1, partial = 0.5</strong>:
<strong>{editor["percent"]:.1f}%</strong> ({editor["done"]} done, {editor["partial"]} partial,
{editor["todo"]} todo of {editor["total"]}).</p>
{''.join(feature_html)}
"""

    # Build health.
    build_html = f"""
<h2 id="build">Build health</h2>
<div class="health">
  {health_card("Bit-matching rebuild", build["bitmatch"])}
  {health_card("Tests", build["tests"])}
  {health_card("Project verification", build["verification"])}
</div>
<p class="note">The bit-match check hashes <code>build/code.bin</code> against the retail
SHA-256. When the artifact is absent the last audit snapshot is shown as stale, never as green.</p>
"""

    notes_html = """
<h2 id="notes">Notes / counting rules</h2>
<ul class="small">
<li><strong>Named</strong>: the effective function name is no longer a decompiler/seed
placeholder (<code>FUN_</code>, <code>func_</code>, <code>sub_</code>, <code>thunk_</code>,
<code>LAB_</code>, <code>maybe_</code>, <code>DAT_</code>). A high-confidence naming proposal counts
as named even before M1_merge_names.</li>
<li><strong>Proposed</strong>: a naming proposal exists but the name is provisional
(<code>maybe_</code> prefix or confidence &lt; 0.5), so it stays amber rather than blue.</li>
<li><strong>Documented</strong>: the function carries a human summary &mdash; a summary field in
<code>functions_merged.jsonl</code>, a naming-proposal summary of at least 20 characters, or a
comment block in its readable C beyond the Ghidra export header. The generic "Regenerated by
Ghidra" header does not count.</li>
<li><strong>Matching C</strong>: only functions proven byte-identical by
<code>build/replacement_report.json</code> (or the last
<code>audit/PROJECT_VERIFICATION.json</code> snapshot). Readable Ghidra C is not matching C.</li>
<li><strong>Data &amp; types</strong>: worker answers in
<code>orchestration/types/out/{G,S,V}_*.json</code> count as <strong>named</strong> when confidence
&ge; 0.5 without a <code>maybe_</code> prefix, and <strong>guessed</strong> when provisional
(<code>maybe_</code> or confidence &lt; 0.5). <strong>Merged</strong> counts declarations and maps
actually written to <code>include/dqxi/*.h</code> and <code>orchestration/types/merged/</code> by
<code>M2_types_merge</code> / <code>M3_vars_merge</code>.</li>
<li><strong>Scripts</strong>: total = CNUT containers; decompiled = <code>scripts_ok</code> or live
<code>*.decompiled.nut</code>; recompile-verified needs an explicit recompile manifest or
<code>*.recompiled.*</code> output. Decompiling is not recompiling.</li>
<li><strong>Assets</strong>: converted means a standard-format output exists, not that the asset is
semantically complete (for example 4,779 of 10,542 BCH files yield meshes). Editable counts are
capability counts for the write-back tools; tables stay at 0 until a general BXON writer exists.</li>
<li><strong>Editor</strong>: checklist from <code>progress/features.json</code>, weighted
done=1 / partial=0.5. It is a human judgement, not a test result.</li>
<li><strong>Build health</strong>: parsed from <code>build/</code> artifacts and audit reports.
"Stale" means a previous run passed but the artifact/log is missing now.</li>
<li>Every number is regenerated from files on disk. Missing generated data shows zero or
&ldquo;not generated yet&rdquo; rather than an error.</li>
</ul>
"""

    badges = (
        '<div class="badge-row">'
        '<a href="badge-functions.svg"><img src="badge-functions.svg" alt="functions named badge"></a>'
        '<a href="badge-types.svg"><img src="badge-types.svg" alt="data and types badge"></a>'
        '<a href="badge-assets.svg"><img src="badge-assets.svg" alt="assets converted badge"></a>'
        '<a href="badge-editor.svg"><img src="badge-editor.svg" alt="editor features badge"></a>'
        "</div>"
    )
    body = f"""
<div class="grid">{cards}</div>
{overview_pair}
{badges}
{native_html}
{types_html}
{scripts_html}
{assets_html}
{editor_html}
{build_html}
{notes_html}
<p><a href="history.html">Progress history</a> (one point per day) &middot;
<a href="tasks.html">Worker board</a> &middot; <a href="progress.json">Raw progress.json</a></p>
"""
    return page_html("DQXI 3DS - project progress", "progress.html",
                     f"Generated {esc(stamp)} &middot; readable source, converted assets, "
                     f"editor and build health.", body)


# --------------------------------------------------------------------------- #
# coverage map SVG
# --------------------------------------------------------------------------- #
STATUS_COLORS = {
    "unnamed": "#4b5563",
    "proposed": "#d97706",
    "named": "#2563eb",
    "documented": "#16a34a",
    "matching": "#9333ea",
}
STATUS_LABELS = {
    "unnamed": "unnamed",
    "proposed": "proposed",
    "named": "named",
    "documented": "documented",
    "matching": "matching C",
}
STATUS_ORDER = ["unnamed", "proposed", "named", "documented", "matching"]


def coverage_svg(native: dict) -> str:
    functions = native.get("_functions") or []
    if not functions:
        return """<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="180" viewBox="0 0 900 180" preserveAspectRatio="xMinYMin meet" style="height:auto;background:#0d1117;display:block" role="img">
<title>DQXI 3DS native coverage map (not generated yet)</title>
<rect width="100%" height="100%" fill="#0d1117"/>
<text x="24" y="40" fill="#e6edf3" font-family="Verdana, sans-serif" font-size="16" font-weight="700">DQXI 3DS native code coverage</text>
<text x="24" y="72" fill="#9aa7b8" font-family="Verdana, sans-serif" font-size="12">No per-function index yet.</text>
<text x="24" y="94" fill="#9aa7b8" font-family="Verdana, sans-serif" font-size="12">Run P0_regen (or tools/organize_ghidra.py) to generate decomp/ghidra, then rerun tools/progress.py.</text>
<text x="24" y="116" fill="#9aa7b8" font-family="Verdana, sans-serif" font-size="12">Interactive map: progress/map.html</text>
</svg>
"""

    cell, gap, cols = 4, 1, 160
    left, top = 18, 56
    step = cell + gap
    width = left * 2 + cols * step
    by_domain: dict[str, list[dict]] = {d: [] for d in DOMAIN_ORDER}
    for fn in functions:
        by_domain.setdefault(fn["domain"], []).append(fn)

    blocks = []
    y = top
    for domain in DOMAIN_ORDER:
        group = by_domain.get(domain, [])
        if not group:
            continue
        rows = (len(group) + cols - 1) // cols
        block_h = 16 + rows * step
        paths: dict[str, list[str]] = {s: [] for s in STATUS_ORDER}
        for index, fn in enumerate(group):
            col, row = index % cols, index // cols
            x = left + col * step
            yy = y + 16 + row * step
            status = fn["status"] if fn["status"] in paths else "unnamed"
            paths[status].append(f"M{x} {yy}h{cell}v{cell}h-{cell}z")
        rects = []
        for status in STATUS_ORDER:
            if paths[status]:
                rects.append(
                    f'<path fill="{STATUS_COLORS[status]}" d="{"".join(paths[status])}"/>'
                )
        blocks.append(
            f'<g><text x="{left}" y="{y + 10}" fill="#c9d4e3" font-family="Verdana, sans-serif" '
            f'font-size="11" font-weight="700">{esc(domain)}</text>'
            f'<text x="{width - left}" y="{y + 10}" text-anchor="end" fill="#7d8a9c" '
            f'font-family="Verdana, sans-serif" font-size="10">{len(group):,} functions &#183; '
            f'{esc(group[0]["addr"])}&#8211;{esc(group[-1]["addr"])}</text>'
            f'<rect x="{left}" y="{y + 16}" width="{cols * step}" height="{rows * step}" '
            f'fill="#111827" opacity=".55" rx="2"/>'
            + "".join(rects) + "</g>"
        )
        y += block_h + 12

    legend_y = y + 12
    legend = []
    x = left
    counts = Counter(fn["status"] for fn in functions)
    for status in STATUS_ORDER:
        label = f'{STATUS_LABELS[status]} ({counts.get(status, 0):,})'
        legend.append(
            f'<rect x="{x}" y="{legend_y}" width="10" height="10" rx="2" fill="{STATUS_COLORS[status]}"/>'
            f'<text x="{x + 15}" y="{legend_y + 9}" fill="#c9d4e3" '
            f'font-family="Verdana, sans-serif" font-size="11">{esc(label)}</text>'
        )
        x += 18 + 7 * len(label)
    height = legend_y + 34
    desc = (f"{counts.get('matching', 0):,} matching C, {counts.get('documented', 0):,} documented, "
            f"{counts.get('named', 0):,} named, {counts.get('proposed', 0):,} proposed, "
            f"{counts.get('unnamed', 0):,} unnamed of {len(functions):,} native functions.")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" style="height:auto;background:#0d1117;display:block" role="img">
<title>DQXI 3DS native code coverage map</title>
<desc>{esc(desc)}</desc>
<rect width="100%" height="100%" fill="#0d1117"/>
<text x="{left}" y="24" fill="#e6edf3" font-family="Verdana, sans-serif" font-size="16" font-weight="700">DQXI 3DS native code coverage</text>
<text x="{left}" y="42" fill="#9aa7b8" font-family="Verdana, sans-serif" font-size="11">{esc(desc)}</text>
<text x="{width - left}" y="42" text-anchor="end" fill="#7d8a9c" font-family="Verdana, sans-serif" font-size="10">hover/search: progress/map.html</text>
{''.join(blocks)}
{''.join(legend)}
</svg>
"""


# --------------------------------------------------------------------------- #
# interactive coverage map (progress/map.html)
# --------------------------------------------------------------------------- #
def build_map_data(native: dict, stamp: str) -> dict:
    """Compact JSON payload for the canvas map.

    Functions are re-ordered so that the known subsystem blocks come first and the
    huge ``General_Procedures`` bucket is split into 64 KiB address ranges. Each
    function is a positional array to keep the embedded JSON small:
    ``[address, name, size, statusIndex, domainIndex, summary, readablePath]``.
    """
    functions = native.get("_functions") or []
    by_domain: dict[str, list[dict]] = {}
    for fn in functions:
        by_domain.setdefault(fn["domain"], []).append(fn)

    domains = list(DOMAIN_ORDER)
    for fn in functions:
        if fn["domain"] not in domains:
            domains.append(fn["domain"])
    domain_index = {name: i for i, name in enumerate(domains)}
    status_index = {name: i for i, name in enumerate(STATUS_ORDER)}

    ordered: list[dict] = []
    sections: list[dict] = []

    def add_section(label: str, kind: str, group: list[dict], note: str = "") -> None:
        if not group:
            return
        start = len(ordered)
        ordered.extend(group)
        sections.append({
            "label": label,
            "kind": kind,
            "start": start,
            "count": len(group),
            "named": sum(1 for f in group
                         if f["status"] in ("named", "documented", "matching")),
            "first": group[0]["addr"],
            "last": group[-1]["addr"],
            "note": note,
        })

    for domain in domains:
        if domain == GENERAL:
            continue
        group = sorted(by_domain.get(domain, []), key=lambda f: f["address"])
        add_section(domain, "subsystem", group)

    general = sorted(by_domain.get(GENERAL, []), key=lambda f: f["address"])
    if general:
        buckets: dict[int, list[dict]] = {}
        for fn in general:
            buckets.setdefault(fn["address"] >> 16, []).append(fn)
        sections.append({
            "label": "General procedures \u2014 no subsystem match",
            "kind": "divider",
            "start": len(ordered),
            "count": 0,
            "named": 0,
            "first": "",
            "last": "",
            "note": (f"{len(general):,} functions grouped into {len(buckets)} labelled "
                     "64 KiB address ranges"),
        })
        for bucket in sorted(buckets):
            group = buckets[bucket]
            add_section(f"0x{bucket:04X}xxxx", "range", group)

    rows = []
    for fn in ordered:
        rows.append([
            fn["address"],
            fn["name"],
            _as_int(fn.get("size")),
            status_index.get(fn["status"], 0),
            domain_index.get(fn["domain"], len(domains) - 1),
            fn.get("summary") or fn.get("proposal_summary") or "",
            readable_relpath(fn.get("file")),
        ])

    return {
        "generated": stamp,
        "statuses": STATUS_ORDER,
        "labels": [STATUS_LABELS[s] for s in STATUS_ORDER],
        "colors": [STATUS_COLORS[s] for s in STATUS_ORDER],
        "domains": domains,
        "sections": sections,
        "functions": rows,
        "total": len(rows),
    }


MAP_CSS = """
:root{color-scheme:dark;--bg:#0b0f16;--panel:#101824;--fg:#e6edf3;--mut:#8fa0b6;
  --line:#22304a;--accent:#a78bfa}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--fg)}
body{font:14px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Verdana,sans-serif;min-height:100vh}
a{color:#7dd3fc;text-decoration:none}
a:hover{text-decoration:underline}
header{padding:14px clamp(10px,2vw,26px) 0}
nav{display:flex;flex-wrap:wrap;gap:.35rem .9rem;padding:.55rem .8rem;background:var(--panel);
  border:1px solid var(--line);border-radius:9px;margin:0 0 14px}
nav a{font-weight:600}
nav .here{color:var(--fg);text-decoration:none;border-bottom:2px solid var(--accent)}
h1{font-size:clamp(1.25rem,2.4vw,1.8rem);margin:.2em 0 .1em}
.sub{color:var(--mut);margin:.15em 0 .6em;max-width:110ch}
main{padding:0 clamp(8px,1.5vw,24px) 26px}
.controls{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;margin:0 0 10px;
  padding:8px 10px;background:var(--panel);border:1px solid var(--line);border-radius:9px}
.legend{display:flex;flex-wrap:wrap;gap:5px 14px;align-items:center;margin:0}
.legend label{display:inline-flex;align-items:center;gap:6px;cursor:pointer;white-space:nowrap}
.legend input{margin:0;accent-color:var(--accent)}
.sw{width:12px;height:12px;border-radius:2px;background:var(--c);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.18)}
.legend .n{color:var(--mut);font-variant-numeric:tabular-nums}
.search{display:flex;gap:8px;align-items:center;flex:1 1 240px;min-width:0}
.search input{flex:1;min-width:0;background:#0c1320;color:var(--fg);border:1px solid var(--line);
  border-radius:7px;padding:7px 10px;font:inherit}
.search input:focus{outline:2px solid rgba(167,139,250,.5);outline-offset:1px}
#matchinfo{color:var(--mut);font-size:.85rem;white-space:nowrap;min-width:4.5em}
.toggle{display:inline-flex;align-items:center;gap:6px;color:var(--mut);white-space:nowrap;
  cursor:pointer}
.toggle input{margin:0;accent-color:var(--accent)}
#mapwrap{position:relative;width:100%;border:1px solid var(--line);border-radius:9px;
  overflow:hidden;background:#0b0f16}
canvas{display:block;width:100%;touch-action:manipulation}
#ring{position:absolute;display:none;pointer-events:none;border:1px solid #fff;
  box-shadow:0 0 0 1px rgba(0,0,0,.7),0 0 8px rgba(255,255,255,.55);z-index:2}
#tip{position:fixed;z-index:50;display:none;max-width:min(400px,calc(100vw - 20px));
  padding:9px 11px;background:#131d2b;border:1px solid #35486a;border-radius:8px;
  box-shadow:0 10px 30px rgba(0,0,0,.55);pointer-events:none}
#tip .t-head{display:flex;gap:8px;align-items:center;justify-content:space-between;
  margin-bottom:2px}
#tip .t-addr{font:600 12px ui-monospace,Consolas,monospace}
#tip .t-state{font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;
  padding:1px 6px;border-radius:999px;color:#08101c}
#tip .t-name{font-weight:650;font-size:13px;word-break:break-word;margin:1px 0 2px}
#tip .t-meta{color:var(--mut);font-size:11.5px}
#tip .t-sum{color:#c3cede;font-size:12px;margin-top:5px;word-break:break-word}
#tip .t-open{color:#7dd3fc;font-size:11.5px;margin-top:5px}
.hint{color:var(--mut);font-size:.82rem;margin:8px 2px 0}
footer{padding:14px clamp(10px,2vw,26px) 30px;color:var(--mut);font-size:12px;
  border-top:1px solid var(--line);margin-top:16px}
footer code{color:#c3cede}
@media(max-width:520px){
  header{padding-top:10px}
  .controls{gap:8px 12px;padding:7px 8px}
  .legend{gap:4px 10px}
  .legend label{font-size:12.5px}
}
"""

MAP_JS = """
(function(){
  "use strict";
  var D = DATA;
  var canvas = document.getElementById("map");
  var wrap = document.getElementById("mapwrap");
  var ctx = canvas.getContext("2d");
  var tip = document.getElementById("tip");
  var ring = document.getElementById("ring");
  var q = document.getElementById("q");
  var matchinfo = document.getElementById("matchinfo");
  var sizeMode = document.getElementById("sizeMode");
  var boxes = Array.prototype.slice.call(document.querySelectorAll("input[data-state]"));
  var STATUS = D.statuses, COLORS = D.colors, LABELS = D.labels;
  var TOTAL = D.functions.length;
  var PAD = 10, GAP = 1, HEAD = 17, SECTION_GAP = 7, DIVIDER_H = 36;
  var active = new Set(STATUS);
  var matched = null, layout = null, hovered = null;

  function hex8(v){
    return "0x" + (v >>> 0).toString(16).toUpperCase().padStart(8, "0");
  }
  function fmtSize(n){
    if (!n) return "size unknown";
    if (n < 1024) return n.toLocaleString() + " B";
    return (n / 1024).toFixed(1) + " KiB (" + n.toLocaleString() + " B)";
  }
  function cellSize(w){
    if (w < 480) return 4;
    if (w < 720) return 5;
    if (w < 1100) return 6;
    if (w < 1600) return 7;
    if (w < 2400) return 9;
    if (w < 3200) return 11;
    return 13;
  }

  function computeLayout(){
    var cssW = Math.max(240, canvas.clientWidth || wrap.clientWidth || 240);
    var cell = cellSize(cssW);
    var step = cell + GAP;
    var cols = Math.max(1, Math.floor((cssW - PAD * 2 + GAP) / step));
    var y = PAD, secs = [];
    D.sections.forEach(function(s){
      if (s.kind === "divider"){
        secs.push({label:s.label, note:s.note, kind:s.kind, start:s.start, count:0,
                   named:0, y:y, cellY:y + DIVIDER_H, rows:0, cols:cols, cell:cell});
        y += DIVIDER_H + SECTION_GAP;
        return;
      }
      var rows = Math.max(1, Math.ceil(s.count / cols));
      secs.push({label:s.label, note:s.note || "", kind:s.kind, start:s.start,
                 count:s.count, named:s.named || 0, first:s.first, last:s.last,
                 y:y, cellY:y + HEAD, rows:rows, cols:cols, cell:cell});
      y += HEAD + rows * step + SECTION_GAP;
    });
    return {cssW:cssW, cell:cell, step:step, cols:cols, sections:secs, height:y + PAD};
  }

  function drawCell(x, y, cell, idx){
    var f = D.functions[idx], st = STATUS[f[3]];
    if (!active.has(st)) return;
    var hit = !matched || matched.has(idx);
    ctx.globalAlpha = (matched && !hit) ? 0.12 : 1;
    ctx.fillStyle = COLORS[f[3]];
    var side = cell;
    if (sizeMode.checked){
      var sz = f[2] || 0;
      var t = Math.min(1, Math.log2(1 + sz) / Math.log2(16385));
      side = Math.max(1, Math.round(cell * (0.45 + 0.55 * t)));
    }
    var off = Math.floor((cell - side) / 2);
    ctx.fillRect(x + off, y + off, side, side);
    if (matched && hit){
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, Math.max(1, cell - 1), Math.max(1, cell - 1));
    }
    ctx.globalAlpha = 1;
  }

  function draw(){
    layout = computeLayout();
    var h = layout.height;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.style.height = h + "px";
    canvas.width = Math.round(layout.cssW * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = "#0b0f16";
    ctx.fillRect(0, 0, layout.cssW, h);

    if (!TOTAL){
      ctx.fillStyle = "#c9d4e3";
      ctx.font = "600 14px system-ui,sans-serif";
      ctx.fillText("No per-function index yet.", PAD + 6, PAD + 28);
      ctx.fillStyle = "#8fa0b6";
      ctx.font = "12px system-ui,sans-serif";
      ctx.fillText("Run P0_regen (tools/organize_ghidra.py) and rerun tools/progress.py.",
                   PAD + 6, PAD + 50);
      return;
    }

    layout.sections.forEach(function(s){
      if (s.kind === "divider"){
        ctx.fillStyle = "#c9d4e3";
        ctx.font = "700 12px system-ui,sans-serif";
        ctx.textBaseline = "alphabetic";
        ctx.fillText(s.label, PAD, s.y + 14);
        ctx.fillStyle = "#7d8a9c";
        ctx.font = "11px system-ui,sans-serif";
        ctx.fillText(s.note, PAD, s.y + 29);
        ctx.fillStyle = "#1d2836";
        ctx.fillRect(PAD, s.y + DIVIDER_H - 6, layout.cssW - PAD * 2, 1);
        return;
      }
      if (s.kind === "subsystem"){
        ctx.fillStyle = "#0e1520";
        ctx.fillRect(PAD - 2, s.y + 1, layout.cssW - (PAD - 2) * 2,
                     HEAD + s.rows * layout.step - 2);
      }
      ctx.fillStyle = s.kind === "subsystem" ? "#dbe5f3" : "#aebccc";
      ctx.font = (s.kind === "subsystem" ? "700" : "600") + " 11px system-ui,sans-serif";
      ctx.textBaseline = "alphabetic";
      ctx.fillText(s.label + "  (" + s.count.toLocaleString() + ")", PAD, s.y + 11);
      if (layout.cssW > 720){
        ctx.fillStyle = "#718096";
        ctx.font = "10.5px system-ui,sans-serif";
        ctx.textAlign = "right";
        var meta = s.first + "\\u2013" + s.last + "  \\u00b7  " +
                   s.named.toLocaleString() + " named";
        ctx.fillText(meta, layout.cssW - PAD, s.y + 11);
        ctx.textAlign = "left";
      }
      ctx.fillStyle = "#1d2836";
      ctx.fillRect(PAD, s.y + HEAD - 4, layout.cssW - PAD * 2, 1);

      for (var i = 0; i < s.count; i++){
        var row = Math.floor(i / s.cols), col = i % s.cols;
        drawCell(PAD + col * layout.step, s.cellY + row * layout.step, s.cell, s.start + i);
      }
    });
  }

  function hitTest(px, py){
    if (!layout) return null;
    var secs = layout.sections, lo = 0, hi = secs.length - 1;
    while (lo <= hi){
      var mid = (lo + hi) >> 1, s = secs[mid];
      var bottom = (s.kind === "divider") ? s.y + DIVIDER_H + SECTION_GAP
                                          : s.cellY + s.rows * layout.step + SECTION_GAP;
      if (py < s.y){ hi = mid - 1; }
      else if (py >= bottom){ lo = mid + 1; }
      else {
        if (s.kind === "divider" || !s.rows || py < s.cellY) return null;
        var row = Math.floor((py - s.cellY) / layout.step);
        var col = Math.floor((px - PAD) / layout.step);
        if (col < 0 || col >= s.cols || row < 0 || row >= s.rows) return null;
        var i = row * s.cols + col;
        if (i >= s.count) return null;
        if (!active.has(STATUS[D.functions[s.start + i][3]])) return null;
        return {idx:s.start + i, x:PAD + col * layout.step, y:s.cellY + row * layout.step,
                cell:s.cell};
      }
    }
    return null;
  }

  function hideTip(){
    tip.style.display = "none";
    ring.style.display = "none";
    hovered = null;
  }

  function showTip(hit, ev){
    var f = D.functions[hit.idx];
    tip.replaceChildren();
    var head = document.createElement("div"); head.className = "t-head";
    var addr = document.createElement("span"); addr.className = "t-addr";
    addr.textContent = hex8(f[0]);
    var state = document.createElement("span"); state.className = "t-state";
    state.textContent = LABELS[f[3]];
    state.style.background = COLORS[f[3]];
    head.appendChild(addr); head.appendChild(state);
    var name = document.createElement("div"); name.className = "t-name";
    name.textContent = f[1];
    var meta = document.createElement("div"); meta.className = "t-meta";
    meta.textContent = fmtSize(f[2]) + " \\u00b7 subsystem: " + D.domains[f[4]] +
                       " \\u00b7 state: " + STATUS[f[3]];
    tip.appendChild(head); tip.appendChild(name); tip.appendChild(meta);
    if (f[5]){
      var sum = document.createElement("div"); sum.className = "t-sum";
      sum.textContent = f[5];
      tip.appendChild(sum);
    }
    if (f[6]){
      var open = document.createElement("div"); open.className = "t-open";
      open.textContent = "Click to open the readable C in a new tab";
      tip.appendChild(open);
    }
    tip.style.display = "block";
    var pad = 10, x = ev.clientX + 16, y = ev.clientY + 18;
    var r = tip.getBoundingClientRect();
    if (x + r.width > window.innerWidth - pad) x = ev.clientX - r.width - 14;
    if (y + r.height > window.innerHeight - pad) y = ev.clientY - r.height - 14;
    tip.style.left = Math.max(pad, x) + "px";
    tip.style.top = Math.max(pad, y) + "px";

    ring.style.display = "block";
    ring.style.left = hit.x + "px";
    ring.style.top = hit.y + "px";
    ring.style.width = hit.cell + "px";
    ring.style.height = hit.cell + "px";
    hovered = hit;
    canvas.style.cursor = f[6] ? "pointer" : "crosshair";
  }

  canvas.addEventListener("mousemove", function(ev){
    if (!layout) return;
    var rect = canvas.getBoundingClientRect();
    var sx = layout.cssW / (rect.width || 1);
    var sy = layout.height / (rect.height || 1);
    var hit = hitTest((ev.clientX - rect.left) * sx, (ev.clientY - rect.top) * sy);
    if (!hit){ hideTip(); canvas.style.cursor = "default"; return; }
    showTip(hit, ev);
  });
  canvas.addEventListener("mouseleave", hideTip);
  canvas.addEventListener("click", function(ev){
    if (!layout) return;
    var rect = canvas.getBoundingClientRect();
    var sx = layout.cssW / (rect.width || 1);
    var sy = layout.height / (rect.height || 1);
    var hit = hitTest((ev.clientX - rect.left) * sx, (ev.clientY - rect.top) * sy);
    if (!hit) return;
    var file = D.functions[hit.idx][6];
    if (file){
      window.open("../decomp/readable/" + encodeURI(file), "_blank", "noopener");
    }
  });

  function runSearch(){
    var raw = q.value.trim();
    if (!raw){ matched = null; matchinfo.textContent = ""; draw(); return; }
    var low = raw.toLowerCase();
    var hex = low.replace(/^0x/, "");
    var prefix = hex.replace(/x+$/, "");
    var isHex = /^[0-9a-f]{2,8}$/.test(prefix);
    matched = new Set();
    for (var i = 0; i < TOTAL; i++){
      var f = D.functions[i];
      var addr = hex8(f[0]).toLowerCase();
      var hit = f[1].toLowerCase().indexOf(low) !== -1 ||
                addr.indexOf(low) !== -1 ||
                D.domains[f[4]].toLowerCase().indexOf(low) !== -1;
      if (!hit && isHex && addr.slice(2).indexOf(prefix) !== -1) hit = true;
      if (hit) matched.add(i);
    }
    matchinfo.textContent = matched.size.toLocaleString() + " match" +
                            (matched.size === 1 ? "" : "es");
    draw();
  }

  var searchTimer = 0;
  q.addEventListener("input", function(){
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 120);
  });
  q.addEventListener("keydown", function(ev){
    if (ev.key !== "Enter" || !matched || !matched.size || !layout) return;
    var first = Infinity;
    matched.forEach(function(i){ if (i < first) first = i; });
    for (var k = 0; k < layout.sections.length; k++){
      var s = layout.sections[k];
      if (s.count && first >= s.start && first < s.start + s.count){
        var y = s.cellY + Math.floor((first - s.start) / s.cols) * layout.step;
        window.scrollTo({top: wrap.offsetTop + y - 70, behavior:"smooth"});
        break;
      }
    }
  });

  boxes.forEach(function(box){
    box.addEventListener("change", function(){
      if (box.checked) active.add(box.dataset.state);
      else active.delete(box.dataset.state);
      draw();
    });
  });
  sizeMode.addEventListener("change", draw);

  var resizeTimer = 0;
  function relayout(){
    hideTip();
    if (matched) runSearch();
    else draw();
  }
  window.addEventListener("resize", function(){
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(relayout, 120);
  });
  if (window.ResizeObserver){
    var lastW = 0;
    new ResizeObserver(function(entries){
      var w = entries[0].contentRect.width;
      if (Math.abs(w - lastW) > 1){ lastW = w; clearTimeout(resizeTimer);
        resizeTimer = setTimeout(relayout, 120); }
    }).observe(wrap);
  }

  draw();
})();
"""


def coverage_map_html(native: dict, stamp: str) -> str:
    """Self-contained interactive map page: dark, full-width, no network."""
    data = build_map_data(native, stamp)
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    counts = Counter(fn["status"] for fn in (native.get("_functions") or []))
    legend = "".join(
        f'<label><input type="checkbox" data-state="{status}" checked>'
        f'<span class="sw" style="--c:{STATUS_COLORS[status]}"></span>'
        f'{esc(STATUS_LABELS[status])} <span class="n">({counts.get(status, 0):,})</span></label>'
        for status in STATUS_ORDER
    )
    total = data["total"]
    named = native.get("named", 0)
    functions_txt = f"{total:,} functions" if total else "no per-function index yet"
    body = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark">
<title>DQXI 3DS - native code coverage map</title>
<style>{MAP_CSS}</style>
</head>
<body>
<header>
{nav_html("map.html")}
<h1>Native code coverage map</h1>
<p class="sub">{functions_txt} &mdash; one cell each, grouped by subsystem then by 64 KiB address
range. {named:,} named ({native.get("pct_named", 0):.2f}%), {native.get("matching_c", 0):,}
matching C. Hover a cell for address, name, size, state, subsystem and summary; click a cell to
open its readable C in a new tab (when the board server is running). Generated {esc(stamp)}.
Source: <code>{esc(native.get("source", "unavailable"))}</code>.</p>
<div class="controls">
  <div class="legend" role="group" aria-label="Filter by coverage state">{legend}</div>
  <div class="search">
    <input id="q" type="search" placeholder="Search name, address (0x0012xxxx) or subsystem"
           aria-label="Search function name, address or subsystem" autocomplete="off"
           spellcheck="false">
    <span id="matchinfo" aria-live="polite"></span>
  </div>
  <label class="toggle" title="The cell grid stays aligned; the filled square grows with function size.">
    <input id="sizeMode" type="checkbox"> weight cells by function size</label>
</div>
</header>
<main>
<noscript><p class="hint">The interactive map needs JavaScript. The static
<a href="progress.svg">progress.svg</a> and the raw <a href="progress.json">progress.json</a>
contain the same coverage data.</p></noscript>
<div id="mapwrap">
  <canvas id="map" role="img" aria-label="Coverage grid: one cell per native function, coloured by naming/documentation state"></canvas>
  <div id="ring"></div>
  <div id="tip" role="tooltip"></div>
</div>
<p class="hint">Colours: grey unnamed, amber proposed, blue named, green documented, purple
matching C. Uncheck a state to hide it; search dims non-matching cells and outlines the hits.
Unnamed functions are split by address so the map is no longer one grey wall. The static
<a href="progress.svg">progress.svg</a> remains for badges and README embeds.</p>
</main>
<footer>
<p>Counting rules are on the <a href="progress.html">overview page</a>. Raw data:
<a href="progress.json">progress.json</a>. No external libraries, no network requests; the
function table is embedded in this file as JSON and drawn with a &lt;canvas&gt;.</p>
</footer>
<script>const DATA = {payload};</script>
<script>{MAP_JS}</script>
</body>
</html>
"""
    return body


# --------------------------------------------------------------------------- #
# shields-style badges
# --------------------------------------------------------------------------- #
def badge_svg(label: str, value: str, color: str) -> str:
    label = str(label)
    value = str(value)
    lw = int(12 + 6.6 * len(label))
    vw = int(12 + 6.6 * len(value))
    width, height = lw + vw, 20
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<title>{esc(label)}: {esc(value)}</title>
<defs><clipPath id="round"><rect width="{width}" height="{height}" rx="3"/></clipPath></defs>
<g clip-path="url(#round)">
<rect width="{lw}" height="{height}" fill="#555b66"/>
<rect x="{lw}" width="{vw}" height="{height}" fill="{color}"/>
</g>
<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">
<text x="{lw / 2:.1f}" y="14">{esc(label)}</text>
<text x="{lw + vw / 2:.1f}" y="14">{esc(value)}</text>
</g>
</svg>
"""


# --------------------------------------------------------------------------- #
# history (one point per calendar day)
# --------------------------------------------------------------------------- #
HISTORY_SERIES = [
    ("functions_named_pct", "named functions", "#60a5fa"),
    ("types_named_pct", "data & types", "#4ade80"),
    ("assets_pct", "assets converted", "#fbbf24"),
    ("editor_pct", "editor features", "#c084fc"),
]


def update_history(native: dict, assets: dict, editor: dict, now: datetime,
                   types: dict | None = None, out_dir: Path | None = None) -> list[dict]:
    t = types if isinstance(types, dict) else types_fallback()
    t_batches = t.get("batches") if isinstance(t.get("batches"), dict) else {}
    target_dir = out_dir if out_dir is not None else OUT
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "history.jsonl"
    by_date: dict[str, dict] = {}
    try:
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                date = str(entry.get("date") or "")
                if date:
                    by_date[date] = entry
    except OSError:
        pass

    today = now.strftime("%Y-%m-%d")
    by_date[today] = {
        "date": today,
        "timestamp": now.isoformat(timespec="seconds"),
        "functions_named_pct": native["pct_named"],
        "functions_documented_pct": native["pct_documented"],
        "types_named_pct": float(t.get("pct_named") or 0.0),
        "types_globals_pct": float(t.get("pct_globals") or 0.0),
        "types_classes_pct": float(t.get("pct_classes") or 0.0),
        "types_fields_pct": float(t.get("pct_fields") or 0.0),
        "types_locals_pct": float(t.get("pct_locals") or 0.0),
        "assets_pct": assets["pct_converted"],
        "assets_editable_pct": assets["pct_editable"],
        "editor_pct": editor["percent"],
        "functions_named": native["named"],
        "functions_total": native["total"],
        "types_named": _as_int(t.get("named"), 0),
        "types_guessed": _as_int(t.get("guessed"), 0),
        "types_merged": _as_int(t.get("merged"), 0),
        "types_total": _as_int(t.get("total"), 0),
        "types_batches_done": _as_int(t_batches.get("done"), 0),
        "types_batches_total": _as_int(t_batches.get("total"), 0),
        "assets_converted": assets["converted_total"],
        "assets_source": assets["source_total"],
        "editor_done": editor["done"],
        "editor_partial": editor["partial"],
        "editor_total": editor["total"],
    }
    entries = [by_date[d] for d in sorted(by_date)]
    path.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries),
                    encoding="utf-8")
    return entries


def history_chart(entries: list[dict]) -> str:
    width, height = 920, 340
    left, right, top, bottom = 54, 166, 24, 46
    plot_w = width - left - right
    plot_h = height - top - bottom
    if not entries:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<rect width="{width}" height="{height}" fill="#0d1117"/>
<text x="{left}" y="40" fill="#e6edf3" font-family="Verdana, sans-serif" font-size="15">No history yet</text>
<text x="{left}" y="64" fill="#9aa7b8" font-family="Verdana, sans-serif" font-size="12">Run tools/progress.py to record the first daily point.</text>
</svg>"""

    dates = []
    for entry in entries:
        try:
            dates.append(datetime.strptime(str(entry.get("date")), "%Y-%m-%d").toordinal())
        except ValueError:
            dates.append(dates[-1] if dates else 0)
    lo, hi = min(dates), max(dates)

    def x_for(index: int) -> float:
        if len(entries) == 1 or hi == lo:
            return left + plot_w / 2
        return left + plot_w * (dates[index] - lo) / (hi - lo)

    def y_for(value: float) -> float:
        value = max(0.0, min(100.0, float(value or 0)))
        return top + plot_h * (1.0 - value / 100.0)

    grid = []
    for value in (0, 25, 50, 75, 100):
        y = y_for(value)
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
            f'stroke="#253041" stroke-width="1"/>'
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#7d8a9c" '
            f'font-family="Verdana, sans-serif" font-size="10">{value}%</text>'
        )

    series = []
    right_labels = []
    last = entries[-1]
    for key, label, color in HISTORY_SERIES:
        points = " ".join(
            f"{x_for(i):.1f},{y_for(entry.get(key, 0)):.1f}" for i, entry in enumerate(entries)
        )
        series.append(f'<polyline fill="none" stroke="{color}" stroke-width="2.2" '
                      f'stroke-linejoin="round" points="{points}"/>')
        for i, entry in enumerate(entries):
            series.append(f'<circle cx="{x_for(i):.1f}" cy="{y_for(entry.get(key, 0)):.1f}" '
                          f'r="3.2" fill="{color}"><title>{esc(entry.get("date"))}: '
                          f'{float(entry.get(key, 0)):.1f}%</title></circle>')
        val = float(last.get(key, 0) or 0.0)
        right_labels.append([y_for(val) + 4.0, color, f"{esc(label)} {val:.1f}%"])

    # Keep right-side series labels from colliding vertically when two values are close.
    right_labels.sort(key=lambda item: item[0])
    min_gap = 13.0
    for idx in range(1, len(right_labels)):
        if right_labels[idx][0] < right_labels[idx - 1][0] + min_gap:
            right_labels[idx][0] = right_labels[idx - 1][0] + min_gap
    max_y = top + plot_h + 12.0
    if right_labels and right_labels[-1][0] > max_y:
        right_labels[-1][0] = max_y
        for idx in range(len(right_labels) - 2, -1, -1):
            if right_labels[idx][0] > right_labels[idx + 1][0] - min_gap:
                right_labels[idx][0] = right_labels[idx + 1][0] - min_gap
    for ly, color, text_html in right_labels:
        series.append(
            f'<text x="{left + plot_w + 12}" y="{ly:.1f}" '
            f'fill="{color}" font-family="Verdana, sans-serif" font-size="11">'
            f'{text_html}</text>'
        )

    label_indices = sorted({0, len(entries) // 2, len(entries) - 1})
    xlabels = []
    for i in label_indices:
        xlabels.append(
            f'<text x="{x_for(i):.1f}" y="{height - 18}" text-anchor="middle" fill="#9aa7b8" '
            f'font-family="Verdana, sans-serif" font-size="10">{esc(entries[i].get("date"))}</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
<title>DQXI 3DS progress history</title>
<rect width="{width}" height="{height}" fill="#0d1117"/>
<text x="{left}" y="18" fill="#e6edf3" font-family="Verdana, sans-serif" font-size="14" font-weight="700">Daily progress</text>
{''.join(grid)}
{''.join(series)}
{''.join(xlabels)}
</svg>"""


def html_history(entries: list[dict], stamp: str) -> str:
    rows = []
    for entry in reversed(entries):
        rows.append(
            "<tr>"
            f'<td>{esc(entry.get("date"))}</td>'
            f'<td class="num">{float(entry.get("functions_named_pct", 0)):.1f}%</td>'
            f'<td class="num">{float(entry.get("functions_documented_pct", 0)):.1f}%</td>'
            f'<td class="num">{float(entry.get("types_named_pct", 0)):.1f}%</td>'
            f'<td class="num">{float(entry.get("assets_pct", 0)):.1f}%</td>'
            f'<td class="num">{float(entry.get("editor_pct", 0)):.1f}%</td>'
            f'<td class="num">{int(entry.get("functions_named", 0)):,} / '
            f'{int(entry.get("functions_total", 0)):,}</td>'
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="7" class="muted">No history recorded yet.</td></tr>')
    body = f"""
<p class="muted">One point per calendar day; the last run of a day replaces the earlier point.
Raw series: <a href="history.jsonl">history.jsonl</a>.</p>
{history_chart(entries)}
<table>
<thead><tr><th>Date</th><th>Named functions</th><th>Documented</th><th>Data &amp; types</th>
<th>Assets converted</th><th>Editor features</th><th>Named / total</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p><a href="progress.html">Back to the overview</a></p>
"""
    return page_html("Progress history", "history.html",
                     f"One point per day &middot; generated {esc(stamp)}", body)


# --------------------------------------------------------------------------- #
# live worker board
# --------------------------------------------------------------------------- #
ATTEMPT_RE = re.compile(r"^===== attempt (\d+) model (\S+) (.+?) =====\s*$", re.M)


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r", "")


def parse_ctime(value: str) -> datetime | None:
    value = re.sub(r"\s+", " ", value.strip())
    for fmt in ("%a %b %d %H:%M:%S %Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def fmt_dt(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "&mdash;"


def parse_task_meta(path: Path) -> dict:
    text = read_text(path)
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---"):
        try:
            head, body = text[3:].split("---", 1)
            for line in head.strip().splitlines():
                key, _, value = line.partition(":")
                meta[key.strip()] = value.split("#")[0].strip()
        except ValueError:
            body = text
    after = [a.strip() for a in meta.get("after", "").split(",") if a.strip()]
    first = next((line.strip() for line in body.splitlines() if line.strip()), "")
    if first.startswith("#"):
        first = first.lstrip("# ").strip()
    return {
        "id": path.stem,
        "lane": meta.get("lane") or path.stem,
        "after": after,
        "summary": first[:140],
    }


def parse_log(path: Path) -> dict:
    raw = read_text(path)
    clean = strip_ansi(raw)
    attempts = []
    for match in ATTEMPT_RE.finditer(clean):
        attempts.append({
            "model": match.group(2),
            "when": parse_ctime(match.group(3)),
        })
    lines = [line.rstrip() for line in clean.splitlines() if line.strip()]
    return {
        "attempts": attempts,
        "start": attempts[0]["when"] if attempts else None,
        "model": attempts[-1]["model"] if attempts else None,
        "tail": lines[-15:] if lines else [],
        "when": datetime.fromtimestamp(path.stat().st_mtime) if path.is_file() else None,
    }


def collect_tasks() -> dict:
    state = read_json(ORC / "state.json", {})
    state = state if isinstance(state, dict) else {}
    done_dir = ORC / "done"
    tasks_dir = ORC / "tasks"
    done_ids = {p.stem for p in done_dir.glob("*.md")} if done_dir.is_dir() else set()
    tasks = []
    for path in sorted(tasks_dir.glob("*.md")) if tasks_dir.is_dir() else []:
        meta = parse_task_meta(path)
        tid = meta["id"]
        status = "DONE" if tid in done_ids else str(state.get(tid) or "pending").upper()
        if status not in ("DONE", "FAILED", "RUNNING"):
            status = "pending"

        log_path = ORC / "logs" / f"{tid}.log"
        log = parse_log(log_path) if log_path.is_file() else {
            "attempts": [], "start": None, "model": None, "tail": [], "when": None,
        }
        report = done_dir / f"{tid}.md"
        has_report = report.is_file()
        end = None
        if has_report:
            end = datetime.fromtimestamp(report.stat().st_mtime)
        elif status == "FAILED" and log["when"]:
            end = log["when"]
        tasks.append({
            "id": tid,
            "lane": meta["lane"],
            "after": meta["after"],
            "summary": meta["summary"],
            "status": status,
            "start": log["start"],
            "end": end,
            "model": log["model"],
            "attempts": len(log["attempts"]),
            "tail": log["tail"] if status == "RUNNING" else [],
            "report": read_text(report) if has_report else "",
            "has_report": has_report,
        })

    rank = {"RUNNING": 0, "FAILED": 1, "pending": 2, "DONE": 3}
    tasks.sort(key=lambda t: (rank.get(t["status"], 9), t["id"]))
    counts = Counter(t["status"] for t in tasks)
    return {
        "tasks": tasks,
        "counts": {
            "total": len(tasks),
            "running": counts.get("RUNNING", 0),
            "done": counts.get("DONE", 0),
            "failed": counts.get("FAILED", 0),
            "pending": counts.get("pending", 0),
        },
    }


TASK_CSS = """
.task-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:.85rem}
.task{padding:.8rem .95rem}
.task-head{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;margin-bottom:.25rem}
.task-head code{font-size:1rem;font-weight:700}
.task .meta{color:var(--muted);font-size:.82rem}
.task pre{max-height:300px;font-size:11px}
"""


def html_tasks(board: dict, stamp: str) -> str:
    counts = board["counts"]
    cards = []
    for task in board["tasks"]:
        status = task["status"].lower()
        deps = ", ".join(task["after"]) if task["after"] else "\u2014"
        meta = (f"lane <strong>{esc(task['lane'])}</strong> &middot; after {esc(deps)} &middot; "
                f"started {fmt_dt(task['start'])} &middot; ended {fmt_dt(task['end'])} &middot; "
                f"model <code>{esc(task['model'] or 'not started')}</code>")
        detail = ""
        if status == "running":
            tail = "\n".join(task["tail"]) or "(log is empty)"
            detail = (f'<details open><summary>Last 15 log lines</summary>'
                      f'<pre>{esc(tail)}</pre></details>')
        elif task["has_report"]:
            detail = (f'<details><summary>Done report '
                      f'(<a href="../orchestration/done/{esc(task["id"])}.md">raw</a>)</summary>'
                      f'<pre>{esc(task["report"])}</pre></details>')
        elif status in ("done", "failed"):
            detail = '<p class="note">No done report found.</p>'
        cards.append(
            f'<article class="card task"><div class="task-head"><code>{esc(task["id"])}</code>'
            f'{status_chip(status)}</div>'
            f'<div class="small">{esc(task["summary"])}</div>'
            f'<div class="meta">{meta}</div>{detail}</article>'
        )
    if not cards:
        cards.append('<p class="muted">No task files in <code>orchestration/tasks/</code>.</p>')

    body = f"""
<style>{TASK_CSS}</style>
<p class="muted">Live view of <code>orchestration/tasks/</code> and
<code>orchestration/state.json</code>; refreshes every 30 seconds. Logs are
<code>orchestration/logs/&lt;id&gt;.log</code>, reports are
<code>orchestration/done/&lt;id&gt;.md</code>.</p>
<div class="grid">
  {kpi_card("Running", str(counts["running"]), "in progress now")}
  {kpi_card("Done", str(counts["done"]), "report written")}
  {kpi_card("Failed", str(counts["failed"]), "needs attention")}
  {kpi_card("Pending", str(counts["pending"]), "waiting for deps/lane")}
</div>
<div class="task-grid">{''.join(cards)}</div>
<p><a href="progress.html">Back to the overview</a></p>
"""
    return page_html("Worker board", "tasks.html",
                     f"Auto-refresh 30 s &middot; generated {esc(stamp)}", body, refresh=30)


# --------------------------------------------------------------------------- #
# fallbacks (a broken section must never break the page)
# --------------------------------------------------------------------------- #
def native_fallback() -> dict:
    return {
        "total": 0, "named": 0, "proposed": 0, "documented": 0, "matching_c": 0,
        "decompiled": 0, "covered_by_container": 0, "unresolved": 0,
        "pct_named": 0.0, "pct_documented": 0.0, "pct_matching_c": 0.0,
        "proposals": {"addresses": 0, "high_confidence": 0, "batches": 0,
                      "vector": "orchestration/naming/out/*.json"},
        "verified_c": [], "source": "unavailable", "subsystems": [],
        "notes": ["Native data could not be read; see the console for the error."],
        "_functions": [],
    }


def scripts_fallback() -> dict:
    return {"total": 0, "decompiled": 0, "recompile_verified": 0, "functions": 0,
            "pct_decompiled": 0.0, "pct_recompiled": 0.0, "source": "unavailable",
            "recompile_source": "not generated yet"}


def assets_fallback() -> dict:
    families = [{"key": k, "label": label, "source": SOURCE_BASELINE.get(k, 0),
                 "converted": 0, "editable": 0, "pct_converted": 0.0, "pct_editable": 0.0}
                for k, label in ASSET_FAMILIES]
    return {"families": families, "source_total": sum(f["source"] for f in families),
            "converted_total": 0, "editable_total": 0, "pct_converted": 0.0,
            "pct_editable": 0.0, "source": "unavailable", "roundtrip_manifest": False}


def editor_fallback() -> dict:
    return {"groups": [], "done": 0, "partial": 0, "todo": 0, "total": 0, "percent": 0.0}


def build_fallback() -> dict:
    unknown = {"status": "unknown", "label": "Not generated yet", "detail": "", "when": ""}
    return {"bitmatch": dict(unknown), "tests": dict(unknown, passed=None, total=None, source=""),
            "verification": dict(unknown)}


def safe_call(label: str, fn, fallback):
    try:
        return fn()
    except Exception as exc:  # keep the dispatcher alive even if one section breaks
        print(f"progress: {label} failed: {exc}", file=sys.stderr)
        return fallback


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset-features", action="store_true",
                        help="restore progress/features.json to the default checklist")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    features = ensure_features(reset=args.reset_features)
    now, stamp = timestamp()

    native = safe_call("native", collect_native, native_fallback())
    scripts = safe_call("scripts", collect_scripts, scripts_fallback())
    assets = safe_call("assets", collect_assets, assets_fallback())
    editor = safe_call("editor", lambda: collect_editor(features), editor_fallback())
    build = safe_call("build", collect_build, build_fallback())
    types = safe_call("types", collect_types, types_fallback())
    board = safe_call("tasks", collect_tasks, {"tasks": [], "counts": {
        "total": 0, "running": 0, "done": 0, "failed": 0, "pending": 0}})

    history = safe_call("history", lambda: update_history(native, assets, editor, now, types), [])

    native_public = {k: v for k, v in native.items() if not k.startswith("_")}
    map_html = safe_call(
        "coverage map", lambda: coverage_map_html(native, stamp),
        "<!doctype html><meta charset=\"utf-8\"><title>Coverage map</title>"
        "<p>Coverage map generation failed; see the console for the error.</p>",
    )
    payload = {
        "schema": 1,
        "timestamp": now.isoformat(timespec="seconds"),
        "generated_local": stamp,
        "native": native_public,
        "scripts": scripts,
        "assets": assets,
        "editor": editor,
        "build": build,
        "types": types,
        "tasks": board["counts"],
    }

    t_batches = types.get("batches") if isinstance(types.get("batches"), dict) else {}
    types_badge_val = (
        f"{types['pct_named']:.1f}% "
        f"({_as_int(t_batches.get('done'), 0)}/{_as_int(t_batches.get('total'), 0)})"
    )
    files = {
        "progress.json": json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        "progress.html": html_progress(native, scripts, assets, editor, build, types, stamp),
        "map.html": map_html,
        "progress.svg": coverage_svg(native),
        "history.svg": history_chart(history),
        "history.html": html_history(history, stamp),
        "tasks.html": html_tasks(board, stamp),
        "badge-functions.svg": badge_svg("native named", f"{native['pct_named']:.1f}%", "#2563eb"),
        "badge-types.svg": badge_svg("data & types", types_badge_val, "#15803d"),
        "badge-assets.svg": badge_svg("assets converted", f"{assets['pct_converted']:.1f}%", "#b45309"),
        "badge-editor.svg": badge_svg("editor features", f"{editor['percent']:.1f}%", "#7e22ce"),
    }
    for name, text in files.items():
        (OUT / name).write_text(text, encoding="utf-8")

    print(
        f"progress: native named {native['pct_named']:.1f}% "
        f"({native['named']:,}/{native['total']:,}), documented {native['pct_documented']:.1f}%, "
        f"assets {assets['pct_converted']:.1f}%, editor {editor['percent']:.1f}%, "
        f"types {types['pct_named']:.2f}% (globals {types['pct_globals']:.1f}%, "
        f"classes {types['pct_classes']:.1f}%, fields {types['pct_fields']:.1f}%, "
        f"locals {types['pct_locals']:.1f}%, "
        f"batches {_as_int(t_batches.get('done'), 0)}/{_as_int(t_batches.get('total'), 0)}), "
        f"tasks {board['counts']['done']}/{board['counts']['total']} done -> {OUT}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

