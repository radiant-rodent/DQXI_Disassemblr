# M1_merge_names — completed (resumed)

## What was already there / what was missing

There was **no `tools/merge_names.py`** and nothing had been merged. `symbols.json` still had
477 entries (460 seeded function names), `symbols_recovered.json` had 460, `decomp/ghidra/
functions_merged.jsonl` still had 18,327 `FUN_`/`func_` names, and `decomp/readable/` had been
generated from those pre-merge names. All 128 naming batches did exist:
`orchestration/naming/out/N_001.json` … `N_128.json` (18,327 proposals).

The previous worker's partial state was therefore only the input data. This task created the
merger, validated every proposal, wrote the symbol/catalog files, regenerated the readable tree
and added the shared recovered-type header.

## Validation of the proposals

Command: `python tools/merge_names.py --check`

| Check | Result |
|---|---|
| Proposals | **18,327** from **128** batches |
| Missing / incomplete batches | **none** (every batch file address has a proposal) |
| Unknown addresses | **0** (all exist in `functions_index.json`) |
| Invalid C identifiers | **0** (all 18,327 names are valid identifiers, no reserved words) |
| Duplicate proposal names | **22** (resolved; see clash table) |
| Confidence histogram | `0.1: 12, 0.2: 123, 0.3: 1,943, 0.4: 3,534, 0.5: 7,203, 0.6: 3,292, 0.7: 906, 0.8: 941, 0.9: 373` |
| `maybe_` names | 10,295 (`confidence < 0.5` is 9,887; 8 non-`maybe_` low-confidence `std_*` names were left as written) |
| Signature forms | 18,325 functions, **2 data** (`Ui_Pane_VtablePtr`, `Field_DataWord_6B24F8`), 0 unparsable |
| Signature names normalised | **478** (signature text had a stale `maybe_`/alias; the proposal's `name` now always wins) |
| Parameter names repaired | **13,967** values were prose/placeholder (`self`, `equipment window`, `param_2`, `SARC reader (…)`) and were turned into valid identifiers or `argN` |
| Functions with a param-map count mismatch | 903 (kept the available names; the rest stay `argN`) |
| Address formatting repaired | **150** (N_049 wrote `0x2BB90C`; normalised to `0x002BB90C`) |
| Encoding | N_014 was cp1252 on the first read (byte `0x97`); the loader accepts UTF-8 + cp1252. It was UTF-8 on the final pass; 128/128 batches now read as UTF-8. |

No batch was missing or incomplete, so **no `orchestration/tasks/N_redo_###.md` files were
needed**. N_049's non-canonical address format was data-only and is repaired by the merger.

### The 22 name clashes (higher confidence kept the name)

| Original name | Kept | Suffixed |
|---|---|---|
| `Field_SceneObject_DeleteSprite` | `0x005B0274` (0.55) | `0x005C8728` → `_2` (0.50) |
| `Mem_AllocAligned` | `0x0010F6EC` (0.85) | `0x00109DC8` → `_2` (0.75) |
| `Sound_CommandQueue_Push` | `0x005EAF40` (0.65) | `0x001EB8C8` → `_2` (0.60) |
| `Ui_CreditWindow_Dtor` | `0x00212A24` (0.62) | `0x002880F4` → `_2` (0.50) |
| `Ui_FourRowTextWindow_InitPanes` | `0x004F8C54` (0.72) | `0x00392E20` → `_2` (0.50) |
| `Ui_GaugeWindow_InitPanesB` | `0x004129B0` (0.55) | `0x0032CCC4` → `_2` (0.50) |
| `Ui_Object_DtorTrivialB` | `0x00448560` (0.70) | `0x00417BE8` → `_2` (0.55) |
| `Ui_SakusenWindow_InitPanes` | `0x002A12E0` (0.85) | `0x0046A584` → `_2` (0.65) |
| `Ui_TwoColumnTextWindow_InitPanes` | `0x003FBD40` (0.60) | `0x0036BAF8` → `_2` (0.50) |
| `maybe_BattleScene_LayoutUnitModel` | `0x00603B9C` (0.45) | `0x006068E8` → `_2` (0.45) |
| `maybe_Battle_Effect_UpdateLinkSegment` | `0x002DB2F0` (0.40) | `0x004E1630` → `_2` (0.35) |
| `maybe_Field_ActorAction_DeletingDtor` | `0x00301E44` (0.45) | `0x00413A7C` → `_2` (0.40) |
| `maybe_Ui_EquipmentListWindow_InitPanes` | `0x0041CAB4` (0.45) | `0x003653C0` → `_2` (0.40) |
| `maybe_Ui_ItemInfoWindow_Dtor` | `0x002F6870` (0.45) | `0x002F6B74` → `_2` (0.40) |
| `maybe_Ui_MessageWindow_Dtor` | `0x002E4D08` (0.45) | `0x00318808` → `_2` (0.45) |
| `maybe_Ui_Panel_Dtor` | `0x001CE95C` (0.45) | `0x002C1B9C` → `_2` (0.40) |
| `maybe_Ui_RowList_Dtor` | `0x004478F8` (0.50) | `0x002298F8` → `_2` (0.42) |
| `maybe_Ui_Screen_DtorDelete` | `0x002D2804` (0.45) | `0x00452D54` → `_2` (0.45) |
| `maybe_Ui_Widget_Dtor` | `0x001D71E4` (0.40) | `0x002BD834` → `_2` (0.40) |
| `maybe_Ui_Window_CompareNameWithSlot` | `0x00307AC8` (0.40) | `0x002A6140` → `_2` (0.30) |
| `maybe_Ui_Window_Dtor` | `0x002B7868` (0.45) | `0x00319148` → `_2` (0.42) |
| `maybe_Ui_Window_DtorDelete` | `0x00444B48` (0.50) | `0x002B7858` → `_2` (0.45) |

Ties are broken by lower address. The merger is idempotent: names that came from a previous merge
carry a `batch` field and are ignored when deciding seed-name clashes, so a rerun keeps `_2`, not
`_3`/`_4`.

## Spot-check of 30 random proposals

Seed `2026-10-25`, 30 proposals from 30 different batches. Each was checked against its readable
C body, callees and (where useful) the vtable/literal-pool evidence.

| # | Batch / address | Proposed name | Verdict |
|---|---|---|---|
| 1 | N_109 `0x003E0F3C` | `maybe_Field_ActorAimPoseAction_DtorDelete` | plausible (base dtor 0x193E44 + release) |
| 2 | N_049 `0x002DB940` | `maybe_Actor_UpdateIfModelReady` | plausible (0x66A2BC guard + 0x38AB68) |
| 3 | N_100 `0x0070673C` | `Script_Bind_Actor2DMoveSylviaShip` | correct (binding table, arity 6) |
| 4 | N_029 `0x004BFA20` | `maybe_Field_ActorFocusSequence_Update` | name plausible; signature had a different name → **mechanical defect, fixed** |
| 5 | N_026 `0x0031AF8C` | `maybe_Gfx_SpriteActor_SetModelAndPos` | correct (model table + 0x5F3500/0x5F36E0) |
| 6 | N_087 `0x00257ECC` | `Text_CommandHandler1` | correct (slot 1 of 0x72C5B8; pushes byte 4) |
| 7 | N_093 `0x0056F0A8` | `Gfx_GpuCmd_WriteColorState` | correct (two command descriptors) |
| 8 | N_074 `0x006296BC` | `Battle_IsTargetRestrictedByAbility` | plausible (special ability ids) |
| 9 | N_113 `0x004D3C20` | `Battle_Action_SpecialMove_Sp7Loop_Play` | correct (`sp7_loop`, vtable 0x779930) |
| 10 | N_057 `0x003C9B08` | `maybe_Battle_ActionSequence_UpdateTalkMembers` | plausible (member loop + 0x1FAF48) |
| 11 | N_010 `0x001A1AA4` | `maybe_Ui_MessageWindow_AdvanceStateEx` | plausible; params `a`/`b` were placeholders (renamed `argN`) |
| 12 | N_105 `0x002985C4` | `maybe_Ui_SmithMenu_UpdateAnimation` | correct (vtable 0x75DF7C, 1/30 step) |
| 13 | N_116 `0x00535FA4` | `Fs_Sarc_FindFile` | correct (SFAT hash + binary search + strcmp) |
| 14 | N_053 `0x00361AC4` | `Gfx_SpriteActor_InitFromRecord` | correct (sprite lookup, anim, 0x5E7650 bind) |
| 15 | N_047 `0x0028A4FC` | `maybe_Ui_Window_ReadTimestampBytes` | behaviour matches; **verb is weak** ("apply time to render object" is more accurate) |
| 16 | N_019 `0x00504324` | `maybe_Svc_ReleaseAllSharedState` | plausible (releases 0x209 then 0x207) |
| 17 | N_099 `0x00704E74` | `Script_Bind_ActorAttachGadget` | correct (script binding 0x24EF80, two strings) |
| 18 | N_089 `0x0041FE88` | `Ui_SaveSlotWindow_UpdateSlots` | correct (4 × 0x5C rows, save getters) |
| 19 | N_018 `0x00464EC4` | `maybe_Ui_PartyIconRow_RefreshAlt` | correct (same cell loop as 0x464E8C) |
| 20 | N_007 `0x00564130` | `Gfx_BindResourceSetVariant` | correct (desc kind 2, 0x532DE8) |
| 21 | N_044 `0x002276EC` | `maybe_Actor_CheckInteractionRange` | correct (distance + facing cone + acosf) |
| 22 | N_119 `0x00661BEA` | `maybe_Sound_Seq_ExecuteChannelCommand_Tail` | **not a function** (Ghidra split of the 0x661974 tail); summary says so, name kept as `maybe_` |
| 23 | N_050 `0x002EBF4C` | `Ui_ListData_AppendSpecialPartyRows` | correct (`special_party` table + text ranges) |
| 24 | N_081 `0x0011C880` | `Gfx_CmdBlitTexture` | plausible dispatch stub; name is slightly broader than the 2-instruction body |
| 25 | N_097 `0x0065B310` | `Gfx_Mesh_AllocSubmeshBuffers` | correct (0x158-byte records, 16-byte alignment) |
| 26 | N_118 `0x0062B0F8` | `maybe_Actor_IsHandleAlive` | **semantics questionable** (returns 1 when the owner chain is broken; may be "can release") |
| 27 | N_046 `0x0026DF1C` | `maybe_Ui_TextLayout_FillSlotsByMode` | plausible (layout sources + qsort) |
| 28 | N_075 `0x00635EA0` | `maybe_Field_Actor_GetGridColumn` | correct (returns `f_b0` after the +0x18 lookup) |
| 29 | N_080 `0x00104520` | `Fs_CacheSet_UpdateEntries` | correct (list sort by +0x84, vtable visibility) |
| 30 | N_011 `0x001DC428` | `Message_SetArgTextById` | correct (slot 5 through 0x1F076C) |

**Tally:** 27/30 accepted as supported by the code, 1/30 mechanically inconsistent (signature name,
fixed), 1/30 a documented Ghidra split (not a function), 1/30 an uncertain predicate. That is
~10% max concern and **no batch came close to the >30%-wrong redo threshold**; no batch was
queued for redo. The two remaining semantic concerns are recorded as follow-ups below.

### Corrections requested by the batch workers

The batch reports ask the merge to treat four specific entries differently. Three cannot be
represented without rewriting another worker's proposal JSON, so they are recorded here rather
than silently changed:

- **N_023 `0x0062AB4C`** is currently `maybe_Battle_RefreshUnitStats`, but its body fills a
  0x40-byte billboard-sprite record from the actor world transform (the callers pass
  `&self->f_b0->f_48`), not unit stats. The `maybe_` hedge is right; the name is wrong and is the
  single most misleading name the merge leaves behind.
- **N_034 `0x0051B158`** `std_FastSinCos`: 0x51B630 inside it is the table-interpolating
  sin/cos LUT and 0x51B66C a SWAR popcount, so the "fast" name is imprecise. Left as proposed
  (confidence 0.60).
- **N_037 `0x001336E4`** `maybe_Video_McFilterOffsetTable` is a **data table**, but the proposal
  gave it a `void …(void)` signature, so the merger classified it as a function. It is the one
  remaining proposal that should be reclassified as data (the other two data proposals were
  correct).
- **N_049** flagged seven `maybe_FalseEntry_*` addresses; all seven are typed `label` and their
  readable C was skipped, as requested. N_037's and N_105's other false entries are handled the
  same way (14 labels in total).

## Merge results

### Symbol files

- `symbols.json`: **18,804 entries** (18,327 proposals + 477 pre-existing seed/global symbols),
  unique names, canonical `0x00XXXXXX` addresses. Every proposal entry carries `name`, `type`,
  `mode`, `size`, `signature`, `summary`/`description`, `confidence`, `batch`, `params`, `evidence`
  and `source` (`orchestration/naming/out/N_###.json`). Types: 18,783 functions, 14 labels
  (`maybe_FalseEntry_*`), 2 data (`Ui_Pane_VtablePtr`, `Field_DataWord_6B24F8`), plus the 6
  pre-existing object/table/thunk entries.
- `symbols_recovered.json`: **18,787 entries**, canonical keys, every proposal present.
- `decomp/ghidra/functions_merged.jsonl`: all 18,327 proposal rows renamed and given their
  signature/summary/confidence/batch/params/evidence; 0 `FUN_` names remain. Source file paths were
  deliberately **not** renamed (the Ghidra tree is a stable export; renaming 18k files would churn
  every path and add no readability that the readable tree does not already provide).
- `decomp/ghidra/functions_index.json`: same names/signatures/summaries; `named_functions` now
  **8,492**, `documented_functions` **8,032** (the seed rows without a summary explain the gap).

### Readable C

`decomp/readable/` was fully regenerated (the two trees are cleared first):

- **18,737** files written (18,151 under `functions/`, 586 under `recovered/`); 11 skipped because
  they are 4-byte data / false `maybe_FalseEntry_*` labels / container-only entries.
- Each file now has a doc comment with the final name, one-line summary, batch, confidence,
  address/mode/size, signature and evidence, followed by the named, typed definition and the body.
- Parameter names from `params` are applied to the body; placeholder types are converted
  (`undefined4`→`u32`, etc.); calls resolve through the full 18k name map.
- Noise reduction across the tree:

| Measure | Before | After |
|---|---:|---:|
| temporaries (`iVarN`, `uVarN`, `in_rN`) | 811,481 | 724,947 |
| placeholder types (`undefinedN`, …) | 278,899 | 9,166 |
| `param_N` | 277,880 | 31 (all remaining are inside quoted evidence text, not code) |
| unnamed calls | 152,598 | 59,240 |
| pointer-arithmetic fields (`*(T*)(p+0x..)`) | 107,701 | 24 |
| `DAT_` globals | 50,622 | 10 |

Named percentage against all 18,787 indexed entry points:
**before 460 / 18,787 = 2.45% → after 8,492 / 18,787 = 45.20%**.
The progress page's optimistic metric (which already credited high-confidence proposals before
the merge) is 8,024 non-`maybe_` proposals; it stays 8,024 after the merge, which is expected.
Documented functions (name + summary) are **8,032**.

