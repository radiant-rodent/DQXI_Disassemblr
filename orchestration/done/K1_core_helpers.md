# K1_core_helpers — Bottom-up Disassembly Refinement of the Top 120 Most-Called Unnamed Helpers

**Task:** From `orchestration/naming/refine/scores.jsonl`, select the top 120 functions whose current name is `maybe_*` or `func_*` sorted by `callers_conf` (named confident callers) descending, skipping addresses already covered by `orchestration/naming/refine/out/R_S01.json`. Decode the actual ARM/Thumb/VFP disassembly (`asm/` / `code.bin`) and inspect 3–5+ named callers per helper, write `orchestration/naming/refine/out/R_K01.json`, append reusable verified facts to `orchestration/naming/FACTS.md`, merge names across the project (`python tools/merge_names.py`), and verify the bit-matching rebuild (`python tools/build.py`), `python tools/verify_project.py`, and `python tests/run_all.py`.

**Result:** **120 / 120** top-leverage helpers refined in `orchestration/naming/refine/out/R_K01.json`:
- **97 `corrected`**
- **8 `confirmed`**
- **15 `kept_maybe`**
- **79** promoted to confident names (`confidence >= 0.50`, range `0.55–0.92`) and **41** intentionally retained with `maybe_*` (`confidence < 0.50`, range `0.40–0.48`) where one descriptor or subtype remains unproven.
- Across these 120 helpers alone, the refinement covers **744 `callers_conf`** in `scores.jsonl` (**1,051 live confident callers**, **1,461 distinct caller functions**, and **1,929 direct call sites** in `code.bin`).

---

## 1. Verdict Breakdown & Methodology

| Metric | Value |
|---|---|
| Total helpers refined (`R_K01.json`) | **120** (`R_S01.json` overlap: `0`) |
| `corrected` | **97** (71 promoted to `>= 0.50`, 26 corrected while keeping `maybe_*` `< 0.50`) |
| `confirmed` | **8** (all 8 promoted from `maybe_*` to `0.55–0.62`) |
| `kept_maybe` | **15** (names retained at `0.40–0.45` with decoded assembly evidence) |
| High-confidence names (`>= 0.50`) | **79** |
| Low-confidence `maybe_*` (`< 0.50`) | **41** |
| Total direct reach in `code.bin` | **1,929 call sites** across **1,461 caller functions** (**1,051 confident-named callers**) |

For every one of the 120 targets:
1. Decoded the raw ARM/Thumb/VFP instructions directly from `code.bin` / `asm/` across the true function span (catching mid-function bogus symbols, `blx` to Thumb CRT helpers mis-marked `noreturn` by Ghidra, dropped VFP `s0..s15` arguments/`s0` float returns, forwarded `r1..r3` registers omitted from outer C prototypes, and fake `push {r3, ..., lr}` alignment parameters).
2. Disassembled and read 3–8 named caller call sites (both ARM call-site register setup/return usage and `decomp/readable/` context) plus key inner callees before choosing a name.
3. Recorded the exact decoded assembly behavior, register/offset math, and caller usage in `evidence`.

---

## 2. Top 10 Most Important Corrections (with Caller Counts)

Caller counts list both `scores.jsonl` `callers_conf` (pre-merge snapshot) and exact `code.bin` direct-call reach (`live confident callers / total caller functions / direct call sites`).

