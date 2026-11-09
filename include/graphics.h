#ifndef DQXI_GRAPHICS_H
#define DQXI_GRAPHICS_H

#pragma once

#include "types.h"

/* PICA200 Screen Dimensions */
#define TOP_SCREEN_WIDTH        400
#define TOP_SCREEN_HEIGHT       240
#define TOP_SCREEN_3D_WIDTH     800
#define BOTTOM_SCREEN_WIDTH     320
#define BOTTOM_SCREEN_HEIGHT    240

/* PICA200 Color Formats */
typedef enum DisplayFormat {
    FORMAT_RGBA8    = 0,
    FORMAT_RGB8     = 1,
    FORMAT_RGB565   = 2,
    FORMAT_RGBA4    = 3,
    FORMAT_RGB5_A1  = 4
} DisplayFormat;

/* PICA200 Framebuffer Buffer Structure */
typedef struct FrameBufferInfo {
    u32           vram_addr;
    u16           width;
    u16           height;
    u16           stride;
    DisplayFormat format;
    bool          is_active;
} FrameBufferInfo;

/* PICA200 GPU Command Packet Header */
typedef struct GpuCommand {
    u32 register_id : 16;
    u32 mask : 4;
    u32 extra_words : 11;
    u32 is_be : 1;
} GpuCommand;

/* PICA200 Display Context */
typedef struct Pica200Context {
    FrameBufferInfo top_left;
    FrameBufferInfo top_right;
    FrameBufferInfo bottom;
    u32             clear_color;
    u32            *command_buffer;
    u32             cmd_buffer_size;
    u32             cmd_offset;
    bool            stereoscopic_3d;
    u32             frame_counter;
} Pica200Context;

/* Core Display and Command Buffer Functions */
void Graphics_Init(Pica200Context *ctx, u32 *cmd_buffer, u32 cmd_size);
void Graphics_SetClearColor(Pica200Context *ctx, u32 color);
void Graphics_SwapBuffers(Pica200Context *ctx, bool is_top, bool wait_vblank);
void Graphics_FlushCommandBuffer(Pica200Context *ctx);
void Graphics_WaitVBlank(bool is_top);
void Graphics_SetStereo3D(Pica200Context *ctx, bool enabled);

#endif /* DQXI_GRAPHICS_H */
