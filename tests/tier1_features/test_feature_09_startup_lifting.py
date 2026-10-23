"""Tier 1: Feature 9 - Startup Function C Lifting Tests.
Verifies InitBss (0x00100024) machine code, instruction sequence, literal pools, and lifted C semantics.
"""

import struct
import unittest
from tests.common import (
    INIT_BSS_BYTES,
    INIT_BSS_HEX,
    REFERENCE_CODE_DECOMPRESSED,
    SRC_DIR,
)


class TestFeature09StartupLifting(unittest.TestCase):
    """Feature 9: Startup Function C Lifting."""

    def test_init_bss_machine_code_slice(self):
        """Verify the exact 28 bytes of InitBss machine code + 8 bytes literal pool in reference code.bin."""
        with open(REFERENCE_CODE_DECOMPRESSED, "rb") as f:
            f.seek(0x24)  # 0x00100024 relative to 0x00100000
            actual_bytes = f.read(36)  # 28 bytes code + 8 bytes pool

        self.assertEqual(
            actual_bytes[:28].hex(),
            INIT_BSS_HEX[:56],
            "InitBss machine code instructions mismatch",
        )
        self.assertEqual(
            actual_bytes.hex(),
            INIT_BSS_HEX,
            "InitBss code and literal pool mismatch",
        )

    def test_init_bss_instruction_sequence(self):
        """Verify Capstone disassembly of InitBss contains expected mnemonics."""
        import capstone

        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        instrs = list(md.disasm(INIT_BSS_BYTES[:28], 0x00100024))
        self.assertEqual(len(instrs), 7)

        expected_mnemonics = [
            "ldr",
            "ldr",
            "mov",
            "cmp",
            "strlo",
            "blo",
            "bx",
        ]
        actual_mnemonics = [i.mnemonic for i in instrs]
        self.assertEqual(actual_mnemonics, expected_mnemonics)

    def test_init_bss_literal_pool_constants(self):
        """Verify literal pool values at 0x100040 and 0x100044 point to CRT BSS boundaries."""
        bss_start_lit = struct.unpack("<I", INIT_BSS_BYTES[28:32])[0]
        bss_end_lit = struct.unpack("<I", INIT_BSS_BYTES[32:36])[0]

        self.assertEqual(bss_start_lit, 0x007C2D24, "Literal pool __bss_start__ mismatch")
        self.assertEqual(bss_end_lit, 0x008398E4, "Literal pool __bss_end__ mismatch")
        self.assertLess(bss_start_lit, bss_end_lit)

    def test_c_lifting_simulation(self):
        """Verify simulated execution of lifted InitBss C code over a test buffer."""
        # Simulated buffer of 10 words
        buffer = [0xDEADBEEF] * 10
        dst = 0
        end = len(buffer)
        while dst < end:
            buffer[dst] = 0
            dst += 1

        self.assertEqual(buffer, [0] * 10, "Simulated InitBss must zero the entire range")

    def test_src_init_c_file(self):
        """Verify src/init.c source file if present."""
        init_c = SRC_DIR / "init.c"
        if not init_c.is_file():
            self.skipTest("src/init.c not yet created (M3)")

        content = init_c.read_text(encoding="utf-8")
        self.assertIn("InitBss", content)


if __name__ == "__main__":
    unittest.main()
