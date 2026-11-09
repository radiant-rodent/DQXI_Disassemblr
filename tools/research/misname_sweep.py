#!/usr/bin/env python3
"""Fact-driven sweep for families of misnamed functions in DQXI 3DS.

For each verified fact in orchestration/naming/FACTS.md that pins a helper,
data-table getter, struct offset, or SDK constant to a concrete subsystem,
this script scans all 18,787 functions in build/code.bin (both ARM and Thumb
calls plus literal-pool constants) and lists functions whose current name
contradicts the pinned fact.

Outputs a ranked table:
    (address, current_name, contradicted_fact, caller_count)

Expect false positives where a cross-subsystem call is legitimate (for example,
a UI status screen reading a PartyMember or formatting an item name); each
candidate must be judged in disassembly before adding to R_S02.json.

Usage:
    python tools/research/misname_sweep.py
    python tools/research/misname_sweep.py --exclude-overlay R_S02
    python tools/research/misname_sweep.py --exclude-overlay R_S02 --json out/scratch/K2/sweep_pre_s02.json
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import struct
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import merge_names  # noqa: E402

CODE_BASE = 0x00100000
CODE_BIN = ROOT / "build" / "code.bin"
FUNCTIONS_JSONL = ROOT / "decomp" / "ghidra" / "functions_merged.jsonl"
PROPOSALS_DIR = ROOT / "orchestration" / "naming" / "out"
REFINE_DIR = ROOT / "orchestration" / "naming" / "refine" / "out"


@dataclass(frozen=True)
class FactRule:
    fact_id: str
    description: str
    target_callees: tuple[int, ...]
    target_literals: tuple[int, ...]
    include_self: bool
    contradict_re: re.Pattern[str]
    self_only_targets: tuple[int, ...] = ()
    allow_re: re.Pattern[str] | None = None


FACT_RULES: tuple[FactRule, ...] = (
    FactRule(
        fact_id="F01_Item_Lookup",
        description="Calls Item_LookupRecord(0x61BD4C) / Data_GetItemRecord(0x63DF9C) / ItemBag gold-or-count(0x6138D4,0x613FC0)",
        target_callees=(0x0061BD4C, 0x0063DF9C, 0x006138D4, 0x00613FC0),
        target_literals=(),
        include_self=False,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_(?!FormatItem|AppendItem)|Font_|"
            r"Container_(?:Glyph|CompareIdNames|SortIdsByName)|"
            r"Ui_Text(?:Layout|Scroll)_|Ui_DataPanel_Sort|"
            r"Ui_MessageWindow_UpdateGlyphStyle|Ui_Message_ShowItemName|"
            r"Monster_Model_|BattleUnitDisplay_ResolveModel|"
            r"Gfx_|Audio_|Sound_|Camera_|Math_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F02_Party_Member",
        description="Calls Party_GetMemberById(0x35EB98) or member equip/slot helpers(0x6292A4,0x6292F0,0x6297C8,0x629890,0x1901F4)",
        target_callees=(0x0035EB98, 0x006292A4, 0x006292F0, 0x006297C8, 0x00629890, 0x001901F4),
        target_literals=(),
        include_self=False,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_|Font_|Monster_Model_|"
            r"Ui_TextScroll_|Ui_MessageWindow_UpdateGlyphStyle|Ui_Message_ShowItemName|"
            r"Actor2D_DebugPrint|Ui_SpriteSpan_Log|Ui_DebugLabel_|"
            r"Gfx_|Audio_|Sound_|Math_|Container_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F03_Party_StatCalc",
        description="Calls/is Party_Member_RecalculateStats(0x19201C) or Party_StatCalc passes(0x456D68..0x45BF38) or LevelGrowth(0x63E7F8)",
        target_callees=(
            0x0019201C,
            0x00456D68,
            0x004573CC,
            0x00459654,
            0x00459A70,
            0x00459F7C,
            0x00459FE0,
            0x0045A5C8,
            0x0045BD14,
            0x0045BF38,
            0x0063E7F8,
        ),
        target_literals=(),
        include_self=True,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_|Font_|Party_ApplyFont|Party_Member_ApplyPageContent|"
            r"Monster_Model_|Ui_Window_RebuildSlotPages|Ui_Window_ResetState|"
            r"Gfx_|Audio_|Sound_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F04_Spell_Skill_Panel_Table",
        description="Calls SkillPanelRecord(0x63CF74), PassiveTraitRecord(0x63EB4C), SpellRecord(0x63CFC8), or SkillRecord(0x63D018)",
        target_callees=(0x0063CF74, 0x0063EB4C, 0x0063CFC8, 0x0063D018),
        target_literals=(),
        include_self=False,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_|Font_|Monster_Model_|Ui_TextLayout_|Ui_Message_Draw|Ui_Message_Update|"
            r"Gfx_|Audio_|Sound_|Container_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F05_SaveData_24A98",
        description="Calls/is SaveData ctor/reset(0x109990,0x10F448,0x19371C,0x1939C0) or loads GameWork+0x24A98/+0x24ACC",
        target_callees=(0x00109990, 0x0010F448, 0x0019371C),
        target_literals=(0x00024A98, 0x00024ACC),
        include_self=True,
        self_only_targets=(0x001939C0,),
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_|Font_|Container_Glyph|"
            r"Ui_Window_ResetState|Ui_Window_UpdateFadeTimers|"
            r"Ui_PartyStatusWindow_(?:Ctor|Reset)|Ui_PartyStatus_InitMemberData|"
            r"Gfx_Context_Ctor|Gfx_|Audio_|Sound_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F06_Battle_MessageQueue",
        description="Calls/is Battle message queue(0x3FBE4C push batch, 0x1FD96C get queue, 0x1FE274 push entry, 0x1FD9BC..0x1FE494)",
        target_callees=(0x003FBE4C, 0x001FD96C, 0x001FE274, 0x001FE054, 0x001FDDD0),
        target_literals=(),
        include_self=True,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_Command|Text_Layout_|Text_MsgWindow_|Text_Queue|Text_EntryQueue|"
            r"Ui_PopupEntry_SpawnFromTable|Ui_Message_Draw|Ui_Message_Update|"
            r"Ui_Message_ShowItemName|Ui_Message_Queue|"
            r"Effect_|Net_|Packet_|Font_|Gfx_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F07_Message_FormatArgSlot",
        description="Calls/is Message_FormatArgSlot*(0x6D3EA0,0x6D3EDC,0x6D3F18,0x6D3F54 on *0x7AC834 + slot*0x108)",
        target_callees=(0x006D3EA0, 0x006D3EDC, 0x006D3F18, 0x006D3F54),
        target_literals=(),
        include_self=True,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Ui_TextFormat_ReleaseSlot|Text_ResetChannelSlot|Ui_TextEntry_Reset|"
            r".*DebugPrint.*|.*DebugLabel.*|Ui_SpriteSpan_Log|Ui_Window_LogCurrentEntry|"
            r"Monster_Model_|Text_Command|Text_Layout_|Text_MsgWindow_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F08_Battle_Rng",
        description="Calls Battle RNG(0x1CA474 Battle_RollPercent on +0x4218) or loads BattleWork RNG offset 0x4218",
        target_callees=(0x001CA474,),
        target_literals=(0x00004218,),
        include_self=False,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_|Font_|Ui_Text|Ui_Message|Menu_|Container_|Gfx_|Audio_|Sound_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F09_Battle_UnitState_And_TurnOrder",
        description="Calls Battle_Unit_HasState(0x639954) or Battle_CalcTurnOrderPriority(0x16815C)",
        target_callees=(0x00639954, 0x0016815C),
        target_literals=(),
        include_self=False,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_|Font_|Ui_TextLayout_|Ui_Text_|Ui_Message_Draw|Ui_Message_Update|"
            r"Menu_Text|Menu_Cursor|Menu_Action|Container_|Gfx_|Audio_|Sound_"
            r")"
        ),
    ),
    FactRule(
        fact_id="F10_Battle_CombatMath_And_UnitRatios",
        description="Calls Battle unit stat/HP/MP helpers(0x4900A8,0x492520,0x487150,0x48E380,0x48BA90)",
        target_callees=(0x004900A8, 0x00492520, 0x00487150, 0x0048E380, 0x0048BA90),
        target_literals=(),
        include_self=True,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:"
            r"Text_|Font_|Ui_TextLayout_|Ui_Text_UpdateWrapWidthLimit|Ui_Message_Draw|Ui_Message_Update"
            r")"
        ),
    ),
    FactRule(
        fact_id="F11_CtrSdk_ErrDisp",
        description="Loads nn::err Result 0xC8A0CFFC or calls fatal ErrDisp trigger",
        target_callees=(0x0010D9D0,),
        target_literals=(0xC8A0CFFC,),
        include_self=True,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:Dsp_|Audio_|Sound_|Text_|Ui_|Battle_|Field_|Shop_)"
        ),
    ),
    FactRule(
        fact_id="F12_Field_Trigger_And_PastPlace",
        description="Calls Data_GetFieldTriggerRecord(0x63DCE8) or Data_GetPastPlaceRecord(0x63DDCC)",
        target_callees=(0x0063DCE8, 0x0063DDCC),
        target_literals=(),
        include_self=False,
        contradict_re=re.compile(
            r"^(?:maybe_)?(?:Text_|Font_|Battle_|Shop_|Audio_|Sound_|Gfx_)"
        ),
    ),
)


def load_symbols(exclude_overlays: set[str]) -> dict[int, dict]:
    """Load merged function metadata + proposals, optionally excluding named R_* overlays."""
    rows = [
        json.loads(line)
        for line in FUNCTIONS_JSONL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_addr: dict[int, dict] = {}
    for r in rows:
        a = int(r["address"], 16)
        by_addr[a] = {
            "address": a,
            "name": r.get("name", f"FUN_{a:08x}"),
            "confidence": float(r.get("confidence", 1.0)),
            "batch": r.get("batch", "seed"),
            "mode": r.get("mode", "arm"),
            "size": int(r.get("size", 0)),
        }

    batch_files = sorted(PROPOSALS_DIR.glob("N_*.json")) + [
        p for p in sorted(REFINE_DIR.glob("R_*.json")) if p.stem not in exclude_overlays
    ]
    for path in batch_files:
        data, err = merge_names.read_json(path)
        if err or not isinstance(data, list):
            continue
        for entry in data:
            if not isinstance(entry, dict) or "address" not in entry or "name" not in entry:
                continue
            addr = merge_names.norm_addr(entry["address"])
            if addr is None:
                continue
            if addr not in by_addr:
                by_addr[addr] = {
                    "address": addr,
                    "mode": "arm",
                    "size": 0,
                }
            by_addr[addr].update(
                {
                    "name": entry["name"],
                    "confidence": float(entry.get("confidence", 0.0)),
                    "batch": path.stem,
                    "change": entry.get("change", ""),
                }
            )
    return by_addr


def build_call_and_literal_graph(
    by_addr: dict[int, dict],
) -> tuple[dict[int, set[int]], dict[int, set[int]], dict[int, set[int]]]:
    """Scan build/code.bin to recover direct callees, callers, and loaded 32-bit literals per function."""
    code = CODE_BIN.read_bytes()
    code_len = len(code)
    sorted_addrs = sorted(by_addr)
    addr_set = set(sorted_addrs)

    callees: dict[int, set[int]] = defaultdict(set)
    callers: dict[int, set[int]] = defaultdict(set)
    literals: dict[int, set[int]] = defaultdict(set)

    for idx, faddr in enumerate(sorted_addrs):
        meta = by_addr[faddr]
        next_addr = sorted_addrs[idx + 1] if idx + 1 < len(sorted_addrs) else CODE_BASE + code_len
        size = meta.get("size", 0)
        end_addr = faddr + size if size > 0 else next_addr
        end_addr = min(max(end_addr, min(next_addr, faddr + 4)), next_addr, CODE_BASE + code_len)

        start_off = faddr - CODE_BASE
        end_off = end_addr - CODE_BASE
        if start_off < 0 or start_off >= code_len or end_off <= start_off:
            continue

        mode = meta.get("mode", "arm")
        # 3DS CPU is ARM11 MPCore (ARMv6K, Thumb-1 only — no Thumb-2 push.w).
        # If a 4-byte-aligned function tagged "thumb" begins with ARM condition
        # 0xE words (e.g. E92D.... push, E59F.... ldr, E1A0.... mov), decode as ARM.
        if mode == "thumb" and (faddr & 3) == 0 and (end_off - start_off) >= 8:
            w0, w1 = struct.unpack_from("<II", code, start_off)
            if ((w0 >> 28) == 0xE and (w1 >> 28) == 0xE) or (w0 & 0xFFFF0000) == 0xE92D0000:
                mode = "arm"
        if mode == "thumb":
            off = start_off
            while off + 2 <= end_off:
                hw1 = struct.unpack_from("<H", code, off)[0]
                pc = CODE_BASE + off
                # 32-bit Thumb BL / BLX
                if (hw1 & 0xF800) == 0xF000 and off + 4 <= end_off:
                    hw2 = struct.unpack_from("<H", code, off + 2)[0]
                    if (hw2 & 0xD000) in (0xD000, 0xC000):
                        s = (hw1 >> 10) & 1
                        imm10 = hw1 & 0x3FF
                        j1 = (hw2 >> 13) & 1
                        j2 = (hw2 >> 11) & 1
                        imm11 = hw2 & 0x7FF
                        i1 = (~(j1 ^ s)) & 1
                        i2 = (~(j2 ^ s)) & 1
                        imm = (s << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
                        if s:
                            imm -= 1 << 25
                        if (hw2 & 0x1000) == 0:
                            tgt = ((pc + 4) & ~3) + (imm & ~3)
                        else:
                            tgt = pc + 4 + imm
                        if CODE_BASE <= tgt < CODE_BASE + code_len and tgt != faddr:
                            callees[faddr].add(tgt)
                            callers[tgt].add(faddr)
                        off += 4
                        continue
                # 16-bit Thumb LDR Rd, [PC, #imm8*4]
                if (hw1 & 0xF800) == 0x4800:
                    lit_addr = ((pc + 4) & ~3) + ((hw1 & 0xFF) << 2)
                    lit_off = lit_addr - CODE_BASE
                    if 0 <= lit_off <= code_len - 4:
                        val = struct.unpack_from("<I", code, lit_off)[0]
                        literals[faddr].add(val)
                off += 2
        else:
            for off in range(start_off, end_off - 3, 4):
                w = struct.unpack_from("<I", code, off)[0]
                pc = CODE_BASE + off
                cond = (w >> 28) & 0xF
                if cond == 0xF:
                    # Unconditional BLX imm24: 1111 101H imm24
                    if ((w >> 25) & 0x7F) == 0x7D:
                        h = (w >> 24) & 1
                        imm24 = w & 0xFFFFFF
                        if imm24 & 0x800000:
                            imm24 -= 0x1000000
                        tgt = pc + 8 + (imm24 << 2) + (h << 1)
                        if CODE_BASE <= tgt < CODE_BASE + code_len and tgt != faddr:
                            callees[faddr].add(tgt)
                            callers[tgt].add(faddr)
                    continue
                op = (w >> 24) & 0xF
                if op == 0xB:
                    # ARM BL imm24 — always a call, even to unmerged helpers (e.g. func_0035EB98)
                    imm24 = w & 0xFFFFFF
                    if imm24 & 0x800000:
                        imm24 -= 0x1000000
                    tgt = pc + 8 + (imm24 << 2)
                    if CODE_BASE <= tgt < CODE_BASE + code_len and tgt != faddr:
                        callees[faddr].add(tgt)
                        callers[tgt].add(faddr)
                elif op == 0xA:
                    # ARM B imm24 — count as tailcall when jumping outside [faddr, end_addr)
                    imm24 = w & 0xFFFFFF
                    if imm24 & 0x800000:
                        imm24 -= 0x1000000
                    tgt = pc + 8 + (imm24 << 2)
                    if (tgt < faddr or tgt >= end_addr) and CODE_BASE <= tgt < CODE_BASE + code_len:
                        callees[faddr].add(tgt)
                        callers[tgt].add(faddr)
                elif (w & 0x0F7F0000) == 0x051F0000:
                    imm12 = w & 0xFFF
                    lit_addr = pc + 8 + (imm12 if (w & 0x00800000) else -imm12)
                    lit_off = lit_addr - CODE_BASE
                    if 0 <= lit_off <= code_len - 4:
                        val = struct.unpack_from("<I", code, lit_off)[0]
                        literals[faddr].add(val)
                        if val in addr_set and val != faddr:
                            # Function pointer reference (e.g. std_ConstructArray ctor callback)
                            callees[faddr].add(val)
                            callers[val].add(faddr)

    # Also count vtable / data pointers into functions for caller_count awareness
    _ = bisect.bisect_left  # keep bisect imported for extensions
    return callees, callers, literals


def run_sweep(
    by_addr: dict[int, dict],
    callees: dict[int, set[int]],
    callers: dict[int, set[int]],
    literals: dict[int, set[int]],
    only_family: str | None = None,
) -> list[dict]:
    """Evaluate all FACT_RULES and return ranked contradiction rows."""
    hits_by_addr: dict[int, list[tuple[str, str]]] = defaultdict(list)

    for rule in FACT_RULES:
        if only_family and rule.fact_id != only_family:
            continue
        target_callee_set = set(rule.target_callees)
        target_lit_set = set(rule.target_literals)

        for addr, meta in by_addr.items():
            name = meta["name"]
            if name.startswith(("FUN_", "func_", "thunk_")):
                continue
            if rule.allow_re and rule.allow_re.search(name):
                continue
            if not rule.contradict_re.search(name):
                continue

            matched_reasons: list[str] = []
            if (rule.include_self and addr in target_callee_set) or addr in rule.self_only_targets:
                matched_reasons.append(f"self=0x{addr:08X}")
            callee_hits = sorted(callees.get(addr, set()) & target_callee_set)
            if callee_hits:
                matched_reasons.extend(f"calls 0x{c:08X}" for c in callee_hits)
            lit_hits = sorted(literals.get(addr, set()) & target_lit_set)
            if lit_hits:
                matched_reasons.extend(f"lit 0x{v:08X}" for v in lit_hits)

            if matched_reasons:
                hits_by_addr[addr].append((rule.fact_id, ", ".join(matched_reasons)))

    rows: list[dict] = []
    for addr, rule_hits in hits_by_addr.items():
        meta = by_addr[addr]
        cc = len(callers.get(addr, ()))
        facts_str = "; ".join(f"{fid} ({why})" for fid, why in rule_hits)
        rows.append(
            {
                "address": f"0x{addr:08X}",
                "addr_int": addr,
                "name": meta["name"],
                "confidence": meta["confidence"],
                "batch": meta["batch"],
                "change": meta.get("change", ""),
                "caller_count": cc,
                "fact_ids": [fid for fid, _ in rule_hits],
                "contradicted_fact": facts_str,
            }
        )

    rows.sort(key=lambda r: (-r["caller_count"], -len(r["fact_ids"]), r["addr_int"]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--exclude-overlay",
        action="append",
        default=[],
        help="Exclude one or more refine overlay stems (e.g. R_S02) when loading names.",
    )
    ap.add_argument("--family", help="Filter to a single fact_id (e.g. F01_Item_Lookup).")
    ap.add_argument("--limit", type=int, default=0, help="Limit printed table to top N rows (0 = all).")
    ap.add_argument("--json", type=Path, help="Write full ranked candidates to UTF-8 JSON file.")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    exclude = set(args.exclude_overlay)
    by_addr = load_symbols(exclude)
    callees, callers, literals = build_call_and_literal_graph(by_addr)
    rows = run_sweep(by_addr, callees, callers, literals, only_family=args.family)

    per_fact: dict[str, int] = defaultdict(int)
    for r in rows:
        for fid in r["fact_ids"]:
            per_fact[fid] += 1

    excl_note = f" (excluding {', '.join(sorted(exclude))})" if exclude else " (live)"
    print(f"misname_sweep{excl_note}: {len(rows)} candidate functions across {len(FACT_RULES)} fact rules")
    print("-" * 116)
    for rule in FACT_RULES:
        if args.family and rule.fact_id != args.family:
            continue
        print(f"  {rule.fact_id:<36} {per_fact[rule.fact_id]:>4}  {rule.description}")
    print("-" * 116)
    print(f"{'Address':<12} {'CallerCnt':>9}  {'Batch':<8} {'Conf':>4}  {'Current Name':<44} {'Fact Contradicted'}")
    print("-" * 116)

    shown = rows[: args.limit] if args.limit > 0 else rows
    for r in shown:
        print(
            f"{r['address']:<12} {r['caller_count']:>9}  {r['batch']:<8} {r['confidence']:>4.2f}  "
            f"{r['name']:<44} {r['contradicted_fact']}"
        )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {len(rows)} rows to {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