Three honest qualifications on that 45.20%:

1. **Every** entry point now has a human-readable name (8,492 strict + 10,295 `maybe_`-hedged /
   placeholder-era names), but the strict metric only counts the non-`maybe_` ones.
2. The proposals are not consistent about the `maybe_` convention. Of the 8,492 "named" entries,
   **2,614 sit at confidence exactly 0.50 and 8 below it**, so ~31% of the total is borderline
   and is only counted because those workers did not add the `maybe_` prefix. Conversely,
   **123 `maybe_` names carry confidence above 0.50**. A conservative "named at >0.50" count is
   **5,870 / 18,787 = 31.24%**.
3. The 460 seed names (confidence 1.0) are included in the 8,492; 8,032 proposal-derived names
   come from the merger itself.

### Recovered types in `include/`

- New `include/recovered_types.h`: **992 opaque forward declarations** for struct/class types that
  appear in the parameter lists of at least three independent proposals (threshold ≥3). Each entry
  records the use count and up to three example function names; the header is explicitly opaque
  and does not claim field layouts. Top examples: `UiWindow` (578 uses), `ScriptVm` (285),
  `UiWidget` (238), `Actor` (206), `UiMessageWindow`/`UiObject` (156).
- `include/dqxi.h` got one additive line: `#include "recovered_types.h"`.
- `gcc -fsyntax-only -I include -include include/dqxi.h <empty.c>` passes.

