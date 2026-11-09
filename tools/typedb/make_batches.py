#!/usr/bin/env python3
"""Turn the type/global/local evidence into worker batches and task files.

Inputs (written by the two previous steps):

* ``orchestration/types/structs.json`` - candidate classes, their fields, vtables,
  allocation sizes and the functions that touch them (:mod:`tools.typedb.struct_db`);
* ``orchestration/types/globals.json`` / ``locals.json`` - global addresses and
  per-function local variables (:mod:`tools.typedb.inventory`).

Outputs:

* ``orchestration/types/batches/S_###.json`` - ~15 related classes per batch:
  struct layout + field evidence + vtable slots + readable functions;
* ``orchestration/types/batches/G_###.json`` - ~300 globals per batch, grouped by
  subsystem and address;
* ``orchestration/types/batches/V_###.json`` - ~150 functions per batch, grouped
  like the ``N_###`` naming batches, with every local/parameter and its use;
* ``orchestration/tasks/S_###.md``, ``G_###.md``, ``V_###.md`` - the worker
  briefs (front matter ``after:`` is set so S/G run before M2 and V after it);
* ``orchestration/types/batches/index.json`` - the batch catalogue.

The script is idempotent: rerunning it rewrites the batches and task files from
the current evidence but does **not** touch worker output in
``orchestration/types/out/``.

Usage:
    python tools/typedb/make_batches.py
    python tools/typedb/make_batches.py --only S --dry
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.typedb.common import (  # noqa: E402
    BATCH_DIR, OUT_DIR, ROOT, TYPES_DIR, hex_addr, subsystem_of, write_json,
)

TASK_DIR = ROOT / "orchestration" / "tasks"
N_BATCH_DIR = ROOT / "orchestration" / "naming" / "batches"

# Classes that share one of these nouns are kept next to each other inside a
# subsystem.  Purely cosmetic ordering: it makes an S batch read like one feature
# ("all gauge windows") instead of an alphabetic dump.
NOUN_ORDER = (
    "Object", "Window", "WindowBase", "Layout", "Panel", "Widget", "Gauge", "Bar",
    "Message", "Text", "Menu", "List", "Row", "Cell", "Cursor", "Icon", "Sprite",
    "Model", "Mesh", "Camera", "Scene", "Actor", "Unit", "Action", "Effect",
    "Manager", "Controller", "Data", "Table", "Entry", "Node", "Buffer", "File",
    "Archive", "Stream", "Sound", "Voice", "Script", "State", "Task", "Pool",
)
KNOWN_NOUNS = {
    "Action", "Actor", "Anim", "Battle", "Bg2D", "Camera", "Casino", "Container",
    "Cutscene", "Data", "Debug", "Dive", "Effect", "Engine", "Event", "Field",
    "Flag", "Font", "Fs", "Fx", "Gfx", "Hid", "Input", "Item", "ItemList", "Map",
    "Math", "Mem", "Menu", "Message", "Model", "MoLive", "Monster", "Object", "Os",
    "Pack", "Party", "Regex", "Save", "SaveCode", "Screen", "Script", "Serializer",
    "Shop", "Sound", "Sprite", "Str", "Svc", "Text", "Ui", "Video", "Work",
    "std", "nn",
}


def canonical_subsystem(name: str) -> str:
    """Bucket a function/class name into a stable subsystem for grouping.

    ``subsystem_of`` returns the first underscore token.  A seed symbol without
    underscores ("ActorSetEnableFollow") would therefore become its own
    "subsystem"; this maps it to the first CamelCase noun when that noun is a
    known subsystem, else to General.
    """
    sub = subsystem_of(name)
    if sub in KNOWN_NOUNS:
        return sub
    if "_" not in sub:
        m = re.match(r"^(maybe_)?([A-Z][a-z0-9]+)", sub)
        if m and m.group(2) in KNOWN_NOUNS:
            return m.group(2)
    return "General"


def noun_rank(cls: str) -> int:
    for i, noun in enumerate(NOUN_ORDER):
        if cls.endswith(noun):
            return i
    return len(NOUN_ORDER)


# --------------------------------------------------------------------------- #
# trimming helpers (keep the batch files readable)
# --------------------------------------------------------------------------- #
def trim_class(cls: dict) -> dict:
    vtables = []
    for vt in (cls.get("vtables") or [])[:1]:
        vtables.append({
            "address": vt["address"],
            "slot_count": vt["slot_count"],
            "slots": vt["slots"][:24],
        })
    fields = []
    for f in cls.get("fields") or []:
        fields.append({
            "offset": f["offset"],
            "offset_hex": f["offset_hex"],
            "size": f["size"],
            "type_guess": f["type_guess"],
            "is_vtable": f["is_vtable"],
            "is_pointer": f["is_pointer"],
            "is_function_pointer": f["is_function_pointer"],
            "float_hint": f["float_hint"],
            "weak": f["weak"],
            "reads": f["reads"],
            "writes": f["writes"],
            "constants": f["constants"][:4],
            "callees": f["callees"][:4],
            "evidence": f["evidence"][:4],
        })
    return {
        "class": cls["class"],
        "type": cls["type"],
        "subsystem": cls["subsystem"],
        "base": cls["base"],
        "bases_seen": cls.get("bases_seen") or {},
        "size": cls["size"],
        "size_source": cls["size_source"],
        "size_alloc": cls["size_alloc"],
        "field_count": cls["field_count"],
        "weak_field_count": cls["weak_field_count"],
        "has_self": cls["has_self"],
        "vtable": cls.get("vtable"),
        "vtables": vtables,
        "functions": [
            {"name": fn["name"], "address": fn["address"], "role": fn["role"],
             "readable": fn.get("readable")}
            for fn in (cls.get("functions") or [])[:24]
        ],
        "fields": fields,
    }


def trim_global(g: dict) -> dict:
    return {
        "address": g["address"],
        "section": g["section"],
        "width": g["width"],
        "type_guess": g["type_guess"],
        "access": g.get("access"),
        "is_array": g.get("is_array"),
        "array_bytes": g.get("array_bytes"),
        "size_hint": g.get("size_hint"),
        "initial_value": g.get("initial_value"),
        "string": g.get("string"),
        "pointee_string": g.get("pointee_string"),
        "vtable": g.get("vtable"),
        "comment_hint": g.get("comment_hint"),
        "use_count": g["use_count"],
        "function_count": g["function_count"],
        "functions": g["functions"][:10],
        "samples": g["samples"][:3],
        "literals": g.get("literals", [])[:3],
    }


def trim_function(f: dict) -> dict:
    variables = []
    for v in f["variables"]:
        usage = v.get("usage") or {}
        variables.append({
            "name": v["name"],
            "type": v["type"],
            "stars": v["stars"],
            "array": v.get("array"),
            "is_param": v["is_param"],
            "reads": usage.get("reads", 0),
            "writes": usage.get("writes", 0),
            "hint": usage.get("hint", ""),
            "calls": usage.get("calls", []),
            "fields": usage.get("fields", []),
            "constants": usage.get("constants", []),
        })
    return {
        "name": f["name"],
        "address": f["address"],
        "class": f.get("class"),
        "role": f.get("role"),
        "signature": f["signature"],
        "params": f["params"],
        "readable": f["readable"],
        "fields_used": f["fields_used"][:16],
        "variables": variables,
    }


# --------------------------------------------------------------------------- #
# packing
# --------------------------------------------------------------------------- #
def pack_s_batches(classes: list[dict], max_classes: int = 15,
                   max_fields: int = 420) -> list[list[dict]]:
    """~15 related classes per batch, balanced by field count.

    A class with more fields than the budget (Field_SceneObject has 532) becomes
    its own batch: splitting one struct over two workers would produce two
    contradictory layouts.
    """
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for cls in classes:
        groups[canonical_subsystem(cls["class"])].append(cls)
    batches: list[list[dict]] = []
    for subsystem in sorted(groups):
        items = sorted(groups[subsystem],
                       key=lambda c: (noun_rank(c["class"]), -len(c["fields"]), c["class"]))
        current: list[dict] = []
        fields = 0
        for cls in items:
            count = len(cls["fields"])
            if current and (len(current) >= max_classes or fields + count > max_fields):
                batches.append(current)
                current, fields = [], 0
            current.append(cls)
            fields += count
        if current:
            batches.append(current)
    return batches


def pack_g_batches(globals_: list[dict], per_batch: int = 300) -> list[list[dict]]:
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for g in globals_:
        groups[canonical_subsystem(g["subsystem"])].append(g)
    batches: list[list[dict]] = []
    for subsystem in sorted(groups):
        items = sorted(groups[subsystem], key=lambda g: int(g["address"], 16))
        for i in range(0, len(items), per_batch):
            batches.append(items[i:i + per_batch])
    return batches


def n_batch_addresses() -> list[tuple[str, list[int]]]:
    """(batch id, addresses) from the existing N_### naming batches."""
    out: list[tuple[str, list[int]]] = []
    if not N_BATCH_DIR.is_dir():
        return out
    for path in sorted(N_BATCH_DIR.glob("N_*.txt")):
        addresses = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            address = line.split("\t")[0].strip()
            try:
                addresses.append(int(address, 16))
            except ValueError:
                continue
        out.append((path.stem, addresses))
    return out


