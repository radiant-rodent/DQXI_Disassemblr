# Squirrel scripts: format, compiler and tooling

Dragon Quest XI (3DS) drives every map event, cutscene, quest and battle setup from **769 Squirrel
scripts**. This page explains the file format, how the readable source and the assembler are built,
and what the compiler can and cannot do. For the modder workflow see
[EDITING.md](EDITING.md#scripts-events-cutscenes-quests).

## Where the scripts live

```
romfs/script/<area>.pack          a PACK with exactly one member
  script.cnut                     compiled Squirrel ("CNUT") bytecode
game_data/packs/script/<area>/script.cnut      extracted member
game_assets/scripts/packs/script/<area>/
  script.nut                      annotated disassembly (editable, bit-exact tier)
  script.decompiled.nut           readable source (editable, compiled tier)
game_assets/scripts/script_index.json          functions/natives/xrefs for the editor
```

The area name is also the pack name (`a_010`, `a_010_cs_050x`, `b001`, `d021`, ...).
`tools/organize_scripts.py` maps story areas; `tools/script_build.py describe_area` adds names for
the system and cutscene packs that map does not cover.

## CNUT container

All integers are little endian. The parser and writer are `tools/sqbin.py`.

```
FA FA                     magic (not part of the SQ serialisation proper)
"RIQS"                     HEAD
u32 1                      SQChar size (1 = byte strings)
<function>
"LIAT"                     TAIL

<function> =
  "TRAP" <obj sourcename> <obj name> "TRAP"
  u32 n_literals, n_parameters, n_outervalues, n_localvarinfos,
      n_lineinfos, n_defaultparams, n_instructions, n_functions
  "TRAP" <obj>*n_literals
  "TRAP" <obj>*n_parameters
  "TRAP" (u32 type, <obj src>, <obj name>)*n_outervalues
  "TRAP" (<obj name>, u32 slot, u32 start_op, u32 end_op)*n_localvarinfos
  "TRAP" (u32 line, u32 pc)*n_lineinfos
  "TRAP" u32*n_defaultparams
  "TRAP" <instruction>*n_instructions
  "TRAP" <function>*n_functions          (closures, index order)
  u32 stacksize, u8 bgenerator, u8 varparams

<obj>      = u32 type, payload
  type 0x01000001 NULL          no payload
       0x05000002 INTEGER       i32
       0x05000004 FLOAT         f32 bits
       0x01000008 BOOL          u32
       0x08000010 STRING        u32 length + bytes (UTF-8)

<instruction> = i32 arg1, u8 opcode, u8 arg0, u8 arg2, u8 arg3
```

`stacksize` is the highest VM register used, `varparams` marks `function f(...)`, and
`localvarinfos.start_op` is the pc **after** the initializer (the decompiler uses that to fold
`local x = expr` back together).

## Instruction set

The game ships **Squirrel 2.2-style bytecode**: `ARITH` and `CMP` carry an operator byte, `JNZ`
exists, and table construction uses `NEWSLOTA`. The 3.2 sources in the read-only reference
workspace (`_emutest/tools/squirrel_src`) use different opcodes (`ADD`/`SUB`/`MUL`, `JCMP`,
`NEWOBJ`) and a different serializer, so they cannot be used as a drop-in compiler. There is no
compiler for this exact format in `third_party/`; the project ships its own assembler and compiler.

Opcodes used by the corpus (from `audit/SCRIPT_DECOMPILE.md`): `LINE`, `LOAD`, `LOADINT`,
`LOADFLOAT`, `DLOAD`, `CALL`, `PREPCALL`, `PREPCALLK`, `GETK`, `MOVE`, `NEWSLOT`, `SET`, `GET`,
`EQ`, `NE`, `ARITH`, `BITW`, `RETURN`, `LOADNULLS`, `LOADROOTTABLE`, `LOADBOOL`, `DMOVE`, `JMP`,
`JNZ`, `JZ`, `VARGC`, `GETVARGV`, `NEWTABLE`, `NEWARRAY`, `APPENDARRAY`, `COMPARITHL`, `INC`,
`INCL`, `PINC`, `PINCL`, `CMP`, `AND`, `OR`, `NEG`, `NOT`, `CLOSURE`, `DELEGATE`, `NEWSLOTA`.
`TAILCALL` and `COMPARITH` appear a handful of times.

Operand conventions that matter when editing the listing:

| Opcode | arg0 | arg1 | arg2 | arg3 |
|---|---|---|---|---|
| `LOAD` | dst | literal index | | |
| `LOADINT` / `LOADFLOAT` | dst | signed i32 / float bits | | |
| `MOVE` | dst | src | | |
| `LOADNULLS` | first reg | count | | |
| `GETK` / `PREPCALLK` | dst | literal index | object reg | (`PREPCALLK`: `this` reg) |
| `GET` / `PREPCALL` | dst | key reg | object reg | (`PREPCALL`: `this` reg) |
| `CALL` | dst (a real register, never 0xFF) | function reg | `this`/arg area | arg count **including `this`** |
| `ARITH` | dst | rhs reg | lhs reg | ASCII operator (`+`, `-`, `*`, `/`, `%`) |
| `CMP` | dst | rhs reg | lhs reg | 0 `>`, 2 `>=`, 3 `<`, 4 `<=` |
| `EQ` / `NE` | dst | rhs reg or literal | lhs reg | 1 = arg1 is a literal |
| `JZ` / `JNZ` | condition reg | relative offset (`target - pc - 1`) | | |
| `AND` / `OR` | dst | relative offset | value reg | |
| `NEWSLOT` / `SET` | dst or 0xFF | object reg | key reg | value reg |
| `NEWSLOTA` | flags | table reg | key reg | value reg |
| `CLOSURE` | dst | child function index | outer count | |
| `RETURN` | 1 = has value, 0xFF = none | value reg | | |

`this` is always register 0. Unqualified names are looked up on the script table (`this`), so the
decompiler prints both `name` and `this.name` depending on how the compiler happened to emit it;
they mean the same thing.

## The decompiler (`tools/squirrel_decompile.py`)

It rebuilds expressions from register writes and structures control flow into `if`/`else`,
`while`, `for`, `switch`, `break`/`continue`. Coverage today:

- 769/769 scripts, 8,960/8,960 functions fully structured;
- 0 ASM fallback blocks, 0 unresolved `$rN` reads;
- locals named from `localvarinfos`; line numbers from `lineinfos`.

Anything it cannot structure is emitted as a clearly marked `ASM FALLBACK` comment block rather
than wrong code. `--all` rewrites `script.decompiled.nut` and `audit/SCRIPT_DECOMPILE.md`.

## The source compiler (`tools/script_build.py`)

`source_build()` parses the `.nut` text, compiles changed functions, and copies unchanged functions
straight out of the retail script:

1. **Parse** (lexer + recursive descent) into statements/expressions. Comments and whitespace are
   ignored; `line` is kept for jump-to-error and line tables.
2. **Pair functions** with the original script by their unique name (unnamed closures by
   position). Matching by position made one inserted function recompile every later function in
   the pack, which is both slow and unnecessary exposure to compiler gaps.
3. **Reuse**: if a function's AST fingerprint equals the original's, deep-copy the original
   `sqbin.Func` (instructions, literals, line table, local variable info, stack size). This is why
   an untouched file is byte-identical.
4. **Compile** changed functions: expressions write into explicit target registers, statements
   emit jumps that are back-patched, locals live in registers and produce `localvarinfos`,
   `stacksize` is the high-water mark. Expression results are released after each statement so a
   13,000-instruction function stays under the VM's 255-register limit.
5. **Validate** the whole `Func` tree (`validate_nut`) before serializing; see the frame rules
   below. A function that would run a register, literal, prototype or jump outside its tables is
   refused instead of written.
6. **Serialize** the `Func` tree with `sqbin.build`.

### Frame rules the VM enforces silently

The game sizes a call frame as `stackbase + func->stacksize` and does not bounds-check register
operands. An out-of-frame register therefore does not raise a script error: the pack loads and the
scene faults. Two rules are checked on every build (`script_build.validate_nut`):

- every register operand and every call-argument slot is below `stacksize`;
- a `CALL`'s result register is a real register, **not `0xFF`**. Stock Squirrel uses `-1` for a
  discarded call result, but this VM loads the 8-bit operand **unsigned**: `0xFF` is 255, not -1,
  and the closure/native result (and a resumed callee's value) is stored at `stackbase + 255` —
  far outside the frame. A statement-position call to a waiting native (`MessageLoop`,
  `WaitMenu`, ...) makes it worse because the same value is kept for the resume. All 8,960
  retail functions satisfy the rule (**0 of 190,229 `CALL`s use `0xFF`**), and so does the whole
  corpus recompiled from scratch. The compiler sends a discarded result to the lowest free
  temporary below the call frame; a value that is used still lands in the callee register.

The compiler deliberately does not try to clone Squirrel's original register allocation or debug
line table, so a from-scratch compile is **not** byte-identical. It is verified by compiling,
decompiling the result and comparing the program AST. Errors are `BuildError(line, message)` and
are shown as a clickable list in the editor.

### Supported language subset

`local`, `=`, `<-`, compound assignment, `if`/`else`, `while`, `for`, ternary, `&& || !`, `+ - * /
%`, comparisons, bitwise/shift, `++`/`--`, table/array literals, closures and table methods
(`function Name(...)` entries), `delegate`, `vargc`, `vargv[i]`, `this`, `::name`.

Not emitted by the corpus and therefore rejected with an error rather than guessed: `class`,
`yield`, `foreach`, `try`/`catch`/`throw`, `resume`, and outer-variable captures
(`GETOUTER`/`SETOUTER`/`LOADFREEVAR`). `clone`, `typeof`, `delete`, `instanceof`, `in` and `switch`
have code paths but no coverage in the shipped corpus, so treat them as untested.

### Assembly tier

`assembly_build()` uses `sqbin.assemble_nut()`, which reads the listing produced by
`sqbin.disasm()`. This reproduces the retail bytes for all 769 scripts and is the safe path for
timing-sensitive or exotic edits. Its comments are ignored; literals, local slots and the line
table are not.

## Measurement

`python -m tools.script_build verify` writes `audit/SCRIPT_BUILD.md`:

| Metric | Result |
|---|---|
| Assembly identical | 769 / 769 |
| Source parses and compiles | 769 / 769 |
| Unchanged source identical (incremental reuse) | 769 / 769 |
| Source semantic round-trip | 769 / 769 (`audit/SCRIPT_BUILD.md`) |
| From-scratch source byte-identical | 0 / 769 |

## Editor metadata (`script_index.json`)

`python -m tools.script_build index` writes one compact JSON (about 1.1 MB):

- `scripts.<area>`: readable title/category/description, line count, function list
  (`name`, `params`, `line`), native calls used, pack path. 8,191 named functions are listed; the
  anonymous script body of each pack is not, which is why the decompiler's 8,960 count is higher;
- `natives`: the 460 native engine callables registered in `symbols.json`
  (`source: native_engine_table`), each with address + summary; summaries are upgraded from
  `orchestration/naming/out/N_*.json` when an address has been named;
- `xrefs.<function>`: cross-pack callers (count, number of packs defining it, first 20 call sites).
  The editor computes same-pack call sites directly from the open file.

Regenerate the index after adding an area or renaming a script; the panel tells you when it is
missing.

## Known gaps

- No edited script has run on **hardware** yet. The emulator proof suite boots both tiers
  (`script_src`, `script_asm`) and the scene-load edit (`script_load`) in Azahar; see
  [EXPORT.md](./EXPORT.md#8-verified-in-emulator-2026-10-26). Unchanged packs are byte-identical.
- The source compiler cannot emit closure captures, generators or classes.
- From-scratch compiles are semantically verified, not byte-verified.
- The readable names for 53 of the 769 packs (system/field/scene helpers) are still code names.
- `scan_decompiled` uses brace counting, not the full parser, so a `{`/`}` inside a string would
  mis-track the caller name in the index (the decompiled corpus has none).
