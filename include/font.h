#ifndef DQXI_FONT_H
#define DQXI_FONT_H

#pragma once

#include "types.h"

/* BFFNT Font Binary Header */
typedef struct BffntHeader {
    u32 magic;               /* "FFNT" = 0x544E4646 */
    u16 endianness;          /* 0xFEFF */
    u16 header_size;         /* Size of header (0x14) */
    u32 version;             /* Format version */
    u32 file_size;           /* Total file size */
    u16 block_count;         /* Number of sections (FINF, TGLP, CWDH, CMAP) */
    u16 reserved;
} BffntHeader;

/* Font Metrics Information Block (FINF) */
typedef struct BffntFinf {
    u32 magic;               /* "FINF" = 0x464E4946 */
    u32 size;
    u8  font_type;
    u8  line_feed;
    u16 alter_char_index;
    u8  default_width;
    u8  max_width;
    u8  glyph_width;
    u8  glyph_height;
    u8  ascent;
    u8  descent;
} BffntFinf;

/* Target Game Fonts used in DQXI 3DS */
#define FONT_MAIN_3D14      "3D14"   /* Primary dialogue and menu font */
#define FONT_BATTLE_2D14    "2D14"   /* 2D battle and status windows */
#define FONT_SMALL_2D9      "2D9"    /* Small labels and help strings */

#endif /* DQXI_FONT_H */
