# M3_vars_merge: done (2026-11-13, by Claude directly, not a worker)

- `python tools/typedb/apply.py --validate` / `--merge`: merged 14,343 functions, 76,957 local/param tokens
  (plus 1,649 classes, 26,154 fields, 4,490 globals). 12 errors, 463 warnings (param_N vs argN, expected).
- Rejected answers (12): the worker used `self` as a new name, which `tools/typedb/common.py` reserves as a keyword
  (Ui_EquipWindow_UpdateInputState, ActorActionSeq_CollectPendingNodes, Gfx_EffectNode_SetupFromDesc,
  Field_SceneNode_UpdateActAnim, Ui_LogFormat, Casino_Slot_UpdateSpeed(B), Snd_LoadArchiveTail(Arm|Thumb),
  Ui_ListWindow_UpdateRowEnable, Ui_DiveForm_HandleInputTween, Ui_DiveForm_ResetChildrenState50).
  Those variables keep their Ghidra names. No tool or answer was edited.
- `merge_names.py --check` clean; `merge_names.py` regenerated decomp/readable.
- Progress: locals named 62.6% (was 21.8% before the V merge), types 62.24%, batches 341/341.
- `tools/build.py`, `tests/run_all.py`, `tools/verify_project.py`: all pass, OVERALL: PASS (audit/PROJECT_VERIFICATION.json).
- Names remain static-analysis hypotheses; V workers mixed Sonnet subagents, Gemini 4 Hydrogen, OpenCode DeepSeek and Mistral Vibe.


## Update 2026-11-15 (final)
- Gap-fill pass (VG_001..078) plus the R5 and SF refine rounds merged. Locals 91.9%, native functions 84.1% named, build bit-match, tests and verify_project all PASS.
- The 12 `self` rejects were resolved by renaming the answers (`selfObj` / `maybe_selfReg`); `self` stays reserved.
- Bug fixed in tools/readable_c.py: locals are now also looked up by function address, so functions outside function_by_address get their local names in decomp/readable.
