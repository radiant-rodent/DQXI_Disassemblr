/**
 * src/battle/damage.c - Dragon Quest XI Damage Formulas
 *
 * Implements standard Dragon Quest XI CTR damage calculations:
 * - Physical Base Damage: (Attack / 2) - (Defense / 4)
 * - Critical Hit: Ignores enemy defense, applies full attack scaling.
 * - Spells & Skills: Magic potency scaling and Pep Power state multipliers.
 */

#include "dqxi.h"
#include "battle.h"

s32 Battle_CalculateDamage(const BattleActor *attacker, const BattleActor *defender, const BattleAction *action) {
    if (!attacker || !defender || !action) return 0;

    s32 base_damage = 0;

    switch (action->action_type) {
        case ACTION_PHYSICAL: {
            if (action->is_critical) {
                /* Critical hit: Ignores defense */
                base_damage = attacker->attack;
                if (base_damage < 1) base_damage = 1;
            } else {
                /* Standard DQ physical formula: (Atk / 2) - (Def / 4) */
                s32 atk_half = attacker->attack / 2;
                s32 def_quarter = defender->defense / 4;
                base_damage = atk_half - def_quarter;
                if (base_damage < 1) base_damage = 1;
            }
            break;
        }

        case ACTION_SPELL: {
            /* Frizz / Sizz / Bang standard base damage with Magic Might */
            s32 spell_power = 20 + (action->skill_or_spell_id * 15);
            base_damage = spell_power;
            break;
        }

        case ACTION_SKILL: {
            /* Falcon Slash / Miracle Sword / Gigaslash scaling */
            s32 skill_mult = 12; /* 1.2x baseline */
            base_damage = ((attacker->attack / 2) - (defender->defense / 4)) * skill_mult / 10;
            if (base_damage < 1) base_damage = 1;
            break;
        }

        case ACTION_PEP_POWER: {
            /* Pep Power composite strike: Massive damage ignoring 50% defense */
            base_damage = (attacker->attack - (defender->defense / 8));
            if (base_damage < 1) base_damage = 1;
            break;
        }

        case ACTION_DEFEND:
        case ACTION_NONE:
        default:
            return 0;
    }

    /* Pepped up bonus (1.2x damage multiplier) */
    if (attacker->is_pepped_up) {
        base_damage = (base_damage * 12) / 10;
    }

    return base_damage;
}
