#!/usr/bin/env python3
"""tools/sqbin.py - Compiled Squirrel script (.cnut) parser, builder, disassembler, and assembler.

Supports full parse, rebuild, human-readable disassembly, structured JSON export,
and text assembly of DQXI 3DS Squirrel 3.0 scripts with the game's Squirrel 2.2 bytecode
instruction set.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

HEAD, PART, TAIL = b"RIQS", b"TRAP", b"LIAT"
OT_NULL, OT_INTEGER, OT_FLOAT, OT_BOOL, OT_STRING = 0x01000001, 0x05000002, 0x05000004, 0x01000008, 0x08000010

OPS = [
    "LINE", "LOAD", "LOADINT", "LOADFLOAT", "DLOAD", "TAILCALL", "CALL", "PREPCALL", "PREPCALLK",
    "GETK", "MOVE", "NEWSLOT", "DELETE", "SET", "GET", "EQ", "NE", "ARITH", "BITW", "RETURN",
    "LOADNULLS", "LOADROOTTABLE", "LOADBOOL", "DMOVE", "JMP", "JNZ", "JZ", "LOADFREEVAR", "VARGC",
    "GETVARGV", "NEWTABLE", "NEWARRAY", "APPENDARRAY", "GETPARENT", "COMPARITH", "COMPARITHL", "INC",
    "INCL", "PINC", "PINCL", "CMP", "EXISTS", "INSTANCEOF", "AND", "OR", "NEG", "NOT", "BWNOT",
    "CLOSURE", "YIELD", "RESUME", "FOREACH", "POSTFOREACH", "DELEGATE", "CLONE", "TYPEOF",
    "PUSHTRAP", "POPTRAP", "THROW", "CLASS", "NEWSLOTA"
]
OP = {n: i for i, n in enumerate(OPS)}


@dataclass
class Obj:
    type: int
    value: object = None

    def __repr__(self):
        return repr(self.value) if self.type != OT_NULL else "null"


def S(text: str) -> Obj:
    return Obj(OT_STRING, text)


def I(v: int) -> Obj:
    return Obj(OT_INTEGER, v)


@dataclass
class Insn:
    op: int
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0
    arg3: int = 0

    def __repr__(self):
        return f"{OPS[self.op] if self.op < len(OPS) else self.op:<10} {self.arg0:3} {self.arg1:6} {self.arg2:3} {self.arg3:3}"


@dataclass
class Func:
    sourcename: Obj
    name: Obj
    literals: list = field(default_factory=list)
    parameters: list = field(default_factory=list)
    outervalues: list = field(default_factory=list)
    localvarinfos: list = field(default_factory=list)
    lineinfos: list = field(default_factory=list)
    defaultparams: list = field(default_factory=list)
    instructions: list = field(default_factory=list)
    functions: list = field(default_factory=list)
    stacksize: int = 0
    bgenerator: int = 0
    varparams: int = 0

    def find(self, name: str) -> "Func | None":
        if self.name.value == name:
            return self
        for f in self.functions:
            r = f.find(name)
            if r:
                return r
        return None

    def walk(self):
        yield self
        for f in self.functions:
            yield from f.walk()


class _R:
    def __init__(self, d: bytes):
        self.d, self.o = d, 0

    def u32(self):
        v = struct.unpack_from("<I", self.d, self.o)[0]
        self.o += 4
        return v

    def u8(self):
        v = self.d[self.o]
        self.o += 1
        return v

    def tag(self, t):
        if self.d[self.o:self.o + 4] != t:
            raise ValueError(f"expected {t} at {self.o:#x}, got {self.d[self.o:self.o + 4]!r}")
        self.o += 4

    def obj(self) -> Obj:
        t = self.u32()
        if t == OT_STRING:
            n = self.u32()
            s = self.d[self.o:self.o + n].decode("utf-8", "replace")
            self.o += n
            return Obj(t, s)
        if t == OT_INTEGER:
            return Obj(t, struct.unpack("<i", struct.pack("<I", self.u32()))[0])
        if t == OT_FLOAT:
            return Obj(t, struct.unpack("<f", struct.pack("<I", self.u32()))[0])
        if t == OT_BOOL:
            return Obj(t, self.u32())
        if t == OT_NULL:
            return Obj(t)
        raise ValueError(f"object type {t:#x} at {self.o - 4:#x}")


def _func(r: _R) -> Func:
    r.tag(PART)
    f = Func(r.obj(), r.obj())
    r.tag(PART)
    nlit, npar, nout, nloc, nline, ndef, nins, nfun = (r.u32() for _ in range(8))
    r.tag(PART)
    f.literals = [r.obj() for _ in range(nlit)]
    r.tag(PART)
    f.parameters = [r.obj() for _ in range(npar)]
    r.tag(PART)
    f.outervalues = [(r.u32(), r.obj(), r.obj()) for _ in range(nout)]
    r.tag(PART)
    f.localvarinfos = [(r.obj(), r.u32(), r.u32(), r.u32()) for _ in range(nloc)]
    r.tag(PART)
    f.lineinfos = [(r.u32(), r.u32()) for _ in range(nline)]
    r.tag(PART)
    f.defaultparams = [r.u32() for _ in range(ndef)]
    r.tag(PART)
    for _ in range(nins):
        a1, op, a0, a2, a3 = struct.unpack_from("<iBBBB", r.d, r.o)
        r.o += 8
        f.instructions.append(Insn(op, a0, a1, a2, a3))
    r.tag(PART)
    f.functions = [_func(r) for _ in range(nfun)]
    f.stacksize, f.bgenerator, f.varparams = r.u32(), r.u8(), r.u8()
    return f


def parse(data: bytes) -> Func:
    r = _R(data)
    if data[:2] != b"\xfa\xfa":
        raise ValueError("not a cnut")
    r.o = 2
    r.tag(HEAD)
    if r.u32() != 1:
        raise ValueError("SQChar size != 1")
    f = _func(r)
    r.tag(TAIL)
    if r.o != len(data):
        raise ValueError(f"trailing data at {r.o:#x}")
    return f


def _obj(o: Obj) -> bytes:
    b = struct.pack("<I", o.type)
    if o.type == OT_STRING:
        s = o.value.encode("utf-8") if isinstance(o.value, str) else str(o.value).encode("utf-8")
        return b + struct.pack("<I", len(s)) + s
    if o.type == OT_INTEGER:
        return b + struct.pack("<i", int(o.value) if o.value is not None else 0)
    if o.type == OT_FLOAT:
        return b + struct.pack("<f", float(o.value) if o.value is not None else 0.0)
    if o.type == OT_BOOL:
        return b + struct.pack("<I", 1 if o.value else 0)
    return b


def _build(f: Func) -> bytes:
    out = [
        PART, _obj(f.sourcename), _obj(f.name), PART,
        struct.pack("<8I", len(f.literals), len(f.parameters), len(f.outervalues), len(f.localvarinfos),
                    len(f.lineinfos), len(f.defaultparams), len(f.instructions), len(f.functions)), PART
    ]
    out += [_obj(o) for o in f.literals]
    out.append(PART)
    out += [_obj(o) for o in f.parameters]
    out.append(PART)
    for t, s, n in f.outervalues:
        out += [struct.pack("<I", t), _obj(s), _obj(n)]
    out.append(PART)
    for n, p, a, b in f.localvarinfos:
        out += [_obj(n), struct.pack("<3I", p, a, b)]
    out.append(PART)
    out += [struct.pack("<2I", *li) for li in f.lineinfos]
    out.append(PART)
    out += [struct.pack("<I", d) for d in f.defaultparams]
    out.append(PART)
    out += [struct.pack("<iBBBB", i.arg1, i.op, i.arg0, i.arg2, i.arg3) for i in f.instructions]
    out.append(PART)
    out += [_build(g) for g in f.functions]
    out.append(struct.pack("<IBB", f.stacksize, f.bgenerator, f.varparams))
    return b"".join(out)


def build(f: Func) -> bytes:
    """Serialize a Func structure back into identical Squirrel .cnut binary bytecode."""
    return b"\xfa\xfa" + HEAD + struct.pack("<I", 1) + _build(f) + TAIL


# ---------------------------------------------------------------------------
# JSON Serialization / Deserialization
# ---------------------------------------------------------------------------

def obj_to_dict(o: Obj) -> dict:
    return {"type": o.type, "value": o.value}


def dict_to_obj(d: dict) -> Obj:
    return Obj(type=d["type"], value=d.get("value"))


def insn_to_dict(i: Insn) -> dict:
    return {
        "op": i.op,
        "op_name": OPS[i.op] if i.op < len(OPS) else str(i.op),
        "arg0": i.arg0,
        "arg1": i.arg1,
        "arg2": i.arg2,
        "arg3": i.arg3,
    }


def dict_to_insn(d: dict) -> Insn:
    op = d["op"]
    if isinstance(op, str):
        op = OP.get(op, int(op))
    return Insn(op, d.get("arg0", 0), d.get("arg1", 0), d.get("arg2", 0), d.get("arg3", 0))


def func_to_dict(f: Func) -> dict:
    """Convert Func object tree to a JSON-serializable dictionary."""
    return {
        "sourcename": obj_to_dict(f.sourcename),
        "name": obj_to_dict(f.name),
        "stacksize": f.stacksize,
        "bgenerator": f.bgenerator,
        "varparams": f.varparams,
        "literals": [obj_to_dict(o) for o in f.literals],
        "parameters": [obj_to_dict(o) for o in f.parameters],
        "outervalues": [
            {"type": t, "src": obj_to_dict(s), "name": obj_to_dict(n)}
            for t, s, n in f.outervalues
        ],
        "localvarinfos": [
            {"name": obj_to_dict(n), "pos": p, "start_op": a, "end_op": b}
            for n, p, a, b in f.localvarinfos
        ],
        "lineinfos": [list(li) for li in f.lineinfos],
        "defaultparams": list(f.defaultparams),
        "instructions": [insn_to_dict(i) for i in f.instructions],
        "functions": [func_to_dict(g) for g in f.functions],
    }


def dict_to_func(d: dict) -> Func:
    """Reconstruct Func object tree from a dictionary."""
    return Func(
        sourcename=dict_to_obj(d["sourcename"]),
        name=dict_to_obj(d["name"]),
        literals=[dict_to_obj(o) for o in d.get("literals", [])],
        parameters=[dict_to_obj(o) for o in d.get("parameters", [])],
        outervalues=[
            (x["type"], dict_to_obj(x["src"]), dict_to_obj(x["name"]))
            for x in d.get("outervalues", [])
        ],
        localvarinfos=[
            (dict_to_obj(x["name"]), x["pos"], x["start_op"], x["end_op"])
            for x in d.get("localvarinfos", [])
        ],
        lineinfos=[tuple(li) for li in d.get("lineinfos", [])],
        defaultparams=list(d.get("defaultparams", [])),
        instructions=[dict_to_insn(i) for i in d.get("instructions", [])],
        functions=[dict_to_func(g) for g in d.get("functions", [])],
        stacksize=d.get("stacksize", 0),
        bgenerator=d.get("bgenerator", 0),
        varparams=d.get("varparams", 0),
    )


def func_to_json(f: Func, indent: int = 2) -> str:
    """Serialize Func tree to structured JSON string."""
    return json.dumps(func_to_dict(f), indent=indent, ensure_ascii=False)


def json_to_func(data: str | dict) -> Func:
    """Deserialize Func tree from JSON string or dictionary."""
    if isinstance(data, str):
        data = json.loads(data)
    return dict_to_func(data)


# ---------------------------------------------------------------------------
# Disassembly and Assembly
# ---------------------------------------------------------------------------

def disasm(f: Func, indent: str = "") -> str:
    """Human-readable Squirrel script disassembly with round-trip metadata."""
    params_str = ", ".join(repr(p.value) for p in f.parameters)
    source_val = repr(f.sourcename.value) if f.sourcename.type != OT_NULL else "null"
    out = [f"{indent}function {f.name!r}({params_str}) /* stack={f.stacksize} bgen={f.bgenerator} varp={f.varparams} source={source_val} */ {{"]

    if f.outervalues:
        out.append(f"{indent}  // Outervalues: {[(t, s.value, n.value) for t, s, n in f.outervalues]!r}")

    if f.lineinfos:
        out.append(f"{indent}  // Lineinfos: {f.lineinfos!r}")

    if f.defaultparams:
        out.append(f"{indent}  // Defaultparams: {f.defaultparams!r}")

    if f.literals:
        out.append(f"{indent}  // Literals ({len(f.literals)}):")
        for k, o in enumerate(f.literals):
            out.append(f"{indent}  //   lit[{k:2d}] = {o.type:#010x}:{o.value!r}")

    if f.localvarinfos:
        out.append(f"{indent}  // Local variables:")
        for n, p, a, b in f.localvarinfos:
            out.append(f"{indent}  //   var {n.value} (slot {p}, ops {a}..{b})")

    out.append(f"{indent}  // Bytecode instructions:")
    for k, i in enumerate(f.instructions):
        note = ""
        if i.op in (OP["LOAD"], OP["PREPCALLK"], OP["GETK"]) and 0 <= i.arg1 < len(f.literals):
            note = f"  // lit: {f.literals[i.arg1]!r}"
        elif i.op == OP["DLOAD"] and i.arg3 < len(f.literals):
            note = f"  // lit: {f.literals[i.arg1]!r}, {f.literals[i.arg3]!r}"
        elif i.op == OP["CLOSURE"] and 0 <= i.arg1 < len(f.functions):
            note = f"  // closure: {f.functions[i.arg1].name!r}"
        out.append(f"{indent}  [{k:4d}] {i!r}{note}")

    for g in f.functions:
        out.append("")
        out.append(disasm(g, indent + "  "))

    out.append(f"{indent}}}")
    return "\n".join(out)


def assemble_nut(text: str) -> Func:
    """Assemble human-readable Squirrel disassembly back into a Func structure."""
    lines = text.splitlines()
    idx = 0

    def parse_func() -> Func:
        nonlocal idx
        while idx < len(lines) and not lines[idx].strip().startswith("function"):
            idx += 1
        if idx >= len(lines):
            raise ValueError("Expected function definition")

        hdr = lines[idx].strip()
        idx += 1

        # Match function header
        m_name = re.search(r"function\s+(?:'([^']*)'|\"([^\"]*)\"|(\w+)|null)\s*\((.*?)\)", hdr)
        fname = m_name.group(1) or m_name.group(2) or m_name.group(3) or ""
        params_str = m_name.group(4).strip() if m_name else ""

        m_stack = re.search(r"stack=(\d+)", hdr)
        stacksize = int(m_stack.group(1)) if m_stack else 10

        m_bgen = re.search(r"bgen=(\d+)", hdr)
        bgen = int(m_bgen.group(1)) if m_bgen else 0

        m_varp = re.search(r"varp=(\d+)", hdr)
        varp = int(m_varp.group(1)) if m_varp else 0

        m_src = re.search(r"source=(?:'([^']*)'|\"([^\"]*)\"|null)", hdr)
        sourcename = ""
        if m_src:
            s_raw = m_src.group(0).split("=", 1)[1].strip()
            if s_raw == "null":
                sourcename = None
            else:
                sourcename = ast.literal_eval(s_raw)

        parameters = []
        if params_str:
            for p in params_str.split(","):
                p = p.strip()
                if p:
                    if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
                        val = ast.literal_eval(p)
                    else:
                        val = p
                    parameters.append(Obj(OT_STRING, val))

        func = Func(
            sourcename=Obj(OT_STRING, sourcename) if sourcename is not None else Obj(OT_NULL),
            name=Obj(OT_STRING, fname) if fname and fname != "null" else Obj(OT_NULL),
            stacksize=stacksize,
            bgenerator=bgen,
            varparams=varp,
            parameters=parameters,
        )

        while idx < len(lines):
            line = lines[idx].strip()
            if line.startswith("function"):
                func.functions.append(parse_func())
                continue
            idx += 1
            if line == "}":
                break

            if line.startswith("// Outervalues:"):
                val_str = line.split(":", 1)[1].strip()
                ov_list = ast.literal_eval(val_str)
                func.outervalues = [
                    (item[0], Obj(OT_STRING, item[1]), Obj(OT_STRING, item[2]))
                    for item in ov_list
                ]
            elif line.startswith("// Lineinfos:"):
                val_str = line.split(":", 1)[1].strip()
                func.lineinfos = [tuple(x) for x in ast.literal_eval(val_str)]
            elif line.startswith("// Defaultparams:"):
                val_str = line.split(":", 1)[1].strip()
                func.defaultparams = list(ast.literal_eval(val_str))
            elif line.startswith("//   lit["):
                m_lit = re.search(r"lit\[\s*\d+\]\s*=\s*(?:(0x[0-9a-fA-F]+):)?(.*)", line)
                if m_lit:
                    type_str, val_part = m_lit.group(1), m_lit.group(2).strip()
                    if type_str:
                        lit_type = int(type_str, 16)
                        try:
                            lit_val = ast.literal_eval(val_part)
                        except Exception:
                            lit_val = val_part
                    else:
                        if val_part == "null":
                            lit_type, lit_val = OT_NULL, None
                        elif val_part in ("True", "true", "False", "false"):
                            lit_type, lit_val = OT_BOOL, 1 if val_part.lower() == "true" else 0
                        elif (val_part.startswith("'") and val_part.endswith("'")) or (val_part.startswith('"') and val_part.endswith('"')):
                            lit_type, lit_val = OT_STRING, ast.literal_eval(val_part)
                        elif "." in val_part:
                            lit_type, lit_val = OT_FLOAT, float(val_part)
                        else:
                            try:
                                lit_type, lit_val = OT_INTEGER, int(val_part)
                            except ValueError:
                                lit_type, lit_val = OT_STRING, val_part
                    func.literals.append(Obj(lit_type, lit_val))
            elif line.startswith("//   var "):
                m_var = re.search(r"var\s+(\w+)\s+\(slot\s+(\d+),\s+ops\s+(\d+)\.\.(\d+)\)", line)
                if m_var:
                    vname = m_var.group(1)
                    pos = int(m_var.group(2))
                    start_op = int(m_var.group(3))
                    end_op = int(m_var.group(4))
                    func.localvarinfos.append((Obj(OT_STRING, vname), pos, start_op, end_op))
            elif line.startswith("[") and "]" in line:
                m_ins = re.match(r"\[\s*\d+\]\s+([A-Z0-9_]+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", line)
                if m_ins:
                    op_name = m_ins.group(1)
                    op_code = OP.get(op_name)
                    if op_code is None:
                        op_code = int(op_name)
                    arg0 = int(m_ins.group(2))
                    arg1 = int(m_ins.group(3))
                    arg2 = int(m_ins.group(4))
                    arg3 = int(m_ins.group(5))
                    func.instructions.append(Insn(op_code, arg0, arg1, arg2, arg3))

        return func

    return parse_func()


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_all(limit: int | None = None, romfs_image: str | Path | None = None) -> bool:
    """Verify parse -> build and disasm -> assemble bit-matching across RomFS script packs."""
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root))
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    from tools import pack

    rom_path = str(romfs_image) if romfs_image else r"..\reference project\DQXI.3ds"
    f, ncsd, ncch = open_image(rom_path)
    romfs = ncch.romfs()
    script_files = [x for x in romfs.files if x.path.startswith("/script/") and x.path.endswith(".pack")]
    if limit:
        script_files = script_files[:limit]

    print(f"Verifying {len(script_files)} script packs...")
    total_scripts = 0
    all_ok = True

    for i, sf in enumerate(script_files):
        p = pack.Pack.parse(romfs.read_file(sf))
        for entry in p.entries:
            if entry.name.endswith(".cnut"):
                total_scripts += 1
                try:
                    func = parse(entry.data)
                    rebuilt = build(func)
                    if rebuilt != entry.data:
                        print(f"  [FAIL] Binary rebuild mismatch in {sf.path}:{entry.name}")
                        all_ok = False
                        continue

                    # Test JSON round-trip
                    j = func_to_json(func)
                    f_json = json_to_func(j)
                    if build(f_json) != entry.data:
                        print(f"  [FAIL] JSON round-trip mismatch in {sf.path}:{entry.name}")
                        all_ok = False
                        continue

                    # Test Assembly round-trip
                    dis_text = disasm(func)
                    f_asm = assemble_nut(dis_text)
                    if build(f_asm) != entry.data:
                        print(f"  [FAIL] Assembly round-trip mismatch in {sf.path}:{entry.name}")
                        all_ok = False
                        continue

                except Exception as e:
                    print(f"  [ERROR] Exception processing {sf.path}:{entry.name}: {e}")
                    all_ok = False

    f.close()
    status = "SUCCESS" if all_ok else "FAILURE"
    print(f"Verification {status}: Checked {total_scripts} scripts across {len(script_files)} packs. Bit-matching: {all_ok}")
    return all_ok


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="DQXI Squirrel (.cnut) Script Tool")
    parser.add_argument("--disasm", type=Path, help="Disassemble .cnut to .nut")
    parser.add_argument("--assemble", type=Path, help="Assemble .nut to .cnut")
    parser.add_argument("--json", type=Path, help="Export .cnut to .json")
    parser.add_argument("--from-json", type=Path, help="Build .cnut from .json")
    parser.add_argument("-o", "--output", type=Path, help="Output file path")
    parser.add_argument("--verify", action="store_true", help="Verify bit-matching on RomFS script packs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of packs to verify")
    args = parser.parse_args()

    if args.verify:
        ok = verify_all(limit=args.limit)
        sys.exit(0 if ok else 1)

    if args.disasm:
        data = args.disasm.read_bytes()
        func = parse(data)
        out_text = disasm(func)
        if args.output:
            args.output.write_text(out_text, encoding="utf-8")
        else:
            print(out_text)
        return

    if args.assemble:
        text = args.assemble.read_text(encoding="utf-8")
        func = assemble_nut(text)
        bin_data = build(func)
        out_path = args.output or args.assemble.with_suffix(".cnut")
        out_path.write_bytes(bin_data)
        print(f"Assembled {len(bin_data)} bytes -> {out_path}")
        return

    if args.json:
        data = args.json.read_bytes()
        func = parse(data)
        out_json = func_to_json(func)
        if args.output:
            args.output.write_text(out_json, encoding="utf-8")
        else:
            print(out_json)
        return

    if args.from_json:
        json_data = args.from_json.read_text(encoding="utf-8")
        func = json_to_func(json_data)
        bin_data = build(func)
        out_path = args.output or args.from_json.with_suffix(".cnut")
        out_path.write_bytes(bin_data)
        print(f"Built {len(bin_data)} bytes -> {out_path}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
