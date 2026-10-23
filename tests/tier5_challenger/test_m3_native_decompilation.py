"""Tier 5: Challenger - Milestone 3 Comprehensive Native Decompilation & Subsystems Tests.

Verifies:
1. Modular C/C++ Subsystems:
   - src/graphics/, src/battle/, src/field/, src/audio/, src/kernel/
   - Existing subsystems: src/memory/, src/ui/, src/save/, src/hid/, src/init.c
   - Headers: include/graphics.h, include/battle.h, include/field.h, include/audio.h, include/kernel.h, include/dqxi.h
2. Comprehensive Decompilation:
   - All 18,787 discovered functions indexed in decomp/functions_index.json
   - Function catalog contains address, name, size, mode, and source file
   - Decompiled C functions in decomp/functions/
3. Bit-Matching Binary Verification:
   - tools/build.py produces bit-matching code.bin & code.compressed.bin
4. Bytecode Diff Tool Verification:
   - tools/diff.py validates bit-identical assembly and error handling
"""

import json
import unittest
from pathlib import Path

from tests.common import (
    BUILD_DIR,
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    INCLUDE_DIR,
    PROJECT_ROOT,
    SRC_DIR,
    TOOLS_DIR,
    sha256_file,
    run_python_tool,
)

DECOMP_DIR = PROJECT_ROOT / "decomp"
DECOMP_FUNCS = DECOMP_DIR / "functions"
INDEX_FILE = DECOMP_DIR / "functions_index.json"


