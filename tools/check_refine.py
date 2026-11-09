"""Check a refine batch's output before the dispatcher accepts it.

    python tools/check_refine.py R_007          # exit 0 = accepted, 1 = problems (printed)

Hard errors (the batch is sent back): missing/extra addresses, bad JSON, invalid identifiers,
`change` not one of the three values, confidence < 0.5 without the `maybe_` prefix (or >= 0.5
with it), `confirmed` whose name is not the previous name minus `maybe_`.

Known-misread flags (also sent back; see orchestration/naming/FACTS.md): a Text/Glyph/Char/Font
name on a function that resolves item rows or indexes member inventory; a Check/Is/Has/Can name
on a `void` function (Ghidra dropped the return value); confidence >= 0.5 on a damaged body.
A flagged entry passes once its evidence mentions why the flag does not apply.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFINE = ROOT / "orchestration" / "naming" / "refine"
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TEXTY = re.compile(r"(^|_)(maybe_)?(Text|Glyph|Char|Font)|CharSet|Glyph|Char(?!a)", re.I)
ITEMY = re.compile(r"Item_LookupRecord|func_006292A4|\+\s*0xec\b|0x24a98|0x24800", re.I)
PREDICATE = re.compile(r"(^|_)(Check|Is|Has|Can)[A-Z0-9]")
DAMAGED = re.compile(r"unaff_r\d|in_NG|in_ZR|in_OV|coprocessor_")
WAIVER = re.compile(r"not an item|not item|flag does not apply|returns? (a )?value|getter|damaged", re.I)


def norm(a: str) -> str:
    return "0x" + str(a).upper().replace("0X", "").zfill(8)


def check(batch: str) -> list[str]:
    rows = {}
    for line in (REFINE / "batches" / f"{batch}.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("0x"):
            addr, name, conf, path = line.split("\t")[:4]
            rows[norm(addr)] = (name, path)
    out = REFINE / "out" / f"{batch}.json"
    try:
        data = json.loads(out.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as e:
        return [f"{out.name}: cannot read JSON ({e})"]
    if not isinstance(data, list):
        return [f"{out.name}: top level must be a JSON array"]
    errs, seen = [], set()
    for e in data:
        if not isinstance(e, dict) or "address" not in e:
            errs.append(f"entry without address: {str(e)[:60]}")
            continue
        a = norm(e["address"])
        seen.add(a)
        if a not in rows:
            errs.append(f"{a}: not in the batch")
            continue
        prev, path = rows[a]
        name = str(e.get("name", ""))
        ev = str(e.get("evidence", "")) + " " + str(e.get("summary", ""))
        try:
            conf = float(e.get("confidence"))
        except (TypeError, ValueError):
            errs.append(f"{a}: confidence missing or not a number")
            continue
        if not IDENT.match(name):
            errs.append(f"{a}: invalid C identifier {name!r}")
        if e.get("change") not in ("confirmed", "corrected", "kept_maybe"):
            errs.append(f"{a}: change must be confirmed|corrected|kept_maybe, got {e.get('change')!r}")
        if (conf < 0.5) != name.startswith("maybe_"):
            errs.append(f"{a}: {name} at confidence {conf}: below 0.5 needs maybe_, 0.5+ must drop it")
        if e.get("change") == "confirmed" and name != prev.removeprefix("maybe_"):
            errs.append(f"{a}: confirmed must be {prev.removeprefix('maybe_')!r}, got {name!r} (use corrected)")
        try:
            body = (ROOT / path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        code = body.split("*/", 1)[-1]
        if TEXTY.search(name) and ITEMY.search(code) and not WAIVER.search(ev):
            errs.append(f"{a}: {name} looks like text code but the body resolves items / member inventory "
                        "(FACTS.md: Items, shop, inventory). Rename, or say in evidence why it is not item code.")
        sig = re.search(r"Signature:\s*(\w[\w\s\*]*?)\s+\w+\(", body)
        if PREDICATE.search(name.removeprefix("maybe_")) and sig and sig.group(1).strip() == "void" \
                and not WAIVER.search(ev):
            errs.append(f"{a}: {name} is a predicate name on a void function; Ghidra may have dropped a "
                        "returned value (FACTS.md: Ghidra traps). Check the callee, or explain in evidence.")
        if conf >= 0.5 and DAMAGED.search(code) and not WAIVER.search(ev):
            errs.append(f"{a}: confidence {conf} on a damaged decompilation (unaff_/flag registers); "
                        "keep maybe_ <= 0.3 or cite the disassembly in evidence.")
    missing = sorted(set(rows) - seen)
    if missing:
        errs.append(f"{len(missing)} batch addresses missing, e.g. {', '.join(missing[:8])}")
    return errs


def main() -> int:
    errs = check(sys.argv[1])
    for e in errs:
        print(e)
    print(f"{sys.argv[1]}: {'OK' if not errs else f'{len(errs)} problem(s)'}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
