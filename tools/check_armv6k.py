"""Refuse native code that a real 3DS cannot execute (ARMv6K / VFPv2 only).

Why this exists
---------------
Azahar (like Citra) also executes ARMv7 / VFPv3 instructions.  A code cave that works in the
emulator can therefore crash a real 3DS/2DS with "undefined instruction" -- exactly what
happened in the translation project on 2026-10-17 when a `vmov.f32 s16, #1.0` (VFPv3) was
used.  Emulator testing cannot catch it, so the exporter must.

This is a port of that project's `emutest/armv6check.py`, with two deliberate improvements:

* only the **executable** range is scanned (.text 0x100000-0x72403C plus its zero-filled tail
  pad to 0x725000; `sections.ld`), so `.rodata`/`.data` words can never be mistaken for
  instructions;
* PC-relative literal-pool words are skipped (they are data, not instructions).  This is the
  "ldrd hits are literal pools" caveat from the original, detected instead of left to the
  reader.

Usage
-----
    python tools/check_armv6k.py                     # retail vs mod/code/code.bin
    python tools/check_armv6k.py ORIG.bin PATCHED.bin
    python tools/check_armv6k.py --json               # machine-readable result

Exit codes: 0 = clean, 1 = forbidden instruction(s), 2 = unreadable/size mismatch.

It is also called by ``tools/export_mod.py`` before anything is written; an export with a
forbidden changed instruction stops with exit code 2.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = 0x100000
# sections.ld: .text ends at 0x72403C; the 4,036-byte tail pad is executable and is where the
# test hook lives (0x724F00).  .rodata starts at 0x725000 and is not code.
TEXT_START = 0x100000
TEXT_END = 0x725000

# (name, mask, value) for ARM instructions (condition != 0xF) that ARMv6K / VFPv2 cannot run.
# The values are the same encodings the translation project's check uses; a match is only
# reported for a word that this patch CHANGED, so retail data is irrelevant.
PATTERNS = (
    ("vmov.f32/f64 #imm (VFPv3)", 0x0FB00EF0, 0x0EB00A00),
    ("movw (ARMv6T2)", 0x0FF00000, 0x03000000),
    ("movt (ARMv6T2)", 0x0FF00000, 0x03400000),
    ("ubfx/sbfx (ARMv6T2)", 0x0FA00070, 0x07A00050),
    ("bfi/bfc (ARMv6T2)", 0x0FE00070, 0x07C00010),
    ("sdiv/udiv (ARMv7VE)", 0x0FD0F0F0, 0x0710F010),
    ("mls (ARMv6T2)", 0x0FF000F0, 0x00600090),
    ("rbit (ARMv6T2)", 0x0FFF0FF0, 0x06FF0F30),
    ("ldrd/strd w/ T (ARMv6T2)", 0x0F2000F0, 0x002000B0),
    ("vcvt fixed (VFPv3)", 0x0FBA0E50, 0x0EBA0A40),
)


def literal_words(code: bytes) -> set[int]:
    """Guest addresses that a PC-relative ``ldr`` loads from (ARM literal pools)."""
    out: set[int] = set()
    end = min(len(code), TEXT_END - BASE)
    for off in range(0, end - 3, 4):
        w, = struct.unpack_from("<I", code, off)
        if (w & 0x0F5F0000) != 0x051F0000:      # ldr Rd, [pc, #+/-imm] (not byte, not pc dest)
            continue
        rd = (w >> 12) & 0xF
        if rd == 15:                            # `ldr pc, ...` is a jump, its target is code
            continue
        imm = w & 0xFFF
        addr = BASE + off + 8 + (imm if w & 0x00800000 else -imm)
        out.add(addr)
    return out


def check_code(original: bytes, patched: bytes, *, include_data: bool = False) -> dict:
    """Compare two decompressed executables and return every forbidden changed word.

    ``original``/``patched`` must be the same length (the exporter's code.bin contract).
    Returns ``{"ok": bool, "hits": [...], "changed_words": n, "scanned_bytes": n}``.
    """
    if len(original) != len(patched):
        raise ValueError(f"code images differ in length: {len(original)} vs {len(patched)}")
    literals = set() if include_data else literal_words(patched)
    hits = []
    changed = 0
    start = TEXT_START - BASE
    end = min(len(patched), TEXT_END - BASE)
    for off in range(start, end - 3, 4):
        w_new, = struct.unpack_from("<I", patched, off)
        w_old, = struct.unpack_from("<I", original, off)
        if w_new == w_old:
            continue
        changed += 1
        guest = BASE + off
        if guest in literals:
            hits.append({"address": guest, "word": w_new, "name": "literal pool (data)",
                         "data": True, "allowed": include_data})
            continue
        if (w_new >> 28) == 0xF:                # BLX/unconditional encoding: allowed
            continue
        for name, mask, value in PATTERNS:
            if (w_new & mask) == value:
                hits.append({"address": guest, "word": w_new, "name": name,
                             "data": False, "allowed": False})
                break
    real = [h for h in hits if not h.get("data")]
    return {"ok": not real, "hits": hits, "changed_words": changed,
            "scanned_bytes": max(0, end - start)}


def format_hits(result: dict) -> str:
    lines = []
    for hit in result["hits"]:
        mark = "data, skipped" if hit.get("data") else "FORBIDDEN"
        lines.append(f"  0x{hit['address']:08X}  {hit['word']:08X}  {hit['name']}  ({mark})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("original", nargs="?", default=str(ROOT / "original" / "exefs" /
                                                      "code.decompressed.bin"),
                    help="retail decompressed executable")
    ap.add_argument("patched", nargs="?", default=str(ROOT / "mod" / "code" / "code.bin"),
                    help="patched decompressed executable")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    ap.add_argument("--include-data", action="store_true",
                    help="also report literal-pool words (debugging only)")
    a = ap.parse_args(argv)
    try:
        original = Path(a.original).read_bytes()
        patched = Path(a.patched).read_bytes()
        result = check_code(original, patched, include_data=a.include_data)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    result["original"] = a.original
    result["patched"] = a.patched
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        real = [h for h in result["hits"] if not h.get("data")]
        print(f"ARMv6K/VFPv2 check: {result['changed_words']} changed words in "
              f"0x{TEXT_START:X}-0x{TEXT_END:X}")
        if result["hits"]:
            print(format_hits(result))
        if real:
            print(f"{len(real)} changed instruction(s) a real 3DS/2DS cannot execute")
            print("Replace them with ARMv6K/VFPv2 code (no movw/movt, ubfx/sbfx/bfi/bfc, "
                  "sdiv/udiv, mls, rbit, VFP immediates or fixed-point vcvt).")
        else:
            print("OK: every changed instruction is ARMv6K/VFPv2-safe.")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
