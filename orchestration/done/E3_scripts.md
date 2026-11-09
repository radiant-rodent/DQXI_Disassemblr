# E3_scripts — Squirrel scripts editable and recompilable (resumed)

**Status:** complete for the tooling, the two build tiers and the editor panel; all automated checks
are green. **Not verified:** no edited script has been booted in the game or an emulator, and the
readable-source compiler is semantically (not byte-) equal to retail when a function is recompiled
from scratch.

## What existed when this session started

- `tools/sqbin.py`: exact CNUT parse/build, `disasm()`, and `assemble_nut()` (never measured
  corpus-wide by this lane).
- `tools/squirrel_decompile.py`: 769/769 decompiled, 8,960/8,960 functions structured, 0 fallbacks.
- `tools/disasm_scripts.py`, `tools/organize_scripts.py`.
- `viewer_rs/src/ui/panels/scripts.rs`: a **read-only** browser. Its `Script.area` was the first
  path component, so every one of the 769 packs was labelled `packs`; the list was effectively
  broken. There was no `tools/script_build.py`, no `data/scripts.rs` metadata, no native-call list,
  no cross-references, no compile/save action, no `orchestration/done/E3_scripts.md` and no E3
  `AGENT_LOG.md` entry.

## 1. Is there a compiler for this exact Squirrel version?

**No.** `third_party/` contains only `SPICA` (a model tool). The read-only reference workspace has
the **Squirrel 3.2** sources under
`..\3DS_Translate\_emutest\tools\squirrel_src`, but they cannot produce this game's
format: DQXI uses the **2.2-style bytecode** (`ARITH`/`CMP` with an operator byte, `JNZ`,
`NEWSLOTA`, `PREPCALLK`) and a `CNUT` container (`FA FA`, `RIQS`/`TRAP`/`LIAT`), while Squirrel 3.2
emits `ADD`/`SUB`/`MUL`/`JCMP`/`NEWOBJ` and a different serializer. There is also no build of it on
the machine. So the project needed its own assembler + compiler; `sqbin` already had the assembler,
this task added the source compiler and made both reachable from the editor.

## 2. Measured round-trip of all 769 scripts

`python tools/script_build.py verify` (writes `audit/SCRIPT_BUILD.md`, 115 s):

| Metric | Result |
|---|---|
| Annotated **assembly listing** rebuilds identical bytes | **769 / 769** |
| Readable `.nut` source parses and compiles to a valid CNUT | **769 / 769** |
| **Unchanged** source rebuilds identical bytes (incremental reuse) | **769 / 769** |
| Compiled source decompiles back to the same program (AST, `this.x` normalised to `x`) | **769 / 769** |
| From-scratch source compile is byte-identical to retail | **0 / 769** |

Interpretation, stated plainly:

- **Readable source recompiles to *identical bytecode* only when the function is unchanged.** The
  build copies unchanged functions straight out of the retail script, so saving a script you only
  read is bit-identical (and the staged PACK is byte-identical too, checked once).
- **A from-scratch recompile is not byte-identical.** Squirrel's original register allocation,
  instruction fusion (`DLOAD`/`DMOVE`) and debug line table are not recoverable from the bytecode.
  The compiled result is verified by decompiling it and comparing the program AST; that is
  769/769. Where byte-exact output matters, the assembly tier is the answer and is 769/769 exact.
- This is the honest ceiling for a decompiler-based source path; anyone claiming byte-exact
  Squirrel source recompilation would need the original compiler binary *and* the original source
  line breaks.

## 3. Two editing levels, both building back to CNUT

`tools/script_build.py`:

```powershell
python tools/script_build.py compile SRC --area a_010 [-o build/x.cnut] [--tier source|asm|auto]
python tools/script_build.py pack    SRC --area a_010 [--mod mod] [--json]
python tools/script_build.py index
python tools/script_build.py verify
```

- **source tier** (`script.decompiled.nut`): lexer + recursive-descent parser for the decompiler's
  subset, AST fingerprinting for reuse, a register-based code generator (jumps back-patched,
  `localvarinfos` and line infos emitted, 255-register guard), then `sqbin.build`.
- **asm tier** (`script.nut`): `sqbin.assemble_nut` + parse/build verification before writing
  anything.
- `pack` compiles, writes `build/script_edits/<area>/script.cnut`, then rebuilds the containing
  `script/<area>.pack` into `mod/romfs/...` via the project's existing
  `export_mod.stage_member` (LayeredFS path used by tables/text).
- `--json` returns a machine-readable result for the editor; errors are `line N: …` strings.
- Auto tier detects a listing by its `[   0] OPCODE` lines.

