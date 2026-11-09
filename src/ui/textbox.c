/**
 * src/ui/textbox.c - UI Text Box and Message Builder for Dragon Quest XI (3DS)
 *
 * Reconstructed human-readable C implementation of text pane buffer management
 * and dialogue message window formatting discovered in 3DS_Translate.
 */

#include "dqxi.h"
#include "heap.h"
#include "ui.h"

extern SmallBlockAllocator *g_pUIAllocator;

/**
 * TextBox_AllocBuffer - Allocate vertex buffers for a layout text box.
 * Address: 0x0053F344
 *
 * Allocates ~312 bytes per character of its current string length from the UI heap.
 * The game dynamically grows this allocation when longer text is assigned at runtime.
 */
void *TextBox_AllocBuffer(LayoutTextPane *pane, u32 char_count) {
    if (!pane || char_count == 0) {
        return NULL;
    }

    /* 312 bytes per character vertex requirement */
    u32 needed_bytes = char_count * VERTEX_BYTES_PER_CHAR;

    /* Allocate from Small-Block UI Allocator (0x007F50F0) */
    void *buffer = SmallBlockAlloc(g_pUIAllocator, needed_bytes);
    if (!buffer) {
        /* Fallback heap allocation failed */
        return NULL;
    }

    pane->text_len = (u16)char_count;
    pane->text_buf_bytes = (u16)needed_bytes;
    return buffer;
}

/**
 * MessageWindow_Builder - Format dialogue lines and speaker prefix tags.
 * Address: 0x00614CF0
 */
u32 MessageWindow_Builder(const u16 *speaker_name, const u16 *body_text, u16 *out_formatted, u32 max_len) {
    if (!body_text || !out_formatted || max_len == 0) {
        return 0;
    }

    u32 pos = 0;

    /* 1. Append speaker prefix if present */
    if (speaker_name && speaker_name[0] != 0) {
        while (*speaker_name && pos + 4 < max_len) {
            out_formatted[pos++] = *speaker_name++;
        }
        out_formatted[pos++] = 0x000A; /* '\n' line break */
    }

    /* 2. Copy and wrap body text */
    while (*body_text && pos + 1 < max_len) {
        out_formatted[pos++] = *body_text++;
    }

    out_formatted[pos] = 0; /* Null terminator */
    return pos;
}
