/* GetTalkPartyYesIndex - 0x0015A140 (ARM). */
extern int func_003847A0(void);

int GetTalkPartyYesIndex(void) {
    return *(signed char *)(func_003847A0() + 9);
}
