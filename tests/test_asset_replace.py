#!/usr/bin/env python3
"""Round-trip and validation tests for the E4 asset replacement workflows.

Every family follows the same rule: taking the exported standard-format file
and importing it again without changing a byte must reproduce the retail
binary exactly (or, for lossy codecs, reproduce the same size and a decoded
signal within the codec's error bound). The tests use the generated
``game_data``/``game_assets`` trees and need no retail image.
"""

from __future__ import annotations

import json
import math
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import asset_replace, layout_tool, sarc_tool, texture_tool
from tools.audio_tool import decode_bcstm, parse_bcstm_info
from tools.bcstm_encode import build_bcstm, build_bcstm_dsp
from tools.bch_texture_patch import encode_for_info, replace_texture, texture_infos
from tools.dspadpcm_encode import encode_channel
from tools.model_patch import apply_indices, apply_positions, obj_indices, obj_positions
from tools.model_tool import BchParser, export_to_obj


def _first(pattern: str, root: str = "game_data") -> Path | None:
    matches = sorted((PROJECT_ROOT / root).rglob(pattern))
    return matches[0] if matches else None


class TextureRoundTripTests(unittest.TestCase):
    def test_every_bflim_format_reencodes_identically(self):
        """Decoded pixels -> encoder -> the exact retail bytes, for all formats but ETC1."""
        samples: dict[int, int] = {}
        tested = 0
        for png in (PROJECT_ROOT / "game_data/arcs").rglob("*.bflim"):
            raw = png.read_bytes()
            try:
                info = texture_tool.bflim_info(raw)
            except ValueError:
                continue
            if info["format"] in (10, 11):     # lossy, tested separately
                continue
            if samples.get(info["format"], 0) >= 3:
                continue
            samples[info["format"]] = samples.get(info["format"], 0) + 1
            rgba, _ = texture_tool.decode_bflim(raw)
            rebuilt = texture_tool.encode_bflim(rgba, info, footer_template=raw)
            self.assertEqual(rebuilt, raw, f"{png.name} ({info['format_name']}) did not round-trip")
            tested += 1
        self.assertGreaterEqual(tested, 8, "expected several uncompressed BFLIM formats")

    def test_etc1_reencode_keeps_size_and_is_visually_close(self):
        sample = next((p for p in (PROJECT_ROOT / "game_data/arcs").rglob("*.bflim")
                       if texture_tool.bflim_info(p.read_bytes())["format"] in (10, 11)), None)
        if sample is None:
            self.skipTest("no ETC1 BFLIM present")
        raw = sample.read_bytes()
        info = texture_tool.bflim_info(raw)
        rgba, _ = texture_tool.decode_bflim(raw)
        rebuilt = texture_tool.encode_bflim(rgba, info, footer_template=raw)
        self.assertEqual(len(rebuilt), len(raw), "ETC1 replacement must keep the byte size")
        again, _ = texture_tool.decode_bflim(rebuilt)
        mae = float(np.abs(rgba.astype(int) - again.astype(int)).mean())
        self.assertLess(mae, 12.0, f"ETC1 reintroduced a large error ({mae:.1f})")

    def test_four_bit_formats_pack_and_unpack(self):
        """L4/A4 store two pixels per byte; the encoder must not fall back to RGBA8."""
        for fmt in (12, 13):
            info = {"width": 8, "height": 8, "format": fmt, "flags": 0, "alignment": 0}
            rgba = np.zeros((8, 8, 4), np.uint8)
            rgba[..., 0] = np.arange(64, dtype=np.uint8).reshape(8, 8) * 4
            rgba[..., 3] = 255
            encoded = texture_tool.encode_bflim(rgba, info)
            decoded, read = texture_tool.decode_bflim(encoded)
            self.assertEqual(read["format"], fmt)
            self.assertEqual(len(encoded), 0x28 + 32)   # 64 pixels at 4 bpp
            channel = 3 if fmt == 13 else 0             # A4 carries alpha, L4 luminance
            self.assertLessEqual(
                int(np.abs(decoded[..., channel].astype(int) - rgba[..., channel].astype(int)).max()), 17
            )

    def test_replacement_validates_dimensions_and_reports_hardware_limits(self):
        sample = _first("*.bflim", "game_data/arcs")
        raw = sample.read_bytes()
        info = texture_tool.bflim_info(raw)
        from PIL import Image

        with tempfile.TemporaryDirectory() as td:
            wrong = Path(td) / "wrong.png"
            Image.new("RGBA", (info["width"] + 1, info["height"]), (255, 0, 0, 255)).save(wrong)
            warnings, errors = texture_tool.validate_bflim_replacement(raw, wrong)
        self.assertTrue(errors, "a differently sized PNG must be refused")
        self.assertIn("resize", errors[0].lower())
        self.assertIsInstance(warnings, list)

    def test_uncompressed_png_export_replace_is_byte_identical(self):
        """Export the standard PNG, import it unchanged: same BFLIM bytes."""
        for asset in ("arcs/ui/battle_2d/battle_2d/timg/icon_cursor_battle_2d.png",
                      "arcs/ui/battle_2d/battle_2d/timg/icon_target_2d.png"):
            png, bflim, _rel = asset_replace._texture_paths(asset)
            if not (png.is_file() and bflim.is_file()):
                continue
            info = texture_tool.bflim_info(bflim.read_bytes())
            if info["format"] in (10, 11):
                continue
            with tempfile.TemporaryDirectory() as td:
                out = Path(td)
                asset_replace.export_texture(asset, out)
                exported = out / "textures" / asset
                report = asset_replace.replace_texture(asset, exported, stage=False,
                                                       preview=False, allow_resize=False,
                                                       mod=PROJECT_ROOT / "mod")
                self.assertTrue(report["ok"])
                rebuilt = (PROJECT_ROOT / report["encoded"]).read_bytes()
                self.assertEqual(rebuilt, bflim.read_bytes(), f"{asset} changed on a no-op replace")
            return
        self.skipTest("no uncompressed UI texture sample present")


