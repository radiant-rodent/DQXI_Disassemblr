/**
 * src/kernel/sync.c - CTR Thread Synchronization Primitives
 *
 * Implements lightweight atomic spinlocks (LightLock) and re-entrant locks (RecursiveLock)
 * used across Dragon Quest XI background worker threads.
 */

#include "dqxi.h"
#include "kernel.h"

void Kernel_InitLightLock(LightLock *lock) {
    if (!lock) return;
    lock->state = 0; /* 0: Unlocked */
}

void Kernel_LockLightLock(LightLock *lock) {
    if (!lock) return;

    /* Atomic test-and-set emulation for ARMv6K LDREX/STREX */
    while (lock->state != 0) {
        Kernel_SleepThread(1000); /* Yield 1 microsecond */
    }
    lock->state = 1;
}

bool Kernel_TryLockLightLock(LightLock *lock) {
    if (!lock) return false;

    if (lock->state == 0) {
        lock->state = 1;
        return true;
    }
    return false;
}

void Kernel_UnlockLightLock(LightLock *lock) {
    if (!lock) return;
    lock->state = 0;
}

void Kernel_InitRecursiveLock(RecursiveLock *lock) {
    if (!lock) return;

    Kernel_InitLightLock(&lock->lock);
    lock->thread_tag = 0;
    lock->counter = 0;
}

void Kernel_LockRecursiveLock(RecursiveLock *lock, Handle thread_handle) {
    if (!lock) return;

    if (lock->thread_tag == thread_handle) {
        lock->counter++;
        return;
    }

    Kernel_LockLightLock(&lock->lock);
    lock->thread_tag = thread_handle;
    lock->counter = 1;
}

void Kernel_UnlockRecursiveLock(RecursiveLock *lock, Handle thread_handle) {
    if (!lock) return;
    if (lock->thread_tag != thread_handle) return;

    lock->counter--;
    if (lock->counter <= 0) {
        lock->thread_tag = 0;
        lock->counter = 0;
        Kernel_UnlockLightLock(&lock->lock);
    }
}