def pack_v_batches(functions: dict[int, dict]) -> list[tuple[str, list[int]]]:
    """Mirror the N_### grouping, then add functions the naming batches skipped."""
    covered: set[int] = set()
    batches: list[tuple[str, list[int]]] = []
    for name, addresses in n_batch_addresses():
        keep = [a for a in addresses if a in functions]
        if keep:
            batches.append((name.replace("N_", "V_"), keep))
            covered.update(keep)
    leftovers = [a for a in functions if a not in covered]
    leftovers.sort()
    for i in range(0, len(leftovers), 150):
        batches.append((f"V_{len(batches) + 1:03d}", leftovers[i:i + 150]))
    # leftovers may collide with an existing V number when N has gaps; renumber
    seen: dict[str, int] = {}
    fixed: list[tuple[str, list[int]]] = []
    for name, addresses in batches:
        if name in seen:
            seen[name] += 1
            name = f"{name}r{seen[name]}"
        else:
            seen[name] = 1
        fixed.append((name, addresses))
    return fixed


# --------------------------------------------------------------------------- #
# task file templates
# --------------------------------------------------------------------------- #
RULES = """Never invent a name. A correct vague name (`someUnit`, `titleStateTable`) beats a precise
wrong one. Every name carries a `confidence` (0.0-1.0); when it is below 0.5 prefix the name with
`maybe_`. Write the reason into `evidence` (function names, vtable slot, string, constant, field
width). Save your JSON every ~25 items so a resumed worker can continue. Read
`orchestration/WORKER_RULES.md` first; you are bound by it."""

