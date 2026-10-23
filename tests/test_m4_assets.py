#!/usr/bin/env python3
"""tests/test_m4_assets.py - Comprehensive E2E and Unit Tests for Milestone 4 Asset Tools.

Covers all 6 asset decompilation, extraction, and re-encoding categories:
1. Category 1: Texture Tool (BFLIM <-> PNG lossless round-trip, Morton raster swizzle)
2. Category 2: Model Tool (NW4C BCH/BCMDL parser to glTF 2.0 & Wavefront OBJ)
3. Category 3: UI Layout Tool (BFLYT layouts & BFLAN animations <-> JSON round-trip bit-matching)
4. Category 4: Audio Tool (BCSTM DSP-ADPCM / PCM decoding to standard WAV & BCSAR unpacker)
5. Category 5: Squirrel Script Re-encoder (Bytecode round-trip, JSON export, Assembly)
6. Category 6: BXON Table Re-encoder (Structural refs, JSON rebuild, String relocation, Table builder)
"""
from __future__ import annotations

import io
import json
import struct
import sys
import unittest
import wave
from pathlib import Path

# Add project root and reference directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, "../reference project")

from dq11tool.ctr.formats import open_image
from tools import audio_tool, bxon, layout_tool, model_tool, pack, sqbin, texture_tool

ROM_PATH = r"..\reference project\DQXI.3ds"


class TestTextureTool(unittest.TestCase):
    """Category 1: Texture Tool tests."""

    def test_texture_synthetic_rgba8_roundtrip(self):
        """Test Morton-order tiled swizzling and decoding on synthetic RGBA8 image."""
        width, height = 16, 16
        # Generate 16x16 gradient with alpha
        pixels = bytearray(width * height * 4)
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4
                pixels[idx] = (x * 16) % 256        # R
                pixels[idx + 1] = (y * 16) % 256    # G
                pixels[idx + 2] = (x + y) * 8 % 256 # B
                pixels[idx + 3] = 255 if x != y else 128 # A

        bflim_bytes = texture_tool.encode_bflim(bytes(pixels), width, height, format_id=9)
        self.assertEqual(bflim_bytes[-0x28:-0x24], b"FLIM")

        rgba_arr, info = texture_tool.decode_bflim(bflim_bytes)
        self.assertEqual(info["width"], width)
        self.assertEqual(info["height"], height)
        self.assertEqual(info["format"], 9)
        self.assertEqual(rgba_arr.tobytes(), bytes(pixels))

    def test_texture_synthetic_rgb565_roundtrip(self):
        """Test RGB565 format packing, Morton swizzling, and unpacking."""
        width, height = 8, 8
        # Simple solid colors
        pixels = bytearray([0xFF, 0x00, 0x00, 0xFF] * (width * height))
        bflim_bytes = texture_tool.encode_bflim(bytes(pixels), width, height, format_id=5)
        rgba_arr, info = texture_tool.decode_bflim(bflim_bytes)
        self.assertEqual(info["width"], width)
        self.assertEqual(info["height"], height)
        self.assertEqual(info["format"], 5)
        # Check red channel is 0xFF and alpha is 0xFF
        self.assertEqual(rgba_arr[0, 0, 0], 0xFF)
        self.assertEqual(rgba_arr[0, 0, 1], 0x00)
        self.assertEqual(rgba_arr[0, 0, 2], 0x00)
        self.assertEqual(rgba_arr[0, 0, 3], 0xFF)

    def test_texture_real_bflim_roundtrip(self):
        """Test real extracted BFLIM texture decode and re-encode bit-matching."""
        f, ncsd, ncch = open_image(ROM_PATH)
        romfs = ncch.romfs()
        rf = next(x for x in romfs.files if x.path == "/ui/battle_2d.pack")
        p = pack.Pack.parse(romfs.read_file(rf))
        f.close()

        # Find SARC archive inside pack
        sarc_entry = next((e for e in p.entries if e.data[:4] == b"SARC"), None)
        self.assertIsNotNone(sarc_entry)
        sarc = texture_tool.Sarc.parse(sarc_entry.data)

        # Find an uncompressed BFLIM texture
        tested = False
        for node in sarc.nodes:
            name = node.name
            data = sarc.files[name]
            if name.endswith(".bflim") and data[-0x28:-0x24] == b"FLIM":
                info = texture_tool.bflim_info(data)
                if info["format"] in (0, 1, 2, 3, 5, 6, 7, 8, 9):  # uncompressed format
                    rgba, inf = texture_tool.decode_bflim(data)
                    rebuilt = texture_tool.encode_bflim(rgba, inf, footer_template=data[-0x28:])
                    self.assertEqual(rebuilt, data, f"Bit-matching failed for {name} (format {info['format']})")
                    tested = True
                    break
        self.assertTrue(tested, "Did not find suitable uncompressed BFLIM in /ui/battle_2d.pack")


