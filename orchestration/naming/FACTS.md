# Established facts (verified by hand; use them, never contradict them)

## Tools (use these; do NOT walk or grep the asm/ or decomp/ trees, that costs minutes per search)
- `python tools/fn.py 0xADDR [0xADDR2 ...]` - dossier in ~0.5 s: current name, doc/summary, callers and
  callees (named ones first, with current names), vtable neighbours, body. Options: `-b 0` no body,
  `--asm 40` first 40 assembly lines, `--max 30` more callers/callees. `python tools/fn.py --find Camera_`
  lists functions whose current name contains the text.
- A function with MANY callers (dozens) is a shared helper: name it by what it returns/does for all of
  them, not by one caller's subsystem (example: 0x0066A720 has 90 callers, among them InnMessage and
  CreateEffect2D, so a "Battle_Ui_*" name is wrong).
- Call graph limits: direct `bl`/tail-jump only; calls through registers (vtable slots) are not listed.

The dispatcher pastes this file into every naming/refine prompt. Add a fact only after checking it
in the code; give the evidence in one line.

## Ghidra traps
- A stub typed `void` that calls a getter and "discards" the result is usually a getter whose return
  Ghidra dropped. Do not name it Check*/Is*/Has*. Example: `func_00387CA4` is
  `cmp r1,#0xff; ldreq r0,[r0,#0xc4]; addne r0,r0,r1,lsl#2; ldrne r0,[r0,#0x24]; bx lr`, a pure
  slot getter, so the `CheckMenuSlot*` stubs are getters (`maybe_Ui_Manager7C_GetSlotNN`).
- `unaff_rN`, `in_NG`/`in_ZR`/`in_OV`, `coprocessor_*` in a body = damaged decompilation. Keep
  `maybe_` and confidence <= 0.3 unless the disassembly says more.
- Identical bodies at different addresses are common (template copies). Say "same body as 0x...".
- ARM hard-float VFP `s0..s15` args and `s0` float returns are silently dropped or shown as `in_s0` (`0x00607650` `BattleScene_CalcUnitModelSize`, `0x001FA974` `Battle_GetUnitModelSizeIf3D`, `0x0062EF8C` returning `1.0f`/`3.0f` in `s0`, `0x0032A288` taking `float` in `s0`).
- `push {r3, ..., lr}` 8-byte stack-alignment prologues make Ghidra invent fake trailing params (`0x0062943C` and `0x002188F8` take 1 arg not 4; `0x00640BBC` and `0x00646060` take 2 args not 4).
- Registers `r1..r3` forwarded untouched into a callee are dropped from Ghidra's outer signature (`0x002E5C38` forwards `r1..r3` to `0x005F24A4`; `0x003D5648` forwards `r1` to `0x0032A5C4`; `0x0053E9A4` forwards `r1, r2`).
- Thumb `blx` to CRT helpers (`0x00100050` `std_ConstructArray`, `0x00100B74` `wcslen`) is mis-marked `noreturn`, and mid-function split symbols (`0x003C3594` in `0x003C3560`, `0x001664AC` in `0x00166308`) cause fake truncation or `halt_baddata()` — check `asm/` before trusting short/damaged C.

## Items, shop, inventory (NOT text)
- `Item_LookupRecord(ref, id)` resolves ITEM rows; ids 0..0xB3A (0xB3B rows). A loop `i < 0xB3B`
  with it is an item walk. Code whose ids go through it is item code even if named Text_/Glyph/Char.
- Item record: +0x0C kind, +0x11 kind2, +0x18 price, +0x20 flags, +0x29 category, +0x45 stack limit.
- Equipment id ranges: 0xA4..0x9BF and 0xB19..0xB1C (checks `id-0xA4 < 0x91B || id-0xB19 < 4`).
- Bag/storage work = work+0x24A98 (written `+0x24800 +0x298`); **gold = bag+0x28**, cap
  9,999,999 (`0x0098967F`). `Shop_CanAffordItem` (0x00311134) compares gold with price.
- Per-item ownership bitmask at work+0x4B30 (0x168 bytes = 2880 bits); `Item_CountOwnedTypesFromBitmask`.
- `func_0035EB98(work, idx)` = party member record (name at +0xCA, 7 chars).
  Member inventory = 24 u16 item ids at member+0xEC (end 0x11C).
  `func_006292A4(member, slot)` = slot is equipped; `func_006292F0(member, slot)` = equipped item id.
  `maybe_Member_RemoveItemAtSlot`, `maybe_Member_SetItemAtSlot`, `maybe_Member_SwapInventorySlots`.