OWN_ONLY = """Owns ONLY: `orchestration/types/out/{batch}.json`. Do not edit any other file except
`AGENT_LOG.md` and your done report. Skip the full test run from WORKER_RULES rule 5 (it does not
apply to a naming batch); a JSON syntax check of your own output is required instead."""

S_TEMPLATE = """---
lane: {batch}
after: M1_merge_names
---
Name the classes and every field of the {count} classes in
`orchestration/types/batches/{batch}.json` (subsystem: {subsystem}).

{rules}

{own}

## What you get

The batch JSON is machine-generated from the retail executable by
`tools/typedb/struct_db.py`. For each class:

* `class` / `type` - the class name recovered from the M1 function names and the C type name;
* `size`, `size_source` - layout size (allocation evidence or highest strong field);
* `base`, `bases_seen` - base class inferred from base-constructor calls;
* `vtables[].slots[]` - the vtable, already resolved to real function names by address;
* `functions[]` - every recovered method, with its readable-C path;
* `fields[]` - one entry per accessed offset: `size`, `type_guess`, `is_pointer`,
  `is_function_pointer`, `reads`/`writes`, `constants`, `callees`, `evidence` (up to four
  readable-C lines that touch it) and `weak` (a single access at a huge offset - usually a
  mistyped `self`, do not let it define the type).

Field offsets are byte offsets from the start of the object. A vtable pointer at offset 0 means
the class is polymorphic. Use `orchestration/types/structs.json` to see every other class and its
type name when a field obviously points at another object.

## What to write

`orchestration/types/out/{batch}.json` - one JSON object per class:

```json
[
  {{
    "class": "Ui_GaugeWindow",
    "type": "UiGaugeWindow",
    "summary": "one sentence: what this object represents and who owns it",
    "size": 452,
    "base": "Ui_Window",
    "confidence": 0.8,
    "evidence": "Ui_GaugeWindow_InitPanes stores the vtable; allocation in Ui_GaugeWindow_Create",
    "fields": [
      {{"offset": 0,    "name": "vtable",       "type": "void*",        "size": 4, "confidence": 0.95,
        "evidence": "written in every ctor, slots are Ui_GaugeWindow_*"}},
      {{"offset": 452,  "name": "targetUnit",   "type": "BattleUnit*",  "size": 4, "confidence": 0.7,
        "evidence": "passed to Battle_Unit_GetHp; f_1c4 sibling is the unit id"}}
    ]
  }}
]
```

Rules for fields:

* Every offset in the batch must appear exactly once. If a field is real but you cannot name it
  honestly, use `unknown` with `confidence: 0.0` and say what it is (e.g. `unknown_counter`) -
  never invent a purpose just to fill the slot. Unknown gaps are emitted as padding by the merge.
* `type` must be a C type that exists: `u8 u16 u32 s8 s16 s32 f32`, `void*`, `char*`, a type from
  `structs.json`, or a function pointer `void (*)(void)`.
* Naming: fields are lowerCamelCase nouns (`targetUnit`, `paneCount`, `titleText`); booleans
  `isVisible`/`hasFocus`; offsets 0 with a vtable are always `vtable`.
* A class name is `Subsystem_NounNoun` (keep the generated `class`) and `type` is the same
  without underscores. Do not rename a class that the project already uses in signatures.
* Confidence is per field; a class-level confidence is the weakest important field.

## How to work

1. Open the readable C of the class's constructor (role `ctor`) first: it shows the vtable store,
   the base-constructor call and every initialised field.
2. Then the `update`/`draw` methods - they read the fields whose meaning you need.
3. The vtable slot names tell you the method family (`Ui_GaugeWindow_DrawBar` etc.).
4. Cross-check a field's width with its `size` and with the `sizes_seen` list in `structs.json`.
5. Do not trust a `weak` field: it is one access at an implausible offset.
"""

