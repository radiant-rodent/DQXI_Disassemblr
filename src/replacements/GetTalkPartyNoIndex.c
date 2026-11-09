/* GetTalkPartyNoIndex - 0x00158874 (ARM).
 *
 * Calls func_003847A0(), then reads a signed byte at offset 10.
 * The linker defsym in tools/build_c_replacement.py resolves the call target
 * so the generated ARM bytes are identical to the retail routine. */
extern int func_003847A0(void);

int GetTalkPartyNoIndex(void) {
    int base = func_003847A0();
    return *(signed char *)(base + 10);
}
