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
extern void* g_animInstanceTemplate[18];             /* 0x00725458 conf 0.60: Default Anim_Instance parameter/callback block: six (code pointer, 0) pairs followed by zeroed slots. maybe_Anim_Instanc */
extern u32 g_motionPackIdLimitByKind[6];             /* 0x0072D754 conf 0.70: Exclusive upper bound on the motion sub-id accepted for each animation kind 0..5 in Anim_FormatMotionPackPath; the funct */
extern void* g_animSequenceVtable[6];                /* 0x0075A79C conf 0.70: Primary vtable installed by Anim_Sequence_CtorBase on the 184-byte Anim_Sequence keyed-timeline object. Its six slots ar */
extern void* maybe_g_animInstanceRefVtable[7];       /* 0x0075AB34 conf 0.45: Dispatch table installed on the anim-ref member that Anim_Instance_CtorSprite builds at offset +0x3C of a sprite instanc */
extern void* maybe_g_modelInstanceVtable[16];        /* 0x0075CC90 conf 0.40: Table stored as the first word of the 64-byte object Anim_ModelLoad_ByName allocates for a loaded model ('%s.ani' + '%s. */
extern void* maybe_g_animSequenceManagerVtable[5];   /* 0x0075D3E8 conf 0.40: Five-word table whose second word is 0x28AF58, four bytes before Anim_SequenceManager_DestroyAndFree (0x28AF5C); maybe_A */
extern void* maybe_g_gfxBillboardObjectVtable[16];   /* 0x0075D434 conf 0.45: Base-object vtable installed by maybe_Anim_ObjectBaseCtor (Gfx_ObjectDesc_Ctor4 plus three initialised words); the Anim_ */
extern void* g_uiListWindowVtableSecondary[14];      /* 0x0075E360 conf 0.70: Secondary vtable of Ui_ListWindow (structs.json lists 0x0075E360 among its vtables): slot 0 is Ui_ListWindow_Dtor (0x002 */
extern void* g_animInstanceVtable[16];               /* 0x00760568 conf 0.65: Primary vtable of Anim_Instance: installed by maybe_Anim_Instance_Dtor (and the matching constructor path). Slot 0 is th */
extern void* g_animOwnerVtable[14];                  /* 0x00760578 conf 0.55: Vtable installed on the sprite-instance base object returned by func_002D9744 in Anim_Instance_CtorSprite. Slot 1 is the */
extern void* g_animClipSlotArcVtable[14];            /* 0x007615A4 conf 0.65: Vtable for the arc-motion Anim_ClipSlot variant, installed by maybe_Anim_ClipSlot_SetEight (which also sets the 8-entry  */
extern void* g_animClipSlotBaseVtable[13];           /* 0x0076160C conf 0.60: Vtable for the plain two-entry Anim_ClipSlot variant, installed by maybe_Anim_ClipSlot_SetTwo. Slot 1 is maybe_Anim_Clip */
extern void* g_fieldActionMoveVtable[16];            /* 0x007628EC conf 0.60: Vtable of the field move action: Anim_SetBeeJumpParams creates this task on top of maybe_Field_ActorMove_CreateTask and  */
extern void* g_fieldActionStepVtable[16];            /* 0x00762920 conf 0.70: Vtable of the Field_Action_Step action (footstep player): slot 1 is Field_Action_Step_DeletingDtor, followed by StopMove */
extern void* g_fieldActionNutVtable[16];             /* 0x007629E4 conf 0.65: Vtable of the 'nut' field action: slot 1 is maybe_Field_Action_Nut_DeletingDtor, then StartNut, UpdateAnim and UpdateNut */
extern void* g_fieldActionAttachNamedEffectVtable[16]; /* 0x00762A50 conf 0.70: Vtable of the Field_Action_AttachNamedEffect action: slot 1 is its deleting destructor, then AttachNamedEffect and Reset */
extern void* g_fieldActionHorseInputVtable[15];      /* 0x00762AB8 conf 0.65: Vtable of the horse-input action (player steering while mounted): slot 1 is maybe_Field_Action_HorseInput_DeletingDtor,  */
extern void* g_fieldActionRunVtable[15];             /* 0x00762AFC conf 0.60: Vtable of the running field action: slot 1 is an unnamed destructor (0x00302C8C), then ToggleRun, StopMoveEffect, Update */
extern void* g_fieldActionHorseStartVtable[16];      /* 0x00762B40 conf 0.65: Vtable of the horse-start action: slot 1 is Field_Action_HorseStart_DeletingDtor, then HorseStart, HorseStart_End and Ho */
extern void* g_fieldActionMoveStepVtable[15];        /* 0x00762B74 conf 0.65: Vtable of the move-step action (walking/footstep movement): slot 1 is maybe_Field_Action_MoveStep_DeletingDtor, then Mov */
extern void* maybe_g_runActionUiBlock[15];           /* 0x00775338 conf 0.40: Block stored into field +0x50 of the run action by maybe_Anim_CreateVariantD. Its words from +0x18 look like a Ui_Window */
extern void* g_animAnimClipVtable[12];               /* 0x007815D8 conf 0.70: Primary vtable of Anim_AnimClip (48-byte animation clip object), installed by Anim_AnimClip_Ctor. Slot 0 is the complete */
extern char g_motionSuffixInit[16];                  /* 0x00782564 conf 0.55: 16-byte all-zero block used to initialise the motion-number suffix buffer in Anim_FormatMotionPackPath: the function cop */
extern void* maybe_g_resourceTypeDescriptor[11];     /* 0x00782574 conf 0.45: Shared type/registry descriptor: Fs_ResourceFindByName loads it as the extra argument of its resource lookup, maybe_Math */
extern void* g_animNodeTypeHandlers[34];             /* 0x007A2D60 conf 0.60: Function-pointer dispatch table indexed by the animation-node type (u16 at node->f_34[8]); Anim_UpdateAttachTrack and An */
extern char* g_effectTrackName;                      /* 0x007A5CFC conf 0.70: Pointer to the string 'Effectpath', the name of the effect animation track. Anim_SetupNamedTrackList looks the track up  */
extern void* g_animClipSpriteBuilder;                /* 0x007A6888 conf 0.50: Optional builder hook called by Anim_Clip_Start / maybe_Anim_Clip_SpawnAndApply to turn a clip's float parameters into a */
extern u32 g_modelInstanceSlotCursor;                /* 0x007B6D70 conf 0.60: Rotating index (masked to 0..0x1FF) into the 0x200-entry model-instance slot table at g_004d2a8c. Anim_ModelLoad_ByName  */
extern u32 g_modelInstanceIdCounter;                 /* 0x007B6D74 conf 0.60: Rotating 22-bit id counter (mod 0x3FFFFF) for named model/animation instances. Anim_ModelLoad_ByName increments it, shif */

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
extern u32 maybe_g_battleUnitDisplayRange[2];        /* 0x007A5AD8 conf 0.40: Two-word value read by maybe_Battle_UpdateUnitDisplay as a pointer (g_002da1f0) and a 64-bit quantity (g_002da1f4) — pro */
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