G_TEMPLATE = """---
lane: {batch}
after: M1_merge_names
---
Name and type the {count} global variables in `orchestration/types/batches/{batch}.json`
(subsystem: {subsystem}).

{rules}

{own}

## What you get

`tools/typedb/inventory.py` resolved every `g_XXXXXXXX` literal through the retail image. The
interesting detail: this Ghidra export labels the *literal-pool slot*, so a batch record carries
the **real data address** and the literal slot(s) that point at it. Per global:

* `address` (real object), `section` (`rodata` / `data` / `bss`);
* `width` and `type_guess` (`u8`..`u32`, `char[]`, `void*`), `access` (`deref` = the value is
  read/written, `address` = the address is used as a base/array);
* `initial_value` - the retail image word (or `0x00000000` for BSS);
* `string` / `pointee_string` - exact printable string content, strong evidence for a name;
* `vtable` - the value is a C++ vtable; `functions[]`/`samples[]` - who uses it and how;
* `literals[]` - the `.text` literal slots that reference it (for cross-checking in the C).

## What to write

`orchestration/types/out/{batch}.json` - one JSON object per global:

```json
[
  {{"address": "0x007BE330",
    "name": "g_titleState",
    "type": "u32",
    "comment": "Current title-screen state: 0 boot, 1 logo, 2 press start (compare constants in Ui_Title_Update).",
    "confidence": 0.7,
    "evidence": "read by Ui_Title_Update/Draw; values 0..3; string 'title' loaded next to it"}}
]
```

Rules:

* `name` is a C identifier starting with `g_` and lowerCamelCase (`g_partyMemberCount`); no
  address and no type in the name. If you cannot name it, `maybe_g_<section>_<hex>` is honest.
* `type` must be a real C type: `u8 u16 u32 s8 s16 s32 f32`, `void*`, `char*`, `char[N]`,
  `void (*)(void)`, or a class type from `structs.json` when the word is a pointer to it.
  `char[]`/`char[N]` for strings (use the byte length you can defend), arrays as `T[N]`.
* `comment` is one or two sentences a modder understands: what it holds, who writes it, which
  values mean what. Never leave it empty.
* Do not name raw numeric literals (addresses that are not data, small integers) - they are not in
  the batch on purpose.
* Confidence < 0.5 -> prefix the *name* with `maybe_`.
"""

