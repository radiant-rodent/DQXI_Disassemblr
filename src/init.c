/**
 * src/init.c - CRT Startup and BSS Initialization for Dragon Quest XI (3DS)
 *
 * Reconstructed C implementation of the InitBss routine at 0x00100024.
 * Zeroes the entire BSS segment from __bss_start__ (0x007C2D24) to __bss_end__ (0x008398E4).
 */

#include "dqxi.h"

/* CRT BSS boundaries defined in linker script */
extern u32 __bss_start__;
extern u32 __bss_end__;

/**
 * InitBss - Clear the BSS section at boot time.
 * Address: 0x00100024
 *
 * Assembly equivalent:
 *   ldr   r0, =__bss_start__   @ 0x007C2D24
 *   ldr   r1, =__bss_end__     @ 0x008398E4
 *   mov   r2, #0
 * loop:
 *   cmp   r0, r1
 *   strlo r2, [r0], #4
 *   blo   loop
 *   bx    lr
 */
void InitBss(void) {
    u32 *dst = (u32 *)&__bss_start__;
    u32 *end = (u32 *)&__bss_end__;
    
    while (dst < end) {
        *dst++ = 0;
    }
}