Language subset is documented in `docs/SCRIPTS.md`: `local`, assignment/`<-`/compound,
`if`/`else`, `while`, `for`, ternary, `&& || !`, arithmetic/comparison/bitwise, `++`/`--`, table and
array literals, closures/table methods, `delegate`, `vargc`/`vargv`, `this`, `::name`. Outer-value
captures, generators, classes, `try`/`throw`, `foreach` are rejected with a line number.
`switch`/`clone`/`typeof`/`delete`/`instanceof`/`in` have code paths but no corpus coverage.

## 4. Editor panel (DQXI Studio → Scripts)

`viewer_rs/src/ui/panels/scripts.rs` (rewritten) and `viewer_rs/src/data/scripts.rs`:

- **Fixed the tree**: `Script.area` is now the PACK name (`a_010`, `a_010_cs_050x`, `b001`, …).
  The tree groups by category from the generated index (Scenarios 15, Cutscenes 600, Boss battles 15,
  Dungeons 25, Fields 37, Overworld fields 7, Battles 35, System 10, General 25) and shows the
  human title (`Cobblestone_Prologue_Departure`) with the raw id in the header/tooltip. Search
  matches area, title, category and description.
- **Two editable views** with a Squirrel source / Assembly listing toggle; each keeps its own
  buffer, so switching does not discard edits. Dirty marker, Revert, Find, Copy path.
- **Syntax-highlighted multiline editor** using the shared `Lang::Nut` colourer, with adjacent
  colour runs merged (a 3,361-line script would otherwise create tens of thousands of sections).
- **Compile (Ctrl+B)** and **Save to mod (Ctrl+S)** run the Python tool on a worker thread; the
  footer shows `compiled N bytes: X functions reused, Y recompiled` or
  `staged /script/<area>.pack:script.cnut -> …`.
- **Error list**: clickable `line N: …` rows jump the caret to the reported line (verified by
  launching with a deliberately broken source: footer showed `compile failed` +
  `line 61: expected '}' before end of file`).
- **Functions tab**: every event/function in the pack with parameters; click jumps.
- **Natives tab**: native engine calls used by the script, with the real registered name, address
  and summary, and a detail box. 460 native names come from `symbols.json`
  (`source: native_engine_table`); 260 summaries were upgraded from
  `orchestration/naming/out/N_*.json` by address, the rest still read “Native gameplay engine
  function” (no worker has named those thunks).
- **Callers tab**: same-pack call sites computed from the open source (function-aware brace
  tracking) plus cross-pack samples and totals from the index (209 called script functions;
  `StartEvent` alone has 1,496 call sites in 768 packs). Clicking a local call site jumps.
- `game_assets/scripts/script_index.json` (generated, ~1.1 MB) carries categories/titles, function
  lists, native use and xrefs. The panel tells the user to run `script_build.py index` when it is
  absent.

Live checks (release build started with `DQXI_START_SECTION=scripts`,
`DQXI_START_QUERY=a_000`): tree/header/editor/native function list render correctly; Ctrl+B
compiled the untouched script (`5337 bytes: 12 reused, 0 recompiled`); Ctrl+S staged
`mod/romfs/script/a_000.pack` (5,416 bytes, byte-identical to retail), then the staged file was
removed to keep the workspace clean; the broken-input error list was screenshotted. The staged PACK
was verified to contain the compiled `script.cnut` and to be byte-identical to the retail PACK when
nothing changed.

## 5. Files

**New**
- `tools/script_build.py` — source compiler + build/pack/index/verify CLI.
- `tests/test_script_build.py` — 11 tests (both tiers, unchanged identity, literal edit, added
  statement, semantic round-trip, pack staging, error line, index scanner).
- `docs/SCRIPTS.md` — CNUT format, opcode conventions, compiler architecture, subset, limits.
- `game_assets/scripts/script_index.json` — generated editor metadata (1.1 MB).
- `audit/SCRIPT_BUILD.md` — generated whole-corpus measurement.
- `orchestration/done/E3_scripts.md` — this report.

**Modified**
- `viewer_rs/src/ui/panels/scripts.rs` — rewritten read-only browser → editor + tabs + jobs.
- `viewer_rs/src/data/scripts.rs` — fixed area names, groups, index metadata, `local_callers`,
  native/xref accessors, search by title; 4 new tests.
- `tools/squirrel_decompile.py` — header/doc wording now says the source is editable and names the
  rebuild command (no code change).
- `docs/EDITING.md` — script row in the inventory, new “Scripts” section, corrected “not possible
  yet” bullet, test command.
- `docs/README.md` — link to `docs/SCRIPTS.md`.
- `README.md` — three factual corrections about script editing.
- `game_assets/scripts/**/script.decompiled.nut` — regenerated with the editable header (769 files,
  content otherwise identical).
- `audit/SCRIPT_DECOMPILE.md` / `.json` — regenerated.
- `AGENT_LOG.md` — Entry 96.

## 6. Test results (all run in this session)

