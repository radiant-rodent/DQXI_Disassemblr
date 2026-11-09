#ifndef DQXI_UI_H
#define DQXI_UI_H

#pragma once

#include "types.h"

/* NW4C BFLYT Text Box Pane structure */
typedef struct LayoutTextPane {
    u32   tag;               /* "txt1" = 0x31747874 */
    u32   size;              /* Section size */
    u8    flags;             /* Visibility and layout flags */
    u8    origin;            /* Origin anchor */
    u8    alpha;             /* Alpha transparency */
    u8    pad;
    char  name[24];          /* Pane identifier name */
    f32   x;                 /* Position X */
    f32   y;                 /* Position Y */
    f32   z;                 /* Position Z */
    f32   width;             /* Pane width */
    f32   height;            /* Pane height */
    u16   text_buf_bytes;    /* Initial buffer allocation size */
    u16   text_len;          /* Current string length in characters */
    u16   material_idx;      /* Material index */
    u16   font_idx;          /* Font resource index */
} LayoutTextPane;

/* Vertex Buffer per character descriptor allocated at 0x0053F344 */
#define VERTEX_BYTES_PER_CHAR       312
#define UI_VERTEX_ALLOC_ADDR        0x0053F344

#endif /* DQXI_UI_H */
