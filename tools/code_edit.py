#!/usr/bin/env python3
"""Edit one native function (or translation code cave) as assembly, on the active game version.

The base is the active version's executable (tools.game_version: the retail code for
'original', the translation's patched code for 'en'); edits go to mod/code/code.bin, which the
exporter turns into code.ips / code.bin.  DQXI Studio's Code section uses these commands.

    python -m tools.code_edit show 0x00724A00            # editable listing (mod > version)
    python -m tools.code_edit show 0x00724A00 --from version|original|mod
    python -m tools.code_edit apply 0x00724A00 --asm edited.s   (or --asm - for stdin)
    python -m tools.code_edit revert 0x00724A00          # back to the version's bytes
    python -m tools.code_edit list                       # functions mod/code differs in
    python -m tools.code_edit info 0x00724A00 --json     # name, size, mode, patch notes

Listing lines look like `00724A00  04e02de5  push {lr}`; `apply` ignores the address/bytes
columns, so lines can be edited, added or removed freely.  Comments start with ';' or '@'.
Branch targets are absolute (`bl #0x724a00`).  The new code must fit in the function's
size (shorter code keeps the remaining bytes, use `--fill nop` to clear them) and must be
ARMv6K/VFPv2 only, or it crashes a real Old 3DS.
"""
from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import game_version as gv  # noqa: E402

MOD_CODE = ROOT / "mod" / "code" / "code.bin"
EDITS = ROOT / "mod" / "code" / "edits.json"
BASE = gv.BASE
NOP = bytes.fromhex("00f020e3")


class EditError(RuntimeError):
    pass


def version_code() -> bytes:
    return gv.code_path().read_bytes()


def current_code() -> bytes:
    return MOD_CODE.read_bytes() if MOD_CODE.is_file() else version_code()


def _catalogue() -> list[dict]:
    funcs = gv._functions()
    ch = gv.code_changes()
    patched = {f["address"]: f for f in ch.get("functions", [])}
    for f in funcs:
        if f["address"] in patched:
            p = patched[f["address"]]
            f.update(patch_kind=p["kind"], notes=p.get("notes", []), hooks=p.get("hooks", []))
    for c in ch.get("caves", []):
        funcs.append({"address": c["address"], "size": c["size"], "name": c["name"], "mode": c.get("mode", "arm"),
                      "file": "", "patch_kind": "cave", "notes": c.get("notes", []),
                      "called_from": c.get("called_from", [])})
    funcs.sort(key=lambda f: f["address"])
    return funcs


def find(addr: int) -> dict:
    funcs = _catalogue()
    starts = [f["address"] for f in funcs]
    i = bisect.bisect_right(starts, addr) - 1
    # caves come after their containing gap; prefer the innermost entry that holds addr
    for j in range(i, max(i - 4, -1), -1):
        f = funcs[j]
        if f["address"] <= addr < f["address"] + max(f["size"], 4):
            return f
    raise EditError(f"no function or code cave at 0x{addr:08X}")


def listing(code: bytes, f: dict) -> str:
    head = [f"; {f['name']}  0x{f['address']:08X}  {f['size']} bytes  {f['mode']}  "
            f"(game version: {gv.active()})"]
    for n in f.get("notes", [])[:6]:
        head.append(f"; {n}")
    return "\n".join(head + gv.disasm_range(code, f["address"], max(f["size"], 4), f["mode"])) + "\n"


_PREFIX = re.compile(r"^\s*(?:0x)?[0-9A-Fa-f]{8}\s+[0-9A-Fa-f]{4,8}\s+")


def assemble(text: str, addr: int, mode: str) -> bytes:
    import keystone
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB if mode == "thumb" else keystone.KS_MODE_ARM)
    out = bytearray()
    for no, raw in enumerate(text.splitlines(), 1):
        line = re.split(r"[;@]", raw, maxsplit=1)[0]
        line = _PREFIX.sub("", line).strip()
        if not line:
            continue
        m = re.fullmatch(r"\.word\s+(0x[0-9A-Fa-f]+|\d+)", line)
        if m:
            out += int(m.group(1), 0).to_bytes(4, "little")
            continue
        m = re.fullmatch(r"\.(?:short|hword)\s+(0x[0-9A-Fa-f]+|\d+)", line)
        if m:
            out += int(m.group(1), 0).to_bytes(2, "little")
            continue
        try:
            enc, _ = ks.asm(line, addr + len(out))
        except keystone.KsError as exc:
            raise EditError(f"line {no}: cannot assemble {line!r}: {exc}") from exc
        if not enc:
            raise EditError(f"line {no}: {line!r} produced no code")
        out += bytes(enc)
    return bytes(out)


def _armv6k(base: bytes, new: bytes) -> list[str]:
    from tools import check_armv6k as c6
    saved = c6.TEXT_END
    c6.TEXT_END = 0x00725000            # the translation's caves live after .text
    try:
        res = c6.check_code(base, new)
    finally:
        c6.TEXT_END = saved
    return [f"0x{h['address']:08X} {h['word']:08X} {h['name']}" for h in res["hits"] if not h.get("data")]


def _edits() -> dict:
    return gv._read_json(EDITS, {})