| Command | Result |
|---|---|
| `python tools/script_build.py verify` | **769/769** assembly exact, **769/769** source compiles, **769/769** unchanged exact, **769/769** semantic, 0/769 from-scratch exact, 115 s |
| `python -m unittest tests.test_script_build -v` | **11/11 OK** |
| `python -m unittest tests.test_squirrel_decompile -v` | **11/11 OK** |
| `python tests/run_all.py` | **216/216 PASS** (Tiers 1–4), 114 s |
| `cd viewer_rs; cargo test` | **59 passed, 1 ignored, 0 failed** |
| `cargo build --release` | **OK** (pre-existing warnings only) |
| `python tools/verify.py` | **PASS** — manifest 16/16, repacked ROM bit-identical (`0f04b51b…a37a9b74`) |
| `python tools/verify_project.py` | **OVERALL: PASS** (incl. assets scripts 769/769 and release editor binary) |
| live app | Scripts section: tree, source view, tabs, compile, save, error list exercised (see §4) |

## 7. Open problems / not verified

- **No game boot.** Nothing was run in an emulator or on a 3DS. The PACK/RomFS layer is the proven
  one used by tables/text and an unchanged staged PACK is byte-identical, but an edited script has
  not executed.
- **Source tier is semantically verified, not byte-verified.** From-scratch compiles differ in
  register allocation and line table (0/769 identical). Use the assembly tier for byte-exact
  changes.
- **No original compiler.** The exact Squirrel version/vendor patch is not on disk; the compiler is
  a reimplementation of the language subset the decompiler emits.
- **Untested language paths**: `switch` (no script has one), `clone`, `typeof`, `delete`,
  `instanceof`, `in`, and array literals beyond the single `NEWARRAY` in the corpus.
- **UI click-through** was automated (Ctrl+B/Ctrl+S, deliberate syntax error) rather than done by
  hand; jump-to-line and cross-pack xref navigation were not visually confirmed end-to-end.
- **Native summaries**: 200 of 460 are still the generic “Native gameplay engine function” because
  no naming batch covered those thunks; 53 packs still have code-name titles.
- **Index scanner** uses brace counting, not the full parser; a `{`/`}` inside a string would
  mis-attribute a caller (none in the decompiled corpus).
- **Performance**: a 3,361-line script re-lays out the whole `TextEdit` each frame; it was not
  profiled on the slowest machine. Editing is fine on the test machine.
- **No new script content** was authored beyond test edits (one literal, one added `SQCommand`
  call, one assembly immediate), so authoring a whole new cutscene is unproven.
- The tree uses `organize_scripts.py`'s area dictionary, which is a hand-made map; some story
  associations may be wrong even when the title is readable.

## 8. Suggested follow-up tasks

1. **X2_playtest / hardware check**: boot one edited script (a changed flag or `StartEvent` id) via
   Luma LayeredFS on Azahar and on a 2DS, and record the result here.
2. **Opcode coverage tests**: synthesise Squirrel snippets that use `switch`, array literals,
   `typeof`, `clone`, `delete`, `in`; compile them, decompile them and add them to
   `tests/test_script_build.py` (or mark them unsupported explicitly).
3. **Improve exactness**: study `Squirrel 2.2`'s `sqcompiler.cpp` register allocator and reproduce
   its target stack rules; even partial matching would reduce diffs and make edited scripts easier
   to diff against retail.
4. **Native naming**: name the 200 generic thunks in `symbols.json` (they are already in the
   `native_engine_table` band) so the Natives tab has real summaries.
5. **Closure captures**: decode `LOADFREEVAR`/outer values if any future script uses them (none in
   the retail corpus).
6. **Script-aware global search**: clicking a function name in the global search should open the
   Scripts section at that function (the panel can already accept `area#function`).
7. **Source formatting**: add a canonical pretty-printer so recompiled source diffs stay small and
   `local`/`if` formatting is stable across edits.
8. **Index freshness**: have the viewer detect a stale `script_index.json` (mtime vs the script
   files) and offer a regenerate button instead of a passive message.

## 9. Decisions recorded

- Treated the absence of an exact Squirrel compiler as final after checking `third_party/`, the
  reference workspace, and the opcode/serialization mismatch; did not download anything.
- Chose incremental AST reuse as the definition of “round-trips to identical bytecode” for the
  readable tier, because the alternative (clone the original compiler) is impossible from the
  bytes. The number is reported both ways (769/769 unchanged, 0/769 from scratch) so the claim is
  not inflated.
- Kept the assembly listing as the default fallback for byte-exact work instead of hiding it behind
  the source tier.
- Used the existing `export_mod.stage_member`/`mod/romfs` path rather than inventing a new export
  route.
- Fixed `Script.area` (a visible bug) rather than working around it in the panel.