## Messages
- `Ui_PopupEntry_SpawnFromTable(func_001FD96C(self), &{actor, 0, msgId, 0xFF.., 0xFFFF..}, 1)` queues a
  BATTLE MESSAGE. Not an effect, packet or "unit list".
- `Ui_TextFormat_ReleaseSlot(n, fmt, str)` and `Message_SetArg(n, str, 0)` set message argument n.
  Not debug logging.

## Game work (work+8 -> ...)
- +0x48 UI overlay manager (mode byte +0x281); +0x54 +0x1C / +0x20 actors; +0x5C battle work;
  +0x64 2D effect manager; +0x6C event state (actor slots f_430/f_434, 0x10 bytes); +0x74 scene
  transition controller; +0x7C menu manager (slot getter func_00387CA4); +0x98 game RNG; +0xB4 entry table.
- Battle work: RNG at +0x4218 (`func_001CA474(rng, lo, hi)` = roll in [lo, hi]); party list +0x4260;
  unit lists +0x4254/+0x4270/+0x428C/+0x4298 (stride 0x1C x4); +0x4320 current actor; +0x4244 flag.
- `Os_GetGameWork` and `Game_GetWork` both reach the work; `Game_GetDataManager` the data tables
  (`func_0063E05C(dm, id)` message-ish rows, `func_0063FD24(dm, id)` action rows).

## Poisoned address ranges (verified by disassembly — DO NOT repeat old prefixes)
- `0x00269F64..0x00277700` (was `Ui_TextLayout_*`) is **`BattleAi_*` (Party Tactics / AI Action & Target Evaluator)**: scores up to `0x7C` (`40 spells + 60 skills + 24 items`) `0x14`-byte candidates across 16 `0x9BC`-byte target-unit buckets (`0x0026AE8C` switches tactics `0..6`; `0x0026DF1C` & `0x00271938` return action kind `2`=attack, `4`=skill, `5`=spell, `6`=item; `0x002736BC` compares estimated damage vs `target->vt[+0x90]()` HP).
- `0x00485D90..0x00497900` (was `Text_MeasureTextRun`, `Text_BuildRowForActor*`, `Battle_Message_*`) is **Battle Combat, Agility & MP-Cost Math**: `0x00485D90` rolls free-MP proc (`PartyMember +0xB78/+0xF38`); `0x0048748C` reads `PartyMember +0xDEF/+0xDF0` equip attrs; `0x00487870` resolves spell MP cost (`SpellRecord->u8_2EC` or `-1/-2/-3`) for `0x003CABEC` `Battle_ActionSequence_ConsumeSpellMp`; `0x0048F08C` returns unit Agility in `s0` for `0x0016815C` `Battle_CalcTurnOrderPriority`; `0x00490994` computes attack damage.
- `0x0040A980..0x0040BA78` is **`Model_Equip_*` 3D item bone attachment**, NOT UI labels (`0x0040B7A8` `Model_Equip_AttachItemSlot` reads `ItemRecord->u8_29`, gets `"N_ALL"` bone Euler transform via `0x0040AC1C`, and calls `0x0040A980` `Model_CreateAttachedEffect`).
- `0x0051BA34..0x0051CD40` (was `Sound_Driver_*` / `maybe_Sound_ChannelWork_Ctor`) is **CTR SDK `nn::err` (`err:f` fatal error applet)**: `0x0051CBF8` builds a `0xF80`-byte `FatalErrInfo` (`nn::Result` at `+0x04`), `0x0051BA34`/`0x0051CCF8`/`0x0051CD28` check `0xC8A0CFFC`, and `0x0051CC68` throws it (`0x001D033C` `Fs_ReportFatalError`).
- `0x005047E0` (`Fs_ArchiveStream_ReadAt`, was `maybe_Svc_Object_Write`) **READS** archive bytes into `dstBuf` (`[sp+0x18]`) at `s64 offset` (`r2:r3`) via `0x00116A14` (`__aeabi_memcpy(dst, directBuf+offset, size)`) or `IReadStream::TryRead` for `Fs_Archive_FindDirectory`/`ReadDirectoryEntry`/`FindFile`.