class TestModelTool(unittest.TestCase):
    """Category 2: Model Tool tests (NW4C BCH -> glTF 2.0 / OBJ)."""

    def test_model_bch_gltf_obj_export(self):
        """Test NW4C BCH parser, vertex attribute decoding, glTF 2.0 and OBJ export."""
        f, ncsd, ncch = open_image(ROM_PATH)
        romfs = ncch.romfs()
        # Load a character model pack
        model_rf = next(x for x in romfs.files if x.path.startswith("/3d/model/") and x.path.endswith(".pack"))
        p = pack.Pack.parse(romfs.read_file(model_rf))
        f.close()

        bch_entry = next(e for e in p.entries if e.name.endswith(".bch"))
        bch = model_tool.parse_bch(bch_entry.data)

        self.assertGreater(len(bch.models), 0, "No H3D models found in BCH container")
        model = bch.models[0]
        self.assertGreater(len(model.meshes), 0, "No meshes found in model")

        mesh = model.meshes[0]
        self.assertGreater(len(mesh.positions), 0, "Mesh contains 0 vertices")
        self.assertGreater(len(mesh.indices), 0, "Mesh contains 0 triangle indices")

        # Test glTF 2.0 export
        gltf_dict, bin_data = model_tool.export_gltf(mesh)
        self.assertEqual(gltf_dict["asset"]["version"], "2.0")
        self.assertEqual(len(gltf_dict["meshes"]), 1)
        self.assertIn("POSITION", gltf_dict["meshes"][0]["primitives"][0]["attributes"])
        self.assertGreater(len(bin_data), 0)

        # Test Wavefront OBJ export
        obj_text, mtl_text = model_tool.export_obj(mesh)
        self.assertIn("v ", obj_text)
        self.assertIn("f ", obj_text)
        self.assertIn("newmtl default_mat", mtl_text)


class TestLayoutTool(unittest.TestCase):
    """Category 3: UI Layout Tool tests (BFLYT / BFLAN <-> JSON round-trip)."""

    def test_layout_bflyt_bflan_json_roundtrip(self):
        """Test BFLYT layout and BFLAN animation parse -> JSON -> binary rebuild bit-matching."""
        f, ncsd, ncch = open_image(ROM_PATH)
        romfs = ncch.romfs()
        rf = next(x for x in romfs.files if x.path == "/ui/battle_2d.pack")
        p = pack.Pack.parse(romfs.read_file(rf))
        f.close()

        sarc_entry = next(e for e in p.entries if e.data[:4] == b"SARC")
        sarc = layout_tool.Sarc.parse(sarc_entry.data)

        # Find a BFLYT layout
        bflyt_node = next(n for n in sarc.nodes if n.name.endswith(".bflyt"))
        bflyt_data = sarc.files[bflyt_node.name]
        d_lyt = layout_tool.parse_bflyt(bflyt_data)
        self.assertGreater(len(d_lyt.get("panes", [])), 0)

        # Test bit-matching rebuild
        rebuilt_bflyt = layout_tool.build_bflyt(d_lyt)
        self.assertEqual(rebuilt_bflyt, bflyt_data, f"BFLYT rebuild mismatch in {bflyt_node.name}")

        # Find a BFLAN animation
        bflan_node = next(n for n in sarc.nodes if n.name.endswith(".bflan"))
        bflan_data = sarc.files[bflan_node.name]
        d_lan = layout_tool.parse_bflan(bflan_data)
        self.assertGreater(len(d_lan.get("raw_sections", [])), 0)

        # Test bit-matching rebuild
        rebuilt_bflan = layout_tool.build_bflan(d_lan)
        self.assertEqual(rebuilt_bflan, bflan_data, f"BFLAN rebuild mismatch in {bflan_node.name}")


