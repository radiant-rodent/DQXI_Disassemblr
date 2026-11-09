#ifndef DQXI_DQXI_BASE_H
#define DQXI_DQXI_BASE_H

/* Fixed-width integer and float types shared by every generated struct.
 * Self-contained (only <stdint.h>) so a generated header can be syntax-checked
 * or included by matching C source without pulling in any SDK header.  The
 * typedefs are identical to include/types.h, so including both is harmless. */
#include <stdint.h>

typedef uint8_t   u8;
typedef uint16_t  u16;
typedef uint32_t  u32;
typedef uint64_t  u64;
typedef int8_t    s8;
typedef int16_t   s16;
typedef int32_t   s32;
typedef int64_t   s64;
typedef float     f32;
typedef double    f64;

#ifndef DQXI_ARRAY_COUNT
#define DQXI_ARRAY_COUNT(a) (sizeof(a) / sizeof((a)[0]))
#endif

#endif /* DQXI_DQXI_BASE_H */
