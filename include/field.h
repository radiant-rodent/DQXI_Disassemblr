#ifndef DQXI_FIELD_H
#define DQXI_FIELD_H

#pragma once

#include "types.h"

#define MAX_FIELD_ENTITIES      64
#define MAX_FIELD_TRIGGERS      32
#define MAX_ZONE_NAME_LEN       32

/* 3D Vector Representation */
typedef struct Vec3f {
    f32 x;
    f32 y;
    f32 z;
} Vec3f;

/* Axis-Aligned Bounding Box Collision */
typedef struct MapCollisionAABB {
    Vec3f min_bounds;
    Vec3f max_bounds;
    u32   terrain_flags;
} MapCollisionAABB;

/* Terrain Type Flags */
typedef enum TerrainFlags {
    TERRAIN_WALKABLE    = BIT(0),
    TERRAIN_WATER       = BIT(1),
    TERRAIN_SLOPE       = BIT(2),
    TERRAIN_LADDER      = BIT(3),
    TERRAIN_OBSTACLE    = BIT(4),
    TERRAIN_ENCOUNTER   = BIT(5)
} TerrainFlags;

/* Field Trigger Types */
typedef enum TriggerType {
    TRIGGER_NONE            = 0,
    TRIGGER_ZONE_TRANSITION = 1,
    TRIGGER_TREASURE_CHEST  = 2,
    TRIGGER_NPC_TALK        = 3,
    TRIGGER_DOOR            = 4,
    TRIGGER_CAMPFIRE        = 5,
    TRIGGER_SPARKLING_SPOT  = 6
} TriggerType;

/* Field Trigger Definition */
typedef struct FieldTrigger {
    u16              trigger_id;
    TriggerType      type;
    MapCollisionAABB bounds;
    u16              target_zone_id;
    u16              spawn_point_id;
    u32              script_id;
    bool             is_active;
} FieldTrigger;

/* Field Entity (NPC, Monster, Party follower) */
typedef struct FieldEntity {
    u16   entity_id;
    u8    entity_type;
    Vec3f position;
    f32   yaw_angle;
    Vec3f velocity;
    u32   state_flags;
    u16   model_handle;
    bool  is_active;
} FieldEntity;

/* Field Zone / Map Definition */
typedef struct FieldZone {
    u16   zone_id;
    char  zone_name[MAX_ZONE_NAME_LEN];
    u16   background_music_id;
    bool  is_2d_mode;
    Vec3f default_spawn_pos;
    f32   default_spawn_yaw;
} FieldZone;

/* Field World Management Context */
typedef struct FieldManager {
    FieldZone       current_zone;
    Vec3f           hero_position;
    f32             hero_yaw;
    FieldEntity     entities[MAX_FIELD_ENTITIES];
    u32             entity_count;
    FieldTrigger    triggers[MAX_FIELD_TRIGGERS];
    u32             trigger_count;
    MapCollisionAABB collision_boxes[64];
    u32             collision_box_count;
} FieldManager;

/* Global Hero World Position symbol from 0x007F3110 */
extern Vec3f g_HeroWorldPosition;

/* Core Field Subsystem Functions */
void Field_Init(FieldManager *mgr, u16 initial_zone_id);
void Field_UpdateEntities(FieldManager *mgr, f32 delta_time);
bool Field_CheckCollision(const FieldManager *mgr, const Vec3f *pos, const Vec3f *box_radius, Vec3f *out_corrected_pos);
FieldTrigger *Field_CheckTriggers(FieldManager *mgr, const Vec3f *hero_pos);
bool Field_TransitionZone(FieldManager *mgr, u16 target_zone_id, u16 spawn_point_id);
void Field_SetHeroPosition(FieldManager *mgr, f32 x, f32 y, f32 z, f32 yaw);

#endif /* DQXI_FIELD_H */