class LayoutRoundTripTests(unittest.TestCase):
    def test_bflyt_json_rebuild_is_identical(self):
        sample = _first("*.bflyt", "game_data/arcs")
        if sample is None:
            self.skipTest("no BFLYT present")
        raw = sample.read_bytes()
        doc = layout_tool.parse_bflyt(raw)
        self.assertEqual(layout_tool.build_bflyt(json.loads(json.dumps(doc))), raw)

    def test_pane_transform_edit_lands_in_the_binary(self):
        sample = _first("*.bflyt", "game_data/arcs")
        doc = layout_tool.parse_bflyt(sample.read_bytes())
        if not doc.get("panes"):
            self.skipTest("layout has no panes")
        edited = json.loads(json.dumps(doc))
        edited["panes"][0]["translate"][0] += 1.25
        rebuilt = layout_tool.build_bflyt(edited)
        self.assertEqual(len(rebuilt), len(sample.read_bytes()))
        back = layout_tool.parse_bflyt(rebuilt)
        self.assertAlmostEqual(back["panes"][0]["translate"][0], edited["panes"][0]["translate"][0], places=5)

    def test_exported_json_without_raw_sections_rebuilds_identically(self):
        # a hand-trimmed JSON with only the pane list must not build a header-only layout
        rel = "arcs/ui/battle_2d/battle_2d/blyt/battle_2d_lw.bflyt"
        exported = PROJECT_ROOT / "game_assets/layouts" / (rel + ".json")
        binary = PROJECT_ROOT / "game_data" / rel
        if not exported.is_file() or not binary.is_file():
            self.skipTest("sample layout missing")
        doc = json.loads(exported.read_text(encoding="utf-8"))
        doc.pop("raw_sections", None)
        original = binary.read_bytes()
        self.assertEqual(layout_tool.build_bflyt(layout_tool.complete(doc, original)), original)
        doc["panes"][0]["translate"][0] += 2.0
        moved = layout_tool.parse_bflyt(layout_tool.build_bflyt(layout_tool.complete(doc, original)))
        self.assertAlmostEqual(moved["panes"][0]["translate"][0], doc["panes"][0]["translate"][0], places=5)

    def test_added_pane_is_a_sibling_and_leaves_the_rest_alone(self):
        for sample in sorted((PROJECT_ROOT / "game_data/arcs").rglob("*.bflyt")):
            raw = sample.read_bytes()
            doc = layout_tool.parse_bflyt(raw)
            magics = [s["magic"] for s in doc["raw_sections"]]
            # a text pane that has children and user data exercises every branch
            src = next((p for i, p in enumerate(doc["panes"]) if p["type"] == "txt1"), None)
            if src is None or "pas1" not in magics:
                continue
            grown = layout_tool.build_bflyt(layout_tool.add_pane(doc, src["name"], "N_added_pane"))
            back = layout_tool.parse_bflyt(grown)
            names = [p["name"] for p in back["panes"]]
            self.assertEqual(names.count("N_added_pane"), 1)
            self.assertEqual(len(back["panes"]), len(doc["panes"]) + 1)
            new = back["panes"][names.index("N_added_pane")]
            self.assertEqual(new["text"], src["text"])
            self.assertEqual(new["translate"], src["translate"])
            others = [p for p in back["panes"] if p["name"] != "N_added_pane"]
            self.assertEqual([p["raw_header_hex"] for p in others],
                             [p["raw_header_hex"] for p in doc["panes"]])
            def depth_of(d, name):
                depth = 0
                for s in d["raw_sections"]:
                    depth += {"pas1": 1, "pae1": -1}.get(s["magic"], 0)
                    if s["magic"] in layout_tool.PANE_MAGICS and \
                            bytes.fromhex(s["payload_hex"])[4:28].split(b"\0")[0].decode() == name:
                        return depth
            self.assertEqual(depth_of(back, "N_added_pane"), depth_of(back, src["name"]))
            with self.assertRaises(ValueError):
                layout_tool.add_pane(doc, src["name"], src["name"])
            return
        self.skipTest("no layout with a text pane and a child block")

    def test_longer_text_grows_the_pane(self):
        for sample in sorted((PROJECT_ROOT / "game_data/arcs").rglob("*.bflyt")):
            doc = layout_tool.parse_bflyt(sample.read_bytes())
            for i, pane in enumerate(doc.get("panes", [])):
                if pane.get("type") == "txt1" and pane.get("text"):
                    edited = json.loads(json.dumps(doc))
                    edited["panes"][i]["text"] = "X" * 200
                    back = layout_tool.parse_bflyt(layout_tool.build_bflyt(edited))
                    self.assertEqual(back["panes"][i]["text"], "X" * 200)
                    self.assertEqual(back["panes"][i]["text_id"], pane["text_id"])
                    self.assertEqual([p["name"] for p in back["panes"]], [p["name"] for p in doc["panes"]])
                    return
        self.skipTest("no text pane found")

    def test_sarc_noop_replacement_is_identical(self):
        arc = _first("*.arc", "game_data/packs/ui")
        if arc is None:
            self.skipTest("no SARC present")
        raw = arc.read_bytes()
        archive = sarc_tool.SarcArchive.parse(raw)
        node = archive.nodes[0]
        same = archive.member(node.name)
        self.assertEqual(sarc_tool.replace_member(raw, node.name, same), raw)
        rebuilt = sarc_tool.build_sarc(raw, {node.name: same})
        self.assertEqual(sarc_tool.SarcArchive.parse(rebuilt).member(node.name), same)


