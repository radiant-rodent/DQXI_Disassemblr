#ifndef DQXI_HEAP_H
#define DQXI_HEAP_H

#pragma once

#include "types.h"

/* Free block node within heap free list */
typedef struct HeapNode {
    u8   pad_00[0x0C];       /* +0x00 - +0x0B: Reserved / flags */
    struct HeapNode* next;   /* +0x0C: Pointer to next free block */
    u32  size;               /* +0x10: Size of block in bytes */
} HeapNode;

/* General Heap Manager Object (e.g. 0x0055E928 Allocator) */
typedef struct HeapObject {
    u8        pad_00[0x14];  /* +0x00 - +0x13: Heap metadata */
    HeapNode  sentinel;      /* +0x14: Free list sentinel node */
    HeapNode* first_free;    /* +0x20: Pointer to first available free block */
    u32       total_size;    /* +0x24: Total capacity */
    u32       used_size;     /* +0x28: High-water mark / current allocated bytes */
} HeapObject;

/* Small Block Allocator with 5 fixed-size pools and fallback heap */
typedef struct SmallBlockAllocator {
    u8          pad_00[0x54];       /* +0x00 - +0x53: 5 fixed block pool descriptors */
    HeapObject* fallback_heap;     /* +0x54: Pointer to fallback heap object */
} SmallBlockAllocator;

/* Heap API (see src/memory/heaps.c) */
void *HeapAlloc(HeapObject *heap, u32 size);
void HeapFree(HeapObject *heap, void *ptr);
void *SmallBlockAlloc(SmallBlockAllocator *allocator, u32 size);

/* Known Global Memory Addresses discovered in 3DS_Translate */
#define HEAP_INIT_ADDR              0x00102EF8
#define HEAP_ALLOC_ADDR             0x0055E928
#define HEAP_FREE_ADDR              0x0055E808
#define SMALL_BLOCK_ALLOC_ADDR      0x006F1C9C

#define UI_ALLOCATOR_ADDR           0x007F50F0
#define UI_FALLBACK_HEAP_ADDR       0x007F5144
#define UI_FALLBACK_HEAP_SIZE       0x0023F880

#endif /* DQXI_HEAP_H */