| # | Address | Old Name → New Name (Conf) | Callers (`scores_cc` / `live_conf` / `funcs` / `sites`) | Why Old Name Was Wrong & Decoded Disassembly Evidence |
|---|---|---|---|---|
| 1 | `0x00627308` | `maybe_Ui_Object_InitHeader` (`0.45`) → **`Engine_ResourceNode_CtorBase`** (`0.58`) | **40** / **79** / **129** / **155** | Previously poisoned 129 Field, Dialog, NPC cursor, Map, and UI constructors (`Field_SetMapSection`, `SetNPCTargetCursor`, `MessageRegistActor`, `DBOpenDialog`) as `"Ui_Object"`. Ghidra halted at `blx std_ConstructArray` (`0x100050`); full ARM `0x627308..0x6273E8` installs base vtable `0x00780384`, links `(*Engine_GetMemoryManager())+0x354` at `self+4`, constructs the 8-slot (`+0x18`) and 6-slot (`+0x58`) handle arrays, sets `u16_94 = 0xFFFF`, and returns `self`. |
| 2 | `0x0029E41C` | `maybe_Gfx_GetSharedCoreNode` (`0.32`) → **`Gfx_LookupSpritePriorityByte`** (`0.60`) | **45** / **54** / **76** / **81** | Rank #1 in `scores.jsonl`. Ghidra truncated mid-function at bogus Thumb symbol `0x29E44A`, making it look like a pointer getter. Full ARM `0x29E41C..0x29E484` reads `col = u8[r0+0x28]`, `row = s8[r0+0x29]`, `mode = u8[r0+0x2A]`, queries `0x006651D4((*Gfx_GetContext())+0xF50, row, col)`, adjusts for `mode == 1` (`val - 6`) or `mode == 2` (`col = 0x0A`), and returns `u8` in `r0`, which all 76 callers `strb` into `sprite->f_B8->f_128`. |
| 3 | `0x0010AF00` | `maybe_Gfx_GetRenderContextB` (`0.45`) → **`Engine_GetMemoryManager`** (`0.68`) | **16** / **33** / **45** / **106** | Called at **106 sites** across 45 functions. `ldr r0, =0x007BE2F0; ldr r0, [r0]; bx lr` returns the engine `MemoryManager` singleton (`*0x007BE2F0`, initialized at `0x00237BE0`, owning heap allocators, free-lists, and the `+0x354` tracked resource node list), not a graphics render context. |
| 4 | `0x001BDD50` | `maybe_Script_Compiler_PushStackOp` (`0.35`) → **`Script_FuncState_AddInstruction`** (`0.90`) | **9** / **13** / **14** / **94** | Called at **94 sites** across the Squirrel bytecode compiler. Exact match to Squirrel 3.x `SQFuncState::AddInstruction(SQOpcode op, SQInteger arg0..arg3)` (`self+0x5C` `_instructions`, peephole coalescing for `_OP_LOAD`/`_OP_JZ`/`_OP_SETOUTER`/`_OP_GET`). Paired with `0x001BD318` `Script_FuncState_CreateString` (`0.92`, 13 sites) and `0x001BD1A4` `Script_SqFuncState_AddLineInfos` (`0.90`, 3 sites). |
| 5 | `0x002E7F08` | `maybe_Gfx_Scene_DrawSpriteVariant` (`0.45`) → **`Field_Collision_RaycastScene`** (`0.65`) | **12** / **18** / **28** / **33** | Not sprite drawing at all: fetches `Field_ObjectManager` (`(work+8)->f_54`), accesses collision world `+0x14`, and runs a 3D raycast (`rayStart`, `rayEnd`, `hitResultOut`, `filterMask`) used by 28 camera, NPC grounding, jump, and gimmick line-of-sight callers. |
| 6 | `0x0030B5F4` | `maybe_Ui_List_BuildRows` (`0.45`) → **`Effect_Instance_ReleaseResources`** (`0.65`) | **6** / **15** / **23** / **32** | Mislabeled `"Ui_List_BuildRows"` despite being called in 23 battle/field/cutscene destructors (`Effect_LinkInstance_Dtor`, action sequences, gimmick teardowns). Releases live particle/VFX handles at `self+0x08/+0x0C` through FX manager singleton `*0x007BE388` and resets handle slots. |
| 7 | `0x001905E4` *(+ `0x0066C470`)* | `maybe_Text_UpdateCellState` (`0.40`) → **`Party_Member_EquipInventorySlot`** (`0.68`) | **10** / **9** / **13** / **21** *(+16 funcs on `0x66C470`)* | Classic `Item_LookupRecord` `"Text_*"` poison fix: takes `(PartyMember* member, int equipSlot, int invSlot)`, validates `invSlot < 24` (`member+0xEC`), resolves 2H (`u8_29` in `5..9`) vs offhand/shield conflicts across `member+0x11C..+0x121`, and writes the equipped slot index. Likewise `0x0066C470` (`maybe_Text_MeasureNameRef` → **`Item_RollStatBoostDelta`**, `0.62`, 16 callers) rolls seed/consumable stat gain `ItemRecord->u16_12 + rand(0..u8_14)`. |
| 8 | `0x0026DF1C` *(+ `0x00271938`)* | `maybe_Ui_TextLayout_FillSlotsByMode` (`0.45`) → **`BattleAi_SelectBestAttackAction`** (`0.72`) | **4** / **7** / **7** / **8** *(+20 sites on `0x271938`)* | Uncovered the largest poisoned module in the binary (`0x00269F64..0x00277700`, 60+ functions named `Ui_TextLayout_*` by `N_046` after an earlier `N_024` helper misread). Evaluates up to `0x7C` (`40 spells + 60 skills + 24 items`) `0x14`-byte AI candidates across 16 `0x9BC`-byte target-unit buckets, checking `SpellRecord->u8_293 == 1` / `SkillRecord->u8_DC == 1` and returning action kind `2`=attack, `4`=skill, `5`=spell, `6`=item. |
| 9 | `0x0016815C` *(+ `0x003CABEC`)* | `maybe_Ui_GetScaledValue` (`0.40`) → **`Battle_CalcTurnOrderPriority`** (`0.72`) | **3** / **10** / **14** / **16** *(+7 funcs on `0x3CABEC`)* | Un-poisoned the `0x00485D90..0x00497900` battle combat/agility/MP-cost math range (previously misnamed `Text_MeasureTextRun` / `Battle_Message_*`). `0x0016815C` queries unit Agility in VFP `s0` (`0x0048F08C`), rolls `0.51f + rand01(&battleWork->rng_4218) * 0.49f`, and returns `(int)(agility * factor)` for turn-order sorting (`10000`/`9999` overrides for round-first statuses). `0x003CABEC` (`Battle_ActionSequence_ConsumeSpellMp`, `0.72`) resolves spell MP cost (`0x00487870`) and free-MP equipment procs (`0x00485D90`). |
| 10 | `0x005047E0` *(+ `0x001D033C`, `0x006572F8`)* | `maybe_Svc_Object_Write` (`0.45`) → **`Fs_ArchiveStream_ReadAt`** (`0.78`) | **3** / **3** / **3** / **8** *(+6 sites `0x1D033C`, +8 sites `0x6572F8`)* | Fixed three inverted SDK/GPU ground-truth primitives: `0x005047E0` **reads** archive bytes *into* `dstBuf` (`[sp+0x18]`) at `s64 offset` (`r2:r3`) via `__aeabi_memcpy` or `IReadStream::TryRead` for `Fs_Archive_FindDirectory`/`FindFile` (was `Write`); `0x001D033C` (**`Fs_ReportFatalError`**, `0.72`) builds a `0xF80`-byte CTR SDK `nn::err` `FatalErrInfo` and calls `err:f` `Throw` (exposing `0x0051BA34..0x0051CD40` as `nn::err`, NOT `Sound_Driver_*`); `0x006572F8` (**`Gfx_Pica_WriteVertexAttrCommands`**, `0.82`) writes PICA200 `0x0200..0x02BC` Vertex Attribute registers (was `WriteLightingCommands`). |

