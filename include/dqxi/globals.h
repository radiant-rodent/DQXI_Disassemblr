#ifndef DQXI_DQXI_GLOBALS_H
#define DQXI_DQXI_GLOBALS_H

#include "structs.h"

/* Named data objects of the retail executable. Each comment gives the
 * address in the original image and what the object is for. */

/* --- Action --- */
extern void* g_stateSequence62Vtable[7];             /* 0x0075AAEC conf 0.65: Vtable of the std_StateSequence62 animation state machine (7 words: a null complete-destructor slot, the delete stub 0x0 */
extern void* g_flwActionVtable[11];                  /* 0x0075DC98 conf 0.55: Vtable of the small 44-byte (0x2C) action descriptor built by maybe_Action_InstallVtable for slot 5 of a field actor's a */
extern void* g_followTaskVtable[11];                 /* 0x0075DCCC conf 0.60: Vtable of the 0x58-byte behaviour task whose action name is "follow": every constructor that allocates it passes that st */
extern void* g_actionBaseVtable[11];                 /* 0x0075DD34 conf 0.60: Vtable of the common action base class between Gfx_ObjectDesc and the concrete action classes: maybe_Action_CtorBase ins */
extern void* g_actionSubclass4AnimVtable[23];        /* 0x0075FCFC conf 0.55: Vtable of the action subclass built by maybe_Action_Subclass4Anim_Ctor: a 0x114-byte action object with an animation sta */

/* --- Actor --- */
extern char* g_actorDefaultAnimName;                 /* 0x00725900 conf 0.60: Default animation-name pointer handed to the 2-D actor / model-record loaders (func_002D1258): the retail value is 0x007 */
extern u8 g_actorStateAnimIdTable[8];                /* 0x00725904 conf 0.70: Per-animation-state sprite pattern ids for 2-D actors (retail bytes 0xFF,03,05,05,05,06,04,00). 0xFF means "keep the pre */
extern u32 g_actor2DSpriteClassDesc[34];             /* 0x00725B1C conf 0.55: {create function, vtable} class descriptor for the 2-D sprite actor built by maybe_Actor2D_CreateSpriteWithDefaults: wor */
extern u8 g_actor2DStatePatternTable[16];            /* 0x00726064 conf 0.75: Per-state sprite pattern pairs (state*2 -> [pattern index, secondary pattern byte]) used by Actor2D_SetPatternForState:  */
extern u32 maybe_g_actorActionDefaults[8];           /* 0x007266E0 conf 0.45: Default action-table block read while maybe_Actor_CreateActionTable builds the actor's action list (entries used through */
extern f32 g_actorModelScaleLarge;                   /* 0x007277F4 conf 0.60: Model scale constant 4.0f (0x40800000) stored into an actor's f_1D4 in maybe_Actor_UpdateActionState (player states 1 an */
extern f32 g_actorModelScaleMedium;                  /* 0x007277F8 conf 0.55: Model scale constant 2.0f (0x40000000), the f_1D4 value used when player state 1 has the scene-work byte at +0x27C clear */
extern f32 g_actorModelScaleMediumAlt;               /* 0x007277FC conf 0.55: Second 2.0f (0x40000000) model-scale constant: the default f_1D4 value and the divisor in maybe_Actor_UpdateModelOnState */
extern u8 maybe_g_rodata_74756e[4];                  /* 0x0074756E conf 0.10: NOT a real global: the literal slots that "reference" this address are the inline strings "nut" at 0x00177D20 / 0x001802 */
extern void* g_partyStatusVtable[4];                 /* 0x00759AD0 conf 0.65: Dispatch table installed on a Ui_PartyStatus / actor status instance: slots Ui_PartyStatus_Reset, DeleteDtor and Refresh */
extern void* g_actorActionTableStateVtable[7];       /* 0x0075A8D0 conf 0.55: Vtable of the state-sequence object that maybe_Actor_CreateActionTable installs on the actor's action table (structs.jso */
extern void* g_actorActionSetStateVtable[7];         /* 0x0075AA80 conf 0.50: Vtable for the state-sequence member of the four-slot action set built by maybe_Actor_ActionSet4_Ctor (structs.json clas */
extern void* maybe_g_actor2DStateVtable[7];          /* 0x0075ADE0 conf 0.45: Vtable installed by maybe_Actor2D_InitFromRecord on the 2-D actor state object (structs.json class std_StateSequence13:  */
extern u32 g_actor2DSpanGroupClassDesc[34];          /* 0x0075BBDC conf 0.50: {create function 0x00633618, vtable} class descriptor used by maybe_Actor2D_InitSpanGroupB: the vtable (Gfx_Sprite_Creat */
extern u32 g_actor2DNodeClassDesc[26];               /* 0x0075BC9C conf 0.50: {create function 0x00633624, vtable} class descriptor installed by maybe_Actor2D_CtorBase; the vtable carries the Gfx_No */
extern void* g_actorStatusBlockVtable[4];            /* 0x0075CE50 conf 0.65: Vtable of an Actor_StatusBlock instance (slots 0x0027A7F0, Ui_WindowManager_DeletingDtor, 0x0027A4E0) followed at +0x10  */
extern u32 g_actor2DSpriteNodeClassDesc[34];         /* 0x0075D888 conf 0.60: {create function 0x0063A6B4, vtable} class descriptor for the 2-D sprite-node class built by Actor2D_SpriteNode_Ctor: vt */
extern void* g_actorActionVtable[12];                /* 0x0075DD00 conf 0.70: Base vtable of the Actor_Action class (11 slots: 0x00294C24, the deleting dtor, and the init/end/update hooks at +8..+0x */
extern void* g_actorActionSet4WindowVtable[12];      /* 0x0075EA70 conf 0.60: Vtable installed at +0 of the four-slot action-set object constructed by maybe_Actor_ActionSet4_Ctor (structs.json class */
extern u32 g_actor2DSpriteNodeClassDescB[34];        /* 0x0075F098 conf 0.60: Second {create function 0x0063B9D8, vtable} descriptor for the 2-D sprite-node class, installed by Actor2D_SpriteNode_Ct */
extern void* g_actorActionCurveMoveVtable[11];       /* 0x0075FC60 conf 0.70: Vtable for action-table entry type 2 (curve/jump move) built by maybe_Actor_Action_CreateJump: slots maybe_Actor_Action_ */
extern void* g_actorActionCurveMove2Vtable[11];      /* 0x0075FC94 conf 0.70: Vtable for action-table entry type 4 (second curve/jump move), created by maybe_Actor_Action_CreateJump2; slots include  */
extern void* g_actorActionMoveVtable[11];            /* 0x0075FCC8 conf 0.70: Vtable for the default action-table entry (opcode 0, no parameters) created by Actor_Action_CreateMove; slots are DtorDe */
extern void* g_fieldActionPitfallVtable[11];         /* 0x0075FDD0 conf 0.55: Vtable used by maybe_Actor_StartBehaviourState for the "pitfall" field action created through maybe_Action_CtorBase(..., */
extern void* g_fieldActionPitfallFallVtable[11];     /* 0x0075FE04 conf 0.55: Vtable of the pitfall/idle field action created by maybe_Actor_Action_CreateIdle; slots include Field_Action_Pitfall_Dto */
extern void* g_fieldActionNutTreeVtable[11];         /* 0x0075FE6C conf 0.55: Vtable of the "nut tree" field action created by maybe_Actor_Action_CreateWithData; the subclass hooks at +0x38/+0x3C ar */
extern void* g_fieldActionNutTreeVtableB[11];        /* 0x0075FEA0 conf 0.55: Second nut-tree action vtable, for the type-0x1E entry built by maybe_Actor_Action_CreateType30; slots include NutTree_B */
extern u32 g_actor2DSceneObjectClassDesc[34];        /* 0x00764D20 conf 0.55: {create function 0x00643608, vtable} class descriptor installed by maybe_Actor2D_Ctor: vtable includes Gfx_Sprite_Create */
extern u32 g_actor2DNodeClassDescB[26];              /* 0x00764DDC conf 0.50: {create function 0x00643614, vtable} descriptor installed by maybe_Actor2D_CtorWithSprite; the vtable carries the Gfx_No */
extern void* g_fieldActorActionMoveVtable[11];       /* 0x00768780 conf 0.60: Vtable of the field actor move-to action created by maybe_ActorAction_CreateMoveAction; slots include CacheActorSnapshot */
extern void* g_fieldActorActionMoveVtableB[11];      /* 0x007687B4 conf 0.60: Second move-action vtable, installed by maybe_ActorAction_CreateMoveActionB; slots are DtorDeleteC, BeginMove, EndMove a */
extern void* g_monsterBehaviourActionVtable[11];     /* 0x00768918 conf 0.50: Vtable installed by the actor state-chain helpers (maybe_Actor_EndStateChain / EndStateChainEx / StartStateOne); slots i */
extern void* g_fieldActorActionAnimResourceVtable[11]; /* 0x0076DF9C conf 0.55: Vtable of the animation-resource actor action created by maybe_Actor_CreateTaskChainB; slots are the anim-resource delet */
extern void* g_fieldActorBehaviourVtable[11];        /* 0x0076DFD0 conf 0.55: Vtable of the actor behaviour/step object installed by maybe_Actor_StartBehaviourState; slots include Field_ActorBehavio */
extern void* g_actorActionTableEntryVtable[11];      /* 0x007716E0 conf 0.60: Vtable of an actor action-table entry built by Actor_Action_TableEntryCtor; slots include InitState, End, UpdateState an */
extern void* g_actorActionTableEntryVtableB[11];     /* 0x00771714 conf 0.60: Second action-table-entry vtable, installed by Actor_Action_TableEntryCtorB; slots include maybe_Field_ActorAction_DtorB */
extern void* g_fieldActorStepSoundActionVtable[16];  /* 0x00771828 conf 0.60: Vtable of the foot-step sound action created by Actor_Action_SkullRunCtor; slots include Field_ActorStepSoundAction_Dtor */
extern void* g_fieldSkullRunActionVtable[11];        /* 0x00771870 conf 0.65: Vtable of the running-skull action class constructed by Actor_Action_BaseCtor; slots are Field_SkullRunAction_Dtor, Skul */
extern u32 maybe_g_fieldPartyObjectClassDesc[24];    /* 0x007722F0 conf 0.40: Class descriptor installed by maybe_Actor_Object_Ctor (word 0 doubles as the type tag); the following words are a mixed  */
extern void* g_actorActionIvyBaseVtable[11];         /* 0x00775690 conf 0.50: Base vtable used by maybe_ActorAction_Noop_Ctor before a subclass overwrites it; slots are IvyMove_DtorDelete, IvyMove_S */
extern void* g_actorActionIvyMoveVtable[11];         /* 0x007756C4 conf 0.70: Vtable of the Ivy-move actor action constructed by ActorAction_IvyMove_Ctor; slots are IvyMove_Start, Finish, Update and */
extern void* g_actorHandleRefVtable[9];              /* 0x0077630C conf 0.70: Vtable of the actor handle-reference object built by maybe_Actor_HandleRef_Ctor (8 slots: dtor, getter, Field_HandleRef_ */
extern void* g_fieldHandleRefVtable[9];              /* 0x00776334 conf 0.70: Vtable of the extended field handle reference built by Actor_HandleRefEx_Ctor (dtor, CallGetter, Field_HandleRef_SetValu */
extern void* g_fieldActorActionAttractVtable[11];    /* 0x00776B80 conf 0.50: Vtable of the whale/attract actor action created by maybe_Actor_CreateTaskChain; slots include WhaleStart_DtorDelete, Se */
extern void* g_actorActionTrailVtable[11];           /* 0x007787A4 conf 0.70: Vtable of the trail action created by maybe_Actor_Action_Trail_Ctor; slots are Trail_Dtor, Trail_Start, Trail_AddSample  */
extern void* g_actorActionTrailVtableB[11];          /* 0x007787D8 conf 0.65: Second trail-action vtable used by maybe_Actor_Action_TrailB_Ctor; slots are Trail_InitSamples, Trail_End, Trail_Distrib */
extern void* g_actorActionRiremitoVtable[11];        /* 0x0077880C conf 0.70: Vtable of the Riremito (teleport) actor action constructed by Actor_Action_Riremito_Ctor; slots are Riremito_Dtor, Start */
extern void* g_actorActionWhaleStartVtable[11];      /* 0x00778840 conf 0.65: Vtable of the whale-start actor action constructed by Actor_Action_WhaleStart_Ctor; slots are WhaleStart_Start/End and t */
extern void* g_actorActionIvyNutVtable[11];          /* 0x007788A8 conf 0.70: Vtable of the IvyNut action constructed by maybe_Actor_Action_IvyNut_Ctor; slots are IvyNut_Dtor, IvyDown_Start, IvyNut_ */
extern void* g_actorActionLadderClimbVtable[11];     /* 0x0077A204 conf 0.60: Vtable of the ladder-climb action used by maybe_Actor_StartStateOne/EndStateChain; slots are LadderClimb_Dtor, End, Upda */
extern void* g_actorActionGrabNutVtable[11];         /* 0x0077A238 conf 0.70: Vtable of the GrabNut action constructed by maybe_Actor_Action_GrabNut_Ctor; slots are GrabNut_Dtor, Start, End, Update  */
extern void* maybe_g_eventGimmickVtable[11];         /* 0x0077C3D0 conf 0.45: Vtable installed by maybe_Actor_ActionEntry_Ctor; its slots are the Ui_ScreenSlideAnim start/stop/update pair at +8..+0x */
extern void* maybe_g_actorWarpActionVtable[11];      /* 0x0077D198 conf 0.45: Action vtable shared by Actor_Action_WhaleStart_Ctor and Field_ActorAction_RuraStart_Ctor: the Rura ctor also copies a 1 */
extern u8 maybe_g_emptyTextLayoutTemplate[248];      /* 0x00782790 conf 0.30: 248-byte all-zero .rodata block used as the initial value/magic area of temporary text-layout and sprite-span structures */
extern u32 g_actorMotionTableInitFlag;               /* 0x007A372C conf 0.60: One-time-initialisation flag for the actor default-motion table: byte 0 is tested by Actor_GetDefaultMotionId and func_0 */
extern u32 g_actorResolveCache[2];                   /* 0x007A37B8 conf 0.55: Two-word lazy-init cache used by Actor_ResolveHandleFast / WithTypeCheck: word 0 is the one-time init flag (tested as bi */
extern f32 maybe_g_actorRotationSpeedScale;          /* 0x007A3ED0 conf 0.40: Runtime-initialised float scale multiplied into the per-frame rotation delta by the running-skull and spin action update */
extern f32 maybe_g_actorDragonJumpSpeedScale;        /* 0x007A3F44 conf 0.40: Runtime-initialised float multiplier for the dragon-jump forward speed; used only when the action's actor has flag f_3F1 */
extern f32 maybe_g_actorEggJumpSpeedScale;           /* 0x007A3F4C conf 0.40: Runtime-initialised float factor used by Actor_Action_EggJumpUpdate when the actor is moving faster than 1.0: the result */
extern u32 g_playerActor2DClassId;                   /* 0x007A3F6C conf 0.65: Class/type id assigned to the PlayerActor2D class at startup: Field_RegisterActorClass_PlayerActor2D writes its value he */
extern u32 g_playerActor3DDefaultParams[10];         /* 0x007A3F7C conf 0.60: Default parameter block of the PlayerActor3D class: floats 0.0, 1.5, 0.05, 0.98 followed by the id/flag words (the regis */
extern f32 maybe_g_actorBehaviourLastValue;          /* 0x007A3F90 conf 0.35: Single shared float scratch word: actor behaviour setup and model-preview code store a parameter here and Sound_Emitter_ */
extern u8 maybe_g_uiBusyFlag;                        /* 0x007A58F8 conf 0.45: Shared "UI/menu busy" gate: non-zero suppresses actor height adjustment, party-status value changes and battle balloon s */
extern u32 g_globalMutexObject;                      /* 0x007AE4E0 conf 0.55: Opaque global OS lock object: its address is passed to Os_MutexLock / Os_SetSyncState and the semaphore calls, and it se */
extern u32 g_actor2DHandleTable[128];                /* 0x007B7D90 conf 0.80: 64-entry generational actor handle table (8 bytes per entry: object pointer + generation) used by the script-facing Acto */
extern u16 g_actor2DDebugFormatInt[3];               /* 0x007BE738 conf 0.65: Wide debug format string L"%d" (bytes 25 00 64 00 00 00) used by maybe_Actor2D_DebugPrintSpriteInfo via maybe_Text_Reset */
extern u16 g_actor2DDebugFormatString[4];            /* 0x007BE73E conf 0.65: Wide debug format string L"%ls" used by maybe_Actor2D_DebugPrintSpriteInfo when releasing text slot 2 on the debug text  */
extern char g_actor2DSpritePartName[7];              /* 0x007BE7B5 conf 0.65: The literal part name "sprite" (NUL-terminated) copied into a FixedString15 when Actor2D_CreateWithAnimInstanceA builds  */
extern char g_actor2DSpritePartNameB[7];             /* 0x007BE833 conf 0.65: Second copy of the literal part name "sprite", used by Actor2D_CreateWithAnimInstanceB. */
extern u16 g_actor2DSpanFormatString[4];             /* 0x007BE894 conf 0.60: Wide L"%ls" format string used by maybe_Actor2D_DebugPrintSpanInfo when it releases text slots 2 and 3 for the two sprit */
extern u16 g_actor2DSpanFormatInt[3];                /* 0x007BE89C conf 0.60: Wide L"%d" format string used by maybe_Actor2D_DebugPrintSpanInfo when resetting debug text channel 8 for span self->f_2 */
extern u16 g_actor2DSpanPairFormatString[4];         /* 0x007BE8A2 conf 0.65: Wide L"%ls" format string used by maybe_Actor2D_DebugPrintSpanPairInfo to print each of the two span names on debug text */
extern u32 g_actorDefaultMotionTable[18];            /* 0x007C4244 conf 0.70: Default motion-id table for field actors: two 0x24-byte records; Actor_GetDefaultMotionId returns the id at +4 of the fi */
extern u32 maybe_g_actorBookIdClassTokenA;           /* 0x007C443C conf 0.40: Class-type token for an actor class whose region-book id is the byte at +0x297; matched by ActorGetRegionBookID and by m */
extern u32 g_actorRttiTokenC;                        /* 0x007C44F0 conf 0.60: Class-type token specialised by Actor_FindByHandleAndRttiC: the function resolves a handle through the global actor tabl */
extern u32 maybe_g_actor2DSpriteClassToken;          /* 0x007C4630 conf 0.45: Class-type token for the 2-D sprite actor class: maybe_Actor2D_CreateSpriteWithDefaults returns the new object only when */
extern u32 g_actorRttiTokenB;                        /* 0x007C4860 conf 0.60: Class-type token specialised by Actor_FindByHandleAndRttiB: resolves a generational actor handle and returns the object  */
extern u32 maybe_g_actorBookIdClassTokenD;           /* 0x007C4928 conf 0.40: Class-type token used by ActorGetRegionBookID (returns the field f_B2 for this class) and by maybe_Actor_GetIndexedValue */
extern u32 g_eggJumpTargetClassToken;                /* 0x007C4A7C conf 0.55: Class-type token for the actor class that EggJumpUpdate treats as its landing target: after resolving the actor handle a */
extern u32 g_dragonJumpTargetClassToken;             /* 0x007C4AA4 conf 0.55: Class-type token for the actor class DragonJump_Update marks when the jump starts: on a class-chain match it clears word */
extern u32 g_gmMiniGameBoot3DClassRecord[5];         /* 0x007C4B6C conf 0.65: BSS class-registration record for GmMiniGameBoot3DActor: Field_RegisterActorClass_GmMiniGameBoot3D fills the self/class  */
extern u8 maybe_g_sharedActionPacketBuffer[1024];    /* 0x007CCAA0 conf 0.45: BSS scratch buffer: Actor_ActionSeq_BeginIfReady builds a 0x11C-byte action-sequence request here (handle at +0, u16 at  */

/* --- Actor2DTurnTarget --- */
extern f32 g_actor2DDefaultTurnDir[2];               /* 0x007AE744 conf 0.85: Default 2D direction vector (two floats: X, Y) loaded when turning toward a locator or target whose delta vector length  */

/* --- ActorGetJumpMapID --- */
extern u32 g_gmMermaidHarp2DClassRecord[5];          /* 0x007C45CC conf 0.55: BSS class-registration record used as the class id for GmMermaidHarp2D: Ui_CreateStaticTextWidgets passes its address wi */
extern u32 g_actorJumpInfoClassToken;                /* 0x007C49B4 conf 0.55: Class-type token for the actor class that supplies jump target data: ActorGetJumpMapID returns the u16 at table_base+obj */

/* --- ActorGetRegionBookID --- */
extern u32 g_fieldTwoPartObjClassToken;              /* 0x007C4400 conf 0.60: Class-type token: its address is the RTTI/class id compared against the first vtable slot. ActorGetRegionBookID matches  */
extern u32 maybe_g_actorBookIdClassTokenB;           /* 0x007C4518 conf 0.35: Class-type token used both by ActorGetRegionBookID and by maybe_Ui_Actor_CalcOverlayPosition when projecting an actor ov */
extern u32 maybe_g_actorBookIdClassTokenC;           /* 0x007C452C conf 0.35: Class-type token used by ActorGetRegionBookID (calls func_00640DF4 for this class) and by maybe_Ui_Actor_CalcOverlayPosi */
extern u32 g_gmWaterfall2DClassRecord[5];            /* 0x007C46E4 conf 0.65: BSS class-registration record for GmWaterfall2D: Field_RegisterActorClass_GmWaterfall2D writes the self-pointer links at */
extern u32 g_gfxModelPartClassToken;                 /* 0x007C48EC conf 0.55: Class-type token for Gfx_ModelPart: ActorGetRegionBookID matches it and returns the book byte at +0x315 or +0x316, and m */

/* --- ActorSetEnableFollow --- */
extern u8 g_actorFollowSlotIndices[8];               /* 0x00728A4C conf 0.70: The eight animation/attach slot indices {1,2,3,27,4,5,6,7} that ActorSetEnableFollow touches when arg1 == 0xFF ("all"):  */

/* --- Anim --- */
extern u32 g_animTemplateTable[16];                  /* 0x00725458 conf 0.55: 64-byte rodata array (16 u32 words) referenced as a template by Anim_Instance_ApplyTemplate; accessed at indices 0xe and */
extern u32 maybe_g_motionFormatIndex;                /* 0x0072D754 conf 0.45: Pointer/index used by Anim_FormatMotionPackPath to compare motion IDs against the motion format table at 0x00636704. Zer */
extern void* maybe_g_sequenceBasePointer;            /* 0x0075A79C conf 0.45: Zero-initialised rodata pointer installed as the base vtable/pointer by Anim_Sequence_CtorBase (`*self = g_0010b504`). L */
extern void* maybe_g_spriteInstanceBase;             /* 0x0075AB34 conf 0.40: Zero-initialised rodata pointer written into sprite instances by Anim_Instance_CtorSprite. Points to 0x002D2034 (code/da */
extern void* maybe_g_modelLoadTemplate;              /* 0x0075CC90 conf 0.40: Zero-initialised pointer assigned by Anim_ModelLoad_ByName (`*result = g_004d2a94`). Points to the model-load descriptor */
extern void* maybe_g_instanceCtorBase;               /* 0x0075D3E8 conf 0.35: Zero-initialised rodata pointer loaded as a local base by maybe_Anim_Instance_Ctor (`local_68 = g_003dc7ac`). Points to  */
extern void* g_objectBaseCtorTable;                  /* 0x0075D434 conf 0.50: Pointer to the object-base constructor descriptor/code at 0x0028B6F4, installed by maybe_Anim_ObjectBaseCtor (`*puVar2 = */
extern void* g_clipSpawnResourceTable[4];            /* 0x0075E360 conf 0.55: Shared resource pointer table (4 words, 3 literals: 0x0029EAF8, 0x0029F23C, 0x0029F2A4) used by Anim_Clip_Start and rela */
extern void* g_instanceDtorTable;                    /* 0x00760568 conf 0.50: Pointer to the instance destructor/template at 0x002D11EC, installed by maybe_Anim_Instance_Dtor. Initial value points t */
extern void* maybe_g_spriteInstanceCtorTable;        /* 0x00760578 conf 0.40: Zero-initialised pointer assigned by Anim_Instance_CtorSprite (`*puVar2 = g_002d2030`). Points to the sprite constructor */
extern void* maybe_g_clipSlotEightTable;             /* 0x007615A4 conf 0.40: Zero-initialised pointer assigned by maybe_Anim_ClipSlot_SetEight (`uVar3 = g_002ebe34`). Points to 0x002EBE34. */
extern void* maybe_g_clipSlotTwoTable;               /* 0x0076160C conf 0.40: Zero-initialised pointer assigned by maybe_Anim_ClipSlot_SetTwo (`uVar2 = g_002ebf38`). Points to 0x002EBF38. */
extern void* g_beeJumpParamsTable;                   /* 0x007628EC conf 0.50: Pointer assigned by Anim_SetBeeJumpParams (`*result = g_003017c0`). Points to the bee-jump parameter descriptor at 0x003 */
extern void* maybe_g_objectCtorTable;                /* 0x00762920 conf 0.35: Zero-initialised pointer assigned by maybe_Anim_ObjectCtor (`uVar2 = g_00301a90`). Points to 0x00301A90. */
extern void* maybe_g_createVariantATable;            /* 0x007629E4 conf 0.35: Zero-initialised pointer assigned by maybe_Anim_CreateVariantA (`*puVar1 = g_00301e30`). Points to 0x00301E30. */
extern void* maybe_g_createVariantBTable;            /* 0x00762A50 conf 0.35: Zero-initialised pointer assigned by maybe_Anim_CreateVariantB (`uVar1 = g_00301fa4`). Points to 0x00301FA4. */
extern void* maybe_g_createVariantCTable;            /* 0x00762AB8 conf 0.35: Zero-initialised pointer assigned by maybe_Anim_CreateVariantC (`uVar3 = g_00302468`). Points to 0x00302468. */
extern void* maybe_g_createVariantDTable;            /* 0x00762AFC conf 0.40: Zero-initialised pointer assigned by maybe_Anim_CreateVariantD (`uVar3 = g_00302c84`). Points to 0x00302C84. */
extern void* maybe_g_createVariantETable;            /* 0x00762B40 conf 0.35: Zero-initialised pointer assigned by maybe_Anim_CreateVariantE (`*puVar3 = g_00303464`). Points to 0x00303464. */
extern void* maybe_g_createVariantFTable;            /* 0x00762B74 conf 0.35: Zero-initialised pointer assigned by maybe_Anim_CreateVariantF (`*result = g_0030404c`). Points to 0x0030404C. */
extern void* maybe_g_createVariantDAltTable;         /* 0x00775338 conf 0.35: Zero-initialised pointer written to by maybe_Anim_CreateVariantD (`result[0x14] = g_00302c88`). Points to 0x00302C88 (al */
extern void* g_animClipCtorTable;                    /* 0x007815D8 conf 0.55: Pointer to the animation-clip constructor descriptor/code at 0x0054031C, installed by Anim_AnimClip_Ctor. Initial value  */
extern void* g_motionPackPathTable;                  /* 0x00782564 conf 0.50: Pointer to the motion-pack format descriptor/code at 0x00636738, loaded by Anim_FormatMotionPackPath (`local_24 = g_0063 */
extern void* g_sharedAnimationResourceTable[3];      /* 0x00782574 conf 0.60: High-use shared pointer/resource table (23 uses, 22 functions, initial 0x00572C4C). Points to animation/model resource d */
extern void* maybe_g_attachTrackUpdateTable[2];      /* 0x007A2D60 conf 0.45: Data-section pointer pair used by Anim_UpdateAttachTrack and Anim_UpdateModelInstance (literals 0x005ACAA4 and 0x005AD1C */
extern char* g_effectPathString;                     /* 0x007A5CFC conf 0.70: Data pointer to the NUL-terminated string "Effectpath" (pointee_string=Effectpath, initial value 0x00784824 points to .r */
extern u8 g_clipSpawnActiveFlag;                     /* 0x007A6888 conf 0.50: Single-byte dereference flag in .data: non-zero when the animation clip spawn pointer at 0x0029EAF4 is active (used by A */
extern void* maybe_g_modelLoadDescriptorA;           /* 0x007B6D70 conf 0.40: Zero-initialised data pointer assigned by Anim_ModelLoad_ByName (`puVar1 = g_004d2a88`). Points to 0x004D2A88. */
extern void* maybe_g_modelLoadDescriptorB;           /* 0x007B6D74 conf 0.40: Zero-initialised data pointer assigned by Anim_ModelLoad_ByName (`piVar4 = g_004d2978`). Points to 0x004D2978. */

/* --- Battle --- */
extern u32 g_battleSceneBackgroundModelSet[9];       /* 0x00726A7C conf 0.55: Battle-background model/animation set: +4 points at the animation pack 'bg.ani', +8/+0xc/+0x10 at the models 'm210','m21 */
extern u32 g_battleUnitVariantSlotDefaults;          /* 0x00726AA0 conf 0.50: Constant block copied into the local two-slot unit-variant list by maybe_BattleScene_UpdateUnitList0: bytes 0xFFFF 0xFFF */
extern f32 g_battleTargetMarkerLayoutTable;          /* 0x00726EA4 conf 0.50: First float (1.0) of the 26-float target-marker layout table that runs from 0x00726EA4 to 0x00726F0C (1.0, 2.5, then rep */
extern f32 maybe_g_battleActionSceneDistanceThreshold; /* 0x00726EA8 conf 0.40: Float 2.5 (entry 1 of the target-marker float table) used as a distance threshold by maybe_Battle_UpdateActionScene: the */
extern f32 g_battleTargetMarkerOffsets[24];          /* 0x00726EAC conf 0.55: Per-target-slot float offsets (330,-310,130,210, 250,70,340,160 ...) inside the marker-layout table; Battle_Ui_UpdateTar */
extern u32 maybe_g_battleActorActionEffectDesc[12];  /* 0x00726F0C conf 0.35: Zero-initialised descriptor block used by Battle_ActorAction_UpdateSubCommands, maybe_Battle_ActorAction_UpdateReaction  */
extern u32 g_battleUiScrollAnimTable[18];            /* 0x00726F48 conf 0.55: Table driving the battle UI scroll/slide animation: the first 8 bytes are per-slot byte counters (0A 05 05 02 02 05 0A 0 */
extern u32 g_battleSceneUnitModelSet[16];            /* 0x00727098 conf 0.50: Model-name set (m210 / m210_0 / m210_1 at +4/+8/+0xc) plus transform data used by BattleScene_BindUnitModelResources: it */
extern void* g_battleCutsceneAnimObjectVtable[6];    /* 0x00727214 conf 0.55: Virtual method table installed on the battle cutscene anim object by maybe_Battle_CutsceneObject_Init; slot 1 is maybe_A */
extern s32 g_battleActionRangeClampValue;            /* 0x007273A0 conf 0.55: Clamp value 99999 (0x1869F) returned by maybe_Battle_Unit_CalcActionRange when the summed per-slot range is below the li */
extern u32 g_battleConditionParamTable[2];           /* 0x0072866C conf 0.50: Packed condition-parameter table: the first two words are 0x100/0x100, followed by byte pairs/flags (12 12 FF FF, 13 12  */
extern char* g_battleTextWindowModelNames[37];       /* 0x0072AD60 conf 0.70: 37-entry (0x94 byte) table of battle enemy model file names, 'n4101a.bch' ... 'n4103o.bch'. Battle_TextWindow_LoadTextur */
extern void* g_battleManagerVtable[12];              /* 0x00758308 conf 0.80: Virtual method table of the Battle manager object (slot 0 is maybe_Battle_Destroy); Battle_Ctor stores it at battle[0]:  */
extern void* g_battleActionModelVtable[12];          /* 0x00759948 conf 0.65: Virtual method table of the Battle_ActionModel object (slot 2 is Battle_ActionModel_InitFromDescriptor). Installed/destr */
extern void* g_battleCutsceneObjectVtable[5];        /* 0x00759DC0 conf 0.55: Virtual method table of the battle cutscene object created by maybe_Battle_CutsceneObject_Init (slot 1 maybe_Actor_Check */
extern void* g_battleTextWindowPaneStateSequenceVtable[7]; /* 0x0075AB58 conf 0.60: Virtual method table of the std::StateSequence object embedded in the battle text-window pane (slot 1 std_StateSequence6 */
extern void* g_battleTextWindowChildWidgetVtableA[16]; /* 0x0075D2A8 conf 0.50: Virtual method table of a child widget created by maybe_Battle_TextWindow_CtorChildren (slot 2 is Ui_Widget_ReleaseSub,  */
extern void* g_battleActionAnimEntryVtable[10];      /* 0x0075E744 conf 0.70: Virtual method table of the Battle action-animation entry (one row of the 'battleact' action list). Slot 1 is the list-r */
extern void* g_battlePopupEntryVtable[12];           /* 0x0075E91C conf 0.80: Virtual method table of Battle_PopupEntry (the pooled damage/heal popup object, 464 bytes; class recovered in structs.js */
extern void* g_battleActionSubObjectVtableA[11];     /* 0x00760D64 conf 0.60: Virtual method table of the action sub-object built by maybe_Battle_ActionSubObject_CreateA (slot 1 maybe_Battle_UnitDis */
extern void* g_battleActionSubObjectVtableB[11];     /* 0x00760D98 conf 0.60: Virtual method table of the action sub-object built by maybe_Battle_ActionSubObject_CreateB (slot 2 maybe_Battle_ActionS */
extern void* g_battleActionSubObjectVtableC[11];     /* 0x00760DCC conf 0.60: Virtual method table of the action sub-object built by maybe_Battle_ActionSubObject_CreateC (slot 1 maybe_Battle_Unit_De */
extern void* g_battleActionAnimState3Vtable[11];     /* 0x00760E00 conf 0.55: Virtual method table of the object placed in slot 3 of the 'battleact' action table by Battle_ActionAnimWindow_Init (its */
extern void* g_battlePopupObjectVtable[16];          /* 0x00760FD4 conf 0.60: Virtual method table of the 3D battle popup object created by Battle_PopupObject_Create (slot 2 Battle_PopupWindow_Relea */
extern void* g_battlePopup3DGaugeBarVtable[16];      /* 0x007613AC conf 0.50: Virtual method table of the gauge-bar sub-widget used by the 3D popup (slot 1 maybe_Ui_GaugeBarWindow_Ctor+0x70, slot 8  */
extern void* g_battleTextWindowVtable[10];           /* 0x00761474 conf 0.80: Virtual method table of Battle_TextWindow (class recovered in structs.json, 2144 bytes); installed by maybe_Battle_TextW */
extern void* g_battleAnimWindowVtable[16];           /* 0x00761640 conf 0.90: Virtual method table of Battle_AnimWindow (class recovered in structs.json, 636 bytes); slot 1 Battle_AnimWindow_Release */
extern void* g_battleActionSubObjectVtableD[11];     /* 0x00763978 conf 0.60: Virtual method table of the action sub-object built by maybe_Battle_ActionSubObject_CreateD (slot 1 maybe_Battle_Action_ */
extern void* g_battleActionSubObjectVtableE[11];     /* 0x007639AC conf 0.60: Virtual method table of the action sub-object built by maybe_Battle_ActionSubObject_CreateE (slot 2 Battle_Action_CalcTa */
extern void* g_battleActionAnimState4Vtable[11];     /* 0x007639E0 conf 0.55: Virtual method table of the object placed in slot 4 of the 'battleact' action table by Battle_ActionAnimWindow_Init (slo */
extern void* g_battleActionSubObjectVtableF[11];     /* 0x00763A14 conf 0.60: Virtual method table of the action sub-object built by maybe_Battle_ActionSubObject_CreateF (slot 2 maybe_Battle_Action_ */
extern void* g_battleSceneModelSlotManagerVtable[12]; /* 0x00763A90 conf 0.70: Virtual method table of the battle-scene model-slot manager; BattleScene_ModelSlotManager_Dtor stores it at self[0] befo */
extern void* g_battleUiActionQueueVtable[12];        /* 0x007663C8 conf 0.60: Virtual method table of the battle UI action-queue/list object created by Battle_Ui_InitActionQueue; slot 3 is Ui_Action */
extern void* g_battleCommandQueueVtable[12];         /* 0x00766544 conf 0.65: Virtual method table of the battle command queue object; Battle_CommandQueue_Init stores it at queue[0] and the queue's  */
extern void* g_battleActorActionVtableA[11];         /* 0x007668A8 conf 0.55: Virtual method table of an actor-action sub-object built by maybe_Battle_ActionAnimObject_CtorA (slot 1 Battle_ActorActi */
extern void* g_battleActorActionVtableB[11];         /* 0x007668DC conf 0.55: Virtual method table of an actor-action sub-object built by maybe_Battle_ActionAnimObject_CtorB (slot 1 Battle_ActorActi */
extern void* g_battleCommandWindowVtable[8];         /* 0x00766A14 conf 0.50: Virtual method table of the battle command window/list object; Battle_CommandQueue_ReleaseSlots stores it and slots 4-7  */
extern void* g_battleTextLayoutVtable[16];           /* 0x00766AD8 conf 0.60: Virtual method table of the battle text-layout object created by Battle_TextLayout_Ctor (slot 2 Ui_ThreeRowTextWindow_De */
extern void* g_battlePopup3DPopupVtable[16];         /* 0x00766ED8 conf 0.55: Virtual method table of one of the popup widgets created by Battle_Popup3D_InitPopups (slot 2 Battle_PopupWindow_Release */
extern void* g_battleTextWindowChildWidgetVtableB[16]; /* 0x00766F8C conf 0.50: Virtual method table of a child widget created by maybe_Battle_TextWindow_CtorChildren (slot 1 Ui_GaugeWindow_InitPanesC */
extern void* g_battleTextWindowChildWidgetVtableC[16]; /* 0x00766FF0 conf 0.50: Virtual method table of a child widget created by maybe_Battle_TextWindow_CtorChildren (slot 1 maybe_Ui_SkillOpenWindow_ */
extern void* g_fieldPartyVtable[4];                  /* 0x00769398 conf 0.55: Virtual method table of the FieldParty object embedded in battle action sequences (slot 1 is maybe_FieldParty_Ui_DtorB,  */
extern void* g_battleActorBaseVtable[4];             /* 0x007694E0 conf 0.50: Secondary/base virtual method table of Battle_Actor (slot 2 FieldParty_InitFromParams, installed next to the primary g_b */
extern void* g_battleActionAnimObjectVtableC[11];    /* 0x00769750 conf 0.60: Virtual method table of the action-animation object built by maybe_Battle_ActionAnimObject_CtorC (slot 1 ..._DtorDeleteB */
extern void* g_battleActionAnimObjectVtableD[11];    /* 0x00769784 conf 0.60: Virtual method table of the action-animation object built by maybe_Battle_ActionAnimObject_CtorD (slot 1 ..._DtorDeleteC */
extern void* g_battleHpGaugeWindowVtable[16];        /* 0x007697B8 conf 0.85: Virtual method table of Battle_HpGaugeWindow (class recovered in structs.json, 608 bytes); slot 0 Battle_HpGaugeWindow_D */
extern void* g_battlePopup3DTargetResultVtable[16];  /* 0x00769A40 conf 0.55: Virtual method table of the target-result widget created by Battle_Popup3D_TargetResult_Init (slot 1 maybe_Ui_Widget_Hid */
extern void* g_battleUiFlowSelectedRowWindowVtable[4]; /* 0x0076A514 conf 0.50: Virtual method table of the 'selected row' window opened by Battle_UiFlow_OpenSelectedRowWindow (slot 2 maybe_Ui_Label_S */
extern void* g_battleUiFlowDetailWindowVtable[4];    /* 0x0076ACA4 conf 0.50: Virtual method table of the detail/message window toggled by Battle_UiFlow_ToggleDetailWindow and maybe_Battle_UiFlow_Op */
extern void* g_battleActionRowVtable[11];            /* 0x0076BBDC conf 0.50: Virtual method table of an action-list row/entry used by Battle_ActionAnimTable_InitSlots, Ui_ActionListWindow_InitPanes */
extern void* g_battleActionUiVtableA[16];            /* 0x0076BDEC conf 0.60: Virtual method table of a Battle_ActionUi sub-object installed by Battle_ActionUi_Ctor (slot 1 Battle_ActionUi_Ctor+0xbc */
extern void* g_battleActionAnimConfuseElementVtable[11]; /* 0x0076C410 conf 0.75: Virtual method table of the confusion animation element (Battle_ActionAnim_ConfuseElement_Dtor / _Play); created by Batt */
extern void* g_battleActionAnimDamageElementVtable[11]; /* 0x0076C444 conf 0.75: Virtual method table of the damage animation element (Battle_ActionAnim_DamageElement_Dtor / PlayDamageAnim); created by */
extern void* maybe_g_battleEmbeddedAnimVtable[12];   /* 0x0076C4DC conf 0.35: Secondary vtable block stored into Battle+0xbc (battle[0x2f]) by Battle_Ctor. Its first five words are zero and slot 5 i */
extern void* g_battleActionAnimMoveLandingElementVtable[11]; /* 0x0076C4EC conf 0.75: Virtual method table of the move-landing animation element (slot 1 Battle_ActionAnim_MoveLandingElement_Dtor): a read-on */
extern void* g_battleActionAnimLevelUpElementVtable[11]; /* 0x0076C520 conf 0.75: Virtual method table of the level-up animation element (slot 1 Battle_ActionAnim_LevelUpElement_Dtor): a read-only array */
extern void* g_battleActionAnimDyingElementVtable[11]; /* 0x0076C554 conf 0.75: Virtual method table of the dying/death animation element (slot 1 Battle_ActionAnim_DyingElement_Dtor): a read-only arra */
extern void* g_battleActionAnimUseItemElementVtable[11]; /* 0x0076C588 conf 0.75: Virtual method table of the use-item animation element (slot 1 Battle_ActionAnim_UseItemElement_Dtor): a read-only array */
extern void* g_battleActionAnimRevivalElementVtable[11]; /* 0x0076C5BC conf 0.75: Virtual method table of the revival animation element (slot 1 Battle_ActionAnim_RevivalElement_Dtor): a read-only array  */
extern void* g_battleTargetResultCursorVtable[16];   /* 0x0076CAE8 conf 0.50: Virtual method table of the cursor widget of the target-result popup (slot 1 Ui_CursorWidget_InitFromLayout+0x7c): a rea */
extern void* g_battleHealPopupVtable[16];            /* 0x0076CBE8 conf 0.70: Virtual method table of the heal popup (slot 1 Battle_Popup_Heal_Dtor, slot 8 maybe_Battle_Popup_InitHealPopup): a read- */
extern void* g_battleMissPopupVtable[16];            /* 0x0076CC4C conf 0.65: Virtual method table of the MISS popup (slot 1 Battle_Popup_InitMissPopup+0x44, slot 8 Battle_Popup_InitMissPopup): a re */
extern void* g_battleTextWindowSubWidgetVtable[10];  /* 0x0076D1E4 conf 0.60: Virtual method table of the sub-widget created by Battle_TextWindow_CtorSub; the same vtable is shared with Ui_DungeonSk */
extern void* g_battleUiFlowItemNameWindowVtable[4];  /* 0x0076DE38 conf 0.50: Virtual method table of the item-name window opened by Battle_UiFlow_OpenItemNameWindow/Ex (slot 2 maybe_Ui_Screen_LogEn */
extern void* g_battleActionRowAnimVtable[11];        /* 0x0076EB58 conf 0.50: Virtual method table of an animated action-list row used by Battle_ActionAnimTable_InitSlots / Ui_ActionListWindow_InitP */
extern void* g_battleUiFlowRowInfoWindowVtable[4];   /* 0x0076ECA8 conf 0.50: Virtual method table of the row-info window opened by Battle_UiFlow_OpenRowInfoWindow (slot 2 Monster_Model_BuildFromRec */
extern void* g_battleUiFlowRowInfoWindowExVtable[4]; /* 0x0076ECC0 conf 0.50: Virtual method table of the extended row-info window opened by Battle_UiFlow_OpenRowInfoWindowEx (slot 2 Monster_Model_B */
extern void* g_battleUiSubVtableA[16];               /* 0x0076ECD8 conf 0.50: Virtual method table of a secondary vtable of Battle_Ui installed by Battle_Ui_Ctor / destroyed by Battle_Ui_DestroyBase */
extern void* g_battleUnitObjectVtable[16];           /* 0x0076EE58 conf 0.60: Virtual method table of the Battle_UnitObject created by Battle_UnitObject_Ctor (slot 6 maybe_Battle_RefreshUnitTextSlot */
extern void* maybe_g_battleUnitModelDrawListVtable[9]; /* 0x0076EF70 conf 0.40: Vtable-shaped block installed on the battle unit-model transform/draw-list object: slot 0 is a code pointer, slots 1-3 a */
extern void* g_battleActorActionVtable[16];          /* 0x0076F260 conf 0.70: Virtual method table of the Battle_ActorAction object (slot 1 Battle_ActorAction_Dtor, slot 6 ClearPendingTarget, slot 7 */
extern void* g_battleActorVtable[16];                /* 0x0076F630 conf 0.90: Virtual method table of Battle_Actor (class recovered in structs.json, 6608 bytes); slot 0 Battle_Actor_DtorNoFree, slot */
extern void* g_battleUnitVtable[16];                 /* 0x0076F78C conf 0.70: Virtual method table of the Battle_Unit object (slot 6 Battle_Unit_InitPartyModel, slot 7 Battle_Actor_UpdateDispatch);  */
extern void* g_battleActionAnimPreMove1Vtable[11];   /* 0x0076F9B4 conf 0.85: Virtual method table of the 'pre_move_1' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimPreMove2Vtable[11];   /* 0x0076F9E8 conf 0.85: Virtual method table of the 'pre_move_2' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimPreMove3Vtable[11];   /* 0x0076FA1C conf 0.85: Virtual method table of the 'pre_move_3' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimPreMove4Vtable[11];   /* 0x0076FA50 conf 0.85: Virtual method table of the 'pre_move_4' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimSleepEndVtable[11];   /* 0x0076FA84 conf 0.75: Virtual method table of the sleep-end animation element (slot 1 Battle_ActionAnim_SleepEnd_DtorDelete, slot 2 ..._Play): */
extern void* g_battleActionAnimElementVtable[11];    /* 0x0076FB80 conf 0.70: Virtual method table of the generic battle action-animation element (slot 1 Battle_ActionAnim_Element_DtorDelete); base  */
extern void* g_battleActionAnimAtkSpellElementVtable[11]; /* 0x0076FBB4 conf 0.75: Virtual method table of the attack-spell animation element (slot 1 Battle_ActionAnim_AtkSpellElement_DtorDelete): a read */
extern void* g_battleActionAnimAttackStartVtable[11]; /* 0x0076FBE8 conf 0.70: Virtual method table of the attack-start animation element (slot 1 Battle_ActionAnim_AttackStart_DtorDelete): a read-onl */
extern void* g_battleActionAnimBackJumpVtable[11];   /* 0x0076FC1C conf 0.70: Virtual method table of the back-jump animation element (slot 1 Battle_ActionAnim_BackJump_DtorDelete): a read-only arra */
extern void* g_battleActionAnimGuardElementVtable[11]; /* 0x0076FC50 conf 0.75: Virtual method table of the guard animation element (slot 1 Battle_ActionAnim_GuardElement_DtorDelete): a read-only arra */
extern void* g_battleActionAnimRevSpellElementVtable[11]; /* 0x0076FC84 conf 0.75: Virtual method table of the revival-spell animation element (slot 1 Battle_ActionAnim_RevSpellElement_DtorDelete): a rea */
extern void* g_battleUiFlowItemDetailWindowVtable[4]; /* 0x00770248 conf 0.50: Virtual method table of the item-detail window opened by Battle_UiFlow_OpenItemDetailWindow (slot 1 Ui_EquipmentRow_Dtor */
extern void* g_battleUiFlowItemNameWidgetVtable[4];  /* 0x007713BC conf 0.50: Virtual method table of a widget of the item-name window opened by Battle_UiFlow_OpenItemNameWindow/Ex (slot 1 maybe_Ui_ */
extern void* g_battleActionRowActorAnimVtable[11];   /* 0x00771FD4 conf 0.50: Virtual method table of an action-list row animator used by Battle_ActionAnimTable_InitSlots / Ui_ActionListWindow_InitP */
extern void* g_battleUiFlowRowInfoWindowBVtable[4];  /* 0x00772198 conf 0.50: Virtual method table of the row-info window variant opened by Battle_UiFlow_OpenRowInfoWindowB (slot 1 maybe_Container_R */
extern void* g_battleActionAnimMoveBack1Vtable[11];  /* 0x0077269C conf 0.85: Virtual method table of the 'move_back_1' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimMoveBack2Vtable[11];  /* 0x007726D0 conf 0.85: Virtual method table of the 'move_back_2' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimMoveBack3Vtable[11];  /* 0x00772704 conf 0.85: Virtual method table of the 'move_back_3' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimMoveBack4Vtable[11];  /* 0x00772738 conf 0.85: Virtual method table of the 'move_back_4' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimPostMove1Vtable[11];  /* 0x0077276C conf 0.85: Virtual method table of the 'post_move_1' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimPostMove2Vtable[11];  /* 0x007727A0 conf 0.85: Virtual method table of the 'post_move_2' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimPostMove3Vtable[11];  /* 0x007727D4 conf 0.85: Virtual method table of the 'post_move_3' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimPostMove4Vtable[11];  /* 0x00772808 conf 0.85: Virtual method table of the 'post_move_4' action state object. Battle_ActionAnimWindow_Init creates the object right aft */
extern void* g_battleActionAnimSleepLoopVtable[11];  /* 0x0077283C conf 0.75: Virtual method table of the sleep-loop animation element (slot 1 Battle_ActionAnim_SleepLoop_DtorDelete): a read-only ar */
extern void* maybe_g_battleAnimWindowEmbeddedVtable[12]; /* 0x007728A8 conf 0.35: Mostly-zero vtable block stored at Battle_AnimWindow[0x8a] (offset 0x228) by Battle_AnimWindow_Ctor; slots 2/3 are Gfx n */
extern void* g_battleActionAnimAstronVtable[11];     /* 0x007728C4 conf 0.70: Virtual method table of the 'astron' animation element (slot 1 Battle_ActionAnim_Astron_DtorDelete, slot 2 AstronSelectV */
extern void* g_battleActionAnimFrontJumpVtable[11];  /* 0x007728F8 conf 0.70: Virtual method table of the front-jump animation element (slot 1 Battle_ActionAnim_FrontJump_DtorDelete): a read-only ar */
extern void* g_battleActionAnimGuardLoopVtable[11];  /* 0x0077292C conf 0.75: Virtual method table of the guard-loop animation element (slot 1 Battle_ActionAnim_GuardLoop_DtorDelete, slot 2 PlayGuar */
extern void* g_battleActionAnimPoisonDamageVtable[11]; /* 0x00772960 conf 0.75: Virtual method table of the poison-damage animation element (slot 1 maybe_Battle_ActionAnim_ElementE_DtorDelete, slot 2  */
extern void* g_battleActionAnimTumbleEndVtable[11];  /* 0x00772994 conf 0.70: Virtual method table of the tumble-end animation element (slot 1 Battle_ActionAnim_TumbleEnd_DtorDelete, slot 4 ElementF */
extern void* g_battleActionAnimTumbleEndVtableB[11]; /* 0x007729C8 conf 0.70: Virtual method table of the bat tumble-end animation element (slot 1 Battle_ActionAnim_TumbleEnd_DtorDeleteB, slot 4 Ele */
extern void* g_battlePopupNumberVtable[10];          /* 0x00772A98 conf 0.55: Virtual method table of the number popup created by Battle_Popup_Ctor (slot 2 Battle_Popup_InitNumberWidget, slot 5 Batt */
extern void* g_battleHealPopupVtableB[16];           /* 0x00772B88 conf 0.70: Virtual method table of the second heal-popup variant (slot 1 maybe_Battle_HealPopup_Dtor, slot 8 Battle_Popup_InitDamag */
extern void* g_battleCritPopupVtable[16];            /* 0x00772BEC conf 0.70: Virtual method table of the critical-hit popup (slot 1 maybe_Battle_CritPopup_Dtor, slot 8 Battle_Popup_InitMpHealPopup) */
extern void* g_battleActionProtectVtable[11];        /* 0x00772FF0 conf 0.60: Virtual method table of the protect/guard action object created by Battle_Action_Protect_Ctor (slot 1 maybe_Field_ActorA */
extern void* g_battleTextWindowPartySelectVtable[10]; /* 0x00773024 conf 0.50: Virtual method table of the party-select sub-widget created by maybe_Battle_TextWindow_CreateSubWidget (slot 1 Ui_PartyS */
extern void* g_battleSceneEnemyModelNodeVtable[12];  /* 0x00773290 conf 0.55: Virtual method table of the Gfx scene-node used for battle enemy models; BattleScene_BuildEnemyModel stores it in the no */
extern void* g_battleTextWindowPartyRowVtable[10];   /* 0x0077404C conf 0.70: Virtual method table of the party row of the battle text window (slot 1 maybe_Battle_TextWindow_PartyRowCtor+0x70, slot  */
extern void* g_battleUiSubVtableB[16];               /* 0x00774220 conf 0.50: Virtual method table of a secondary vtable of Battle_Ui (slot 1 Battle_Ui_DestroyBase, slot 6 Battle_Ui_ResetUnitSlots,  */
extern void* g_battle2DUnitSubVtable[4];             /* 0x00774568 conf 0.50: Secondary vtable of the 2D battle unit / screen object (slot 1 is maybe_Ui_ScreenCtor_vt774568+0x110, later Battle_Party */
extern void* g_battleActionSleepStartVtable[11];     /* 0x00774A70 conf 0.75: Virtual method table of the sleep-start action (slot 1 Battle_Action_SleepStart_DtorDelete, slot 2 its Update): a read-o */
extern void* g_battleActionCounterActVtable[11];     /* 0x00774ABC conf 0.75: Virtual method table of the counter-attack action (slot 1 Battle_Action_CounterAct_DtorDelete, slot 4 Execute): a read-o */
extern void* g_battleActionCounterEndVtable[11];     /* 0x00774AF0 conf 0.75: Virtual method table of the counter-attack end phase (slot 1 Battle_Action_CounterEnd_DtorDelete, slot 4 Execute): a rea */
extern void* g_battleActionGuardStartVtable[11];     /* 0x00774B24 conf 0.75: Virtual method table of the guard-start action (slot 1 Battle_Action_GuardStart_DtorDelete): a read-only array of .text  */
extern void* g_battleActionSpecialLanding1Vtable[11]; /* 0x00774B58 conf 0.70: Virtual method table of the first special-landing action (slot 1 Battle_Action_SpecialLanding1_Ctor+0x20, slot 4 Execute */
extern void* g_battleActionSpecialLanding2Vtable[11]; /* 0x00774B8C conf 0.70: Virtual method table of the second special-landing action (slot 1 Battle_Action_SpecialLanding_DtorDelete, slot 4 Execut */
extern void* g_battleActionCutInVtable[11];          /* 0x00774BC0 conf 0.70: Virtual method table of the cut-in action (slot 1 Battle_Action_CutIn_Ctor+0x20): a read-only array of .text function po */
extern u32 g_battleActionModelVtableB[12];           /* 0x00774BF4 conf 0.60: Virtual method table of a Battle_ActionModel variant (slot 1 Battle_ActionModel_DtorDelete); installed by maybe_Battle_E */
extern u32 g_battleActionModelVtableC[12];           /* 0x00774D7C conf 0.60: Virtual method table of a second Battle_ActionModel variant (slot 1 Battle_ActionModel_DtorDeleteB); installed by maybe_ */
extern void* g_battleDamagePopupVtable[16];          /* 0x00774F04 conf 0.70: Virtual method table of the damage popup widget (slot 1 maybe_Ui_DamagePopupWidget_Dtor, slot 8 Ui_DamagePopupWindow_Ini */
extern void* g_battleTargetResultCursorWidgetVtable[16]; /* 0x00774F68 conf 0.50: Virtual method table of a cursor widget used by Battle_Popup3D_TargetResult_Init (slot 1 Ui_CursorWidget_InitFromLayout+ */
extern void* g_battleUnitModelBVtable[16];           /* 0x007759FC conf 0.60: Virtual method table of the Battle_UnitModel (B variant) object built by maybe_Battle_SceneInit_Shared (slot 1 Battle_Un */
extern void* g_battleUnitModelBVtableB[16];          /* 0x00775AB8 conf 0.55: Virtual method table of a second Battle_UnitModel (B variant) vtable from maybe_Battle_SceneInit_Shared (slot 1 maybe_Ba */
extern void* g_battleActionGuardShieldVtable[11];    /* 0x00775C88 conf 0.75: Virtual method table of the shield-guard action (slot 1 Battle_Action_GuardShield_DtorDelete): a read-only array of .tex */
extern void* g_battleActionSpecialMoveVtable[11];    /* 0x00775CBC conf 0.80: Virtual method table of Battle_Action_SpecialMove (class recovered in structs.json; also the Battle_Action base vtable), */
extern void* g_battleActionGuardWeaponVtable[11];    /* 0x00775CF0 conf 0.75: Virtual method table of the weapon-guard action (slot 1 Battle_Action_GuardWeapon_DtorDelete): a read-only array of .tex */
extern void* g_battleActionCombinationVtable[11];    /* 0x00775D40 conf 0.75: Virtual method table of the combination attack action (slot 1 Battle_Action_Combination_DtorDelete): a read-only array o */
extern void* g_battleActionCounterLoopVtable[11];    /* 0x00775D74 conf 0.75: Virtual method table of the counter-attack loop phase (slot 1 Battle_Action_CounterLoop_DtorDelete): a read-only array o */
extern void* g_battleActionShieldGuardVtable[11];    /* 0x00775DA8 conf 0.75: Virtual method table of the shield-guard action variant (slot 1 Battle_Action_ShieldGuard_DtorDelete, slot 2 PlayMotion) */
extern void* g_battleActionWeaponGuardVtable[11];    /* 0x00775DDC conf 0.75: Virtual method table of the weapon-guard action variant (slot 1 Battle_Action_WeaponGuard_DtorDelete, slot 2 PlayMotion) */
extern void* g_battleMpDamagePopupVtable[16];        /* 0x00775F48 conf 0.70: Virtual method table of the MP-damage popup (slot 1 Ui_MpDamagePopup_Dtor, slot 8 Ui_MpDamagePopup_Init): a read-only ar */
extern void* g_battleUnitModelVtable[16];            /* 0x007770C8 conf 0.55: Virtual method table of the Battle_UnitModel object built by maybe_Battle_SceneInit_Shared (slot 1 maybe_Battle_Model_Up */
extern void* g_battleActionAnimSp1EndVtable[11];     /* 0x007779C8 conf 0.85: Virtual method table of the 'sp1End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp2EndVtable[11];     /* 0x007779FC conf 0.85: Virtual method table of the 'sp2End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp3EndVtable[11];     /* 0x00777A30 conf 0.85: Virtual method table of the 'sp3End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp4EndVtable[11];     /* 0x00777A64 conf 0.85: Virtual method table of the 'sp4End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp5EndVtable[11];     /* 0x00777A98 conf 0.85: Virtual method table of the 'sp5End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp6EndVtable[11];     /* 0x00777ACC conf 0.85: Virtual method table of the 'sp6End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp7EndVtable[11];     /* 0x00777B00 conf 0.85: Virtual method table of the 'sp7End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp8EndVtable[11];     /* 0x00777B34 conf 0.85: Virtual method table of the 'sp8End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionAnimSp9EndVtable[11];     /* 0x00777B68 conf 0.85: Virtual method table of the 'sp9End' action state object. Battle_ActionAnimWindow_Init creates the object right after th */
extern void* g_battleActionSupportSpellVtable[11];   /* 0x00777C00 conf 0.75: Virtual method table of the support-spell action (slot 1 Battle_Action_SupportSpell_Dtor): a read-only array of .text fu */
extern void* g_battleActionBreakVtable[11];          /* 0x00777EBC conf 0.60: Virtual method table of the break action object created by Battle_Action_Break_Ctor (slot 1 Ui_LoopPane_DtorDelete): a r */
extern void* g_battleTextWindowChildWidgetVtableD[16]; /* 0x00777EF0 conf 0.50: Virtual method table of a child widget created by maybe_Battle_TextWindow_CtorChildren (slot 1 Ui_LoopPane_Init+0x54): a */
extern void* g_battleUiFlowConfirmWindowVtable[4];   /* 0x00778DD0 conf 0.50: Virtual method table of the confirm window opened by Battle_UiFlow_OpenConfirmWindow (slot 1 maybe_Ui_Object_DtorVirtual */
extern void* g_battleActionAnimApproach1Vtable[11];  /* 0x007793E4 conf 0.85: Virtual method table of the 'approach_1' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimApproach2Vtable[11];  /* 0x00779418 conf 0.85: Virtual method table of the 'approach_2' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimApproach3Vtable[11];  /* 0x0077944C conf 0.85: Virtual method table of the 'approach_3' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimApproach4Vtable[11];  /* 0x00779480 conf 0.85: Virtual method table of the 'approach_4' action state object. Battle_ActionAnimWindow_Init creates the object right afte */
extern void* g_battleActionAnimSp10EndVtable[11];    /* 0x007794B4 conf 0.85: Virtual method table of the 'sp10End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp11EndVtable[11];    /* 0x007794E8 conf 0.85: Virtual method table of the 'sp11End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp12EndVtable[11];    /* 0x0077951C conf 0.85: Virtual method table of the 'sp12End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp13EndVtable[11];    /* 0x00779550 conf 0.85: Virtual method table of the 'sp13End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp14EndVtable[11];    /* 0x00779584 conf 0.85: Virtual method table of the 'sp14End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp15EndVtable[11];    /* 0x007795B8 conf 0.85: Virtual method table of the 'sp15End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp16EndVtable[11];    /* 0x007795EC conf 0.85: Virtual method table of the 'sp16End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp17EndVtable[11];    /* 0x00779620 conf 0.85: Virtual method table of the 'sp17End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp18EndVtable[11];    /* 0x00779654 conf 0.85: Virtual method table of the 'sp18End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp19EndVtable[11];    /* 0x00779688 conf 0.85: Virtual method table of the 'sp19End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp1LoopVtable[11];    /* 0x007796BC conf 0.85: Virtual method table of the 'sp1Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp20EndVtable[11];    /* 0x007796F0 conf 0.85: Virtual method table of the 'sp20End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp21EndVtable[11];    /* 0x00779724 conf 0.85: Virtual method table of the 'sp21End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp22EndVtable[11];    /* 0x00779758 conf 0.85: Virtual method table of the 'sp22End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp23EndVtable[11];    /* 0x0077978C conf 0.85: Virtual method table of the 'sp23End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp24EndVtable[11];    /* 0x007797C0 conf 0.85: Virtual method table of the 'sp24End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp25EndVtable[11];    /* 0x007797F4 conf 0.85: Virtual method table of the 'sp25End' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp2LoopVtable[11];    /* 0x00779828 conf 0.85: Virtual method table of the 'sp2Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp3LoopVtable[11];    /* 0x0077985C conf 0.85: Virtual method table of the 'sp3Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp4LoopVtable[11];    /* 0x00779890 conf 0.85: Virtual method table of the 'sp4Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp5LoopVtable[11];    /* 0x007798C4 conf 0.85: Virtual method table of the 'sp5Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp6LoopVtable[11];    /* 0x007798F8 conf 0.85: Virtual method table of the 'sp6Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp7LoopVtable[11];    /* 0x0077992C conf 0.85: Virtual method table of the 'sp7Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp8LoopVtable[11];    /* 0x00779960 conf 0.85: Virtual method table of the 'sp8Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleActionAnimSp9LoopVtable[11];    /* 0x00779994 conf 0.85: Virtual method table of the 'sp9Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after t */
extern void* g_battleUiFlowInfoWindowVtable[4];      /* 0x00779D10 conf 0.50: Virtual method table of the info window opened by maybe_Battle_UiFlow_OpenInfoWindow (slot 1 maybe_Battle_TargetMarker_C */
extern void* g_battleTextWindowChildWidgetVtableE[16]; /* 0x00779D28 conf 0.50: Virtual method table of a child widget created by maybe_Battle_TextWindow_CtorChildren (slot 1 maybe_Ui_LoopPane3_Init+0 */
extern void* g_battleActionDmgExtVtable[11];         /* 0x0077A8C0 conf 0.75: Virtual method table of the extended-damage action (slot 1 Battle_Action_DmgExt_Dtor); created by Battle_Action_DmgExt_C */
extern void* g_battleActionAnimSp10LoopVtable[11];   /* 0x0077A8F4 conf 0.85: Virtual method table of the 'sp10Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp11LoopVtable[11];   /* 0x0077A928 conf 0.85: Virtual method table of the 'sp11Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp12LoopVtable[11];   /* 0x0077A95C conf 0.85: Virtual method table of the 'sp12Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp13LoopVtable[11];   /* 0x0077A990 conf 0.85: Virtual method table of the 'sp13Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp14LoopVtable[11];   /* 0x0077A9C4 conf 0.85: Virtual method table of the 'sp14Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp15LoopVtable[11];   /* 0x0077A9F8 conf 0.85: Virtual method table of the 'sp15Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp16LoopVtable[11];   /* 0x0077AA2C conf 0.85: Virtual method table of the 'sp16Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp17LoopVtable[11];   /* 0x0077AA60 conf 0.85: Virtual method table of the 'sp17Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp18LoopVtable[11];   /* 0x0077AA94 conf 0.85: Virtual method table of the 'sp18Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp19LoopVtable[11];   /* 0x0077AAC8 conf 0.85: Virtual method table of the 'sp19Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp1StartVtable[11];   /* 0x0077AAFC conf 0.85: Virtual method table of the 'sp1Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp20LoopVtable[11];   /* 0x0077AB30 conf 0.85: Virtual method table of the 'sp20Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp21LoopVtable[11];   /* 0x0077AB64 conf 0.85: Virtual method table of the 'sp21Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp22LoopVtable[11];   /* 0x0077AB98 conf 0.85: Virtual method table of the 'sp22Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp23LoopVtable[11];   /* 0x0077ABCC conf 0.85: Virtual method table of the 'sp23Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp24LoopVtable[11];   /* 0x0077AC00 conf 0.85: Virtual method table of the 'sp24Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp25LoopVtable[11];   /* 0x0077AC34 conf 0.85: Virtual method table of the 'sp25Loop' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp2StartVtable[11];   /* 0x0077AC68 conf 0.85: Virtual method table of the 'sp2Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp3StartVtable[11];   /* 0x0077AC9C conf 0.85: Virtual method table of the 'sp3Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp4StartVtable[11];   /* 0x0077ACD0 conf 0.85: Virtual method table of the 'sp4Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp5StartVtable[11];   /* 0x0077AD04 conf 0.85: Virtual method table of the 'sp5Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp6StartVtable[11];   /* 0x0077AD38 conf 0.85: Virtual method table of the 'sp6Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp7StartVtable[11];   /* 0x0077AD6C conf 0.85: Virtual method table of the 'sp7Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp8StartVtable[11];   /* 0x0077ADA0 conf 0.85: Virtual method table of the 'sp8Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp9StartVtable[11];   /* 0x0077ADD4 conf 0.85: Virtual method table of the 'sp9Start' action state object. Battle_ActionAnimWindow_Init creates the object right after  */
extern void* g_battleActionAnimSp10StartVtable[11];  /* 0x0077BB4C conf 0.85: Virtual method table of the 'sp10Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp11StartVtable[11];  /* 0x0077BB80 conf 0.85: Virtual method table of the 'sp11Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp12StartVtable[11];  /* 0x0077BBB4 conf 0.85: Virtual method table of the 'sp12Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp13StartVtable[11];  /* 0x0077BBE8 conf 0.85: Virtual method table of the 'sp13Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp14StartVtable[11];  /* 0x0077BC1C conf 0.85: Virtual method table of the 'sp14Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp15StartVtable[11];  /* 0x0077BC50 conf 0.85: Virtual method table of the 'sp15Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp16StartVtable[11];  /* 0x0077BC84 conf 0.85: Virtual method table of the 'sp16Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp17StartVtable[11];  /* 0x0077BCB8 conf 0.85: Virtual method table of the 'sp17Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp18StartVtable[11];  /* 0x0077BCEC conf 0.85: Virtual method table of the 'sp18Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp19StartVtable[11];  /* 0x0077BD20 conf 0.85: Virtual method table of the 'sp19Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp20StartVtable[11];  /* 0x0077BD54 conf 0.85: Virtual method table of the 'sp20Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp21StartVtable[11];  /* 0x0077BD88 conf 0.85: Virtual method table of the 'sp21Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp22StartVtable[11];  /* 0x0077BDBC conf 0.85: Virtual method table of the 'sp22Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp23StartVtable[11];  /* 0x0077BDF0 conf 0.85: Virtual method table of the 'sp23Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp24StartVtable[11];  /* 0x0077BE24 conf 0.85: Virtual method table of the 'sp24Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionAnimSp25StartVtable[11];  /* 0x0077BE58 conf 0.85: Virtual method table of the 'sp25Start' action state object. Battle_ActionAnimWindow_Init creates the object right after */
extern void* g_battleActionSkillVtable[11];          /* 0x0077BE8C conf 0.55: Virtual method table of the skill action object created by Battle_Action_Skill_Ctor (slot 1 maybe_Ui_StatusPlate_DtorDel */
extern void* g_battleActionBadConditionVtable[11];   /* 0x0077BEC0 conf 0.55: Virtual method table of the bad-condition action created by Battle_Action_BadConditionNut_Ctor (slot 1 maybe_Ui_AilmentP */
extern void* g_battleActionAnimElementVtableA[11];   /* 0x0077CC88 conf 0.60: Virtual method table of a generic battle action-animation element (slot 1 Battle_ActionAnimElement_DtorDelete, slot 3/4  */
extern void* g_battleActionAnimElementStandVtable[11]; /* 0x0077CCBC conf 0.70: Virtual method table of the 'stand' animation element (slot 1 Battle_ActionAnimElement_Stand_DtorDelete, slot 2 PlayStan */
extern void* g_battleUiFlowSelectionWindowVtable[4]; /* 0x0077CF78 conf 0.50: Virtual method table of the selection/list window opened by Battle_UiFlow_OpenSelectionWindow/Ex (slot 5 maybe_Ui_ListWi */
extern void* g_battleActionAnimAttachedActionVtable[11]; /* 0x0077D7F4 conf 0.55: Virtual method table of the attached-action animation element (slot 1 Anim_AttachedAction_Delete, slot 2 PlayAnimationBy */
extern void* g_battleTargetMarkerVtable[11];         /* 0x0077D828 conf 0.70: Virtual method table of the battle target-marker object (slot 1 Battle_TargetMarker_Delete, slot 3/4 UpdateForOwner): a  */
extern void* maybe_g_battleActionAnimActorVtable[11]; /* 0x0077DFE0 conf 0.45: Virtual method table of an action-animation element whose methods are named Field_ActorAction (slot 1 maybe_Field_ActorA */
extern void* maybe_g_battleActionAnimCharVtableA[11]; /* 0x0077E014 conf 0.45: Virtual method table of an action-animation element whose methods are named Field_Char (slot 1 maybe_Field_CharAction_De */
extern void* maybe_g_battleActionAnimCharVtableB[11]; /* 0x0077E048 conf 0.45: Virtual method table of an action-animation element whose methods are named Field_Char (slot 1 maybe_Field_CharAction_De */
extern void* maybe_g_battleActionAnimCharVtableC[11]; /* 0x0077E07C conf 0.45: Virtual method table of an action-animation element whose methods are named Field_Char (slot 1 maybe_Field_CharAction_De */
extern void* g_battleUiVtable[16];                   /* 0x0077EAC0 conf 0.85: Virtual method table of Battle_Ui (class recovered in structs.json, 60776 bytes); slot 1 Battle2DUnit_DeleteDtor, slot 6 */
extern void* g_battleSceneUnitPlacementVtable[16];   /* 0x0077F9AC conf 0.80: Virtual method table of the BattleScene unit-placement object (slot 0 BattleScene_UnitPlacement_Dtor); created by Battle */
extern u32 maybe_g_battleTargetSlotPatternA[12];     /* 0x00782090 conf 0.40: Zero-initialised 12-word rodata block copied into the target-slot locals of Battle_BuildTargetSlots (one of the g_001728 */
extern u32 maybe_g_battleTargetSlotPatternB[12];     /* 0x00782AD4 conf 0.40: Second zero-initialised 12-word target-slot descriptor read by Battle_BuildTargetSlots (local_70 = g_00172848 / local_68 */
extern void* g_battlePopupPoolVtable[4];             /* 0x00782B10 conf 0.55: Virtual method table of the battle popup pool / handle list created by maybe_Battle_PopupPool_Init and maybe_Field_Handl */
extern void* g_gfxSceneVtable[4];                    /* 0x00782B54 conf 0.85: Virtual method table of Gfx_Scene (class recovered in structs.json, 18340 bytes; also the Battle_PopupPool base vtable); */
extern char g_firstStrikeTwoWayPackCondition[11];    /* 0x00786966 conf 0.50: String '_2way.pack' appended to the first-strike condition expression by Battle_DecideFirstStrike (through func_0028B70C */
extern u8 maybe_g_rodata_00796873[12];               /* 0x00796873 conf 0.30: Small unaligned byte blob in rodata passed by address to maybe_Battle_ActionAnim_ElementCtorSlot9F as the parameter bloc */
extern u32 maybe_g_battleCameraRangeBlend[12];       /* 0x007A3788 conf 0.40: Zero-initialised 12-word data block used by maybe_Battle_CameraRangeBlend_Update (read as two floats/words at +0/+4) and */
extern u8 maybe_g_battleUnitKeyframeValue;           /* 0x007A419C conf 0.40: Byte multiplied into the keyframe spacing of maybe_BattleScene_BuildUnitKeyframesVariant (local_6c = *g_0060524c; local_ */
extern f32 maybe_g_battleSceneModelSizeOverride;     /* 0x007A41A0 conf 0.45: Size value returned for model id 0x34A by maybe_BattleScene_GetUnitModelSize (VectorFloatToUnsigned(*g_0060312c,3)). Zer */
extern u32 maybe_g_battleSceneFinishState;           /* 0x007A4228 conf 0.40: Object pointer read as g_001715c0->f_c by maybe_Battle_FinishBattleScene (field +0xc of a scene/manager object) while hi */
extern u8 maybe_g_battleUnitLayoutSkipFlag;          /* 0x007A58F7 conf 0.45: Debug/override byte: when non-zero, Battle_ActionModel_PruneAndLayoutUnits and Battle_ActionModel_UpdateUnitVisibility s */
extern u8 maybe_g_battleUiForceSlotRefresh;          /* 0x007A58FC conf 0.45: Force-refresh byte: five battle/field-party UI functions test it and, when non-zero, force the 'slots changed' flag (fie */
extern u8 maybe_g_battleUiForceBalloons;             /* 0x007A58FD conf 0.45: Override byte for the battle balloon/HUD path: maybe_Battle_Ui_StartBalloonForAll and maybe_FieldParty_GetMemberRideObje */
extern u8 maybe_g_battleUiForceUnitSelectable;       /* 0x007A590E conf 0.45: Override byte that makes battle units selectable even when the game work's selectable mask bit is clear (Battle_IsUnitSe */
extern f32 maybe_g_battleUiBalloonLerp;              /* 0x007A5A0C conf 0.45: Interpolation factor (read as a float) used by maybe_Battle_Ui_LayoutBalloons to blend balloon positions toward the refe */
extern u32 maybe_g_battleUnitDisplayRange[2];        /* 0x007A5AD8 conf 0.40: Two-word value read by maybe_Battle_UpdateUnitDisplay as a pointer (g_002da1f0) and a 64-bit quantity (g_002da1f4) - pro */
extern f32 g_battleMoveFinishThreshold;              /* 0x007A5C60 conf 0.50: Movement threshold 0.3 (two consecutive 0.3 floats) used by Battle_ActorAction_FinishMove and maybe_Battle2DUnit_UpdateS */
extern u32 maybe_g_battleUiScrollSlot4Fallback[2];   /* 0x007A5CA8 conf 0.40: Fallback slot entry for the >3-slot branch of maybe_Battle_Ui_UpdateScrollAnimation (pfVar6 = g_0059f7d4). Zero in retai */
extern u32 maybe_g_battleUiScrollSlotXFallback[2];   /* 0x007A5CB0 conf 0.40: Second fallback slot entry of maybe_Battle_Ui_UpdateScrollAnimation (pfVar6 = g_0059f7d8, used after the first fallback  */
extern u32 maybe_g_battleMemberWidgetState;          /* 0x007A5CB8 conf 0.40: Object read as g_003cb3c8->f_10 (field +0x10) by maybe_Battle_Ui_MemberWidget_PushPopup while hiding the 3D popup. Zero  */
extern f32 g_battleTargetPanelFocusFactors[5];       /* 0x007A60D0 conf 0.60: Five float factors (0.625, 1.25, 3, 6.25, 6.25) at the start of the target-panel factor block, used by Battle_Ui_TargetP */
extern f32 g_battleTargetGroupBoundsFactors[5];      /* 0x007A60E4 conf 0.60: Sub-table of five float factors (0.625, 1.25, 2, 4.2, 4.2) at offset 0x14 of the target-panel factor table; Battle_Ui_Ta */
extern u8 maybe_g_battleTargetMarkerParams;          /* 0x007A60F8 conf 0.40: First byte of the target-marker parameter block used by maybe_Battle_Ui_PlaceMarkerOnModel: the function reads the float */
extern u8 g_battleTargetMarkerEnabled;               /* 0x007A60F9 conf 0.50: Enable flag for the 3D battle target marker: maybe_Battle_Ui_PlaceMarkerOnModel returns early unless it is non-zero (and */
extern u8 maybe_g_battleTargetMarkerOffset[2];       /* 0x007A6104 conf 0.40: Two byte values read as floats by maybe_Battle_Ui_PlaceMarkerOnModel to offset the marker sprite (local_d4 = *g_004e3278 */
extern u8 g_battleTargetMarkerColorA;                /* 0x007A6108 conf 0.50: Default colour/index written into the target-marker widget's field f_c0 when the marker is created without a resolved ta */
extern u8 g_battleTargetMarkerColorB;                /* 0x007A610C conf 0.50: Second default colour/index written into the target-marker widget's field f_bc (paired with g_battleTargetMarkerColorA)  */
extern f32 maybe_g_battleTargetMarkerHeight;         /* 0x007A6110 conf 0.45: Vertical offset added to the 3D target marker position by maybe_Battle_Ui_PlaceMarkerOnModel (fStack_6c + *g_004e3264).  */
extern u8 g_encounterExtraCondition1;                /* 0x007A65AA conf 0.50: When non-zero, maybe_Battle_Encounter_BuildConditions adds extra condition index 1 (func_001DA6A4(&local_f8,1)) to the e */
extern u8 g_encounterExtraCondition2;                /* 0x007A65AB conf 0.50: When non-zero, maybe_Battle_Encounter_BuildConditions adds extra condition index 2 (func_001DA6A4(&local_f8,2)). Zero in */
extern u8 maybe_g_battleEncounterTransitionParamA;   /* 0x007A7394 conf 0.40: Byte copied into battle-scene object field f_119c on frame 1 of the encounter screen transition (Battle_UpdateEncounterT */
extern u8 maybe_g_battleEncounterTransitionParamB;   /* 0x007A7398 conf 0.40: Byte copied into battle-scene object field f_11a0 on frame 1 of the encounter screen transition, alongside g_battleEncou */
extern char* g_battleUiPartNameTable[3];             /* 0x007A7800 conf 0.70: Three battle UI pane names: 'icon_target_3d', 'icon_target_2d', 'gau_hp_bar2'. Indexed by the gauge/target code (Battle_ */
extern u32 maybe_g_battleCommandTargetState;         /* 0x007A78B4 conf 0.40: Shared battle command-target state object read as g_0038da34->f_c (field +0xc) by eight command/target update functions  */
extern u8 maybe_g_battleCommandListRowStep;          /* 0x007A7974 conf 0.40: Byte value 6 used by the battle command-list window as a row/scroll step (multiplied by the row index in maybe_Battle_Ac */
extern u8 maybe_g_battlePopupRowCount;               /* 0x007A7A7C conf 0.40: Byte value 6 stored into popup field f_66 by maybe_Battle_Popup_RefreshActor (the same field the command list uses for i */
extern u32 maybe_g_battlePopupEntryPool;             /* 0x007A7B00 conf 0.40: Pool/list head used by maybe_Battle_PopupEntry_Create when it links a new popup entry (read as g_002e0210 next to a u16  */
extern f32 g_battlePopup3DSlideSpeed[2];             /* 0x007AA30C conf 0.50: Two floats (horizontal/vertical speed) used by Battle_Popup3D_UpdateRoot, maybe_Battle_Popup3D_UpdateRootEx and Menu_Spa */
extern char* g_statusModelNameTable[78];             /* 0x007AE19C conf 0.60: Table of 3D model/icon names indexed by a battle unit's status byte (bounds-checked < 78) in maybe_Battle_Action_CheckSt */
extern u32 maybe_g_objectHandleHashTable;            /* 0x007B6D78 conf 0.45: Header of a global open-addressed handle table used by Anim_ModelLoad_ByName and UI message/talk code: word 0 is the mas */
extern char g_battleAnimSpriteName[7];               /* 0x007BE802 conf 0.70: Animation/part name 'sprite' passed to func_0011CCA0 by maybe_Battle_CutsceneObject_InitFromParams and maybe_Model_Setup */
extern char g_battleSceneModelNameM210f[6];          /* 0x007BFBFA conf 0.65: String 'm210f' selected by the unit-variant switch in maybe_BattleScene_SyncUnitRenderResources (passed as the model/ani */
extern char g_battleSceneModelNameM210b[6];          /* 0x007BFC00 conf 0.65: String 'm210b' selected by the unit-variant switch in maybe_BattleScene_SyncUnitRenderResources (passed as the model/ani */
extern char g_battleSceneModelNameM210g[6];          /* 0x007BFC06 conf 0.65: String 'm210g' selected by the unit-variant switch in maybe_BattleScene_SyncUnitRenderResources (passed as the model/ani */
extern char g_battleSceneModelNameM210i[6];          /* 0x007BFC0C conf 0.65: String 'm210i' selected by the unit-variant switch in maybe_BattleScene_SyncUnitRenderResources (passed as the model/ani */
extern char g_battleSceneModelNameM210h[6];          /* 0x007BFC12 conf 0.65: String 'm210h' selected by the unit-variant switch in maybe_BattleScene_SyncUnitRenderResources (passed as the model/ani */
extern u8 maybe_g_battleAnimPreMove1Pad[2];          /* 0x007BFC18 conf 0.30: Points at the NUL padding byte immediately before the 'pre_move_1' string; used as the name pointer for one switch case  */
extern char g_battleAnimNameDrop[5];                 /* 0x007BFCDB conf 0.60: Animation name 'drop' played through model vtable slot 0x84 by BattleScene_LayoutEnemyFormation when an enemy is dropped */
extern char g_battleAnimNameOpen[5];                 /* 0x007BFCE0 conf 0.60: Animation name 'open' played through model vtable slot 0x84 while maybe_BattleScene_CreateFormationWidgets builds the en */
extern char g_battleAnimNameSp1End[8];               /* 0x007BFE1B conf 0.80: Animation clip name 'sp1_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp1End_Play at the end  */
extern char g_battleAnimNameSp2End[8];               /* 0x007BFE23 conf 0.80: Animation clip name 'sp2_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp2End_Play at the end  */
extern char g_battleAnimNameSp3End[8];               /* 0x007BFE2B conf 0.80: Animation clip name 'sp3_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp3End_Play at the end  */
extern char g_battleAnimNameSp4End[8];               /* 0x007BFE33 conf 0.80: Animation clip name 'sp4_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp4End_Play at the end  */
extern char g_battleAnimNameSp5End[8];               /* 0x007BFE3B conf 0.80: Animation clip name 'sp5_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp5End_Play at the end  */
extern char g_battleAnimNameSp6End[8];               /* 0x007BFE43 conf 0.80: Animation clip name 'sp6_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp6End_Play at the end  */
extern char g_battleAnimNameSp7End[8];               /* 0x007BFE4B conf 0.80: Animation clip name 'sp7_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp7End_Play at the end  */
extern char g_battleAnimNameSp8End[8];               /* 0x007BFE53 conf 0.80: Animation clip name 'sp8_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp8End_Play at the end  */
extern char g_battleAnimNameSp9End[8];               /* 0x007BFE5B conf 0.80: Animation clip name 'sp9_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp9End_Play at the end  */
extern char g_battleAnimNameSp10End[9];              /* 0x007BFEA0 conf 0.80: Animation clip name 'sp10_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp10End_Play at the en */
extern char g_battleAnimNameSp11End[9];              /* 0x007BFEA9 conf 0.80: Animation clip name 'sp11_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp11End_Play at the en */
extern char g_battleAnimNameSp12End[9];              /* 0x007BFEB2 conf 0.80: Animation clip name 'sp12_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp12End_Play at the en */
extern char g_battleAnimNameSp13End[9];              /* 0x007BFEBB conf 0.80: Animation clip name 'sp13_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp13End_Play at the en */
extern char g_battleAnimNameSp14End[9];              /* 0x007BFEC4 conf 0.80: Animation clip name 'sp14_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp14End_Play at the en */
extern char g_battleAnimNameSp15End[9];              /* 0x007BFECD conf 0.80: Animation clip name 'sp15_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp15End_Play at the en */
extern char g_battleAnimNameSp16End[9];              /* 0x007BFED6 conf 0.80: Animation clip name 'sp16_end' played through model vtable slot 0x84 by Battle_Action_SpecialMove_Sp16End_Play at the en */
extern char g_battleClipSp17End[9];                  /* 0x007BFEDF conf 0.90: Model animation clip name "sp17_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp17En */
extern char g_battleClipSp18End[9];                  /* 0x007BFEE8 conf 0.90: Model animation clip name "sp18_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp18En */
extern char g_battleClipSp19End[9];                  /* 0x007BFEF1 conf 0.90: Model animation clip name "sp19_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp19En */
extern char g_battleClipSp1Loop[9];                  /* 0x007BFEFA conf 0.90: Model animation clip name "sp1_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp1Lo */
extern char g_battleClipSp20End[9];                  /* 0x007BFF03 conf 0.90: Model animation clip name "sp20_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp20En */
extern char g_battleClipSp21End[9];                  /* 0x007BFF0C conf 0.90: Model animation clip name "sp21_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp21En */
extern char g_battleClipSp22End[9];                  /* 0x007BFF15 conf 0.90: Model animation clip name "sp22_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp22En */
extern char g_battleClipSp23End[9];                  /* 0x007BFF1E conf 0.90: Model animation clip name "sp23_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp23En */
extern char g_battleClipSp24End[9];                  /* 0x007BFF27 conf 0.90: Model animation clip name "sp24_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp24En */
extern char g_battleClipSp25End[9];                  /* 0x007BFF30 conf 0.90: Model animation clip name "sp25_end": the end phase of a battle special-move animation. Battle_Action_SpecialMove_Sp25En */
extern char g_battleClipSp2Loop[9];                  /* 0x007BFF39 conf 0.90: Model animation clip name "sp2_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp2Lo */
extern char g_battleClipSp3Loop[9];                  /* 0x007BFF42 conf 0.90: Model animation clip name "sp3_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp3Lo */
extern char g_battleClipSp4Loop[9];                  /* 0x007BFF4B conf 0.90: Model animation clip name "sp4_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp4Lo */
extern char g_battleClipSp5Loop[9];                  /* 0x007BFF54 conf 0.90: Model animation clip name "sp5_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp5Lo */
extern char g_battleClipSp6Loop[9];                  /* 0x007BFF5D conf 0.90: Model animation clip name "sp6_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp6Lo */
extern char g_battleClipSp7Loop[9];                  /* 0x007BFF66 conf 0.90: Model animation clip name "sp7_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp7Lo */
extern char g_battleClipSp8Loop[9];                  /* 0x007BFF6F conf 0.90: Model animation clip name "sp8_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp8Lo */
extern char g_battleClipSp9Loop[9];                  /* 0x007BFF78 conf 0.90: Model animation clip name "sp9_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp9Lo */
extern char g_battleClipSp10Loop[10];                /* 0x007BFFB4 conf 0.90: Model animation clip name "sp10_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp10 */
extern char g_battleClipSp11Loop[10];                /* 0x007BFFBE conf 0.90: Model animation clip name "sp11_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp11 */
extern char g_battleClipSp12Loop[10];                /* 0x007BFFC8 conf 0.90: Model animation clip name "sp12_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp12 */
extern char g_battleClipSp13Loop[10];                /* 0x007BFFD2 conf 0.90: Model animation clip name "sp13_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp13 */
extern char g_battleClipSp14Loop[10];                /* 0x007BFFDC conf 0.90: Model animation clip name "sp14_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp14 */
extern char g_battleClipSp15Loop[10];                /* 0x007BFFE6 conf 0.90: Model animation clip name "sp15_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp15 */
extern char g_battleClipSp16Loop[10];                /* 0x007BFFF0 conf 0.90: Model animation clip name "sp16_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp16 */
extern char g_battleClipSp17Loop[10];                /* 0x007BFFFA conf 0.90: Model animation clip name "sp17_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp17 */
extern char g_battleClipSp18Loop[10];                /* 0x007C0004 conf 0.90: Model animation clip name "sp18_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp18 */
extern char g_battleClipSp19Loop[10];                /* 0x007C000E conf 0.90: Model animation clip name "sp19_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp19 */
extern char g_battleClipSp1Start[10];                /* 0x007C0018 conf 0.90: Model animation clip name "sp1_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp1 */
extern char g_battleClipSp20Loop[10];                /* 0x007C0022 conf 0.90: Model animation clip name "sp20_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp20 */
extern char g_battleClipSp21Loop[10];                /* 0x007C002C conf 0.90: Model animation clip name "sp21_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp21 */
extern char g_battleClipSp22Loop[10];                /* 0x007C0036 conf 0.90: Model animation clip name "sp22_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp22 */
extern char g_battleClipSp23Loop[10];                /* 0x007C0040 conf 0.90: Model animation clip name "sp23_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp23 */
extern char g_battleClipSp24Loop[10];                /* 0x007C004A conf 0.90: Model animation clip name "sp24_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp24 */
extern char g_battleClipSp25Loop[10];                /* 0x007C0054 conf 0.90: Model animation clip name "sp25_loop": the loop phase of a battle special-move animation. Battle_Action_SpecialMove_Sp25 */
extern char g_battleClipSp2Start[10];                /* 0x007C005E conf 0.90: Model animation clip name "sp2_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp2 */
extern char g_battleClipSp3Start[10];                /* 0x007C0068 conf 0.90: Model animation clip name "sp3_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp3 */
extern char g_battleClipSp4Start[10];                /* 0x007C0072 conf 0.90: Model animation clip name "sp4_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp4 */
extern char g_battleClipSp5Start[10];                /* 0x007C007C conf 0.90: Model animation clip name "sp5_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp5 */
extern char g_battleClipSp6Start[10];                /* 0x007C0086 conf 0.90: Model animation clip name "sp6_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp6 */
extern char g_battleClipSp7Start[10];                /* 0x007C0090 conf 0.90: Model animation clip name "sp7_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp7 */
extern char g_battleClipSp8Start[10];                /* 0x007C009A conf 0.90: Model animation clip name "sp8_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp8 */
extern char g_battleClipSp9Start[10];                /* 0x007C00A4 conf 0.90: Model animation clip name "sp9_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp9 */
extern char g_battleClipSp10Start[11];               /* 0x007C00AE conf 0.90: Model animation clip name "sp10_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp11Start[11];               /* 0x007C00B9 conf 0.90: Model animation clip name "sp11_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp12Start[11];               /* 0x007C00C4 conf 0.90: Model animation clip name "sp12_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp13Start[11];               /* 0x007C00CF conf 0.90: Model animation clip name "sp13_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp14Start[11];               /* 0x007C00DA conf 0.90: Model animation clip name "sp14_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp15Start[11];               /* 0x007C00E5 conf 0.90: Model animation clip name "sp15_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp16Start[11];               /* 0x007C00F0 conf 0.90: Model animation clip name "sp16_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp17Start[11];               /* 0x007C00FB conf 0.90: Model animation clip name "sp17_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp18Start[11];               /* 0x007C0106 conf 0.90: Model animation clip name "sp18_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp19Start[11];               /* 0x007C0111 conf 0.90: Model animation clip name "sp19_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp20Start[11];               /* 0x007C011C conf 0.90: Model animation clip name "sp20_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp21Start[11];               /* 0x007C0127 conf 0.90: Model animation clip name "sp21_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp22Start[11];               /* 0x007C0132 conf 0.90: Model animation clip name "sp22_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp23Start[11];               /* 0x007C013D conf 0.90: Model animation clip name "sp23_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp24Start[11];               /* 0x007C0148 conf 0.90: Model animation clip name "sp24_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_battleClipSp25Start[11];               /* 0x007C0153 conf 0.90: Model animation clip name "sp25_start": the start phase of a battle special-move animation. Battle_Action_SpecialMove_Sp */
extern char g_modelPartNameFormat[5];                /* 0x007C228E conf 0.85: Builds the per-part resource prefix ("sp" + part id) for the 47x6 part loop of BattleScene_BindUnitModelResources; the r */
extern char g_aniFileSuffixFormat[7];                /* 0x007C2293 conf 0.85: Appends the animation-resource extension: "%s.ani" turns the part prefix into the animation file name loaded from the ba */
extern char g_bxonFileSuffixFormat[8];               /* 0x007C229A conf 0.85: Appends the .bxon extension (binary object/animation container) when building the part's resource path. */
extern char g_bchFileSuffixFormat[7];                /* 0x007C22A2 conf 0.85: Appends the .bch model extension when building the part's model resource path. */
extern char g_modelPartNameFormatB[5];               /* 0x007C22C4 conf 0.85: Second copy of the part-name format, used by the extra pass that BattleScene_BindUnitModelResources runs for unit id 400 */
extern char g_aniFileSuffixFormatB[7];               /* 0x007C22C9 conf 0.85: Second copy of the animation-file format, used by the unit-400 extra pass of BattleScene_BindUnitModelResources. */
extern char g_bxonFileSuffixFormatB[8];              /* 0x007C22D0 conf 0.85: Second copy of the .bxon format, used by the unit-400 extra pass of BattleScene_BindUnitModelResources. */
extern char g_bchFileSuffixFormatB[7];               /* 0x007C22D8 conf 0.85: Second copy of the .bch format, used by the unit-400 extra pass of BattleScene_BindUnitModelResources. */
extern u32 g_actorBaseClass;                         /* 0x007C33D4 conf 0.55: Static class-descriptor (type-info node) of the engine's base actor class: the class that PlayerBattleActor, EnemyBattle */
extern u32 g_enemyBattleActorClass;                  /* 0x007C428C conf 0.60: Static class-descriptor of the battle enemy-actor class 'EnemyBattleActor' (parent = g_actorBaseClass). Battle UI/action */
extern u32 g_enemyBattleActorNizuzerufaClass;        /* 0x007C42A0 conf 0.55: Static class-descriptor of the enemy battle-actor subclass registered as 'EnemyBattleActor_Nizuzerufa' (parent = g_enemy */
extern f32 maybe_g_actorDisplayOffset[3];            /* 0x007C4304 conf 0.40: Three-float offset added to battle actor/effect placement: the EnemyDesertWhale class registration seeds it with (0, 0,  */
extern u32 g_attachVehicleActor3DClass;              /* 0x007C4E14 conf 0.60: Static class-descriptor of the field actor class 'AttachVehicleActor3D' (parent = g_actorBaseClass). The battle action-U */
extern u32 g_playerBattleActorClass;                 /* 0x007C5014 conf 0.60: Static class-descriptor of the battle player-actor class 'PlayerBattleActor' (parent = g_actorBaseClass), i.e. the type  */
extern f32 g_battleLayoutOrigin[3];                  /* 0x007C5120 conf 0.55: Battle layout origin as three floats: maybe_BattleScene_LayoutUnitModel_2 places units on a line at 'origin.y' (it copie */
extern f32 g_battleEntryPosition[3];                 /* 0x007C512C conf 0.50: Three-float position where a unit is put at the start of the battle slide-in: BattleScene_ApplyUnitSlideTransform copies */
extern f32 g_battleUnitSlotPos2[3];                  /* 0x007C5138 conf 0.55: Three-float (x, 0, z) battle position of unit-layout slot 2 (-5.4, 0, -2.33): the index==2 branch of BattleScene_ApplyUn */
extern f32 g_battleUnitSlotPos1[3];                  /* 0x007C5144 conf 0.55: Three-float (x, 0, z) battle position of unit-layout slot 1 (5.48, 0, -2.32): the index==1 branch of BattleScene_ApplyUn */
extern f32 g_battleUnitSlotPos0[3];                  /* 0x007C5150 conf 0.55: Three-float (x, 0, z) battle position of unit-layout slot 0 (-3.51, 0, 4.66): the index==0 branch of BattleScene_ApplyUn */
extern f32 g_battleUnitSlotPos3[3];                  /* 0x007C515C conf 0.55: Three-float (x, 0, z) battle position of unit-layout slot 3 (3.52, 0, 4.62): the index==3 branch of BattleScene_ApplyUni */
extern f32 g_battleUnitSlotPos4[3];                  /* 0x007C5168 conf 0.55: Three-float (x, 0, z) battle position of unit-layout slot 4 (0, 0, 7.24), the front-centre slot: the index==4 branch of  */
extern f32 maybe_g_battleScrollOffsetTable[16];      /* 0x007C5180 conf 0.45: Eight (min, max) float pairs read by maybe_Battle_Ui_UpdateScrollAnimation: entry i is fetched at +i*8 as the start/end  */
extern u32 maybe_g_actorListNodePoolTail[2];         /* 0x007C8578 conf 0.40: Last node of the static actor-list node pool that Field_InitActorListNodePool builds: it chains the six 0x58-byte nodes  */
extern u32 maybe_g_modelClass;                       /* 0x007E2164 conf 0.45: Static class-descriptor (type-info node) of the loaded model/animation instance class: every resource loader validates t */
extern f32 maybe_g_defaultBasisVector2[3];           /* 0x007E700C conf 0.35: Second of the five consecutive 12-byte (3-float) default-vector entries at 0x7E7000..0x7E703C that object constructors c */

/* --- Battle2D --- */
extern char g_strBattle2DEnemyModelPath[24];         /* 0x007C2246 conf 0.95: Path format string "2d/battle2/enemy/%s.bch" used by Battle2D_LoadEnemyModel to load 2D battle enemy model assets by nam */
extern char g_fmtStr[3];                             /* 0x007C225E conf 0.95: Format string "%s" used by Battle2D_LoadBackgroundModel to format string parameters into a path buffer. */
extern char g_fmtDec[3];                             /* 0x007C2261 conf 0.95: Format string "%d" used by Battle2D_LoadBackgroundModel to format integer variant numbers (e.g. variant + 1) into a path */
extern char g_strBattle2DBackgroundModelPath[29];    /* 0x007C2264 conf 0.95: Path format string "2d/battle2/background/%s.bch" used by Battle2D_LoadBackgroundModel to load 2D battle background mode */

/* --- Battle2DScene --- */
extern void* g_battleSceneVtable[26];                /* 0x0077F7C8 conf 0.80: Primary vtable of the 2D battle scene controller (Battle2DScene): installed by Battle2DScene_Create (0x006059A0) and res */

/* --- BattleEndToDefaultField --- */
extern f32 maybe_g_battleEndFieldFadeValue;          /* 0x00728AA0 conf 0.40: Float 1.0 in rodata read by BattleEndToDefaultField into local_1c (a fade/time value passed while switching back to the  */

/* --- Bg2D --- */
extern u8 g_bg2dLayerPageSearchOrder[8];             /* 0x007275DC conf 0.70: Search order for the four Bg2D layer texture pages (2x u8[4]): bytes 4..7 are each layer's first-choice page id (3,0,1,2 */

/* --- Camera --- */
extern u8 g_cameraTargetFilterAll[4];                /* 0x007272A4 conf 0.60: Option bytes handed to Camera_IsCandidateVisible: byte 0 also rejects candidates whose hidden flag is set, byte 1 also r */
extern u8 g_cameraTargetFilterNoRadius[4];           /* 0x007272A8 conf 0.55: Same option pair as g_cameraTargetFilterAll but byte 1 is 0, so only the hidden-flag test runs and the distance/radius t */
extern void* g_battleCameraRangeVtable[24];          /* 0x007731C8 conf 0.50: Vtable installed by the 0x50-byte battle-camera range object built by the constructor at 0x0046E8B8 (called from maybe_F */
extern void* g_battleCameraRangeVtableB[24];         /* 0x0077B190 conf 0.50: Sibling battle-camera range vtable of the same 24-word shape, installed by the constructor at 0x004E5B3C, which also see */
extern void* g_cameraShakeWorkVtable[4];             /* 0x0077D85C conf 0.70: Vtable (4 words) of the 0x94-byte camera-shake work registered under the name 'ReguralyShake': word 0 null, word 1 the d */
extern f32 g_cameraManualYawSpeed;                   /* 0x007A6050 conf 0.60: Pad-yaw speed: Camera_UpdateManualYaw multiplies the stick yaw delta by this before adding it to the camera yaw (retail  */
extern f32 maybe_g_cameraOccludedHeightOffset;       /* 0x007A6058 conf 0.45: Target value for the camera's vertical collision offset f_268 in Camera_ResolveCollision on the branch that uses the sto */
extern f32 maybe_g_cameraBoomDecay;                  /* 0x007A605C conf 0.45: Per-frame decay applied to the camera boom length f_15c at the end of Camera_ResolveCollision (f_15c -= f_15c * k). Reta */
extern f32 maybe_g_cameraBoomLerpA;                  /* 0x007A6060 conf 0.40: Ease rate for the boom length f_158 in Camera_ResolveCollision on the branch where the stored collision-history entry is */
extern f32 maybe_g_cameraBoomLerpB;                  /* 0x007A6064 conf 0.40: Ease rate for the boom length f_158 on the opposite branch of Camera_ResolveCollision (no valid history entry); retail 0 */
extern f32 g_cameraAutoYawGain;                      /* 0x007A6068 conf 0.50: Gain applied to the per-frame yaw delta in Camera_Update's auto/gyro camera branch, after the delta is converted to degr */
extern f32 g_cameraAutoYawMaxDegrees;                /* 0x007A606C conf 0.50: Upper bound, in degrees per frame, on how far the auto/gyro camera may turn at once: Camera_Update clamps the computed a */
extern f32 g_cameraTargetEyeScale;                   /* 0x007A6070 conf 0.60: Scale of the last camera transition target (Camera.f_108), published by Camera_SetTransitionTarget and read back by Came */
extern f32 g_cameraTargetEyeDistance;                /* 0x007A6074 conf 0.65: Distance of the last camera transition eye position from the world origin (sqrt of the new eye vector), published by Cam */
extern f32 maybe_g_cameraSetupAngleDegrees;          /* 0x007A6078 conf 0.35: Published camera angle in degrees: Camera_SetupFromActor writes self->f_114 (radians) times 57.29578 here. No reader was */
extern f32 maybe_g_defaultCameraParam;               /* 0x007A6148 conf 0.35: Default float copied into Camera+0x28 by maybe_Camera_InitOrbitParams (camera constructor path) and into UiModelView f_1 */
extern f32 maybe_g_cameraStereoRollDegrees;          /* 0x007A6184 conf 0.45: Roll angle in degrees used by maybe_Camera_UpdateStereoSmoothing: it is scaled by 0.01745329 (deg->rad) and stored in Ca */
extern u8 maybe_g_cameraPathProbeFlag;               /* 0x007A63E1 conf 0.40: Byte switch in maybe_Camera_UpdateWorkPathEx: when non-zero, a successful sprite/occlusion test is followed by an extra  */
extern u32 g_cameraPathInitGuard;                    /* 0x007A63E4 conf 0.60: Static-initialisation guard word at +0xC of the 0x7A63D8 camera-path block. maybe_Camera_UpdateWorkPathEx tests bit 0 an */
extern u8 g_nullWorkEntry[0x88];                     /* 0x007A6428 conf 0.70: Zero-filled 'null object' (0x88 bytes) that stands in for a missing per-screen work-entry detail pointer: camera, UI row */
extern u8 g_nullCameraWork[0x58];                    /* 0x007A64B0 conf 0.60: Second zero-filled null object, used where a camera-work pointer is 0 (target finding, work list, work-path update and b */
extern u8 g_distanceScaleConfig[0x28];               /* 0x007A8B80 conf 0.55: Base of the 0x28-byte distance-scale config used by maybe_Camera_ComputeDistanceScale to shrink billboards/overlays with */
extern u8 g_distanceScaleConfigEnableB;              /* 0x007A8B81 conf 0.55: Byte +1 of g_distanceScaleConfig: second on/off switch of the distance scaling (the factor built from the object field f */
extern f32 g_distanceScaleConfigFarDistance;         /* 0x007A8B8C conf 0.50: Far end of the first distance range at +0xC of g_distanceScaleConfig: distances above it clamp to this value before the  */
extern f32 g_distanceScaleConfigMaxScale;            /* 0x007A8B90 conf 0.50: Maximum output scale at +0x10 of g_distanceScaleConfig; the routine divides the clamped distance by (this - the +0x14 mi */
extern f32 g_distanceScaleConfigNearDistanceB;       /* 0x007A8B9C conf 0.50: Near end of the second distance range at +0x1C of g_distanceScaleConfig (the range used by the model-width factor); the  */
extern f32 g_distanceScaleConfigMaxScaleB;           /* 0x007A8BA0 conf 0.50: Maximum output scale at +0x20 of g_distanceScaleConfig for the second (model-width) factor; the minimum is at +0x24. Ret */
extern f32 g_cameraTransitionTarget[3];              /* 0x007C51C0 conf 0.65: World-space look-at target (x,y,z) of the last camera transition, written by Camera_SetTransitionTarget and re-read by C */
extern f32 maybe_g_cameraAnchorOffsetA[3];           /* 0x007C51CC conf 0.40: First of two zero offset vectors that maybe_Camera_ComputeAnchorPoint rotates by the player's forward quaternion and add */
extern f32 maybe_g_cameraAnchorOffsetB[3];           /* 0x007C51D8 conf 0.40: Second zero offset vector added by maybe_Camera_ComputeAnchorPoint after the first one (0x7C51CC); both are rotated by t */
extern f32 g_stereoEyeOffsetLeft[3];                 /* 0x007C51F0 conf 0.55: Left-eye offset added to the camera eye by Camera_CalcStereoEyePositions (the 3DS parallax shift), together with a base  */
extern f32 g_fieldCameraOffset[3];                   /* 0x007C5208 conf 0.50: Constant world-space offset added to both the eye and the target of the field camera every frame in Camera_Field_Update. */
extern f32 maybe_g_cameraProbeOffset[3];             /* 0x007C522C conf 0.45: Offset/direction vector used by maybe_Camera_UpdateWorkPathEx when a sprite or occlusion probe hits: the probe point is  */

/* --- Casino --- */
extern s32 g_slotReelColumnOffset[5];                /* 0x0072AB4C conf 0.60: Column offset of each of the five slot reels inside one interleaved symbol row. Casino_Slot_PickStopBySymbol reads table */
extern u32 g_slotJackpotDelegate[2];                 /* 0x0072AC78 conf 0.55: Two-word C++ pointer-to-member-function delegate {function = Ui_Delegate_BindActionB, this-adjust = 0}. Casino_Slot_Buil */
extern void* g_slotWinTextLine0Vtable[5];            /* 0x0075E0AC conf 0.60: Method table for line 0 of the slot machine's win-message text. Word +8 is Ui_MessageVoice_UpdateLine0, which starts/rev */
extern void* g_slotWinTextLine1Vtable[5];            /* 0x0075E0D4 conf 0.60: Method table for line 1 of the slot machine's win-message text (word +8 = Ui_MessageVoice_UpdateLine1). Registered by Ca */
extern void* g_slotWinTextLine2Vtable[5];            /* 0x0075E0FC conf 0.60: Method table for line 2 of the slot machine's win-message text (word +8 = Ui_MessageVoice_UpdateLine2). Registered by Ca */
extern void* g_slotWinTextLine3Vtable[5];            /* 0x0075E124 conf 0.60: Method table for line 3 of the slot machine's win-message text (word +8 = Ui_MessageVoice_UpdateLine3). Registered by Ca */
extern void* g_slotWinTextLine4Vtable[5];            /* 0x0075E14C conf 0.60: Method table for the last (line 4) win-message text: word +8 is Ui_MessageVoice_FinishLine4, which releases the voice ha */
extern void* g_slotWinTextCycleNodeVtable[5];        /* 0x00760458 conf 0.55: Win-text id cycling node: pushes a new string id on the first and 0x49th step, plays the matching SEs and finishes when  */
extern void* g_slotDigitRollNodeVtable[5];           /* 0x0076046C conf 0.70: Five-digit rolling-counter animation node: exec maybe_Ui_DigitRoll_Update scrolls the five payout digits over 0x2E frame */
extern void* g_slotWinTextLayoutNodeVtable[5];       /* 0x00762F88 conf 0.55: Win-message layout node: exec maybe_Ui_TextBuild_Start lays out the up-to-three parts of the message, plays SE 0xE70 whe */
extern void* g_slotWinLineANodeVtable[5];            /* 0x00762F9C conf 0.75: Win-line A presentation node: on its first call it hides the spinning symbols, resets the payout rows and evaluates the  */
extern void* g_slotWinLineBNodeVtable[5];            /* 0x00762FB0 conf 0.75: Win-line B presentation node (row B of the payline evaluation). Same one-shot hide/reset/evaluate pattern as win line A; */
extern void* g_slotWinLineCNodeVtable[5];            /* 0x00762FC4 conf 0.75: Win-line C presentation node (row C of the payline evaluation). Same one-shot hide/reset/evaluate pattern as win line A; */
extern void* g_slotWinLineDNodeVtable[5];            /* 0x00762FD8 conf 0.75: Win-line D presentation node (row D / default row of the payline evaluation). Also the default line node that maybe_Ui_S */
extern void* g_slotDisplayScaleNodeVtable[5];        /* 0x00766008 conf 0.55: One-shot node that scales the slot display by the payout rank (Casino_Slot_GetPayoutRank returns 0/1/2 mapped to 1/10/10 */
extern void* g_slotWinTransitionNodeVtable[5];       /* 0x0076601C conf 0.50: Win-presentation transition controller: waits for the message widget, starts cue 0x3A/0x3B, fades the window out and fin */
extern void* g_slotDelegateNodeVtable[5];            /* 0x00766030 conf 0.60: One-shot node that invokes the pointer-to-member-function stored at node+0x10/+0x14 (exec Ui_Delegate_Invoke) and report */
extern void* g_slotWinMessageRowsNodeVtable[5];      /* 0x00766044 conf 0.55: Win-message row animation node: lays out up to three message rows, starts cue 0x3A/0x3B/0x3C and finishes when the messa */
extern void* g_casinoSlotVtable[10];                 /* 0x00766DC4 conf 0.75: Class table of the Casino_Slot object (the 5880-byte slot-machine part that the casino window embeds at +0x11C). Word 0  */
extern void* g_slotPayoutSequenceNodeVtable[5];      /* 0x00768D2C conf 0.65: Credit/payout presentation sequence: at frame 0 it starts the payout animation and its SE, at 0x14 switches the machine  */
extern void* g_slotReelStopSequenceNodeVtable[5];    /* 0x00768D40 conf 0.65: Reel-stop sequence: writes the reel result, plays the stop SE and after 0x29 frames attaches the per-line result object  */
extern void* g_slotMachineStateNodeVtable[5];        /* 0x00768D54 conf 0.55: One-shot slot-machine command: refreshes the payout display from map state, copies the request flags into Casino_Slot+0x */
extern void* g_slotDisplayByte173NodeVtable[5];      /* 0x00768D68 conf 0.60: One-shot node that writes its byte at +0x10 into Casino_Slot+0x173 (one of the two bet/credit digit fields) and finishes */
extern void* g_slotDisplayByte171NodeVtable[5];      /* 0x0076B7B8 conf 0.60: One-shot node that writes its byte at +0x10 into Casino_Slot+0x171 (the other bet/credit digit field) and finishes. Casi */
extern void* g_slotWidgetPollNodeVtable[5];          /* 0x0076B7CC conf 0.55: Short poll node: increments its +0x10 counter and finishes after 5 frames or as soon as the slot widget at Casino_Slot+0 */
extern void* g_slotPayoutCounterNodeVtable[5];       /* 0x0076E2AC conf 0.65: Payout count-up animation node: snapshots the medal counter, interpolates the seven gauge segments toward the new total  */
extern void* g_slotWinSequenceNodeVtable[5];         /* 0x00771B24 conf 0.55: Long slot win-result timeline: at frame 0x14 it stops all reels and applies the row state, at 0x19/0x1E/0x23/0x28/0x2D i */
extern void* g_casinoSlotDisplayVtable[10];          /* 0x00776084 conf 0.75: Class vtable of the casino slot display / digit-panel object installed by Casino_SlotMachine_DigitPanel_Ctor. Slots +0/+ */
extern void* g_casinoPokerWindowVtable[10];          /* 0x0077A2B8 conf 0.90: Class vtable of Casino_PokerWindow (the 560-byte poker window): +0 Casino_PokerWindow_DtorBase, +4 Casino_PokerWindow_Dt */
extern char* g_casinoSlotDetachedObjectNames[3];     /* 0x007AA048 conf 0.60: Three layout-object names that Casino_Slot_InitPanes looks up and detaches at start-up: "win_talk", "win_yesno" and "coi */
extern char* g_slotDigitLightAnimNames[3];           /* 0x007AA158 conf 0.65: Animation names "light_l", "light_c" and "light_r" played while the slot digit counter steps: maybe_Casino_Slot_StepDigi */
extern u8 g_slotShuffleInitFlag;                     /* 0x007C22FC conf 0.65: Once-only guard byte for the function-local static shuffle state g_slotShuffleState used by Casino_Slot_PickStopBySymbol */
extern u32 g_slotShuffleState[57];                   /* 0x00839800 conf 0.60: 228-byte BSS state of the function-local static shuffle used by Casino_Slot_PickStopBySymbol: a 54-entry (0x36) permutat */

/* --- Container --- */
extern void* g_smithSequenceStateCallbacks[10];      /* 0x0072863C conf 0.65: Callback transition table for the Fun-Size Forge (Smith) sequence; each entry is a pair {void (*func)(void), void *ctx}  */
extern void* g_sortListWindowItemDelegates[16];      /* 0x00729B80 conf 0.60: Pointer-to-member-function delegate table for Ui_SortListWindow / Ui_EquipWindow; pairs {code *fn, u32 adj} dispatching  */
extern u32 maybe_g_nullListDescriptor[2];            /* 0x0072B3AC conf 0.40: Two-word zero constant {0, 0} loaded by maybe_Container_List_InitAt5C to clear or initialize a double-linked node pointe */
extern void* g_rowListObjectVtable[11];              /* 0x0075A6C8 conf 0.60: Virtual method table installed into the primary vptr of RowList/Container objects by maybe_Container_CreateObject. */
extern void* g_rowListPresentVtable[16];             /* 0x0075A6F4 conf 0.60: Virtual method table for the presentation / layout sub-component of RowList/StringMap containers; contains methods for p */
extern void* g_menuCampVtable[14];                   /* 0x0075BB68 conf 0.65: Virtual method table for the Camp menu (Menu_Camp) slot interface; methods handle camp slot status, visibility, readines */
extern void* g_uiPagerWindowVtable[10];              /* 0x0075E274 conf 0.65: Virtual method table for Ui_PagerWindow / widget paging container; dispatches page number initialization, child pane vis */
extern void* g_uiIntrusiveListWidgetVtable[16];      /* 0x0075E90C conf 0.60: Virtual method table for intrusive list UI widget; installed by Container_IntrusiveList_Dtor during object teardown. */
extern void* g_containerList3Vtable[2];              /* 0x0075E9A4 conf 0.65: Virtual destructor table for 3-element container lists; installed by maybe_Container_List3_Dtor during list destruction. */
extern void* g_containerList15Vtable[2];             /* 0x0075E9B4 conf 0.65: Virtual destructor table for 15-element container lists; installed by maybe_Container_List15_Dtor during list destructio */
extern void* g_containerListPairBaseVtable[6];       /* 0x00760550 conf 0.60: Base virtual method table for Container_ListPair; restored by maybe_Container_InitListPair during sub-list teardown. */
extern void* g_containerNameHashBaseVtable[4];       /* 0x007610D4 conf 0.70: Base virtual method table for Container_NameHash objects; installed by Container_NameHash_Ctor with pure virtual sentine */
extern void* g_containerNameHashVtable[4];           /* 0x0076111C conf 0.75: Full virtual method table for Container_NameHash; recorded in structs.json as the definitive class vtable. */
extern void* g_containerNamedLinkNodeVtable[2];      /* 0x00762E34 conf 0.65: Virtual method table for named linked container nodes; holds destructor and link-by-name methods. */
extern void* g_uiObjectBaseVtable[12];               /* 0x0076334C conf 0.65: Base virtual method table for UI objects and container nodes; restored by maybe_Ui_Object_Dtor and node destructor varia */
extern void* g_uiNodeListMenuHandlerVtable[12];      /* 0x0076BA90 conf 0.65: Virtual method table for the menu display handler node created by maybe_Container_NodeList_Init; methods ensure menu dis */
extern void* g_stringMapWidgetVtable[12];            /* 0x0076E1B0 conf 0.65: Virtual method table for string-map widget component; installed by maybe_Container_StringMap_Ctor at sub-object offset + */
extern void* g_uiHandleListWindowVtable[10];         /* 0x0076FF14 conf 0.65: Virtual method table for handle-list window container; dispatches animation updates, handle lifetime checks, and transit */
extern void* g_uiSortListWindowVtable[11];           /* 0x007702FC conf 0.70: Virtual method table for Ui_SortListWindow; installed by constructor at 0x00448800 and used for header binding and row l */
extern void* g_uiNodeListObject2DHandlerVtable[12];  /* 0x00771ECC conf 0.65: Virtual method table for 2D field object handler node created by maybe_Container_NodeList_Init; dispatches child window  */
extern void* g_uiNodeListHandler5Vtable[12];         /* 0x00771F00 conf 0.60: Virtual method table for the fifth handler node in the 2D scene node list created by maybe_Container_NodeList_Init. */
extern void* g_uiNodeListHandler6Vtable[12];         /* 0x00771F38 conf 0.60: Virtual method table for the sixth handler node in the 2D scene node list created by maybe_Container_NodeList_Init. */
extern void* g_uiNodeListHandler7Vtable[12];         /* 0x00773EB4 conf 0.60: Virtual method table for the seventh handler node in the 2D scene node list created by maybe_Container_NodeList_Init. */
extern void* g_uiNodeListSakusenHandlerVtable[12];   /* 0x00773EEC conf 0.70: Virtual method table for the tactics/strategy (Sakusen) detail handler node created by maybe_Container_NodeList_Init; ma */
extern void* g_uiNodeListAnimHandlerVtable[12];      /* 0x00775980 conf 0.65: Virtual method table for animation instance list handler node created by maybe_Container_NodeList_Init; manages animatio */
extern void* g_containerNameHandleVtable[11];        /* 0x007759C8 conf 0.70: Virtual method table for Container_NameHandle; installed by constructor at 0x004A7C08; matches Container_NameHandle clas */
extern void* g_containerListPairDerivedVtable[12];   /* 0x00776D84 conf 0.65: Derived virtual method table for Container_ListPair / path point list; holds path generation and list cleanup methods. */
extern void* g_containerListNodeVtable[8];           /* 0x00778F00 conf 0.65: Virtual method table for Container_ListNode / battle effect list nodes; installed by constructor at 0x004D2AA0. */
extern void* g_uiHandleListSubVtable[12];            /* 0x00780AC0 conf 0.60: Secondary virtual method table for handle list sub-components; installed by maybe_Container_HandleList_Ctor at sub-objec */
extern void* g_uiBagListHandleVtable[12];            /* 0x00780AD8 conf 0.65: Virtual method table for inventory bag list handle component; installed by maybe_Container_HandleList_Ctor at sub-object */
extern void* g_containerAbstractPureVtable[7];       /* 0x007810E8 conf 0.70: Pure virtual interface vtable for abstract container objects; all 7 method slots point to __cxa_pure_virtual (0x00101A9F */
extern void* g_gfxOverlayBatchVtable[1];             /* 0x00782080 conf 0.65: Virtual method table for graphics overlay batch / list object; installed by maybe_Container_InitListObject and used duri */
extern void* g_gfxMaterialSetVtable[14];             /* 0x00782210 conf 0.65: Virtual method table for graphics material set component installed at offset +0x60 of objects by maybe_Container_CreateO */
extern void* g_gfxSceneNodeBaseVtable[12];           /* 0x007826D8 conf 0.70: Base virtual method table for Gfx_SceneNode objects; installed by Container_List_Init and Gfx_SceneNode_DtorBase. */
extern void* g_gfxSceneNodeVtable[10];               /* 0x00782704 conf 0.75: Primary virtual method table for Gfx_SceneNode; recorded in structs.json as the definitive class vtable for Container_Li */
extern void* g_containerNamedMapKeyVtable[1];        /* 0x00782750 conf 0.65: Virtual table / type header for temporary lookup key nodes in Container_NamedMap and hash tables; assigned to stack-allo */
extern void* g_uiSortListWindowSubVtable[4];         /* 0x00782E98 conf 0.60: Secondary virtual method table for Ui_SortListWindow sub-component installed at offset +0x11C by maybe_Container_Intrusi */
extern void* g_namedObjectRegistryHead[2];           /* 0x007A30B8 conf 0.60: Two-word linked list head descriptor in .data section initialized by maybe_Container_NamedObjectRegistry_Create. */
extern void* g_containerAllocatorInstance;           /* 0x007AEABC conf 0.70: Global allocator pointer in .data; dereferenced by operator delete / maybe_Container_DestroyObject to invoke virtual dea */
extern void* g_activeContainerListContext;           /* 0x007AED40 conf 0.60: Global active list / texture resource container pointer in .data; written by Container_InitList and read during GPU text */
extern void* g_namedObjectRegistryList[5];           /* 0x007C331C conf 0.65: Circular double-linked list root node (20 bytes) in BSS initialized by maybe_Container_NamedObjectRegistry_Create with s */
extern ContainerInlineVector g_globalUniqueIdList;   /* 0x007C859C conf 0.70: Global 36-byte InlineVector in BSS initialized by Font_InitGlyphBitmapPools; holds active unique IDs and resources with  */
extern void* g_tagTypeResourceRegistry[6];           /* 0x007C85F0 conf 0.65: Global 24-byte resource registry object in BSS initialized by Mem_BitmapPool_Init; queried by tag and type to resolve pa */

/* --- CreateEffect2D --- */
extern char g_strStart[6];                           /* 0x007BFB40 conf 0.95: String literal "Start" used as the initial animation tag or trigger name for 2D effects, roulette wheel animations, and  */

/* --- Cutscene --- */
extern u32 g_cutsceneSceneVtable[7];                 /* 0x00766E7C conf 0.90: Vtable of the Cutscene_Scene class: slot 0 creates the actor models, slots 1-5 are the scene's layout/script helpers and */
extern u8 maybe_g_cutsceneToggleFlag;                /* 0x007A2CFC conf 0.40: One-byte latch toggled between 0 and 1 by Cutscene_AdvanceTimeline while action bit 0x1000 is set in the input snapshot  */
extern u32 g_cutSceneActorClassRecord[5];            /* 0x007C34C0 conf 0.85: Named class record for the 'CutSceneActor' actor type: three intrusive list words (+0x0..+0x8), a parent-class pointer ( */
extern u32 g_cutScenePlayerActorClassRecord[5];      /* 0x007C34D4 conf 0.85: Named class record for the 'CutScenePlayerActor' type, the player-controlled actor in a cutscene: parent pointer +0xC =  */
extern u32 maybe_g_listPanelClassRecord[6];          /* 0x007C8608 conf 0.45: Static class record for the four-row list-panel window class (vtable 0x00762FEC): +0xC parent descriptor 0x007E2000, +0x */

/* --- Data --- */
extern u8 g_partyComboSortOrder[37];                 /* 0x0072C618 conf 0.85: Permutation table of 37 category indices (0x00..0x24) grouping the 7 party members and 30 pairwise combinations by prima */
extern u32 g_heroMotionTableInitGuard;               /* 0x007A3728 conf 0.90: One-time static initialization guard word for the Hero battle motion table g_heroMotionRecordTable (0x007C3698). Checked */
extern u32 g_formatMessageArgInitGuard;              /* 0x007A70BC conf 0.90: One-time static initialization guard word for the formatted message argument buffer (0x007C55DC). Checked and set via fu */
extern u32 g_itemModelPathInitGuard;                 /* 0x007A70C0 conf 0.90: One-time static initialization guard word for the item BCH model path buffer g_itemModelPathBuffer (0x007C57E0). Checked */
extern u8 g_heroMotionRecordTable[2988];             /* 0x007C3698 conf 0.85: Static table of 83 Hero battle animation string records (0x24 bytes each, total 2988 bytes). First 23 entries hold anima */
extern u8 g_itemModelPathBuffer[68];                 /* 0x007C57E0 conf 0.85: Static string object in BSS used by maybe_Data_ResolveRelativeEntry8OrTrap to format default item model resource paths ( */

/* --- Debug --- */
extern u32 g_debugLogRingIndex;                      /* 0x007A7420 conf 0.85: Current slot index (0..9) in the 10-entry debug log ring buffer (g_debugLogRingBuffers at 0x007C5A44). Incremented modul */
extern u16 g_debugLogRingBuffers[2560];              /* 0x007C5A44 conf 0.85: Ring buffer of 10 UTF-16 string slots (each 256 u16 characters / 512 bytes, 2560 u16s total). Written by Debug_AppendLog */

/* --- Effect2DMove --- */
extern void* g_uiSpriteMoveToVtable[5];              /* 0x00775580 conf 0.85: Vtable of the Ui_SpriteMoveTo 2D sprite interpolation controller (class size 44 / 0x2C); installed by Effect2DMove (0x00 */

/* --- Effect2DPlay --- */
extern void* g_effect2DPlayVtable[5];                /* 0x0077B1F8 conf 0.75: Vtable of the 2D effect playback controller object (class size 40 / 0x28); installed by Effect2DPlay (0x00149454) into n */

/* --- Engine --- */
extern void* g_gfxCmdListBaseVtable[8];              /* 0x007821E8 conf 0.75: Base class vtable for the graphics command list singleton (installed in the 52-byte object at 0x00834040 during inlined  */
extern void* g_gfxRenderContextVtable[10];           /* 0x00782220 conf 0.80: Primary vtable of the graphics render context / display presenter singleton (the 0x1F8-byte object at 0x00834084, refere */
extern void* g_fsChannelTableVtable[11];             /* 0x0078295C conf 0.75: Multi-inheritance vtable for the filesystem channel table / worker manager class (the 0xE3C8-byte object at 0x007F52E4,  */
extern void* g_fsCacheEvictMonitorVtable[5];         /* 0x007829F4 conf 0.75: Vtable of the filesystem cache eviction and task monitor controller (the 20-byte object at 0x00833F54, referenced by *0x */
extern void* g_gfxCmdListVtable[6];                  /* 0x00782A30 conf 0.80: Primary vtable of the graphics command list singleton class (the 52-byte object at 0x00834040, pointed to by *0x007BE350 */
extern void* g_gfxRenderContextSecondaryVtable[6];   /* 0x00782A44 conf 0.80: Secondary vtable of the graphics render context singleton class (installed at sub-object offset 0x60 within the 0x1F8-by */
extern void* g_gfxDefaultTextureVtable[5];           /* 0x00782A58 conf 0.75: Vtable of the graphics default texture / framebuffer texture manager class (the 20-byte object at 0x0083428C, stored in  */
extern u8 g_engineRuntimeFlags[4];                   /* 0x007AE49C conf 0.85: Four-byte engine runtime status and lifecycle control flags. Byte 0 is the engine termination request flag checked by th */
extern u8 g_engineEarlyExitFlag;                     /* 0x007AE5AC conf 0.85: One-byte latch recording whether an engine exit was already requested before subsystem initialization began. If non-zero */
extern u8 g_fsCacheEvictMonitorGuardFlag;            /* 0x007BE334 conf 0.80: Initialization guard byte for the filesystem cache eviction monitor singleton. Initialized in the retail data image to 1 */
extern void* g_fsCacheEvictMonitor;                  /* 0x007BE338 conf 0.80: Global pointer to the filesystem cache eviction and task monitor controller singleton. Points to the 20-byte object in B */
extern u8 g_gfxCmdListGuardFlag;                     /* 0x007BE34C conf 0.85: Initialization guard byte for the graphics command list singleton. Retail image value is 1 (0xFFFFFF01 word); cleared to */
extern void* g_gfxCmdList;                           /* 0x007BE350 conf 0.85: Global pointer to the graphics command list / overlay draw manager singleton. Points to the 52-byte object at 0x00834040 */
extern u8 g_gfxDefaultTextureGuardFlag;              /* 0x007BE35C conf 0.80: Initialization guard byte for the graphics default texture / framebuffer texture manager singleton. Retail image word is */
extern void* g_gfxDefaultTexture;                    /* 0x007BE360 conf 0.80: Global pointer to the default texture / framebuffer texture manager singleton. Points to the 20-byte object in BSS at 0x */
extern u32 g_engineFrameCallbackLists[45];           /* 0x007C8674 conf 0.85: Engine frame callback registry containing 5 callback lists (each with a 4-byte count and 4 eight-byte callback function/ */
extern u8 g_fsCacheSet[0x3C];                        /* 0x007CF324 conf 0.85: Global filesystem cache set and background task descriptor object (60 bytes in BSS). Manages cache entry queues, evictio */
extern u8 g_fsCacheEvictMonitorBuffer[0x14];         /* 0x00833F54 conf 0.80: Static memory buffer (20 bytes in BSS) hosting the filesystem cache eviction monitor singleton instance pointed to by g_ */
extern u8 g_gfxCmdListBuffer[0x34];                  /* 0x00834040 conf 0.85: Static memory buffer (52 bytes in BSS) hosting the graphics command list singleton instance pointed to by g_gfxCmdList ( */
extern u8 g_gfxDefaultTextureBuffer[0x14];           /* 0x0083428C conf 0.80: Static memory buffer (20 bytes in BSS) hosting the default texture / framebuffer texture manager singleton instance poin */

/* --- Event --- */
extern f32 g_beeRiseMaxDuration;                     /* 0x00726550 conf 0.85: Maximum duration (10.0f) for the bee-rise field event sequence in Event_BeeRise_Start. The computed duration derived fro */
extern char* g_cutsceneCommandEventNames[6];         /* 0x00728A88 conf 0.85: Six-entry table of string pointers holding cutscene script hook event names ("OnPreSetupLevel", "OnSetupScene", "OnBegin */
extern void* g_eventActorSlotModelVtable[43];        /* 0x00769228 conf 0.85: Virtual method table installed on 0xBC-byte ActorSlotModel instances by Event_ActorModels_CreateSlotModel; shares UI scr */
extern void* g_eventActorModelsVtable[38];           /* 0x00776F38 conf 0.85: Virtual method table of the event actor model manager (EventActorModels / ActorModelSet). Slot 1 is destructor Event_Act */
extern void* g_eventGimmickVtable[11];               /* 0x0077C404 conf 0.85: Virtual method table for the field-gimmick base action object. Slot 1 is deleting destructor 0x004F0F48, slot 2 is start */
extern void* g_eventBeeRiseVtable[11];               /* 0x0077C438 conf 0.85: Virtual method table for the bee-rise field-gimmick subclass. Slot 1 is deleting destructor 0x004F128C, slot 2 is Event_ */
extern void* g_eventSkullRunVtable[11];              /* 0x0077C46C conf 0.85: Virtual method table for the skull-run field-gimmick subclass. Slot 1 is destructor 0x004F1894, slot 2 is 'Skull_Run' ha */
extern void* g_eventClimbVtable[11];                 /* 0x0077C4D4 conf 0.85: Virtual method table for the climb (ladder/rope) field-gimmick action. Slot 1 is destructor 0x004F23D4, slot 2 is climb  */
extern u32 g_eventDispatchField39InitGuard;          /* 0x007A3030 conf 0.90: One-time static initialization guard word for the 4-entry command dispatch table g_eventDispatchField39Table (0x007C30CC */
extern u32 g_eventDispatchField14InitGuard;          /* 0x007A3040 conf 0.90: One-time static initialization guard word for the 4-entry command dispatch table g_eventDispatchField14Table (0x007C30EC */
extern u32 g_eventDispatchByte6InitGuard;            /* 0x007A3050 conf 0.90: One-time static initialization guard word for the single-entry event timeline command dispatch table g_eventDispatchByte */
extern u32 g_eventDispatchByte6Table[2];             /* 0x007A3060 conf 0.85: Static 8-byte handler entry {handler, type} for timeline commands dispatched by Event_DispatchHandlerByte6; indexed by b */
extern u32 g_eventDispatchByte4InitGuard;            /* 0x007A3068 conf 0.90: One-time static initialization guard word for the 66-entry event command dispatch table g_eventDispatchByte4Table (0x007 */
extern u32 g_eventDispatchByTypeInitGuard;           /* 0x007A6874 conf 0.90: One-time static initialization guard word for the event handler dispatch table g_eventDispatchByTypeTable (0x007A6880).  */
extern u32 g_eventDispatchByTypeTable[2];            /* 0x007A6880 conf 0.85: Single-entry 8-byte static dispatch table {handler, type} in .data populated by maybe_Event_DispatchByType with default  */
extern u8 maybe_g_eventSequenceReturnContextFlag;    /* 0x007A68BC conf 0.45: Flag byte in .data checked at the conclusion of Event_Sequence_DispatchCommands (0x001AF6B8, literal 0x001B2444); if non */
extern char g_scriptTriggerCommandWrongParamsError[27]; /* 0x007C2146 conf 0.85: Squirrel VM error message string "wrong number of parameters" set in Event_RunTriggerCommandCallbacks when invoking an e */
extern char g_scriptTriggerDispatchWrongParamsError[27]; /* 0x007C217C conf 0.85: Squirrel VM error message string "wrong number of parameters" set in Event_DispatchScriptTrigger when invoking a script  */
extern char g_eventModelPartNameFormat[5];           /* 0x007C22A9 conf 0.85: Format string "sp%s" used in Event_ActorModels_LoadModelResources (0x004B9590) to build the cutscene actor model part re */
extern char g_eventAniFileSuffixFormat[7];           /* 0x007C22AE conf 0.85: Format string "%s.ani" used in Event_ActorModels_LoadModelResources to append the animation filename suffix when resolvi */
extern char g_eventBxonFileSuffixFormat[8];          /* 0x007C22B5 conf 0.85: Format string "%s.bxon" used in Event_ActorModels_LoadModelResources to append the binary object/animation container suf */
extern char g_eventBchFileSuffixFormat[7];           /* 0x007C22BD conf 0.85: Format string "%s.bch" used in Event_ActorModels_LoadModelResources to append the binary model suffix when resolving cut */
extern u32 g_eventDispatchField39Table[8];           /* 0x007C30CC conf 0.85: 4-entry static dispatch table (8 bytes per entry: {handler, type}) in .bss indexed by cmd->f_39 in Event_DispatchHandler */
extern u32 g_eventDispatchField14Table[8];           /* 0x007C30EC conf 0.85: 4-entry static dispatch table (8 bytes per entry: {handler, type}) in .bss indexed by cmd->f_14 in Event_DispatchHandler */
extern u32 g_eventDispatchByte4Table[132];           /* 0x007C310C conf 0.85: 66-entry static dispatch table (8 bytes per entry: {handler, type}, 528 bytes total) in .bss indexed by byte at cmd+4 in */

/* --- Field --- */
extern u8 g_fieldMapInstanceTypeTable[2];            /* 0x00725378 conf 0.65: Map instance type translation table used by Field_SceneNode_CreateMapInstance; maps instance_type byte to a map-add inst */
extern u16 g_fieldActorEffectIdBySlot[7];            /* 0x007255D8 conf 0.70: Table of 16-bit effect IDs indexed by slot number (0x04FA, 0x04FC, 0x04FE, 0x0500...) passed to effect player by Field_A */
extern u16 g_fieldActorAttachedEffectIdTable[7];     /* 0x007255E6 conf 0.70: Table of 16-bit attached effect IDs indexed by actor->f_23b (0x04FB, 0x04FD, 0x04FF...) passed by Field_Actor_PlayAttach */
extern f32 g_fieldNpcPlayerDistanceThreshold;        /* 0x0072582C conf 0.65: Float constant 5.0f used by Field_NpcCheckPlayerDistance to compare against player-to-NPC distance threshold for interac */
extern void* g_fieldFrogJumpActionTable[8];          /* 0x0072584C conf 0.60: Action handler dispatch table for frog jump action sequence in Field_ActorAction_FrogJumpStart; starts with size/count 0 */
extern void* g_fieldNpcActionScriptHandlerTable[12]; /* 0x007258B8 conf 0.60: Table of NPC action script handlers referenced by Field_SetupNpcActionScript; pairs of function pointer and context. */
extern void* g_fieldSceneObjectSpriteMethodTable[39]; /* 0x00725A54 conf 0.55: Method table or component descriptor table used by Field_SceneObject_CreateSprite for 2D/sprite scene objects (0x9C byte */
extern u32 g_fieldSceneRenderObjectConfig[4];        /* 0x00725C8C conf 0.55: Configuration table used by maybe_Field_SceneInit_Shared and maybe_Field_SceneObject_CreateRenderObject; entry 2 contain */
extern void* g_fieldActorRuntimeStateMethodTable[40]; /* 0x00725D94 conf 0.55: Method table used by maybe_Field_CreateActorRuntimeState to initialize actor runtime state components (0xA0 bytes). */
extern void* g_fieldCollisionObjectHandlerTable[10]; /* 0x007262C4 conf 0.60: Handler table for collision objects referenced by Field_CollisionObject_Init; contains collision dispatch routine pointe */
extern u32 g_fieldGimmickUpdateConfig[4];            /* 0x00726348 conf 0.55: Descriptor table referenced in maybe_Field_Gimmick_Update at offset +0xC containing handler 0x00319674. */
extern u8 g_fieldNpcEmoteBalloonEnabledTable[30];    /* 0x007263A7 conf 0.70: Boolean flag table indexed by NPC talk/balloon style ID (f_313) indicating whether emote balloon is displayed. */
extern u8 g_fieldNpcEmoteFaceStateTable[20];         /* 0x007263ED conf 0.65: Mapping table from NPC style ID (f_313) to face emote state ID, used by Field_Gimmick_SetEmoteState and maybe_Field_Npc_ */
extern void* g_fieldSceneEffectMethodTable[39];      /* 0x00726418 conf 0.55: Method table or component descriptor table used by maybe_Field_SceneEffect_Create for scene effect objects (0x9C bytes). */
extern f32 g_fieldBeeRiseActionParams[4];            /* 0x0072654C conf 0.65: Motion parameters (rise velocity 10.0f, max height 10.0f, scale 1.5f) for the bee rise field action in Field_BeeRiseActi */
extern u32 g_fieldActorActionListConfig[8];          /* 0x00726838 conf 0.60: Action list configuration header containing initial slot flags 0xFFFF0000 and handler pointer 0x003E8704 used by Field_A */
extern void* g_fieldActorControllerMethodTable[39];  /* 0x00726908 conf 0.55: Method table or component table installed by maybe_Field_Actor_CreateController for actor controller objects (0x9C bytes */
extern void* g_fieldSharedParamHandlerTable[8];      /* 0x00726AA8 conf 0.55: Table of parameter handlers and callbacks referenced at offset +0x7C in maybe_Field_InitSharedParams. */
extern u32 g_fieldSharedParamOffsets[8];             /* 0x00726CA8 conf 0.60: Offset and flag descriptor pairs (0x130, 1, 0x138, 1, 0x134, 1, 0x13c, 1) loaded by maybe_Field_InitSharedParams to init */
extern void* g_fieldObjectHandlerTable[90];          /* 0x00726D10 conf 0.60: Handler and callback dispatch table for field objects initialized by maybe_Field_InitObjectTable (0x168 bytes of functio */
extern void* g_fieldObjectSecondaryHandlerTable[8];  /* 0x00726E10 conf 0.55: Secondary callback table referenced at offset +0x10 by maybe_Field_InitObjectTable containing object lifecycle pointers. */
extern u8 g_fieldGridInteractionMaskTable[8];        /* 0x007272AC conf 0.55: Grid interaction mask bytes (0x00, 0x02, 0x03, 0x08) checked against tile flags in maybe_Field_CheckGridInteraction. */
extern u32 g_fieldPlacementCellMask2D[4];            /* 0x007272B0 conf 0.55: Tile collision and placement cell bitmask table used by Field_FindFreePlacementCell2D to find valid free cells. */
extern u8 g_fieldNpcMovementStateAllowed[6];         /* 0x007272B8 conf 0.65: Byte boolean lookup table indexing NPC movement state eligibility (states 0..5 allowed, state 6+ blocked) in Field_NpcCa */
extern f32 g_fieldPlacementSearchOffsets3D[8];       /* 0x007272D4 conf 0.70: Radial search step offsets (0.0, 0.125, -0.125, 0.25, -0.25, 0.375, -0.375, 0.5) used by maybe_Field_FindFreePlacementPo */
extern void* g_fieldMarkerUpdateDrawCallbackTable[8]; /* 0x00727300 conf 0.60: Table of update and draw callback functions (0x004C7430, 0x004C6ED0, etc.) for field markers in Field_Marker_UpdateAndDr */
extern void* g_fieldSceneObjectInitDispatchTable[120]; /* 0x007273B0 conf 0.60: Large dispatch table of scene object initialization and setup handlers (0x1E0 bytes = 120 words) used by Field_InitScene */
extern void* g_fieldSceneObjectSubDispatchTable[32]; /* 0x007274B0 conf 0.60: Secondary scene object initialization callback table containing function pointers 0x0019EE04, 0x0019E318 used by Field_I */
extern u32 g_field2dMapChipStepMovementTable[8];     /* 0x00727800 conf 0.65: Map chip step movement attribute table starting with code pointer 0x0070D920 and powers of 4 (1, 4, 0x10, 0x40) used by  */
extern u32 g_field2dReachableCellConfig[8];          /* 0x00727850 conf 0.60: Configuration descriptor holding data pointer 0x0070D8FC used by maybe_Field2D_MapChip_FindReachableCell for 2D cell pat */
extern u32 g_field2dPassableEdgeConfig[8];           /* 0x00727864 conf 0.65: Passable edge query table holding pointers 0x0070DB3C used by Field2D_MapChip_FindPassableEdge and Alt to determine walk */
extern u32 g_field2dElevationPassableConfig[8];      /* 0x00727878 conf 0.60: Elevation passability attribute descriptor holding data pointers 0x0070DB3C and 0x0070D920 used by Field2D_MapChip_Check */
extern u32 g_field2dCellAttributesConfig[8];         /* 0x0072788C conf 0.60: Cell attribute query table holding pointers 0x0070D920 and 0x0070DBA8 used by Field2D_MapChip_QueryCellAttributes. */
extern u32 g_field2dTileLayerBitshifts[16];          /* 0x007278B0 conf 0.70: Bit shift / power-of-4 table (1, 4, 0x10, 0x40, 0x100, 0x400, 0x1000, 0x4000...) used by Field2D_MapChip_ResolveTileLaye */
extern u32 g_field2dColumnRendererBitshifts[16];     /* 0x007278F0 conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40, 0x100, 0x400, 0x1000, 0x4000...) used by Field2D_MapChip_InitColumnRendere */
extern u32 g_field2dSolidCheckConfig[8];             /* 0x00727930 conf 0.60: Collision check configuration table starting with pointer 0x0070DB3C and powers of 4 used by Field2D_MapChip_IsSolidAt. */
extern u32 g_field2dSpriteVisibilityBitshifts[16];   /* 0x00727944 conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40...) used by Field2D_Sprite_UpdateVisibility for 2D sprite visibility bitmas */
extern u32 g_field2dGridRendererBitshifts[16];       /* 0x00727984 conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40...) used by Field2D_MapChip_InitGridRenderer for grid rendering calculation */
extern u32 g_field2dPathFollowerBitshifts[16];       /* 0x007279C4 conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40...) used by Field2D_Sprite_CreatePathFollower for path follower step scalin */
extern u32 g_field2dTweenMoveBitshifts[16];          /* 0x00727A04 conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40...) used by Field2D_Sprite_CreateTweenMove for tween interpolation scaling. */
extern u32 g_field2dBobMotionBitshifts[16];          /* 0x00727A44 conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40...) used by Field2D_Sprite_CreateBobMotion for bobbing animation scaling. */
extern u32 g_field2dSpriteDefaultAnimConfig[8];      /* 0x00727AD8 conf 0.60: Default sprite animation configuration header holding pointer 0x007844AC read by maybe_Field2D_Sprite_BindDefaultAnim. */
extern u32 g_field2dTweenMoveAltBitshifts[16];       /* 0x00727B18 conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40...) used by Field2D_Sprite_CreateTweenMoveAlt for alternate tween movement  */
extern u32 g_field2dGlyphAttachmentConfig[8];        /* 0x00727B58 conf 0.60: Glyph attachment and UV mapping descriptor table holding pointer 0x0070D8FC used across Field2D glyph attachment routine */
extern u32 g_field2dGlyphQuadBitshifts[16];          /* 0x00727B9C conf 0.70: Power-of-4 bit shift table (1, 4, 0x10, 0x40...) used by Field2D_Sprite_BuildGlyphQuad for glyph quad scaling. */
extern u32 g_field2dStepTowardsGoalConfig[8];        /* 0x00727C30 conf 0.60: Movement goal descriptor table holding pointer 0x0070DB3C used by Field2D_Sprite_StepTowardsGoal. */
extern u32 g_field2dActorCollisionBoxConfig[8];      /* 0x00727C40 conf 0.60: 2D actor collision box configuration table holding pointer 0x0070D924 used by Field2D_Actor_CheckCollisionBox. */
extern u32 g_field2dSceneRenderAllConfig[8];         /* 0x00727D38 conf 0.60: Render pass descriptor holding pointer 0x0070D924 used by Field2D_Scene_RenderAll. */
extern u32 g_field2dMapChipCollectRegionConfig[8];   /* 0x00727DA0 conf 0.60: Region collection descriptor table holding pointer 0x0070D908 used by maybe_Field2D_MapChip_CollectRegion. */
extern u8 g_field2dMapChipCollisionMaskTable[40];    /* 0x00727DE8 conf 0.70: Collision mask lookup table (stride 5 bytes) used by Field2D_MapChip_BuildCollisionMask to construct tile collision mask */
extern u32 g_field2dTilePaletteConfig[8];            /* 0x00727E10 conf 0.60: Tile palette configuration header (stride 0x60 and data pointer 0x0070D8FC) used by Field2D_MapChip_LoadTilePalette. */
extern u32 g_field2dPathConnectivityDescriptor[8];   /* 0x00727E14 conf 0.60: Path connectivity descriptor holding context pointer 0x0070D8FC used in Field2D pathfinding algorithms. */
extern void* g_field2dSceneRenderObjectMethodTable[12]; /* 0x00727EDC conf 0.65: Render callback and dispatch table for 2D field scene object rendering in maybe_Field2D_Scene_RenderObjects. */
extern u32 g_field2dMapChipTraceConfig[12];          /* 0x00727F20 conf 0.60: Configuration table holding layer descriptors 0x0070D924 and 0x0070D90C used by Field2D_MapChip_WalkTrace and Field2D_Sc */
extern void* g_fieldGimmickEffectCallbackTable[28];  /* 0x00727FBC conf 0.65: Effect handler callback table used by maybe_Field_Gimmick_ApplyEffectConfig (0x70 bytes of function pointers). */
extern void* g_fieldGimmickVariantInitMethodTable[16]; /* 0x00728294 conf 0.65: Method table of variant initialization handlers used by maybe_Field_Gimmick_InitVariant to set up gimmick variants. */
extern u8 g_fieldGimmickVariantIdMappingTable[28];   /* 0x007283C4 conf 0.70: Mapping table from gimmick variant ID to row index passed to func_0018C1B8 in Field_Gimmick_InitRowsFromWork. */
extern u32 g_fieldNpcMotionDescriptor[4];            /* 0x007283F8 conf 0.60: Descriptor holding motion nut pointers 0x007844C8 and 0x0070D21C used by maybe_Field_Npc_SetMotionNut. */
extern f32 g_fieldObjectModelScaleDefault;           /* 0x00728A44 conf 0.65: Default model scale float constant (7.0f) read by maybe_Field_Object_GetModelScale. */
extern u32 g_fieldScreenSystemDescriptor[4];         /* 0x00729A54 conf 0.60: Screen system component descriptor loaded by maybe_Field_CreateScreenSystem; slot 2 contains function pointer 0x00195F8C */
extern u8 g_fieldAreaActorIndexTable[12];            /* 0x0072D6C8 conf 0.65: Sequential actor index mapping table (0..7, 0x1B) copied into local buffer in maybe_Field_LoadAreaActorData. */
extern f32 g_mathFastSinCosTable[1024];              /* 0x0072FC50 conf 0.85: Precomputed fast sine/cosine trigonometric lookup table (256 entries of 4 floats: sin, cos, sin_delta, cos_delta) used a */
extern u8 maybe_g_rodata_0073635f[16];               /* 0x0073635F conf 0.35: Unaligned rodata parameter block passed by address to Fs_FormatMapBg3DPackPath in Field_Level_InitFromRecord. */
extern u8 maybe_g_rodata_0074754e[16];               /* 0x0074754E conf 0.35: Unaligned rodata byte block passed by address to motion setup in ActorGadgetSetActionSeq and Field_Actor_PlayIdleAnim. */
extern void* g_fieldScreenSystemWidgetVtable[10];    /* 0x007584E4 conf 0.60: Vtable for field screen system widget (structs.json class Ui_Widget) (10 slots), installed by maybe_Field_CreateScreenSy */
extern void* g_uiLayoutVtable[11];                   /* 0x00758598 conf 0.55: Vtable for uiLayout (11 slots), slot 1 deleting destructor Ui_Layout_DeleteSubComponent, slot 2 method 0x001775d0. Insta */
extern void* maybe_g_fieldObjectVt00758818Vtable[37]; /* 0x00758818 conf 0.40: Vtable for fieldObjectVt00758818 (37 slots), slot 1 deleting destructor 0x0018132c, slot 2 method 0x00181308. Installed  */
extern void* g_fieldActorDataVtable[53];             /* 0x007588B4 conf 0.60: Vtable for fieldActorData (53 slots), slot 1 deleting destructor maybe_Field_Object_DtorWithHandle, slot 2 method maybe_ */
extern void* g_fieldGridObjectVtable[1];             /* 0x00758A60 conf 0.60: Vtable for fieldGridObject (1 slots). Installed by maybe_Field_CreateGridObject. */
extern void* g_fieldVtable[2];                       /* 0x00758EF4 conf 0.55: Vtable for field (2 slots), slot 1 deleting destructor Field_DeleteScene. Installed by Field_DeleteScene. */
extern void* g_fieldRenderNodeAVtable[11];           /* 0x0075946C conf 0.60: Vtable for fieldRenderNodeA (11 slots), slot 1 deleting destructor Ui_Layout_DeleteSubComponentC, slot 2 method 0x00193c */
extern void* g_fieldRenderNodeBVtable[11];           /* 0x007594A0 conf 0.60: Vtable for fieldRenderNodeB (11 slots), slot 1 deleting destructor Ui_Layout_DeleteSubComponentD, slot 2 method 0x00193c */
extern void* g_fieldActionCutVtable[11];             /* 0x0075959C conf 0.65: Vtable for field cut action (11 slots), installed by maybe_Field_Action_CreateCut; slot 1 deleting destructor Ui_Layout_ */
extern void* g_fieldActionDigVtable[11];             /* 0x007595D0 conf 0.65: Vtable for field dig action (structs.json class Field_Action) (11 slots), installed by maybe_Field_Action_CreateDig; slo */
extern void* g_fieldActionNutVtable[11];             /* 0x00759604 conf 0.65: Vtable for field nut action (11 slots), installed by maybe_Field_Action_CreateNut; slot 1 deleting destructor Ui_Layout_ */
extern void* g_fieldSmallObjectVtable[11];           /* 0x00759F10 conf 0.60: Vtable for fieldSmallObject (11 slots), slot 1 deleting destructor Object_DtorThunkA, slot 2 method maybe_Ui_Widget_Play */
extern void* g_fieldConfigVtable[11];                /* 0x00759F44 conf 0.60: Vtable for fieldConfig (11 slots), slot 1 deleting destructor Object_DtorThunkB, slot 2 method Math_QuatRotateVector. In */
extern void* g_fieldSceneObjectCtorVt1D582CVtable[2]; /* 0x00759F78 conf 0.60: Vtable for fieldSceneObjectCtorVt1D582C (2 slots), slot 1 deleting destructor 0x001d584c. Installed by maybe_Field_Scene */
extern void* g_fieldObjectCtorVt1D6C98Vtable[2];     /* 0x00759F88 conf 0.60: Vtable for fieldObjectCtorVt1D6C98 (2 slots), slot 1 deleting destructor 0x001d6cac. Installed by maybe_Field_ObjectCtor */
extern void* g_fieldStateObjectVtable[2];            /* 0x0075A444 conf 0.60: Vtable for fieldStateObject (2 slots), slot 1 deleting destructor 0x001da6a0. Installed by maybe_Field_CreateStateObject */
extern void* maybe_g_fieldObjectVt0075a554Vtable[5]; /* 0x0075A554 conf 0.40: Vtable for fieldObjectVt0075a554 (5 slots), slot 1 deleting destructor 0x001dc57c, slot 2 method maybe_Ui_List_RemoveEnt */
extern void* g_fieldActorVtable[11];                 /* 0x0075A590 conf 0.65: Vtable for fieldActor (structs.json class Field_Actor) (11 slots), slot 1 deleting destructor 0x001e0d28, slot 2 method  */
extern void* g_fieldActorMoveVtable[11];             /* 0x0075A5C4 conf 0.65: Vtable for fieldActorMove (structs.json class Field_ActorMove) (11 slots), slot 1 deleting destructor maybe_Field_ActorM */
extern void* g_fieldActorMoveTaskVtable[11];         /* 0x0075A5F8 conf 0.60: Vtable for fieldActorMoveTask (11 slots), slot 1 deleting destructor 0x001e1608, slot 2 method Field_ActorMove_InitDirec */
extern void* g_fieldActorBehaviourTaskVtable[16];    /* 0x0075A62C conf 0.60: Vtable for fieldActorBehaviourTask (16 slots), slot 1 deleting destructor 0x001e1b6c, slot 2 method Field_Actor_BeginSte */
extern void* g_stateSequence40Vtable[7];             /* 0x0075A7D4 conf 0.70: Vtable for stateSequence40 (structs.json class std_StateSequence40) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence41Vtable[7];             /* 0x0075A7F8 conf 0.70: Vtable for stateSequence41 (structs.json class std_StateSequence41) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence43Vtable[7];             /* 0x0075A840 conf 0.70: Vtable for stateSequence43 (structs.json class std_StateSequence43) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence44Vtable[7];             /* 0x0075A864 conf 0.70: Vtable for stateSequence44 (structs.json class std_StateSequence44) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence45Vtable[7];             /* 0x0075A888 conf 0.70: Vtable for stateSequence45 (structs.json class std_StateSequence45) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence06Vtable[7];             /* 0x0075ACE4 conf 0.70: Vtable for stateSequence06 (structs.json class std_StateSequence06) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence18Vtable[7];             /* 0x0075AE94 conf 0.70: Vtable for stateSequence18 (structs.json class std_StateSequence18) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence21Vtable[7];             /* 0x0075AF00 conf 0.70: Vtable for stateSequence21 (structs.json class std_StateSequence21) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence24Vtable[7];             /* 0x0075AF6C conf 0.70: Vtable for stateSequence24 (structs.json class std_StateSequence24) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence78Vtable[7];             /* 0x0075B284 conf 0.70: Vtable for stateSequence78 (structs.json class std_StateSequence78) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence79Vtable[7];             /* 0x0075B2A8 conf 0.70: Vtable for stateSequence79 (structs.json class std_StateSequence79) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence80Vtable[7];             /* 0x0075B2CC conf 0.70: Vtable for stateSequence80 (structs.json class std_StateSequence80) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence81Vtable[7];             /* 0x0075B2F0 conf 0.70: Vtable for stateSequence81 (structs.json class std_StateSequence81) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence82Vtable[7];             /* 0x0075B314 conf 0.70: Vtable for stateSequence82 (structs.json class std_StateSequence82) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence83Vtable[7];             /* 0x0075B338 conf 0.70: Vtable for stateSequence83 (structs.json class std_StateSequence83) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence84Vtable[7];             /* 0x0075B35C conf 0.70: Vtable for stateSequence84 (structs.json class std_StateSequence84) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_stateSequence85Vtable[7];             /* 0x0075B380 conf 0.70: Vtable for stateSequence85 (structs.json class std_StateSequence85) (7 slots), slot 1 deleting destructor std_StateSeque */
extern void* g_uiOverlayVtable[2];                   /* 0x0075C72C conf 0.65: Vtable for uiOverlay (structs.json class Ui_Overlay) (2 slots), slot 1 deleting destructor maybe_Ui_Overlay_DestroyChild */
extern void* g_fieldSceneSubObjectVtable[2];         /* 0x0075C9A0 conf 0.65: Vtable for fieldSceneSubObject (structs.json class Field_SceneSubObject) (2 slots), slot 1 deleting destructor Ui_Window */
extern void* g_gfxSprite2DVtable[34];                /* 0x0075D55C conf 0.65: Vtable for gfxSprite2D (structs.json class Gfx_Sprite2D) (34 slots), slot 1 deleting destructor 0x0028e6c4, slot 2 metho */
extern void* g_uiSpriteActorVtable[26];              /* 0x0075D618 conf 0.65: Vtable for uiSpriteActor (structs.json class Ui_SpriteActor) (26 slots), slot 1 deleting destructor 0x0028efb4, slot 2 m */
extern void* maybe_g_fieldObjectVt0075dc18Vtable[5]; /* 0x0075DC18 conf 0.40: Vtable for fieldObjectVt0075dc18 (5 slots), slot 1 deleting destructor 0x00294168, slot 2 method maybe_Ui_Window_UpdateB */
extern void* g_fieldActorMotionVtable[11];           /* 0x0075EAA4 conf 0.65: Vtable for fieldActorMotion (structs.json class Field_ActorMotion) (11 slots), slot 1 deleting destructor maybe_Ui_Widge */
extern void* g_fieldActorMotionSimpleVtable[11];     /* 0x0075EAD8 conf 0.60: Vtable for fieldActorMotionSimple (11 slots), slot 1 deleting destructor maybe_Ui_Widget_DtorDeleteC, slot 2 method mayb */
extern void* g_fieldNpcActionWaitVtable[11];         /* 0x0075EDAC conf 0.65: Vtable for NPC wait action task (11 slots), installed by maybe_Field_NpcAction_SetWaitParams; slot 1 deleting destructor */
extern void* g_fieldNpcActionIdleVtable[11];         /* 0x0075EDE0 conf 0.65: Vtable for NPC idle action task (11 slots), installed by maybe_Field_NpcAction_SetIdleParams; slot 1 deleting destructor */
extern void* g_fieldSceneObjectVtable[1];            /* 0x0075EFDC conf 0.60: Vtable for fieldSceneObject (1 slots). Installed by maybe_Field_SceneObject_CtorCompact. */
extern void* g_fieldDragControllerVtable[1];         /* 0x0075F158 conf 0.60: Vtable for fieldDragController (1 slots). Installed by Field_DragController_Ctor. */
extern void* g_fieldSceneObjectTypedChildVtable[1];  /* 0x0075F214 conf 0.60: Vtable for fieldSceneObjectTypedChild (1 slots). Installed by maybe_Field_SceneObject_CreateTypedChild. */
extern void* g_fieldActionMoveInputDescriptor[8];    /* 0x0075F904 conf 0.60: Descriptor table for field character move input processing in maybe_Field_Action_MoveInput; contains callback pointers a */
extern void* g_fieldObjectFactoryType1368Vtable[4];  /* 0x00760898 conf 0.65: Vtable for fieldObjectFactoryType1368 (4 slots), slot 1 deleting destructor maybe_FieldParty_DeletingDtorA, slot 2 metho */
extern void* g_fieldObjectFactoryKind35Vtable[4];    /* 0x00760C08 conf 0.65: Vtable for fieldObjectFactoryKind35 (4 slots), slot 1 deleting destructor 0x002dac04, slot 2 method FieldParty_InitFromP */
extern void* g_fieldActorMotionComponentVtable[11];  /* 0x007614C4 conf 0.60: Vtable for field actor motion component (11 slots), installed by Field_ActorMotion_Ctor; slot 1 deleting destructor mayb */
extern void* g_animClipSlotDeletingDtorLinearVtable[11]; /* 0x007615D8 conf 0.55: Vtable for animClipSlotDeletingDtorLinear (11 slots), slot 1 deleting destructor maybe_Anim_ClipSlot_DeletingDtorLinear, */
extern void* g_fieldMarkerVtable[1];                 /* 0x007617EC conf 0.60: Vtable for fieldMarker (1 slots). Installed by maybe_Field_Marker_Ctor. */
extern void* g_fieldMarkerVariantBVtable[1];         /* 0x007618A8 conf 0.60: Vtable for field marker variant B (4 slots), installed by maybe_Field_Marker_CtorB. */
extern void* g_fieldMarkerVariantCVtable[1];         /* 0x00761A60 conf 0.60: Vtable for field marker variant C (4 slots), installed by maybe_Field_Marker_CtorC. */
extern void* maybe_g_fieldObjectVt00761c50Vtable[1]; /* 0x00761C50 conf 0.40: Vtable for fieldObjectVt00761c50 (1 slots). Installed by maybe_Field_Marker_DestroyChildren. */
extern void* g_uiItemInfoWindowVtable[10];           /* 0x00761E68 conf 0.65: Vtable for uiItemInfoWindow (structs.json class Ui_ItemInfoWindow) (10 slots), slot 1 deleting destructor 0x002f6b44, sl */
extern void* g_uiModeWindowVtable[10];               /* 0x0076216C conf 0.65: Vtable for uiModeWindow (structs.json class Ui_ModeWindow) (10 slots), slot 1 deleting destructor Ui_ListWindow_DtorB, s */
extern void* g_fieldGimmickDeletingDtorVtable[12];   /* 0x007625D4 conf 0.55: Vtable for fieldGimmickDeletingDtor (12 slots), slot 1 deleting destructor maybe_Field_Gimmick_DeletingDtor, slot 2 meth */
extern void* g_fieldStateCarryVtable[11];            /* 0x00762850 conf 0.60: Vtable for fieldStateCarry (11 slots), slot 1 deleting destructor Field_Action_Base_DeletingDtor, slot 2 method Field_Ac */
extern void* g_fieldActionCheckAnyDeletingDtorVtable[11]; /* 0x00762884 conf 0.55: Vtable for fieldActionCheckAnyDeletingDtor (11 slots), slot 1 deleting destructor Field_Action_CheckAny_DeletingDtor, sl */
extern void* g_fieldStateMoveVtable[11];             /* 0x007628B8 conf 0.60: Vtable for fieldStateMove (11 slots), slot 1 deleting destructor Field_Action_Walk_DeletingDtor, slot 2 method Field_Act */
extern void* g_fieldActionMoveDirDeletingDtorVtable[11]; /* 0x007629B0 conf 0.55: Vtable for fieldActionMoveDirDeletingDtor (11 slots), slot 1 deleting destructor Field_Action_MoveDir_DeletingDtor, slot */
extern void* g_fieldActionOpenDoorDeletingDtorVtable[11]; /* 0x00762A84 conf 0.55: Vtable for fieldActionOpenDoorDeletingDtor (11 slots), slot 1 deleting destructor Field_Action_OpenDoor_DeletingDtor, sl */
extern void* g_fieldActorObjectVtable[1];            /* 0x00762FEC conf 0.60: Vtable for fieldActorObject (1 slots). Installed by maybe_Field_CreateActorObject. */
extern void* g_fieldObjectFactoryKind31Vtable[4];    /* 0x0076335C conf 0.65: Vtable for fieldObjectFactoryKind31 (4 slots), slot 1 deleting destructor maybe_FieldParty_SubObjectDtorDelete, slot 2 m */
extern void* g_fieldWorldStateCtorVtable[4];         /* 0x007634AC conf 0.60: Vtable for fieldWorldStateCtor (4 slots), slot 1 deleting destructor 0x0031f9c0, slot 2 method FieldParty_InitFromParams */
extern void* g_fieldObjectFactoryKind22Vtable[4];    /* 0x00763608 conf 0.65: Vtable for fieldObjectFactoryKind22 (4 slots), slot 1 deleting destructor FieldParty_DeletingDestructorA, slot 2 method  */
extern void* g_fieldObjectFactoryType1359Vtable[4];  /* 0x0076371C conf 0.65: Vtable for fieldObjectFactoryType1359 (4 slots), slot 1 deleting destructor maybe_FieldParty_DeletingDestructorB, slot 2 */
extern void* g_fieldWorldStateCtorBVtable[4];        /* 0x00763830 conf 0.60: Vtable for fieldWorldStateCtorB (4 slots), slot 1 deleting destructor Battle_ActionSequence_Dtor, slot 2 method FieldPar */
extern void* g_fieldActorMotionVariantVtable[11];    /* 0x0076423C conf 0.65: Vtable for field actor motion variant (11 slots), installed by Field_ActorMotion_CreateVariant. */
extern void* g_fieldEnemyAiAnimCtorVtable[11];       /* 0x007648B0 conf 0.60: Vtable for fieldEnemyAiAnimCtor (11 slots), slot 1 deleting destructor maybe_Field_NpcAction_RunToward_DeletingDestructo */
extern void* g_fieldNpcGestureVtable[11];            /* 0x00764918 conf 0.60: Vtable for fieldNpcGesture (11 slots), slot 1 deleting destructor Field_NpcAction_SubactionDeletingDtor, slot 2 method 0 */
extern void* g_fieldNpcManagerVtable[31];            /* 0x00764A38 conf 0.65: Vtable for fieldNpcManager (structs.json class Field_NpcManager) (31 slots), slot 1 deleting destructor Field_Object_Dto */
extern void* maybe_g_fieldObjectVt00764f90Vtable[1]; /* 0x00764F90 conf 0.40: Vtable for fieldObjectVt00764f90 (1 slots). Installed by maybe_Field_SpriteObject_DtorBody. */
extern void* g_fieldSceneObjectDefaultsVtable[26];   /* 0x00765340 conf 0.60: Vtable for field scene object with defaults (8 slots), installed by maybe_Field_SceneObject_CtorWithDefaults. */
extern void* g_uiScreenFadeVtable[6];                /* 0x007654A4 conf 0.65: Vtable for uiScreenFade (structs.json class Ui_ScreenFade) (6 slots), slot 1 deleting destructor 0x00368558, slot 2 meth */
extern void* g_uiGuideWindowVtable[6];               /* 0x007654C4 conf 0.65: Vtable for uiGuideWindow (structs.json class Ui_GuideWindow) (6 slots), slot 1 deleting destructor 0x00368698, slot 2 me */
extern void* g_fieldSceneObjectsVtable[6];           /* 0x007654E4 conf 0.60: Vtable for fieldSceneObjects (6 slots), slot 1 deleting destructor 0x0036887c, slot 2 method 0x006437b4. Installed by Fi */
extern void* g_fieldActorTurnActionCtorVtable[13];   /* 0x00765638 conf 0.60: Vtable for fieldActorTurnActionCtor (13 slots), slot 1 deleting destructor Field_ActorAction_DeletingDtor, slot 2 method */
extern void* g_fieldHorseActionVtable[14];           /* 0x00765674 conf 0.65: Vtable for field horse action base (11 slots), installed by maybe_Field_HorseAction_Ctor; slot 1 deleting destructor Fie */
extern void* g_fieldHorseRideActionVtable[12];       /* 0x007656B4 conf 0.65: Vtable for field horse ride action (11 slots), installed by maybe_Field_HorseAction_CtorVariantA; slot 1 deleting destru */
extern void* g_fieldHorseTurnActionVtable[14];       /* 0x007656EC conf 0.65: Vtable for field horse turn action (11 slots), installed by maybe_Field_HorseAction_CtorVariantB; slot 1 deleting destru */
extern void* g_fieldActorActionVtable[12];           /* 0x0076572C conf 0.60: Vtable for fieldActorAction (12 slots), slot 1 deleting destructor maybe_Field_TurnAction_DeletingDtor, slot 2 method 0x */
extern void* maybe_g_fieldObjectVt00765764Vtable[5]; /* 0x00765764 conf 0.40: Vtable for fieldObjectVt00765764 (5 slots), slot 1 deleting destructor 0x0036d3e8, slot 2 method Ui_ShowInfoMessage. Ins */
extern void* g_fieldActorSimpleAVtable[11];          /* 0x007658F8 conf 0.60: Vtable for simple field actor variant A (11 slots), installed by maybe_Field_Actor_CtorSimpleA; slot 1 deleting destruct */
extern void* g_fieldActorSimpleBVtable[11];          /* 0x0076592C conf 0.60: Vtable for simple field actor variant B (11 slots), installed by maybe_Field_Actor_CtorSimpleB; slot 1 deleting destruct */
extern void* g_fieldActorPushActionVtable[11];       /* 0x007659A8 conf 0.65: Vtable for field actor push action (11 slots), installed by maybe_Field_ActorAction_Ctor; slot 1 deleting destructor 0x0 */
extern void* g_fieldActorActionBaseCtorVtable[12];   /* 0x00765A58 conf 0.60: Vtable for fieldActorActionBaseCtor (12 slots), slot 1 deleting destructor Field_Action_DeletingDtorA, slot 2 method Fie */
extern void* g_fieldActorTurnActionVtable[11];       /* 0x00765AFC conf 0.65: Vtable for field actor turn action (11 slots), installed by maybe_Field_ActorAction_CtorB; slot 1 deleting destructor Fi */
extern void* g_fieldPartyVariantBVtable[4];          /* 0x00766568 conf 0.65: Vtable for field party variant B (4 slots), installed by FieldParty_CtorB; slot 1 deleting destructor Ui_BattleActor_Dir */
extern void* g_fieldObjectFactoryKind26Vtable[4];    /* 0x00766680 conf 0.65: Vtable for fieldObjectFactoryKind26 (4 slots), slot 1 deleting destructor Battle_Ui_DeletingDtorA, slot 2 method FieldPa */
extern void* g_fieldObjectFactoryType1365Vtable[4];  /* 0x00766794 conf 0.65: Vtable for fieldObjectFactoryType1365 (4 slots), slot 1 deleting destructor Battle_Ui_DeletingDtorB, slot 2 method Field */
extern void* g_fieldActorActionDeadVtable[11];       /* 0x00767054 conf 0.60: Vtable for fieldActorActionDead (11 slots), slot 1 deleting destructor Field_NpcAction_DeletingDtorAlt2, slot 2 method F */
extern void* g_fieldActorInstanceVtable[1];          /* 0x00767140 conf 0.60: Vtable for field actor instance (11 slots), installed by Field_Actor_Create; slot 1 deleting destructor Field_Actor_Dtor */
extern void* g_fieldEnemyAiAnimCtorBVtable[12];      /* 0x0076731C conf 0.60: Vtable for fieldEnemyAiAnimCtorB (12 slots), slot 1 deleting destructor Field_NpcAction_SubactionDeletingDtorC, slot 2 m */
extern void* g_fieldSceneObjectSpritePrimaryVtable[1]; /* 0x00767394 conf 0.65: Vtable for field scene object sprite primary (8 slots), installed by Field_SceneObjectSprite_Ctor; slot 1 deleting destr */
extern void* g_fieldObjectSpriteBaseVtable[1];       /* 0x007673A4 conf 0.60: Vtable for field object sprite base (8 slots), installed by maybe_Field_ObjectSprite_CtorBase. */
extern void* g_fieldObjectSpriteDrawVtable[8];       /* 0x007673B4 conf 0.65: Vtable for drawable field object sprite (8 slots), installed by Field_ObjectSprite_Ctor; slot 1 deleting destructor 0x00 */
extern void* g_fieldObjectSpriteVariantVtable[8];    /* 0x007673DC conf 0.60: Vtable for field object sprite variant (8 slots), installed by maybe_Field_ObjectSprite_CtorVariant. */
extern void* g_uiPresentWindowVtable[3];             /* 0x0076741C conf 0.60: Vtable for uiPresentWindow (3 slots), slot 1 deleting destructor Ui_Pane_DeletingDtor, slot 2 method maybe_Field_ObjectS */
extern void* g_fieldGadgetVtable[1];                 /* 0x0076775C conf 0.60: Vtable for fieldGadget (1 slots). Installed by Field_Gadget_Ctor. */
extern void* g_fieldGadgetComponentVtable[1];        /* 0x0076781C conf 0.60: Vtable for field gadget component (11 slots), installed by maybe_Field_Gadget_Ctor. */
extern void* maybe_g_fieldObjectVt00768278Vtable[1]; /* 0x00768278 conf 0.40: Vtable for fieldObjectVt00768278 (1 slots). Installed by maybe_Field_GetSceneNode. */
extern void* maybe_g_fieldObjectVt007684f4Vtable[5]; /* 0x007684F4 conf 0.40: Vtable for fieldObjectVt007684f4 (5 slots), slot 1 deleting destructor 0x003a9dfc, slot 2 method Ui_ShowInfoMessage. Ins */
extern void* g_fieldObjectFactoryKind37Vtable[4];    /* 0x0076923C conf 0.65: Vtable for fieldObjectFactoryKind37 (4 slots), slot 1 deleting destructor 0x003c2634, slot 2 method FieldParty_InitFromP */
extern void* g_fieldObjectFactoryKind00Vtable[4];    /* 0x0076963C conf 0.65: Vtable for fieldObjectFactoryKind00 (4 slots), slot 1 deleting destructor maybe_Battle_ActionAnimObject_DtorDelete, slot */
extern void* g_fieldPartyMemberSlotsVtable[4];       /* 0x00769B58 conf 0.60: Vtable for field party member slot manager (4 slots), installed by FieldParty_InitMemberSlots; slot 1 deleting destructo */
extern void* g_fieldPartyTargetMarkerManagerVtable[4]; /* 0x00769CDC conf 0.65: Vtable for field party target marker manager (4 slots), installed by FieldParty_InitMemberSlots; slot 1 deleting destruc */
extern void* g_fieldActorActionSetVtable[11];        /* 0x0076A118 conf 0.60: Vtable for fieldActorActionSet (11 slots), slot 1 deleting destructor 0x003d5e34, slot 2 method maybe_Ui_DungeonWindow_A */
extern void* g_fieldNpcActionStateCtorVtable[11];    /* 0x0076A4AC conf 0.60: Vtable for fieldNpcActionStateCtor (11 slots), slot 1 deleting destructor maybe_Field_ActorAction_DtorDeleteH, slot 2 me */
extern void* g_fieldNpcEcstacyActionVtable[11];      /* 0x0076A4E0 conf 0.65: Vtable for fieldNpcEcstacyAction (structs.json class Field_NpcEcstacyAction) (11 slots), slot 1 deleting destructor mayb */
extern void* g_fieldTalkBalloonVtable[8];            /* 0x0076A52C conf 0.60: Vtable for fieldTalkBalloon (8 slots), slot 1 deleting destructor 0x003d95f4, slot 2 method maybe_Field_IsTalkActive. In */
extern void* g_fieldActorAimPoseActionCtorVtable[11]; /* 0x0076AC70 conf 0.60: Vtable for fieldActorAimPoseActionCtor (11 slots), slot 1 deleting destructor maybe_Field_ActorAimPoseAction_DtorDelete, */
extern void* g_fieldActorActionEffectVtable[11];     /* 0x0076AE84 conf 0.60: Vtable for field actor action effect (11 slots), installed by maybe_Field_ActorAction_BaseCtor; slot 1 deleting destruct */
extern void* g_fieldSceneEffectVtable[11];           /* 0x0076AEB8 conf 0.65: Vtable for fieldSceneEffect (structs.json class Field_SceneEffect) (11 slots), slot 1 deleting destructor Field_SceneEff */
extern void* g_fieldActorActionAltHandlerVtable[11]; /* 0x0076AEEC conf 0.60: Vtable for field actor action alternate handler (11 slots), installed by maybe_Field_ActorAction_CtorAlt; slot 1 deletin */
extern void* g_fieldAscentActionVtable[11];          /* 0x0076AF20 conf 0.60: Vtable for fieldAscentAction (11 slots), slot 1 deleting destructor maybe_Field_ActorAction_DtorDeleteJ, slot 2 method m */
extern void* g_fieldBreakObjectActionVtable[11];     /* 0x0076AF88 conf 0.65: Vtable for fieldBreakObjectAction (structs.json class Field_BreakObjectAction) (11 slots), slot 1 deleting destructor ma */
extern void* g_gfxEffect2DVtable[11];                /* 0x0076AFF0 conf 0.65: Vtable for gfxEffect2D (structs.json class Gfx_Effect2D) (11 slots), slot 1 deleting destructor maybe_Field_ActorAction_ */
extern void* g_fieldActorActionRelativeMoveVtable[11]; /* 0x0076B024 conf 0.65: Vtable for field actor action relative move (11 slots), installed by maybe_Field_ActorAction_CtorVariant; slot 1 deletin */
extern void* g_fieldDragonJumpActionCtorVtable[11];  /* 0x0076B058 conf 0.60: Vtable for fieldDragonJumpActionCtor (11 slots), slot 1 deleting destructor Field_DragonJumpAction_DtorDelete, slot 2 me */
extern void* g_fieldClimbActionVtable[11];           /* 0x0076B0D4 conf 0.65: Vtable for fieldClimbAction (structs.json class Field_ClimbAction) (11 slots), slot 1 deleting destructor maybe_Field_Cl */
extern void* g_fieldOpenItemBoxActionVtable[11];     /* 0x0076B13C conf 0.60: Vtable for fieldOpenItemBoxAction (11 slots), slot 1 deleting destructor maybe_Field_HellTackleAction_DtorDelete, slot 2 */
extern void* g_fieldNarrowPassActionVtable[11];      /* 0x0076B1A4 conf 0.65: Vtable for fieldNarrowPassAction (structs.json class Field_NarrowPassAction) (11 slots), slot 1 deleting destructor Fiel */
extern void* g_fieldRenderObjectSubVtable[1];        /* 0x0076B348 conf 0.60: Vtable for fieldRenderObjectSub (1 slots). Installed by maybe_Field_ActorModel_Dtor. */
extern void* g_fieldEquipPreviewModelVtable[1];      /* 0x0076B3DC conf 0.60: Vtable for fieldEquipPreviewModel (1 slots). Installed by maybe_Field_EquipPreviewModel_Ctor. */
extern void* g_uiDebugLabelVtable[3];                /* 0x0076B4A8 conf 0.65: Vtable for UI debug label / presentation window (4 slots), installed by Ui_PresentWindow_Ctor; slot 1 deleting destructo */
extern void* g_fieldHitBoxBaseVtable[6];             /* 0x0076B63C conf 0.60: Vtable for field hit box base (24 slots), installed by maybe_Field_HitBox_Ctor; slot 1 deleting destructor 0x003EA410. */
extern void* g_fieldHitBoxFloatVtable[6];            /* 0x0076B65C conf 0.60: Vtable for float-configured field hit box (24 slots), installed by maybe_Field_HitBox_CtorFloat; slot 1 deleting destruc */
extern void* g_fieldObjectFactoryKind24Vtable[4];    /* 0x0076BF78 conf 0.65: Vtable for fieldObjectFactoryKind24 (4 slots), slot 1 deleting destructor Battle_ActionUi_MemberWidget_Dtor, slot 2 meth */
extern void* g_fieldObjectFactoryKind23Vtable[4];    /* 0x0076C08C conf 0.65: Vtable for fieldObjectFactoryKind23 (4 slots), slot 1 deleting destructor Battle_ActionUi_StatusWidget_Dtor, slot 2 meth */
extern void* g_fieldGameObjectVtable[4];             /* 0x0076C1A0 conf 0.65: Vtable for fieldGameObject (structs.json class Field_GameObject) (4 slots), slot 1 deleting destructor BattleParty_Dtor, */
extern void* g_fieldObjectFactoryKind42Vtable[4];    /* 0x0076C2FC conf 0.65: Vtable for fieldObjectFactoryKind42 (4 slots), slot 1 deleting destructor Battle_ActionUi_DirectorWidget_Dtor, slot 2 me */
extern void* g_fieldNpcActionOpeFrameCtorVtable[11]; /* 0x0076D5A8 conf 0.60: Vtable for fieldNpcActionOpeFrameCtor (11 slots), slot 1 deleting destructor maybe_Ui_TextWindow_DeletingDtor_2, slot 2  */
extern void* g_fieldObject2DSceneEntryVtable[14];    /* 0x0076D6E4 conf 0.60: Vtable for fieldObject2DSceneEntry (14 slots), slot 1 deleting destructor maybe_Ui_PanelPart_DeletingDtorB, slot 2 metho */
extern void* g_fieldObject2DVtable[14];              /* 0x0076D724 conf 0.65: Vtable for fieldObject2D (structs.json class Field_Object2D) (14 slots), slot 1 deleting destructor 0x0040c3c4, slot 2 m */
extern void* g_fieldObject2DSpriteEntryBVtable[14];  /* 0x0076D77C conf 0.60: Vtable for fieldObject2DSpriteEntryB (14 slots), slot 1 deleting destructor 0x0040ccc0, slot 2 method 0x00265004. Instal */
extern void* g_fieldSceneObject2dBaseVtable[8];      /* 0x0076D7D4 conf 0.60: Vtable for 2D field scene object base (24 slots), installed by maybe_Field_SceneObject_Ctor; slot 1 deleting destructor  */
extern void* g_fieldObject2DNodeVtable[8];           /* 0x0076D7FC conf 0.60: Vtable for fieldObject2DNode (8 slots), slot 1 deleting destructor 0x0040d328, slot 2 method Field_Object2D_CommitPendin */
extern void* maybe_g_fieldObjectVt0076d83cVtable[1]; /* 0x0076D83C conf 0.40: Vtable for fieldObjectVt0076d83c (1 slots). Installed by Field_Object2D_DtorWithSubObject. */
extern void* g_fieldObject2dAttachedEffectVtable[1]; /* 0x0076D934 conf 0.60: Vtable for 2D field object with attached effect (24 slots), installed by Field_Object2D_CtorWithAttachedEffect. */
extern void* g_fieldObject2dSpriteVtable[1];         /* 0x0076DB24 conf 0.60: Vtable for 2D field object sprite (24 slots), installed by Field_Object2D_CtorSprite. */
extern void* g_fieldObject2dMeshVtable[1];           /* 0x0076DBE0 conf 0.60: Vtable for 2D field object mesh (24 slots), installed by Field_Object2D_CtorMesh. */
extern void* g_fieldActionMoveSecondaryDescriptor[8]; /* 0x0076DDB0 conf 0.60: Secondary move descriptor table loaded into local_44 by maybe_Field_Action_MoveInput; contains action step callbacks at  */
extern void* g_fieldActorActionTurnStateVtable[11];  /* 0x0076DEC8 conf 0.60: Vtable for fieldActorActionTurnState (11 slots), slot 1 deleting destructor 0x00413714, slot 2 method maybe_Field_ActorA */
extern void* g_fieldActorBehaviourDeletingDtorVtable[16]; /* 0x0076E004 conf 0.55: Vtable for fieldActorBehaviourDeletingDtor (16 slots), slot 1 deleting destructor Field_ActorBehaviour_DeletingDtor, slo */
extern void* g_fieldMarkerVisualVtable[1];           /* 0x0076E2C0 conf 0.60: Vtable for fieldMarkerVisual (1 slots). Installed by maybe_Field_Marker_CreateVisual. */
extern void* g_fieldNpcObjectVtable[1];              /* 0x0076E9EC conf 0.60: Vtable for fieldNpcObject (1 slots). Installed by Field_NpcObject_Ctor. */
extern void* g_fieldSpriteObjectVtable[1];           /* 0x0076EA88 conf 0.60: Vtable for fieldSpriteObject (1 slots). Installed by Field_SpriteObject_Ctor. */
extern void* g_fieldObjectFactoryKind28Vtable[4];    /* 0x0076F038 conf 0.65: Vtable for fieldObjectFactoryKind28 (4 slots), slot 1 deleting destructor maybe_Battle_ActorAction_DeletingDtorA, slot 2 */
extern void* g_fieldObjectFactoryKind25Vtable[4];    /* 0x0076F14C conf 0.65: Vtable for fieldObjectFactoryKind25 (4 slots), slot 1 deleting destructor maybe_Battle_ActorAction_DeletingDtorB, slot 2 */
extern void* g_fieldObjectFactoryKind49Vtable[4];    /* 0x0076F51C conf 0.65: Vtable for fieldObjectFactoryKind49 (4 slots), slot 1 deleting destructor maybe_Battle_ActorAction_Motion_DeletingDtor,  */
extern void* g_fieldObjectFactoryKind43Vtable[4];    /* 0x0076F8A0 conf 0.65: Vtable for fieldObjectFactoryKind43 (4 slots), slot 1 deleting destructor maybe_Ui_BattleScreen_DtorDelete, slot 2 metho */
extern void* g_fieldNpcActionJumpVtable[12];         /* 0x007702C4 conf 0.55: Vtable for fieldNpcActionJump (12 slots), slot 1 deleting destructor Field_NpcAction_Jump_Dtor, slot 2 method Field_NpcA */
extern void* g_fieldSceneObjectType1Vtable[8];       /* 0x0077034C conf 0.60: Vtable for fieldSceneObjectType1 (8 slots), slot 1 deleting destructor 0x00448c70, slot 2 method Script_IsSystemReady. I */
extern void* g_fieldSceneObjectBaseVtable[8];        /* 0x0077039C conf 0.60: Vtable for field scene object base (24 slots), installed by maybe_Field_SceneObject_CtorBase. */
extern void* g_fieldSceneObjectSpriteComponentVtable[1]; /* 0x00770578 conf 0.60: Vtable for field scene object sprite component (24 slots), installed by maybe_Field_SceneObject_CtorSprite. */
extern void* g_fieldSceneObjectVariantBVtable[1];    /* 0x00770638 conf 0.60: Vtable for field scene object variant B (24 slots), installed by maybe_Field_SceneObject_CtorB. */
extern void* g_fieldSceneObjectVariantCVtable[1];    /* 0x00770B9C conf 0.60: Vtable for field scene object variant C (24 slots), installed by maybe_Field_SceneObject_CtorC. */
extern void* g_fieldSceneObjectVariantDVtable[1];    /* 0x00770C5C conf 0.60: Vtable for field scene object variant D (24 slots), installed by maybe_Field_SceneObject_CtorD. */
extern void* g_fieldMultiPartDestroyVtable[26];      /* 0x00770D58 conf 0.55: Vtable for fieldMultiPartDestroy (26 slots), slot 1 deleting destructor Field_MultiPart_Destroy, slot 2 method Field_Mul */
extern void* g_fieldObjectFactoryKind45Vtable[4];    /* 0x007721DC conf 0.65: Vtable for fieldObjectFactoryKind45 (4 slots), slot 1 deleting destructor maybe_Ui_PartyScreen_Dtor, slot 2 method Field */
extern void* g_fieldObjectFactoryKind33Vtable[4];    /* 0x00772438 conf 0.65: Vtable for fieldObjectFactoryKind33 (4 slots), slot 1 deleting destructor Ui_PartyStatusWindow_Dtor, slot 2 method Field */
extern void* g_fieldObjectFactoryType1374Vtable[4];  /* 0x00772588 conf 0.65: Vtable for fieldObjectFactoryType1374 (4 slots), slot 1 deleting destructor maybe_Ui_PartyScreen_DtorB, slot 2 method Fi */
extern void* g_fieldPartyBattleScreenVtable[4];      /* 0x00772E08 conf 0.60: Vtable for field party battle screen manager (4 slots), installed by FieldParty_InitMemberSlots; slot 1 deleting destruc */
extern void* g_fieldSceneObjectDescriptorVtable[8];  /* 0x00773230 conf 0.60: Vtable for field scene object descriptor (24 slots), installed by maybe_Field_SceneObject_Ctor_E988; slot 1 deleting des */
extern void* g_fieldSceneObjectCtorVt773258Vtable[8]; /* 0x00773258 conf 0.60: Vtable for fieldSceneObjectCtorVt773258 (8 slots), slot 1 deleting destructor 0x0046eddc, slot 2 method maybe_Field_Npc_ */
extern void* g_fieldActorDataInitVtable[1];          /* 0x007738B8 conf 0.60: Vtable for field actor data initialization (11 slots), installed by maybe_Field_ActorData_Init; slot 1 deleting destruct */
extern void* g_fieldObjectFactoryKind21Vtable[4];    /* 0x00774454 conf 0.65: Vtable for fieldObjectFactoryKind21 (4 slots), slot 1 deleting destructor maybe_Battle_Ui_CommandWidget_DtorDelete, slot */
extern void* g_fieldObjectFactoryKind36Vtable[4];    /* 0x00774800 conf 0.65: Vtable for fieldObjectFactoryKind36 (4 slots), slot 1 deleting destructor Battle_PartyMember_EffectDtorDelete, slot 2 me */
extern void* g_fieldObjectFactoryType0050Vtable[4];  /* 0x0077495C conf 0.65: Vtable for fieldObjectFactoryType0050 (4 slots), slot 1 deleting destructor Battle_PartyMember_ModelDtorDelete, slot 2 m */
extern void* g_fieldPartySlotDispatchVtable[4];      /* 0x007751B4 conf 0.60: Vtable for field party slot dispatch (4 slots), installed by FieldParty_InitMemberSlots; slot 1 deleting destructor 0x00 */
extern void* g_fieldActorActionSklEdVtable[11];      /* 0x007753A0 conf 0.60: Vtable for fieldActorActionSklEd (11 slots), slot 1 deleting destructor Field_ActorAction_SklEd_DtorDelete, slot 2 metho */
extern void* g_fieldActorGroupVtable[1];             /* 0x007753D4 conf 0.60: Vtable for fieldActorGroup (1 slots). Installed by Field_ActorGroup_Init. */
extern void* g_fieldInteractJobVtable[8];            /* 0x00775558 conf 0.65: Vtable for fieldInteractJob (structs.json class Field_InteractJob) (8 slots), slot 1 deleting destructor maybe_Ui_Intera */
extern void* g_fieldBattleTriggerVtable[24];         /* 0x0077627C conf 0.65: Vtable for fieldBattleTrigger (structs.json class Field_BattleTrigger) (24 slots), slot 1 deleting destructor 0x004aebf8 */
extern void* g_fieldMapObject2DVtable[8];            /* 0x007762E4 conf 0.60: Vtable for fieldMapObject2D (8 slots), slot 1 deleting destructor 0x004af2a8, slot 2 method 0x0017c020. Installed by Fie */
extern void* g_fieldModelSlotEmitterVtable[26];      /* 0x0077696C conf 0.65: Vtable for fieldModelSlotEmitter (structs.json class Field_ModelSlotEmitter) (26 slots), slot 1 deleting destructor 0x00 */
extern void* g_fieldTaggedObjectVtable[1];           /* 0x00776A64 conf 0.60: Vtable for fieldTaggedObject (1 slots). Installed by maybe_Field_CreateTaggedObject. */
extern void* g_eventRuraVtable[11];                  /* 0x00776BB4 conf 0.65: Vtable for eventRura (structs.json class Event_Rura) (11 slots), slot 1 deleting destructor 0x004b427c, slot 2 method Ev */
extern u8 maybe_g_rodata_00776c66[22];               /* 0x00776C66 conf 0.35: Unaligned rodata block at 0x00776C66 passed by address via literal 0x00180250 in Field_RegisterNpcActions; 22 bytes. */
extern void* g_fieldRunwayEnvPartsVtable[7];         /* 0x00776F6C conf 0.60: Vtable for fieldRunwayEnvParts (7 slots), slot 1 deleting destructor FieldParty_ClearSlotTypeFlags, slot 2 method Contai */
extern void* g_fieldObjectFactoryType1369Vtable[4];  /* 0x00777184 conf 0.65: Vtable for fieldObjectFactoryType1369 (4 slots), slot 1 deleting destructor maybe_FieldParty_MemberModel_DtorA, slot 2 m */
extern void* g_fieldObjectFactoryKind36AltVtable[4]; /* 0x00777484 conf 0.60: Vtable for field object factory kind 36 variant (4 slots), installed by Field_ObjectFactory_Kind36; slot 1 deleting dest */
extern void* g_fieldObjectFactoryType1363Vtable[4];  /* 0x007775E0 conf 0.65: Vtable for fieldObjectFactoryType1363 (4 slots), slot 1 deleting destructor maybe_FieldParty_MemberModel_DtorC, slot 2 m */
extern void* g_gfxSpriteObjectVtable[8];             /* 0x007781C4 conf 0.55: Vtable for gfxSpriteObject (8 slots), slot 1 deleting destructor Gfx_SpriteObject_DtorB, slot 2 method 0x004c6cf8. Insta */
extern void* g_fieldMarkerBaseVtable[8];             /* 0x00778214 conf 0.60: Vtable for field marker base (8 slots), installed by Field_Marker_Ctor; slot 1 deleting destructor Field_Marker_DtorB. */
extern void* g_fieldMarkerDefaultVtable[8];          /* 0x0077823C conf 0.65: Vtable for default field marker (8 slots), installed by Field_Marker_CreateDefault; slot 1 deleting destructor 0x004C868 */
extern void* g_fieldSceneObjectStaticVtable[1];      /* 0x00778280 conf 0.60: Vtable for static field scene object (8 slots), installed by Field_SceneObject_Ctor_vt778280. */
extern void* g_fieldGadgetVariantAVtable[1];         /* 0x0077833C conf 0.60: Vtable for field gadget variant A (8 slots), installed by Field_Gadget_Ctor_vt77833C. */
extern void* g_fieldGadgetVariantBVtable[1];         /* 0x00778438 conf 0.60: Vtable for field gadget variant B (8 slots), installed by Field_Gadget_Ctor_vt778438. */
extern void* g_fieldGadgetVariantCVtable[1];         /* 0x007784F4 conf 0.60: Vtable for field gadget variant C (8 slots), installed by Field_Gadget_Ctor_vt7784F4. */
extern void* g_fieldObjectFactoryKind32Vtable[4];    /* 0x00778F10 conf 0.65: Vtable for fieldObjectFactoryKind32 (4 slots), slot 1 deleting destructor maybe_Battle_EffectList_Dtor, slot 2 method Fi */
extern void* g_fieldPartyModelWithSequenceVtable[4]; /* 0x00779060 conf 0.65: Vtable for field party model with sequence (4 slots), installed by Field_ObjectFactory_Kind38; slot 1 deleting destructo */
extern void* g_fieldObjectFactoryKind50Vtable[4];    /* 0x007791BC conf 0.65: Vtable for fieldObjectFactoryKind50 (4 slots), slot 1 deleting destructor maybe_Battle_Ui_LevelUpPopup_Dtor, slot 2 meth */
extern void* g_uiObjectVtable[8];                    /* 0x00779ECC conf 0.55: Vtable for uiObject (8 slots), slot 1 deleting destructor maybe_Ui_Object_DtorVirtual_D7350, slot 2 method 0x0017c020. I */
extern void* g_fieldObjectSpriteWarpVtable[8];       /* 0x00779EF4 conf 0.65: Vtable for field object sprite warp handler (8 slots), installed by maybe_Field_ObjectSprite_Ctor_D76D4; slot 1 deleting */
extern void* g_fieldObjectSpriteStaticVtable[8];     /* 0x00779F1C conf 0.60: Vtable for static field object sprite (8 slots), installed by maybe_Field_ObjectSprite_CtorStatic. */
extern void* g_fieldObjectHookVtable[8];             /* 0x00779F44 conf 0.60: Vtable for fieldObjectHook (8 slots), slot 1 deleting destructor maybe_Ui_Object_DtorVirtual_D7ABC, slot 2 method 0x0017 */
extern void* g_fieldObjectKind15Vtable[4];           /* 0x0077A778 conf 0.60: Vtable for fieldObjectKind15 (4 slots), slot 1 deleting destructor 0x004e1e48, slot 2 method FieldParty_InitFromParams.  */
extern void* g_fieldActorVariantVtable[16];          /* 0x0077B078 conf 0.60: Vtable for field actor variant (11 slots), installed by maybe_Field_Actor_CtorVariant; slot 1 deleting destructor 0x004E */
extern void* g_ui3DNameRegistryVtable[8];            /* 0x0077B0F0 conf 0.55: Vtable for ui3DNameRegistry (8 slots), slot 1 deleting destructor maybe_Ui3D_NameRegistry_DtorDeleting, slot 2 method 0x */
extern void* g_fieldObjectFactoryKind38Vtable[4];    /* 0x0077B780 conf 0.65: Vtable for field object factory kind 38 (4 slots), installed by Field_ObjectFactory_Kind38; slot 1 deleting destructor 0 */
extern void* g_fieldBattleTriggerGatedVtable[24];    /* 0x0077C1C8 conf 0.60: Vtable for fieldBattleTriggerGated (24 slots), slot 1 deleting destructor 0x004efc7c, slot 2 method Field_BattleTrigger_ */
extern void* g_fieldBattleTriggerEnemyDisplayVtable[24]; /* 0x0077C230 conf 0.60: Vtable for fieldBattleTriggerEnemyDisplay (24 slots), slot 1 deleting destructor 0x004efcd8, slot 2 method Battle_Create */
extern void* g_fieldActorActionWhaleStartVtable[11]; /* 0x0077C4A0 conf 0.60: Vtable for fieldActorActionWhaleStart (11 slots), slot 1 deleting destructor 0x004f1d9c, slot 2 method Event_Rura_Start. */
extern void* g_fieldLampGlowVtable[4];               /* 0x0077CEFC conf 0.65: Vtable for field lamp glow sub-component (4 slots), installed by maybe_Field_LampGimmick_CtorGlow; slot 1 deleting destr */
extern void* g_fieldLampGimmickBaseVtable[10];       /* 0x0077CF14 conf 0.65: Vtable for field lamp gimmick base (structs.json class Field_LampGimmick) (10 slots), installed by maybe_Field_LampGimmi */
extern void* g_fieldNpcActionVtable[12];             /* 0x0077D000 conf 0.55: Vtable for fieldNpcAction (12 slots), slot 1 deleting destructor Field_NpcAction_DtorDelete, slot 2 method Field_NpcActi */
extern void* g_uiSceneObjectVtable[8];               /* 0x0077D038 conf 0.55: Vtable for uiSceneObject (8 slots), slot 1 deleting destructor maybe_Ui_SceneObject_Dtor, slot 2 method 0x0017c020. Inst */
extern void* g_fieldObjectFactoryType0893Vtable[4];  /* 0x0077D338 conf 0.65: Vtable for fieldObjectFactoryType0893 (4 slots), slot 1 deleting destructor FieldParty_ActionSpawnInfoPopup_Delete, slot */
extern void* g_fieldObjectFactoryType1364Vtable[4];  /* 0x0077D44C conf 0.65: Vtable for fieldObjectFactoryType1364 (4 slots), slot 1 deleting destructor FieldParty_ActionPlayEmote_Delete, slot 2 me */
extern void* g_fieldObject2DDefaultVtable[24];       /* 0x0077D8BC conf 0.60: Vtable for fieldObject2DDefault (24 slots), slot 1 deleting destructor 0x00591adc, slot 2 method Battle_CreateEnemyDispl */
extern void* g_fieldObject2DMeshVtable[24];          /* 0x0077D924 conf 0.60: Vtable for fieldObject2DMesh (24 slots), slot 1 deleting destructor maybe_Battle_Unit_Delete, slot 2 method Battle_Creat */
extern void* g_fieldBeeRiseActionVtable[11];         /* 0x0077DA0C conf 0.65: Vtable for fieldBeeRiseAction (structs.json class Field_BeeRiseAction) (11 slots), slot 1 deleting destructor Field_BeeR */
extern void* g_fieldSpinActionVtable[11];            /* 0x0077DA40 conf 0.65: Vtable for fieldSpinAction (structs.json class Field_SpinAction) (11 slots), slot 1 deleting destructor Field_SpinAction */
extern void* g_fieldObjectFactoryKind34Vtable[4];    /* 0x0077DC00 conf 0.65: Vtable for fieldObjectFactoryKind34 (4 slots), slot 1 deleting destructor maybe_Ui_Screen_DeleteInstance, slot 2 method  */
extern void* g_fieldCharVtable[8];                   /* 0x0077E0B0 conf 0.65: Vtable for fieldChar (structs.json class Field_Char) (8 slots), slot 1 deleting destructor Field_Char_Delete, slot 2 met */
extern void* g_fieldActionVtable[11];                /* 0x0077E0D8 conf 0.60: Vtable for fieldAction (11 slots), slot 1 deleting destructor maybe_Field_CharNarrowPassAction_Delete, slot 2 method Fie */
extern void* g_fieldObject2DSpriteVtable[24];        /* 0x0077E284 conf 0.60: Vtable for fieldObject2DSprite (24 slots), slot 1 deleting destructor 0x0059aa60, slot 2 method Field_BattleTrigger_Star */
extern void* g_uiModelViewVtable[8];                 /* 0x0077E2EC conf 0.65: Vtable for uiModelView (structs.json class Ui_ModelView) (8 slots), slot 1 deleting destructor maybe_Ui_ModelView_Delete */
extern void* g_fieldObjectSpriteDeleteVtable[8];     /* 0x0077E314 conf 0.60: Vtable for field object sprite deletion handler (8 slots), installed by maybe_Field_ObjectSprite_Ctor; slot 1 deleting d */
extern void* g_fieldObjectFactoryKind44Vtable[4];    /* 0x0077E450 conf 0.65: Vtable for fieldObjectFactoryKind44 (4 slots), slot 1 deleting destructor Battle_Ui_PartyRowPanel_DeleteAlt, slot 2 meth */
extern void* g_fieldObjectFactoryKind40Vtable[4];    /* 0x0077EC6C conf 0.65: Vtable for fieldObjectFactoryKind40 (4 slots), slot 1 deleting destructor Battle2DUnit_StateAction_Delete, slot 2 method */
extern void* g_field2dSpriteThunkVtable[8];          /* 0x0077EF60 conf 0.60: Vtable for 2D sprite deletion thunk (8 slots), installed by maybe_Field_Scene_UpdateObjectsFromTable; slot 1 deleting de */
extern void* g_battleSequenceThunkVtable[8];         /* 0x0077F174 conf 0.60: Vtable for battle sequence thunk object (8 slots), installed by maybe_Field_ObjectType_InitRecord; slot 1 deleting destr */
extern void* g_field2dSpriteSimpleThunkVtable[8];    /* 0x0077F324 conf 0.60: Vtable for simple 2D sprite deletion thunk (8 slots), installed by maybe_Field_Scene_UpdateObjectsFromTable; slot 1 dele */
extern void* g_fieldSpriteSceneObjectVtable[1];      /* 0x0077FBDC conf 0.60: Vtable for fieldSpriteSceneObject (1 slots). Installed by Field_SpriteSceneObject_Create. */
extern void* g_fieldLevelDataVtable[2];              /* 0x0077FC9C conf 0.55: Vtable for fieldLevelData (2 slots), slot 1 deleting destructor Field_LevelData_Dtor. Installed by Field_LevelData_Dtor. */
extern void* g_fieldNpcActionBehaviorVtable[11];     /* 0x0077FE30 conf 0.60: Vtable for fieldNpcActionBehavior (11 slots), slot 1 deleting destructor maybe_Container_DestroyObjectRefB, slot 2 metho */
extern void* g_fieldBillboardDescriptorVtable[8];    /* 0x007800C8 conf 0.60: Vtable for fieldBillboardDescriptor (8 slots), slot 1 deleting destructor 0x001d8718, slot 2 method Ui_TimeWindow_BindPa */
extern void* g_gfxNodeDefaultDescriptor[8];          /* 0x007801A0 conf 0.60: Default configuration and callback block copied into local stack variables during Gfx_Node_Ctor, Battle_AnimWindow_Ctor  */
extern void* g_fieldActorListNodePoolVtable[3];      /* 0x0078104C conf 0.65: Vtable of the intrusive node list that seeds the field actor-list node pool; installed by Field_InitActorListNodePool (l */
extern void* g_fieldActorListCursorVtable[1];        /* 0x00781064 conf 0.60: Single-slot vtable/destructor thunk for the actor-list cursor object; Field_InitActorListNodePool and maybe_Field_InitAc */
extern u32 g_actor2DSpriteMeshDefaultParams[4];      /* 0x00782234 conf 0.55: Default zero parameter block passed into Gfx_CreateSpriteMesh and animation instance constructors by Actor2D_CreateSprit */
extern u8 g_fieldActorPlacementResetFlag;            /* 0x0078251C conf 0.50: Reset flag byte read by Field_Actor_InitFromPlacementRecord when creating an actor model/animator from a placement recor */
extern u32 g_actor2DSpanDefaultOffsets[4];           /* 0x00782524 conf 0.55: Default sprite span offset block read by Actor2D_CreateEightSpans and Actor2D_CreateEightSpansAlt when building 2D actor */
extern void* g_actorModelSetByNameVtable[1];         /* 0x00782534 conf 0.55: Callback descriptor / single-slot vtable installed during actor model set switching in Actor_ApplyModelSetByName and Act */
extern u32 maybe_g_fieldSceneObjectDefaults[4];      /* 0x00782648 conf 0.45: Default initialization block loaded by maybe_Field_SceneObject_CtorWithDefaults when building a field scene object. */
extern u32 g_actorActionWhaleStartDefaults[2];       /* 0x00782740 conf 0.50: Default zero-constant block copied during Whale_Start action initialization in Actor_Action_WhaleStart_Ctor and Battle_A */
extern u32 maybe_g_fieldActorEffectSlotDefaults[4];  /* 0x00782748 conf 0.45: Default effect parameter block loaded by Field_Actor_PlayEffectBySlot and maybe_Gfx_CreateSpriteFromTemplate when initia */
extern u32 maybe_g_fieldEffectDescDefaults[4];       /* 0x00782850 conf 0.45: Default parameter descriptor copied into local state by maybe_Field_EffectDesc_Build. */
extern u32 maybe_g_fieldCameraSceneWorkDefaults[4];  /* 0x007829A4 conf 0.45: Zero-initialized default block copied into camera work and field scene structures during Camera_UpdateWorkPath and Field */
extern u32 maybe_g_fieldBitmapPoolDefaults[4];       /* 0x00782AC0 conf 0.45: Default zero block used during bitmap pool initialization and field area actor registration in Mem_BitmapPool_Init and m */
extern void* g_field2DMapChipColumnRendererVtable[1]; /* 0x007834C8 conf 0.65: Vtable of the 2D map chip column renderer; Field2D_MapChip_InitColumnRenderer installs this pointer at self[0]. Slot 0 p */
extern u32 g_field2DMapChipCollisionMaskDefaults[4]; /* 0x0078367C conf 0.55: Default collision and passability bitmask block used by Field2D_MapChip_BuildCollisionMask and Field2D_MapChip_QueryColl */
extern void* g_field2DSceneSpawnPointsVtable[2];     /* 0x007836A4 conf 0.65: Vtable of the 2D scene spawn point manager; Field2D_Scene_InitSpawnPoints installs it at self[0]. Slots are 0x005C3FE0 a */
extern void* g_field2DSceneLayerDescriptorVtable[1]; /* 0x007836C4 conf 0.65: Vtable of the 2D scene layer descriptor; Field2D_Scene_AllocLayerList installs it at self[0]. Slot 0 is 0x005C71AC. */
extern void* g_field2DTaskVtable[1];                 /* 0x0078381C conf 0.60: Vtable of the 0x38-byte field 2D task object; maybe_Field2D_Task_Init installs it at self[0]. Slot 0 is 0x005C89D0. */
extern void* g_field2DSpriteTweenMoveVtable[1];      /* 0x00783838 conf 0.65: Vtable of the 2D movement tween controller; Field2D_Sprite_CreateTweenMove installs it at self[0]. Slot 0 is 0x005C8C68. */
extern void* g_field2DSpriteNodeVtable[1];           /* 0x00783870 conf 0.60: Vtable of the 2D sprite node initialized from parameters; maybe_Field2D_SpriteNode_InitFromParams installs it at self[0] */
extern void* g_field2DSpritePathFollowerVtable[1];   /* 0x0078388C conf 0.65: Vtable of the 2D path follower controller; Field2D_Sprite_CreatePathFollower installs it at self[0]. Slot 0 is 0x005C936 */
extern void* g_field2DSpriteNodeFromParamsVtable[1]; /* 0x007838A8 conf 0.60: Vtable of the 2D sprite node created from parameters; maybe_Field2D_SpriteNode_CreateFromParams installs it at self[0].  */
extern void* g_field2DSpriteAppearanceNodeVtable[1]; /* 0x007838E0 conf 0.65: Vtable of the sprite appearance node; Field2D_SpriteNode_CreateAppearanceNode installs it at self[0]. Slot 0 is 0x005C95 */
extern void* g_field2DSpriteBobMotionVtable[1];      /* 0x007838FC conf 0.65: Vtable of the 2D bob motion controller; Field2D_Sprite_CreateBobMotion installs it at self[0]. Slot 0 is 0x005C990C. */
extern void* g_field2DSpriteVisibilityVtable[1];     /* 0x0078399C conf 0.60: Vtable of the 2D sprite visibility controller; Field2D_Sprite_UpdateVisibility installs it at self[0]. Slot 0 is 0x005CA */
extern void* g_field2DSceneLayerEntryVtable[1];      /* 0x007839F4 conf 0.65: Vtable of the 2D scene layer update entry; Field2D_Scene_InitLayerEntry installs it at self[0]. Slot 0 is 0x005CB8F8. */
extern void* g_field2DSpriteTweenMoveAltVtable[1];   /* 0x00783A4C conf 0.65: Vtable of the alternative 2D movement tween controller; Field2D_Sprite_CreateTweenMoveAlt installs it at self[0]. Slot 0 */
extern void* g_field2DSpriteNodeChildVtable[1];      /* 0x00783A70 conf 0.60: Vtable of the 2D field child sprite node; maybe_Field2D_SpriteNode_CreateChild installs it at self[0]. Slot 0 is 0x005CC */
extern void* g_field2DSpriteTweenMoveDirectVtable[1]; /* 0x00783A94 conf 0.65: Vtable of the direct 2D movement controller; Field2D_Sprite_CreateTweenMoveDirect installs it at self[0]. Slot 0 is 0x00 */
extern void* g_field2DMapInlineDescBVtable[1];       /* 0x00783AB8 conf 0.60: Vtable of the 2D map inline descriptor variant B; maybe_Field2D_Map_SetInlineDescriptorB installs it at self[0]. Slot 0  */
extern void* g_field2DSpriteAnimNodeVtable[1];       /* 0x00783B1C conf 0.60: Vtable of the 2D sprite animation node; Field2D_SpriteNode_UpdateAnimation installs it at self[0]. Slot 0 is 0x005CDABC. */
extern void* g_field2DMapInlineDescAVtable[1];       /* 0x00783B5C conf 0.60: Vtable of the 2D map inline descriptor variant A; maybe_Field2D_Map_SetInlineDescriptorA installs it at self[0]. Slot 0  */
extern void* g_field2DSpriteBobHeadingVtable[1];     /* 0x00783C44 conf 0.60: Vtable of the 2D bob motion and heading controller; Field2D_Sprite_UpdateBobAndHeading installs it at self[0]. Slot 0 is */
extern void* g_field2DSpriteElevationThunkVtable[1]; /* 0x00783CAC conf 0.60: Vtable of the 2D sprite elevation controller thunk; Field2D_Sprite_SetElevationThunk installs it at self[0]. Slot 0 is 0 */
extern void* g_field2DSpriteMeshNodeVtable[1];       /* 0x00783CD4 conf 0.65: Vtable of the 2D sprite mesh node; Field2D_SpriteNode_CreateMeshNode installs it at self[0]. Slot 0 is 0x005D06A8. */
extern void* g_field2DMapChipGridRendererVtable[1];  /* 0x00783CE8 conf 0.65: Vtable of the 2D map chip grid renderer; Field2D_MapChip_InitGridRenderer installs it at self[0]. Slot 0 is 0x005D0A60. */
extern void* g_fieldGimmickMasterConfigVtable[3];    /* 0x00783D34 conf 0.65: Vtable installed at offset +0x68 of the field gimmick object in Field_Gimmick_Ctor (literal 0x005E4CF0). */
extern void* g_fieldGimmickHandlerList5PrimaryVtable[3]; /* 0x00783D48 conf 0.65: Primary vtable of the 5-entry gimmick handler list component; Field_Gimmick_InitHandlerList5 installs it at self[0]. */
extern void* g_fieldGimmickMasterStateVtable[3];     /* 0x00783D5C conf 0.65: Secondary configuration vtable installed at offset +0x68 of the field gimmick object in Field_Gimmick_Ctor (literal 0x00 */
extern void* g_fieldGimmickHandlerList3PrimaryVtable[3]; /* 0x00783D70 conf 0.65: Primary vtable of the 3-entry gimmick handler list component; Field_Gimmick_InitHandlerList3 installs it at self[0]. */
extern void* g_fieldGimmickHandleSlotPrimaryVtable[3]; /* 0x00783D98 conf 0.65: Primary vtable of the single-handle gimmick slot component; Field_Gimmick_InitHandleSlot installs it at self[0]. */
extern void* g_fieldGimmickSlotArray8PrimaryVtable[3]; /* 0x00783DAC conf 0.65: Primary vtable of the 8-slot gimmick component; maybe_Field_Gimmick_InitSlotArray8 installs it at self[0]. */
extern void* g_fieldGimmickHandleSlotBPrimaryVtable[3]; /* 0x00783DC0 conf 0.65: Primary vtable of gimmick handle slot variant B; Field_Gimmick_InitHandleSlotB installs it at self[0]. */
extern void* g_fieldGimmickActorSlotPrimaryVtable[3]; /* 0x00783DD4 conf 0.65: Primary vtable of the gimmick actor slot component; Field_Gimmick_InitActorSlot installs it at self[0]. */
extern void* g_fieldGimmickHandlerList9PrimaryVtable[3]; /* 0x00783DFC conf 0.65: Primary vtable of the 9-entry gimmick handler list component; Field_Gimmick_InitHandlerList9 installs it at self[0]. */
extern void* g_fieldGimmickHandlerList5BPrimaryVtable[3]; /* 0x00783E10 conf 0.65: Primary vtable of 5-entry gimmick handler list variant B; Field_Gimmick_InitHandlerList5B installs it at self[0]. */
extern void* g_fieldGimmickHandlePairPrimaryVtable[3]; /* 0x00783E24 conf 0.65: Primary vtable of the two-handle gimmick component; Field_Gimmick_InitHandlePair installs it at self[0]. */
extern void* g_fieldGimmickHandlePairBPrimaryVtable[3]; /* 0x00783E38 conf 0.65: Primary vtable of two-handle gimmick component variant B; Field_Gimmick_InitHandlePairB installs it at self[0]. */
extern void* g_fieldGimmickHandlerList7PrimaryVtable[3]; /* 0x00783E4C conf 0.65: Primary vtable of the 7-entry gimmick handler list component; Field_Gimmick_InitHandlerList7 installs it at self[0]. */
extern void* g_fieldGimmickParamBlockVtable[3];      /* 0x00783E60 conf 0.60: Vtable of the gimmick parameter block component; maybe_Field_Gimmick_InitParamBlock installs it at self[0]. Slots are 0x */
extern void* g_fieldGimmickParam32Vtable[3];         /* 0x00783E74 conf 0.60: Vtable of the 32-byte gimmick parameter handler; maybe_Field_Gimmick_InitParam32 installs it at self[0]. */
extern void* g_fieldGimmickHandlePairCVtable[3];     /* 0x00783E88 conf 0.60: Vtable of gimmick handle pair C component; Field_Gimmick_InitHandlePairC installs it at self[0]. */
extern void* g_fieldGimmickParamBlockBVtable[3];     /* 0x00783E9C conf 0.60: Vtable of gimmick parameter block component variant B; maybe_Field_Gimmick_InitParamBlockB installs it at self[0]. */
extern void* g_fieldGimmickHandleSlotCVtable[3];     /* 0x00783EC4 conf 0.60: Vtable of gimmick handle slot C component; Field_Gimmick_InitHandleSlotC installs it at self[0]. */
extern void* g_fieldGimmickFlagTableVtable[3];       /* 0x00783ED8 conf 0.60: Vtable of gimmick flag table component; Field_Gimmick_InitFlagTable installs it at self[0]. */
extern void* g_fieldGimmickHandleSlotDVtable[3];     /* 0x00783EEC conf 0.60: Vtable of gimmick handle slot D component; Field_Gimmick_InitHandleSlotD installs it at self[0]. */
extern void* g_fieldGimmickAnchorVtable[1];          /* 0x00783F00 conf 0.60: Vtable of the gimmick anchor sub-object; maybe_Field_Gimmick_AnchorCtor installs it at self[0]. Slot 0 points to 0x005D3 */
extern void* g_fieldGimmickHandlerList3Vtable[3];    /* 0x00783F28 conf 0.60: Vtable of the 3-entry gimmick handler list component; Field_Gimmick_InitHandlerList3 installs it at self[0]. */
extern void* g_fieldGimmickHandlerList3BVtable[3];   /* 0x00783F3C conf 0.60: Vtable of the 3-entry gimmick handler list component variant B; maybe_Field_Gimmick_InitHandlerList3B installs it at sel */
extern void* g_fieldGimmickHandleSlotVtable[3];      /* 0x00783F50 conf 0.60: Vtable of the gimmick single handle slot component; Field_Gimmick_InitHandleSlot installs it at self[0]. */
extern void* g_fieldGimmickValuePairVtable[1];       /* 0x00783F64 conf 0.60: Vtable of the gimmick value pair component; maybe_Field_Gimmick_InitValuePair installs it at self[0]. Slot 0 points to 0 */
extern void* g_fieldGimmickSlotArray8Vtable[3];      /* 0x00783F8C conf 0.60: Vtable of the 8-slot gimmick component; maybe_Field_Gimmick_InitSlotArray8 installs it at self[0]. */
extern void* g_fieldGimmickStateGetterVtable[1];     /* 0x00783FA0 conf 0.60: Vtable of the gimmick state accessor sub-object; maybe_Field_Gimmick_GetManagerState installs it at self[0]. Slot 0 poin */
extern void* g_fieldGimmickRectPairVtable[1];        /* 0x00783FC8 conf 0.60: Vtable of the gimmick rectangle pair sub-object; maybe_Field_Gimmick_InitRectPair installs it at self[0]. Slot 0 points  */
extern void* g_fieldGimmickHandleSlotBVtable[3];     /* 0x00783FF0 conf 0.60: Vtable of gimmick handle slot component variant B; Field_Gimmick_InitHandleSlotB installs it at self[0]. */
extern void* g_fieldGimmickActorSlotVtable[3];       /* 0x00784018 conf 0.60: Vtable of the gimmick actor slot component; Field_Gimmick_InitActorSlot installs it at self[0]. */
extern void* g_fieldGimmickHandlerList5Vtable[3];    /* 0x00784040 conf 0.60: Vtable of the 5-entry gimmick handler list component; Field_Gimmick_InitHandlerList5 installs it at self[0]. */
extern void* g_fieldGimmickHandlerList9Vtable[3];    /* 0x00784054 conf 0.60: Vtable of the 9-entry gimmick handler list component; Field_Gimmick_InitHandlerList9 installs it at self[0]. */
extern void* g_fieldGimmickHandlerList5BVtable[3];   /* 0x00784068 conf 0.60: Vtable of the 5-entry gimmick handler list component variant B; Field_Gimmick_InitHandlerList5B installs it at self[0]. */
extern void* g_fieldGimmickHandlePairVtable[3];      /* 0x0078407C conf 0.60: Vtable of the gimmick two-handle component; Field_Gimmick_InitHandlePair installs it at self[0]. */
extern void* g_fieldGimmickHandlePairBVtable[3];     /* 0x00784090 conf 0.60: Vtable of the gimmick two-handle component variant B; Field_Gimmick_InitHandlePairB installs it at self[0]. */
extern void* g_fieldGimmickHandlerList7Vtable[3];    /* 0x007840A4 conf 0.60: Vtable of the 7-entry gimmick handler list component; Field_Gimmick_InitHandlerList7 installs it at self[0]. */
extern void* g_fieldGimmickCompositeAVtable[3];      /* 0x007840B8 conf 0.65: Vtable of the composite gimmick outer object; Field_Gimmick_CreateCompositeA and Field_Gimmick_CreateCompositeB install  */
extern void* g_fieldGimmickSubBufferVtable[1];       /* 0x007840CC conf 0.60: Vtable of the gimmick buffer sub-object; Field_Gimmick_ReleaseBuffers installs it during teardown. Slot 0 is Field_Gimmi */
extern void* g_fieldGimmickCompositeBVtable[3];      /* 0x007840E8 conf 0.65: Secondary vtable of the composite gimmick outer object; Field_Gimmick_CreateCompositeA and Field_Gimmick_CreateComposite */
extern void* g_fieldGimmickHandlePairDVtable[3];     /* 0x007840FC conf 0.60: Vtable of the gimmick two-handle component variant D; Field_Gimmick_InitHandlePairC installs it at self[0]. */
extern void* g_fieldGimmickParamBlockCVtable[3];     /* 0x00784110 conf 0.60: Secondary vtable of gimmick parameter block component variant B; maybe_Field_Gimmick_InitParamBlockB installs it. */
extern void* g_fieldGimmickSlotArray8BVtable[3];     /* 0x00784124 conf 0.60: Vtable of the 8-slot gimmick component variant B; Field_Gimmick_InitSlotArray8B installs it at self[0]. */
extern void* g_fieldGimmickHandleSlotEVtable[3];     /* 0x00784138 conf 0.60: Secondary vtable of gimmick handle slot C component; Field_Gimmick_InitHandleSlotC installs it. */
extern void* g_fieldGimmickFlagTableBVtable[3];      /* 0x0078414C conf 0.60: Secondary vtable of gimmick flag table component; Field_Gimmick_InitFlagTable installs it. */
extern void* g_fieldGimmickHandleSlotFVtable[3];     /* 0x00784160 conf 0.60: Secondary vtable of gimmick handle slot D component; Field_Gimmick_InitHandleSlotD installs it. */
extern void* g_fieldUiGimmickVtable[30];             /* 0x00784174 conf 0.70: Master vtable of Field_UiGimmick (the UI-driven field gimmick class); installed by Field_UiGimmick_Dtor and constructors */
extern void* g_fieldHandleListVtable[1];             /* 0x00784304 conf 0.60: Vtable of the field handle list object; maybe_Field_HandleList_Ctor installs it at self[0]. Slot 0 points to Field_Scene */
extern char g_fieldSpriteMarkerName[7];              /* 0x00784994 conf 0.80: ASCII string "sprite" (with NUL terminator) passed to Gfx_CreateSpriteMesh by Field_SpriteMarker_Create and Field_Sprite */
extern u32 g_actorColorTable7A2CCC[12];              /* 0x007A2CCC conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A2CCC for field actor rendering pale */
extern u32 g_fieldSceneNodeUpdateMapRecord;          /* 0x007A30C0 conf 0.55: Map placement record synchronization state word updated by Field_SceneNode_UpdateMapRecord. */
extern u32 g_fieldActorTalkMotionPrefix;             /* 0x007A3120 conf 0.55: Per-character talk motion resource name prefix pointer used by Field_Actor_PlayTalkMotionFromTable. */
extern u32 g_fieldActorTalkMotionBuffer;             /* 0x007A3124 conf 0.55: Talk motion name formatting buffer pointer passed to func_0010009C by Field_Actor_PlayTalkMotionFromTable. */
extern u32 g_fieldActorEffectDefaults[2];            /* 0x007A3168 conf 0.55: Default effect configuration descriptor referenced by Effect_CreateInstanceWithDefaults and Field_CreateActorFromId. */
extern u8 g_fieldActorModelGroupCounter;             /* 0x007A316C conf 0.50: Group counter byte read during unit model construction in BattleScene_BuildEnemyModel and Field_ActorGroup_AddMember. */
extern u32 g_fieldObjectKind15AttachmentParams[4];   /* 0x007A3230 conf 0.50: Array of placement record attachment parameters queried by maybe_Field_ObjectKind15_UpdateAttachment. */
extern u32 g_diveObjectActor3DParams[2];             /* 0x007A35B0 conf 0.65: Registration parameter table for Dive_ObjectActor3D; Field_RegisterActorClass_Dive_ObjectActor3D links it. */
extern u32 g_diveSpiritSquadActor3DParams[3];        /* 0x007A35B8 conf 0.65: Registration parameter table for Dive_SpiritSquadActor3D; Field_RegisterActorClass_Dive_SpiritSquadActor3D links it. */
extern u32 g_spiritMenuActor3DParams[2];             /* 0x007A35C4 conf 0.65: Registration parameter table for SpiritMenuActor3D; Field_RegisterActorClass_SpiritMenuActor3D links it. */
extern u8 maybe_g_fieldNpcJumpRandomState;           /* 0x007A3688 conf 0.45: Random state byte read during NPC jump trajectory planning in maybe_Field_NpcJumpAction_RandomizeAndPlan. */
extern u32 g_fieldNpcSightCheckFlag;                 /* 0x007A36E4 conf 0.55: Perception test flag read by Field_NpcCheckSight to verify whether an NPC can detect the player. */
extern u32 g_enemyActorParams[10];                   /* 0x007A36F4 conf 0.65: Static registration parameter block (10 words) filled with default actor attributes by Field_RegisterActorClass_EnemyAct */
extern u32 g_enemyMenuActorParams[13];               /* 0x007A3774 conf 0.65: Registration parameter table for EnemyMenuActor (enemy 3D model shown in bestiary/menu); linked by Field_RegisterActorCl */
extern u32 g_fieldItemGet3DActorParams[9];           /* 0x007A37A8 conf 0.65: Registration parameter table for FieldItemGet3DActor; Field_RegisterActorClass_FieldItemGet3DActor links it. */
extern u32 g_gimmick2DClassesParamsA;                /* 0x007A37CC conf 0.60: First registration parameter block for 2D field gimmicks configured by Field_RegisterGimmick2DClasses. */
extern u32 g_gimmick2DClassesParamsB;                /* 0x007A37D0 conf 0.60: Second registration parameter block for 2D field gimmicks configured by Field_RegisterGimmick2DClasses. */
extern u32 g_gmGetOffGondola2DParams[3];             /* 0x007A383C conf 0.65: Registration parameter table for GmGetOffGondola2D; Field_RegisterActorClass_GmGetOffGondola2D links it. */
extern u32 g_gmHellkachaRock2DParams[9];             /* 0x007A3848 conf 0.65: Registration parameter table for GmHellkachaRock2D; Field_RegisterActorClass_GmHellkachaRock2D links it. */
extern u32 g_gmPitfall2DParams[10];                  /* 0x007A386C conf 0.65: Registration parameter table for GmPitfall2D; Field_RegisterActorClass_GmPitfall2D links it. */
extern u32 g_gmWaterfall2DParams[6];                 /* 0x007A38F4 conf 0.65: Registration parameter table for GmWaterfall2D; Field_RegisterActorClass_GmWaterfall2D links it. */
extern u32 g_gmBeeRider2DParams[6];                  /* 0x007A390C conf 0.65: Registration parameter table for GmBeeRider2D; Field_RegisterActorClass_GmBeeRider2D links it. */
extern u32 g_gmDullahanKnight2DParams[12];           /* 0x007A3924 conf 0.65: Registration parameter table for GmDullahanKnight2D; Field_RegisterActorClass_GmDullahanKnight2D links it. */
extern u32 g_gmHellkacha2DParams[3];                 /* 0x007A3954 conf 0.65: Registration parameter table for GmHellkacha2D; Field_RegisterActorClass_GmHellkacha2D links it. */
extern u32 g_gmHorse2DParams[3];                     /* 0x007A3960 conf 0.65: Registration parameter table for GmHorse2D; Field_RegisterActorClass_GmHorse2D links it. */
extern u32 g_gmShip2DParams[12];                     /* 0x007A396C conf 0.65: Registration parameter table for GmShip2D; Field_RegisterActorClass_GmShip2D links it. */
extern u32 g_gmWhale2DParams[12];                    /* 0x007A399C conf 0.65: Registration parameter table for GmWhale2D; Field_RegisterActorClass_GmWhale2D links it. */
extern u32 g_pursuer3DActorParams[3];                /* 0x007A3A10 conf 0.65: Registration parameter table for Pursuer3DActor; Field_RegisterActorClass_Pursuer3DActor links it. */
extern u32 g_gmPursuerSquad3DActorParams[3];         /* 0x007A3A1C conf 0.65: Registration parameter table for GmPursuerSquad3DActor; Field_RegisterActorClass_GmPursuerSquad3DActor links it. */
extern u32 g_gmSpiritGenerator3DActorParamsA[3];     /* 0x007A3A28 conf 0.65: First registration parameter table for GmSpiritGenerator3DActor; Field_RegisterActorClass_GmSpiritGenerator3DActor links */
extern u32 g_gmSpiritGenerator3DActorParamsB[13];    /* 0x007A3A34 conf 0.65: Second registration parameter table for GmSpiritGenerator3DActor; Field_RegisterActorClass_GmSpiritGenerator3DActor link */
extern u32 g_fieldActorScheduleUpdateState;          /* 0x007A3A68 conf 0.55: Active schedule entry state pointer updated during actor schedule processing in Field_ActorSchedule_Update. */
extern u32 g_gmWorldFloating3DActorParams[10];       /* 0x007A3A74 conf 0.65: Registration parameter table for GmWorldFloating3DActor; Field_RegisterActorClass_GmWorldFloating3DActor links it. */
extern u32 g_gmVehicle3DActorParamsA;                /* 0x007A3A9C conf 0.65: First registration parameter block for GmVehicle3DActor; Field_RegisterActorClass_GmVehicle3DActor links it. */
extern u32 g_gmVehicle3DActorParamsB[9];             /* 0x007A3AA0 conf 0.65: Second registration parameter block for GmVehicle3DActor; Field_RegisterActorClass_GmVehicle3DActor links it. */
extern u32 g_fieldActorDetachTargetState;            /* 0x007A3B14 conf 0.55: Attached entity handle status flag checked by Field_Actor_DetachTargetAndReset and Ui_RegisterStaticObject_7A3B14. */
extern u32 g_npc3DActorParamsA;                      /* 0x007A3C38 conf 0.65: First registration parameter block for NPC3DActor; Field_RegisterActorClass_NPC3DActor links it. */
extern u32 g_npc3DActorParamsB[12];                  /* 0x007A3C3C conf 0.65: Second registration parameter block for NPC3DActor; Field_RegisterActorClass_NPC3DActor links it. */
extern u32 g_fieldNpcApproachAnimName;               /* 0x007A3C6C conf 0.55: Character approach animation name pointer read in Field_Npc_OnApproach when checking player proximity. */
extern u32 g_attachVehicleActor3DParams[10];         /* 0x007A3CF8 conf 0.65: Registration parameter table for AttachVehicleActor3D; Field_RegisterActorClass_AttachVehicleActor3D links it. */
extern u32 maybe_g_fieldActorNearbyListA;            /* 0x007A3EB4 conf 0.45: Float pointer / list head used in nearby same-type actor searches by maybe_Field_Actor_FindNearbySameType. */
extern u32 g_fieldActionCameraRelativeDirTable[6];   /* 0x007A3EC8 conf 0.60: Table of direction thresholds used by Field_Action_GetCameraRelativeDirection to resolve camera-relative motion angles. */
extern u8 maybe_g_fieldActionMoveDirScale;           /* 0x007A3ECC conf 0.45: Movement direction scale multiplier read in maybe_Field_Action_MoveDir. */
extern u32 g_fieldActionDirAnimTable[4];             /* 0x007A3EE8 conf 0.60: Directional animation resource table read in Field_Action_SelectDirAnim to map motion heading to animation id. */
extern u32 maybe_g_fieldActorActionJumpParam;        /* 0x007A3F18 conf 0.45: Actor jump trajectory parameter word updated in maybe_Field_ActorAction_UpdateJump. */
extern u8 g_fieldHellTackleSpeedThreshold;           /* 0x007A3F38 conf 0.55: Speed threshold byte compared against in-flight speed in Field_HellTackleAction_Update. */
extern u8 g_fieldHellTackleStartSpeed;               /* 0x007A3F3C conf 0.55: Initial speed multiplier byte used in Field_HellTackleAction_Start to set self->f_3C. */
extern u8 maybe_g_fieldActorActionJumpGravity;       /* 0x007A3F50 conf 0.45: Gravity/acceleration adjustment byte read in maybe_Field_ActorAction_UpdateJump. */
extern u32 g_playerActor2DParams[10];                /* 0x007A3F68 conf 0.65: Registration parameter table for PlayerActor2D; Field_RegisterActorClass_PlayerActor2D links it. */
extern u32 g_uiStaticObject7A3FFC;                   /* 0x007A3FF8 conf 0.55: Static UI registration object state word referenced in Ui_RegisterStaticObject_7A3FFC. */
extern u32 g_smithProductActor3DParams[3];           /* 0x007A4018 conf 0.65: Registration parameter table for SmithProductActor3D; Field_RegisterActorClass_SmithProductActor3D links it. */
extern u32 g_smithStandActor3DParams[3];             /* 0x007A402C conf 0.65: Registration parameter table for SmithStandActor3D; Field_RegisterActorClass_SmithStandActor3D links it. */
extern u32 maybe_g_actorColorTable7A41A8[12];        /* 0x007A41A8 conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A41A8. */
extern u32 maybe_g_fieldActorParamBlock68745C;       /* 0x007A58F5 conf 0.45: Parameter block word initialized in maybe_Field_InitActorParamBlock_68745C. */
extern u8 maybe_g_fieldPartyTalkDistanceThreshold;   /* 0x007A5A50 conf 0.45: Distance threshold byte checked in maybe_FieldParty_Talk_Update during party talk trigger checks. */
extern u32 g_actorColorTable7A5C74[12];              /* 0x007A5C74 conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A5C74 for field actor rendering pale */
extern u32 g_actorColorTable7A5C78;                  /* 0x007A5C78 conf 0.60: One-shot initialization guard flag for color table 0x007A5C74; checked by Field_InitActorColorTable_7A5C74. */
extern u32 maybe_g_actorColorTable7A5E58;            /* 0x007A5E58 conf 0.45: Initialization guard flag for color table 0x007A5E5C; checked by maybe_Field_InitActorColorTable_7A5E58. */
extern u32 maybe_g_actorColorTable7A5E5C[12];        /* 0x007A5E5C conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A5E58. */
extern u32 g_fieldLampGimmickGlowName;               /* 0x007A6248 conf 0.65: Lamp glow effect name pointer ('0Hx') looked up in named map work+0x74 by Field_LampGimmick_FindGlow and Field_LampGimmi */
extern u32 maybe_g_actorColorTable7A62A4[12];        /* 0x007A62A4 conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A62A4. */
extern u32 g_actorColorTable7A6534[12];              /* 0x007A6534 conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A6534. */
extern f32 g_fieldNpcFaceAnimScale;                  /* 0x007A66BC conf 0.55: Scale factor float read during NPC face talking animation advancement in Field_Npc_UpdateFace. */
extern u8 maybe_g_fieldEffectDescInitFlagA;          /* 0x007A66EC conf 0.45: Initialization flag byte checked during effect descriptor building in maybe_Field_EffectDesc_Build. */
extern u8 maybe_g_fieldEffectDescInitFlagB;          /* 0x007A66ED conf 0.45: Secondary initialization flag byte checked in maybe_Field_EffectDesc_Build. */
extern u8 g_fieldTalkParamsDurationScale;            /* 0x007A66F4 conf 0.55: Duration scale factor byte read by Field_SetupTalkParams and multiplied by 60 to convert seconds to frames. */
extern u8 g_fieldTalkParamsFrameDuration;            /* 0x007A66F8 conf 0.55: Secondary duration byte read by Field_SetupTalkParams and multiplied by 60 for talk window frame limits. */
extern u8 g_fieldSceneFadeTargetAlpha;               /* 0x007A67D8 conf 0.50: Scene fade target alpha byte stored into scene->f_54->f_D8C by maybe_Field_ApplySceneFade. */
extern u16 g_fieldLevelBackgroundEffectId;           /* 0x007A68B0 conf 0.65: Background cloud / sky effect resource id (retail 0x04EE = 1262) loaded by Field_Level_LoadBackgroundSettings and Gfx_Sk */
extern u32 g_fieldNpcFacePatternFrame;               /* 0x007A68E8 conf 0.55: Facial expression animation pattern frame table pointer accessed by Field_Npc_Face_AdvanceFrame. */
extern u32 maybe_g_fieldActorPartPlainParams[10];    /* 0x007A6970 conf 0.45: Registration parameter table for plain actor parts linked by maybe_Field_RegisterActorPart_Plain. */
extern u32 g_fieldActorBarrierRegistryEntry[10];     /* 0x007A6A50 conf 0.60: Secondary registration descriptor entry for Barrier field actors in Field_RegisterActorClass_Barrier. */
extern u8 maybe_g_field2DSpriteAppearanceCharId;     /* 0x007A6AE4 conf 0.45: Fallback character id byte read in maybe_Field2D_Sprite_SetAppearanceFromCharId when setting 2D appearance. */
extern u32 g_fieldActorCommonParams[6];              /* 0x007A6AF8 conf 0.65: Common actor registration attributes table (initialized with -1 in first word) by Field_RegisterActorClass_CommonActor. */
extern u8 maybe_g_field2DSpriteDrawRectOffset;       /* 0x007A6B10 conf 0.45: Draw rect offset byte read during 2D sprite draw parameter computation in maybe_Field2D_Sprite_ComputeDrawRect. */
extern u8 maybe_g_field2DSpriteScaleAnimFactor;      /* 0x007A6B14 conf 0.45: Scale animation factor byte read in maybe_Field2D_Sprite_SetScaleAnim and maybe_Field2D_Sprite_SubmitBlend. */
extern u32 g_field2DSceneSpawnPointsBuffer;          /* 0x007A6B28 conf 0.60: Entity spawn point buffer pointer initialized by Field2D_Scene_InitSpawnPoints. */
extern u32 g_field2DSceneSpawnPointsMode;            /* 0x007A6B30 conf 0.60: Spawn point mode configuration word read and updated by Field2D_Scene_InitSpawnPoints. */
extern u8 g_field2DMapChipRegionTileStride;          /* 0x007A6B6C conf 0.55: Region tile scan stride byte added to tile index in Field2D_MapChip_ScanRegionTiles. */
extern u8 g_field2DSceneUploadTileVerticesState;     /* 0x007A6B88 conf 0.55: Tile upload state or configuration byte checked during 2D map tile vertex uploading in Field2D_Scene_UploadTileVertices. */
extern u8 maybe_g_field2DSpriteScreenBoundsVector;   /* 0x007A6B9C conf 0.45: Vector component byte converted to float by VectorSignedToFloat in maybe_Field2D_Sprite_UpdateScreenBounds. */
extern u8 g_field2DSceneRenderAllFlag;               /* 0x007A6BD0 conf 0.60: Scene rendering enable flag byte checked by Field2D_Scene_RenderAll before dispatching draw passes. */
extern u8 g_field2DMapChipReachablePathStep;         /* 0x007A6BD4 conf 0.55: Reachable path search step byte read in Field2D_MapChip_FindReachablePath. */
extern u32 maybe_g_fieldResolveActorOverlapScale;    /* 0x007A6E64 conf 0.45: Actor overlap scale pointer dereferenced at +0x38 in maybe_Field_ResolveActorOverlap. */
extern u8 g_fieldHorseActionRideOrientationParams;   /* 0x007A6E70 conf 0.55: Horse ride orientation parameter byte read in Field_HorseAction_UpdateRideOrientation. */
extern u8 g_fieldHorseActionRideOrientationScale;    /* 0x007A6E78 conf 0.55: Ride orientation scale factor byte read in Field_HorseAction_UpdateRideOrientation. */
extern u8 maybe_g_fieldHorseActionStartState;        /* 0x007A6E88 conf 0.45: Horse action start state byte stored into action[0xB] by maybe_Field_HorseAction_Start. */
extern u8 maybe_g_fieldActionToggleRunState;         /* 0x007A6E8C conf 0.45: Run toggle state byte stored into actor->f_278 by maybe_Field_Action_ToggleRun. */
extern u8 g_fieldActionHorseJumpHeight;              /* 0x007A6E94 conf 0.55: Horse jump height parameter byte stored into self->f_3C by Field_Action_HorseJump. */
extern u8 g_fieldActionHorseJumpSpeed;               /* 0x007A6E98 conf 0.55: Horse jump forward speed multiplier byte stored into self->f_40 by Field_Action_HorseJump. */
extern u8 g_fieldActorActionTurnDirectionScale;      /* 0x007A6EA0 conf 0.55: Turn direction scale factor byte multiplied by delta time in Field_ActorAction_UpdateTurnDirection. */
extern u8 maybe_g_fieldActionHorseParamA;            /* 0x007A6EA4 conf 0.45: Horse parameter byte stored into self[0xF] by maybe_Field_Action_InitHorseParams. */
extern u8 maybe_g_fieldActionHorseParamB;            /* 0x007A6EA8 conf 0.45: Horse parameter byte stored into self[0x10] by maybe_Field_Action_InitHorseParams. */
extern u8 maybe_g_fieldActionHorseParamC;            /* 0x007A6EAC conf 0.45: Horse parameter byte stored into self[0x11] by maybe_Field_Action_InitHorseParams. */
extern u8 maybe_g_fieldActionHorseParamD;            /* 0x007A6EB0 conf 0.45: Horse parameter byte stored into self[0x12] by maybe_Field_Action_InitHorseParams. */
extern u8 maybe_g_fieldActionHorseParamE;            /* 0x007A6EB4 conf 0.45: Horse parameter byte stored into self[0x13] by maybe_Field_Action_InitHorseParams. */
extern u8 maybe_g_fieldActionToggleRunParamA;        /* 0x007A6EB8 conf 0.45: Run toggle speed parameter byte stored into self->f_3C by maybe_Field_Action_ToggleRun. */
extern u8 maybe_g_fieldActionToggleRunParamB;        /* 0x007A6EBC conf 0.45: Run toggle speed parameter byte stored into self->f_40 by maybe_Field_Action_ToggleRun. */
extern u8 maybe_g_fieldActionToggleRunParamC;        /* 0x007A6EC0 conf 0.45: Run toggle speed parameter byte stored into self->f_44 by maybe_Field_Action_ToggleRun. */
extern u8 maybe_g_fieldActionToggleRunParamD;        /* 0x007A6EC4 conf 0.45: Run toggle speed parameter byte stored into self->f_48 by maybe_Field_Action_ToggleRun. */
extern u8 maybe_g_fieldActionToggleRunParamE;        /* 0x007A6EC8 conf 0.45: Run toggle speed parameter byte stored into self->f_4C by maybe_Field_Action_ToggleRun. */
extern u8 maybe_g_fieldActionHorseTurnThreshold;     /* 0x007A6ECC conf 0.45: Horse turn threshold angle byte compared against in-flight heading in maybe_Field_Action_HorseTurn. */
extern u8 maybe_g_fieldActionHorseTurnScale;         /* 0x007A6ED0 conf 0.45: Horse turn rate scale byte read in maybe_Field_Action_HorseTurn. */
extern u32 g_actorColorTable7A704C[12];              /* 0x007A704C conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A704C. */
extern u8 maybe_g_fieldActorCanUpdateMotionSetFlag;  /* 0x007A7238 conf 0.45: Motion set update guard flag read through g_0023BF30->f_C in maybe_Field_Actor_CanUpdateMotionSet. */
extern u32 g_actorColorTable7A728C[12];              /* 0x007A728C conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTables_7A728C. */
extern u32 g_actorColorTable7A72DC[12];              /* 0x007A72DC conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A72DC. */
extern u32 maybe_g_actorColorTable7A7514[12];        /* 0x007A7514 conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A7514. */
extern u32 maybe_g_actorColorTable7A7518;            /* 0x007A7518 conf 0.45: Initialization guard flag for color table 0x007A7514; checked by maybe_Field_InitActorColorTable_7A7514. */
extern u32 g_actorColorTable7A7600[12];              /* 0x007A7600 conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A7600. */
extern u32 g_actorColorTable7A7F8C[12];              /* 0x007A7F8C conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A7F8C. */
extern u32 maybe_g_actorColorTable7A82FC[12];        /* 0x007A82FC conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A82FC. */
extern u32 g_fieldActorEmotionSlotsDescriptor;       /* 0x007A8ADC conf 0.60: Facial emotion sub-object descriptor pointer loaded by Field_Actor_LoadEmotionSlots when binding emotion slots. */
extern u32 maybe_g_actorColorTable7A8CD4[12];        /* 0x007A8CD4 conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A8CD4. */
extern u32 g_actorColorTable7A8F40[12];              /* 0x007A8F40 conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A8F40. */
extern u32 maybe_g_actorColorTable7A9194[12];        /* 0x007A9194 conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A9194. */
extern u32 g_actorColorTable7A95D0[12];              /* 0x007A95D0 conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7A95D0. */
extern u32 maybe_g_actorColorTable7A9B5C;            /* 0x007A9B5C conf 0.45: Initialization guard flag for color table 0x007A9B68; checked by maybe_Field_InitActorColorTable_7A9B68. */
extern u32 maybe_g_actorColorTable7A9B68[12];        /* 0x007A9B68 conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7A9B68. */
extern u8 maybe_g_field2DSpriteScreenBoundsByte;     /* 0x007AA401 conf 0.45: Screen bounds adjustment byte passed to func_00213E1C by Field2D_Sprite_UpdateScreenBounds. */
extern u32 g_actorColorTable7AB190[12];              /* 0x007AB190 conf 0.65: 12-entry RGBA color table (48 bytes) initialized once by Field_InitActorColorTable_7AB190. */
extern u32 maybe_g_actorColorTable7AB7A0[12];        /* 0x007AB7A0 conf 0.45: 12-entry RGBA color table (48 bytes) initialized once by maybe_Field_InitActorColorTable_7AB7A0. */
extern u32 g_fieldObjectPrefixKey;                   /* 0x007AE194 conf 0.60: Prefix search key pointer ('5-byte key' stored at 0x00789BBC) used by Field_FindObjectByPrefix. */
extern u32 maybe_g_fieldObject2DRebuildSpriteHandle; /* 0x007AE4D8 conf 0.45: Global sprite handle storage used during 2D object rebuilds by maybe_Field_Object2D_RebuildSprite. */
extern u32 g_fieldObjectSpriteComplexDescriptor[2];  /* 0x007B2D60 conf 0.55: Descriptor array header (indexed by self+4 & 0x7FF * 8) used by Field_ObjectSprite_InitComplex. */
extern u32 g_fieldBattleActionSequenceMap[2];        /* 0x007B4D68 conf 0.55: Battle action sequence lookup table header (indexed by slot & 0x3FF * 8) used by Battle_ActionSequence_Update. */
extern u32 g_fieldEffect2DAttachActorHandleMap[2];   /* 0x007B5D70 conf 0.55: Handle lookup table header for 2D actor effects in Effect2DAttachActor and Effect2DChangeSpeed. */
extern u32 g_actorAimLocatorHandleMap[2];            /* 0x007B7F28 conf 0.55: Locator handle mapping table header (indexed by slot & 0x3F * 8) used by ActorAimLocator and ActorAimLocatorDirect. */
extern u32 g_actorAttachGadgetHandleMap[2];          /* 0x007B80C0 conf 0.70: Master entity/gadget handle lookup table header used across ActorAttachGadget, ActorGetJumpLocatorID, and field actor re */
extern u32 g_fieldGimmickMasterInitSlotA;            /* 0x007BA0C0 conf 0.60: Master field gimmick initialization slot A updated during Field_Gimmick_Ctor and Field_Gimmick_InitActorSlot. */
extern u8 g_fieldGimmickMasterInitCount;             /* 0x007BA0C4 conf 0.60: Master field gimmick sub-component count byte updated by Field_Gimmick_Ctor. */
extern u32 g_fieldGimmickMasterInitSlotB;            /* 0x007BA0C8 conf 0.60: Master field gimmick initialization slot B updated during Field_Gimmick_Ctor and Field_Gimmick_InitActorSlot. */
extern u32 g_actorColorTableInitState;               /* 0x007BE2D0 conf 0.60: Initialization state pointer passed to func_0010009C by Field_InitActorColorTable_7A2CCC and Field_InitActorColorTable_7 */
extern u32 g_actor2DCreateEightSpansState;           /* 0x007BE2D4 conf 0.55: 2D actor span generation state pointer read by Actor2D_CreateEightSpans and Actor2D_CreateEightSpansAlt. */
extern u8 g_fieldCameraWorkPathActiveFlag;           /* 0x007BE314 conf 0.65: Active status flag byte for camera work path interpolation checked by Camera_UpdateWorkPath and Field_DestroyScene. */
extern u32 g_fieldCameraWorkPathTable[44];           /* 0x007BE318 conf 0.65: Camera work path interpolation table (44 words = 176 bytes) walked and updated by Camera_UpdateWorkPath and Field_Destro */
extern u32 g_fieldActorRegistryInitializedFlag;      /* 0x007BE374 conf 0.70: One-shot initialization guard flag for the global field actor class registry; checked in Field_RegisterActorClass_Attach */
extern u32 g_fieldActorRegistryHeadNode;             /* 0x007BE378 conf 0.70: Head pointer of the global field actor class registry intrusive list; initialized in Field_RegisterActorClass_AttachVehi */
extern char g_actorGimmickDefaultTalkAction[12];     /* 0x007BE394 conf 0.80: ASCII string "defaultTalk" passed as default talk action name by maybe_Field_ActorGimmick_InitFromRecord. */
extern char g_npcEmoteDefaultTalkAction[12];         /* 0x007BE3A0 conf 0.80: ASCII string "defaultTalk" passed as default talk action name by Field_Npc_InitEmoteBalloon. */
extern char g_npcTalkBalloonsDefaultTalkAction[12];  /* 0x007BE3AC conf 0.80: ASCII string "defaultTalk" passed as default talk action name by Field_Npc_InitTalkBalloons. */
extern char g_npcFullBalloonsDefaultTalkAction[12];  /* 0x007BE3B8 conf 0.80: ASCII string "defaultTalk" passed as default talk action name by maybe_Field_Npc_InitFullBalloons. */
extern char g_npcColorBalloonADefaultTalkAction[12]; /* 0x007BE3C4 conf 0.80: ASCII string "defaultTalk" passed as default talk action name by maybe_Field_Npc_InitColorBalloonA. */
extern char g_spawnObjectBDefaultTalkAction[12];     /* 0x007BE3D0 conf 0.80: ASCII string "defaultTalk" passed as default talk action name by maybe_Field_SpawnObjectRecordB. */
extern char g_npcColorBalloonBDefaultTalkAction[12]; /* 0x007BE3DC conf 0.80: ASCII string "defaultTalk" passed as default talk action name by maybe_Field_Npc_InitColorBalloonB. */
extern char g_spawnObjectCDefaultTalkAction[12];     /* 0x007BE3E8 conf 0.80: ASCII string "defaultTalk" passed as default talk action name by maybe_Field_SpawnObjectRecordC. */
extern char g_sceneObjInitSpriteName[7];             /* 0x007BE792 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_SceneObj_InitFromRecord. */
extern char g_modelObjInitSpriteName[7];             /* 0x007BE799 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_ModelObj_InitFromRecord. */
extern char g_twoPartObjInitSpriteName[7];           /* 0x007BE7A0 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_TwoPartObj_InitFromRecord. */
extern char g_createMapObjectSpriteName[7];          /* 0x007BE7AE conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_CreateMapObject. */
extern char g_sceneObjectCreateSpriteName[7];        /* 0x007BE7CA conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_SceneObject_CreateSprite. */
extern char g_gadgetInitGridASpriteName[7];          /* 0x007BE7D8 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_Gadget_InitSpriteGridA. */
extern char g_sceneObjectCreateSpriteBName[7];       /* 0x007BE7DF conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_SceneObject_CreateSpriteB. */
extern char g_sceneObjectLayoutModelSpriteName[7];   /* 0x007BE7E6 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_SceneObject_InitModelFromLayout. */
extern char g_sceneObjectLayoutSpriteName[7];        /* 0x007BE7ED conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_SceneObject_InitSpriteFromLayout. */
extern char g_markerCreateChildSpriteName[7];        /* 0x007BE7F4 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_Marker_CreateSpriteChild. */
extern char g_object2DInitModelSpriteName[7];        /* 0x007BE7FB conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_Object2D_InitModel. */
extern char g_spriteObjectInitRecordSpriteName[7];   /* 0x007BE809 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_SpriteObject_InitFromRecord. */
extern char g_actorInitPlacementSpriteName[7];       /* 0x007BE810 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_Actor_InitFromPlacementRecord. */
extern char g_spriteActorSetupSpriteName[7];         /* 0x007BE817 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_SpriteActor_SetupSpriteA. */
extern char g_propInitModelRecordSpriteName[7];      /* 0x007BE82C conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_Prop_InitFromModelRecord. */
extern char g_object2DInitModelVariantSpriteName[7]; /* 0x007BE83A conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_Object2D_InitModelVariant. */
extern char g_actorInitModelRecordSpriteName[7];     /* 0x007BE848 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_Actor_InitModelFromRecord. */
extern char g_gadgetInitKind1BSpriteName[7];         /* 0x007BE84F conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_Gadget_InitKind1B. */
extern char g_gadgetInitKind1CSpriteName[7];         /* 0x007BE856 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_Gadget_InitKind1C. */
extern char g_gadgetInitKind1DSpriteName[7];         /* 0x007BE85D conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_Gadget_InitKind1D. */
extern char g_gadgetInitGridBSpriteName[7];          /* 0x007BE864 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_Gadget_InitSpriteGridB. */
extern char g_markerSetupAnimatedSpriteName[7];      /* 0x007BE879 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by Field_Marker_SetupAnimatedObject. */
extern char g_createActorSpriteName[7];              /* 0x007BE880 conf 0.80: ASCII string "sprite" passed to model/billboard sprite builder by maybe_Field_CreateActor. */
extern char g_fieldActorRunMotionName[4];            /* 0x007BFAA3 conf 0.80: ASCII string "Run" passed to motion player during actor creation in Field_Actor_Create and Field_ActorGroup_PlaceMember. */
extern char g_fieldGimmickSubMotionName[3];          /* 0x007C22DF conf 0.75: ASCII string "01" passed as sub-motion identifier in maybe_Field_Gimmick3107_PlayDefaultAction. */
extern char g_fieldDefaultNutAnimName[4];            /* 0x007C22E2 conf 0.80: Default animation name string "Nut" read in maybe_Field_Gimmick3107_PlayDefaultAction and maybe_Field_SceneNode_OnComman */
extern char g_fieldCollisionProxyName[16];           /* 0x007C22E9 conf 0.85: ASCII string "field_collision" passed to collision shape builder by Field_CreateCollisionObject. */
extern u32 g_commonActorClassRecord[5];              /* 0x007C3330 conf 0.65: BSS class registration descriptor node for CommonActor; Field_RegisterActorClass_CommonActor links it into the class reg */
extern u32 g_fieldActorTalkMotionClassRecord[5];     /* 0x007C3344 conf 0.55: BSS class registration record used during talk motion resolution in Field_Actor_PlayTalkMotionFromTable. */
extern u32 g_scriptGadgetActorClassRecord[5];        /* 0x007C34E8 conf 0.65: BSS class registration record for ScriptGadgetActor; Field_RegisterCutSceneActorClasses initializes it with string 'Scri */
extern u32 g_fieldGimmickActorListClassRecord[5];    /* 0x007C3510 conf 0.55: BSS class record / handle list node used by Field_Gimmick_MarkActorsInState and Container_FindObjectByTypeIdE. */
extern u32 g_fieldGimmickStateTable[16];             /* 0x007C3524 conf 0.55: Array of gimmick runtime state indicators and class pointers queried by Field_Object2D_ResolveAndGetState221 and Field_R */
extern u32 g_fieldGimmickEventRecord[5];             /* 0x007C3538 conf 0.55: Event notification record node initialized during gimmick event handling in Field_Gimmick_SendEventType6 and Field_Gimmi */
extern u32 g_fieldGimmickPartsVariantDRecord[5];     /* 0x007C354C conf 0.55: Part descriptor record used by maybe_Field_Gimmick_UpdatePartsVariantD and maybe_Field_Gimmick_UpdatePartsVariantE for v */
extern u32 g_fieldGimmickPartsVariantARecord[5];     /* 0x007C3560 conf 0.55: Part descriptor record used by maybe_Field_Gimmick_UpdatePartsVariantA, B, and C for multi-variant gimmick part tracking */
extern u32 g_fieldActorGlobalHandleTable[5];         /* 0x007C3588 conf 0.60: Global actor handle resolution table / hash header used by Field_Actor_ResolveByHandle and Field_Gimmick_UpdateRowStates */
extern u32 g_fieldActorGroupMemberRecord[5];         /* 0x007C359C conf 0.55: Intrusive class node / tracking structure for actor group members used by Field_ActorGroup_AddMember and Container_Handl */
extern f32 g_fieldActorGroupFormationTable[24];      /* 0x007C35B0 conf 0.65: Global formation offset pattern table (stride 0x60, 12 bytes per placement) indexed by Field_ActorGroup_PlaceMember to p */
extern u32 g_enemyMenuActorClassRecord[5];           /* 0x007C42F0 conf 0.65: BSS class registration descriptor node for EnemyMenuActor; Field_RegisterActorClass_EnemyMenuActor links it into the cla */
extern u32 g_enemyDesertWhaleClassRecord[5];         /* 0x007C4310 conf 0.65: BSS class registration descriptor node for EnemyDesertWhale; Field_RegisterActorClass_EnemyDesertWhale links it into the */
extern u32 g_fieldEventActor3DClassRecord[5];        /* 0x007C4324 conf 0.80: BSS class registration descriptor node for FieldEventActor3D; registered in Ui_CreateStaticTextWidgets_698444 with strin */
extern u32 g_fieldEventActor2DClassRecord[5];        /* 0x007C4338 conf 0.80: BSS class registration descriptor node for FieldEventActor2D; registered in Ui_CreateStaticTextWidgets_698444 with strin */
extern u32 g_fieldItemGet3DActorClassRecord[5];      /* 0x007C434C conf 0.85: BSS class registration descriptor node for FieldItemGet3DActor; registered in Field_RegisterActorClass_FieldItemGet3DAct */
extern u32 g_fieldGadgetListArray[96];               /* 0x007C4360 conf 0.60: Array of 16-byte field gadget entries queried and maintained by Field_GadgetList_FindOrAddByHandle and Field_MapObject2D */
extern u32 g_gmItemBox2DClassRecord[36];             /* 0x007C439C conf 0.60: BSS class registration record and RTTI descriptor for 2D gimmick item box classes registered by Field_RegisterGimmick2DC */
extern u32 g_gmEggRoboJump2DClassRecord[5];          /* 0x007C4568 conf 0.65: BSS class registration descriptor node for GmEggRoboJump2D; Field_RegisterActorClass_GmEggRoboJump2D registers it with s */
extern u32 g_gmEggRoboMapJump2DClassRecord[5];       /* 0x007C457C conf 0.65: BSS class registration descriptor node for GmEggRoboMapJump2D; Field_RegisterActorClass_GmEggRoboJump2D registers it wit */
extern u32 g_gmHellkachaRock2DClassRecord[5];        /* 0x007C45B8 conf 0.65: BSS class registration descriptor node for GmHellkachaRock2D; Field_RegisterActorClass_GmHellkachaRock2D links it into t */
extern u32 g_fieldForegroundClassRecord[5];          /* 0x007C45E0 conf 0.60: BSS class registration descriptor node for Foreground field scene objects; Ui_CreateStaticTextWidgets_69EF88 registers i */
extern u32 g_gmPitfall2DClassRecord[5];              /* 0x007C4608 conf 0.65: BSS class registration descriptor node for GmPitfall2D; Field_RegisterActorClass_GmPitfall2D links it into the class reg */
extern u32 g_gmBeeRider2DClassRecord[5];             /* 0x007C470C conf 0.65: BSS class registration descriptor node for GmBeeRider2D; Field_RegisterActorClass_GmBeeRider2D links it into the class r */
extern u32 g_gmDullahanKnight2DClassRecord[5];       /* 0x007C4734 conf 0.65: BSS class registration descriptor node for GmDullahanKnight2D; Field_RegisterActorClass_GmDullahanKnight2D links it into */
extern u32 g_gmHellkacha2DClassRecord[5];            /* 0x007C4784 conf 0.65: BSS class registration descriptor node for GmHellkacha2D; Field_RegisterActorClass_GmHellkacha2D links it into the class */
extern u32 g_gmHorse2DClassRecord[5];                /* 0x007C4798 conf 0.65: BSS class registration descriptor node for GmHorse2D; Field_RegisterActorClass_GmHorse2D links it into the class registr */
extern u32 g_gmVehicleBase2DClassRecord[6];          /* 0x007C47D4 conf 0.65: BSS class registration descriptor node for GmVehicleBase2D; Field_RegisterActorClass_GmVehicleBase2D registers it with s */
extern u32 g_gmGondola2DClassRecord[5];              /* 0x007C47E8 conf 0.65: BSS class registration descriptor node for GmGondola2D; Field_RegisterActorClass_GmGondola2D links it into the class reg */
extern u32 g_gmGondoraClassRecord[5];                /* 0x007C47FC conf 0.65: BSS class registration descriptor node for Gondora vehicle; Field_RegisterActorClass_GmGondola2D registers it with strin */
extern u32 g_gmWhale2DClassRecord[5];                /* 0x007C4838 conf 0.65: BSS class registration descriptor node for GmWhale2D; Field_RegisterActorClass_GmWhale2D links it into the class registr */
extern u32 g_gmD011BookShelf3DActorClassRecord[5];   /* 0x007C484C conf 0.65: BSS class registration descriptor node for GmD011BookShelf3DActor; Field_RegisterActorClass_GmD011BookShelf3DActor links */
extern u32 maybe_g_fieldActorNearbyList;             /* 0x007C48C4 conf 0.45: Head pointer of the cached nearby same-type actor list used by maybe_Field_Actor_FindNearbySameType. */
extern u32 g_fieldSceneObjectResetTarget;            /* 0x007C4914 conf 0.55: Scene object target reference reset by Field_SceneObject_ResetState during entity teardown. */
extern u32 maybe_g_fieldActionPitfallState;          /* 0x007C4978 conf 0.45: Global state word tracking the active pitfall action in maybe_Field_Action_PitfallSetState. */
extern u32 maybe_g_fieldActionWalkTarget;            /* 0x007C498C conf 0.45: Active walk target reference updated during NPC movement in maybe_Field_Action_WalkStartToTarget and maybe_Field_Action_ */
extern u32 g_gmRacePillar3DActorClassRecord[5];      /* 0x007C4AE0 conf 0.65: BSS class registration descriptor node for horse race pillar obstacle GmRacePillar3DActor; registered by Field_RegisterR */
extern u32 g_gmRaceMud3DActorClassRecord[5];         /* 0x007C4AF4 conf 0.65: BSS class registration descriptor node for horse race mud obstacle GmRaceMud3DActor; registered by Field_RegisterRaceAct */
extern u32 g_gmRaceWood3DActorClassRecord[5];        /* 0x007C4B08 conf 0.65: BSS class registration descriptor node for horse race wood obstacle GmRaceWood3DActor; registered by Field_RegisterRaceA */
extern u32 g_gmRaceSlope3DActorClassRecord[5];       /* 0x007C4B1C conf 0.65: BSS class registration descriptor node for horse race slope ramp GmRaceSlope3DActor; registered by Field_RegisterRaceAct */
extern u32 g_gmRaceHighRoad3DActorClassRecord[5];    /* 0x007C4B30 conf 0.65: BSS class registration descriptor node for horse race high road GmRaceHighRoad3DActor; registered by Field_RegisterRaceA */
extern u32 g_gmRaceJumpRamp3DActorClassRecord[5];    /* 0x007C4B44 conf 0.65: BSS class registration descriptor node for horse race jump ramp GmRaceJumpRamp3DActor; registered by Field_RegisterRaceA */
extern u32 g_gmRaceQuickItem3DActorClassRecord[5];   /* 0x007C4B58 conf 0.65: BSS class registration descriptor node for horse race quick item GmRaceQuickItem3DActor; registered by Field_RegisterRac */
extern u32 g_gmD011BookShelfSubClassRecord[5];       /* 0x007C4B94 conf 0.60: Secondary BSS class registration node for bookshelf gimmick sub-objects in Field_RegisterActorClass_GmD011BookShelf3DAct */
extern u32 g_pursuer3DActorClassRecord[5];           /* 0x007C4BBC conf 0.75: BSS class-registration record for field pursuer actors (Pursuer3DActor): Field_RegisterActorClass_Pursuer3DActor initial */
extern u32 g_gmPursuerSquad3DActorClassRecord[5];    /* 0x007C4BD0 conf 0.75: BSS class-registration record for field pursuer squad actors (GmPursuerSquad3DActor): Field_RegisterActorClass_GmPursuer */
extern u32 g_gmWorldFloating3DActorClassRecord[5];   /* 0x007C4C0C conf 0.75: BSS class-registration record for overworld floating object actors (GmWorldFloating3DActor): Field_RegisterActorClass_Gm */
extern u32 g_quickItemGet3DActorClassRecord[5];      /* 0x007C4D24 conf 0.80: BSS class-registration record for quick item pickup actors (QuickItemGet3DActor): Field_RegisterActorClass_QuickItemGet3 */
extern u32 g_npc2DActorClassRecords[20];             /* 0x007C4D4C conf 0.85: Table of four 20-byte class-registration records for 2D NPCs: NPC2DActor (+0x00), NPC2DPlayerActor (+0x14), NPC2DEnemyAc */
extern u32 g_npc3DActorClassRecord[5];               /* 0x007C4D9C conf 0.80: BSS class-registration record for 3D NPCs (NPC3DActor): base record of the six-entry NPC3D family table; Field_RegisterA */
extern u32 g_npc3DPlayerActorClassRecord[5];         /* 0x007C4DB0 conf 0.85: BSS class-registration record for 3D player NPC actors (NPC3DPlayerActor): second entry of the NPC3D table; Field_Regist */
extern u32 g_npc3DAnimalActorClassRecord[5];         /* 0x007C4DC4 conf 0.80: BSS class-registration record for 3D animal NPC actors (NPC3DAnimalActor): third entry of the NPC3D table; Field_Registe */
extern u32 g_npc3DEnemyActorClassRecord[5];          /* 0x007C4DD8 conf 0.85: BSS class-registration record for 3D enemy NPC actors (NPC3DEnemyActor): fourth entry of the NPC3D table; Field_Register */
extern u32 maybe_g_fieldSceneEffectClassRecord[5];   /* 0x007C4E28 conf 0.45: BSS class-registration record for field scene effect actors: situated immediately after g_attachVehicleActor3DClass (0x0 */
extern u32 g_paddingFollower2DClassRecord[5];        /* 0x007C5050 conf 0.70: BSS class-registration record for 2D padding follower actors (PaddingFollower2D): Ui_RegisterStaticObject_7A3FEC links i */
extern f32 g_actorParamZeroVector[3];                /* 0x007C5174 conf 0.65: Three-float zero vector (0.0f, 0.0f, 0.0f) in BSS cleared by maybe_Field_InitActorParamBlock_68745C alongside the actor  */
extern f32 g_fieldWorldBoundsMin3D[3];               /* 0x007C5238 conf 0.85: Three-float world minimum boundary position (min X, min Y, min Z) for 3D field mode: used by Field_EffectDesc_Build for  */
extern f32 g_fieldWorldBoundsMax3D[3];               /* 0x007C5244 conf 0.85: Three-float world maximum boundary position (max X, max Y, max Z) for 3D field mode: paired with g_fieldWorldBoundsMin3D */
extern f32 g_fieldWorldBoundsMin2D[3];               /* 0x007C5250 conf 0.85: Three-float world minimum boundary position (min X, min Y, min Z) for 2D field mode (mode 8): used by Field_EffectDesc_B */
extern f32 g_fieldWorldBoundsMax2D[3];               /* 0x007C525C conf 0.85: Three-float world maximum boundary position (max X, max Y, max Z) for 2D field mode (mode 8): paired with g_fieldWorldBo */
extern u32 g_gmDiveCheckPoint2DClassRecord[5];       /* 0x007C5380 conf 0.80: BSS class-registration record for 2D dive checkpoint actors (GmDiveCheckPoint2D): Ui_RegisterStaticObject_6A2B08 initial */
extern u32 g_gmDiveItemBox2DClassRecord[5];          /* 0x007C5394 conf 0.80: BSS class-registration record for 2D dive item box actors (GmDiveItemBox2D): Ui_RegisterStaticObject_694BBC initializes  */
extern u32 g_gmDiveMonster2DClassRecord[5];          /* 0x007C53BC conf 0.80: BSS class-registration record for 2D dive monster actors (GmDiveMonster2D): Field_RegisterActorClass_GmDiveMonster2D ini */
extern f32 g_fieldActorCameraVectors[6];             /* 0x007C6E64 conf 0.80: Six-float camera positioning block for field actor inspection/preview: position (0, 0.2, 0) at +0x0 and look-at target ( */
extern f32 g_actorScreenRectA[4];                    /* 0x007C7EB0 conf 0.65: Four-float screen-space rectangle (40.0, 60.0, 140.0, -60.0) written by maybe_Field_InitActorColorTable_7A9194 as part o */
extern f32 g_actorScreenRectB[4];                    /* 0x007C7EC0 conf 0.65: Four-float screen-space rectangle (-60.0, 60.0, 120.0, -60.0) written by maybe_Field_InitActorColorTable_7A9194 immediat */
extern f32 maybe_g_actorCameraVectorsB[6];           /* 0x007C7FC0 conf 0.45: Six-float camera positioning block for field actor preview: eye offset (2.5, 0.3, 0) at +0x0 and look-at target (2.5, 2. */
extern f32 maybe_g_actorCameraVectorsC[6];           /* 0x007C8008 conf 0.45: Six-float camera positioning block for field actor preview: eye offset (0, 0.8, 0) at +0x0 and look-at target (0, 2.5, 7 */
extern u32 g_weatherVisualClassRecord[6];            /* 0x007C85D8 conf 0.65: BSS class-registration descriptor for weather visual / render objects: Font_InitGlyphBitmapPools registers it with base  */
extern u32 g_resourceBaseClassRecord[6];             /* 0x007E2000 conf 0.70: Root class-descriptor record in BSS for resource/model/visual object registry: passed as the parent class descriptor to  */
extern f32 g_vector3Zero[3];                         /* 0x007E7000 conf 0.90: Constant three-float zero vector (0.0f, 0.0f, 0.0f) in BSS: head of the default basis vector array at 0x007E7000; copied */
extern f32 maybe_g_defaultBasisVector3[3];           /* 0x007E7018 conf 0.45: Third 12-byte vector in the default basis vector table at 0x007E7000: read by Camera_Shake_Update, Camera_UpdateObstruct */
extern f32 maybe_g_defaultBasisVector4[3];           /* 0x007E7024 conf 0.45: Fourth 12-byte vector in the default basis vector table at 0x007E7000: read by Actor_Action_DragonJumpAirDriftUpdate, Dr */
extern f32 g_directionReferenceVector[3];            /* 0x007E7030 conf 0.85: Fifth 12-byte vector in the basis table at 0x007E7000: used by Actor_ClassifyDirection4 and Actor_ClassifyDirection8 for */
extern f32 g_vector4One[4];                          /* 0x007E709C conf 0.85: Constant four-float vector (1.0f, 1.0f, 1.0f, 1.0f) in BSS: used as identity rotation/scale quaternion or unit vector in */
extern f32 g_defaultNodeTransformParams[8];          /* 0x007E719C conf 0.75: Eight-float (32-byte) default transform/attachment parameter block: copied by Gfx_Node_Ctor to initialize node fields at */
extern u32 maybe_g_fieldActorCursorState[7];         /* 0x007EF084 conf 0.45: Seven-word static state block in BSS cleared by maybe_Field_InitActorGlobalState_7EF084 when resetting the field actor l */
extern u32 g_sceneSpriteContextStorage[24];          /* 0x008040F0 conf 0.85: 0x60-byte (24-word) BSS storage for the Gfx_Scene_SpriteContext singleton: initialized by Gfx_Scene_SpriteCtx_Init (guar */
extern u32 g_actorRegistryRootNodeStorage[8];        /* 0x00837108 conf 0.85: Static buffer storage in BSS for the root intrusive list node of the field actor class registry: aligned to 16 bytes by  */
extern u32 g_resourceRegistryRootNodeStorage[8];     /* 0x00837128 conf 0.85: Static buffer storage in BSS for the root intrusive list node of the resource/model class registry: aligned to 16 bytes  */

/* --- Flag --- */
extern u32 g_umaCupFlagTable[5];                     /* 0x0072B20C conf 0.80: Lookup table mapping each of the 5 horse race (uma) cup tiers (0..4: Bronze, Silver, Gold, Platinum, and Black Cup) to i */

/* --- Font --- */
extern u32 g_powersOfFour[16];                       /* 0x00727BF0 conf 0.90: Lookup table of powers of 4 (4^0 through 4^15, i.e. 1 << 2*k). Used in 2D quad/quadtree indexing and map chip trace rout */
extern u32 g_spriteLayerConfigs[14];                 /* 0x00728420 conf 0.60: Configuration table of callback and flag pairs for 2D actor sprite layers and font glyph quad UV buffers, determining vi */
extern u32 g_fontDisplayListCommandTemplate[2];      /* 0x0072F530 conf 0.80: Initial PICA200 GPU command template word pair (0x00000001, 0x000F02BF) appended to the font display list to configure p */
extern u8 g_fontVertexAttrComponentOffsets[8];       /* 0x0072F538 conf 0.85: Lookup table of base component indices for font vertex shader attributes, used in Font_BuildDisplayList to map glyph ver */
extern u32 g_fontDisplayListTexEnvCommands[38];      /* 0x0072F570 conf 0.85: Static PICA200 texture combiner and rasterizer state command packet (0x98 bytes) appended to the display list in Font_Bu */
extern u32 g_fontDisplayListBufferColorCommands[6];  /* 0x0072F668 conf 0.80: PICA200 command packet (0x18 bytes) setting texture environment buffer color (0x0FF00FF0) and facing attributes in Font_ */
extern u32 g_fontDisplayListSecondaryBufferCommands[10]; /* 0x0072F680 conf 0.80: PICA200 command packet (0x28 bytes) appended to the secondary display list buffer in Font_BuildDisplayList to restore bl */
extern u32 g_fontDisplayListVtxShaderCommands[80];   /* 0x0072F6E8 conf 0.85: Initial PICA200 vertex shader and input buffer setup command packet (0x140 bytes) appended to the font display list in F */
extern u32 g_fontQuadVertexIndices[6];               /* 0x0072F8C0 conf 0.90: Six-vertex index sequence (1, 0, 3, 3, 0, 2) defining two triangles for a font glyph quad in Font_BuildDisplayList. */
extern u32 g_fontDisplayListLutCommands[37];         /* 0x0072F8D8 conf 0.80: PICA200 command packet (0x94 bytes) appended to the font display list in Font_BuildDisplayList after ramp LUT physical a */
extern u32 g_fontDisplayListLutHeaderTemplate[24];   /* 0x0072F930 conf 0.75: Command template table used in Font_BuildDisplayList to assemble the 0x1C-byte ramp LUT command header around the physic */
extern u32 g_fontPageParserDescriptor[15];           /* 0x0073BAE4 conf 0.65: Descriptor containing stream reader callbacks (0x005592AC..0x0055932C) and default texture combiner words for font page  */
extern void* g_fontBaseVtable[32];                   /* 0x00781DB4 conf 0.90: Virtual method table for the base Font class (dtor slot at +0x04 is Font_DestructBase 0x00559220). Installed by Font_Cre */
extern void* g_fontDerivedVtable[32];                /* 0x00781F18 conf 0.90: Virtual method table for the derived resource-backed Font class (dtor slot at +0x04 is Font_DestructDerived 0x0055A28C). */
extern char g_emptyString[4];                        /* 0x00782780 conf 0.85: Constant empty string ("") in .rodata passed to string manipulation and name registration functions when no prefix or na */
extern u32 maybe_g_popupPoolHeader[4];               /* 0x00782B34 conf 0.45: Rodata descriptor block preceding the popup pool / scene sprite helper vtable, read during font glyph caching and scene  */
extern void* maybe_g_popupPoolHelperVtable[6];       /* 0x00782B44 conf 0.48: Vtable header for a temporary stack-allocated popup pool / scene helper object initialized during Font_CacheGlyphsForTex */
extern void* g_glyphSpriteVtable[84];                /* 0x0078372C conf 0.90: Primary and secondary virtual method table pair (0x54 words) for Font_GlyphSprite, installed in Font_GlyphSprite_Ctor. */
extern void* g_glyphSpriteAVtable[31];               /* 0x00783798 conf 0.85: Virtual method table for the 0x1F8-byte glyph sprite actor class created by Font_GlyphSprite_CreateA (derived from Field */
extern void* g_glyphQuadVariantBaseVtable[8];        /* 0x007838C4 conf 0.75: Virtual method table for the Font_GlyphQuad variant base sub-object, installed by maybe_Font_GlyphQuad_InitVariantBase. */
extern void* g_glyphQuadSimpleVtable[31];            /* 0x00783918 conf 0.85: Virtual method table for the simple 500-byte glyph quad sprite actor created by Font_GlyphQuad_CreateSimple (derived fro */
extern void* g_glyphQuadVtable[36];                  /* 0x007839B8 conf 0.90: Dual virtual method table (36 words) for Font_GlyphQuad created from UV coordinates, installed in Font_GlyphQuad_CreateF */
extern void* g_glyphSpriteVariantVtable[31];         /* 0x00783BC0 conf 0.85: Virtual method table for the five-way variant glyph sprite actor created by Font_GlyphSprite_CreateVariant (derived from */
extern void* g_glyphQuadDerivedVtable[8];            /* 0x00783C68 conf 0.85: Virtual method table for the derived glyph quad class instantiated in Font_GlyphQuad_Ctor. */
extern void* g_glyphQuadAttachmentVtable[8];         /* 0x00783CC0 conf 0.75: Virtual method table for the glyph quad attachment sub-object, installed by maybe_Font_GlyphQuad_InitBaseAttachment. */
extern u8 g_glyphCacheFreeSpanFlag;                  /* 0x007AE5F6 conf 0.70: Byte flag in .data controlling deferred span reclamation behaviour in Font_GlyphCache_FreeSpan and Font_GlyphCache_MarkF */
extern u32 g_glyphCacheInitGuard;                    /* 0x007AE8E0 conf 0.90: One-time initialization guard word (__cxa_guard) for the singleton Font_GlyphCache instance at 0x007E7578, tested and up */
extern u32 g_actorPartPlainClassNode[5];             /* 0x007C52CC conf 0.90: Class registration node (20 bytes) for the 'Plain' actor part in the field actor class registry. Used for dynamic type i */
extern u32 g_actorClassBarrierClassNode[5];          /* 0x007C52E0 conf 0.90: Class registration node (20 bytes) for the 'Barrier' actor class in the field actor class registry. Used for dynamic typ */
extern u32 g_actorClassCommonActorClassNode[5];      /* 0x007C52F4 conf 0.90: Class registration node (20 bytes) for the 'CommonActor' actor class in the field actor class registry. Used for dynamic */
extern u32 g_fontGlyphBitmapPool2[6];                /* 0x007C85C0 conf 0.85: Second glyph bitmap memory pool descriptor (0x18 bytes) initialized by Font_InitGlyphBitmapPools (0x0069BD40) via Mem_Bi */
extern FontGlyphCache g_fontGlyphCacheInstance;      /* 0x007E7578 conf 0.90: Singleton instance of the Font_GlyphCache object in .bss, lazily initialized on first use by maybe_Font_GlyphCache_GetIn */

/* --- Fs --- */
extern u8 g_fsTransferPriorityTable[60];             /* 0x0072D710 conf 0.75: Mode-to-channel enablement table for filesystem background transfer; defines whether each of the 12 transfer channels is */
extern char g_nimAocServiceName[8];                  /* 0x0072F41F conf 0.90: Service port name string "nim:aoc" (Network Information Management - Add-On Content); passed to Os_CreateEvent in Fs_Mou */
extern char g_fsUserServiceName[8];                  /* 0x0072FC13 conf 0.95: Service port name string "fs:USER" (3DS filesystem user service); passed to srvGetServiceHandle in Fs_Initialize to obta */
extern char g_fsEmptyMountName[4];                   /* 0x0072FC28 conf 0.70: Empty fallback mount name string ("\0"); parsed by Fs_RegisterMountByName and Fs_UnmountByName as a dummy device name wh */
extern char g_amAppServiceName[7];                   /* 0x007354B5 conf 0.95: Service port name string "am:app" (3DS Application Manager); passed to srvGetServiceHandle in maybe_Fs_OpenGlobalFile to */
extern void* g_fsChannelTableVtableAlt[7];           /* 0x007602B4 conf 0.65: Primary vtable header for FsChannelTable; installed at self (with secondary vtable at offset +0x18) by maybe_Fs_ChannelT */
extern void* g_fsArchiveVtable[6];                   /* 0x00781730 conf 0.65: Base vtable of the archive object (FsArchive / SoundArchive); installed at self[0] by constructor 0x00542B98 and restore */
extern void* g_fsArchiveStreamVtable[20];            /* 0x007818B8 conf 0.65: Vtable of the archive stream object (FsArchiveStream); installed at self[0] by constructors maybe_Fs_ArchiveStream_Creat */
extern void* g_fsCacheSubAllocVtable[6];             /* 0x007821B8 conf 0.65: Secondary allocator interface vtable; stored at offset +8 (puVar4[2]) of the 48-byte cache controller object by Fs_Cache */
extern void* g_fsCacheControllerRefVtable[6];        /* 0x007822D4 conf 0.60: Vtable of the 8-byte cache-controller reference wrapper stored at self+4; installed by Fs_CacheSet_Initialize (0x0010372 */
extern void* g_fsHandleArrayVtable[6];               /* 0x0078230C conf 0.70: Vtable of the FsHandleArray wrapper object; installed at self[0] by Fs_Cache_SetHandleArray (0x00108574) when wrapping a */
extern void* g_fsCacheAllocDescVtable[6];            /* 0x0078233C conf 0.65: Vtable of the 20-byte cache-allocator descriptor stored at self+0x18; installed by Fs_CacheSet_Initialize (0x00103724);  */
extern void* g_fsSlotPool58Vtable[6];                /* 0x0078236C conf 0.70: Vtable of the 0x58-byte-record variant of FsSlotPool; installed at self[0] by Fs_Cache_CreateSlotPool58 and Fs_Cache_Cre */
extern void* g_fsSlotPool54Vtable[6];                /* 0x0078239C conf 0.70: Vtable of the 0x54-byte-record variant of FsSlotPool; installed at self[0] by Fs_Cache_CreateSlotPool54 and Fs_Cache_Cre */
extern void* g_fsStreamVtable[4];                    /* 0x007823CC conf 0.65: Vtable of the file stream object (FsStream); installed by maybe_Fs_Stream_Ctor and restored by maybe_Fs_Stream_Destroy;  */
extern void* g_fsStreamReaderVtable[4];              /* 0x00782430 conf 0.65: Vtable of the stack stream reader context passed to maybe_Fs_NamedObject_FindAndRead by Fs_NamedObject_Open (0x0056F7A4) */
extern void* g_fsCacheControllerVtable[6];           /* 0x007824D0 conf 0.65: Primary vtable for the 48-byte cache controller object stored at self+8; installed by Fs_CacheSet_Initialize (0x00103724 */
extern char* g_fsContentArchiveId;                   /* 0x007AE4A8 conf 0.75: Pointer to default content archive path string "2712327116" at 0x00789DC8; loaded by Fs_Request_Build (0x001D0218) when  */
extern u8 g_fsDefaultArchivesMounted;                /* 0x007AE5E4 conf 0.90: Boolean flag tracking whether default filesystem archives (including the nim:aoc event/service session) are currently mo */
extern void* g_fsPackFormatConfig;                   /* 0x007AE5F4 conf 0.85: Archive package format configuration descriptor; byte 0 is package enable flag, byte 2 is record fast-path flag, word at */
extern void* g_fsUserSession;                        /* 0x007AEA38 conf 0.75: Filesystem user service session structure; word at offset +4 (0x007AEA3C) holds the 3DS IPC Handle for fs:USER, initiali */
extern void* maybe_g_fsUserSessionSentinel;          /* 0x007AEA39 conf 0.45: Sentinel / tagged pointer value (address 0x007AEA39, offset 0x39 or tagged with bit 0); stored into the session list hea */
extern u32 g_fsUserSessionHandle;                    /* 0x007AEA3C conf 0.95: 3DS IPC session handle for the fs:USER service; initialized by Fs_Initialize (0x00106AD0) via srvGetServiceHandle (func_ */
extern u32 g_fsNamedObjectSlotHint;                  /* 0x007BA2C8 conf 0.80: Rotating search index hint (bounded to 0..0x7FF) used to locate the next free entry in the 2048-slot named object table  */
extern u32 g_fsNamedObjectNextId;                    /* 0x007BA2CC conf 0.85: Rotating sequence counter used to allocate unique 20-bit IDs for registered named objects in Fs_NamedObject_Register (0x */
extern u8 g_fsReaderListNeedsInit;                   /* 0x007BE37C conf 0.75: One-time initialization flag (initial value 1); cleared to 0 when maybe_Fs_NamedObject_FindAndRead (0x0056F9AC) sets up  */
extern void* g_fsReaderList;                         /* 0x007BE380 conf 0.80: Pointer to the global reader list head; initialized on first use to point to g_fsReaderListStorage (0x00837130) and trav */
extern char g_fsNamedObjectDefaultName[4];           /* 0x007C0194 conf 0.75: Empty string constant ("\0") stored into self[10] as the default category name when a named object is registered in Fs_N */
extern u8 g_fsRequestBuffer[48];                     /* 0x007D0000 conf 0.75: Shared request work buffer in BSS; formatted with command header and argument descriptors by Fs_BuildRequestArgs and Fs_ */
extern u8 g_fsReadRequestArgs[68];                   /* 0x007D0030 conf 0.75: Shared argument buffer in BSS for async file read operations; populated with 0x44 (68) bytes of request context and argu */
extern u8 maybe_g_fsDefaultRecordTable[32];          /* 0x007E7560 conf 0.45: Default empty record table buffer in BSS; assigned to self->f_18 (with capacity count 0x20) when closing an archive reco */
extern u32 g_fsMountTable[128];                      /* 0x007E7BE0 conf 0.85: Global filesystem mount table (32 entries of 16 bytes = 512 bytes); stores 8-byte device name, archive object pointer, a */
extern u8 g_fsSharedRequestBlock[156];               /* 0x007E8044 conf 0.85: Shared 156-byte (0x9C) filesystem request block in BSS; filled by Fs_FillRequestBlock with command, payload (0x40 bytes) */
extern void* maybe_g_fsReaderListStorage[4];         /* 0x00837137 conf 0.45: Static BSS storage buffer (aligned to 0x00837130 via & ~0xF) hosting the default FsReaderList head; initialized with vta */

/* --- GetAltarGimmickID --- */
extern u32 g_altarGimmick3DClassRecord[5];           /* 0x007C44DC conf 0.85: BSS class-registration record and RTTI token for 3D altar gimmick objects (AltarGimmick3D); checked in GetAltarGimmickID */
extern u32 g_altarGimmick2DClassRecord[5];           /* 0x007C4A40 conf 0.85: BSS class-registration record and RTTI token for 2D altar gimmick objects (AltarGimmick2D); checked in GetAltarGimmickID */

/* --- GetLimitedTooShyTalkIndex --- */
extern s32 g_tooShyTalkOverrideIndex;                /* 0x007A746C conf 0.90: Debug/fixed override message index for the 'Too Shy to Talk' (Shypox) Draconian Quest restriction; when >= 0, GetLimited */
extern u32 g_tooShyTalkRate;                         /* 0x007A7470 conf 0.90: Trigger probability percentage (0-100) for the 'Too Shy to Talk' (Shypox) Draconian restriction; GetLimitedTooShyTalkInd */

/* --- GetNPCActorPlayerID --- */
extern u32 g_npcActor3DClassRecord[5];               /* 0x007C4478 conf 0.80: BSS class-registration record and RTTI token for 3D NPC actors: checked in ActorGetRegionBookID (0x0015940C), GetNPCActo */
extern u32 g_npcActor2DClassRecord[5];               /* 0x007C4964 conf 0.80: BSS class-registration record and RTTI token for 2D NPC actors: checked in ActorGetRegionBookID, Field_ActorAction_Updat */
extern u32 g_npc2DPlayerActorClassRecord[5];         /* 0x007C4D60 conf 0.85: BSS class-registration record and RTTI token for 2D player NPC actors (NPC2DPlayerActor): entry +0x14 in table g_npc2DAc */

/* --- Gfx --- */
extern u32 g_trailFollowPathParams[12];              /* 0x0072534C conf 0.70: Configuration table and callback pointers for ribbon and trail path following, read by Gfx_Trail_AdvancePathNode and Gfx */
extern u32 g_modelPartAttributeMasks[13];            /* 0x0072537C conf 0.80: Table of 13 bitmasks used to set or test model part attribute and render flags indexed by part row in maybe_Ui_SetNamedF */
extern char* g_animNameOpen;                         /* 0x00725B08 conf 0.75: Default animation name pointer pointing to 'Open' string, used by maybe_Gfx_Sprite2D_PlayIdleAnim and maybe_Gfx_Effect_U */
extern void* g_sprite2DDispatchTable[39];            /* 0x00725BD8 conf 0.70: Dispatch table of 39 function pointers for 2D sprite actors, indexed during Gfx_Sprite2D_InitFromTableB to configure beh */
extern u32 g_particleEmitterDefaultBlockA[48];       /* 0x00725E4C conf 0.75: Shared table of default parameters, colour fade values, and callback pointers used by particle emitter pool initializers */
extern u32 g_modelPartListDefaults[8];               /* 0x00725F4C conf 0.65: Default configuration and float vectors copied into new model part list objects in maybe_Gfx_ModelPartList_Init. */
extern u32 g_effectNodeDefaultColorBlockA[28];       /* 0x00726074 conf 0.70: Default color and transform block copied to fallback buffers upon child allocation failure in effect node child creators */
extern u32 g_particleEmitterDefaultBlockC[14];       /* 0x00726114 conf 0.75: 14-word parameter table containing default color and motion values for particle emitter pool C, read by maybe_Effect_Par */
extern u32 g_effectNodeDefaultBlockB[16];            /* 0x00726164 conf 0.70: Default parameter block copied into effect node child instances in maybe_Gfx_EffectNodeCreateChild_75B1AC. */
extern u32 g_effectNodeDefaultBlockC[50];            /* 0x007261B4 conf 0.70: Default parameter block containing animation motion entries and fallback node properties used by effect node child creat */
extern char* g_modelSlotNames[12];                   /* 0x00726808 conf 0.85: Table of 12 string pointers for preview model mesh slots ('meshNone', 'meshEGG', 'meshBee', etc.), indexed by slot id in */
extern u32 g_effectParamsDefaultTemplate[70];        /* 0x00726F70 conf 0.80: Default template of 70 words used by Gfx_EffectParams_LoadTemplate to initialize a newly allocated 0x1BC-byte effect par */
extern f32 g_skyBlendThresholds[4];                  /* 0x007275E4 conf 0.70: Float coefficients (0.0f, 30.0f, 60.0f, 90.0f) used by Gfx_SceneSpriteSet_BlendPresets to interpolate sky and weather pa */
extern char* g_animNameNut;                          /* 0x00727940 conf 0.85: Pointer to the default neutral/idle animation name 'Nut' at 0x007844AC, passed to Anim_PlayByIdForActor by 2D sprite act */
extern void* g_spriteAnimDescriptorTable[16];        /* 0x0072840C conf 0.65: 16-word table of default animation name pointers (such as 'Open' at 0x007844C8) and handler descriptors used by Gfx_Spri */
extern void* g_sceneNodeChildDispatchTable[46];      /* 0x00728470 conf 0.70: Dispatch table of 23 handler and constructor function pointers used by maybe_Gfx_SceneNode_EnsureChild to instantiate ch */
extern u32 g_sharedRenderStatePicaCommands[32];      /* 0x0072D818 conf 0.85: 32-word static command template uploaded to PICA200 GPU registers by maybe_Gfx_SharedRenderState_Apply to set up the def */
extern u32 g_displayBufferInitTemplate[4];           /* 0x0072D8F0 conf 0.65: Display buffer initialization parameter descriptor at 0x0072D8F0, read by Gfx_DisplayBuffer_InitState to configure frame */
extern s32 g_modelPartLayerMap[4];                   /* 0x0072F488 conf 0.80: Table mapping model render layer types to part filtering flags or indices, read by Gfx_ModelInstance_DrawPartLayerByType */
extern u32 g_picaCmdMaterialDrawTemplate[48];        /* 0x0072F548 conf 0.85: Command buffer template containing PICA200 register writes for drawing a material/pass pair, emitted by Gfx_CmdBuf_EmitM */
extern u32 g_picaCmdMaterialPassFooter[12];          /* 0x0072F608 conf 0.85: 48-byte (12-word) PICA command sequence emitted at the end of a material draw pass by Gfx_CmdBuf_EmitMaterialDraw and ap */
extern u32 g_picaCmdRenderStateTemplate[12];         /* 0x0072F638 conf 0.85: 48-byte render-state template consisting of 12 PICA command words starting with 0x0EED0EEE, copied into output command b */
extern u16 g_emitterTransformFlagTable[6];           /* 0x0072FA60 conf 0.75: Array of bit flags (0x1000, 0x2000, 0x4000...) indexed by emitter kind in Fx_BuildEmitterTransforms to determine transfo */
extern u32 g_picaDrawRecordSlotCommands[16];         /* 0x0072FA78 conf 0.80: Table of PICA200 register 0x1C5 command pairs indexed by slot to write fixed slot header commands in Gfx_DrawRecord_Writ */
extern f32 g_vec4ZeroOne[4];                         /* 0x0072FC2C conf 0.80: 4-element float vector constant {0.0f, 0.0f, 0.0f, 1.0f} used as default transform/scale values in maybe_Gfx_ResourceSet */
extern u32 g_nullFrameBufferHandle;                  /* 0x0072FC3C conf 0.70: Null/zero constant word copied into frame buffer state variables during framebuffer cleanup in maybe_Gfx_FreeFrameBuffer */
extern u32 g_y2rCurrentProcessHandle;                /* 0x00730D0C conf 0.85: Current process pseudo-handle constant (0xFFFF8001) passed to CTR Y2R service functions for memory buffer transfer and a */
extern u16 g_drawLine2DStepTable[91];                /* 0x00735090 conf 0.80: Lookup table of 91 coordinate step offsets for Bresenham 2D line and curve rasterization in Gfx_DrawLine2D16. */
extern char g_strBytesWarning[12];                   /* 0x007352DF conf 0.80: String literal ' bytes !!!\n' printed or formatted by texture tile conversion routines when checking buffer capacity. */
extern u16 g_emitterTransformShiftTable[6];          /* 0x0073BB04 conf 0.75: Table of 16-bit shift and bitmask constants indexed by emitter flag byte in Fx_BuildEmitterTransforms. */
extern u8 g_emitterComponentCountTable[4];           /* 0x0073BB10 conf 0.70: Byte table of emitter matrix component counts/indices read by Fx_BuildEmitterTransforms. */
extern u8 g_emitterTransformAxisMap[4];              /* 0x0073BB13 conf 0.65: Byte mapping of emitter axis permutation and transform order used in Fx_BuildEmitterTransforms. */
extern u32 g_flimFormatDescriptors[25];              /* 0x0073BD74 conf 0.80: Table of 20-byte (0x14) format descriptor entries indexed by FLIM texture format code, read by Gfx_Flim_Parse to extract */
extern u32 g_picaDefaultRegisterValues[1192];        /* 0x0073FF18 conf 0.80: Static master table of default PICA200 GPU register values copied into the GfxState context during Gfx_InitRegisterTable */
extern u32 g_picaRegisterIdLists[64];                /* 0x007411B8 conf 0.80: List of register IDs terminated by 0xBD expanded into bitsets during GPU context initialization in Gfx_InitRegisterTable */
extern u32 g_gfxProcessPseudoHandle;                 /* 0x007418C8 conf 0.85: Current process pseudo-handle constant (0xFFFF8001) used during graphics draw state initialization in maybe_Gfx_InitDraw */
extern u32 g_fxParticleFlags[6];                     /* 0x00741AE4 conf 0.70: Array of particle list update flags and mode constants {0x100, 0x200, 0, 1, 2, 3} used by particle simulation routines. */
extern f32 g_fxTrigStepConstants[8];                 /* 0x00741AFC conf 0.75: Table of float trigonometric step constants and angle radians used by Fx_BuildParticleRenderQuad and Fx_BuildEmitterTran */
extern u32 g_skeletalAnimDefaultFrameTable[72];      /* 0x00754B2C conf 0.85: 0x120-byte (72-word) default skeletal animation state table copied into per-frame animation work structures by maybe_Gfx */
extern f32 g_modelResourceInitDefaults[16];          /* 0x00754C4C conf 0.75: 16-word float table starting with {1.0f, 1.0f, 1.0f, 1.0f} used as default scale, color, and bounds parameters in Gfx_Mo */
extern void* g_effectInstanceVtable[10];             /* 0x00758714 conf 0.75: Vtable of the 2D/3D effect instance object, installed by maybe_Effect_FindOrCreateInstance into newly created effect ins */
extern void* g_gfxNodeBaseVtable[8];                 /* 0x00758A18 conf 0.85: Base vtable of GfxNode, restored by Gfx_Node_DtorBase during teardown before releasing children. */
extern void* g_gfxObjectDescVtable[24];              /* 0x00758E70 conf 0.90: Vtable of the Gfx_ObjectDesc class, installed by Gfx_ObjectDesc_Ctor4 into type-4 graphics object descriptors. */
extern void* g_sprite2DDispatchTableC[40];           /* 0x00759080 conf 0.75: Table of 40 function pointers and cleanup handlers for 2D sprite objects, referenced during destruction in maybe_Gfx_Spr */
extern void* g_gfxEmoteVtable[8];                    /* 0x00759638 conf 0.75: Vtable of the emote/speech bubble graphics object, installed by maybe_Gfx_Emote_InitVector. */
extern void* g_gadgetMeshVtable[8];                  /* 0x007598A0 conf 0.75: Vtable of the gadget mesh attachment object, installed during sub-model instantiation in Gfx_Model_AttachGadgetMesh. */
extern void* g_bufferChannelVtable[8];               /* 0x00759F98 conf 0.75: Vtable of the buffer channel object, installed during channel initialization in maybe_Gfx_BufferChannel_Init. */
extern void* g_gfxRenderNodeAVtable[12];             /* 0x0075A4EC conf 0.85: Vtable of graphics render node variant A, installed into newly allocated nodes by maybe_Gfx_CreateNodeA. */
extern void* g_gfxRenderNodeBVtable[12];             /* 0x0075A520 conf 0.85: Vtable of graphics render node variant B, installed into newly allocated nodes by maybe_Gfx_CreateNodeB. */
extern void* g_meshObjectVtable[14];                 /* 0x0075A8AC conf 0.85: Vtable of the renderable mesh scene object, installed during object initialization in Gfx_MeshObject_Init. */
extern void* g_trailMeshAnimRefVtable[6];            /* 0x0075A9F0 conf 0.80: Vtable of the anim-ref member embedded in trail-mesh effect objects, installed by Gfx_TrailMesh_Ctor. */
extern void* g_meshNodeChildVtable[8];               /* 0x0075AAA4 conf 0.80: Vtable of the mesh child node object, installed during child node initialization in maybe_Gfx_MeshNode_InitChildren. */
extern void* g_spriteChainNodeVtable[8];             /* 0x0075AAC8 conf 0.85: Vtable of the sprite-chain node object, installed by Gfx_SpriteChain_Node_Ctor. */
extern void* g_sceneNodeLazyChildVtable[8];          /* 0x0075ABA0 conf 0.80: Vtable of the 0x134-byte child scene object instantiated lazily by maybe_Gfx_SceneNode_EnsureChild. */
extern void* g_modelPartListVtable[8];               /* 0x0075AE04 conf 0.80: Vtable of the model part list object, installed into newly allocated 0xAC-byte part lists in maybe_Gfx_ModelPartList_Ini */
extern void* g_particleEmitterPoolAVtable[10];       /* 0x0075AF90 conf 0.85: Vtable of the particle emitter pool A class, installed into 0xAC-byte emitter objects by maybe_Effect_ParticleEmitter_In */
extern void* g_particleEmitterPoolBVtable[10];       /* 0x0075AFB4 conf 0.85: Vtable of the particle emitter pool B class, installed into 0x6C-byte emitter objects by maybe_Effect_ParticleEmitter_In */
extern void* g_particleEmitterPoolCVtable[10];       /* 0x0075AFD8 conf 0.85: Vtable of the particle emitter pool C class, installed into 0xAC-byte emitter objects by maybe_Effect_ParticleEmitter_In */
extern void* g_particleEmitterPoolDVtable[10];       /* 0x0075AFFC conf 0.85: Vtable of the particle emitter pool D class, installed into 0xAC-byte emitter objects by maybe_Effect_ParticleEmitter_In */
extern void* g_particleEmitterPoolEVtable[10];       /* 0x0075B020 conf 0.85: Vtable of the particle emitter pool E class, installed into 0xAC-byte emitter objects by maybe_Effect_ParticleEmitter_In */
extern void* g_effectNodeChild75B0B0Vtable[10];      /* 0x0075B0B0 conf 0.85: Vtable of the 0xAC-byte effect node child object, installed by maybe_Gfx_EffectNodeCreateChild_75B0B0. */
extern void* g_effectNodeChild75B0D4Vtable[10];      /* 0x0075B0D4 conf 0.85: Vtable of the effect node child class 75B0D4, installed by maybe_Gfx_EffectNodeCreateChild_75B0D4. */
extern void* g_effectNodeChild75B164Vtable[10];      /* 0x0075B164 conf 0.85: Vtable of the effect node child class 75B164, installed by maybe_Gfx_EffectNodeCreateChild_75B164. */
extern void* g_effectNodeChild75B188Vtable[10];      /* 0x0075B188 conf 0.85: Vtable of the effect node child class 75B188, installed by maybe_Gfx_EffectNodeCreateChild_75B188. */
extern void* g_effectNodeChild75B1ACVtable[10];      /* 0x0075B1AC conf 0.85: Vtable of the effect node child class 75B1AC, installed by maybe_Gfx_EffectNodeCreateChild_75B1AC. */
extern void* g_effectNodeChild75B1F4Vtable[10];      /* 0x0075B1F4 conf 0.85: Vtable of the effect node child class 75B1F4, installed by maybe_Gfx_EffectNodeCreateChild_75B1F4. */
extern void* g_effectNodeChild75B23CVtable[10];      /* 0x0075B23C conf 0.85: Vtable of the effect node child class 75B23C, installed by maybe_Gfx_EffectNodeCreateChild_75B23C. */
extern void* g_sharedRenderStateVtable[8];           /* 0x0075B260 conf 0.85: Vtable of the shared render-state manager object, installed during state initialization in maybe_Gfx_SharedRenderState_A */
extern void* g_trailModelTaskVtable[8];              /* 0x0075B8DC conf 0.75: Vtable of the trail work / model tracker object referenced in Gfx_TrailObject_Ctor and FieldParty_ResetMemberModels. */
extern void* g_modelAttachSlotVtable[12];            /* 0x0075C334 conf 0.90: Vtable of the Model_AttachSlot class in structs.json, installed into model attachment slot objects during initialization */
extern void* g_gfxRenderNodeCVtable[12];             /* 0x0075C378 conf 0.85: Vtable of graphics render node variant C, installed into newly allocated nodes by maybe_Gfx_CreateRenderNodeC. */
extern void* g_gfxRenderNodeDVtable[12];             /* 0x0075C3AC conf 0.85: Vtable of graphics render node variant D, installed into newly allocated nodes by maybe_Gfx_CreateRenderNodeD. */
extern void* g_spriteObjectVtable[47];               /* 0x0075C660 conf 0.85: Primary vtable (47 virtual method slots) of the 2D sprite object, installed by maybe_Gfx_SpriteObject_Ctor. */
extern void* g_sceneSubObjectVtable[16];             /* 0x0075CDFC conf 0.85: Vtable of the scene sub-object (and Ui_BattleTargetWindow base in structs.json), installed by Gfx_SceneSubObject_Ctor. */
extern void* g_trailMeshVtable[14];                  /* 0x0075D480 conf 0.85: Primary vtable of the trail-mesh effect object, installed by Gfx_TrailMesh_Ctor. */
extern void* g_gfxObjectDescSharedVtable[10];        /* 0x0075EA3C conf 0.80: Vtable of the shared object descriptor base class, installed by maybe_Gfx_ObjectDesc_InitShared. */
extern void* g_gfxObjectVariantVtable[10];           /* 0x0075ED78 conf 0.80: Vtable of the graphics object variant class, installed into newly allocated objects by maybe_Gfx_CreateObjectVariant. */
extern void* g_spriteChainVtable[12];                /* 0x0075F38C conf 0.90: Vtable of the Gfx_SpriteChain class in structs.json, installed by Gfx_SpriteChain_Node_Ctor. */
extern void* g_spriteChainUpdateVtable[55];          /* 0x0075F488 conf 0.80: 55-word primary vtable of the sprite chain updater object, installed by maybe_Gfx_SpriteChain_Update. */
extern void* g_drawable2DVtable[16];                 /* 0x0076007C conf 0.85: Vtable of the 2D drawable object, installed by maybe_Gfx_Drawable2D_Ctor. */
extern void* g_drawable2DEmptyVtable[16];            /* 0x00760480 conf 0.85: Vtable of the empty 2D drawable object variant, installed by maybe_Gfx_Drawable2D_Ctor_Empty. */
extern void* g_renderPassTaskVtable[12];             /* 0x007605E4 conf 0.85: Vtable of the render-pass task object, installed by Gfx_RenderPassTask_Init. */
extern void* g_gfxLargeObjectVtable[14];             /* 0x00760AC0 conf 0.80: Vtable of the large 0x1800-byte graphics scene object, installed by maybe_Gfx_ObjectCtor. */
extern void* g_sceneSpriteCtxVtable[10];             /* 0x007611F8 conf 0.85: Vtable of the scene sprite context object, installed by Gfx_Scene_SpriteCtx_Init. */
extern void* g_fieldSpriteBaseDtorVtable[14];        /* 0x007617CC conf 0.85: Vtable of the 2D field sprite base class, restored during teardown by Gfx_Sprite_Dtor and Gfx_Sprite_DtorAlt. */
extern void* g_spriteObjectSecondaryVtable[12];      /* 0x00763154 conf 0.80: Secondary vtable of the 2D sprite/particle object, installed into sub-interfaces by maybe_Gfx_SpriteObject_Ctor. */
extern void* g_spriteAnimBankVtable[8];              /* 0x007631B8 conf 0.85: Vtable of the sprite animation bank object, installed during construction in Gfx_SpriteAnimationBank_Create. */
extern void* g_spriteAnimBankTurnsVtable[8];         /* 0x007631D8 conf 0.85: Vtable of the turn-capable sprite animation bank variant, installed in Gfx_SpriteAnimationBank_CreateWithTurns. */
extern void* g_spriteParamsVtable[10];               /* 0x007642D4 conf 0.80: Vtable of the sprite parameters object, installed by maybe_Gfx_Sprite_InitParams. */
extern void* g_spriteParamsAltVtable[10];            /* 0x0076438C conf 0.80: Vtable of the alternative sprite parameters object, installed by maybe_Gfx_Sprite_InitParamsAlt. */
extern void* g_effectNodeListVtable[8];              /* 0x00764B98 conf 0.90: Vtable of the Gfx_EffectNodeList class in structs.json, installed by Gfx_EffectNodeList_Ctor and restored by its destruc */
extern void* g_spriteDescriptorVtable[39];           /* 0x00767430 conf 0.85: Primary vtable (39 slots, 0x9C bytes) of the 2D sprite descriptor object, installed by Gfx_Sprite_InitDescriptor. */
extern void* g_spriteMaterialBindingVtable[39];      /* 0x00767A8C conf 0.85: Primary vtable (39 slots, 0x9C bytes) of the sprite material binding descriptor, installed by Gfx_Sprite_InitMaterialBin */
extern void* g_spriteLayerDescriptorVtable[54];      /* 0x00767B48 conf 0.85: Primary vtable (54 slots, 0xD8 bytes) of the sprite layer descriptor object, installed by Gfx_Sprite_InitLayerDescriptor */
extern void* g_spriteSubBufferVtable[39];            /* 0x00767D38 conf 0.85: Primary vtable (39 slots, 0x9C bytes) of the sprite sub-buffer descriptor, installed by Gfx_Sprite_InitSubBuffer. */
extern void* g_spriteTextureLayerVtable[54];         /* 0x00767DF4 conf 0.85: Primary vtable (54 slots, 0xD8 bytes) of the sprite texture layer descriptor, installed by Gfx_Sprite_InitTextureLayer. */
extern void* g_sceneNodeDtorVtable[16];              /* 0x0076A57C conf 0.90: Vtable of the Gfx_SceneNode class in structs.json, restored during destruction in Gfx_SceneNode_Dtor. */
extern void* g_gfxRenderListVtable[14];              /* 0x0076AAFC conf 0.85: Vtable of the graphics render list object, installed by maybe_Gfx_RenderList_Init and restored during part destruction. */
extern void* g_actorTrailSubVtable[8];               /* 0x0076B690 conf 0.80: Secondary vtable of the actor trail effect object, installed by Effect_ActorTrail_Ctor and its variant. */
extern void* g_equipObjectVtable[10];                /* 0x0076D6A4 conf 0.85: Vtable of the 'equip' item attachment graphics object, installed by Gfx_CreateEquipObject. */
extern void* g_objectDescCtorAVtable[12];            /* 0x0076E04C conf 0.80: Virtual method table for object descriptor variant A installed in maybe_Gfx_ObjectDesc_CtorA. */
extern void* g_objectDescCtorBVtable[12];            /* 0x0076E0B4 conf 0.80: Virtual method table for object descriptor variant B installed in maybe_Gfx_ObjectDesc_CtorB. */
extern void* g_shakeNodeAVtable[12];                 /* 0x00772C50 conf 0.85: Virtual method table for camera shake node variant A installed in maybe_Gfx_CreateNodeNamedShakeA. */
extern void* g_shakeNodeBVtable[12];                 /* 0x00772D3C conf 0.85: Virtual method table for camera shake node variant B installed in maybe_Gfx_CreateNodeNamedShakeB and SpawnShakeNode. */
extern void* g_spriteMotionNodeVtable[54];           /* 0x00773630 conf 0.85: Virtual method table for animated sprite motion nodes installed in Gfx_SpriteNode_CtorWithMotion. */
extern void* g_actorTrailBaseVtable[12];             /* 0x007757A0 conf 0.85: Virtual method table for actor trail generator base instances installed in Effect_ActorTrail_Ctor. */
extern void* g_fieldSmithySparkEffectVtable[16];     /* 0x00776540 conf 0.95: Virtual method table for Field_Smithy_SparkEffect spark particle effect node used during smithing scenes. */
extern void* g_collisionProxyDescVtable[12];         /* 0x00777E58 conf 0.85: Virtual method table for collision proxy descriptors installed in Gfx_CollisionProxy_InitDesc. */
extern void* g_effectVariantSubClassVtable[12];      /* 0x00778084 conf 0.80: Virtual method table for effect variant subclass instances referenced in maybe_Effect_CreateVariant. */
extern void* g_spriteObjectCtorVtable[12];           /* 0x0077810C conf 0.85: Virtual method table for sprite objects installed in Gfx_SpriteObject_Ctor. */
extern void* g_spriteObjectVectorsVtable[12];        /* 0x00778154 conf 0.85: Virtual method table for sprite objects with vector initialization installed in Gfx_SpriteObject_CtorWithVectors. */
extern void* g_actorTrailVariantBVtable[12];         /* 0x0077D1CC conf 0.85: Virtual method table for second actor trail variant installed in maybe_Effect_ActorTrailVariant_Ctor. */
extern void* g_regularShakeWorkVtable[12];           /* 0x0077D8A4 conf 0.85: Virtual method table for periodic camera shake work items installed in maybe_Gfx_CreateRegularShakeWork and RegularShake */
extern void* g_trailObjectVtable[31];                /* 0x0077F578 conf 0.90: Virtual method table for Gfx_TrailObject instances installed in Gfx_TrailObject_Ctor. */
extern void* g_gfxNodeVtable[26];                    /* 0x0077F5FC conf 0.90: Virtual method table for base Gfx_Node class instances (26 slots) installed in Gfx_Node_Ctor. */
extern void* g_screenDtorVtable[12];                 /* 0x0077FB78 conf 0.85: Virtual method table restored during screen object destruction in Gfx_Screen_Dtor. */
extern void* g_sceneSpriteSubSetVtable[12];          /* 0x00780120 conf 0.85: Virtual method table for scene sprite sub-set instances installed in Gfx_SceneSpriteSubSet_Create. */
extern void* g_sceneSpriteSetVtable[12];             /* 0x00780158 conf 0.85: Virtual method table for scene sprite collection set instances installed in Gfx_SceneSpriteSet_Create. */
extern void* g_trailObjectFieldResetVtable[12];      /* 0x00780190 conf 0.85: Virtual method table assigned during party member model trail reset in FieldParty_ResetMemberModels. */
extern void* g_moviePlayerDtorVtable[12];            /* 0x007804BC conf 0.85: Virtual method table restored during movie player shutdown in maybe_Gfx_MoviePlayer_Dtor. */
extern void* g_streamSlotVtable[12];                 /* 0x00780C28 conf 0.85: Virtual method table for media streaming buffer slots installed in maybe_Gfx_StreamSlot_Init. */
extern void* g_moviePlayerBuffersVtable[4];          /* 0x00780C3C conf 0.90: Virtual method table for Gfx_MoviePlayer buffer management installed in maybe_Gfx_MoviePlayer_InitBuffers. */
extern void* g_moviePlayerInitAVtable[12];           /* 0x00780C5C conf 0.85: Virtual method table for movie player decoder stream context installed in maybe_Gfx_MoviePlayer_Init. */
extern void* g_movieVtable[4];                       /* 0x00780C70 conf 0.90: Virtual method table for base Gfx_Movie playback controller installed in maybe_Gfx_MoviePlayer_Init. */
extern void* g_movieStreamDeleteAVtable[12];         /* 0x00780C88 conf 0.85: Virtual method table for movie stream track A deletion and creation in Gfx_MovieStream_DtorDeleteA and CreateStreamObjec */
extern void* g_movieStreamDeleteBVtable[12];         /* 0x00780CAC conf 0.85: Virtual method table for movie stream track B deletion and creation in Gfx_MovieStream_DtorDeleteB and CreateStreamObjec */
extern void* g_movieStreamDeleteCVtable[12];         /* 0x00780CD0 conf 0.85: Virtual method table for movie stream track C deletion and creation in Gfx_MovieStream_DtorDeleteC and CreateStreamObjec */
extern void* g_movieStreamDeleteDVtable[12];         /* 0x00780D04 conf 0.85: Virtual method table for movie stream track D deletion and creation in Gfx_MovieStream_DtorDeleteD and CreateStreamObjec */
extern void* g_gpuChannelOpenVtable[12];             /* 0x00780FB4 conf 0.85: Virtual method table for GPU IPC communication channel object installed in Gfx_OpenGpuChannel. */
extern void* g_moviePlayerSubObjectVtable[12];       /* 0x0078112C conf 0.85: Virtual method table for movie player sub-service object restored during shutdown in maybe_Gfx_MoviePlayer_Dtor. */
extern void* g_fxSystemSubVtableA[12];               /* 0x0078118C conf 0.85: Virtual method table for particle system subsystem node A installed in Fx_System_Init. */
extern void* g_fxSystemSubVtableB[12];               /* 0x0078119C conf 0.85: Virtual method table for particle system subsystem node B installed in Fx_System_Init. */
extern void* g_fxSystemSubVtableC[12];               /* 0x007811C4 conf 0.85: Virtual method table for particle system subsystem node C installed in Fx_System_Init. */
extern void* g_fxSystemSubVtableD[12];               /* 0x007811EC conf 0.85: Virtual method table for particle system subsystem node D installed in Fx_System_Init. */
extern void* g_textureDescriptorInitVtable[12];      /* 0x00781214 conf 0.85: Virtual method table for texture descriptor management installed in Gfx_Texture_InitDescriptor. */
extern void* g_modelResourceResetVtable[12];         /* 0x00781240 conf 0.85: Virtual method table restored during model resource reset in maybe_Gfx_ModelResource_Reset. */
extern void* g_modelInstanceInitVtable[12];          /* 0x0078215C conf 0.85: Virtual method table installed into newly allocated model instance objects in Gfx_ModelInstance_Init. */
extern void* g_animKeyframeTrackVtable[12];          /* 0x0078216C conf 0.85: Virtual method table for keyframe animation track evaluators used across model instance updates. */
extern void* g_sceneSpriteDebugStringVtable[12];     /* 0x00782544 conf 0.80: Virtual method table for sprite set debugging descriptor objects in maybe_Gfx_SceneSpriteSet_BuildDebugString. */
extern void* g_gfxNode7826E8Vtable[12];              /* 0x007826E8 conf 0.85: Virtual method table for specialized scene graph node subclass installed in maybe_Gfx_NodeCtor_7826E8. */
extern void* g_modelInstanceResetVtable[5];          /* 0x00782714 conf 0.90: Virtual method table for Gfx_ModelInstance instances (5 slots) restored during reuse reset in maybe_Gfx_ModelInstance_Re */
extern void* g_sceneSpriteSetStringVtable[12];       /* 0x00782760 conf 0.80: Virtual method table for secondary sprite debug string generator in maybe_Gfx_SceneSpriteSet_BuildDebugString. */
extern void* g_fontGlyphPageVtable[12];              /* 0x00782868 conf 0.85: Virtual method table for font glyph texture page render targets in maybe_Font_GlyphPage_FillTexels and SubmitDrawList. */
extern void* g_charModelConstructVtable[12];         /* 0x007828B0 conf 0.85: Virtual method table for character model instances installed during construction in Gfx_CharModel_Construct. */
extern void* g_animKeyframeTrackVtableAlt[12];       /* 0x00782A1C conf 0.85: Alternative virtual method table for keyframe animation track evaluators in Anim_KeyframeTrack_EvaluateAll. */
extern void* g_overlayQuadVtable[12];                /* 0x00782AFC conf 0.85: Virtual method table for screen overlay quad display elements in Gfx_Overlay_AddQuad and track reset. */
extern void* g_renderListSubVtableA[12];             /* 0x00783320 conf 0.85: Sub-interface virtual method table A for Gfx_RenderList container initialized in maybe_Gfx_RenderList_Init. */
extern void* g_renderListSubVtableB[12];             /* 0x00783384 conf 0.85: Sub-interface virtual method table B for Gfx_RenderList container initialized in maybe_Gfx_RenderList_Init. */
extern void* g_renderListSubVtableC[12];             /* 0x007833AC conf 0.85: Sub-interface virtual method table C for Gfx_RenderList container initialized in maybe_Gfx_RenderList_Init. */
extern void* g_renderListSubVtableD[12];             /* 0x007833C0 conf 0.85: Sub-interface virtual method table D for Gfx_RenderList container initialized in maybe_Gfx_RenderList_Init. */
extern void* g_renderListSubVtableE[12];             /* 0x007833D4 conf 0.85: Sub-interface virtual method table E for Gfx_RenderList container initialized in maybe_Gfx_RenderList_Init. */
extern void* g_renderObjectMaterialVtable[12];       /* 0x0078348C conf 0.85: Virtual method table for material set binding objects in Gfx_RenderObject_BindMaterialSet. */
extern void* g_renderObjectBaseVtable[12];           /* 0x007834A0 conf 0.90: Virtual method table for base Gfx_RenderObject instances installed in Gfx_RenderObject_InitBase. */
extern void* g_renderObjectBlendMaterialVtable[12];  /* 0x007834B4 conf 0.85: Virtual method table for alpha blend material set bindings in Gfx_RenderObject_BindBlendMaterialSet. */
extern void* g_gfxNodeHandleReleaseVtable[12];       /* 0x00783A28 conf 0.85: Virtual method table assigned during node handle release operations in maybe_Gfx_ReleaseNodeHandle. */
extern u32 maybe_g_drawStateBuffer1C40[4];           /* 0x007A1C40 conf 0.45: State buffer block referenced during GPU draw state initialization in maybe_Gfx_InitDrawState. */
extern char* g_materialSetTcsBaseName;               /* 0x007A2DA4 conf 0.90: Pointer to material set name string 'tcs_base' used by Gfx_RenderObject_BindMaterialSetFromDesc. */
extern void* g_renderObjectKeyframeTrackJumpTable[64]; /* 0x007A2DE8 conf 0.90: 64-slot jump table of keyframe track evaluation handlers dispatched in Gfx_KeyframeTrack_DispatchHandler. */
extern u32 g_screenFadeState;                        /* 0x007A61A0 conf 0.85: Global screen fade transition state word checked and updated in Gfx_ScreenFade_Update. */
extern u32 g_effect2dManagerPackHandle;              /* 0x007A626C conf 0.85: Handle to 2D effect manager archive pack loaded by Gfx_Effect2D_LoadManagerPack and referenced during effect creation. */
extern u32 g_effect2dCommonPackEntry[4];             /* 0x007A62D4 conf 0.90: Common 2D effect pack descriptor entry ('effect2d/common_effect.pack') initialized in Gfx_Effect2D_LoadCommonPack. */
extern f32 g_billboardBasisMatrix[16];               /* 0x007A63D8 conf 0.85: Global 4x4 matrix storage for camera billboard basis calculations in maybe_Gfx_ComputeBillboardBasis and Field_Scene_Fin */
extern u8 g_viewTransformActiveFlag;                 /* 0x007A63D9 conf 0.85: Byte flag indicating whether camera view transform caching is active in maybe_Gfx_ComputeViewTransform. */
extern f32 g_billboardScaleFactor;                   /* 0x007A6408 conf 0.85: Float scale multiplier applied to billboard vertex distances in maybe_Gfx_ComputeBillboardBasis. */
extern u8 g_sceneSpriteDebugFlag;                    /* 0x007A68E0 conf 0.85: Debug logging enable flag checked in maybe_Gfx_SceneSpriteSet_BuildDebugString. */
extern u32 g_screenClearColorPreset2;                /* 0x007A74D0 conf 0.90: RGB screen clear color value for preset #2 in maybe_Gfx_SetScreenClearColor. */
extern u32 g_screenClearColorPreset1;                /* 0x007A74D4 conf 0.90: RGB screen clear color value for preset #1 in maybe_Gfx_SetScreenClearColor. */
extern u32 g_screenClearColorPreset3;                /* 0x007A74DC conf 0.90: RGB screen clear color value for preset #3 in maybe_Gfx_SetScreenClearColor. */
extern u32 g_screenClearColorPreset4;                /* 0x007A74E8 conf 0.90: RGB screen clear color value for preset #4 in maybe_Gfx_SetScreenClearColor. */
extern u32 g_screenClearColorPreset5;                /* 0x007A74F4 conf 0.90: RGB screen clear color value for preset #5 in maybe_Gfx_SetScreenClearColor. */
extern u32 g_screenClearColorPreset6;                /* 0x007A74F8 conf 0.90: RGB screen clear color value for preset #6 in maybe_Gfx_SetScreenClearColor. */
extern u32 g_billboardOrientationWork;               /* 0x007A8F34 conf 0.80: Global billboard orientation state block passed to func_0010009C in maybe_Effect_UpdateBillboardOrientation. */
extern u32 g_movieCmdPoolHead[8];                    /* 0x007AE154 conf 0.85: Command pool queue head for movie playback track buffers in Gfx_InitCommandPool and movie track operations. */
extern u32 g_movieCmdPoolTail;                       /* 0x007AE174 conf 0.85: Tail pointer for movie playback command pool queue initialized in Gfx_InitCommandPool. */
extern u32 g_movieSurfaceDescriptorCount;            /* 0x007AE178 conf 0.85: Counter of allocated movie rendering surface descriptors incremented in maybe_Gfx_MovieSurface_SetupDescriptor. */
extern u32 g_y2rSessionHandle;                       /* 0x007AE17C conf 0.90: Session handle to the CTR Y2R (YUV-to-RGB conversion) hardware service initialized in Gfx_Y2r_Init. */
extern u32 g_moviePlayerVramState;                   /* 0x007AE180 conf 0.85: VRAM allocation pointer for movie player frame decoding initialized in maybe_Gfx_MoviePlayer_Init. */
extern u32 g_vramBankConfig;                         /* 0x007AE184 conf 0.85: Configuration descriptor word for CTR VRAM memory banks set in Gfx_InitVramBanks. */
extern u8 g_drawListSubmittedFlag;                   /* 0x007AE18C conf 0.85: Flag indicating whether GPU draw command lists have been submitted in the current frame. */
extern u32 g_gfxResourceAttachFlag;                  /* 0x007AE324 conf 0.85: Global boolean flag controlling resource attachment in Gfx_SetGlobalBoolFlag and maybe_Gfx_ResourceList_Attach. */
extern u32 g_charShadowPassState;                    /* 0x007AE500 conf 0.85: Render state descriptor pointer for character shadow rendering passes in Gfx_CharShadowPass_Release. */
extern void* g_movieStreamAllocatorC;                /* 0x007AE5B4 conf 0.85: Function pointer to stream allocation routine C for movie stream decoding. */
extern void* g_movieSliceTableAllocator;             /* 0x007AE5BC conf 0.85: Function pointer to allocation routine for movie frame slice tables in Gfx_Movie_AllocSliceTable. */
extern void* g_movieStreamAllocatorB;                /* 0x007AE5C4 conf 0.85: Function pointer to stream allocation routine B for movie stream decoding. */
extern void* g_movieStreamAllocatorA;                /* 0x007AE5CC conf 0.85: Function pointer to stream allocation routine A for movie stream decoding. */
extern void* g_vramAllocatorD;                       /* 0x007AE5D4 conf 0.85: Function pointer to VRAM allocator D used by MoLive decoder stream creation. */
extern void* g_vramAllocatorC;                       /* 0x007AE5DC conf 0.85: Function pointer to VRAM allocator C used during VRAM entry allocation in Gfx_Vram_AllocEntry. */
extern char* g_fsRomMountPath;                       /* 0x007AE5E8 conf 0.90: Pointer to ROM filesystem mount prefix string 'rom:' used by Fs_MountByName in streaming initialization. */
extern u32 g_overlayAddQuadGuard;                    /* 0x007AE608 conf 0.90: One-time static initialization guard word for overlay quad table in Gfx_Overlay_AddQuad. */
extern u32 g_displayContextState[8];                 /* 0x007AE61C conf 0.85: Global display context parameters (resolution, format, VRAM buffers) initialized in Gfx_Display_Initialize. */
extern u32 g_modelTextureDrawConfig[8];              /* 0x007AE63C conf 0.85: Configuration descriptor for model texture binding and rendering in Gfx_ModelInstance_BindTextureAndDraw. */
extern u32 g_modelTextureDrawGuardA;                 /* 0x007AE654 conf 0.90: Static initialization guard word A for model texture drawing in Gfx_ModelInstance_BindTextureAndDraw. */
extern u32 g_modelTextureDrawGuardB;                 /* 0x007AE658 conf 0.90: Static initialization guard word B for model texture drawing in Gfx_ModelInstance_BindTextureAndDraw. */
extern u32 g_modelTextureDrawState[4];               /* 0x007AE670 conf 0.85: State parameters updated during model texture binding in Gfx_ModelInstance_BindTextureAndDraw. */
extern u32 g_modelMeshWriteBuffer[4];                /* 0x007AE690 conf 0.85: Buffer header for model mesh command generation in Gfx_ModelInstance_WriteMeshCommands. */
extern u8 g_overlayQuadStateFlag;                    /* 0x007AE6E4 conf 0.85: Byte state flag indicating overlay quad rendering mode in maybe_Gfx_Overlay_WriteQuadState. */
extern u32 g_overlaySpriteTransitionGuardA;          /* 0x007AE6EC conf 0.90: Static initialization guard word A for sprite quad overlay rendering in Gfx_Overlay_DrawSpriteQuad. */
extern u32 g_overlaySpriteQuadGuardB;                /* 0x007AE6F0 conf 0.90: Static initialization guard word B passed to __cxa_guard_acquire in Gfx_Overlay_DrawSpriteQuad. */
extern u32 g_overlaySpriteQuadGuardC;                /* 0x007AE6F4 conf 0.90: Static initialization guard word C passed to __cxa_guard_acquire in Gfx_Overlay_DrawSpriteQuad. */
extern u32 g_overlaySpriteTransitionGuardB;          /* 0x007AE6F8 conf 0.90: Static initialization guard word passed to __cxa_guard_acquire in maybe_Gfx_Overlay_DrawSpriteTransition. */
extern u32 g_overlaySpriteTransitionGuardC;          /* 0x007AE6FC conf 0.90: Static initialization guard word C passed to __cxa_guard_acquire in maybe_Gfx_Overlay_DrawSpriteTransition. */
extern u32 g_overlaySpriteTransitionGuardD;          /* 0x007AE700 conf 0.90: Static initialization guard word D passed to __cxa_guard_acquire in maybe_Gfx_Overlay_DrawSpriteTransition. */
extern u32 g_overlaySpriteQuadBuffer[4];             /* 0x007AE704 conf 0.85: Static buffer storage populated for sprite quad overlay rendering in Gfx_Overlay_DrawSpriteQuad. */
extern u32 g_overlaySpriteTransitionBuffer[4];       /* 0x007AE714 conf 0.85: Static buffer storage populated during sprite transition overlay rendering in maybe_Gfx_Overlay_DrawSpriteTransition. */
extern u32 g_displayDriverInitFlag;                  /* 0x007AE724 conf 0.85: Display driver subsystem initialisation flag set during maybe_Gfx_InitDisplayDriver and Input_Initialize. */
extern u32 g_renderDeviceState[8];                   /* 0x007AE734 conf 0.85: Global rendering device state and context descriptor pointer initialized in Gfx_InitRenderDevice. */
extern u32 g_moveNodeSingleton[8];                   /* 0x007AE738 conf 0.80: Singleton motion graph node descriptor initialized in maybe_Gfx_MoveNode_CreateA and CreateB. */
extern u32 g_soundVoicePoolState;                    /* 0x007AE8D0 conf 0.80: Audio voice pool buffer pointer referenced during audio/video subsystem shutdown and track updates. */
extern u32 g_gpuStateInvalidateFlag;                 /* 0x007AE8E8 conf 0.85: Flag indicating GPU state cache invalidation required in Gfx_GpuState_Invalidate and Gfx_InitSubsystems. */
extern void* g_gpuCommandListPool;                   /* 0x007AE8EC conf 0.90: Pointer to allocated GPU command list pool buffer initialized in Gfx_InitCommandLists and Gfx_InitializeContext. */
extern void* g_gpuCommandListFreeHead;               /* 0x007AE8F0 conf 0.90: Head pointer of the GPU command list free list managed by Gfx_InitCommandLists and Gfx_InitRenderQueue. */
extern void* g_gpuSubsystemContext;                  /* 0x007AE900 conf 0.85: Context pointer for the GPU subsystem initialized during Gfx_InitializeContext. */
extern u32 g_gpuSyncTimestampLo;                     /* 0x007AE928 conf 0.85: Low 32 bits of GPU vertical blank synchronization timestamp in maybe_Gfx_HandleVBlank and ProcessFrame. */
extern u32 g_gpuDeadlinePair[2];                     /* 0x007AE930 conf 0.85: 64-bit GPU buffer transfer deadline timestamp (lo/hi pair) checked in maybe_Gfx_ReadGpuBuffer and TransferGpuBuffer. */
extern void* g_gpuCallbackListHead;                  /* 0x007AE954 conf 0.85: Head pointer of GPU frame completion callback linked list in maybe_Gfx_InvokeCallbacks and ProcessFrame. */
extern u32 g_picaLightSourceRegister;                /* 0x007AEA6C conf 0.85: PICA GPU lighting source configuration register cache word in maybe_Gfx_Pica_SetLightSource. */
extern u32 g_framebufferInitFlag;                    /* 0x007AEA70 conf 0.90: Framebuffer hardware allocation and initialization status word checked in maybe_Gfx_FreeFrameBuffers and InitFrameBuffer */
extern u32 g_y2rIpcSessionHandle;                    /* 0x007AEAAC conf 0.90: Hardware IPC session handle for CTR Y2R service queries in Gfx_Y2r_SendDriverInit and related send commands. */
extern u32 g_staticNodeRefs[8];                      /* 0x007AEAE0 conf 0.80: Static scene graph node reference array initialized in maybe_Gfx_StaticInitNodeRefs. */
extern void* g_fxSystemParticlePool;                 /* 0x007AEB68 conf 0.90: Pointer to global particle allocation pool passed to maybe_Fx_AllocParticleNode in Fx_BuildParticleRenderQuad and emissi */
extern u32 g_fxEmitterFrameContext[8];               /* 0x007AEB6C conf 0.85: Current particle emitter frame transformation context in maybe_Fx_UpdateEmitterFrame. */
extern f32* g_particleRandomTableB;                  /* 0x007AEBA8 conf 0.85: Pointer to random float lookup table B (points to 0x0073555C) used in maybe_Fx_EmitParticlesRandomOrientedB. */
extern f32* g_particleRandomTableC;                  /* 0x007AEBC8 conf 0.85: Pointer to random float lookup table C (points to 0x00735970) used in maybe_Fx_EmitParticlesRandomOrientedC. */
extern u32 g_spriteQuadTransformGuard;               /* 0x007AECD0 conf 0.90: One-time static initialization guard word for sprite quad transform vector in maybe_Gfx_Sprite_BuildQuadTransforms. */
extern f32 g_spriteQuadOffsetVec2[2];                /* 0x007AECD4 conf 0.90: 2-float quad offset vector (X, Y) lazily initialized and added to sprite vertex coordinates in maybe_Gfx_Sprite_BuildQua */
extern u32 g_gpuTextureUnitsDirtyMask;               /* 0x007AED34 conf 0.90: Bitmask of dirty GPU texture units (units 0-2) flagged for pending command list flush in Gfx_GpuCmd_FlushTextureUnits. */
extern u32 g_gpuTextureUnitsActiveMask;              /* 0x007AED38 conf 0.90: Bitmask of active GPU texture units configured and bound in Gfx_GpuState_SetupTextureUnit. */
extern u32 g_gpuMasterState[16];                     /* 0x007AED44 conf 0.85: Global GPU master render state structure initialized in Gfx_LoadDefaultState and used by lighting setup routines. */
extern u32 g_picaRegisterTableFormatA;               /* 0x007AED54 conf 0.85: PICA register configuration table descriptor initialized in maybe_Gfx_InitRegisterTables. */
extern u32 g_picaRegisterTableFormatB;               /* 0x007AEDB4 conf 0.85: PICA register descriptor table format B (initial value 9) configured in maybe_Gfx_InitRegisterTables. */
extern u32 g_picaRegisterTableFormatC;               /* 0x007AEDCC conf 0.85: PICA register descriptor table format C (initial value 1) configured in maybe_Gfx_InitRegisterTables. */
extern u32 g_picaRegisterTableFormatD;               /* 0x007AEDE4 conf 0.85: PICA register descriptor table format D (initial value 23 / 0x17) configured in maybe_Gfx_InitRegisterTables. */
extern u32 g_gpuMaterialDirtyMask;                   /* 0x007AF058 conf 0.85: Bitmask of dirty GPU material registers needing hardware state synchronization in Gfx_GpuState_Invalidate. */
extern f32 g_gpuMaterialAmbientRed;                  /* 0x007AF05C conf 0.85: Material ambient red color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialAmbientGreen;                /* 0x007AF060 conf 0.85: Material ambient green color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialAmbientBlue;                 /* 0x007AF064 conf 0.85: Material ambient blue color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialDiffuseRed;                  /* 0x007AF068 conf 0.85: Material diffuse red color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialDiffuseGreen;                /* 0x007AF06C conf 0.85: Material diffuse green color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialDiffuseBlue;                 /* 0x007AF070 conf 0.85: Material diffuse blue color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialSpecularRed;                 /* 0x007AF074 conf 0.85: Material specular red color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialSpecularGreen;               /* 0x007AF078 conf 0.85: Material specular green color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern f32 g_gpuMaterialSpecularBlue;                /* 0x007AF07C conf 0.85: Material specular blue color component written to PICA GPU registers in maybe_Gfx_GpuState_WriteMaterialColor. */
extern void* g_gpuActiveCommandContext;              /* 0x007AF080 conf 0.85: Pointer to the currently active GPU command context initialized in Gfx_InitCommandLists. */
extern void* g_gpuRenderQueue;                       /* 0x007AF088 conf 0.85: Global GPU render queue object pointer initialized in Gfx_InitRenderQueue and updated during texture binding. */
extern u32 g_gpuIpcCommandResult;                    /* 0x007AF0D8 conf 0.85: Status result code cached from GPU hardware service IPC command executions in Gfx_IpcCmd190040 and Gfx_IpcCmd2B0000. */
extern u32 g_gspGpuSessionActive[6];                 /* 0x007AF178 conf 0.85: GSP::GPU service session active state and synchronization parameters initialized in maybe_Gfx_InitDrawState. */
extern u32 g_gspGpuEventHandle;                      /* 0x007AF188 conf 0.90: CTR GSPGPU hardware synchronization event handle initialized in maybe_Gfx_InitDrawState and Sound_OpenDriverSession. */
extern u32 g_gspGpuSharedMemHandle;                  /* 0x007AF18C conf 0.90: CTR GSPGPU shared memory block handle initialized in maybe_Gfx_InitDrawState and Sound_OpenDriverSession. */
extern u32 g_gpuCommandBufferState;                  /* 0x007AF1A4 conf 0.85: Command buffer allocation state and display mode mask in Gfx_InitializeCommandBuffers and Gfx_SetDisplayMode. */
extern u32 g_gpuFrameBufferIpcResult;                /* 0x007AF1A8 conf 0.85: IPC query result status for framebuffer allocation queries in Os_SendIpcQuery6 and maybe_Gfx_FreeFrameBuffers. */
extern void* g_fxParticleListUpdateTable[16];        /* 0x007AFED8 conf 0.85: Function pointer dispatch table for particle list update handlers in maybe_Fx_UpdateParticleListL and related particle e */
extern u32 g_fxGlobalEmitterFrameState[12];          /* 0x007AFF18 conf 0.85: Global particle emitter frame step counter and batch flags array incremented cyclically in Fx_AdvanceEmitterFrame. */
extern f32 g_fxParticleVelocityScaleTable[4];        /* 0x007AFF34 conf 0.85: Lookup table of floating-point velocity scaling factors indexed during particle list updates in maybe_Fx_UpdateParticleL */
extern u32 g_fxEmitterStepLimit;                     /* 0x007AFF3C conf 0.85: Cyclical frame step limit word (increments up to 8 then resets) evaluated in Fx_AdvanceEmitterFrame. */
extern void* g_modelResourceSectionDescriptors;      /* 0x007AFF40 conf 0.85: Pointer to model resource binary section descriptor table initialized in Gfx_ModelResource_Parse. */
extern f32* g_fxSinTable128Pointer;                  /* 0x007B0030 conf 0.85: Pointer to 128-entry trigonometry sine lookup table initialized in maybe_Math_InitSinTable128. */
extern u32 g_fxParticleOffsetIndex;                  /* 0x007B0034 conf 0.85: Current particle offset buffer index incremented in Fx_AddParticleOffset and used in quad generation. */
extern f32 g_fxGlobalVelocityVector[4];              /* 0x007B0038 conf 0.85: Global velocity reference vector applied during particle emission in maybe_Fx_EmitParticlesFromGlobalVelocity. */
extern u32 g_gfxTextureBlitEnabled;                  /* 0x007B0070 conf 0.90: Global flag enabling direct texture blit and sub-region transfer operations in Gfx_SetTextureBlit and Gfx_SetTextureRegi */
extern u32 g_gpuChannelStatus;                       /* 0x007B0080 conf 0.85: Status and configuration word (initial value 0x100) for CTR GPU communication channel in Gfx_OpenGpuChannel. */
extern void* g_gpuChannelBuffer;                     /* 0x007B00A4 conf 0.85: Pointer to memory buffer mapped for GPU channel transfers in Gfx_OpenGpuChannel and cleared in ShutdownChannel. */
extern u32 g_gpuChannelEventHandle;                  /* 0x007B00AC conf 0.90: CTR synchronization event handle for GPU channel interrupt completion in Gfx_OpenGpuChannel. */
extern u32 g_gpuChannelSessionHandle;                /* 0x007B00E0 conf 0.90: CTR service session handle for GPU IPC channel communication in Gfx_OpenGpuChannel. */
extern void* g_fxParticleUpdateDispatchTableA[8];    /* 0x007B2CAC conf 0.85: Per-emitter particle step evaluation dispatch table A in maybe_Fx_UpdateParticleListB and UpdateParticleListD. */
extern void* g_fxParticleUpdateDispatchTableB[8];    /* 0x007B2CCC conf 0.85: Per-emitter particle step evaluation dispatch table B in maybe_Fx_UpdateParticleListB and UpdateParticleListD. */
extern void* g_fxParticleUpdateDispatchTableC[8];    /* 0x007B2CE8 conf 0.85: Per-emitter particle step evaluation dispatch table C in maybe_Fx_UpdateParticleListB and UpdateParticleListD. */
extern u32 g_gpuSessionTimeout;                      /* 0x007B2D08 conf 0.85: GPU session communication timeout value or handle cleared during session finalization in maybe_Gfx_FinalizeSession. */
extern void* g_gfxBufferCopyByFormatFn;              /* 0x007B2D18 conf 0.85: Function pointer to format-specific buffer blit and copy routine invoked by maybe_Gfx_BufferCopyByFormat. */
extern void* g_defaultRenderStatePointers[8];        /* 0x007B2D4C conf 0.85: Array of default shader configuration and pipeline state pointers populated in Gfx_RenderState_SetDefaultPointers. */
extern void* g_effectInstancePool;                   /* 0x007B4D60 conf 0.85: Pointer to global effect instance pool buffer traversed in maybe_Effect_FindOrCreateInstance. */
extern u32 g_effectInstanceCount;                    /* 0x007B4D64 conf 0.85: Active count of allocated effect instances checked and incremented in maybe_Effect_FindOrCreateInstance. */
extern void* g_spriteAnimBankPool;                   /* 0x007B7D88 conf 0.90: Pointer to global sprite animation bank storage pool (50 slots) populated in Gfx_SpriteAnimationBank_Create. */
extern u32 g_spriteAnimBankPoolIndex;                /* 0x007B7D8C conf 0.90: Next available slot index within g_spriteAnimBankPool incremented in Gfx_SpriteAnimationBank_Create. */
extern void* g_spriteAnimBankTurnsPool;              /* 0x007B7F20 conf 0.90: Pointer to turn-capable sprite animation bank storage pool (5 slots) populated in Gfx_SpriteAnimationBank_CreateWithTurn */
extern u32 g_spriteAnimBankTurnsPoolIndex;           /* 0x007B7F24 conf 0.90: Next available slot index within g_spriteAnimBankTurnsPool incremented in Gfx_SpriteAnimationBank_CreateWithTurns. */
extern u8 g_charShadowTextureInit;                   /* 0x007BE344 conf 0.90: One-time initialization flag for character shadow texture and curve tables in Gfx_CharShadowPass_Init. */
extern void* g_charShadowTextureDescriptor;          /* 0x007BE348 conf 0.90: Texture descriptor pointer for character shadow rendering passes initialized in Gfx_CharShadowPass_Init. */
extern u8 g_engineSubsystemInitFlag;                 /* 0x007BE354 conf 0.90: Engine subsystem one-time initialization guard flag checked in Engine_Initialize and Engine_ShutdownAllSubsystems. */
extern u8 g_overlayQuadBatchInitFlag;                /* 0x007BE38C conf 0.90: Singleton initialization guard flag for overlay quad rendering buffer in Gfx_Overlay_AddQuad. */
extern void* g_overlayQuadBatchSingleton;            /* 0x007BE390 conf 0.90: Singleton buffer base pointer for screen overlay quad batching initialized in Gfx_Overlay_AddQuad. */
extern char g_strSpriteActor[7];                     /* 0x007BE784 conf 0.95: String literal 'sprite' used for sprite actor component tagging in Gfx_SpriteActor_InitFromRecord. */
extern char g_strSprite2dDesc[7];                    /* 0x007BE78B conf 0.95: String literal 'sprite' used during 2D sprite descriptor initialization in Gfx_Sprite2D_InitFromDesc. */
extern char g_strSpriteMeshEmitter[7];               /* 0x007BE7BC conf 0.95: String literal 'sprite' used in mesh emitter creation in maybe_Effect_CreateMeshEmitterFromParams. */
extern char g_strSpriteMeshEmitterPair[7];           /* 0x007BE7C3 conf 0.95: String literal 'sprite' used in mesh emitter pair creation in maybe_Effect_CreateMeshEmitterPair. */
extern char g_strSpriteMeshEmitterPos[7];            /* 0x007BE7D1 conf 0.95: String literal 'sprite' used in positioned mesh emitter creation in maybe_Effect_CreateMeshEmitterAtPosition. */
extern char g_strSpriteModelPart[7];                 /* 0x007BE81E conf 0.95: String literal 'sprite' used during animated model part initialization in maybe_Gfx_ModelPart_InitAnimated. */
extern char g_strSpriteDualMesh[7];                  /* 0x007BE825 conf 0.95: String literal 'sprite' used during dual mesh initialization in maybe_Gfx_ModelPart_InitDualMesh. */
extern char g_strSpriteFieldGadget[7];               /* 0x007BE86B conf 0.95: String literal 'sprite' used in field gadget sprite grid setup in maybe_Field_Gadget_InitSpriteGridC. */
extern char g_strSprite2dTableA[7];                  /* 0x007BE872 conf 0.95: String literal 'sprite' used in 2D sprite table A initialization in Gfx_Sprite2D_InitFromTableA. */
extern char g_strSprite2dTableB[7];                  /* 0x007BE887 conf 0.95: String literal 'sprite' used in 2D sprite table B initialization in Gfx_Sprite2D_InitFromTableB. */
extern char g_strActionAnimEquip[6];                 /* 0x007BE88E conf 0.95: Fixed string literal 'equip' used to tag equipment-driven action animations in Battle_ActionAnimTable_Build. */
extern char g_strFormatBspa[8];                      /* 0x007BFB6A conf 0.95: Format string '%s.bspa' used for loading binary sprite animation asset packages in Gfx_Effect2D_CreateInstance. */
extern u32 g_projectWorldToScreenGuard;              /* 0x007C017C conf 0.90: Static initialization guard word passed to __cxa_guard_acquire in Gfx_ProjectWorldToScreen. */
extern f32 g_fxQuadVertexCoordBuffer[2];             /* 0x007C0180 conf 0.85: Particle quad vertex coordinate buffer pair accessed during quad assembly in Fx_BuildParticleRenderQuad. */
extern u32 g_fxParticleNodeAllocCount;               /* 0x007C0188 conf 0.85: Allocation counter or flag for particle node pool tracking in maybe_Fx_AllocParticleNode. */
extern u32 g_materialDrawTemplateGuard;              /* 0x007C018C conf 0.90: Static initialization guard word passed to __cxa_guard_acquire in Gfx_CmdBuf_EmitMaterialDraw. */
extern u8 g_emitterTransformsInitFlag;               /* 0x007C0190 conf 0.90: Static initialization guard flag for emitter transformation matrix templates in Fx_BuildEmitterTransforms. */
extern void* g_componentRegistryTable;               /* 0x007C3684 conf 0.85: Global component and object registry table searched by type identifier in Container_FindObjectByTypeId. */
extern void* g_sprite2DTableBInstanceList;           /* 0x007C466C conf 0.85: Global instance list head for 2D sprites created from table B in Gfx_Sprite2D_InitFromTableB. */
extern void* g_spriteActorPoolWork;                  /* 0x007C4810 conf 0.85: Global sprite actor allocation pool work buffer initialized in Gfx_SpriteActor_CreatePooled. */
extern u32 g_effectPackInfoClassRecord[5];           /* 0x007C5214 conf 0.85: BSS class-registration node and RTTI token (5 words) for EffectPackInfo; initialized in 0x006B3314 with handler pointers */
extern f32 g_effectBillboardUpVector[3];             /* 0x007C6EF8 conf 0.90: Reference up-vector (3 floats: X, Y, Z) used by Effect_UpdateBillboardOrientation (0x0039E374) to compute camera-facing  */
extern u32 g_movieCommandBuffer[6];                  /* 0x007C8038 conf 0.90: Command buffer/worker state (0x18 bytes) for asynchronous movie playback; submitted via Gfx_CommandBuffer_Submit in Gfx_ */
extern u32 g_movieTrackCriticalSection[3];           /* 0x007C8050 conf 0.95: Critical section (12 bytes) protecting movie track operations; initialized via Os_InitCriticalSection in Gfx_InitCommand */
extern u32 g_movieTrackBufferQueue[192];             /* 0x007C805C conf 0.95: 64-entry ring buffer (768 / 0x300 bytes) of movie buffer requests {track, data, size} indexed by ring head/tail (mask 0x */
extern u32 g_vramSubHeapD[22];                       /* 0x007C835C conf 0.90: VRAM sub-heap D allocator instance (0x58 bytes); configured in Gfx_InitVramBanks (0x001B6FAC) for VRAM bank allocation a */
extern u32 g_vramSubHeapB[22];                       /* 0x007C83B4 conf 0.90: VRAM sub-heap B allocator instance (0x58 bytes); configured in Gfx_InitVramBanks (0x001B6FAC) with 0x40000 bytes and use */
extern u32 g_vramSubHeapA[22];                       /* 0x007C840C conf 0.90: VRAM sub-heap A allocator instance (0x58 bytes); configured in Gfx_InitVramBanks (0x001B6FAC) with 0x80000 bytes and use */
extern u32 g_vramSubHeapC[22];                       /* 0x007C8464 conf 0.90: VRAM sub-heap C allocator instance (0x58 bytes); configured in Gfx_InitVramBanks (0x001B6FAC) with 0x8000 bytes and used */
extern u32 g_vramSubHeapE[22];                       /* 0x007C84BC conf 0.85: VRAM sub-heap E allocator instance (0x58 bytes); configured in Gfx_InitVramBanks (0x001B6FAC) with offset +0x388000 and  */
extern u32 g_vramSubHeapF[22];                       /* 0x007C8514 conf 0.85: VRAM sub-heap F allocator instance (0x58 bytes); configured in Gfx_InitVramBanks (0x001B6FAC) with offset +0x180000 and  */
extern u32 g_movieCommandPoolAllocator[22];          /* 0x007C856C conf 0.85: Movie command pool allocator instance (0x58 bytes); initialized in 0x00680C54 with vtable 0x0078104C and passed to Gfx_I */
extern u32 g_displayLayerLockCD[3];                  /* 0x007C865C conf 0.90: Critical section (12 bytes) synchronizing graphics display layer tables C and D (0x007C86E0, 0x007C86BC); initialized in */
extern u32 g_displayLayerLockAB[3];                  /* 0x007C8668 conf 0.90: Critical section (12 bytes) synchronizing graphics display layer tables A and B (0x007C8698, 0x007C8674); initialized in */
extern u32 g_displayLayerTableA[9];                  /* 0x007C8698 conf 0.90: Display layer state table A (36 bytes: active count followed by 4 pairs of {owner, value}); updated by maybe_Gfx_SetLaye */
extern u32 g_displayLayerTableD[9];                  /* 0x007C86BC conf 0.90: Display layer state table D (36 bytes: active count followed by 4 pairs of {owner, value}); updated by maybe_Gfx_SetLaye */
extern u32 g_displayLayerTableC[9];                  /* 0x007C86E0 conf 0.90: Display layer state table C (36 bytes: active count followed by 4 pairs of {owner, value}); updated by maybe_Gfx_SetLaye */
extern u8 g_displayDoubleBufferState[264];           /* 0x007CCAA8 conf 0.85: Display double-buffer state structure (264 / 0x108 bytes) initialized in Gfx_DisplayBuffer_InitState (0x0067BFD0); zeroe */
extern char g_peakDrawCostElementName[36];           /* 0x007CF300 conf 0.85: Name buffer (36 bytes) recording the model part or element name with the highest rendering draw cost, updated in Gfx_Sub */
extern u32 g_movieQueueCriticalSection[3];           /* 0x007CF360 conf 0.95: Critical section (12 bytes) synchronizing MovieFrameQueue operations; acquired and released via Os_LockMonitor / func_00 */
extern f32 g_overlayQuadDefaultRgb[3];               /* 0x007E2030 conf 0.90: Static default RGB color float vector (3 floats: R, G, B) in Gfx_Overlay_AddQuad (0x0055AEB8, guard 0x007AE608); loaded  */
extern u32 g_modelTextureBindingDesc[16];            /* 0x007E2080 conf 0.85: Static texture binding descriptor (64 bytes / 0x40) configured in Gfx_ModelInstance_BindTextureAndDraw (0x00568BB4) with */
extern u32 g_meshDrawPicaCommands[4];                /* 0x007E20C0 conf 0.85: PICA GPU register command packet (16 bytes / 4 words) emitted in Gfx_ModelInstance_WriteMeshCommands (0x005659E8) and Gf */
extern u32 g_meshChunkDefaultDrawTag[5];             /* 0x007E20D0 conf 0.85: Default mesh chunk draw tag / cull parameter structure (20 bytes / 5 words) passed to Gfx_MeshChunk_DrawStrips in Gfx_Ch */
extern u32 g_overlaySpriteTextureConfig[16];         /* 0x007E20E4 conf 0.85: GPU texture unit configuration block (64 bytes / 0x40) for 2D sprite quad overlay rendering; initialized under guard 0x0 */
extern u32 g_overlayTransitionTextureConfig[16];     /* 0x007E2124 conf 0.85: GPU texture unit configuration block (64 bytes / 0x40) for 2D sprite transition rendering; initialized under guard 0x007 */
extern u8 g_primaryGpuCommandBuffer[12288];          /* 0x007E4000 conf 0.95: Primary GPU command buffer (0x3000 / 12,288 bytes) registered by Gfx_InitializeCommandBuffers in Gfx_InitDisplay (0x0010 */
extern f32 maybe_g_spriteBufferClampMax;             /* 0x007E70BC conf 0.70: Float boundary clamp constant loaded in Gfx_Sprite_BuildBuffers (0x0058765C) when sprite coordinate exceeds approximatel */
extern f32 g_identityMatrix4x3[12];                  /* 0x007E7110 conf 0.95: Standard 4x3 identity transform matrix (48 bytes / 12 floats); copied by matrix copy function 0x00574428 in Gfx_ModelIns */
extern f32 g_modelDefaultInstanceBounds[8];          /* 0x007E7140 conf 0.90: Default 8-float bounding extent template (32 bytes / 0x20) copied into model instance fields (+0x30 and +0x50) in Gfx_Mo */
extern f32 g_defaultBoundingBox[6];                  /* 0x007E7204 conf 0.95: Default 6-float Axis-Aligned Bounding Box (AABB, 24 bytes: min XYZ, max XYZ) used as fallback in Gfx_Bounds_CalcTransfor */
extern u8 g_gpuCommandQueueManager[384];             /* 0x007E7780 conf 0.95: Primary GPU command queue and display driver context structure (384 / 0x180 bytes); manages submission queues (+0x9C/+0x */
extern void* g_commandSlotPool;                      /* 0x007E7AE0 conf 0.85: Command slot pool node buffer pointer initialized under guard 0x007AEA48 and allocated via maybe_Mem_PoolAllocNode in Gf */
extern u32 g_commandSlotPoolLock[3];                 /* 0x007E7BD0 conf 0.90: Critical section (12 bytes) synchronizing command slot pool node allocation in Gfx_GetCommandSlot (0x001118D4). */
extern u32 g_displayFrameBufferSet[12];              /* 0x007E7DE0 conf 0.90: Display framebuffer set structure (48 bytes) holding display handles and sync primitives; released by Gfx_FreeFrameBuffe */
extern u32 g_picaRegisterDefTable[891];              /* 0x007ECE7C conf 0.90: PICA GPU register metadata table (0xDEC / 3,564 bytes, 297 12-byte entries); populated in Gfx_InitRegisterTables (0x0010 */
extern u8 g_picaRegisterDirtyBits[496];              /* 0x007EDC68 conf 0.85: PICA GPU register dirty-bit and state mask table (496 / 0x1F0 bytes); checked and updated in Gfx_LoadDefaultState (0x001 */
extern u32 g_picaVertexAttrConfigTable[71];          /* 0x007EDE58 conf 0.85: PICA vertex attribute and shader configuration table (284 / 0x11C bytes) spanning 0x007EDE58..0x007EDF74; initialized in */
extern u32 g_picaShaderRegisterRemapA[6];            /* 0x007EDF74 conf 0.80: PICA GPU register remap / index mapping table A (24 bytes) spanning 0x007EDF74..0x007EDF8C; iterated against 0xBD entrie */
extern u32 g_picaShaderRegisterRemapB[6];            /* 0x007EDF8C conf 0.80: PICA GPU register remap / index mapping table B (24 bytes) spanning 0x007EDF8C..0x007EDFA4; iterated against 0xBD entrie */
extern u32 g_gpuSessionLock[3];                      /* 0x007EF0B0 conf 0.90: Critical section (12 bytes) protecting GPU session and drawing initialization in maybe_Gfx_InitDrawState (0x001135D0) an */
extern u32 g_displayModeCriticalSection[3];          /* 0x007EF0E8 conf 0.95: Critical section (12 bytes) protecting display mode transitions; initialized by Os_InitCriticalSection in Gfx_Initialize */
extern u32 g_gpuSharedMemoryBlockA[8];               /* 0x007EF0F4 conf 0.90: GPU shared memory mapping descriptor A (32 bytes) mapped to command buffer base offset 0x0000 in Gfx_InitializeCommandBu */
extern u32 g_gpuSharedMemoryBlockB[12];              /* 0x007EF114 conf 0.90: GPU shared memory mapping descriptor B mapped to command buffer base+0x2000 in Gfx_InitializeCommandBuffers (0x00107328) */
extern u32 g_frameRateBudgetParams[17];              /* 0x007F2644 conf 0.90: Frame rate and timing budget parameter block (68 bytes / 0x44) configured in maybe_Gfx_SetFrameTimeBudget (0x0010B9E0) w */
extern u32 g_gpuWorkerThreadSync[60];                /* 0x007F2A58 conf 0.85: Exclusive-access synchronization state / worker thread context at 0x007F2A58 passed to Os_CreateThreadWithStack in Gfx_O */
extern u32 g_gpuChannelState[16];                    /* 0x007F2B48 conf 0.85: GPU channel status descriptor (64 bytes / 0x40) initialized in Gfx_OpenGpuChannel (0x0010BB34) with active flag at +10 a */
extern u32 g_displayTransferSharedMemory[8];         /* 0x007F2DE0 conf 0.85: Shared memory mapping descriptor (32 bytes / 0x20) mapped via Os_MapSharedMemory in 0x00122200 and closed via Os_CloseHa */
extern u8 g_charShadowPassBuffer[32];                /* 0x00834020 conf 0.85: 16-byte-aligned memory buffer (32 bytes) for the character shadow pass render state object; aligned and constructed unde */
extern u8 g_gfxRenderContextBuffer[520];             /* 0x00834084 conf 0.90: 16-byte-aligned memory buffer (520 / 0x208 bytes) for the primary GfxRenderContext singleton (size 0x1F8); constructed i */
extern u8 g_overlayBatchSingletonBuffer[320];        /* 0x008384A0 conf 0.90: Memory buffer (320 / 0x140 bytes) for the 2D overlay quad batch singleton (vtable 0x00782AFC); initialized under guard 0 */
extern f32 g_fxParticleDefaultVelocity[3];           /* 0x008386F0 conf 0.85: Static default 3D velocity vector (12 bytes / 3 floats) copied into particle node fields (+0x13..+0x15) in maybe_Fx_Allo */
extern f32 g_fxDefaultTransformMatrix[12];           /* 0x008386FC conf 0.90: Default 4x3 transform matrix (48 bytes / 12 floats) initialized under guard 0x007C018C; copied into emitter transforms i */
extern f32 g_identityMatrix4x4[16];                  /* 0x0083872C conf 0.95: Standard 4x4 identity matrix (64 bytes / 16 floats); copied via 16-float VFP load/store helper 0x00125560 (vldmia/vstmia */

/* --- Hid --- */
extern u8 g_hidDisableSelectRemap;                   /* 0x007AEA72 conf 0.85: Configuration flag in .data controlling SELECT button behavior: when 0 (default), SELECT button inputs (bit 0x04) are au */
extern u8 g_camSleepCameraState[8];                  /* 0x007AF0DC conf 0.85: 8-byte CTR-SDK camera sleep state record in .data: byte +0 holds the combined camera status mask from cam:GetSleepCamera */

/* --- InitBss --- */
extern u32 g_bssEnd;                                 /* 0x008398E4 conf 1.00: Linker boundary symbol marking the upper limit of the zero-initialized BSS segment in RAM; InitBss (0x00100024) clears m */

/* --- Input --- */
extern u32 g_hidPadButtonMasks[24];                  /* 0x007354FC conf 0.90: Table of 24 32-bit hardware button masks for standard 3DS buttons (indices 0..15) and extended Circle Pad Pro / New 3DS  */
extern u32 g_padDeviceInitGuard;                     /* 0x007AE728 conf 0.90: Call-once static initialization guard (__cxa_guard) in .data for the global circle pad input device object at 0x007E3058 */
extern u32 g_buttonSnapshotInitGuard;                /* 0x007AE72C conf 0.90: Call-once static initialization guard (__cxa_guard) in .data for the global button and touch snapshot state record at 0x */
extern u32 g_buttonMappingTable[19];                 /* 0x007AEB04 conf 0.90: Mapping table of 19 32-bit button masks used by Input_UpdateButtonMasks to translate input snapshot states into engine b */
extern u8 g_globalTouchState[24];                    /* 0x007E3040 conf 0.85: Global 24-byte touch panel and button snapshot state record in .bss. Constructed in Input_Initialize under guard g_butto */
extern u8 g_globalPadSnapshot[160];                  /* 0x007E3058 conf 0.85: Global pad and analog stick snapshot object in .bss. Constructed in Input_Initialize under guard g_padDeviceInitGuard wi */
extern u8 g_rawTouchSampleBuffer[12];                /* 0x007F25CC conf 0.85: Raw 12-byte touch panel hardware sample buffer in .bss. Populated by service query 0x001148F0 in Input_ReadTouchState wi */

/* --- IsSavePointGoddess --- */
extern u32 g_savePointGoddess3DClassRecord[5];       /* 0x007C44A0 conf 0.85: BSS class-registration record and RTTI token for 3D Goddess Statue save points (SavePointGoddess3D); checked in IsSavePo */
extern u32 g_savePointGoddess2DClassRecord[5];       /* 0x007C49DC conf 0.85: BSS class-registration record and RTTI token for 2D Goddess Statue save points (SavePointGoddess2D); checked in IsSavePo */

/* --- Item --- */
extern u32 g_craftIngredientWorkingTableInit[10];    /* 0x0072A248 conf 0.85: Initial template array of 5 item slots ({u16 itemId = 0xFFFF, u16 pad = 0, u32 count = 0}) copied to the stack in Item_C */
extern void* g_uiItemPanelConditionRowVtable[12];    /* 0x0075D390 conf 0.85: Vtable for item view presenter row for condition/status effect items; slot 3 is Ui_ItemPanel_RefreshFromConditions (0x00 */
extern void* g_uiEquipRowUpdateVtable[12];           /* 0x007614F8 conf 0.85: Vtable for equipment row presenter; slot 3 is Ui_EquipRow_Update (0x002EB3B4) and slot 0 is dtor 0x002EB618. */
extern void* g_uiStatusMaxHpRowVtable[12];           /* 0x00764574 conf 0.90: Vtable for the equipment status comparison presenter for Max HP; slot 4 calls Ui_Status_ShowMaxHp (0x006E3364) and slot  */
extern void* g_uiStatusMaxMpRowVtable[12];           /* 0x007645B4 conf 0.90: Vtable for the equipment status comparison presenter for Max MP; slot 4 calls Ui_Status_ShowMaxMp (0x006E3544) and slot  */
extern void* g_uiStatusAgilityRowVtable[12];         /* 0x007645F4 conf 0.90: Vtable for the equipment status comparison presenter for Agility; slot 4 calls Ui_Status_ShowAgility (0x006E3724) and sl */
extern void* g_uiStatusDeftnessRowVtable[12];        /* 0x00764634 conf 0.90: Vtable for the equipment status comparison presenter for Deftness; slot 4 calls Ui_Status_ShowDeftness (0x006E3904) and  */
extern void* g_uiStatusDefenceRowVtable[12];         /* 0x00764674 conf 0.90: Vtable for the equipment status comparison presenter for Defence; slot 4 calls Ui_Status_ShowDefence (0x006E3AE0) and sl */
extern void* g_uiStatusStrengthRowVtable[12];        /* 0x007646B4 conf 0.90: Vtable for the equipment status comparison presenter for Strength / Attack; slot 4 calls Ui_Status_ShowStrength (0x006E3 */
extern void* g_uiStatusAttackMagicRowVtable[12];     /* 0x007646F4 conf 0.90: Vtable for the equipment status comparison presenter for Attack Magic; slot 4 calls Ui_Status_ShowAttackMagic (0x006E3EA */
extern void* g_uiStatusCharmRowVtable[12];           /* 0x00764734 conf 0.90: Vtable for the equipment status comparison presenter for Charm; slot 4 calls Ui_Status_ShowCharm (0x006E4080) and slot 0 */
extern void* g_uiStatusRecoveryMagicRowVtable[12];   /* 0x00764774 conf 0.90: Vtable for the equipment status comparison presenter for Recovery Magic; slot 4 calls Ui_Status_ShowRecoveryMagic (0x006 */
extern void* g_uiStatusSkillPointsRowVtable[12];     /* 0x007647B4 conf 0.90: Vtable for the equipment status comparison presenter for Skill Points; slot 4 calls Ui_Status_ShowSkillPoints (0x006E444 */
extern void* g_uiEquipFieldCommandRowVtable[12];     /* 0x007671F8 conf 0.80: Vtable for equipment menu field command presenter; slot 3 calls 0x0039A6B8 and slot 0 is dtor 0x0039A9E8. */
extern void* g_uiEquipRowRefreshVtable[12];          /* 0x0076A290 conf 0.85: Vtable for equipment row refresh presenter; slot 3 is Ui_EquipRow_Refresh (0x003D628C) and slot 0 is dtor 0x003D6440. */
extern void* g_uiEquipDetailScrollVtableA[12];       /* 0x0076A2D0 conf 0.85: Vtable for equipment item detail scrolling presenter variant A; slot 4 is maybe_Ui_EquipmentDetail_ScrollNameA (0x003D64 */
extern void* g_uiEquipWindowCloseAltRowVtable[12];   /* 0x0076A310 conf 0.85: Vtable for equipment window close/teardown presenter; slot 3 is Ui_EquipmentWindow_CloseAlt (0x003D66C4) and slot 0 is d */
extern void* g_uiEquipDetailScrollVtableB[12];       /* 0x0076A350 conf 0.85: Vtable for equipment item detail scrolling presenter variant B; slot 4 is maybe_Ui_EquipmentDetail_ScrollNameB (0x003D67 */
extern void* g_uiEquipWindowItemPageRowVtable[12];   /* 0x0076D4AC conf 0.85: Vtable for equipment window item page navigation presenter; slot 3 is Ui_EquipmentWindow_OpenItemPage (0x00408A70) and s */
extern void* g_uiEquipWindowMemberPageRowVtable[12]; /* 0x0076D4EC conf 0.85: Vtable for equipment window party member page navigation presenter; slot 3 is Ui_EquipmentWindow_OpenPageForMember (0x00 */
extern void* g_uiEquipWindowItemDetailsRowVtable[12]; /* 0x00770164 conf 0.85: Vtable for equipment window item details view presenter; slot 4 is Ui_EquipmentWindow_OpenItemDetails (0x00447EA4) and s */
extern void* g_uiEquipWindowStatusUpdateRowVtable[12]; /* 0x007701A4 conf 0.85: Vtable for equipment window status update presenter; slot 3 is Ui_EquipmentWindow_UpdateEquipStatus (0x00448030) and slo */
extern void* maybe_g_uiEquipMessageWindowRowVtableA[12]; /* 0x00773078 conf 0.45: Tentative vtable for equipment message window presenter variant A; slot 3 is 0x0046CC5C and slot 0 is dtor 0x0046CDE8. */
extern void* maybe_g_uiEquipMessageWindowRowVtableB[12]; /* 0x007730B8 conf 0.45: Tentative vtable for equipment message window presenter variant B; slot 3 is 0x0046CE28 and slot 0 is dtor 0x0046CF50. */
extern void* maybe_g_uiEquipMessageEntryRowVtable[12]; /* 0x0077548C conf 0.45: Tentative vtable for equipment message entry presenter; slot 4 is 0x004A34A0 and slot 0 is dtor 0x004A35C4. */
extern void* g_uiEquipPartyListDeltaRowVtable[12];   /* 0x007761C8 conf 0.85: Vtable for equipment party member delta presenter (used for shield/dual-wield weapons); slot 3 is Ui_PartyListWindow_Upd */
extern void* g_uiEquipMemberValueGainRowVtable[12];  /* 0x00777F54 conf 0.85: Vtable for equipment party member stat gain presenter; slot 4 is 0x004C4868 (value gain display) and slot 0 is dtor 0x00 */
extern void* g_uiEquipMemberValueChangeRowVtable[12]; /* 0x00779D8C conf 0.85: Vtable for equipment party member stat change presenter; slot 4 is 0x004D64F8 (value change display) and slot 0 is dtor  */
extern void* g_uiEquipActorStateInterfaceVtable[8];  /* 0x00780634 conf 0.70: Secondary component interface vtable embedded at offset +0x18 in case 0x2b equipment view presenter; slot 0 is 0x0032F1F */
extern u32 g_itemTextColorTable[14];                 /* 0x007A94C4 conf 0.85: Item name text color code palette in .data; offset +1 holds default/owned RGBA color (0xFFFFFFFF) and offset +9 holds un */
extern u32 g_itemCategoryTextColorTable[14];         /* 0x007AAF18 conf 0.85: Item category label RGBA text color table in .data; offset 0 is default/unlocked color (0xFFFFFFFF) and offset +8 is loc */

/* --- LoadDiveMapJump --- */
extern u32 g_gmDiveMapJump2DClassRecord[5];          /* 0x007C53A8 conf 0.85: BSS class-registration record for 2D dive map jump actors (GmDiveMapJump2D): sits between g_gmDiveItemBox2DClassRecord ( */

/* --- Map --- */
extern u32 g_mapCellOccupancyFilterTable[4];         /* 0x00726A00 conf 0.75: Table of two 8-byte filter descriptors {filterFunc, flags} used by Map_FindCellInDirectionEx (0x002D7F20) to filter cand */
extern void* g_fieldMarkerWarpVtable[5];             /* 0x00778264 conf 0.75: Vtable (5 slots) for 2D field warp marker node objects (0x18 bytes) allocated by Effect2DWarp (0x001496BC) and linked in */
extern s32 g_invalidMapRecordId[2];                  /* 0x007A8A40 conf 0.80: Pair of 32-bit sentinel values initialized to -1 (0xFFFFFFFF) at 0x00679328. Word 1 (+0x4) represents the invalid/unassi */
extern u32 g_mapInstanceHandleConfig[2];             /* 0x007A8B40 conf 0.80: Pair of 32-bit values {handleWrapLimit, invalidHandle} (size 8 bytes) for map instance handle allocation. Read by Map_Ad */

/* --- Math --- */
extern void* g_enemyAnim2dPackPathDesc[8];           /* 0x0072D74C conf 0.85: 8-word descriptor in .rodata for 2D enemy battle animation pack archives: word +0 is zero/type tag, word +1 (offset +0x0 */
extern f32 g_transitionDuration;                     /* 0x007A6E90 conf 0.80: Global single-precision float in .data representing the time duration / scale divisor for normalized unit ratio calculat */
extern void* g_animCurveDispatchTable[48];           /* 0x007AE7C8 conf 0.95: 2D function-pointer dispatch table in .data (6 curve types x 8 interpolation modes, 48 entries / 0xC0 bytes) for animati */
extern f32 g_defaultBoundingSphere[4];               /* 0x007E71BC conf 0.95: Default 4-float bounding sphere template in .bss (16 bytes / 4 floats: center x, y, z = 0.0f, radius = 0.0f): copied as  */

/* --- Mem --- */
extern void* g_recordArrayVtable[1];                 /* 0x0075868C conf 0.85: Virtual method table for dynamic record array (RecordArray) whose slot 0 is virtual destructor Mem_FreeRecordArray (0x00 */
extern void* g_renderObjectPoolVtable[8];            /* 0x0075F958 conf 0.85: Virtual method table for pooled render object allocated by maybe_Mem_CreatePoolObject (0x00162278): slot 0 queries RTTI  */
extern void* g_fxSystemVtable[3];                    /* 0x0078122C conf 0.95: Virtual method table for the effect system singleton (Fx_System): slot 0 is the destructor/shutdown routine Fx_System_Sh */
extern u32 g_frameCallbackLightEvent[2];             /* 0x007AE4A0 conf 0.90: CTR-SDK nn::os::LightEvent synchronization object (8 bytes: state at +0x00 and LightLock at +0x04) used for engine frame */
extern u32 g_sharedBlockLock;                        /* 0x007AE920 conf 0.85: Synchronization spinlock for shared-memory block mapping in Mem_MapSharedBlock (0x00107B54): reset atomically by func_00 */
extern u32 g_committedFreeRegion[2];                 /* 0x007AEA7C conf 0.95: Two-word descriptor (8 bytes) of the committed free memory region: word +0 is the base virtual address, and word +4 is t */
extern u8 g_isBlockRegistryInitialized;              /* 0x007B006C conf 0.90: One-shot initialization guard flag for the global memory block registry: when 0 (default), maybe_Mem_BlockRegistry_Inser */
extern void* g_defaultHeap;                          /* 0x007B0078 conf 0.90: Pointer to the default general heap object used by Mem_Alloc (0x002FF628) as the engine-wide malloc backing store; locke */
extern u32 g_handleNextSlotHint;                     /* 0x007B5D68 conf 0.90: Search cursor / slot allocation hint for the 512-entry handle table: holds the next slot index (masked with 0x1FF) to te */
extern u32 g_handleGenerationCounter;                /* 0x007B5D6C conf 0.90: Monotonic generation counter for 32-bit object handles: incremented on every handle allocation in Mem_AllocHandle (0x003 */
extern u32 g_mainHeapListNode[4];                    /* 0x007E790C conf 0.85: Intrusive circular list node descriptor (16 bytes: next, prev, data, and key=0x100 at +0x0C) for the application main he */
extern u32 g_memBlockRegistryRoot[3];                /* 0x007F25C0 conf 0.90: Root intrusive doubly-linked list header (12 bytes: head at +0x00, tail at +0x04, count at +0x08, node offset at +0x0A)  */
extern u32 g_linearHeapRangeAllocator[6];            /* 0x007F2B88 conf 0.95: Range allocator / bump descriptor (24 bytes: base address at +0x00, limit at +0x04, and critical section at +0x0C) for t */

/* --- Menu --- */
extern u16 g_menuEntryFallbackActorIds[18];          /* 0x00726A30 conf 0.85: Table of candidate actor IDs (3 slots of 6 priority u16 IDs) checked by Menu_ResolveSelectedEntryActors (0x0020605C) via */
extern char* g_menuInitAnimNames[3];                 /* 0x00726E98 conf 0.90: Array of 3 animation name string pointers ("c1", "c2", "c3") randomly chosen (0..2) in Menu_InitFromParams (0x0020713C)  */
extern u32 g_uiCampSelectCallbackTable[24];          /* 0x007291F0 conf 0.90: Camp selection menu callback table: 12 8-byte delegate entries (6 action callbacks + 6 state transition handlers) indexe */
extern char* g_horseRacePlayerIconNames[7];          /* 0x0072B330 conf 0.95: Array of 7 string pointers to horse race contestant UI icon names ("icon_player_red" .. "icon_player_pink") iterated in  */
extern void* g_uiCampSelectWindowVtable[23];         /* 0x0075B78C conf 0.90: Vtable for camp selection window (Ui_CampSelectWindow, 23 virtual method slots); slot 0 is Ui_CampSelectWindow_DeletingD */
extern void* g_uiItemSelectWindowVtable[23];         /* 0x0075BA3C conf 0.90: Vtable for item selection window (Ui_ItemSelectWindow, 23 virtual method slots); installed in Menu_ItemSelect_CreateWind */
extern void* g_uiItemSelectRowPresenterVtable[10];   /* 0x0075BAA0 conf 0.85: Vtable for item selection row and emotion layout presenter (10 virtual method slots); slot 0 is dtor 0x002155A4, slot 4  */
extern void* g_uiCampGestureLayoutVtable[11];        /* 0x0075BB34 conf 0.85: Vtable for camp dialogue gesture animation controller (11 virtual method slots); slot 1 is dtor 0x00215B10, slot 2 is Me */
extern void* maybe_g_uiItemBoxWindowVtable[23];      /* 0x00762760 conf 0.45: Vtable for item box / list window subclass (23 virtual method slots); installed in maybe_Menu_ItemBox_Ctor (0x002FCC44)  */
extern void* g_uiPokerWindowVtable[23];              /* 0x00762BB8 conf 0.90: Vtable for casino poker minigame window (Ui_PokerWindow, 23 virtual method slots); slot 0 is dtor 0x00304800, slot 8 is  */
extern void* g_rouletteIconModelVtable[1];           /* 0x00762E44 conf 0.85: Vtable for casino roulette 3D icon/model presenter with virtual destructor Menu_IconModel_Delete (0x0030CD90) at slot 0. */
extern u16 g_menuTargetSelectEndBanner[37];          /* 0x0078C6FC conf 0.95: Wide-string debug banner (L"/////////////ターゲット選択終了///////////// ", 37 UTF-16LE characters) printed at the completion of  */
extern u16 g_menuTargetSelectStartBanner[39];        /* 0x0078C748 conf 0.95: Wide-string debug banner (L"/////////////ターゲット選択スタート///////////// ", 39 UTF-16LE characters) printed at the start of tar */
extern s32 g_menuDebugEquipStatSlotOverride;         /* 0x007A40B4 conf 0.85: Debug override slot ID checked in maybe_Menu_CalcEquipStatValues (0x002004AC); if not -1, forces target slot self->f_44c */
extern s32 g_menuDebugRecipeRowOverride;             /* 0x007A40B8 conf 0.85: Debug override recipe row index checked in Menu_SelectRecipeRow (0x00202C38); if not -1, overrides row index written to  */
extern s32 g_menuDebugEquipCandidateOverride;        /* 0x007A40BC conf 0.85: Debug override candidate index checked in maybe_Menu_CalcEquipStatValues (0x002004AC); if not -1, overrides self->f_44c  */
extern s32 g_menuDebugEntryActionOverride;           /* 0x007A40C0 conf 0.85: Debug override return code for entry action dispatch checked in maybe_Menu_DispatchEntryAction (0x00202F28); if not -1,  */
extern u32 g_menuDefaultStateParam;                  /* 0x007A5918 conf 0.80: Default 32-bit configuration parameter copied into menu state (+0x41F8) in Menu_InitFromParams (0x0020713C). */
extern u32 g_menuActorAnimParamBlock[4];             /* 0x007A5B9C conf 0.80: Actor UI animation parameter block; offset +0xC is loaded in maybe_Menu_Actor_PlayUiAnimation (0x0020A9B8) and passed to */
extern char* g_talkPartyActorModelCodes[54];         /* 0x007A763C conf 0.95: Table of 54 string pointers to party talk character model and costume prefix codes ("a010" .. "y010") indexed by charact */
extern char* g_menuEmotionAnimNames[10];             /* 0x007A8A88 conf 0.95: Array of 10 string pointers ("emotion1" .. "emotion10") bound to UI emotion animation panes in maybe_Menu_ItemSelect_Cre */
extern char* g_menuEmotionCharaPaneNames[5];         /* 0x007A8AB0 conf 0.95: Array of 5 string pointers ("null_hud_emotion_chara1" .. "null_hud_emotion_chara5") bound to character emotion HUD layou */
extern u32 g_uiTextColorPaletteTable[16];            /* 0x007A8D7C conf 0.90: UI text RGBA color palette table initialized in 0x0067A06C; color entry at +8 (0x007A8D84) is read in Menu_StartLayoutAn */
extern char g_strSprite[7];                          /* 0x007BE7A7 conf 0.95: Constant C-string "sprite" used by maybe_TalkParty_ApplyMessageParams (0x00218B00) to initialize a std::FixedString15 pa */
extern u32 g_playerJockeyActor3DClassRecord[5];      /* 0x007C4D38 conf 0.90: BSS class registration node and RTTI token (5 words) for PlayerJockeyActor3D; registered in 0x006AA5B8 and tested via vi */

/* --- MessageWindow --- */
extern f32 g_messageDefaultTextSpeed;                /* 0x007AC424 conf 0.90: Default message typewriter text speed (40.0f glyphs/sec); dynamically copied to message buffer/window field +0x408 in Ui */

/* --- MoLive --- */
extern char g_moLiveErrDuplicateStreamFormat[74];    /* 0x00735194 conf 0.95: Format string for duplicate stream error logged in MoLive_Reader_DecodePacket: 'Found stream index %d but this stream is */
extern char g_moLiveFixedPacketSizeErrorFormat[98];  /* 0x007351E0 conf 0.95: Format string for fixed-size packet mismatch error logged in MoLive_Reader_Process: 'error: synchronized fixe packet siz */
extern char g_moLiveVariablePacketSizeErrorFormat[101]; /* 0x00735244 conf 0.95: Format string for variable packet size overflow error logged in MoLive_Reader_Process: 'error: synchronized variable pac */
extern void* g_moLiveSourceAdapterVtable[9];         /* 0x0075FA28 conf 0.85: Virtual method table for the MoLive stream data source adapter installed at reader+0x14C0 in MoLive_Decoder_Create; forw */
extern void* g_moLiveAllocatorVtable[3];             /* 0x00773868 conf 0.90: Virtual method table for the MoLive allocator adapter instance created by MoLive_Decoder_Create; delegates allocations a */
extern void* g_moLiveDecoderFilterAVtable[9];        /* 0x00784228 conf 0.85: Virtual method table for MoLive stream decoder filter node variant A (type 2, subtype 6); installed on 0x24-byte filter  */
extern void* g_moLiveDecoderFilterBVtable[9];        /* 0x0078424C conf 0.85: Virtual method table for MoLive stream decoder filter node variant B (type 1, subtype 0xC); installed on 0x24-byte filte */
extern void* g_moLiveDecoderFilterCVtable[9];        /* 0x00784270 conf 0.85: Virtual method table for MoLive stream decoder filter node variant C (type 4, subtype 2); installed on 0x1C-byte filter  */
extern void* g_moLiveDecoderFilterDVtable[9];        /* 0x00784294 conf 0.85: Virtual method table for MoLive stream decoder filter node variant D (type 3, subtype 0xD); installed on 0x30-byte filte */

/* --- Model --- */
extern f32 g_actorModelVisualFactorLarge;            /* 0x00725370 conf 0.65: Float constant 0.6f (0x3F19999A) assigned to actor->f_1cc in maybe_Actor_UpdateActionState (0x0022D8D4) and maybe_Model_ */
extern f32 g_actorModelVisualFactorMedium;           /* 0x00725374 conf 0.65: Float constant 0.4f (0x3ECCCCCD) assigned to actor->f_1cc in maybe_Actor_UpdateActionState (0x0022D8D4) and maybe_Model_ */
extern char* g_modelAimDirectionSuffixes[8];         /* 0x00725438 conf 0.90: Array of 8 direction suffix strings ('u', 'd', 'l', 'ul', 'dl', 'r', 'ur', 'dr') used by Model_AttachAimParts to constru */
extern s16 g_actorStateEffectIds[2];                 /* 0x00726750 conf 0.85: Array of 2 effect IDs indexed by actor state index (0 and 1); entry 0 is -1 (no effect) and entry 1 is 1202 (0x04B2), us */
extern u8 g_colorVariantIndexMap[3];                 /* 0x00727397 conf 0.70: 3-byte translation table mapping random weighted outcome indices (0, 1, 2) to variant/slot values (0, 2, 3), used by Ui_ */
extern void* g_modelAccessoryCallbackDesc[2];        /* 0x00728548 conf 0.65: 8-byte callback descriptor {func, context} ({0x00313C88, NULL}) installed into attachment context (+0x20/+0x24) by maybe */
extern f32 g_modelFaceBlinkKeyframeTimes[8];         /* 0x0072F468 conf 0.85: Array of 8 float parameters (keyframe frame thresholds 0.0f, 8.0f, 16.0f, 24.0f and animation targets 0.0f, 120.0f, 80.0 */
extern u32 g_modelSecondaryMotionParamDescriptors[21]; /* 0x0072F49C conf 0.90: Table of 7 secondary-motion attribute descriptors (each 3 words: suffix string pointer, type flag, min-parameter count)  */
extern void* g_skillAnimCtrlCat2Sub4Vtable[5];       /* 0x0075C9CC conf 0.75: 5-slot virtual method table (deleting destructor 0x00257804, execute method 0x00257704, and evaluate method 0x00257780)  */
extern void* g_skillAnimCtrlCat2Sub6Vtable[5];       /* 0x00760534 conf 0.75: 5-slot virtual method table (deleting destructor 0x002D0738, execute method 0x002D04EC, shared stubs 0x001C2DCC/0x001C2D */
extern void* g_modelObjectVtable[26];                /* 0x00764ABC conf 0.90: 26-slot virtual method table for Model_Object / Field_SceneObject, containing destructors (0x00336B3C / 0x00336AB8), mes */
extern void* g_skillAnimCtrlCat2Sub5Vtable[5];       /* 0x00766120 conf 0.75: 5-slot virtual method table (deleting destructor 0x00381EB0, execute method 0x00381D3C, shared stubs 0x001C2DCC/0x001C2D */
extern void* g_skillAnimCtrlCat2Sub3Vtable[5];       /* 0x0076613C conf 0.75: 5-slot virtual method table (deleting destructor 0x00381FE4, execute method 0x00381ED8, shared stubs 0x001C2DCC/0x001C2D */
extern void* g_meshSheathEquipVtable[15];            /* 0x0076B710 conf 0.95: 15-slot virtual method table installed into sheath equipment mesh objects (named 'meshSheathEquip') for equipment slots  */
extern void* g_skillAnimCtrlCat0WeaponVtable[5];     /* 0x0076B9AC conf 0.75: 5-slot virtual method table (deleting destructor 0x003F0E88, execute method 0x003F0CEC, and method 0x003F0D54) for skill */
extern void* g_meshWeaponEquipVtable[15];            /* 0x0076BC74 conf 0.95: 15-slot virtual method table installed into weapon equipment mesh objects (named 'meshWeaponEquip') for equipment slots  */
extern void* g_battleActionModelType74Vtable[48];    /* 0x0076C5F0 conf 0.85: 48-slot virtual method table for the type-0x74 battle action model subclass (slots 1/2: Battle_ActionModel_Dtor 0x00401A */
extern void* g_skillAnimCtrlCat6AndCat2Sub2Vtable[5]; /* 0x00771CF0 conf 0.75: 5-slot virtual method table (deleting destructor 0x0045FF78, execute method 0x0045FDB8, and method 0x0045FE20) for skill */
extern void* g_skillAnimCtrlCat5Sub6Vtable[5];       /* 0x00775964 conf 0.75: 5-slot virtual method table (deleting destructor 0x004A6FE8, execute method 0x004A6E74, and method 0x004A6EDC) for skill */
extern void* g_skillAnimCtrlCat0DefaultVtable[5];    /* 0x00776D68 conf 0.75: 5-slot virtual method table (deleting destructor 0x004B5BC8, execute method 0x004B5A6C, shared stubs 0x001C2DCC/0x001C2D */
extern void* g_characterModelNodeListVtable[5];      /* 0x00782070 conf 0.80: 5-slot virtual method table (deleting destructor 0x0055AC5C at slot 1, list unlink 0x0055AD04 at slot 4) for character m */
extern void* g_modelNodeSubclass782140Vtable[5];     /* 0x00782140 conf 0.65: 5-slot virtual method table (deleting destructor 0x00664718 at slot 0, node methods 0x0055AEA8/0x0055AE38/0x0055AE3C at  */
extern void* g_modelNodeSubclass78217CVtable[5];     /* 0x0078217C conf 0.65: 5-slot virtual method table (deleting destructor 0x00664724 at slot 0, list methods 0x0055E270/0x0055E254/0x0055E260 at  */
extern void* g_modelSecondaryMotionVtable[3];        /* 0x007821FC conf 0.90: 3-slot virtual method table for secondary motion simulation objects (slot 1: Model_SecondaryMotion_Destroy 0x005631D8, s */
extern void* g_gfxMaterialSetSecondaryVtable[11];    /* 0x00782244 conf 0.90: 11-slot secondary virtual method table for Gfx_MaterialSet (slot 0: Gfx_MaterialSet_Dtor 0x0056427C; pure virtual method */
extern void* g_modelTransformNodeVtable[5];          /* 0x00783470 conf 0.70: 5-slot virtual method table (deleting destructor 0x00666AA0 at slot 0, evaluation methods 0x005A79C0/0x005A7950/0x005A79 */
extern void* g_modelNodeTransformEvalDispatchTable[32]; /* 0x007A2EE8 conf 0.90: Jump table of 32 function pointers for model node transform evaluation, indexed by node type *(u16*)(self->f_34 + 8) and */
extern u32 g_modelFaceBlinkDefaultInterval;          /* 0x007A3514 conf 0.85: Default/fallback blink interval frame count stored into face state +0x10 by maybe_Model_UpdateBlinkTimer (0x001D5C94). */
extern u32 g_modelFaceModeIntervalMultiplier;        /* 0x007A3518 conf 0.85: Frame multiplier multiplied by (rand % 3 + 2) to set face animation timer (+0x20) in Model_SetupFaceParams, maybe_Model_ */
extern u8 maybe_g_modelUpdateNamedNodeFlag;          /* 0x007A3F7D conf 0.40: Byte flag at 0x007A3F7D checked by maybe_Model_UpdateNamedNodeAndId (0x0023018C) to guard calling func_003F422C on model */
extern u32 g_weaponAttachmentDefaultFlags;           /* 0x007ABB9C conf 0.65: Default 32-bit value copied into weapon attachment object +0x88 by Model_Attach_CreateWeaponAttachment (0x0064EA10). */
extern void* g_modelLookAtHeadAimConfig[4];          /* 0x007AE680 conf 0.90: 4-word look-at configuration block (+0: 'HeadAim', +4: 'Spine02Aim', +8: yaw divisor, +0xC: pitch divisor) used by Model */
extern char* g_modelSecondaryMotionSwingPrefix;      /* 0x007AE6E8 conf 0.95: Pointer to string literal '$Swing' (at 0x00789E30), used as prefix by maybe_Model_SecondaryMotion_BuildChains to identif */
extern char g_modelRootBoneName_N_ALL[6];            /* 0x007BFBCE conf 0.95: String literal 'N_ALL' naming the root/all-bone attachment node, used by Model_Equip_AttachItemNode (0x0040A6B8) and Mod */
extern char g_modelDefaultEmptyString[1];            /* 0x007C2621 conf 0.95: Empty string literal (\0) at 0x007C2621 used as fallback name string in maybe_Model_ApplyResourceAppearance, maybe_Model */
extern char g_modelAttachBoneLWeapon[36];            /* 0x007C50B4 conf 0.95: std_FixedString31 object holding 'L_Weapon' (left-hand weapon attachment bone name), initialized by Model_Attach_InitPoi */
extern char g_modelAttachBoneRWeapon[36];            /* 0x007C50D8 conf 0.95: std_FixedString31 object holding 'R_Weapon' (right-hand weapon attachment bone name), initialized by Model_Attach_InitPo */
extern char g_modelAttachBoneShield[36];             /* 0x007C50FC conf 0.95: std_FixedString31 object holding 'Shield' (shield/off-hand attachment bone name), initialized by Model_Attach_InitPointN */
extern char g_modelAttachBoneShieldName[32];         /* 0x007C5100 conf 0.95: 32-byte string buffer at offset +4 of g_modelAttachBoneShield (0x007C50FC) holding 'Shield', copied directly by Model_Eq */
extern f32 g_vector4SecondaryMotionOpposite[4];      /* 0x007E70AC conf 0.75: Constant four-float vector (4 words at 0x007E70AC) used in Model_SimulateSecondaryMotion as fallback quaternion/vector w */
extern f32 g_mathMatrix3x3Identity[9];               /* 0x007E70EC conf 0.95: 3x3 identity matrix (9 floats: row-major 1,0,0, 0,1,0, 0,0,1) used as default/fallback rotation by Math_MatrixInverse (0 */

/* --- Monster --- */
extern u32 g_monsterVariantFieldOffsets[3];          /* 0x007273A4 conf 0.85: Array of three field offsets (+0x24, +0x26, +0x28) within MonsterRecord, indexing u16 monster IDs of related or variant  */
extern void* g_stdStateSequence04Vtable[7];          /* 0x0075AC9C conf 0.90: Virtual method table for std_StateSequence04 state machine used for monster ecology behaviors; contains deleting destruc */
extern void* g_stdStateSequence12Vtable[7];          /* 0x0075ADBC conf 0.90: Virtual method table for std_StateSequence12 state machine used for monster AI variant behaviors; contains deleting dest */
extern void* g_stdStateSequence15Vtable[7];          /* 0x0075AE28 conf 0.90: Virtual method table for std_StateSequence15 state machine used in monster behavior action sequencing; contains deleting */
extern void* g_stdStateSequence31Vtable[7];          /* 0x0075B068 conf 0.90: Virtual method table for std_StateSequence31 state machine driving monster field actions; contains deleting destructor ( */
extern void* g_stdStateSequence35Vtable[7];          /* 0x0075B0F8 conf 0.90: Virtual method table for std_StateSequence35 state machine controlling specialized monster actions; contains deleting de */
extern void* g_monsterAiAnimVtable[13];              /* 0x0075D3F8 conf 0.85: Virtual method table for Ui_Anim sprite animation node installed on monster AI behavior instances; slot 0 is Ui_AnimSpri */
extern void* g_fieldActionStateAnimVtableA[12];      /* 0x0075FD60 conf 0.80: Virtual method table for field action animation state machine variant A; slot 0 is deleting destructor 0x002C0A14, slot  */
extern void* g_fieldActionStateAnimVtableB[12];      /* 0x0075FD98 conf 0.80: Virtual method table for field action animation state machine variant B; slot 0 is deleting destructor 0x002C0A24, slot  */
extern void* g_fieldActorStepBehaviourVtable[16];    /* 0x00762968 conf 0.85: Virtual method table for field actor step behavior; slot 0 is Field_Action_StepBehaviour_DeletingDtor (0x00301AA4), slot */
extern void* g_fieldActorActionStateAnimVtable[12];  /* 0x00762A18 conf 0.85: Virtual method table for field actor action state anim controller; slot 0 is deleting destructor 0x00301E44, slot 1 is F */
extern void* g_monsterEcologyAnimVtable[13];         /* 0x0076480C conf 0.85: Virtual method table for monster ecology animation controller node; slot 1 is Field_Actor_UpdateMotionScale (0x0032FA3C) */
extern void* g_monsterEcologyRunToLinkActionVtable[11]; /* 0x00764848 conf 0.85: Virtual method table for monster ecology run-to-link behavior action; slots 1 and 2 are Field_NpcAction_RunToLinkSetup ( */
extern void* g_monsterJumpActionVtable[11];          /* 0x0076487C conf 0.85: Virtual method table for monster NPC jump action; slot 0 is deleting destructor 0x00331D9C, slots 1 and 2 are Field_NpcJ */
extern void* g_monsterBehaviorActorVtable[16];       /* 0x00765960 conf 0.85: Virtual method table for monster field actor behavior controller; slot 0 is deleting destructor 0x00371F5C, slot 1 is Fi */
extern void* g_fieldActorBaseBehaviourVtable[16];    /* 0x007659DC conf 0.85: Virtual method table for field actor base behavior; slot 0 is Field_ActorBase_DeletingDtor (0x00372AF0), slots 1-3 are s */
extern void* g_monsterMoveActionVtable[11];          /* 0x00765A24 conf 0.85: Virtual method table for monster move action controller; slots 1-3 handle action initialization, transform application,  */
extern void* g_fieldActionStateAnimVtableC[12];      /* 0x00765A90 conf 0.80: Virtual method table for field action animation state machine variant C; slot 0 is Field_Action_DeletingDtorB (0x003736A */
extern void* g_monsterChaseActionVtable[11];         /* 0x00765AC8 conf 0.85: Virtual method table for monster chase / pursuit action; slot 0 is deleting destructor 0x00373AD4, slot 1 is Field_NpcAc */
extern void* g_monsterAiAnchorAnimVtable[13];        /* 0x007672E0 conf 0.85: Virtual method table for monster AI animation controller node with anchor tracking; slot 1 is Field_Npc_UpdateAnchor (0x */
extern void* g_monsterAttractActionVtable[11];       /* 0x007687E8 conf 0.85: Virtual method table for monster attract / approach behavior action; slot 0 is deleting destructor 0x003AE2AC, slot 1 is */
extern void* g_monsterFieldBehaviourVtableA[16];     /* 0x0076881C conf 0.85: Virtual method table for monster field behavior state machine variant A; slot 0 is deleting destructor 0x003AE340; refer */
extern void* g_monsterFieldBehaviourSkullDashVtable[16]; /* 0x00768864 conf 0.85: Virtual method table for monster field behavior with skull dash capability; slot 0 is deleting destructor 0x003AE470, sl */
extern void* g_monsterBehaviorActionVtable[11];      /* 0x007688AC conf 0.90: Virtual method table for Monster_BehaviorAction; slot 0 is deleting destructor 0x003AE50C; installed by maybe_Monster_Be */
extern void* g_fieldActionStateAnimVtableD[12];      /* 0x007688E0 conf 0.80: Virtual method table for field action animation state machine variant D; slot 0 is deleting destructor 0x003AE5F4, slot  */
extern void* g_monsterClimbActionVtable[11];         /* 0x0076AF54 conf 0.85: Virtual method table for monster climb action behavior; slot 0 is deleting destructor 0x003DE308, slot 1 is Field_Action */
extern void* g_monsterIvyClimbActionVtable[11];      /* 0x0076AFBC conf 0.85: Virtual method table for monster ivy/rope climb action behavior; slot 0 is Field_Action_IvyClimb_Dtor (0x003DF178), slot */
extern void* g_monsterClimbActorVtable[16];          /* 0x0076B08C conf 0.85: Virtual method table for monster climb actor behavior controller; slot 0 is deleting destructor 0x003DF200, slot 3 is ca */
extern void* g_monsterOpenItemBoxActionVtable[11];   /* 0x0076B108 conf 0.85: Virtual method table for monster mimic / treasure chest open action (Field_OpenItemBoxAction); slot 0 is deleting destru */
extern void* g_monsterHellTackleActionVtable[11];    /* 0x0076B170 conf 0.90: Virtual method table for monster Hell Tackle (charging attack) field action; slot 0 is Field_HellTackleAction_Dtor (0x00 */
extern void* g_monsterModelSubInstanceBaseVtable[10]; /* 0x0076BF68 conf 0.80: Base virtual method table restored on monster model sub-instance members at +0x148 and +0x2a0 during teardown in Monster */
extern void* g_monsterTurnBaseActionVtable[11];      /* 0x0076DEFC conf 0.85: Virtual method table for monster turn-base action controller; slot 0 is deleting destructor 0x0041372C, slots 1-3 evalua */
extern void* g_monsterTurnTowardTargetActionVtable[11]; /* 0x0076DF30 conf 0.85: Virtual method table for monster turn-toward-target field action; slot 0 is deleting destructor 0x0041399C, slots 1-3 ha */
extern void* g_fieldActorActionPlayStateAnimVtable[12]; /* 0x0076DF64 conf 0.85: Virtual method table for field actor action playing state animations; slot 0 is deleting destructor 0x00413A94, slot 1 i */
extern void* g_monsterPatternNodeDrawListVtable[6];  /* 0x0076EF7C conf 0.85: Virtual method table for monster pattern node display list manager; slots 1 and 2 merge display lists and insert nodes;  */
extern void* g_monsterModelBaseVtable[8];            /* 0x0076F408 conf 0.85: Virtual method table for monster model base instance; slot 0 is deleting destructor 0x00438D38, followed by common model */
extern void* g_fieldEggJumpActionVtable[23];         /* 0x00771748 conf 0.90: Virtual method table for monster egg-jump / bounce field action (Field_EggJumpAction); contains 22 slots including lifec */
extern void* g_monsterEggJumpMovementActionVtable[11]; /* 0x007717AC conf 0.85: Virtual method table for monster egg-jump movement controller; slot 0 is deleting destructor 0x004566CC, slots 1-3 handl */
extern void* g_monsterActorWalkBehaviourVtable[16];  /* 0x007717E0 conf 0.85: Virtual method table for monster field walk behavior controller; slot 0 is deleting destructor 0x004566DC, slots 1-3 han */
extern void* g_monsterActionMTurnVtable[13];         /* 0x0077387C conf 0.90: Virtual method table for monster movement-turn (MTurn) action; slot 0 is Monster_Action_DtorDelete (0x00475104), slot 1  */
extern void* g_monsterDragonJumpActionVtable[11];    /* 0x00773AB0 conf 0.90: Virtual method table for monster dragon-jump / flying leap field action; slots 1-3 are Actor_Action_DragonJump_Begin, En */
extern void* g_monsterActionDulneighVtable[11];      /* 0x00773AE4 conf 0.90: Virtual method table for Dulneigh monster specialized action; slot 0 is Monster_Action_Dulneigh_DtorDelete (0x00477378), */
extern void* g_monsterActionReactVtable[11];         /* 0x00776B24 conf 0.90: Virtual method table for monster reaction / notice behavior action; slot 0 is Monster_Action_React_DtorDelete (0x004B40B */
extern void* g_monsterIvyActionVtable[11];           /* 0x00778874 conf 0.85: Virtual method table for monster ivy/obstacle action; slot 0 is Actor_Action_Ivy_BaseDtor (0x004CDF54), slot 1 is relati */
extern void* g_monsterEcoChaseActionVtable[11];      /* 0x00779E30 conf 0.90: Virtual method table for monster ecology chase action; slot 0 is Field_NpcAction_Chase_Dtor (0x004D6F6C), slot 3 is Fiel */
extern void* g_monsterAiBehaviorVtable[11];          /* 0x0077FDFC conf 0.85: Virtual method table for primary monster AI behavior container; slot 0 is destructor helper 0x00619D28; installed by Mon */
extern void* g_monsterModelPatternDrawListVtable[6]; /* 0x0078081C conf 0.85: Virtual method table for monster model pattern display list node; slot 0 is maybe_Monster_ModelInstance_Delete (0x00420F */
extern void* g_monsterModelInstanceVtable[6];        /* 0x007808B4 conf 0.90: Virtual method table for Monster_ModelInstance; slot 0 is Monster_ModelInstance_Dtor (0x00421674), slots 1 and 2 handle  */
extern void* g_monsterDualPatternState0Vtable[6];    /* 0x007809A8 conf 0.85: State handler vtable for monster dual pattern mode state 0; slot 0 is action state update handler 0x004217D0; stored at  */
extern void* g_monsterDualPatternState3Vtable[6];    /* 0x007809C0 conf 0.85: State handler vtable for monster dual pattern mode state 3; slot 0 is Monster_Model_SetState (0x00421D2C); stored at +0x */
extern void* g_monsterDualPatternState4Vtable[6];    /* 0x007809D8 conf 0.85: State handler vtable for monster dual pattern mode state 4; slot 0 is Monster_Model_UpdateFadeAlpha (0x0042222C); stored */
extern void* g_monsterDualPatternState2Vtable[6];    /* 0x007809F0 conf 0.85: State handler vtable for monster dual pattern mode state 2; slot 0 is child busy check handler 0x004223A4; stored at +0x */
extern void* g_monsterDualPatternState1Vtable[6];    /* 0x00780A08 conf 0.85: State handler vtable for monster dual pattern mode state 1; slot 0 is animation keyframe event dispatcher maybe_Monster_ */
extern void* g_monsterDualPatternModelInstanceVtable[6]; /* 0x00780A20 conf 0.85: Primary virtual method table for monster dual pattern model instance; slot 0 is maybe_Monster_ModelInstance_DtorB (0x004 */
extern u32 g_monsterModelAnimEventFrame0;            /* 0x007A5EF4 conf 0.85: Target keyframe index for monster model animation event 0; compared against current frame in maybe_Monster_Model_ApplyVa */
extern u32 g_monsterModelAnimEventFrame1;            /* 0x007A5EF8 conf 0.85: Target keyframe index for monster model animation event 1; compared against current frame in maybe_Monster_Model_ApplyVa */
extern f32 g_monsterModelAnimEventParam1;            /* 0x007A5EFC conf 0.85: Floating-point scale/intensity parameter for monster model animation event 1; loaded via vldr into s16 in maybe_Monster_ */
extern u32 g_monsterModelAnimEventFrame2;            /* 0x007A5F00 conf 0.85: Target keyframe index for monster model animation event 2; compared against current frame in maybe_Monster_Model_ApplyVa */
extern f32 g_monsterModelAnimEventParam2;            /* 0x007A5F04 conf 0.85: Floating-point scale/intensity parameter for monster model animation event 2; loaded via vldr into s16 in maybe_Monster_ */
extern char g_monsterSizeSuffixSs[3];                /* 0x007BFD2B conf 0.95: Null-terminated monster size suffix string "ss" (Super Small); selected by monster size index 0 in Anim_FormatEnemyAnima */
extern char g_monsterSizeSuffixS[2];                 /* 0x007BFD2E conf 0.95: Null-terminated monster size suffix string "s" (Small); selected by monster size index 1 in Anim_FormatEnemyAnimationPat */
extern char g_monsterSizeSuffixM[2];                 /* 0x007BFD30 conf 0.95: Null-terminated monster size suffix string "m" (Medium); selected by monster size index 2 in Anim_FormatEnemyAnimationPa */
extern char g_monsterSizeSuffixL[2];                 /* 0x007BFD32 conf 0.95: Null-terminated monster size suffix string "l" (Large); selected by monster size index 3 in Anim_FormatEnemyAnimationPat */
extern char g_monsterSizeSuffixLl[3];                /* 0x007BFD34 conf 0.95: Null-terminated monster size suffix string "ll" (Super Large); selected by monster size index 4 in Anim_FormatEnemyAnima */
extern char g_monsterSizeSuffixDefault[1];           /* 0x007BFD37 conf 0.95: Empty string "" used as default monster size suffix fallback when no size prefix applies in Anim_FormatEnemyAnimationPat */
extern char g_enemyAnimPathFmtVariant[15];           /* 0x007BFD38 conf 0.95: Format string "enemy_%s%d.ani" used to construct enemy animation file paths with size suffix and numeric variant index. */
extern char g_enemyAnimPathFmt[13];                  /* 0x007BFD47 conf 0.95: Format string "enemy_%s.ani" used to construct enemy animation file paths with size suffix and no numeric variant index. */

/* --- NPCEnemyDisable --- */
extern u32 g_npc2DEnemyActorClassRecord[5];          /* 0x007C4D74 conf 0.85: BSS class-registration record and RTTI token for 2D enemy NPC actors (NPC2DEnemyActor): entry +0x28 in table g_npc2DActo */

/* --- Object --- */
extern void* g_objectDescSubclassVtable[12];         /* 0x0076E080 conf 0.80: Virtual method table for object descriptor subclass variant installed by maybe_Object_Subclass_Ctor (0x00414584); slot 1 */
extern void* maybe_g_svcContentBaseVtable[34];       /* 0x00780E5C conf 0.45: Base class virtual method table (34 slots) for the content archive / service mount object; slot 0 is the open-by-path me */
extern void* maybe_g_multiBaseSubObjectVtable[7];    /* 0x00781028 conf 0.45: Base virtual method table (7 slots) for 0x3C-byte sub-objects embedded at offsets +0xB8 and +0xF4 in MultiBaseObject; in */

/* --- Os --- */
extern u32 g_dspDefaultSyncTokens[2];                /* 0x0072FBB8 conf 0.85: Default synchronization token pair in .rodata for the DSP service state block: contains current process pseudo-handle (0 */
extern char g_dspServiceName[9];                     /* 0x0072FBC0 conf 0.95: DSP service port name ("dsp::DSP") passed to srvGetServiceHandle in Snd_OpenDspService (0x00107024) to open audio DSP IP */
extern u32 g_osClosedHandleSentinel;                 /* 0x007418A8 conf 0.85: Zero constant word in .rodata used to reset IPC session handles and scheduler locks to 0 upon handle closure in Os_Close */
extern void* g_cfgUServiceDescriptor[2];             /* 0x007418BC conf 0.90: Service initialization descriptor in .rodata for 3DS 'cfg:u' (system configuration): contains default handle (0) and poi */
extern u32 g_curProcessHandle;                       /* 0x007418D0 conf 0.95: 3DS Horizon OS pseudo-handle constant for current process (0xFFFF8001); passed to OS and sound service wrappers in maybe */
extern u32 g_srvDefaultHandle;                       /* 0x00741AD4 conf 0.90: Zero handle constant in .rodata preceding 'srv:' string; copied into g_srvSessionHandle (0x007AF900) to reset the handle */
extern char g_srvServiceName[5];                     /* 0x00741AD8 conf 0.95: 3DS Service Manager port name string ("srv:") used to initialize the Horizon service registry client in Os_WaitRuntimeRe */
extern void* g_cfgIServiceDescriptor[2];             /* 0x00754F8C conf 0.90: Service initialization descriptor in .rodata for 3DS 'cfg:i' (internal configuration): contains default handle (0) and p */
extern void* g_cfgSServiceDescriptor[2];             /* 0x00754F94 conf 0.90: Service initialization descriptor in .rodata for 3DS 'cfg:s' (secure configuration): contains default handle (0) and poi */
extern u32 g_gpuChannelProcessHandle;                /* 0x00754FBC conf 0.90: 3DS Horizon current-process pseudo-handle constant (0xFFFF8001); loaded in Gfx_OpenGpuChannel (0x0010bb34) and passed to */
extern void* g_osSequenceTaskVtable[9];              /* 0x0075CACC conf 0.90: Virtual method table for Os_SequenceTask (9 words: 1 RTTI/offset word + 8 virtual methods); installed on task instances  */
extern void* g_asyncWaitOpBaseVtable[6];             /* 0x0075D3D0 conf 0.90: Virtual method table for the base 0x18-byte asynchronous wait operation token; installed on tokens across all operation  */
extern void* g_asyncWaitOpKind1Vtable[4];            /* 0x00761538 conf 0.90: Virtual method table for Kind 1 asynchronous wait operation companion object; installed when param_2 == 1 in maybe_Os_Cr */
extern void* g_asyncWaitOpKind3Vtable[4];            /* 0x007647F4 conf 0.90: Virtual method table for Kind 3 asynchronous wait operation companion object; installed when param_2 == 3 in maybe_Os_Cr */
extern void* g_asyncWaitOpKind2Vtable[4];            /* 0x0076D52C conf 0.90: Virtual method table for Kind 2 asynchronous wait operation companion object; installed when param_2 == 2 in maybe_Os_Cr */
extern void* g_recordReaderVariableVtable[2];        /* 0x00780F94 conf 0.90: Virtual dispatch table in .rodata for variable-length inline record stream reader (method 0x0065841C); installed on stac */
extern void* g_recordReaderFixed6ByteVtable[2];      /* 0x00780FA4 conf 0.90: Virtual dispatch table in .rodata for 6-byte fixed-length record stream reader (method 0x00658478); installed on stack r */
extern void* g_osOwnerTableNodeVtable[2];            /* 0x007821C8 conf 0.85: Virtual method table for owner/handle container terminal node in .rodata; installed at node +0x30 in maybe_Os_OwnerTable */
extern void* g_osThreadObjectVtable[1];              /* 0x00782668 conf 0.95: Virtual method table for Os_ThreadObject in .rodata; slot 0 points to deleting destructor Os_ThreadObject_Dtor (0x005761 */
extern u32 g_dspDefaultPeriodConstant;               /* 0x0078D8F4 conf 0.85: DSP service timing period constant (0x1B14A172) in .rodata; copied into DSP service state block (+0x1C) in maybe_Snd_Ini */
extern u8 g_gfxIpcCommandRingBuffer[4096];           /* 0x0079C000 conf 0.90: 4096-byte (0x1000) circular command ring buffer in .data for GPU and sound IPC message dispatch; processed per-frame in  */
extern u32 g_dspServiceState[12];                    /* 0x007AEA00 conf 0.90: 48-byte DSP service runtime state block in .data; tracks initialization (+0x08), ready flags (+0x01..+0x03), timeout lim */
extern u32 g_dspServiceMutex;                        /* 0x007AEA10 conf 0.90: Synchronization lock/mutex in .data guarding concurrent access to g_dspServiceState; initialized in Snd_OpenDspService ( */
extern u32 g_dspServiceHandle;                       /* 0x007AEA18 conf 0.95: IPC session handle for 3DS 'dsp::DSP' service in .data; populated by srvGetServiceHandle in Snd_OpenDspService (0x001070 */
extern u8 g_sharedServiceSessionIsOpen;              /* 0x007AEAB4 conf 0.90: Single-byte status flag in .data indicating whether shared service session is open; set to 1 in FUN_001074AC and cleared */
extern u8 g_gpuSessionClosingFlag;                   /* 0x007AF0A0 conf 0.90: Shutdown status flag in .data for GPU session; cleared to 0 upon session initialization (0x0010d6cc) and set to 1 during */
extern u32 g_gpuSessionEvent[2];                     /* 0x007AF0B4 conf 0.90: LightEvent synchronization object in .data used to synchronize GPU worker thread; initialized with ResetType 1 in maybe_ */
extern void* g_aptSessionDesc[3];                    /* 0x007AF0BC conf 0.95: 12-byte IPC session descriptor in .data for 3DS 'APT:A' (applet service); +0x00 open flag, +0x04 pointer to "APT:A" (0x0 */
extern s8 g_schedulerLockSavedPriority;              /* 0x007AF0C8 conf 0.90: Thread priority value saved prior to acquiring scheduler/GPU lock; restored via svcSetThreadPriority (svc 0x14) in Os_Un */
extern u32 g_cfgServiceLock[3];                      /* 0x007AF0EC conf 0.90: Monitor and reference counter block in .data for 3DS 'cfg:u' service; +0x08 tracks active users in Svc_Cfg_AcquireServic */
extern u32 g_cfgServiceHandle;                       /* 0x007AF0F8 conf 0.95: Active IPC session handle in .data for 3DS 'cfg:u' (configuration service); opened by Svc_Cfg_AcquireService (0x00112050 */
extern u32 g_osMemoryManagerLock[2];                 /* 0x007AF8D0 conf 0.85: Critical section lock object in .data guarding system memory manager; +0x04 ownership flag and +0x00 lock recursion dept */
extern u32 g_tlsDestructorSlotMask;                  /* 0x007AF8E0 conf 0.95: 16-bit bitmask in .data (init 0xFFFF0000) indicating which of the 16 thread-local storage destructor slots at 0x007EF378 */
extern u32 g_addressArbiterHandle;                   /* 0x007AF8E4 conf 0.95: Kernel handle in .data for process address arbiter; created via svcCreateAddressArbiter (svc 0x21) in FUN_00106EC8 and p */
extern u32 g_srvClientState[2];                      /* 0x007AF8F8 conf 0.95: 8-byte SRV client session descriptor in .data (+0x00 ready flag, +0x04 reference count); checked in Os_WaitRuntimeReady  */
extern u32 g_srvSessionHandle;                       /* 0x007AF900 conf 0.95: Active IPC session handle in .data for 3DS Service Manager ('srv:'); used across kernel wrappers to query service ports  */
extern u32 g_cfgIServiceRefCount;                    /* 0x007B0060 conf 0.95: Reference count in .data of active users of 3DS 'cfg:i' service; incremented in Svc_Cfg_OpenServiceI (0x001183a4) and de */
extern u32 g_cfgSServiceState[2];                    /* 0x007B0064 conf 0.95: 8-byte session descriptor in .data for 3DS 'cfg:s' service (+0x00 open flag, +0x04 user refcount); updated in Svc_Cfg_Op */
extern u32 g_frameTickThreshold[2];                  /* 0x007B00B8 conf 0.85: 64-bit system tick threshold (u32[2]) in .data; compared against elapsed system tick delta from svcGetSystemTick (svc 0x */
extern u32 g_linearHeapPhysDelta[2];                 /* 0x007B2C9C conf 0.95: Physical address translation offset table in .data (+0x00 linear heap physical delta added in Os_TranslateLinearAddress, */
extern u32 g_cfgIServiceHandle;                      /* 0x007B2CF8 conf 0.95: Active IPC session handle in .data for 3DS 'cfg:i' (internal configuration); opened by Svc_Cfg_OpenServiceI (0x001183a4) */
extern u32 g_cfgSServiceHandle;                      /* 0x007B2CFC conf 0.95: Active IPC session handle in .data for 3DS 'cfg:s' (secure configuration); opened by Svc_Cfg_OpenServiceS (0x001182fc) a */
extern u32 g_gspGpuServiceHandle;                    /* 0x007B2D2C conf 0.95: Active IPC session handle in .data for 3DS 'gsp::Gpu' service; used to send GPU commands and register interrupts via svc */
extern u32 g_osCallbackListLock[2];                  /* 0x007E793C conf 0.90: Synchronization monitor lock in .bss guarding global ordered callback list at 0x007AE954; passed to 0x00117E50/0x00117ed */
extern u32 g_dspEventHandles[8];                     /* 0x007E7978 conf 0.90: Array of 8 event/wait synchronization handles in .bss (32 bytes); validated in maybe_Os_WaitSyncObject (0x00107100) and  */
extern void* g_dspShutdownCallbacks[8];              /* 0x007E79B8 conf 0.95: Array of 8 finalizer function pointers in .bss (32 bytes) for DSP service; registered/cleared in Snd_OpenDspService (0x0 */
extern u32 g_dspServiceListNode[5];                  /* 0x007E79D8 conf 0.90: Intrusive doubly-linked list node descriptor in .bss (20 bytes) for DSP service; linked into global ordered list 0x007AE */
extern u32 g_gpuSessionHandles[3];                   /* 0x007EDFA4 conf 0.95: Array of 3 kernel object handles in .bss (12 bytes) for GPU worker thread; populated in maybe_Os_OpenServiceHandle (0x00 */
extern u32 g_osSystemMonitor[2];                     /* 0x007EF0A4 conf 0.90: Global system lock/monitor object in .bss; initialized once via FUN_00111E28 under atomic one-shot flag in Os_Initialize */
extern u32 g_memMappedBlockAllocator[6];             /* 0x007EF360 conf 0.95: Virtual address range allocator in .bss for memory block mapping; manages address ranges for svcMapMemoryBlock in Mem_Ma */
extern void* g_tlsDestructors[16];                   /* 0x007EF378 conf 0.95: Array of 16 thread-local storage destructor function pointers in .bss (64 bytes); iterated and invoked for active slots  */
extern u32 g_srvNotificationManager[32];             /* 0x007F2358 conf 0.90: State block in .bss for service notification worker; contains session handle (+0x0C), worker thread object (+0x10), regi */
extern u32 g_osResourceCapabilityConfig[10];         /* 0x007F2630 conf 0.90: 40-byte capability and resource limits descriptor table in .bss; initialized with early-boot resource limit attributes ( */
extern u8 g_paramBlockChecksum;                      /* 0x007F2C7C conf 0.95: Single-byte CRC checksum accumulator in .bss; reset to 0 and populated with 15-byte checksum in maybe_Os_ScanParamBlocks */
extern u8 g_paramBlockBuffer[64];                    /* 0x007F2DA0 conf 0.95: 64-byte (0x40) parameter block buffer in .bss; populated by chunked table reader FUN_001223B0 in maybe_Os_LookupParamEnt */

/* --- Pack --- */
extern void* g_fsResourceVtable[12];                 /* 0x0077F6C4 conf 0.90: Virtual method table (12 slots) for Fs_Resource; slot 0 is destructor thunk 0x005F9518 (releasing pack handle at +0x3C), */
extern void* g_fsWorkerVtable[9];                    /* 0x007824A4 conf 0.90: Two-part virtual method table (primary at +0x00, secondary interface at +0x18) for Fs_Worker; slot 0 is complete destruc */
extern void* g_packHandleTableVtable[9];             /* 0x00782A6C conf 0.90: Two-part virtual method table (primary at +0x00, secondary interface at +0x18) for PackHandleTable; slot 3 is Fs_Worker_ */
extern u32 g_packEffectLoadTable[14];                /* 0x007A62DC conf 0.90: Table of 7 effect pack archive descriptors in .data (56 bytes, 14 words: each entry is {char* path, u32 loadMode}); inde */
extern u8 g_packHandleTableInitGuard;                /* 0x007BE364 conf 0.90: One-shot initialization guard flag (1 byte in .data, initialized to 1) for the PackHandleTable singleton; checked and cl */
extern PackHandleTable* g_packHandleTable;           /* 0x007BE368 conf 0.95: Global singleton pointer to the lazily initialized PackHandleTable instance; populated by Pack_HandleTable_Get (0x0010AF */
extern u8 g_packHandleTableBuffer[11364];            /* 0x008342B0 conf 0.90: Static BSS memory buffer (11,364 / 0x2C64 bytes, aligned to 16 bytes) providing placement storage for the PackHandleTabl */

/* --- Party --- */
extern u8 g_partyAutoHealDefaultAction[8];           /* 0x0072A5F8 conf 0.90: Default sentinel action decision record (8 bytes: u8 actorIdx=0xFF, u8 targetIdx=0xFF, u8 skillId=0xFF, u8 unk=0xFF, u8  */

/* --- PartyAdd --- */
extern u32 g_partyMemberJoinTable[8];                /* 0x00728A54 conf 0.95: Table of 8 playable party member join records (4 bytes each: u8 charaId, u8 pad, u16 saveFlagOffset) for the 8 main stor */

/* --- Regex --- */
extern u32 g_regexPredefinedClassRangeTable[2574];   /* 0x00754FC8 conf 0.90: Master lookup table of 2,574 Unicode code-point ranges used by regex predefined character classes (POSIX classes and Uni */
extern u32 g_regexPredefinedClassDescriptorTable[264]; /* 0x00757800 conf 0.90: Descriptor slice table for the 132 predefined regex character classes (class IDs 0..0x83). Each 8-byte entry stores a {u */
extern void* g_regexPredefinedClassNameTable[264];   /* 0x00757C20 conf 0.90: Name lookup table for the 132 predefined regex character classes matched by Regex_ParsePredefinedClass when parsing '\p{ */
extern u32 g_regexOpcodeDispatchTable[76];           /* 0x007AF1B0 conf 0.90: Regex pattern VM opcode dispatch table in .data containing 38 8-byte {void* handler, u32 flagsOrCtxOffset} entries split */

/* --- Save --- */
extern u16 g_senrekiCompletedFlagIdsA[40];           /* 0x007250BC conf 0.90: Flag-id table A for the 'senreki' (play-record) completion counter: 10 groups of 4 u16 save-progress flag ids. Save_Senr */
extern u16 g_senrekiCompletedFlagIdsE[48];           /* 0x0072514C conf 0.90: Flag-id table E for the 'senreki' (play-record) completion counter: 12 groups of 4 u16 save-progress flag ids tested aga */
extern u16 g_senrekiCompletedFlagIdsB[56];           /* 0x007251AC conf 0.90: Flag-id table B for the 'senreki' (play-record) completion counter: 14 groups of 4 u16 save-progress flag ids tested aga */
extern u16 g_senrekiCompletedFlagIdsC[36];           /* 0x0072521C conf 0.90: Flag-id table C for the 'senreki' (play-record) completion counter: 9 groups of 4 u16 save-progress flag ids tested agai */
extern u16 g_senrekiCompletedFlagIdsD[56];           /* 0x007252A4 conf 0.90: Flag-id table D for the 'senreki' (play-record) completion counter: 14 groups of 4 u16 save-progress flag ids tested aga */
extern u16 g_saveMemberPresenceOffsets[14];          /* 0x007288C8 conf 0.55: Seven {u16 partySlot, u16 presentByteOffset} pairs telling the save loader which party slots have a stored character rec */
extern u32 g_saveDataLimits[5];                      /* 0x0072D76C conf 0.60: Save-data limit/descriptor record: word 0 = 9,999,999 (gold/value clamp), +0x04 = 99 (level cap), +0x08 = 255 (byte/coun */
extern char g_saveDataMountName[8];                  /* 0x0072D780 conf 0.75: Inline mount/device name 'data:' at the head of the save-data archive descriptor; six 8-byte path-formatter method slots */
extern void* g_saveArchiveSystemPathMethod[2];       /* 0x0072D7A0 conf 0.65: One 8-byte ARM pointer-to-member-function slot {formatter 0x002CE46C, this-adjust 0} inside the save-archive descriptor' */
extern void* g_saveArchiveMiniPathMethod[2];         /* 0x0072D7B0 conf 0.65: One 8-byte ARM pointer-to-member-function slot {Fs_FormatMiniPath 0x002CE660, this-adjust 0} inside the save-archive des */
extern u32 g_saveCryptoBlowfishInitP[18];            /* 0x0072D8F4 conf 0.95: Default Blowfish P-array (18 subkeys) for the save-data cipher: Save_Crypto_ExpandKey copies it (0x48 bytes) to the stac */
extern u32 g_saveCryptoBlowfishInitS[1024];          /* 0x0072D93C conf 0.95: Default Blowfish S-boxes for the save-data cipher: four boxes of 256 u32 subkeys copied by Save_Crypto_ExpandKey (0x1000 */
extern u16 g_saveCryptoCrc16Table[256];              /* 0x0072E93C conf 0.90: 256-entry CRC-16 lookup table for the save-data integrity check: Save_Crypto_Context_Init copies the 512 bytes to ctx+0x */
extern void* g_fieldObject2DSharedVtable[4];         /* 0x0075CCA0 conf 0.70: Shared base vtable for the 2-D field-object class: Field_Object2D_CtorA runs the actor base constructor and installs thi */
extern void* g_saveSlotPanelVtable[11];              /* 0x00780B20 conf 0.50: Vtable of the save-slot UI panel object built by maybe_Save_SlotUi_Ctor: word 0 is the complete destructor 0x0045E700, w */
extern u32 maybe_g_fsArchiveEntryEmptyTemplate[4];   /* 0x00780D20 conf 0.45: Static 16-byte template used to initialise stack Fs archive/file objects: word 0 and word 3 are the vtable 0x00780D60 (w */
extern u32 maybe_g_rodata_780F84;                    /* 0x00780F84 conf 0.20: Zero-initialised 4-byte rodata word loaded by the GPU-channel/Save_AsyncReadWorker thread (0x001170CC) and stored into t */
extern void* g_saveCryptoContextVtable[7];           /* 0x007842B8 conf 0.80: Vtable of the save-data crypt context: installed at *ctx by Save_CryptoContext_Destroy. Seven words: complete destructor */
extern u8 maybe_g_saveValidateItemRecords;           /* 0x007A7114 conf 0.45: Retail-disabled validation switch in the save-record loader: when non-zero, maybe_Save_ApplyRecordToWork walks the recor */
extern u8 g_gpuChannelStatusByte2;                   /* 0x007B0082 conf 0.55: Third byte of the GPU-channel work/status word at 0x007B0080: Gfx_OpenGpuChannel clears it when starting the channel, an */
extern u8 g_gpuChannelIpcCommandBuffer[3];           /* 0x007B0086 conf 0.70: Three-byte IPC command buffer at GPU-channel work+6: Gfx_OpenGpuChannel copies the channel configuration bytes (0x100 /  */
extern f32 g_gpuChannelTimeoutRemaining;             /* 0x007B0090 conf 0.50: Fraction of the GPU-channel wait timeout still remaining: initialised to 1.0f, recomputed by maybe_Os_ComputeDeadline as */

/* --- SaveCode --- */
extern u16 g_saveCodeAlphabet[64];                   /* 0x0072EF3C conf 0.95: Canonical 64-character Japanese Hiragana alphabet table (128 bytes, UTF-16LE) used for Spell of Restoration (Fukkatsu no */
extern f64 g_saveCodeCheckDigitWeights[6];           /* 0x0072F1C0 conf 0.90: Array of 6 double-precision probability weights (48 bytes: 0.1, 5e-5, 0.001, 0.1, 0.05, 0.001) used by SaveCode_Generate */
extern u16 g_saveCodeFixed20InputAlphabet[64];       /* 0x0072F1F0 conf 0.95: Input character table (128 bytes, UTF-16LE) for the fixed 20-character Spell of Restoration encoder (SaveCode_EncodeFixe */
extern u16 g_saveCodeFixed20OutputAlphabet[64];      /* 0x0072F272 conf 0.95: Output character alphabet table (128 bytes, UTF-16LE) for the fixed 20-character Spell of Restoration encoder (SaveCode_ */
extern u16 g_saveCodeVariableInputAlphabet[64];      /* 0x0072F2F4 conf 0.95: Input character table (128 bytes, UTF-16LE) for the variable-length Spell of Restoration encoder (SaveCode_EncodeVariabl */
extern u16 g_saveCodeVariableOutputAlphabet[64];     /* 0x0072F376 conf 0.95: Output character alphabet table (128 bytes, UTF-16LE) for the variable-length Spell of Restoration encoder (SaveCode_Enc */

/* --- ScreenEffect --- */
extern f32 g_screenEffectSepiaColor[3];              /* 0x007C5268 conf 0.95: Default RGB color vector [0.9f, 0.5f, 0.25f] used for the cutscene sepia screen effect (CSScreenEffectType mode 2); copi */

/* --- Script --- */
extern u32 maybe_g_rodata_00726f66;                  /* 0x00726F66 conf 0.20: Spurious rodata entry resolved from literal pool 0x005FE514 which actually contains inline text bytes 'for\0' in Sq_VmIn */
extern void* g_sqCompilerExpVtable[16];              /* 0x007354BC conf 0.85: Virtual method dispatch table for SQCompiler expression parsing and bytecode emission routines; contains code pointers f */
extern void* g_sqFuncStateVtable[8];                 /* 0x007589F4 conf 0.85: Virtual method table for SQFuncState compiler state class used during function compilation and instruction generation. */
extern void* g_scriptIntTableVtable[8];              /* 0x00758B34 conf 0.80: Virtual method table for integer key lookup table and sound emitter helper objects. */
extern void* g_sqGeneratorVtable[8];                 /* 0x007596E4 conf 0.85: Virtual method table for Squirrel SQGenerator coroutine object; handles suspension, resumption, and cleanup. */
extern void* g_sqSystemStringVtable[8];              /* 0x00759814 conf 0.80: Virtual method table for Squirrel shared system string manager and string table initializer. */
extern void* g_sqObjectBaseVtable[8];                /* 0x0075A728 conf 0.85: Virtual method table for base refcounted Squirrel object / SQCollectable base class; invoked during instance destruction */
extern void* g_sqFunctionProtoVtable[8];             /* 0x00760280 conf 0.85: Virtual method table for SQFunctionProto compiled bytecode function prototype object. */
extern void* g_sqClosureVtable[8];                   /* 0x00760294 conf 0.85: Virtual method table for SQClosure callable script closure object with bound environment. */
extern void* g_sqStackFrameVtable[8];                /* 0x0077F4E8 conf 0.85: Virtual method table for Squirrel VM stack execution call frame structure. */
extern void* g_sqArrayVtable[8];                     /* 0x0077F730 conf 0.85: Virtual method table for SQArray resizable array script object. */
extern void* g_sqInstanceVtable[8];                  /* 0x0077F750 conf 0.85: Virtual method table for SQInstance class instance script object. */
extern void* g_sqTableVtable[8];                     /* 0x0077F770 conf 0.85: Virtual method table for SQTable associative key-value dictionary script object. */
extern void* g_scriptUiSystemObjectVtable[8];        /* 0x0077F794 conf 0.80: Virtual method table for UI script system interface object wrapper. */
extern void* g_scriptVmInitTablesVtable[8];          /* 0x0077FCAC conf 0.80: Virtual method table for script VM table initialization context object. */
extern void* g_scriptHashTableVtable[8];             /* 0x0077FCB8 conf 0.80: Virtual method table for script hash table lookup and insertion operations. */
extern void* g_sqClassVtable[8];                     /* 0x00780258 conf 0.85: Virtual method table for SQClass class definition script object. */
extern void* g_scriptTableValueDtorVtable[6];        /* 0x00781004 conf 0.80: Virtual method table for script table value cleanup destructor wrapper. */
extern void* g_scriptBindingErrorVtable[6];          /* 0x00782514 conf 0.80: Virtual method table for script parameter type-error formatting and reporting wrapper. */
extern void* g_scriptCallbackInvokerVtable[6];       /* 0x00782678 conf 0.80: Virtual method table for script callback dispatch invoker wrapper. */
extern void* g_scriptSubThreadVtable[6];             /* 0x00782690 conf 0.85: Primary virtual method table for script subthread execution context and callback handler. */
extern void* g_scriptSubThreadSecondaryVtable[6];    /* 0x007826A8 conf 0.85: Secondary interface virtual method table (at +0x18 offset) for script subthread execution context. */
extern void* g_scriptInvokeCallbackStackVtable[6];   /* 0x007826C0 conf 0.80: Virtual method table for script callback invoker stack frame reference holder. */
extern void* g_scriptErrorStringFormatterVtable[6];  /* 0x00782730 conf 0.80: Virtual method table for script error string allocation and formatting utility. */
extern char g_scriptIoErrorReadFunctionFailureMsg[79]; /* 0x00789E80 conf 0.95: Squirrel VM bytecode deserialization error message emitted when stream reading fails while loading a compiled script clo */
extern u32 maybe_g_rodata_00797274;                  /* 0x00797274 conf 0.20: Spurious rodata entry resolved from literal pool 0x005FE9AC which actually contains inline text keyword bytes 'try\0' (0 */
extern u32 g_sqNullObject[2];                        /* 0x007AEAC0 conf 0.95: Canonical null object pointer (_null_ in sqvm.cpp) representing an uninitialized or null Squirrel object (SQObject: type */
extern u32 g_sqTrueObject[2];                        /* 0x007AEAC8 conf 0.95: Canonical boolean true object pointer (_true_ in sqvm.cpp) representing Squirrel boolean true. */
extern u32 g_sqFalseObject[2];                       /* 0x007AEAD0 conf 0.95: Canonical boolean false object pointer (_false_ in sqvm.cpp) representing Squirrel boolean false. */
extern u32 g_sqSystemGlobalsTable[68];               /* 0x007AF908 conf 0.95: Table of 16 system global function registrations (SQRegFunction: seterrorhandler, setdebughook, enabledebuginfo, getstac */
extern u32 g_sqTableDefaultDelegateMethods[36];      /* 0x007AFA18 conf 0.95: Table of 8 table default delegate methods (SQRegFunction: len, rawget, rawset, rawdelete, rawin, weakref, tostring, clea */
extern u32 g_sqArrayDefaultDelegateMethods[64];      /* 0x007AFAA8 conf 0.95: Table of 15 array default delegate methods (SQRegFunction: len, append, extend, push, pop, top, insert, remove, resize,  */
extern u32 g_sqStringDefaultDelegateMethods[40];     /* 0x007AFBA8 conf 0.95: Table of 9 string default delegate methods (SQRegFunction: len, tointeger, tofloat, tostring, slice, find, tolower, toup */
extern u32 g_sqNumberDefaultDelegateMethods[24];     /* 0x007AFC48 conf 0.95: Table of 5 numeric/boolean default delegate methods (SQRegFunction: tointeger, tofloat, tostring, tochar, weakref plus n */
extern u32 g_sqGeneratorDefaultDelegateMethods[16];  /* 0x007AFCA8 conf 0.95: Table of 3 generator coroutine default delegate methods (SQRegFunction: getstatus, weakref, tostring plus null terminato */
extern u32 g_sqClosureDefaultDelegateMethods[36];    /* 0x007AFCE8 conf 0.95: Table of 8 closure default delegate methods (SQRegFunction: call, pcall, acall, pacall, weakref, tostring, bindenv, geti */
extern u32 g_sqThreadDefaultDelegateMethods[24];     /* 0x007AFD78 conf 0.95: Table of 5 thread/coroutine default delegate methods (SQRegFunction: call, wakeup, getstatus, weakref, tostring plus nul */
extern u32 g_sqClassDefaultDelegateMethods[28];      /* 0x007AFDD8 conf 0.95: Table of 6 class default delegate methods (SQRegFunction: getattributes, setattributes, rawin, weakref, tostring, instan */
extern u32 g_sqInstanceDefaultDelegateMethods[20];   /* 0x007AFE48 conf 0.95: Table of 4 instance default delegate methods (SQRegFunction: getclass, rawin, weakref, tostring plus null terminator; 5  */
extern u32 g_sqWeakRefDefaultDelegateMethods[16];    /* 0x007AFE98 conf 0.95: Table of 3 weak reference default delegate methods (SQRegFunction: ref, weakref, tostring plus null terminator; 4 entrie */
extern char g_sqCompilerCantDeleteExpressionMsg[27]; /* 0x007BE3F4 conf 0.95: Squirrel compiler error message 'can't delete an expression' emitted when attempting to delete an un-deletable expressio */
extern char g_sqCompilerCannotDeleteLocalMsg[22];    /* 0x007BE40F conf 0.95: Squirrel compiler error message 'cannot delete a local' emitted when attempting to delete a local variable slot. */
extern char g_sqCompilerCantAssignExpressionMsg[24]; /* 0x007BE425 conf 0.95: Squirrel compiler error message 'can't assign expression' emitted when target of assignment is not an l-value. */
extern char g_sqCompilerFreeVariablesCannotBeModifiedMsg[34]; /* 0x007BE43D conf 0.95: Squirrel compiler error message 'free variables cannot be modified' emitted when modifying an outer free variable. */
extern char g_sqCompilerCantCreateLocalSlotMsg[28];  /* 0x007BE45F conf 0.95: Squirrel compiler error message "can't 'create' a local slot" emitted when attempting slot creation on a local. */
extern char g_sqCompilerScalarExpectedIntFloatMsg[32]; /* 0x007BE47B conf 0.95: Squirrel compiler error message 'scalar expected : integer,float' emitted in switch/case evaluation. */
extern char g_sqCompilerScalarExpectedIntFloatStringMsg[42]; /* 0x007BE49B conf 0.95: Squirrel compiler error message 'scalar expected : integer,float or string' emitted in switch/case evaluation. */
extern char g_sqCompilerParentCannotBeSetMsg[21];    /* 0x007BE4C5 conf 0.95: Squirrel compiler error message 'parent cannot be set' emitted when attempting to assign to 'parent' keyword. */
extern char g_sqCompilerCannotBrakeDerefCommaNeededMsg[68]; /* 0x007BE4DA conf 0.95: Squirrel compiler error message 'cannot brake deref/or comma needed after [exp]=exp slot declaration' in table slot cons */
extern char g_sqCompilerInvalidClassNameMsg[19];     /* 0x007BE51E conf 0.95: Squirrel compiler error message 'invalid class name' emitted during class declaration. */
extern char g_sqCompilerCannotCreateClassInLocalMsg[64]; /* 0x007BE531 conf 0.95: Squirrel compiler error message 'cannot create a class in a local with the syntax(class <local>)'. */
extern char g_sqCompilerThisParamIdent[5];           /* 0x007BE571 conf 0.95: Identifier string 'this' used as implicit self parameter in member functions. */
extern char g_sqCompilerDefaultParamsVarargsConflictMsg[75]; /* 0x007BE576 conf 0.95: Squirrel compiler error message 'function with default parameters cannot have variable number of parameters'. */
extern char g_sqCompilerExpectedClosingParenMsg[13]; /* 0x007BE5C1 conf 0.95: Squirrel compiler syntax error message "expected ')'". */
extern char g_sqCompilerExpectedEqualsMsg[13];       /* 0x007BE5CE conf 0.95: Squirrel compiler syntax error message "expected '='". */
extern char g_sqCompilerExpectedParenOrCommaMsg[20]; /* 0x007BE5DB conf 0.95: Squirrel compiler syntax error message "expected ')' or ','". */
extern char g_sqCompilerForeachIndexIdent[8];        /* 0x007BE5EF conf 0.95: Internal compiler identifier string '@INDEX@' generated for foreach loop index counter variable. */
extern char g_sqCompilerForeachIteratorIdent[11];    /* 0x007BE5F7 conf 0.95: Internal compiler identifier string '@ITERATOR@' generated for foreach loop iterator object. */
extern char g_sqCompilerExpressionExpectedFoundParenMsg[31]; /* 0x007BE602 conf 0.95: Squirrel compiler syntax error message "expression expected, found ')'". */
extern char g_sqCompilerEndOfStatementExpectedMsg[36]; /* 0x007BE621 conf 0.95: Squirrel compiler syntax error message 'end of statement expected (; or lf)'. */
extern char g_sqCompilerConstructorMethodIdent[12];  /* 0x007BE645 conf 0.95: Identifier string 'constructor' used to match class constructor methods. */
extern char g_sqCompilerIdentifierTokenName[11];     /* 0x007BE651 conf 0.95: Token type name string 'IDENTIFIER' used in compiler error reporting. */
extern char g_sqCompilerStringLiteralTokenName[15];  /* 0x007BE65C conf 0.95: Token type name string 'STRING_LITERAL' used in compiler error reporting. */
extern char g_sqCompilerIntegerTokenName[8];         /* 0x007BE66B conf 0.95: Token type name string 'INTEGER' used in compiler error reporting. */
extern char g_sqCompilerFloatTokenName[6];           /* 0x007BE673 conf 0.95: Token type name string 'FLOAT' used in compiler error reporting. */
extern char g_sqCompilerExpectedStringFormat[14];    /* 0x007BE679 conf 0.95: Compiler error format string "expected '%s'". */
extern char g_sqCompilerExpectedCharFormat[14];      /* 0x007BE687 conf 0.95: Compiler error format string "expected '%c'". */
extern char g_sqCompilerThisFactorIdent[5];          /* 0x007BE695 conf 0.95: Identifier string 'this' evaluated as a factor in expression parsing. */
extern char g_sqCompilerConstructorFactorIdent[12];  /* 0x007BE69A conf 0.95: Identifier string 'constructor' evaluated as a factor in expression parsing. */
extern char g_sqCompilerInvalidConstantFormat[25];   /* 0x007BE6A6 conf 0.95: Compiler error format string 'invalid constant [%s.%s]'. */
extern char g_sqCompilerExpressionExpectedMsg[20];   /* 0x007BE6BF conf 0.95: Squirrel compiler syntax error message 'expression expected'. */
extern char g_sqCompilerMainClosureIdent[5];         /* 0x007BE6D3 conf 0.95: Identifier string 'main' for top-level script compilation unit closure. */
extern char g_sqCompilerThisRootIdent[5];            /* 0x007BE6D8 conf 0.95: Identifier string 'this' for root environment in compiled script closure. */
extern char g_sqCompilerBreakNotInLoopMsg[34];       /* 0x007BE6E5 conf 0.95: Squirrel compiler syntax error message "'break' has to be in a loop block". */
extern char g_sqCompilerContinueNotInLoopMsg[37];    /* 0x007BE707 conf 0.95: Squirrel compiler syntax error message "'continue' has to be in a loop block". */
extern char g_scriptFloatTypeName[6];                /* 0x007C019C conf 0.95: Type name string 'float' used in script parameter verification and float retrieval routines. */
extern char g_scriptTriggerEventParamCode[2];        /* 0x007C01A2 conf 0.85: One-character parameter code string '\x01' passed to Script_Vm_CallClosure during script trigger event dispatch. */
extern char g_scriptTriggerEmptyParamStr[1];         /* 0x007C01A3 conf 0.85: Empty string parameter '\0' passed to Script_Vm_CallClosure during script trigger event dispatch. */
extern char g_scriptTypeDescCutsceneID[15];          /* 0x007C01A4 conf 0.95: Runtime type descriptor string 'xp::CutsceneID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescDoorTypeID[15];          /* 0x007C01B3 conf 0.95: Runtime type descriptor string 'xp::DoorTypeID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescLevelGroup[15];          /* 0x007C01C2 conf 0.95: Runtime type descriptor string 'xp::LevelGroup' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescLevelMapID[15];          /* 0x007C01D1 conf 0.95: Runtime type descriptor string 'xp::LevelMapID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescScenarioID[15];          /* 0x007C01E0 conf 0.95: Runtime type descriptor string 'xp::ScenarioID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSoundBgmID[15];          /* 0x007C01EF conf 0.95: Runtime type descriptor string 'xp::SoundBgmID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescDisplayMode[16];         /* 0x007C01FE conf 0.95: Runtime type descriptor string 'xp::DisplayMode' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescEmotionKind[16];         /* 0x007C020E conf 0.95: Runtime type descriptor string 'xp::EmotionKind' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMouseKindID[16];         /* 0x007C021E conf 0.95: Runtime type descriptor string 'xp::MouseKindID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPastAltarID[16];         /* 0x007C022E conf 0.95: Runtime type descriptor string 'xp::PastAltarID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRuraPointID[16];         /* 0x007C023E conf 0.95: Runtime type descriptor string 'xp::RuraPointID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescTimeZoneFlg[16];         /* 0x007C024E conf 0.95: Runtime type descriptor string 'xp::TimeZoneFlg' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescVehicleType[16];         /* 0x007C025E conf 0.95: Runtime type descriptor string 'xp::VehicleType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescEffectPlayID[17];        /* 0x007C026E conf 0.95: Runtime type descriptor string 'xp::EffectPlayID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescFacialKindID[17];        /* 0x007C027F conf 0.95: Runtime type descriptor string 'xp::FacialKindID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMapJumpEvent[17];        /* 0x007C0290 conf 0.95: Runtime type descriptor string 'xp::MapJumpEvent' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMouseOrderID[17];        /* 0x007C02A1 conf 0.95: Runtime type descriptor string 'xp::MouseOrderID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescNelsenBossID[17];        /* 0x007C02B2 conf 0.95: Runtime type descriptor string 'xp::NelsenBossID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescNelsenHopeID[17];        /* 0x007C02C3 conf 0.95: Runtime type descriptor string 'xp::NelsenHopeID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPlayerStatus[17];        /* 0x007C02D4 conf 0.95: Runtime type descriptor string 'xp::PlayerStatus' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRecordFlagID[17];        /* 0x007C02E5 conf 0.95: Runtime type descriptor string 'xp::RecordFlagID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRegionBookID[17];        /* 0x007C02F6 conf 0.95: Runtime type descriptor string 'xp::RegionBookID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescScenarioFlag[17];        /* 0x007C0307 conf 0.95: Runtime type descriptor string 'xp::ScenarioFlag' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescTimeZoneType[17];        /* 0x007C0318 conf 0.95: Runtime type descriptor string 'xp::TimeZoneType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescUIScriptType[17];        /* 0x007C0329 conf 0.95: Runtime type descriptor string 'xp::UIScriptType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescUITutorialID[17];        /* 0x007C033A conf 0.95: Runtime type descriptor string 'xp::UITutorialID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescActorFindType[18];       /* 0x007C034B conf 0.95: Runtime type descriptor string 'xp::ActorFindType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescAddMotionKind[18];       /* 0x007C035D conf 0.95: Runtime type descriptor string 'xp::AddMotionKind' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescChipDirection[18];       /* 0x007C036F conf 0.95: Runtime type descriptor string 'xp::ChipDirection' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescEquipPartType[18];       /* 0x007C0381 conf 0.95: Runtime type descriptor string 'xp::EquipPartType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescHorseRaceRank[18];       /* 0x007C0393 conf 0.95: Runtime type descriptor string 'xp::HorseRaceRank' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMessageCursor[18];       /* 0x007C03A5 conf 0.95: Runtime type descriptor string 'xp::MessageCursor' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPictureCardID[18];       /* 0x007C03B7 conf 0.95: Runtime type descriptor string 'xp::PictureCardID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRecordCountID[18];       /* 0x007C03C9 conf 0.95: Runtime type descriptor string 'xp::RecordCountID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescScriptMessage[18];       /* 0x007C03DB conf 0.95: Runtime type descriptor string 'xp::ScriptMessage' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSoundStepType[18];       /* 0x007C03ED conf 0.95: Runtime type descriptor string 'xp::SoundStepType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescActorResetType[19];      /* 0x007C03FF conf 0.95: Runtime type descriptor string 'xp::ActorResetType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescBGControlGroup[19];      /* 0x007C0412 conf 0.95: Runtime type descriptor string 'xp::BGControlGroup' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescEventMessageID[19];      /* 0x007C0425 conf 0.95: Runtime type descriptor string 'xp::EventMessageID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescGlobalGameFlag[19];      /* 0x007C0438 conf 0.95: Runtime type descriptor string 'xp::GlobalGameFlag' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescLevelGimmickID[19];      /* 0x007C044B conf 0.95: Runtime type descriptor string 'xp::LevelGimmickID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescLevelMapAreaID[19];      /* 0x007C045E conf 0.95: Runtime type descriptor string 'xp::LevelMapAreaID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMapChipAreaFlg[19];      /* 0x007C0471 conf 0.95: Runtime type descriptor string 'xp::MapChipAreaFlg' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPlayerVisualID[19];      /* 0x007C0484 conf 0.95: Runtime type descriptor string 'xp::PlayerVisualID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRespawnPointID[19];      /* 0x007C0497 conf 0.95: Runtime type descriptor string 'xp::RespawnPointID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRevivalPointID[19];      /* 0x007C04AA conf 0.95: Runtime type descriptor string 'xp::RevivalPointID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSoundStepChara[19];      /* 0x007C04BD conf 0.95: Runtime type descriptor string 'xp::SoundStepChara' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescTalkDataOption[19];      /* 0x007C04D0 conf 0.95: Runtime type descriptor string 'xp::TalkDataOption' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescCameraShakeType[20];     /* 0x007C04E3 conf 0.95: Runtime type descriptor string 'xp::CameraShakeType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescEffect2DEndType[20];     /* 0x007C04F7 conf 0.95: Runtime type descriptor string 'xp::Effect2DEndType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPlayerParamType[20];     /* 0x007C050B conf 0.95: Runtime type descriptor string 'xp::PlayerParamType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRiremitoPointID[20];     /* 0x007C051F conf 0.95: Runtime type descriptor string 'xp::RiremitoPointID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRuraPatternType[20];     /* 0x007C0533 conf 0.95: Runtime type descriptor string 'xp::RuraPatternType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescScenarioMessage[20];     /* 0x007C0547 conf 0.95: Runtime type descriptor string 'xp::ScenarioMessage' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescTrainingTrialID[20];     /* 0x007C055B conf 0.95: Runtime type descriptor string 'xp::TrainingTrialID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescActSeqEffectType[21];    /* 0x007C056F conf 0.95: Runtime type descriptor string 'xp::ActSeqEffectType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMapJumpLocatorID[21];    /* 0x007C0584 conf 0.95: Runtime type descriptor string 'xp::MapJumpLocatorID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescScenarioBattleID[21];    /* 0x007C0599 conf 0.95: Runtime type descriptor string 'xp::ScenarioBattleID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescTargetCursorType[21];    /* 0x007C05AE conf 0.95: Runtime type descriptor string 'xp::TargetCursorType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPlayerFieldEffect[22];   /* 0x007C05C3 conf 0.95: Runtime type descriptor string 'xp::PlayerFieldEffect' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescRegionCharacterID[22];   /* 0x007C05D9 conf 0.95: Runtime type descriptor string 'xp::RegionCharacterID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescScriptActorOption[22];   /* 0x007C05EF conf 0.95: Runtime type descriptor string 'xp::ScriptActorOption' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescScriptTalkEmotion[22];   /* 0x007C0605 conf 0.95: Runtime type descriptor string 'xp::ScriptTalkEmotion' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSoundStepFadeType[22];   /* 0x007C061B conf 0.95: Runtime type descriptor string 'xp::SoundStepFadeType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescWeatherVisualType[22];   /* 0x007C0631 conf 0.95: Runtime type descriptor string 'xp::WeatherVisualType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescCSScreenEffectType[23];  /* 0x007C0647 conf 0.95: Runtime type descriptor string 'xp::CSScreenEffectType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMiniGameCategoryID[23];  /* 0x007C065E conf 0.95: Runtime type descriptor string 'xp::MiniGameCategoryID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPlayerFieldActType[23];  /* 0x007C0675 conf 0.95: Runtime type descriptor string 'xp::PlayerFieldActType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescUIScriptDialogType[23];  /* 0x007C06A3 conf 0.95: Runtime type descriptor string 'xp::UIScriptDialogType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescUIScriptTalkSEType[23];  /* 0x007C06BA conf 0.95: Runtime type descriptor string 'xp::UIScriptTalkSEType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescAccessDirectionType[24]; /* 0x007C06D1 conf 0.95: Runtime type descriptor string 'xp::AccessDirectionType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescShipAnchoragePointID[25]; /* 0x007C06E9 conf 0.95: Runtime type descriptor string 'xp::ShipAnchoragePointID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescCharacterModelPattern[26]; /* 0x007C0702 conf 0.95: Runtime type descriptor string 'xp::CharacterModelPattern' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescActor2DLocatorMoveType[27]; /* 0x007C071C conf 0.95: Runtime type descriptor string 'xp::Actor2DLocatorMoveType' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescMapChipCharacterLayerID[28]; /* 0x007C0737 conf 0.95: Runtime type descriptor string 'xp::MapChipCharacterLayerID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescItemID[11];              /* 0x007C0753 conf 0.95: Runtime type descriptor string 'xp::ItemID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPanelID[12];             /* 0x007C075E conf 0.95: Runtime type descriptor string 'xp::PanelID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescQuestID[12];             /* 0x007C076A conf 0.95: Runtime type descriptor string 'xp::QuestID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSkillID[12];             /* 0x007C0776 conf 0.95: Runtime type descriptor string 'xp::SkillID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSpellID[12];             /* 0x007C0782 conf 0.95: Runtime type descriptor string 'xp::SpellID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescUIMapID[12];             /* 0x007C078E conf 0.95: Runtime type descriptor string 'xp::UIMapID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescActorMID[13];            /* 0x007C079A conf 0.95: Runtime type descriptor string 'xp::ActorMID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescInnMsgID[13];            /* 0x007C07A7 conf 0.95: Runtime type descriptor string 'xp::InnMsgID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescPlayerID[13];            /* 0x007C07B4 conf 0.95: Runtime type descriptor string 'xp::PlayerID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescFadeColor[14];           /* 0x007C07C1 conf 0.95: Runtime type descriptor string 'xp::FadeColor' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescLevelWork[14];           /* 0x007C07CF conf 0.95: Runtime type descriptor string 'xp::LevelWork' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescModel3DID[14];           /* 0x007C07DD conf 0.95: Runtime type descriptor string 'xp::Model3DID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescQuestFlag[14];           /* 0x007C07EB conf 0.95: Runtime type descriptor string 'xp::QuestFlag' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSQCommand[14];           /* 0x007C07F9 conf 0.95: Runtime type descriptor string 'xp::SQCommand' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSoundMeID[14];           /* 0x007C0807 conf 0.95: Runtime type descriptor string 'xp::SoundMeID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescSoundSeID[14];           /* 0x007C0815 conf 0.95: Runtime type descriptor string 'xp::SoundSeID' used by script binding system to validate parameter types. */
extern char g_scriptTypeDescTextArgID[14];           /* 0x007C0823 conf 0.95: Runtime type descriptor string 'xp::TextArgID' used by script binding system to validate parameter types. */
extern char g_scriptBindingEmptyStr1[1];             /* 0x007C0831 conf 0.80: Empty string literal '\0' used as default parameter in native script binding functions. */
extern char g_scriptBindingWrongTypeErrorFormat[34]; /* 0x007C0832 conf 0.95: Format string 'wrong type (%s expected, got %s )' emitted when a script binding argument fails runtime type check. */
extern char g_scriptBindingWrongTypeUnknownErrorFormat[39]; /* 0x007C0854 conf 0.95: Format string 'wrong type (%s expected, got unknown )' emitted when argument type cannot be identified. */
extern char g_scriptBindingEmptyStr2[1];             /* 0x007C087B conf 0.80: Empty string literal '\0' passed as default argument in script value error formatting. */
extern char g_scriptBindingEmptyStr3[1];             /* 0x007C087C conf 0.80: Empty string literal '\0' used in script VM retrieval or light initialization error handling. */
extern char g_scriptNativeGetNextCutsceneIDWrongParamCountMsg[27]; /* 0x007C0880 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetNextCutsceneID when called with an  */
extern char g_scriptNativeGetGimmickDoorTypeWrongParamCountMsg[27]; /* 0x007C089B conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetGimmickDoorType when called with an */
extern char g_scriptNativeGetHorseRaceResultWrongParamCountMsg[27]; /* 0x007C08B6 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetHorseRaceResult when called with an */
extern char g_scriptNativeGetLevelMapIDWrongParamCountMsg[27]; /* 0x007C08D1 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetLevelMapID when called with an inva */
extern char g_scriptNativeActorGetJumpMapIDWrongParamCountMsg[27]; /* 0x007C08EC conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_ActorGetJumpMapID when called with an  */
extern char g_scriptNativeGetDisplayModeWrongParamCountMsg[27]; /* 0x007C0907 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetDisplayMode when called with an inv */
extern char g_scriptNativeGetAltarGimmickIDWrongParamCountMsg[27]; /* 0x007C0922 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetAltarGimmickID when called with an  */
extern char g_scriptNativePlayerGetVehicleTypeWrongParamCountMsg[27]; /* 0x007C093D conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_PlayerGetVehicleType when called with  */
extern char g_scriptNativeGetMapJumpEventWrongParamCountMsg[27]; /* 0x007C0958 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetMapJumpEvent when called with an in */
extern char g_scriptNativeGetSelectHopeBossWrongParamCountMsg[27]; /* 0x007C0973 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetSelectHopeBoss when called with an  */
extern char g_scriptNativeGetSelectHopeWrongParamCountMsg[27]; /* 0x007C098E conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetSelectHope when called with an inva */
extern char g_scriptNativeActorGetRegionBookIDWrongParamCountMsg[27]; /* 0x007C09A9 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_ActorGetRegionBookID when called with  */
extern char g_scriptNativeGetScenarioFlagWrongParamCountMsg[27]; /* 0x007C09C4 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetScenarioFlag when called with an in */
extern char g_scriptNativeGetTimeZoneTypeWrongParamCountMsg[27]; /* 0x007C09DF conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetTimeZoneType when called with an in */
extern char g_scriptNativeIEGetUITypeWrongParamCountMsg[27]; /* 0x007C09FA conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IEGetUIType when called with an invali */
extern char g_scriptNativeGetDroppedVehicleTutorialWrongParamCountMsg[27]; /* 0x007C0A15 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetDroppedVehicleTutorial when called  */
extern char g_scriptNativeGetGimmickDoorKeyTypeWrongParamCountMsg[27]; /* 0x007C0A30 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetGimmickDoorKeyType when called with */
extern char g_scriptNativeGetHorseRaceRankWrongParamCountMsg[27]; /* 0x007C0A4B conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetHorseRaceRank when called with an i */
extern char g_scriptNativeGetActorLevelGimmickIDWrongParamCountMsg[27]; /* 0x007C0A66 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetActorLevelGimmickID when called wit */
extern char g_scriptNativeGetAreaIDWrongParamCountMsg[27]; /* 0x007C0A81 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetAreaID when called with an invalid  */
extern char g_scriptNativeEndUIWrongParamCountMsg[27]; /* 0x007C0A9C conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_EndUI when called with an invalid argu */
extern char g_scriptNativeGetRiremitoPointWrongParamCountMsg[27]; /* 0x007C0AB7 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetRiremitoPoint when called with an i */
extern char g_scriptNativeGetTrainingTrialIDWrongParamCountMsg[27]; /* 0x007C0AD2 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetTrainingTrialID when called with an */
extern char g_scriptNativeGetBattleResultWrongParamCountMsg[27]; /* 0x007C0AED conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetBattleResult when called with an in */
extern char g_scriptNativeGetScenarioBattleResultWrongParamCountMsg[27]; /* 0x007C0B08 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetScenarioBattleResult when called wi */
extern char g_scriptNativeGetRegionIDWrongParamCountMsg[27]; /* 0x007C0B23 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetRegionID when called with an invali */
extern char g_scriptNativeGetMapJumpLocatorIDWrongParamCountMsg[27]; /* 0x007C0B3E conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetMapJumpLocatorID when called with a */
extern char g_scriptNativeActorGetJumpLocatorIDWrongParamCountMsg[27]; /* 0x007C0B59 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_ActorGetJumpLocatorID when called with */
extern char g_scriptNativeGetScenarioBattleIDWrongParamCountMsg[27]; /* 0x007C0B74 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetScenarioBattleID when called with a */
extern char g_scriptNativeGetActorRegionCharacterIDWrongParamCountMsg[27]; /* 0x007C0B8F conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetActorRegionCharacterID when called  */
extern char g_scriptNativeActorGetTalkEmotionWrongParamCountMsg[27]; /* 0x007C0BAA conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_ActorGetTalkEmotion when called with a */
extern char g_scriptNativeIEGetAtmarkCommandWrongParamCountMsg[27]; /* 0x007C0BC5 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IEGetAtmarkCommand when called with an */
extern char g_scriptNativeGetMiniGameCategoryFromGimmickWrongParamCountMsg[27]; /* 0x007C0BE0 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetMiniGameCategoryFromGimmick when ca */
extern char g_scriptNativeGetGimmickAccessDirTypeWrongParamCountMsg[27]; /* 0x007C0BFB conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetGimmickAccessDirType when called wi */
extern char g_scriptNativeGetDialogResultWrongParamCountMsg[27]; /* 0x007C0C16 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetDialogResult when called with an in */
extern char g_scriptNativePlayerGetVehicleModelPatternWrongParamCountMsg[27]; /* 0x007C0C31 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_PlayerGetVehicleModelPattern when call */
extern char g_scriptNativeGetSoulSelectItemWrongParamCountMsg[27]; /* 0x007C0C4C conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetSoulSelectItem when called with an  */
extern char g_scriptNativeGetGimmickItemIDWrongParamCountMsg[27]; /* 0x007C0C67 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetGimmickItemID when called with an i */
extern char g_scriptNativeActorGetQuestIDWrongParamCountMsg[27]; /* 0x007C0C82 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_ActorGetQuestID when called with an in */
extern char g_scriptNativeGetGameModeWrongParamCountMsg[27]; /* 0x007C0C9D conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetGameMode when called with an invali */
extern char g_scriptNativeGetPlayerIDWrongParamCountMsg[27]; /* 0x007C0CB8 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetPlayerID when called with an invali */
extern char g_scriptNativeGetQuestFlagWrongParamCountMsg[27]; /* 0x007C0CD3 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetQuestFlag when called with an inval */
extern char g_scriptNativeGetTalkPartyYesIndexWrongParamCountMsg[27]; /* 0x007C0CEE conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetTalkPartyYesIndex when called with  */
extern char g_scriptNativeIsMovieEndWrongParamCountMsg[27]; /* 0x007C0D09 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsMovieEnd when called with an invalid */
extern char g_scriptNativeGetCSWatchFlagWrongParamCountMsg[27]; /* 0x007C0D24 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetCSWatchFlag when called with an inv */
extern char g_scriptNativeIsClearedAltarWrongParamCountMsg[27]; /* 0x007C0D3F conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsClearedAltar when called with an inv */
extern char g_scriptNativeIsEnableRuraPointWrongParamCountMsg[27]; /* 0x007C0D5A conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsEnableRuraPoint when called with an  */
extern char g_scriptNativeGetNelsenHopeFlagWrongParamCountMsg[27]; /* 0x007C0D75 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetNelsenHopeFlag when called with an  */
extern char g_scriptNativeIsTimeZoneWrongParamCountMsg[27]; /* 0x007C0D90 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsTimeZone when called with an invalid */
extern char g_scriptNativeHasTravelMenuTutorialIDWrongParamCountMsg[27]; /* 0x007C0DAB conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_HasTravelMenuTutorialID when called wi */
extern char g_scriptNativeIsBG3DVisibleWrongParamCountMsg[27]; /* 0x007C0DC6 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsBG3DVisible when called with an inva */
extern char g_scriptNativeIsClearTrainingTrialWrongParamCountMsg[27]; /* 0x007C0DE1 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsClearTrainingTrial when called with  */
extern char g_scriptNativeIsHalfGoldScenarioBattleWrongParamCountMsg[27]; /* 0x007C0DFC conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsHalfGoldScenarioBattle when called w */
extern char g_scriptNativeIsRecipeItemWrongParamCountMsg[27]; /* 0x007C0E17 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsRecipeItem when called with an inval */
extern char g_scriptNativeGetQuestEnableFlagWrongParamCountMsg[27]; /* 0x007C0E32 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetQuestEnableFlag when called with an */
extern char g_scriptNativeIsZoneWrongParamCountMsg[27]; /* 0x007C0E4D conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsZone when called with an invalid arg */
extern char g_scriptNativeGetLevelWorkEnableWrongParamCountMsg[27]; /* 0x007C0E68 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_GetLevelWorkEnable when called with an */
extern char g_scriptNativeIEChangeBlockWrongParamCountMsg[27]; /* 0x007C0E83 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IEChangeBlock when called with an inva */
extern char g_scriptNativeIsEndFadeWrongParamCountMsg[27]; /* 0x007C0E9E conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsEndFade when called with an invalid  */
extern char g_scriptNativeIsEndEffect2DCommandWrongParamCountMsg[27]; /* 0x007C0EB9 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsEndEffect2DCommand when called with  */
extern char g_scriptNativeIsMEStartWrongParamCountMsg[27]; /* 0x007C0ED4 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsMEStart when called with an invalid  */
extern char g_scriptNativeIsLearnPanelWrongParamCountMsg[27]; /* 0x007C0EEF conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsLearnPanel when called with an inval */
extern char g_scriptNativeIsLearnSkillWrongParamCountMsg[27]; /* 0x007C0F0A conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsLearnSkill when called with an inval */
extern char g_scriptNativeIsLearnSpellWrongParamCountMsg[27]; /* 0x007C0F25 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_IsLearnSpell when called with an inval */
extern char g_scriptNativeActorGetCtrlOptionWrongParamCountMsg[27]; /* 0x007C0F40 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Native_ActorGetCtrlOption when called with an */
extern char g_scriptBindSpiritMessageWrongParamCountMsg[27]; /* 0x007C0F5B conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SpiritMessage when called with an invali */
extern char g_scriptBindIECheckOptionWrongParamCountMsg[27]; /* 0x007C0F76 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_IECheckOption when called with an invali */
extern char g_scriptBindIsYesNoOpenTalkPartyWrongParamCountMsg[27]; /* 0x007C0F91 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_IsYesNoOpenTalkParty when called with an */
extern char g_scriptBindEncountEventExWrongParamCountMsg[27]; /* 0x007C0FAC conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_EncountEventEx when called with an inval */
extern char g_scriptBindIECameraGetYawWrongParamCountMsg[27]; /* 0x007C0FC7 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_IECameraGetYaw when called with an inval */
extern char g_scriptBindGetGlobalGameFlagWrongParamCountMsg[27]; /* 0x007C0FE2 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetGlobalGameFlag when called with an in */
extern char g_scriptBindIEGetCountWrongParamCountMsg[27]; /* 0x007C0FFD conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_IEGetCount when called with an invalid a */
extern char g_scriptBindFindActorWrongParamCountMsg[27]; /* 0x007C1018 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_FindActor when called with an invalid ar */
extern char g_scriptBindGetGimmickActorIDWrongParamCountMsg[27]; /* 0x007C1033 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetGimmickActorID when called with an in */
extern char g_scriptBindGetActorIDWrongParamCountMsg[27]; /* 0x007C104E conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetActorID when called with an invalid a */
extern char g_scriptBindGetNeedBoushiTicketNumWrongParamCountMsg[27]; /* 0x007C1069 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetNeedBoushiTicketNum when called with  */
extern char g_scriptBindGetPlayerActorIDWrongParamCountMsg[27]; /* 0x007C1084 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetPlayerActorID when called with an inv */
extern char g_scriptBindPlaySEWrongParamCountMsg[27]; /* 0x007C109F conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_PlaySE when called with an invalid argum */
extern char g_scriptBindGetActorIDFromUniqueIDWrongParamCountMsg[27]; /* 0x007C10BA conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetActorIDFromUniqueID when called with  */
extern char g_scriptBindIEGetTextIDWrongParamCountMsg[27]; /* 0x007C10D5 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_IEGetTextID when called with an invalid  */
extern char g_scriptBindIEGetAtmarkCountWrongParamCountMsg[27]; /* 0x007C10F0 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_IEGetAtmarkCount when called with an inv */
extern char g_scriptBindGetCountEquipedItemWrongParamCountMsg[27]; /* 0x007C110B conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetCountEquipedItem when called with an  */
extern char g_scriptBindGetDaysElapsedWrongParamCountMsg[27]; /* 0x007C1126 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetDaysElapsed when called with an inval */
extern char g_scriptBindGetItemNumInPartyWrongParamCountMsg[27]; /* 0x007C1141 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetItemNumInParty when called with an in */
extern char g_scriptBindGetTalkPartyIDWrongParamCountMsg[27]; /* 0x007C115C conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetTalkPartyID when called with an inval */
extern char g_scriptBindGetGimmickGetGoldWrongParamCountMsg[27]; /* 0x007C1177 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetGimmickGetGold when called with an in */
extern char g_scriptBindGetRandWrongParamCountMsg[27]; /* 0x007C1192 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetRand when called with an invalid argu */
extern char g_scriptBindGetGimmickItemNumWrongParamCountMsg[27]; /* 0x007C11AD conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetGimmickItemNum when called with an in */
extern char g_scriptBindPlayMEWrongParamCountMsg[27]; /* 0x007C11C8 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_PlayME when called with an invalid argum */
extern char g_scriptBindGetPartyMemberNumberWrongParamCountMsg[27]; /* 0x007C11E3 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetPartyMemberNumber when called with an */
extern char g_scriptBindGetPartyMemberMaxHPWrongParamCountMsg[27]; /* 0x007C11FE conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_GetPartyMemberMaxHP when called with an  */
extern char g_scriptBindMessageEndWrongParamCountMsg[27]; /* 0x007C1219 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_MessageEnd when called with an invalid a */
extern char g_scriptBindLoadCutSceneWrongParamCountMsg[27]; /* 0x007C1234 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_LoadCutScene when called with an invalid */
extern char g_scriptBindSendTrgMapJumpWrongParamCountMsg[27]; /* 0x007C124F conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SendTrgMapJump when called with an inval */
extern char g_scriptBindPrepareBGMWrongParamCountMsg[27]; /* 0x007C126A conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_PrepareBGM when called with an invalid a */
extern char g_scriptBindSetDisplayModeWrongParamCountMsg[27]; /* 0x007C1285 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetDisplayMode when called with an inval */
extern char g_scriptBindRuraPointAddWrongParamCountMsg[27]; /* 0x007C12A0 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_RuraPointAdd when called with an invalid */
extern char g_scriptBindPlayerSetVehicleTypeWrongParamCountMsg[27]; /* 0x007C12BB conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_PlayerSetVehicleType when called with an */
extern char g_scriptBindLoadEffect3DWrongParamCountMsg[27]; /* 0x007C12D6 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_LoadEffect3D when called with an invalid */
extern char g_scriptBindSetRecordFlagWrongParamCountMsg[27]; /* 0x007C12F1 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetRecordFlag when called with an invali */
extern char g_scriptBindBookIDMessageSetupWrongParamCountMsg[27]; /* 0x007C130C conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_BookIDMessageSetup when called with an i */
extern char g_scriptBindFixedTimeZoneWrongParamCountMsg[27]; /* 0x007C1327 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_FixedTimeZone when called with an invali */
extern char g_scriptBindStartTutorialUIWrongParamCountMsg[27]; /* 0x007C1342 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_StartTutorialUI when called with an inva */
extern char g_scriptBindLoadHorseRaceWrongParamCountMsg[27]; /* 0x007C135D conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_LoadHorseRace when called with an invali */
extern char g_scriptBindLoadPictureCardWrongParamCountMsg[27]; /* 0x007C1378 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_LoadPictureCard when called with an inva */
extern char g_scriptBindAddRecordCountWrongParamCountMsg[27]; /* 0x007C1393 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_AddRecordCount when called with an inval */
extern char g_scriptBindScriptMessageSetupWrongParamCountMsg[27]; /* 0x007C13AE conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_ScriptMessageSetup when called with an i */
extern char g_scriptBindSendFieldEventMessageWrongParamCountMsg[27]; /* 0x007C13C9 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SendFieldEventMessage when called with a */
extern char g_scriptBindSetRevivalPointIDWrongParamCountMsg[27]; /* 0x007C13E4 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetRevivalPointID when called with an in */
extern char g_scriptBindSetRiremitoPointWrongParamCountMsg[27]; /* 0x007C13FF conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetRiremitoPoint when called with an inv */
extern char g_scriptBindScenarioMessageSetupWrongParamCountMsg[27]; /* 0x007C141A conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_ScenarioMessageSetup when called with an */
extern char g_scriptBindBattleEndToDefaultFieldWrongParamCountMsg[27]; /* 0x007C1435 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_BattleEndToDefaultField when called with */
extern char g_scriptBindIEMessageSetupWrongParamCountMsg[27]; /* 0x007C1450 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_IEMessageSetup when called with an inval */
extern char g_scriptBindDialogOpenWrongParamCountMsg[27]; /* 0x007C146B conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_DialogOpen when called with an invalid a */
extern char g_scriptBindSetDefaultTalkSEWrongParamCountMsg[27]; /* 0x007C1486 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetDefaultTalkSE when called with an inv */
extern char g_scriptBindSetEmbarkartionInfoWrongParamCountMsg[27]; /* 0x007C14A1 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetEmbarkartionInfo when called with an  */
extern char g_scriptBindQuestCompletedMessageWrongParamCountMsg[27]; /* 0x007C14BC conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_QuestCompletedMessage when called with a */
extern char g_scriptBindChangeUIMapWrongParamCountMsg[27]; /* 0x007C14D7 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_ChangeUIMap when called with an invalid  */
extern char g_scriptBindClearStatusWrongParamCountMsg[27]; /* 0x007C14F2 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_ClearStatus when called with an invalid  */
extern char g_scriptBindSQCommandWrongParamCountMsg[27]; /* 0x007C150D conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SQCommand when called with an invalid ar */
extern char g_scriptBindSetMessageArgDropVehicleWrongParamCountMsg[27]; /* 0x007C1528 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetMessageArgDropVehicle when called wit */
extern char g_scriptBindActorRemoveGadgetWrongParamCountMsg[27]; /* 0x007C1543 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_ActorRemoveGadget when called with an in */
extern char g_scriptBindSetActionInputEnableWrongParamCountMsg[27]; /* 0x007C155E conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_SetActionInputEnable when called with an */
extern char g_scriptBindStartTripDoorEffectWrongParamCountMsg[27]; /* 0x007C1579 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_StartTripDoorEffect when called with an  */
extern char g_scriptBindPictureCardDisableWrongParamCountMsg[27]; /* 0x007C1594 conf 0.95: Static error message string 'wrong number of parameters' emitted by Script_Bind_PictureCardDisable when called with an i */
extern char g_scriptBindCameraReguralyShakeStopParamCountError[27]; /* 0x007C15AF conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetLevelGroupEnableParamCountError[27]; /* 0x007C15CA conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindLoadInnMapJumpParamCountError[27]; /* 0x007C15E5 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetScenarioFlagParamCountError[27]; /* 0x007C1600 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPlayBGMParamCountError[27];  /* 0x007C161B conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPlayerSetVehicleTypeExParamCountError[27]; /* 0x007C1636 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetNelsenHopeFlagParamCountError[27]; /* 0x007C1651 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindStartUIParamCountError[27];  /* 0x007C166C conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindBG3DSetVisibleParamCountError[27]; /* 0x007C1687 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetGlobalGameFlagParamCountError[27]; /* 0x007C16A2 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetScenarioWeatherParamCountError[27]; /* 0x007C16BD conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindBG2DSetVisibleParamCountError[27]; /* 0x007C16D8 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetBasicRespawnIDParamCountError[27]; /* 0x007C16F3 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindLoadBattleFuncParamCountError[27]; /* 0x007C170E conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPlayerSetFieldEffectParamCountError[27]; /* 0x007C1729 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetWeatherParamCountError[27]; /* 0x007C1744 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindScreenEffectChangeParamCountError[27]; /* 0x007C175F conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetMessageArgMiniGameNameParamCountError[27]; /* 0x007C177A conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindCameraResetFreeCamParamCountError[27]; /* 0x007C1795 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindAutoAddItemInPartyParamCountError[27]; /* 0x007C17B0 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetQuestFlagParamCountError[27]; /* 0x007C17CB conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetQuestEnableFlagParamCountError[27]; /* 0x007C17E6 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindInnMessageParamCountError[27]; /* 0x007C1801 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindAddStatusParamCountError[27]; /* 0x007C181C conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindChangePlayerVisualParamCountError[27]; /* 0x007C1837 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetDrawPlayerEquipmentParamCountError[27]; /* 0x007C1852 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindAddPartyMemberHPParamCountError[27]; /* 0x007C186D conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPlayerResurrectParamCountError[27]; /* 0x007C1888 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetLevelWorkEnableParamCountError[27]; /* 0x007C18A3 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetMessageArgNelsenBossParamCountError[27]; /* 0x007C18BE conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetMessageArgItemNameParamCountError[27]; /* 0x007C18D9 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetMessageArgNumParamCountError[27]; /* 0x007C18F4 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindLoadCharaGadgetParamCountError[27]; /* 0x007C190F conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindRegistThreadParamCountError[27]; /* 0x007C192A conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindCameraChangeParamCountError[27]; /* 0x007C1945 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindUpdateTripDoorEffectParamCountError[27]; /* 0x007C1960 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetBackFilmBlendParamParamCountError[27]; /* 0x007C197B conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindChangeGimmickDoorTypeParamCountError[27]; /* 0x007C1996 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetEyeParamCountError[27]; /* 0x007C19B1 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetMouseParamCountError[27]; /* 0x007C19CC conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActor2DTurnParamCountError[27]; /* 0x007C19E7 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorResetPosAndDirBeforeEventParamCountError[27]; /* 0x007C1A02 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSendGimmickMessageParamCountError[27]; /* 0x007C1A1D conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindEffect2DStopParamCountError[27]; /* 0x007C1A38 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorDeleteEffectActionSeqParamCountError[27]; /* 0x007C1A53 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorWarpToMapJumpLocatorIDParamCountError[27]; /* 0x007C1A6E conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetNPCTargetCursorParamCountError[27]; /* 0x007C1A89 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorTalkEmotionParamCountError[27]; /* 0x007C1AA4 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPlayerSetFieldActionParamCountError[27]; /* 0x007C1ABF conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindMessageRegistActorParamCountError[27]; /* 0x007C1ADA conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActor2DSetLayerParamCountError[27]; /* 0x007C1AF5 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSendActorMessageParamCountError[27]; /* 0x007C1B10 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorTurnLocatorParamCountError[27]; /* 0x007C1B2B conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetCollideParamCountError[27]; /* 0x007C1B46 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetFootStepVolumeParamCountError[27]; /* 0x007C1B61 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPictureCardEnableParamCountError[27]; /* 0x007C1B7C conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindStopSEParamCountError[27];   /* 0x007C1B97 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindStopMEParamCountError[27];   /* 0x007C1BB2 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindLoadFieldParamCountError[27]; /* 0x007C1BCD conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindUpdateDaysParamCountError[27]; /* 0x007C1BE8 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPlayFootSEParamCountError[27]; /* 0x007C1C03 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindChangeFootStepVolumeParamCountError[27]; /* 0x007C1C1E conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindIECameraExParamCountError[27]; /* 0x007C1C39 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindAddItemInPlayerParamCountError[27]; /* 0x007C1C54 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindChangeEquipedItemParamCountError[27]; /* 0x007C1C6F conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindAddPlayerParamParamCountError[27]; /* 0x007C1C8A conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindDBOpenDialogParamCountError[27]; /* 0x007C1CA5 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindTalkStartParamCountError[27]; /* 0x007C1CC0 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetLocatorOffsetParamCountError[27]; /* 0x007C1CDB conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindTalkZoomCameraEnableParamCountError[27]; /* 0x007C1CF6 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindStartFadeOutParamCountError[27]; /* 0x007C1D11 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindCameraShakeParamCountError[27]; /* 0x007C1D2C conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindScreenEffectSetSepiaMulParamCountError[27]; /* 0x007C1D47 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorEmotionIconParamCountError[27]; /* 0x007C1D62 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetFaceParamCountError[27]; /* 0x007C1D7D conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorPlayAddMotionParamCountError[27]; /* 0x007C1D98 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetCtrlOptionParamCountError[27]; /* 0x007C1DB3 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindGimmickDoorOpenParamCountError[27]; /* 0x007C1DCE conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActor2DWalkLocatorParamCountError[27]; /* 0x007C1DE9 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorAttachGadgetParamCountError[27]; /* 0x007C1E04 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetTurnSpeedLocatorParamCountError[27]; /* 0x007C1E1F conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorWalkTargetParamCountError[27]; /* 0x007C1E3A conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPictureCardSetAlphaParamCountError[27]; /* 0x007C1E55 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetBackgroundDrawOffsetParamCountError[27]; /* 0x007C1E70 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetTurnSpeedTargetParamCountError[27]; /* 0x007C1E8B conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindEffect2DMoveParamCountError[27]; /* 0x007C1EA6 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPartyTalkParamCountError[27]; /* 0x007C1EC1 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSwapBasicRespawnIDParamCountError[27]; /* 0x007C1EDC conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindSetFadeExParamParamCountError[27]; /* 0x007C1EF7 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindStartDelayFadeOutParamCountError[27]; /* 0x007C1F12 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindCameraShakeExParamCountError[27]; /* 0x007C1F2D conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorSetFaceEXParamCountError[27]; /* 0x007C1F48 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActorMeshShakeParamCountError[27]; /* 0x007C1F63 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPictureCardMoveTargetParamCountError[27]; /* 0x007C1F7E conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindMessageFuncParamCountError[27]; /* 0x007C1F99 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActor2DMoveSylviaShipParamCountError[27]; /* 0x007C1FB4 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindEffect2DAttachActorParamCountError[27]; /* 0x007C1FCF conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActor2DMoveParamCountError[27]; /* 0x007C1FEA conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActor2DWarpParamCountError[27]; /* 0x007C2005 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindBookIDMessageSetupExParamCountError[27]; /* 0x007C2020 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindScenarioMessageSetupExParamCountError[27]; /* 0x007C203B conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindIEMessageSetupExParamCountError[27]; /* 0x007C2056 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindPictureCardZoomParamCountError[27]; /* 0x007C2071 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindCameraReguralyShakeParamCountError[27]; /* 0x007C208C conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptBindActor2DMoveExParamCountError[27]; /* 0x007C20A7 conf 0.90: Squirrel native-binding error text "wrong number of parameters" (27 bytes including the terminating NUL) that Script_Bin */
extern char g_scriptGetByteArgTypeErrorInteger[8];   /* 0x007C20C2 conf 0.80: Type-error text "integer" (8 bytes including NUL) passed to Script_FormatTypeError as the expected type when maybe_Scrip */
extern char g_scriptGetIntegerArgTypeErrorInteger[8]; /* 0x007C20CA conf 0.80: Type-error text "integer" (8 bytes including NUL) passed to Script_FormatTypeError by Script_GetIntegerArg, the main int */
extern char g_scriptGetIntArgTypeErrorInteger[8];    /* 0x007C20D2 conf 0.80: Type-error text "integer" (8 bytes including NUL) passed to Script_FormatTypeError by Script_GetIntArg when a stack slot */
extern char g_scriptBindTypeErrorIntegerShared[8];   /* 0x007C20DA conf 0.75: Shared type-error text "integer" (8 bytes including NUL) used by several native bindings, including Script_Bind_AddParty */
extern char g_scriptPlayerResurrectTypeErrorInteger[8]; /* 0x007C20E2 conf 0.80: Type-error text "integer" (8 bytes including NUL) passed to Script_FormatTypeError by Script_Bind_PlayerResurrect when t */
extern u32 g_sqNullObjectRef;                        /* 0x007C20EC conf 0.60: Shared zero word used as the null initial value for Squirrel object references: Script_RegisterSubThread and Field_Scene */
extern char g_scriptCallEventHandlersParamCountError[27]; /* 0x007C212B conf 0.85: Copy of the Squirrel error text "wrong number of parameters" (27 bytes including NUL) that maybe_Script_CallEventHandler */
extern char g_scriptCallBookIdCommandParamCountError[27]; /* 0x007C2161 conf 0.85: Copy of the Squirrel error text "wrong number of parameters" (27 bytes including NUL) that Script_CallBookIdCommand copi */
extern char g_scriptNativeATrgMapJumpEventParamCountError[27]; /* 0x007C2197 conf 0.85: Copy of the Squirrel error text "wrong number of parameters" (27 bytes including NUL) that Script_Native_ATrgMapJumpEven */
extern char g_scriptCallSelectRuraPatternParamCountError[27]; /* 0x007C21B2 conf 0.85: Copy of the Squirrel error text "wrong number of parameters" (27 bytes including NUL) that Script_CallSelectRuraPattern  */
extern char g_scriptCallSelectRiremitoUsableParamCountError[27]; /* 0x007C21E8 conf 0.85: Copy of the Squirrel error text "wrong number of parameters" (27 bytes including NUL) that Script_CallSelectRiremitoUsab */
extern char g_sharedFormatBuffer[256];               /* 0x008385F0 conf 0.75: Shared 256-byte scratch buffer for formatted text. The Squirrel compiler writes error messages into it with func_0010018 */
extern u8 g_scriptErrorState[140];                   /* 0x0083876C conf 0.75: Global Squirrel error-state record (140 bytes): +0 error flag, +4 VM pointer, +8 value vtable (0x00782514), +0xC char[12 */

/* --- Serializer --- */
extern u32 g_varUIntByteCountTable[16];              /* 0x0072F4F0 conf 0.80: Total byte count of a UTF-8-style variable-length unsigned integer, indexed by the high nibble of its lead byte: 1 for 0 */

/* --- Shop --- */
extern void* g_shopEquipSlotFilterTable[6];          /* 0x00729B50 conf 0.90: Lookup table of 6 item-filter predicate function pointers corresponding to equipment slots 0..5 (0: weapon Item_IsWeapon */
extern void* g_shopPartyEquipSlotFilterTable[6];     /* 0x00729B68 conf 0.90: Party-inventory variant of the 6-entry equipment-slot filter predicate table (identical callbacks for slots 0..5: weapon */

/* --- Sound --- */
extern u16 g_soundCachedSeIds[10];                   /* 0x0072AC80 conf 0.90: Lookup table of 10 sound effect IDs (0x0E66..0x0E7E) cached for playback checking in Sound_PlaySeCached. */
extern u32 maybe_g_soundCachedSeIdsEnd;              /* 0x0072AC94 conf 0.35: Boundary address immediately following g_soundCachedSeIds; used as an end-of-array sentinel in Sound_PlaySeCached. */
extern void* g_soundBgmRestoreTransitionTable[8];    /* 0x0072BD64 conf 0.85: State transition table of 4 handler function and context pairs driving multi-stage BGM restore/fade transitions (FUN_001 */
extern u8 g_soundSeqCategoryIndexTable[4];           /* 0x0072D8B8 conf 0.90: 4-byte lookup table mapping event sequence category indices (0..3) to audio parameter slots for Sound_PlaySeFromTable. */
extern u8 g_soundSeqChannelLimitTable[14];           /* 0x0072D8BC conf 0.90: 14-byte lookup table mapping sequence event sub-types (0..13) to sound channel polyphony/category limits in Sound_PlaySe */
extern u16 g_soundDefaultSeIdTable[9];               /* 0x0072D8CC conf 0.90: Table of 9 default sound effect IDs (0x45..0x4D) corresponding to sound categories 0..8 in Sound_PlaySeById. */
extern f32 g_soundSeAttenuationTable[4];             /* 0x0072D8E0 conf 0.90: Table of 4 float volume/pitch attenuation scale factors {1.0f, 1.2f, 1.5f, 0.8f} indexed by category in Sound_PlaySeFrom */
extern u32 g_soundDefaultVoiceConfig[4];             /* 0x0072FB70 conf 0.80: Default voice configuration descriptor in rodata passed to Sound_Voice_RequestPlayWithPriority in Sound_Voice_StartPlayb */
extern u32 g_curProcessPseudoHandle;                 /* 0x0072FBCC conf 0.85: CTR-SDK pseudo-handle 0xFFFF8001 representing the current process (CUR_PROCESS_HANDLE) passed into service IPC requests. */
extern u16 g_moLiveAudioFilterWindowTable0[4224];    /* 0x00730D10 conf 0.90: Static filter coefficient / synthesis window lookup table (first of 3 banks spaced 0x2100 bytes apart) assigned to MoLiv */
extern char g_moLiveAllocatorOutOfMemoryFormat[62];  /* 0x007352AC conf 0.95: Error format string logged when MoLive::Allocator fails to allocate the requested buffer size. */
extern void* g_soundSeqChannelSetPauseModeMemFn[2];  /* 0x0073D2E8 conf 0.90: ARM C++ member function pointer pair {Sound_SeqChannel::SetPauseMode (0x0054EBA4), this_adjust=0} passed to Sound_SeqPla */
extern char g_soundExtStm[4];                        /* 0x0073D348 conf 0.95: File extension string 'stm' for binary sound stream archives (BCSTM) in nw::snd. */
extern char g_soundExtWsd[4];                        /* 0x0073D34C conf 0.95: File extension string 'wsd' for wave sound data archives (BCWSD) in nw::snd. */
extern char g_soundExtSeq[4];                        /* 0x0073D350 conf 0.95: File extension string 'seq' for binary sequence sound archives (BCSEQ) in nw::snd. */
extern char g_soundSignatureBxstm[6];                /* 0x0073D354 conf 0.95: Format signature string 'bxstm' for binary CTR stream audio files in nw::snd. */
extern char g_soundSignatureBxwsd[6];                /* 0x0073D35A conf 0.95: Format signature string 'bxwsd' for binary CTR wave sound data files in nw::snd. */
extern char g_soundSignatureBxseq[6];                /* 0x0073D360 conf 0.95: Format signature string 'bxseq' for binary CTR sequence sound files in nw::snd. */
extern char g_soundSignatureBxwar[6];                /* 0x0073D36C conf 0.95: Format signature string 'bxwar' for binary CTR wave archive files in nw::snd. */
extern char g_soundSignatureBxstp[6];                /* 0x0073D372 conf 0.95: Format signature string 'bxstp' for binary CTR stream track/patch files in nw::snd. */
extern u32 g_soundBlockMagicCwat;                    /* 0x0073FF04 conf 0.95: 4-byte block header magic 'CWAT' (0x54415743) written into wave archive / bank info blocks during parsing. */
extern u32 g_ndmProcessPseudoHandle;                 /* 0x007418D4 conf 0.85: CTR-SDK pseudo-handle 0xFFFF8001 representing the current process (CUR_PROCESS_HANDLE) passed into sleep/suspend daemon  */
extern u32 g_csndChannelTimingTable1[5];             /* 0x00741A84 conf 0.85: CSND hardware channel sample transfer timing lookup table (entries: 1200, 1750, 1100, 1800, 3000) used in CSND channel s */
extern u32 g_csndChannelTimingTable2[5];             /* 0x00741A9C conf 0.85: CSND hardware channel sample transfer offset/timing lookup table (entries: 800, 1300, 1800, 3100, 1800) used in CSND cha */
extern f32 g_soundMixerDefaultPanZero;               /* 0x00754F60 conf 0.80: Default float zero constant (0.0f) used for neutral panning / zero volume in Sound_Mixer_BuildVolumeMatrix. */
extern f32 g_soundSeqChannelDefaultParamZero;        /* 0x00754F6C conf 0.80: Default float zero constant (0.0f) used for channel parameter resets in Sound_SeqChannel_StartNote. */
extern char g_irUserServicePortName[8];              /* 0x00754FC0 conf 0.95: Service port name string 'ir:USER' used to acquire a service handle to the CTR Infrared (IR) user service. */
extern void* g_soundPlayerVtable[5];                 /* 0x007730F8 conf 0.75: Virtual method table installed into 0x88-byte sound player / listener objects in maybe_Sound_CreatePlayer. */
extern void* g_soundStreamBufferVtable[5];           /* 0x007816D8 conf 0.85: Virtual method table for stream audio buffer handler objects in nw::snd. */
extern void* g_sound3DManagerVtable[6];              /* 0x0078176C conf 0.85: Virtual method table for 3D sound positioning and attenuation manager in nw::snd. */
extern void* g_soundPlayerBaseVtable[6];             /* 0x007817A4 conf 0.85: Virtual method table for the base sound player interface in nw::snd. */
extern void* g_soundStreamPlayerVtable[6];           /* 0x0078182C conf 0.85: Virtual method table for stream sound player instances (StreamPlayer) in nw::snd. */
extern void* g_soundSequenceTrackAllocatorVtable[6]; /* 0x0078187C conf 0.85: Virtual method table for sequence sound track memory allocators in nw::snd. */
extern void* g_soundSequenceTrackWorkVtable[6];      /* 0x00781948 conf 0.85: Virtual method table for sequence sound track work contexts in nw::snd. */
extern void* g_soundArchiveStreamVtable[6];          /* 0x00781A80 conf 0.85: Virtual method table for archive audio stream reader instances in nw::snd. */
extern void* g_soundStreamPlayerBufferPoolVtable[4]; /* 0x00781B20 conf 0.85: Virtual method table for stream player audio buffer pool allocators in nw::snd. */
extern void* g_soundSeqChannelVtable[6];             /* 0x00781B34 conf 0.85: Virtual method table for sequence sound playback channels (SeqChannel) in nw::snd. */
extern void* g_soundStreamVoiceVtable[5];            /* 0x00781B5C conf 0.85: Virtual method table for stream audio hardware voice allocators in nw::snd. */
extern void* g_soundStreamLockVtable[6];             /* 0x00781B70 conf 0.85: Virtual method table for stream audio buffer lock and synchronization wrappers in nw::snd. */
extern void* g_soundMutexVtable[5];                  /* 0x00781BD0 conf 0.85: Virtual method table for sound subsystem mutex synchronization wrappers in nw::snd. */
extern void* g_soundStreamWorkItemVtable[5];         /* 0x00781C08 conf 0.85: Virtual method table for stream audio work queue items in nw::snd. */
extern void* g_soundSeqBufferPoolVtable[5];          /* 0x00781C1C conf 0.85: Virtual method table for sequence sound buffer pool allocators in nw::snd. */
extern void* g_soundTrackPoolVtable[5];              /* 0x00781C30 conf 0.85: Virtual method table for sound track slot pool managers in nw::snd. */
extern void* g_soundVoiceSeqWorkVtable[5];           /* 0x00781C7C conf 0.85: Virtual method table for sequence voice work context wrappers in nw::snd. */
extern void* g_soundTrackWorkVtable[6];              /* 0x00781C90 conf 0.85: Virtual method table for sequence track runtime work blocks in nw::snd. */
extern void* g_soundStreamRequestVtable[6];          /* 0x00781D3C conf 0.85: Virtual method table for stream sound asynchronous playback requests in nw::snd. */
extern void* g_soundStreamPlayerReleaseVtable[6];    /* 0x00784218 conf 0.80: Virtual method table for stream player cleanup and teardown handlers in nw::snd. */
extern u8 g_soundSystemInitialized;                  /* 0x007AE484 conf 0.95: Boolean flag indicating whether the sound subsystem has been initialized (1) or shut down (0). */
extern u8 g_soundSeOverrideFlag;                     /* 0x007AE485 conf 0.80: Byte flag that overrides requested sound effect IDs with default SE 0x1A when non-zero. */
extern u32 g_soundCommandQueueEventHandle;           /* 0x007AE488 conf 0.90: 3DS KEvent handle signaled via svcSignalEvent (svc 0x14) when commands are pushed to the sound command queue. */
extern u32 g_soundCommandQueueMutex;                 /* 0x007AE48C conf 0.90: Mutex synchronization object protecting the sound command queue during command commit and push operations. */
extern u32 g_soundStreamThreadState;                 /* 0x007AE494 conf 0.85: Thread context pointer for the audio streaming background thread created with priority 0x12 and 8KB stack. */
extern u32 g_soundDecoderChannelGainTable[5];        /* 0x007AE8BC conf 0.90: 5-channel gain/volume buffer table registered into audio decoder work at offsets +0x78..+0x88 in maybe_Sound_Decoder_Ini */
extern u32 g_soundDefaultVoiceCount;                 /* 0x007AE8D4 conf 0.90: Default sound player voice pool capacity (initial value 24 / 0x18) assigned to sound system work at +0xB0. */
extern u32 g_soundVoicePoolAllocationCount;          /* 0x007AE8D8 conf 0.85: Active voice allocation count tracked by the sound voice pool during buffer allocation in Sound_VoicePool_AllocateBuffer */
extern u32 g_defaultMainHeapDescriptor;              /* 0x007AE910 conf 0.80: Default allocator/heap descriptor object used during system initialization and memory management in Mem_InitializeMainHe */
extern u8 g_engineSubsystemInitState;                /* 0x007AE91C conf 0.80: Subsystem initialization state byte tracked during engine startup and shutdown in Engine_Initialize and Engine_ShutdownA */
extern u32 g_errSessionHandle;                       /* 0x007AEA24 conf 0.85: IPC service session handle for the CTR error reporting applet (err:f) stored in .data at 0x007AEA24. */
extern u32 g_csndTransferActive;                     /* 0x007AEA98 conf 0.85: Flag / handle indicating whether a CSND audio hardware DMA transfer is currently in progress. */
extern u32 g_csndAudioSampleTimer;                   /* 0x007AEAA0 conf 0.85: Sample playback elapsed tick counter updated during CSND audio transfer in Snd_WaitAudioTransfer. */
extern u8 g_y2rAudioSessionActive;                   /* 0x007AEAA8 conf 0.85: Boolean flag indicating whether an audio/video stream conversion session (Y2R/CSND) is currently active. */
extern u8 g_soundSeqChannelCommandEnabled;           /* 0x007AECE8 conf 0.85: Byte flag at 0x007AECE8 tested in Sound_Seq_ExecuteChannelCommand (0x00661FDC); when zero, command processing short-circ */
extern u32 g_soundSeqMaxPlaybackFrames;              /* 0x007AECF4 conf 0.85: Maximum frame/tick threshold (default 768 / 0x300) checked during sequence player update in Sound_SeqPlayer_PlayFrame (0 */
extern u32 g_sndChannelNodePoolState;                /* 0x007AECF8 conf 0.85: Descriptor / state word for the CSND channel descriptor pool array (128 elements x 12 bytes at 0x007E8684). */
extern u32 g_soundAdpcmDecoderInitialized;           /* 0x007AECFC conf 0.90: Initialization flag for the ADPCM audio stream decoder; when zero, stream decode operations exit immediately. */
extern u16 g_soundSeqNextInstanceId;                 /* 0x007AED00 conf 0.95: Auto-incrementing 16-bit sequence player instance/handle ID counter stored in .data at 0x007AED00. */
extern u32 g_csndDefaultWaveSampleRateTimer;         /* 0x007AF8E8 conf 0.90: Default wave audio sample rate timer value (0xBE0 = 3040) used when channel wave rate is unconfigured. */
extern u32 g_csndSystemGuard;                        /* 0x007AF8F4 conf 0.95: C++ static initialization guard (__cxa_guard) protecting the singleton initialization of g_csndSystemState at 0x007F09C8 */
extern u32 g_soundDummySeqDataBlock;                 /* 0x007B003C conf 0.85: Dummy/fallback sequence field block pointer (0x007B003C) returned when tag-0 field lookup fails in maybe_Sound_SeqField_ */
extern u32 g_soundDummyWaveDataBlock;                /* 0x007B0048 conf 0.85: Dummy/fallback sound data block pointer (0x007B0048) returned when wave info or sequence field tag resolution fails in m */
extern u32 maybe_g_sndArchiveState;                  /* 0x007B2D00 conf 0.30: Sound archive loader state byte modified at offset +1 when parameter lookup fails in damaged function maybe_Snd_LoadArch */
extern u32 g_soundStreamThreadStack;                 /* 0x007C8650 conf 0.80: Stack / thread work buffer for the sound stream background player thread created in Sound_StreamPlayer_StartLocked. */
extern u8 g_soundStreamThreadWork1[0x30];            /* 0x007CF2B8 conf 0.85: Thread control/synchronization structure (48 bytes) for sound stream worker thread 1, shut down in maybe_Sound_StreamThr */
extern u8 g_soundStreamThreadWork2[0x30];            /* 0x007CF2E8 conf 0.85: Thread control/synchronization structure (48 bytes) for sound stream worker thread 2, shut down in maybe_Sound_StreamThr */
extern u8 g_soundDecoderContext[0x200];              /* 0x007E7268 conf 0.90: Sound decoder context in .bss holding device channel state and status flags initialized by Sound_Decoder_InitChannelTabl */
extern u32 g_audioInterruptMonitor;                  /* 0x007E7998 conf 0.80: Audio hardware interrupt synchronization monitor in .bss used during channel flushing and transfer relay. */
extern u32 g_errAppletSyncMonitor;                   /* 0x007E7A70 conf 0.85: Synchronization monitor in .bss locked via Os_LockMonitor to serialize error applet IPC requests in 0x0011896C. */
extern u8 g_sndChannelNodePool[0x600];               /* 0x007E8684 conf 0.90: CSND channel descriptor pool array in .bss containing 128 elements of 12 bytes each (1536 bytes = 0x600). */
extern u8 g_soundAdpcmDecodeBuffer[0x200];           /* 0x007E8CA0 conf 0.90: Internal scratch buffer in .bss used for ADPCM sample decompression in Sound_Stream_DecodeAdpcmBlock. */
extern u32 g_csndPublishedChannelTable[18];          /* 0x007EF3C4 conf 0.90: CSND hardware channel state publication table in .bss (72 bytes = 0x48) updated per frame in Sound_Frame_PublishChannelT */
extern u32 g_csndChannelParamBlock[6];               /* 0x007EF414 conf 0.90: CSND channel parameter update block in .bss (24 bytes = 0x18) passed to hardware channel register configuration function */
extern u8 g_csndDefaultChannelSettings[0x30];        /* 0x007F0714 conf 0.90: Default CSND hardware channel configuration template in .bss from which default volume/pan settings (+0x1D) are copied. */
extern u32 g_csndSystemState[20];                    /* 0x007F09C8 conf 0.95: CSND system singleton instance in .bss holding master audio driver state, initialized under g_csndSystemGuard in maybe_S */
extern u32 g_csndChannelTableState;                  /* 0x007F0A18 conf 0.85: State descriptor word in .bss tracking CSND channel table initialization and publication state. */
extern u32 g_soundRegistryNotificationList;          /* 0x007F2594 conf 0.80: Callback notification registry list head in .bss traversed during sound event notifications in maybe_Sound_Registry_Noti */
extern u32 g_soundStreamPcmBuffer;                   /* 0x007F259C conf 0.85: Stereo audio PCM sample buffer pointer in .bss used as the source during sample de-interleaving in Sound_Stream_Calculat */
extern u32 g_soundStreamPcmReader;                   /* 0x007F25A0 conf 0.85: PCM audio stream reader context pointer in .bss checked before sample rate calculation and de-interleaving. */
extern u32 g_csndHardwareState;                      /* 0x007F2C3C conf 0.85: CSND audio hardware state flag word in .bss updated during audio driver initialization and wave buffer configuration. */
extern u32 g_irUserSessionHandle;                    /* 0x007F2E00 conf 0.85: IPC service session handle in .bss for the CTR Infrared (ir:USER) service, acquired in maybe_Snd_SetupChannelBuffer. */

/* --- SpiritMessage --- */
extern u32 g_npc2DSpiritActorClassRecord[5];         /* 0x007C4D88 conf 0.85: BSS class-registration record and RTTI token for 2D spirit NPC actors (NPC2DSpiritActor): entry +0x3C in table g_npc2DAc */
extern u32 g_npc3DSpiritActorClassRecord[5];         /* 0x007C4DEC conf 0.85: BSS class-registration record and RTTI token for 3D spirit NPC actors (NPC3DSpiritActor): entry +0x50 in 3D NPC table st */

/* --- Str --- */
extern u16 g_nameHashCrc16Table[256];                /* 0x007275F4 conf 0.90: 256-entry CRC-16/ARC table (reflected polynomial 0xA001, init 0) used by Str_HashName to fold the text after the '@' in  */

/* --- Svc --- */
extern char g_acServiceName[5];                      /* 0x0072FB84 conf 0.95: Null-terminated service port name string "ac:u" used by Svc_AcClient_OpenSession (0x00501554) to request a session handl */
extern u32 g_daysPerMonthTable[12];                  /* 0x0072FBD8 conf 0.95: Lookup table of 12 words specifying days per month for a standard calendar year (January = 31 through December = 31, wit */
extern char g_cecdServiceName[7];                    /* 0x007418AC conf 0.95: Null-terminated service port name string "cecd:u" used by Svc_Cecd_OpenService (0x0050C520) to request a session handle  */
extern void* maybe_g_svcHandleHolderVtable[1];       /* 0x00741A74 conf 0.50: Single-slot virtual method table for a kernel handle holder wrapper object; slot 0 points to maybe_Svc_Object_ReleaseHan */
extern void* maybe_g_entityHandleRefVtable[1];       /* 0x00759794 conf 0.50: Single-slot virtual method table for a generational entity handle reference object; slot 0 is maybe_Svc_Handle_Release ( */
extern void* maybe_g_svcThreadObjectVtable[2];       /* 0x0075A4DC conf 0.50: Virtual method table (2 slots) for a service worker thread object owning thread and synchronization handles; slot 0 is c */
extern void* maybe_g_fsArchiveRecordAccessorVtable[14]; /* 0x00780E18 conf 0.60: Virtual method table (14 slots) for a content archive file/directory accessor node; installed into 0x30-byte nodes alloc */
extern void* maybe_g_fsStreamDecoderVtable[14];      /* 0x00780EAC conf 0.60: Virtual method table (14 slots) for content stream decoder objects; installed into nodes allocated from pool 0x007E7B58  */
extern void* maybe_g_fsContentHandleVtable[14];      /* 0x00780EF0 conf 0.60: Virtual method table (14 slots) for content handle descriptor objects; installed into objects allocated from node pool 0 */
extern u32 g_faceFrameTableInitGuard;                /* 0x007A3510 conf 0.85: One-time initialization guard word (__cxa_guard) protecting lazy population of the character model face animation frame  */
extern u32 g_acClientSessionState;                   /* 0x007AE904 conf 0.85: State and reference count header for the AC ('ac:u') client session: byte 0 records whether the NDM/AC service has been  */
extern u8 g_cecdIconAtlasStateFlags[5];              /* 0x007AE9E5 conf 0.75: Array of byte flags governing the CECD icon atlas and cache: byte 0 is the cache initialized/open flag, byte +3 tracks a */
extern char g_iconCacheErrorTag[8];                  /* 0x007AE9F3 conf 0.90: Fallback 8-byte ASCII placeholder string "ERROR " copied into icon cache timestamp/descriptor slots when looking up an e */
extern u8 maybe_g_ipcSessionStatusByte;              /* 0x007AEA01 conf 0.85: Status and reply byte located at offset +1 of IPC session object 0x007AEA00; tested for zero in maybe_Svc_IpcCmd1100C2 ( */
extern u64 g_timeBaselineTick;                       /* 0x007AEA28 conf 0.90: 64-bit hardware tick count baseline subtracted from the current system tick in Svc_ComputeClockMs (0x005161E0) before mu */
extern u32 maybe_g_osTimeoutBaseRecord[8];           /* 0x007AEA48 conf 0.50: Global timing and timeout configuration record: stores 10x system tick period at +0x18/+0x1C, time source readiness flag */
extern void* maybe_g_fsSharedContext;                /* 0x007AEA68 conf 0.50: Global pointer to the shared filesystem archive context singleton, returned by maybe_Svc_GetSharedContext (0x00505D18) a */
extern u32 g_fsArchiveEventHandle;                   /* 0x007AEAB0 conf 0.90: Horizon kernel Event handle for filesystem archive mounting, created by Os_CreateEvent in Fs_MountDefaultArchives (0x001 */
extern u32 g_acServiceHandle;                        /* 0x007AF090 conf 0.95: Horizon service session handle for 'ac:u' (Auto-Connect WiFi service), populated by srvGetServiceHandle in Svc_AcClient_ */
extern u8 g_isAcSessionOpen;                         /* 0x007AF094 conf 0.90: Boolean flag indicating whether the 'ac:u' service session is currently open and connected; read under g_acClientLock by */
extern u32 g_gpuSessionEventHandle;                  /* 0x007AF0AC conf 0.85: Horizon kernel Event handle for GPU session synchronization; waited on via svc 0x24 (svcWaitSynchronization1) and closed */
extern u8 maybe_g_cecdMailboxActiveFlag;             /* 0x007AF0E0 conf 0.50: Boolean status flag indicating whether the CECD StreetPass mailbox state is currently active; checked and cleared in may */
extern u32 g_amAppServiceHandle;                     /* 0x007AF904 conf 0.95: Horizon service session handle for 'am:app' (Application Manager service), populated via srvGetServiceHandle at 0x00106A */
extern u32 maybe_g_hidDriverSessionHandle;           /* 0x007B0054 conf 0.70: Session handle for the low-level HID/input driver service used to submit command 0x13 (Os_IpcSendCommand13), command 0x3 */
extern u32 g_cecdServiceHandle;                      /* 0x007B0058 conf 0.95: Horizon service session handle for 'cecd:u' (StreetPass CEC user service), populated via srvGetServiceHandle in Svc_Cecd */
extern u32 g_cecdServiceHandleSecondary;             /* 0x007B005C conf 0.85: Secondary/override CECD session handle; tested in Svc_Cecd_Cmd0001B..0x000EB before g_cecdServiceHandle (0x007B0058) to  */
extern u32 g_ndmServiceHandle;                       /* 0x007B00E8 conf 0.95: Horizon service session handle for 'ndm:u' (Nintendo Daemon Manager service), populated via srvGetServiceHandle at 0x001 */
extern u32 g_faceAnimFrameTable[30];                 /* 0x007C3448 conf 0.85: Table of 15 8-byte entries (30 words total) defining character model face animation frame parameters; indexed as base +  */
extern u32 maybe_g_actorTalkPartyClassToken;         /* 0x007C43D8 conf 0.55: Class-type RTTI token for the talk-party actor class; matched against object inheritance chains in maybe_Svc_FindTypedOb */
extern u32 maybe_g_actor2DHasPatternClassToken;      /* 0x007C489C conf 0.55: Class-type RTTI token for 2D actors with secondary pattern resources; matched against object inheritance chains in maybe */
extern u32 g_playerActor2DClassRecord[5];            /* 0x007C4E3C conf 0.95: 5-word class registration record for PlayerActor2D; initialized by Field_RegisterActorClass_PlayerActor2D (0x0068C3BC) w */
extern u8 maybe_g_fsContentResponseBuffer[68808];    /* 0x007D1000 conf 0.50: Large response buffer (0x10CC8 = 68,808 bytes) zeroed by func_0051BA18 during Svc_Content_ResolveEntryType (0x00502E20)  */
extern u32 g_acClientLock[3];                        /* 0x007E7900 conf 0.90: Critical section (12 bytes) protecting the AC ('ac:u') client session state, handle, and reference counter during open,  */
extern u32 maybe_g_svcObjectPoolListB[5];            /* 0x007E7AA4 conf 0.60: Linked list head descriptor managing service object pool B (resource id 0x207 entries); appended to via Os_ListAppendNod */
extern u32 maybe_g_svcObjectPoolListA[5];            /* 0x007E7AB8 conf 0.60: Linked list head descriptor managing service object pool A (resource id 0x209 entries); appended to via Os_ListAppendNod */
extern u32 maybe_g_contentHandleNodePool[15];        /* 0x007E7B1C conf 0.60: Node pool / free-list descriptor (0x3C bytes) for content handle objects (vtable 0x00780EF0), allocated via maybe_Mem_Po */
extern u32 maybe_g_contentAccessorNodePool[15];      /* 0x007E7B58 conf 0.60: Node pool / free-list descriptor (0x3C bytes) for 0x30-byte content stream accessor objects (vtables 0x00780E18 and 0x00 */
extern u32 maybe_g_cecdStateBlock[4];                /* 0x007EF020 conf 0.50: CECD (StreetPass) state context block (16 bytes) in BSS; fields at +4, +8..+10 are reset with state bytes and the 0xFFFF */
extern u8 maybe_g_gpuCommandBufferCleanedFlag;       /* 0x007F09C4 conf 0.70: Boolean flag in BSS set to 1 by Svc_Gpu_CleanupCommandBuffers (0x00517A70) after closing the command buffer handles, syn */
extern u32 maybe_g_bss_00800002;                     /* 0x00800002 conf 0.40: CTR IPC static buffer 0 descriptor constant (IPC_Desc_StaticBuffer for 0x200 bytes, buffer 0 = 0x00800002) loaded into T */
extern u32 maybe_g_bss_00800402;                     /* 0x00800402 conf 0.40: CTR IPC static buffer 1 descriptor constant (IPC_Desc_StaticBuffer for 0x200 bytes, buffer 1 = 0x00800402) loaded into c */

/* --- Text --- */
extern u32 g_encounterGroupEmptySlot;                /* 0x007272A0 conf 0.85: Default sentinel word (0x00FFFFFF) used to initialize four monster group slots to empty/unassigned before encounter grou */
extern u32 g_partyMemberMaxExpCap;                   /* 0x0072739C conf 0.95: Maximum EXP cap constant (9,999,999 = 0x0098967F) used by Party_Member_AddExp to clamp party member accumulated experien */
extern u32 g_field2DMapChipNullCallback[5];          /* 0x00727A84 conf 0.80: Constant empty callback/delegate descriptor (20 bytes) containing a no-op stub (0x0070DBA4) used as default for 2D map c */
extern u32 g_textSpanCursorNullCallback[5];          /* 0x00727ADC conf 0.80: Constant empty callback/delegate descriptor (20 bytes) with a no-op stub (0x0070D8FC) used when advancing a text span cu */
extern u32 g_textSpanMultilineNullCallback[5];       /* 0x00727AF0 conf 0.80: Constant empty callback/delegate descriptor (20 bytes) with a no-op stub (0x0070D8FC) used for multiline text span curso */
extern u32 g_itemBagEntryClearPmf[2];                /* 0x00728454 conf 0.90: Member function pointer pair { &ItemBag_Entry_Clear, 0 } used by ItemBag_ResetEntries to iterate over all item bag slots */
extern u8 g_battleElementAttrIndexTable[24];         /* 0x00728674 conf 0.90: 24-byte lookup table mapping battle elemental attribute IDs to resistance/multiplier attribute indices in combat math. */
extern u8 g_partyEquipSlotSentinelBytes[4];          /* 0x007288FC conf 0.85: 4-byte sentinel array (all 0xFF) initializing four party member equipment slot categories to unequipped before looking u */
extern void* g_vtableUiPartyStatus;                  /* 0x0072A3D8 conf 0.90: Virtual method table for Ui_PartyStatusPanel / UiPartyStatus widget; slot 1 is Ui_PartyStatus_Delete (0x005AEDCC) and sl */
extern char* g_msgArgEnemySuffixLetterTable[8];      /* 0x0072B13C conf 0.95: Array of 8 wide-string pointers to enemy group letter designations (A, B, C, D, E, F, S, and empty) formatted into messa */
extern char g_fsNgWordArchiveName[8];                /* 0x00730C60 conf 0.95: Filesystem archive name string ('ngword:') used to mount and unmount the 3DS profanity filter (NG-word) content archive. */
extern u16 g_ngWordEmailRegexPattern[72];            /* 0x00730C68 conf 0.95: UTF-16LE regular expression pattern for matching and masking email addresses in the 3DS NG-word profanity filter. */
extern u16 g_kanaSmallToFullwidthTable[24];          /* 0x007418EA conf 0.95: 12-entry lookup table of {u16 small, u16 normal} pairs converting small Japanese Katakana characters to standard full-si */
extern u16 g_kanaHalfwidthToFullwidthTable[116];     /* 0x0074191A conf 0.95: 58-entry lookup table of {u16 halfwidth, u16 fullwidth} pairs converting halfwidth Japanese Katakana (0xFF66..0xFF9F) to */
extern u16 g_kanaDakutenCombineTable[42];            /* 0x00741A02 conf 0.95: 21-entry lookup table of {u16 base, u16 voiced} pairs combining a halfwidth Katakana with a voiced mark (dakuten 0xFF9E) */
extern u16 g_kanaHandakutenCombineTable[10];         /* 0x00741A56 conf 0.95: 5-entry lookup table of {u16 base, u16 semivoiced} pairs combining a halfwidth Katakana with a semi-voiced mark (handaku */
extern void* g_vtableTextFontManager;                /* 0x007621BC conf 0.90: Virtual method table for the Text_FontManager singleton; installed during Text_FontManager_Ctor (0x002F7ABC). */
extern void* g_vtableUiIconRequest;                  /* 0x00762F54 conf 0.85: Virtual method table for the Ui_IconRequest icon request state machine object; slot 1 is Ui_IconRequest_Update (0x003106 */
extern void* g_vtablePartyMember;                    /* 0x007803AC conf 0.90: Virtual method table for the complete PartyMember class; installed after base construction in Party_Member_InitEquipSlot */
extern void* g_vtablePartyMemberBase;                /* 0x007803DC conf 0.90: Base virtual method table for PartyMemberBase; installed in Party_Member_InitEquipSlots (0x00192450) prior to base conta */
extern void* maybe_g_vtableAudioStreamRenderer;      /* 0x00781BF4 conf 0.45: Virtual method table installed by constructor 0x005508A4; slot 0 contains virtual destructor 0x0054EE90 which releases s */
extern void* g_vtableTextSpanCursor;                 /* 0x00783BA0 conf 0.95: Virtual method table for Text_SpanCursor; installed during cursor initialization in Text_SpanCursor_Init (0x005CE5B0). */
extern u8 g_battleActionCommandMessageFlag;          /* 0x007A590D conf 0.70: Boolean flag in .data controlling whether action command message row generation is suppressed or enabled during battle a */
extern u32 g_battleItemConsumePopupTemplate[8];      /* 0x007A5B58 conf 0.80: Static template structure in .data whose field at offset +0x10 provides the battle popup parameter for item consumption  */
extern s8 g_encounterWeightedRngBias;                /* 0x007A6514 conf 0.80: Bias/seed modifier byte in .data passed as the third parameter to Math_WeightedRandomIndexDefaultRng during monster enco */
extern u16 g_partyMemberSpecialEquipmentIds[32];     /* 0x007A674C conf 0.85: Array of 16-bit item IDs in .data representing special equipment and costume pieces matched against member inventory slo */
extern s8 g_field2DMapChipOverrideMode;              /* 0x007A6AE6 conf 0.75: Signed byte flag in .data overriding 2D map chip entry selection (-1 = no override, 1 = force index 0). */
extern u32 g_uiPagerDefaultTextId;                   /* 0x007AB420 conf 0.80: Default 32-bit text/string ID in .data passed to Ui_TextLayer_SetText when initializing pager text layers in Ui_Pager_In */
extern u16 g_textGlyphQuadCountLimit;                /* 0x007AE60C conf 0.70: 16-bit/32-bit glyph count threshold in .data checked in Text_BuildGlyphQuads to bound the number of glyph quad vertices  */
extern s32 g_textGlyphRunAlignmentOffset;            /* 0x007AE610 conf 0.70: Row glyph alignment and spacing adjustment in .data used by Text_LayoutGlyphRunTwoPass to adjust text row bounds during  */
extern u32 g_guardSoundDecoderSingleton;             /* 0x007AECDC conf 0.95: C++ __cxa_guard variable in .data ensuring one-time thread-safe construction of the sound decoder / text system singleto */
extern u32 g_regexCharDispatchTable[96];             /* 0x007AF2E0 conf 0.95: 96-entry function pointer dispatch table in .data used by Regex_ParseTokenStream to dispatch character tokens to per-cha */
extern u32 g_guardSoundRegistrySingleton;            /* 0x007B0044 conf 0.95: C++ __cxa_guard variable in .data ensuring one-time construction of the sound/text notification registry list head at 0x */
extern u16 g_msgFormatWideStringPattern[4];          /* 0x007C015E conf 0.95: UTF-16LE format specifier string ('%ls') in .data used by Text_FormatRecordName to format wide-character names into mess */
extern s32 g_textGlyphVertexOffsetBias;              /* 0x007C0198 conf 0.75: Signed 32-bit vertex offset bias in .data added to vertex buffer destination offsets in Text_BuildGlyphQuads. */
extern u16 g_kanaNameNormalizeChars[16];             /* 0x007C2204 conf 0.85: UTF-16LE string table in .data containing composite Japanese Katakana/Hiragana pairs (e.g. ヴ vs う+゛) used for name compa */
extern u16 g_msgLineStringBuffer[128];               /* 0x007C54DC conf 0.95: 128-wide-character (256-byte) string buffer in .bss used by Text_CopyMessageLine as shared scratch space when copying me */
extern u32 g_msgArgFormatStreamHeader;               /* 0x007C55DC conf 0.90: Control/stream header word in .bss directly preceding the formatted message argument buffer at 0x007C55E0. */
extern u16 g_msgArgFormatStringBuffer[64];           /* 0x007C55E0 conf 0.95: 64-wide-character (128-byte) string buffer in .bss containing the formatted message argument string returned by Text_For */
extern u16 g_msgArgStripBreaksBuffer[64];            /* 0x007C5660 conf 0.95: 64-wide-character (128-byte) scratch buffer in .bss used by Text_FormatMessageArg to filter out CR/LF line breaks from r */
extern u16 g_msgLineBreakExpandedBuffer[128];        /* 0x007C56E0 conf 0.95: 128-wide-character (256-byte) string buffer in .bss populated by Text_ExpandLineBreak when expanding embedded newline co */
extern u32 g_soundDecoderSingletonInstance[8];       /* 0x007E8100 conf 0.85: Static singleton instance in .bss constructed by 0x0054EFB0 under protection of guard variable 0x007AECDC. */
extern u32 g_animTimelineTypeDispatchTable[8];       /* 0x007E8120 conf 0.85: 8-entry function pointer dispatch table in .bss indexed by animation timeline type byte to invoke per-type timeline upda */
extern u32 g_soundNotificationRegistryList[4];       /* 0x007F2590 conf 0.85: Intrusive list head in .bss holding registered callback handlers for sound/text notification events, guarded by 0x007B00 */
extern u8 g_textLayoutStorageBuffer[128];            /* 0x00833CA7 conf 0.95: 128-byte static buffer in .bss aligned to 16 bytes and constructed as the text layout manager object (vtable 0x007829CC) */

/* --- Ui --- */
extern void* g_uiLayoutConfigCallbackTable[26];      /* 0x007253B0 conf 0.85: Table of 13 callback function pointer pairs (function pointer and flags) used by maybe_Ui_ApplyLayoutConfig (0x00221AA8) */
extern u32 g_uiSubWidgetConfigDefaults[18];          /* 0x007255F4 conf 0.85: Array of 18 default configuration words (pairs of field offset and enable flag) copied by maybe_Ui_SubWidgetConfig_InitB */
extern char* g_uiWidgetVariantAnimationNames[6];     /* 0x00725830 conf 0.90: Table of 6 string pointers ('Nut', 'Sleep', 'Ecstacy', 'Nut', 'Mimic', 'Nut') used by maybe_Ui_Widget_PlayVariantAnimati */
extern void* g_uiWidgetPlacementInitConfig[4];       /* 0x00725C9C conf 0.80: Configuration descriptor table starting with callback 0x00319674 (Data_ResolveRecordPtrs) used by maybe_Ui_PlaceWidgetIn */
extern void* g_uiSpriteActorEntryVtable[40];         /* 0x00725CB4 conf 0.90: Primary and secondary virtual method table for 3D UI sprite actor instances, installed by maybe_Ui_SpriteActor_CreateEnt */
extern u8 g_uiListFreeSlotScanOrder0[4];             /* 0x00725D6C conf 0.85: 4-byte direction scan order {6, 4, 0, 2} used by maybe_Ui_List_FindFirstFreeSlot (0x003BD008) when searching for availab */
extern u8 g_uiListFreeSlotScanOrder1[4];             /* 0x00725D70 conf 0.85: 4-byte direction scan order {0, 6, 2, 4} used by maybe_Ui_List_FindFirstFreeSlot (0x003BD008) when searching for availab */
extern u8 g_uiListFreeSlotScanOrder2[4];             /* 0x00725D74 conf 0.85: 4-byte direction scan order {2, 0, 4, 6} used by maybe_Ui_List_FindFirstFreeSlot (0x003BD008) when searching for availab */
extern u8 g_uiListFreeSlotScanOrder3[4];             /* 0x00725D78 conf 0.85: 4-byte direction scan order {4, 2, 6, 0} used by maybe_Ui_List_FindFirstFreeSlot (0x003BD008) when searching for availab */
extern u32 g_uiCameraAnimWindowRowCallbacks[56];     /* 0x00726984 conf 0.90: Table of 8 camera animation window row callback descriptors (stride 0x1C) containing delegate callbacks and flags, bound */
extern void* g_uiRecipeBookCallbacks[8];             /* 0x00726A10 conf 0.85: Table of 4 recipe book menu callback function pointer pairs (0x006374F4, 0x00637568, 0x0063791C, 0x00637A14) used by may */
extern u16 g_battleAiActionPriorityOrder[20];        /* 0x00726A54 conf 0.85: Priority order table of 20 16-bit action/weapon category IDs terminated by 0xFFFF, evaluated by BattleAi_EvaluateCandida */
extern u8 g_cameraTargetFilterNone[2];               /* 0x007272A6 conf 0.85: Two-byte filter option flags {0, 0} passed as parameter 4 to Camera_IsCandidateVisible by maybe_Ui_ApplyRowLayoutDefault */
extern u8 g_uiSlotKindMapping[12];                   /* 0x00727390 conf 0.85: Lookup table of 12 slot classification mapping bytes used by Ui_SlotTable_MarkSlotsByKind (0x003DA7D8) to match slot typ */
extern u16 g_uiSceneFlowDefaultLayerIndices[6];      /* 0x007275D0 conf 0.85: Array of 6 16-bit layer indices ({0xFFFF, 2, 1, 0xFFFF, 0xFFFF, 0xFFFF}) loaded by Ui_SceneFlow_SetLayerVisible (0x0019F */
extern void* g_fieldGadgetMotionDescriptor[4];       /* 0x007283E4 conf 0.85: 4-word animation descriptor containing a pointer to ASCII string 'Act_00' (0x0078498C) and handler callback (0x0070D264) */
extern void* g_uiStatusListDispatchEntry[4];         /* 0x0072845C conf 0.80: 4-word descriptor entry pointing to callback 0x0070DBB0, read by maybe_Ui_BuildStatusList (0x00197D14) to configure stat */
extern void* g_uiChoiceActionCallbacks[4];           /* 0x00728550 conf 0.85: Callback descriptor table containing pointer to maybe_Ui_Choice_Start (0x003EB694), used by UI choice and marker compone */
extern void* g_uiSmithMenuCommandFilterEntry[2];     /* 0x00728580 conf 0.85: Two-word command filter descriptor {0xFFFFFFFF, 0x00625308} read by Ui_ListWindow_SelectEntry and Ui_SmithMenu_HandleCom */
extern void* g_uiSmithMenuSelectRowCallbacks[4];     /* 0x00728584 conf 0.85: Callback pair descriptor {0x00625308, 0, 0x00710E00, 0} used by maybe_Ui_SmithMenu_CommitRow and maybe_Ui_SmithMenu_Sele */
extern u8 g_uiAttributeTextIndexMapping[8];          /* 0x007285B4 conf 0.85: 8-byte attribute index mapping table ({0, 1, 3, 2, 4, 0xFF, 5, 0xFF}) read by maybe_Ui_Panel_BuildAttributeText (0x004E7 */
extern void* g_uiListWindowStateInitCallbacks[4];    /* 0x007285BC conf 0.85: Callback descriptor {0x00625308, 0, 0, 0} read by maybe_Ui_ListWindow_InitState (0x00625A70) during list window state in */
extern void* g_uiListWindowSelectCallbacks[12];      /* 0x007285CC conf 0.90: Array of 6 callback descriptor pairs ({func, 0}) indexed by entry mode in Ui_ListWindow_SelectEntry (0x006258B0) to disp */
extern void* g_uiMessageWindowTransitionCallbacks[12]; /* 0x007285FC conf 0.85: Table of transition and state handler function pointers (starting with 0x00313BCC and 0x00313270) read by Ui_MessageWind */
extern void* g_uiMessageWindowTextAnimCallbacks[8];  /* 0x0072860C conf 0.85: Table of text animation handler function pointers starting with 0x003B75F4 read by maybe_Ui_MessageWindow_SetTextByIdAni */
extern void* g_uiLayoutDefaultMethodTable[16];       /* 0x007286A0 conf 0.85: Table of default layout handler and callback function pointers copied by maybe_Ui_CopyDefaultLayoutTable (0x00326760) in */
extern void* g_uiOverlayEntryPlacementCallbacks[9];  /* 0x00728900 conf 0.85: Delegate callback table containing handlers 0x00319674 and 0x003BC8D8 used by maybe_Ui_Overlay_CheckEntryPlacement (0x00 */
extern s32 g_uiOverlayTargetColumnIndices[12];       /* 0x00728924 conf 0.85: Array of 12 target column/slot indices (-1, 0, 1, 2 repeated 3 times) indexed during cursor target searches in maybe_Ui_ */
extern s32 g_uiOverlayTargetRowIndices[16];          /* 0x00728954 conf 0.85: Array of 16 target row indices (four -1s, four 0s, four 1s, four 2s) paired with column indices in maybe_Ui_Overlay_Find */
extern u32 g_uiOverlayTargetFlags[8];                /* 0x00728A04 conf 0.85: Table of 8 target active/validity flag words read by maybe_Ui_Overlay_FindTargetUnderCursor (0x006358C8). */
extern s8 g_uiMessageScrollStepTable[4];             /* 0x00728A48 conf 0.80: 4-byte scroll step/direction configuration ({0, 1, -1, -1}) read by maybe_Ui_MessageWindow_UpdateTextScroll. */
extern void* g_creatorDefaultNames;                  /* 0x00728AB8 conf 0.95: Pointer to wide-character default hero names table containing 'ゆうぼん' (Yuji Horii), 'すぎやん' (Koichi Sugiyama), and 'アキーラ'  */
extern u32 g_uiPartyPanelDefaultMemberOrder[10];     /* 0x00728F3C conf 0.85: Default party member display order table initialized with -1 (0xFFFFFFFF) used by maybe_Ui_PartyPanel_BuildMemberOrder ( */
extern void* g_uiCreditWindowCallbackTable[10];      /* 0x00728FCC conf 0.90: Table of credit window handler callbacks and resource state values starting with Ui_CreditWindow_LoadPageResources (0x00 */
extern void* g_uiCreditWindowReleaseOffsets[8];      /* 0x00728FD4 conf 0.85: Table of reset callback and state words loaded by Ui_CreditWindow_Release (0x002128D0) into credit window fields +0x30.. */
extern void* g_uiTextScrollRowLayoutConfig[12];      /* 0x0072900C conf 0.85: Configuration descriptor starting with line spacing float 16.0f (0x41800000) followed by 6 row layout helper callbacks,  */
extern u32 g_uiDefaultPartTransform[2];              /* 0x007291E0 conf 0.85: Two-word default transform / coordinate block ({0, 0}) copied into part offsets +0x11C/+0x120 by maybe_Ui_CopyDefaultTra */
extern u32 g_uiStpassCallVipMsgInitState[2];         /* 0x007291E8 conf 0.85: Two-word initialization descriptor ({0, 0}) read by Ui_StpassCallVipMsg_Create (0x0021193C) during StreetPass VIP messag */
extern void* g_uiHandleListInitCallbacks[4];         /* 0x00729250 conf 0.85: 4-word descriptor table containing constructor callback 0x00444DFC used by maybe_Container_HandleList_Ctor (0x00444DC0)  */
extern u8 g_uiSixRowChildIndices[6];                 /* 0x00729278 conf 0.85: 6-byte sequence {0, 1, 2, 3, 4, 5} used by maybe_Ui_SixRowChildLayout_Start (0x0020A864) to iterate over child elements  */
extern void* g_uiMessageWindowPageNavCallbacks[12];  /* 0x00729288 conf 0.85: Table of page navigation callback descriptors used by maybe_Ui_MessageWindow_AdvancePage and maybe_Ui_MessageWindow_Prep */
extern void* g_uiBigWindowCtorBaseCallbacks[8];      /* 0x007292A8 conf 0.85: Callback pair descriptor {0x00365DD8, 0, 0x003695A0, 0...} used by Ui_BigWindow_CtorBase (0x003660DC) to register node l */
extern void* g_uiGuideWindowPageCallbacks[25];       /* 0x007292B0 conf 0.85: Table of guide window page handler callbacks and descriptors starting with 0x003695A0 and 0x0036949C, used across Ui_Gui */
extern void* g_uiStampBookWindowCtorDescriptor[4];   /* 0x00729328 conf 0.85: Stamp book window constructor descriptor loaded in Ui_StampBookWindow_Ctor */
extern u8 g_uiDiveStartPaletteBytes[8];              /* 0x007294C8 conf 0.85: Palette entry byte mapping loaded in maybe_Ui_DiveStartWindow_GetPaletteEntry */
extern void* g_uiCasinoPrizeWindowNodeCallbacks[12]; /* 0x007294D0 conf 0.85: Node list callback descriptor pair {0x001E5A4C, 0, 0x001E5A08, 0...} loaded into prize window nodes by Ui_CasinoPrizeWin */
extern void* g_uiCasinoWindowStackCallbacks[6];      /* 0x00729538 conf 0.85: Table of casino window stack callbacks starting with 0x0023FCDC used by Ui_CasinoWin_PopWindowStack and Ui_CasinoWindow_ */
extern u16 g_uiItemScreenCheckItemId;                /* 0x00729550 conf 0.85: Special item ID 0x0139 (decimal 313) checked by maybe_Ui_ItemScreen_Confirm (0x001BFEB4) when validating item usage. */
extern void* g_uiItemScreenSelectCallbacks[14];      /* 0x00729554 conf 0.85: Table of item screen selection transition callbacks (starting with clamp limit 9999999 and callback 0x001C0A8C) read by  */
extern void* g_uiShopItemListBuyCallbacks[18];       /* 0x007295C0 conf 0.85: Shop item list purchase transition callbacks and state values read by maybe_Ui_ShopItemList_BeginBuy and maybe_Ui_ShopIt */
extern u32 g_uiResultRowRenderConfig[10];            /* 0x0072960C conf 0.85: Row rendering descriptor table with flags and filter callback 0x0066CD14 (stride 0x1C) read by maybe_Ui_Result_AdvanceTo */
extern u8 g_uiShopItemRecordOffsets[4];              /* 0x0072975C conf 0.85: 4-byte offset table {2, 4, 6, 8} into item data records used by Ui_ShopWindow_SetupItemName (0x0037F6F8) to index string */
extern void* g_uiShopWindowStateCallbacks[4];        /* 0x007297BC conf 0.85: Shop window event callback descriptor {0x001C1098, 0, 0x001C10CC, 0} read by Ui_ShopWindow_Ctor and Ui_Window_OnActiveSt */
extern u32 g_uiShopWindowPanelConfig[4];             /* 0x007297E4 conf 0.85: 4-word shop window panel initialization descriptor {0, 0, 0xFF020100, 0x00382AF8} copied during Ui_ShopWindow_Ctor (0x00 */
extern void* g_uiMessageSelectWindowDtorCallbacks[4]; /* 0x007297F0 conf 0.85: Callback descriptor {0x00382AF8, 0, 0x00382ACC, 0} read during message select window destructor Ui_MessageSelectWindow_D */
extern void* g_uiMessageSelectWindowHandles[4];      /* 0x00729810 conf 0.80: Zero-initialized descriptor table read by Ui_MessageSelectWindow_Ctor (0x003831B0) to clear handle slots. */
extern void* g_uiLoadingScreenTransitionCallbacks[4]; /* 0x00729A04 conf 0.85: Transition callback descriptor {0x001B65EC, 0, 0x001B68E4, 0} read by Ui_LoadingScreen_Create and maybe_Ui_LoadingScreen */
extern void* g_uiCampMenuPaneDescriptor[4];          /* 0x00729A24 conf 0.85: Camp menu pane push descriptor {0x00176BAC, 0, 0x00176AD8, 0} read by Ui_CampMenu_Setup and maybe_Ui_UpdateChildObject. */
extern void* g_uiCreateMessageWindowDescriptor[4];   /* 0x00729A5C conf 0.85: Message window creation descriptor {0x00195F8C, 0, 0, 0} read by Ui_CreateMessageWindow (0x001962F0). */
extern u8 g_uiTxtOnlyOptionIndices[8];               /* 0x00729A74 conf 0.85: Option text index mapping bytes {0x34, 0x36, 0x38, 0x3A, 0x3C, 0x3E, 0xFF, 0xFF} read by Ui_TxtOnlyWindow_SetOptionText  */
extern void* g_uiEquipmentWindowPaneDescriptor[4];   /* 0x00729A7C conf 0.85: Equipment window pane push descriptor {0x0019B338, 0, 0x001994F4, 0} read across Ui_EquipmentWindow methods. */
extern void* g_uiEquipmentWindowStateCallbacks[12];  /* 0x00729ACC conf 0.85: Table of equipment window action callbacks (starting with state 0x00020100 and callback 0x00199E30) read during equipmen */
extern void* g_uiEquipmentWindowPopPaneIds[4];       /* 0x00729AD4 conf 0.85: Pane identifier pair {0x00199E30, 0, 0x0019A890, 0} passed to Ui_Window_PopPaneUntilId by Ui_EquipmentWindow_Confirm. */
extern u8 g_uiTwoChoiceCategoryIndices[16];          /* 0x00729B3C conf 0.85: Table of category mapping bytes used by maybe_Ui_TwoChoiceDialog_Init and maybe_Ui_TwoChoiceDialog_SetPage to select dia */
extern void* g_uiSortListWindowDtorDescriptor[4];    /* 0x00729B88 conf 0.80: Zero-initialized descriptor table read by Ui_SortListWindow_Dtor (0x004488D0) during sort list window cleanup. */
extern void* g_uiEquipWindowPanePushDescriptors[4];  /* 0x00729B98 conf 0.85: Equipment window pane push descriptor {0x003341AC, 0, 0x00333BEC, 0} read across Ui_EquipWindow methods. */
extern void* g_uiEquipWindowPopPaneIds[4];           /* 0x00729BA0 conf 0.85: Pane identifier pair {0x00333BEC, 0, 0x00334B84, 0} passed to Ui_Window_PopPaneUntilIdB in Ui_EquipWindow_UpdatePaneAndP */
extern void* g_uiEquipWindowCursorMoveCallbacks[4];  /* 0x00729BB8 conf 0.85: Cursor movement callback pair {0x00334580, 0, 0x0033537C, 0} dispatched by Ui_EquipWindow_MoveCursor (0x0033503C). */
extern void* g_uiEquipWindowCallbackPair[4];         /* 0x00729BD0 conf 0.85: Callback pair {0x00333FD8, 0, 0x003343D8, 0} executed by maybe_Ui_EquipWindow_PopPaneAndRunCallbacks (0x00334B50). */
extern void* g_uiEquipWindowReleaseDescriptor[4];    /* 0x00729C00 conf 0.80: Zero-initialized descriptor table read by maybe_Ui_EquipWindow_ReleaseCallbacks (0x00333FA8) during callback reset. */
extern s32 g_uiEquipWindowDefaultSlotIds[3];         /* 0x00729C10 conf 0.85: Default slot index array {-1, -1, -1} loaded by Ui_EquipWindow_RebuildSlotText (0x00334A68) when initializing slot text. */
extern void* g_uiEquipTextWindowLayoutCallbacks[4];  /* 0x00729C1C conf 0.85: Layout callback pair {0x0039DA6C, 0, 0x0039D48C, 0} read by Ui_EquipTextWindow_Ctor and Ui_Window_LayoutTransition. */
extern void* g_uiEquipTextWindowDtorDescriptor[4];   /* 0x00729C34 conf 0.80: Zero-initialized descriptor table read by Ui_EquipTextWindow_Dtor (0x0039EF70) during cleanup. */
extern void* g_uiEquipPanelCompareArrowDescriptor[4]; /* 0x00729C54 conf 0.85: Descriptor table {0, 0, 0x00666F30, ...} read by maybe_Ui_EquipPanel_UpdateCompareArrows (0x0039DA34). */
extern u8 g_uiCompareMarkGlyphs[6];                  /* 0x00729C60 conf 0.90: 6-byte glyph index mapping {0x5C, 0x5D, 0x5E, 0x5F, 0x60, 0x61} read by maybe_Ui_GridWindow_SetCompareMark (0x0046D5E4)  */
extern void* g_uiJumonWindowPaneDescriptors[4];      /* 0x00729C68 conf 0.85: Spell/magic (Jumon) window pane push descriptor {0x0019C9E8, 0, 0x0019CB30, 0} read by Ui_JumonWindow_InitPanes. */
extern void* g_uiDialogRootCreateDescriptor[4];      /* 0x00729C78 conf 0.80: Zero-initialized descriptor table read by maybe_Ui_DialogRoot_Create (0x0019CC80). */
extern u8 g_uiEquipSlotBestPriorityOrder[8];         /* 0x00729C80 conf 0.85: Priority sequence {0, 1, 2, 3, 4, 0xFF, 0xFF, 0xFF} read by maybe_Ui_EquipWindow_UpdateBestItems (0x00296B20) to scan eq */
extern void* g_uiMainWindowPaneIds[4];               /* 0x00729C88 conf 0.85: Main menu window pane identifiers {0x00292FBC, 0, 0, 0} read by Ui_MainWindow_BindPanes (0x00292FA4). */
extern void* g_uiMainWindowCtorDescriptor[4];        /* 0x00729C90 conf 0.85: Descriptor table {0, 0, 0x00368F1C, 0} read by maybe_Ui_MainWindow_Ctor (0x00293630). */
extern void* g_uiMainMenuTextStateCallbacks[8];      /* 0x00729CB0 conf 0.85: Main menu text handler callbacks {0x002F6A64, 0, 0x002BC788, 0...} read by maybe_Ui_MainMenuText_Ctor and maybe_Ui_MainM */
extern void* g_uiMainMenuTextReleaseDescriptor[4];   /* 0x00729D18 conf 0.80: Zero-initialized descriptor table read by Ui_MainMenuText_ReleaseResources (0x002BD530). */
extern void* g_uiItemInfoWindowDtorDescriptor[4];    /* 0x00729D20 conf 0.80: Zero-initialized descriptor table read by Ui_ItemInfoWindow_Dtor (0x004528C0) during cleanup. */
extern void* g_uiPlateWidgetRowInitCallbacks[4];     /* 0x00729D38 conf 0.85: Plate widget row initialization callbacks {0x00229154, 0, 0x002290BC, 0} read by maybe_Ui_PlateWidget_InitRows (0x002297 */
extern void* g_uiPanelMessageWindowCtorDescriptor[4]; /* 0x00729D90 conf 0.80: Zero-initialized descriptor table read by maybe_Ui_PanelMessageWindowCtor (0x002298A8). */
extern u32 g_uiRowListIndicesSet0[3];                /* 0x00729DB8 conf 0.85: Row index sequence {6, 7, 8} read by maybe_Ui_RowList_PopulateRows (0x00229440) for populating row layouts. */
extern u32 g_uiRowListIndicesSet1[4];                /* 0x00729DC4 conf 0.85: Row index sequence {0, 2, 9, 10} read by maybe_Ui_RowList_PopulateRows (0x00229440) for populating row layouts. */
extern u32 g_uiRowListIndicesSet2[4];                /* 0x00729DD4 conf 0.85: Row index sequence {0, 1, 2, 9} read by maybe_Ui_RowList_PopulateRows (0x00229440) for populating row layouts. */
extern u32 g_uiRowListIndicesSet3[4];                /* 0x00729DE8 conf 0.85: Row index sequence {0, 1, 2, 3} read by maybe_Ui_RowList_PopulateRows (0x00229440) for populating row layouts. */
extern void* g_uiPanelMessageWindowCallbacks[8];     /* 0x00729E00 conf 0.85: Panel message window callback descriptors {0x003ABB98, 0, 0x003ABB58, 0...} read by Ui_PanelMessageWindow_LoadPanels and */
extern void* g_uiMessagePartTableDtorDescriptor[4];  /* 0x00729E68 conf 0.80: Zero-initialized descriptor table read by maybe_Ui_MessagePartTable_Dtor (0x003E3A70) during cleanup. */
extern void* g_uiPanelMessageWindowCtorExDescriptor[4]; /* 0x00729E70 conf 0.80: Zero-initialized descriptor table read by Ui_PanelMessageWindow_Ctor and Ui_PanelMessageWindow_CtorEx. */
extern u32 g_uiPanelMessageWindowPanelIndices[4];    /* 0x00729EA0 conf 0.85: Panel index array {0, 0, 0x12, 0x13} read by Ui_PanelMessageWindow_LoadPanels (0x001DF000). */
extern u32 g_uiPartAnimSlotIndices[4];               /* 0x00729EA8 conf 0.85: Animation slot index array {0x12, 0x13, 0x14, 0x15} read by maybe_Ui_Part_CheckAnimConditions and maybe_Ui_Part_GetAnimS */
extern void* g_uiPlatePlayerTitleStrPtrA;            /* 0x00729EC8 conf 0.85: Pointer to title formatting string (0x00666F78) read by maybe_Ui_Plate_FormatPlayerTitle (0x00646FC8). */
extern void* g_uiPlatePlayerTitleStrPtrB;            /* 0x00729ED4 conf 0.85: Pointer to title formatting string (0x00666FA4) read by maybe_Ui_Plate_FormatPlayerTitle (0x00646FC8). */
extern void* g_uiPlatePlayerTitleStrPtrC;            /* 0x00729EE0 conf 0.85: Pointer to title formatting string (0x00666F4C) read by maybe_Ui_Plate_FormatPlayerTitle (0x00646FC8). */
extern void* g_uiMessagePartTableElementCallbacks[12]; /* 0x00729EE4 conf 0.85: Table of message part element callbacks starting with 0x003E1AF4 and 0x003E1B58, read across Ui_MessagePartTable routine */
extern void* g_uiMessagePartTableCreateDescriptor[4]; /* 0x00729F74 conf 0.80: Zero-initialized descriptor table read by maybe_Ui_MessagePartTable_Create and maybe_Ui_MessagePartTable_Ctor. */
extern void* g_uiMessagePagePartDescriptors[4];      /* 0x00729F84 conf 0.85: Message page part descriptors {0, 0x00785270, 0x00785158, 1} read by Ui_MessagePage_SetupParts (0x003E1FA8). */
extern void* g_uiMessagePartTableSmallDescriptor[4]; /* 0x0072A000 conf 0.85: Descriptor table {0, 0, 0, 0x007853B4} read by maybe_Ui_MessagePartTable_CreateSmall (0x003E3570) containing pointer to  */
extern void* g_uiSkillPanelStateCallbacks[8];        /* 0x0072A050 conf 0.85: Skill panel state transition callbacks {0x0036E870, 0, 0x0036E8A4, 0...} read across Ui_SkillPanel routines. */
extern void* g_uiSkillPanelStateDescriptors[4];      /* 0x0072A088 conf 0.85: Skill panel state descriptors {0, 0, 0x0036F190, 0} read by Ui_SkillPanel_ApplyState (0x0036E530). */
extern void* g_uiSkillPanelCtorDescriptorA[4];       /* 0x0072A128 conf 0.80: Zero-initialized descriptor table read by Ui_SkillPanel_Ctor (0x0036F9F4). */
extern void* g_uiSkillPanelCtorDescriptorB[4];       /* 0x0072A148 conf 0.80: Zero-initialized secondary descriptor table read by Ui_SkillPanel_Ctor (0x0036F9F4). */
extern void* g_uiSkillPanelCtorDescriptorC[4];       /* 0x0072A150 conf 0.85: Descriptor table {0, 0, 0x003AC930, 0} read by Ui_SkillPanel_Ctor (0x0036F9F4) containing callback 0x003AC930. */
extern void* g_uiSkillPanelWindowPaneDescriptors[8]; /* 0x0072A158 conf 0.85: Skill panel window pane push descriptors {0x003AC930, 0, 0x003AC780, 0...} read across Ui_SkillPanelWindow methods. */
extern void* g_uiSkillPanelWindowCtorDescriptor[4];  /* 0x0072A1C0 conf 0.80: Zero-initialized descriptor table read by Ui_SkillPanelWindow_Ctor (0x003AD068). */
extern void* g_uiPartAnimRecordDescriptors[4];       /* 0x0072A1E0 conf 0.85: Part animation record setup descriptors {0x00785488, 0, 0x00785424, 1} read by Ui_Part_SetupFromAnimRecord (0x001B9394). */
extern void* g_uiPresentWindowCallbacks[4];          /* 0x0072A1F0 conf 0.85: Present window update callbacks {0x003796EC, 0, 0, 0} read across Ui_PresentWindow routines. */
extern void* g_uiMessagePanelStateCallbacks[8];      /* 0x0072A210 conf 0.85: Message panel state transition callbacks {0x003B0A1C, 0, 0x003B0C44, 0...} read across maybe_Ui_MessagePanel routines. */
extern u32 g_uiWindowCtorDescriptor[4];              /* 0x0072A240 conf 0.85: Window initialization descriptor {0, 0, 0x0000FFFF, 0} read by maybe_Ui_Window_Ctor (0x003B11A4). */
extern void* g_uiRecordWindowUpdateCallbacks[4];     /* 0x0072A270 conf 0.85: Record window update callbacks {0x0037BF0C, 0, 0x05F5E0FF, 0x001E8790} read by Ui_RecordWindow_Update (0x0037BE50). */
extern void* g_uiRowListPageDrawCallbacks[4];        /* 0x0072A27C conf 0.85: Row list page draw callbacks {0x001E8790, 0, 0x0037D1EC, 0} read by Ui_RowList_DrawPage (0x001E86E8). */
extern void* g_uiPresentPanelDisplayCallbacks[8];    /* 0x0072A284 conf 0.85: Present panel display resolution callbacks {0x0037D1EC, 0, 0x0037D4C0, 0...} read across Ui_PresentPanel routines. */
extern void* g_uiSenrekiWindowCtorCallback[4];       /* 0x0072A2BC conf 0.85: Battle records (Senreki) window constructor callback {0x00296C7C, 0, 0, 0} read by Ui_SenrekiWindow_Ctor (0x00296E58). */
extern void* g_uiMonsterBookInitDescriptor[4];       /* 0x0072A2D4 conf 0.85: Monster book initialization descriptor {0x0001869F, 0x00418478, 0, 0} read by Ui_MonsterBook_InitData (0x00419D40). */
extern void* g_uiMonsterBookEntryDtorDescriptor[4];  /* 0x0072A2E0 conf 0.80: Zero-initialized descriptor table read across maybe_Ui_MonsterBook_EntryDtor routines. */
extern void* g_uiSenrekiWindowRowDescriptor[4];      /* 0x0072A2E8 conf 0.85: Senreki window row descriptor {0, 0, 0x00241D0C, 0} read by Ui_SenrekiWindow_CtorRow (0x00419EA0). */
extern void* g_uiMonsterBookWindowCallbacks[8];      /* 0x0072A2F0 conf 0.85: Monster book window callbacks {0x00241D0C, 0, 0x00241650, 0...} read across Ui_MonsterBookWindow routines. */
extern void* g_uiMonsterBookWindowReleaseDescriptor[4]; /* 0x0072A308 conf 0.80: Zero-initialized descriptor table read by Ui_MonsterBookWindow_Release (0x002430CC). */
extern void* g_uiFaceIconModelCallbacks[8];          /* 0x0072A320 conf 0.85: Face icon and monster model display callbacks {0x00243C84, 0, 0x00244178, 0...} read across character and monster displa */
extern void* g_uiPanelGroupPushCallbacks[4];         /* 0x0072A340 conf 0.85: Panel group push callback pair {0x001BB13C, 0, 0x001BB798, 0} read by maybe_Ui_PanelGroup_Push (0x001BB044). */
extern void* g_uiRowListRowStateCallbacks[4];        /* 0x0072A348 conf 0.85: Row list row state callback pair {0x001BB798, 0, 4, 12} read by maybe_Ui_RowList_SetRowState (0x001BB564). */
extern u32 g_uiStoryListModelRowOffsets[4];          /* 0x0072A350 conf 0.85: Story list model row field offsets {4, 12, 20, 28} read by Ui_StoryListWindow_BindRowModels (0x002C5424). */
extern u32 g_uiStoryListModelRowIndices[4];          /* 0x0072A360 conf 0.85: Story list model row base indices {0, 8, 16, 24} read by Ui_StoryListWindow_BindRowModels (0x002C5424). */
extern u8 g_uiSenrekiCategoryIndices[8];             /* 0x0072A378 conf 0.85: Category index sequence {8, 13, 9, 10, 11, 12, 14, 0} read by Ui_SenrekiWindow_BuildPanes (0x00297528). */
extern void* g_uiSenrekiWindowCtorBDescriptor[4];    /* 0x0072A388 conf 0.85: Descriptor table {0, 0, 0x001C25E8, 0} read by maybe_Ui_SenrekiWindow_CtorB (0x00297AA0). */
extern void* g_uiJumonWindowActionCallbacks[8];      /* 0x0072A390 conf 0.85: Spell/magic (Jumon) window action callbacks {0x001C25E8, 0, 0x001C24C4, 0...} read across Ui_JumonWindow routines. */
extern void* g_uiTsuyosaWindowCtorCallback[4];       /* 0x0072A568 conf 0.85: Status (Tsuyosa) window constructor callback {0x002A007C, 0, 0, 0} read by maybe_Ui_TsuyosaWindow_CreateInstance (0x002A */
extern char* g_uiProfileWindowRowTitleNames[8];      /* 0x0072A580 conf 0.90: Table of 8 string pointers to profile row title strings in .rodata (0x007855A0, 0x007855BC...) read by maybe_Ui_ProfileW */
extern void* g_uiTsuyosaWindowPaneCallbacks[8];      /* 0x0072A5A0 conf 0.85: Tsuyosa window pane callbacks {0x002A0BE0, 0, 0x003F12D0, 0...} read across Ui_TsuyosaWindow routines. */
extern void* g_uiTsuyosaWindowCtorDescriptor[4];     /* 0x0072A5C0 conf 0.85: Descriptor table {0, 0, 0x002A050C, 0} read by Ui_TsuyosaWindow_Ctor (0x002A1078). */
extern void* g_uiTsuyosaWindowPaneDescriptors[4];    /* 0x0072A5C8 conf 0.85: Tsuyosa window pane descriptors {0x002A050C, 0, 0x002A0D48, 0} read by Ui_TsuyosaWindow_Update and Ui_TsuyosaWindow_Upda */
extern void* g_uiSakusenWindowPaneCallbacks[8];      /* 0x0072A600 conf 0.85: Tactics (Sakusen) window pane callbacks {0x002A31D4, 0, 0x002A2E70, 0...} read across Ui_SakusenWindow routines. */
extern void* g_uiSakusenWindowPaneDescriptors[4];    /* 0x0072A610 conf 0.85: Sakusen window pane descriptors {0x002A16E8, 0, 0x002A2C94, 0} read by maybe_Ui_SakusenWindow_CloseDetail. */
extern u8 g_uiPanelStateIconLookupTable[16];         /* 0x0072A6E8 conf 0.85: State icon lookup byte array indexed by state in Ui_Panel_SetStateIcon */
extern u8 g_uiPartyIconRowIndices[10];               /* 0x0072A6F3 conf 0.85: Party member icon row index bytes used in maybe_Ui_CommandList_BuildRows and maybe_Ui_PartyIconRow_Refresh */
extern void* g_uiScreenTransitionLayerCallbacks[8];  /* 0x0072A79C conf 0.85: Screen transition and fade layer callbacks table used in Ui_ScreenTransition_CreateLayers and Ui_Transition_CreateFadeQu */
extern u32 g_uiStyleParamFieldOffsets[8];            /* 0x0072A87C conf 0.85: Array of style parameter field offsets (8, 0xC, 0x10, 0x14...) in maybe_Ui_Entry_FillStyleParam */
extern void* g_uiPanelRowSelectionCallbacks[8];      /* 0x0072A8A4 conf 0.85: Panel row selection and card slot callbacks table in Ui_Panel_UpdateRowData and Ui_Panel_UpdateRowSelection */
extern void* g_uiPokerCardSlotCallbacks[8];          /* 0x0072A8EC conf 0.85: Poker card row and slot callbacks {0x00294C8C, 0, 0x00295280, 0...} read across poker and casino card UI routines. */
extern void* g_uiPartyPanelSlotObjectCallbacks[35];  /* 0x0072A944 conf 0.85: Table of party panel slot object and cursor position callbacks (starting with 0x001E2DA4 and 0x001E2444) read across par */
extern void* g_uiPanelRowSelectCallbacks[4];         /* 0x0072A9E4 conf 0.85: Panel row selection callbacks {0x001E30D8, 0, 0x001E3330, 0} read by Ui_Panel_UpdateRowSelection (0x001E2A74). */
extern void* g_uiPokerWindowCtorDescriptor[4];       /* 0x0072AA04 conf 0.85: Poker window constructor descriptor {0x001E2808, 0, 0x002C7584, 0} read by Ui_PokerWindow_Ctor (0x001E4498). */
extern void* g_uiJackpotScreenCallbacks[8];          /* 0x0072AA0C conf 0.85: Casino jackpot screen animation and display callbacks {0x002C7584, 0, 0x002C6F74, 0...} read across Ui_JackpotScreen rou */
extern u32 g_uiJackpotScreenPayoutSlotIndices[8];    /* 0x0072AABC conf 0.85: Jackpot screen payout slot indices {0, 21, 4, 14, 8, 12, 16, 20} read by maybe_Ui_JackpotScreen_StartPayout (0x002C7510) */
extern u32 g_uiJackpotScreenPayoutMultipliers[8];    /* 0x0072AB2C conf 0.85: Jackpot screen payout multiplier sequence {15, 13, 19, 13, 20, 15, 10, 5} read by maybe_Ui_JackpotScreen_StartPayout (0x */
extern void* g_uiSlotPlateNumberCallbacks[8];        /* 0x0072ABA8 conf 0.85: Casino slot machine plate digit display callbacks {0x004C3138, 0, 0x004C32A0, 0...} read across Ui_SlotPlate routines. */
extern void* g_uiSlotWindowAnimationCallbacks[8];    /* 0x0072ABF8 conf 0.85: Slot machine window reel animation callbacks {0x003805B4, 0, 0, 0...} read across Ui_SlotWindow routines. */
extern void* g_uiHitIconSpriteNamePointers[40];      /* 0x0072AC98 conf 0.85: Array of 40 pointer pairs to hit icon sprite descriptors and names used in Ui_HitIcon_CreateSprites and Ui_HitIcon_Rebui */
extern void* g_uiPartyGaugeWindowPaneNames[8];       /* 0x0072AE6C conf 0.85: Array of 8 pane name string pointers initialized in Ui_PartyGaugeWindow_InitPanes */
extern u32 g_uiTwoColumnListRowIndices[16];          /* 0x0072AEDC conf 0.85: Pane index table (1, 4, 7, 10...) for two-column list layout initialization in Ui_TwoColumnListWindow_InitPanes */
extern void* g_uiWidgetLinkCallbackPair[4];          /* 0x0072AF1C conf 0.80: Callback table used in maybe_Ui_Widget_LinkCallbacks to set widget link handlers */
extern void* g_uiWidgetInstanceCtorDescriptor[4];    /* 0x0072AF3C conf 0.80: Widget construction descriptor structure loaded in maybe_Ui_Widget_CreateInstance */
extern void* g_uiDiveManagerCtorCallback[4];         /* 0x0072AF4C conf 0.80: Constructor callback and vtable descriptor pointer loaded in maybe_Ui_DiveManager_Ctor */
extern void* g_uiDiveManagerDtorDescriptor[4];       /* 0x0072AF54 conf 0.80: Destructor descriptor structure loaded in maybe_Ui_DiveManager_Dtor */
extern u8 g_uiChildTableMappingBytes[8];             /* 0x0072B09C conf 0.80: Byte mapping table used in maybe_Ui_GetTableByteByChild to translate child indices to table slots */
extern void* g_uiUpdateCallbackPair[4];              /* 0x0072B0A4 conf 0.80: Function pointer pair passed to UI update callback binder in maybe_Ui_BindUpdateCallback */
extern u32 g_uiEightRowWindowPaneOrder[8];           /* 0x0072B0D4 conf 0.85: Index array (1, 5, 2, 6, 3, 7, 4, 8) ordering panes in Ui_EightRowIndexedWindow_InitPanes */
extern u32 g_uiUmaWindowPanelInitDescriptor[4];      /* 0x0072B204 conf 0.80: Initialization descriptor for horse race (Uma) UI panel in maybe_Ui_UmaWindow_InitPanel */
extern u8 g_uiUmaWindowPageSelectTable[6];           /* 0x0072B220 conf 0.85: Page validation byte table for horse race (Uma) window in maybe_Ui_UmaWindow_SelectPage */
extern void* g_uiUmaWindowDtorDescriptor[4];         /* 0x0072B2F0 conf 0.80: Destructor descriptor structure for horse race (Uma) window in maybe_Ui_UmaWindow_Dtor */
extern void* g_uiWidgetBindCallbacks[4];             /* 0x0072B318 conf 0.80: Widget callback binding table in maybe_Ui_Widget_BindCallbacks */
extern void* g_uiListDtorCallbacks[4];               /* 0x0072B34C conf 0.80: List cleanup callbacks table in maybe_Ui_List_DtorWithArray */
extern void* g_uiTwoElementPanelCtorDescriptor[4];   /* 0x0072B36C conf 0.80: Two-element panel constructor descriptor in maybe_Ui_TwoElementPanel_Ctor */
extern void* g_uiAnimatableElementCtorDescriptor[4]; /* 0x0072B374 conf 0.80: Animatable element initialization descriptor in Ui_AnimatableElement_Ctor */
extern void* g_uiShopWindowPanelAttachCallbacks[4];  /* 0x0072B37C conf 0.80: Shop window panel attachment callback table in maybe_Ui_ShopWindow_AttachPanels */
extern void* g_uiShopWindowResetDescriptor[4];       /* 0x0072B384 conf 0.80: Shop window state reset descriptor in maybe_Ui_ShopWindow_ResetState */
extern void* g_uiShopWindowBindPanelCallbacks[4];    /* 0x0072B394 conf 0.80: Shop window panel bind callback table in maybe_Ui_ShopWindow_BindPanels */
extern void* g_uiAnimRefListInitDescriptor[4];       /* 0x0072B3B4 conf 0.80: Animation reference list initializer descriptor in maybe_Ui_AnimRefList_Init */
extern void* g_uiSingleElementPanelCtorDescriptor[4]; /* 0x0072B404 conf 0.80: Single-element panel constructor descriptor in maybe_Ui_SingleElementPanel_Ctor */
extern void* g_uiLayoutRefListDescriptor[4];         /* 0x0072B40C conf 0.80: Layout reference list descriptor in Ui_LayoutRef_InitList */
extern void* g_uiSmithMenuSubWindowCallbacks[4];     /* 0x0072B414 conf 0.80: Blacksmithing sub-window command callback table in Ui_SmithMenu_SubWindow_Ctor */
extern void* g_uiPageStackPushCallbacks[4];          /* 0x0072B42C conf 0.80: Page stack push callback descriptor in maybe_Ui_PageStack_Push */
extern void* g_uiSmithMenuCommandPaneCallbacks[8];   /* 0x0072B43C conf 0.80: Blacksmithing command pane callback array in Ui_SmithMenu_InitCommandPanes */
extern void* g_uiSmithMenuCommandPageCallbacks[4];   /* 0x0072B44C conf 0.80: Blacksmithing command page callbacks in Ui_SmithMenu_InitCommandPage */
extern void* g_uiSmithMenuPopPageDescriptor[4];      /* 0x0072B4E4 conf 0.80: Blacksmithing menu page popping descriptor in Ui_SmithMenu_PopPage */
extern void* g_uiSmithMenuCtorDescriptor[4];         /* 0x0072B4EC conf 0.80: Blacksmithing menu constructor descriptor in Ui_SmithMenu_Ctor */
extern void* g_uiHandleSetPaneNames[12];             /* 0x0072B540 conf 0.85: Array of 12 pane name pointers used in maybe_Ui_HandleSet_SetPaneNames */
extern void* g_uiHandleSetPaneNamesOffset1;          /* 0x0072B544 conf 0.70: Offset pointer within g_uiHandleSetPaneNames array referenced in maybe_Ui_HandleSet_SetPaneNames */
extern void* g_uiHandleSetPaneNamesOffset2;          /* 0x0072B548 conf 0.70: Offset pointer within g_uiHandleSetPaneNames array referenced in maybe_Ui_HandleSet_SetPaneNames */
extern u8 g_uiPartySelectModelRowIndices[8];         /* 0x0072B718 conf 0.85: Row index sequence for party selection model widget in maybe_Ui_PartySelect_InitRows */
extern void* g_uiChoiceWindowDtorDescriptor[4];      /* 0x0072B748 conf 0.80: Choice window destructor descriptor in maybe_Ui_ChoiceWindow_Dtor */
extern void* g_uiObjectWithListDtorDescriptor[4];    /* 0x0072B750 conf 0.80: Destructor descriptor for object containing a list in maybe_Ui_ObjectWithList_Dtor */
extern void* g_uiPartySelectFreeBlockDescriptor[4];  /* 0x0072B758 conf 0.80: Memory free block descriptor for party selection widget in maybe_Ui_PartySelect_FreeBlock */
extern u8 g_uiKyoukaiSlotListIndices[12];            /* 0x0072B7FC conf 0.85: Slot configuration byte array for church (Kyoukai) menu in maybe_Ui_Kyoukai_SelectEntry */
extern void* g_uiWindowStateTransitionCallbacks[18]; /* 0x0072B810 conf 0.85: Window state transition callback descriptor array (0x48 bytes) copied in maybe_Ui_ShopWindow_ResetToIdle and other windo */
extern void* g_uiMessageVoiceSeCallbacks[8];         /* 0x0072B858 conf 0.80: Voice sound effect callback array for message control codes (3D/3E/3F/42) in maybe_Ui_MessageWindow_PlayVoiceSe */
extern void* g_uiMessageStepQueuedByteDescriptor[4]; /* 0x0072B888 conf 0.80: Message window byte stepping descriptor in maybe_Ui_MessageWindow_StepNextQueuedByte */
extern void* g_uiMessageNextPageControlCallbacks[8]; /* 0x0072B898 conf 0.80: Next page control callbacks table in maybe_Ui_MessageWindow_ShowNextPageWithControls */
extern void* g_uiMessageBranchCallbacks[8];          /* 0x0072BA14 conf 0.80: Branch control callbacks table in maybe_Ui_MessageWindow_StepBranchOnFlag8 */
extern void* g_uiScrollListWindowDtorCallbacks[4];   /* 0x0072BF64 conf 0.80: Scroll list window destructor callbacks table in Ui_ScrollListWindow_Dtor */
extern char g_uiOptionIdentifierString[6];           /* 0x0072C01C conf 0.90: ASCII string './012' used as option identifier prefix in maybe_Ui_ChoiceWindow_ResetOptions */
extern void* g_uiListWidgetScreenCtorCallback[4];    /* 0x0072C3B8 conf 0.80: List widget screen constructor callback table in maybe_Ui_ListWidget_Screen_Ctor */
extern void* g_uiListWidgetScreenDtorDescriptor[4];  /* 0x0072C3C0 conf 0.80: List widget screen destructor descriptor in maybe_Ui_ListWidget_Screen_Dtor */
extern void* g_uiListWindow1F8DtorCallbacks[4];      /* 0x0072C498 conf 0.80: List window 0x1F8-size object destructor callbacks in Ui_ListWindow1F8_Dtor */
extern void* g_uiListWindow1F8CtorDescriptor[4];     /* 0x0072C4B8 conf 0.80: List window 0x1F8-size object constructor descriptor in maybe_Ui_ListWindow_Ctor1F8 */
extern void* g_uiDiveFormMessageCallbacks[8];        /* 0x0072C4C8 conf 0.80: Dive form message and input handling callbacks table in Ui_MessageWindow_CtorLayout2 and DiveForm handlers */
extern u32 g_uiDiveFormPageEntryConfig[18];          /* 0x0072C570 conf 0.85: Dive form page entry configuration block (0x48 bytes) copied in maybe_Ui_DiveForm_BuildPageEntries */
extern void* g_uiListWidgetRowRecordCallbacks[16];   /* 0x0072C5B8 conf 0.85: Function pointer array for list widget row record formatting callbacks in Ui_ListWidget_SetRowFromRecord */
extern void* g_uiPartyMemberRowPaneNames[8];         /* 0x0072C5F8 conf 0.85: Array of 8 pane name string pointers initialized in Ui_PartyMemberRow_BindPanesR */
extern void* g_uiMessageWindowCtorDescriptor[4];     /* 0x0072C6B0 conf 0.80: Message window construction descriptor structure loaded in Ui_MessageWindow_Ctor */
extern void* g_uiMessageWindowUpdateDescriptor[32];  /* 0x0072C6B8 conf 0.85: Message window update descriptor array loaded in Ui_MessageWindow_Update */
extern void* g_uiMessageWindowClearCallbacks[16];    /* 0x0072C738 conf 0.85: Message window cleanup callbacks table loaded in Ui_MessageWindow_ClearCallbacks */
extern f32 g_uiTalkWindowEventScale;                 /* 0x0072C784 conf 0.85: Scale constant (2.0f) loaded into talk window state field f_2a4 in maybe_Ui_TalkWindow_HandleEvent11 */
extern u8 g_uiWindowFrameSkinPartIndices[6];         /* 0x0072CC98 conf 0.85: Window frame skin part index bytes used in maybe_Ui_WindowFrame_ApplySkin */
extern u32 g_uiItemListRowDescriptor[16];            /* 0x0072CCB0 conf 0.85: Descriptor stride block for populating item list window rows in maybe_Ui_ItemListWindow_BuildRowsFromItem */
extern u32 g_uiRewardRowDescriptor[16];              /* 0x0072CD60 conf 0.85: Descriptor stride block for populating quest/battle reward rows in maybe_Ui_ListWindow_FillRewardRows */
extern u8 g_uiSlotGridSelectionBytes[8];             /* 0x0072D430 conf 0.85: Slot grid selection state validation bytes used in Ui_SlotGrid_SelectSlot and SakusenWindow */
extern void* g_uiSlotGridSelectionCallbacks[10];     /* 0x0072D43C conf 0.80: Selection handler callback array for slot grid in Ui_SlotGrid_SelectSlot */
extern void* g_uiTenRowModePaneSetupDescriptor[20];  /* 0x0072D464 conf 0.85: Pane setup descriptor list for 10-row mode window in maybe_Ui_TenRowModePanes_Setup */
extern void* g_uiSaveSlotEntryDescriptorsA[21];      /* 0x0072D4B4 conf 0.85: Save slot window entry descriptors block A used in Save_SlotUi_BuildEntry */
extern void* g_uiSaveSlotEntryDescriptorsB[20];      /* 0x0072D4FC conf 0.85: Save slot window entry descriptors block B used in Save_SlotUi_BuildEntry */
extern void* g_uiSaveSlotEntryDescriptorsC[20];      /* 0x0072D504 conf 0.85: Save slot window entry descriptors block C used in Save_SlotUi_BuildEntry */
extern void* g_uiSmithMenuSlotHandleDescriptor[4];   /* 0x0072D564 conf 0.85: Smithing menu slot handle descriptor used in maybe_Ui_System_Init and Ui_SmithMenu_SetSlotHandle */
extern void* g_uiSmithMenuPaneNameList0[4];          /* 0x0072D594 conf 0.85: Pane name pointer list 0 for blacksmithing slot layout in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuPaneNameList1[4];          /* 0x0072D5A4 conf 0.85: Pane name pointer list 1 for blacksmithing slot layout in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuPaneNameList2[4];          /* 0x0072D5B4 conf 0.85: Pane name pointer list 2 for blacksmithing slot layout in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategoryIconBase[4];       /* 0x0072D5C4 conf 0.85: Category icon pointer list in Ui_SmithMenu_SetCategoryIcons */
extern void* g_uiSmithMenuCategorySlotNamePtr0;      /* 0x0072D5D4 conf 0.80: Category slot name pointer entry 0 for blacksmithing menu in Ui_SmithMenu_SetCategoryIcons */
extern void* g_uiSmithMenuCategorySlotNamePtr1;      /* 0x0072D5E4 conf 0.80: Category slot name pointer entry 1 for blacksmithing menu in Ui_SmithMenu_SetCategoryIcons */
extern void* g_uiSmithMenuCategorySlotNamePtr2;      /* 0x0072D5F4 conf 0.80: Category slot name pointer entry 2 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategorySlotNamePtr3;      /* 0x0072D604 conf 0.80: Category slot name pointer entry 3 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategorySlotNamePtr4;      /* 0x0072D614 conf 0.80: Category slot name pointer entry 4 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategorySlotNamePtr5;      /* 0x0072D624 conf 0.80: Category slot name pointer entry 5 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategorySlotNamePtr6;      /* 0x0072D634 conf 0.80: Category slot name pointer entry 6 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategoryIconNamePtr0;      /* 0x0072D644 conf 0.80: Category icon name pointer entry 0 for blacksmithing menu in Ui_SmithMenu_SetCategoryIcons */
extern void* g_uiSmithMenuCategorySlotNamePtr7;      /* 0x0072D654 conf 0.80: Category slot name pointer entry 7 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategorySlotNamePtr8;      /* 0x0072D664 conf 0.80: Category slot name pointer entry 8 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategoryIconNamePtr1;      /* 0x0072D674 conf 0.80: Category icon name pointer entry 1 for blacksmithing menu in Ui_SmithMenu_SetCategoryIcons */
extern void* g_uiSmithMenuCategorySlotNamePtr9;      /* 0x0072D684 conf 0.80: Category slot name pointer entry 9 for blacksmithing menu in Ui_SceneFlow_ApplySlotLayout */
extern void* g_uiSmithMenuCategoryIconNamePtr2;      /* 0x0072D694 conf 0.80: Category icon name pointer entry 2 for blacksmithing menu in Ui_SmithMenu_SetCategoryIcons */
extern u8 g_uiSmithMenuCategorySlotFlags[18];        /* 0x0072D6B4 conf 0.85: Flag array indexed by category (stride 6) in Ui_SmithMenu_SetAllSlotHandles */
extern u8 g_uiWindowStateColorBytes[20];             /* 0x0072D6FC conf 0.85: Color/palette mapping bytes by window state in maybe_Ui_Window_SetColorByState */
extern u32 g_uiPicaFlushCmdPacket[16];               /* 0x0072F6A8 conf 0.90: 0x40-byte PICA200 GPU register command packet for flushing pipeline state in Ui_LayoutText_FlushDrawPacket */
extern u32 g_uiPicaRenderStatePacket[24];            /* 0x0072FAC4 conf 0.90: 0x60-byte PICA200 GPU register command packet for initializing UI layout render state in Ui_LayoutText_InitRenderState */
extern void* g_uiTextLayoutRunCallbacks[4];          /* 0x0072FB2C conf 0.80: Text run layout processing callbacks table in maybe_Ui_TextLayout_InsertRun */
extern char g_uiAnimBflanFormatStr[12];              /* 0x0072FB44 conf 0.95: Format string '%s_%s.bflan' for binary layout animation file names in Ui_AnimClip_Load */
extern char g_uiLayoutBflytFormatStr[9];             /* 0x0072FB50 conf 0.95: Format string '%s.bflyt' for binary layout file names in maybe_Ui_LayoutPlayer_CreateFromName */
extern u32 g_uiPicaTevStagePacket0[6];               /* 0x0073BB18 conf 0.90: 0x18-byte PICA200 GPU TEV stage combiner command packet 0 in Ui_LayoutText_PackTevStages */
extern u32 g_uiPicaTevStagePacket1[6];               /* 0x0073BB30 conf 0.90: 0x18-byte PICA200 GPU TEV stage combiner command packet 1 in Ui_LayoutText_SetupMaterialAndShading */
extern u32 g_uiPicaTextureFilterPacket0[6];          /* 0x0073BB48 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 0 in Ui_LayoutText_SetupTextureFilters */
extern u32 g_uiPicaTextureFilterPacket1[6];          /* 0x0073BB60 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 1 in Ui_LayoutText_SetupTextureFilters */
extern u32 g_uiPicaTextureFilterPacket2[6];          /* 0x0073BB78 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 2 in Ui_LayoutText_SetupTextureFilters */
extern u32 g_uiPicaTextureFilterPacket3[6];          /* 0x0073BB90 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 3 in Ui_LayoutText_SetupTextureFilters */
extern u32 g_uiPicaTextureFilterPacket4[6];          /* 0x0073BBA8 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 4 in Ui_LayoutText_SetupMultiTextureFilters */
extern u32 g_uiPicaTextureFilterPacket5[6];          /* 0x0073BBC0 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 5 in Ui_LayoutText_SetupMultiTextureFilters */
extern u32 g_uiPicaTextureFilterPacket6[6];          /* 0x0073BBD8 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 6 in Ui_LayoutText_SetupMultiTextureFilters */
extern u32 g_uiPicaTextureFilterPacket7[6];          /* 0x0073BBF0 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 7 in Ui_LayoutText_SetupTextureFilters */
extern u32 g_uiPicaTextureFilterPacket8[6];          /* 0x0073BC08 conf 0.90: 0x18-byte PICA200 GPU texture filter parameter packet 8 in Ui_LayoutText_SetupTextureFilters */
extern u32 g_uiPicaTevStageRegisterOffsets[4];       /* 0x0073BC20 conf 0.90: PICA200 GPU TEV stage register offsets (0xC0, 0xC8, 0xD0, 0xD8) in Ui_LayoutText_SetupAlphaAndBlendMode */
extern u32 g_uiPicaAlphaBlendPacket[6];              /* 0x0073BC38 conf 0.90: 0x18-byte PICA200 GPU alpha combiner and blend mode parameter packet in Ui_LayoutText_SetupAlphaAndBlendMode */
extern u32 g_uiPicaTextureCombinerPacket0[4];        /* 0x0073BC50 conf 0.90: 0x10-byte PICA200 GPU texture combiner register packet in Ui_LayoutText_SetupTextureCombiners */
extern u32 g_uiPicaTextureCombinerPacket1[4];        /* 0x0073BC60 conf 0.90: 0x10-byte PICA200 GPU texture combiner register packet in Ui_LayoutText_SetupTextureCombiners */
extern u32 g_uiPicaTevStagePacket2[4];               /* 0x0073BC70 conf 0.90: 0x10-byte PICA200 GPU TEV stage command packet in Ui_LayoutText_PackTevStages */
extern u32 g_uiPicaTevStagePacket3[4];               /* 0x0073BC90 conf 0.90: 0x10-byte PICA200 GPU TEV stage command packet in Ui_LayoutText_PackTevStages */
extern u32 g_uiPicaTevStageConfigBlock[17];          /* 0x0073BD00 conf 0.90: 0x44-byte PICA200 GPU TEV stage configuration block in Ui_LayoutText_PackTevStages */
extern char g_ndmUserServiceName[6];                 /* 0x007418E4 conf 0.95: Horizon OS service port name string 'ndm:u' (Nintendo Data Management user port) in maybe_Ui_AcquireAtlasContext */
extern u32 maybe_g_rodata_00746968;                  /* 0x00746968 conf 0.10: Rodata literal value referenced in maybe_Ui_DualDisplayWindow_Init for animation call */
extern u32 maybe_g_rodata_0074756f;                  /* 0x0074756F conf 0.10: Rodata literal value referenced in Ui_AnimInOutWindow_InitPanes and animation binding */
extern u32 maybe_g_rodata_00747874;                  /* 0x00747874 conf 0.10: Rodata literal value referenced in Ui_CommandBar_BindPanes and pane collection */
extern u32 maybe_g_rodata_00750025;                  /* 0x00750025 conf 0.10: Rodata literal value coinciding with format string '%u\0\0' referenced in shader buffer binding */
extern void* g_uiWindowBaseVtable[20];               /* 0x007582B8 conf 0.90: Virtual method table for UI window base class Ui_WindowBase */
extern void* g_uiLayoutSlotNodeVtable[12];           /* 0x007585CC conf 0.90: Virtual method table for UI layout slot node class */
extern void* g_uiFadeWindowVtable[12];               /* 0x0075869C conf 0.90: Virtual method table for UI screen fade window class */
extern void* g_uiWorldMapVtable[12];                 /* 0x00758788 conf 0.90: Virtual method table for UI world map window class */
extern void* g_uiLoadingScreenVtable[12];            /* 0x007587A8 conf 0.90: Virtual method table for UI loading screen window class */
extern void* g_uiWorldMapSubVtable[12];              /* 0x007587F8 conf 0.90: Virtual method table for UI world map sub-panel class */
extern void* g_uiObjectPriorityVtable[12];           /* 0x00758A7C conf 0.90: Virtual method table for UI object priority controller class */
extern void* g_uiActionPaneVtable[12];               /* 0x00758AE0 conf 0.90: Virtual method table for UI action pane widget class */
extern void* g_uiWindowHandleVtable[12];             /* 0x00758B14 conf 0.90: Virtual method table for UI window handle manager class */
extern void* g_uiMovieWindowVtable[12];              /* 0x00758C0C conf 0.90: Virtual method table for UI movie playback window class */
extern void* g_uiMessageWindowStorageVtable[12];     /* 0x00758CDC conf 0.90: Virtual method table for UI message window storage buffer class */
extern void* g_uiPagerVtable[12];                    /* 0x00758CFC conf 0.90: Virtual method table for UI pager controller class */
extern void* g_uiItemMenuRootVtable[12];             /* 0x00758D78 conf 0.90: Virtual method table for UI item menu root controller class */
extern void* g_uiDialogRootVtable[12];               /* 0x00758EA4 conf 0.90: Virtual method table for UI dialog root controller class */
extern void* g_uiSpriteWidgetVtable[40];             /* 0x00758FC0 conf 0.90: Virtual method table for UI 2D sprite widget class */
extern void* g_uiSlotWidgetVtable[39];               /* 0x007591FC conf 0.90: Virtual method table for UI slot widget class */
extern void* g_uiAnimatableElementVtable[12];        /* 0x00759378 conf 0.90: Virtual method table for UI animatable element class */
extern void* g_uiCompositeWindowVtable[12];          /* 0x00759388 conf 0.90: Virtual method table for UI composite window class */
extern void* g_uiRenderNodeVtable[12];               /* 0x007593A4 conf 0.90: Virtual method table for UI graphics render node class */
extern void* g_uiWindowDtorVtable[12];               /* 0x00759408 conf 0.90: Virtual method table for UI window destructor helper class */
extern void* g_uiWindowCtorAVtable[12];              /* 0x007594D4 conf 0.90: Virtual method table for UI window variant A constructor class */
extern void* g_uiWindowCtorBVtable[12];              /* 0x00759538 conf 0.90: Virtual method table for UI window variant B constructor class */
extern void* g_uiListInstanceVtable[12];             /* 0x0075966C conf 0.90: Virtual method table for UI list instance class */
extern void* g_uiSenrekiWindowPartVtable[12];        /* 0x007596A0 conf 0.90: Virtual method table for UI battle records (Senreki) window part class */
extern void* g_uiHandleSetUnlinkVtable[12];          /* 0x007596D4 conf 0.90: Virtual method table for UI handle set unlinking class */
extern void* g_uiShopWindowVtable[12];               /* 0x00759704 conf 0.90: Virtual method table for UI shop window class */
extern void* g_uiComplexWindowVtable[12];            /* 0x00759724 conf 0.90: Virtual method table for UI complex multi-pane window class */
extern void* g_uiSimpleWindowVtable[12];             /* 0x007597A4 conf 0.90: Virtual method table for UI simple single-pane window class */
extern void* g_uiMessageWindowInstanceVtable[12];    /* 0x007597F4 conf 0.90: Virtual method table for UI message window instance class */
extern void* g_uiHandleSetLargeVtableA[12];          /* 0x00759860 conf 0.90: Virtual method table for UI large handle set variant A class */
extern void* g_uiHandleSetLargeVtableB[12];          /* 0x00759878 conf 0.90: Virtual method table for UI large handle set variant B class */
extern void* g_uiWidget1C9AD4Vtable[12];             /* 0x007598B0 conf 0.90: Virtual method table for UI widget class instantiated at 0x001C9AD4 */
extern void* g_uiObjectArrayVtable[12];              /* 0x007598D4 conf 0.90: Virtual method table for UI object array container class */
extern void* g_uiMovieWindowBaseVtable[12];          /* 0x00759C68 conf 0.90: Virtual method table for UI movie playback window base class */
extern void* g_uiBigScreenVtable[12];                /* 0x00759CD0 conf 0.90: Virtual method table for UI big screen presentation class */
extern void* g_uiModelSelectVtable[12];              /* 0x00759D5C conf 0.90: Virtual method table for UI 3D model selection widget class */
extern void* g_uiObjectPooledVtable[12];             /* 0x00759FAC conf 0.90: Virtual method table for UI memory-pooled object class */
extern void* maybe_g_uiOverlaySlotVtable;            /* 0x00759FBC conf 0.45: Virtual method table of the UI overlay slot object created by maybe_Ui_OverlaySlotCtor, installed at object offset 0; th */
extern void* g_uiPartyHpGaugeWindowVtable[10];       /* 0x0075A07C conf 0.60: Virtual method table of the party HP gauge widget, installed at object offset 0; the engine reaches the object's virtual */
extern void* maybe_g_uiOverlayQuadVtable;            /* 0x0075A0CC conf 0.40: Virtual method table of the UI overlay quad object created by maybe_Ui_Overlay_CreateQuadObject, installed at object off */
extern void* g_uiCursorVtable[10];                   /* 0x0075A184 conf 0.70: Virtual method table of the UI cursor widget (Ui_Cursor_Ctor / maybe_Ui_Cursor_Dtor). Named dispatch slots in the retail */
extern void* g_uiMultiTextWindowVtable[10];          /* 0x0075A204 conf 0.55: Virtual method table of the multi-text message window (Ui_MultiTextWindow_Ctor). Named dispatch slots in the retail imag */
extern void* maybe_g_rodata_0075a2f4[10];            /* 0x0075A2F4 conf 0.30: Virtual method table of the unidentified UI widget vtable sharing Ui_CursorWindow_InitPanes. Named dispatch slots in the */
extern void* g_uiCursorIconVtable[2];                /* 0x0075A3E4 conf 0.85: Virtual method table of the Ui_CursorIcon, installed at object offset 0; the engine reaches the object's virtual update, */
extern void* g_uiWidgetVtable[10];                   /* 0x0075A3F4 conf 0.75: Virtual method table of the Ui_Widget base widget. Named dispatch slots in the retail image: ToD, Ui_Window_LayoutRows,  */
extern void* g_uiLoadingScreenWidgetVtable[10];      /* 0x0075A454 conf 0.60: Virtual method table of the loading-screen sub-widget (Ui_LoadingScreen_Create), installed at object offset 0; the engin */
extern void* g_uiMessagePageVtable;                  /* 0x0075A4A4 conf 0.75: Virtual method table of the Ui_MessagePage text page, installed at object offset 0; the engine reaches the object's virt */
extern void* g_uiPanelMessageWindowVtable[6];        /* 0x0075A570 conf 0.75: Virtual method table of the Ui_PanelMessageWindow, installed at object offset 0; the engine reaches the object's virtual */
extern void* g_uiPokerWindowBaseVtable[6];           /* 0x0075A674 conf 0.75: Virtual method table of the Ui_PokerWindow base sub-object (maybe_Ui_PanelState_Update slot), installed at object offset */
extern void* g_uiCardTableVtable;                    /* 0x0075A694 conf 0.70: Virtual method table of the card table used by the poker window, installed at object offset 0; the engine reaches the ob */
extern void* g_uiCasinoPrizeWindowVtable[6];         /* 0x0075A6A8 conf 0.60: Virtual method table of the prize window shared by casino and medal prizes. Named dispatch slots in the retail image: ma */
extern void* g_uiShopWindowWidgetVtable[10];         /* 0x0075A73C conf 0.65: Virtual method table of the shop-window sub-widget created by Ui_ShopWindow_CreateSubObjects. Named dispatch slots in th */
extern void* maybe_g_uiShopWindowPartVtable;         /* 0x0075A78C conf 0.45: Virtual method table of the shop-window sub-part (maybe_Ui_ShopWindow_Dtor), installed at object offset 0; the engine re */
extern void* g_stateSequence39Vtable[7];             /* 0x0075A7B0 conf 0.85: Virtual method table of the std_StateSequence39 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence49Vtable[7];             /* 0x0075A918 conf 0.85: Virtual method table of the std_StateSequence49 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence50Vtable[7];             /* 0x0075A93C conf 0.85: Virtual method table of the std_StateSequence50 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence52Vtable[7];             /* 0x0075A984 conf 0.85: Virtual method table of the std_StateSequence52 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence54Vtable[7];             /* 0x0075A9CC conf 0.85: Virtual method table of the std_StateSequence54 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence56Vtable[7];             /* 0x0075AA14 conf 0.85: Virtual method table of the std_StateSequence56 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence57Vtable[7];             /* 0x0075AA38 conf 0.85: Virtual method table of the std_StateSequence57 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence63Vtable[7];             /* 0x0075AB10 conf 0.85: Virtual method table of the std_StateSequence63 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence69Vtable[7];             /* 0x0075ABE8 conf 0.85: Virtual method table of the std_StateSequence69 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence01Vtable[7];             /* 0x0075AC30 conf 0.85: Virtual method table of the std_StateSequence01 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence02Vtable[7];             /* 0x0075AC54 conf 0.85: Virtual method table of the std_StateSequence02 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence03Vtable[7];             /* 0x0075AC78 conf 0.85: Virtual method table of the std_StateSequence03 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence07Vtable[7];             /* 0x0075AD08 conf 0.85: Virtual method table of the std_StateSequence07 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence08Vtable[7];             /* 0x0075AD2C conf 0.85: Virtual method table of the std_StateSequence08 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence10Vtable[7];             /* 0x0075AD74 conf 0.85: Virtual method table of the std_StateSequence10 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence11Vtable[7];             /* 0x0075AD98 conf 0.85: Virtual method table of the std_StateSequence11 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence16Vtable[7];             /* 0x0075AE4C conf 0.85: Virtual method table of the std_StateSequence16 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence17Vtable[7];             /* 0x0075AE70 conf 0.85: Virtual method table of the std_StateSequence17 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence19Vtable[7];             /* 0x0075AEB8 conf 0.85: Virtual method table of the std_StateSequence19 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence20Vtable[7];             /* 0x0075AEDC conf 0.85: Virtual method table of the std_StateSequence20 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence22Vtable[7];             /* 0x0075AF24 conf 0.85: Virtual method table of the std_StateSequence22 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence23Vtable[7];             /* 0x0075AF48 conf 0.85: Virtual method table of the std_StateSequence23 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence30Vtable[7];             /* 0x0075B044 conf 0.85: Virtual method table of the std_StateSequence30 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence32Vtable[7];             /* 0x0075B08C conf 0.85: Virtual method table of the std_StateSequence32 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence36Vtable[7];             /* 0x0075B11C conf 0.85: Virtual method table of the std_StateSequence36 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence37Vtable[7];             /* 0x0075B140 conf 0.85: Virtual method table of the std_StateSequence37 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence73Vtable[7];             /* 0x0075B1D0 conf 0.85: Virtual method table of the std_StateSequence73 UI window state machine, a small animation state machine embedded in a U */
extern void* g_stateSequence75Vtable[7];             /* 0x0075B218 conf 0.85: Virtual method table of the std_StateSequence75 UI window state machine, a small animation state machine embedded in a U */
extern void* maybe_g_rodata_0075b3a4;                /* 0x0075B3A4 conf 0.30: Virtual method table of the small table installed by Ui_SakusenWindow_Dtor (container-like helper), installed at object  */
extern void* maybe_g_uiSlotArrayVtable;              /* 0x0075B3BC conf 0.40: Virtual method table of the slot array helper (maybe_Ui_System_CreateSlotArray), installed at object offset 0; the engin */
extern void* g_uiRecipeBookVtable[6];                /* 0x0075B3CC conf 0.60: Virtual method table of the Ui_RecipeBook / Ui_Sequence, installed at object offset 0; the engine reaches the object's v */
extern void* g_uiBalloonWindowVtable;                /* 0x0075B3EC conf 0.60: Virtual method table of the balloon window (Ui_BalloonWindow_BindLayout), installed at object offset 0; the engine reach */
extern void* g_uiScreenVtable[4];                    /* 0x0075B460 conf 0.70: Virtual method table of the Ui_Screen base screen object. Named dispatch slots in the retail image: maybe_FieldParty_Ini */
extern void* g_uiBoushiPartVtable[6];                /* 0x0075B71C conf 0.85: Virtual method table of the Ui_BoushiPart, installed at object offset 0; the engine reaches the object's virtual update, */
extern void* g_uiStpassCallVipMsgVtable[10];         /* 0x0075B73C conf 0.85: Virtual method table of the Ui_StpassCallVipMsg StreetPass VIP message, installed at object offset 0; the engine reaches */
extern void* maybe_g_uiCreditWindowSceneVtable;      /* 0x0075B7F0 conf 0.45: Virtual method table of the credit-window 3D scene object (Ui_CreditWindow_Dtor), installed at object offset 0; the engi */
extern void* maybe_g_uiTextWidgetVtable[11];         /* 0x0075B978 conf 0.45: Virtual method table of the text widget created by maybe_Ui_CreateTextWidget. Named dispatch slots in the retail image:  */
extern void* maybe_g_uiCreditWindowPartsVtable[10];  /* 0x0075B9AC conf 0.50: Virtual method table of the credit-window sub-widget (Ui_SetupStartButton). Named dispatch slots in the retail image: Ui */
extern void* g_battleTextWindowWidgetVtable[6];      /* 0x0075BA1C conf 0.75: Virtual method table of the Battle_TextWindow object (Battle_TextWindow_Release/Dtor), installed at object offset 0; the */
extern void* maybe_g_uiEquipWindowAuxVtable;         /* 0x0075BAF0 conf 0.40: Virtual method table of the equipment-window auxiliary object (maybe_Ui_EquipWindow_Dtor), installed at object offset 0; */
extern void* maybe_g_uiTalkWindowSceneVtable;        /* 0x0075BBCC conf 0.45: Virtual method table of the talk-window 3D/Sprite scene object (Ui_TalkWindow_Dtor), installed at object offset 0; the e */
extern void* g_actor2DVtable;                        /* 0x0075BD94 conf 0.55: Virtual method table of the Actor2D sprite actor base, installed at object offset 0; the engine reaches the object's vir */
extern void* g_uiHorseraceReceptMsgVtable;           /* 0x0075C108 conf 0.80: Virtual method table of the Ui_HorseraceReceptMsg, installed at object offset 0; the engine reaches the object's virtual */
extern void* maybe_g_rodata_0075c120[7];             /* 0x0075C120 conf 0.30: Virtual method table of the small table from Ui_Object_InitMemberPair, slots are stubs, installed at object offset 0; th */
extern void* maybe_g_uiCompositeWindowVtable;        /* 0x0075C144 conf 0.40: Virtual method table of the composite window fragment (maybe_Ui_CompositeWindowCtor), installed at object offset 0; the  */
extern void* g_uiNameEntryVtable[10];                /* 0x0075C154 conf 0.80: Virtual method table of the Ui_NameEntry name-entry window. Named dispatch slots in the retail image: Ui_NameEntry_Dtor, */
extern void* maybe_g_uiSystemVtable;                 /* 0x0075C238 conf 0.40: Virtual method table of the UI system object (maybe_Ui_System_Ctor), installed at object offset 0; the engine reaches th */
extern void* maybe_g_uiGridCursorVtable[10];         /* 0x0075C248 conf 0.50: Virtual method table of the grid cursor widget (Ui_GridCursor/maybe_Ui_BigGridCursor). Named dispatch slots in the retai */
extern void* maybe_g_uiStatusWindowVtable[10];       /* 0x0075C2AC conf 0.60: Virtual method table of the status window (Ui_SetupStatusTextLayers). Named dispatch slots in the retail image: Ui_Widge */
extern void* g_uiPartVtable[6];                      /* 0x0075C3E0 conf 0.80: Virtual method table of the Ui_Part, installed at object offset 0; the engine reaches the object's virtual update, layou */
extern void* g_uiRowListVtable[10];                  /* 0x0075C400 conf 0.55: Virtual method table of the row list (maybe_Ui_RowList_DeleteThunk). Named dispatch slots in the retail image: maybe_Ui_ */
extern void* g_uiListOwnerVtable[10];                /* 0x0075C450 conf 0.85: Virtual method table of the Ui_ListOwner. Named dispatch slots in the retail image: Ui_ListOwner_DtorBase, Ui_ListOwner_ */
extern void* maybe_g_actorBaseVtable[11];            /* 0x0075C598 conf 0.50: Virtual method table of the actor base object (maybe_Actor_DeleteThunk). Named dispatch slots in the retail image: maybe */
extern void* g_actorVtable;                          /* 0x0075C5CC conf 0.60: Virtual method table of the actor object (maybe_Actor_Dtor), installed at object offset 0; the engine reaches the object */
extern void* g_uiListVtable[10];                     /* 0x0075C73C conf 0.85: Virtual method table of the Ui_List, installed at object offset 0; the engine reaches the object's virtual update, layou */
extern void* g_uiPokerCardsVtable[10];               /* 0x0075C78C conf 0.80: Virtual method table of the Ui_PokerCards. Named dispatch slots in the retail image: ToD, Ui_PokerTable_SetupCards, mayb */
extern void* g_uiCasinoWindowVtable[10];             /* 0x0075C7DC conf 0.85: Virtual method table of the Ui_CasinoWindow. Named dispatch slots in the retail image: Ui_CasinoWindow_DeletingDtor, ToD */
extern void* maybe_g_uiMapWindowVtable[10];          /* 0x0075C82C conf 0.50: Virtual method table of the map window sub-part (maybe_Ui_MapWindow_Init). Named dispatch slots in the retail image: ToD */
extern void* g_uiAdventureLogWindowVtable[10];       /* 0x0075C87C conf 0.55: Virtual method table of the adventure-log window (Ui_SetupAdventureLogWindow). Named dispatch slots in the retail image: */
extern void* g_uiMonsterBookWindowVtable[6];         /* 0x0075C8E4 conf 0.85: Virtual method table of the Ui_MonsterBookWindow, installed at object offset 0; the engine reaches the object's virtual  */
extern void* maybe_g_uiMonsterBookEntryVtable;       /* 0x0075C904 conf 0.55: Virtual method table of the monster-book entry (maybe_Ui_MonsterBookEntry_Ctor), installed at object offset 0; the engin */
extern void* maybe_g_uiSystemVtableA[24];            /* 0x0075C938 conf 0.40: Virtual method table of the UI system/manager object (Ui_SmithMenu_Init dispatch). Named dispatch slots in the retail im */
extern void* maybe_g_uiWindowFactoryVtable;          /* 0x0075C9B0 conf 0.40: Virtual method table of the window factory helper (maybe_Ui_InitEmbeddedByFactory), installed at object offset 0; the en */
extern void* g_uiListWidgetVtable;                   /* 0x0075C9E8 conf 0.75: Virtual method table of the Ui_ListWidget, installed at object offset 0; the engine reaches the object's virtual update, */
extern void* g_uiCharaStatusWindowVtable[10];        /* 0x0075CA18 conf 0.60: Virtual method table of the character-status window (Ui_SetupCharaStatusWindow). Named dispatch slots in the retail imag */
extern void* maybe_g_uiCharaStatusWindowChildVtable[10]; /* 0x0075CA7C conf 0.45: Virtual method table of the character-status window child (maybe_Ui_CharaStatusWindow_BindCharaPanes). Named dispatch sl */
extern void* g_uiDateDisplayVtable[10];              /* 0x0075CB00 conf 0.70: Virtual method table of the Ui_DateDisplay. Named dispatch slots in the retail image: maybe_Ui_Object_DeletingDtor, ToD, */
extern void* g_uiLoadScreenVtable[10];               /* 0x0075CB58 conf 0.60: Virtual method table of the Ui_LoadScreen. Named dispatch slots in the retail image: maybe_Ui_TrainingWindow_DeletingDto */
extern void* g_uiTrainingWindowVtable[10];           /* 0x0075CBA8 conf 0.80: Virtual method table of the Ui_TrainingWindow, installed at object offset 0; the engine reaches the object's virtual upd */
extern void* g_uiTrainingWindowPartVtable[10];       /* 0x0075CC00 conf 0.85: Virtual method table of the Ui_TrainingWindowPart. Named dispatch slots in the retail image: maybe_Ui_WindowPart_Deletin */
extern void* g_uiCompositeWindowObjectVtable[24];    /* 0x0075CFC8 conf 0.75: Virtual method table of the Ui_CompositeWindow object. Named dispatch slots in the retail image: Ui_CompositeWindow_Dtor */
extern void* maybe_g_uiPanelUpdateTextVtable;        /* 0x0075D030 conf 0.35: Virtual method table of the panel text updater (maybe_Ui_Panel_UpdateText), installed at object offset 0; the engine rea */
extern void* g_uiSlotVtable[10];                     /* 0x0075D044 conf 0.80: Virtual method table of the Ui_Slot. Named dispatch slots in the retail image: Ui_Slot_Dtor, ToD, maybe_Ui_UpdateScrollO */
extern void* g_uiBoushiShopWindowVtable[10];         /* 0x0075D098 conf 0.85: Virtual method table of the Ui_BoushiShopWindow, installed at object offset 0; the engine reaches the object's virtual u */
extern void* g_uiStreetPassVipMsgVtable[6];          /* 0x0075D0F8 conf 0.80: Virtual method table of the Ui_StreetPassVipMsg. Named dispatch slots in the retail image: Ui_StreetPassVipMsg_DeletingD */
extern void* maybe_g_uiShopWindowTransitionVtable;   /* 0x0075D118 conf 0.45: Virtual method table of the shop-window idle/transition helper, installed at object offset 0; the engine reaches the obj */
extern void* maybe_g_uiShopWindowSelectVtable;       /* 0x0075D144 conf 0.40: Virtual method table of the shop-window row-selection helper, installed at object offset 0; the engine reaches the objec */
extern void* g_uiCreditWindowVtable[10];             /* 0x0075D15C conf 0.70: Virtual method table of the Ui_CreditWindow, installed at object offset 0; the engine reaches the object's virtual updat */
extern void* maybe_g_uiCreditWindowContentVtable[10]; /* 0x0075D1AC conf 0.50: Virtual method table of the credit-window content sub-widget, installed at object offset 0; the engine reaches the objec */
extern void* g_uiCreditSubWidgetVtable[11];          /* 0x0075D210 conf 0.75: Virtual method table of the Ui_CreditSubWidget. Named dispatch slots in the retail image: Ui_CreditSubWidget_DeletingDto */
extern void* maybe_g_uiDungeonStartWindowVtable[10]; /* 0x0075D258 conf 0.50: Virtual method table of the dungeon-start window (Ui_DungeonStartWindow_BindPane). Named dispatch slots in the retail im */
extern void* g_uiTalkSubWidgetVtable[11];            /* 0x0075D30C conf 0.70: Virtual method table of the Ui_TalkSubWidget. Named dispatch slots in the retail image: Ui_TalkSubWidget_DeletingDtor, m */
extern void* g_uiTalkWindowVtable[10];               /* 0x0075D340 conf 0.85: Virtual method table of the Ui_TalkWindow. Named dispatch slots in the retail image: Ui_TalkPaneController_DeletingDtor, */
extern void* maybe_g_uiPopupUnitEffectVtable;        /* 0x0075D468 conf 0.45: Virtual method table of the popup unit-effect object, installed at object offset 0; the engine reaches the object's virt */
extern void* maybe_g_uiPanelUpdateTextVtableB;       /* 0x0075DA44 conf 0.35: Virtual method table of the panel text updater variant (maybe_Ui_Panel_UpdateTextB), installed at object offset 0; the e */
extern void* g_uiBigWindowVtable[10];                /* 0x0075DA68 conf 0.70: Virtual method table of the Ui_BigWindow. Named dispatch slots in the retail image: maybe_Ui_Object_DtorDeleteShort, Ui_ */
extern void* g_uiPaneGroupVtable[10];                /* 0x0075DAF4 conf 0.70: Virtual method table of the Ui_PaneGroup. Named dispatch slots in the retail image: Ui_PaneGroup_BindPanes, Ui_PaneGroup */
extern void* g_uiMainWindowVtable[10];               /* 0x0075DB48 conf 0.65: Virtual method table of the main window (Ui_MainWindow_BindPanes). Named dispatch slots in the retail image: ToD, Ui_Mai */
extern void* maybe_g_uiObjectVtable;                 /* 0x0075DBAC conf 0.45: Virtual method table of the shared UI object base (message-page decode slots), installed at object offset 0; the engine  */
extern void* g_uiMessageWindowVtable;                /* 0x0075DBD0 conf 0.70: Virtual method table of the message window (Ui_MessageWindow_ShowMessage), installed at object offset 0; the engine reac */
extern void* g_uiWidgetBaseVtable[10];               /* 0x0075DC34 conf 0.55: Virtual method table of the shared widget base used by dialog root, past-place and selectable-grid panels (Ui_PartySelec */
extern void* maybe_g_uiCompositeSingletonVtable;     /* 0x0075DD68 conf 0.35: Virtual method table of the composite-window singleton helper, installed at object offset 0; the engine reaches the obje */
extern void* maybe_g_uiCompositeStatusVtable[6];     /* 0x0075DD90 conf 0.40: Virtual method table of the composite status window (maybe_Ui_StatusWindow_UpdateState). Named dispatch slots in the ret */
extern void* g_uiSenrekiWindowVtable[10];            /* 0x0075DE78 conf 0.85: Virtual method table of the Ui_SenrekiWindow, installed at object offset 0; the engine reaches the object's virtual upda */
extern void* g_uiSenrekiWindowListVtable[10];        /* 0x0075DEC8 conf 0.70: Virtual method table of the Ui_SenrekiWindow list variant, installed at object offset 0; the engine reaches the object's */
extern void* maybe_g_uiPopupBalloonVtable;           /* 0x0075DF18 conf 0.45: Virtual method table of the popup balloon entry, installed at object offset 0; the engine reaches the object's virtual u */
extern void* g_uiKyoukaiWindowVtable[10];            /* 0x0075DF30 conf 0.80: Virtual method table of the Ui_KyoukaiWindow. Named dispatch slots in the retail image: ToD, Ui_KyoukaiWindow_CreatePane */
extern void* maybe_g_uiSystemVtableB[24];            /* 0x0075DF90 conf 0.40: Virtual method table of the UI system/manager object (Ui_SmithMenu_Init dispatch). Named dispatch slots in the retail im */
extern void* g_uiShopWindowSubWidgetVtable[10];      /* 0x0075DFF8 conf 0.50: Virtual method table of the shop-window sub-widget (Ui_PartySelectWindow_InitPanes layout). Named dispatch slots in the  */
extern void* maybe_g_uiTalkYesNoWindowVtable[10];    /* 0x0075E05C conf 0.55: Virtual method table of the talk yes/no window (Ui_TalkYesNoWindow_BindPanes). Named dispatch slots in the retail image: */
extern void* g_uiMessageVoiceLine0Vtable;            /* 0x0075E0C0 conf 0.70: Virtual method table of the Ui_MessageVoice line-0 player, installed at object offset 0; the engine reaches the object's */
extern void* g_uiMessageVoiceLine1Vtable;            /* 0x0075E0E8 conf 0.70: Virtual method table of the Ui_MessageVoice line-1 player, installed at object offset 0; the engine reaches the object's */
extern void* g_uiMessageVoiceLine2Vtable;            /* 0x0075E110 conf 0.70: Virtual method table of the Ui_MessageVoice line-2 player, installed at object offset 0; the engine reaches the object's */
extern void* g_uiMessageVoiceLine3Vtable;            /* 0x0075E138 conf 0.70: Virtual method table of the Ui_MessageVoice line-3 player, installed at object offset 0; the engine reaches the object's */
extern void* g_uiDungeonCheckWindowVtable[10];       /* 0x0075E160 conf 0.60: Virtual method table of the dungeon check window (Ui_DungeonCheckWindow_BindPanes). Named dispatch slots in the retail i */
extern void* g_uiDiveWindowVtable[10];               /* 0x0075E1B0 conf 0.85: Virtual method table of the Ui_DiveWindow, installed at object offset 0; the engine reaches the object's virtual update, */
extern void* g_uiComplexWindowWidgetVtable[10];      /* 0x0075E200 conf 0.65: Virtual method table of the Ui_ComplexWindow widget. Named dispatch slots in the retail image: maybe_Ui_ComplexWindow_Dt */
extern void* g_uiStreetPassTextVtable[10];           /* 0x0075E370 conf 0.85: Virtual method table of the Ui_StreetPassText. Named dispatch slots in the retail image: Ui_StreetPassText_Dtor, Ui_Stre */
extern void* maybe_g_uiTsuyosaWindowBodyVtable[10];  /* 0x0075E3C4 conf 0.50: Virtual method table of the Tsuyosa window body (Ui_TsuyosaWindow_BindPanes). Named dispatch slots in the retail image:  */
extern void* g_uiTsuyosaWindowVtable[10];            /* 0x0075E414 conf 0.85: Virtual method table of the Ui_TsuyosaWindow, installed at object offset 0; the engine reaches the object's virtual upda */
extern void* g_uiSakusenWindowVtable[10];            /* 0x0075E464 conf 0.85: Virtual method table of the Ui_SakusenWindow, installed at object offset 0; the engine reaches the object's virtual upda */
extern void* g_uiTalkLightWindowVtable[10];          /* 0x0075E4B4 conf 0.60: Virtual method table of the Ui_TalkLightWindow. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui */
extern void* g_uiLayoutChildVtable[10];              /* 0x0075E540 conf 0.50: Virtual method table of the layout child widget (maybe_Ui_LayoutChild_InitDispatch). Named dispatch slots in the retail  */
extern void* maybe_g_uiPopupModelVtable;             /* 0x0075E694 conf 0.40: Virtual method table of the popup model actor entry, installed at object offset 0; the engine reaches the object's virtu */
extern void* maybe_g_uiDiveFormVtable;               /* 0x0075E6AC conf 0.55: Virtual method table of the dive form window (Ui_DiveForm_InitPanes), installed at object offset 0; the engine reaches t */
extern void* maybe_g_uiLargeStateObjectVtable;       /* 0x0075E7B8 conf 0.40: Virtual method table of the large UI state object, installed at object offset 0; the engine reaches the object's virtual */
extern void* maybe_g_uiPopupMessageVtable;           /* 0x0075E9C4 conf 0.50: Virtual method table of the popup message entry (Ui_MessageWindow_SetNumberArg), installed at object offset 0; the engin */
extern void* g_uiTextScrollBarVtable[6];             /* 0x0075EA1C conf 0.50: Virtual method table of the text scroll bar / scroll window. Named dispatch slots in the retail image: maybe_Ui_TextScro */
extern void* g_uiPagedListWindowVtable[10];          /* 0x0075EB0C conf 0.60: Virtual method table of the Ui_PagedListWindow. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui */
extern void* maybe_g_uiListWindowVtable[10];         /* 0x0075EB84 conf 0.50: Virtual method table of the list window (maybe_Ui_ListWindow_DtorBase). Named dispatch slots in the retail image: maybe_ */
extern void* g_uiNumberWindowVtable[10];             /* 0x0075EBF8 conf 0.85: Virtual method table of the Ui_NumberWindow. Named dispatch slots in the retail image: Ui_NumberWindow_Dtor, Ui_Widget_R */
extern void* g_uiItemMenuRootPartVtable[10];         /* 0x0075EC5C conf 0.75: Virtual method table of the Ui_ItemMenu root part (Ui_ItemMenu_RootPart_Ctor). Named dispatch slots in the retail image: */
extern void* maybe_g_uiEquipWindowVtable;            /* 0x0075ED24 conf 0.45: Virtual method table of the equipment-window auxiliary pane group, installed at object offset 0; the engine reaches the  */
extern void* g_uiFadeWindowWidgetVtable;             /* 0x0075EE14 conf 0.60: Virtual method table of the fade window created by maybe_Ui_CreateFadeWindow, installed at object offset 0; the engine r */
extern void* maybe_g_uiWorldMapVtable[10];           /* 0x0075EED0 conf 0.55: Virtual method table of the world-map widget (maybe_Ui_WorldMapMarker_UpdateCurrent). Named dispatch slots in the retail */
extern void* g_uiWidget5AnimVtable[10];              /* 0x0075F7F8 conf 0.80: Virtual method table of the Ui_Widget5Anim. Named dispatch slots in the retail image: maybe_Ui_Window_Dtor, maybe_Ui_Win */
extern void* g_uiItemInfoWindowPaneVtable[10];       /* 0x0075F8A0 conf 0.60: Virtual method table of the item info window pane (Ui_ItemInfoWindow_InitPanes). Named dispatch slots in the retail imag */
extern void* g_uiTimerDisplayVtable;                 /* 0x0075F928 conf 0.80: Virtual method table of the Ui_TimerDisplay, installed at object offset 0; the engine reaches the object's virtual updat */
extern void* g_uiMainMenuTextVtable[6];              /* 0x0075F938 conf 0.85: Virtual method table of the Ui_MainMenuText, installed at object offset 0; the engine reaches the object's virtual updat */
extern void* maybe_g_uiWidgetGpuVtable[10];          /* 0x0075F974 conf 0.40: Virtual method table of the widget GPU buffer helper (maybe_Ui_Widget_CreateGpuBuffer). Named dispatch slots in the reta */
extern void* maybe_g_uiWidgetSubObjectVtable[10];    /* 0x0075F9C4 conf 0.50: Virtual method table of the widget sub-object (maybe_Ui_Widget_CtorWithSubObject). Named dispatch slots in the retail im */
extern void* maybe_g_fieldObjectVtable[11];          /* 0x0075FA64 conf 0.50: Virtual method table of the field object base (maybe_Field_Object_DtorDelete). Named dispatch slots in the retail image: */
extern void* maybe_g_uiPanelMessageWidgetVtable[10]; /* 0x0075FC10 conf 0.50: Virtual method table of the panel message child widget. Named dispatch slots in the retail image: maybe_Ui_Widget_DtorDe */
extern void* maybe_g_fieldActionVtable[11];          /* 0x0075FE38 conf 0.50: Virtual method table of the field action base (maybe_Field_Action_DtorDeleteD). Named dispatch slots in the retail image */
extern void* g_uiKeyAnimWindowVtable[10];            /* 0x0075FFA0 conf 0.60: Virtual method table of the key-animation window (Ui_KeyAnimWindow_InitPanes). Named dispatch slots in the retail image: */
extern void* g_uiWindowHolderVtable[6];              /* 0x00760004 conf 0.80: Virtual method table of the Ui_WindowHolder, installed at object offset 0; the engine reaches the object's virtual updat */
extern void* g_uiDiveStartWindowPartVtable[10];      /* 0x00760024 conf 0.70: Virtual method table of the Ui_DiveStartWindow part (Ui_DiveStartWindowPart_Ctor). Named dispatch slots in the retail im */
extern void* maybe_g_uiWindowRingBufferVtable;       /* 0x007600D4 conf 0.35: Virtual method table of the window ring-buffer helper (maybe_Text_MessageStack_Pop), installed at object offset 0; the e */
extern void* maybe_g_uiRecordDetailWindowVtable;     /* 0x007600EC conf 0.45: Virtual method table of the record-detail window (Ui_RecordDetailWindow_Ctor), installed at object offset 0; the engine  */
extern void* maybe_g_uiSenrekiWindowPartVtable[10];  /* 0x00760134 conf 0.45: Virtual method table of the monster-record list part. Named dispatch slots in the retail image: Ui_Object_DtorThenFree,  */
extern void* maybe_g_uiResourceSetVtable;            /* 0x00760198 conf 0.50: Virtual method table of the UI resource set (maybe_Ui_ResourceSet_Dtor), installed at object offset 0; the engine reache */
extern void* g_uiJackpotScreenVtable[26];            /* 0x007601A8 conf 0.85: Virtual method table of the Ui_JackpotScreen. Named dispatch slots in the retail image: maybe_Gfx_SceneNode_Init, Gfx_No */
extern void* g_uiJackpotScreenWidgetVtable[6];       /* 0x00760260 conf 0.70: Virtual method table of the Ui_JackpotScreen widget part, installed at object offset 0; the engine reaches the object's  */
extern void* g_uiListWindowBaseVtable[10];           /* 0x007602E0 conf 0.60: Virtual method table of the Ui_ListWindow / Ui_Drawable base. Named dispatch slots in the retail image: maybe_Ui_Drawabl */
extern void* maybe_g_uiPagedTextListWindowVtable[10]; /* 0x00760350 conf 0.55: Virtual method table of the paged text list window. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, mayb */
extern void* maybe_g_uiObjectSmallVtable[10];        /* 0x007603C8 conf 0.40: Virtual method table of the small UI object (Ui_Object_CtorSmallB). Named dispatch slots in the retail image: Ui_Object_ */
extern void* maybe_g_uiJumonWindowVtable;            /* 0x0076043C conf 0.50: Virtual method table of the spell (jumon) window entry, installed at object offset 0; the engine reaches the object's vi */
extern void* maybe_g_uiScreenDtorVtable;             /* 0x007605D4 conf 0.35: Virtual method table of the screen deletion helper (maybe_Ui_Screen_DtorDelete), installed at object offset 0; the engin */
extern void* maybe_g_rodata_00760618;                /* 0x00760618 conf 0.30: Virtual method table of the four-slot stub table from maybe_Ui_HandleSet_DtorLarge, installed at object offset 0; the en */
extern void* maybe_g_uiSubObjectVtable[6];           /* 0x00760628 conf 0.45: Virtual method table of the UI sub-object (maybe_Ui_SubObject_Ctor). Named dispatch slots in the retail image: maybe_Ui_ */
extern void* g_uiKeyHintWindowVtable[10];            /* 0x00760648 conf 0.55: Virtual method table of the key-hint window (Ui_KeyHintWindow_InitPanes). Named dispatch slots in the retail image: Ui_W */
extern void* g_uiPastScenarioWindowVtable[10];       /* 0x007606C0 conf 0.60: Virtual method table of the past-scenario window (Ui_ListWindow_InitRows). Named dispatch slots in the retail image: Ui_ */
extern void* g_uiScrollBarObjectVtable[10];          /* 0x0076081C conf 0.60: Virtual method table of the Ui_ScrollBarObject. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui */
extern void* maybe_g_uiBigWindowListVtable;          /* 0x007609AC conf 0.45: Virtual method table of the large window with party list, installed at object offset 0; the engine reaches the object's  */
extern void* maybe_g_battleUiRowVtable[11];          /* 0x00760E34 conf 0.50: Virtual method table of the battle UI row (maybe_Battle_UiRow_DeletingDtorA). Named dispatch slots in the retail image:  */
extern void* g_battleDamageExtWindowVtable[11];      /* 0x00760E68 conf 0.80: Virtual method table of the Battle_DamageExtWindow, installed at object offset 0; the engine reaches the object's virtua */
extern void* g_battleUiRowVtable[11];                /* 0x00760E9C conf 0.70: Virtual method table of the Battle_UiRow, installed at object offset 0; the engine reaches the object's virtual update,  */
extern void* maybe_g_battleUiRowVtableB[11];         /* 0x00760ED0 conf 0.50: Virtual method table of the battle UI row variant (maybe_Battle_UiRow_DeletingDtorC). Named dispatch slots in the retail */
extern void* maybe_g_battleUiRowVtableC[11];         /* 0x00760F04 conf 0.50: Virtual method table of the battle UI row variant (maybe_Battle_UiRow_DeletingDtorD). Named dispatch slots in the retail */
extern void* g_uiMessageWindowFieldVtable[10];       /* 0x00760F38 conf 0.65: Virtual method table of the field message window (Ui_MessageWindow_InitFieldPanes). Named dispatch slots in the retail i */
extern void* g_animInterpVtable[7];                  /* 0x007610B0 conf 0.75: Virtual method table of the Anim_Interp, installed at object offset 0; the engine reaches the object's virtual update, l */
extern void* g_uiCompositeObjectVtable[10];          /* 0x007610EC conf 0.60: Virtual method table of the Ui_CompositeObject / Ui_SceneObject. Named dispatch slots in the retail image: Ui_AnimWindow */
extern void* g_uiMessageWindowPairsVtable[10];       /* 0x00761134 conf 0.55: Virtual method table of the message window with paired panes. Named dispatch slots in the retail image: ToD, Ui_MessageW */
extern void* maybe_g_uiPopupValueVtable;             /* 0x00761184 conf 0.45: Virtual method table of the popup value entry (Ui_Message_SetNameArg), installed at object offset 0; the engine reaches  */
extern void* maybe_g_uiPopupActorPairVtable;         /* 0x0076119C conf 0.45: Virtual method table of the popup actor-pair entry, installed at object offset 0; the engine reaches the object's virtua */
extern void* maybe_g_uiPopupStatusVtable;            /* 0x007611B4 conf 0.45: Virtual method table of the popup status entry, installed at object offset 0; the engine reaches the object's virtual up */
extern void* g_uiScrollBarVtable[10];                /* 0x0076120C conf 0.80: Virtual method table of the Ui_ScrollBar. Named dispatch slots in the retail image: Ui_ScrollBar_Dtor, Ui_Widget_Release */
extern void* g_uiTwoTextWindowVtable[10];            /* 0x0076128C conf 0.70: Virtual method table of the Ui_TwoTextWindow. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui_S */
extern void* g_battlePopup3DVtable[10];              /* 0x007612F0 conf 0.80: Virtual method table of the Battle_Popup3D, installed at object offset 0; the engine reaches the object's virtual update */
extern void* maybe_g_battlePopup3DVtableB[11];       /* 0x00761344 conf 0.55: Virtual method table of the Battle_Popup3D attack-animation entry, installed at object offset 0; the engine reaches the  */
extern void* maybe_g_battlePopup3DVtableC[11];       /* 0x00761378 conf 0.55: Virtual method table of the Battle_Popup3D damage-animation entry, installed at object offset 0; the engine reaches the  */
extern void* g_uiAnimWindowVtable[10];               /* 0x00761410 conf 0.75: Virtual method table of the Ui_AnimWindow. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui_SetT */
extern void* g_uiHopeSelectVtable[10];               /* 0x00761E08 conf 0.75: Virtual method table of the Ui_HopeSelect. Named dispatch slots in the retail image: ToD, Ui_HopeSelect_LoadLayout, mayb */
extern void* g_uiItemInfoWindowObjectVtable;         /* 0x00761E58 conf 0.65: Virtual method table of the item info window object (Ui_ItemInfoWindow_Open), installed at object offset 0; the engine r */
extern void* maybe_g_uiBigWindowBodyVtable[6];       /* 0x00761EB8 conf 0.50: Virtual method table of the big window body (maybe_Ui_BigWindow_Dtor). Named dispatch slots in the retail image: maybe_U */
extern void* g_uiCursorWindowVtable[10];             /* 0x00761ED8 conf 0.75: Virtual method table of the Ui_CursorWindow. Named dispatch slots in the retail image: maybe_Ui_Pager_Destruct, Ui_Widge */
extern void* g_uiObjectDrawVtable[10];               /* 0x00761FC4 conf 0.55: Virtual method table of the UI object base with draw passes, installed at object offset 0; the engine reaches the object */
extern void* maybe_g_uiObjectDrawVtableB[10];        /* 0x00762028 conf 0.50: Virtual method table of the UI object base with draw passes (variant), installed at object offset 0; the engine reaches  */
extern void* maybe_g_uiLoadingWindowVtable[10];      /* 0x007620F0 conf 0.50: Virtual method table of the loading window (Ui_LoadingWindow_InitPane). Named dispatch slots in the retail image: Ui_Wid */
extern void* maybe_g_uiPopupCountVtable;             /* 0x00762154 conf 0.45: Virtual method table of the popup count entry (Ui_Message_SetNameAndCountArg), installed at object offset 0; the engine  */
extern void* g_uiItemMenuWindowVtable[10];           /* 0x007626EC conf 0.60: Virtual method table of the item menu window (Ui_ItemMenuWindow_InitPanes). Named dispatch slots in the retail image: ma */
extern void* maybe_g_uiWindowVtable[6];              /* 0x00762830 conf 0.40: Virtual method table of the small window object (maybe_Ui_Window_Ctor_530). Named dispatch slots in the retail image: ma */
extern void* maybe_g_uiDiveStartWindowVariantVtable[10]; /* 0x00762C1C conf 0.55: Virtual method table of the Ui_DiveStartWindow variant. Named dispatch slots in the retail image: ToD, Ui_DiveStartWindo */
extern void* maybe_g_uiDiveStartWindowWidgetVtable[10]; /* 0x00762C74 conf 0.50: Virtual method table of the dive-start window widget. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, ma */
extern void* maybe_g_uiDualWindowVtable[6];          /* 0x00762CD8 conf 0.50: Virtual method table of the dual window (maybe_Ui_DualWindow_Ctor). Named dispatch slots in the retail image: maybe_Menu */
extern void* maybe_g_rodata_00762d2c;                /* 0x00762D2C conf 0.30: Virtual method table of the ring-buffer helper table (Container_RingBuffer_Pop), installed at object offset 0; the engin */
extern void* maybe_g_uiRecipeMessageVtable[6];       /* 0x00762D44 conf 0.55: Virtual method table of the recipe message window. Named dispatch slots in the retail image: Ui_MessageWindow_ShowNextPa */
extern void* maybe_g_uiRecordListWindowVtable[10];   /* 0x00762D64 conf 0.50: Virtual method table of the record list window (Ui_ListWindow_SetupTextRows). Named dispatch slots in the retail image:  */
extern void* g_uiRouletteWindowVtable[10];           /* 0x00762E54 conf 0.75: Virtual method table of the Ui_RouletteWindow. Named dispatch slots in the retail image: ToD, Ui_RouletteWindow_InitPane */
extern void* g_uiCasinoWinWindowVtable[10];          /* 0x00762EA4 conf 0.80: Virtual method table of the Ui_CasinoWinWindow, installed at object offset 0; the engine reaches the object's virtual up */
extern void* g_uiBigScreenWidgetVtable[10];          /* 0x00762EF4 conf 0.75: Virtual method table of the Ui_BigScreen object. Named dispatch slots in the retail image: maybe_Ui_BigScreen_Dtor, mayb */
extern void* maybe_g_uiTextBuildVtable;              /* 0x00762F74 conf 0.40: Virtual method table of the text build helper (maybe_Ui_TextBuild_Start), installed at object offset 0; the engine reach */
extern void* maybe_g_uiMessageSelectWindowVtable[10]; /* 0x00763024 conf 0.50: Virtual method table of the message select window pane. Named dispatch slots in the retail image: ToD, Pb1, maybe_Svc_Ti */
extern void* maybe_g_uiKeyPromptWindowVtable;        /* 0x00763074 conf 0.60: Virtual method table of the key-prompt window (maybe_Ui_KeyPromptWindow_InitPanes), installed at object offset 0; the en */
extern void* g_uiPanePairVtable[10];                 /* 0x007630A0 conf 0.80: Virtual method table of the Ui_PanePair. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui_SetThr */
extern void* g_uiSakusenTutorialVtable[10];          /* 0x00763104 conf 0.60: Virtual method table of the tactics tutorial window (Ui_SakusenTutorial_InitPanes). Named dispatch slots in the retail i */
extern void* g_uiTwoPaneWindowVtable[10];            /* 0x00763168 conf 0.60: Virtual method table of the Ui_TwoPaneWindow. Named dispatch slots in the retail image: ToD, Ui_PastScenarioWindow_InitP */
extern void* maybe_g_uiScreenWithTextCacheVtable;    /* 0x007631F8 conf 0.55: Virtual method table of the screen with text cache (Ui_Screen_CtorWithTextCache), installed at object offset 0; the engi */
extern void* g_uiObjectBaseAltVtable[11];            /* 0x00763A48 conf 0.60: Virtual method table of the Ui_ObjectBase (second table variant). Named dispatch slots in the retail image: maybe_Battle */
extern void* g_uiWindowWithTweensVtable;             /* 0x00763A7C conf 0.70: Virtual method table of the Ui_WindowWithTweens, installed at object offset 0; the engine reaches the object's virtual u */
extern void* g_uiMessage3DWindowVtable[10];          /* 0x00763AA0 conf 0.60: Virtual method table of the 3D message window (Ui_Message3DWindow_InitPanes). Named dispatch slots in the retail image:  */
extern void* maybe_g_battlePopup3DVtableD[11];       /* 0x00763B04 conf 0.50: Virtual method table of the Battle_Popup3D entry (release actor anim). Named dispatch slots in the retail image: maybe_B */
extern void* maybe_g_battlePopup3DVtableE[11];       /* 0x00763B38 conf 0.50: Virtual method table of the Battle_Popup3D entry. Named dispatch slots in the retail image: maybe_Battle_Popup3D_Deletin */
extern void* maybe_g_battlePopup3DVtableF[11];       /* 0x00763B6C conf 0.50: Virtual method table of the Battle_Popup3D entry (release actor hook). Named dispatch slots in the retail image: maybe_B */
extern void* g_battlePopup3DResultListVtable[10];    /* 0x00763C3C conf 0.55: Virtual method table of the Battle_Popup3D target-result list (Battle_Popup3D_TargetResult_Init), installed at object of */
extern void* g_uiMessageSelectWindowVtable[10];      /* 0x00763C90 conf 0.70: Virtual method table of the Ui_MessageSelectWindow. Named dispatch slots in the retail image: maybe_Ui_MessageSelectWind */
extern void* maybe_g_uiWindowBaseVtable[10];         /* 0x00763D2C conf 0.50: Virtual method table of the window base object (maybe_Ui_WindowBase_Ctor). Named dispatch slots in the retail image: may */
extern void* g_uiSlotSubVtable[10];                  /* 0x00763DC8 conf 0.80: Virtual method table of the Ui_SlotSub. Named dispatch slots in the retail image: maybe_Ui_SlotSub_Delete, Ui_Widget_Rel */
extern void* g_uiSlotWindowVtable[6];                /* 0x00763E30 conf 0.85: Virtual method table of the Ui_SlotWindow, installed at object offset 0; the engine reaches the object's virtual update, */
extern void* maybe_g_uiPopupFlaggedVtable;           /* 0x00763E50 conf 0.45: Virtual method table of the popup entry selected by flags, installed at object offset 0; the engine reaches the object's */
extern void* maybe_g_uiTextureNameWindowVtable[10];  /* 0x00763F74 conf 0.45: Virtual method table of the texture-name window (maybe_Ui_TextureNameWindow_InitPanes). Named dispatch slots in the reta */
extern void* g_uiGaugeBarWindowVtable[10];           /* 0x00763FD8 conf 0.65: Virtual method table of the Ui_GaugeBarWindow. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui_ */
extern void* maybe_g_uiTweenSequenceVtable[11];      /* 0x00764050 conf 0.50: Virtual method table of the tween sequence object (maybe_Ui_TweenSequence_Update). Named dispatch slots in the retail im */
extern void* g_uiTwoColumnListWindowVtable[10];      /* 0x00764084 conf 0.80: Virtual method table of the Ui_TwoColumnListWindow. Named dispatch slots in the retail image: Ui_TwoColumnListWindow_Del */
extern void* g_uiDiveStartWindowVtable[10];          /* 0x00764160 conf 0.85: Virtual method table of the Ui_DiveStartWindow main object, installed at object offset 0; the engine reaches the object' */
extern void* g_uiDiveManagerVtable[6];               /* 0x007641B8 conf 0.80: Virtual method table of the Ui_DiveManager, installed at object offset 0; the engine reaches the object's virtual update */
extern void* maybe_g_uiDiveGaugeBarVtable[10];       /* 0x007641D8 conf 0.50: Virtual method table of the dive gauge-bar sub-object. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, m */
extern void* maybe_g_uiGaugeWindowVtable[10];        /* 0x00764270 conf 0.50: Virtual method table of the gauge window sub-object. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, may */
extern void* g_uiTitleWindowVtable[10];              /* 0x0076446C conf 0.50: Virtual method table of the title window (Ui_TitleWindow_InitPanes). Named dispatch slots in the retail image: maybe_Fie */
extern void* maybe_g_uiTitleTextWindowVtable[10];    /* 0x007644D0 conf 0.45: Virtual method table of the title text window (maybe_Ui_TitleTextWindow_InitPanes). Named dispatch slots in the retail i */
extern void* maybe_g_uiEquipmentWindowVtable;        /* 0x00764534 conf 0.50: Virtual method table of the equipment window row list (Ui_EquipmentWindow_HandleInput), installed at object offset 0; th */
extern void* g_uiEquipWindowVtable[10];              /* 0x007649E8 conf 0.85: Virtual method table of the Ui_EquipWindow. Named dispatch slots in the retail image: Field_NpcController_DeletingDtor,  */
extern void* g_uiSceneCompositeVtable[2];            /* 0x00764B74 conf 0.80: Virtual method table of the Ui_SceneComposite, installed at object offset 0; the engine reaches the object's virtual upd */
extern void* maybe_g_objectHandlerVtable;            /* 0x00764B84 conf 0.30: Virtual method table of the shared object vtable from generic field/UI handlers, installed at object offset 0; the engin */
extern void* g_fieldActorPartVtable[11];             /* 0x00765240 conf 0.70: Virtual method table of the Field_ActorPart. Named dispatch slots in the retail image: maybe_Field_ActorPart_DeletingDto */
extern void* g_uiItemMenuRowVtable[10];              /* 0x00765274 conf 0.75: Virtual method table of the Ui_ItemMenu_Row. Named dispatch slots in the retail image: Ui_ItemMenu_Row_Dtor, Ui_Widget_R */
extern void* g_uiJewelShopWindowVtable[10];          /* 0x007652F0 conf 0.70: Virtual method table of the Ui_JewelShopWindow / Ui_BigWindow. Named dispatch slots in the retail image: Ui_JewelShopWin */
extern void* g_uiTimerDisplayPartVtable[10];         /* 0x00765420 conf 0.80: Virtual method table of the Ui_TimerDisplayPart. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_U */
extern void* maybe_g_uiScreenFadeVtable;             /* 0x00765484 conf 0.50: Virtual method table of the screen fade object (Ui_ScreenFade_Setup), installed at object offset 0; the engine reaches t */
extern void* maybe_g_uiGuideWindowLoadingVtable[10]; /* 0x00765504 conf 0.50: Virtual method table of the guide/loading window (Ui_LoadingWindow_Init), installed at object offset 0; the engine reach */
extern void* g_uiGuideWindowBodyVtable[10];          /* 0x00765554 conf 0.55: Virtual method table of the Ui_GuideWindow body (Ui_GuideWindow_CtorB). Named dispatch slots in the retail image: ToD, U */
extern void* g_uiStampBookWindowVtable[6];           /* 0x007655A4 conf 0.80: Virtual method table of the Ui_StampBookWindow, installed at object offset 0; the engine reaches the object's virtual up */
extern void* g_uiNodeListVtable;                     /* 0x007655C4 conf 0.70: Virtual method table of the UI node list (Ui_NodeList_Register), installed at object offset 0; the engine reaches the ob */
extern void* g_uiTwoColumnTextWindowVtable[10];      /* 0x007655D4 conf 0.55: Virtual method table of the two-column text window (Ui_TwoColumnTextWindow_InitPanes_2). Named dispatch slots in the ret */
extern void* g_uiSkillPanelVtable[10];               /* 0x00765790 conf 0.85: Virtual method table of the Ui_SkillPanel, installed at object offset 0; the engine reaches the object's virtual update, */
extern void* maybe_g_uiSkillPanelListVtable[10];     /* 0x007657E0 conf 0.60: Virtual method table of the skill-panel party list. Named dispatch slots in the retail image: Ui_Object_DtorSimple, Ui_W */
extern void* g_uiPastPlaceWindowVtable[10];          /* 0x007658A8 conf 0.85: Virtual method table of the Ui_PastPlaceWindow, installed at object offset 0; the engine reaches the object's virtual up */
extern void* g_ui3DAttachmentWindowVtable[26];       /* 0x00765B30 conf 0.85: Virtual method table of the Ui_3DAttachmentWindow. Named dispatch slots in the retail image: Field_NpcAction_DeletingDto */
extern void* g_uiPresentMessageManagerVtable[6];     /* 0x00765C0C conf 0.65: Virtual method table of the Ui_PresentMessage manager (Ui_PresentMessage_Manager_Dtor), installed at object offset 0; th */
extern void* maybe_g_uiPresentMessageVtable[10];     /* 0x00765C2C conf 0.60: Virtual method table of the Ui_PresentMessage. Named dispatch slots in the retail image: ToD, Ui_PresentMessage_Manager_ */
extern void* g_uiMemoriesWindowVtable[10];           /* 0x00765C7C conf 0.85: Virtual method table of the Ui_MemoriesWindow, installed at object offset 0; the engine reaches the object's virtual upd */
extern void* g_uiPresentActionVtable[11];            /* 0x00765CCC conf 0.60: Virtual method table of the Ui_PresentAction. Named dispatch slots in the retail image: Ui_PresentAction_DeletingDtor, m */
extern void* g_uiPresentListVtable[6];               /* 0x00765D00 conf 0.80: Virtual method table of the Ui_PresentList, installed at object offset 0; the engine reaches the object's virtual update */
extern void* maybe_g_uiMonsterRecordVtable;          /* 0x00765D20 conf 0.60: Virtual method table of the monster record window (Ui_MonsterRecord_Ctor), installed at object offset 0; the engine reac */
extern void* g_uiRowObjectVtable[10];                /* 0x00765D54 conf 0.80: Virtual method table of the Ui_RowObject. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui_SetTh */
extern void* maybe_g_uiRecordDetailRowVtable;        /* 0x00765DC8 conf 0.55: Virtual method table of the record-detail row object, installed at object offset 0; the engine reaches the object's virt */
extern void* maybe_g_uiRecordDetailListVtable;       /* 0x00765DFC conf 0.50: Virtual method table of the record-detail list object, installed at object offset 0; the engine reaches the object's vir */
extern void* g_uiRecordListWindowVtable[10];         /* 0x00765E78 conf 0.60: Virtual method table of the record list window (Ui_RecordListWindow_InitRows). Named dispatch slots in the retail image: */
extern void* maybe_g_uiTwoColumnListWindowVtableB[10]; /* 0x00765F94 conf 0.55: Virtual method table of the two-column list window variant. Named dispatch slots in the retail image: Ui_Object_DtorWith */
extern void* maybe_g_uiPresentWindowSceneVtable;     /* 0x00766058 conf 0.40: Virtual method table of the present-window scene object, installed at object offset 0; the engine reaches the object's v */
extern void* maybe_g_ui3DBackgroundVtable;           /* 0x00766210 conf 0.40: Virtual method table of the 3D background object (maybe_Ui_3DBackground_Init), installed at object offset 0; the engine  */
extern void* g_uiMessageSelectWindowBodyVtable[6];   /* 0x0076622C conf 0.60: Virtual method table of the Ui_MessageSelectWindow body, installed at object offset 0; the engine reaches the object's v */
extern void* g_uiMessageSelectRowVtable[10];         /* 0x007662B0 conf 0.50: Virtual method table of the message-select row (Ui_Row_SetCursorIcon). Named dispatch slots in the retail image: Ui_Widg */
extern void* maybe_g_uiTalkWindowMessageVtable[10];  /* 0x00766328 conf 0.50: Virtual method table of the talk-window message pane. Named dispatch slots in the retail image: ToD, maybe_Ui_TalkWindow */
extern void* maybe_g_uiTalkLightWindowVtable[10];    /* 0x00766378 conf 0.55: Virtual method table of the talk light window (Ui_TalkWindow_InitPanes). Named dispatch slots in the retail image: maybe */
extern void* g_uiScrollListWindowVtable[6];          /* 0x00766524 conf 0.80: Virtual method table of the Ui_ScrollListWindow, installed at object offset 0; the engine reaches the object's virtual u */
extern void* g_battleActorActionWaitVtable[11];      /* 0x00766910 conf 0.70: Virtual method table of the Battle_ActorAction wait action. Named dispatch slots in the retail image: Battle_ActorAction */
extern void* g_battleActorActionBaseVtable[11];      /* 0x00766944 conf 0.65: Virtual method table of the Battle_ActorAction base (Battle_ActorAction_DeletingDtorAlt). Named dispatch slots in the re */
extern void* g_uiBattleEnemyListWindowVtable[10];    /* 0x00766978 conf 0.80: Virtual method table of the Ui_BattleEnemyListWindow. Named dispatch slots in the retail image: maybe_Ui_SubWidgetConfig */
extern void* g_uiBattlePartyWindowVtable[10];        /* 0x00766A3C conf 0.80: Virtual method table of the Ui_BattlePartyWindow. Named dispatch slots in the retail image: Ui_BattleSpellWindow_DtorBas */
extern void* maybe_g_uiFourRowTextWindowVtable[10];  /* 0x00766B74 conf 0.50: Virtual method table of the four-row text window (Ui_FourRowTextWindow_InitPanes_2). Named dispatch slots in the retail  */
extern void* maybe_g_uiTextLayerWindowVtable[10];    /* 0x00766C10 conf 0.50: Virtual method table of the text layer window (maybe_Ui_TextLayerWindow_Init). Named dispatch slots in the retail image: */
extern void* maybe_g_uiNumberedTextRowsWindowVtable[10]; /* 0x00766D10 conf 0.50: Virtual method table of the numbered text rows window. Named dispatch slots in the retail image: maybe_Ui_TwoListWindow_ */
extern void* g_uiSlotMachineDisplayVtable[10];       /* 0x00766D74 conf 0.55: Virtual method table of the Ui_SlotMachineDisplay. Named dispatch slots in the retail image: L69, Ui_SlotMachineDisplay_ */
extern void* g_uiTitleMessageWindowVtable[10];       /* 0x00766E14 conf 0.85: Virtual method table of the Ui_TitleMessageWindow. Named dispatch slots in the retail image: Ui_Dialog_DeletingDtor, ToD */
extern void* maybe_g_uiBigScreenDialogVtable;        /* 0x00766E64 conf 0.40: Virtual method table of the big-screen dialog scene object, installed at object offset 0; the engine reaches the object' */
extern void* g_uiDungeonListWindowVtable[10];        /* 0x00766F3C conf 0.70: Virtual method table of the Ui_DungeonListWindow. Named dispatch slots in the retail image: ToD, Ui_DungeonListWindow_In */
extern void* g_uiListWindow1F8Vtable[6];             /* 0x00767238 conf 0.80: Virtual method table of the Ui_ListWindow1F8, installed at object offset 0; the engine reaches the object's virtual upda */
extern void* maybe_g_uiSlotSubObjectVtable;          /* 0x0076729C conf 0.40: Virtual method table of the slot sub-object (maybe_Ui_SlotSubObject_Dtor), installed at object offset 0; the engine reac */
extern void* g_uiEquipTextWindowVtable[6];           /* 0x00767354 conf 0.85: Virtual method table of the Ui_EquipTextWindow, installed at object offset 0; the engine reaches the object's virtual up */
extern void* maybe_g_rodata_00767374;                /* 0x00767374 conf 0.30: Virtual method table of the four-slot table from maybe_Ui_BigScreen_Dtor, installed at object offset 0; the engine reach */
extern void* maybe_g_gfxSpriteVtable;                /* 0x00767384 conf 0.50: Virtual method table of the Gfx_Sprite-derived object (Gfx_Sprite_Dtor), installed at object offset 0; the engine reache */
extern void* maybe_g_uiPopupActorSpanVtable;         /* 0x00767404 conf 0.45: Virtual method table of the popup actor span entry, installed at object offset 0; the engine reaches the object's virtua */
extern void* g_fieldWalkActionVtable[11];            /* 0x0076819C conf 0.75: Virtual method table of the Field_WalkAction, installed at object offset 0; the engine reaches the object's virtual upda */
extern void* g_uiTensionGaugeWindowVtable[10];       /* 0x007681D0 conf 0.60: Virtual method table of the tension gauge window (Ui_TensionGaugeWindow_InitPanes). Named dispatch slots in the retail i */
extern void* maybe_g_uiPopupActorListVtable;         /* 0x00768234 conf 0.45: Virtual method table of the popup actor-list entry, installed at object offset 0; the engine reaches the object's virtua */
extern void* maybe_g_uiViewportStateVtable;          /* 0x0076824C conf 0.40: Virtual method table of the UI layout viewport state (Ui_Layout_AllocViewportState), installed at object offset 0; the e */
extern void* g_uiWorldMapMarkerVtable[10];           /* 0x0076828C conf 0.80: Virtual method table of the Ui_WorldMapMarker, installed at object offset 0; the engine reaches the object's virtual upd */
extern void* g_uiLocationWindowVtable[10];           /* 0x007682DC conf 0.75: Virtual method table of the Ui_LocationWindow, installed at object offset 0; the engine reaches the object's virtual upd */
extern void* maybe_g_uiTwoLineGuideWindowVtable[10]; /* 0x0076832C conf 0.60: Virtual method table of the two-line guide window (Ui_TwoLineGuideWindow_InitPanes). Named dispatch slots in the retail  */
extern void* maybe_g_uiStampBookPageVtable[10];      /* 0x0076837C conf 0.55: Virtual method table of the stamp-book page (Ui_StampBookPage_Ctor). Named dispatch slots in the retail image: maybe_Ui_ */
extern void* maybe_g_uiTabPanelVtable[6];            /* 0x00768484 conf 0.40: Virtual method table of the tab panel (Ui_Tab_PlayChangeSe). Named dispatch slots in the retail image: Ui_Tab_PlayChange */
extern void* g_uiMovieTextWindowVtable[10];          /* 0x007684A4 conf 0.60: Virtual method table of the movie text window (Ui_MovieTextWindow_InitPanes). Named dispatch slots in the retail image:  */
extern void* g_uiPanelVtable[10];                    /* 0x00768510 conf 0.60: Virtual method table of the Ui_Panel. Named dispatch slots in the retail image: Ui_Widget_ReleaseSub, maybe_Ui_SetThreeO */
extern void* g_uiPanelMessageTextVtable[10];         /* 0x00768574 conf 0.55: Virtual method table of text object created by Ui_PanelMessageWindow_CreateText (0x16C-byte Ui_AnimRefList_Ctor object). */
extern void* g_uiMiniPlateWindowVtable[10];          /* 0x007685C4 conf 0.50: Virtual method table of Ui_MiniPlateWindow. The object's vptr is set by Ui_PanelMessageWindow_LoadPanels. Named virtual  */
extern void* g_uiSkillPanelWindowVtable[10];         /* 0x00768614 conf 0.88: Virtual method table of Ui_SkillPanelWindow (base Ui_ListWindow). The object's vptr is set by Ui_SkillPanelWindow_Ctor.  */
extern void* g_uiSelectListWindowVtable[10];         /* 0x00768664 conf 0.88: Virtual method table of Ui_SelectListWindow. The object's vptr is set by maybe_Ui_SelectListWindow_Delete, maybe_Ui_Sele */
extern void* g_uiDateDisplayVtableB[10];             /* 0x007689B0 conf 0.76: Virtual method table of Ui_DateDisplay. The object's vptr is set by Ui_PresentWindow_Ctor. Named virtual slots: 1:maybe_ */
extern void* g_uiTalkMenuWindowVtable[10];           /* 0x00768A08 conf 0.86: Virtual method table of Ui_TalkMenuWindow. The object's vptr is set by maybe_Ui_Window_Ctor. Named virtual slots: 1:mayb */
extern void* g_uiQuestWindowVtable[10];              /* 0x00768A58 conf 0.88: Virtual method table of Ui_QuestWindow. The object's vptr is set by Ui_QuestWindow_Ctor. Named virtual slots: 1:Ui_Quest */
extern void* maybe_g_uiFaceIconSubVtable;            /* 0x00768ABC conf 0.40: Virtual method table of sub-object created inside maybe_Ui_FaceIcon_Init; slots are shared widget virtuals, the class it */
extern void* g_uiSmallObjectVtable[10];              /* 0x00768AE0 conf 0.88: Virtual method table of Ui_SmallObject. The object's vptr is set by maybe_Ui_SmallObject_Ctor. Named virtual slots: 1:ma */
extern void* g_uiKyoukaiWindowVtableB[10];           /* 0x00768B40 conf 0.80: Virtual method table of Ui_KyoukaiWindow. The object's vptr is set by Ui_MessageCommandWindow_Ctor8. Named virtual slots */
extern void* g_uiKyoukaiWindowVtableC[10];           /* 0x00768BA0 conf 0.80: Virtual method table of Ui_KyoukaiWindow. The object's vptr is set by Ui_MessageCommandWindow_Ctor9. Named virtual slots */
extern void* g_uiThreeRowNullTextWindowVtable[10];   /* 0x00768C00 conf 0.88: Virtual method table of Ui_ThreeRowNullTextWindow. The object's vptr is set by Ui_ThreeRowNullTextWindow_Ctor. Named vir */
extern void* g_uiGoldWindowVtable[10];               /* 0x00768C64 conf 0.88: Virtual method table of Ui_GoldWindow. The object's vptr is set by Ui_GoldWindow_Ctor. Named virtual slots: 1:Ui_GoldWin */
extern void* g_uiTwoColumnRowVtable[10];             /* 0x00768CC8 conf 0.55: Virtual method table of two-column list row built by maybe_Ui_Row_Ctor (slot 8 Ui_TwoColumnRow_InitPanes; the dtor at sl */
extern void* maybe_g_rodata_00768d7c[4];             /* 0x00768D7C conf 0.30: Four-word table stamped by maybe_Ui_ReleaseResourceHandles; its only non-zero slot is that same release thunk, so it is  */
extern void* g_uiSoulWindowVtable[10];               /* 0x00768D8C conf 0.80: Virtual method table of Ui_SoulWindow. The object's vptr is set by maybe_Ui_DiveForm_Ctor. Named virtual slots: 4:Ui_Sou */
extern void* g_uiGridTextWindowVtable[10];           /* 0x00768E48 conf 0.58: Virtual method table of Ui_GridTextWindow. The object's vptr is set by Ui_TsuyosaWindow_Ctor, maybe_Ui_TsuyosaWindow_Ini */
extern void* g_uiPartySelectRowWidgetVtable[10];     /* 0x00768EAC conf 0.82: Virtual method table of Ui_PartySelectRowWidget (base Ui_AnimWidget12). The object's vptr is set by Ui_PartySelectRowWid */
extern void* g_uiTsuyosaWindowVtableB[10];           /* 0x00768F10 conf 0.82: Virtual method table of Ui_TsuyosaWindow (base Ui_Row). The object's vptr is set by maybe_Ui_TsuyosaWindow_CreateRow. Na */
extern void* g_uiTitleLoopWindowVtable[10];          /* 0x00769034 conf 0.86: Virtual method table of Ui_TitleLoopWindow. The object's vptr is set by Ui_TitleLoopWindow_Ctor. Named virtual slots: 2: */
extern void* g_fieldPartyUiVtable;                   /* 0x00769084 conf 0.70: Virtual method table of FieldParty_Ui. The object's vptr is set by maybe_Ui_ScreenManager_Ctor. Named virtual slots: 1:F */
extern void* g_itemListIteratorVtable;               /* 0x0076919C conf 0.60: Virtual method table of ItemList_Iterator (slot 3 ItemList_Iterator_GetEntryId, slot 6 GetEntryByte); the constructor ma */
extern void* g_battleTargetMarkerVtableB[11];        /* 0x0076981C conf 0.70: Virtual method table of Battle_TargetMarker. The object's vptr is set by maybe_Ui_ListSubObject_CreateJ. Named virtual s */
extern void* g_eventPacketVtable[7];                 /* 0x00769850 conf 0.82: Virtual method table of Event_Packet. The object's vptr is set by Battle_ActionUi_Ctor, maybe_Ui_ScreenCtor_vt77A630, ma */
extern void* g_uiIconRowWindowVtable[10];            /* 0x007698A4 conf 0.82: Virtual method table of Ui_IconRowWindow. The object's vptr is set by maybe_Ui_BattleCommandWindow_CtorA. Named virtual  */
extern void* g_uiIconRowWindowVtableB[10];           /* 0x00769940 conf 0.82: Virtual method table of Ui_IconRowWindow. The object's vptr is set by maybe_Ui_BattleCommandWindow_CtorB. Named virtual  */
extern void* g_uiIconButtonVtable[10];               /* 0x007699DC conf 0.50: Virtual method table of Ui_IconButton. The object's vptr is set by maybe_Ui_Widget_Ctor. Named virtual slots: 2:Ui_Widge */
extern void* g_uiAmountSpinnerVtable[10];            /* 0x00769AA4 conf 0.55: Virtual method table of Ui_AmountSpinner. The object's vptr is set by maybe_Ui_Card_Ctor. Named virtual slots: 1:maybe_U */
extern void* g_uiGoldCounterWindowVtable[10];        /* 0x00769AF4 conf 0.82: Virtual method table of Ui_GoldCounterWindow. The object's vptr is set by maybe_Ui_GoldWindow_Create. Named virtual slot */
extern void* g_uiEffectIconsWindowVtable[10];        /* 0x00769E74 conf 0.82: Virtual method table of Ui_EffectIconsWindow. The object's vptr is set by Ui_CreditWindow_Ctor, Ui_EffectIconsWindow_Dto */
extern void* g_uiResourceListVtable[2];              /* 0x00769ED8 conf 0.88: Virtual method table of Ui_ResourceList (base Anim_AnimClip). The object's vptr is set by Ui_AnimRefList_Ctor, Ui_Layout */
extern void* g_uiDungeonHpWindowVtable[10];          /* 0x0076A028 conf 0.82: Virtual method table of Ui_DungeonHpWindow (base Ui_GaugeBarWindow). The object's vptr is set by Ui_DungeonHpWindow_Ctor */
extern void* g_uiDungeonMessageWindowVtable[10];     /* 0x0076A078 conf 0.80: Virtual method table of Ui_DungeonMessageWindow. The object's vptr is set by maybe_Ui_CompositeWindow_Ctor1. Named virtu */
extern void* g_uiDungeonOperationWindowVtable[10];   /* 0x0076A0C8 conf 0.50: Virtual method table of Ui_DungeonOperationWindow. The object's vptr is set by maybe_Ui_TwoTextWindow_Ctor. Named virtua */
extern void* g_uiSinglePaneWindowVtable[10];         /* 0x0076A22C conf 0.82: Virtual method table of Ui_SinglePaneWindow. The object's vptr is set by Ui_ItemMenu_CreateRoot, Ui_ShopWindow_CreateSub */
extern void* g_uiTwelveRowNumberedTextWindowVtable[10]; /* 0x0076A390 conf 0.82: Virtual method table of Ui_TwelveRowNumberedTextWindow. The object's vptr is set by Ui_MessageWindow_CtorLayout2, Ui_Mul */
extern void* g_uiThreeRowNumberedTextWindowVtable[10]; /* 0x0076A3F4 conf 0.82: Virtual method table of Ui_ThreeRowNumberedTextWindow. The object's vptr is set by Ui_MessageWindow_CtorLayout2, Ui_Mult */
extern void* g_uiMessageWindowVtableB[10];           /* 0x0076A458 conf 0.88: Virtual method table of Ui_MessageWindow. The object's vptr is set by Ui_MessageWindow_CtorLayout2. Named virtual slots: */
extern void* g_uiMessageWindowVtableC[10];           /* 0x0076AAAC conf 0.82: Virtual method table of Ui_MessageWindow. The object's vptr is set by Ui_MessageWindow2_CtorB, maybe_Ui_MessageWindow_Su */
extern void* g_uiPopupSpeakerBalloonVtable;          /* 0x0076AB34 conf 0.50: Virtual method table of speaker-balloon popup entry created by maybe_Ui_PopupEntry_SpawnSpeakerBalloon. The object's vpt */
extern void* g_uiSubObjectVtable[6];                 /* 0x0076AB4C conf 0.70: Virtual method table of Ui_SubObject. The object's vptr is set by maybe_Ui_SubObject_Create, maybe_Ui_SubObject_Dtor. Na */
extern void* g_uiAnimInOutWindowVtable[10];          /* 0x0076AB6C conf 0.50: Virtual method table of Ui_AnimInOutWindow (base Anim_AnimClip). The object's vptr is set by Ui_AnimRefList_CreateTriple */
extern void* maybe_g_uiPanelSmallVtableA[10];        /* 0x0076ABD0 conf 0.45: Virtual method table of small 0x16C-byte panel allocated by maybe_Ui_Panel_CtorSmall (variant with Ui_Element_ResolveRes */
extern void* maybe_g_uiPanelSmallVtableB[10];        /* 0x0076AC20 conf 0.45: Virtual method table of small 0x16C-byte panel allocated by maybe_Ui_Panel_CtorSmall (variant with Ui_Element_ResolveRes */
extern void* g_uiMessageWindowVtableD[10];           /* 0x0076ACBC conf 0.76: Virtual method table of Ui_MessageWindow. The object's vptr is set by Ui_MessageWindow_InitBase, Ui_MessageWindow_Releas */
extern void* g_uiMessagePartTableVtable[10];         /* 0x0076AD44 conf 0.70: Virtual method table of Ui_MessagePartTable. The object's vptr is set by maybe_Ui_MessagePartTable_Create. Named virtual */
extern void* g_uiMessagePartTableSmallVtable[10];    /* 0x0076AD94 conf 0.70: Virtual method table of Ui_MessagePartTableSmall. The object's vptr is set by maybe_Ui_MessagePartTable_CreateSmall. Nam */
extern void* g_uiMessagePageVtableB[10];             /* 0x0076ADE4 conf 0.70: Virtual method table of Ui_MessagePage. The object's vptr is set by Ui_PanelMessageWindow_LoadPanels. Named virtual slot */
extern void* maybe_g_uiPanelMessageElementVtable[10]; /* 0x0076AE34 conf 0.45: Virtual method table of UI element of the panel-message window (slot 4 Ui_MessageWindow_BindSelectAnims), installed by U */
extern void* g_uiEquipmentListWindowVtable[10];      /* 0x0076B1D8 conf 0.58: Virtual method table of Ui_EquipmentListWindow. The object's vptr is set by Ui_ItemMenu_CreateRoot, Ui_ItemMenu_DestroyR */
extern void* g_uiLabelVtable[10];                    /* 0x0076B4BC conf 0.70: Virtual method table of Ui_Label. The object's vptr is set by Ui_CasinoWindow_Ctor. Named virtual slots: 1:maybe_Ui_Labe */
extern void* g_uiTxtRightWindowVtable[10];           /* 0x0076B754 conf 0.70: Virtual method table of Ui_TxtRightWindow. The object's vptr is set by Ui_CasinoWindow_Ctor, Ui_ShopWindow_CreateSubObje */
extern void* maybe_g_uiSmithMenuDetailPanelVtable[4]; /* 0x0076B7E0 conf 0.50: Four-word table stamped by maybe_Ui_SmithMenu_DetailPanel_Dtor (slot 0 is that destructor); it is the vtable of the smit */
extern void* g_cameraMotionSetVtable[10];            /* 0x0076B7F0 conf 0.88: Virtual method table of Camera_MotionSet. The object's vptr is set by Camera_MotionSet_Init, Ui_SmithMenu_SubWindow_Ctor */
extern void* g_uiCameraAnimWindowVtable;             /* 0x0076B840 conf 0.58: Virtual method table of Ui_CameraAnimWindow. The object's vptr is set by Ui_CameraAnimWindow_CtorBase. Named virtual slo */
extern void* g_uiSmithMenuVtable[10];                /* 0x0076B8F8 conf 0.88: Virtual method table of Ui_SmithMenu. The object's vptr is set by Ui_SmithMenu_Ctor, Ui_SmithMenu_Dtor. Named virtual sl */
extern void* g_uiTsuyosaWindowVtableC[10];           /* 0x0076BA2C conf 0.86: Virtual method table of Ui_TsuyosaWindow (base Ui_Row). The object's vptr is set by Ui_TsuyosaWindow_ChildCtor. Named vi */
extern void* g_uiFourRowIconWindowVtable[10];        /* 0x0076BAC4 conf 0.82: Virtual method table of Ui_FourRowIconWindow. The object's vptr is set by Ui_FourRowIconWindow_Ctor. Named virtual slots */
extern void* g_uiStatusParamWindowVtable[10];        /* 0x0076BB28 conf 0.88: Virtual method table of Ui_StatusParamWindow. The object's vptr is set by Ui_StatusParamWindow_Ctor, Ui_StatusParamWindo */
extern void* g_uiMenuWindowVtable[10];               /* 0x0076BB8C conf 0.88: Virtual method table of Ui_MenuWindow (base Ui_Window). The object's vptr is set by Ui_MenuWindow_Ctor, maybe_Ui_MenuWin */
extern void* g_uiTwoAxisSelectWindowVtable[10];      /* 0x0076BC10 conf 0.58: Virtual method table of Ui_TwoAxisSelectWindow. The object's vptr is set by Ui_TwoAxisSelectWindow_Ctor. Named virtual s */
extern void* maybe_g_rodata_0076bd1c;                /* 0x0076BD1C conf 0.30: Descriptor stored at +0x10 of the text part built by maybe_Ui_TextPart_Create; the following 0x20 bytes are a separate G */
extern void* g_uiNameStatWindowVtable[10];           /* 0x0076C778 conf 0.82: Virtual method table of Ui_NameStatWindow. The object's vptr is set by Ui_BattleWindowManager_CreateWindows, Ui_SetupCom */
extern void* g_uiFourLineMenuWindowVtable[10];       /* 0x0076C814 conf 0.82: Virtual method table of Ui_FourLineMenuWindow. The object's vptr is set by Ui_SetupIrekaeWindow. Named virtual slots: 1: */
extern void* g_uiFourLineMenuWindowVtableB[10];      /* 0x0076C8B0 conf 0.82: Virtual method table of Ui_FourLineMenuWindow. The object's vptr is set by Ui_SetupIrekaeWindow. Named virtual slots: 1: */
extern void* g_uiPartyPanelVtable[10];               /* 0x0076C94C conf 0.76: Virtual method table of Ui_PartyPanel (base Ui_BattleCommandWindow). The object's vptr is set by Ui_SetupIrekaeWindow, U */
extern void* g_uiTwoLineTextWindowVtable[10];        /* 0x0076CA4C conf 0.82: Virtual method table of Ui_TwoLineTextWindow. The object's vptr is set by Ui_SetupIrekaeWindow, Ui_SetupSwapWindow. Name */
extern void* g_uiSixPairMenuWindowVtable[10];        /* 0x0076CB4C conf 0.58: Virtual method table of Ui_SixPairMenuWindow. The object's vptr is set by Ui_SetupEquipWindow. Named virtual slots: 2:Ui */
extern void* maybe_g_uiPagedTextChildWindowVtable[10]; /* 0x0076CCB0 conf 0.50: Virtual method table of paged-text child window set up by Ui_SetupSakusenWindow (slot 8 maybe_Ui_PagedTextChildWindow_In */
extern void* g_uiSwapWindowVtable[10];               /* 0x0076CDB0 conf 0.82: Virtual method table of Ui_SwapWindow (base Ui_WindowBase). The object's vptr is set by Ui_SwapWindow_SlotTable_Ctor. Na */
extern void* g_uiShopWindowVtableB[10];              /* 0x0076CE4C conf 0.76: Virtual method table of Ui_ShopWindow. The object's vptr is set by Ui_SetupIrekaeWindow, Ui_SetupSwapWindow. Named virtu */
extern void* maybe_g_uiScreenObjectVtable[10];       /* 0x0076CEEC conf 0.50: Virtual method table of UI screen object built by maybe_Ui_ScreenObject_Ctor (slot 1 Ui_ScreenObject_Dtor). The object's */
extern void* g_uiTxtOnlyWindowVtable[10];            /* 0x0076CF1C conf 0.88: Virtual method table of Ui_TxtOnlyWindow. The object's vptr is set by Ui_TxtOnlyWindow_CtorB. Named virtual slots: 1:Ui_ */
extern void* g_uiListWidgetScreenVtable[6];          /* 0x0076CF80 conf 0.88: Virtual method table of Ui_ListWidget_Screen. The object's vptr is set by maybe_Ui_ListWidget_Screen_Ctor, maybe_Ui_List */
extern void* g_uiPopupMonsterPairVtable;             /* 0x0076CFA0 conf 0.50: Virtual method table of monster-pair popup entry allocated by Ui_PopupEntry_SpawnForMonsterPair (0x218-byte entry). The  */
extern void* g_uiMessageWindowVtableE[16];           /* 0x0076D028 conf 0.88: Virtual method table of Ui_MessageWindow. The object's vptr is set by maybe_Ui_MessageWindow_CreateFromDefs. Named virtu */
extern void* g_uiMessageWindowVtableF[16];           /* 0x0076D070 conf 0.88: Virtual method table of Ui_MessageWindow. The object's vptr is set by maybe_Ui_MessageWindow_CreateFromDefsB. Named virt */
extern void* g_uiThreeLineTwoSelectWindowVtable[10]; /* 0x0076D0B8 conf 0.58: Virtual method table of Ui_ThreeLineTwoSelectWindow. The object's vptr is set by maybe_Ui_Table_DtorDelete. Named virtua */
extern void* g_uiSevenLineSelectWindowVtable[10];    /* 0x0076D11C conf 0.82: Virtual method table of Ui_SevenLineSelectWindow. The object's vptr is set by Ui_SevenLineSelectWindow_Dtor, maybe_Ui_Ta */
extern void* g_uiPlaceNameWindowVtable[10];          /* 0x0076D180 conf 0.82: Virtual method table of Ui_PlaceNameWindow. The object's vptr is set by maybe_Ui_ModelSelect_Ctor. Named virtual slots:  */
extern void* g_uiNineLineTextWindowVtable[10];       /* 0x0076D544 conf 0.82: Virtual method table of Ui_NineLineTextWindow. The object's vptr is set by Ui_MessageWindow_CtorLayout2, Ui_MultiTextWin */
extern void* g_uiNumberedTextWindowVtable[10];       /* 0x0076D5DC conf 0.88: Virtual method table of Ui_NumberedTextWindow. The object's vptr is set by Ui_NumberedTextWindow_Ctor. Named virtual slo */
extern void* g_uiTitleNameWindowVtable[10];          /* 0x0076D640 conf 0.86: Virtual method table of Ui_TitleNameWindow. The object's vptr is set by maybe_Ui_TitleNameWindow_Ctor. Named virtual slo */
extern void* maybe_g_uiDescWidgetVtable[6];          /* 0x0076DCF0 conf 0.50: Virtual method table of widget built by maybe_Ui_Widget_CreateFromDesc (slot 1 Ui_DescWidget_DeleteDtor). The object's v */
extern void* g_menuHorseRaceVtable[10];              /* 0x0076DD10 conf 0.80: Virtual method table of Menu_HorseRace (base Ui_AnimRef). The object's vptr is set by Ui_MessageWindow_CreatePartsB. Nam */
extern void* g_uiTimerDisplayVtableB[10];            /* 0x0076DD60 conf 0.88: Virtual method table of Ui_TimerDisplay (base Ui_AnimatableElement). The object's vptr is set by Ui_TimerDisplay_Ctor. N */
extern void* g_uiColorSelectWindowVtable[10];        /* 0x0076DDD4 conf 0.86: Virtual method table of Ui_ColorSelectWindow. The object's vptr is set by Ui_ColorSelectWindow_Ctor, Ui_Object_DtorWithA */
extern void* g_uiGaugeWindowVtable[10];              /* 0x0076DE64 conf 0.50: Virtual method table of Ui_GaugeWindow. The object's vptr is set by maybe_Ui_Window_CtorWithThreeParts. Named virtual sl */
extern void* g_uiListTextWindowVtable[10];           /* 0x0076E14C conf 0.58: Virtual method table of Ui_ListTextWindow. The object's vptr is set by Ui_RecordDetailWindow_Ctor, Ui_SmithMenu_Ctor. Na */
extern void* g_uiSenrekiWindowVtableB[10];           /* 0x0076E1C4 conf 0.82: Virtual method table of Ui_SenrekiWindow. The object's vptr is set by Ui_SenrekiWindow_CtorRow. Named virtual slots: 2:U */
extern void* g_uiRecordQuestWindowVtable[10];        /* 0x0076E228 conf 0.58: Virtual method table of Ui_RecordQuestWindow. The object's vptr is set by maybe_Ui_IndexPairTable_Ctor, maybe_Ui_Object_ */
extern void* g_messageVoiceBlipPatternLongLine;      /* 0x0076E29C conf 0.70: Static message-voice typing-blip pattern descriptor selected by Ui_MessageVoice_SelectBlipPattern for lineIndex >= 2 wit */
extern void* g_uiTalkWindowVtableB[10];              /* 0x0076E710 conf 0.80: Virtual method table of Ui_TalkWindow. The object's vptr is set by Ui_TalkWindow_Ctor. Named virtual slots: 4:Ui_TalkWin */
extern void* g_uiListWindowVtable[10];               /* 0x0076E760 conf 0.82: Virtual method table of Ui_ListWindow. The object's vptr is set by Ui_ListWindow_Ctor. Named virtual slots: 2:Ui_Widget_ */
extern void* g_uiSmithMenuVtableB[10];               /* 0x0076E7D4 conf 0.82: Virtual method table of Ui_SmithMenu. The object's vptr is set by maybe_Ui_SmithMenu_SubObject_Ctor. Named virtual slots */
extern void* g_uiLoopPaneWindowVtable[10];           /* 0x0076E848 conf 0.58: Virtual method table of Ui_LoopPaneWindow. The object's vptr is set by maybe_Ui_Widget_CreateInstance. Named virtual slo */
extern void* g_uiSakusenWindowDataVtable[10];        /* 0x0076E988 conf 0.60: Virtual method table of data sub-object of the tactics (sakusen) window built by maybe_Ui_SakusenWindow_Data_Ctor (slot  */
extern void* g_uiThreeLineTwoColumnSelectWindowVtable[10]; /* 0x0076EB8C conf 0.58: Virtual method table of Ui_ThreeLineTwoColumnSelectWindow. The object's vptr is set by Ui_ThreeLineTwoColumnSelectWindow */
extern void* g_uiScoreCheckWindowVtable[10];         /* 0x0076EBF0 conf 0.58: Virtual method table of Ui_ScoreCheckWindow. The object's vptr is set by Ui_ScoreCheckWindow_Ctor. Named virtual slots:  */
extern void* g_uiCommandBarVtable[10];               /* 0x0076FB1C conf 0.58: Virtual method table of Ui_CommandBar. The object's vptr is set by Ui_Object_DtorWithRowArray. Named virtual slots: 1:Ui */
extern void* g_uiTxtOnlyWindowVtableB[10];           /* 0x0076FCB8 conf 0.58: Virtual method table of Ui_TxtOnlyWindow. The object's vptr is set by Ui_Window_Ctor. Named virtual slots: 1:Ui_Window_D */
extern void* g_animInterpVtableB[7];                 /* 0x0076FE10 conf 0.80: Virtual method table of Anim_Interp. The object's vptr is set by maybe_Ui_ChildWindowList_Init. Named virtual slots: 2:A */
extern void* maybe_g_uiScreenChildStatusVtable[10];  /* 0x0076FE34 conf 0.45: Virtual method table of status sub-object of the UI screen child (constructed by maybe_Ui_ScreenChild_StatusObject_Ctor) */
extern void* maybe_g_uiScreenChildGaugeVtable[10];   /* 0x0076FE64 conf 0.45: Virtual method table of gauge sub-object of the UI screen child (constructed by maybe_Ui_ScreenChild_GaugeObject_Ctor).  */
extern void* maybe_g_screenChildCameraVtable[10];    /* 0x0076FE94 conf 0.50: Virtual method table of camera sub-object of the UI screen child (Camera_Dtor/SetupFromActor/Update slots; constructed b */
extern void* g_uiDiveCaptureVtable[10];              /* 0x0076FEC4 conf 0.86: Virtual method table of Ui_DiveCapture. The object's vptr is set by HKD, Ui_DiveCapture_Ctor. Named virtual slots: 1:Ui_ */
extern void* g_uiTransitionVtable;                   /* 0x0076FF34 conf 0.70: Virtual method table of Ui_Transition. The object's vptr is set by Ui_Transition_Dtor, maybe_Ui_Card_Ctor. Named virtual */
extern void* g_uiHitIconVtable[10];                  /* 0x0076FF44 conf 0.88: Virtual method table of Ui_HitIcon. The object's vptr is set by Ui_HitIcon_Ctor. Named virtual slots: 1:Ui_HitIcon_Dtor, */
extern void* g_uiPopupEquipCompareVtable;            /* 0x0076FFA8 conf 0.50: Virtual method table of equipment-compare popup entry created by maybe_Ui_PopupEntry_SpawnEquipCompare. The object's vpt */
extern void* maybe_g_uiMessageWindowSpeakerVtable[10]; /* 0x0076FFD8 conf 0.45: Virtual method table of message-window speaker/update table installed by Ui_ScrollBar_Ctor (slot 4 maybe_Ui_MessageWindo */
extern void* g_uiToggleButtonVtable[10];             /* 0x00770028 conf 0.70: Virtual method table of Ui_ToggleButton. The object's vptr is set by maybe_Ui_ToggleButton_Ctor. Named virtual slots: 1: */
extern void* g_uiPartyGaugeWindowVtable[10];         /* 0x0077008C conf 0.86: Virtual method table of Ui_PartyGaugeWindow. The object's vptr is set by Ui_PartyGaugeWindow_Ctor. Named virtual slots:  */
extern void* g_uiEquipmentRowVtable[10];             /* 0x00770100 conf 0.88: Virtual method table of Ui_EquipmentRow. The object's vptr is set by Ui_EquipmentRow_Ctor. Named virtual slots: 1:Ui_Equ */
extern void* g_uiEquipmentRowVtableB[10];            /* 0x007701E4 conf 0.60: Virtual method table of equipment-window row built by Ui_EquipmentRow_CtorSmall (doc: installs vtable 0x7701E4; slot 8 U */
extern void* g_uiThreeLineTextWindowVtable[10];      /* 0x00770260 conf 0.58: Virtual method table of Ui_ThreeLineTextWindow. The object's vptr is set by Ui_MessageWindow_CtorLayout2, Ui_MultiTextWi */
extern void* g_uiPartVtableB[8];                     /* 0x00770374 conf 0.70: Virtual method table of Ui_Part. The object's vptr is set by Ui_Part_Ctor. Named virtual slots: 1:Ui_Part_DeletingDtor,  */
extern void* g_uiMessagePairVtable[10];              /* 0x007712EC conf 0.50: Virtual method table of Ui_MessagePair. The object's vptr is set by maybe_Ui_MessagePairWindow_Ctor. Named virtual slots */
extern void* g_uiChildTransformVtable[10];           /* 0x007713D4 conf 0.80: Virtual method table of Ui_ChildTransform. The object's vptr is set by maybe_Ui_Actor_Create, maybe_Ui_ChildTransform_Ap */
extern void* g_uiItemInfoWindowVtableB[10];          /* 0x00771428 conf 0.76: Virtual method table of Ui_ItemInfoWindow. The object's vptr is set by maybe_Ui_MainMenuText_SetWindowState. Named virtu */
extern void* g_uiStampWindowVtable[10];              /* 0x00771478 conf 0.80: Virtual method table of stamp-card window Ui_StampWindow (doc: installs vtable 0x771478, slot 4 Ui_StampWindow_RefreshSt */
extern void* g_uiSixLineTextWindowVtable[10];        /* 0x007714C8 conf 0.58: Virtual method table of Ui_SixLineTextWindow. The object's vptr is set by maybe_Ui_TreeWidget_Ctor. Named virtual slots: */
extern void* g_uiThreePairNumberWindowVtable[10];    /* 0x0077152C conf 0.86: Virtual method table of Ui_ThreePairNumberWindow. The object's vptr is set by Ui_ThreePairNumberWindow_Ctor. Named virtu */
extern void* g_uiSkillPanelVtableB[10];              /* 0x00771590 conf 0.82: Virtual method table of Ui_SkillPanel. The object's vptr is set by maybe_Ui_SkillPanel_InitParts. Named virtual slots: 2 */
extern void* g_uiItemMenuWindowVtableB[10];          /* 0x007715F4 conf 0.80: Virtual method table of Ui_ItemMenuWindow (base Ui_CheckListWindow). The object's vptr is set by Ui_SkillPanelWindow_Cto */
extern void* maybe_g_textLayoutStateTable;           /* 0x007718A4 conf 0.40: Text-layout state table written by Text_LayoutState_Init / maybe_Ui_ItemDetail_Setup; it holds Party_BuildUsedCharacterL */
extern void* g_uiTextLayoutVtable[10];               /* 0x007718BC conf 0.70: Virtual method table of Ui_TextLayout. The object's vptr is set by maybe_Ui_TextLayout_ObjectCtor. Named virtual slots:  */
extern void* g_uiTextWindowVtable[10];               /* 0x00771920 conf 0.88: Virtual method table of Ui_TextWindow. The object's vptr is set by maybe_Ui_TextWindow_Ctor. Named virtual slots: 1:Ui_T */
extern void* g_uiSlotArrayWindowVtable[10];          /* 0x00771994 conf 0.88: Virtual method table of Ui_SlotArrayWindow. The object's vptr is set by Ui_SixteenRowCheckListWindow_Ctor, Ui_SlotArrayW */
extern void* g_uiSlotSymbolVtable[10];               /* 0x007719F8 conf 0.70: Virtual method table of Ui_SlotSymbol. The object's vptr is set by Ui_SlotSymbol_Ctor. Named virtual slots: 1:Ui_SlotSym */
extern void* g_uiDualDisplayWindowVtable[10];        /* 0x00771A5C conf 0.58: Virtual method table of Ui_DualDisplayWindow. The object's vptr is set by Ui_SlotMachine_PartCtor. Named virtual slots:  */
extern void* g_uiSlotMachineVtable[10];              /* 0x00771AC0 conf 0.70: Virtual method table of Ui_SlotMachine. The object's vptr is set by Ui_ListWindow_CtorBase, Ui_Object_DtorWithArrayD, Ui */
extern void* maybe_g_rodata_00771b38[5];             /* 0x00771B38 conf 0.30: Five-word table referenced by maybe_Ui_SlotWindow_ReelStopSequence; slot 0 is that function itself and the remaining wor */
extern void* g_uiColorGaugeWindowVtable[10];         /* 0x00771B4C conf 0.50: Virtual method table of Ui_ColorGaugeWindow. The object's vptr is set by maybe_Ui_Window_CtorWithSubobject. Named virtua */
extern void* g_uiFiveLineTextWindowVtable[10];       /* 0x00771BB0 conf 0.58: Virtual method table of Ui_FiveLineTextWindow. The object's vptr is set by Ui_FiveLineTextWindow_Ctor. Named virtual slo */
extern void* g_uiEightRowIndexedWindowVtable[10];    /* 0x00771C28 conf 0.58: Virtual method table of Ui_EightRowIndexedWindow. The object's vptr is set by Ui_EightRowIndexedWindow_Ctor, Ui_Window_D */
extern void* g_uiEightRowTextWindowVtable[10];       /* 0x00771C8C conf 0.58: Virtual method table of Ui_EightRowTextWindow. The object's vptr is set by Ui_EightRowTextWindow_Ctor. Named virtual slo */
extern void* g_uiTxtOnlyWindowVtableC[10];           /* 0x00771D0C conf 0.58: Virtual method table of Ui_TxtOnlyWindow. The object's vptr is set by Ui_ComplexWindow_PartCtor. Named virtual slots: 1: */
extern void* g_uiPartyMemberRowVtable;               /* 0x00771D9C conf 0.58: Virtual method table of Ui_PartyMemberRow. The object's vptr is set by maybe_Ui_ListWidget_CreateSubWidgetA. Named virtu */
extern void* g_uiPartyMemberRowVtableB;              /* 0x00771DB8 conf 0.58: Virtual method table of Ui_PartyMemberRow. The object's vptr is set by maybe_Ui_ListWidget_CreateSubWidgetB. Named virtu */
extern void* g_ui3DBackgroundVtable[10];             /* 0x00771DD4 conf 0.88: Virtual method table of Ui_3DBackground. The object's vptr is set by maybe_Ui_3DBackground_Init, maybe_Ui_ListWidget_Ini */
extern void* g_uiProfileWindowVtable[10];            /* 0x00771E34 conf 0.70: Virtual method table of Ui_ProfileWindow. The object's vptr is set by Ui_TsuyosaWindow_PartCtor. Named virtual slots: 1: */
extern void* g_uiFourRowTextWindowVtable[10];        /* 0x00771F70 conf 0.50: Virtual method table of Ui_FourRowTextWindow. The object's vptr is set by maybe_Ui_Widget_Ctor_53A8. Named virtual slots */
extern void* g_uiFiveRowPagedWindowVtable[10];       /* 0x00772008 conf 0.58: Virtual method table of Ui_FiveRowPagedWindow. The object's vptr is set by Ui_FiveRowPagedWindow_Ctor. Named virtual slo */
extern void* g_uiThreeLineTextWindowVtableB[10];     /* 0x00772080 conf 0.55: Virtual method table of Ui_ThreeLineTextWindow. The object's vptr is set by maybe_Ui_Widget_Ctor_5B9C. Named virtual slo */
extern void* maybe_g_uiWidgetVtable[10];             /* 0x007720E4 conf 0.42: Virtual method table of Ui_Widget. The object's vptr is set by Ui_ProfileScreen_Ctor. Named virtual slots: 5:Ui_Cursor_U */
extern void* g_uiFiveRowWindowVtable[10];            /* 0x00772134 conf 0.70: Virtual method table of Ui_FiveRowWindow. The object's vptr is set by Ui_FiveRowWindow_Ctor, maybe_Ui_FiveRowWindow_Dtor */
extern void* maybe_g_containerHandleNodeVtable;      /* 0x007721CC conf 0.50: Virtual method table of container node base table of a large UI screen (slot 1 Container_HandleNode_Dtor, slot 5 maybe_U */
extern void* g_uiTitleNameWindowVtableB[10];         /* 0x007729FC conf 0.55: Virtual method table of Ui_TitleNameWindow. The object's vptr is set by Ui_SetupEquipWindow. Named virtual slots: 1:mayb */
extern void* g_battlePopupVtable[10];                /* 0x00772AEC conf 0.70: Virtual method table of Battle_Popup. The object's vptr is set by Ui_SetupSakusenWindow, maybe_Battle_Popup_DtorArray. N */
extern void* g_uiArcListWindowVtable[47];            /* 0x00772C68 conf 0.76: Virtual method table of Ui_ArcListWindow. The object's vptr is set by maybe_Ui_ScreenChild_WindowObject_Ctor. Named virt */
extern void* g_uiGoldWindowVtableB[10];              /* 0x00772D54 conf 0.50: Virtual method table of Ui_GoldWindow. The object's vptr is set by maybe_Ui_GoldWindow_Create. Named virtual slots: 4:Ui */
extern void* g_uiCasinoJackpotWindowVtable[10];      /* 0x00772DA4 conf 0.88: Virtual method table of Ui_CasinoJackpotWindow (base Ui_AnimRef). The object's vptr is set by Ui_CasinoJackpotWindow_Cto */
extern void* g_uiDigitRowWidgetVtable[10];           /* 0x00772F8C conf 0.55: Virtual method table of Ui_DigitRowWidget. The object's vptr is set by maybe_Ui_Widget_Ctor_CB9C. Named virtual slots: 1 */
extern void* g_uiEquipWindowVtableB[10];             /* 0x00773114 conf 0.55: Virtual method table of Ui_EquipWindow. The object's vptr is set by Ui_EquipWindow_CtorBase. Named virtual slots: 1:mayb */
extern void* g_uiDigitDemoVtable[10];                /* 0x00773178 conf 0.80: Virtual method table of Ui_DigitDemo. The object's vptr is set by maybe_Ui_StatCompare_Create. Named virtual slots: 4:ma */
extern void* g_uiSlideWindowVtable;                  /* 0x00773348 conf 0.70: Virtual method table of Ui_SlideWindow (primary table; doc says a secondary table sits at object+0x258). The object's vp */
extern void* maybe_g_uiPopupDescriptorVtableA;       /* 0x00773728 conf 0.45: Virtual method table of one of the generic popup-entry tables used by Ui_PopupEntry_SpawnFromDescriptor (descriptor vari */
extern void* g_uiSelectListWindowVtableB[10];        /* 0x00773740 conf 0.50: Virtual method table of Ui_SelectListWindow. The object's vptr is set by Ui_SakusenWindow_Dtor, Ui_SelectListWindow_Ctor */
extern void* g_fieldSceneObjectVtableB;              /* 0x007737B0 conf 0.70: Virtual method table of Field_SceneObject. The object's vptr is set by maybe_Ui_GuideWindow_CreateBackgroundSprite. Name */
extern void* g_uiSkillPanelBaseVtable[10];           /* 0x00773994 conf 0.70: Virtual method table of Ui_SkillPanel base object built by Ui_SkillPanel_CtorBase (slot 8 Ui_SkillPointWindow_Init). The */
extern void* g_uiPokerDisplayWindowVtable[10];       /* 0x00773B40 conf 0.88: Virtual method table of Ui_PokerDisplayWindow. The object's vptr is set by Ui_PokerDisplayWindow_Ctor, maybe_Ui_PokerDis */
extern void* maybe_g_rodata_00773ba4[4];             /* 0x00773BA4 conf 0.30: Four zero words stamped by Ui_PresentWindow_Ctor (a placeholder table whose virtual functions are filled in later); noth */
extern void* g_uiPagedTextListWindowVtable[10];      /* 0x00773BB4 conf 0.58: Virtual method table of Ui_PagedTextListWindow. The object's vptr is set by Ui_PagedTextListWindow_Ctor. Named virtual s */
extern void* maybe_g_uiHudTargetLayoutVtable;        /* 0x00773C2C conf 0.45: Virtual method table of HUD-target layout object installed by Ui_MonsterRecord_Ctor (slot 3 Ui_HudTarget_GetLayoutRecord */
extern void* g_uiTextPaneVtable[10];                 /* 0x00773C50 conf 0.55: Virtual method table of Ui_TextPane. The object's vptr is set by maybe_Ui_SenrekiWindow_CtorB. Named virtual slots: 1:ma */
extern void* g_uiTextListWidgetVtable[10];           /* 0x00773CB4 conf 0.55: Virtual method table of Ui_TextListWidget. The object's vptr is set by maybe_Ui_FaceIcon_Init. Named virtual slots: 1:ma */
extern void* maybe_g_uiTextListWidgetNodeVtable[4];  /* 0x00773D18 conf 0.45: Four-word node table stamped by maybe_Ui_TextListWidget_Ctor; slot 0 is the text-list widget deinit at 0x478B60 and the  */
extern void* g_uiTextListWidgetVtableB;              /* 0x00773D28 conf 0.70: Virtual method table of Ui_TextListWidget. The object's vptr is set by maybe_Ui_Toggle_Init. Named virtual slots: 2:Ui_T */
extern void* g_messageVoiceBlipPatternLongA[4];      /* 0x00773DE0 conf 0.70: Static message-voice typing-blip pattern descriptor A (50% weight for long runs) selected by Ui_MessageVoice_SelectBlipP */
extern void* g_messageVoiceBlipPatternLongB[4];      /* 0x00773DF0 conf 0.70: Static message-voice typing-blip pattern descriptor B (30% weight for long runs) selected by Ui_MessageVoice_SelectBlipP */
extern void* g_messageVoiceBlipPatternLongC[4];      /* 0x00773E00 conf 0.70: Static message-voice typing-blip pattern descriptor C (20% weight for long runs) selected by Ui_MessageVoice_SelectBlipP */
extern void* g_messageVoiceBlipPatternDefault[4];    /* 0x00773E10 conf 0.70: Static default (short-line) message-voice typing-blip pattern descriptor selected by Ui_MessageVoice_SelectBlipPattern.  */
extern void* g_uiSakusenWindowBaseVtable[3];         /* 0x00773E84 conf 0.70: Virtual method table of base vtable of the tactics (sakusen) window (3 slots, slot 0 Ui_SakusenWindow_DtorBase). The obj */
extern void* maybe_g_uiMessageWindowLayoutVtable;    /* 0x00773E98 conf 0.45: Layout helper table stamped by Ui_MessageWindow_CtorLayout2; slot 2 is Ui_PaneBinding_BindToLayout, the other words are  */
extern void* g_uiTwoLineMessageWindowVtable[10];     /* 0x00773F20 conf 0.70: Virtual method table of Ui_TwoLineMessageWindow. The object's vptr is set by maybe_Ui_SakusenWindow_CtorPane. Named virt */
extern void* g_uiSakusenWindowSubPaneVtable[10];     /* 0x00773FE8 conf 0.65: Virtual method table of sub-pane of the tactics (sakusen) window built by maybe_Ui_SakusenWindow_CtorPaneB (slot 1 maybe */
extern void* g_uiChoiceSelectWindowVtable[10];       /* 0x007740A0 conf 0.58: Virtual method table of Ui_ChoiceSelectWindow. The object's vptr is set by Ui_ChoiceSelectWindow_Ctor. Named virtual slo */
extern void* g_uiPartySelectWindowVtable[10];        /* 0x00774104 conf 0.58: Virtual method table of Ui_PartySelectWindow. The object's vptr is set by Ui_PartySelectWindow_CtorRows. Named virtual s */
extern void* g_uiPartySelectWindowVtableB[10];       /* 0x00774168 conf 0.50: Virtual method table of Ui_PartySelectWindow. The object's vptr is set by maybe_Ui_MemberRowWidget_Create. Named virtual */
extern void* g_uiTwoPositionSelectorVtable[10];      /* 0x007741BC conf 0.86: Virtual method table of Ui_TwoPositionSelector. The object's vptr is set by Ui_TwoPositionSelector_Ctor. Named virtual s */
extern void* g_uiDrawListVtable[6];                  /* 0x007743A0 conf 0.82: Virtual method table of Ui_DrawList. The object's vptr is set by Ui_AllocWidget_Dtor, Ui_NamedEntry_Dtor, maybe_Monster_ */
extern void* maybe_g_containerHandleNodeVtableB;     /* 0x00774444 conf 0.50: Virtual method table of second container-node base table of a large UI screen (slot 1 Container_HandleNode_DtorB, slot 5 */
extern void* g_battlePartyMemberVtable;              /* 0x007746EC conf 0.70: Virtual method table of Battle_PartyMember. The object's vptr is set by maybe_Ui_ScreenCtor_vt7746EC. Named virtual slot */
extern void* g_uiArcListWindowVtableB[47];           /* 0x00774FDC conf 0.82: Virtual method table of Ui_ArcListWindow. The object's vptr is set by Camera_Shake_Dtor, Ui_ArcListWindow_CtorParts, Ui_ */
extern void* g_uiArcListWindowVtableC[47];           /* 0x007750B0 conf 0.82: Virtual method table of Ui_ArcListWindow. The object's vptr is set by maybe_Ui_ScreenCtor_vt7750B0. Named virtual slots: */
extern void* g_uiMotionPathVtable[10];               /* 0x00775184 conf 0.88: Virtual method table of Ui_MotionPath. The object's vptr is set by Ui_MotionPath_Dtor, maybe_Ui_ScreenCtor_vt775184. Nam */
extern void* g_uiDungeonBattleWindowVtable[10];      /* 0x00775350 conf 0.86: Virtual method table of Ui_DungeonBattleWindow. The object's vptr is set by Ui_DungeonBattleWindow_Ctor. Named virtual s */
extern void* g_uiSixRowTextWidgetVtable[10];         /* 0x007754CC conf 0.58: Virtual method table of Ui_SixRowTextWidget. The object's vptr is set by Ui_MessageWindow_CtorLayout2, Ui_MultiTextWindo */
extern void* maybe_g_uiPopupDescriptorVtableB;       /* 0x0077559C conf 0.45: Virtual method table of one of the generic popup-entry tables used by Ui_PopupEntry_SpawnFromDescriptor (descriptor vari */
extern void* maybe_g_uiPopupDescriptorVtableC;       /* 0x007755B4 conf 0.45: Virtual method table of one of the generic popup-entry tables used by Ui_PopupEntry_SpawnFromDescriptor (descriptor vari */
extern void* maybe_g_rodata_007755cc[4];             /* 0x007755CC conf 0.30: Four-word table stamped by maybe_Ui_MessageWindow_ApplyIconStyles; slot 0 is maybe_Ui_LogFormat and the rest is zero, so */
extern void* g_uiStampWindowVtableB[10];             /* 0x007755DC conf 0.58: Virtual method table of Ui_StampWindow. The object's vptr is set by maybe_Ui_Screen_DtorDelete_2. Named virtual slots: 2 */
extern void* g_uiItemTextWindowVtable[10];           /* 0x00775640 conf 0.50: Virtual method table of Ui_ItemTextWindow. The object's vptr is set by maybe_Ui_Window_Create4Sub. Named virtual slots:  */
extern void* g_actorActionIvyDownVtable[11];         /* 0x007756F8 conf 0.70: Virtual method table of ActorAction_IvyDown. The object's vptr is set by maybe_Ui_GetTableSingleton. Named virtual slots */
extern void* maybe_g_uiRecordDetailTextListVtable[10]; /* 0x0077573C conf 0.45: Virtual method table of text-list sub-object of the record-detail window (slot 1 maybe_Ui_Object_DeleteViaVtable, slot 7 */
extern void* g_uiSmithMenuVtableC[24];               /* 0x007757E4 conf 0.58: Virtual method table of Ui_SmithMenu. The object's vptr is set by maybe_Ui_UpdateCharaStatus. Named virtual slots: 2:Ui_ */
extern void* g_uiMessagePageVtableC[10];             /* 0x0077584C conf 0.50: Virtual method table of Ui_MessagePage. The object's vptr is set by Ui_SmithMenu_Ctor. Named virtual slots: 4:Ui_Message */
extern void* g_uiNumberTextWidgetVtable[10];         /* 0x0077589C conf 0.82: Virtual method table of Ui_NumberTextWidget. The object's vptr is set by maybe_Ui_DiveForm_Ctor. Named virtual slots: 1: */
extern void* g_uiEightLineTextWindowVtable[10];      /* 0x00775900 conf 0.82: Virtual method table of Ui_EightLineTextWindow. The object's vptr is set by maybe_Ui_DiveForm_Ctor. Named virtual slots: */
extern void* maybe_g_uiEquipListRowVtable;           /* 0x007759B4 conf 0.45: Virtual method table of equipment-list row object written by maybe_Ui_EquipWindow_UpdateBestItems (slot 2 maybe_Ui_ListR */
extern void* g_battleActionGuardVtable;              /* 0x00775B74 conf 0.70: Virtual method table of Battle_Action_Guard. The object's vptr is set by maybe_Ui_ScreenCtor_vt775C54. Named virtual slo */
extern void* g_uiMessageTextWindowVtable[10];        /* 0x00775E10 conf 0.58: Virtual method table of Ui_MessageTextWindow. The object's vptr is set by maybe_Ui_BattleCommandPopup_Create. Named virt */
extern void* g_battleCommandListWindowVtable[10];    /* 0x00775EAC conf 0.70: Virtual method table of Battle_CommandListWindow. The object's vptr is set by Ui_BattleWindowManager_CreateWindows, Ui_S */
extern void* g_uiMessageSubTextWindowVtable[10];     /* 0x00775FAC conf 0.58: Virtual method table of Ui_MessageSubTextWindow. The object's vptr is set by Ui_EquipWindow_SubWidget_Ctor. Named virtua */
extern void* maybe_g_uiMessageWindowFieldPaneTable[6]; /* 0x00776048 conf 0.40: Six-word field-pane table stamped by Ui_MessageWindow_CtorFieldPanes; it stores the pane update/creation callbacks for t */
extern void* g_animInterpVtableC[7];                 /* 0x00776060 conf 0.80: Virtual method table of Anim_Interp. The object's vptr is set by maybe_Ui_ListRowData_Ctor. Named virtual slots: 2:Anim_ */
extern void* maybe_g_uiWidgetVtableB[10];            /* 0x007760E8 conf 0.45: Virtual method table of Ui_Widget. The object's vptr is set by maybe_Ui_Widget_Ctor_7760E8. Named virtual slots: 1:maybe */
extern void* g_uiPopupLogEntryVtable;                /* 0x0077614C conf 0.50: Virtual method table of current-log popup entry created by maybe_Ui_PopupEntry_SpawnCurrentLogEntry. The object's vptr i */
extern void* g_uiCharacterEntryVtable[10];           /* 0x00776164 conf 0.55: Virtual method table of Ui_CharacterEntry. The object's vptr is set by maybe_Ui_CharacterEntry_Ctor. Named virtual slots */
extern void* g_uiPartyListWindowVtable[10];          /* 0x00776208 conf 0.88: Virtual method table of Ui_PartyListWindow. The object's vptr is set by Ui_PartyListWindow_Ctor. Named virtual slots: 1: */
extern void* g_uiValueHolderVtable[8];               /* 0x0077635C conf 0.82: Virtual method table of Ui_ValueHolder. The object's vptr is set by maybe_Ui_ValueHolder_Ctor. Named virtual slots: 1:ma */
extern void* maybe_g_uiMessageWindowIconSlotTable[4]; /* 0x00776AB0 conf 0.40: Four-word table used by Ui_MessageWindow_SetTextId and maybe_Ui_MessageWindow_ApplyIconStyles; slot 0 is Ui_ItemSlot_Set */
extern void* g_uiIconRowVtable[10];                  /* 0x00776AC0 conf 0.58: Virtual method table of Ui_IconRow. The object's vptr is set by maybe_Ui_MainWindow_Ctor. Named virtual slots: 1:Ui_Obje */
extern void* maybe_g_uiListRowDrawTableA[5];         /* 0x00776B58 conf 0.40: Five-word list-row draw table written by maybe_Ui_EquipWindow_UpdateBestItems; slot 2 is maybe_Ui_ListRow_DrawDispatchB. */
extern void* maybe_g_uiListRowDrawTableB[5];         /* 0x00776B6C conf 0.40: Five-word list-row draw table written by maybe_Ui_EquipWindow_UpdateBestItems; slot 2 is maybe_Ui_ListRow_DrawDispatchC. */
extern void* g_uiPokerCardObjectVtable[11];          /* 0x00776BE8 conf 0.55: Virtual method table of poker card object (slot 1 Ui_PokerWindow_CardObject_DtorDelete). The object's vptr is set by may */
extern void* maybe_g_uiPokerCardWidgetVtable[10];    /* 0x00776C1C conf 0.50: Virtual method table of card widget of the poker window (slot 1 Ui_Object_PlayAnimationPoor_DtorDelete, slot 4 Ui_PokerW */
extern void* maybe_g_rodata_00776c6c[6];             /* 0x00776C6C conf 0.30: Six-word table written by maybe_Ui_EquipWindow_UpdateBestItems; it holds list-row draw callbacks and no class name was r */
extern void* g_uiRouletteSelectGridVtable[10];       /* 0x00776C84 conf 0.58: Virtual method table of Ui_RouletteSelectGrid. The object's vptr is set by Ui_RouletteSelectGrid_Ctor. Named virtual slo */
extern void* g_uiItemHaveListVtable[10];             /* 0x00776CE8 conf 0.50: Virtual method table of Ui_ItemHaveList (base ItemList_Iterator). The object's vptr is set by maybe_Ui_Object_CtorWithSl */
extern void* g_uiJumonEntryVtable;                   /* 0x00776D4C conf 0.55: Virtual method table of spell-window (jumon) entry created by maybe_Ui_JumonWindow_CreateEntry. The object's vptr is set */
extern void* g_uiStrengthCompareWindowVtable[10];    /* 0x00776D9C conf 0.58: Virtual method table of Ui_StrengthCompareWindow. The object's vptr is set by Ui_StrengthCompareWindow_Ctor. Named virtu */
extern void* g_uiSakusenWindowSlotWidgetVtable[10];  /* 0x00776E00 conf 0.60: Virtual method table of slot widget of the tactics (sakusen) window built by maybe_Ui_SakusenWindow_CtorSlotWidget. The  */
extern void* g_uiSakusenSlotListVtable[10];          /* 0x00776E64 conf 0.60: Virtual method table of sakusen (tactics) slot-list variant built by Ui_SakusenWindow_SlotList_Ctor (overrides the selec */
extern void* g_uiTwoColumnValueListVtable[10];       /* 0x00776ED4 conf 0.86: Virtual method table of Ui_TwoColumnValueList. The object's vptr is set by Ui_SakusenWindow_CtorSlotTable. Named virtual */
extern void* g_fieldPartyMemberModelVtable;          /* 0x00777304 conf 0.70: Virtual method table of FieldParty_MemberModel. The object's vptr is set by maybe_Ui_ScreenCtor_vt777304. Named virtual  */
extern void* g_fieldPartyMemberModelVtableB;         /* 0x00777760 conf 0.70: Virtual method table of FieldParty_MemberModel. The object's vptr is set by maybe_Ui_ScreenCtor_vt777348. Named virtual  */
extern void* g_uiBattleTargetMarkerVtable;           /* 0x00777874 conf 0.70: Virtual method table of Ui_BattleTargetMarker. The object's vptr is set by Ui_BattleTargetMarker_DeleteDtor, maybe_Ui_Sc */
extern void* g_uiFourStateWidgetVtable[10];          /* 0x00777B9C conf 0.86: Virtual method table of Ui_FourStateWidget. The object's vptr is set by H22, Ui_FourStateWidget_Ctor, Ui_Object_DeleteDt */
extern void* maybe_g_uiMessageWindowTimerPaneTable[6]; /* 0x00777C5C conf 0.40: Six-word timer-pane table stamped by Ui_MessageWindow_CtorFieldPanes; slots 3 and 4 are Ui_Window_UpdateTwoTimerSlots /  */
extern void* maybe_g_uiMessageWindowSoundPaneTable[6]; /* 0x00777CAC conf 0.40: Six-word sound-pane table stamped by Ui_MessageWindow_CtorFieldPanes; slot 3 is Ui_Window_SetVisibleWithSound. Reference */
extern void* g_uiArcListWindowVtableD[47];           /* 0x00777CC4 conf 0.82: Virtual method table of Ui_ArcListWindow. The object's vptr is set by maybe_Ui_ArcListWindow_CtorEmbedded. Named virtual */
extern void* maybe_g_uiPokerSubObjectVtable[4];      /* 0x00777D98 conf 0.50: Virtual method table of sub-object of the poker window (slot 0 Ui_PokerWindow_SubObject_Dtor). The object's vptr is set  */
extern void* g_uiSlotMachineVtableB[10];             /* 0x00777DA8 conf 0.82: Virtual method table of Ui_SlotMachine. The object's vptr is set by maybe_Ui_SlotMachine_CtorSubParts. Named virtual slo */
extern void* g_fieldMarker3DVtable[17];              /* 0x00777E0C conf 0.70: Virtual method table of Field_Marker3D. The object's vptr is set by maybe_Ui_MessageWindow_CreateBrief. Named virtual sl */
extern void* g_uiListVtableB[10];                    /* 0x00777F94 conf 0.70: Virtual method table of Ui_List. The object's vptr is set by Ui_List_DeleteDtor, Ui_PagedListWindow_Ctor. Named virtual  */
extern void* g_uiPagedListWindow2Vtable[10];         /* 0x0077800C conf 0.80: Virtual method table of Ui_PagedListWindow2. The object's vptr is set by maybe_Ui_PagedListWindow_CtorVariant. Named vir */
extern void* g_uiEquipWindowVtableC[10];             /* 0x007780A8 conf 0.82: Virtual method table of Ui_EquipWindow (base Ui_PaneGroup). The object's vptr is set by Ui_EquipWindow_SubObject_Ctor. N */
extern void* g_gfxSpriteObjectVtableB[8];            /* 0x0077819C conf 0.82: Virtual method table of Gfx_SpriteObject (base Ui_MessageWindow). The object's vptr is set by Ui_Layout_AllocSlotNodeB.  */
extern void* maybe_g_gfxSpriteObjectCallbackVtable[8]; /* 0x007781EC conf 0.45: Gfx sprite-object callback table installed by maybe_Ui_Overlay_ReleaseSubObjects / maybe_Ui_Widget_Ctor_vt7781EC; slot 2 */
extern void* g_uiUmaWindowVtable[10];                /* 0x007786E8 conf 0.82: Virtual method table of Ui_UmaWindow. The object's vptr is set by maybe_Ui_MemberListWindow_Dtor, maybe_Ui_UmaWindow_Dto */
extern void* g_uiUmaWindowVtableB[6];                /* 0x0077874C conf 0.88: Virtual method table of Ui_UmaWindow. The object's vptr is set by Ui_UmaWindow_Dtor, maybe_Ui_UmaWindow_Ctor. Named virt */
extern void* maybe_g_rodata_0077876c;                /* 0x0077876C conf 0.30: Data/function table written by Ui_ItemListCore_Ctor; it mixes Work/Data helper pointers with Actor_Action_Trail slots an */
extern void* maybe_g_rodata_00778794;                /* 0x00778794 conf 0.30: Data/function table referenced by Ui_MessageWindow_SetTextId; it contains Ui_ListWindow_FillThreeColumnRows and Actor_Ac */
extern void* g_uiPagedListWindow3Vtable[10];         /* 0x007788DC conf 0.58: Virtual method table of Ui_PagedListWindow3. The object's vptr is set by maybe_Ui_ListWindow_Ctor_vt7788DC. Named virtua */
extern void* maybe_g_uiListWindowChildVtable[4];     /* 0x00778954 conf 0.45: Four-word child-window table created by maybe_Ui_ListWindow_MakeChildWindow; only slot 0 (0x4CE9A8) is filled. Reference */
extern void* g_uiRouletteWheelVtable[10];            /* 0x00778964 conf 0.58: Virtual method table of Ui_RouletteWheel. The object's vptr is set by maybe_Ui_FaceIcon_Init. Named virtual slots: 1:may */
extern void* g_uiValuePanelVtable[10];               /* 0x007789C8 conf 0.58: Virtual method table of Ui_ValuePanel. The object's vptr is set by Ui_RecordDetailWindow_Ctor. Named virtual slots: 1:ma */
extern void* g_uiSevenRowListVtable[10];             /* 0x00778A90 conf 0.82: Virtual method table of Ui_SevenRowList. The object's vptr is set by maybe_Ui_SevenRowList_Ctor. Named virtual slots: 2: */
extern void* g_uiMemberOrderWindowVtable[10];        /* 0x00778AF4 conf 0.88: Virtual method table of Ui_MemberOrderWindow. The object's vptr is set by maybe_Ui_MemberOrderWindow_Ctor. Named virtual */
extern void* g_uiSmithGaugeVtable[10];               /* 0x00778B58 conf 0.55: Virtual method table of smith gauge widget of the smith menu (slot 8 Ui_SmithGauge_Init). The object's vptr is set by ma */
extern void* g_uiTalkWindowVtableC[10];              /* 0x00778BBC conf 0.70: Virtual method table of Ui_TalkWindow. The object's vptr is set by maybe_Ui_Object_Ctor_CF6C0. Named virtual slots: 1:ma */
extern void* g_uiTextPaneWindowVtable[10];           /* 0x00778C20 conf 0.50: Virtual method table of Ui_TextPaneWindow. The object's vptr is set by maybe_Ui_Object_Ctor_CF840. Named virtual slots:  */
extern void* g_uiTacticsPartySelectWindowVtable[10]; /* 0x00778C84 conf 0.65: Virtual method table of TacticsPartySelectWindow table shared with the tactics window base (slot 0 Ui_SakusenWindow_Dtor */
extern void* g_uiScrollBarVtableB[10];               /* 0x00778CE8 conf 0.82: Virtual method table of Ui_ScrollBar. The object's vptr is set by Ui_ScrollBar_InitFields. Named virtual slots: 1:maybe_ */
extern void* g_battleUiSkillPopupVtable;             /* 0x007792D0 conf 0.60: Virtual method table of battle skill-popup screen (slot 1 Battle_Ui_SkillPopup_Dtor, slot 7 maybe_Battle_Ui_UpdateSkillP */
extern void* g_uiTwoLineTextWindow2Vtable[10];       /* 0x007799C8 conf 0.70: Virtual method table of Ui_TwoLineTextWindow2. The object's vptr is set by Ui_SetupSakusenWindow. Named virtual slots: 1 */
extern void* maybe_g_uiMessageWindowFieldPaneTable2[6]; /* 0x00779A64 conf 0.40: Second six-word field-pane table stamped by Ui_MessageWindow_CtorFieldPanes; only the two pane callbacks at slots 2/3 ar */
extern void* g_uiArcListWindowVtableE[47];           /* 0x00779A7C conf 0.82: Virtual method table of Ui_ArcListWindow. The object's vptr is set by maybe_Ui_ScreenCtor_vt779A7C. Named virtual slots: */
extern void* maybe_g_rodata_00779c7c[10];            /* 0x00779C7C conf 0.30: Virtual method table of UI object table installed by maybe_Ui_Object_Ctor_D4F18; slot 1 is the generic maybe_Ui_Object_D */
extern void* g_uiPopupMultiActorVtable;              /* 0x00779CE0 conf 0.50: Virtual method table of multi-actor popup entry created by maybe_Ui_PopupEntry_SpawnMultiActor. The object's vptr is set */
extern void* g_uiPopupModelDebugTextVtable;          /* 0x00779CF8 conf 0.50: Virtual method table of model-debug-text popup entry created by maybe_Ui_PopupEntry_SpawnModelDebugText. The object's vp */
extern void* g_uiRowWindowVtable[10];                /* 0x00779DCC conf 0.70: Virtual method table of Ui_RowWindow. The object's vptr is set by maybe_Ui_EightSlotWindow_Dtor, maybe_Ui_RowWindow_Ctor */
extern void* g_uiRacingWindowVtable[10];             /* 0x0077A050 conf 0.70: Virtual method table of Ui_RacingWindow. The object's vptr is set by maybe_Ui_RacingWindow_Ctor. Named virtual slots: 1: */
extern void* g_uiRacingWindowVtableB[10];            /* 0x0077A0B4 conf 0.80: Virtual method table of Ui_RacingWindow. The object's vptr is set by maybe_Ui_UmaWindow_InitPanel. Named virtual slots:  */
extern void* g_uiUmaWindowVtableC[10];               /* 0x0077A104 conf 0.88: Virtual method table of Ui_UmaWindow. The object's vptr is set by maybe_Ui_UmaWindow_CtorSub11, maybe_Ui_UmaWindow_Dtor. */
extern void* g_uiPointTextVtable[10];                /* 0x0077A1A0 conf 0.58: Virtual method table of Ui_PointText. The object's vptr is set by maybe_Ui_SkillPanel_SubCtor. Named virtual slots: 1:Ui */
extern void* maybe_g_rodata_0077a31c[4];             /* 0x0077A31C conf 0.30: Four zero words used for the embedded member at +0x10 of the list built by maybe_Ui_List_Ctor_vt77D210; no functions are */
extern void* g_uiCursorSpriteWindowVtable[10];       /* 0x0077A32C conf 0.70: Virtual method table of Ui_CursorSpriteWindow. The object's vptr is set by maybe_Casino_CardWindow_Dtor, maybe_Ui_Cursor */
extern void* g_uiSmithMaterialWindowVtable[10];      /* 0x0077A3F4 conf 0.70: Virtual method table of Ui_SmithMaterialWindow. The object's vptr is set by Ui_SmithMenu_Ctor. Named virtual slots: 1:ma */
extern void* g_ui3DBackgroundVtableB[10];            /* 0x0077A458 conf 0.70: Virtual method table of Ui_3DBackground. The object's vptr is set by Ui_ListWidget_Ctor. Named virtual slots: 1:maybe_Ui */
extern void* g_textMessageWindowVtable;              /* 0x0077A51C conf 0.70: Virtual method table of Text_MessageWindow. The object's vptr is set by maybe_Ui_ScreenCtor_vt77A51C. Named virtual slot */
extern void* g_textMessageWindowVtableB;             /* 0x0077A630 conf 0.70: Virtual method table of Text_MessageWindow. The object's vptr is set by maybe_Ui_ScreenCtor_vt77A630. Named virtual slot */
extern void* g_modelActorVtable[10];                 /* 0x0077AE08 conf 0.82: Virtual method table of Model_Actor. The object's vptr is set by Model_Actor_DtorDelete, maybe_Ui_SceneObject_Ctor_77AE0 */
extern void* g_modelActorVtableB[10];                /* 0x0077AE38 conf 0.76: Virtual method table of Model_Actor. The object's vptr is set by maybe_Ui_SceneObject_Ctor_77AE38. Named virtual slots:  */
extern void* g_uiSelectCoreLoopVtable[10];           /* 0x0077AE68 conf 0.70: Virtual method table of Ui_SelectCoreLoop. The object's vptr is set by maybe_Ui_StaticInit_4E36E0. Named virtual slots:  */
extern void* g_uiItemListCoreVtable[10];             /* 0x0077AECC conf 0.82: Virtual method table of Ui_ItemListCore (base ItemList_Iterator). The object's vptr is set by Ui_ItemListCore_Ctor. Name */
extern void* g_uiTenRowTextWidgetVtable[10];         /* 0x0077AF48 conf 0.70: Virtual method table of Ui_TenRowTextWidget. The object's vptr is set by Ui_MessageWindow_CtorLayout2, Ui_MultiTextWindo */
extern void* maybe_g_ui3DEffectPairTable[6];         /* 0x0077B0C0 conf 0.45: Six-word UI3D effect-pair table: ApplyEffectPairState / ShowEffectEntry / HideEffectEntry callbacks for one effect pair. */
extern void* maybe_g_ui3DEffectPairTextTable;        /* 0x0077B0D8 conf 0.45: UI3D effect-pair text table: SetEffectPairText and HideEffectPairAux callbacks for one effect pair. Referenced by maybe_ */
extern void* maybe_g_ui3DPanelVtable[8];             /* 0x0077B118 conf 0.45: UI3D panel table with Ui3D_AttachDrawNodes / Ui3D_DetachDrawNodes and element-construction callbacks. Referenced by mayb */
extern void* g_ui3DSlotMaskTableVtable[8];           /* 0x0077B140 conf 0.70: Virtual method table of Ui3D_SlotMaskTable. The object's vptr is set by maybe_Ui3D_ConstructListElement. Named virtual s */
extern void* g_uiMessageWindow3DNodeVtable;          /* 0x0077B214 conf 0.65: Virtual method table of 3D scene-node of the message window built by maybe_Ui_MessageWindow_Construct (Gfx_Node slots pl */
extern void* g_uiMessageWindow3DNodeVtableB;         /* 0x0077B30C conf 0.65: Virtual method table of 3D scene-node of the message window built by maybe_Ui_MessageWindow_ConstructVariant. The object */
extern void* g_uiThreeLineTextWindow2Vtable[10];     /* 0x0077B4FC conf 0.70: Virtual method table of Ui_ThreeLineTextWindow2. The object's vptr is set by maybe_Ui_StaticInit_4E6EF8. Named virtual s */
extern void* g_uiFourRowTextWidgetVtable[10];        /* 0x0077B6AC conf 0.70: Virtual method table of Ui_FourRowTextWidget. The object's vptr is set by maybe_Ui_Widget_Init_77B6AC. Named virtual slo */
extern void* g_uiSelectListWindowVtableC[10];        /* 0x0077B710 conf 0.50: Virtual method table of Ui_SelectListWindow. The object's vptr is set by maybe_Ui_Object_Ctor_vt77B710. Named virtual sl */
extern void* maybe_g_uiScreenVtable[4];              /* 0x0077B8DC conf 0.40: Virtual method table of anonymous UI screen built by maybe_Ui_ScreenCtor_vt77B8DC. The object's vptr is set by maybe_Ui_ */
extern void* g_battleUiPartyPanelVtable;             /* 0x0077BA38 conf 0.70: Virtual method table of Battle_Ui_PartyPanel. The object's vptr is set by maybe_Ui_ScreenCtor_vt77BA38. Named virtual sl */
extern void* g_uiInLoopOutAnimVtable[10];            /* 0x0077BEF4 conf 0.82: Virtual method table of Ui_InLoopOutAnim (base Ui_AnimRef). The object's vptr is set by Ui_InLoopOutAnim_Dtor, maybe_Ui_ */
extern void* g_uiTxtL1WindowVtable[10];              /* 0x0077BF90 conf 0.60: Virtual method table of one-line text window (slot 1 maybe_Ui_TxtL1Window_Dtor, slot 8 Ui_TxtL1Window_Init). The object' */
extern void* g_uiTextNumberWidgetVtable[10];         /* 0x0077C02C conf 0.82: Virtual method table of Ui_TextNumberWidget (base Ui_WindowBase). The object's vptr is set by Ui_TextNumberWidget_Ctor.  */
extern void* g_uiSixLineTextWidgetVtable[10];        /* 0x0077C0C8 conf 0.82: Virtual method table of Ui_SixLineTextWidget. The object's vptr is set by Ui_SetupSakusenWindow. Named virtual slots: 1: */
extern void* g_uiSlotPlateNumberVtable[10];          /* 0x0077C164 conf 0.82: Virtual method table of Ui_SlotPlateNumber. The object's vptr is set by maybe_Ui_SlotMachine_CtorSubParts. Named virtual */
extern void* g_uiFloorMapJumpTriggerVtable[8];       /* 0x0077C298 conf 0.82: Virtual method table of Ui_FloorMapJumpTrigger. The object's vptr is set by maybe_Ui_FloorMapJumpTrigger_Ctor. Named vir */
extern void* maybe_g_uiPopupDescriptorVtableD;       /* 0x0077C3B8 conf 0.45: Virtual method table of one of the generic popup-entry tables used by Ui_PopupEntry_SpawnFromDescriptor (descriptor vari */
extern void* g_uiNumberPaneVtable[10];               /* 0x0077C508 conf 0.70: Virtual method table of Ui_NumberPane. The object's vptr is set by maybe_Ui_Widget_Init_77C508. Named virtual slots: 1:m */
extern void* g_textWindowVtable[10];                 /* 0x0077C56C conf 0.60: Virtual method table of Text_Window (shared with the smith menu; slot 1 Text_Window_DeletingDestructor, slot 8 Ui_CheckL */
extern void* g_battleUiMemberPanelVtable;            /* 0x0077C648 conf 0.70: Virtual method table of Battle_Ui_MemberPanel. The object's vptr is set by maybe_Ui_ScreenCtor_vt77C648. Named virtual s */
extern void* g_text3DVtable;                         /* 0x0077C75C conf 0.65: Virtual method table of 3D text window Text3D (slot 1 Text3D_DeletingDestructor). The object's vptr is set by Text3D_Del */
extern void* g_fieldObjectKind15ScreenVtable;        /* 0x0077C8B0 conf 0.60: Vtable of the 3D variant of field-object factory kind 15 (a 0xDE18-byte screen object). Slot 0 is Text_Scroll_DeletingDe */
extern void* g_fieldObjectKind09Vtable;              /* 0x0077C9F8 conf 0.60: Vtable of the 0xDE18-byte screen object created for field-object factory kind 9; installed by maybe_Field_Object_Kind09_ */
extern void* g_fieldObjectKind06Vtable;              /* 0x0077CB40 conf 0.55: Vtable installed by Ui_ScreenObject_Ctor to build the screen object allocated by Field_ObjectFactory_Kind06. */
extern void* g_uiFourRowTextWindowVtable2[10];       /* 0x0077CCF0 conf 0.85: Vtable of Ui_FourRowTextWindow (battle window with four 0x50-byte anim-ref groups at +0x1C). */
extern void* g_uiTextWindowVtable2[10];              /* 0x0077CD8C conf 0.85: Vtable of Ui_TextWindow, the shared text-window base used by the tactics/scene windows. */
extern void* g_uiArcListWindowVtable2[47];           /* 0x0077CE28 conf 0.85: Vtable of Ui_ArcListWindow, the arc/ring list window class. */
extern void* maybe_g_uiListWindowVtableAlt[10];      /* 0x0077CF88 conf 0.50: Alternative/final vtable of a nine-row list window built by maybe_Ui_ListWindow_Ctor_vt77CF88; the constructor switches  */
extern void* g_uiClockWindowVtable[10];              /* 0x0077D0D0 conf 0.85: Vtable of Ui_ClockWindow (clock/time widget with an InitPanes slot). */
extern void* maybe_g_uiMessageWindowSkinCmdTable[2]; /* 0x0077D154 conf 0.45: Two-entry command/skin table passed as the first field of a command record to maybe_Ui_MessageCmd_Apply from maybe_Ui_Me */
extern void* g_uiSceneWindowVtable[11];              /* 0x0077D164 conf 0.85: Vtable of Ui_SceneWindow (scene-sprite menu window with Open/Close/part-offset virtuals). */
extern void* g_uiTitlePagerWindowVtable;             /* 0x0077D210 conf 0.60: Vtable of the title pager/list window; restored by Ui_TitlePagerWindow_Dtor and installed by maybe_Ui_List_Ctor_vt77D210 */
extern void* maybe_g_uiCompositeWindowPartsVtable[10]; /* 0x0077D2E8 conf 0.45: Vtable of a composite window object whose parts are created by Ui_Object_CreatePartsFromTable; slot 0 is Ui_CompositeWin */
extern void* maybe_g_uiScriptScreenObjectVtableA;    /* 0x0077D5CC conf 0.45: Vtable for one of the script-visible 0xDE18-byte screen objects created by the script-class factories; the class itself  */
extern void* maybe_g_uiScriptScreenObjectVtableB;    /* 0x0077D6E0 conf 0.45: Vtable for a second script-visible screen object variant; handle words at +0x497/+0x498 are reset by its constructor. */
extern void* g_modelBlendAttachmentVtable[10];       /* 0x0077D874 conf 0.75: Vtable of the ModelBlendAttachment scene node used to blend two skeletal attachments. */
extern void* maybe_g_uiListWindowStatRowCmdTable[6]; /* 0x0077D9EC conf 0.45: Six-entry list-row command table used by the message-window icon/skin path; only slot 0 (maybe_Ui_ListWindow_FillStatRow */
extern void* g_uiSevenRowListVtable2[10];            /* 0x0077DA74 conf 0.85: Vtable of Ui_SevenRowList (seven-row list window with 0x50-byte rows). */
extern void* g_uiTwoAnimListWindowVtable[10];        /* 0x0077DAD8 conf 0.85: Vtable of Ui_TwoAnimListWindow, a window with two Ui_AnimRefList members. */
extern void* maybe_g_uiListWidgetPartsVtable[10];    /* 0x0077DB3C conf 0.45: Vtable of a list-widget part object handed to Ui_Object_CreatePartsFromTable by Ui_ListWidget_Ctor; slot 0 is Ui_3DBackg */
extern void* g_fieldObjectKind11Vtable;              /* 0x0077DD50 conf 0.60: Vtable of the field object built for factory kind 11 (a member/screen object derived from the field-party base). */
extern void* g_uiScreenObjectBaseVtable;             /* 0x0077DE98 conf 0.60: Base vtable of the generic UI screen object; Ui_ScreenObject_CtorBase installs it and all screen-object destructors rest */
extern void* g_fieldObjectKind08Vtable;              /* 0x0077E10C conf 0.60: Vtable of the field object built for factory kind 8; its constructor resets the 0x3784/0x3785 state block and the child  */
extern void* g_cameraFieldVtable[10];                /* 0x0077E254 conf 0.80: Vtable of Camera_Field, the field camera object (Delete/Update slots). */
extern void* maybe_g_uiScriptScreenObjectVtableC;    /* 0x0077E33C conf 0.45: Vtable of a mid-size script screen object with a 0x100-byte string buffer at +0x497. */
extern void* g_uiTextScreenVtable;                   /* 0x0077E564 conf 0.55: Vtable of a screen object that owns a text line cache (text-cache screen family, variant 1). */
extern void* g_uiTextScreenVtableB;                  /* 0x0077E6B8 conf 0.55: Second text-cache screen variant; same class family as g_uiTextScreenVtable but a different vtable. */
extern void* g_battle2DUnitPartyMemberVtable[4];     /* 0x0077E80C conf 0.70: Vtable of the 2D battle party-member unit (Battle2DUnit derived). */
extern void* maybe_g_ui3DPanelSubObjectVtable[8];    /* 0x0077EA5C conf 0.45: Vtable installed on a sub-object constructed by Ui3D_ConstructPanel; the panel's own type table is 0x0077B118, so this i */
extern void* maybe_g_uiPartyListCmdTable[3];         /* 0x0077EAAC conf 0.40: Three-entry list command table passed to maybe_Ui_MessageCmd_Apply; slot 0 builds member rows (Ui_PartyListWindow_BuildM */
extern void* maybe_g_uiScriptScreenObjectVtableD;    /* 0x0077ED80 conf 0.45: Vtable of another script-visible screen object variant created by the script-class factory. */
extern void* g_uiSkillPanelVtable2[10];              /* 0x0077EF88 conf 0.70: Vtable installed by Ui_SkillPanel_Ctor on the skill-panel root object. */
extern void* maybe_g_uiItemListBuildRowCmdTable[6];  /* 0x0077EFEC conf 0.45: Six-entry list command table whose slot 0 builds an item row (Ui_ItemListWindow_BuildItemRow); used by the message-windo */
extern void* maybe_g_uiItemListBuildRowsCmdTable[6]; /* 0x0077F00C conf 0.45: Six-entry list command table whose slot 0 builds rows from a record (Ui_ItemListWindow_BuildRowsFromRecord). */
extern void* g_battleSequenceVtable;                 /* 0x0077F02C conf 0.60: Vtable of the 0xDE18-byte battle-sequence object created by Battle_Sequence_Ctor. */
extern void* maybe_g_uiItemListBuildRowCmdTableB[6]; /* 0x0077F19C conf 0.45: Second instance of the six-entry item-row command table (same slot 0 as the first). */
extern void* maybe_g_uiScriptScreenObjectVtableE;    /* 0x0077F1DC conf 0.45: Vtable of a 0x1800-byte script/UI object variant. */
extern void* maybe_g_uiScriptScreenObjectVtableF;    /* 0x0077F34C conf 0.45: Vtable of a second 0x1800-byte script/UI object variant (stores a default sub-table at +0x1804). */
extern void* maybe_g_uiPartyListCmdTableB[3];        /* 0x0077F494 conf 0.40: Variant of the three-entry party-list command table; slot 0 builds member rows. */
extern void* maybe_g_uiListExtraRowsCmdTableA[6];    /* 0x0077F4A8 conf 0.40: Six-entry list command table whose slot 0 fills extra rows (maybe_Ui_ListWindow_FillExtraRows). */
extern void* maybe_g_uiListExtraRowsCmdTableB[6];    /* 0x0077F4C8 conf 0.40: Second instance of the six-entry extra-row command table. */
extern void* g_uiFadeAnimatorCurveAVtable;           /* 0x0077F6B4 conf 0.60: Vtable of fade/curve animator variant A (first user of the shared Ui_CurveAnimator base). */
extern void* g_uiFadeAnimatorCurveBVtable;           /* 0x0077F6FC conf 0.60: Vtable of fade/curve animator variant B. */
extern void* g_uiCurveAnimatorVtable;                /* 0x0077F70C conf 0.60: Vtable of the shared base class Ui_CurveAnimator (two-speed animator used by the fade windows). */
extern void* g_uiPagedListWidgetVtable;              /* 0x0077F71C conf 0.50: Vtable of the paged list widget embedded in the five-line / five-row / paged text windows. */
extern void* g_uiMessageDualBufferVtable[7];         /* 0x0077FCCC conf 0.70: Vtable of the message-window dual text buffer part (UpdateOpen/ChangeText/ClearText/InitPanes slots). */
extern void* g_uiMessageExtendedBufferVtable[7];     /* 0x0077FCFC conf 0.70: Vtable of the message-window extended buffer part (advance-talk-state/reset/init-scroll-panes slots). */
extern void* g_uiObjectBodyVtable[10];               /* 0x0077FD38 conf 0.85: Vtable of the generic Ui_Object base class. */
extern void* g_uiMessageWindowBaseVtable;            /* 0x0077FD9C conf 0.50: Base-class vtable installed by the message-window destructor before the derived members are torn down. */
extern void* g_uiFadeOverlayVtable[10];              /* 0x0077FE64 conf 0.60: Vtable of the full-screen fade overlay object built by Ui_CreateFadeWindow. */
extern void* g_uiOverlaySlotObjectVtable[40];        /* 0x0077FEDC conf 0.55: Vtable block of the overlay-slot object; the same block also contains the embedded sub-object vtable at +0x9C. */
extern void* g_uiOverlaySlotObjectVtableB[40];       /* 0x0077FF9C conf 0.55: Second overlay-slot vtable block (variant B), also containing the embedded sub-object vtable at +0x9C. */
extern void* g_uiWindowVtable[10];                   /* 0x0078005C conf 0.60: Vtable of the plain Ui_Window base (Ui_Window_CtorBaseB does not attach a layout child). */
extern void* g_uiTimeWindowVtable[10];               /* 0x007800C0 conf 0.85: Vtable of Ui_TimeWindow (clock/time window with pane binding and render-clock slots). */
extern void* maybe_g_uiTimerDisplayPartsTable;       /* 0x00780110 conf 0.40: Part/table pointer stored at +0xD8 of the timer display object; identifies the digit sub-widget set. */
extern void* g_uiMapWindowVtable[10];                /* 0x007801B4 conf 0.85: Vtable of Ui_MapWindow (world-map window with pane binding and touch-target slots). */
extern void* g_uiLazyHelperVtable;                   /* 0x00780278 conf 0.50: Vtable of the 0x14-byte helper object lazily created and cached by its owner (value at +0xC, back-pointer at +0x10). */
extern void* maybe_g_uiCharaStatusSubObjectVtableA[23]; /* 0x0078028C conf 0.45: One of the five sub-object vtables used by the character-status window state machine (table at 0x007AE55C, five kinds). */
extern void* g_uiSceneFlowVtable[23];                /* 0x007802F0 conf 0.85: Vtable of Ui_SceneFlow, the UI scene transition/flow controller. */
extern void* maybe_g_uiMessageArgTemplate;           /* 0x00780374 conf 0.40: Static template used to initialise message-argument/stack records (a null handler slot at +0x18). */
extern void* g_engineResourceNodeVtable;             /* 0x00780384 conf 0.60: Vtable of the tracked engine resource/actor base node (0x98-byte object with two handle arrays). */
extern void* maybe_g_uiItemMenuConfigTable;          /* 0x007803F0 conf 0.40: Static config/parts table referenced by the item-menu root object (stored at root+0x98). */
extern void* g_uiItemMenuSubObjectVtable;            /* 0x00780408 conf 0.50: Vtable of one of the item-menu root sub-objects created by Ui_ItemMenu_CreateRoot. */
extern void* maybe_g_uiShopWindowConfigA;            /* 0x00780448 conf 0.40: Config/parts table stored in the shop window (field +0x2C) and consumed when the price/skin sub-objects are built. */
extern void* maybe_g_uiShopWindowConfigB;            /* 0x00780460 conf 0.40: Second shop-window config/parts table (stored alongside g_uiShopWindowConfigA). */
extern void* maybe_g_uiComplexWindowConfigTable;     /* 0x0078046C conf 0.40: Config/parts table of the composite window built by Ui_ComplexWindow_Ctor. */
extern void* g_uiWindowCtorBaseVtable;               /* 0x00780484 conf 0.55: Base vtable installed by the generic window constructor before the derived vtable is written. */
extern void* maybe_g_uiSimpleWindowPartsTable;       /* 0x007804A0 conf 0.40: Parts table of the small simple-window object (stored at +0x34). */
extern void* maybe_g_uiPokerWindowPartsTable;        /* 0x007804D0 conf 0.40: Parts/table pointer stored at +0x18 of the poker mini-game window. */
extern void* maybe_g_uiPrizeWindowPartsTableA;       /* 0x007804E8 conf 0.40: Parts table shared by the casino and mini-medal prize windows (stored near +0x48). */
extern void* maybe_g_uiPrizeWindowPartsTableB;       /* 0x00780500 conf 0.40: Second parts table shared by the casino and mini-medal prize windows. */
extern void* maybe_g_uiShopWindowSubObjectTable;     /* 0x00780524 conf 0.40: Sub-object table stored at +0x410 of a shop-window child built by Ui_ShopWindow_CreateSubObjects. */
extern void* g_uiPrizeWindowSubObjectVtable;         /* 0x0078053C conf 0.50: Vtable of the shared prize-window sub-object installed by both the shop window and Ui_PrizeWindow_Init. */
extern void* maybe_g_uiItemMenuRootPartTable;        /* 0x00780578 conf 0.40: Sub-object table stored at +0x410 of the item-menu root widget. */
extern void* maybe_g_uiJackpotScreenPartsTable;      /* 0x00780590 conf 0.40: Parts table of the jackpot/casino screen (stored at +0xC). */
extern void* g_uiCasinoScreenBaseVtable;             /* 0x007805A8 conf 0.50: Base vtable shared by the poker, jackpot and stamp-book screens. */
extern void* maybe_g_uiBigWindowPartsTable;          /* 0x00780640 conf 0.40: Parts table stored at +0x60 of the big message window. */
extern void* maybe_g_uiStampBookPartsTableA;         /* 0x00780658 conf 0.40: Parts table stored at +0x124 of the stamp-book window. */
extern void* maybe_g_uiStampBookPartsTableB;         /* 0x00780664 conf 0.40: Second parts table of the stamp-book window (member at +0x24). */
extern void* maybe_g_uiSkillPanelPartsTable;         /* 0x0078067C conf 0.40: Parts table stored at +0x58 of the skill panel. */
extern void* maybe_g_uiWindowPartsTable;             /* 0x007806AC conf 0.40: Parts table stored at +0x48 of the generic composite window. */
extern void* maybe_g_uiPartySelectRowPartsTable;     /* 0x007806C4 conf 0.40: Callback/parts table stored at +0x410 of the party-select row widget. */
extern void* maybe_g_uiMessagePartTableFieldsA;      /* 0x0078079C conf 0.40: Field-initialisation table used by the reduced message-part-table constructor. */
extern void* maybe_g_uiMessagePartTableFieldsB;      /* 0x007807A8 conf 0.40: Second field-initialisation table used by the reduced message-part-table constructor. */
extern void* maybe_g_uiSmithMenuPartsTableA;         /* 0x007807B4 conf 0.40: Parts table stored at +0x58 of the smith/forge menu. */
extern void* maybe_g_uiSmithMenuPartsTableB;         /* 0x007807CC conf 0.40: Parts table stored at +0x50 of the smith/forge menu. */
extern void* maybe_g_uiNotifyListPartsTable;         /* 0x007807E0 conf 0.40: Parts/lookup table used by the intrusive notification-list constructor. */
extern void* maybe_g_uiSmithMenuPartsTableC;         /* 0x007807F4 conf 0.40: Parts table stored at +0x54 of the smith-menu sub-object. */
extern void* maybe_g_uiEquipmentRowPartsTable;       /* 0x00780AE4 conf 0.40: Callback/parts table stored at +0x410 of one equipment-window row. */
extern void* maybe_g_uiSmithMenuPartsTableD;         /* 0x00780B30 conf 0.40: Parts table used by the smith/forge menu when building its sub-object chain. */
extern void* g_uiCursorWindowVtable2[10];            /* 0x00780B54 conf 0.85: Vtable of Ui_CursorWindow, the cursor/highlight sub-window. */
extern u32 g_saveSlotDataTemplate[4];                /* 0x00780D90 conf 0.50: Four-word header template copied onto the stack by the save-slot loader before the slot record is read. */
extern void* g_uiIconAtlasVtable[3];                 /* 0x00780FC4 conf 0.85: Vtable of Ui_IconAtlas (icon-graphics descriptor with Init/Release/Dtor). */
extern void* g_uiAnimClipVtable[2];                  /* 0x00781250 conf 0.55: Vtable of the 0x34-byte UI animation clip object loaded from a .bflan resource. */
extern void* g_uiLayoutElementVtable[2];             /* 0x007812F0 conf 0.85: Vtable of the embedded layout element/tween record. */
extern void* g_uiLayoutPaneBaseVtable;               /* 0x00781348 conf 0.60: Base vtable of the nw::lyt pane wrapper, installed from the BFLYT pan1 resource initialiser. */
extern void* g_uiAnimTrackListVtable;                /* 0x007813A4 conf 0.50: Vtable of the animation track-list object built from a bflyt record table. */
extern void* g_uiLayoutPaneVtable;                   /* 0x007813B4 conf 0.70: Vtable of the UI layout pane object created by Ui_LayoutPane_Ctor. */
extern void* g_uiLayoutTextDefaultStateVtable;       /* 0x00781410 conf 0.55: Vtable of the global default layout-text rendering state registered at UI-system startup. */
extern void* g_uiLayoutPlayerVtable;                 /* 0x0078144C conf 0.60: Vtable of the nw::lyt Layout player instance loaded from a .bflyt resource. */
extern void* g_uiLayoutTextBoxVtable;                /* 0x00781498 conf 0.70: Vtable of the BFLYT 'txt1' (TextBox) layout pane. */
extern void* g_uiLayoutPictureVtable;                /* 0x007814F4 conf 0.70: Vtable of the BFLYT 'pic1' (Picture) layout pane. */
extern void* g_uiLayoutWindowPaneVtable;             /* 0x00781554 conf 0.70: Vtable of the BFLYT 'wnd1' (Window) layout pane. */
extern void* g_uiLayoutPartsPaneVtable;              /* 0x00781650 conf 0.70: Vtable of the BFLYT 'prt1' (Parts) layout pane. */
extern void* g_uiLayoutSystemGlobalTable;            /* 0x007816AC conf 0.50: Global layout-system descriptor block (pane-type mappings and font coordinate defaults) initialised once at startup. */
extern void* g_uiLayoutPaneDescriptorArray;          /* 0x007816C0 conf 0.50: Vtable/header of the global array of layout pane descriptors with default bounds and transform flags. */
extern void* g_soundStreamBufferWorkVtable[9];       /* 0x007816F8 conf 0.70: Vtable of Sound_StreamBuffer; the object's second vtable follows at +0x24. */
extern void* g_soundVoiceVtable[6];                  /* 0x007817C4 conf 0.65: Vtable of the sound voice component (UpdateVolumeAndPan / OnEvent slots). */
extern void* g_soundSequenceWorkVtable[9];           /* 0x00781AE4 conf 0.60: Vtable of the sound sequence work block; the block continues with a second table at +0x20. */
extern void* g_cameraShakeSecondaryVtable;           /* 0x00782060 conf 0.60: Secondary base vtable installed at +0x3F8 of the camera-shake object (next to the primary 0x774FDC). */
extern u32 maybe_g_wideStringEmptyRep[4];            /* 0x007820E0 conf 0.40: Zeroed wide-string header used as the empty/default value for the wide-string helper (length 0, capacity 0). */
extern void* g_gfxMaterialBindingVtable[2];          /* 0x00782198 conf 0.60: Vtable of the Gfx material-binding descriptor (Dtor / deleting-Dtor slots). */
extern void* g_gfxTextureBindingVtable[2];           /* 0x007821A8 conf 0.60: Vtable of the Gfx texture-binding descriptor (Dtor / deleting-Dtor slots). */
extern void* maybe_g_gfxResourceBindingTemplate;     /* 0x00782254 conf 0.40: Static descriptor template placed next to the material/texture binding vtables and used as a stack binding record. */
extern void* maybe_g_uiTextObjectBaseVtable;         /* 0x00782294 conf 0.45: Base vtable restored by the destructor of the large UI text object before its lists and heap blocks are freed. */
extern void* g_osSequenceTaskBaseVtable[9];          /* 0x007824E0 conf 0.70: Vtable of the OS sequence/task object (three intrusive list heads, state fields, name 'SequenceTask'). */
extern void* maybe_g_modelLoadVariantTable;          /* 0x00782554 conf 0.40: Resource/anim lookup table used when a model variant is loaded by name. */
extern void* maybe_g_uiProfileTitleRowTable;         /* 0x00782584 conf 0.40: Format/table seeded into the stack record used to compose the profile card's title rows. */
extern void* g_messageArgTemplate;                   /* 0x007825A8 conf 0.50: Template record used to initialise a message-argument slot before a dialogue/name string is assigned. */
extern void* maybe_g_uiCharacterQuestPanelTable;     /* 0x007825D8 conf 0.40: Format/table seeded into the stack record used to fill the character quest panel. */
extern void* maybe_g_battleUiWindowDescriptor;       /* 0x00782608 conf 0.50: Window-descriptor template used when the battle UI opens row/item/name windows. */
extern void* maybe_g_uiListWindowRowTable;           /* 0x00782618 conf 0.40: Row/record template used when a list window fills its rows from a data-manager record. */
extern void* maybe_g_uiTextTableRecord;              /* 0x00782628 conf 0.40: Record template used by the equipment window and the text-table record lookup. */
extern void* g_uiStpassVipMessageVtable;             /* 0x00782638 conf 0.50: Vtable installed by the StreetPass 'call VIP' message factory and by the dive-start window. */
extern void* maybe_g_fsResourceSetTemplate;          /* 0x00782770 conf 0.40: Static template used when a resource-set object is filled from a data record. */
extern void* maybe_g_uiShopItemTextTemplate;         /* 0x007827A0 conf 0.40: Template used when the shop builds the selected-item info line. */
extern void* maybe_g_uiDirectionIndicatorTable;      /* 0x007827C0 conf 0.40: Static table for the four-way direction indicator (arrow sprite submission). */
extern void* maybe_g_uiCharaStatusPanelTemplate;     /* 0x007827E0 conf 0.40: Template used when the character-status panel is filled for one party member. */
extern void* maybe_g_uiMessageWindowCommandTable;    /* 0x007827F0 conf 0.45: Command/record table used by Ui_MessageWindow_ApplyCommand when dispatching a queued message-window command. */
extern void* maybe_g_uiMessageWindowTextTemplate;    /* 0x00782820 conf 0.40: Text template copied into the message window's subject/speaker buffer at +0x4A4. */
extern void* maybe_g_uiPartChildDescriptor;          /* 0x00782830 conf 0.40: Descriptor template used when a ui2d child part is created (200x120 default block). */
extern void* maybe_g_uiSystemLayoutTemplate;         /* 0x00782898 conf 0.40: Template used by Ui_System_Ctor to seed the shared 0x37C-byte layout block. */
extern u8 g_battleEncounterTransitionTemplate[0xDC]; /* 0x007828EC conf 0.60: Static template for the 0x1348-byte battle-encounter transition object; 0xDC bytes are copied over a zeroed block on the */
extern void* maybe_g_movieFrameVtable;               /* 0x00782900 conf 0.45: All-zero vtable installed as word 0 of the 0x28-byte movie/frame object created by Movie_GetFrame; slots are filled or n */
extern void* g_animSequenceVtable;                   /* 0x00782914 conf 0.55: Vtable of the 0x1EB0-byte animation/sound sequence object created during engine bring-up (Anim_Sequence_CtorBase). */
extern void* g_uiLayoutBlockVtable;                  /* 0x00782928 conf 0.50: Vtable of the shared 0x37C-byte UI layout block lazily created by Ui_System_Ctor. */
extern void* g_uiStateRequestVtable;                 /* 0x0078293C conf 0.50: Vtable of the 8-byte one-shot UI request object offered to the UI subsystems by maybe_Ui_State_Apply. */
extern void* g_uiMessageWindowBaseVtable2;           /* 0x00782950 conf 0.55: Base vtable installed on the message-window object built by Ui_CreateMessageWindow. */
extern void* g_uiCommandPaneVtable;                  /* 0x00782964 conf 0.55: Vtable of the command-pane object pushed by the tactics window; the object continues with a second table at +0x18. */
extern void* g_gameDataManagerVtable;                /* 0x00782990 conf 0.55: Vtable of the process-wide game-data manager object lazily created by Game_GetDataManager. */
extern void* maybe_g_partyStatusSnapshotTable;       /* 0x007829B8 conf 0.40: Working table used when the per-party-member status snapshot array is rebuilt. */
extern void* g_textLayoutVtable;                     /* 0x007829CC conf 0.55: Vtable of the lazily created text-layout object whose entries the layout statistics walk. */
extern void* maybe_g_packManagerVtable;              /* 0x007829E0 conf 0.45: Vtable of the pack manager singleton created during engine bring-up. */
extern void* maybe_g_fieldSceneQueryTable;           /* 0x00782A08 conf 0.40: Shared query/record table used by the dialog, map-section and NPC-target-cursor helpers. */
extern void* maybe_g_uiScreenShakeTable;             /* 0x00782A98 conf 0.40: Screen-shake parameter table used by the panel-message update and engine bring-up. */
extern void* maybe_g_uiTextWidgetRegistryVtable;     /* 0x00782AAC conf 0.45: Vtable of the shared global registry node that text widgets register themselves in. */
extern void* maybe_g_uiListWindow1F8SubVtable1;      /* 0x00782BC8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ListWindow_Ctor1F8 / Ui_ListWindow1F8_Dtor; t */
extern void* maybe_g_uiSenrekiRowVtable;             /* 0x00782BF0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SenrekiWindow_CtorRow; the sub-object class i */
extern void* maybe_g_uiPanelMessageWindowSubVtableA; /* 0x00782C18 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindow_Ctor; the sub-object class */
extern void* maybe_g_uiPanelMessageWindowCtorSubVtableA; /* 0x00782C2C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindowCtor; the sub-object class  */
extern void* maybe_g_uiSkillPanelSubVtableA;         /* 0x00782C40 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanel_Ctor; the sub-object class itself  */
extern void* maybe_g_uiMessagePartTableSubVtableA;   /* 0x00782C54 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MessagePartTable_Create; the sub-object class */
extern void* maybe_g_uiPanelMessageWindowSubVtableB; /* 0x00782C68 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindow_Ctor / CtorEx / Dtor; the  */
extern void* maybe_g_uiPanelMessageWindowCtorSubVtableB; /* 0x00782C7C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindowCtor; the sub-object class  */
extern void* maybe_g_uiSkillPanelSubVtableB;         /* 0x00782C90 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanel_Ctor; the sub-object class itself  */
extern void* maybe_g_ui3DPanelMessageWindowSubVtableA; /* 0x00782CA4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindow_LoadPanels; the sub-object */
extern void* maybe_g_uiSkillPanelWindowSubVtableA;   /* 0x00782CB8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanelWindow_Ctor; the sub-object class i */
extern void* maybe_g_uiPanelMessageWindowSubVtableC; /* 0x00782CCC conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindow_Ctor; the sub-object class */
extern void* maybe_g_uiPanelMessageWindowCtorSubVtableC; /* 0x00782CE0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindowCtor; the sub-object class  */
extern void* maybe_g_uiSkillPanelSubVtableC;         /* 0x00782CF4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanel_Ctor; the sub-object class itself  */
extern void* maybe_g_ui3DPanelMessageWindowSubVtableB; /* 0x00782D08 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindow_LoadPanels; the sub-object */
extern void* maybe_g_uiSkillPanelWindowSubVtableB;   /* 0x00782D1C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanelWindow_Ctor; the sub-object class i */
extern void* maybe_g_ui3DPanelMessageWindowSubVtableC; /* 0x00782D30 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindow_LoadPanels / message-part- */
extern void* maybe_g_uiMonsterBookSubVtableA;        /* 0x00782D44 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MonsterBookWindow_Ctor / Release; the sub-obj */
extern void* maybe_g_uiSenrekiWindowSubVtable;       /* 0x00782D58 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SenrekiWindow_Ctor; the sub-object class itse */
extern void* maybe_g_uiPanelMessageWindowCtorSubVtableD; /* 0x00782D6C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindowCtor; the sub-object class  */
extern void* maybe_g_uiSkillPanelSubVtableD;         /* 0x00782D80 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanel_Ctor; the sub-object class itself  */
extern void* maybe_g_uiChoiceSelectWindowRowVtable;  /* 0x00782DA8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ChoiceSelectWindow_Dtor; the sub-object class */
extern void* maybe_g_uiScrollListWindowSubVtableA;   /* 0x00782DD0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Ctor / Dtor; the sub-object  */
extern void* maybe_g_uiMessagePartTableSubVtableB;   /* 0x00782DE4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MessagePartTable_Create; the sub-object class */
extern void* maybe_g_uiScrollListWindowSubVtableB;   /* 0x00782E0C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Dtor; the sub-object class i */
extern void* maybe_g_uiDiveWidgetVtableA;            /* 0x00782E20 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by maybe_Ui_Widget_CreateInstance; the sub-object c */
extern void* maybe_g_uiDiveManagerSubVtableA;        /* 0x00782E34 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_DiveManager_Ctor / Dtor; the sub-object class */
extern void* maybe_g_uiObjectWithListVtable;         /* 0x00782E5C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_Object_DtorWithList; the sub-object class its */
extern void* maybe_g_uiScrollListWindowSubVtableC;   /* 0x00782E70 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Dtor; the sub-object class i */
extern void* maybe_g_uiEquipTextWindowSubVtableA;    /* 0x00782E84 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_EquipTextWindow_Ctor / Dtor; the sub-object c */
extern void* maybe_g_uiUmaWindowSubVtableA;          /* 0x00782EAC conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_UmaWindow_Dtor_2; the sub-object class itself */
extern void* maybe_g_uiUmaWindowPanelTable;          /* 0x00782EC0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_UmaWindow_InitPanel; the sub-object class its */
extern void* g_uiListWithArrayVtable;                /* 0x00782EE8 conf 0.55: Vtable of the list widget whose sentinel sits at +0x714 and which owns four 0x1C4-byte rows; used by its base-form destr */
extern void* maybe_g_uiDiveWidgetVtableB;            /* 0x00782EFC conf 0.45: Secondary/sub-object vtable stored into a member of the object built by maybe_Ui_Widget_CreateInstance; the sub-object c */
extern void* maybe_g_uiPartySelectWindowRowVtable;   /* 0x00782F10 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PartySelectWindow_DeletingDtor; the sub-objec */
extern void* maybe_g_uiListWindow1F8SubVtable2;      /* 0x00782F24 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ListWindow_Ctor1F8 / Ui_ListWindow1F8_Dtor; t */
extern void* maybe_g_uiSkillPanelSubVtableE;         /* 0x00782F38 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanel_Ctor; the sub-object class itself  */
extern void* maybe_g_uiMessageSelectWindowSubVtableA; /* 0x00782F60 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MessageSelectWindow_Ctor / Dtor; the sub-obje */
extern void* maybe_g_uiLayoutRefListVtable;          /* 0x00782F88 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_LayoutRef_InitList; the sub-object class itse */
extern void* maybe_g_uiAnimRefListVtable;            /* 0x00782FB0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_AnimRefList_Init; the sub-object class itself */
extern void* maybe_g_uiAnimatableElementVtable;      /* 0x00782FC4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_AnimatableElement_Ctor; the sub-object class  */
extern void* maybe_g_uiMessageSelectWindowSubVtableB; /* 0x00782FEC conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MessageSelectWindow_Ctor / Dtor; the sub-obje */
extern void* maybe_g_uiListWidgetScreenSubVtableA;   /* 0x00783000 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by maybe_Ui_ListWidget_Screen_Ctor / Dtor; the sub- */
extern void* maybe_g_uiMessageWindowSubVtableA;      /* 0x00783014 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_CreateMessageWindow; the sub-object class its */
extern void* maybe_g_uiTsuyosaWindowSubVtable;       /* 0x00783028 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_TsuyosaWindow_CreateInstance; the sub-object  */
extern void* maybe_g_uiMainMenuTextSubVtableA;       /* 0x0078303C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MainMenuText_Ctor / ReleaseResources; the sub */
extern void* maybe_g_uiMainMenuTextSubVtableB;       /* 0x00783064 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MainMenuText_SetWindowState; the sub-object c */
extern void* maybe_g_uiPanelMessageWindowSubVtableD; /* 0x00783078 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindow_Ctor / CtorEx / Dtor; the  */
extern void* maybe_g_uiPanelMessageWindowCtorSubVtableE; /* 0x0078308C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessageWindowCtor; the sub-object class  */
extern void* maybe_g_uiSkillPanelSubVtableF;         /* 0x007830A0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanel_Ctor; the sub-object class itself  */
extern void* maybe_g_uiSkillPanelWindowSubVtableC;   /* 0x007830B4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_SkillPanelWindow_Ctor; the sub-object class i */
extern void* maybe_g_uiMessagePartTableSubVtableC;   /* 0x007830C8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MessagePartTable_CreateSmall; the sub-object  */
extern void* maybe_g_uiDiveManagerSubVtableB;        /* 0x007830F0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_DiveManager_Ctor / Dtor / Ui_ScrollListWindow */
extern void* maybe_g_uiListWindow1F8SubVtable3;      /* 0x00783104 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ListWindow_Ctor1F8 / Ui_ListWindow1F8_Dtor; t */
extern void* maybe_g_uiTextListWidgetSubVtableA;     /* 0x0078312C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_TextListWidget_Ctor; the sub-object class its */
extern void* maybe_g_uiWindowReleaseVtable;          /* 0x00783140 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_Window_ReleaseResources; the sub-object class */
extern void* maybe_g_uiPanelMessageWindowSubVtableE; /* 0x00783154 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessage_Dtor; the sub-object class itsel */
extern void* maybe_g_uiPanelMessageWindowSubVtableF; /* 0x00783168 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessage_Dtor; the sub-object class itsel */
extern void* maybe_g_uiPanelMessageWindowSubVtableG; /* 0x0078317C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessage_Dtor; the sub-object class itsel */
extern void* maybe_g_uiMonsterBookSubVtableB;        /* 0x00783190 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MonsterBookWindow_Ctor / Release; the sub-obj */
extern void* maybe_g_uiTitleScreenSubVtableA;        /* 0x007831A4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_TitleScreen_Ctor / Dtor; the sub-object class */
extern void* maybe_g_uiPanelMessageWindowSubVtableH; /* 0x007831B8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessage_Dtor; the sub-object class itsel */
extern void* maybe_g_uiSequenceSubVtableA;           /* 0x007831CC conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_Sequence_Dtor; the sub-object class itself is */
extern void* maybe_g_uiScrollListWindowSubVtableD;   /* 0x007831E0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Ctor / Dtor; the sub-object  */
extern void* maybe_g_uiScrollListWindowSubVtableE;   /* 0x007831F4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Ctor / Dtor; the sub-object  */
extern void* maybe_g_uiPanelMessageWindowSubVtableI; /* 0x00783208 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessage_Dtor; the sub-object class itsel */
extern void* maybe_g_uiScrollListWindowSubVtableF;   /* 0x0078321C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Ctor / Dtor; the sub-object  */
extern void* maybe_g_uiDiveManagerSubVtableC;        /* 0x00783230 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_DiveManager_Ctor / Dtor; the sub-object class */
extern void* maybe_g_uiSequenceSubVtableB;           /* 0x00783244 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_Sequence_Dtor / message-arg formatter; the su */
extern void* maybe_g_uiScrollListWindowSubVtableG;   /* 0x00783258 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Dtor; the sub-object class i */
extern void* maybe_g_uiDiveManagerSubVtableD;        /* 0x0078326C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_DiveManager_Ctor / Dtor; the sub-object class */
extern void* maybe_g_uiTitleScreenSubVtableB;        /* 0x00783280 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_TitleScreen_Ctor / Dtor; the sub-object class */
extern void* maybe_g_uiSequenceSubVtableC;           /* 0x00783294 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_Sequence_Dtor / message-arg formatter; the su */
extern void* maybe_g_uiScrollListWindowSubVtableH;   /* 0x007832A8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ScrollListWindow_Ctor / Dtor; the sub-object  */
extern void* maybe_g_uiEquipTextWindowSubVtableB;    /* 0x007832BC conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_EquipTextWindow_Ctor / Dtor; the sub-object c */
extern void* maybe_g_uiUmaWindowSubVtableB;          /* 0x007832D0 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_UmaWindow_Ctor / Dtor; the sub-object class i */
extern void* maybe_g_uiUmaWindowSubVtableC;          /* 0x007832E4 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_UmaWindow_Ctor / Dtor; the sub-object class i */
extern void* maybe_g_uiSequenceSubVtableD;           /* 0x007832F8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_Sequence_Dtor; the sub-object class itself is */
extern void* maybe_g_uiListWidgetScreenSubVtableB;   /* 0x0078330C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by maybe_Ui_ListWidget_Screen_Ctor / Dtor; the sub- */
extern void* maybe_g_uiDiveManagerSubVtableE;        /* 0x00783334 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_DiveManager_Ctor / Dtor; the sub-object class */
extern void* maybe_g_uiSequenceSubVtableE;           /* 0x00783348 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_Sequence_Dtor / message-arg formatter; the su */
extern void* maybe_g_uiListWindow1F8SubVtable4;      /* 0x0078335C conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_ListWindow_Ctor1F8 / Ui_ListWindow1F8_Dtor; t */
extern void* maybe_g_uiPanelMessageWindowSubVtableJ; /* 0x00783370 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessage_Dtor; the sub-object class itsel */
extern void* maybe_g_uiMessageSelectWindowSubVtableC; /* 0x00783398 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MessageSelectWindow_Ctor / Dtor; the sub-obje */
extern void* maybe_g_uiMessageSelectWindowSubVtableD; /* 0x007833E8 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_MessageSelectWindow_Ctor / Dtor; the sub-obje */
extern void* maybe_g_uiListWidgetScreenSubVtableC;   /* 0x007833FC conf 0.45: Secondary/sub-object vtable stored into a member of the object built by maybe_Ui_ListWidget_Screen_Ctor / Dtor; the sub- */
extern void* maybe_g_uiMessageWindowSubVtableB;      /* 0x00783410 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_CreateMessageWindow / Ui_MainMenuText_Ctor; t */
extern void* maybe_g_uiPanelMessageWindowSubVtableK; /* 0x00783424 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_PanelMessage_Dtor; the sub-object class itsel */
extern void* maybe_g_uiTextListWidgetSubVtableB;     /* 0x00783438 conf 0.45: Secondary/sub-object vtable stored into a member of the object built by Ui_TextListWidget_Ctor; the sub-object class its */
extern void* g_uiObjectList30Vtable;                 /* 0x00783D04 conf 0.60: Vtable of the Ui_ObjectList variant with a 0x30-byte header and a 3+2 slot array. */
extern void* g_uiObjectList10Vtable;                 /* 0x00783D14 conf 0.60: Vtable of the ten-slot Ui_ObjectList variant (10 x 0xC0 entries at +0x22). */
extern void* g_uiObjectList3Vtable;                  /* 0x00783D24 conf 0.60: Vtable of the three-slot Ui list variant (three 0xC0-byte entries at +6). */
extern void* g_uiEquipBestItemScoreFuncs[6];         /* 0x0078430C conf 0.60: Six-entry dispatch table of best-item scoring functions indexed by equipment mode; called as a function pointer array. */
extern void* g_uiListRowDrawDispatchFuncs[3];        /* 0x00784318 conf 0.55: Three-entry dispatch table used by the list-row draw paths (a three-element subset of the six-entry score table). */
extern u32 maybe_g_uiTextColorTagQuadFlags[4];       /* 0x00784324 conf 0.45: First of two parallel four-word tables OR-ed together to build the vertex colour/attribute word for a colour-tagged glyp */
extern u32 maybe_g_uiTextColorTagQuadCodes[4];       /* 0x0078433C conf 0.45: Second of two parallel four-word tables OR-ed into the colour-tagged glyph-quad vertex attribute. */
extern u32 maybe_g_uiTextRubyQuadFlags[6];           /* 0x0078434C conf 0.45: Six-word attribute base table OR-ed into the ruby (furigana) quad vertex words. */
extern u32 maybe_g_uiTextRubyQuadCodes[8];           /* 0x00784364 conf 0.45: Eight-word per-corner code table combined with the ruby quad attribute base. */
extern u32 maybe_g_uiTextVerticalQuadFlags[6];       /* 0x00784384 conf 0.45: Six-word vertex-attribute base table for vertical-text quads. */
extern u32 maybe_g_uiTextVerticalQuadCodes[2];       /* 0x0078439C conf 0.45: Two-word per-corner code table combined with the vertical-text attribute base. */
extern u32 maybe_g_uiTextBlockQuadFlags[6];          /* 0x007843A4 conf 0.45: Six-word vertex-attribute base table for block/multi-line text quads. */
extern u32 maybe_g_uiTextBlockQuadCodes[2];          /* 0x007843BC conf 0.45: Two-word per-corner code table combined with the block/multi-line attribute base. */
extern char g_uiGaugePaneNameC1[4];                  /* 0x00786574 conf 0.55: Pane-name string "_c1" passed to Ui_Control_BindChildPaneByName for the fifth gauge ring of Ui_GaugeWindow_InitPanes; it */
extern u8 maybe_g_iconCacheContentInfo[0x30];        /* 0x0079D000 conf 0.40: Output block filled by Svc_FetchContentInfo when the icon-cache loader checks whether external content is present; the e */
extern u8 maybe_g_iconCacheVersionInfo[0x30];        /* 0x0079F000 conf 0.40: Cached content/version record: a halfword at +0x2C is compared with the low half of the kernel content version to decide */
extern u32 g_uiColorPaletteDefault[12];              /* 0x007A2D20 conf 0.60: Standard 12-entry UI colour palette (black/grey/red/yellow/green/cyan/pale-cyan/orange/near-black/blue/dark-red/bright-g */
extern u32 maybe_g_senrekiEvaluatorTableGuard;       /* 0x007A2FB0 conf 0.45: One-shot guard for the lazily built achievement/senreki evaluator table; func_0010009C is called on it before the table  */
extern u8 g_uiWindowBackdropEnabled;                 /* 0x007A301C conf 0.50: Global enable flag for the window-backdrop sprite pass; when zero, maybe_Ui_Window_UpdateBackdrop skips drawing the back */
extern u32 g_dataEntry8TableGuard;                   /* 0x007A350C conf 0.55: One-shot guard (bit 0) for the lazily constructed fixed 8-byte-entry data table at 0x007C33E8. */
extern u32 maybe_g_uiStaticObjectA;                  /* 0x007A359C conf 0.40: State block of one module-static UI object built at startup and spliced into the module list head 0x007BE378. */
extern u32 g_uiColorPaletteSecondary[12];            /* 0x007A3744 conf 0.60: Second standard 12-entry UI colour palette block (same colours as g_uiColorPaletteDefault). */
extern u32 g_uiModelViewIdleVariantTable[3];         /* 0x007A377C conf 0.50: Three-entry table of idle-animation variants cycled by the UI model view (index at self+0x220 modulo 3). */
extern u32 maybe_g_uiStaticObjectB;                  /* 0x007A3818 conf 0.40: State block of a module-static UI object built at startup (register function 0x00695480). */
extern u32 maybe_g_uiStaticObjectC;                  /* 0x007A3860 conf 0.40: State block of a module-static UI object built at startup (register function 0x0069A5DC). */
extern u32 maybe_g_uiStaticObjectD;                  /* 0x007A38C4 conf 0.40: State block of a module-static UI object built at startup (register function 0x0069A810). */
extern u32 maybe_g_uiStaticObjectE;                  /* 0x007A3900 conf 0.40: State block of a module-static UI object built at startup (register function 0x0069F04C). */
extern u32 maybe_g_uiStaticObjectF;                  /* 0x007A3918 conf 0.40: State block of a module-static UI object built at startup; its first word is initialised to -1. */
extern u32 maybe_g_uiStaticObjectG;                  /* 0x007A3978 conf 0.40: State block of a module-static UI object built at startup; its first word is initialised to -1. */
extern u32 maybe_g_uiStaticObjectH;                  /* 0x007A3B28 conf 0.40: State block of a module-static UI object built at startup; its first word is initialised to -1. */
extern u8 maybe_g_uiLabelTextResolvedFlag;           /* 0x007A3FA4 conf 0.45: Flag byte tested before a field-object label's text lines are rebuilt; likely marks that the label font/character has be */
extern u32 maybe_g_uiLabelTextResolveGuard;          /* 0x007A3FA8 conf 0.45: One-shot guard for the lazily resolved label text/font table. */
extern u32 maybe_g_uiStaticObjectI;                  /* 0x007A3FB8 conf 0.40: State block of a module-static UI object built at startup; its first byte is initialised to 0xFF. */
extern u32 maybe_g_uiStaticObjectJ;                  /* 0x007A3FEC conf 0.40: State block of a module-static UI object built at startup (register function 0x006A1B78). */
extern u32 maybe_g_uiStaticObjectK;                  /* 0x007A400C conf 0.40: State block of a module-static UI object built at startup; its first word is initialised to -1. */
extern char* g_uiSmithPageSuffixes[3];               /* 0x007A4020 conf 0.75: Three page-suffix strings ("_start", "_loop", "_end") used to build the smith-menu page label; indexed by the high byte  */
extern u8 g_battleAiHealModeOverride;                /* 0x007A4114 conf 0.60: Debug/AI override for emergency healing: 1 forces the heal threshold to 100 (always heal), 2 forces it to 0 (never heal) */
extern u8 g_battleAiActionOverride;                  /* 0x007A4118 conf 0.50: Debug/AI override for the chosen action: when not 0xFF the value replaces the AI-selected action index; 0xFF keeps the n */
extern void* g_fieldObjectFactoryKindTable;          /* 0x007A4268 conf 0.70: Kind-to-constructor dispatch table of the field-object factory; entry 0 is Field_ObjectFactory_Kind00. structs.json reco */
extern void* g_fieldObjectFactoryMonsterKindTable;   /* 0x007A4338 conf 0.55: Kind-to-constructor dispatch table for the monster/field-game-object part of the field-object factory (all nearby entrie */
extern u8 maybe_g_uiTargetTransformOverride[8];      /* 0x007A6088 conf 0.40: Optional override for the UI target-transform block: a flag byte at +0 and a 32-bit value at +4 are consulted when the b */
extern u32 g_uiModelViewSourceParams[17];            /* 0x007A6140 conf 0.60: Seventeen-word transform/parameter block copied from the selected character record (fields +0x30..+0x70) when the model- */
extern u32 g_uiModelViewSourceParam1;                /* 0x007A6144 conf 0.50: Second word of g_uiModelViewSourceParams, used on its own as the default colour/alpha written into three model-view fiel */
extern u32 maybe_g_uiModelViewDefaultParam;          /* 0x007A6180 conf 0.45: Default parameter copied into a model-view field (+0x11C) when a character model is set up. */
extern u32 maybe_g_cameraViewParams;                 /* 0x007A6200 conf 0.40: Start of the global camera view parameter block rebuilt by Camera_UpdateViewAndProjection (position/target/up and projec */
extern u8 g_uiModelViewRebuildDisabled;              /* 0x007A6203 conf 0.50: Global disable flag for the model-view character rebuild: when non-zero, Ui_ModelView_SetSelectedCharacter keeps the cur */
extern u8 g_uiChildListCleanupEnabled;               /* 0x007A65A8 conf 0.50: Teardown enable flag: when non-zero, the UI window child-list detach helpers drop the list at +0x3C. */
extern u32 maybe_g_fieldGimmickDefaultTransform;     /* 0x007A6D04 conf 0.40: Default transform/state block used when a field gimmick is reset to its initial values (large initialiser truncated by d */
extern u32 g_uiColorPaletteTertiary[12];             /* 0x007A6E28 conf 0.60: Third standard 12-entry UI colour palette block (same colours as the other two). */
extern f32 maybe_g_uiMessagePlacementDefault;        /* 0x007A6F98 conf 0.40: Default scalar copied into the placement matrix of the message window when its 3D transform is rebuilt. */
extern u8 maybe_g_uiSceneLayerFlags;                 /* 0x007A7030 conf 0.45: Packed UI scene display-flag word; its first byte gates the per-layer visibility application (initial word in the image  */
extern u8 maybe_g_partyListIdFilter;                 /* 0x007A7154 conf 0.45: Party-member list id filter: only members whose id equals this byte are appended to the display list. */
extern u32 maybe_g_uiDebugStringRecord[6];           /* 0x007A71A4 conf 0.35: Lazily initialised UI string record for string id 0xF4: a self-relative pointer is patched into word 0 and the UTF-16 te */
extern u8 g_uiInputUpdateEnabled;                    /* 0x007A7228 conf 0.50: Global enable flag for the per-frame UI input update; when zero Ui_UpdateInput leaves the focused window unchanged. */
extern u8 maybe_g_uiOverlaySlotVisibilityFlag;       /* 0x007A723E conf 0.40: Flag consulted by the overlay slot-visibility pass; when non-zero the anchor probe/state application is skipped. */
extern f32 g_uiSakusenDurationDivisor;               /* 0x007A72C0 conf 0.70: Divisor used by the tactics window to derive the short display time from a record's duration (self+0xC = duration / this */
extern u8 maybe_g_uiListRowOverrideFlagA;            /* 0x007A75C6 conf 0.45: First of three consecutive override flags applied when a name/count/icon list row is built. */
extern u8 maybe_g_uiListRowOverrideFlagB;            /* 0x007A75C7 conf 0.45: Second of the three consecutive list-row override flags. */
extern u8 maybe_g_uiListRowOverrideFlagC;            /* 0x007A75C8 conf 0.45: Third of the three consecutive list-row override flags (used as the override table index/id). */
extern s32 maybe_g_uiResourceListFieldTable[6];      /* 0x007A7714 conf 0.45: Six-word field table used by the resource-backed UI list (entry +8 is added to self as a field offset). */
extern u32 g_uiPaneVisibilityColorPair[3];           /* 0x007A7795 conf 0.50: Three colour/attribute words used when a pane pair is shown or hidden with the layout fade; index 0 and index 2 are the  */
extern u32 g_uiPartyMemberTextColor0;                /* 0x007A7814 conf 0.50: Text colour for party-panel member state 0: first word of the 2x4 party-panel text-colour block (states 0..3, row 0; the */
extern u32 g_uiPartyMemberTextColor1;                /* 0x007A7818 conf 0.50: Text colour for party-panel member state 1 (second word of the block). */
extern u32 g_uiPartyMemberTextColor2;                /* 0x007A781C conf 0.50: Text colour for party-panel member state 2 (third word of the block). */
extern u32 g_uiPartyMemberTextColor3;                /* 0x007A7820 conf 0.50: Text colour for party-panel member state 3 (fourth word, last of the first row). */
extern u32 g_uiPartyMemberTextColor4;                /* 0x007A7824 conf 0.50: Fifth word of the 2x4 party-panel text-colour block: first entry of the second (selected/unselected) row; the remaining  */
extern u32 g_uiTextColorSelectedState2;              /* 0x007A7828 conf 0.60: Text colour for a party-panel member whose state byte (self+0x6E..0x71) is 2 while the row is selected. Read by Ui_Party */
extern u32 g_uiTextColorUnselectedState3;            /* 0x007A782C conf 0.60: Text colour for a party-panel member in state 3 on an unselected row, and the lowest value/max ratio band of Ui_TextLaye */
extern u32 g_uiTextColorSelectedState3;              /* 0x007A7830 conf 0.60: Text colour for a party-panel member in state 3 while the row is selected. Zero in the retail image, filled at runtime. */
extern u32 maybe_g_battlePartyPanelState[4];         /* 0x007A7874 conf 0.35: Small static state block shared by the battle command window and the party panel; the code reads a word at +0xC (a mode/ */
extern u32 maybe_g_partyPanelState[6];               /* 0x007A7934 conf 0.45: Static state block of the party panel: the panel code reads words at +0xC and +0x14 (row/selection state) and passes the */
extern u32 maybe_g_messageSelectWindowState[4];      /* 0x007A79B8 conf 0.30: Static state word of the message select window, read when the window takes focus. */
extern u32 maybe_g_battleEnemyListState[6];          /* 0x007A79F8 conf 0.35: Static state block of the battle enemy-list window; words at +0xC and +0x14 are copied into the row build. */
extern u8 maybe_g_equipListColumnCount;              /* 0x007A7A38 conf 0.40: Constant 6 used as a multiplier when the equipment list lays out its rows (row index * this value). Read by Ui_EquipList */
extern u32 maybe_g_messageSelectRowState[6];         /* 0x007A7AC0 conf 0.30: Static state block of the message select window rows; words at +0xC and +0x14 drive the row style. */
extern u32 maybe_g_partyStatusWindowState[4];        /* 0x007A7B40 conf 0.30: Static state word of the party status window, read at +0xC while refreshing rows. */
extern u32 maybe_g_listWindowScrollStep;             /* 0x007A7B80 conf 0.30: Constant 6 used by the generic list window when it computes a scroll target. */
extern u32 maybe_g_battlePartyWindowState[6];        /* 0x007A7BC4 conf 0.30: Static state block of the battle party window, read at +0x14 while rendering a row. */
extern u32 maybe_g_battleSpellWindowCount;           /* 0x007A7C04 conf 0.35: Constant 6 read by the battle spell window when it builds and refreshes the spell list. */
extern u32 maybe_g_battleSkillWindowCount;           /* 0x007A7C48 conf 0.35: Constant 8 read by the battle skill window when it builds and refreshes the skill list. */
extern u8 maybe_g_listWindowRowHeight;               /* 0x007A7CCC conf 0.30: Row height (as an integer converted to float) used by the generic list window constructor. */
extern u8 maybe_g_creditWindowLineCountA;            /* 0x007A7DA0 conf 0.30: Line count read by the first credit-window text pane setup. */
extern u8 maybe_g_creditWindowLineCountB;            /* 0x007A7E3C conf 0.30: Line count read by the second credit-window text pane setup. */
extern u32 maybe_g_boushiPartState;                  /* 0x007A7FC8 conf 0.30: Static state word of the "boushi" (hat) UI part, cleared on release. */
extern u32 maybe_g_rowListWindowState[4];            /* 0x007A803C conf 0.30: Static state block of the row-list window; a word at +8 is read while applying row colours. */
extern u32 maybe_g_uiColorPaletteB[12];              /* 0x007A8078 conf 0.40: Second UI colour palette block, filled by Ui_InitColorPalette_7A8078 (12 32-bit colour words). */
extern char* g_paneNameWinHpmp1;                     /* 0x007A8200 conf 0.70: Pointer to the layout pane name "win_hpmp1"; maybe_Ui_Widget_ApplyPaneAnimation passes it to the layout/pane lookup so t */
extern char* g_paneNamePlateD;                       /* 0x007A8370 conf 0.70: Pointer to the layout pane name "plateD"; maybe_Ui_GuideWindow_SetCell / maybe_Ui_List_UpdateRow passes it to the layout */
extern u32 maybe_g_aspectObjectState;                /* 0x007A8458 conf 0.30: Static state word of the aspect-ratio object initialiser. */
extern u32 maybe_g_rowRenderState[6];                /* 0x007A872C conf 0.30: Static state block read while a list row is rendered and while the shop window builds an item description. */
extern u32 maybe_g_sevenSlotWindowState;             /* 0x007A88B4 conf 0.30: Static state word of the seven-slot window pane initialiser. */
extern f32 maybe_g_overlayBillboardScale[2];         /* 0x007A8960 conf 0.45: Two float scale factors used by the overlay billboard update: the first multiplies the frame delta, the second scales th */
extern char* g_paneNameTxt1;                         /* 0x007A89A4 conf 0.70: Pointer to the layout pane name "txt1"; maybe_Ui_BindFourParts passes it to the layout/pane lookup so the engine can fin */
extern char* g_paneNameBalloon1_2;                   /* 0x007A89B4 conf 0.70: Pointer to the layout pane name "balloon1_2"; Ui_Balloon_BindWinParts passes it to the layout/pane lookup so the engine  */
extern char* g_paneNameBalloon2_2;                   /* 0x007A89DC conf 0.70: Pointer to the layout pane name "balloon2_2"; Ui_Balloon_BindWinParts passes it to the layout/pane lookup so the engine  */
extern u32 maybe_g_windowSlotPool[4];                /* 0x007A8A48 conf 0.35: Static window-slot pool header; the code compares a slot id against the word at +8 and reads the same field when looking */
extern char* g_paneNameNullIconSleep2;               /* 0x007A8ACC conf 0.70: Pointer to the layout pane name "null_icon_sleep2"; maybe_Ui_EmotionWindow_Init passes it to the layout/pane lookup so t */
extern u32 maybe_g_slotDefaults[4];                  /* 0x007A8AF4 conf 0.30: Default values copied into a UI slot when it is reset (word at +8). */
extern char* g_paneNameIconTargetField1;             /* 0x007A8BE4 conf 0.70: Pointer to the layout pane name "icon_target_field1"; Ui_SakusenWindow_CreateDetailSlots passes it to the layout/pane lo */
extern f32 maybe_g_loadingScreenProgress;            /* 0x007A8CCC conf 0.35: Float progress/alpha value read by the loading-screen update. */
extern char* g_paneNameTxtChage;                     /* 0x007A8EB4 conf 0.70: Pointer to the layout pane name "txt_chage"; Ui_SortListWindow_BindHeaders passes it to the layout/pane lookup so the en */
extern void* maybe_g_equipWindowCallbackTable[3];    /* 0x007A8F00 conf 0.40: Three-entry table of code pointers walked by the equipment window when it moves the cursor or pops a pane; the first ent */
extern u32 maybe_g_equipWindowState[4];              /* 0x007A8F30 conf 0.30: Static state block of the equipment window, read by its constructor, destructor and cursor movement. */
extern u32 maybe_g_gridWindowState[4];               /* 0x007A8F7C conf 0.30: Static state block shared by the grid window, item grid and item-icon row refresh code. */
extern u16 maybe_g_equipCompareColorScale[8];        /* 0x007A8F84 conf 0.40: Per-channel 16-bit scale factors used when the equipment-compare window tints a colour word (each channel is multiplied  */
extern u16 maybe_g_statCompareColorScale[12];        /* 0x007A8FE8 conf 0.40: Per-channel 16-bit scale factors used when the stat-compare window tints a colour word. */
extern u32 maybe_g_mainMenuTextState;                /* 0x007A909C conf 0.35: State word of the main-menu text resources (retail value 1); read by the loader, the constructor and the release path. */
extern u32 maybe_g_skillListState[4];                /* 0x007A91C4 conf 0.30: Static state block of the skill list, read at +4 while pruning entries. */
extern u8 g_messageWindowClampInitGuard;             /* 0x007A9238 conf 0.55: C++ function-local static initialisation guard for the message-window text clamp helper: bit 0 is tested and func_001000 */
extern u32 maybe_g_itemRowIconState[8];              /* 0x007A9318 conf 0.30: Static state block read while the item-row icons are updated and while a node looks up its base child. */
extern u16 maybe_g_itemRowIconColors[8];             /* 0x007A9320 conf 0.40: Per-channel 16-bit colour scale factors used when the item-row icons are tinted. */
extern char* g_animNameEffectHamon2;                 /* 0x007A9350 conf 0.70: Pointer to the animation name "effect_hamon2"; Ui_Part_ClearAnimsAndPlayOpenedIn passes it to the layout/pane lookup so  */
extern char* g_animNameHibi6;                        /* 0x007A935C conf 0.70: Pointer to the animation name "hibi6"; Ui_Part_SetVisibleMask passes it to the layout/pane lookup so the engine can find */
extern u32 maybe_g_pagedIconSelectState;             /* 0x007A9418 conf 0.30: Static state word of the paged icon-select window, read by its pane initialiser and row update. */
extern u8 maybe_g_recordDetailWindowState;           /* 0x007A94C5 conf 0.30: Byte state read by the record-detail window while it updates its text. */
extern char* g_paneNameIconKeyPad;                   /* 0x007A9578 conf 0.70: Pointer to the layout pane name "icon_key_pad"; Ui_MonsterBook_InitData passes it to the layout/pane lookup so the engin */
extern u32 maybe_g_monsterBookState[4];              /* 0x007A9588 conf 0.35: Static state block of the monster book window, read by its constructor, release path and icon update. */
extern u8 maybe_g_monsterBookFlag;                   /* 0x007A95C4 conf 0.30: Byte flag read by the monster book data initialiser and the text-list widget constructor. */
extern u32 maybe_g_monsterBookRowValues[8];          /* 0x007A96E8 conf 0.35: Row values copied out of the monster book list when it refreshes (indices 0, 2 and 4 are read). */
extern char* g_paneNameTxtL1;                        /* 0x007A9720 conf 0.70: Pointer to the layout pane name "txt_l1"; maybe_Ui_RouletteWheel_BuildSlots passes it to the layout/pane lookup so the e */
extern u32 maybe_g_charaStatusWindowState;           /* 0x007A982C conf 0.30: Static state word of the character status window, read while filling a party-member row. */
extern u32 maybe_g_rowColors[4];                     /* 0x007A989C conf 0.35: Colour words applied to a generic list row (normal, selected and flagged variants). */
extern char* g_paneNameFmtTxtName;                   /* 0x007A98DC conf 0.70: Pointer to the layout pane name "txt%d_name"; Ui_TsuyosaWindow_InitPagerPanes passes it to the layout/pane lookup so the */
extern u32 maybe_g_fourRowIconWindowState[3];        /* 0x007A9958 conf 0.35: Static state block shared by the four-row icon window, party icon rows and the two-column value list. */
extern u16 maybe_g_tsuyosaColorScale[8];             /* 0x007A9960 conf 0.40: Per-channel 16-bit colour scale factors used by the "tsuyosa" (strength) window when it tints member rows. */
extern u8 maybe_g_worldMapFlag;                      /* 0x007A9A90 conf 0.30: Byte flag of the world-map screen, tested and set by the world-map setup, display-mode and page-selection code. */
extern f32 maybe_g_worldMapShipIconScale;            /* 0x007A9A9C conf 0.35: Float scale applied to the world-map ship icon position. */
extern f32 maybe_g_worldMapShipIconOffset[2];        /* 0x007A9AA0 conf 0.35: Two float offsets added to the world-map ship icon position (x and y). */
extern u32 maybe_g_fadeWipeState;                    /* 0x007A9AE8 conf 0.30: Static state word of the fade/wipe effect, tested by its initialiser and by the world-map variant loader. */
extern u32 maybe_g_nodeListState;                    /* 0x007A9B20 conf 0.30: Static state word of the UI node-list registration helper. */
extern f32 maybe_g_overlayQuadScale;                 /* 0x007A9B58 conf 0.35: Float scale multiplied into the overlay quad size when the quad object is created. */
extern u32 maybe_g_pokerWindowTable[4];              /* 0x007A9CCC conf 0.35: Table of 32-bit entries indexed by the poker window constructor; the first retail entry is a data pointer. */
extern f32 maybe_g_jackpotCameraOffsetX;             /* 0x007A9D6C conf 0.35: Float X offset subtracted from the jackpot camera track position. */
extern f32 maybe_g_jackpotCameraOffsetY;             /* 0x007A9D70 conf 0.35: Float Y offset added to the jackpot camera track position. */
extern f32 maybe_g_jackpotCameraOffsetZ;             /* 0x007A9D74 conf 0.35: Float Z offset subtracted from the jackpot camera track position. */
extern char* g_textureNameTexHitSlime;               /* 0x007A9EA0 conf 0.70: Pointer to the texture name "tex_hit_slime"; Ui_SlotMachine_UpdateReelPositions passes it to the layout/pane lookup so t */
extern u32 maybe_g_slotNumberPlateState;             /* 0x007A9F1C conf 0.30: Static state word of the slot-machine number-plate 3D initialiser. */
extern u32 maybe_g_uiColorPaletteC[12];              /* 0x007A9FDC conf 0.40: Third UI colour palette block, filled by Ui_InitColorPalette_7A9FDC (12 32-bit colour words). */
extern char* g_layoutNameFmtMenuSlotBelt3d;          /* 0x007AA054 conf 0.70: Pointer to the layout name format "menu_slot_belt_%s_%c_3d.bflyt"; Ui_HitIcon_CreateSprites/RebuildSprites passes it to  */
extern char* g_paneNameBelt01;                       /* 0x007AA098 conf 0.70: Pointer to the layout pane name "belt01"; Ui_HitIcon_FindSlotNode passes it to the layout/pane lookup so the engine can  */
extern u32 maybe_g_digitRowWidgetState[8];           /* 0x007AA1A4 conf 0.30: Static state block read by the digit-row widget initialiser and the window icon-sprite setter (words at +8 and +0x1C). */
extern u32 maybe_g_battleTextWindowState;            /* 0x007AA3B8 conf 0.30: Static state word of the battle text window, read by its release path and the draw-context initialiser. */
extern u32 maybe_g_subObjectAnimRef;                 /* 0x007AA510 conf 0.30: Animation reference copied into a UI sub-object when it is constructed. */
extern char* g_paneNameTxtTitle;                     /* 0x007AA5B8 conf 0.70: Pointer to the layout pane name "txt_title"; Ui_TwoColumnListWindow_InitPanes passes it to the layout/pane lookup so the */
extern char* g_paneNameWinDouguDoSelect1;            /* 0x007AAA3C conf 0.70: Pointer to the layout pane name "win_dougu_do_select1"; maybe_Ui_UmaWindow_BuildModeRows passes it to the layout/pane lo */
extern char* g_paneNameNullTxtL1;                    /* 0x007AAA54 conf 0.70: Pointer to the layout pane name "null_txt_l1"; maybe_Ui_MemberListWindow_RebuildRows passes it to the layout/pane lookup */
extern char* g_paneNameColorRed;                     /* 0x007AAB48 conf 0.70: Pointer to the layout pane name "color_red"; Ui_ColorSelectWindow_InitPanes passes it to the layout/pane lookup so the e */
extern char* g_paneNameDownOut;                      /* 0x007AAB64 conf 0.70: Pointer to the layout pane name "down_out"; Ui_ColorSelectWindow_InitPanes passes it to the layout/pane lookup so the en */
extern u8 maybe_g_shopWindowState;                   /* 0x007AABEC conf 0.30: Byte state copied into the shop window when its visibility is applied. */
extern char* g_paneNameSelectL1;                     /* 0x007AAE40 conf 0.70: Pointer to the layout pane name "select_l1"; Ui_TalkWindow_BuildWidgets passes it to the layout/pane lookup so the engin */
extern char* g_paneNamePopL1;                        /* 0x007AAE60 conf 0.70: Pointer to the layout pane name "pop_l1"; Ui_TalkWindow_BuildWidgets passes it to the layout/pane lookup so the engine c */
extern char* g_paneNamePop2L1;                       /* 0x007AAE80 conf 0.70: Pointer to the layout pane name "pop2_l1"; Ui_TalkWindow_BuildWidgets passes it to the layout/pane lookup so the engine  */
extern u32 maybe_g_statusPanelState;                 /* 0x007AAED4 conf 0.30: Static state word of the status panel, read while a slot text is updated. */
extern char* g_paneNameNullKanban2;                  /* 0x007AAF08 conf 0.70: Pointer to the layout pane name "null_kanban2"; Ui_TalkWindow_Init passes it to the layout/pane lookup so the engine can */
extern u8 maybe_g_listWidgetRowCount;                /* 0x007AAF50 conf 0.30: Byte count read by the list widget while it fills its rows. */
extern u8 maybe_g_drawSpriteId;                      /* 0x007AB184 conf 0.30: Byte sprite id read by the sprite draw helper. */
extern u8 maybe_g_listWindowRowCount;                /* 0x007AB338 conf 0.30: Byte count read by the list window while it sets up its rows. */
extern u8 maybe_g_kyoukaiSelectFlagA;                /* 0x007AB3E4 conf 0.30: Byte flag tested by the "kyoukai" (boundary) select window refresh, together with a per-row byte array. */
extern u8 maybe_g_kyoukaiSelectFlagB;                /* 0x007AB3E5 conf 0.30: Second byte flag tested by the "kyoukai" (boundary) select window refresh. */
extern u8 g_uiColorPalette[48];                      /* 0x007AB514 conf 0.55: Base of the 48-byte UI colour palette filled by Ui_InitColorPalette_7AB514: twelve four-byte RGBA colours (red, green, b */
extern u8 g_uiColorPaletteByte01;                    /* 0x007AB515 conf 0.50: Byte 0x01 of the 48-byte UI RGBA palette at 0x007AB514: colour 0, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte02;                    /* 0x007AB516 conf 0.50: Byte 0x02 of the 48-byte UI RGBA palette at 0x007AB514: colour 0, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte03;                    /* 0x007AB517 conf 0.50: Byte 0x03 of the 48-byte UI RGBA palette at 0x007AB514: colour 0, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte04;                    /* 0x007AB518 conf 0.50: Byte 0x04 of the 48-byte UI RGBA palette at 0x007AB514: colour 1, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte05;                    /* 0x007AB519 conf 0.50: Byte 0x05 of the 48-byte UI RGBA palette at 0x007AB514: colour 1, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte06;                    /* 0x007AB51A conf 0.50: Byte 0x06 of the 48-byte UI RGBA palette at 0x007AB514: colour 1, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte07;                    /* 0x007AB51B conf 0.50: Byte 0x07 of the 48-byte UI RGBA palette at 0x007AB514: colour 1, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte08;                    /* 0x007AB51C conf 0.50: Byte 0x08 of the 48-byte UI RGBA palette at 0x007AB514: colour 2, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte09;                    /* 0x007AB51D conf 0.50: Byte 0x09 of the 48-byte UI RGBA palette at 0x007AB514: colour 2, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte0A;                    /* 0x007AB51E conf 0.50: Byte 0x0A of the 48-byte UI RGBA palette at 0x007AB514: colour 2, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte0B;                    /* 0x007AB51F conf 0.50: Byte 0x0B of the 48-byte UI RGBA palette at 0x007AB514: colour 2, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte0C;                    /* 0x007AB520 conf 0.50: Byte 0x0C of the 48-byte UI RGBA palette at 0x007AB514: colour 3, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte0D;                    /* 0x007AB521 conf 0.50: Byte 0x0D of the 48-byte UI RGBA palette at 0x007AB514: colour 3, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte0E;                    /* 0x007AB522 conf 0.50: Byte 0x0E of the 48-byte UI RGBA palette at 0x007AB514: colour 3, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte0F;                    /* 0x007AB523 conf 0.50: Byte 0x0F of the 48-byte UI RGBA palette at 0x007AB514: colour 3, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte10;                    /* 0x007AB524 conf 0.50: Byte 0x10 of the 48-byte UI RGBA palette at 0x007AB514: colour 4, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte11;                    /* 0x007AB525 conf 0.50: Byte 0x11 of the 48-byte UI RGBA palette at 0x007AB514: colour 4, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte12;                    /* 0x007AB526 conf 0.50: Byte 0x12 of the 48-byte UI RGBA palette at 0x007AB514: colour 4, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte13;                    /* 0x007AB527 conf 0.50: Byte 0x13 of the 48-byte UI RGBA palette at 0x007AB514: colour 4, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte14;                    /* 0x007AB528 conf 0.50: Byte 0x14 of the 48-byte UI RGBA palette at 0x007AB514: colour 5, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte15;                    /* 0x007AB529 conf 0.50: Byte 0x15 of the 48-byte UI RGBA palette at 0x007AB514: colour 5, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte16;                    /* 0x007AB52A conf 0.50: Byte 0x16 of the 48-byte UI RGBA palette at 0x007AB514: colour 5, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte17;                    /* 0x007AB52B conf 0.50: Byte 0x17 of the 48-byte UI RGBA palette at 0x007AB514: colour 5, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte18;                    /* 0x007AB52C conf 0.50: Byte 0x18 of the 48-byte UI RGBA palette at 0x007AB514: colour 6, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte19;                    /* 0x007AB52D conf 0.50: Byte 0x19 of the 48-byte UI RGBA palette at 0x007AB514: colour 6, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte1A;                    /* 0x007AB52E conf 0.50: Byte 0x1A of the 48-byte UI RGBA palette at 0x007AB514: colour 6, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte1B;                    /* 0x007AB52F conf 0.50: Byte 0x1B of the 48-byte UI RGBA palette at 0x007AB514: colour 6, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte1C;                    /* 0x007AB530 conf 0.50: Byte 0x1C of the 48-byte UI RGBA palette at 0x007AB514: colour 7, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte1D;                    /* 0x007AB531 conf 0.50: Byte 0x1D of the 48-byte UI RGBA palette at 0x007AB514: colour 7, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte1E;                    /* 0x007AB532 conf 0.50: Byte 0x1E of the 48-byte UI RGBA palette at 0x007AB514: colour 7, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte1F;                    /* 0x007AB533 conf 0.50: Byte 0x1F of the 48-byte UI RGBA palette at 0x007AB514: colour 7, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte20;                    /* 0x007AB534 conf 0.50: Byte 0x20 of the 48-byte UI RGBA palette at 0x007AB514: colour 8, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte21;                    /* 0x007AB535 conf 0.50: Byte 0x21 of the 48-byte UI RGBA palette at 0x007AB514: colour 8, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte22;                    /* 0x007AB536 conf 0.50: Byte 0x22 of the 48-byte UI RGBA palette at 0x007AB514: colour 8, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte23;                    /* 0x007AB537 conf 0.50: Byte 0x23 of the 48-byte UI RGBA palette at 0x007AB514: colour 8, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte24;                    /* 0x007AB538 conf 0.50: Byte 0x24 of the 48-byte UI RGBA palette at 0x007AB514: colour 9, red channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte25;                    /* 0x007AB539 conf 0.50: Byte 0x25 of the 48-byte UI RGBA palette at 0x007AB514: colour 9, green channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte26;                    /* 0x007AB53A conf 0.50: Byte 0x26 of the 48-byte UI RGBA palette at 0x007AB514: colour 9, blue channel. Written by Ui_InitColorPalette_7AB514. */
extern u8 g_uiColorPaletteByte27;                    /* 0x007AB53B conf 0.50: Byte 0x27 of the 48-byte UI RGBA palette at 0x007AB514: colour 9, alpha channel. Written by Ui_InitColorPalette_7AB514. */
extern void* g_uiListData;                           /* 0x007AB814 conf 0.55: Pointer to the external list-data object used by the multi-purpose list window; NULL until the list is built. Its row ta */
extern u32 maybe_g_listWindowRowItem;                /* 0x007AB88C conf 0.30: Static state word read by the list window when it sets a row item. */
extern u32 maybe_g_listRowValueColor[4];             /* 0x007AB8C4 conf 0.35: Colour words used when a list row applies its value colour or a window sets its tab icons (words at +0xC and +0x10). */
extern u32 maybe_g_listRowFlaggedValue[3];           /* 0x007ABAA4 conf 0.35: Three words copied into a list row when it renders a flagged value. */
extern u32 maybe_g_profileWindowState;               /* 0x007ABC18 conf 0.30: Static state word of the profile window, read while its details are updated. */
extern char* g_paneNameWinTalk;                      /* 0x007ABD8C conf 0.70: Pointer to the layout pane name "win_talk"; maybe_Ui_MenuWindow_UpdateLayout passes it to the layout/pane lookup so the  */
extern u32 maybe_g_titleScreenState;                 /* 0x007ABEEC conf 0.35: Static state block of the title screen, read by its constructor and destructor. */
extern u32 maybe_g_partyListRowColors[4];            /* 0x007AC230 conf 0.35: Colour words used when the party-list window fills a member row or the item-list window builds rows from an item. */
extern u8 maybe_g_shopItemListCount;                 /* 0x007AC270 conf 0.30: Byte count read by the shop item list while it populates its rows. */
extern u16 maybe_g_textColorTint[8];                 /* 0x007AC3B8 conf 0.40: Per-channel 16-bit tint factors applied by Ui_SetTextColorTint (each channel is multiplied by one entry and divided by 0 */
extern u8 maybe_g_messageWindowLineHeight;           /* 0x007AC428 conf 0.30: Byte line height copied into the message window when it measures and lays out its text. */
extern u32 maybe_g_messageWindowPaneName;            /* 0x007AC464 conf 0.35: Pane-name pointer used by Ui_MessageWindow_InitPanes; the retail word is a data-section pointer. */
extern u32 maybe_g_messageWindowPaneNameB;           /* 0x007AC474 conf 0.35: Second pane-name pointer passed to Ui_MessageWindow_BindPanes by Ui_MessageWindow_InitPanes. */
extern u32 maybe_g_messageWindowPaneNameC;           /* 0x007AC4A4 conf 0.35: Third pane-name pointer passed to Ui_MessageWindow_BindPanes by Ui_MessageWindow_InitPanes. */
extern u32 maybe_g_renderObjectTexState[2];          /* 0x007AC4D8 conf 0.30: Two words read by the render-object texture draw (indices 0 and 1). */
extern u8 maybe_g_renderObjectTexFlag;               /* 0x007AC4E0 conf 0.30: Byte flag read by the render-object texture draw. */
extern char* g_paneNameTxtKanban1;                   /* 0x007AC51C conf 0.70: Pointer to the layout pane name "txt_kanban1"; Ui_MessageWindow_InitScrollPanes passes it to the layout/pane lookup so t */
extern u32 maybe_g_messageWindowScrollPaneName;      /* 0x007AC538 conf 0.35: Pane-name pointer passed to Ui_MessageWindow_BindPanes by Ui_MessageWindow_InitScrollPanes. */
extern u32 maybe_g_messageWindowScrollPaneNameB;     /* 0x007AC568 conf 0.35: Second pane-name pointer passed to Ui_MessageWindow_BindPanes by Ui_MessageWindow_InitScrollPanes. */
extern u32 maybe_g_partySelectRowColors[3];          /* 0x007AC5D4 conf 0.35: Colour words used when the party-select window refreshes its rows. */
extern u16 maybe_g_partySelectColorScale[8];         /* 0x007AC5DC conf 0.40: Per-channel 16-bit colour scale factors used by the party-select window row refresh. */
extern u8 maybe_g_widgetDrawFlagA;                   /* 0x007AC77C conf 0.30: Byte flag tested before a widget draws itself and its children (variant C/Ex). */
extern u8 maybe_g_widgetDrawFlagB;                   /* 0x007AC77D conf 0.30: Byte flag tested before a widget draws itself and its children (variant B). */
extern char* g_fontName2D9;                          /* 0x007AC7B4 conf 0.70: Pointer to the font resource name "2D9.bffnt"; Ui_Object_SetSlotResource passes it to the layout/pane lookup so the engi */
extern void* g_messageFormatArgSlots;                /* 0x007AC834 conf 0.60: Pointer to the array of formatted message-argument slots; each slot is 0x108 bytes and the text formatter writes the for */
extern char* g_fontPath2D9;                          /* 0x007AC8B0 conf 0.70: Pointer to the font resource name "font/2D9.bffnt"; Ui_SmithMenu_SetAllSlotHandles/SetCategoryIcons passes it to the lay */
extern char* g_textureNameC4_16x32Flip;              /* 0x007AE2D4 conf 0.70: Pointer to the texture name "c4_16x32_flip"; Ui_2dModel_Load passes it to the layout/pane lookup so the engine can find  */
extern u32 maybe_g_iconCacheState[2];                /* 0x007AE4C0 conf 0.40: Static state block of the icon cache: the worker thread and the loaders test the word at +4 for zero. */
extern u8 maybe_g_iconCacheServiceFlag;              /* 0x007AE4C2 conf 0.35: Byte flag of the icon-cache service, passed to maybe_Ui_IconCache_ReleaseService by the worker thread. */
extern u32 maybe_g_charaStatusUpdateState;           /* 0x007AE55C conf 0.30: State word of the character-status update (retail value 1). */
extern u8 maybe_g_pagedTextWindowFlag;               /* 0x007AE725 conf 0.30: Byte flag read by the paged text window while it initialises its rows. */
extern u32 maybe_g_animRefPanes;                     /* 0x007AE880 conf 0.30: Static state word read by the animation-reference pane reset. */
extern u32 maybe_g_nodeBoundingBox;                  /* 0x007AE888 conf 0.30: Static state word read by the node bounding-box helper. */
extern u32 maybe_g_uiAnimObjectPool[4];              /* 0x007AE890 conf 0.40: Static pool/manager pointer used by the UI animation object code: the layout player, the animation clip loader and the o */
extern u8 maybe_g_uiSlotPoolParam;                   /* 0x007AE894 conf 0.35: Byte parameter written by maybe_Ui_System_SetSlotPoolParam. */
extern u32 maybe_g_containerChildList;               /* 0x007AE89C conf 0.30: Static state word read by the present/render child-list walk and the filtered-child collector. */
extern u32 maybe_g_uiPartPool;                       /* 0x007AE8A0 conf 0.40: Static pool pointer shared by the UI part code (popups, hit icons, casino windows, check lists). */
extern u32 maybe_g_uiPartAnimPool;                   /* 0x007AE8A4 conf 0.40: Static pool pointer shared by the UI part animation setup (gauge, map, location, poker and party-gauge windows). */
extern u32 maybe_g_uiPaneLookupState;                /* 0x007AE8AC conf 0.35: Static state word used by the pane lookup helpers (find child by name, collect named pane) and the text-scroll layout co */
extern u32 maybe_g_componentLookupState;             /* 0x007AE8E4 conf 0.30: Static state word read by maybe_Ui_FindComponentByType. */
extern u32 maybe_g_iconCacheService[2];              /* 0x007AE9E0 conf 0.40: Icon-cache service state: the first byte is the "service open" flag tested by the ensure/open/stop helpers, the second w */
extern u8 g_glyphQuadArrayInitGuard;                 /* 0x007AECCC conf 0.55: C++ function-local static initialisation guard for the glyph quad array builder: bit 0 is tested and func_0010009C (__cx */
extern u8 g_textConsoleInitGuard;                    /* 0x007AECE4 conf 0.55: C++ function-local static initialisation guard for the text console singleton getter. */
extern u8 g_textSystem2InitGuard;                    /* 0x007AECEC conf 0.55: C++ function-local static initialisation guard for the second text-system singleton getter. */
extern u8 g_textScrollerInitGuard;                   /* 0x007AED04 conf 0.55: C++ function-local static initialisation guard for the text-scroller singleton getter. */
extern u8 g_textSystemInitGuard;                     /* 0x007AED08 conf 0.55: C++ function-local static initialisation guard for the text-system singleton getter. */
extern u32 maybe_g_atlasContext;                     /* 0x007AF1AC conf 0.35: Static atlas-context pointer tested for zero by the atlas acquire helper and the reference-count release path. */
extern u32 maybe_g_panelMessageWindowState;          /* 0x007B7D80 conf 0.30: Static state word of the panel message window, read by its update and by the window layout transition. */
extern u32 maybe_g_handleTable;                      /* 0x007BA2D0 conf 0.40: Base of a global handle table: a 32-bit handle is split into an index (low bits, masked by the companion word) and a gen */
extern u8 g_sceneTransitionManagerInitFlag;          /* 0x007BE2DC conf 0.60: Lazy-initialisation flag of the scene-transition manager singleton: the accessor tests it, clears it and then allocates  */
extern void* g_sceneTransitionManager;               /* 0x007BE2E0 conf 0.65: Pointer to the process-wide scene-transition/state manager (0x28 bytes), created on first use by Ui_GetSceneTransitionMa */
extern u8 g_soundPlayerInitFlag;                     /* 0x007BE2E4 conf 0.60: Lazy-initialisation flag of the sound player singleton: the accessor tests it, clears it and then allocates the instance */
extern void* g_soundPlayer;                          /* 0x007BE2E8 conf 0.70: Pointer to the process-wide sound player singleton (0x1EB0 bytes), created on first use by Sound_GetPlayer and stored he */
extern u8 g_memoryManagerInitFlag;                   /* 0x007BE2EC conf 0.55: Lazy-initialisation flag of the memory manager singleton: the accessor tests it, clears it and then allocates the instan */
extern void* g_memoryManager;                        /* 0x007BE2F0 conf 0.60: Pointer to the process-wide memory manager singleton, created on first use by the memory-manager accessor and stored her */
extern u8 g_uiCommonResourcesInitFlag;               /* 0x007BE2F4 conf 0.50: Lazy-initialisation flag of the UI common-resource block singleton: the accessor tests it, clears it and then allocates  */
extern void* g_uiCommonResources;                    /* 0x007BE2F8 conf 0.50: Pointer to the process-wide UI common-resource block, created on first use by maybe_Ui_InitCommonResources and stored he */
extern u8 g_osGameWorkInitFlag;                      /* 0x007BE2FC conf 0.60: Lazy-initialisation flag of the per-thread game work singleton: the accessor tests it, clears it and then allocates the  */
extern void* g_osGameWork;                           /* 0x007BE300 conf 0.65: Pointer to the process-wide per-thread game work root (context at +0x08), created on first use by Os_GetGameWork and sto */
extern u8 g_partySaveWorkInitFlag;                   /* 0x007BE304 conf 0.60: Lazy-initialisation flag of the party/save work singleton: the accessor tests it, clears it and then allocates the insta */
extern void* g_partySaveWork;                        /* 0x007BE308 conf 0.70: Pointer to the process-wide party/save work singleton (0xE3C8 bytes, built by SaveWork_Container_BaseCtor), created on f */
extern u8 g_dataManagerInitFlag;                     /* 0x007BE30C conf 0.55: Lazy-initialisation flag of the data-table manager singleton: the accessor tests it, clears it and then allocates the in */
extern void* g_dataManager;                          /* 0x007BE310 conf 0.60: Pointer to the process-wide data-table manager singleton, created on first use by the data-manager accessor and stored h */
extern u8 g_gameWorkInitFlag;                        /* 0x007BE31C conf 0.65: Lazy-initialisation flag of the save/party game work singleton: the accessor tests it, clears it and then allocates the  */
extern void* g_gameWork;                             /* 0x007BE320 conf 0.70: Pointer to the process-wide save/party game work (party at +0x24A98), created on first use by Game_GetWork and stored he */
extern u8 g_uiRootSingletonInitFlag;                 /* 0x007BE324 conf 0.60: Lazy-initialisation flag of the UI root singleton singleton: the accessor tests it, clears it and then allocates the ins */
extern void* g_uiRootSingleton;                      /* 0x007BE328 conf 0.65: Pointer to the process-wide UI root singleton (0x80 bytes), created on first use by Ui_GetRootSingleton and stored here; */
extern u8 g_fsCacheSetInitFlag;                      /* 0x007BE32C conf 0.55: Lazy-initialisation flag of the filesystem cache set singleton: the accessor tests it, clears it and then allocates the  */
extern void* g_fsCacheSetSingleton;                  /* 0x007BE330 conf 0.60: Pointer to the process-wide filesystem cache set (0x21C bytes), created on first use by Fs_CacheSet_Initialize and store */
extern u8 g_uiCoreInitFlag;                          /* 0x007BE33C conf 0.60: Lazy-initialisation flag of the UI core object singleton: the accessor tests it, clears it and then allocates the instan */
extern void* g_uiCore;                               /* 0x007BE340 conf 0.70: Pointer to the process-wide UI core object (0x98 bytes; +0x10 2D UI manager, +0x14 fade manager), created on first use b */
extern u8 maybe_g_engineStateFlag;                   /* 0x007BE358 conf 0.30: Byte flag of the engine/render state, cleared by Engine_Initialize and read by the overlay draw and main-menu text code. */
extern u8 g_inputManagerInitFlag;                    /* 0x007BE36C conf 0.55: Lazy-initialisation flag of the input manager singleton: the accessor tests it, clears it and then allocates the instanc */
extern void* g_inputManager;                         /* 0x007BE370 conf 0.60: Pointer to the process-wide input/pad-state manager (0x1D4 bytes), created on first use by Input_Initialize and stored h */
extern u8 g_gfxContextInitFlag;                      /* 0x007BE384 conf 0.60: Lazy-initialisation flag of the graphics context singleton: the accessor tests it, clears it and then allocates the inst */
extern void* g_gfxContext;                           /* 0x007BE388 conf 0.70: Pointer to the process-wide graphics context (0x1348 bytes: camera matrices, material layers, UI draw lists, font pages, */
extern u16 g_wideEmptyName[1];                       /* 0x007BE72C conf 0.60: Empty wide string L"" used as the source when a 7-character name field is cleared: Text_Style_Create and Ui_PartyList_In */
extern char g_paneNameCasino[7];                     /* 0x007BE72E conf 0.70: NUL-terminated layout pane name "casino" passed to a widget virtual call by maybe_Ui_Widget_ResetVirtual. */
extern u16 g_wideEmptyFormat[1];                     /* 0x007BE736 conf 0.55: Empty wide string L"" used as the default format string by Ui_Text_MeasureAndEmitRuns when a text run has no format argu */
extern char g_paneNameWinLoadStory[15];              /* 0x007BE746 conf 0.70: NUL-terminated layout pane name "win_load_story" used by maybe_Ui_CharaStatusWindow_BindCharaPanes. */
extern u16 g_wideFormatLs[4];                        /* 0x007BE774 conf 0.70: Wide format string L"%ls" passed to Message_FormatArgSlot_Reset by Ui_TextFormat_FormatWideString so a text argument is  */
extern u16 g_wideBlankTextA[2];                      /* 0x007BE77C conf 0.55: Single-character wide string holding code point 0xFF1F, used as the argument value for the "%ls" format when the text wi */
extern u16 g_wideBlankTextB[2];                      /* 0x007BE780 conf 0.55: Single-character wide string holding code point 0xFF01, used as the argument value for the "%ls" format when the text wi */
extern u16 g_wideFormatLs2[4];                       /* 0x007BE8AA conf 0.70: Second copy of the wide format string L"%ls", used by Ui_MessageWindow_SetNumberArg when it sets a message argument to a */
extern char g_resNameAccessoryTableParam[27];        /* 0x007BE8B2 conf 0.75: NUL-terminated resource file name "accessory_table_param.bxon" handed to the resource manager (func_00124B24) by maybe_U */
extern char g_resNameItemBoxParam[20];               /* 0x007BE8CD conf 0.75: NUL-terminated resource file name "item_box_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layou */
extern char g_resNameItemTableParam[22];             /* 0x007BE8E1 conf 0.75: NUL-terminated resource file name "item_table_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Lay */
extern char g_resNameMonsterParam[19];               /* 0x007BE8F7 conf 0.75: NUL-terminated resource file name "monster_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout */
extern char g_resNameMonsterModelParam2d[28];        /* 0x007BE90A conf 0.75: NUL-terminated resource file name "monster_model_param_2d.bxon" handed to the resource manager (func_00124B24) by maybe_ */
extern char g_resNameMonsterTable[19];               /* 0x007BE926 conf 0.75: NUL-terminated resource file name "monster_table.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout */
extern char g_resNameSkillParam[17];                 /* 0x007BE939 conf 0.75: NUL-terminated resource file name "skill_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_L */
extern char g_resNameLayerParam[17];                 /* 0x007BE94A conf 0.75: NUL-terminated resource file name "layer_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_L */
extern char g_resNameLevelMapType[19];               /* 0x007BE95B conf 0.75: NUL-terminated resource file name "level_mapType.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout */
extern char g_resNameFieldMaterial[20];              /* 0x007BE96E conf 0.75: NUL-terminated resource file name "field_material.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layou */
extern char g_resNameEnemyBase[16];                  /* 0x007BE982 conf 0.75: NUL-terminated resource file name "enemy_base.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameEnemyCategory[20];              /* 0x007BE992 conf 0.75: NUL-terminated resource file name "enemy_category.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layou */
extern char g_resNameEnemyBattle[18];                /* 0x007BE9A6 conf 0.75: NUL-terminated resource file name "enemy_battle.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_ */
extern char g_resNameEnemyAI[14];                    /* 0x007BE9B8 conf 0.75: NUL-terminated resource file name "enemy_AI.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Load */
extern char g_resNameEnemyPop[15];                   /* 0x007BE9C6 conf 0.75: NUL-terminated resource file name "enemy_pop.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Loa */
extern char g_resNameEncountTable[19];               /* 0x007BE9D5 conf 0.75: NUL-terminated resource file name "encount_table.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout */
extern char g_resNameEnemyEcoAct[18];                /* 0x007BE9E8 conf 0.75: NUL-terminated resource file name "enemy_ecoAct.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_ */
extern char g_resNameScenarioBattle[21];             /* 0x007BE9FA conf 0.75: NUL-terminated resource file name "scenario_battle.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layo */
extern char g_resNameIrregularPartyParam[27];        /* 0x007BEA0F conf 0.75: NUL-terminated resource file name "irregular_party_param.bxon" handed to the resource manager (func_00124B24) by maybe_U */
extern char g_resNameStoryB160[16];                  /* 0x007BEA2A conf 0.75: NUL-terminated resource file name "story_b160.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryB170[16];                  /* 0x007BEA3A conf 0.75: NUL-terminated resource file name "story_b170.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC010[16];                  /* 0x007BEA4A conf 0.75: NUL-terminated resource file name "story_c010.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC020[16];                  /* 0x007BEA5A conf 0.75: NUL-terminated resource file name "story_c020.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC030[16];                  /* 0x007BEA6A conf 0.75: NUL-terminated resource file name "story_c030.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC040[16];                  /* 0x007BEA7A conf 0.75: NUL-terminated resource file name "story_c040.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC050[16];                  /* 0x007BEA8A conf 0.75: NUL-terminated resource file name "story_c050.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC060[16];                  /* 0x007BEA9A conf 0.75: NUL-terminated resource file name "story_c060.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC070[16];                  /* 0x007BEAAA conf 0.75: NUL-terminated resource file name "story_c070.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC080[16];                  /* 0x007BEABA conf 0.75: NUL-terminated resource file name "story_c080.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameSpell[11];                      /* 0x007BEACA conf 0.75: NUL-terminated resource file name "spell.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_LoadAnd */
extern char g_resNameStoryC090[16];                  /* 0x007BEAD5 conf 0.75: NUL-terminated resource file name "story_c090.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC100[16];                  /* 0x007BEAE5 conf 0.75: NUL-terminated resource file name "story_c100.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC110[16];                  /* 0x007BEAF5 conf 0.75: NUL-terminated resource file name "story_c110.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC120[16];                  /* 0x007BEB05 conf 0.75: NUL-terminated resource file name "story_c120.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC130[16];                  /* 0x007BEB15 conf 0.75: NUL-terminated resource file name "story_c130.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC140[16];                  /* 0x007BEB25 conf 0.75: NUL-terminated resource file name "story_c140.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC150[16];                  /* 0x007BEB35 conf 0.75: NUL-terminated resource file name "story_c150.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC160[16];                  /* 0x007BEB45 conf 0.75: NUL-terminated resource file name "story_c160.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC170[16];                  /* 0x007BEB55 conf 0.75: NUL-terminated resource file name "story_c170.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC180[16];                  /* 0x007BEB65 conf 0.75: NUL-terminated resource file name "story_c180.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameSkillParam2[17];                /* 0x007BEB75 conf 0.75: NUL-terminated resource file name "skill_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_L */
extern char g_resNameStoryC190[16];                  /* 0x007BEB86 conf 0.75: NUL-terminated resource file name "story_c190.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC210[16];                  /* 0x007BEB96 conf 0.75: NUL-terminated resource file name "story_c210.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC220[16];                  /* 0x007BEBA6 conf 0.75: NUL-terminated resource file name "story_c220.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC230[16];                  /* 0x007BEBB6 conf 0.75: NUL-terminated resource file name "story_c230.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC240[16];                  /* 0x007BEBC6 conf 0.75: NUL-terminated resource file name "story_c240.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameStoryC300[16];                  /* 0x007BEBD6 conf 0.75: NUL-terminated resource file name "story_c300.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameCharaFacialParam[24];           /* 0x007BEBE6 conf 0.75: NUL-terminated resource file name "chara_facial_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_L */
extern char g_resNameCharaMouseorderParam[28];       /* 0x007BEBFE conf 0.75: NUL-terminated resource file name "chara_mouseorder_param.bxon" handed to the resource manager (func_00124B24) by maybe_ */
extern char g_resNamePassiveSkill[19];               /* 0x007BEC1A conf 0.75: NUL-terminated resource file name "passive_skill.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout */
extern char g_resNamePictureCard[18];                /* 0x007BEC2D conf 0.75: NUL-terminated resource file name "picture_card.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_ */
extern char g_resNameUiText[13];                     /* 0x007BEC3F conf 0.75: NUL-terminated resource file name "ui_text.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_LoadA */
extern char g_resNameUiProfileText[21];              /* 0x007BEC4C conf 0.75: NUL-terminated resource file name "ui_profile_text.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layo */
extern char g_resNameTutorial[14];                   /* 0x007BEC61 conf 0.75: NUL-terminated resource file name "tutorial.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Load */
extern char g_resNameBattleActText[21];              /* 0x007BEC6F conf 0.75: NUL-terminated resource file name "battle_act_text.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layo */
extern char g_resNameCutsceneParam[20];              /* 0x007BEC84 conf 0.75: NUL-terminated resource file name "cutscene_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layou */
extern char g_resNameCutsceneChapterParam[28];       /* 0x007BEC98 conf 0.75: NUL-terminated resource file name "cutscene_chapter_param.bxon" handed to the resource manager (func_00124B24) by maybe_ */
extern char g_resNameCsChapterPlayerVisual[30];      /* 0x007BECB4 conf 0.75: NUL-terminated resource file name "cs_chapter_player_visual.bxon" handed to the resource manager (func_00124B24) by mayb */
extern char g_resNameAchievement[17];                /* 0x007BECD2 conf 0.75: NUL-terminated resource file name "achievement.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_L */
extern char g_resNamePlayerVisualParam[25];          /* 0x007BECE3 conf 0.75: NUL-terminated resource file name "player_visual_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_ */
extern char g_resNameLevelBGMParam[21];              /* 0x007BECFC conf 0.75: NUL-terminated resource file name "level_BGM_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layo */
extern char g_resNameLevelBGMGroupRef[25];           /* 0x007BED11 conf 0.75: NUL-terminated resource file name "level_BGM_group_ref.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_ */
extern char g_resNameRuraPoint[16];                  /* 0x007BED2A conf 0.75: NUL-terminated resource file name "rura_point.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameRiremitoPoint[20];              /* 0x007BED3A conf 0.75: NUL-terminated resource file name "riremito_point.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layou */
extern char g_resNameShipAnchoragePoint[26];         /* 0x007BED4E conf 0.75: NUL-terminated resource file name "ship_anchorage_point.bxon" handed to the resource manager (func_00124B24) by maybe_Ui */
extern char g_resNameRespawnPoint[19];               /* 0x007BED68 conf 0.75: NUL-terminated resource file name "respawn_point.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout */
extern char g_resNameCombinationParam[23];           /* 0x007BED7B conf 0.75: NUL-terminated resource file name "combination_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_La */
extern char g_resNameBattleZoneparam[22];            /* 0x007BED92 conf 0.75: NUL-terminated resource file name "battle_zoneparam.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Lay */
extern char g_resNameEffectPlaylist[21];             /* 0x007BEDA8 conf 0.75: NUL-terminated resource file name "effect_playlist.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layo */
extern char g_resNameEffect2dPlaylist[23];           /* 0x007BEDBD conf 0.75: NUL-terminated resource file name "effect2d_playlist.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_La */
extern char g_resNameSlotMachine[18];                /* 0x007BEDD4 conf 0.75: NUL-terminated resource file name "slot_machine.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_ */
extern char g_resNameRecipe[12];                     /* 0x007BEDE6 conf 0.75: NUL-terminated resource file name "recipe.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_LoadAn */
extern char g_resNameSmithPlayerParam[24];           /* 0x007BEDF2 conf 0.75: NUL-terminated resource file name "smith_player_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_L */
extern char g_resNameSmithArtParam[21];              /* 0x007BEE0A conf 0.75: NUL-terminated resource file name "smith_art_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layo */
extern char g_resNameRecipebook[16];                 /* 0x007BEE1F conf 0.75: NUL-terminated resource file name "recipebook.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_Lo */
extern char g_resNameJackpotParam[19];               /* 0x007BEE2F conf 0.75: NUL-terminated resource file name "jackpot_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout */
extern char g_resNameLevel2dmapEffectVisual[29];     /* 0x007BEE42 conf 0.75: NUL-terminated resource file name "level_2dmapEffectVisual.bxon" handed to the resource manager (func_00124B24) by maybe */
extern char g_resNameLevel2druinEffectVisual[30];    /* 0x007BEE5F conf 0.75: NUL-terminated resource file name "level_2druinEffectVisual.bxon" handed to the resource manager (func_00124B24) by mayb */
extern char g_resNameProfileProgressParam[28];       /* 0x007BEE7D conf 0.75: NUL-terminated resource file name "profile_progress_param.bxon" handed to the resource manager (func_00124B24) by maybe_ */
extern char g_resNameScenarioProgressParam[29];      /* 0x007BEE99 conf 0.75: NUL-terminated resource file name "scenario_progress_param.bxon" handed to the resource manager (func_00124B24) by maybe */
extern char g_resNameQuestParam[17];                 /* 0x007BEEB6 conf 0.75: NUL-terminated resource file name "quest_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layout_L */
extern char g_resNameQuestUiParam[20];               /* 0x007BEEC7 conf 0.75: NUL-terminated resource file name "quest_ui_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Layou */
extern char g_resNamePastAltarParam[22];             /* 0x007BEEDB conf 0.75: NUL-terminated resource file name "past_altar_param.bxon" handed to the resource manager (func_00124B24) by maybe_Ui_Lay */
extern char g_resNamePastWorldParam[22];             /* 0x007BEEF1 conf 0.85: Resource name of the 'past_world_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNa */
extern char g_resNamePresent[13];                    /* 0x007BEF07 conf 0.85: Resource name of the 'present.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) from  */
extern char g_resNameItemAddEffectText[26];          /* 0x007BEF14 conf 0.85: Resource name of the 'item_add_effect_text.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNamePlayerSpecialLearning[29];      /* 0x007BEF2E conf 0.85: Resource name of the 'player_special_learning.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceF */
extern char g_resNameSpiritHpRange[21];              /* 0x007BEF4B conf 0.85: Resource name of the 'spirit_hp_range.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNam */
extern char g_resNameSpiritWeaponCoeff[25];          /* 0x007BEF60 conf 0.85: Resource name of the 'spirit_weapon_coeff.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindB */
extern char g_resNameSpiritExceptAtkWeapon[30];      /* 0x007BEF79 conf 0.85: Resource name of the 'spirit_except_atk_weapon.bxon' data table, passed by name to the resource pack lookup (Fs_Resource */
extern char g_resNameSpiritPassCountBnsUpg[31];      /* 0x007BEF97 conf 0.85: Resource name of the 'spirit_pass_count_bns_upg.bxon' data table, passed by name to the resource pack lookup (Fs_Resourc */
extern char g_resNameSpiritNameTable[23];            /* 0x007BEFB6 conf 0.85: Resource name of the 'spirit_name_table.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameDiveProgressionCap[26];         /* 0x007BEFCD conf 0.85: Resource name of the 'dive_progression_cap.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameLayerItem[16];                  /* 0x007BEFE7 conf 0.85: Resource name of the 'layer_item.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameScenarioRestoreParam[28];       /* 0x007BEFF7 conf 0.85: Resource name of the 'scenario_restore_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFi */
extern char g_resNameSpecialRevivalSpell[27];        /* 0x007BF013 conf 0.85: Resource name of the 'special_revival_spell.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFin */
extern char g_resNamePasswordExpTable[24];           /* 0x007BF02E conf 0.85: Resource name of the 'password_exp_table.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameOldPasswordBonus[24];           /* 0x007BF046 conf 0.85: Resource name of the 'old_password_bonus.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameRevivalPointParam[25];          /* 0x007BF05E conf 0.85: Resource name of the 'revival_point_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindB */
extern char g_resNameScenarioGuide[20];              /* 0x007BF077 conf 0.85: Resource name of the 'scenario_guide.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName */
extern char g_resNameAnotherNameHero[23];            /* 0x007BF08B conf 0.85: Resource name of the 'another_name_hero.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameAnotherNameCamu[23];            /* 0x007BF0A2 conf 0.85: Resource name of the 'another_name_camu.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameAnotherNameVeronica[27];        /* 0x007BF0B9 conf 0.85: Resource name of the 'another_name_veronica.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFin */
extern char g_resNameAnotherNameSena[23];            /* 0x007BF0D4 conf 0.85: Resource name of the 'another_name_sena.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameAnotherNameSylvia[25];          /* 0x007BF0EB conf 0.85: Resource name of the 'another_name_sylvia.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindB */
extern char g_resNameAnotherNameRou[22];             /* 0x007BF104 conf 0.85: Resource name of the 'another_name_rou.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNa */
extern char g_resNameAnotherNameMartina[26];         /* 0x007BF11A conf 0.85: Resource name of the 'another_name_martina.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameAnotherNameGraig[24];           /* 0x007BF134 conf 0.85: Resource name of the 'another_name_graig.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameAnotherNameExSena[26];          /* 0x007BF14C conf 0.85: Resource name of the 'another_name_ex_sena.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameStoryA010[16];                  /* 0x007BF166 conf 0.85: Resource name of the 'story_a010.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA020[16];                  /* 0x007BF176 conf 0.85: Resource name of the 'story_a020.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA030[16];                  /* 0x007BF186 conf 0.85: Resource name of the 'story_a030.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA050[16];                  /* 0x007BF196 conf 0.85: Resource name of the 'story_a050.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA060[16];                  /* 0x007BF1A6 conf 0.85: Resource name of the 'story_a060.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA070[16];                  /* 0x007BF1B6 conf 0.85: Resource name of the 'story_a070.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA080[16];                  /* 0x007BF1C6 conf 0.85: Resource name of the 'story_a080.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA100[16];                  /* 0x007BF1D6 conf 0.85: Resource name of the 'story_a100.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA110[16];                  /* 0x007BF1E6 conf 0.85: Resource name of the 'story_a110.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA130[16];                  /* 0x007BF1F6 conf 0.85: Resource name of the 'story_a130.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA140[16];                  /* 0x007BF206 conf 0.85: Resource name of the 'story_a140.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA150[16];                  /* 0x007BF216 conf 0.85: Resource name of the 'story_a150.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA170[16];                  /* 0x007BF226 conf 0.85: Resource name of the 'story_a170.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryA180[16];                  /* 0x007BF236 conf 0.85: Resource name of the 'story_a180.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB010[16];                  /* 0x007BF246 conf 0.85: Resource name of the 'story_b010.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB020[16];                  /* 0x007BF256 conf 0.85: Resource name of the 'story_b020.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB030[16];                  /* 0x007BF266 conf 0.85: Resource name of the 'story_b030.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB040[16];                  /* 0x007BF276 conf 0.85: Resource name of the 'story_b040.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB060[16];                  /* 0x007BF286 conf 0.85: Resource name of the 'story_b060.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB070[16];                  /* 0x007BF296 conf 0.85: Resource name of the 'story_b070.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB080[16];                  /* 0x007BF2A6 conf 0.85: Resource name of the 'story_b080.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB090[16];                  /* 0x007BF2B6 conf 0.85: Resource name of the 'story_b090.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB100[16];                  /* 0x007BF2C6 conf 0.85: Resource name of the 'story_b100.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB110[16];                  /* 0x007BF2D6 conf 0.85: Resource name of the 'story_b110.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB120[16];                  /* 0x007BF2E6 conf 0.85: Resource name of the 'story_b120.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameStoryB150[16];                  /* 0x007BF2F6 conf 0.85: Resource name of the 'story_b150.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameShop[10];                       /* 0x007BF306 conf 0.85: Resource name of the 'shop.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) from may */
extern char g_resNameCoinshop[14];                   /* 0x007BF310 conf 0.85: Resource name of the 'coinshop.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) from */
extern char g_resNameCasinoPrize[18];                /* 0x007BF31E conf 0.85: Resource name of the 'casino_prize.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName)  */
extern char g_resNameMedalPrize[17];                 /* 0x007BF330 conf 0.85: Resource name of the 'medal_prize.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) f */
extern char g_resNameInn[9];                         /* 0x007BF341 conf 0.85: Resource name of the 'inn.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) from mayb */
extern char g_resNameLocationCsUi[20];               /* 0x007BF34A conf 0.85: Resource name of the 'location_cs_ui.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName */
extern char g_resNameBank[10];                       /* 0x007BF35E conf 0.85: Resource name of the 'bank.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) from may */
extern char g_resNameWorld2dAreaName[23];            /* 0x007BF368 conf 0.85: Resource name of the 'world2d_area_name.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameFukubiki[14];                   /* 0x007BF37F conf 0.85: Resource name of the 'fukubiki.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) from */
extern char g_resNameEnemyField[17];                 /* 0x007BF38D conf 0.85: Resource name of the 'enemy_field.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) f */
extern char g_resNameEnemyFieldCommon[24];           /* 0x007BF39E conf 0.85: Resource name of the 'enemy_field_common.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameBattleLocationLottery[29];      /* 0x007BF3B6 conf 0.85: Resource name of the 'battle_location_lottery.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceF */
extern char g_resNameEnemyDetection[21];             /* 0x007BF3D3 conf 0.85: Resource name of the 'enemy_detection.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNam */
extern char g_resNameMetalPartyParam[23];            /* 0x007BF3E8 conf 0.85: Resource name of the 'metal_party_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameSpPartyParam[20];               /* 0x007BF3FF conf 0.85: Resource name of the 'sp_party_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName */
extern char g_resNameQuestEnemyConvert[25];          /* 0x007BF413 conf 0.85: Resource name of the 'quest_enemy_convert.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindB */
extern char g_resNameFieldCameraParam[24];           /* 0x007BF42C conf 0.85: Resource name of the 'field_camera_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameFieldTimeZone[21];              /* 0x007BF444 conf 0.85: Resource name of the 'field_time_zone.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNam */
extern char g_resNameFieldGeography2dParam[29];      /* 0x007BF459 conf 0.85: Resource name of the 'field_geography2d_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceF */
extern char g_resNameWeatherSectionParam[27];        /* 0x007BF476 conf 0.85: Resource name of the 'weather_section_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFin */
extern char g_resNameTalkEmotionParam[24];           /* 0x007BF491 conf 0.85: Resource name of the 'talk_emotion_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameFieldLevelParam[23];            /* 0x007BF4A9 conf 0.85: Resource name of the 'field_level_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameField3dSeaEncount[26];          /* 0x007BF4C0 conf 0.85: Resource name of the 'field_3d_sea_encount.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameAreaDropParam[21];              /* 0x007BF4DA conf 0.85: Resource name of the 'area_drop_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNam */
extern char g_resNameAreaDropTable[21];              /* 0x007BF4EF conf 0.85: Resource name of the 'area_drop_table.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNam */
extern char g_resNameFixedDropParam[22];             /* 0x007BF504 conf 0.85: Resource name of the 'fixed_drop_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNa */
extern char g_resNameGlitterDropParam[24];           /* 0x007BF51A conf 0.85: Resource name of the 'glitter_drop_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameGlitterMaterialTable[28];       /* 0x007BF532 conf 0.85: Resource name of the 'glitter_material_table.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFi */
extern char g_resNameVehicleParam[19];               /* 0x007BF54E conf 0.85: Resource name of the 'vehicle_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) */
extern char g_resNameHorseraceRankParam[26];         /* 0x007BF561 conf 0.85: Resource name of the 'horserace_rank_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameHorseraceCalcParam[26];         /* 0x007BF57B conf 0.85: Resource name of the 'horserace_calc_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameMinigameCategoryParam[29];      /* 0x007BF595 conf 0.85: Resource name of the 'minigame_category_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceF */
extern char g_resNameSpiritLotteryTable[26];         /* 0x007BF5B2 conf 0.85: Resource name of the 'spirit_lottery_table.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameSpiritGeneratorTable[28];       /* 0x007BF5CC conf 0.85: Resource name of the 'spirit_generator_table.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFi */
extern char g_resNameSpiritTalkParam[23];            /* 0x007BF5E8 conf 0.85: Resource name of the 'spirit_talk_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameDummySpiritLotteryTable[32];    /* 0x007BF5FF conf 0.85: Resource name of the 'dummy_spirit_lottery_table.bxon' data table, passed by name to the resource pack lookup (Fs_Resour */
extern char g_resNameDummyPlayerProfile[26];         /* 0x007BF61F conf 0.85: Resource name of the 'dummy_player_profile.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameDummyPlayerName[23];            /* 0x007BF639 conf 0.85: Resource name of the 'dummy_player_name.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameDummyPlayerMessage[26];         /* 0x007BF650 conf 0.85: Resource name of the 'dummy_player_message.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameResGimmick3dBounds[26];         /* 0x007BF66A conf 0.85: Resource name of the 'res_gimmick3d_bounds.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameSpiritPasscountBonus[28];       /* 0x007BF684 conf 0.85: Resource name of the 'spirit_passcount_bonus.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFi */
extern char g_resNameDiveLayerMap[20];               /* 0x007BF6A0 conf 0.85: Resource name of the 'dive_layer_map.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName */
extern char g_resNameSpiritExclusionWeapon[29];      /* 0x007BF6B4 conf 0.85: Resource name of the 'spirit_exclusion_weapon.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceF */
extern char g_resNameBlendSpiritRarityUpPer[32];     /* 0x007BF6D1 conf 0.85: Resource name of the 'blend_spirit_rarity_up_per.bxon' data table, passed by name to the resource pack lookup (Fs_Resour */
extern char g_resNameBlendSpiritColorPercent[32];    /* 0x007BF6F1 conf 0.85: Resource name of the 'blend_spirit_color_percent.bxon' data table, passed by name to the resource pack lookup (Fs_Resour */
extern char g_resNameSpiritPresentParam[26];         /* 0x007BF711 conf 0.85: Resource name of the 'spirit_present_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameTrainingTrialParam[26];         /* 0x007BF72B conf 0.85: Resource name of the 'training_trial_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameNelsenBoss[17];                 /* 0x007BF745 conf 0.85: Resource name of the 'nelsen_boss.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) f */
extern char g_resNameTalkParty[16];                  /* 0x007BF756 conf 0.85: Resource name of the 'talk_party.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fr */
extern char g_resNameTalkContent[18];                /* 0x007BF766 conf 0.85: Resource name of the 'talk_content.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName)  */
extern char g_resNameTalkParty2dOverwrite[29];       /* 0x007BF778 conf 0.85: Resource name of the 'talk_party_2d_overwrite.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceF */
extern char g_resNameJackMapConvert[22];             /* 0x007BF795 conf 0.85: Resource name of the 'jack_map_convert.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNa */
extern char g_resNameJackAreaConvert[23];            /* 0x007BF7AB conf 0.85: Resource name of the 'jack_area_convert.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameTalkFlagEndConvert[27];         /* 0x007BF7C2 conf 0.85: Resource name of the 'talk_flag_end_convert.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFin */
extern char g_resNameEnemyBattleAction[24];          /* 0x007BF7DD conf 0.85: Resource name of the 'enemy_battleAction.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameEnemyActionArray[24];           /* 0x007BF7F5 conf 0.85: Resource name of the 'enemy_action_array.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNamePlayerBattle[19];               /* 0x007BF80D conf 0.85: Resource name of the 'player_battle.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) */
extern char g_resNameBattleHitstopParam[26];         /* 0x007BF820 conf 0.85: Resource name of the 'battle_hitstop_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFind */
extern char g_resNameBattle2dParam[21];              /* 0x007BF83A conf 0.85: Resource name of the 'battle_2d_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNam */
extern char g_resNameBattle2dsParam[22];             /* 0x007BF84F conf 0.85: Resource name of the 'battle_2ds_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNa */
extern char g_resNameSupportNPCAI[19];               /* 0x007BF865 conf 0.85: Resource name of the 'supportNPC_AI.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) */
extern char g_resNameEnemySpecialAttack[24];         /* 0x007BF878 conf 0.85: Resource name of the 'enemySpecialAttack.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameBattleExtraState[22];           /* 0x007BF890 conf 0.85: Resource name of the 'battleExtraState.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNa */
extern char g_resNamePlayerAI[15];                   /* 0x007BF8A6 conf 0.85: Resource name of the 'Player_AI.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) fro */
extern char g_resNameEnemyBattleSound[22];           /* 0x007BF8B5 conf 0.85: Resource name of the 'enemyBattleSound.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByNa */
extern char g_resNameBattle2dBgParam[24];            /* 0x007BF8CB conf 0.85: Resource name of the 'battle_2d_bg_param.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindBy */
extern char g_resNameBattle2dsAppendparam[28];       /* 0x007BF8E3 conf 0.85: Resource name of the 'battle_2ds_appendparam.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFi */
extern char g_resNameBattle2dsAppendreaction[31];    /* 0x007BF8FF conf 0.85: Resource name of the 'battle_2ds_appendreaction.bxon' data table, passed by name to the resource pack lookup (Fs_Resourc */
extern char g_resNameBattleMessage[20];              /* 0x007BF91E conf 0.85: Resource name of the 'battle_Message.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName */
extern char g_resNameBattleCommon[19];               /* 0x007BF932 conf 0.85: Resource name of the 'battle_common.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) */
extern char g_resNameBattleItem[17];                 /* 0x007BF945 conf 0.85: Resource name of the 'battle_item.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) f */
extern char g_resNameBattleItemAddtional[27];        /* 0x007BF956 conf 0.85: Resource name of the 'battle_item_addtional.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFin */
extern char g_resNameBattleZone[17];                 /* 0x007BF971 conf 0.85: Resource name of the 'battle_zone.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName) f */
extern char g_resNameSecondCheck[18];                /* 0x007BF982 conf 0.85: Resource name of the 'second_check.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByName)  */
extern char g_resNameBattleModelLoad[23];            /* 0x007BF994 conf 0.85: Resource name of the 'battle_model_load.bxon' data table, passed by name to the resource pack lookup (Fs_ResourceFindByN */
extern char g_resNameBattle2dBossanimParam[30];      /* 0x007BF9AB conf 0.85: Resource name of the 'battle_2d_bossanim_param.bxon' data table, passed by name to the resource pack lookup (Fs_Resource */
extern char g_paneNameWinTalkMessageWindowBindMessagePairs[9]; /* 0x007BF9CD conf 0.75: Layout pane/animation name 'win_talk' looked up in the loaded layout by Ui_MessageWindow_BindMessagePairs. */
extern char g_paneNameWinYesnoMessageWindowBindMessagePairs[10]; /* 0x007BF9D6 conf 0.75: Layout pane/animation name 'win_yesno' looked up in the loaded layout by Ui_MessageWindow_BindMessagePairs. */
extern u16 g_wideFmtLsNameArg[4];                    /* 0x007BF9E0 conf 0.80: Wide format L"%ls" used to set message argument 2 (party member name at member+0xCA) and argument 5 in Ui_Message_SetNam */
extern u16 g_wideFmtLsNameAndNumber[4];              /* 0x007BF9E8 conf 0.75: Wide format L"%ls" for the name argument of Ui_Message_SetNameAndNumberArgs. */
extern u16 g_wideFmtIdeographicSpace[2];             /* 0x007BF9F0 conf 0.70: Wide string holding a single ideographic space (U+3000), the separator between name and number in Ui_Message_SetNameAndN */
extern u16 g_wideFmtLsNameAndCode[4];                /* 0x007BF9F4 conf 0.75: Wide format L"%ls" for the name argument of Ui_Message_SetNameAndCodeArgs. */
extern u16 g_wideTextSpellName[4];                   /* 0x007BF9FC conf 0.70: Wide label text L"呪文名" ("spell name") used by Ui_Message_SetNameAndCodeArgs when it builds the spell description line. */
extern u16 g_wideFmtLsNameAndCount[4];               /* 0x007BFA08 conf 0.75: Wide format L"%ls" for the name argument of Ui_Message_SetNameAndCountArg. */
extern u16 g_wideFmtDNameAndCount[3];                /* 0x007BFA10 conf 0.70: Wide format L"%d" for the count argument of Ui_Message_SetNameAndCountArg. */
extern char g_paneNameIconNext[10];                  /* 0x007BFA74 conf 0.75: Layout pane/animation name 'icon_next' looked up in the loaded layout by Ui_MessageWindow_UpdateNextIcon. */
extern char g_paneNameMask0[7];                      /* 0x007BFA7E conf 0.75: Layout pane/animation name 'mask_0' looked up in the loaded layout by maybe_Ui_ChildTransform_CreateRowChildren. */
extern char g_paneNameWinTalkTalkWindowInitMessage[9]; /* 0x007BFA9A conf 0.75: Layout pane/animation name 'win_talk' looked up in the loaded layout by maybe_Ui_TalkWindow_InitMessage. */
extern char g_paneNameTxtLeft[9];                    /* 0x007BFABC conf 0.75: Layout pane/animation name 'txt_left' looked up in the loaded layout by Ui_MiniPlateWindow_InitPanes. */
extern char g_paneNamePlateMiniIn[14];               /* 0x007BFAC5 conf 0.75: Layout pane/animation name 'plate_mini_in' looked up in the loaded layout by Ui_MiniPlateWindow_InitPanes. */
extern char g_paneNamePlateMiniOut[15];              /* 0x007BFAD3 conf 0.75: Layout pane/animation name 'plate_mini_out' looked up in the loaded layout by Ui_MiniPlateWindow_InitPanes. */
extern char g_paneNameCoinLoop[10];                  /* 0x007BFAE2 conf 0.75: Layout pane/animation name 'coin_loop' looked up in the loaded layout by maybe_Ui_Widget_AdaptLayout. */
extern char g_paneNameEffectLoop[12];                /* 0x007BFAEC conf 0.75: Layout pane/animation name 'effect_loop' looked up in the loaded layout by maybe_Ui_Widget_AdaptLayout. */
extern char g_paneNameCoinget[8];                    /* 0x007BFAF8 conf 0.75: Layout pane/animation name 'coinget' looked up in the loaded layout by Ui_ScreenTransition_CreateLayers. */
extern char* g_uiWidgetLayerClipNames[4];            /* 0x007BFB00 conf 0.70: Four pointers to the clip names of the widget animation layers (first is 'bg_effect3_bg'); maybe_Ui_Widget_CreateChildLa */
extern u16 g_wideFmtDEquipmentDetail[3];             /* 0x007BFB3A conf 0.60: Wide format L"%d" used by maybe_Ui_EquipmentDetail_ScrollNameA when it formats the scrolled value. */
extern u16 g_wideFmtLsSpeaker[4];                    /* 0x007BFB72 conf 0.70: Wide format L"%ls" for the speaker-name argument of maybe_Ui_Message_SetSpeakerArgs. */
extern char g_paneNameEffect0[8];                    /* 0x007BFB88 conf 0.75: Layout pane/animation name 'effect0' looked up in the loaded layout by maybe_Ui_Text_ScanNumberedPanes. */
extern char g_paneNameSelect[7];                     /* 0x007BFB90 conf 0.75: Layout pane/animation name 'select' looked up in the loaded layout by Ui_MessageWindow_BindSelectAnims. */
extern char g_paneNameSelectIn[10];                  /* 0x007BFB97 conf 0.75: Layout pane/animation name 'select_in' looked up in the loaded layout by Ui_MessageWindow_BindSelectAnims. */
extern char g_paneNameSelectOut[11];                 /* 0x007BFBA1 conf 0.75: Layout pane/animation name 'select_out' looked up in the loaded layout by Ui_MessageWindow_BindSelectAnims. */
extern char g_paneNameNullSelect[12];                /* 0x007BFBAC conf 0.75: Layout pane/animation name 'null_select' looked up in the loaded layout by Ui_MessageWindow_BindSelectAnims. */
extern u16 g_wideFmtLsNameAndNumberB[4];             /* 0x007BFBC6 conf 0.65: Wide format L"%ls" used by maybe_Ui_Message_SetNameAndNumberArgs for arguments 2 and 3. */
extern u16 g_wideFmtDScreenLayout[3];                /* 0x007BFBD4 conf 0.60: Wide format L"%d" used by maybe_Ui_Screen_BindLayoutAnimation when it formats a layout index. */
extern char g_paneNameTxt2[6];                       /* 0x007BFBE8 conf 0.75: Layout pane/animation name 'txt_2' looked up in the loaded layout by maybe_Ui_Panel_UpdateStateA. */
extern char g_paneNameTxt4[6];                       /* 0x007BFBEE conf 0.75: Layout pane/animation name 'txt_4' looked up in the loaded layout by maybe_Ui_Panel_UpdateStateB. */
extern char g_paneNameTxt3[6];                       /* 0x007BFBF4 conf 0.75: Layout pane/animation name 'txt_3' looked up in the loaded layout by maybe_Ui_Panel_UpdateStateC. */
extern u16 g_wideFmtLsWindowLog[4];                  /* 0x007BFC46 conf 0.65: Wide format L"%ls" used by maybe_Ui_Window_LogMessageArgs for the name and value arguments. */
extern u16 g_wideFmtLsWindowLogText[4];              /* 0x007BFCE6 conf 0.60: Wide format L"%ls" used by maybe_Ui_Window_LogTextWithFormat. */
extern char g_paneNameG3085bOff[11];                 /* 0x007BFCEE conf 0.75: Layout pane/animation name 'g3085b_off' looked up in the loaded layout by maybe_Ui_TextListWidget_AttachPane. */
extern u16 g_wideFmtLsInteractRecordA[4];            /* 0x007BFD02 conf 0.60: Wide format L"%ls" used by maybe_Ui_InteractJob_LogRecordA to attach a record field as message argument 5. */
extern u16 g_wideFmtLsInteractRecordB[4];            /* 0x007BFD0A conf 0.60: Wide format L"%ls" used by maybe_Ui_InteractJob_LogRecordB (same shape as the A variant). */
extern u16 g_wideNewline;                            /* 0x007BFD12 conf 0.65: Wide string holding a single newline (U+000A), appended by maybe_Ui_LogFormat when it terminates a log line. */
extern char g_paneNameWinTalkMessagePageInit[9];     /* 0x007BFD18 conf 0.75: Layout pane/animation name 'win_talk' looked up in the loaded layout by Ui_MessagePage_Init. */
extern char g_paneNameWinYesnoMessagePageInit[10];   /* 0x007BFD21 conf 0.75: Layout pane/animation name 'win_yesno' looked up in the loaded layout by Ui_MessagePage_Init. */
extern u16 g_wideFmtLsWindowLogEntry[4];             /* 0x007BFD66 conf 0.60: Wide format L"%ls" used by maybe_Ui_Window_LogCurrentEntry for message argument 7. */
extern u16 g_wideFmtDPartyListStep[3];               /* 0x007BFD6E conf 0.60: Wide format L"%d" used by maybe_Ui_PartyListWindow_StepEntry when it formats a row value. */
extern u16 g_wideFmtDItemSlot[3];                    /* 0x007BFD74 conf 0.60: Wide format L"%d" used by maybe_Ui_ItemSlot_SetEntry when it formats the slot value. */
extern char g_paneNamePokerCardNumB0[22];            /* 0x007BFD7A conf 0.75: Layout pane/animation name 'poker_card_num_b_0' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. Mut */
extern char g_paneNamePokerCardNumG0[22];            /* 0x007BFD8D conf 0.75: Layout pane/animation name 'poker_card_num_g_0' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. Mut */
extern char g_paneNamePokerCardNumM0[22];            /* 0x007BFDA0 conf 0.75: Layout pane/animation name 'poker_card_num_m_0' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. Mut */
extern char g_paneNamePokerCardNumR0[22];            /* 0x007BFDB3 conf 0.75: Layout pane/animation name 'poker_card_num_r_0' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. Mut */
extern char g_paneNamePokerCardSlime[17];            /* 0x007BFDC6 conf 0.75: Layout pane/animation name 'poker_card_slime' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. */
extern char g_paneNamePokerCardSword[17];            /* 0x007BFDD7 conf 0.75: Layout pane/animation name 'poker_card_sword' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. */
extern char g_paneNamePokerCardShield[18];           /* 0x007BFDE8 conf 0.75: Layout pane/animation name 'poker_card_shield' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. */
extern char g_paneNamePokerCardCrown[17];            /* 0x007BFDFA conf 0.75: Layout pane/animation name 'poker_card_crown' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. */
extern char g_paneNamePokerCardBox0[16];             /* 0x007BFE0B conf 0.75: Layout pane/animation name 'poker_card_box0' looked up in the loaded layout by Ui_PokerWindow_ResolveCardObjects. Mutabl */
extern u16 maybe_g_wideFmtMultiplierTail;            /* 0x007BFE64 conf 0.40: First word of the wide string L"×%d" (multiplier display) - the literal slot points two bytes before the text, so this w */
extern u16 g_wideFmtMultiplier[4];                   /* 0x007BFE66 conf 0.70: Wide format L"×%d" (multiplication sign + number) used by maybe_Ui_ListWindow_FillThreeColumnRows for the multiplier col */
extern u16 g_wideFmtDThreeColumn[3];                 /* 0x007BFE6E conf 0.65: Wide format L"%d" used by maybe_Ui_ListWindow_FillThreeColumnRows for the numeric columns. */
extern u16 g_wideFmtLsLsDebugModel[7];               /* 0x007BFF8A conf 0.65: Wide format L"%ls%ls" used by maybe_Ui_DebugLabel_BuildModelText to join two strings (model and part name). */
extern u16 g_wideFmtLsDebugModel[4];                 /* 0x007BFF98 conf 0.60: Wide format L"%ls" used by maybe_Ui_DebugLabel_BuildModelText for message argument 2. */
extern u16 g_wideFmtDValueChange[3];                 /* 0x007BFFAE conf 0.60: Wide format L"%d" used by maybe_Ui_PartyMember_ShowValueChange when it formats the changed value. */
extern u16 g_wideFmtPlusDStat[4];                    /* 0x007C0166 conf 0.65: Wide format L"+%d" used by maybe_Ui_ListWindow_FillStatRows to show a positive stat delta. */
extern u16 maybe_g_wideFmtStatSeparatorTail;         /* 0x007C016E conf 0.40: First word of the wide string L"・%ls" (middle-dot separator + text) - the literal slot points two bytes before the text, */
extern u16 g_wideFmtDotLsTableRow[5];                /* 0x007C0170 conf 0.65: Wide format L"・%ls" (middle-dot separator followed by a string) used by maybe_Ui_ListWindow_SetTableRows to join row cel */
extern u16 maybe_g_wideTableRowBuffer;               /* 0x007C017A conf 0.40: Start of a static wide-character scratch buffer that maybe_Ui_ListWindow_SetTableRows fills with the formatted row text  */
extern char g_sqErrorCannotWakeIdleThread[29];       /* 0x007C20F0 conf 0.75: Squirrel VM error message 'cannot wakeup a idle thread', thrown through Script_Vm_ThrowError when a script wakes a threa */
extern char g_sqErrorCannotWakeRunningThread[32];    /* 0x007C210C conf 0.75: Squirrel VM error message 'cannot wakeup a running thread', thrown through Script_Vm_ThrowError. */
extern u16 g_wideFmtDRewardRow[4];                   /* 0x007C220E conf 0.60: Wide format L"%d" used by maybe_Ui_ListWindow_FillRewardRows for the reward count column. */
extern u16 g_wideFmtDRewardRowB[4];                  /* 0x007C2216 conf 0.60: Second wide L"%d" format of maybe_Ui_ListWindow_FillRewardRows (the reward id column). */
extern u16 maybe_g_wideRewardRowBuffer;              /* 0x007C221E conf 0.40: Start of the static wide scratch buffer that maybe_Ui_ListWindow_FillRewardRows formats reward rows into (zeroed in the  */
extern u16 maybe_g_wideRowHideBuffer;                /* 0x007C2220 conf 0.35: Start of the static wide scratch buffer used by Ui_ListWindow_HideUnusedRows when it blanks unused rows. */
extern u16 maybe_g_wideFmtPlusDPartyRowTail;         /* 0x007C2222 conf 0.40: First word of the wide string L"+%d" - the literal slot points two bytes before the text, so this word is the previous s */
extern u16 g_wideFmtPlusDItemList[4];                /* 0x007C2224 conf 0.60: Wide format L"+%d" used by maybe_Ui_ItemListWindow_BuildRowsFromItem for a positive item value. */
extern u16 g_wideFmtDItemList[3];                    /* 0x007C222C conf 0.60: Wide format L"%d" used by maybe_Ui_ItemListWindow_BuildRowsFromItem for the item count column. */
extern u16 g_wideFmtPlusDItemListB;                  /* 0x007C2232 conf 0.60: Second wide L"+%d" format of maybe_Ui_ItemListWindow_BuildRowsFromItem (the stat bonus column). */
extern u16 g_wideFmtPlusDItemRecord[4];              /* 0x007C2234 conf 0.60: Wide format L"+%d" used by maybe_Ui_ItemListWindow_BuildRowsFromRecord for a positive record value. */
extern u16 maybe_g_wideFmtItemRecordSeparatorTail;   /* 0x007C223C conf 0.40: First word of the wide string L"・%d" - the literal slot points two bytes before the text, so this word is the previous s */
extern u16 g_wideFmtDotDItemRecord[4];               /* 0x007C223E conf 0.60: Wide format L"・%d" (middle-dot separator + number) used by maybe_Ui_ItemListWindow_BuildRowsFromRecord. */
extern u16 g_wideFmtPlusDScrollList;                 /* 0x007C2282 conf 0.55: Wide format L"+%d" used by maybe_Ui_ScrollListWindow_Ctor when it seeds a row value. */
extern u16 g_wideFmtPlusDExtraRow[4];                /* 0x007C2284 conf 0.60: Wide format L"+%d" used by maybe_Ui_ListWindow_FillExtraRows for the extra row value. */
extern u16 maybe_g_wideFmtExtraRowTail;              /* 0x007C228C conf 0.35: First word of the wide string L"sp%s" - the literal slot points two bytes before the text, so this word is the previous  */
extern char g_dataTableNameFieldCollision[16];       /* 0x007C22E6 conf 0.70: Name of the 'field_collision' data table, passed to maybe_Game_GetDataManager by Ui_ListData_AppendMetalPartyRows. */
extern char maybe_g_dataTableNameFieldCollisionAlt[15]; /* 0x007C22E7 conf 0.40: Second literal pointing one byte into the same 'field_collision' table name (the slot value is 0x007C22E7, so the text r */
extern u32 maybe_g_uiSortWidgetsTempPointer;         /* 0x007C2300 conf 0.40: Scratch pointer of maybe_Ui_SortWidgetsByLayer: the sort loop keeps its current widget here between iterations. */
extern u8 maybe_g_uiSortWidgetsInitGuard;            /* 0x007C2304 conf 0.45: One-shot constructor guard byte for the widget sort helper: bit 0 set means the static list was already initialised (fun */
extern u32 maybe_g_uiSortWidgetsListHead;            /* 0x007C2308 conf 0.40: Head pointer of the static widget list sorted by maybe_Ui_SortWidgetsByLayer; zero until the first sort. */
extern char g_resPathUiItemBch[15];                  /* 0x007C2310 conf 0.80: Resource path format 'ui/item/%s.bch' used by Ui_ItemModel_Load to build the item model path from an item name. */
extern char g_resNameMainItem3dUp[28];               /* 0x007C2352 conf 0.60: Name of the 'mainitem_3d_up.bflyt' layout resource used by Ui_BattleSpellWindow_Refresh and Ui_Entry_GetDisplayText; the */
extern char maybe_g_resNameMainItem3dUpAlt[26];      /* 0x007C2354 conf 0.40: Second literal pointing four bytes before the same 'mainitem_3d_up.bflyt' name; used by Ui_Message_GetSpellDescription. */
extern char maybe_g_resNameMainItem3dUpAltB[24];     /* 0x007C2356 conf 0.40: Third literal pointing two bytes before the same 'mainitem_3d_up.bflyt' name; used by Ui_Message_GetItemDescription. */
extern char g_resNameDiveDungeonDamage3dUp[27];      /* 0x007C26B2 conf 0.60: Name of the 'dive_dngn_damage_3d_up.bflyt' layout resource loaded by Ui_DungeonDamage_LoadLayout; the literal slot point */
extern u8 g_entryTable8Byte;                         /* 0x007C33E8 conf 0.55: Base of a fixed table of 8-byte entries in BSS; maybe_Ui_GetTableEntry returns base + index*8 after running the one-shot */
extern u32 maybe_g_uiWindowDescriptorObject;         /* 0x007C34FC conf 0.45: Static object that Ui_RegisterStaticObject_7A35A0 registers and maybe_Ui_Window_BuildDescriptor fills; the window descri */
extern u32 g_diveObjectActor3DClass;                 /* 0x007C3574 conf 0.55: Static class/registry node of the 'Dive_ObjectActor3D' field actor, registered by Field_RegisterActorClass_Dive_ObjectAc */
extern u32 g_spiritMenuActor3DClass;                 /* 0x007C3670 conf 0.55: Static class/registry node of the 'SpiritMenuActor3D' field actor; also used by Model_Attach_CreateWeaponAttachment and  */
extern u32 g_uiNizuzerufaArmTextWidgets[11];         /* 0x007C42B4 conf 0.60: Two 0x14-byte Ui_TextWidget objects (at +0 and +0x14) that Ui_InitColorPalette_7A3744 constructs for the Nizuzerufa left */
extern u32 maybe_g_uiEquipmentWindowStatic;          /* 0x007C43B0 conf 0.40: Static object shared by the equipment window, the gimmick fixed-item test and the overlay cursor-row query. */
extern u32 maybe_g_uiOverlayCursorRowState;          /* 0x007C448C conf 0.35: Static state word of the overlay cursor-row helper (maybe_Ui_Overlay_GetCursorRowState). */
extern u32 maybe_g_uiColorPaletteObject[6];          /* 0x007C4540 conf 0.45: 24-byte static object initialised by Ui_InitColorPalette_7A97F8 and registered by Ui_RegisterStaticObject_7A3818; also t */
extern u32 g_gmGetOffGondola2DClass;                 /* 0x007C45A4 conf 0.55: Static class/registry node of the 'GmGetOffGondola2D' field actor, registered by Field_RegisterActorClass_GmGetOffGondol */
extern u32 maybe_g_uiStaticObject7A3860;             /* 0x007C45F4 conf 0.35: Static object registered by Ui_RegisterStaticObject_7A3860; its role is not resolved beyond the registration. */
extern u32 maybe_g_uiStaticObject7A38C4;             /* 0x007C4644 conf 0.35: Static object registered by Ui_RegisterStaticObject_7A38C4; its role is not resolved beyond the registration. */
extern u32 g_straySpirit2DClass;                     /* 0x007C4680 conf 0.55: Static class/registry node of the default 'StraySpirit2D' field actor, also used when the scene creates its draw object. */
extern u32 maybe_g_straySpirit2DClassB;              /* 0x007C4694 conf 0.40: Second static node of the 'StraySpirit2D' actor family (the shared scene-init variant). */
extern u32 maybe_g_uiMapIconLocatorTarget;           /* 0x007C46D0 conf 0.35: Static target/context object of Ui_MapIcon_BindLocatorTarget. */
extern u32 maybe_g_uiActorOverlayStatic;             /* 0x007C46F8 conf 0.40: Static object shared by the region-book lookup, a UI static registration and the actor overlay position calculation. */
extern u32 maybe_g_uiStaticObject7A3918;             /* 0x007C4720 conf 0.35: Static object registered by Ui_RegisterStaticObject_7A3918; role not resolved. */
extern u32 g_gmGondola2DClass;                       /* 0x007C475C conf 0.60: Class descriptor of the 'GmGondola2D' field actor: Field_RegisterActorClass_GmGondola2D registers it and Ui_MapIcon_Bind */
extern u32 maybe_g_gondola2DClass;                   /* 0x007C4770 conf 0.45: Second static node of the 'GmGondola2D' actor (the 'Gondora' sprite entry), used by maybe_Ui_SpriteActor_CreateEntry. */
extern u32 g_gmShip2DClass;                          /* 0x007C47AC conf 0.60: Class descriptor of the 'GmShip2D' field actor; Ui_MapIcon_ProvideShipIconAlt compares actors against it before creating */
extern u32 maybe_g_uiStaticObject7A3978;             /* 0x007C47C0 conf 0.35: Static object registered by Ui_RegisterStaticObject_7A3978; role not resolved. */
extern u32 g_gmWhale2DClass;                         /* 0x007C4824 conf 0.55: Static class/registry node of the 'GmWhale2D' field actor. */
extern u32 maybe_g_uiEquipmentWindowStaticB;         /* 0x007C4874 conf 0.40: Second static object of the equipment window / overlay cursor-row group (companion of 0x007C43B0). */
extern u32 maybe_g_uiMapIconShipTransform;           /* 0x007C49A0 conf 0.35: Static transform state used by Ui_MapIcon_UpdateShipIconTransform. */
extern u32 maybe_g_uiOverlayCursorRowStateB;         /* 0x007C49C8 conf 0.35: Second static state word of maybe_Ui_Overlay_GetCursorRowState. */
extern u32 g_gmD011BookShelf3DClass;                 /* 0x007C4BA8 conf 0.55: Static class/registry node of the 'GmD011BookShelf3DActor' field actor; maybe_Ui_ModePane_UpdateVisibility walks sibling */
extern u32 maybe_g_uiMapIconHighlight;               /* 0x007C4BF8 conf 0.40: Static state of the map-icon highlight pulse, also read by the model-slot emitter and the list-widget screen dispatch. */
extern u32 maybe_g_uiOverlaySlotSetup;               /* 0x007C4C48 conf 0.35: Static slot-setup record used by maybe_Ui_Overlay_ApplySlotSetup. */
extern u32 g_uiComponentClass;                       /* 0x007C4C5C conf 0.55: Class descriptor of a UI component: maybe_Ui_Component_FindAndNotify finds the object of this class behind the scene nod */
extern u32 g_quickItemGet3DClass;                    /* 0x007C4CFC conf 0.55: Static class/registry node of the 'QuickItemGet3DActor' field actor, shared with two UI static registrations. */
extern u32 maybe_g_uiPartStatic;                     /* 0x007C4D10 conf 0.40: Static object shared by Ui_RegisterStaticObject_7A3B28 and maybe_Ui_Part_CreateChildPartEx. */
extern u32 g_gmShip2DRotatedClass;                   /* 0x007C4E00 conf 0.60: Class descriptor of the rotated 'GmShip2D' icon variant; Ui_MapIcon_ProvideShipIconRotated compares actors against it be */
extern u32 g_playerActor3DClass;                     /* 0x007C4E50 conf 0.55: Class descriptor of the player 3D field actor, used by the actor handle resolver and the draw-equipment pass (16 users). */
extern u32 maybe_g_uiLabelCharPairStatic;            /* 0x007C4E64 conf 0.35: Static object used by maybe_Ui_Label_SetFromCharPairC when it builds a label from a character pair. */
extern u32 maybe_g_uiLabelShortTripleStatic;         /* 0x007C4F3C conf 0.35: Static object used by maybe_Ui_Label_SetFromShortTriple when it builds a label from three shorts. */
extern u32 maybe_g_actorAttachStatic;                /* 0x007C5028 conf 0.40: Static object shared by the draw-equipment pass, the attach-target lookup and the party status setter (13 users). */
extern u32 maybe_g_actorHandleRegistry;              /* 0x007C503C conf 0.45: Static registry used by the field-actor handle resolver and the NPC player-id lookup (32 users); the handle table itself */
extern u32 maybe_g_uiEquipTextWindowStatic;          /* 0x007C5064 conf 0.40: Static object shared by Ui_EquipTextWindow_SetCharacter and Ui_RegisterStaticObject_7A3FFC. */
extern u32 maybe_g_uiFaceIconStatic;                 /* 0x007C5078 conf 0.40: Static object shared by a UI static registration, the hash-bucket type lookup and the face-icon on/off setter. */
extern u32 g_smithProductActor3DClass;               /* 0x007C508C conf 0.55: Static class/registry node of the 'SmithProductActor3D' field actor; also read by the message-glyph text object. */
extern u32 g_smithStandActor3DClass;                 /* 0x007C50A0 conf 0.55: Static class/registry node of the 'SmithStandActor3D' field actor; also read by the window sub-object finder. */
extern u32 maybe_g_uiObjectListSlotOrder;            /* 0x007C5308 conf 0.35: Static slot-order state of the UI object list (maybe_Ui_ObjectList_UpdateSlotOrder). */
extern u32 maybe_g_uiSharedStatic;                   /* 0x007C53D0 conf 0.40: Static object created on demand by maybe_Ui_EnsureSharedStatic_006A0CD4 and then written through the returned pointer. */
extern char g_uiDungeonDamageNameBuffer[256];        /* 0x007C53DC conf 0.60: 256-byte buffer that Ui_DungeonDamage_LoadLayout clears with func_001113EC(...,0x100) and then fills with the layout nam */
extern char g_uiSpellDescriptionBuffer[256];         /* 0x007C5844 conf 0.60: 256-byte buffer that Ui_Message_GetSpellDescription clears and fills with the formatted spell description. */
extern char g_uiItemDescriptionBuffer[256];          /* 0x007C5944 conf 0.60: 256-byte buffer that Ui_Message_GetItemDescription clears and fills with the formatted item description. */
extern u32 g_uiResourceCache;                        /* 0x007C6E58 conf 0.60: UI resource cache object: maybe_Ui_ResourceCache_GetOrCreate creates it through func_0053623C and inserts entries with U */
extern u32 g_textFormatContext;                      /* 0x007C6F04 conf 0.50: Static text-formatting context (13 users): Text_InitStaticLayout initialises it and Text_SetFormatArgsFromPlayerData fil */
extern u32 maybe_g_textControlState;                 /* 0x007C6F0A conf 0.45: Static control state of the text renderer, reset with func_00111384(g, 0xc, 0xff) by the control-handler dispatcher. */
extern u16 g_uiPlateDescriptorBuffer;                /* 0x007C7ED0 conf 0.50: Wide-character buffer that maybe_Ui_Plate_FormatFullDescriptor fills with std_wcsncpy when it builds the plate descripto */
extern f32 g_uiMessageWindowTextBounds[4];           /* 0x007C7F30 conf 0.55: Four floats holding the text-area bounds of the message window; Ui_MessageWindow_ClampTextPosition compares the text pos */
extern u16 maybe_g_uiItemRowFormatBuffer;            /* 0x007C7F40 conf 0.40: Wide scratch buffer that maybe_Ui_ItemRow_Format writes the formatted item row into. */
extern f32 g_uiSenrekiMonsterCameraPos[3];           /* 0x007C7FCC conf 0.55: Camera position (three floats) used by Ui_SenrekiMonsterList_SetupCamera when it frames the monster list. */
extern f32 g_uiJackpotCameraPosA[3];                 /* 0x007C7FD8 conf 0.55: First of two camera positions (three floats) that maybe_Ui_JackpotCamera_UpdateTrack interpolates towards. */
extern f32 g_uiJackpotCameraPosB[3];                 /* 0x007C7FE4 conf 0.55: Second camera position (three floats) of the jackpot camera track. */
extern f32 maybe_g_ui3DBackgroundViewMatrix[6];      /* 0x007C8020 conf 0.45: Six floats of the 3D background view setup (eye/target pair) read by maybe_Ui_3DBackground_SetupView. */
extern u32 maybe_g_modelResourceCache;               /* 0x007C8584 conf 0.45: Static model-resource cache used by the model loader and the battle unit-model binding (34 users). */
extern u32 maybe_g_uiSceneFlowSlotObject;            /* 0x007C8620 conf 0.40: Static slot object of the UI scene flow, also used by the world-map model loader and a hash-map name lookup. */
extern u32 maybe_g_uiSceneFlowSlotResources;         /* 0x007C8638 conf 0.40: Static resource set of the UI scene flow slot, also read by the packed-table reader initialiser. */
extern u32 g_uiIconCacheBusyFlag;                    /* 0x007C9980 conf 0.55: Flag word of the icon-cache worker: set to 1 while the worker loads icons and back to 0 when it finishes (17 users). */
extern u32 maybe_g_uiIconCacheWorkerParam;           /* 0x007CC418 conf 0.35: Parameter block handed to the icon-cache worker thread by Ui_IconCache_WorkerThread. */
extern u32 maybe_g_uiIconCacheWorkerEntry;           /* 0x007CCEA0 conf 0.35: Entry record that Ui_IconCache_WorkerThread writes through maybe_Ui_IconCache_WriteEntry. */
extern u32 g_uiIconCacheCriticalSection;             /* 0x007CF2A0 conf 0.55: Critical section that protects the icon cache: Os_InitCriticalSection initialises it and the worker/loader lock it. */
extern u32 maybe_g_uiIconCacheThread;                /* 0x007CF2AC conf 0.40: Thread handle of the icon-cache loader, created and joined by Ui_LoadIconTextures. */
extern u32 maybe_g_uiIconCacheThreadParam;           /* 0x007CF2D0 conf 0.40: Parameter block of the icon-cache loader thread; its second word is cleared after the thread starts. */
extern u32 maybe_g_modelClassRegistry;               /* 0x007E2018 conf 0.40: Static class registry used by the object-by-class-and-name search, the character shadow pass and the model child counter */
extern f32 g_uiArcListRowSwingPose[2];               /* 0x007E7004 conf 0.50: Two floats of the swing pose that Ui_ArcListRow_UpdateSwingPose applies to the arc list row. */
extern u32 maybe_g_gfxSceneStatic[6];                /* 0x007E71EC conf 0.40: 24-byte static block shared by the glyph cache, the sprite-from-resource creator and the bounds builder (20 users). */
extern u32 maybe_g_mathWorkArea[10];                 /* 0x007E721C conf 0.40: 40-byte static work area used by the glyph cache, the sprite creator and the OBB computation (38 users). */
extern u32 g_resourcePackTypeInfo;                   /* 0x007E7250 conf 0.55: Type descriptor compared against the resource object's vtable[0] result in Ui_Layout_LoadAndBind_Type1 before the pack i */
extern u32 g_uiIconCacheMonitor;                     /* 0x007E7948 conf 0.55: Monitor object that serialises icon-cache service creation/release (Os_LockMonitor/Os_UnlockMonitor). */
extern u32 g_uiIconCacheOpenMonitor;                 /* 0x007E7954 conf 0.50: Monitor object that serialises opening and closing the icon cache. */
extern u32 g_uiIconAtlasMonitor;                     /* 0x007E7960 conf 0.50: Monitor object that serialises icon-atlas access (close, entry-header read, cache close). */
extern u32 maybe_g_uiIconCacheReadyMonitor;          /* 0x007E796C conf 0.45: Monitor object used by maybe_Ui_IconCache_IsContentReady when it checks whether the icon content is loaded. */
extern u32 maybe_g_uiGlyphQuadArray;                 /* 0x007E80E0 conf 0.40: Static quad array that Ui_GlyphQuadArray_AppendQuads appends glyph quads to. */
extern u32 g_uiTextConsoleInstance;                  /* 0x007E84B0 conf 0.60: Singleton pointer returned by maybe_Ui_TextConsole_GetInstance (the on-screen text console). */
extern u32 g_uiTextSystemInstance2;                  /* 0x007E8640 conf 0.55: Singleton pointer returned by maybe_Ui_TextSystem_GetInstance2 (second text-system accessor). */
extern u32 maybe_g_uiTextDrawState;                  /* 0x007E8664 conf 0.35: Static draw state read by Ui_Text_DrawGlyphRun before it emits a glyph run. */
extern u32 g_uiTextScrollerInstance;                 /* 0x007ECCA0 conf 0.60: Singleton pointer returned by maybe_Ui_TextScroller_GetInstance (the scrolling-text helper). */
extern u32 g_uiTextSystemInstance;                   /* 0x007ECD8C conf 0.60: Singleton pointer returned by maybe_Ui_TextSystem_GetInstance (the main text system). */
extern u32 g_uiAtlasContextMonitor;                  /* 0x007EF144 conf 0.50: Monitor object that serialises acquisition of the atlas context (also used by the refcount release path). */
extern u32 maybe_g_gfxOverlayState;                  /* 0x007F3024 conf 0.40: Static overlay state shared by the cutscene layout mode, the sprite overlay draw and the movie frame getter (8 users). */
extern u8 maybe_g_engineGlobalBlockA[19];            /* 0x007F305C conf 0.30: 19-byte static block in the engine global area, read by 122 call sites including the battle unit-model animation update  */
extern u8 maybe_g_engineGlobalBlockB[19];            /* 0x007F4F1C conf 0.30: 19-byte static block in the engine global area used by engine start-up and shutdown (42 call sites); fields not resolved */
extern u32 maybe_g_uiListWindowCommonResources;      /* 0x007F52A8 conf 0.45: Static resource set of the 0x1F8-byte list window: initialised by maybe_Ui_InitCommonResources, used by the constructor  */
extern u8 maybe_g_engineGlobalBlockC[19];            /* 0x007F52B8 conf 0.30: 19-byte static block in the engine global area read by 122 call sites including the battle popup and the UI transition s */
extern u8 g_partySaveWorkStorage[0xE3C8];            /* 0x007F52E4 conf 0.70: Static BSS backing store for the 0xE3C8-byte party/save work container; the object itself starts at the next 16-byte bou */
extern u8 g_gameDataManagerStorage[0xA24];           /* 0x008036BC conf 0.80: Static BSS backing store for the 0xA24-byte GameData/DataManager singleton (object at 0x008036C0); accessor Game_GetData */
extern u8 g_gameWorkStorage[0x2FB28];                /* 0x00804160 conf 0.80: Static BSS backing store for the 0x2FB28-byte GameWork singleton (object at 0x00804160, already 16-aligned); accessor Ga */
extern u8 g_uiSubsystemWork[0x80];                   /* 0x00833C98 conf 0.55: Static BSS backing store for the UI subsystem's 0x80-byte state object (object at 0x00833CA0; flag 0x007BE324, holder *0 */
extern u8 g_fsCacheSetStorage[0x21C];                /* 0x00833D28 conf 0.75: Static BSS backing store for the 0x21C-byte FsCacheSet singleton (object at 0x00833D30; flag 0x007BE32C, holder *0x007BE */
extern u8 g_uiCoreStorage[0x98];                     /* 0x00833F78 conf 0.75: Static BSS backing store for the 0x98-byte UiCore singleton (object at 0x00833F80; accessor Ui_GetCore 0x006F229C, flag  */
extern u8 g_inputPadStateStorage[0x1D4];             /* 0x00836F24 conf 0.80: Static BSS backing store for the 0x1D4-byte input pad-state singleton (object at 0x00836F30; accessor Input_GetPadState  */
extern u8 g_gfxContextStorage[0x1348];               /* 0x00837148 conf 0.75: Static BSS backing store for the 0x1348-byte GfxContext singleton (object at 0x00837150; accessor Gfx_GetContext 0x006F2 */

/* --- X80 --- */
extern f32 maybe_g_fieldHorseMinSpeed;               /* 0x007A6E74 conf 0.55: Lower speed clamp / reverse speed limit float for horse/mount field movement actions; read by horse movement step (0x003 */

/* --- std --- */
extern u32 g_crc32Table[256];                        /* 0x0072EB3C conf 0.95: Standard IEEE 802.3 (reflected, polynomial 0xEDB88320) CRC-32 lookup table: 256 u32 entries, 1024 bytes. std_Crc32_InitT */
extern char g_moLiveAllocatorOutOfMemoryMessage[63]; /* 0x00735154 conf 0.85: Allocator out-of-memory report text: "MoLive::Allocator: not enough memory to allocate %d bytes !!!\n" (62 characters pl */
extern void* g_formatStringTag128;                   /* 0x00781FA0 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorA (0x006F */
extern void* g_formatStringTag12;                    /* 0x00781FB0 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorB (0x006F */
extern void* g_formatStringTag14;                    /* 0x00781FC0 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtor14 (0x006 */
extern void* g_formatStringTag16;                    /* 0x00781FD0 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorC (0x006F */
extern void* g_formatStringTag17;                    /* 0x00781FE0 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtor17 (0x006 */
extern void* g_formatStringTag20;                    /* 0x00781FF0 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorD (0x006F */
extern void* g_formatStringTag24;                    /* 0x00782000 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorE (0x006F */
extern void* g_formatStringTag32;                    /* 0x00782010 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorF (0x006F */
extern void* g_formatStringTag48;                    /* 0x00782020 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorG (0x006F */
extern void* g_formatStringTag4;                     /* 0x00782030 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorH (0x006F */
extern void* g_formatStringTag64;                    /* 0x00782040 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorI (0x006F */
extern void* g_formatStringTag8;                     /* 0x00782050 conf 0.50: Class word stored at offset 0 of the narrow (char) format-string temporary built by maybe_std_String_FormatCtorJ (0x006F */
extern void* g_wideFormatStringTag10;                /* 0x007820A0 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorA (0x00 */
extern void* g_wideFormatStringTag128;               /* 0x007820B0 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorB (0x00 */
extern void* g_wideFormatStringTag16;                /* 0x007820C0 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorC (0x00 */
extern void* g_wideFormatStringTag2;                 /* 0x007820D0 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorD (0x00 */
extern void* g_wideFormatStringTag3;                 /* 0x007820F0 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtor3 (0x00 */
extern void* g_wideFormatStringTag4;                 /* 0x00782100 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorF (0x00 */
extern void* g_wideFormatStringTag64;                /* 0x00782110 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorG (0x00 */
extern void* g_wideFormatStringTag6;                 /* 0x00782120 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorH (0x00 */
extern void* g_wideFormatStringTag8;                 /* 0x00782130 conf 0.50: Class word stored at offset 0 of the wide (wchar_t) format-string temporary built by maybe_std_WString_FormatCtorI (0x00 */
extern s32 g_itemBagCategoryOrder[31];               /* 0x007C6E7C conf 0.80: Display order of the 31 item bag categories: g_itemBagCategoryOrder[category] is the slot index the bag UI shows that ca */

#endif /* DQXI_DQXI_GLOBALS_H */
