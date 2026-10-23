#!/usr/bin/env python3
"""Round-trip tests for the extracted local asset tree.

These tests do not need the retail image: they use files under `game_data/` and
`game_assets/`. They are intentionally small and fast enough to run after any
converter change.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import bxon, layout_tool, sqbin, texture_tool
from tools.map_tool import patch_project
from tools.model_patch import apply_positions, obj_positions
from tools.model_tool import BchParser, export_gltf, export_to_gltf, export_to_obj
from tools.bch_texture_patch import replace_texture, texture_infos
from tools.etc1_encode import encode_etc1
from tools.romfs_hash import verify as verify_romfs


class AssetRoundTripTests(unittest.TestCase):
    def test_texture_uncompressed_roundtrip(self):
        candidates = list((PROJECT_ROOT / "game_data/arcs").rglob("*.bflim"))
        for src in candidates:
            raw = src.read_bytes()
            info = texture_tool.bflim_info(raw)
            if info["format"] in (10, 11):  # ETC1 / ETC1A4 are lossy
                continue
            rebuilt = texture_tool.encode_bflim(texture_tool.decode_bflim(raw)[0], info, footer_template=raw)
            self.assertEqual(rebuilt, raw, f"texture round-trip failed: {src}")
            return
        self.skipTest("no uncompressed BFLIM found")

    def test_layout_and_animation_roundtrip(self):
        for ext, parser, builder in [
            (".bflyt", layout_tool.parse_bflyt, layout_tool.build_bflyt),
            (".bflan", layout_tool.parse_bflan, layout_tool.build_bflan),
        ]:
            src = next((PROJECT_ROOT / "game_data/arcs").rglob(f"*{ext}"))
            raw = src.read_bytes()
            self.assertEqual(builder(parser(raw)), raw, f"{ext} round-trip failed")

    def test_script_roundtrip(self):
        src = next((PROJECT_ROOT / "game_data/packs").rglob("*.cnut"))
        raw = src.read_bytes()
        self.assertEqual(sqbin.build(sqbin.parse(raw)), raw)

    def test_table_string_roundtrip(self):
        src = next((PROJECT_ROOT / "game_data/packs").rglob("*.bxon"))
        raw = src.read_bytes()
        table = bxon.Bxon.parse(raw)
        # A no-op string replacement must rebuild identical bytes.
        self.assertEqual(table.rebuild({}), raw)

    def test_table_json_builder_roundtrip(self):
        src = next((PROJECT_ROOT / "game_data/packs").rglob("*.bxon"))
        raw = src.read_bytes()
        table = bxon.Bxon.parse(raw)
        rebuilt = bxon.Bxon.build_from_json(json.dumps(table.to_dict()), raw)
        self.assertEqual(rebuilt, raw)

    def test_map_noop_patch_roundtrip(self):
        src = PROJECT_ROOT / "game_data/packs/level3d/b001_101a/level3d.bxon"
        project = {
            "map": "b001_101a",
            "edits": [{"offset": "0x194C", "value": struct.unpack_from("<f", src.read_bytes(), 0x194C)[0]}],
        }
        out = PROJECT_ROOT / "game_assets/maps/b001_101a/level3d.patched.bxon"
        before = out.read_bytes() if out.exists() else None
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "project.json"
            p.write_text(json.dumps(project), encoding="utf-8")
            patch_project(p)
            self.assertEqual(out.read_bytes(), src.read_bytes())
        if before is None:
            out.unlink(missing_ok=True)
        else:
            out.write_bytes(before)

    def test_generated_wav_header(self):
        src = next((PROJECT_ROOT / "game_assets/audio").rglob("*.wav"))
        with wave.open(str(src), "rb") as w:
            self.assertEqual(w.getsampwidth(), 2)
            self.assertGreater(w.getnframes(), 0)

    def test_model_position_patch_roundtrip(self):
        bch = PROJECT_ROOT / "game_data/packs/3d/model/ani00000a_h/ani00000a_h.bch"
        raw = bch.read_bytes()
        models = BchParser(raw).parse_models("roundtrip")
        with tempfile.TemporaryDirectory() as td:
            obj = Path(td) / "model.obj"
            for model in models:
                export_to_obj(model, obj)
            positions = obj_positions(obj)
            patched, report = apply_positions(raw, positions)
            self.assertEqual(patched, raw, "unmodified OBJ positions must round-trip exactly")
            self.assertGreaterEqual(report["vertices"], len(positions))
            self.assertEqual(report["vertices"] % len(positions), 0)
            positions[0] = (positions[0][0] + 0.5, positions[0][1], positions[0][2])
            changed, _ = apply_positions(raw, positions)
            self.assertNotEqual(changed, raw)
            edited = BchParser(changed).parse_models("changed")[0].meshes[0].positions[0]
            self.assertAlmostEqual(edited[0], positions[0][0], places=5)

    def test_model_texture_materials_are_distinct(self):
        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_101a/b001_101a.bch"
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("b001_101a")[0]
        if len(model.textures) < 2:
            self.skipTest("sample model has fewer than two textures")
        self.assertNotEqual(model.meshes[0].texture_name, model.meshes[1].texture_name)
        # 36 draws, all distinct once lamps/decals sit on their bones (before
        # bone placement 15 of them were stacked on the origin and collapsed)
        self.assertEqual(len(model.meshes), 36)
        keys = {
            (tuple(round(c, 4) for p in m.positions for c in p), tuple(m.indices))
            for m in model.meshes
        }
        self.assertEqual(len(keys), len(model.meshes))
        self.assertEqual(model.meshes[0].texture_name, "na_b001_collumsection01.png")
        p = model.meshes[0].positions[0]
        uv = model.meshes[0].uvs[0]
        self.assertAlmostEqual(p[0], 1.816, places=2)
        # raw value 18.044 (matches SPICA) plus the map root bone's z offset 2.711
        self.assertAlmostEqual(p[2], 18.044 + 2.711, places=2)
        self.assertAlmostEqual(uv[0], 0.1142, places=3)
        self.assertAlmostEqual(uv[1], 0.8750, places=3)
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "model.obj"
            export_to_obj(model, out)
            mtl = out.with_suffix(".mtl").read_text(encoding="utf-8")
            self.assertEqual(mtl.count("newmtl "), len([m for m in model.meshes if m.positions and m.indices]))
            self.assertIn(model.meshes[1].texture_name, mtl)
            gt = Path(td) / "model.gltf"
            export_to_gltf(model, gt)
            gltf = json.loads(gt.read_text(encoding="utf-8"))
            self.assertEqual(len(gltf["images"]), len(model.textures))
            self.assertGreaterEqual(len(gltf["materials"]), 2)
            untextured = [m for m in model.meshes if not m.texture_name]
            if untextured:
                idx = model.meshes.index(untextured[0])
                self.assertNotIn("material", gltf["meshes"][idx]["primitives"][0])

    def test_etc1_texture_encoder_and_bch_replacement(self):
        import numpy as np
        from PIL import Image

        flat = np.zeros((8, 8, 4), np.uint8)
        flat[..., 0] = 200
        flat[..., 1] = 120
        flat[..., 2] = 40
        flat[..., 3] = 255
        enc = encode_etc1(flat, alpha=False)
        self.assertEqual(len(enc), 8 * 8 // 2)
        dec = texture_tool._decode_etc1(enc, 8, 8, False)
        self.assertLess(int(np.abs(dec.astype(int) - flat.astype(int)).mean()), 40)

        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_101a/b001_101a.bch"
        if not bch.exists():
            self.skipTest("sample map BCH is not present")
        data = bch.read_bytes()
        infos = {t["name"]: t for t in texture_infos(data)}
        self.assertIn("ko_b001_wall01", infos)
        with tempfile.TemporaryDirectory() as td:
            png = Path(td) / "red.png"
            colored = np.zeros((64, 64, 4), np.uint8)
            colored[..., 0] = 230
            colored[..., 3] = 255
            Image.fromarray(colored, "RGBA").save(png)
            out = replace_texture(data, "ko_b001_wall01", png)
        self.assertEqual(len(out), len(data))
        imgs = dict(BchParser(out).extract_textures())
        r, g, b, _a = imgs["ko_b001_wall01"].getpixel((16, 16))
        self.assertGreater(r, 200)
        self.assertLess(g, 80)
        self.assertLess(b, 80)

    def test_bcstm_pcm16_reencode_roundtrip(self):
        import math
        import numpy as np
        from tools.audio_tool import decode_bcstm, parse_bcstm_info
        from tools.bcstm_encode import build_bcstm

        template = PROJECT_ROOT / "game_data/romfs/sound/str/BGM_B01.dspadpcm.bcstm"
        if not template.exists():
            self.skipTest("BCSTM template is not present")
        rate = 32728
        t = np.arange(rate) / rate
        mono = (0.4 * np.sin(2 * math.pi * 440 * t) * 32767).astype("<i2")
        pcm = np.stack([mono, mono], axis=1)
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "tone.wav"
            with wave.open(str(wav), "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(rate)
                wf.writeframes(pcm.tobytes())
            out = build_bcstm(template.read_bytes(), pcm, rate, 2)
        info = parse_bcstm_info(out)[0]
        self.assertEqual(info.codec, 1)
        self.assertEqual(info.total_samples, rate)
        decoded, out_rate, out_channels = decode_bcstm(out)
        self.assertEqual((out_rate, out_channels), (rate, 2))
        self.assertEqual(decoded, pcm.tobytes())

    def test_material_diffuse_patch(self):
        from tools.model_material import DIFFUSE_OFFSET, material_entries, set_diffuse

        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_101a/b001_101a.bch"
        if not bch.exists():
            self.skipTest("sample map BCH is not present")
        raw = bch.read_bytes()
        entries = material_entries(raw)
        self.assertGreater(len(entries), 0)
        out = set_diffuse(raw, 0, (10, 20, 30, 255))
        self.assertEqual(len(out), len(raw))
        ptr = entries[0] + DIFFUSE_OFFSET
        self.assertEqual(out[ptr:ptr + 4], bytes((10, 20, 30, 255)))
        self.assertNotEqual(out, raw)

    def test_model_index_patch_roundtrip(self):
        from tools.model_patch import apply_indices, obj_indices

        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_101a/b001_101a.bch"
        if not bch.exists():
            self.skipTest("sample map BCH is not present")
        raw = bch.read_bytes()
        model = BchParser(raw, source_path=bch).parse_models("b001_101a")[0]
        with tempfile.TemporaryDirectory() as td:
            obj = Path(td) / "model.obj"
            export_to_obj(model, obj)
            groups = obj_indices(obj)
            out, report = apply_indices(raw, groups, source_path=bch)
        self.assertEqual(out, raw, "unmodified OBJ indices must round-trip exactly")
        self.assertGreaterEqual(report["meshes"], len(model.meshes))
        groups[0][0] = (groups[0][0] + 1) % (max(groups[0]) + 1)
        changed, _ = apply_indices(raw, groups, source_path=bch)
        self.assertNotEqual(changed, raw)

    def test_model_position_patch_handles_duplicate_layers(self):
        from tools.model_patch import apply_positions

        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_101a/b001_101a.bch"
        if not bch.exists():
            self.skipTest("sample map BCH is not present")
        raw = bch.read_bytes()
        model = BchParser(raw, source_path=bch).parse_models("b001_101a")[0]
        positions = [p for mesh in model.meshes for p in mesh.positions]
        out, report = apply_positions(raw, positions, source_path=bch)
        self.assertEqual(out, raw, "no-op edit must preserve every duplicate layer")
        self.assertGreaterEqual(report["meshes"], len(model.meshes))
        changed = list(positions)
        changed[0] = (changed[0][0] + 1.0, changed[0][1], changed[0][2])
        out2, _ = apply_positions(raw, changed, source_path=bch)
        self.assertNotEqual(out2, raw)

    def test_bone_placed_position_patch_lands_where_edited(self):
        # The hero face is stored in head-bone space; an edit made in model
        # space must come back at the edited model-space position.
        from tools.model_patch import apply_positions

        bch = PROJECT_ROOT / "game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"
        if not bch.exists():
            self.skipTest("sample character model is not present")
        raw = bch.read_bytes()
        model = BchParser(raw, source_path=bch).parse_models("cha01000a_h")[0]
        positions = [p for mesh in model.meshes for p in mesh.positions]
        face = next(i for i, m in enumerate(model.meshes) if m.placement is not None)
        start = sum(len(m.positions) for m in model.meshes[:face])
        moved = list(positions)
        x, y, z = moved[start]
        moved[start] = (x + 0.05, y, z)
        out, _ = apply_positions(raw, moved, source_path=bch)
        again = BchParser(out, source_path=bch).parse_models("cha01000a_h")[0]
        got = again.meshes[face].positions[0]
        self.assertAlmostEqual(got[0], x + 0.05, places=4)
        self.assertAlmostEqual(got[1], y, places=4)

    def test_non_square_bch_texture_dimensions(self):
        bch = PROJECT_ROOT / "game_data/packs/3d/model/w1603b/w1603b.bch"
        if not bch.exists():
            self.skipTest("sample weapon BCH is not present")
        parser = BchParser(bch.read_bytes(), source_path=bch)
        textures = dict(parser.extract_textures())
        self.assertIn("w1003b", textures)
        self.assertEqual(textures["w1003b"].size, (64, 128))
        infos = {t["name"]: t for t in texture_infos(bch.read_bytes())}
        self.assertEqual((infos["w1003b"]["width"], infos["w1003b"]["height"]), (64, 128))

    def test_character_material_texture_mapping(self):
        bch = PROJECT_ROOT / "game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"
        if not bch.exists():
            self.skipTest("sample character model is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("cha01000a_h")[0]
        self.assertEqual(model.meshes[0].texture_name, "cha01000a_body_high.png")
        # the layered face (eye/mouth atlas + skin) is baked into one composite texture
        self.assertEqual(model.meshes[4].texture_name, "cha01000a_face_composite.png")
        self.assertEqual(model.meshes[5].texture_name, "cha01000a_hair.png")
        keys = {
            (tuple(round(c, 4) for p in m.positions for c in p), tuple(m.indices))
            for m in model.meshes
        }
        self.assertEqual(len(keys), len(model.meshes))

    def test_vectorized_etc1_matches_reference_decoder(self):
        import numpy as np

        rng = np.random.default_rng(7)
        for alpha in (False, True):
            for sw, sh in ((8, 8), (32, 16), (64, 64)):
                data = rng.integers(0, 256, sw * sh // 2 * (2 if alpha else 1), dtype=np.uint8).tobytes()
                fast = texture_tool._decode_etc1(data, sw, sh, alpha)
                slow = texture_tool._decode_etc1_reference(data, sw, sh, alpha)
                self.assertTrue(np.array_equal(fast, slow), f"ETC1 alpha={alpha} {sw}x{sh}")

    def test_blend_state_reaches_obj_and_gltf(self):
        # additive glow/mist draws must not export as opaque quads with black backgrounds
        from tools.model_tool import load_material_map

        manifest = load_material_map()
        candidates = [
            PROJECT_ROOT / key for key, entries in manifest.items()
            if any(e.get("blend") == "SourceAlpha,One" and e.get("tex0") for e in entries)
        ]
        candidates = [c for c in candidates if c.exists()]
        if not candidates:
            self.skipTest("no additive model present")
        src = min(candidates, key=lambda c: c.stat().st_size)
        model = BchParser(src.read_bytes(), source_path=src).parse_models(src.stem)[0]
        self.assertIn("additive", {m.blend for m in model.meshes})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / f"{src.stem}.obj"
            export_to_obj(model, out)
            self.assertIn("dqxi_blend additive", out.with_suffix(".mtl").read_text(encoding="utf-8"))
            export_to_gltf(model, out.with_suffix(".gltf"))
            gltf = json.loads(out.with_suffix(".gltf").read_text(encoding="utf-8"))
            self.assertTrue(any(m.get("extras", {}).get("dqxi_blend") == "additive" for m in gltf.get("materials", [])))

    def test_material_texture_transform(self):
        # SPICA DccMaya transform: scale 1, rotation 0 -> uv - translation
        m = BchParser._uv_matrix({"scale": [1.0, 1.0], "rotation": 0.0, "translation": [0.25, 0.5],
                                  "type": "DccMaya", "mapping": "UvCoordinateMap"})
        u, v = BchParser._transform_uv(m, 0.75, 0.75)
        self.assertAlmostEqual(u, 0.5, places=6)
        self.assertAlmostEqual(v, 0.25, places=6)
        # scale 2 doubles the coordinates (texture repeats twice)
        m = BchParser._uv_matrix({"scale": [2.0, 2.0], "rotation": 0.0, "translation": [0.0, 0.0],
                                  "type": "DccMaya", "mapping": "UvCoordinateMap"})
        self.assertEqual(tuple(round(c, 6) for c in BchParser._transform_uv(m, 0.25, 0.5)), (0.5, 1.0))
        self.assertIsNone(BchParser._uv_matrix({"scale": [1.0, 1.0], "rotation": 0.0, "translation": [0.0, 0.0]}))
        self.assertIsNone(BchParser._uv_matrix({"scale": [2.0, 2.0], "mapping": "CameraSphereEnvMap"}))

    def test_pica_texture_formats_match_spica(self):
        # RGB565 (bg), RGBA4 (2d model) and an L4 texture stored in the RawExt
        # section; all used to be decoded as ETC1 or read from the wrong section.
        ref_root = PROJECT_ROOT / "build/spica_ref"
        if not (ref_root / "index.json").is_file():
            self.skipTest("SPICA reference dump missing (tools/audit_model_textures.py --dump)")
        import numpy as np
        from PIL import Image

        samples = [
            ("game_data/packs/2d/bg/b001_101a/b001_101a.bch", None),
            ("game_data/packs/2d/model/g0010a/g0010a.bch", None),
            ("game_data/packs/3d/bg/b018_001a/b018_001a.bch", "mt_b018_white01"),
        ]
        checked = 0
        for rel, only in samples:
            src = PROJECT_ROOT / rel
            if not src.is_file():
                continue
            ours = dict(BchParser(src.read_bytes(), source_path=src).extract_textures())
            for png in (ref_root / rel[:-4]).glob("*.png"):
                if only and png.stem != only:
                    continue
                ref = np.asarray(Image.open(png).convert("RGBA")).astype(int)
                mine = np.asarray(ours[png.stem].convert("RGBA")).astype(int)
                self.assertEqual(mine.shape, ref.shape, png.stem)
                visible = (ref[..., 3] > 0)[..., None]
                self.assertLessEqual(int((np.abs(mine - ref) * visible).max()), 4, png.stem)
                checked += 1
        if not checked:
            self.skipTest("sample BCH files not present")

    def test_rigid_meshes_are_bone_placed(self):
        # Faces/eyes are stored on the head bone; without bone placement they sat
        # at the character's feet.
        bch = PROJECT_ROOT / "game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"
        if not bch.exists():
            self.skipTest("sample character model is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("cha01000a_h")[0]
        face = next(m for m in model.meshes if m.texture_name == "cha01000a_face_composite.png")
        self.assertGreater(min(p[1] for p in face.positions), 1.0)
        top = max(p[1] for m in model.meshes for p in m.positions)
        self.assertGreater(min(p[1] for p in face.positions), top * 0.7)

    def test_layered_face_is_baked_onto_skin(self):
        # The face material adds eye/mouth atlas cells (black background) onto the
        # skin texture. Exported alone, the atlas made the face nearly black.
        import numpy as np

        bch = PROJECT_ROOT / "game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"
        if not bch.exists():
            self.skipTest("sample character model is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("cha01000a_h")[0]
        images = {name: np.asarray(img.convert("RGBA")) for name, img in model.textures}
        face = next(m for m in model.meshes if m.texture_name.endswith("_composite.png"))
        tex = images[face.texture_name[:-4]]
        h, w = tex.shape[:2]
        dark = total = 0
        self.assertEqual(len(face.corner_uvs), len(face.indices))
        for i in range(0, len(face.indices) - 2, 3):
            corners = face.corner_uvs[i:i + 3]
            u = sum(c[0] for c in corners) / 3
            v = sum(c[1] for c in corners) / 3
            pixel = tex[min(int((1 - v % 1) * h), h - 1), min(int(u % 1 * w), w - 1)]
            dark += int(pixel[:3].max() < 40)
            total += 1
        self.assertLess(dark / total, 0.1, f"{dark}/{total} face triangles are black")

    def test_baked_face_triangles_do_not_overlap(self):
        # Face skin UVs overlap 2.4-5x (one skin patch, detail from the eye/mouth
        # UVs). The bake gives every triangle its own texels, so none overwrites another.
        import numpy as np
        from PIL import Image, ImageDraw

        bch = PROJECT_ROOT / "game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"
        if not bch.exists():
            self.skipTest("sample character model is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("cha01000a_h")[0]
        face = next(m for m in model.meshes if m.texture_name.endswith("_composite.png"))
        size = 1024
        layers = np.zeros((size, size), np.uint16)
        for i in range(0, len(face.indices) - 2, 3):
            img = Image.new("L", (size, size))
            ImageDraw.Draw(img).polygon([(u * size, (1 - v) * size) for u, v in face.corner_uvs[i:i + 3]], fill=1)
            layers += np.asarray(img)
        # polygon edges are shared at most by neighbours' outlines; interiors never
        self.assertLessEqual(int((layers > 1).sum()), int(0.002 * size * size))
        # the OBJ keeps the BCH vertex order (model_patch relies on it) but gives corners own UVs
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "hero.obj"
            export_to_obj(model, out)
            text = out.read_text(encoding="utf-8")
            self.assertEqual(sum(1 for line in text.splitlines() if line.startswith("v ")),
                             sum(len(m.positions) for m in model.meshes))
            self.assertEqual(obj_positions(out), [p for m in model.meshes for p in m.positions])

    def test_terrain_decal_uses_its_mask_as_alpha(self):
        # b001_106a: unit 0 is a black/white *_nuki* mask read through its red channel
        # as alpha, the colour comes from the grass in unit 1. Exporting unit 0 as the
        # diffuse showed the mask as an opaque cloud pattern.
        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_106a/b001_106a.bch"
        if not bch.exists():
            self.skipTest("sample map is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("b001_106a")[0]
        decal = next(m for m in model.meshes if m.mask_texture == "tl_b001_nuki01.png")
        self.assertEqual(decal.texture_name, "tl_b001_grass01.png")
        self.assertEqual(decal.mask_channel, "red")
        self.assertEqual(len(decal.mask_uvs), len(decal.positions))
        self.assertNotIn("tl_b001_nuki01.png", {m.texture_name for m in model.meshes})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "b001_106a.obj"
            export_to_obj(model, out)
            mtl = out.with_suffix(".mtl").read_text(encoding="utf-8")
            self.assertIn("dqxi_mask_map tl_b001_nuki01.png", mtl)
            self.assertIn("dqxi_mask_channel red", mtl)
            self.assertIn("dqxi_vt_mask ", out.read_text(encoding="utf-8"))
            export_to_gltf(model, out.with_suffix(".gltf"))
            gltf = json.loads(out.with_suffix(".gltf").read_text(encoding="utf-8"))
            self.assertTrue(any("dqxi_mask" in m.get("extras", {}) for m in gltf["materials"]))

    def test_decal_vertex_alpha_is_exported(self):
        # blended decals (mist, cloud and water overlays) fade out through vertex alpha
        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_106a/b001_106a.bch"
        if not bch.exists():
            self.skipTest("sample map is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("b001_106a")[0]
        faded = [m for m in model.meshes if m.vertex_alpha]
        self.assertTrue(faded, "no draw kept its vertex alpha")
        self.assertTrue(all(m.blend != "opaque" for m in faded))
        self.assertTrue(any(min(m.vertex_alpha) < 0.05 for m in faded))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "b001_106a.obj"
            export_to_obj(model, out)
            self.assertIn("dqxi_va ", out.read_text(encoding="utf-8"))
            export_to_gltf(model, out.with_suffix(".gltf"))
            gltf = json.loads(out.with_suffix(".gltf").read_text(encoding="utf-8"))
            self.assertTrue(any("COLOR_0" in prim["attributes"] for mesh in gltf["meshes"] for prim in mesh["primitives"]))

    def test_map_vertex_lighting_keeps_the_combiner_scale(self):
        # map draws: Modulate(FragmentPrimaryColor, PrimaryColor) -> Modulate(Previous, Texture) x2;
        # the export must carry min(rgb * s0, 1) per vertex and s1 per draw, not the raw half-bright rgb
        bch = PROJECT_ROOT / "game_data/packs/3d/bg/b001_106a/b001_106a.bch"
        if not bch.exists():
            self.skipTest("sample map is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("b001_106a")[0]
        lit = [m for m in model.meshes if m.vertex_rgb]
        self.assertTrue(lit)
        self.assertIn(2.0, {m.color_scale for m in lit})
        self.assertTrue(all(0.0 <= c <= 1.0 for m in lit for v in m.vertex_rgb for c in v))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "b001_106a.obj"
            export_to_obj(model, out)
            self.assertIn("dqxi_vc ", out.read_text(encoding="utf-8"))
            self.assertIn("dqxi_color_scale 2", out.with_suffix(".mtl").read_text(encoding="utf-8"))

    def test_readable_c_pass(self):
        # synthetic Ghidra-style input; the pass names objects, fields, types, calls and temps
        from tools.readable_c import rewrite
        src = "\n".join([
            "void FUN_00200000(int param_1,undefined4 param_2)",
            "{",
            "  int iVar1;",
            "  uint uVar2;",
            "  iVar1 = GetActorID(0);",
            "  uVar2 = *(uint *)(param_1 + 0x24);",
            "  *(undefined4 *)(*(int *)(param_1 + 0x160) + 0x1c) = param_2;",
            "  FUN_00300000(param_1 + 0x254,DAT_00401000,iVar1,uVar2);",
            "  return;",
            "}",
        ])
        out = rewrite(src, {0x00300000: "UpdateTimer"})
        self.assertIn("self->f_160->f_1c = arg2;", out)
        self.assertIn("UpdateTimer(&self->f_254,g_00401000,actorId,f24);", out)
        self.assertIn("u32 f24;", out)
        self.assertNotRegex(out, r"param_|undefined|DAT_|iVar|uVar")
        self.assertIn("func_00200000(int self,u32 arg2)", out)

    def test_alternate_hand_poses_are_hidden(self):
        # characters ship Hand01..05 per side; the game shows one pose at a time
        bch = PROJECT_ROOT / "game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"
        if not bch.exists():
            self.skipTest("sample character model is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("cha01000a_h")[0]
        hands = {m.node_name: m.hidden for m in model.meshes if "Hand" in m.node_name and "Outline" not in m.node_name}
        self.assertFalse(hands["L_Hand01_MS"])
        self.assertFalse(hands["R_Hand01_MS"])
        self.assertTrue(all(hands[f"{side}_Hand0{n}_MS"] for side in "LR" for n in range(2, 6)))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "hero.obj"
            export_to_obj(model, out)
            self.assertIn("dqxi_hidden 1", out.with_suffix(".mtl").read_text(encoding="utf-8"))

    def test_face_pose_changes_the_baked_face(self):
        # Expressions slide the eye/mouth atlases (MaterialTexCoord0/1Trans);
        # baking a different pose must give a different face texture.
        import numpy as np

        bch = PROJECT_ROOT / "game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"
        if not bch.exists():
            self.skipTest("sample character model is not present")

        def face(pose):
            parser = BchParser(bch.read_bytes(), source_path=bch)
            parser.face_pose = pose
            model = parser.parse_models("cha01000a_h")[0]
            return np.asarray(dict(model.textures)["cha01000a_face_composite"].convert("RGB"))

        rest = face(((0.0, 0.0), (0.0, 0.0)))
        other = face(((0.0, 0.797), (0.0, 0.75)))
        self.assertEqual(rest.shape, other.shape)
        self.assertTrue((rest != other).any(), "pose did not change the baked face")

    def test_gltf_uvs_use_top_left_origin(self):
        # BCH/OBJ UVs start bottom-left, glTF top-left: the glTF must store 1 - v
        # or every texture shows up vertically flipped (faces upside down).
        bch = PROJECT_ROOT / "game_data/packs/3d/model/w1603b/w1603b.bch"
        if not bch.exists():
            self.skipTest("sample weapon BCH is not present")
        model = BchParser(bch.read_bytes(), source_path=bch).parse_models("w1603b")[0]
        gltf, blob = export_gltf(model)
        prim = gltf["meshes"][0]["primitives"][0]
        acc = gltf["accessors"][prim["attributes"]["TEXCOORD_0"]]
        view = gltf["bufferViews"][acc["bufferView"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        u, v = struct.unpack_from("<2f", blob, start)
        src_u, src_v = model.meshes[0].uvs[0]
        self.assertAlmostEqual(u, src_u, places=5)
        self.assertAlmostEqual(v, 1.0 - src_v, places=5)

    def test_table_edit_by_field_name(self):
        # Named-field table edits are single same-size scalar writes.
        from tools.table_edit import Table

        if not (PROJECT_ROOT / "game_assets/tables/packs/syscmn/item.json").is_file():
            self.skipTest("item table not extracted")
        table = Table("syscmn/item.json")
        original = bytes(table.raw)
        self.assertEqual(table.value(0, "buy_price"), 8)
        self.assertEqual(table.value(0, "sell_price"), 4)
        table.set(0, "buy_price", "5")
        self.assertEqual(table.value(0, "buy_price"), 5)
        self.assertEqual(len(table.raw), len(original))
        changed = [i for i, (a, b) in enumerate(zip(original, table.raw)) if a != b]
        self.assertEqual(changed, [table.address(0, table.field("buy_price"))])

    def test_compressed_pack_round_trip(self):
        # PACA packs: rebuilding must keep the magic and the exact decompressed bytes.
        from tools import blz, pack

        src = PROJECT_ROOT / "game_data/romfs/syscmn.pack"
        if not src.is_file():
            self.skipTest("syscmn.pack not extracted")
        raw = src.read_bytes()
        built = pack.Pack.parse(raw).build()
        self.assertEqual(built[:4], b"PACA")
        self.assertEqual(blz.decompress(built), blz.decompress(raw))
        self.assertLessEqual(len(built), len(raw))

    def test_table_edit_lands_in_compressed_pack(self):
        # A named-field table edit survives the PACA recompression that
        # patch_asset uses for syscmn.pack.
        from tools import pack
        from tools.patch_asset import rebuild_pack
        from tools.table_edit import Table

        src = PROJECT_ROOT / "game_data/romfs/syscmn.pack"
        if not src.is_file():
            self.skipTest("syscmn.pack not extracted")
        table = Table("syscmn/item.json")
        table.set(0, "buy_price", "5")
        with tempfile.TemporaryDirectory() as td:
            replacement = Path(td) / "item.bxon"
            replacement.write_bytes(bytes(table.raw))
            built = rebuild_pack(src, "item.bxon", replacement, Path(td) / "syscmn.pack")
        self.assertLessEqual(len(built), src.stat().st_size)
        item = next(e for e in pack.Pack.parse(built).entries if e.name == "item.bxon").data
        self.assertEqual(struct.unpack_from("<I", item, table.address(0, table.field("buy_price")))[0], 5)

    def test_weapon_model_names(self):
        names_file = PROJECT_ROOT / "game_assets/models/model_names.json"
        if not names_file.is_file():
            self.skipTest("run tools/build_model_names.py first")
        names = json.loads(names_file.read_text(encoding="utf-8"))
        self.assertEqual(names.get("w1603b"), "Flametang boomerang")
        self.assertEqual(names.get("w1003b"), "Flametang boomerang")

    def test_romfs_hash_tree(self):
        result = verify_romfs(PROJECT_ROOT / "original/romfs.bin")
        self.assertTrue(result["ok"], result)

    def test_resized_romfs_header_matches_retail(self):
        # recomputing the IVFC header for the retail data size reproduces it exactly
        from tools import romfs_hash

        with open(PROJECT_ROOT / "original/romfs.bin", "rb") as f:
            head = f.read(0x60)
        info = romfs_hash.parse_header(head)
        self.assertEqual(romfs_hash.resized_header(head, info["data_size"]), head)
        self.assertEqual(romfs_hash.total_size(info), (PROJECT_ROOT / "original/romfs.bin").stat().st_size)

    def test_grown_member_is_appended_to_romfs(self):
        # Growing a table makes syscmn.pack larger than its RomFS slot: it must be
        # appended at the end of the data, the hash levels moved, and the file
        # must read back with its new content and size.
        from tools import pack, romfs_hash
        from tools.patch_asset import rebuild_pack, write_romfs_file

        src = PROJECT_ROOT / "game_data/romfs/syscmn.pack"
        if not src.is_file():
            self.skipTest("syscmn.pack not extracted")
        original = src.read_bytes()
        item = next(e for e in pack.Pack.parse(original).entries if e.name == "item.bxon").data
        grown_item = item + bytes(range(256)) * 64  # 16 KiB more than any recompression saves
        filler = bytes((i * 7) & 0xFF for i in range(0x5123))
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            romfs = td / "romfs.bin"
            _write_test_romfs(romfs, [("syscmn.pack", original), ("filler.bin", filler)])
            self.assertTrue(romfs_hash.verify(romfs)["ok"])
            before = _read_test_romfs(romfs)
            old_offset, old_size = before["syscmn.pack"][0], len(original)

            replacement = td / "item.bxon"
            replacement.write_bytes(grown_item)
            built = rebuild_pack(src, "item.bxon", replacement, td / "syscmn.pack")
            self.assertGreater(len(built), old_size)
            old_info = romfs_hash.parse_header(romfs.read_bytes()[:0x60])

            placed = write_romfs_file(romfs, old_offset, old_size, built)
            romfs_hash.rebuild(romfs)

            self.assertTrue(placed["relocated"])
            self.assertTrue(romfs_hash.verify(romfs)["ok"])
            info = romfs_hash.parse_header(romfs.read_bytes()[:0x60])
            self.assertGreater(info["data_size"], old_info["data_size"])
            self.assertEqual(romfs.stat().st_size, romfs_hash.total_size(info))
            after = _read_test_romfs(romfs)
            self.assertEqual(after["syscmn.pack"], (placed["offset"], built))
            self.assertEqual(after["filler.bin"], before["filler.bin"])
            entries = pack.Pack.parse(after["syscmn.pack"][1]).entries
            self.assertEqual(next(e for e in entries if e.name == "item.bxon").data, grown_item)
            others = {e.name: e.data for e in pack.Pack.parse(original).entries if e.name != "item.bxon"}
            self.assertEqual({e.name: e.data for e in entries if e.name != "item.bxon"}, others)


def _write_test_romfs(path: Path, files: list[tuple[str, bytes]]) -> None:
    """A minimal RomFS (root directory with `files`) with a valid IVFC hash tree."""
    from tools import romfs_hash

    dir_meta = struct.pack("<IIIIII", 0, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0xFFFFFFFF, 0)
    file_meta = bytearray()
    data = bytearray()
    for i, (name, blob) in enumerate(files):
        while len(data) % 0x10:
            data.append(0)
        enc = name.encode("utf-16-le")
        size = 0x20 + ((len(enc) + 3) & ~3)
        sibling = len(file_meta) + size if i + 1 < len(files) else 0xFFFFFFFF
        file_meta += struct.pack("<IIQQII", 0, sibling, len(data), len(blob), 0xFFFFFFFF, len(enc))
        file_meta += enc + bytes(size - 0x20 - len(enc))
        data += blob
    tables = [struct.pack("<I", 0), dir_meta, struct.pack("<I", 0), bytes(file_meta)]
    header_len = 0x28
    offs, pos = [], header_len
    for t in tables:
        offs += [pos, len(t)]
        pos += len(t)
    file_data_off = romfs_hash.align(pos, 0x10)
    level3 = struct.pack("<10I", header_len, *offs, file_data_off) + b"".join(tables)
    level3 += bytes(file_data_off - len(level3)) + data

    head = bytearray(0x60)
    head[:8] = b"IVFC" + struct.pack("<I", 0x10000)
    for i in range(3):
        struct.pack_into("<QQI", head, 0x0C + i * 0x18, 0, 0, 12)
    head = romfs_hash.resized_header(bytes(head), len(level3))
    info = romfs_hash.parse_header(head)
    image = bytearray(romfs_hash.total_size(info))
    image[:0x60] = head
    image[info["data_start"]:info["data_start"] + len(level3)] = level3
    path.write_bytes(bytes(image))
    romfs_hash.rebuild(path)


def _read_test_romfs(path: Path) -> dict:
    """{name: (data offset, bytes)} for the files in the RomFS root directory."""
    from tools import romfs_hash

    raw = path.read_bytes()
    info = romfs_hash.parse_header(raw[:0x60])
    l3 = raw[info["data_start"]:info["data_start"] + info["data_size"]]
    header = struct.unpack_from("<10I", l3)
    dir_meta, file_meta, file_data = header[3], header[7], header[9]
    out = {}
    pos = struct.unpack_from("<I", l3, dir_meta + 0x0C)[0]
    while pos != 0xFFFFFFFF:
        _, sibling, off, size, _, name_len = struct.unpack_from("<IIQQII", l3, file_meta + pos)
        name = l3[file_meta + pos + 0x20:file_meta + pos + 0x20 + name_len].decode("utf-16-le")
        out[name] = (off, l3[file_data + off:file_data + off + size])
        pos = sibling
    return out


if __name__ == "__main__":
    unittest.main()