V_TEMPLATE = """---
lane: {batch}
after: M2_types_merge
---
Rename the local variables and remaining `argN` parameters of the {count} functions in
`orchestration/types/batches/{batch}.json`.

{rules}

{own}

## Why this runs after M2

`M2_types_merge` has already merged the S/G results into `include/dqxi/*.h` and regenerated
`decomp/readable/` with real field names (`unit->targetUnit` instead of `f_1b4`) and global names.
Read the **current** readable C, not the raw Ghidra file: the batch's `readable` path is updated
by the merge, and the merged headers tell you what each `->field` means. Use those field and
global names to name the locals (`iVar2` that holds `unit->targetUnit` becomes `targetUnit`).

## What you get

One record per function: `name`, `address`, `class`, `signature`, `params`, `fields_used` and
`variables`. Each variable has:

* `name` - the exact token in the readable C (`iVar2`, `uStack_10`, `arg1`, ...) - rename these
  tokens, nothing else;
* `type`/`stars`/`array` - current declaration, `is_param`;
* `reads`/`writes`, `hint` (`loop counter`, `return value`, `assigned from X`, `argument to Y`,
  `object/struct pointer (fields at 0x...)`), `calls`, `fields`, `constants`.

## What to write

`orchestration/types/out/{batch}.json` - one JSON object per function:

```json
[
  {{"address": "0x00123456",
    "function": "Field_UpdateActor",
    "params": {{"arg1": "actor", "arg2": "deltaFrames"}},
    "locals": {{"iVar2": "partyCount", "uStack_10": "moveSpeed", "puVar3": "targetUnit"}},
    "confidence": 0.7,
    "evidence": "iVar2 comes from Party_GetMemberCount and bounds the loop; uStack_10 is scaled by deltaFrames"}}
]
```

Rules:

* `params` renames the parameters still called `argN` (or `self` - keep `self` unless a better
  noun exists); `locals` renames declaration tokens. Use the exact tokens from the batch.
* Names are lowerCamelCase nouns (`partyCount`, `targetUnit`, `isVisible`), never a type name,
  never a C keyword, never duplicated inside one function. A loop counter is `i`/`j`/`k` when it
  is only an index, otherwise give it the counted thing (`memberIndex`).
* Rename only what you can justify from the body, the calls, or the merged field/global names.
  Leaving a name out is better than a wrong one; a whole function may be omitted if nothing is
  clear (say why in `evidence`).
* Confidence < 0.5 -> prefix the individual name with `maybe_` (the merge keeps those, but they
  count as unnamed in progress).
* Do not touch the readable C tree yourself; `M3_vars_merge` applies your maps.
"""


