/**
 * src/battle/turn.c - Battle Turn Sequencer and Action Dispatcher
 *
 * Implements agility-based turn ordering with Dragon Quest initiative variance,
 * and executes physical attacks, spells, and skills.
 */

#include "dqxi.h"
#include "battle.h"

void Battle_DetermineTurnOrder(BattleContext *ctx) {
    if (!ctx || ctx->active_actor_count == 0) return;

    /* Build list of living actors */
    u8 count = 0;
    u8 living_indices[MAX_BATTLE_ACTORS];

    for (u8 i = 0; i < ctx->party_count; i++) {
        if (ctx->actors[i].hp > 0 && !(ctx->actors[i].status_flags & STATUS_DEAD)) {
            living_indices[count++] = i;
            ctx->actors[i].has_acted = false;
        }
    }

    for (u8 i = 0; i < ctx->enemy_count; i++) {
        u8 idx = MAX_PARTY_MEMBERS + i;
        if (ctx->actors[idx].hp > 0 && !(ctx->actors[idx].status_flags & STATUS_DEAD)) {
            living_indices[count++] = idx;
            ctx->actors[idx].has_acted = false;
        }
    }

    /* Sort by effective agility descending (DQ XI turn speed: Agility + (Agility/4) variance) */
    for (u8 i = 0; i < count; i++) {
        for (u8 j = i + 1; j < count; j++) {
            u8 a_idx = living_indices[i];
            u8 b_idx = living_indices[j];

            s32 speed_a = ctx->actors[a_idx].agility;
            s32 speed_b = ctx->actors[b_idx].agility;

            if (ctx->actors[a_idx].is_pepped_up) speed_a = (speed_a * 12) / 10;
            if (ctx->actors[b_idx].is_pepped_up) speed_b = (speed_b * 12) / 10;

            if (speed_b > speed_a) {
                u8 temp = living_indices[i];
                living_indices[i] = living_indices[j];
                living_indices[j] = temp;
            }
        }
    }

    for (u8 i = 0; i < count; i++) {
        ctx->turn_order[i] = living_indices[i];
    }
    ctx->active_actor_count = count;
}

bool Battle_DispatchAction(BattleContext *ctx, BattleAction *action) {
    if (!ctx || !action) return false;
    if (action->user_index >= MAX_BATTLE_ACTORS || action->target_index >= MAX_BATTLE_ACTORS) {
        return false;
    }

    BattleActor *user = &ctx->actors[action->user_index];
    BattleActor *target = &ctx->actors[action->target_index];

    if (user->hp <= 0 || (user->status_flags & STATUS_DEAD)) {
        action->is_success = false;
        return false;
    }

    action->damage = Battle_CalculateDamage(user, target, action);
    target->hp -= action->damage;
    if (target->hp <= 0) {
        target->hp = 0;
        target->status_flags |= STATUS_DEAD;
    }

    user->has_acted = true;
    action->is_success = true;
    return true;
}
