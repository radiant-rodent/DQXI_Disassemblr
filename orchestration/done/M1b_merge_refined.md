# M1b_merge_refined — Second-Pass Refine Merge & Readable C Regeneration

## Summary

The second naming pass ("refine") applied refined function proposals from `orchestration/naming/refine/out/` across the decompiled catalog. Refined names, signatures, parameter maps, and documentation comments have been merged into `symbols.json`, `symbols_recovered.json`, `decomp/ghidra/functions_merged.jsonl`, `decomp/ghidra/functions_index.json`, and `decomp/readable/`.

Full call-graph context established in the first merge allowed workers across 82 batches (`R_001` .. `R_082`) plus three targeted sweep overlays (`R_K01`, `R_S01`, `R_S02`) to resolve ambiguous `maybe_` functions with concrete caller, callee, vtable, and literal evidence.

Because 6,026 `maybe_` functions remain (>1,500) and this pass converted 41.5% of its inputs (>20%), the third round (`R2`) has been batched and scheduled via `tools/make_refine_batches.py --prefix R2`, producing 47 task files (`R2_001.md` .. `R2_047.md`) chained after `M1b_merge_refined`.

---

## Key Metrics for Orchestrator

| Metric | Before Refine (M1) | After Refine (M1b) | Change |
|---|---|---|---|
| **Named (non-`maybe_`) functions** | 8,492 / 18,787 (45.20%) | **12,761 / 18,787 (67.92%)** | **+4,269 (+22.72%)** |
| **Documented functions** | 8,074 (42.98%) | **12,357 (65.77%)** | **+4,283 (+22.79%)** |
| **High-confidence named (>=0.50)** | 8,492 | **12,301** | **+3,809** |
| **`maybe_` catalog functions** | 10,295 | **6,026** | **-4,269 (-41.47%)** |
| **Catalog entry points** | 18,787 | 18,787 | 0 (conserved) |
| **Readable C files generated** | 18,593 | 18,593 | 0 (155 data/label entries excluded) |
| **Opaque recovered types (`recovered_types.h`)** | 947 | 947 | Stable |

### Refine Proposals Breakdown

Total refined proposals processed: **10,579 entries** across 85 files (82 `R_###` batches + `R_K01`, `R_S01`, `R_S02`).

- **`confirmed`**: **3,672** (previous guess was correct; stripped `maybe_` prefix, confidence promoted to >= 0.50)
- **`corrected`**: **1,958** (previous guess was misleading or incorrect; assigned new descriptive name)
- **`kept_maybe`**: **4,949** (insufficient evidence or ambiguous shared body; retained `maybe_` prefix and confidence < 0.50)
- **Reclassified entries**: **1** (`0x00603148` in `R_002` proposed `BattleScene_BuildUnitKeyframes` (conf 0.50) from `maybe_BattleScene_ApplyUnitAnimTiming` but marked `confirmed`; mechanically reclassified as `corrected`).
- **Demotions / clamps**: 0 entries had `confirmed` with conf < 0.50; 0 entries had `kept_maybe` with conf >= 0.50.

---

## Validation & Batch Integrity

Validation executed via `python tools/merge_names.py --check`:

| Check | Result |
|---|---|
| Total Proposals | 18,327 (from 213 batch inputs across first and second passes) |
| Refine Proposals | 10,579 |
| Batch Coverage | 82/82 `R_###` batches accounted for (10,289/10,289 functions; 0 missing) |
| Missing Batches / Redo | **None** (no `R_redo_###` required) |
| Unknown Addresses | 0 (all addresses match `decomp/ghidra/functions_index.json`) |
| Valid C Identifiers | 100% valid (0 invalid identifiers, 0 reserved keyword conflicts) |
| Parameter Names Repaired | 9,084 descriptive string values normalized to C identifiers |
| Signature Names Fixed | 427 proposals where signature function name lagged proposal name |
| Encoding | 213/213 input files decode cleanly as UTF-8 |

### Name Clashes (23 Resolved)

As in M1, clashes between proposals are resolved deterministically: the higher-confidence proposal keeps the base name, ties are broken by lower address, and the other function receives a `_2` suffix (or `_3` if `_2` was already claimed by an earlier proposal). The allocation is completely idempotent across re-runs.

