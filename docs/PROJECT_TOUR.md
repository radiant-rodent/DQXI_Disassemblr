# Project tour — where everything lives

> Inside the editor: press **Tour** in the top bar (or start it with `DQXI_TOUR=1`) for a
> two-minute walk through every section. This page is the long form: where the files live.

This page is the map. Read it once and you know which folder to open for any job: data,
assets, scripts, native code, the editor, or the export pipeline.

- New to the project? Start with [GETTING_STARTED.md](GETTING_STARTED.md), then make a
  [first mod in 10 minutes](FIRST_MOD.md).
- Want to edit something specific? [EDITING.md](EDITING.md) is the per-asset cheat sheet.
- Want to read the engine? §4 below is the guided tour into `decomp/readable/`.

---

## 1. Folder map

| Path | What it holds | Regenerable? |
|---|---|---|
| `original/` | Decrypted retail baseline: `romfs.bin`, ExeFS (`code.decompressed.bin`), headers, `hashes.sha256` | from your own `DQXI.3ds` dump (`tools/extract_rom.py`) — treat as read-only |
| `asm/` | Complete modular ARM/Thumb disassembly (`start.s`, `init.s`, `text/`, `data/`, `rodata/`, `bss.s`), annotated with the original bytes | yes — `tools/disasm.py`; rebuilt by `tools/build.py` into the retail `code.bin` |
| `build/` | Build products: `code.bin`, compressed `.code`, `DQXI.3ds`, patched images, reports, scratch logs | yes — `tools/build.py`, `tools/recompile_game.py` |
| `decomp/ghidra/` | Raw Ghidra export: one `.c` per entry point, `by_subsystem/`, `functions_index.json`, `functions_merged.jsonl`, `COVERAGE.md` | yes — Ghidra headless + `tools/organize_ghidra.py` (see [CODE.md](CODE.md)) |
| `decomp/readable/` | **The human-facing native source**: 18,737 named, summarised `.c` files (`functions/` 18,151 + `recovered/` 586) | yes — `tools/merge_names.py` |
| `decomp/functions/` | Legacy register-level pseudo-C — comparison only, not the readable source | legacy |
| `src/` | 19 hand-written clean C subsystem models + `src/replacements/` (bit-verified C that *does* compile into the build) | hand-maintained |
| `include/` | Host-side headers (`dqxi.h`, subsystem headers, `recovered_types.h` with 992 opaque types) | hand-maintained |
| `game_data/` | Exact extracted game: `romfs/` (original files & containers), `packs/` (every PACK/PACA member), `arcs/` (every SARC member) | yes — `tools/extract_game_data.py --all`, `tools/extract_arcs.py` — **never edit in place** |
| `game_assets/` | Converted, editable copies: `textures/` `models/` `layouts/` `scripts/` `tables/` `audio/` `maps/` `text/`, each with a `*_summary.json` and `*_manifest.jsonl` | yes — `tools/convert_assets.py`, `tools/map_tool.py`, `tools/text_tool.py export` |
| `editor_projects/` | Level-editor projects (JSON) and editor settings | yours |
| `mod/` | **The mod workspace**: `mod/romfs/<exact RomFS paths>` + `mod/code/code.bin` + optional `mod.json` | yours; exported by `tools/export_mod.py` |
| `out/` | Export results: `luma/` (SD-card folder), `3ds/`, `cia/`, `EXPORT_REPORT.json` | yes — `python -m tools.export_mod --target …` |
| `tools/` | Every CLI tool (extract, convert, patch, export, verify) plus `tools/emu/` (emulator glue) | source |
| `viewer_rs/` | **DQXI Studio** — the Rust/egui browser + editor (`run_editor.bat`, `run_viewer_rs.bat`) | source |
| `tests/` | 223-test E2E suite (`run_all.py`, tiers 1–4) + opt-in emulator proof tests (`tests/emu/`) | source |
| `audit/` | Forensic inventories and reports (`GAP_REPORT.md`, `PROJECT_VERIFICATION.json`, `pack_members.jsonl`, …) | yes — `tools/audit_project.py` |
| `progress/` | Human-readable status pages (`progress.html`, `progress.svg`, `history.html`, `tasks.html`) | yes — `tools/progress.py` (`run_progress.bat`) |
| `docs/` | Task-oriented guides (this file) | source |
| `orchestration/` | Worker coordination: `PLAN.md`, task files, naming batches, done reports | orchestrator |
| `third_party/` | Vendored readers: `SPICA` (BCH reference reader) and `emutest/` (this project's Azahar data root) | read/used, not edited |

### The pipeline at a glance

```
DQXI.3ds ──extract──► original/ + game_data/ ──convert──► game_assets/
                                                          │
                                     edit (DQXI Studio / tools/*.py)
                                                          ▼
                                              mod/romfs/… + mod/code/code.bin
                                                          │
                              export_mod.py ──────────────┴──► out/luma/   (Luma3DS LayeredFS)
                                                              out/3ds/    (4 GiB .3ds)
                                                              out/cia/    (installable .cia)

code.decompressed.bin ──Ghidra──► decomp/ghidra ──merge_names──► decomp/readable (reading)
                       └──disasm──► asm/ ──build.py──► code.bin (bit-matches retail; the safety net)
```

Two rules the whole project keeps: `game_data/` and `original/` are never edited in place, and
every build must keep reassembling the retail `code.bin` with zero differences.

---

## 2. How to read a symbol

All 18,804 symbols live in `symbols.json` (address → name, signature, summary, confidence,
evidence, batch). The naming convention is `Subsystem_VerbNoun`:

```json
{"address": "0x0016E3E0", "name": "Battle_Update", "type": "function",
 "signature": "void Battle_Update(BattleManager* self)", "confidence": 0.55, "batch": "N_039"}
```

- **`maybe_` prefix = confidence < 0.5.** ~10,295 names are guesses; trust the evidence string,
  not the name, until you have checked the body.
- Every file in `decomp/readable/` opens with a doc comment: final name, one-line summary,
  batch, confidence, address/mode/size, signature, evidence and the Ghidra source file — then the
  named definition and body. Example (`decomp/readable/functions/Battle_Update_0016e3e0.c`):

  ```c
  /*
   * Battle_Update - Main per-frame battle update: clears finished command objects, runs the
   * queued action processing, executes the AI pass …, and advances the phase/action counters.
   * Recovered: N_039, confidence 0.55, address 0x0016E3E0 (arm, 636 bytes).
   * Signature: void Battle_Update(BattleManager* self)
   * Evidence: …
   */
  ```

- Current coverage (from `progress/progress.json`): **18,787** entry points, **18,748**
  decompiled, **8,492 named (45.2%)**, **8,074 documented**, **4** compiled from C and verified
  byte-identical.
- The names come from 128 naming batches (`orchestration/naming/out/N_001.json` … `N_128.json`,
  18,327 proposals) merged by `tools/merge_names.py` (`--check` validates everything).

---

## 3. Which subsystem is which

### 3a. By name prefix (recognise a function's area at a glance)

Counts are from `symbols.json` (after stripping `maybe_`):

| Prefix | Domain | Count | Example readable file |
|---|---|---:|---|
| `Ui_` | windows, menus, message boxes, widgets, screens | 6,432 | [`Ui_MessageCmd_ShowPlainTextRecord`](../decomp/readable/recovered/Ui_MessageCmd_ShowPlainTextRecord_003b4d94.c) |
| `Field_` | field/world logic: NPCs, locators, scene objects, triggers | 2,516 | [`Field_NpcAction_Patrol_Update`](../decomp/readable/recovered/Field_NpcAction_Patrol_Update_0039be5c.c) |
| `Battle_` + `BattleScene_` | turn-based battle logic and its 3D presentation | 1,537 | [`Battle_UpdatePhaseState`](../decomp/readable/functions/Battle_UpdatePhaseState_0016d58c.c) |
| `Gfx_` | GPU/display: command buffers, framebuffers, sprites, resources | 1,393 | [`maybe_Gfx_ProcessFrame`](../decomp/readable/functions/maybe_Gfx_ProcessFrame_00113a50.c) |
| `Sound_` + `Snd_` | sound system: streams, channels, players, 3D panning | 681 | [`maybe_Snd_ChannelWorker`](../decomp/readable/functions/maybe_Snd_ChannelWorker_0011f3c0.c) |
| `std_` | runtime support: memory ops, strings, formats, sorts, state sequences | 590 | [`std_StateSequence01_Tick`](../decomp/readable/functions/std_StateSequence01_Tick_006c9708.c) |
| `Script_` + `Sq_` | Squirrel VM, script natives/bindings | 595 | [`Script_BindFieldNatives`](../decomp/readable/functions/Script_BindFieldNatives_0024f1d0.c) |
| `Actor_` + `Actor2D_` + `ActorAction_` | actor objects, parts, action sequences | 517 | [`Actor_Node_SetVisibleAll`](../decomp/readable/recovered/Actor_Node_SetVisibleAll_00166b7c.c) |
| `Text_` + `Message_` + `Font_` | text layout, control tags, glyph caches, message args | 463 | [`Font_GlyphCache_Ctor`](../decomp/readable/recovered/Font_GlyphCache_Ctor_0054dfc8.c) |
| `Field2D_` + `Battle2DUnit_` + `Ui3D_` | the 2D presentation layers (`Actor2D_` is counted above) | 371 | — |
| `Container_` | vectors, maps, lists, handles, hash maps | 251 | [`Container_HashMap_FindEntry`](../decomp/readable/functions/Container_HashMap_FindEntry_00178800.c) |
| `Model_` + `Anim_` + `Effect_` + `Fx_` | model/mesh/animation/effect handling | 599 | [`Gfx_Mesh_AllocSubmeshBuffers`](../decomp/readable/functions/Gfx_Mesh_AllocSubmeshBuffers_0065b310.c) |
| `Svc_` + `Os_` + `Mem_` | CTR kernel services, threads/events, heaps | 498 | [`Os_ThreadEntry`](../decomp/readable/functions/Os_ThreadEntry_0011cc30.c) |
| `Menu_` + `Item_` + `Party_` + `FieldParty_` | game-facing menus and party state | 483 | [`Party_InitMemberSlots`](../decomp/readable/recovered/Party_InitMemberSlots_0018d504.c) |
| `Fs_` + `Pack_` + `Data_` | file system, archive mounts, PACK handles, master tables | 239 | [`Fs_Sarc_FindFile`](../decomp/readable/functions/Fs_Sarc_FindFile_00535fa4.c) |
| `Video_` | BGM/movie (VLC-style) streaming | 176 | — |
| `Event_` + `Cutscene_` | event/cutscene command handlers | 184 | [`Event_Handler_TriggerCommand7`](../decomp/readable/recovered/Event_Handler_TriggerCommand7_003b3f68.c) |
| `Camera_` | camera controllers and descriptors | 106 | [`Camera_FollowController_Setup`](../decomp/readable/recovered/Camera_FollowController_Setup_003ea63c.c) |
| `Monster_` | monster field behaviour | 98 | [`Monster_FieldBehaviour_UpdateChase`](../decomp/readable/recovered/maybe_Monster_FieldBehaviour_UpdateChase_003af004.c) |
| `Casino_`, `Save_`, `Input_`/`Hid_`, `Game_`, `Work_` | minigames, save data, pad input, global game state, flag work | 226 | [`Save_SetParamSavePackName`](../decomp/readable/recovered/Save_SetParamSavePackName_0025dd40.c) |

Anything else (`pGl_`, `tEb_`, 4-letter names …) is either still unnamed or a Ghidra artefact —
check `symbols.json` for its entry before trusting it.

### 3b. By address range (how the progress page groups the binary)

| Subsystem (progress page) | Address span | Functions | Named |
|---|---|---:|---:|
| Kernel & system / boot | `0x00100024`–`0x0070BA3C` | 599 | 206 |
| Memory & heaps | `0x001000BA`– | 147 | 83 |
| Input | `0x00105044`– | 52 | 35 |
| IO & files | `0x00101A82`– | 211 | 92 |
| Audio | `0x00105584`–`0x006FE370` | 779 | 355 |
| Field & world | `0x00102828`–`0x00723950` | 1,649 | 723 |
| Actors & entities | `0x00104240`–`0x0070C00C` | 2,444 | 1,142 |
| Battle | `0x001471B0`–`0x0071D530` | 2,032 | 1,002 |
| Camera | `0x00146CA0`–`0x007074F0` | 179 | 95 |
| UI & message | `0x001006F0`–`0x0072298C` | 6,993 | 2,758 |
| Save & persistence | `0x00105500`–`0x00723438` | 428 | 210 |
| General procedures (runtime/`std_`/shared) | `0x00100000`–`0x00723EF0` | 3,274 | 1,791 |

The same numbers, live, are on the [progress page](../progress/progress.html). The Ghidra tree
also has a folder view in `decomp/ghidra/by_subsystem/` (coarser: most files sit in
`General_Procedures` — prefer the readable tree plus this section).

---

## 4. Engine internals — the guided tour

Every link goes to a real file under `decomp/readable/`. Read the doc comment first; it contains
the evidence behind the name and the confidence.

### 4.1 Boot and the main loop

1. **Reset** — [`ResetVector`](../decomp/readable/functions/ResetVector_00100000.c) is the
   CTR entry vector (36 bytes, from `asm/start.s`); the bring-up path around it is
   [`Engine_Initialize`](../decomp/readable/functions/Engine_Initialize_00101b74.c). The last boot step,
   [`maybe_Os_RunLateBootSetup`](../decomp/readable/functions/maybe_Os_RunLateBootSetup_00102874.c),
   "brings up the SDK sync layer, clamps the committed memory size, creates the application heap
   and finishes the allocator" — it has no callers except the reset path.
2. **Engine bring-up** — [`Engine_Initialize`](../decomp/readable/functions/Engine_Initialize_00101b74.c)
   (`void Engine_Initialize(void)`, 3,192 bytes) initialises the heap system and then lazily
   creates every global singleton (resource caches, renderer, sound, task pool, input) with a
   repeated *init-flag + aligned size + allocate + construct* pattern.
3. **Each frame** —
   [`maybe_Engine_DispatchFrameCallbacks`](../decomp/readable/functions/maybe_Engine_DispatchFrameCallbacks_00102ba4.c)
   is documented as the **main-loop callback dispatcher**: it runs registered `{fn, arg}`
   callbacks from the frame-begin / render / frame-end arrays rooted at `g_00102EB0`.
   The rendering half of the frame is driven by
   [`maybe_Gfx_ProcessFrame`](../decomp/readable/functions/maybe_Gfx_ProcessFrame_00113a50.c),
   which services the vblank callbacks, runs the pending command list and dispatches a
   pause/resume/sleep/wake state machine.
4. **Pacing** — [`Gfx_WaitFrameInterval`](../decomp/readable/functions/Gfx_WaitFrameInterval_00108430.c),
   [`Gfx_Display_PresentFrame`](../decomp/readable/functions/Gfx_Display_PresentFrame_00104dc0.c),
   `Gfx_SwapFrameBuffers`.
5. **Shutdown** — [`Engine_ShutdownAllSubsystems`](../decomp/readable/functions/Engine_ShutdownAllSubsystems_00694e18.c)
   unmounts archives, tears down OS sync, display and input.

> Honesty note: the dispatcher names are `maybe_` (confidence 0.30–0.50). The frame-loop *story*
> is supported by their doc-comment evidence, not by a verified call graph. Treat the exact loop
> location as a hypothesis worth confirming with `tools/disasm.py` xrefs.

### 4.2 Scene / state machine

The engine runs its flows as **state sequences**: a generic template instantiated ~85 times as
`std_StateSequenceNN_{Tick,ChangeState,SetState,Delete}` (files in
[`decomp/readable/functions/`](../decomp/readable/) prefixed `std_StateSequence`). Each instance
owns a vtable of state records; e.g.
[`std_StateSequence01_Tick`](../decomp/readable/functions/std_StateSequence01_Tick_006c9708.c)
calls the virtual `ChangeState` first and only advances the state timer when no transition
happened (a transition freezes the clock for that frame). Its doc comment names the owning
object (`maybe_Ui_BigScreen_Ctor`) and the vtable (`0x0075AC30`, table #33).

Where the sequences are used:

- **Battle scene**: [`maybe_BattleScene_UpdateState`](../decomp/readable/functions/maybe_BattleScene_UpdateState_00606234.c)
  and friends at `0x006062xx` (model layout, transitions, command widgets).
- **UI screens**: hundreds of `Ui_Window_GotoState…` / `Ui_Screen_…` functions (the window/state
  pattern is described per-file in their comments).
- **Global predicate**:
  [`maybe_Game_IsSceneBusy`](../decomp/readable/functions/maybe_Game_IsSceneBusy_004af5e4.c)
  — "true while GameWork's state object reports a non-zero value, i.e. an event/menu/scene is
  occupying the game"; callers use it to suppress field-object actions.
- **Field/map state**: `Field_MapState*`, `Field_*NotifySceneEvent*` functions.

### 4.3 Battle flow

Per frame:

1. [`Battle_Update`](../decomp/readable/functions/Battle_Update_0016e3e0.c)
   `void Battle_Update(BattleManager* self)` — the main battle update: clears finished command
   objects, runs the queued action processing, executes the AI pass, resolves the action queue,
   updates camera/scene hooks, advances phase counters and hands off to the next state when the
   battle is over. It is called from the battle state machine at `0x00606xxx`.
2. [`Battle_UpdatePhaseState`](../decomp/readable/functions/Battle_UpdatePhaseState_0016d58c.c)
   derives the **phase byte** (`self+0xbc`, values 0..8) from virtual predicates on the manager's
   vtable, so the update can branch on a single state value (turn order, command input, action
   resolution, victory/defeat…).
3. The action queue:
   [`Battle_UpdateActionQueue`](../decomp/readable/functions/Battle_UpdateActionQueue_0016e75c.c),
   [`maybe_Battle_Start`](../decomp/readable/functions/maybe_Battle_Start_0016e65c.c),
   [`Battle_ExecuteItemAction`](../decomp/readable/recovered/Battle_ExecuteItemAction_0016dfa8.c),
   target selection modes
   [`Battle_SelectTargetsMode2`](../decomp/readable/recovered/Battle_SelectTargetsMode2_00173b90.c)
   … `Mode6`.
4. Presentation is `BattleScene_*` (§4.2) plus `Ui_*` battle windows.

Clean models without Ghidra artefacts: `src/battle/state.c`, `src/battle/turn.c`,
`src/battle/damage.c`. Data that drives battle lives in `game_assets/tables/gamecmn/`
(`enemy_base.json`, `enemy_battle.json`, `spell.json`, `encount_table.json`,
`scenario_battle.json` — all with named fields, see [EDITING.md](EDITING.md#tables)), and scripted
fights are Squirrel packs under `game_assets/scripts/`.

### 4.4 Script VM and native bindings

- **VM core**: the game embeds a Squirrel 2.2 VM. `Sq_*` functions are the VM itself;
  [`Script_Vm_InitTables`](../decomp/readable/functions/Script_Vm_InitTables_00247c68.c) builds
  the VM header ("the classic VM state block of the Squirrel reference implementation") and
  [`Script_Vm_RegisterDefaultDelegates`](../decomp/readable/functions/Script_Vm_RegisterDefaultDelegates_00245fd0.c)
  installs default delegates.
- **Native bindings**: `Script_Bind*Natives` functions register the engine functions scripts may
  call. [`Script_BindFieldNatives`](../decomp/readable/functions/Script_BindFieldNatives_0024f1d0.c)
  registers **41 named field natives** (`LoadField`, `LoadBattleFunc`, `SetWeather`,
  `SetScenarioWeather`, camera-shake helpers …) through `Sq_BindNativeMethod`. Others:
  `Script_BindActorNatives`, `Script_BindUiMessageNatives`, `Script_BindDebugMenuNatives`,
  `Script_BindPlayerShopNatives`, … — grep `symbols.json` for `Script_Bind`.
- **The scripts themselves**: `romfs/script/<area>.pack` → `script.cnut`; readable source and an
  annotated assembly listing in `game_assets/scripts/packs/script/<area>/`, indexed by
  `script_index.json` (functions, natives with their summaries, cross-pack xrefs). See
  [SCRIPTS.md](SCRIPTS.md) and [EDITING.md](EDITING.md#scripts-events-cutscenes-quests).
- In DQXI Studio's **Scripts** panel, the *Natives* tab shows every native a script calls with
  its registered address and recovered summary — that is the fastest bridge from script to C.

### 4.5 File system, packs and tables

- **Mounting**: [`Fs_MountDefaultArchives`](../decomp/readable/functions/Fs_MountDefaultArchives_00104240.c)
  lazily mounts the built-in archives once; `Fs_MountByName`/`Fs_UnmountByName` and the
  `Fs_CacheSet_*` family (see
  [`Fs_CacheSet_UpdateEntries`](../decomp/readable/functions/Fs_CacheSet_UpdateEntries_00104520.c))
  run the cache/eviction policy.
- **Inside an archive**: [`Fs_Sarc_FindFile`](../decomp/readable/functions/Fs_Sarc_FindFile_00535fa4.c)
  is the classic SARC lookup — SFAT hash, binary search, string compare.
- **Master data**: [`Pack_LoadMasterTables`](../decomp/readable/recovered/Pack_LoadMasterTables_00120464.c)
  is the boot-time loader that resolves every core BXON table (`item`, `player_param_*`,
  `scenario_param_*`, level/area, sound groups, NG words …) by literal name into the data
  singleton. That is why a table edit lands in RAM the moment the game boots.
- **On disk**: the RomFS is `game_data/romfs/`; exploded members are `game_data/packs/`;
  compressed members (`.paca`, e.g. `syscmn.pack`) are decompressed/recompressed by the patch
  tools. Your edits go to `mod/romfs/<same path>` and out through
  `tools/export_mod.py` ([EXPORT.md](EXPORT.md)).

### 4.6 Rendering and UI

- **Display/GPU**: `Gfx_*` owns command buffers (`Gfx_InitializeCommandBuffers`,
  `Gfx_CommandBuffer_Submit`), pipeline state (`Gfx_InitPipelineState`), the GPU IPC
  (`Gfx_IpcCmd*`), sprite/scene nodes (`Gfx_Scene_*`) and resources (`Gfx_RegisterResource`).
  Clean model: `src/graphics/display.c`, `src/graphics/pica.c`.
- **Models/animation**: `Model_*`, `Anim_*`, `Gfx_Mesh_*` — asset side in
  [ASSETS.md](ASSETS.md) (BCH → glTF/OBJ, same-size write-back).
- **Text**: `Text_*` lays lines out and decodes control tags
  ([`Text_Style_Decode`](../decomp/readable/recovered/Text_Style_Decode_001926d4.c));
  [`Font_GlyphCache_Ctor`](../decomp/readable/recovered/Font_GlyphCache_Ctor_0054dfc8.c) runs
  the glyph cache; `Ui_*` builds the windows around it.
- **UI widgets**: `Ui_*` is the largest subsystem (6,432). Widgets draw via
  [`Ui_WidgetGroup_DispatchDraw`](../decomp/readable/recovered/Ui_WidgetGroup_DispatchDraw_001a5f28.c),
  windows are state machines (§4.2), and layouts come from BFLYT/BFLAN JSON
  (`game_assets/layouts/`, [ASSETS.md](ASSETS.md)).

### 4.7 The rest in one line each

- **Audio** (`Sound_`/`Snd_`, `src/audio/`): BCSTM streams + BCSAR archives; see [AUDIO.md](AUDIO.md).
- **Save** (`Save_`, `src/save/`): slot tasks, password restoration codes; data model in `Save_and_Persistence`.
- **Input** (`Input_`/`Hid_`, `src/hid/pad.c`): calibrated pad reader at `0x0011AD3C`.
- **Field & actors** (`Field_`/`Actor_`, `src/field/`): NPCs patrol/walk/talk
  ([`Field_NpcAction_Patrol_Update`](../decomp/readable/recovered/Field_NpcAction_Patrol_Update_0039be5c.c)),
  scene objects spawn from `level3d.bxon` placement records (Level Editor).
- **Party** (`Party_`): member slots ([`Party_InitMemberSlots`](../decomp/readable/recovered/Party_InitMemberSlots_0018d504.c)),
  growth tables `game_assets/tables/syscmn/player_param_*.json`.

---

## 5. Where each editable thing lives

| You want to change | Files | Tool | Guide |
|---|---|---|---|
| Item prices, monster stats, spells, shops, EXP curve | `game_assets/tables/**.json` (42 tables have field names) | `tools/table_edit.py` / Studio **Tables** | [EDITING.md § tables](EDITING.md#tables) |
| Dialogue & messages (792 banks, 68,316 strings) | `game_assets/text/banks/**.json` | `tools/text_tool.py` / Studio **Dialogues** | [EDITING.md § text](EDITING.md#text-and-dialogue) |
| Scripts (events, cutscenes, quests) | `game_assets/scripts/packs/script/<area>/*.nut` | `tools/script_build.py` / Studio **Scripts** | [SCRIPTS.md](SCRIPTS.md) |
| Level object placement | `game_assets/maps/<map>/`, `editor_projects/` | Level Editor (`run_editor.bat`) / `tools/patch_game.py` | [EDITOR.md](EDITOR.md) |
| Textures / models / audio / UI layouts | `game_assets/{textures,models,audio,layouts}/` | `tools/asset_replace.py` (Studio **Export…/Replace…**) | [EDITING.md § replacing](EDITING.md#replacing-assets-in-dqxi-studio) |
| Native code | `src/replacements/*.c` (then `tools/build.py`) | `tools/build_c_replacement.py` | [SOURCE_REPLACEMENT.md](SOURCE_REPLACEMENT.md) |
| Anything → SD card / cartridge / CIA | `mod/` | `tools/export_mod.py` (`run_export.bat`) | [EXPORT.md](EXPORT.md) |

---

## 6. DQXI Studio (`viewer_rs/`)

`run_editor.bat` (level editor) or `run_viewer_rs.bat` (browser). The 13 sections are declared in
`viewer_rs/src/app.rs` (`enum Section`) and implemented by one panel each in
`viewer_rs/src/ui/panels/`:

| Section | Panel | What it does |
|---|---|---|
| Overview | `overview.rs` | project status, quick links |
| Search | `search.rs` | cross-family search |
| Textures | `textures.rs` | BFLIM browse / export / replace |
| Models | `models.rs` | BCH/glTF/OBJ browse, material & texture replace |
| Layouts | `layouts.rs` | BFLYT/BFLAN JSON edit & rebuild |
| Scripts | `scripts.rs` | Squirrel source + assembly, compile, save-to-mod, natives/callers tabs |
| Tables | `tables.rs` | schema-driven spreadsheet, raw columns, save-to-mod |
| Audio | `audio.rs` | OST/jingle browser, replace streams |
| Code | `code.rs` | readable native C browser (falls back to `asm/`) |
| Dialogues | `dialogues.rs` | text banks, search-all, font-metric preview, save-to-mod |
| Maps | `maps.rs` | decoded level scenes |
| Editor | `editor.rs` | the 3D level editor (placement records) |
| Playtest | `playtest.rs` | **Export & Play**: export targets, emulator launch, change list, SD-card copy |

The panels only call the same `tools/*.py` you can run by hand — if a button does something, the
command is in [EDITING.md](EDITING.md).

---

## 7. Trust model — what is solid and what is a hypothesis

Solid (tested on every run):

- the bit-matching build (`python -m tools.build`, verified above); the 223-test suite in
  `tests/run_all.py` (see [progress](../progress/progress.html) and the done reports for the latest run);
- asset round-trips: every named table field (235,769 writes), all 792 text banks, all 769
  scripts rebuild byte-identically;
- the export path: an empty mod rebuilds the retail cartridge byte for byte, and every export is
  re-parsed and hash-checked before `EXPORT OK`.

Hypotheses to check before relying on them:

- **`maybe_` names** (10,295 of 18,327 proposals) carry confidence < 0.5 — read the evidence.
- **Struct field offsets** are inferred; `include/recovered_types.h` declares 992 opaque types
  with *no* field layouts yet.
- A handful of "functions" are Ghidra split fragments or literal-pool words (~200 entries).
- Emulator runs prove an edit executes; only your own console proves hardware acceptance
  ([EXPORT.md §9/§10](EXPORT.md)).

Start from [`progress/progress.html`](../progress/progress.html) whenever you want the current
numbers — it is regenerated after every finished task.