class ModelRoundTripTests(unittest.TestCase):
    def test_obj_position_and_index_noop_are_identical(self):
        bch = PROJECT_ROOT / "game_data/packs/3d/model/ani00000a_h/ani00000a_h.bch"
        if not bch.is_file():
            self.skipTest("sample model missing")
        raw = bch.read_bytes()
        models = BchParser(raw, source_path=bch).parse_models("ani00000a_h")
        with tempfile.TemporaryDirectory() as td:
            obj = Path(td) / "model.obj"
            for model in models:
                export_to_obj(model, obj)
            patched, _ = apply_positions(raw, obj_positions(obj), source_path=bch)
            self.assertEqual(patched, raw)
            patched, _ = apply_indices(raw, obj_indices(obj), source_path=bch)
            self.assertEqual(patched, raw)

    def test_uncompressed_bch_texture_replacement_is_identical(self):
        """A BCH RGB565/RGBA4/L8 texture exported to PNG and re-imported is byte-identical."""
        for bch in (PROJECT_ROOT / "game_data/packs/3d").rglob("*.bch"):
            raw = bch.read_bytes()
            infos = texture_infos(raw)
            target = next((t for t in infos if t["format_name"] not in ("ETC1", "ETC1A4")), None)
            if target is None:
                continue
            images = dict(BchParser(raw, source_path=bch).extract_textures())
            image = images.get(target["name"])
            if image is None:
                continue
            with tempfile.TemporaryDirectory() as td:
                png = Path(td) / "tex.png"
                image.save(png)
                self.assertEqual(replace_texture(raw, target["name"], png), raw,
                                 f"{bch.name}:{target['name']} ({target['format_name']})")
            return
        self.skipTest("no uncompressed BCH texture found")

    def test_etc1_texture_replace_keeps_size_and_colour(self):
        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_101a/b001_101a.bch"
        if not bch.is_file():
            self.skipTest("sample map BCH missing")
        raw = bch.read_bytes()
        infos = {t["name"]: t for t in texture_infos(raw)}
        info = infos.get("ko_b001_wall01")
        if info is None:
            self.skipTest("sample texture missing")
        from PIL import Image

        with tempfile.TemporaryDirectory() as td:
            png = Path(td) / "red.png"
            Image.new("RGBA", (info["width"], info["height"]), (230, 0, 0, 255)).save(png)
            patched = replace_texture(raw, "ko_b001_wall01", png)
        self.assertEqual(len(patched), len(raw))
        pixel = dict(BchParser(patched).extract_textures())["ko_b001_wall01"].getpixel((16, 16))
        self.assertGreater(pixel[0], 200)
        self.assertLess(pixel[1], 80)


