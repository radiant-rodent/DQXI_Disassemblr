/*
 * InitBss - verified C-source replacement for the CRT BSS clear at 0x00100024.
 *
 * This is the one function where the original instruction sequence is small
 * enough to express directly in a naked function. The resulting .text bytes
 * are bit-identical to the retail routine:
 *
 *   ldr r0, =0x007C2D24
 *   ldr r1, =0x008398E4
 *   mov r2, #0
 * loop:
 *   cmp r0, r1
 *   strlo r2, [r0], #4
 *   blo loop
 *   bx lr
 *
 * Build/verify with tools/build_c_replacement.py.
 */
__attribute__((naked)) void InitBss(void) {
    __asm__ volatile(
        "ldr r0, =0x007C2D24\n"
        "ldr r1, =0x008398E4\n"
        "mov r2, #0\n"
        "1:\n"
        "cmp r0, r1\n"
        "strlo r2, [r0], #4\n"
        "blo 1b\n"
        "bx lr\n"
    );
}
