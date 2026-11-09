/**
 * src/kernel/memory.c - CTR Memory Management and Page Table Control
 *
 * Implements linear memory mapping, application heap boundaries,
 * and page-aligned memory protection management.
 */

#include "dqxi.h"
#include "kernel.h"

#define CTR_PAGE_SIZE       4096
#define CTR_LINEAR_HEAP_MAX 0x06000000 /* 96 MB max linear heap on Old 3DS */

typedef struct LinearHeapManager {
    u32  base_virtual_addr;
    u32  allocated_size;
    u32  max_capacity;
    bool is_initialized;
} LinearHeapManager;

static LinearHeapManager s_linear_heap = { 0, 0, 0, false };

Result Kernel_InitLinearHeap(u32 base_addr, u32 capacity) {
    s_linear_heap.base_virtual_addr = base_addr;
    s_linear_heap.max_capacity = capacity;
    s_linear_heap.allocated_size = 0;
    s_linear_heap.is_initialized = true;
    return 0;
}

void *Kernel_AllocateLinearBlock(u32 size) {
    if (!s_linear_heap.is_initialized || size == 0) return NULL;

    u32 aligned_size = ALIGN(size, CTR_PAGE_SIZE);
    if (s_linear_heap.allocated_size + aligned_size > s_linear_heap.max_capacity) {
        return NULL; /* Out of physical linear memory */
    }

    u32 alloc_addr = s_linear_heap.base_virtual_addr + s_linear_heap.allocated_size;
    s_linear_heap.allocated_size += aligned_size;
    return (void *)alloc_addr;
}