def write_task(batch: str, text: str) -> None:
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    path = TASK_DIR / f"{batch}.md"
    path.write_text(text, encoding="utf-8")
    path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", choices=("all", "S", "G", "V"), default="all")
    ap.add_argument("--dry", action="store_true", help="print counts, write nothing")
    args = ap.parse_args()

    structs_path = TYPES_DIR / "structs.json"
    globals_path = TYPES_DIR / "globals.json"
    locals_path = TYPES_DIR / "locals.json"
    for path in (structs_path, globals_path, locals_path):
        if not path.is_file():
            print(f"missing {path} - run struct_db.py and inventory.py first")
            return 1
    structs = json.loads(structs_path.read_text(encoding="utf-8"))
    globals_doc = json.loads(globals_path.read_text(encoding="utf-8"))
    locals_doc = json.loads(locals_path.read_text(encoding="utf-8"))

    all_classes = structs.get("classes") or []
    classes = [c for c in all_classes if c.get("fields")]
    field_total = sum(len(c["fields"]) for c in classes)
    globals_ = globals_doc.get("globals") or []
    functions = {int(f["address"], 16): f for f in locals_doc.get("functions") or []}

    s_groups = pack_s_batches(classes)
    g_groups = pack_g_batches(globals_)
    v_groups = pack_v_batches(functions)

    s_batches = [f"S_{i:03d}" for i in range(1, len(s_groups) + 1)]
    g_batches = [f"G_{i:03d}" for i in range(1, len(g_groups) + 1)]
    v_batches = [name for name, _ in v_groups]

    print(f"classes with fields {len(classes):,} ({field_total:,} fields) "
          f"-> {len(s_groups)} S batches")
    print(f"globals {len(globals_):,} -> {len(g_groups)} G batches")
    print(f"functions {len(functions):,} -> {len(v_groups)} V batches")
    if args.dry:
        return 0

    BATCH_DIR.mkdir(parents=True, exist_ok=True)
    catalogue = {"generated_by": "tools/typedb/make_batches.py",
                 "structs": "orchestration/types/structs.json",
                 "globals": "orchestration/types/globals.json",
                 "locals": "orchestration/types/locals.json",
                 "batches": []}

    if args.only in ("all", "S"):
        for batch, group in zip(s_batches, s_groups):
            subsystem = canonical_subsystem(group[0]["class"])
            fields = sum(len(c["fields"]) for c in group)
            write_json(BATCH_DIR / f"{batch}.json", {
                "batch": batch,
                "kind": "structs",
                "subsystem": subsystem,
                "instruction": ("Name every class and field. Offsets are bytes from the object base. "
                                "Never invent; low confidence -> maybe_ name and confidence < 0.5."),
                "classes": [trim_class(c) for c in group],
            })
            write_task(batch, S_TEMPLATE.format(
                batch=batch, count=len(group), subsystem=subsystem, rules=RULES,
                own=OWN_ONLY.format(batch=batch)))
            catalogue["batches"].append({
                "id": batch, "kind": "S", "subsystem": subsystem,
                "classes": [c["class"] for c in group], "fields": fields,
                "input": f"orchestration/types/batches/{batch}.json",
                "output": f"orchestration/types/out/{batch}.json",
            })

    if args.only in ("all", "G"):
        for batch, group in zip(g_batches, g_groups):
            subsystem = canonical_subsystem(group[0]["subsystem"])
            write_json(BATCH_DIR / f"{batch}.json", {
                "batch": batch,
                "kind": "globals",
                "subsystem": subsystem,
                "instruction": ("Name and type every global. `address` is the real data object; "
                                "`literals` are the .text slots that reference it."),
                "globals": [trim_global(g) for g in group],
            })
            write_task(batch, G_TEMPLATE.format(
                batch=batch, count=len(group), subsystem=subsystem, rules=RULES,
                own=OWN_ONLY.format(batch=batch)))
            catalogue["batches"].append({
                "id": batch, "kind": "G", "subsystem": subsystem,
                "count": len(group),
                "input": f"orchestration/types/batches/{batch}.json",
                "output": f"orchestration/types/out/{batch}.json",
            })

    if args.only in ("all", "V"):
        for batch, addresses in v_groups:
            group = [trim_function(functions[a]) for a in addresses if a in functions]
            if not group:
                continue
            subsystems = collections.Counter(canonical_subsystem(f["name"]) for f in group)
            subsystem = subsystems.most_common(1)[0][0]
            write_json(BATCH_DIR / f"{batch}.json", {
                "batch": batch,
                "kind": "locals",
                "subsystem": subsystem,
                "instruction": ("Rename only the listed tokens in the current readable C. Use the "
                                "merged struct field and global names; omit what you cannot justify."),
                "functions": group,
            })
            write_task(batch, V_TEMPLATE.format(
                batch=batch, count=len(group), subsystem=subsystem, rules=RULES,
                own=OWN_ONLY.format(batch=batch)))
            catalogue["batches"].append({
                "id": batch, "kind": "V", "subsystem": subsystem,
                "count": len(group),
                "input": f"orchestration/types/batches/{batch}.json",
                "output": f"orchestration/types/out/{batch}.json",
            })

    write_json(BATCH_DIR / "index.json", catalogue)
    print(f"wrote {len(catalogue['batches'])} batch files + task files")
    print("  next: workers fill orchestration/types/out/*.json, then M2_types_merge / M3_vars_merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