class AudioRoundTripTests(unittest.TestCase):
    def test_dspadpcm_encoder_decodes_back_to_the_waveform(self):
        template = PROJECT_ROOT / "game_data/romfs/sound/str/B_020_CS_060_06.dspadpcm.bcstm"
        if not template.is_file():
            self.skipTest("small DSP-ADPCM template missing")
        raw = template.read_bytes()
        info, _ = parse_bcstm_info(raw)
        n = 4000
        t = np.arange(n) / info.sample_rate
        mono = (0.5 * np.sin(2 * math.pi * 440 * t) * 32767).astype("<i2")
        pcm = mono.reshape(-1, 1)
        rebuilt = build_bcstm_dsp(raw, pcm, info.sample_rate, info.channels)
        out_info, _ = parse_bcstm_info(rebuilt)
        self.assertEqual(out_info.codec, 2)
        self.assertEqual(out_info.channels, info.channels)
        self.assertEqual(out_info.total_samples, n)
        decoded, rate, channels = decode_bcstm(rebuilt)
        self.assertEqual((rate, channels), (info.sample_rate, info.channels))
        got = np.frombuffer(decoded, dtype="<i2").astype(int)
        self.assertLessEqual(len(got), n + 14)
        err = np.abs(got[:n] - mono.astype(int))
        self.assertLess(float(err.mean()), 160.0, f"DSP-ADPCM error too high ({err.mean():.1f})")
        self.assertLess(int(err.max()), 3000)

    def test_exported_wav_reencodes_to_the_same_stream_geometry(self):
        wav = PROJECT_ROOT / "game_assets/audio/romfs/sound/str/B_020_CS_060_06.dspadpcm.wav"
        bcstm = PROJECT_ROOT / "game_data/romfs/sound/str/B_020_CS_060_06.dspadpcm.bcstm"
        if not (wav.is_file() and bcstm.is_file()):
            self.skipTest("sample audio missing")
        with wave.open(str(wav), "rb") as wf:
            channels, width, rate = wf.getnchannels(), wf.getsampwidth(), wf.getframerate()
            frames = wf.readframes(wf.getnframes())
        pcm = np.frombuffer(frames, dtype="<i2").reshape(-1, channels)
        template = bcstm.read_bytes()
        rebuilt = build_bcstm_dsp(template, pcm, rate, channels)
        self.assertEqual(len(rebuilt), len(template),
                         "re-encoding an unmodified export should keep the retail stream size")
        before, _, _ = decode_bcstm(template)
        after, _, _ = decode_bcstm(rebuilt)
        err = np.abs(np.frombuffer(before, "<i2").astype(int) -
                     np.frombuffer(after, "<i2").astype(int))
        self.assertLess(float(err.mean()), 120.0)

    def test_dspadpcm_frames_have_the_documented_shape(self):
        samples = np.zeros(28, np.int16)
        frames = encode_channel(samples)
        self.assertEqual(len(frames), 16)                 # two 8-byte frames
        self.assertEqual(len(frames) % 8, 0)
        self.assertLessEqual((frames[0] >> 4) & 7, 7)
        self.assertLessEqual(frames[0] & 0xF, 12)

    def test_pcm16_path_stays_lossless(self):
        template = PROJECT_ROOT / "game_data/romfs/sound/str/B_020_CS_060_06.dspadpcm.bcstm"
        if not template.is_file():
            self.skipTest("sample template missing")
        pcm = np.zeros((1000, 1), np.int16)
        rebuilt = build_bcstm(template.read_bytes(), pcm, 22050, 1)
        decoded, _, _ = decode_bcstm(rebuilt)
        self.assertEqual(np.frombuffer(decoded, "<i2").tolist(), pcm[:, 0].tolist())


