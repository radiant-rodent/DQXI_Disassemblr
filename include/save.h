#ifndef DQXI_SAVE_H
#define DQXI_SAVE_H

#pragma once

#include "types.h"

#define SAVE_CODE_LENGTH            17
#define SAVE_CODE_ALPHABET_LEN      64
#define SAVE_NAME_TABLE_LEN         256
#define SAVE_CODE_ALPHABET_ADDR     0x0072EF3C

/* Spell of Restoration (Save Code) Context */
typedef struct SaveCodeContext {
    u16  alphabet[SAVE_CODE_ALPHABET_LEN];  /* UTF-16 representation of 64 valid characters */
    u8   name_table[SAVE_NAME_TABLE_LEN];    /* Name index mapping table */
    u32  crc32_checksum;                    /* CRC32 of save payload */
} SaveCodeContext;

/* Core Save Code Functions discovered in 3DS_Translate */
#define SAVE_CODE_ENCODE_ADDR       0x005EF33C
#define SAVE_CODE_DECODE_ADDR       0x005EF3CC
#define SAVE_CODE_VALIDATE_ADDR     0x005EF474

#endif /* DQXI_SAVE_H */
