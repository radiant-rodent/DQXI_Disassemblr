/* GetTalkPartyPageSize - 0x0015A130 (ARM). */
extern int func_003847A0(void);

int GetTalkPartyPageSize(void) {
    return *(int *)func_003847A0();
}