class TestM3NativeDecompilation(unittest.TestCase):
    """Milestone 3 Comprehensive Decompilation and Subsystems Test Suite."""

    def test_modular_subsystem_directories_exist(self):
        """Verify all required modular subsystem directories exist in src/."""
        required_subsystems = [
            "graphics",
            "battle",
            "field",
            "audio",
            "kernel",
            "memory",
            "ui",
            "save",
            "hid",
        ]
        for sub in required_subsystems:
            p = SRC_DIR / sub
            self.assertTrue(p.is_dir(), f"Required subsystem directory 'src/{sub}' is missing")

    def test_subsystem_source_files_exist(self):
        """Verify essential subsystem C implementation files exist."""
        expected_files = [
            SRC_DIR / "init.c",
            SRC_DIR / "graphics" / "pica.c",
            SRC_DIR / "graphics" / "display.c",
            SRC_DIR / "battle" / "state.c",
            SRC_DIR / "battle" / "turn.c",
            SRC_DIR / "battle" / "damage.c",
            SRC_DIR / "field" / "map.c",
            SRC_DIR / "field" / "entity.c",
            SRC_DIR / "field" / "trigger.c",
            SRC_DIR / "audio" / "stream.c",
            SRC_DIR / "audio" / "voice.c",
            SRC_DIR / "audio" / "sound_effects.c",
            SRC_DIR / "kernel" / "svc.c",
            SRC_DIR / "kernel" / "sync.c",
            SRC_DIR / "kernel" / "memory.c",
            SRC_DIR / "memory" / "heaps.c",
            SRC_DIR / "ui" / "textbox.c",
            SRC_DIR / "save" / "restoration.c",
            SRC_DIR / "hid" / "pad.c",
        ]
        for f in expected_files:
            self.assertTrue(f.is_file(), f"Source file '{f.relative_to(PROJECT_ROOT)}' is missing")
            content = f.read_text(encoding="utf-8")
            self.assertGreater(len(content), 100, f"Source file '{f.name}' is too short or empty")
            self.assertIn("dqxi.h", content, f"Source file '{f.name}' must include dqxi.h")

    def test_typed_subsystem_headers_exist(self):
        """Verify all subsystem headers exist and have proper include guards."""
        expected_headers = [
            "dqxi.h",
            "types.h",
            "heap.h",
            "ui.h",
            "font.h",
            "save.h",
            "graphics.h",
            "battle.h",
            "field.h",
            "audio.h",
            "kernel.h",
        ]
        for h_name in expected_headers:
            h_path = INCLUDE_DIR / h_name
            self.assertTrue(h_path.is_file(), f"Header 'include/{h_name}' is missing")
            content = h_path.read_text(encoding="utf-8")
            self.assertTrue(
                "#ifndef" in content or "#pragma once" in content,
                f"Header '{h_name}' missing include guard",
            )

    def test_functions_index_catalog_completeness(self):
        """Verify decomp/functions_index.json indexes all 18,787 discovered functions."""
        self.assertTrue(INDEX_FILE.is_file(), "decomp/functions_index.json does not exist")
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        self.assertEqual(catalog.get("total_discovered"), 18787)
        self.assertEqual(catalog.get("decompiled_count"), 18787)
        funcs = catalog.get("functions", [])
        self.assertEqual(len(funcs), 18787)

        # Validate structure of entries
        first = funcs[0]
        self.assertIn("address", first)
        self.assertIn("name", first)
        self.assertIn("size", first)
        self.assertIn("mode", first)
        self.assertIn("file", first)
        self.assertIn("source", first)
        self.assertGreater(first["size"], 0)
        self.assertIn(first["mode"], ("arm", "thumb"))

    def test_decompiled_functions_directory_populated(self):
        """Verify decomp/functions/ contains all 18,787 lifted C source files."""
        self.assertTrue(DECOMP_FUNCS.is_dir(), "decomp/functions/ directory is missing")
        files = list(DECOMP_FUNCS.glob("*.c"))
        self.assertEqual(
            len(files), 18787,
            f"Expected 18,787 functions in decomp/functions/, got {len(files)}"
        )

        # Check key named functions exist
        key_symbols = [
            "ResetVector.c",
            "InitBss.c",
            "ThunkToThumb.c",
            "InitHeaps.c",
            "HeapAlloc.c",
            "SaveCode_Decode.c",
            "MessageWindow_Builder.c",
        ]
        for name in key_symbols:
            p = DECOMP_FUNCS / name
            self.assertTrue(p.is_file(), f"Key symbol decompiled file '{name}' is missing")
            content = p.read_text(encoding="utf-8")
            self.assertRegex(content, r"\b(?:void|u32|int|bool)\s+\w+\s*\(")
            self.assertIn("return", content)

    def test_bit_matching_uncompressed_binary(self):
        """Verify build/code.bin matches original SHA-256 and size byte-for-byte."""
        code_bin = BUILD_DIR / "code.bin"
        self.assertTrue(code_bin.is_file(), "build/code.bin does not exist")
        self.assertEqual(code_bin.stat().st_size, EXPECTED_SIZES["code_decompressed"])
        self.assertEqual(
            sha256_file(code_bin).lower(),
            EXPECTED_HASHES["code_decompressed"].lower(),
            "code.bin SHA-256 mismatch",
        )

    def test_bit_matching_compressed_binary(self):
        """Verify build/code.compressed.bin matches original ExeFS .code byte-for-byte."""
        comp_bin = BUILD_DIR / "code.compressed.bin"
        self.assertTrue(comp_bin.is_file(), "build/code.compressed.bin does not exist")
        self.assertEqual(comp_bin.stat().st_size, EXPECTED_SIZES["code_compressed"])
        self.assertEqual(
            sha256_file(comp_bin).lower(),
            EXPECTED_HASHES["code_compressed"].lower(),
            "code.compressed.bin SHA-256 mismatch",
        )

    def test_diff_tool_execution(self):
        """Verify tools/diff.py executes and reports 100% bit-identical match."""
        diff_script = TOOLS_DIR / "diff.py"
        self.assertTrue(diff_script.is_file(), "tools/diff.py does not exist")

        # Test InitBss symbol lookup
        code, stdout, stderr = run_python_tool(diff_script, ["InitBss", "--json"])
        self.assertEqual(code, 0, f"diff.py InitBss failed: {stderr}")
        res = json.loads(stdout)
        self.assertTrue(res.get("bit_identical"))
        self.assertEqual(res.get("match_percentage"), 100.0)

        # Test invalid symbol returns non-zero error
        code, stdout, stderr = run_python_tool(diff_script, ["InvalidNonExistentSymbol999"])
        self.assertNotEqual(code, 0, "diff.py must return non-zero for unknown symbols")


if __name__ == "__main__":
    unittest.main()
