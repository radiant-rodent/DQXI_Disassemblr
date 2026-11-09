/**
 * src/graphics/display.c - Frame Buffer Swap and VBlank Synchronization
 *
 * Implements double-buffering display swap and vertical blank synchronization
 * routines interfacing with CTR GSPGPU service.
 */

#include "dqxi.h"
#include "graphics.h"

/* GSP Shared Memory and Register Base */
#define GSP_SHARED_MEM_ADDR     0x10002000
#define GSP_TOP_FRAME_EVENT     0x00000001
#define GSP_BOTTOM_FRAME_EVENT  0x00000002

void Graphics_WaitVBlank(bool is_top) {
    /* Poll or wait on GSP synchronization event for screen refresh (60 Hz) */
    volatile u32 *gsp_status = (volatile u32 *)GSP_SHARED_MEM_ADDR;
    u32 event_mask = is_top ? GSP_TOP_FRAME_EVENT : GSP_BOTTOM_FRAME_EVENT;
    
    /* Wait for event trigger flag from GSP service */
    u32 timeout = 1000000;
    while ((*gsp_status & event_mask) == 0 && --timeout > 0) {
        /* CTR yield / sleep thread for 100 microseconds */
    }

    /* Acknowledge event flag */
    *gsp_status &= ~event_mask;
}

void Graphics_SwapBuffers(Pica200Context *ctx, bool is_top, bool wait_vblank) {
    if (!ctx) return;

    if (wait_vblank) {
        Graphics_WaitVBlank(is_top);
    }

    if (is_top) {
        /* Swap top screen front and back VRAM addresses */
        u32 temp_left = ctx->top_left.vram_addr;
        ctx->top_left.vram_addr = (temp_left == 0x18000000) ? 0x18046500 : 0x18000000;

        if (ctx->stereoscopic_3d) {
            u32 temp_right = ctx->top_right.vram_addr;
            ctx->top_right.vram_addr = (temp_right == 0x1808CA00) ? 0x180D2F00 : 0x1808CA00;
        }
    } else {
        /* Swap bottom screen buffer addresses */
        u32 temp_bot = ctx->bottom.vram_addr;
        ctx->bottom.vram_addr = (temp_bot == 0x1808CA00) ? 0x180C4E00 : 0x1808CA00;
    }

    ctx->frame_counter++;
}