class MapRoundTripTests(unittest.TestCase):
    """The shared fixture is a real +2-on-X smoke edit; tests must not clobber it."""

    def _replace(self, project_doc):
        fixture = PROJECT_ROOT / "game_assets/maps/b001_101a/level3d.patched.bxon"
        before = fixture.read_bytes() if fixture.is_file() else None
        try:
            with tempfile.TemporaryDirectory() as td:
                project = Path(td) / "project.json"
                project.write_text(json.dumps(project_doc), encoding="utf-8")
                report = asset_replace.replace_map("b001_101a", project, stage=False,
                                                   preview=False, mod=PROJECT_ROOT / "mod")
            return report, (PROJECT_ROOT / report["encoded"]).read_bytes()
        finally:
            if before is None:
                fixture.unlink(missing_ok=True)
            else:
                fixture.write_bytes(before)

    def test_unchanged_project_keeps_level3d_bytes(self):
        source = PROJECT_ROOT / "game_data/packs/level3d/b001_101a/level3d.bxon"
        if not source.is_file():
            self.skipTest("sample map missing")
        raw = source.read_bytes()
        offset = 0x194C
        value = struct.unpack_from("<f", raw, offset)[0]
        report, patched = self._replace({"map": "b001_101a",
                                         "edits": [{"offset": f"0x{offset:X}", "value": value}]})
        self.assertTrue(report["ok"])
        self.assertFalse(report["changed"])
        self.assertEqual(patched, raw)

    def test_one_value_edit_changes_only_those_four_bytes(self):
        source = PROJECT_ROOT / "game_data/packs/level3d/b001_101a/level3d.bxon"
        if not source.is_file():
            self.skipTest("sample map missing")
        raw = source.read_bytes()
        offset = 0x194C
        value = struct.unpack_from("<f", raw, offset)[0] + 0.5
        report, patched = self._replace({"map": "b001_101a",
                                         "edits": [{"offset": f"0x{offset:X}", "value": value}]})
        self.assertTrue(report["ok"])
        changed = [i for i, (a, b) in enumerate(zip(raw, patched)) if a != b]
        self.assertTrue(changed)
        self.assertTrue(all(offset <= i < offset + 4 for i in changed))
        self.assertAlmostEqual(struct.unpack_from("<f", patched, offset)[0], value, places=6)


