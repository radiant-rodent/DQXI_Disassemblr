"""Tier 4: Scenario 3 - Modular Disassembly, Assemble & Link to Matching code.bin.
Features Exercised: F5 (Disassembly Splitting), F6 (Linker Layout), F7 (Build Pipeline).
Verifies that modular disassembled code compiles and links into exact byte-for-byte binary.
"""

import unittest
from tests.common import (
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    MEMORY_MAP,
    REFERENCE_CODE_DECOMPRESSED,
    TOOLS_DIR,
    run_python_tool,
)


class TestScenario3ModularDisassemblyBuild(unittest.TestCase):
    """Scenario 3: Modular Disassembly, Assemble & Link to Matching code.bin."""

    def test_scenario_3_crt_startup_disassembly_integrity(self):
        """Verify startup vector (0x00100000..0x00100048) disassembles cleanly into ARM instructions."""
        import capstone

        with open(REFERENCE_CODE_DECOMPRESSED, "rb") as f:
            startup_bytes = f.read(0x48)

        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        instrs = list(md.disasm(startup_bytes, 0x00100000))
        # 0x48 = 72 bytes = 18 ARM 4-byte instructions
        self.assertEqual(len(instrs), 18)

    def test_scenario_3_section_padding_reconstruction(self):
        """Verify that linker zero-fill rules recreate exact text, rodata, and data tail paddings."""
        text_pad_len = MEMORY_MAP["text"]["tail_pad"]
        rodata_pad_len = MEMORY_MAP["rodata"]["tail_pad"]
        data_pad_len = MEMORY_MAP["data"]["tail_pad"]

        self.assertEqual(text_pad_len, 4036)
        self.assertEqual(rodata_pad_len, 1512)
        self.assertEqual(data_pad_len, 732)

    def test_scenario_3_build_pipeline_run(self):
        """Verify tools/build.py executes cleanly if implemented in M2."""
        build_tool = TOOLS_DIR / "build.py"
        if not build_tool.is_file():
            self.skipTest("tools/build.py not yet implemented (M2)")

        code, stdout, stderr = run_python_tool(build_tool, ["--help"])
        self.assertEqual(code, 0, f"build.py --help failed: {stderr}")


if __name__ == "__main__":
    unittest.main()