## Data tables, ItemBag & PartyMember details
- `SpellRecord`: `0x0063CFC8(dm, spellId)` (`dm->f_2D4`, wrapper `0x0018C184`), `spellId < 0xCA` (202 spells), stride `0x308`; `+0x208` `u16` flags, `+0x290` `u16` desc msgId, `+0x293` `u8` AI category (`1`=offensive, `0x0026DF1C`), `+0x2EC` `u8` MP cost (`0x00487870`).
- `SkillRecord`: `0x0063D018(dm, skillId)` (`dm->f_2BC`, wrapper `0x0018C1B8`), `skillId < 0xBF` (191 skills), stride `0x100`; `+0xDC` `u8` AI category (`1`=offensive, `0x0026DF1C`), `+0xEE` `u8` MP cost.
- `CharacterRecord`: `0x0063EB94(dm, charaId)` (`dm->f_38C`), stride `0x434` (`0x10D*4`); costume/appearance sub-records (`0x0023D078`) and boolean flag `u8 +0x430` (`0x0062943C`).
- `ItemRecord` extra fields (`0x0061BD4C` / `0x0063CDD8`): `+0x0C` weapon subtype (`0x0F` whip group-target, `0x11` falcon 2-hit, `0x13` boomerang all-target; `0x002736BC`/`0x00274EC0`), `+0x12` `u16` base stat & `+0x14` `u8` variance (`0x0066C470`), `+0x29` equip category (`0..4` 1H `0x0066C5A8`, `5..9` 2H `0x0066C5CC`, `6` claws `0x006297D8`); sort key `*(u16*)0x0063D96C(dm, itemId)` (`0x0066C304`).
- `ItemBag` at `work + 0x24ACC` (`(work+0x24A98)+0x34`): `+0x2B8..+0x274C` stores up to 2,341 4-byte `{u16 itemId, u8 count, u8 flags}` entries terminated by `0xFFFF`, sorted by `0x00611DE4` (`ItemBag_SortEntriesBySortKey`).
- Field trigger records (`id < 0x306` = 774): 8-byte rows in `dm->f_8FC` via `0x0063DCE8`; save bitmask at `(work+0x24A98)+0x5418` tested unset by `0x0066B3B0` and set by `0x006125F0` (`0x0044C454`, `0x0044C760`).
- Tickington / PastPlace Altars (`0x00166308` `Altar_CollectPastPlaceEntries`): 33 pastword rows (`idx < 0x21`) via `0x0063DDCC(*0x007BE310, idx)` (`u8 +0x08` altarId, `u16 +0x0E < 0x138` questId at `(work+0x24A98)+0x5A4E`, visited bits at `(work+0x24A98)+0x88E4`).
- `PartyMember` (`0x12EC` bytes x 31 at `work + 0x04`, `0x0015CE48` / `0x0035EB98`): `+0x14` `u16` HP (`vt[+0x08]` max HP, `0x003D3198`), `+0xC8` `u8` charaId (`0x0062943C`), `+0xCA` `wchar_t[7]` name (`0x003D3198`), `+0xE5` `u8` equipped costume (`0xFF`=none, `0x0023D078`), `+0x11C..+0x121` `s8[6]` equipped inv-slot indices (`-1`=none, `0x001905E4`/`0x00191470`), `+0x19E..+0x1BD` `u16[16]` active states (`0x00629348`), `+0xB78`/`+0xF38` `float` free-MP proc % (`0x00485D90`), `+0xDEF`/`+0xDF0` `s8` hand battle attrs (`0x0048748C`), `+0x1274` `u8[40]` spells (`0x006291EC`/`0x006298E0`), `+0x129C` `u8[60]` skills (`0x00629214`/`0x00629924`).

