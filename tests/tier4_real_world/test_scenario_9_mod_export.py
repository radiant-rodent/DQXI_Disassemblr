"""Tier 4: Scenario 9 - mod workspace to a real 3DS/2DS.

Features exercised: the `mod/` workspace convention, table edit -> PACK staging,
Luma3DS LayeredFS export, full `.3ds` rebuild and the exporter's own validation,
and the installable CIA target (`tools/ctr_cia.py`).

Every export here is a real run of `tools/export_mod.py` against the retail
baseline in `original/`; nothing is stubbed. The `.3ds` and CIA cases take about
a minute each because they write and check genuine multi-gigabyte images - the
byte-identical empty-mod image is the proof that the exporter does not invent
changes, and the CIA is parsed field by field rather than trusted.
"""

import hashlib
import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from tests.common import (
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    ORIGINAL_DIR,
    PROJECT_ROOT,
    TOOLS_DIR,
    run_python_tool,
    sha256_file,
)

EXPORT_TOOL = TOOLS_DIR / "export_mod.py"
RETAIL_TITLE_ID = "0004000000199200"
SYSCMN_ITEM = PROJECT_ROOT / "game_data" / "packs" / "syscmn" / "item.bxon"
ROM_SIZE = 4_294_967_296
CIA_ALIGN = 64


def _align(x: int) -> int:
    return (x + CIA_ALIGN - 1) // CIA_ALIGN * CIA_ALIGN


def read_cia_sections(path: Path) -> dict:
    """Parse a CIA independently of the tool that wrote it (the test's own reader)."""
    with open(path, "rb") as f:
        header = f.read(0x2020)
        header_size, typ, ver, cert_size, ticket_size, tmd_size, meta_size, content_size = (
            struct.unpack_from("<IHHIIIIQ", header, 0))
        cert_off = _align(header_size)
        ticket_off = cert_off + _align(cert_size)
        tmd_off = ticket_off + _align(ticket_size)
        content_off = tmd_off + _align(tmd_size)
        meta_off = content_off + content_size
        return {
            "header": header,
            "header_size": header_size,
            "type": typ,
            "version": ver,
            "cert_size": cert_size,
            "ticket_size": ticket_size,
            "tmd_size": tmd_size,
            "meta_size": meta_size,
            "content_size": content_size,
            "content_mask": struct.unpack_from("<I", header, 0x20)[0],
            "cert_off": cert_off,
            "ticket_off": ticket_off,
            "tmd_off": tmd_off,
            "content_off": content_off,
            "meta_off": meta_off,
            "certs": _read_at(f, cert_off, cert_size),
            "ticket": _read_at(f, ticket_off, ticket_size),
            "tmd": _read_at(f, tmd_off, tmd_size),
            "meta": _read_at(f, meta_off, meta_size),
        }


def _read_at(f, offset: int, size: int) -> bytes:
    f.seek(offset)
    return f.read(size)


def _tmd_contents(tmd: bytes) -> list[dict]:
    count = struct.unpack_from(">H", tmd, 0x1DE)[0]
    chunks = tmd[0xB04:0xB04 + 0x30 * count]
    result = []
    for i in range(count):
        content_id, index, flags, size = struct.unpack_from(">IHHQ", chunks, i * 0x30)
        result.append({
            "id": content_id,
            "index": index,
            "flags": flags,
            "size": size,
            "sha256": chunks[i * 0x30 + 0x10:i * 0x30 + 0x30].hex(),
        })
    return result


def _sha256_file_range(path: Path, offset: int, size: int) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        f.seek(offset)
        while size:
            block = f.read(min(size, 16 * 1024 * 1024))
            if not block:
                raise AssertionError(f"short read at 0x{offset:X}")
            h.update(block)
            size -= len(block)
    return h.hexdigest()


def have_baseline() -> bool:
    return (ORIGINAL_DIR / "romfs.bin").is_file() and (
        ORIGINAL_DIR / "exefs" / "code.decompressed.bin"
    ).is_file()