*(Other notable high-leverage fixes among the 97 corrections: `0x005387EC` `maybe_Ui_AnimClip_CtorFromData` → `Ui_LayoutPane_InitFromRes` (`0.85`, `nw::lyt::Pane` BFLYT `pan1` ctor), `0x0053E9A4` `maybe_Gfx_Sprite_ResetAnimator` → `Ui_PicturePane_SetTexCoords` (`0.78`, 13 sites), `0x00111CD8` `maybe_Os_SetSyncState` → `Os_LightEvent_Init` (`0.92`, 20 sites), `0x005761D8` `maybe_Os_CriticalSectionObject_Dtor` → `Os_ThreadObject_Dtor` (`0.78`, `svc 0x24` `Join` + `svc 0x23` `svcCloseHandle`), `0x00611DE4` `maybe_Ui_DataPanel_SortRowsAt2b8ByItemKey` → `ItemBag_SortEntriesBySortKey` (`0.75` on `work+0x24ACC`), `0x0040B7A8` `maybe_Ui_LabelSlots_SubmitRotatedText` → `Model_Equip_AttachItemSlot` (`0.72`), and `0x00166308` `maybe_Ui_SceneObjArray_Ctor` → `Altar_CollectPastPlaceEntries` (`0.68`, Tickington 33-pastword collector).)*

---

## 3. Reusable Facts Added to `orchestration/naming/FACTS.md`

Appended 28 lines of concise, disassembly-verified facts (each with 1-line address/instruction evidence) across four sections of `orchestration/naming/FACTS.md` while keeping all existing 41 lines intact:

