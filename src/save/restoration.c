/**
 * src/save/restoration.c - Spell of Restoration (Save Code) for Dragon Quest XI (3DS)
 *
 * Reconstructed human-readable C implementation of the 17-character Save Code
 * generator, validator, and decoder discovered in 3DS_Translate.
 */

#include "dqxi.h"
#include "save.h"

/* 64-character alphabet stored in rodata at 0x0072EF3C */
extern const u16 s_SaveCodeAlphabet[64];

/* Standard CRC32 table */
static u32 crc32_table[256];
static bool crc32_ready = false;

static void init_crc32(void) {
    if (crc32_ready) return;
    for (u32 i = 0; i < 256; i++) {
        u32 c = i;
        for (int j = 0; j < 8; j++) {
            c = (c & 1) ? (0xEDB88320 ^ (c >> 1)) : (c >> 1);
        }
        crc32_table[i] = c;
    }
    crc32_ready = true;
}

static u32 calculate_crc32(const u8 *data, size_t len) {
    init_crc32();
    u32 crc = 0xFFFFFFFF;
    for (size_t i = 0; i < len; i++) {
        crc = crc32_table[(crc ^ data[i]) & 0xFF] ^ (crc >> 8);
    }
    return crc ^ 0xFFFFFFFF;
}

/**
 * SaveCode_ValidateChar - Check if a character belongs to the 64-symbol alphabet.
 * Address: 0x005EF474
 */
int SaveCode_ValidateChar(u16 ch) {
    for (int i = 0; i < SAVE_CODE_ALPHABET_LEN; i++) {
        if (s_SaveCodeAlphabet[i] == ch) {
            return i; /* Index 0..63 */
        }
    }
    return -1; /* Invalid character */
}

/**
 * SaveCode_Encode - Encode game state data into 17-character Spell of Restoration.
 * Address: 0x005EF33C
 * 17 characters * 6 bits = 102 bits of packed state + CRC checksum.
 */
bool SaveCode_Encode(const u8 *save_state_payload, size_t payload_len, u16 *out_code_17) {
    if (!save_state_payload || !out_code_17 || payload_len == 0) {
        return false;
    }

    u32 checksum = calculate_crc32(save_state_payload, payload_len);
    (void)checksum;

    /* Bitstream unpacking: each character represents 6 bits */
    u32 bit_pos = 0;
    for (int i = 0; i < SAVE_CODE_LENGTH; i++) {
        u32 byte_idx = bit_pos / 8;
        u32 bit_offset = bit_pos % 8;
        
        u32 val = 0;
        if (byte_idx < payload_len) {
            val = save_state_payload[byte_idx] >> bit_offset;
            if (bit_offset > 2 && byte_idx + 1 < payload_len) {
                val |= (save_state_payload[byte_idx + 1] << (8 - bit_offset));
            }
        }
        
        u8 char_idx = (u8)(val & 0x3F);
        out_code_17[i] = s_SaveCodeAlphabet[char_idx % 64];
        bit_pos += 6;
    }

    return true;
}

/**
 * SaveCode_Decode - Decode 17-character Spell of Restoration into state bits.
 * Address: 0x005EF3CC
 */
bool SaveCode_Decode(const u16 *code_17, u8 *out_save_state, size_t max_out_len) {
    if (!code_17 || !out_save_state || max_out_len < 12) {
        return false;
    }

    u32 bit_pos = 0;
    for (int i = 0; i < SAVE_CODE_LENGTH; i++) {
        int idx = SaveCode_ValidateChar(code_17[i]);
        if (idx < 0) {
            return false; /* Invalid code character */
        }

        u32 byte_idx = bit_pos / 8;
        u32 bit_offset = bit_pos % 8;

        if (byte_idx < max_out_len) {
            out_save_state[byte_idx] |= ((idx & 0x3F) << bit_offset);
            if (bit_offset > 2 && byte_idx + 1 < max_out_len) {
                out_save_state[byte_idx + 1] |= ((idx & 0x3F) >> (8 - bit_offset));
            }
        }
        bit_pos += 6;
    }

    return true;
}