class AssetWorkflowTests(unittest.TestCase):
    def test_every_family_inspect_and_export_reports_ok(self):
        cases = [
            ("texture", "arcs/ui/battle_2d/battle_2d/timg/icon_cursor_battle_2d.png"),
            ("layout", "arcs/ui/battle_2d/battle_2d/blyt/battle_2d_lw.bflyt.json"),
            ("audio", "romfs/sound/str/B_020_CS_060_06.dspadpcm.wav"),
            ("model", "3d/model/ani00000a_h/ani00000a_h.bch"),
            ("map", "b001_101a"),
        ]
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            for family, asset in cases:
                with self.subTest(family=family):
                    inspect = {
                        "texture": asset_replace.inspect_texture,
                        "layout": asset_replace.inspect_layout,
                        "audio": asset_replace.inspect_audio,
                        "model": asset_replace.inspect_model,
                        "map": asset_replace.inspect_map,
                    }[family](asset)
                    self.assertTrue(inspect["ok"], inspect)
                    export = {
                        "texture": asset_replace.export_texture,
                        "layout": asset_replace.export_layout,
                        "audio": asset_replace.export_audio,
                        "model": asset_replace.export_model,
                        "map": asset_replace.export_map,
                    }[family]
                    exported = export(asset, out)
                    self.assertTrue(exported["ok"], exported)

    def test_texture_stage_rebuilds_the_ui_pack(self):
        """A staged texture is the *pack* (LayeredFS), with the SARC member intact."""
        from tools import pack

        asset = "arcs/ui/battle_2d/battle_2d/timg/icon_cursor_battle_2d.png"
        _png, bflim, member_rel = asset_replace._texture_paths(asset)
        if not bflim.is_file():
            self.skipTest("sample UI texture missing")
        original = bflim.read_bytes()
        with tempfile.TemporaryDirectory() as td:
            mod = Path(td) / "mod"
            report = asset_replace.replace_texture(asset, _png, stage=True, preview=False,
                                                   allow_resize=False, mod=mod)
            self.assertTrue(report["ok"], report)
            staged = mod / "romfs" / "ui" / "battle_2d.pack"
            self.assertTrue(staged.is_file(), "the pack was not staged")
            entries = pack.Pack.parse(staged.read_bytes()).entries
            arc = next(e.data for e in entries if e.name.endswith(".arc"))
            got = sarc_tool.SarcArchive.parse(arc).member("timg/icon_cursor_battle_2d.bflim")
            self.assertEqual(got, original)

    def test_audio_stage_is_a_loose_romfs_file(self):
        asset = "romfs/sound/str/B_020_CS_060_06.dspadpcm.wav"
        wav = PROJECT_ROOT / "game_assets/audio" / asset
        if not wav.is_file():
            self.skipTest("sample audio missing")
        with tempfile.TemporaryDirectory() as td:
            mod = Path(td) / "mod"
            report = asset_replace.replace_audio(asset, wav, "dspadpcm", stage=True,
                                                 preview=False, mod=mod)
            self.assertTrue(report["ok"], report)
            target = mod / "romfs/sound/str/B_020_CS_060_06.dspadpcm.bcstm"
            self.assertTrue(target.is_file(), "the BCSTM was staged at the wrong path")
            self.assertEqual(parse_bcstm_info(target.read_bytes())[0].codec, 2)

    def test_cli_failure_is_a_clean_json_error(self):
        code = asset_replace.main([
            "replace", "--family", "texture",
            "--asset", "arcs/does/not/exist.png",
            "--file", str(PROJECT_ROOT / "README.md"), "--json",
        ])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