@unittest.skipUnless(EXPORT_TOOL.is_file(), "tools/export_mod.py is missing")
@unittest.skipUnless(have_baseline(), "original/ baseline is not extracted")
class TestScenario9ModExport(unittest.TestCase):
    """Scenario 9: export a mod workspace for real hardware."""

    @classmethod
    def setUpClass(cls):
        from tools import export_mod

        cls.export_mod = export_mod
        cls.tmp = Path(tempfile.mkdtemp(prefix="dqxi_export_"))

        # A mod with exactly one changed table: row 0's buy_price (offset 0x18).
        cls.mod = cls.tmp / "mod"
        (cls.mod / "romfs").mkdir(parents=True)
        (cls.mod / "mod.json").write_text(
            json.dumps({"name": "Export test", "version": "1.0", "author": "tests"}),
            encoding="utf-8",
        )
        edited = bytearray(SYSCMN_ITEM.read_bytes())
        cls.old_price = struct.unpack_from("<I", edited, 0x18)[0]
        struct.pack_into("<I", edited, 0x18, 4321)
        replacement = cls.tmp / "item_edited.bxon"
        replacement.write_bytes(bytes(edited))
        cls.staged = export_mod.stage_table(
            "syscmn/item.json", replacement, cls.mod, work_dir=cls.tmp / "work")
        cls.pack_file = cls.mod / "romfs" / "syscmn.pack"

        cls.out = cls.tmp / "out"
        cls.luma_code, cls.luma_out, cls.luma_err = run_python_tool(
            EXPORT_TOOL, ["--target", "luma", "--mod", str(cls.mod), "--out", str(cls.out)],
            timeout=1800)
        # Each run rewrites out/EXPORT_REPORT.json, so keep the luma report now.
        report_file = cls.out / "EXPORT_REPORT.json"
        cls.luma_report = (json.loads(report_file.read_text(encoding="utf-8"))
                           if report_file.is_file() else {})
        cls.rom_code, cls.rom_out, cls.rom_err = run_python_tool(
            EXPORT_TOOL, ["--target", "3ds", "--mod", str(cls.mod), "--out", str(cls.out)],
            timeout=1800)
        cls.report = json.loads(report_file.read_text(encoding="utf-8"))
        # The CIA target builds its own .3ds first: it must work on its own, not
        # only as part of `--target all`.
        cls.cia_code, cls.cia_out, cls.cia_err = run_python_tool(
            EXPORT_TOOL, ["--target", "cia", "--mod", str(cls.mod), "--out", str(cls.out)],
            timeout=1800)
        cls.cia_report = json.loads(report_file.read_text(encoding="utf-8"))
        cls.cia_path = cls.out / "cia" / "DQXI_modded.cia"
        cls.cia = read_cia_sections(cls.cia_path) if cls.cia_path.is_file() else None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # -- staging ----------------------------------------------------------- #
    def test_schema_names_the_pack_that_holds_the_table(self):
        """A schema entry must say which RomFS PACK a table lives in."""
        pack, member = self.export_mod.schema_pack_for("syscmn/item.json")
        self.assertEqual(pack, "syscmn.pack")
        self.assertEqual(member, "item.bxon")

    def test_staged_pack_replaces_the_member_and_lands_in_the_mod(self):
        """--stage-table writes the *pack*, not the loose table, into mod/romfs."""
        self.assertTrue(self.pack_file.is_file(), "staged pack missing from mod/romfs")
        self.assertFalse((self.mod / "romfs" / "item.bxon").exists(),
                         "a loose table must never appear in mod/romfs")
        self.assertGreater(self.pack_file.stat().st_size, 1000)
        # The vetted PACK reader must find the edited value in the staged pack
        # (tools/pack.py decompresses PACA itself).
        from tools import pack
        parsed = pack.Pack.parse(self.pack_file.read_bytes())
        member = next(e for e in parsed.entries if e.name == "item.bxon")
        self.assertEqual(struct.unpack_from("<I", member.data, 0x18)[0], 4321)

    # -- Luma3DS LayeredFS -------------------------------------------------- #
    def test_luma_export_contains_only_the_changed_file(self):
        self.assertEqual(self.luma_code, 0, f"luma export failed:\n{self.luma_out}\n{self.luma_err}")
        title_dir = self.out / "luma" / "titles" / RETAIL_TITLE_ID
        romfs_dir = title_dir / "romfs"
        files = sorted(p.relative_to(romfs_dir).as_posix()
                       for p in romfs_dir.rglob("*") if p.is_file())
        self.assertEqual(files, ["syscmn.pack"],
                         "the Luma folder must hold the changed file and nothing else")
        self.assertEqual((romfs_dir / "syscmn.pack").read_bytes(), self.pack_file.read_bytes())
        self.assertFalse((title_dir / "code.ips").exists(), "no native change, so no code.ips")
        self.assertFalse((title_dir / "code.bin").exists())
        self.assertTrue((self.out / "luma" / "README.txt").is_file())
        self.assertTrue(self.luma_report["targets"]["luma"]["valid"])

    def test_luma_title_id_comes_from_the_cartridge(self):
        """The title folder must be the NCCH program id, not a hard-coded guess."""
        head = (ORIGINAL_DIR / "ncch0_header.bin").read_bytes()
        program_id = struct.unpack_from("<Q", head, 0x118)[0]
        self.assertEqual(f"{program_id:016X}", RETAIL_TITLE_ID)
        self.assertTrue((self.out / "luma" / "titles" / f"{program_id:016X}").is_dir())
        self.assertEqual(self.report["title_id"], RETAIL_TITLE_ID)

    # -- rebuilt .3ds ------------------------------------------------------- #
    def test_rebuilt_3ds_is_a_full_valid_cartridge(self):
        self.assertEqual(self.rom_code, 0, f"3ds export failed:\n{self.rom_out}\n{self.rom_err}")
        rom = self.out / "3ds" / "DQXI_modded.3ds"
        self.assertEqual(rom.stat().st_size, ROM_SIZE)
        self.assertNotEqual(sha256_file(rom), EXPECTED_HASHES["rom"],
                            "a modded image must not hash like retail")
        target = self.report["targets"]["3ds"]
        validation = target["validation"]
        self.assertTrue(validation["ok"])
        self.assertTrue(validation["exefs"]["all_hashes_ok"])
        self.assertTrue(validation["exefs"]["superblock_ok"])
        self.assertTrue(validation["exheader_hash_ok"])
        self.assertTrue(validation["logo_hash_ok"])
        self.assertTrue(validation["romfs_superblock_ok"])
        self.assertTrue(validation["ivfc"]["ok"], validation["ivfc"])
        self.assertEqual(validation["ivfc"]["bad_level2"], 0)
        # The retail executable is still inside (no native change this time).
        self.assertEqual(validation["code_uncompressed_sha256"],
                         EXPECTED_HASHES["code_decompressed"])

    def test_modified_table_is_in_the_rebuilt_romfs_with_valid_hashes(self):
        """Re-open the image independently: the edited pack is there, hashes hold."""
        rom = self.out / "3ds" / "DQXI_modded.3ds"
        with open(rom, "rb") as f:
            ncch = self.export_mod.parse_ncch(f, 0x4000)
            romfs_base = 0x4000 + ncch["romfs_offset"]
            superblock = self.export_mod.sha256_region(f, romfs_base, ncch["romfs_hash_size"])
            self.assertEqual(superblock, ncch["romfs_superblock"].hex(),
                             "NCCH RomFS superblock hash does not cover the rebuilt RomFS")
            ivfc = self.export_mod._verify_ivfc(f, romfs_base, "DQXI_modded.3ds")
        self.assertTrue(ivfc["ok"], ivfc)
        self.assertEqual(ivfc["data_blocks"], 648_986)

        index = self.export_mod.RomFsIndex(rom, romfs_base)
        self.assertEqual(len(index.files), 21_250, "the rebuilt RomFS must keep every retail file")
        self.assertIn("/syscmn.pack", index.files)
        self.assertEqual(index.read("/syscmn.pack"), self.pack_file.read_bytes())
        # A neighbouring file must be untouched.
        self.assertEqual(index.read("/gamecmn.pack"),
                         (PROJECT_ROOT / "game_data" / "romfs" / "gamecmn.pack").read_bytes())
        # And the standalone romfs.bin that was embedded matches the image.
        romfs_copy = self.out / "3ds" / "romfs.bin"
        self.assertEqual(sha256_file(romfs_copy), self.report["targets"]["3ds"]["romfs_sha256"])

    def test_report_records_the_change_and_the_mod_metadata(self):
        report = self.report
        self.assertEqual(report["mod"]["name"], "Export test")
        self.assertEqual(report["title_id"], RETAIL_TITLE_ID)
        changes = report["romfs_changes"]
        self.assertEqual([c["path"] for c in changes], ["/syscmn.pack"])
        self.assertEqual(changes[0]["sha256"], sha256_file(self.pack_file))
        self.assertEqual(changes[0]["original_size"],
                         (PROJECT_ROOT / "game_data" / "romfs" / "syscmn.pack").stat().st_size)

    # -- empty mod ---------------------------------------------------------- #
    def test_empty_mod_exports_a_byte_identical_3ds(self):
        """No changes at all must reproduce the retail cartridge exactly."""
        empty_mod = self.tmp / "empty_mod"
        empty_mod.mkdir(exist_ok=True)
        out = self.tmp / "out_empty"
        code, stdout, stderr = run_python_tool(
            EXPORT_TOOL, ["--target", "3ds", "--mod", str(empty_mod), "--out", str(out)],
            timeout=1800)
        self.assertEqual(code, 0, f"empty-mod export failed:\n{stdout}\n{stderr}")
        rom = out / "3ds" / "DQXI_modded.3ds"
        self.assertEqual(rom.stat().st_size, EXPECTED_SIZES["rom"])
        self.assertEqual(sha256_file(rom), EXPECTED_HASHES["rom"],
                         "an empty mod must reproduce the retail image")
        report = json.loads((out / "EXPORT_REPORT.json").read_text(encoding="utf-8"))
        self.assertTrue(report["targets"]["3ds"]["retail_identical"])
        self.assertEqual(report["romfs_changes"], [])

    # -- native code -------------------------------------------------------- #
    def test_changed_native_code_becomes_a_reproducible_code_ips(self):
        mod = self.tmp / "code_mod"
        (mod / "code").mkdir(parents=True, exist_ok=True)
        retail_code = (ORIGINAL_DIR / "exefs" / "code.decompressed.bin").read_bytes()
        patched = bytearray(retail_code)
        for offset in (0x6C2D80, 0x6C2E00, 0x6C2F00):   # alignment padding at the image end
            patched[offset] ^= 0xFF
        (mod / "code" / "code.bin").write_bytes(bytes(patched))
        out = self.tmp / "out_code"
        code, stdout, stderr = run_python_tool(
            EXPORT_TOOL, ["--target", "luma", "--mod", str(mod), "--out", str(out)],
            timeout=600)
        self.assertEqual(code, 0, f"code export failed:\n{stdout}\n{stderr}")
        title_dir = out / "luma" / "titles" / RETAIL_TITLE_ID
        self.assertFalse((title_dir / "code.bin").exists(), "IPS is the default, not a full copy")
        ips = (title_dir / "code.ips").read_bytes()
        self.assertLess(len(ips), 512, "three changed bytes must give a tiny IPS")
        self.assertEqual(self.export_mod.apply_ips(retail_code, ips), bytes(patched),
                         "code.ips must reproduce mod/code/code.bin exactly")
        self.assertEqual(sorted(p.name for p in title_dir.iterdir()), ["code.ips", "romfs"])
        # No RomFS change in this mod, so the layered RomFS folder is empty.
        self.assertEqual([p for p in (title_dir / "romfs").rglob("*") if p.is_file()], [])

    # -- level editor path -------------------------------------------------- #
    def test_level_patch_can_be_staged_into_the_mod_workspace(self):
        """The level editor's patched map pack must reach mod/romfs, not just a ROM."""
        patched_bxon = PROJECT_ROOT / "game_assets" / "maps" / "b001_101a" / "level3d.patched.bxon"
        if not patched_bxon.is_file():
            self.skipTest("no exported level patch (open the editor and export BXON first)")
        mod = self.tmp / "map_mod"
        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "patch_game.py", ["--map", "b001_101a", "--stage-mod", str(mod)],
            timeout=600)
        self.assertEqual(code, 0, f"staging the level patch failed:\n{stdout}\n{stderr}")
        staged = mod / "romfs" / "level3d" / "b001_101a.pack"
        self.assertTrue(staged.is_file(), "patched map pack missing from mod/romfs/level3d")
        # The mod workspace was not touched (the tool wrote into the copy we passed).
        out = self.tmp / "out_map"
        code, stdout, stderr = run_python_tool(
            EXPORT_TOOL, ["--target", "luma", "--mod", str(mod), "--out", str(out)],
            timeout=600)
        self.assertEqual(code, 0, f"exporting the map mod failed:\n{stdout}\n{stderr}")
        exported = out / "luma" / "titles" / RETAIL_TITLE_ID / "romfs" / "level3d" / "b001_101a.pack"
        self.assertEqual(exported.read_bytes(), staged.read_bytes())

    # -- refusals ----------------------------------------------------------- #
    def test_new_files_are_refused_on_luma_but_added_on_the_full_image(self):
        """LayeredFS cannot mount a path the retail RomFS lacks; the full-image
        targets rebuild the Level-3 metadata tables and mount it."""
        mod = self.tmp / "new_file"
        (mod / "romfs").mkdir(parents=True, exist_ok=True)
        (mod / "romfs" / "my_own.pack").write_bytes(b"PACK" + bytes(64))
        code, stdout, stderr = run_python_tool(
            EXPORT_TOOL, ["--target", "luma", "--mod", str(mod), "--out", str(self.tmp / "out_bad")],
            timeout=600)
        self.assertEqual(code, 2)
        self.assertIn("LayeredFS can only replace RomFS paths", stderr)

        (mod / "romfs" / "my_own.pack").write_bytes(b"PACK" + bytes(64))
        out = self.tmp / "out_3ds"
        code, stdout, stderr = run_python_tool(
            EXPORT_TOOL, ["--target", "3ds", "--no-rom", "--mod", str(mod), "--out", str(out)],
            timeout=1800)
        self.assertEqual(code, 0, f"export with an added file failed:\n{stdout}\n{stderr}")
        index = self.export_mod.RomFsIndex(out / "3ds" / "romfs.bin")
        self.assertIn("/my_own.pack", index.files)
        self.assertEqual(index.read("/my_own.pack"), b"PACK" + bytes(64))

    def test_wrong_size_native_code_is_refused(self):
        mod = self.tmp / "bad_code"
        (mod / "code").mkdir(parents=True, exist_ok=True)
        (mod / "code" / "code.bin").write_bytes(bytes(1024))
        code, stdout, stderr = run_python_tool(
            EXPORT_TOOL, ["--target", "luma", "--mod", str(mod), "--out", str(self.tmp / "out_bad2")],
            timeout=600)
        self.assertEqual(code, 2)
        self.assertIn("retail decompressed size", stderr)

    def test_cia_refuses_no_rom_because_it_needs_the_full_image(self):
        """--no-rom only produces romfs.bin; a CIA needs the .3ds, so say so."""
        code, stdout, stderr = run_python_tool(
            EXPORT_TOOL,
            ["--target", "cia", "--no-rom", "--mod", str(self.mod), "--out", str(self.tmp / "out_cia_nr")],
            timeout=600)
        self.assertEqual(code, 2)
        self.assertIn("cannot be combined with the CIA target", stderr)

    def test_cia_builder_refuses_an_encrypted_image(self):
        """A zero title key is only valid for decrypted content; fail loudly otherwise."""
        from tools import ctr_cia
        img = self.tmp / "encrypted.3ds"
        data = bytearray(0x8000)
        data[0x100:0x104] = b"NCSD"                          # NCSD magic after the signature
        struct.pack_into("<I", data, 0x104, len(data) // 0x200)
        struct.pack_into("<II", data, 0x120, 0x4000 // 0x200, 0x4000 // 0x200)  # partition 0
        struct.pack_into("<Q", data, 0x190, 0)               # partition id
        ncch = 0x4000
        data[ncch + 0x100:ncch + 0x104] = b"NCCH"
        struct.pack_into("<I", data, ncch + 0x104, 0x4000 // 0x200)
        struct.pack_into("<Q", data, ncch + 0x118, 0x0004000000199200)
        # flags[7] (the "no crypto" bit) stays 0: this image claims to be encrypted.
        img.write_bytes(bytes(data))
        with self.assertRaises(ValueError) as caught:
            ctr_cia.build_cia(img, self.tmp / "should_not_exist.cia")
        self.assertIn("not a decrypted image", str(caught.exception))
        self.assertFalse((self.tmp / "should_not_exist.cia").exists())

    # -- CIA ---------------------------------------------------------------- #
    def test_cia_target_builds_a_verified_archive(self):
        """`--target cia` really writes one, and the shipped verifier accepts it."""
        self.assertEqual(self.cia_code, 0, f"CIA export failed:\n{self.cia_out}\n{self.cia_err}")
        self.assertFalse((self.out / "cia" / "BLOCKED.md").exists(),
                         "the old BLOCKED note must not survive next to a real CIA")
        self.assertTrue(self.cia_path.is_file(), "out/cia/DQXI_modded.cia is missing")
        target = self.cia_report["targets"]["cia"]
        self.assertEqual(target["status"], "ok")
        self.assertTrue(target["valid"])
        self.assertFalse(target["signed"], "the CIA must be labelled fakesigned")
        self.assertEqual(target["source_rom"], str(self.out / "3ds" / "DQXI_modded.3ds"))
        self.assertEqual(target["source_rom_sha256"],
                         self.report["targets"]["3ds"]["rom_sha256"])
        self.assertEqual(self.cia_path.stat().st_size, target["size"])
        self.assertEqual(sha256_file(self.cia_path), target["sha256"])
        self.assertGreater(target["size"], 2_000_000_000)
        self.assertLess(target["size"], ROM_SIZE)

        from tools import ctr_cia
        problems = ctr_cia.verify_cia(self.cia_path)
        self.assertEqual(problems, [], "the CIA does not re-parse cleanly")
        info = ctr_cia.parse_cia(self.cia_path)
        self.assertTrue(info["valid"])
        self.assertEqual(info["title_id"], RETAIL_TITLE_ID)
        self.assertEqual(info["num_contents"], 2)
        self.assertEqual(info["cert_size"], 0xA00)
        self.assertEqual(info["ticket_size"], 0x350)
        self.assertEqual(info["tmd_size"], 0xB04 + 2 * 0x30)
        self.assertEqual(info["meta_size"], 0x3AC0)

    def test_cia_header_sections_and_certificate_chain(self):
        """Header sizes, content mask and the copied Nintendo certificate chain."""
        self.assertIsNotNone(self.cia, "no CIA was built")
        cia = self.cia
        self.assertEqual(cia["header_size"], 0x2020)
        self.assertEqual(cia["type"], 0)
        self.assertEqual(cia["content_size"],
                         sum(_align(c["size"]) for c in _tmd_contents(cia["tmd"])))
        # Contents 0 (game) and 1 (manual) are present; nothing else.
        self.assertEqual(cia["content_mask"], 0xC0)
        # The chain is the three genuine certificates from the update partition:
        # CA (RSA-4096), CP (TMD signer) and XS (ticket signer).  Each 0x40-byte
        # issuer field is "Root-CA00000003" padded with zeros; the certificate's
        # own name is its key id.
        self.assertEqual(cia["cert_size"], 0xA00)
        for key_id in (b"CA00000003", b"CP0000000b", b"XS0000000c"):
            self.assertIn(key_id, cia["certs"], key_id.decode())
        self.assertEqual(cia["certs"].count(b"Root-CA00000003"), 2,
                         "the CP and XS certificates are issued by the Root-CA")
        self.assertEqual(cia["ticket_size"], 0x350)

    def test_cia_ticket_is_fakesigned_and_names_the_game(self):
        ticket = self.cia["ticket"]
        self.assertEqual(ticket[4:0x104], bytes(0x100), "ticket signature must be blank")
        self.assertEqual(ticket[0x1BF:0x1CF], bytes(0x10), "title key must be zero (no crypto)")
        self.assertEqual(struct.unpack_from(">Q", ticket, 0x1DC)[0], 0x0004000000199200)
        self.assertEqual(struct.unpack_from(">Q", ticket, 0x1D0)[0], 0x0004000000199200)
        self.assertEqual(struct.unpack_from(">I", ticket, 0x1D8)[0], 0, "not console-locked")
        self.assertEqual(ticket[0x1F0], 0, "permanent license")
        self.assertEqual(ticket[0x1F1], 0, "common key index 0")

    def test_cia_tmd_hashes_match_and_describe_the_two_contents(self):
        tmd = self.cia["tmd"]
        self.assertEqual(struct.unpack_from(">Q", tmd, 0x18C)[0], 0x0004000000199200)
        self.assertEqual(struct.unpack_from(">I", tmd, 0x194)[0], 0x40, "CTR title type")
        self.assertEqual(struct.unpack_from(">H", tmd, 0x1DE)[0], 2)
        self.assertEqual(struct.unpack_from(">H", tmd, 0x1E0)[0], 0, "boot content 0")
        exheader = (ORIGINAL_DIR / "exheader.bin").read_bytes()
        self.assertEqual(struct.unpack_from("<I", tmd, 0x19A)[0],
                         struct.unpack_from("<Q", exheader, 0x1C0)[0],
                         "save-data size must come from the ExHeader")
        info = tmd[0x204:0xB04]
        chunks = tmd[0xB04:0xB04 + 2 * 0x30]
        self.assertEqual(hashlib.sha256(info).digest(), tmd[0x1E4:0x204])
        self.assertEqual(hashlib.sha256(chunks).digest(), info[4:0x24])
        self.assertEqual(struct.unpack_from(">HH", info, 0)[1], 2)

        # The digests must describe the bytes of the patched .3ds, independently
        # re-hashed here from the NCSD partition table.
        rom = self.out / "3ds" / "DQXI_modded.3ds"
        with open(rom, "rb") as f:
            head = f.read(0x200)
        contents = _tmd_contents(tmd)
        self.assertEqual([c["index"] for c in contents], [0, 1])
        self.assertEqual(contents[0]["flags"], 0x0000)
        self.assertEqual(contents[1]["flags"], 0x4000, "manual is an optional CFA")
        for c in contents:
            part_off, part_size = struct.unpack_from("<II", head, 0x120 + c["index"] * 8)
            self.assertEqual(part_size * 0x200, c["size"])
            self.assertEqual(_sha256_file_range(rom, part_off * 0x200, c["size"]),
                             c["sha256"], f"content {c['index']} hash")
            with open(rom, "rb") as f:
                f.seek(part_off * 0x200 + 0x100)
                self.assertEqual(f.read(4), b"NCCH")
        self.assertEqual(contents[0]["sha256"],
                         _sha256_file_range(rom, 0x4000, contents[0]["size"]))
        # Content 1 is the retail e-manual, unchanged.
        self.assertEqual(contents[1]["sha256"], EXPECTED_HASHES["manual_ncch"])

    def test_cia_meta_carries_dependencies_and_icon(self):
        meta = self.cia["meta"]
        exheader = (ORIGINAL_DIR / "exheader.bin").read_bytes()
        self.assertEqual(meta[0:0x180], exheader[0x40:0x1C0], "dependency list")
        self.assertEqual(struct.unpack_from("<I", meta, 0x300)[0], 2)
        icon = (ORIGINAL_DIR / "exefs" / "icon").read_bytes()
        self.assertEqual(len(icon), 0x36C0)
        self.assertEqual(meta[0x400:0x400 + 0x36C0], icon)

    def test_cia_verifier_rejects_a_truncated_file(self):
        """The verifier must not wave a broken section through."""
        from tools import ctr_cia
        broken = self.tmp / "truncated.cia"
        with open(self.cia_path, "rb") as f:
            broken.write_bytes(f.read(0x2400))
        problems = ctr_cia.verify_cia(broken)
        self.assertTrue(problems, "a truncated CIA must produce problems")
        self.assertTrue(any("truncated" in p for p in problems), problems)


@unittest.skipUnless(EXPORT_TOOL.is_file(), "tools/export_mod.py is missing")
class TestRomFsIndex(unittest.TestCase):
    """The RomFS reader that every export is validated with."""

    @classmethod
    def setUpClass(cls):
        from tools import export_mod
        cls.index = export_mod.RomFsIndex(ORIGINAL_DIR / "romfs.bin")

    def test_reads_every_retail_file(self):
        self.assertEqual(len(self.index.files), 21_250)

    def test_paths_and_sizes_match_the_extracted_tree(self):
        for path in ("/syscmn.pack", "/level3d/b001_101a.pack", "/ui/common_2d.pack"):
            entry = self.index.files[path]
            on_disk = PROJECT_ROOT / "game_data" / "romfs" / path.lstrip("/")
            self.assertEqual(entry["size"], on_disk.stat().st_size, path)
            self.assertEqual(self.index.read(path), on_disk.read_bytes(), path)

    def test_names_are_utf16_as_the_cartridge_stores_them(self):
        # 3DS RomFS usually uses UTF-8; DQXI stores UTF-16LE, so a reader that
        # decodes ASCII silently loses every path. Guard that.
        self.assertIn("/2dcmn.pack", self.index.files)


if __name__ == "__main__":
    unittest.main()
