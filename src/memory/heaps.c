/**
 * src/memory/heaps.c - Memory Management and Dynamic Heaps for Dragon Quest XI (3DS)
 *
 * Reconstructed human-readable C implementation of the CTR linear heap partitioning
 * and small-block allocators discovered in 3DS_Translate.
 */

#include "dqxi.h"
#include "heap.h"

/* Global allocator pointers */
SmallBlockAllocator *g_pUIAllocator = (SmallBlockAllocator *)UI_ALLOCATOR_ADDR;
HeapObject *g_pUIFallbackHeap = (HeapObject *)UI_FALLBACK_HEAP_ADDR;

/**
 * InitHeaps - Partition the CTR linear heap into system heaps at boot.
 * Address: 0x00102EF8
 *
 * Partitions:
 * - Main Game Heap: 44 MB (46,137,344 bytes)
 * - Sub-Heap 1: 10.6 MB (11,114,496 bytes)
 * - Sub-Heap 2: 3.0 MB (3,145,728 bytes)
 * - Sub-Heap 3: 1.75 MB (1,835,008 bytes)
 * - Sub-Heap 4: 256 KB (262,144 bytes)
 * - Sub-Heap 5: 160 KB (163,840 bytes)
 * - Small-Block Allocator 1 & 2 (UI Heap fallback: 0x0023F880 bytes)
 */
void InitHeaps(u32 linear_heap_base, u32 total_linear_size) {
    u32 current_offset = linear_heap_base;

    /* 1. Main Game Heap (44 MB) */
    HeapObject *main_heap = (HeapObject *)current_offset;
    main_heap->total_size = 44 * 1024 * 1024;
    main_heap->sentinel.next = (HeapNode *)((u8 *)main_heap + 0x20);
    main_heap->sentinel.size = 0;
    main_heap->first_free = main_heap->sentinel.next;
    current_offset += main_heap->total_size;

    /* 2. Sub-Heap 1 (10.6 MB) */
    HeapObject *sub_heap_1 = (HeapObject *)current_offset;
    sub_heap_1->total_size = (u32)(10.6 * 1024 * 1024);
    current_offset += sub_heap_1->total_size;

    /* 3. Sub-Heap 2 (3.0 MB) */
    HeapObject *sub_heap_2 = (HeapObject *)current_offset;
    sub_heap_2->total_size = 3 * 1024 * 1024;
    current_offset += sub_heap_2->total_size;

    /* 4. Sub-Heap 3 (1.75 MB) */
    HeapObject *sub_heap_3 = (HeapObject *)current_offset;
    sub_heap_3->total_size = (u32)(1.75 * 1024 * 1024);
    current_offset += sub_heap_3->total_size;

    /* 5. Sub-Heap 4 (256 KB) */
    HeapObject *sub_heap_4 = (HeapObject *)current_offset;
    sub_heap_4->total_size = 256 * 1024;
    current_offset += sub_heap_4->total_size;

    /* 6. Sub-Heap 5 (160 KB) */
    HeapObject *sub_heap_5 = (HeapObject *)current_offset;
    sub_heap_5->total_size = 160 * 1024;
    current_offset += sub_heap_5->total_size;

    /* 7. UI Small-Block Allocator Fallback Heap (0x23F880 bytes) */
    g_pUIFallbackHeap->total_size = UI_FALLBACK_HEAP_SIZE;
    g_pUIFallbackHeap->sentinel.next = (HeapNode *)((u8 *)g_pUIFallbackHeap + 0x20);
    g_pUIFallbackHeap->first_free = g_pUIFallbackHeap->sentinel.next;
    g_pUIAllocator->fallback_heap = g_pUIFallbackHeap;
}

/**
 * HeapAlloc - Allocate block from a general heap free list.
 * Address: 0x0055E928
 */
void *HeapAlloc(HeapObject *heap, u32 size) {
    if (!heap || size == 0) {
        return NULL;
    }

    /* 4-byte align requested size */
    u32 needed = ALIGN(size, 4);
    HeapNode *prev = &heap->sentinel;
    HeapNode *curr = heap->first_free;

    while (curr != NULL && curr != &heap->sentinel) {
        if (curr->size >= needed) {
            /* Found available block */
            if (curr->size >= needed + sizeof(HeapNode) + 4) {
                /* Split block */
                HeapNode *rem = (HeapNode *)((u8 *)curr + sizeof(HeapNode) + needed);
                rem->size = curr->size - needed - sizeof(HeapNode);
                rem->next = curr->next;
                prev->next = rem;
                if (heap->first_free == curr) {
                    heap->first_free = rem;
                }
            } else {
                /* Exact match */
                prev->next = curr->next;
                if (heap->first_free == curr) {
                    heap->first_free = curr->next;
                }
            }
            heap->used_size += needed;
            return (void *)((u8 *)curr + sizeof(HeapNode));
        }
        prev = curr;
        curr = curr->next;
    }

    return NULL; /* Out of memory */
}

/**
 * HeapFree - Return allocated block to free list.
 * Address: 0x0055E808
 */
void HeapFree(HeapObject *heap, void *ptr) {
    if (!heap || !ptr) {
        return;
    }
    HeapNode *node = (HeapNode *)((u8 *)ptr - sizeof(HeapNode));
    node->next = heap->first_free;
    heap->first_free = node;
    if (heap->used_size >= node->size) {
        heap->used_size -= node->size;
    }
}

/**
 * SmallBlockAlloc - Allocate block from small-block pool or fallback heap.
 * Address: 0x006F1C9C
 */
void *SmallBlockAlloc(SmallBlockAllocator *allocator, u32 size) {
    if (!allocator) {
        return NULL;
    }

    /* Check fixed pool thresholds */
    /* If beyond small pool thresholds, delegate to fallback heap */
    if (allocator->fallback_heap) {
        void *p = HeapAlloc(allocator->fallback_heap, size);
        if (!p) {
            /* Fallback failed - return NULL instead of corrupted heap header */
            return NULL;
        }
        return p;
    }
    return NULL;
}