/* --- BattleEndToDefaultField --- */
extern f32 maybe_g_battleEndFieldFadeValue;          /* 0x00728AA0 conf 0.40: Float 1.0 in rodata read by BattleEndToDefaultField into local_1c (a fade/time value passed while switching back to the  */

/* --- Bg2D --- */
extern u8 g_bg2dLayerPageSearchOrder[8];             /* 0x007275DC conf 0.70: Search order for the four Bg2D layer texture pages (2x u8[4]): bytes 4..7 are each layer's first-choice page id (3,0,1,2 */

/* --- Camera --- */
extern u32 maybe_g_rodata_272A4;                     /* 0x007272A4 conf 0.30: Pointer to camera visible target lists table; contains addresses of visible candidate arrays. */
extern u32 maybe_g_rodata_272A8;                     /* 0x007272A8 conf 0.30: Pointer table for camera target list validation; used in Camera_IsCandidateVisible checks. */
extern u32 maybe_g_rodata_731C8;                     /* 0x007731C8 conf 0.20: Zero-initialized placeholder for anim track camera data structure. */
extern u32 maybe_g_rodata_7B190;                     /* 0x0077B190 conf 0.20: Zero-initialized placeholder for second anim track camera data structure. */
extern u32 maybe_g_rodata_7D85C;                     /* 0x0077D85C conf 0.40: Pointer to regular camera shake configuration data. */
extern u32 g_cameraManualYaw;                        /* 0x007A6050 conf 0.80: Manual camera yaw value (4.2.16 fixed-point); used for overriding automatic camera rotation. */
extern u32 maybe_g_bss_6058;                         /* 0x007A6058 conf 0.30: BSS variable for camera collision resolution temporary data. */
extern u8 maybe_g_bss_605C;                          /* 0x007A605C conf 0.30: BSS camera collision flag or temporary byte. */
extern u32 maybe_g_bss_6060;                         /* 0x007A6060 conf 0.30: BSS camera collision temporary pointer. */
extern u32 maybe_g_bss_6064;                         /* 0x007A6064 conf 0.30: BSS camera collision temporary pointer. */
extern u32 maybe_g_bss_6068;                         /* 0x007A6068 conf 0.30: BSS camera update temporary pointer. */
extern u8 maybe_g_bss_606C;                          /* 0x007A606C conf 0.30: BSS camera update temporary flag byte. */
extern u8 maybe_g_bss_6070;                          /* 0x007A6070 conf 0.30: BSS camera update temporary flag byte. */
extern u8 maybe_g_bss_6074;                          /* 0x007A6074 conf 0.30: BSS camera update temporary control byte. */
extern u32 maybe_g_bss_6078;                         /* 0x007A6078 conf 0.30: BSS camera setup temporary pointer. */
extern u8 maybe_g_bss_6148;                          /* 0x007A6148 conf 0.30: BSS camera orbit initialization parameter. */
extern u32 maybe_g_bss_6184;                         /* 0x007A6184 conf 0.30: BSS camera stereo smoothing temporary variable. */
extern u8 maybe_g_bss_63E1;                          /* 0x007A63E1 conf 0.30: BSS camera work path exclude flag. */
extern u32 maybe_g_bss_63E4;                         /* 0x007A63E4 conf 0.30: BSS camera work path function callback. */
extern u32 g_cameraVisibleTargetList;                /* 0x007A6428 conf 0.90: Main camera visible target list pointer; used by all camera visibility functions. */
extern u32 g_cameraWorkPathEntry;                    /* 0x007A64B0 conf 0.80: Camera work path entry structure pointer; used for updating work list entries. */
extern u32 g_cameraDistanceScaleTable;               /* 0x007A8B80 conf 0.80: Camera distance scale table; used for computing distance-based scaling effects. */
extern u8 g_cameraDistanceScaleTableEntry0;          /* 0x007A8B81 conf 0.70: Camera distance scale table entry at index 0. */
extern u8 g_cameraDistanceScaleTableEntry1;          /* 0x007A8B8C conf 0.70: Camera distance scale table entry at index 1. */
extern u8 g_cameraDistanceScaleTableEntry2;          /* 0x007A8B90 conf 0.70: Camera distance scale table entry at index 2. */
extern u8 g_cameraDistanceScaleTableEntry3;          /* 0x007A8B9C conf 0.70: Camera distance scale table entry at index 3. */
extern u8 g_cameraDistanceScaleTableEntry4;          /* 0x007A8BA0 conf 0.70: Camera distance scale table entry at index 4. */
extern u32 g_cameraTransitionTarget0;                /* 0x007C51C0 conf 0.80: BSS camera transition target data at index 0; stores temporary camera transition state. */
extern u32 g_cameraTransitionTarget1;                /* 0x007C51CC conf 0.80: BSS camera transition target data at index 1; stores temporary camera transition state. */
extern u32 g_cameraTransitionTarget2;                /* 0x007C51D8 conf 0.80: BSS camera transition target data at index 2; stores temporary camera transition state. */
extern u32 g_cameraStereoEyePositions[0xC];          /* 0x007C51F0 conf 0.90: BSS camera stereo eye positions array (12 floats); stores left/right eye positions for 3D. */
extern u32 g_cameraFieldUpdate[0xC];                 /* 0x007C5208 conf 0.80: BSS camera field update array (12 floats); stores field-of-view or camera plane data. */
extern u32 g_cameraWorkPathEx[0xC];                  /* 0x007C522C conf 0.80: BSS camera work path extra array (12 floats); stores additional camera work path data. */

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
extern void* g_handleListObjectTable;                /* 0x0072863C conf 0.55: Pointer to the handle-list descriptor table read by HandleList and Ui_Smith functions; initial value points to code at 0 */
extern void* maybe_g_intrusiveListBase;              /* 0x00729B80 conf 0.45: Base pointer installed by maybe_Container_IntrusiveList_Ctor; initial value points to code at 0x004486E4. */
extern void* maybe_g_listInitBase;                   /* 0x0072B3AC conf 0.35: Zero-initialised pointer used by maybe_Container_List_InitAt5C; likely a list-base pointer set at runtime. */
extern void* g_objectCreateDescriptor;               /* 0x0075A6C8 conf 0.50: Pointer installed by maybe_Container_CreateObject; points to an object descriptor at code address 0x0062FF94. */
extern void* g_stringMapBase;                        /* 0x0075A6F4 conf 0.50: String-map base pointer installed by maybe_Container_StringMap_Ctor; points to code at 0x001E8888. */
extern void* maybe_g_arrayCtorTable;                 /* 0x0075BB68 conf 0.35: Zero-initialised pointer shared by array constructor and screen destructor; likely an array descriptor or null sentinel. */
extern void* g_intrusiveListDescriptor;              /* 0x0075E274 conf 0.50: Descriptor pointer for intrusive list constructor; points to code at 0x0029D5F8. */
extern void* g_intrusiveListDtorBase;                /* 0x0075E90C conf 0.50: Base pointer for intrusive list destructor; points to code at 0x002ABC14. */
extern void* g_list3DtorTable;                       /* 0x0075E9A4 conf 0.50: Pointer installed by list-3 destructor; points to code at 0x002ADC20. */
extern void* g_list15DtorTable;                      /* 0x0075E9B4 conf 0.50: Pointer for 15-element list destructor; points to code at 0x002AF880. */
extern void* maybe_g_initListPairTable;              /* 0x00760550 conf 0.35: Zero-initialised pointer used by list-pair initialiser; probably a pair descriptor set at runtime. */
extern void* maybe_g_nameHashInitTable;              /* 0x007610D4 conf 0.45: Pointer used by name-hash constructor; zero-initialised in image, likely a hash descriptor. */
extern void* g_nameHashCtorBTable;                   /* 0x0076111C conf 0.50: Name-hash constructor B pointer shared with object destructor; points to code at 0x002E4C20. */
extern void* g_dtorWithArraysDescriptor;             /* 0x00762E34 conf 0.50: Descriptor pointer for destructor with arrays; points to code at 0x0030BF90. */
extern void* maybe_g_nodeDtorTable;                  /* 0x0076334C conf 0.40: Zero-initialised pointer shared by node destructor variants and UI object destructor; likely a shared node-deletion desc */
extern void* maybe_g_nodeListInitDescriptor;         /* 0x0076BA90 conf 0.40: Descriptor pointer for node list initialisation; zero in image, set at runtime by initializer. */
extern void* g_stringMapDescriptor;                  /* 0x0076E1B0 conf 0.50: String-map descriptor pointer; points to code at 0x0064D448. */
extern void* maybe_g_handleListCtorDescriptor;       /* 0x0076FF14 conf 0.45: Descriptor for handle list constructor; zero-initialised, installed at runtime. */
extern void* maybe_g_intrusiveListCtorDescriptor;    /* 0x007702FC conf 0.45: Descriptor pointer for intrusive-list constructor; points to code at 0x00448888. */
extern void* maybe_g_nodeListInitDescriptor2;        /* 0x00771ECC conf 0.40: Secondary node-list initialisation descriptor; zero in image, set at runtime. */
extern void* maybe_g_nodeListInitDescriptor3;        /* 0x00771F00 conf 0.35: Another node-list initialisation descriptor variant; zero in image. */
extern void* maybe_g_nodeListInitDescriptor4;        /* 0x00771F38 conf 0.35: Fourth node-list init descriptor; zero-initialised. */
extern void* maybe_g_nodeListInitDescriptor5;        /* 0x00773EB4 conf 0.35: Fifth node-list init descriptor; zero in image. */
extern void* maybe_g_nodeListInitDescriptor6;        /* 0x00773EEC conf 0.35: Sixth node-list init descriptor; zero-initialised. */
extern void* maybe_g_nodeListInitDescriptor7;        /* 0x00775980 conf 0.35: Seventh node-list init descriptor; zero in image. */
extern void* g_nameHandleCtorDescriptor;             /* 0x007759C8 conf 0.50: Descriptor for name-handle constructor; points to code at 0x004A7C3C. */
extern void* g_initListPairDescriptor2;              /* 0x00776D84 conf 0.50: Secondary list-pair descriptor; points to code at 0x004B65F4. */
extern void* maybe_g_listNodeCtorDescriptor;         /* 0x00778F00 conf 0.45: Descriptor for list-node constructor; zero in image, installed at runtime. */
extern void* maybe_g_handleListCtorDescriptor2;      /* 0x00780AC0 conf 0.45: Secondary handle-list constructor descriptor; zero-initialised. */
extern void* g_handleListCtorDescriptor3;            /* 0x00780AD8 conf 0.50: Another handle-list constructor descriptor; points to code at 0x00444CF0. */
extern void* g_objectDtorDescriptor;                 /* 0x007810E8 conf 0.50: Descriptor for container object destructor; points to code at 0x00101A9F. */
extern void* g_initListObjectDescriptor;             /* 0x00782080 conf 0.55: Descriptor for initialising list objects; shared with Gfx overlay batch start; points to code at 0x0055AD04. */
extern void* maybe_g_createObjectDescriptor2;        /* 0x00782210 conf 0.40: Secondary create-object descriptor; zero-initialised, set at runtime by object creation. */
extern void* g_listInitDescriptor;                   /* 0x007826D8 conf 0.55: List initialisation descriptor shared with graphics scene node base destructor; points to code at 0x00576B00. */
extern void* g_sceneNodeDtorDescriptor;              /* 0x00782704 conf 0.55: Descriptor for scene-node body destructor and alternate list init; points to code at 0x005777AC. */
extern void* g_namedMapLookupTable;                  /* 0x00782750 conf 0.60: Pointer used extensively by named-map lookup/insert/find and hash-table insert; points to code at 0x00106898 and 0x00108 */
extern void* maybe_g_sortListWindowDescriptor;       /* 0x00782E98 conf 0.45: Descriptor for sort-list-window destructor and intrusive-list constructor variant; zero in image. */
extern void* g_namedObjectRegistryTable;             /* 0x007A30B8 conf 0.50: Table pointer for named-object registry creation in .data section; zero-initialised. */
extern u8 g_objectDestroyTable[0x14];                /* 0x007AEABC conf 0.50: 20-byte array descriptor used by container object destruction; points to registry entry at 0x00147B04. */
extern void* maybe_g_initListDescriptor;             /* 0x007AED40 conf 0.45: Pointer for list initialisation and GPU texture-stage sync; zero in image, set at runtime. */
extern void* maybe_g_namedObjectRegistryBase;        /* 0x007C331C conf 0.45: Base pointer in BSS for named-object registry; zero at boot, set by registry creation. */
extern u32 g_uniqueIdPoolTable[0xC];                 /* 0x007C859C conf 0.55: 12-word (48-byte) array table in BSS used by unique-ID addition, font glyph pools, resource list attach, and global list */
extern void* g_tagTypeLookupTable;                   /* 0x007C85F0 conf 0.55: Pointer table in BSS used by container entry lookup by tag and type, cutscene actor resource resolution, font bitmap poo */

/* --- Cutscene --- */
extern u32 g_cutsceneSceneVtable[7];                 /* 0x00766E7C conf 0.90: Vtable of the Cutscene_Scene class: slot 0 creates the actor models, slots 1-5 are the scene's layout/script helpers and */
extern u8 maybe_g_cutsceneToggleFlag;                /* 0x007A2CFC conf 0.40: One-byte latch toggled between 0 and 1 by Cutscene_AdvanceTimeline while action bit 0x1000 is set in the input snapshot  */
extern u32 g_cutSceneActorClassRecord[5];            /* 0x007C34C0 conf 0.85: Named class record for the 'CutSceneActor' actor type: three intrusive list words (+0x0..+0x8), a parent-class pointer ( */
extern u32 g_cutScenePlayerActorClassRecord[5];      /* 0x007C34D4 conf 0.85: Named class record for the 'CutScenePlayerActor' type, the player-controlled actor in a cutscene: parent pointer +0xC =  */
extern u32 maybe_g_listPanelClassRecord[6];          /* 0x007C8608 conf 0.45: Static class record for the four-row list-panel window class (vtable 0x00762FEC): +0xC parent descriptor 0x007E2000, +0x */

#endif /* DQXI_DQXI_GLOBALS_H */