def _save(code: bytes, edits: dict) -> None:
    base = version_code()
    MOD_CODE.parent.mkdir(parents=True, exist_ok=True)
    if code == base:
        if MOD_CODE.is_file():
            MOD_CODE.unlink()
        if EDITS.is_file():
            EDITS.unlink()
        return
    MOD_CODE.write_bytes(code)
    edits["base_version"] = gv.active()
    edits["base_sha256"] = gv.sha(base)
    gv._write_json(EDITS, edits)


def check_base() -> None:
    """mod/code/code.bin must have been made on the active version's executable."""
    e = _edits()
    if MOD_CODE.is_file() and e.get("base_sha256") and e["base_sha256"] != gv.sha(version_code()):
        raise EditError(f"mod/code/code.bin was edited on version {e.get('base_version')!r}, which no longer "
                        "matches the active version's code (patch re-imported?). Revert or redo the edits.")


def apply(addr: int, text: str, fill: str | None, force: bool) -> dict:
    check_base()
    f = find(addr)
    if addr != f["address"]:
        raise EditError(f"0x{addr:08X} is inside {f['name']}; give its start 0x{f['address']:08X}")
    size = max(f["size"], 4)
    new_bytes = assemble(text, f["address"], f["mode"])
    if len(new_bytes) > size:
        raise EditError(f"{len(new_bytes)} bytes do not fit in {f['name']} ({size} bytes); "
                        "branch to free space instead (see versions/<name>/code_changes.json caves)")
    code = bytearray(current_code())
    off = f["address"] - BASE
    if fill == "nop" and len(new_bytes) < size:
        step = 2 if f["mode"] == "thumb" else 4
        pad = (bytes.fromhex("c046") if step == 2 else NOP) * ((size - len(new_bytes)) // step)
        new_bytes = new_bytes + pad
    code[off:off + len(new_bytes)] = new_bytes
    base = version_code()
    bad = _armv6k(base, bytes(code))
    if bad and not force:
        raise EditError("instructions a real Old 3DS cannot run (ARMv6K/VFPv2 only):\n  " + "\n  ".join(bad[:20]))
    edits = _edits()
    fn = edits.setdefault("functions", {})
    if bytes(code[off:off + size]) == base[off:off + size]:
        fn.pop(f"{f['address']:08X}", None)
    else:
        fn[f"{f['address']:08X}"] = {"name": f["name"], "size": size, "bytes": len(new_bytes)}
    _save(bytes(code), edits)
    return {"function": f["name"], "address": f"0x{f['address']:08X}", "bytes": len(new_bytes), "size": size}


def revert(addr: int) -> dict:
    f = find(addr)
    size = max(f["size"], 4)
    off = f["address"] - BASE
    code = bytearray(current_code())
    code[off:off + size] = version_code()[off:off + size]
    edits = _edits()
    edits.get("functions", {}).pop(f"{f['address']:08X}", None)
    _save(bytes(code), edits)
    return {"function": f["name"], "reverted": True}


def changed_list() -> list[dict]:
    if not MOD_CODE.is_file():
        return []
    base, mod = version_code(), MOD_CODE.read_bytes()
    funcs = _catalogue()
    starts = [f["address"] for f in funcs]
    seen = {}
    for s, e in gv._runs(base, mod, gap=4):
        a = BASE + s
        i = bisect.bisect_right(starts, a) - 1
        f = funcs[i] if i >= 0 and funcs[i]["address"] <= a < funcs[i]["address"] + max(funcs[i]["size"], 4) else None
        key = f["address"] if f else a
        seen.setdefault(key, {"address": f"0x{key:08X}", "name": f["name"] if f else "(no function)", "bytes": 0})
        seen[key]["bytes"] += e - s
    return list(seen.values())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("address")
    s.add_argument("--from", dest="src", choices=["mod", "version", "original"], default="mod")
    a = sub.add_parser("apply")
    a.add_argument("address")
    a.add_argument("--asm", required=True, help="file with the new listing, or - for stdin")
    a.add_argument("--fill", choices=["keep", "nop"], default="keep")
    a.add_argument("--force", action="store_true", help="skip the ARMv6K check")
    r = sub.add_parser("revert")
    r.add_argument("address")
    sub.add_parser("list")
    i = sub.add_parser("info")
    i.add_argument("address")
    i.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        if args.cmd == "show":
            f = find(int(args.address, 16))
            code = {"mod": current_code, "version": version_code,
                    "original": lambda: gv.RETAIL_CODE.read_bytes()}[args.src]()
            sys.stdout.write(listing(code, f))
        elif args.cmd == "apply":
            text = sys.stdin.read() if args.asm == "-" else Path(args.asm).read_text(encoding="utf-8")
            res = apply(int(args.address, 16), text, args.fill, args.force)
            print(f"assembled {res['bytes']} of {res['size']} bytes into {res['function']} ({res['address']}) "
                  f"-> mod/code/code.bin")
        elif args.cmd == "revert":
            res = revert(int(args.address, 16))
            print(f"{res['function']}: back to the {gv.active()} version's bytes")
        elif args.cmd == "list":
            for row in changed_list():
                print(f"{row['address']}  {row['bytes']:>5} B  {row['name']}")
        elif args.cmd == "info":
            f = find(int(args.address, 16))
            print(json.dumps(f, indent=1) if args.json else f"{f['name']} 0x{f['address']:08X} {f['size']} B {f['mode']}")
    except EditError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