class TestAudioTool(unittest.TestCase):
    """Category 4: Audio Tool tests (BCSTM DSP-ADPCM -> WAV & BCSAR unpacker)."""

    def test_audio_bcstm_dsp_adpcm_to_wav(self):
        """Test BCSTM audio stream decoding to valid RIFF WAV with non-zero audio energy."""
        f, ncsd, ncch = open_image(ROM_PATH)
        romfs = ncch.romfs()
        stream_rf = next(x for x in romfs.files if x.path.startswith("/sound/str/") and x.path.endswith(".bcstm"))
        bcstm_data = romfs.read_file(stream_rf)
        f.close()

        bcstm = audio_tool.parse_bcstm(bcstm_data)
        self.assertIn(bcstm.channels, (1, 2))
        self.assertGreater(bcstm.sample_rate, 0)
        self.assertGreater(bcstm.total_samples, 0)

        wav_bytes = audio_tool.bcstm_to_wav_bytes(bcstm_data)
        self.assertTrue(wav_bytes.startswith(b"RIFF"))

        # Verify WAV validity with wave module
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            self.assertEqual(wf.getnchannels(), bcstm.channels)
            self.assertEqual(wf.getframerate(), bcstm.sample_rate)
            self.assertEqual(wf.getsampwidth(), 2)  # 16-bit PCM
            frames = wf.readframes(1000)
            self.assertGreater(len(frames), 0)
            # Verify non-zero audio energy (genuine decoded waveform)
            samples = struct.unpack(f"<{len(frames)//2}h", frames)
            self.assertTrue(any(s != 0 for s in samples), "Decoded audio is completely silent")

    def test_audio_bcsar_archive_unpack(self):
        """Test BCSAR sound archive unpacker."""
        f, ncsd, ncch = open_image(ROM_PATH)
        romfs = ncch.romfs()
        bcsar_rf = next(x for x in romfs.files if x.path.endswith(".bcsar"))
        bcsar_data = romfs.read_file(bcsar_rf)
        f.close()

        files = audio_tool.unpack_bcsar(bcsar_data)
        self.assertGreater(len(files), 0, "No files unpacked from BCSAR archive")


class TestScriptTool(unittest.TestCase):
    """Category 5: Squirrel Script Re-encoder tests."""

    def test_sqbin_roundtrip(self):
        """Test Squirrel .cnut script parse, rebuild bit-matching, JSON roundtrip, and assembly."""
        f, ncsd, ncch = open_image(ROM_PATH)
        romfs = ncch.romfs()
        sf = next(x for x in romfs.files if x.path.startswith("/script/") and x.path.endswith(".pack"))
        p = pack.Pack.parse(romfs.read_file(sf))
        f.close()

        cnut_entry = next(e for e in p.entries if e.name.endswith(".cnut"))
        func = sqbin.parse(cnut_entry.data)

        # 1. Direct binary rebuild
        rebuilt_bin = sqbin.build(func)
        self.assertEqual(rebuilt_bin, cnut_entry.data, "Direct binary rebuild mismatch")

        # 2. JSON roundtrip
        j = sqbin.func_to_json(func)
        func_json = sqbin.json_to_func(j)
        self.assertEqual(sqbin.build(func_json), cnut_entry.data, "JSON roundtrip rebuild mismatch")

        # 3. Disassembly -> Assembly roundtrip
        dis = sqbin.disasm(func)
        func_asm = sqbin.assemble_nut(dis)
        self.assertEqual(sqbin.build(func_asm), cnut_entry.data, "Assembly roundtrip rebuild mismatch")


class TestTableTool(unittest.TestCase):
    """Category 6: BXON Table Re-encoder tests."""

    def test_bxon_roundtrip(self):
        """Test BXON binary table parse, rebuild bit-matching, JSON rebuild, and table construction."""
        f, ncsd, ncch = open_image(ROM_PATH)
        romfs = ncch.romfs()
        rf = next(x for x in romfs.files if x.path == "/battlecmn.pack")
        p = pack.Pack.parse(romfs.read_file(rf))
        f.close()

        # Find table with text strings
        entry = next(e for e in p.entries if e.name == "battle_Text.bxon")
        table = bxon.Bxon.parse(entry.data)
        self.assertGreater(len(table.strings), 0)

        # 1. Empty replacements rebuild bit-matching
        self.assertEqual(table.rebuild({}), entry.data)

        # 2. All text strings replacements rebuild bit-matching
        text_repl = {s.offset: s.text for s in table.strings}
        self.assertEqual(table.rebuild(text_repl), entry.data)

        # 3. JSON build bit-matching
        j = table.to_json()
        rebuilt_json = bxon.Bxon.build_from_json(j, original_bxon=entry.data)
        self.assertEqual(rebuilt_json, entry.data)

        # 4. Fresh table constructor
        custom_strings = ["Slime", "King Slime", "Dragon Quest XI", "Luminary Sword"]
        custom_bxon = bxon.Bxon.build_table("cMonsterTable", custom_strings)
        parsed_custom = bxon.Bxon.parse(custom_bxon)
        self.assertEqual(parsed_custom.type_name, "cMonsterTable")
        self.assertEqual(len(parsed_custom.strings), len(custom_strings))
        for orig_s, parsed_s in zip(custom_strings, parsed_custom.strings):
            self.assertEqual(orig_s, parsed_s.text)

        # 5. String relocation test with extended text
        s = table.strings[0]
        extended_text = s.text + " [TRANSLATION_EXTENDED_OVERFLOW_TEST]"
        extended_bxon = table.rebuild({s.offset: extended_text})
        parsed_ext = bxon.Bxon.parse(extended_bxon)
        self.assertTrue(any(item.text == extended_text for item in parsed_ext.strings))


if __name__ == "__main__":
    unittest.main()