| Original Proposed Name | Kept By | Suffixed To | Confidence |
|---|---|---|---|
| `Mem_AllocAligned` | `0x0010F6EC` (0.85) | `0x00109DC8` → `Mem_AllocAligned_2` | 0.75 |
| `Sound_CommandQueue_Push` | `0x005EAF40` (0.65) | `0x001EB8C8` → `Sound_CommandQueue_Push_2` | 0.60 |
| `Ui_CreditWindow_Dtor` | `0x00212A24` (0.62) | `0x002880F4` → `Ui_CreditWindow_Dtor_2` | 0.50 |
| `Ui_TalkWindow_Ctor` | `0x0041B5D8` (0.60) | `0x002186F4` → `Ui_TalkWindow_Ctor_2` | 0.55 |
| `Actor2D_DeletingDtor` | `0x0021B85C` (0.55) | `0x00219938` → `Actor2D_DeletingDtor_2` | 0.50 |
| `Ui_SakusenWindow_InitPanes` | `0x002A12E0` (0.85) | `0x0046A584` → `Ui_SakusenWindow_InitPanes_2` | 0.65 |
| `Ui_Window_Dtor` | `0x0043FDE0` (0.60) | `0x002B7868` → `Ui_Window_Dtor_3` (`_2` used by `0x00319148`) | 0.50 |
| `Ui_Message_SetNameAndNumberArgs` | `0x002E4E50` (0.55) | `0x004067CC` → `Ui_Message_SetNameAndNumberArgs_2` | 0.50 |
| `Ui_GaugeWindow_InitPanesB` | `0x004129B0` (0.55) | `0x0032CCC4` → `Ui_GaugeWindow_InitPanesB_2` | 0.50 |
| `Ui_TwoColumnTextWindow_InitPanes` | `0x003FBD40` (0.60) | `0x0036BAF8` → `Ui_TwoColumnTextWindow_InitPanes_2` | 0.50 |
| `Ui_FourRowTextWindow_InitPanes` | `0x004F8C54` (0.72) | `0x00392E20` → `Ui_FourRowTextWindow_InitPanes_2` | 0.50 |
| `Ui_CameraAnimWindow_Init` | `0x003EDD10` (0.55) | `0x003ED494` → `Ui_CameraAnimWindow_Init_2` | 0.50 |
| `Ui_Object_DtorTrivialB` | `0x00448560` (0.70) | `0x00417BE8` → `Ui_Object_DtorTrivialB_2` | 0.55 |
| `Ui_MessageWindow_Open` | `0x001C5328` (0.60) | `0x004441E8` → `Ui_MessageWindow_Open_2` | 0.55 |
| `Ui_SakusenWindow_DtorBase` | `0x004CFFB0` (0.60) | `0x00479398` → `Ui_SakusenWindow_DtorBase_2` | 0.55 |
| `Gfx_Movie_StartPlayback` | `0x004FE0DC` (0.60) | `0x001B7340` → `Gfx_Movie_StartPlayback_2` | 0.50 |
| `Battle_ActionSequence_Update` | `0x004E95E0` (0.70) | `0x004F7320` → `Battle_ActionSequence_Update_2` | 0.65 |
| `Fs_ArchiveStream_ReadAt` | `0x005047E0` (0.65) | `0x00547504` → `Fs_ArchiveStream_ReadAt_2` | 0.60 |
| `Sound_StreamPlayer_Shutdown` | `0x00546220` (0.65) | `0x005EB0E0` → `Sound_StreamPlayer_Shutdown_2` | 0.50 |
| `Field_SceneObject_DeleteSprite` | `0x005B0274` (0.55) | `0x005C8728` → `Field_SceneObject_DeleteSprite_2` | 0.50 |
| `BattleScene_BuildUnitKeyframes` | `0x00603148` (0.50) | `0x00604580` → `BattleScene_BuildUnitKeyframes_2` | 0.50 |
| `maybe_Camera_UpdateFollowPosition` | `0x00182B2C` (0.45) | `0x001D1FC4` → `maybe_Camera_UpdateFollowPosition_2` | 0.45 |
| `maybe_Ui_TextWindow_DeletingDtor` | `0x002FFA14` (0.45) | `0x00409710` → `maybe_Ui_TextWindow_DeletingDtor_2` | 0.45 |

---

## Spot-Check of 30 Random Proposals

Sampled with seed `20261105` across 30 different batches:

