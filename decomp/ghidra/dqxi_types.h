/* Minimal CTR/ARM types used by the Ghidra-generated C.
 * These are presentation types, not a claim about the original compiler ABI.
 */
#pragma once
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>


typedef uint8_t  undefined1;
typedef uint16_t undefined2;
typedef uint32_t undefined4;
typedef uint64_t undefined8;
typedef uint8_t  undefined;
typedef uint8_t  byte;
typedef uint16_t ushort;
typedef uint32_t uint;
typedef uint64_t ulong;
typedef uint8_t  code;
typedef int32_t  int3;
typedef uint32_t uint3;
typedef uint64_t uint4;
typedef int64_t  longlong;
typedef uint64_t ulonglong;
typedef float    float4;
typedef uint16_t wchar16;
typedef uint32_t wchar32;

#ifndef NULL
#define NULL ((void*)0)
#endif
