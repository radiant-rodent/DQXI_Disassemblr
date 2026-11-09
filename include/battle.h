#ifndef DQXI_BATTLE_H
#define DQXI_BATTLE_H

#pragma once

#include "types.h"

#define MAX_PARTY_MEMBERS       4
#define MAX_ENEMY_MEMBERS       8
#define MAX_BATTLE_ACTORS       (MAX_PARTY_MEMBERS + MAX_ENEMY_MEMBERS)
#define MAX_ACTIONS_PER_TURN    MAX_BATTLE_ACTORS

/* Battle State Machine States */
typedef enum BattleState {
    BATTLE_STATE_UNINITIALIZED    = 0,
    BATTLE_STATE_ENCOUNTER_INTRO  = 1,
    BATTLE_STATE_COMMAND_INPUT    = 2,
    BATTLE_STATE_CALCULATE_ORDER  = 3,
    BATTLE_STATE_EXECUTE_ACTION   = 4,
    BATTLE_STATE_CHECK_OUTCOME    = 5,
    BATTLE_STATE_VICTORY_REWARD   = 6,
    BATTLE_STATE_DEFEAT           = 7,
    BATTLE_STATE_FINISHED         = 8
} BattleState;

/* Battle Action Types */
typedef enum BattleActionType {
    ACTION_NONE         = 0,
    ACTION_PHYSICAL     = 1,
    ACTION_SPELL        = 2,
    ACTION_SKILL        = 3,
    ACTION_ITEM         = 4,
    ACTION_DEFEND       = 5,
    ACTION_PEP_POWER    = 6,
    ACTION_ESCAPE       = 7
} BattleActionType;

/* Status Effect Flags */
typedef enum StatusFlags {
    STATUS_NORMAL       = 0,
    STATUS_POISON       = BIT(0),
    STATUS_CURSE        = BIT(1),
    STATUS_SLEEP        = BIT(2),
    STATUS_PARALYSIS    = BIT(3),
    STATUS_CONFUSION    = BIT(4),
    STATUS_DEAD         = BIT(5)
} StatusFlags;

/* Battle Actor Definition */
typedef struct BattleActor {
    u16         actor_id;
    u16         monster_id;
    char        name[32];
    s32         hp;
    s32         max_hp;
    s32         mp;
    s32         max_mp;
    s32         attack;
    s32         defense;
    s32         agility;
    u32         status_flags;
    bool        is_enemy;
    bool        is_pepped_up;
    bool        has_acted;
} BattleActor;

/* Battle Action Command */
typedef struct BattleAction {
    BattleActionType action_type;
    u16              skill_or_spell_id;
    u8               user_index;
    u8               target_index;
    s32              damage;
    bool             is_critical;
    bool             is_success;
} BattleAction;

/* 64-byte Scenario Battle Record matching gamecmn.pack:scenario_battle.bxon */
typedef struct ScenarioBattleParam {
    u32 monster_array_count;
    u32 monster_array_relptr;
    u32 secondary_array_count;
    u32 secondary_array_relptr;
    u32 tertiary_array_count;
    u32 tertiary_array_relptr;
    u32 quat_array_count;
    u32 quat_array_relptr;
    u16 battle_zone;
    u16 flags;
    u8  reserved[28];
} ScenarioBattleParam;

/* Main Battle Execution Context */
typedef struct BattleContext {
    BattleState         state;
    u32                 turn_number;
    u8                  party_count;
    u8                  enemy_count;
    u8                  active_actor_count;
    u16                 zone_id;
    u16                 scenario_id;
    BattleActor         actors[MAX_BATTLE_ACTORS];
    u8                  turn_order[MAX_BATTLE_ACTORS];
    u8                  current_turn_step;
    BattleAction        current_action;
    u32                 total_exp_reward;
    u32                 total_gold_reward;
} BattleContext;

/* Core Battle Subsystem Functions */
void Battle_InitContext(BattleContext *ctx, u16 scenario_id, u16 zone_id);
void Battle_AddPartyMember(BattleContext *ctx, const BattleActor *actor);
void Battle_AddEnemy(BattleContext *ctx, const BattleActor *enemy);
void Battle_Update(BattleContext *ctx);
void Battle_DetermineTurnOrder(BattleContext *ctx);
s32  Battle_CalculateDamage(const BattleActor *attacker, const BattleActor *defender, const BattleAction *action);
bool Battle_DispatchAction(BattleContext *ctx, BattleAction *action);
bool Battle_IsPartyWiped(const BattleContext *ctx);
bool Battle_AreEnemiesDefeated(const BattleContext *ctx);

#endif /* DQXI_BATTLE_H */