1. **Ghidra traps (4 new rules)**:
   - Hard-float VFP `s0..s15` args and `s0` float returns dropped or shown as `in_s0` (`0x00607650`, `0x001FA974`, `0x0062EF8C`, `0x0032A288`).
   - `push {r3, ..., lr}` 8-byte stack-alignment prologues inventing fake trailing params (`0x0062943C`, `0x002188F8`, `0x00640BBC`, `0x00646060`).
   - Untouched forwarded `r1..r3` registers omitted from outer signatures (`0x002E5C38`, `0x003D5648`, `0x0053E9A4`).
   - Thumb `blx` to CRT helpers (`0x00100050` `std_ConstructArray`, `0x00100B74` `wcslen`) mis-marked `noreturn` and mid-function split symbols (`0x003C3594`, `0x001664AC`) causing fake truncation or `halt_baddata()`.
2. **Poisoned address ranges (5 verified un-poisoning warnings)**:
   - `0x00269F64..0x00277700` = **`BattleAi_*`** Party Tactics / AI Action & Target Evaluator (NOT `Ui_TextLayout_*`).
   - `0x00485D90..0x00497900` = **Battle Combat, Agility & MP-Cost Math** (NOT `Text_MeasureTextRun` / `Battle_Message_*`).
   - `0x0040A980..0x0040BA78` = **`Model_Equip_*` 3D item bone attachment** (NOT `Ui_LabelSlots_*`).
   - `0x0051BA34..0x0051CD40` = **CTR SDK `nn::err` (`err:f` `FatalErrInfo`, `0xF80` bytes)** (NOT `Sound_Driver_*`).
   - `0x005047E0` = **`Fs_ArchiveStream_ReadAt`** (reads into `dstBuf`, NOT writes).
3. **Data tables, `ItemBag` & `PartyMember` layouts (8 table/struct facts)**:
   - `SpellRecord` (`0x0063CFC8`, `< 0xCA`, stride `0x308`, `+0x208/+0x290/+0x293/+0x2EC`).
   - `SkillRecord` (`0x0063D018`, `< 0xBF`, stride `0x100`, `+0xDC/+0xEE`).
   - `CharacterRecord` (`0x0063EB94`, stride `0x434`, costume sub-records & `u8 +0x430`).
   - `ItemRecord` extra fields (`+0x0C` whip/falcon/boomerang subtypes, `+0x12/+0x14` stat boost base/variance, `+0x29` 1H `0..4` / 2H `5..9` / claws `6`, sort key `0x0063D96C`).
   - `ItemBag` at `work + 0x24ACC` (`+0x2B8..+0x274C`, up to 2,341 4-byte `{u16 itemId, u8 count, u8 flags}` entries).
   - Field trigger records (`id < 0x306`, `0x0063DCE8`, save bitmask `(work+0x24A98)+0x5418` via `0x0066B3B0`/`0x006125F0`).
   - Tickington / PastPlace Altars (`0x00166308`, 33 rows `idx < 0x21` via `0x0063DDCC`, quest state `+0x5A4E`, visited bits `+0x88E4`).
   - `PartyMember` (`0x12EC` bytes x 31 at `work + 0x04`: `+0x14` HP, `+0xC8` charaId, `+0xCA` name, `+0xE5` costume, `+0x11C..+0x121` equipped slots, `+0x19E` active states, `+0xB78/+0xF38` free-MP %, `+0xDEF/+0xDF0` hand battle attrs, `+0x1274` 40 spells, `+0x129C` 60 skills).
4. **Battle, singletons, CTR SDK SVCs, PICA200, `nw::lyt` & Squirrel (5 engine/SDK facts)**:
   - Battle work `(work+8)->f_5C` (`u8 +0x4244` 3D/2D mode, `+0x4330/+0x47A0` model tables, `0x0016815C` turn priority, `0x00639954` status test).
   - Singletons `*0x007BE2F0` (`MemoryManager`), `*0x007BE300->f_08`, `*0x007BE308` (`0xE3C8` save/party container), `*0x007BE320` (`GameWork`), `*0x007BE388` (FX manager), `(work+8)->f_54` (`Field_ObjectManager`), `->f_74` (camera), `->f_88` (`Field2D`).
   - Horizon SVCs `0x23` (`svcCloseHandle`), `0x24` (`svcWaitSynchronization1`), `0x28` (`svcGetSystemTick`).
   - PICA200 `0x0200..0x02BC` Vertex Attribute registers (`0x006572F8`).
   - `nw::lyt::Pane` (`+0x2C`, `+0x80`, `+0x99`), `nw::lyt::Picture` (`+0xB8` UV quads), and Squirrel `SQFuncState` (`+0x64`, `+0x9C`, `+0xD0`).