## Battle, singletons, CTR SDK, nw::lyt & Squirrel
- Battle work `(work+8)->f_5C`: `u8 +0x4244` is 3D/2D mode (`1`=3D, `0`=2D; `0x001FA974` `Battle_GetUnitModelSizeIf3D`, `0x003CC348`); `+0x4330` 3D / `+0x47A0` 2D unit model tables (`0x00607650`); `0x0016815C` (`Battle_CalcTurnOrderPriority`) rolls `(int)(agility * rand[0.51f, 1.0f])` via `0x001CA3E4(&rng_4218)`; `0x00639954(unit, stateId)` tests active battle status.
- Singletons & `(work+8)` pointers: `*0x007BE2F0` `MemoryManager`; `*0x007BE300->f_08` (`+0x48` target scene node, `+0x4C` actor move-override table `0x0028B3D8`/`0x005E812C`, `+0x98` global RNG); `*0x007BE308` `0xE3C8`-byte party/save container (`0x00103594`); `*0x007BE320` `GameWork`; `*0x007BE388` FX manager (`0x0030B5F4`); `(work+8)->f_54` `Field_ObjectManager` (`+0x9C + s8_34*0x0C` class lists, `0x001C7658`); `(work+8)->f_74` camera child `->f_40` and focus offset `+0x84..+0x8C` (`0x002AE144`); `(work+8)->f_88` Field2D manager (`0x0062EF8C`).
- 3DS Horizon SVCs: `svc 0x23` = `svcCloseHandle` & `svc 0x24` = `svcWaitSynchronization1` (`0x005761D8` `Os_ThreadObject_Dtor`, `0x00118170` `Thread::Join`); `svc 0x28` = `svcGetSystemTick` (`0x001112E0`, `0x0010AE64` applet suspend wait on `0x007E7780`).
- PICA200 GPU registers `0x0200..0x02BC` (`0x02B9` `VSH_INPUTBUFFER_CONFIG`, `0x0242` `VSH_NUM_ATTR`, `0x02BB` `VSH_ATTRIBUTES_PERMUTATION`, `0x0200..0x0226` `ATTRIBBUFFERS`, `0x0232` `FIXEDATTRIB_INDEX`) are **Vertex Attribute** commands, NOT lighting (`0x006572F8` `Gfx_Pica_WriteVertexAttrCommands`).
- `nw::lyt::Pane` (`0x005387EC` `Ui_LayoutPane_InitFromRes`): `+0x2C` child list, `+0x80` `char[24]` name, `+0x99` `char[8]` userData; `nw::lyt::Picture + 0xB8` UV quad array (`0x0053E9A4`); Squirrel 3.x `SQFuncState`: `+0x64` `_instructions._size`, `+0x9C` `_lineinfos`, `+0xD0` `_lastline` (`0x001BD1A4` `Script_SqFuncState_AddLineInfos`, `0x001BDD50` `AddInstruction`).

## Misname sweep verified facts (K2_misname_sweep / R_S02)
- `0x0019201C` `Party_Member_RecalculateStats(member)`: full party member stat recalculation pass (HP +0x10, MP +0x12, Atk +0x1A, Def +0x1E, Agi +0x22, Deft +0x26, Charm +0x2A, MMight +0x2C, MMend +0x30; walks 60 skills at +0x129C and 40 spells at +0x1274).
- `0x00190A7C` `Party_Member_AddExp(member, expDelta)`: adds EXP to member+0xDC, clamps at 9,999,999 (`0x0072739C`), checks growth table `0x0063E7F8`, increments level (`member+0xD8`), and calls `0x0019201C`.
- `0x0019180C` `Party_Member_InitFromMasterRecord`: copies 7-wchar name to `member+0xCA`, equips items, and calls `0x0019201C`.
- `0x00109990` `SaveData_ResetSaveWork`: resets GameWork+0x24A98, clearing item ownership mask (`+0x4B30`, 0x168 bytes = 2880 bits) and field trigger bitmask (`+0x5418`, 0x64 bytes).
- `0x0010F448` `SaveData_ResetAllSaveData`: master save reset, calls `Save_BuildSectionList`, zeroes member roster, resets item mask and triggers.
- `0x006D3EA0..0x006D3F54` `Message_FormatArgSlot_Reset*`: clears formatted message argument slots (0..7) on singleton `*0x007AC834` (stride `0x108`).
- `0x0031D178` `Item_ClassifyDualEquipCategory`: checks equip ranges `0xA4..0x9BF` & `0xB19..0xB1C`, inspects `ItemRecord->u8_29` for dual-wield animation style.
- `0x0035F38C` `Party_Member_SyncOwnedItemsToBitmask`: walks 24 inventory items at `member+0xEC`, marks owned bits at `(work+0x24A98)+0x4B30`.
- `0x00491270` `Battle_CalcRandomDamageVariance`: computes +/- damage spread using Battle RNG `func_001CA474(&rng_4218)` into float `s0`.
- `0x0026AE8C` `BattleAi_ExecuteTacticsDecision`: master party tactics switch (modes 0..6) evaluating candidate action utilities.

