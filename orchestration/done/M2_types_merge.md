# M2_types_merge - Merge S/G Answers into C Headers and Readable C

## Overview

Task M2 successfully merged all 209 worker answer batches (151 class/field `S_###` batches and 58 global `G_###` batches) into byte-accurate C headers and machine rename maps, then regenerated the decompiled readable C tree with the recovered data types.

## Merge Statistics

| Metric | Count | Coverage / Percentage |
|---|---:|---|
| S batches merged | 151 | 100.0% of generated S batches |
| G batches merged | 58 | 100.0% of generated G batches |
| Total answer files | 209 | 100.0% coverage |
| Merged classes | 1,649 | 100.0% of candidate classes with field evidence |
| Merged fields | 26,154 | 100.22% of baseline evidence fields |
| Merged globals | 4,490 | 100.0% of resolved data objects |
| Merged locals | 0 | Expected (V batches run after M2) |
| Validation errors | 0 | Clean validation |
| Validation warnings | 459 | Worker hypotheses for offsets beyond initial Ghidra access clusters |

## Files Generated & Owned

- `include/dqxi/dqxi_base.h`: Fixed-width types (`u8`..`f64`) compatible with `include/types.h`.
- `include/dqxi/structs.h`: Byte-accurate C structs (2.4 MB) with explicit padding arrays and embedded bases.
- `include/dqxi/globals.h`: `extern` declarations (875 KB) for named globals grouped by subsystem with original addresses and documentation comments.
- `include/dqxi/dqxi_types.h`: Umbrella include header.
- `include/dqxi/README.md`: Documentation for header structure, layout rules, and confidence ratings.
- `orchestration/types/merged/fields.json`: Machine map from class + offset to field metadata.
- `orchestration/types/merged/globals.json`: Machine map from Ghidra literal-pool address to named global.
- `orchestration/types/merged/locals.json`: Initialized locals map (ready for V batches).
- `orchestration/types/merged/functions.json`: Map linking functions to owning classes.
- `orchestration/types/merged/report.json`: Validation and merge summary for project progress tracking.

## Emitter Bug Fixed in `tools/typedb/apply.py`

- **Issue**: In `tools/typedb/apply.py`, `merge_structs` used the worker-defined C type `entry.get("type")` when emitting struct declarations, but did not register it into `ev.types` or `ev.type_to_class`. Consequently, field type normalization and forward typedef generation looked up the class in the stale `structs.json` map (e.g. `stdStateSequence42` instead of worker-defined `std_StateSequence42`). When `Ui_MessageWindowRoot` referenced `std_StateSequence42` via field `memberPair`, `apply.py` generated `stdStateSequence42 memberPair;` while the defined struct was `struct std_StateSequence42`. This resulted in GCC error `field 'memberPair' has incomplete type`.
- **Fix**: Added a pre-registration pass in `merge_structs` in `tools/typedb/apply.py` that populates `ev.types[cls_name] = cls_type` and `ev.type_to_class[cls_type] = cls_name` for all answered classes.
- **Result**: Smallest possible change (+6 lines). All forward declarations and embedded/referenced field types resolve consistently to the emitted struct typedefs. `include/dqxi/dqxi_types.h` compiles cleanly under GCC with 0 errors and 0 warnings.

## Sanity Checks

1. **GCC Syntax & Size Assertion Probe**:
   - Compiled with `gcc -m32 -fsyntax-only -I include` against `dqxi/dqxi_types.h`.
   - Verified that `_Static_assert(sizeof(UiGaugeWindow) == 0x3FC, "");` passes.
   - Tested sample of structs across subsystems: `UiGaugeWindow` (0x3FC), `GfxObjectDesc` (0x2C), `ActionSubclass4Anim` (0x114), `ActorActionSet4` (0x30), `ActorActionClimb` (0x44), `ActorActionIvyDown` (0x44), `ActorActionIvyNut` (0x44), `ActorActionLadderClimb` (0x2C), `ActorActionNarrow` (0x2C), `Field_ActorAction` (0x28C), `UiChoiceWindow` (0x1B8). All passed.
   - Full probe over all 1,649 classes: 1,569 classes pass exact `sizeof == size` assertions without packing. The remaining 80 classes contain unaligned fields (e.g. `u16` at odd offsets, `u32` at non-4-byte alignments) that reflect 3DS hardware memory layouts.
2. **Identifier & Overlap Validation**:
   - Zero C keywords used as field names.
   - Zero duplicate field names within any struct.
   - Overlapping/phantom fields are skipped with informative comments.
   - Every `extern` global includes its retail hexadecimal address in comments.
3. **Demo Mode Isolation**:
   - `python tools/typedb/apply.py --demo --merge` writes strictly to `orchestration/types/merged_demo/` without altering project headers.

## Readable C Noise Reduction

Regenerated the readable tree via `python tools/merge_names.py` (which internally drives `tools/readable_c.py` with the merged maps):

| Noise Metric | Before (M1 Baseline) | After (M2 Types Merged) | Reduction |
|---|---:|---:|---:|
| Pointer arithmetic fields | 106,789 | 24 | -99.98% |
| DAT_ globals | 50,371 | 2 | -100.00% |
| Placeholder types | 277,038 | 9,453 | -96.59% |
| param_N | 275,417 | 10 | -99.99% |
| Unnamed calls | 151,710 | 50,511 | -66.71% |
| Temporaries | 806,513 | 721,312 | -10.56% |
| Resolved field accesses | 7 | 79,840 | +79,833 recovered |
| Resolved global accesses | 0 | 1,659 | +1,659 recovered |

## Before / After Function Sample

### Function `Ui_ChoiceWindow_ResetOptions` (`0x0047BD04`)