---

## 4. Files Changed

- **Owned task outputs**:
  - `orchestration/naming/refine/out/R_K01.json` — created (120 validated refinement entries, UTF-8).
  - `orchestration/naming/FACTS.md` — appended 28 verified lines under `## Ghidra traps` and three new headings (`## Poisoned address ranges`, `## Data tables, ItemBag & PartyMember details`, `## Battle, singletons, CTR SDK, nw::lyt & Squirrel`).
  - `orchestration/done/K1_core_helpers.md` — created (this report).
  - `AGENT_LOG.md` — appended Entry 234 (`K1_core_helpers`).
- **Standard generated outputs from `python tools/merge_names.py`, `python tools/build.py`, and `python tools/verify_project.py`**:
  - `build/symbols.json` (18,804 entries), `build/symbols_recovered.json` (18,787 entries), `src/include/recovered_types.h`, `decomp/readable/` (18,736 readable C files regenerated), `build/code.bin`, `build/code.compressed.bin`, `audit/PROJECT_VERIFICATION.json`.
- **Scratch directory only (Rule 12b)**:
  - `out/scratch/K1/` — disassembly/caller dump scripts, `entries_01_60.py`, `entries_61_120.py`, `build_rk01.py`, `check_rk01.py`, `summarize_rk01.py`.
- Nothing outside `.` was created, modified, or deleted; `..\3DS_Translate` was strictly untouched.

---

## 5. Verification & Test Results

1. **Custom `R_K01.json` validator (`python out/scratch/K1/check_rk01.py`, mirroring `tools/check_refine.py` + `R_S01.json` non-overlap + strict UTF-8)**:
   - `Checked 120 entries: 0 hard errors, 0 heuristic notices` (all 120 valid C identifiers, `maybe_` iff `confidence < 0.50`, `confirmed` matches `previous_name` minus `maybe_`, 0 symbol collisions against `build/symbols.json` and all `N_*`/`R_*` batches, non-empty `summary` & decoded-disassembly `evidence`, strict UTF-8).
2. **`python tools/merge_names.py --check` & `python tools/merge_names.py`**:
   - `proposals: 18,327 from 194 batch(es)`, `encodings: {'utf-8': 194}`
   - **`bad proposal entries: 0`**, **`unknown addresses: 0`**, **`signature kinds: function=18324, data=3, broken=0`**
   - `refined (R_*) entries: 8,608 {'confirmed': 2861, 'kept_maybe': 4084, 'corrected': 1663}`
   - `named before: 8,492 / 18,787 = 45.20%` → **`named after: 11,774 / 18,787 = 62.67%`** (`high-confidence named: 11,382`)
   - `readable C: 18,736 functions written, 12 skipped` (exit code `0`).
   - *Note on `--check` exit code*: `merge_names.py --check` reported `bad proposal entries 0` and `unknown addresses 0` while returning exit code `1` solely because `batches missing` flagged the original `N_*` batches of the 120 addresses overlaid by `R_K01.json`. In `tools/merge_names.py` line 884, `entry["_n_batch"] = old.get("_batch")` overwrites `_n_batch` with `R_001..R_065` whenever a second-layer `R_*` batch (`R_K01`) refines an address already touched by an earlier `R_*` batch (similar to `R_S01`). Per Rule 2 (`tools/merge_names.py` not owned), we did not modify `tools/merge_names.py`; running `python tools/merge_names.py` merged all 194 batches cleanly with exit code `0`.
3. **Bit-matching rebuild (`python tools/build.py`)**:
   - `Generated 'code.bin' (7,090,176 bytes)` — `SHA-256: dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8`
   - **`[PASS] Reconstructed code.bin bit-matches original uncompressed code.bin (0 differences)!`**
   - `Generated 'code.compressed.bin' (3,920,924 bytes)` — `SHA-256: ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f`
   - **`[PASS] Reconstructed ExeFS .code bit-matches original compressed .code (0 differences)!`** (`Exit Code 0`).
4. **Project verification (`python tools/verify_project.py`)**:
   - All 17 checks `[PASS]` (`code.bin` size/hash, all 7 asset categories with `errors: 0`, model texture manifest, 18,787 native entry points, 18,748 decompiled, 1,196 decoded maps, patched ROM, `viewer_rs.exe`, 4 C source replacements).
   - **`OVERALL: PASS -> audit/PROJECT_VERIFICATION.json`** (`Exit Code 0`).
