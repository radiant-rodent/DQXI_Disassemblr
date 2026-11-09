/**
 * src/kernel/svc.c - CTR System Supervisor Call (SVC) Dispatchers
 *
 * Implements CTR kernel interfaces: svcControlMemory (0x01), svcCreateThread (0x08),
 * svcSleepThread (0x0A), svcCreateEvent (0x17), svcWaitSynchronization (0x24),
 * and svcCloseHandle (0x23).
 */

#include "dqxi.h"
#include "kernel.h"

Result Kernel_ControlMemory(u32 *out_addr, u32 addr0, u32 addr1, u32 size, u32 op, u32 perm) {
    if (!out_addr) return 0xD900182F; /* Invalid argument error */

    /* In CTR architecture, svcControlMemory (0x01) manages application heap allocation */
    if (op == MEMOP_ALLOC) {
        *out_addr = addr0 ? addr0 : 0x14000000;
        return 0; /* Success */
    } else if (op == MEMOP_FREE) {
        *out_addr = 0;
        return 0;
    }

    *out_addr = addr0;
    return 0;
}

Result Kernel_CreateThread(Handle *out_handle, ThreadFunc entry, u32 arg, u32 stack_top, s32 priority, s32 processor_id) {
    if (!out_handle || !entry) return 0xD900182F;

    /* Assign synthetic thread handle in userspace model */
    static Handle s_next_thread_handle = 0x100;
    *out_handle = s_next_thread_handle++;
    return 0;
}

void Kernel_ExitThread(void) {
    /* CTR svcExitThread (0x09) */
}

void Kernel_SleepThread(s64 nanoseconds) {
    /* CTR svcSleepThread (0x0A): yields execution to scheduler */
    (void)nanoseconds;
}

Result Kernel_CreateEvent(Handle *out_handle, ResetType reset_type) {
    if (!out_handle) return 0xD900182F;

    static Handle s_next_event_handle = 0x200;
    *out_handle = s_next_event_handle++;
    return 0;
}

Result Kernel_SignalEvent(Handle handle) {
    if (handle == 0) return 0xD900182F;
    return 0;
}

Result Kernel_ClearEvent(Handle handle) {
    if (handle == 0) return 0xD900182F;
    return 0;
}

Result Kernel_WaitSynchronization(Handle handle, s64 nanoseconds) {
    if (handle == 0) return 0xD900182F;
    (void)nanoseconds;
    return 0;
}

Result Kernel_CloseHandle(Handle handle) {
    if (handle == 0) return 0xD900182F;
    return 0;
}
