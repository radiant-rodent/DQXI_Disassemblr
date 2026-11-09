/**
 * src/field/entity.c - Field Entities and World Coordinates
 *
 * Implements entity movement, actor updates, and synchronization with the
 * global active hero world coordinates at 0x007F3110.
 */

#include "dqxi.h"
#include "field.h"

/* Global active hero position registered in symbols.json at 0x007F3110 */
Vec3f g_HeroWorldPosition = { 0.0f, 0.0f, 0.0f };

void Field_Init(FieldManager *mgr, u16 initial_zone_id) {
    if (!mgr) return;

    mgr->current_zone.zone_id = initial_zone_id;
    mgr->current_zone.is_2d_mode = false;
    mgr->current_zone.background_music_id = 1;
    mgr->current_zone.default_spawn_pos = (Vec3f){ 100.0f, 0.0f, 100.0f };
    mgr->current_zone.default_spawn_yaw = 0.0f;

    mgr->hero_position = mgr->current_zone.default_spawn_pos;
    mgr->hero_yaw = mgr->current_zone.default_spawn_yaw;
    g_HeroWorldPosition = mgr->hero_position;

    mgr->entity_count = 0;
    mgr->trigger_count = 0;
    mgr->collision_box_count = 0;
}

void Field_SetHeroPosition(FieldManager *mgr, f32 x, f32 y, f32 z, f32 yaw) {
    if (!mgr) return;

    mgr->hero_position.x = x;
    mgr->hero_position.y = y;
    mgr->hero_position.z = z;
    mgr->hero_yaw = yaw;

    /* Synchronize global address at 0x007F3110 */
    g_HeroWorldPosition = mgr->hero_position;
}

void Field_UpdateEntities(FieldManager *mgr, f32 delta_time) {
    if (!mgr) return;

    /* Update dynamic entities (NPCs, party followers) */
    for (u32 i = 0; i < mgr->entity_count; i++) {
        FieldEntity *ent = &mgr->entities[i];
        if (!ent->is_active) continue;

        ent->position.x += ent->velocity.x * delta_time;
        ent->position.y += ent->velocity.y * delta_time;
        ent->position.z += ent->velocity.z * delta_time;
    }

    /* Synchronize hero coordinates */
    g_HeroWorldPosition = mgr->hero_position;
}
