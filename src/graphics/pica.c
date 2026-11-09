/**
 * src/graphics/pica.c - PICA200 GPU Display Engine and Command Buffer
 *
 * Implements PICA200 GPU initialization, hardware command buffer packaging,
 * and VRAM framebuffer management for Nintendo 3DS screens.
 */

#include "dqxi.h"
#include "graphics.h"

/* VRAM Screen Base Addresses */
#define VRAM_BASE_TOP_LEFT      0x18000000
#define VRAM_BASE_TOP_RIGHT     0x18046500
#define VRAM_BASE_BOTTOM        0x1808CA00

/* PICA200 Internal Registers */
#define PICA_REG_CLEAR_COLOR    0x00000001
#define PICA_REG_FRAMEBUFFER    0x00000002
#define PICA_REG_VIEWPORT       0x00000003

void Graphics_Init(Pica200Context *ctx, u32 *cmd_buffer, u32 cmd_size) {
    if (!ctx) return;

    /* 1. Setup Top Screen (Left & Right 3D Framebuffers) */
    ctx->top_left.vram_addr = VRAM_BASE_TOP_LEFT;
    ctx->top_left.width = TOP_SCREEN_WIDTH;
    ctx->top_left.height = TOP_SCREEN_HEIGHT;
    ctx->top_left.stride = TOP_SCREEN_HEIGHT * 4; /* 240 * 4 bytes/pixel (RGBA8) */
    ctx->top_left.format = FORMAT_RGBA8;
    ctx->top_left.is_active = true;

    ctx->top_right.vram_addr = VRAM_BASE_TOP_RIGHT;
    ctx->top_right.width = TOP_SCREEN_WIDTH;
    ctx->top_right.height = TOP_SCREEN_HEIGHT;
    ctx->top_right.stride = TOP_SCREEN_HEIGHT * 4;
    ctx->top_right.format = FORMAT_RGBA8;
    ctx->top_right.is_active = false; /* Disabled until stereo 3D enabled */

    /* 2. Setup Bottom Screen */
    ctx->bottom.vram_addr = VRAM_BASE_BOTTOM;
    ctx->bottom.width = BOTTOM_SCREEN_WIDTH;
    ctx->bottom.height = BOTTOM_SCREEN_HEIGHT;
    ctx->bottom.stride = BOTTOM_SCREEN_HEIGHT * 4;
    ctx->bottom.format = FORMAT_RGBA8;
    ctx->bottom.is_active = true;

    /* 3. Command Buffer */
    ctx->command_buffer = cmd_buffer;
    ctx->cmd_buffer_size = cmd_size;
    ctx->cmd_offset = 0;
    ctx->clear_color = 0x000000FF; /* Solid black default */
    ctx->stereoscopic_3d = false;
    ctx->frame_counter = 0;
}

void Graphics_SetClearColor(Pica200Context *ctx, u32 color) {
    if (!ctx) return;
    ctx->clear_color = color;

    /* Emit clear color packet to command buffer if space permits */
    if (ctx->command_buffer && ctx->cmd_offset + 2 <= ctx->cmd_buffer_size) {
        /* Command header: write 1 word to register PICA_REG_CLEAR_COLOR */
        ctx->command_buffer[ctx->cmd_offset++] = (PICA_REG_CLEAR_COLOR & 0xFFFF) | (0xF << 16);
        ctx->command_buffer[ctx->cmd_offset++] = color;
    }
}

void Graphics_FlushCommandBuffer(Pica200Context *ctx) {
    if (!ctx || !ctx->command_buffer || ctx->cmd_offset == 0) return;

    /* In hardware CTR execution, command buffer is submitted via GSPGPU::SubmitGxCommands */
    /* Align command buffer offset to 8-word burst */
    while (ctx->cmd_offset & 7) {
        if (ctx->cmd_offset < ctx->cmd_buffer_size) {
            ctx->command_buffer[ctx->cmd_offset++] = 0; /* NOP padding */
        } else {
            break;
        }
    }

    /* Reset buffer for next frame */
    ctx->cmd_offset = 0;
}

void Graphics_SetStereo3D(Pica200Context *ctx, bool enabled) {
    if (!ctx) return;
    ctx->stereoscopic_3d = enabled;
    ctx->top_right.is_active = enabled;
}