## Files changed

| Path | Change |
|---|---|
| `tools/merge_names.py` | **new** — validation, clash allocation, symbol/catalog writes, readable regeneration, recovered-type header. `--check`, `--no-readable`, `--workers` modes. |
| `symbols.json` | 18,327 proposals merged (18,804 entries) |
| `symbols_recovered.json` | 18,787 address→name entries |
| `decomp/ghidra/functions_merged.jsonl` | 18,327 rows renamed + documented |
| `decomp/ghidra/functions_index.json` | names/signatures/summaries + named/documented counts |
| `decomp/readable/functions/*.c`, `decomp/readable/recovered/*.c` | fully regenerated (18,737 files) |
| `include/recovered_types.h` | new (992 opaque types) |
| `include/dqxi.h` | one include line |
| `orchestration/done/M1_merge_names.md` | this report |
| `AGENT_LOG.md` | one appended entry |

Nothing in `asm/`, `src/`, `..\3DS_Translate`, or the naming proposal files was modified
by the merger. The only unexpected on-disk change observed was N_014's encoding: it was cp1252 at
the first read and UTF-8 on the final pass (the loader supports both; the proposal content is
identical).

## Tests / verification

Run from the project root, after the final merge and readable regeneration:

- `python tools/merge_names.py --check` — 18,327 proposals, 128/128 batches complete, 0 bad
  entries, 0 unknown addresses, 0 missing batches.
