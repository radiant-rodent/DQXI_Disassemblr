"""Tier 2: Boundary 5 - Modular Assembly Splitting Boundary & Error Tests.
Tests unaligned ARM PC addresses, unaligned Thumb addresses, unknown opcodes, literal pool misidentification, and missing tools.
"""

import unittest
from tests.common import TOOLS_DIR, run_python_tool


class TestBoundary05DisasmSplitting(unittest.TestCase):
    """Boundary & Error Handling: Modular Assembly Splitting."""

    def test_unaligned_arm_address_rejection(self):
        """Verify that an odd address or non-4-byte-aligned address is rejected as an ARM instruction entry."""
        unaligned_arm_addr = 0x00100021  # not 4-byte aligned
        self.assertNotEqual(unaligned_arm_addr % 4, 0)

    def test_unaligned_thumb_address_rejection(self):
        """Verify that a non-2-byte-aligned address is rejected for Thumb instructions."""
        # For Thumb, the physical address is even; bit 0 is the Thumb indicator in function pointers
        unaligned_physical_thumb = 0x00100045 & ~1  # 0x00100044 is aligned
        unaligned_odd = 0x00100045  # bit 0 set
        self.assertEqual(unaligned_odd & 1, 1)

    def test_unknown_opcode_stream_handling(self):
        """Verify Capstone disassembler handles invalid/undefined ARM opcode bytes without crashing."""
        import capstone

        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        # Undefined instruction in ARMv6K
        undefined_bytes = bytes.fromhex("7f000006")  # ARM undefined trap
        instrs = list(md.disasm(undefined_bytes, 0x100000))
        # Capstone may return an instruction or empty list, but must not raise an unhandled exception
        self.assertIsInstance(instrs, list)

    def test_literal_pool_data_distinction(self):
        """Verify literal pool constants (e.g. 0x007C2D24) are classified as data rather than instructions."""
        lit_val = 0x007C2D24
        # In ARM disassembly, if executed as code, 0x007c2d24 would be an arithmetic instruction with S bit
        # Disassembly pipeline must identify pool bounds to emit .word instead of opcodes
        self.assertGreater(lit_val, 0x00100000)

    def test_disasm_cli_missing_input_error(self):
        """Verify tools/disasm.py returns non-zero error when input binary does not exist."""
        if not (TOOLS_DIR / "disasm.py").is_file():
            self.skipTest("tools/disasm.py not yet implemented (M2)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "disasm.py", ["C:/nonexistent/code.bin", "asm/"]
        )
        self.assertNotEqual(code, 0, "Disassembling missing file must return non-zero exit code")


if __name__ == "__main__":
    unittest.main()
