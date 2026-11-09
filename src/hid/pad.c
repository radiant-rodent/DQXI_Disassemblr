/**
 * src/hid/pad.c - Hardware Input and Pad Reader for Dragon Quest XI (3DS)
 *
 * Reconstructed human-readable C implementation of nn::hid::PadReader::Read
 * and CTR HID shared memory polling discovered in 3DS_Translate.
 */

#include "dqxi.h"

/* Nintendo 3DS HID Shared Memory Base */
#define CTR_HID_SHARED_MEM_BASE     0x10002000

/* HID Button Bits */
#define KEY_A        BIT(0)
#define KEY_B        BIT(1)
#define KEY_SELECT   BIT(2)
#define KEY_START    BIT(3)
#define KEY_DRIGHT   BIT(4)
#define KEY_DLEFT    BIT(5)
#define KEY_DUP      BIT(6)
#define KEY_DDOWN    BIT(7)
#define KEY_R        BIT(8)
#define KEY_L        BIT(9)
#define KEY_X        BIT(10)
#define KEY_Y        BIT(11)

/* CTR HID Hardware Pad State */
typedef struct HidPadState {
    u64  tick_counter;       /* +0x00: System tick of latest update (268,111,856 ticks/sec) */
    u32  held_buttons;       /* +0x08: Currently pressed button bitmask */
    u32  pressed_buttons;    /* +0x0C: One-shot trigger button bitmask */
    s16  circle_pad_x;       /* +0x10: Circle Pad horizontal tilt (-156 to +156) */
    s16  circle_pad_y;       /* +0x12: Circle Pad vertical tilt (-156 to +156) */
    u32  read_counter;       /* +0x14: Incremented once per 60Hz frame */
} HidPadState;

/**
 * PadReader_Read - Read current controller state from HID shared memory.
 * Address: 0x0011AD3C
 * Called once per frame by the game's main execution loop.
 */
void PadReader_Read(HidPadState *out_state) {
    if (!out_state) {
        return;
    }

    volatile u32 *shared_mem = (volatile u32 *)CTR_HID_SHARED_MEM_BASE;

    /* Read raw hardware ticks and registers */
    u64 ticks = ((u64)shared_mem[1] << 32) | shared_mem[0];
    u32 raw_buttons = shared_mem[2];
    u32 pad_raw = shared_mem[4];

    out_state->tick_counter = ticks;
    out_state->held_buttons = raw_buttons & 0xFFF;
    out_state->pressed_buttons = (raw_buttons ^ out_state->held_buttons) & raw_buttons;
    out_state->circle_pad_x = (s16)(pad_raw & 0xFFFF);
    out_state->circle_pad_y = (s16)((pad_raw >> 16) & 0xFFFF);
    out_state->read_counter++;
}