| # | Batch | Address | Final Name | Conf | Change | Evaluation & Context |
|---|---|---|---|---|---|---|
| 1 | R_017 | `0x001D5EAC` | `Model_ApplyFaceParamQuad` | 0.50 | confirmed | **Correct**: Default-constructs 4 elements via `0x005F9720` for blink face parameter in `Model_SetFaceMode`. |
| 2 | R_020 | `0x002ACF58` | `maybe_Camera_UpdateSmoothFollow` | 0.40 | kept_maybe | **Plausible**: Camera smoothing helper with vector interpolations; correctly kept as maybe. |
| 3 | R_078 | `0x004DDA60` | `maybe_Text_MessageWindow_Dtor` | 0.45 | kept_maybe | **Plausible**: Destructor sequence on message layout structure; ambiguous vtable. |
| 4 | R_013 | `0x00304FC8` | `maybe_Ui_Window_SelectEntryC` | 0.40 | corrected | **Correct**: Queries bound list via vtable +0x58 and selects u16 entry; previous `Text_CommitLine` was wrong. |
| 5 | R_053 | `0x001C4DAC` | `Ui_MessageWindow_UpdateTextStyleIndex` | 0.50 | confirmed | **Correct**: Reads font index parameter and updates window style offset +0x38. |
| 6 | R_079 | `0x005AFC78` | `maybe_Ui_Widget_ApplyFlagToChildren` | 0.45 | kept_maybe | **Plausible**: Bitmask propagation down child widget linked list. |
| 7 | R_022 | `0x003B887C` | `Ui_Row_SetColors` | 0.50 | confirmed | **Correct**: Writes RGBA color values to row vertex buffer at offset +0x24. |
| 8 | R_055 | `0x002FE714` | `maybe_Ui_Window_InputToState18B` | 0.40 | kept_maybe | **Plausible**: State machine transition on pad input; retained as maybe. |
| 9 | R_039 | `0x00113814` | `maybe_Os_SignalAndClose` | 0.40 | kept_maybe | **Plausible**: Event signal / handle release wrapper in OS layer. |
| 10 | R_080 | `0x005F8704` | `Ui_Balloon_MeasureText` | 0.55 | confirmed | **Correct**: Computes text bounding box for dialogue balloon layout. |
| 11 | R_059 | `0x0019C9E8` | `Ui_JumonWindow_UpdateInput` | 0.50 | confirmed | **Correct**: Spell/Jumon selection window pad input processor. |
| 12 | R_041 | `0x002C6468` | `Ui_Model2D_BindBaseAnimation` | 0.50 | confirmed | **Correct**: Binds base skeletal animation track to 2D UI model. |
| 13 | R_024 | `0x001BC3E4` | `Ui_HandleSet_IsReady` | 0.50 | confirmed | **Correct**: Checks readiness flags across handle pair at +0x10 and +0x14. |
| 14 | R_076 | `0x00478A84` | `Ui_TextListWidget_Ctor` | 0.60 | confirmed | **Correct**: In-place constructor installing text list widget vtable `0x00773D30`. |
| 15 | R_004 | `0x003D9618` | `maybe_Field_IsMessageBusy` | 0.40 | kept_maybe | **Plausible**: Busy-flag check on field message work area; retained as maybe. |
| 16 | R_040 | `0x003E7D6C` | `Field_ActorModel_Dtor` | 0.50 | confirmed | **Correct**: Destructor releasing 3D actor model resources in field engine. |
| 17 | R_035 | `0x001F5C90` | `Battle_IsActionQueueIdle` | 0.50 | corrected | **Correct**: Checks if battle queue (+0x4320) is empty; previous `Ui_IsIdle` name was misleading. |
| 18 | R_044 | `0x001A3EE0` | `Ui_SpriteWidget_Ctor` | 0.50 | confirmed | **Correct**: Initializes sprite widget struct and installs vtable `0x00762E40`. |
| 19 | R_007 | `0x00361D10` | `maybe_Model_SetupAnimPart` | 0.45 | kept_maybe | **Plausible**: Sub-mesh animation matrix setup; retained as maybe. |
| 20 | R_063 | `0x00380690` | `maybe_Ui_MessageWindow_UpdateRows` | 0.45 | kept_maybe | **Plausible**: Row layout refresh within message window work area. |
| 21 | R_009 | `0x00451540` | `maybe_Container_AddMaskedEntry08` | 0.40 | corrected | **Correct**: Inserts 8-byte entry into keyed bucket; previous name had redundant `MaskedEntryList` prefix. |
| 22 | R_062 | `0x003260E8` | `maybe_Ui_Tween_EvalDefault` | 0.45 | kept_maybe | **Plausible**: Linear interpolation evaluation helper for UI transitions. |
| 23 | R_037 | `0x004FE0A4` | `Gfx_Movie_Pause` | 0.60 | confirmed | **Correct**: Pauses movie playback (+0x24=0, +0x25=1, calls `0x004FC4C4`); mirrors resume `0x004FE304`. |
| 24 | R_057 | `0x00123070` | `maybe_Snd_SetChannelLoopPoints` | 0.45 | kept_maybe | **Plausible**: Sound channel DSP loop registers setup; retained as maybe. |
| 25 | R_012 | `0x005D9F1C` | `maybe_Ui_Context_SetStatePair` | 0.30 | corrected | **Correct**: Calls UI context core (`0x006F229C`) vtable slot; previous `Field_Gimmick` name was completely wrong. |
| 26 | R_031 | `0x00451F2C` | `Ui_List_HandleInputPad` | 0.60 | confirmed | **Correct**: 9-way key switch dispatching confirm/cancel/d-pad to controller virtual methods. |
| 27 | R_011 | `0x00630998` | `Ui_ListItemRef_ResolveRowSimple` | 0.60 | confirmed | **Correct**: Resolves status byte / list slot offset from item reference. |
| 28 | R_054 | `0x002E6194` | `maybe_Fs_GetResourceByIdC` | 0.40 | kept_maybe | **Plausible**: Resource archive lookup by 32-bit ID; retained as maybe. |
| 29 | R_036` | `0x002A4D2C` | `maybe_Ui_EquipWindow_SetSlotVisibility` | 0.40 | kept_maybe | **Plausible**: Toggles visibility flags on equipment slot panes. |
| 30 | R_025 | `0x003C23A4` | `Ui_ThreeRowNullTextWindow_InitPanesB` | 0.55 | confirmed | **Correct**: Binds literals `null_txt_l1..l3` at row IDs 0..2. |

**Verdict**: 30/30 (100%) sampled proposals verified as correct or appropriate `kept_maybe` decisions. 0 batches have defect rates exceeding threshold (0% defect rate).

---

## Build, Test & Verification Results

All required build, test, and verification suites executed and passing:

1. **Bit-Matching Reassembly (`python tools/build.py`)**:
   - `.text`: 6,438,972 bytes
   - `.rodata`: 481,816 bytes
   - `.data`: 163,108 bytes
   - Reconstructed `code.bin`: 7,090,176 bytes
     - SHA-256: `dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8`
     - Status: **PASS (0 byte delta from retail uncompressed code.bin)**
   - Reconstructed ExeFS `code.compressed.bin`: 3,920,924 bytes
     - SHA-256: `ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f`
     - Status: **PASS (0 byte delta from retail compressed code.bin)**

2. **Decompilation E2E Test Suite (`python tests/run_all.py`)**:
   - Tier 1 (Feature Coverage): 70/70 PASS
   - Tier 2 (Boundary & Corner Cases): 70/70 PASS
   - Tier 3 (Pairwise Combinations): 14/14 PASS
   - Tier 4 (Real-World Scenarios): 69/69 PASS
   - Tier 5 (Challenger - BLZ/ROM/Decomp): 40/40 PASS
   - Tool Unit Tests: 120/121 PASS (1 skipped: opt-in citra emulator)
   - Total: **384 tests executed, 383 passed, 1 skipped, 0 failed** (ALL TIERS SUCCESS).

3. **Full Project Verification (`python tools/verify_project.py`)**:
   - `code.bin` hash & size: PASS
   - Asset verification (textures, layouts, models, scripts, tables, audio, maps): PASS
   - Model texture manifests: PASS
   - Native entry points (18,787) / decompiled (18,748): PASS
   - C source replacements: PASS (4/4 bit-verified)
   - Status: **OVERALL PASS**

4. **Catalog & Symbols Validation (`python tools/merge_names.py --check`)**:
   - Status: **PASS (0 errors, 0 warnings)**

5. **Strict UTF-8 Encoding:**
   - 18,593 files in `decomp/readable/`: 100% verified clean strict UTF-8 (0 decode errors).
   - Core files (`symbols.json`, `symbols_recovered.json`, `functions_merged.jsonl`, `functions_index.json`, `include/recovered_types.h`): clean UTF-8.
   - All 96 generated R2 batch and task files: clean UTF-8.

---

## Round 3 Generation (`R2_001` .. `R2_047`)

Per task step 7, since **6,026 `maybe_` functions remain (>1,500)** and this pass **converted 41.5% of its inputs (>20%)**, the next refine pass (`R2`) has been generated:

Command: `python tools/make_refine_batches.py --prefix R2`

- Candidates: **5,962 functions** (excluding 64 data/label rows).
- Batches: **47 batches** (`R2_001.txt` .. `R2_047.txt`) written to `orchestration/naming/refine/batches/`.
- Tasks: **47 tasks** (`R2_001.md` .. `R2_047.md`) written to `orchestration/tasks/`, with explicit dependency:
  `after: M1b_merge_refined`
- Updated context score database: `orchestration/naming/refine/scores.jsonl` and manifest `orchestration/naming/refine/index.json`.
- Newly unblocked context:
  - Zero-context candidates dropped from 3,249 down to 1,266.
  - Candidates with known vtable siblings increased to 1,189.
  - 100% of readable C paths in `R2_###.txt` verified present on disk (0 missing files).