5. **Full test suite (`python tests/run_all.py`)**:
   - Tier 1 (Feature Coverage): `70 / 70 PASS` (`1.60s`)
   - Tier 2 (Boundary & Corner Cases): `70 / 70 PASS` (`5.42s`)
   - Tier 3 (Pairwise Combinations): `14 / 14 PASS` (`1.33s`)
   - Tier 4 (Real-World Scenarios): `69 / 69 PASS` (`160.13s`)
   - Tier 5 (Challenger — BLZ, ROM pipeline, native decompilation): `40 / 40 PASS` (`34.00s`)
   - Tool unit tests (`tests/test_*.py`): `121 run / 120 pass / 1 skip / 0 fail` (`104.78s`)
   - **`TOTALS: 384 run | 383 pass | 1 skip | 0 fail | 307.26s | SUCCESS`** (`ALL TEST TIERS COMPLETED SUCCESSFULLY (Exit Code 0)`).

---

## 6. Honest Assessment — What Is NOT Verified

1. **Static disassembly & call-graph analysis only (no runtime emulator trace)**: Every decoded behavior, vtable dispatch, and struct offset in `R_K01.json` and `FACTS.md` was proven statically from `code.bin` ARM/Thumb/VFP instructions and caller/callee sites, not stepped through in Azahar or on physical 3DS hardware.
2. **41 entries intentionally remain `maybe_*` (`confidence < 0.50`)**: Where disassembly proved the exact operation (e.g., `0x0062943C` `maybe_PartyMember_GetCharRecordFlag430` reading `CharacterRecord->u8_430`, `0x0062EF8C` `maybe_Field_GetActorAnimSpeedMultiplier` returning `1.0f`/`3.0f` in `s0`, `0x0048748C` `maybe_Battle_Unit_GetPartyHandAttrByte` reading `PartyMember +0xDEF/+0xDF0`, `0x0062F694` `maybe_Ui_PromptRef_IsFirstChoiceConfirmed` checking prompt choice `== 0`), the exact gameplay meaning of the underlying flag/attribute byte is not yet proven from asset tables, so keeping `maybe_` avoids introducing new confident over-claims.
3. **Caller names in poisoned neighbourhoods are still stale**: Merging `R_K01.json` updated the 120 core helpers and regenerated all 18,736 `decomp/readable/*.c` call sites so future passes see the true helper names, but existing *already-confident* callers in poisoned blocks (`0x00269F64..0x00277700` `Ui_TextLayout_*`, `0x00485D90..0x00497900` `Text_*` / `Battle_Message_*`, `0x0051BA34..0x0051CD40` `Sound_Driver_*`) retain their earlier batch names until targeted un-poisoning batches run.

---

## 7. Suggested Follow-Up Tasks

1. **`K2_unpoison_battle_ai` (`0x00269F64..0x00277718`)**: Re-refine the ~60 functions from `N_046` currently named `Ui_TextLayout_LayoutMode0..8` / `Ui_TextLayout_*` into `BattleAi_*` using the `0x7C`-candidate (`40 spells + 60 skills + 24 items`) and 16-target-bucket (`0x9BC` stride) architecture established here.
2. **`K3_unpoison_battle_math_and_errf` (`0x00485D90..0x00497900` & `0x0051BA34..0x0051CD40`)**: Rename the mislabeled `Text_MeasureTextRun` / `Text_BuildRowForActor*` / `Battle_Message_*` combat-math functions (`0x00485D90..0x00497900`) and the CTR SDK `nn::err` `err:f` fatal-error applet helpers (`0x0051BA34..0x0051CD40`, currently `Sound_Driver_*`).
3. **`K4_core_helpers_next120`**: Continue bottom-up disassembly refinement down `scores.jsonl` (`ranks 121..240` by `callers_conf`), prioritizing helpers with short/truncated Ghidra bodies or VFP float returns.
4. **One-line fix in `tools/merge_names.py` line 884**: Change `entry["_n_batch"] = old.get("_batch")` to `entry["_n_batch"] = old.get("_n_batch") or old.get("_batch")` so multi-layer `R_*` overlays (`R_S01`, `R_K01`, future `R_K*`) preserve the original `N_*` provenance during `--check`.
