/**
 * src/field/trigger.c - Field Triggers and Zone Transitions
 *
 * Implements interactive map triggers (treasure chests, doors, NPC dialog, campfires)
 * and seamless zone transitions.
 */

#include "dqxi.h"
#include "field.h"

FieldTrigger *Field_CheckTriggers(FieldManager *mgr, const Vec3f *hero_pos) {
    if (!mgr || !hero_pos) return NULL;

    for (u32 i = 0; i < mgr->trigger_count; i++) {
        FieldTrigger *trig = &mgr->triggers[i];
        if (!trig->is_active) continue;

        const MapCollisionAABB *b = &trig->bounds;
        if (hero_pos->x >= b->min_bounds.x && hero_pos->x <= b->max_bounds.x &&
            hero_pos->y >= b->min_bounds.y && hero_pos->y <= b->max_bounds.y &&
            hero_pos->z >= b->min_bounds.z && hero_pos->z <= b->max_bounds.z) {
            return trig;
        }
    }

    return NULL;
}

bool Field_TransitionZone(FieldManager *mgr, u16 target_zone_id, u16 spawn_point_id) {
    if (!mgr || target_zone_id == 0) return false;

    /* Execute zone change */
    mgr->current_zone.zone_id = target_zone_id;

    /* Reset entities and triggers for target zone */
    mgr->entity_count = 0;
    mgr->trigger_count = 0;
    mgr->collision_box_count = 0;

    /* Reposition hero to target spawn coordinates */
    Field_SetHeroPosition(mgr, mgr->current_zone.default_spawn_pos.x,
                               mgr->current_zone.default_spawn_pos.y,
                               mgr->current_zone.default_spawn_pos.z,
                               mgr->current_zone.default_spawn_yaw);

    return true;
}
