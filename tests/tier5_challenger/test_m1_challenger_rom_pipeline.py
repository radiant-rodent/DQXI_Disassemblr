"""Tier 5: Challenger 1 - ROM Extraction and Bit-Matching Repacking Pipeline Stress Tests.

Empirically validates:
1. Exact bit-for-byte SHA-256 match between repacked ROM and reference cartridge.
2. Integrity of all extracted baseline containers in original/ against hashes.sha256.
3. Dynamic code replacement injection via tools/repack_rom.py --code.
4. Failure modes and error exits on missing directories, missing components, and truncated files.
5. Hash verification failure detection in tools/verify.py.
6. Unexpected EOF handling during extraction of truncated ROMs in tools/extract_rom.py.
7. Reference repository preservation (zero modifications to reference project).
8. Failure mode on uncompressible custom code payloads (exposing blz.py IndexError defect).
"""

import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.common import (
    BUILD_DIR,
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    ORIGINAL_DIR,
    PROJECT_ROOT,
    TOOLS_DIR,
    run_python_tool,
)
import tools.blz as blz


class TestM1ChallengerRomPipeline(unittest.TestCase):
    """Empirical challenge suite for Milestone 1 ROM pipeline."""

    @classmethod
    def setUpClass(cls):
        cls.ref_rom_path = Path(r"..\reference project\DQXI.3ds")
        cls.repack_tool = TOOLS_DIR / "repack_rom.py"
        cls.extract_tool = TOOLS_DIR / "extract_rom.py"
        cls.verify_tool = TOOLS_DIR / "verify.py"
        cls.repacked_rom = BUILD_DIR / "DQXI.3ds"

    def test_01_repack_rom_bit_matching_sha256(self):
        """Verify repacked ROM is exactly 4,294,967,296 bytes and SHA-256 matches retail cartridge."""
        self.assertTrue(self.repacked_rom.is_file(), f"Repacked ROM '{self.repacked_rom}' not found")
        self.assertEqual(
            self.repacked_rom.stat().st_size,
            EXPECTED_SIZES["rom"],
            "Repacked ROM size does not match 4,294,967,296 bytes",
        )

        hasher = hashlib.sha256()
        with open(self.repacked_rom, "rb") as f:
            while chunk := f.read(16 * 1024 * 1024):
                hasher.update(chunk)
        self.assertEqual(
            hasher.hexdigest(),
            EXPECTED_HASHES["rom"],
            "Repacked ROM SHA-256 digest mismatch!",
        )

    def test_02_extracted_baseline_containers_integrity(self):
        """Verify all 16 extracted components in original/ match hashes.sha256 baseline."""
        manifest = ORIGINAL_DIR / "hashes.sha256"
        self.assertTrue(manifest.is_file(), "original/hashes.sha256 missing")

        code, stdout, stderr = run_python_tool(self.verify_tool, [str(manifest)])
        self.assertEqual(code, 0, f"tools/verify.py failed on manifest:\n{stdout}\n{stderr}")
        self.assertIn("OVERALL VERIFICATION: PASS", stdout)

    def test_03_dynamic_code_injection_in_repacker(self):
        """Verify dynamic custom executable injection via --code updates ExeFS header and NCCH0 superblock hash."""
        decomp_path = ORIGINAL_DIR / "exefs" / "code.decompressed.bin"
        self.assertTrue(decomp_path.is_file(), "code.decompressed.bin missing")

        with open(decomp_path, "rb") as f:
            decomp_data = bytearray(f.read())

        # Modify a sentinel byte at offset 0x200000
        sentinel_offset = 0x200000
        decomp_data[sentinel_offset] ^= 0x55
        custom_hash = hashlib.sha256(decomp_data).hexdigest()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_code = Path(tmp_dir) / "custom_code.bin"
            tmp_out_rom = Path(tmp_dir) / "custom_rom.3ds"

            with open(tmp_code, "wb") as f:
                f.write(decomp_data)

            code, stdout, stderr = run_python_tool(
                self.repack_tool,
                [
                    "--in", str(ORIGINAL_DIR),
                    "--out", str(tmp_out_rom),
                    "--code", str(tmp_code),
                ],
            )
            self.assertEqual(code, 0, f"Repacking with custom code failed:\n{stdout}\n{stderr}")
            self.assertTrue(tmp_out_rom.is_file())

            # Read ExeFS header and NCCH 0 header from generated ROM
            with open(tmp_out_rom, "rb") as f:
                rom_head = f.read(0x438000)

            # NCCH 0 ExeFS superblock hash is at 0x4000 + 0x1C0
            ncch_exefs_hash = rom_head[0x41C0:0x41E0]
            # ExeFS header is at 0x6C00
            exefs_hdr = rom_head[0x6C00:0x6E00]
            self.assertEqual(ncch_exefs_hash, hashlib.sha256(exefs_hdr).digest())

            # ExeFS entry 0 is .code
            off0, sz0 = struct.unpack_from("<II", exefs_hdr, 8)
            code_payload = rom_head[0x6E00 + off0 : 0x6E00 + off0 + sz0]
            self.assertEqual(exefs_hdr[0x1E0:0x200], hashlib.sha256(code_payload).digest())

            # Decompress injected code and verify modified byte
            extracted_code = blz.decompress(code_payload)
            self.assertEqual(hashlib.sha256(extracted_code).hexdigest(), custom_hash)
            self.assertEqual(extracted_code[sentinel_offset], decomp_data[sentinel_offset])

    def test_04_missing_orig_dir_graceful_exit(self):
        """Verify tools/repack_rom.py exits with code 1 when input directory does not exist."""
        code, stdout, stderr = run_python_tool(
            self.repack_tool,
            ["nonexistent_directory_xyz", str(BUILD_DIR / "dummy.3ds")],
        )
        self.assertEqual(code, 1)
        self.assertIn("not found", (stdout + stderr).lower())

    def test_05_missing_component_files_graceful_exit(self):
        """Verify tools/repack_rom.py exits with code 1 when a required container file is missing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create minimal dir missing romfs.bin
            for f in ["ncsd_header.bin", "card_info.bin", "ncch0_header.bin", "exheader.bin", "logo.bin", "plain.bin"]:
                shutil.copy(ORIGINAL_DIR / f, tmp_path / f)
            (tmp_path / "exefs").mkdir()
            for f in [".code", "banner", "icon"]:
                shutil.copy(ORIGINAL_DIR / "exefs" / f, tmp_path / "exefs" / f)

            code, stdout, stderr = run_python_tool(
                self.repack_tool,
                [str(tmp_path), str(BUILD_DIR / "dummy.3ds")],
            )
            self.assertEqual(code, 1)
            self.assertIn("missing", (stdout + stderr).lower())

    def test_06_truncated_component_files_detected(self):
        """Verify tools/repack_rom.py detects truncated container components with size mismatch."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            for f in ["ncsd_header.bin", "card_info.bin", "ncch0_header.bin", "exheader.bin", "logo.bin", "plain.bin"]:
                shutil.copy(ORIGINAL_DIR / f, tmp_path / f)
            (tmp_path / "exefs").mkdir()
            for f in [".code", "banner", "icon"]:
                shutil.copy(ORIGINAL_DIR / "exefs" / f, tmp_path / "exefs" / f)
            # Truncate card_info.bin to 50 bytes instead of 0x3E00 (15,872)
            with open(tmp_path / "card_info.bin", "wb") as f:
                f.write(b"\x00" * 50)

            code, stdout, stderr = run_python_tool(
                self.repack_tool,
                [str(tmp_path), str(BUILD_DIR / "dummy.3ds")],
            )
            self.assertEqual(code, 1)
            self.assertIn("size mismatch", (stdout + stderr).lower())

    def test_07_corrupted_hash_manifest_detected(self):
        """Verify tools/verify.py detects corrupt hashes and exits with code 1."""
        with tempfile.NamedTemporaryFile("w", suffix=".sha256", delete=False) as tf:
            tf.write("0" * 64 + "  ncsd_header.bin\n")
            bad_manifest = Path(tf.name)

        try:
            # Place in original/ so relative path resolves
            staged = ORIGINAL_DIR / "test_bad.sha256"
            shutil.copy(bad_manifest, staged)
            code, stdout, stderr = run_python_tool(self.verify_tool, [str(staged)])
            self.assertEqual(code, 1)
            self.assertIn("OVERALL VERIFICATION: FAIL", stdout + stderr)
        finally:
            if bad_manifest.is_file():
                bad_manifest.unlink()
            staged = ORIGINAL_DIR / "test_bad.sha256"
            if staged.is_file():
                staged.unlink()

    def test_08_truncated_rom_extraction_handled(self):
        """Verify tools/extract_rom.py detects unexpected EOF on truncated input ROM."""
        with tempfile.NamedTemporaryFile(suffix=".3ds", delete=False) as tf:
            tf.write(b"NCSD" + b"\x00" * 1024)
            trunc_rom = Path(tf.name)

        with tempfile.TemporaryDirectory() as out_dir:
            try:
                code, stdout, stderr = run_python_tool(
                    self.extract_tool,
                    [str(trunc_rom), out_dir],
                )
                self.assertEqual(code, 1)
                self.assertIn("unexpected eof", (stdout + stderr).lower())
            finally:
                if trunc_rom.is_file():
                    trunc_rom.unlink()

    def test_09_cli_flag_handling(self):
        """Verify CLI tools support both positional and flagged arguments cleanly."""
        code, stdout, stderr = run_python_tool(
            self.verify_tool,
            ["--rom", str(self.repacked_rom)],
        )
        self.assertEqual(code, 0)
        self.assertIn("OVERALL VERIFICATION: PASS", stdout)

    def test_10_reference_repo_immutability(self):
        r"""Verify ..\reference project git status confirms zero unexpected tracked file modifications beyond baseline."""
        from tests.common import BASELINE_TRACKED_MODIFICATIONS
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=r"..\reference project",
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        modified_files = {l[2:].strip().replace("\\", "/") for l in res.stdout.splitlines() if not l.startswith("??")}
        unexpected = modified_files - BASELINE_TRACKED_MODIFICATIONS
        self.assertEqual(
            len(unexpected),
            0,
            f"Reference repository has unexpected modified tracked files: {unexpected}",
        )


    def test_11_uncompressible_custom_code_failure_mode(self):
        """DEFECT ADVERSARIAL TEST: Verify blz.compress raises ValueError instead of crashing with IndexError on uncompressible input."""
        import random
        rng = random.Random(1337)
        noise = bytes(rng.getrandbits(8) for _ in range(1024))
        # Expected behavior: raises ValueError('Data could not be compressed')
        # Current defect: crashes with IndexError: bytearray index out of range
        with self.assertRaises(ValueError, msg="Uncompressible data should raise ValueError('Data could not be compressed')"):
            blz.compress(noise)


if __name__ == "__main__":
    unittest.main()
