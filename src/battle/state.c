/**
 * src/battle/state.c - Dragon Quest XI Battle State Machine
 *
 * Implements battle lifecycle management, scenario encounter loading,
 * and state transitions (Intro -> Input -> Order -> Execution -> Victory/Defeat).
 */

#include "dqxi.h"
#include "battle.h"

void Battle_InitContext(BattleContext *ctx, u16 scenario_id, u16 zone_id) {
    if (!ctx) return;

    ctx->state = BATTLE_STATE_ENCOUNTER_INTRO;
    ctx->turn_number = 1;
    ctx->party_count = 0;
    ctx->enemy_count = 0;
    ctx->active_actor_count = 0;
    ctx->zone_id = zone_id;
    ctx->scenario_id = scenario_id;
    ctx->current_turn_step = 0;
    ctx->total_exp_reward = 0;
    ctx->total_gold_reward = 0;

    for (int i = 0; i < MAX_BATTLE_ACTORS; i++) {
        ctx->turn_order[i] = (u8)i;
    }
}

void Battle_AddPartyMember(BattleContext *ctx, const BattleActor *actor) {
    if (!ctx || !actor || ctx->party_count >= MAX_PARTY_MEMBERS) return;

    u8 idx = ctx->party_count;
    ctx->actors[idx] = *actor;
    ctx->actors[idx].is_enemy = false;
    ctx->party_count++;
    ctx->active_actor_count++;
}

void Battle_AddEnemy(BattleContext *ctx, const BattleActor *enemy) {
    if (!ctx || !enemy || ctx->enemy_count >= MAX_ENEMY_MEMBERS) return;

    u8 idx = MAX_PARTY_MEMBERS + ctx->enemy_count;
    ctx->actors[idx] = *enemy;
    ctx->actors[idx].is_enemy = true;
    ctx->enemy_count++;
    ctx->active_actor_count++;

    /* Accumulate battle rewards */
    ctx->total_exp_reward += 25 * (enemy->monster_id + 1);
    ctx->total_gold_reward += 10 * (enemy->monster_id + 1);
}

bool Battle_IsPartyWiped(const BattleContext *ctx) {
    if (!ctx || ctx->party_count == 0) return true;

    for (u8 i = 0; i < ctx->party_count; i++) {
        if (ctx->actors[i].hp > 0 && !(ctx->actors[i].status_flags & STATUS_DEAD)) {
            return false;
        }
    }
    return true;
}

bool Battle_AreEnemiesDefeated(const BattleContext *ctx) {
    if (!ctx || ctx->enemy_count == 0) return true;

    for (u8 i = 0; i < ctx->enemy_count; i++) {
        u8 idx = MAX_PARTY_MEMBERS + i;
        if (ctx->actors[idx].hp > 0 && !(ctx->actors[idx].status_flags & STATUS_DEAD)) {
            return false;
        }
    }
    return true;
}

void Battle_Update(BattleContext *ctx) {
    if (!ctx) return;

    switch (ctx->state) {
        case BATTLE_STATE_ENCOUNTER_INTRO:
            /* Transition to command input after intro banner display */
            ctx->state = BATTLE_STATE_COMMAND_INPUT;
            break;

        case BATTLE_STATE_COMMAND_INPUT:
            /* Awaiting player command selection for all active party members */
            break;

        case BATTLE_STATE_CALCULATE_ORDER:
            Battle_DetermineTurnOrder(ctx);
            ctx->current_turn_step = 0;
            ctx->state = BATTLE_STATE_EXECUTE_ACTION;
            break;

        case BATTLE_STATE_EXECUTE_ACTION:
            if (Battle_AreEnemiesDefeated(ctx)) {
                ctx->state = BATTLE_STATE_VICTORY_REWARD;
            } else if (Battle_IsPartyWiped(ctx)) {
                ctx->state = BATTLE_STATE_DEFEAT;
            } else if (ctx->current_turn_step >= ctx->active_actor_count) {
                /* End of round, advance turn counter */
                ctx->turn_number++;
                ctx->state = BATTLE_STATE_COMMAND_INPUT;
            }
            break;

        case BATTLE_STATE_VICTORY_REWARD:
            /* Award EXP, Gold, and items */
            ctx->state = BATTLE_STATE_FINISHED;
            break;

        case BATTLE_STATE_DEFEAT:
            /* Game over / Church respawn */
            ctx->state = BATTLE_STATE_FINISHED;
            break;

        case BATTLE_STATE_FINISHED:
        default:
            break;
    }
}
