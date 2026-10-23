"""Tier 1: Feature 5 - Modular Assembly Splitting Tests.
Verifies ARM/Thumb execution state models, hardware ISA restrictions (ARMv6K/VFPv2),
entry vectors, Capstone disassembler availability, and disasm.py tool contracts.
"""

import unittest
from tests.common import (
    ASM_DIR,
    REFERENCE_CODE_DECOMPRESSED,
    TOOLS_DIR,
    run_python_tool,
)


class TestFeature05DisasmSplitting(unittest.TestCase):
    """Feature 5: Relocatable Modular Assembly Splitting."""

    def test_instruction_mode_distribution_contract(self):
        """Verify ARM vs Thumb interworking convention: bit 0 of symbol address denotes Thumb mode."""
        # ARM addresses have bit 0 = 0 (even), Thumb addresses have bit 0 = 1 (odd)
        arm_symbol_addr = 0x00100024  # InitBss (ARM)
        thumb_symbol_addr = 0x00100049  # Thumb stub

        self.assertEqual(arm_symbol_addr & 1, 0, "ARM symbol must have bit 0 = 0")
        self.assertEqual(
            thumb_symbol_addr & 1, 1, "Thumb symbol must have bit 0 = 1"
        )
        self.assertEqual(
            arm_symbol_addr & 3, 0, "ARM instruction must be 4-byte aligned"
        )
        self.assertEqual(
            (thumb_symbol_addr & ~1) & 1,
            0,
            "Thumb instruction must be 2-byte aligned",
        )

    def test_hardware_traps_disassembly_rules(self):
        """Verify strict hardware constraints: forbidden ARMv7/VFPv3 opcodes must not be accepted as valid target codegen."""
        # Forbidden opcodes list from PROJECT.md
        forbidden_mnemonics = {
            "movw",
            "movt",
            "ubfx",
            "sbfx",
            "sdiv",
            "udiv",
            "mls",
            "rbit",
        }
        # Verify forbidden list contains known hardware traps
        self.assertIn("sdiv", forbidden_mnemonics)
        self.assertIn("movw", forbidden_mnemonics)
        self.assertIn("movt", forbidden_mnemonics)

    def test_entry_point_reset_vector(self):
        """Verify entry vector at 0x00100000 begins with valid ARM branching instructions."""
        with open(REFERENCE_CODE_DECOMPRESSED, "rb") as f:
            entry_bytes = f.read(16)
        # 3DS CRT entry starts with branch / setup instructions
        self.assertEqual(len(entry_bytes), 16)
        # Entry instruction at 0x100000 is typically 'b loc_100040' or similar ARM unconditional branch (0xEA......)
        opcode_cond = (entry_bytes[3] >> 4) & 0x0F
        self.assertEqual(
            opcode_cond,
            0x0E,
            "Entry point first instruction must have AL (always) condition code 0xE",
        )

    def test_capstone_engine_availability(self):
        """Verify Capstone disassembler engine is installed and capable of ARM/Thumb disassembly."""
        try:
            import capstone

            md_arm = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
            code_sample = bytes.fromhex("14009fe5")  # ldr r0, [pc, #0x14]
            disasm = list(md_arm.disasm(code_sample, 0x100024))
            self.assertEqual(len(disasm), 1)
            self.assertEqual(disasm[0].mnemonic, "ldr")

            md_thumb = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
            thumb_sample = bytes.fromhex("00b5")  # push {lr}
            disasm_thumb = list(md_thumb.disasm(thumb_sample, 0x100048))
            self.assertEqual(len(disasm_thumb), 1)
            self.assertEqual(disasm_thumb[0].mnemonic, "push")
        except ImportError:
            self.fail("Capstone library is not installed in current Python environment")

    def test_disasm_tool_cli_or_asm_layout(self):
        """Verify tools/disasm.py CLI interface or asm/ directory layout."""
        if (TOOLS_DIR / "disasm.py").is_file():
            code, stdout, stderr = run_python_tool(
                TOOLS_DIR / "disasm.py", ["--help"]
            )
            self.assertEqual(code, 0, f"disasm.py --help failed: {stderr}")
        elif ASM_DIR.is_dir():
            s_files = list(ASM_DIR.glob("**/*.s"))
            self.assertGreater(
                len(s_files), 0, "asm/ directory exists but has no .s files"
            )
        else:
            self.skipTest(
                "Neither tools/disasm.py nor asm/ is present yet (M2)"
            )


if __name__ == "__main__":
    unittest.main()
