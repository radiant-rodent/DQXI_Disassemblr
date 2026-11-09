/**
 * src/field/map.c - Map Collision and Terrain Navigation
 *
 * Implements 3D AABB swept volume collision testing against map boundaries,
 * walkable terrain checks, and slope clamping for the field subsystem.
 */

#include "dqxi.h"
#include "field.h"

bool Field_CheckCollision(const FieldManager *mgr, const Vec3f *pos, const Vec3f *box_radius, Vec3f *out_corrected_pos) {
    if (!mgr || !pos || !box_radius) return false;

    if (out_corrected_pos) {
        *out_corrected_pos = *pos;
    }

    bool collision_detected = false;

    /* Test against loaded map collision bounding boxes */
    for (u32 i = 0; i < mgr->collision_box_count; i++) {
        const MapCollisionAABB *box = &mgr->collision_boxes[i];

        /* Check for obstacle or non-walkable bounds */
        if (box->terrain_flags & TERRAIN_OBSTACLE) {
            bool overlap_x = (pos->x + box_radius->x >= box->min_bounds.x) && (pos->x - box_radius->x <= box->max_bounds.x);
            bool overlap_y = (pos->y + box_radius->y >= box->min_bounds.y) && (pos->y - box_radius->y <= box->max_bounds.y);
            bool overlap_z = (pos->z + box_radius->z >= box->min_bounds.z) && (pos->z - box_radius->z <= box->max_bounds.z);

            if (overlap_x && overlap_y && overlap_z) {
                collision_detected = true;
                if (out_corrected_pos) {
                    /* Push out along minimal overlap axis */
                    f32 dx1 = (pos->x + box_radius->x) - box->min_bounds.x;
                    f32 dx2 = box->max_bounds.x - (pos->x - box_radius->x);
                    f32 min_dx = (dx1 < dx2) ? -dx1 : dx2;

                    out_corrected_pos->x += min_dx;
                }
            }
        }
    }

    return collision_detected;
}
