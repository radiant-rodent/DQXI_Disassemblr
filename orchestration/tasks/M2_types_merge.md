---
lane: merge
after: S_*, G_*
---

# M2_types_merge - merge S/G answers into real C headers

Take the class/field answers (`orchestration/types/out/S_*.json`) and global answers
(`G_*.json`) and turn them into the project's recovered C types, then make the readable
view use them.

Owns: `include/dqxi/**`, `orchestration/types/merged/**`,
`orchestration/done/M2_types_merge.md`. `tools/typedb/apply.py` and
`tools/readable_c.py` already implement the merge; fix them only if a real answer
exposes a bug (smallest possible change).

## 1. Validate

```powershell
python tools/typedb/apply.py --validate
```

Read `orchestration/types/report.json` (or `merged/report.json` for a merge run):
every error excludes one class/global; fix the worker answer or record why the
evidence is wrong. Do not weaken `apply.py` to make an answer pass. Typical real
errors: an offset that does not exist in `structs.json` evidence, an unknown C type,
a duplicate field name, a global address that is not a data object (a literal-pool
number), or a V2 name collision.

## 2. Merge

```powershell
python tools/typedb/apply.py --merge
```

Writes:

* `include/dqxi/dqxi_base.h` - width typedefs (`u8`..`f64`) via `include/types.h`;
* `include/dqxi/structs.h` - one C struct per answered class, byte-accurate offsets,
  explicit `_pad_` arrays for unknown gaps, base classes embedded only when their
  size is known and no derived field overlaps them;
* `include/dqxi/globals.h` - `extern` declarations for named data objects;
* `include/dqxi/dqxi_types.h` - umbrella header;
* `orchestration/types/merged/{fields,globals,locals,functions,report}.json` -
  the machine maps read by `tools/readable_c.py`.

Sanity checks (all must pass):

* `sizeof(struct X) == size` for every emitted struct: compile a tiny probe with
  `gcc -m32 -fsyntax-only -I include` (or `arm-none-eabi-gcc` if present) that includes
  `dqxi/dqxi_types.h` and `_Static_assert(sizeof(UiGaugeWindow) == 0x3FC, "");`
  for a sample of structs. **Use `-m32`**: the host compiler is 64-bit, so pointers would
  be 8 bytes and every pointer-bearing struct would fail a size assert that is correct for
  the 3DS. The struct sizes are evidence-backed, so a mismatch is a real emitter bug.
* no field name is a C keyword, no duplicate names, no two fields overlap;
* every `extern` global has a real data address in its comment;
* `python tools/typedb/apply.py --demo` still works and does not write project files
  (it goes to `orchestration/types/merged_demo/`).

## 3. Make the readable C use the types

`tools/readable_c.py` already loads `orchestration/types/merged/` and:

* prints `unit->targetUnit` instead of `f_1b4` when the class and field are merged;
* follows a field's pointed-to class through nested chains
  (`self->targetUnit->hp`);
* replaces a named global's literal slot with the global name;
* keeps `f_XXXX` where the field is still unknown (honest, not a guess).

Regenerate the readable tree (it also re-runs the M1 docs through
`tools/merge_names.py`; do not delete the summaries):

```powershell
python tools/merge_names.py --check
python tools/merge_names.py            # regenerates decomp/readable/ with docs + types
```

Then verify with `python tools/readable_c.py --stats` that the type/global counters
actually moved and no file fails strict UTF-8. Spot-check the classes you merged:

* open the constructor and two methods of a merged class;
* `grep -c "->f_" decomp/readable/functions/<Class>_*` must drop substantially;
* a function that used `g_...` for a named global shows the real name.

## 4. Keep the build green

Naming/types are a view over the retail bytes; they must not change the build.

```powershell
python tools/build.py                  # code.bin/.code bit-match
python tests/run_all.py                # must stay at the current pass count
python tools/verify_project.py         # OVERALL PASS
```

If `tools/build.py` fails, something outside this lane changed the tree - stop and
report it, do not "fix" the check.

## 5. Report

`orchestration/done/M2_types_merge.md`: numbers of S/G answers, merged classes,
fields, globals; errors fixed; before/after sample of one function; readable-noise
counters; test results; honest list of weak names (`confidence < 0.5`) and classes
that are still namespace-only. The progress page reads
`orchestration/types/merged/report.json`, so leave it in place.

Never modify `..\3DS_Translate`, `asm/`, `original/`, or the retail image.
All text/JSON writes are UTF-8.
