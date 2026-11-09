#ifndef DQXI_H
#define DQXI_H

#pragma once

#include "types.h"
#include "heap.h"
#include "ui.h"
#include "font.h"
#include "save.h"
#include "graphics.h"
#include "battle.h"
#include "field.h"
#include "audio.h"
#include "kernel.h"
#include "recovered_types.h"

/* Execution Base and Section Virtual Addresses */
#define ENTRY_POINT_ADDR            0x00100000
#define INIT_BSS_ADDR               0x00100024

#define TEXT_SECTION_START          0x00100000
#define TEXT_SECTION_END            0x0072403C

#define RODATA_SECTION_START        0x00725000
#define RODATA_SECTION_END          0x0079AA18

#define DATA_SECTION_START          0x0079B000
#define DATA_SECTION_END            0x007C2D24

#define BSS_SECTION_START           0x007C3000
#define BSS_SECTION_END             0x00839BC0

/* CRT Prototype */
void InitBss(void);

#endif /* DQXI_H */
