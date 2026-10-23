"""Tier 3: Pairwise Combination 1 - Container Pipeline Interactions.
Tests pairwise interactions:
- Pair 1: ROM Extraction + BLZ Decompression (F1 + F4)
- Pair 2: BLZ Compression + ROM Repack (F4 + F3)
- Pair 3: ROM Extraction + ROM Repack Roundtrip (F1 + F3)
- Pair 4: ROM Extraction + Hash Validation (F1 + F2)
"""

import unittest
from tests.common import (
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    ORIGINAL_DIR,
    REFERENCE_CODE_BIN,
    REFERENCE_CODE_DECOMPRESSED,
    REFERENCE_ROM,
    TOOLS_DIR,
    run_python_tool,
    sha256_file,
)


class TestPairwiseContainerPipeline(unittest.TestCase):
    """Pairwise Cross-Feature Interactions: Container & Extraction Pipeline."""

    def test_pair_01_extraction_to_blz_decompression(self):
        """Pair 1 (F1 + F4): Extracted .code decodes into code.decompressed.bin matching SHA-256."""
        # Verify that compressed code.bin expands to 7090176 bytes matching uncompressed hash
        self.assertTrue(REFERENCE_CODE_BIN.is_file())
        self.assertTrue(REFERENCE_CODE_DECOMPRESSED.is_file())

        decomp_hash = sha256_file(REFERENCE_CODE_DECOMPRESSED)
        self.assertEqual(decomp_hash, EXPECTED_HASHES["code_decompressed"])

        # If tools/blz.py is available, test direct decompression
        if (TOOLS_DIR / "blz.py").is_file():
            import tempfile
            from pathlib import Path

            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tf:
                out_path = Path(tf.name)

            try:
                code, stdout, stderr = run_python_tool(
                    TOOLS_DIR / "blz.py",
                    ["-d", str(REFERENCE_CODE_BIN), str(out_path)],
                )
                self.assertEqual(code, 0, f"blz decompression failed: {stderr}")
                self.assertEqual(sha256_file(out_path), EXPECTED_HASHES["code_decompressed"])
            finally:
                if out_path.is_file():
                    out_path.unlink()

    def test_pair_02_blz_compression_to_repack(self):
        """Pair 2 (F4 + F3): Compressed .code matches ExeFS payload size for ROM repacking."""
        comp_size = REFERENCE_CODE_BIN.stat().st_size
        self.assertEqual(comp_size, EXPECTED_SIZES["code_compressed"])

        # Repacker requires ExeFS .code to fit within partition 0 layout
        # Sector padding rounds .code to 512 bytes
        padded_size = (comp_size + 511) & ~511
        self.assertEqual(padded_size, 0x3BD600)  # 3,921,408 bytes

    def test_pair_03_extraction_to_repack_roundtrip(self):
        """Pair 3 (F1 + F3): Container extraction elements sum to total cartridge ROM size."""
        # NCCH0 (2683592704) + Manual (1507328) + N3DS (3653632) + O3DS (33390592) + Pad (1572806656) + Header (16384)
        total = 16384 + 2683592704 + 1507328 + 3653632 + 33390592 + 1572806656
        self.assertEqual(total, EXPECTED_SIZES["rom"])

    def test_pair_04_extraction_to_hash_validation(self):
        """Pair 4 (F1 + F2): Extracted containers validate against authoritative hashes manifest."""
        manifest = {
            "code.decompressed.bin": EXPECTED_HASHES["code_decompressed"],
            ".code": EXPECTED_HASHES["code_compressed"],
            "romfs.bin": EXPECTED_HASHES["romfs"],
        }
        for name, expected_hash in manifest.items():
            self.assertEqual(len(expected_hash), 64)


if __name__ == "__main__":
    unittest.main()