- `python tools/build.py` — **PASS**: `code.bin` 7,090,176 bytes, SHA-256
  `dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8`, bit-matches retail
  (0 differences); compressed `.code` SHA-256
  `ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f`, 0 differences.
- `python tests/run_all.py` — **223/223 PASS** (Tier 1 70/70, Tier 2 70/70, Tier 3 14/14,
  Tier 4 69/69; exit 0).
- `python tools/verify_project.py` — **OVERALL PASS** (code hash, assets, 18,787 entry points,
  18,748 decompiled, 1,196 maps, patch report, editor binary, C replacements).
- `python tools/check_clean_c.py` — 23/23 clean C files compile for ARMv6K.
- `gcc -fsyntax-only` on `include/dqxi.h` — passes.

## Open problems / not verified

- The names are **static analysis only**; no emulator or real 3DS playtest was used to confirm any
  function name. Confidence values are carried through so a reader can see which names are guesses.
- ~211 proposals describe interior blocks / Ghidra split fragments rather than true function
  entries (the largest group is N_126's field scene-spawner blocks). They are merged with their
  `maybe_` names and honest summaries; only the 14 `maybe_FalseEntry_*` entries and the 2 data
  proposals are typed `label`/`data`. A future seed cleanup should remove the rest from the
  "function" count rather than pretending they are entry points.
- `maybe_Actor_IsHandleAlive` (N_118 `0x0062B0F8`) may have inverted semantics: it returns 1 when
  the owner chain is broken. It is kept as a `maybe_` name; a caller/usage check is needed before
  relying on the predicate.
- `maybe_Ui_Window_ReadTimestampBytes` (N_047 `0x0028A4FC`) probably wants an "Apply"/"Set" verb;
  the body reads the global clock and applies an 11-byte block to the render object.
- `Gfx_CmdBlitTexture` (N_081 `0x0011C880`) is a 2-instruction dispatch stub, not the command
  builder itself; the name is broader than the body.
- `decomp/ghidra/functions.h` was **not** regenerated: adding the new typed signatures there would
  require definitions for the 992 opaque types and could break `check_ghidra_c.py` for reasons
  unrelated to naming. The readable tree and index are the authoritative human view.
- The Ghidra source filenames remain `FUN_...`; only the index/readable output are named. This is
  intentional (renaming 18k source files would produce a large path churn and break external
  bookmarks).
- `include/recovered_types.h` lists opaque types only. It does not recover field layouts; that is
  the `S0_types_plan` / `M2_types_merge` work.

## Suggested follow-ups

1. `S0_types_plan`: use the 992 recovered parameter types as the seed list for struct/class
   recovery; start with `UiWindow`, `ScriptVm`, `UiWidget`, `Actor`, `FieldSceneObject`.
2. Seed-generator cleanup: reject `mod 4 == 2` ARM seeds, Thumb-prologue false positives and
   literal-pool words (N_124/N_126/N_127/N_128 all report this). That would remove ~200 fake
   "function" entries from the catalog and let `M1` merge only real entry points.
3. Revisit the two spot-check concerns: `maybe_Actor_IsHandleAlive` semantics and
   `maybe_Ui_Window_ReadTimestampBytes` verb.
4. Targeted corrections from the batch reports (above): rename `0x0062AB4C`
   (`maybe_Battle_RefreshUnitStats` → a billboard-sprite-record builder) and reclassify
   `0x001336E4` as data; both are single-entry changes that need the owning proposal updated so
   the next merge keeps them.
5. Consider a small `M1b_vocabulary` pass for repeated helper names that appear in dozens of
   evidence strings (`0x0010F6CC` release, `0x001235A4` list splice, `0x0011CFAC` libgcc udiv,
   `0x0010009C` guard acquire) so the readable C calls them by name.
6. If desired, rename the Ghidra source files to match the index in a separate, mechanical task
   (and update `functions_merged.file`/`functions_index.file`); the merger already produces the
   final names.
