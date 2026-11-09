#ifndef DQXI_KERNEL_H
#define DQXI_KERNEL_H

#pragma once

#include "types.h"

/* CTR SVC Operation Codes */
#define MEMOP_FREE      1
#define MEMOP_RESERVE   2
#define MEMOP_ALLOC     3
#define MEMOP_MAP       4
#define MEMOP_UNMAP     5
#define MEMOP_PROT      6

/* CTR Memory Permissions */
#define MEMPERM_READ    BIT(0)
#define MEMPERM_WRITE   BIT(1)
#define MEMPERM_EXECUTE BIT(2)
#define MEMPERM_DONTCARE BIT(28)

/* Reset Types for Synchronization Events */
typedef enum ResetType {
    RESET_ONESHOT   = 0,
    RESET_STICKY    = 1,
    RESET_PULSE     = 2
} ResetType;

/* Lightweight Synchronization Lock */
typedef struct LightLock {
    s32 state;
} LightLock;

/* Recursive Lock */
typedef struct RecursiveLock {
    LightLock   lock;
    Handle      thread_tag;
    s32         counter;
} RecursiveLock;

/* Thread Entry Function Pointer */
typedef void (*ThreadFunc)(u32 arg);

/* CTR Thread Control Block */
typedef struct ThreadControlBlock {
    Handle      handle;
    ThreadFunc  entry_function;
    u32         argument;
    u32         stack_top;
    s32         priority;
    s32         processor_id;
    bool        is_running;
} ThreadControlBlock;

/* Core Kernel and SVC Dispatcher Functions */
Result Kernel_ControlMemory(u32 *out_addr, u32 addr0, u32 addr1, u32 size, u32 op, u32 perm);
Result Kernel_CreateThread(Handle *out_handle, ThreadFunc entry, u32 arg, u32 stack_top, s32 priority, s32 processor_id);
void   Kernel_ExitThread(void);
void   Kernel_SleepThread(s64 nanoseconds);
Result Kernel_CreateEvent(Handle *out_handle, ResetType reset_type);
Result Kernel_SignalEvent(Handle handle);
Result Kernel_ClearEvent(Handle handle);
Result Kernel_WaitSynchronization(Handle handle, s64 nanoseconds);
Result Kernel_CloseHandle(Handle handle);

/* Synchronization Primitives */
void Kernel_InitLightLock(LightLock *lock);
void Kernel_LockLightLock(LightLock *lock);
bool Kernel_TryLockLightLock(LightLock *lock);
void Kernel_UnlockLightLock(LightLock *lock);

void Kernel_InitRecursiveLock(RecursiveLock *lock);
void Kernel_LockRecursiveLock(RecursiveLock *lock, Handle thread_handle);
void Kernel_UnlockRecursiveLock(RecursiveLock *lock, Handle thread_handle);

#endif /* DQXI_KERNEL_H */