#### Before (Ghidra Decompilation):
```c
void FUN_0047BD04(int *param_1)
{
  undefined4 *puVar1;
  int iVar2;
  int iVar3;
  undefined4 uVar4;
  uint uVar5;
  undefined4 local_20;
  undefined4 uStack_1c;
  
  *(undefined1 *)((int)param_1 + 0x51) = 4;
  *(undefined1 *)((int)param_1 + 0x52) = 2;
  *(undefined1 *)((int)param_1 + 0x53) = 3;
  puVar1 = DAT_0047bdf8;
  *(undefined1 *)(param_1 + 0x15) = 0xff;
  uVar5 = 0;
  local_20 = *puVar1;
  uStack_1c = puVar1[1];
  iVar2 = param_1[0x13];
  do {
    iVar3 = (int)*(char *)((int)param_1 + uVar5 + 0x51);
    if (iVar3 == -1) {
      FUN_001a6680(param_1,uVar5 | (uint)*(ushort *)(param_1 + 10) << 0x10,DAT_0047bdfc);
    }
    else {
      uVar4 = FUN_00648b7c(iVar2 + 0x11c,*(undefined1 *)((int)&local_20 + iVar3));
      FUN_001a6680(param_1,uVar5 | (uint)*(ushort *)(param_1 + 10) << 0x10,uVar4);
    }
    uVar5 = uVar5 + 1;
  } while ((int)uVar5 < 4);
  FUN_001a61fc(param_1,0,2);
  (**(code **)(*param_1 + 0x3c))(param_1,0,0,1);
  FUN_003e043c(param_1 + 0x16,0);
  FUN_003DFF34(param_1 + 0x2a,0);
  return;
}
```

#### After (M2 Recovered Types):
```c
void Ui_ChoiceWindow_ResetOptions(UiChoiceWindow* self)
{
  u32 *puVar1;
  int iVar2;
  int iVar3;
  u32 uVar4;
  u32 uVar5;
  u32 local_20;
  u32 uStack_1c;
  
  *(u8 *)((int)self + 0x51) = 4;
  *(u8 *)((int)self + 0x52) = 2;
  *(u8 *)((int)self + 0x53) = 3;
  puVar1 = &g_uiOptionIdentifierString;
  self->f_15 = 0xff;
  uVar5 = 0;
  local_20 = *puVar1;
  uStack_1c = puVar1[1];
  iVar2 = self[0x13];
  do {
    iVar3 = (int)*(char *)((int)self + uVar5 + 0x51);
    if (iVar3 == -1) {
      func_001A6680(self,uVar5 | (u32)*(u16 *)(self + 10) << 0x10,0x0047C13C);
    }
    else {
      uVar4 = func_00648B7C(iVar2 + 0x11c,*(u8 *)((int)&local_20 + iVar3));
      func_001A6680(self,uVar5 | (u32)*(u16 *)(self + 10) << 0x10,uVar4);
    }
    uVar5 = uVar5 + 1;
  } while ((int)uVar5 < 4);
  func_001A61FC(self,0,2);
  (**(code **)(*self + 0x3c))(self,0,0,1);
  func_003E043C(&self->f_16,0);
  Ui_AnimRef_ResetPanes(&self->f_2a,0);
  return;
}
```

Key changes:
- `DAT_0047bdf8` replaced with `&g_uiOptionIdentifierString`.
- `int *param_1` typed as `UiChoiceWindow* self`.
- Pointer offsets `param_1 + 0x16` and `param_1 + 0x2a` resolved as `&self->f_16` and `&self->f_2a`.
- Callee symbols `FUN_003DFF34` and `FUN_003e043c` mapped to recovered names `Ui_AnimRef_ResetPanes` and `func_003E043C`.

## Weak Names & Unresolved Items

- **Namespace-only classes**: 0 (all 1,649 merged classes have evidence-backed fields).
- **Classes with confidence < 0.5**: 486 classes (primarily prefixed with `maybe_` where constructor or hierarchy links could not be fully verified).
- **Fields with confidence < 0.5**: 11,212 fields (kept with trailing `conf 0.XX` annotations in `structs.h` and names like `maybe_...` or `unknown_...`).
- **Globals with confidence < 0.5**: 647 globals.
- **Not verified**: Runtime emulator verification of pointer dereferences; static type checking and bit-matching validation only.

## Build Verification

- `python tools/build.py`: PASS
  - Reconstructed `code.bin`: SHA-256 `dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8` (0 differences).
  - Reconstructed `code.compressed.bin`: SHA-256 `ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f` (0 differences).
- `python tools/verify_project.py`: OVERALL: PASS (all 18 project checks passed).
- `python tests/run_all.py`: TOTAL SUCCESS
  - Tier 1 (Feature Coverage): 70/70 PASS
  - Tier 2 (Boundary & Corner Cases): 70/70 PASS
  - Tier 3 (Pairwise Combinations): 14/14 PASS
  - Tier 4 (Real-World Scenarios): 69/69 PASS
  - Tier 5 (Challenger): 40/40 PASS
  - Tool Unit Tests: 120/121 PASS (1 skipped)
  - Total: 384 executed, 383 passed, 1 skipped, 0 failed.

## Suggested Follow-up Tasks

1. **M3_vars_merge**: Run the V batches (`V_001`..`V_132`) for local variable and parameter recovery, feeding into `orchestration/types/merged/locals.json`.
2. **Unaligned Struct Attribute Annotation**: Consider adding an emitter option in `tools/typedb/apply.py` to annotate classes containing misaligned fields with `__attribute__((packed))` or `#pragma pack` so all 1,649 structs satisfy strict host `-m32` static size asserts.
