#!/usr/bin/env python3
"""tools/model_tool.py - Universal NW4C BCH 3D Model Decompiler & glTF / OBJ Exporter.

Parses NintendoWare for CTR (NW4C) BCH binary model archives (.bch, .bcmdl, .bcmres),
decodes 3D meshes (VBOs, IBOs, vertex positions, normals, UVs, colors, bone weights),
and exports 3D models into standard glTF 2.0 (.gltf, .bin) and Wavefront OBJ (.obj, .mtl) formats.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
if "../reference project" not in sys.path:
    sys.path.insert(0, "../reference project")

from tools import pack
from tools.texture_tool import PICA_FORMATS, decode_tiled, tiled_size

MODELS_OUT = PROJECT_ROOT / "game_models"
MATERIAL_MAP = PROJECT_ROOT / "game_assets" / "models" / "material_map.json.gz"
SKIN_MAP = PROJECT_ROOT / "game_assets" / "models" / "skin_map.json.gz"
_MATERIAL_MAP_CACHE: dict[str, list[dict]] | None = None
_SKIN_MAP_CACHE: dict[str, list[dict | None]] | None = None


def load_skin_map() -> dict[str, list[dict | None]]:
    """Loads the SPICA-derived per-draw bone placement manifest (optional).

    Rigid and unskinned draws store vertices relative to a bone (faces and eyes
    sit on the head bone, weapons on a hand bone, ...). Each entry gives the
    world matrix of every bone in the draw's palette; see tools/spica_ref.
    """
    global _SKIN_MAP_CACHE
    if _SKIN_MAP_CACHE is None:
        _SKIN_MAP_CACHE = {}
        if SKIN_MAP.is_file():
            with gzip.open(SKIN_MAP, "rt", encoding="utf-8") as f:
                _SKIN_MAP_CACHE = json.load(f)
    return _SKIN_MAP_CACHE


def load_material_map() -> dict[str, list[dict]]:
    """Loads the SPICA-verified per-draw texture manifest (optional)."""
    global _MATERIAL_MAP_CACHE
    if _MATERIAL_MAP_CACHE is not None:
        return _MATERIAL_MAP_CACHE
    if not MATERIAL_MAP.is_file():
        _MATERIAL_MAP_CACHE = {}
        return _MATERIAL_MAP_CACHE
    with gzip.open(MATERIAL_MAP, "rt", encoding="utf-8") as f:
        _MATERIAL_MAP_CACHE = json.load(f)
    return _MATERIAL_MAP_CACHE


def draw_texture(entry: dict) -> str:
    """The texture a draw's colour combiner samples (what the export shows);
    falls back to `pick_diffuse` for manifests without combiner data."""
    colour, _ = BchParser._draw_layers(entry)
    if colour is not None:
        return entry[f"tex{colour}"]
    return pick_diffuse(entry.get("tex0", ""), entry.get("tex1", ""))


def pick_diffuse(tex0: str, tex1: str = "") -> str:
    """Picks the base-colour texture from a material's three texture units."""
    if not tex0:
        return tex1
    low = tex0.lower()
    if ("cubemap" in low or low.startswith("ya_") or "env" in low) and tex1:
        return tex1
    return tex0

# PICA200 GPU Register IDs
GPUREG_ATTRIBBUFFERS_LOC = 0x0200
GPUREG_ATTRIBBUFFERS_FORMAT_LOW = 0x0200
GPUREG_ATTRIBBUFFERS_FORMAT_HIGH = 0x0201
GPUREG_ATTRIBBUFFER0_OFFSET = 0x0202
GPUREG_ATTRIBBUFFER0_CONFIG1 = 0x0203
GPUREG_ATTRIBBUFFER0_CONFIG2 = 0x0204
GPUREG_INDEXBUFFER_CONFIG = 0x0227
GPUREG_NUMVERTICES = 0x0228
GPUREG_PRIMITIVE_CONFIG = 0x0229
GPUREG_DRAWELEMENTS = 0x022F
GPUREG_VSH_NUM_ATTR = 0x0242
GPUREG_VSH_ATTRIBUTES_PERMUTATION_LOW = 0x02BB
GPUREG_VSH_ATTRIBUTES_PERMUTATION_HIGH = 0x02BC


@dataclass
class VertexAttribute:
    name: str
    format: str
    elements: int
    offset: int = 0
    scale: float = 1.0


@dataclass
class MeshGeometry:
    name: str
    positions: list[tuple[float, float, float]] = field(default_factory=list)
    normals: list[tuple[float, float, float]] = field(default_factory=list)
    uvs: list[tuple[float, float]] = field(default_factory=list)
    # second/third UV sets (TexCoord1/2); used by multi-texture materials
    uvs1: list[tuple[float, float]] = field(default_factory=list)
    uvs2: list[tuple[float, float]] = field(default_factory=list)
    colors: list[tuple[float, float, float, float]] = field(default_factory=list)
    bone_indices: list[int] = field(default_factory=list)
    # per-vertex bone matrix applied by bone placement (12 floats, row-vector
    # layout); None when positions are stored in model space already
    placement: list[list[float]] | None = None
    indices: list[int] = field(default_factory=list)
    material_name: str = "default_mat"
    texture_name: str = ""
    # how the game blends the draw: "opaque", "alpha", "additive" or "multiply"
    blend: str = "opaque"
    # alpha-test threshold 0..1 (texels at or below it are cut out); 0 = no test
    alpha_cutoff: float = 0.0
    # one UV per index entry, when a baked texture needs UVs the vertices can't share
    corner_uvs: list[tuple[float, float]] | None = None
    # second texture whose channel multiplies the alpha (terrain decal masks, *_nuki*):
    # file name, channel ("red", "one_minus_red", "alpha", ...) and its own UVs per vertex
    mask_texture: str = ""
    mask_channel: str = ""
    mask_uvs: list[tuple[float, float]] = field(default_factory=list)
    # per-vertex alpha the game multiplies in (PrimaryColor:Alpha), e.g. decal edge fades;
    # empty when the draw does not read it or every vertex is opaque
    vertex_alpha: list[float] = field(default_factory=list)
    # baked vertex lighting the colour combiner multiplies in (PrimaryColor:Color):
    # per vertex min(rgb * stage-0 scale, 1), then times `color_scale` (stage-1 scale)
    vertex_rgb: list[tuple[float, float, float]] = field(default_factory=list)
    color_scale: float = 1.0
    # hidden by default in game (e.g. alternate hand poses L_Hand02..05)
    hidden: bool = False
    node_name: str = ""
    vbo_abs: int = 0
    stride: int = 0
    vertex_count: int = 0
    ibo_abs: int = 0
    index_size: int = 2
    num_indices: int = 0


@dataclass
class BchModel:
    name: str
    transform: list[float]  # 12 floats (3x4 matrix)
    meshes: list[MeshGeometry] = field(default_factory=list)
    materials: list[str] = field(default_factory=list)
    textures: list[tuple[str, Image.Image]] = field(default_factory=list)


class BchParser:
    """Parses NW4C BCH binary containers and extracts 3D mesh geometry."""

    def __init__(self, data: bytes, source_path: str | Path | None = None):
        if len(data) < 0x44 or data[:4] != b"BCH\0":
            raise ValueError("Invalid BCH binary model header")
        self.data = data
        self.source_path = Path(source_path).resolve() if source_path else None
        (
            self.magic,
            self.bcomp,
            self.fcomp,
            self.ver,
            self.hdr_off,
            self.str_off,
            self.cmd_off,
            self.data_off,
            self.data_ext_off,
            self.reloc_off,
            self.hdr_len,
            self.str_len,
            self.cmd_len,
            self.data_len,
            self.data_ext_len,
            self.reloc_len,
        ) = struct.unpack_from("<4sBBH6I6I", data, 0)
        self._reloc_data: bytes | None = None
        self.duplicates_removed = 0

    def _legacy_section(self, section: int) -> int:
        """Maps a relocation target id from older BCH revisions (SPICA GetLegacyRelocDiff)."""
        bc = self.bcomp
        if 7 < bc < 0x21 and section >= 6:
            return section - 1
        if bc < 7 and section >= 3:
            return section + 1
        return section

    def _section_base(self, section: int) -> int | None:
        """File offset a relocation section id points into (SPICA H3DSection).

        0 contents, 1 strings, 2/3 commands, 4-8 raw data, 9-13 raw ext data;
        the Index16 variants (7, 12) also set bit 31, PICA's "16-bit indices" flag.
        """
        if section == 0:
            return self.hdr_off
        if section == 1:
            return self.str_off
        if section in (2, 3):
            return self.cmd_off
        if 4 <= section <= 8:
            return self.data_off | (1 << 31 if section == 7 else 0)
        if 9 <= section <= 13:
            return self.data_ext_off | (1 << 31 if section == 12 else 0)
        return None

    def _relocated(self) -> bytes:
        """Returns a copy of the BCH with relocation entries resolved to absolute offsets.

        BCH stores inter-object references as 25-bit section-relative offsets plus a
        section id. The relocation table lists every pointer field. Resolving the table
        once lets the mesh/material parser follow model -> mesh -> material links that
        are not visible in the raw command stream.
        """
        if self._reloc_data is not None:
            return self._reloc_data
        data = bytearray(self.data)
        for off in range(0, self.reloc_len, 4):
            if self.reloc_off + off + 4 > len(self.data):
                break
            v = struct.unpack_from("<I", self.data, self.reloc_off + off)[0]
            ptr = v & 0x1FFFFFF
            target = self._legacy_section((v >> 25) & 0xF)
            source = v >> 29
            if target != 1:  # everything except string offsets is 4-byte aligned
                ptr <<= 2
            src_base = self._section_base(source)
            dst_base = self._section_base(target)
            if src_base is None or dst_base is None:
                continue
            addr = (src_base & 0x7FFFFFFF) + ptr
            if addr + 4 > len(data):
                continue
            value = struct.unpack_from("<I", data, addr)[0]
            struct.pack_into("<I", data, addr, (value + dst_base) & 0xFFFFFFFF)
        self._reloc_data = bytes(data)
        return self._reloc_data

    def _abs_string(self, offset: int) -> str:
        if offset <= 0 or offset >= len(self.data):
            return ""
        end = self.data.find(b"\0", offset)
        if end == -1:
            end = len(self.data)
        return self.data[offset:end].decode("ascii", "replace")

    def _material_texture_names(self, texture_names: list[str]) -> list[str]:
        """Maps global material index -> most likely diffuse texture name.

        BCH material entries keep a ``MaterialName@ModelName`` reference but do not
        store the diffuse texture pointer in the block we parse. DQXI material names
        and texture names share the same asset suffix (for example
        ``ba_b001_puddle01`` -> ``ko_b001_puddle01``), so we match that suffix instead
        of assigning textures by list position. Ambiguous/non-texture materials are
        left empty rather than silently using a cubemap or LUT.
        """
        rel = self._relocated()
        tree, count, _vals = struct.unpack_from("<3I", self.data, self.hdr_off + 12)
        if count <= 0 or count > 4096 or self.hdr_off + tree + count * 4 > len(rel):
            return []
        ptrs = struct.unpack_from(f"<{count}I", rel, self.hdr_off + tree)
        texture_names = sorted(set(texture_names))
        out: list[str] = []
        for ptr in ptrs:
            mat_name = ""
            if ptr and ptr + 0x10C <= len(rel):
                mat_ref = self._abs_string(struct.unpack_from("<I", rel, ptr + 0x108)[0])
                mat_name = mat_ref.split("@", 1)[0]
            tex = self._match_material_texture(mat_name, texture_names)
            out.append(tex)
        return out

    @staticmethod
    def _match_material_texture(mat_name: str, texture_names: list[str]) -> str:
        if not mat_name or mat_name.lower().startswith(("lambert", "default")):
            return ""
        norm = mat_name.lower()
        norms = {norm}
        if "_" in norm:
            norms.add(norm.split("_", 1)[1])
        cleaned: set[str] = set()
        for n in norms:
            for token in ("_mt", "-mt"):
                if n.endswith(token):
                    n = n[: -len(token)]
            n = n.replace("_high", "").replace("_low", "").strip("_ ")
            if n:
                cleaned.add(n)
        norms = cleaned
        norms.difference_update({"high", "low", "mt", ""})
        if not norms:
            return ""
        # Character materials: the face is the shared eye/mouth atlas (the
        # ``*_high`` texture), while Body/Hair have their own diffuse atlases.
        joined = " ".join(norms)
        if "body" in joined:
            cands = [t for t in texture_names if "body" in t.lower()]
            if cands:
                return sorted(cands, key=len)[0]
        if "hair" in joined:
            cands = [t for t in texture_names if "hair" in t.lower() and "env" not in t.lower()]
            if cands:
                return sorted(cands, key=len)[0]
        if "face" in joined:
            cands = [
                t for t in texture_names
                if t.lower().endswith("_high")
                and "body" not in t.lower()
                and "hair" not in t.lower()
                and "runway" not in t.lower()
                and "env" not in t.lower()
            ]
            if cands:
                return sorted(cands, key=len)[0]
        # Prefer the model-specific diffuse over environment/cubemap helpers.
        bad_tokens = ("env", "cubemap", "silhouette", "nuki", "runway")
        if any(t in n for n in norms for t in bad_tokens):
            bad_tokens = ()
        ranked: list[tuple[int, int, str]] = []
        for tex in texture_names:
            low = tex.lower()
            best_rank = 99
            for norm in norms:
                if low == norm:
                    rank = 0
                elif low.endswith("_" + norm) or low.endswith(norm):
                    rank = 1
                elif "_" + norm in low:
                    rank = 2
                else:
                    continue
                best_rank = min(best_rank, rank)
            if best_rank == 99:
                continue
            if any(t in low for t in bad_tokens):
                best_rank += 10
            ranked.append((best_rank, len(low), tex))
        if not ranked:
            return ""
        ranked.sort()
        return ranked[0][2]

    def _mesh_material_indices(self) -> list[int]:
        """Returns mesh -> material index in draw order from the model dictionary."""
        rel = self._relocated()
        tree, count, _vals = struct.unpack_from("<3I", self.data, self.hdr_off)
        if count <= 0 or count > 4096 or self.hdr_off + tree + count * 4 > len(rel):
            return []
        model_ptrs = struct.unpack_from(f"<{count}I", rel, self.hdr_off + tree)
        indices: list[int] = []
        global_mat = 0
        for model_ptr in model_ptrs:
            if not model_ptr or model_ptr + 0x48 > len(rel):
                continue
            mat_count = struct.unpack_from("<H", rel, model_ptr + 0x38)[0]
            mesh_ptr = struct.unpack_from("<I", rel, model_ptr + 0x40)[0]
            mesh_count = struct.unpack_from("<I", rel, model_ptr + 0x44)[0]
            if mesh_count > 10000 or mesh_ptr + mesh_count * 0x38 > len(rel):
                global_mat += mat_count
                continue
            for i in range(mesh_count):
                base = mesh_ptr + i * 0x38
                local = struct.unpack_from("<H", rel, base)[0]
                subs = struct.unpack_from("<H", rel, base + 0x14)[0]
                if subs < 1 or subs > 64:
                    subs = 1
                indices.extend([global_mat + local] * subs)
            global_mat += mat_count
        return indices

    def _source_key(self) -> str | None:
        if not self.source_path:
            return None
        try:
            return self.source_path.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return None

    @staticmethod
    def _align_draws(entries: list, meshes: list[MeshGeometry]) -> list:
        """Pairs each parsed draw with its manifest entry.

        Entries carry the draw's vertex/index buffer file offsets ("vbo"/"ibo"),
        which identify a draw exactly; SPICA's model -> mesh -> submesh order is
        not always the command-stream order. Manifests without the keys fall back
        to position. Draws with no matching entry get None.
        """
        if not entries:
            return [None] * len(meshes)
        if all(e is None or "ibo" in e for e in entries):
            by_key = {(e["vbo"], e["ibo"]): e for e in entries if e is not None}
            return [by_key.get((m.vbo_abs, m.ibo_abs)) for m in meshes]
        if len(entries) != len(meshes):
            return [None] * len(meshes)
        return list(entries)

    # Character faces combine up to three textures on the GPU, e.g.
    #   Add(Texture0,Texture1) -> AddMult(Previous,Texture2)
    # = eye cells + mouth cells (atlas with a black background) + skin. Faces use
    # several such combiner recipes; `_bake_layered_faces` evaluates the first two
    # stages so every variant bakes to one texture. Unit i reads UV set i (Config0120).
    # Expression to bake: texture-coordinate translations of unit 0 (eyes) and
    # unit 1 (mouth), as animated by MaterialTexCoord0/1Trans in the motion files
    # (see tools/face_expressions.py). None = the material's own translations.
    face_pose: tuple[tuple[float, float], tuple[float, float]] | None = None

    @staticmethod
    def _uv_matrix(coord: dict | None, translation=None) -> tuple[float, ...] | None:
        """(m11, m12, m21, m22, m41, m42) of a material's texture transform (SPICA's
        TextureTransform.GetTransform); None for the identity or non-UV mappings."""
        import math

        if not coord or coord.get("mapping", "UvCoordinateMap") != "UvCoordinateMap":
            return None
        sx, sy = coord.get("scale", [1.0, 1.0])
        r = coord.get("rotation", 0.0)
        tx, ty = translation if translation is not None else coord.get("translation", [0.0, 0.0])
        if (sx, sy, r, tx, ty) == (1.0, 1.0, 0.0, 0.0, 0.0):
            return None
        ca, sa = math.cos(r), math.sin(r)
        kind = coord.get("type", "DccMaya")
        if kind == "DccSoftImage":
            m41, m42 = sx * (-ca * tx - sa * ty), sy * (sa * tx - ca * ty)
        elif kind == "Dcc3dsMax":
            m41 = sx * ca * (-tx - 0.5) - sx * sa * (ty - 0.5) + 0.5
            m42 = sy * sa * (-tx - 0.5) + sy * ca * (ty - 0.5) + 0.5
        else:  # DccMaya
            m41 = sx * ((0.5 * sa - 0.5 * ca) + 0.5 - tx)
            m42 = sy * ((0.5 * -sa - 0.5 * ca) + 0.5 - ty)
        return (sx * ca, sy * sa, sx * -sa, sy * ca, m41, m42)

    @staticmethod
    def _transform_uv(m: tuple[float, ...] | None, u: float, v: float) -> tuple[float, float]:
        if m is None:
            return u, v
        return u * m[0] + v * m[2] + m[4], u * m[1] + v * m[3] + m[5]

    @staticmethod
    def _parse_tev(stage: str) -> tuple[str, list[str]]:
        op, _, args = stage.partition("(")
        return op, args.rstrip(")").split(",")

    @classmethod
    def _face_base_unit(cls, entry: dict) -> int | None:
        """The unit holding the skin texture: the one named like '<char>_face', else
        (monsters name it '<model>_01_high') the texture the second combiner stage
        applies to the summed eye/mouth cells."""
        for unit in (2, 1, 0):
            name = entry.get(f"tex{unit}", "").lower()
            if name.endswith("face") and "env" not in name:
                return unit
        tev = entry.get("tev", [])
        if len(tev) >= 2:
            op, srcs = cls._parse_tev(tev[1])
            if op in ("AddMult", "Add", "MultAdd", "Modulate") and "Previous" in srcs[:2]:
                for src in srcs[:2]:
                    if src.startswith("Texture"):
                        name = entry.get(f"tex{src[-1]}", "").lower()
                        if name and "env" not in name:
                            return int(src[-1])
        return None

    def _bake_layered_faces(
        self, meshes: list[MeshGeometry], images: dict[str, Image.Image]
    ) -> list[tuple[str, Image.Image]]:
        """Bakes multi-texture face materials into one texture on the skin's UVs.

        Lighting and per-stage constant colours are unknown to a static export
        and count as white; environment (reflection) maps are skipped. Matching
        draws switch to the skin UV set and the baked `<skin>_composite` texture.
        Returns the new textures to export next to the model.
        """
        import numpy as np

        key = self._source_key()
        entries = self._align_draws(load_material_map().get(key, []) if key else [], meshes)
        groups: dict[tuple, list[MeshGeometry]] = {}
        for mesh, entry in zip(meshes, entries):
            if not entry or entry.get("texcoord_config") != "Config0120" or len(entry.get("tev", [])) < 2:
                continue
            if "face" not in entry.get("material_name", "").lower():
                continue
            base = self._face_base_unit(entry)
            used = {src for stage in entry["tev"][:2] for src in self._parse_tev(stage)[1] if src.startswith("Texture")}
            if base is None or f"Texture{base}" not in used or len(used) < 2:
                continue
            textures = tuple(entry.get(f"tex{u}", "") for u in range(3))
            uv_sets = (mesh.uvs, mesh.uvs1, mesh.uvs2)
            # reflection maps use generated coordinates and are left neutral, so need no UVs
            needed = [int(t[-1]) for t in used if "env" not in textures[int(t[-1])].lower()]
            if any(textures[u] not in images or len(uv_sets[u]) != len(mesh.uvs) for u in needed):
                continue
            coords = json.dumps(entry.get("uv_coords", []), sort_keys=True)
            groups.setdefault((tuple(entry["tev"][:2]), textures, base, coords), []).append(mesh)

        def sample(img, uv):
            h, w = img.shape[:2]
            x = (np.floor(np.mod(uv[:, 0], 1.0) * w).astype(int)).clip(0, w - 1)
            y = (np.floor((1.0 - np.mod(uv[:, 1], 1.0)) * h).astype(int)).clip(0, h - 1)
            return img[y, x, :3]

        def combine(op, a, b, c):
            if op == "Modulate":
                return a * b
            if op == "Add":
                return a + b
            if op == "AddSigned":
                return a + b - 0.5
            if op == "Subtract":
                return a - b
            if op == "Interpolate":
                return a * c + b * (1.0 - c)
            if op == "MultAdd":
                return a * b + c
            if op == "AddMult":
                return (a + b) * c
            return a  # Replace and anything unexpected

        baked = []
        for (tev, textures, base, coords), group in groups.items():
            coords = json.loads(coords)
            # the pose replaces the eye/mouth translations; everything else keeps the material's
            matrices = {}
            for u in range(3):
                coord = coords[u] if u < len(coords) else None
                override = self.face_pose[u] if self.face_pose is not None and u in (0, 1) and u != base else None
                matrices[u] = self._uv_matrix(coord, override)
            pixels = {u: np.asarray(images[t].convert("RGBA"), dtype=np.float32) / 255.0
                      for u, t in enumerate(textures) if t in images}
            stages = [self._parse_tev(stage) for stage in tev]
            # The skin UVs of a face overlap (one skin patch serves many triangles;
            # eye/mouth detail comes only from UV0/UV1), so baking into skin UV space
            # makes triangles overwrite each other. Every triangle gets its own spot
            # in the composite instead: laid out by its 3D shape, shelf-packed, and
            # addressed through per-corner UVs (`corner_uvs`; positions stay welded).
            tris = [(mesh, i) for mesh in group for i in range(0, len(mesh.indices) - 2, 3)]
            size, placed = self._pack_triangles([[mesh.positions[j] for j in mesh.indices[i:i + 3]] for mesh, i in tris])
            canvas = np.zeros((size, size, 4), np.float32)
            canvas[..., :3] = pixels[base][..., :3].reshape(-1, 3).mean(0) * 255.0
            canvas[..., 3] = 255.0
            corner = {id(mesh): [None] * len(mesh.indices) for mesh in group}
            for (mesh, i), dest in zip(tris, placed):
                tri = mesh.indices[i:i + 3]
                uv_sets = (mesh.uvs, mesh.uvs1, mesh.uvs2)
                px, py = dest[:, 0], dest[:, 1]
                for k in range(3):
                    corner[id(mesh)][i + k] = (px[k] / size, 1.0 - py[k] / size)
                # 2 px of padding around each triangle so filtering never reaches the background
                x0, x1 = int(max(px.min() - 2, 0)), int(min(px.max() + 2, size - 1))
                y0, y1 = int(max(py.min() - 2, 0)), int(min(py.max() + 2, size - 1))
                gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
                d = (py[1] - py[2]) * (px[0] - px[2]) + (px[2] - px[1]) * (py[0] - py[2])
                if abs(d) < 1e-9:
                    continue
                w0 = ((py[1] - py[2]) * (gx - px[2]) + (px[2] - px[1]) * (gy - py[2])) / d
                w1 = ((py[2] - py[0]) * (gx - px[2]) + (px[0] - px[2]) * (gy - py[2])) / d
                w2 = 1.0 - w0 - w1
                # barycentric slack equal to ~2 px at this triangle's scale
                slack = 2.0 * np.sqrt(3.0) / max(np.sqrt(abs(d)), 1e-6)
                inside = (w0 >= -slack) & (w1 >= -slack) & (w2 >= -slack)
                if not inside.any():
                    continue
                w = np.clip(np.stack([w0[inside], w1[inside], w2[inside]], axis=1), 0.0, None)
                w /= w.sum(axis=1, keepdims=True)
                ones = np.ones((len(w), 3), dtype=np.float32)
                texel = {}
                for u, img in pixels.items():
                    if "env" in textures[u].lower() or len(uv_sets[u]) != len(mesh.uvs):
                        texel[u] = ones  # reflection map: view dependent, leave neutral
                        continue
                    uv = w @ np.array([uv_sets[u][j] for j in tri], dtype=np.float64)
                    m = matrices[u]
                    if m is not None:
                        uv = np.stack([uv[:, 0] * m[0] + uv[:, 1] * m[2] + m[4],
                                       uv[:, 0] * m[1] + uv[:, 1] * m[3] + m[5]], axis=1)
                    texel[u] = sample(img, uv)
                previous = ones
                for op, srcs in stages:
                    args = []
                    for src in (srcs + ["Constant"] * 3)[:3]:
                        if src.startswith("Texture") and int(src[-1]) in texel:
                            args.append(texel[int(src[-1])])
                        elif src == "Previous":
                            args.append(previous)
                        else:
                            args.append(ones)  # lighting / constant colours
                    previous = np.clip(combine(op, *args), 0.0, 1.0)
                # strict interior wins over a neighbour's padding
                strict = (w0[inside] >= 0) & (w1[inside] >= 0) & (w2[inside] >= 0)
                ys, xs = np.nonzero(inside)
                for mask in (~strict, strict):
                    canvas[ys[mask] + y0, xs[mask] + x0, :3] = previous[mask] * 255.0
            name = f"{textures[base]}_composite"
            baked.append((name, Image.fromarray(canvas.astype(np.uint8), "RGBA")))
            for mesh in group:
                mesh.corner_uvs = corner[id(mesh)]
                mesh.texture_name = f"{name}.png"
        return baked

    @staticmethod
    def _pack_triangles(tris: list[list[tuple[float, float, float]]], max_size: int = 2048):
        """Lays triangles out flat (true 3D shape, uniform texel density) and
        shelf-packs them into a square canvas. Returns (size, [3x2 pixel coords])."""
        import numpy as np

        flat = []
        for p in tris:
            a, b, c = (np.array(v, dtype=np.float64) for v in p)
            e1, e2 = b - a, c - a
            l1 = np.linalg.norm(e1)
            if l1 < 1e-12:
                flat.append(np.zeros((3, 2)))
                continue
            x2 = float(e2 @ e1) / l1
            y2 = float(np.linalg.norm(np.cross(e1, e2))) / l1
            pts = np.array([[0.0, 0.0], [l1, 0.0], [x2, y2]])
            pts[:, 0] -= pts[:, 0].min()
            flat.append(pts)
        total = sum(max(f[:, 0].max(), 1e-9) * max(f[:, 1].max(), 1e-9) for f in flat) or 1.0
        size = max_size if len(tris) > 64 else 1024
        pad = 5.0
        scale = np.sqrt(0.45 * size * size / total)
        while True:
            placed, x, y, row = [], pad, pad, 0.0
            order = sorted(range(len(flat)), key=lambda k: -flat[k][:, 1].max())
            ok = True
            result = [None] * len(flat)
            for k in order:
                f = flat[k] * scale
                w, h = max(f[:, 0].max(), 1.0), max(f[:, 1].max(), 1.0)
                if x + w + pad > size:
                    x, y, row = pad, y + row + pad, 0.0
                if y + h + pad > size:
                    ok = False
                    break
                result[k] = f + np.array([x, y])
                x += w + pad
                row = max(row, h)
            if ok:
                return size, result
            scale *= 0.9

    def _exact_draw_textures(self, meshes: list[MeshGeometry]) -> list[str | None]:
        """Returns the SPICA-verified diffuse texture for each draw (None = unknown)."""
        key = self._source_key()
        entries = load_material_map().get(key) if key else None
        aligned = self._align_draws(entries or [], meshes)
        return [pick_diffuse(e.get("tex0", ""), e.get("tex1", "")) if e else None for e in aligned]

    def get_string(self, offset: int) -> str:
        if offset >= self.str_len:
            return ""
        abs_off = self.str_off + offset
        end = self.data.find(b"\0", abs_off)
        if end == -1:
            end = self.str_off + self.str_len
        return self.data[abs_off:end].decode("ascii", "replace")

    def extract_textures(self) -> list[tuple[str, Image.Image]]:
        """Extracts embedded NW4C BCH textures from Dict 3 into standard PIL Images."""
        if len(self.data) < 0x44 or self.data[:4] != b"BCH\0":
            return []
        tree, count, vals = struct.unpack_from("<3I", self.data, self.hdr_off + 3 * 12)
        if count == 0 or tree == 0 or count > 100:
            return []

        ptrs = struct.unpack_from(f"<{count}I", self.data, self.hdr_off + tree)
        textures = []
        for ptr in ptrs:
            if self.hdr_off + ptr + 32 > len(self.data):
                continue
            t_words = struct.unpack_from("<8I", self.data, self.hdr_off + ptr)
            name_off = t_words[7]
            name = self.get_string(name_off) or f"texture_{len(textures)}"
            cmd_rel = t_words[0]
            if self.cmd_off + cmd_rel + 32 > len(self.data):
                continue

            dim_word = struct.unpack_from("<I", self.data, self.cmd_off + cmd_rel)[0]
            # GPUREG_TEXUNIT0_DIM stores height in the low half and width in the high half.
            width = (dim_word >> 16) & 0xFFFF
            height = dim_word & 0xFFFF
            if width == 0 or height == 0 or width > 2048 or height > 2048:
                continue

            # relocated command words hold absolute file offsets (RawData or RawExt)
            cmd_blk = struct.unpack_from("<8I", self._relocated(), self.cmd_off + cmd_rel)
            # H3DTexture header: 3x (cmd offset, cmd count), then the format byte at +0x18
            fmt_code = t_words[6] & 0xFF
            addr_off = 0
            for i, cw in enumerate(cmd_blk):
                reg = cw & 0xFFFF
                if reg in (0x0085, 0x0095, 0x009D) and i > 0:
                    addr_off = cmd_blk[i - 1]
            fmt_name = PICA_FORMATS.get(fmt_code)
            if fmt_name is None:
                continue

            tex_start = addr_off & 0x7FFFFFFF
            tex_data = self.data[tex_start: tex_start + tiled_size(width, height, fmt_name)]
            if not tex_data:
                continue

            try:
                rgba = decode_tiled(tex_data, width, height, fmt_name)
                textures.append((name, Image.fromarray(rgba, "RGBA")))
            except Exception:
                pass

        return textures

    def parse_models(self, default_name: str = "", dedupe: bool = True) -> list[BchModel]:
        # Main header at hdr_off contains 15 dictionary pointers (tree_off, count, values_off)
        # Dict 0: Models, Dict 1: Materials
        m_tree, m_count, m_vals = struct.unpack_from("<3I", self.data, self.hdr_off)
        mat_tree, mat_count, mat_vals = struct.unpack_from("<3I", self.data, self.hdr_off + 12)

        mat_names = []
        if mat_count > 0 and mat_tree != 0:
            for i in range(mat_count):
                mat_names.append(f"Material_{i}")

        model_name = default_name or "model"
        # Try finding clean model name from string table
        if self.str_len > 0:
            str_data = self.data[self.str_off:self.str_off + self.str_len]
            strings = [s.decode("ascii", "replace") for s in str_data.split(b"\0") if s]
            candidates = [s for s in strings if not s.startswith("$") and not s.startswith("0@") and not s.startswith("1@") and not s.startswith("j_") and not s.startswith("n_")]
            if candidates and not default_name:
                model_name = candidates[0]

        # Extract all distinct meshes from GPU command buffer
        meshes = self._parse_meshes(model_name)
        if not meshes:
            # Fallback for synthetic/header-only files: create single minimal mesh if VBO exists
            return []

        textures = self.extract_textures()
        if textures:
            tex_names = [name for name, _ in textures]
            per_material = self._material_texture_names(tex_names)
            mesh_materials = self._mesh_material_indices()
            exact = self._exact_draw_textures(meshes)
            used = set()
            for i, mesh in enumerate(meshes):
                tex = ""
                exact_available = exact[i] is not None
                if exact_available:
                    tex = exact[i]
                elif i < len(mesh_materials):
                    mi = mesh_materials[i]
                    if 0 <= mi < len(per_material):
                        tex = per_material[mi]
                if tex:
                    used.add(tex)
                # no verified or structural match: leave the mesh untextured rather
                # than guessing a texture from the list
                mesh.texture_name = f"{tex}.png" if tex else ""
                if tex:
                    mesh.material_name = f"Material_{i}"
            mat_names = sorted(used) or [n for n in per_material if n] or mat_names
            textures = textures + self._bake_layered_faces(meshes, dict(textures))

        self._apply_bone_placement(meshes)
        self._apply_blend_state(meshes)
        for i, mesh in enumerate(meshes):
            if mesh.hidden and mesh.material_name == "default_mat":
                mesh.material_name = f"Hidden_{i}"

        # The same static geometry is often emitted several times for layered
        # effects (torch/fire/light decals) or two-pass alpha. In a static OBJ/glTF
        # export those become visually duplicate objects at the same coordinates.
        # Collapse exact geometry+index duplicates and keep the first material.
        if dedupe:
            unique = []
            seen = set()
            for mesh in meshes:
                key = (
                    tuple(round(c, 4) for p in mesh.positions for c in p),
                    tuple(mesh.indices),
                )
                if key in seen:
                    continue
                seen.add(key)
                unique.append(mesh)
            self.duplicates_removed = len(meshes) - len(unique)
            meshes = unique
        else:
            self.duplicates_removed = 0

        model = BchModel(
            name=model_name,
            transform=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
            meshes=meshes,
            materials=mat_names or ["default_mat"],
            textures=textures
        )
        return [model]

    # PICA blend function (colour src, dst) -> exported blend mode
    BLEND_MODES = {
        "SourceAlpha,OneMinusSourceAlpha": "alpha",
        "SourceAlpha,One": "additive",
        "One,One": "additive",
        "DestinationColor,Zero": "multiply",
        "DestinationColor,One": "additive",
    }

    # numbered pose variants of one part, e.g. L_Hand03_MS, m104_Hand_R_02_MS_Outline
    _VARIANT = re.compile(r"hand_?[lr]?_?(\d{2})", re.IGNORECASE)

    @classmethod
    def _is_alternate_variant(cls, node: str) -> bool:
        """Characters ship several hand poses (Hand01..05) and the game shows one; the
        motion files that animate them start with 01 visible and the rest hidden."""
        m = cls._VARIANT.search(node)
        return bool(m) and int(m.group(1)) > 1

    # arguments each combiner reads (the rest of the three sources are ignored)
    TEV_ARGS = {"Replace": 1, "Modulate": 2, "Add": 2, "AddSigned": 2, "Subtract": 2,
                "Interpolate": 3, "MultAdd": 3, "AddMult": 3, "DotProduct3Rgb": 2, "DotProduct3Rgba": 2}

    @classmethod
    def _tev_inputs(cls, stages: list[str]) -> list[tuple[str, str]]:
        """(source, operand) pairs the first two stages actually read, stage 0 only
        when stage 1 uses Previous. Stage strings look like "Modulate(Texture0:Red,...)"."""
        parsed = []
        for stage in stages[:2]:
            op, _, rest = stage.partition("(")
            args = [tuple((a.split(":") + [""])[:2]) for a in rest.rstrip(")").split(",")]
            parsed.append(args[:cls.TEV_ARGS.get(op, 2)])
        if len(parsed) == 2 and not any(src == "Previous" for src, _ in parsed[1]):
            parsed = parsed[1:]
        return [arg for stage in parsed for arg in stage]

    @staticmethod
    def _unit_uv_set(entry: dict, unit: int) -> int:
        """UV set a texture unit reads: Config0120 -> unit i uses UV digit i."""
        digits = entry.get("texcoord_config", "Config0120")[len("Config"):]
        return int(digits[unit]) if unit < len(digits) and digits[unit].isdigit() else unit

    @classmethod
    def _draw_layers(cls, entry: dict) -> tuple[int | None, tuple[int, str] | None]:
        """(colour unit, (mask unit, channel)) from the material's combiners.

        The colour unit is the first texture the colour path samples through its UVs
        (environment/projection maps are skipped). The mask is a texture channel the
        alpha path reads that the colour texture's own alpha does not cover, e.g.
        `Modulate(PrimaryColor:Alpha,Texture0:Red)` on a grass decal whose unit 0 is a
        black/white `*_nuki*` mask.
        """
        coords = entry.get("uv_coords") or []

        def uv_mapped(u: int) -> bool:
            if not entry.get(f"tex{u}"):
                return False
            return u >= len(coords) or coords[u].get("mapping", "UvCoordinateMap") == "UvCoordinateMap"

        colour = None
        sampled = [int(src[-1]) for src, _ in cls._tev_inputs(entry.get("tev_color_ops") or entry.get("tev") or [])
                   if src.startswith("Texture") and uv_mapped(int(src[-1]))]
        # a reflection texture can be UV-mapped too; prefer a plain one when both are sampled
        plain = [u for u in sampled if not any(k in entry[f"tex{u}"].lower() for k in ("env", "cubemap"))]
        if plain or sampled:
            colour = (plain or sampled)[0]
        mask = None
        for src, operand in cls._tev_inputs(entry.get("tev_alpha_ops") or []):
            if not src.startswith("Texture") or not uv_mapped(int(src[-1])):
                continue
            unit = int(src[-1])
            if unit == colour and operand == "Alpha":
                continue  # the colour texture's own alpha, already in its PNG
            channel = {"Alpha": "alpha", "OneMinusAlpha": "one_minus_alpha", "Red": "red",
                       "OneMinusRed": "one_minus_red", "Green": "green", "OneMinusGreen": "one_minus_green",
                       "Blue": "blue", "OneMinusBlue": "one_minus_blue"}.get(operand)
            if channel:
                mask = (unit, channel)
                break
        return colour, mask

    def _apply_blend_state(self, meshes: list[MeshGeometry]) -> None:
        """Applies each draw's material state from the material map: which texture
        the colour path samples (and through which UV set and texture transform),
        an alpha mask from another texture channel, blend function, alpha test and
        default visibility."""
        key = self._source_key()
        entries = self._align_draws(load_material_map().get(key, []) if key else [], meshes)
        for index, (mesh, entry) in enumerate(zip(meshes, entries)):
            if not entry:
                continue
            coords = entry.get("uv_coords") or []
            uv_sets = (mesh.uvs, mesh.uvs1, mesh.uvs2)

            def unit_uvs(unit: int):
                uvs = uv_sets[self._unit_uv_set(entry, unit)]
                if len(uvs) != len(mesh.positions) and not mesh.uvs1 and not mesh.uvs2:
                    # only one UV attribute stored (the other units use generated
                    # environment coordinates): every UV-mapped unit reads it
                    uvs = mesh.uvs
                if len(uvs) != len(mesh.positions):
                    return None
                m = self._uv_matrix(coords[unit]) if unit < len(coords) else None
                return [self._transform_uv(m, u, v) for u, v in uvs] if m is not None else list(uvs)

            if not mesh.texture_name.endswith("_composite.png"):
                colour, mask = self._draw_layers(entry)
                if colour is not None and unit_uvs(colour) is not None:
                    mesh.texture_name = f"{entry[f'tex{colour}']}.png"
                    mesh.uvs = unit_uvs(colour)
                    if mesh.material_name == "default_mat":
                        mesh.material_name = f"Material_{index}"
                if mask is not None and unit_uvs(mask[0]) is not None and mesh.texture_name:
                    mesh.mask_texture = f"{entry[f'tex{mask[0]}']}.png"
                    mesh.mask_channel = mask[1]
                    mesh.mask_uvs = unit_uvs(mask[0])
            mesh.blend = self.BLEND_MODES.get(entry.get("blend", ""), "opaque")
            colour_ops = entry.get("tev_color_ops") or []
            scales = [{"One": 1.0, "Two": 2.0, "Four": 4.0}.get(x, 1.0) for x in entry.get("tev_scale") or []] + [1.0, 1.0]
            stage0_reads = len(colour_ops) > 0 and ("PrimaryColor", "Color") in self._tev_inputs(colour_ops[:1])
            reads_vertex_rgb = ("PrimaryColor", "Color") in self._tev_inputs(colour_ops)
            if (reads_vertex_rgb and len(mesh.colors) == len(mesh.positions)
                    and not mesh.texture_name.endswith("_composite.png")):
                # the GPU clamps every stage to 0..1: stage 0 = min(rgb * s0, 1), stage 1 scales by s1
                pre = scales[0] if stage0_reads else 1.0
                mesh.vertex_rgb = [tuple(min(max(c[k] * pre, 0.0), 1.0) for k in range(3)) for c in mesh.colors]
                mesh.color_scale = scales[1] if len(colour_ops) > 1 else 1.0
            reads_vertex_alpha = ("PrimaryColor", "Alpha") in self._tev_inputs(entry.get("tev_alpha_ops") or [])
            if (reads_vertex_alpha and mesh.blend != "opaque" and len(mesh.colors) == len(mesh.positions)
                    and any(c[3] < 0.999 for c in mesh.colors)):
                mesh.vertex_alpha = [max(0.0, min(1.0, c[3])) for c in mesh.colors]
            mesh.node_name = entry.get("node", "")
            mesh.hidden = not entry.get("visible", True) or self._is_alternate_variant(mesh.node_name)
            test = entry.get("alpha_test", "")
            func, _, ref = test.partition(",")
            if func in ("Greater", "GreaterOrEqual") and ref.isdigit():
                mesh.alpha_cutoff = int(ref) / 255.0

    def _apply_bone_placement(self, meshes: list[MeshGeometry]) -> None:
        """Moves rigid/unskinned draws from bone space into model space.

        Same rule as SPICA's MeshTransform: a vertex is transformed by the world
        matrix of palette[BoneIndex] (the per-vertex attribute, or the mesh's
        fixed BoneIndex). Smooth-skinned draws are already in model space.
        """
        key = self._source_key()
        entries = load_skin_map().get(key) if key else None
        if not entries:
            return
        for mesh, entry in zip(meshes, self._align_draws(entries, meshes)):
            if not entry or entry.get("indices") != len(mesh.indices):
                continue
            palette = entry.get("palette")
            if not palette:
                continue
            fixed = int(entry.get("fixed_bone", 0))
            positions, normals, placement = [], [], []
            for v, (x, y, z) in enumerate(mesh.positions):
                b = mesh.bone_indices[v] if v < len(mesh.bone_indices) else fixed
                m = palette[b] if 0 <= b < len(palette) else palette[0]
                placement.append(m)
                # System.Numerics row-vector layout: p' = p * M
                positions.append((
                    x * m[0] + y * m[3] + z * m[6] + m[9],
                    x * m[1] + y * m[4] + z * m[7] + m[10],
                    x * m[2] + y * m[5] + z * m[8] + m[11],
                ))
                if v < len(mesh.normals):
                    nx, ny, nz = mesh.normals[v]
                    n = (
                        nx * m[0] + ny * m[3] + nz * m[6],
                        nx * m[1] + ny * m[4] + nz * m[7],
                        nx * m[2] + ny * m[5] + nz * m[8],
                    )
                    length = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0
                    normals.append((n[0] / length, n[1] / length, n[2] / length))
            mesh.positions = positions
            mesh.placement = placement
            if normals:
                mesh.normals = normals

    @staticmethod
    def _pica_commands(cmd_words: tuple[int, ...]) -> list[tuple[int, list[int]]]:
        """Splits a PICA command buffer into (register, parameters).

        PICA streams a parameter word before each command word. Consecutive commands
        (bit 31) consume one parameter per register; non-consecutive commands store
        their remaining parameters after the command.
        """
        out: list[tuple[int, list[int]]] = []
        index = 0
        n = len(cmd_words)
        while index + 1 < n:
            parameter = cmd_words[index]
            command = cmd_words[index + 1]
            index += 2
            reg = command & 0xFFFF
            extra = (command >> 20) & 0x7FF
            consecutive = (command >> 31) != 0
            if consecutive:
                for k in range(extra + 1):
                    out.append((reg + k, [parameter]))
                    if k < extra and index < n:
                        parameter = cmd_words[index]
                        index += 1
            else:
                params = [parameter]
                for _ in range(extra):
                    if index >= n:
                        break
                    params.append(cmd_words[index])
                    index += 1
                out.append((reg, params))
            if index & 1:
                index += 1
        return out

    @staticmethod
    def _vertex_attributes(vbo: dict) -> list[dict]:
        """Decodes the PICA attribute permutation into ordered vertex fields."""
        formats = vbo["fmt_low"] | (vbo["fmt_high"] << 32)
        attrs = vbo["cfg1"] | ((vbo["cfg2"] & 0xFFFF) << 32)
        perm = vbo["perm_low"] | (vbo["perm_high"] << 32)
        count = vbo.get("attr_cnt") or vbo.get("num_attr") or 4
        count = min(max(count, 1), 16)
        uniforms = vbo.get("uniforms", {})
        out = []
        for slot in range(count):
            pidx = (attrs >> (slot * 4)) & 0xF
            name = (perm >> (pidx * 4)) & 0xF
            fmt = (formats >> (pidx * 4)) & 0xF
            ftype = fmt & 3
            elements = (fmt >> 2) + 1
            # PICA vertex shader uniform 7/8 carry per-semantic fixed-point scale.
            scale = 1.0
            if name == 0:
                scale = uniforms.get(7, [1.0])[0]
            elif name in (1, 2):
                scale = uniforms.get(7, [1.0, 1.0, 1.0])[name - 1]
            elif name == 3:
                scale = uniforms.get(7, [1.0, 1.0, 1.0, 1.0])[3]
            elif name in (4, 5, 6):
                scale = uniforms.get(8, [1.0, 1.0, 1.0])[name - 4]
            elif name == 8:
                scale = uniforms.get(8, [1.0, 1.0, 1.0, 1.0])[3]
            if not scale or not (abs(scale) > 1e-30):
                scale = 1.0
            out.append({
                "name": name,
                "format": ftype,
                "elements": elements,
                "scale": scale,
            })
        return out

    def _parse_meshes(self, model_name: str) -> list[MeshGeometry]:
        meshes = []
        if self.cmd_len == 0:
            return meshes

        # relocated words: buffer addresses are absolute file offsets into RawData
        # or RawExt, and the index buffer address carries bit 31 for 16-bit indices
        cmd_words = struct.unpack_from(f"<{self.cmd_len // 4}I", self._relocated(), self.cmd_off)
        current_vbo = None
        draw_calls = []
        uniforms = [[1.0, 1.0, 1.0, 1.0] for _ in range(96)]
        uniform_index = 0
        uniform_32 = False
        vsh_perm_low = 0
        vsh_perm_high = 0
        vsh_num_attr = 0
        ibo_addr = 0
        num_indices = 0

        for reg, params in self._pica_commands(cmd_words):
            if not params:
                continue
            param = params[0]
            if reg == 0x0201:
                current_vbo = dict(current_vbo or {})
                current_vbo["fmt_low"] = param
            elif reg == 0x0202:
                current_vbo = dict(current_vbo or {})
                current_vbo["fmt_high"] = param
            elif reg == 0x0203:
                current_vbo = dict(current_vbo or {})
                current_vbo["offset"] = param
            elif reg == 0x0204:
                current_vbo = dict(current_vbo or {})
                current_vbo["cfg1"] = param
            elif reg == 0x0205:
                current_vbo = dict(current_vbo or {})
                current_vbo["cfg2"] = param
                current_vbo["stride"] = (param >> 16) & 0xFF
                current_vbo["attr_cnt"] = (param >> 28) & 0xF
                if current_vbo["stride"] <= 0:
                    current_vbo["stride"] = 24
                current_vbo["perm_low"] = vsh_perm_low
                current_vbo["perm_high"] = vsh_perm_high
                current_vbo["num_attr"] = vsh_num_attr
                current_vbo["uniforms"] = {i: list(v) for i, v in enumerate(uniforms)}
            elif reg == 0x0242:
                vsh_num_attr = param + 1
            elif reg == 0x02BB:
                vsh_perm_low = param
            elif reg == 0x02BC:
                vsh_perm_high = param
            elif reg == 0x02C0:
                uniform_index = (param & 0xFF) << 2
                uniform_32 = (param >> 31) != 0
            elif 0x02C1 <= reg <= 0x02C8:
                for value in params:
                    uidx = (uniform_index >> 2) & 0x5F
                    if uniform_32:
                        f = struct.unpack("<f", struct.pack("<I", value & 0xFFFFFFFF))[0]
                        component = uniform_index & 3
                        # PICA writes W,Z,Y,X for successive words.
                        idx = {0: 3, 1: 2, 2: 1, 3: 0}[component]
                        uniforms[uidx][idx] = f
                    uniform_index += 1
            elif reg == 0x0227:
                ibo_addr = param
            elif reg == 0x0228:
                num_indices = param
            elif reg == 0x022F and current_vbo and 0 < num_indices < 100000:
                snapshot = dict(current_vbo)
                snapshot["uniforms"] = {i: list(v) for i, v in enumerate(uniforms)}
                draw_calls.append({
                    "vbo": snapshot,
                    "ibo_offset": ibo_addr & 0x7FFFFFFF,
                    "ibo_u16": bool(ibo_addr >> 31),
                    "num_indices": num_indices,
                })

        # Fallback if no draw calls discovered via command scan
        if not draw_calls and current_vbo:
            draw_calls.append({
                "vbo": dict(current_vbo),
                "ibo_offset": 0,
                "num_indices": 3,
            })


        for idx, call in enumerate(draw_calls):
            vbo = call["vbo"]
            stride = vbo["stride"]
            vbo_off = vbo["offset"]
            vbo_abs = vbo_off & 0x7FFFFFFF
            ibo_abs = call["ibo_offset"]
            num_indices = call["num_indices"]


            is_u8 = not call.get("ibo_u16", False)
            if is_u8:
                u8_indices = list(self.data[ibo_abs:ibo_abs + num_indices])
                u16_indices = []
            else:
                u16_indices = list(struct.unpack_from(f"<{num_indices}H", self.data, ibo_abs)) if ibo_abs + num_indices * 2 <= len(self.data) else []
                u8_indices = []
            indices = u8_indices if is_u8 else u16_indices
            if not indices:
                continue

            max_vtx = max(indices)
            geom = MeshGeometry(f"{model_name}_mesh{idx}")
            geom.indices = indices
            geom.vbo_abs = vbo_abs
            geom.stride = stride
            geom.vertex_count = max_vtx + 1
            geom.ibo_abs = ibo_abs
            geom.index_size = 1 if is_u8 else 2
            geom.num_indices = num_indices

            attributes = self._vertex_attributes(vbo)
            for v_idx in range(max_vtx + 1):
                pos = vbo_abs + v_idx * stride
                if pos + stride > len(self.data):
                    break
                values: dict[int, tuple[float, ...]] = {}
                off = 0
                for attr in attributes:
                    ftype = attr["format"]
                    if ftype not in (0, 1):
                        off += off & 1
                    elems = attr["elements"]
                    vals: list[float] = []
                    if ftype == 3:
                        for e in range(elems):
                            if pos + off + 4 > len(self.data):
                                break
                            vals.append(struct.unpack_from("<f", self.data, pos + off)[0])
                            off += 4
                    elif ftype == 2:
                        for e in range(elems):
                            if pos + off + 2 > len(self.data):
                                break
                            vals.append(struct.unpack_from("<h", self.data, pos + off)[0] * attr["scale"])
                            off += 2
                    elif ftype == 1:
                        for _e in range(elems):
                            if pos + off >= len(self.data):
                                break
                            vals.append(self.data[pos + off] * attr["scale"])
                            off += 1
                    else:
                        for _e in range(elems):
                            if pos + off >= len(self.data):
                                break
                            vals.append(struct.unpack_from("<b", self.data, pos + off)[0] * attr["scale"])
                            off += 1
                    values[attr["name"]] = tuple(vals)

                p = values.get(0, (0.0, 0.0, 0.0))
                geom.positions.append((p[0], p[1], p[2] if len(p) > 2 else 0.0))
                n = values.get(1, (0.0, 1.0, 0.0))
                geom.normals.append((n[0], n[1], n[2] if len(n) > 2 else 0.0))
                uv = values.get(4, (0.0, 0.0))
                geom.uvs.append((uv[0], uv[1] if len(uv) > 1 else 0.0))
                for name, target in ((5, geom.uvs1), (6, geom.uvs2)):
                    extra = values.get(name)
                    if extra:
                        target.append((extra[0], extra[1] if len(extra) > 1 else 0.0))
                colour = values.get(3)
                if colour:
                    geom.colors.append(tuple((list(colour) + [1.0, 1.0, 1.0, 1.0])[:4]))
                bone = values.get(7)
                if bone:
                    geom.bone_indices.append(int(round(bone[0])))

            if geom.positions and geom.indices:
                meshes.append(geom)

        return meshes


def parse_bch(data: bytes, default_name: str = "") -> BchParser:
    """Convenience helper to instantiate NW4C BCH parser and parse models."""
    p = BchParser(data)
    p.models = p.parse_models(default_name)
    return p


def export_obj(target: MeshGeometry | BchModel, texture_name: str = "") -> tuple[str, str]:
    """In-memory exporter of MeshGeometry or BchModel to (obj_text, mtl_text)."""
    if isinstance(target, MeshGeometry):
        model = BchModel(name=target.name, transform=[], meshes=[target])
    else:
        model = target

    obj_lines = [
        "# Dragon Quest XI 3DS - Wavefront OBJ Export",
        f"# Model: {model.name}",
        f"mtllib {model.name}.mtl",
        "",
    ]
    mtl_lines = [
        f"# Material library for {model.name}",
        "",
    ]
    v_base = 1
    vt_base = 1
    for m in model.meshes:
        obj_lines.append(f"o {m.name}")
        obj_lines.append(f"usemtl {m.material_name}")
        for x, y, z in m.positions:
            obj_lines.append(f"v {x!r} {y!r} {z!r}")
        for nx, ny, nz in m.normals:
            obj_lines.append(f"vn {nx:.4f} {ny:.4f} {nz:.4f}")
        # baked faces carry one UV per triangle corner; vertices (and so model_patch's
        # vertex order) stay exactly as in the BCH
        texcoords = m.corner_uvs if m.corner_uvs else m.uvs
        for u, v in texcoords:
            obj_lines.append(f"vt {u:.5f} {v:.5f}")
        # mask texture coordinates, one per vertex (other OBJ readers skip the keyword)
        for u, v in m.mask_uvs:
            obj_lines.append(f"dqxi_vt_mask {u:.5f} {v:.5f}")
        # per-vertex alpha, one per vertex (other OBJ readers skip the keyword)
        for a in m.vertex_alpha:
            obj_lines.append(f"dqxi_va {a:.4f}")
        # baked vertex lighting, one per vertex
        for r, g, b in m.vertex_rgb:
            obj_lines.append(f"dqxi_vc {r:.4f} {g:.4f} {b:.4f}")
        for i in range(0, len(m.indices) - 2, 3):
            corners = []
            for k in range(3):
                vi = m.indices[i + k] + v_base
                ti = (i + k if m.corner_uvs else m.indices[i + k]) + vt_base
                corners.append(f"{vi}/{ti}/{vi}")
            obj_lines.append("f " + " ".join(corners))
        v_base += len(m.positions)
        vt_base += len(texcoords)
        obj_lines.append("")

        tex = texture_name or getattr(m, "texture_name", "")
        mtl_lines.append(f"newmtl {m.material_name}")
        mtl_lines.append("  Ka 0.200 0.200 0.200")
        mtl_lines.append("  Kd 0.800 0.800 0.800")
        mtl_lines.append("  Ks 0.100 0.100 0.100")
        mtl_lines.append("  d 1.0")
        mtl_lines.append("  illum 2")
        if tex:
            mtl_lines.append(f"  map_Kd {tex}")
            if (m.blend == "alpha" or m.alpha_cutoff) and not m.mask_texture:
                mtl_lines.append(f"  map_d -imfchan m {tex}")
        # game render state; other OBJ readers ignore unknown keywords
        if m.hidden:
            mtl_lines.append("  dqxi_hidden 1")
        if m.vertex_rgb and m.color_scale != 1.0:
            mtl_lines.append(f"  dqxi_color_scale {m.color_scale:g}")
        if m.mask_texture:
            mtl_lines.append(f"  dqxi_mask_map {m.mask_texture}")
            mtl_lines.append(f"  dqxi_mask_channel {m.mask_channel}")
        if m.blend != "opaque":
            mtl_lines.append(f"  dqxi_blend {m.blend}")
        if m.alpha_cutoff:
            mtl_lines.append(f"  dqxi_alpha_cutoff {m.alpha_cutoff:.3f}")
        mtl_lines.append("")

    return "\n".join(obj_lines), "\n".join(mtl_lines)


def _unwelded(m: MeshGeometry) -> MeshGeometry:
    """Copy with one vertex per triangle corner (glTF has a single index per vertex)."""
    import dataclasses

    order = list(m.indices)
    return dataclasses.replace(
        m,
        positions=[m.positions[i] for i in order],
        normals=[m.normals[i] for i in order] if len(m.normals) == len(m.positions) else [],
        uvs=list(m.corner_uvs),
        mask_uvs=[m.mask_uvs[i] for i in order] if len(m.mask_uvs) == len(m.positions) else [],
        vertex_alpha=[m.vertex_alpha[i] for i in order] if len(m.vertex_alpha) == len(m.positions) else [],
        vertex_rgb=[m.vertex_rgb[i] for i in order] if len(m.vertex_rgb) == len(m.positions) else [],
        indices=list(range(len(order))),
        corner_uvs=None,
    )


def export_gltf(target: MeshGeometry | BchModel, texture_name: str = "") -> tuple[dict, bytes]:
    """In-memory exporter of MeshGeometry or BchModel to (gltf_dict, bin_bytes)."""
    if isinstance(target, MeshGeometry):
        model = BchModel(name=target.name, transform=[], meshes=[target])
    else:
        model = target

    valid_meshes = [_unwelded(m) if m.corner_uvs else m for m in model.meshes if m.positions and m.indices]
    bin_data = bytearray()
    accessors = []
    buffer_views = []
    meshes_json = []

    tex = texture_name or (model.meshes[0].texture_name if model.meshes else "")
    texture_files = [f"{name}.png" for name, _ in model.textures]
    if not texture_files and tex:
        texture_files = [tex]
    image_index = {name: i for i, name in enumerate(texture_files)}
    # one glTF material per (image, blend, alpha test)
    material_index: dict[tuple, int] = {}
    has_mat = bool(texture_files)

    for m in valid_meshes:
        idx_bytes = struct.pack(f"<{len(m.indices)}H", *m.indices)
        idx_offset = len(bin_data)
        bin_data.extend(idx_bytes)
        while len(bin_data) % 4 != 0:
            bin_data.append(0)

        idx_bv = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": idx_offset,
            "byteLength": len(idx_bytes),
            "target": 34963,
        })
        idx_acc = len(accessors)
        accessors.append({
            "bufferView": idx_bv,
            "byteOffset": 0,
            "componentType": 5123,
            "count": len(m.indices),
            "type": "SCALAR",
            "max": [int(max(m.indices))],
            "min": [int(min(m.indices))],
        })

        pos_floats = [f for p in m.positions for f in p]
        pos_bytes = struct.pack(f"<{len(pos_floats)}f", *pos_floats)
        pos_offset = len(bin_data)
        bin_data.extend(pos_bytes)
        while len(bin_data) % 4 != 0:
            bin_data.append(0)

        pos_bv = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": pos_offset,
            "byteLength": len(pos_bytes),
            "target": 34962,
        })
        pos_acc = len(accessors)
        accessors.append({
            "bufferView": pos_bv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(m.positions),
            "type": "VEC3",
            "max": [float(max(p[0] for p in m.positions)), float(max(p[1] for p in m.positions)), float(max(p[2] for p in m.positions))],
            "min": [float(min(p[0] for p in m.positions)), float(min(p[1] for p in m.positions)), float(min(p[2] for p in m.positions))],
        })

        norm_floats = [f for n in m.normals for f in n]
        norm_bytes = struct.pack(f"<{len(norm_floats)}f", *norm_floats)
        norm_offset = len(bin_data)
        bin_data.extend(norm_bytes)
        while len(bin_data) % 4 != 0:
            bin_data.append(0)

        norm_bv = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": norm_offset,
            "byteLength": len(norm_bytes),
            "target": 34962,
        })
        norm_acc = len(accessors)
        accessors.append({
            "bufferView": norm_bv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(m.normals),
            "type": "VEC3",
        })

        # BCH/OBJ UVs have their origin at the bottom-left; glTF's is top-left
        uv_floats = [f for u, v in m.uvs for f in (u, 1.0 - v)]
        uv_bytes = struct.pack(f"<{len(uv_floats)}f", *uv_floats)
        uv_offset = len(bin_data)
        bin_data.extend(uv_bytes)
        while len(bin_data) % 4 != 0:
            bin_data.append(0)

        uv_bv = len(buffer_views)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": uv_offset,
            "byteLength": len(uv_bytes),
            "target": 34962,
        })
        uv_acc = len(accessors)
        accessors.append({
            "bufferView": uv_bv,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(m.uvs),
            "type": "VEC2",
        })

        prim = {
            "attributes": {
                "POSITION": pos_acc,
                "NORMAL": norm_acc,
                "TEXCOORD_0": uv_acc,
            },
            "indices": idx_acc,
            "mode": 4,
        }
        mask_image = image_index.get(Path(m.mask_texture).name) if m.mask_texture and len(m.mask_uvs) == len(m.positions) else None
        if mask_image is not None:
            mask_floats = [f for u, v in m.mask_uvs for f in (u, 1.0 - v)]
            mask_bytes = struct.pack(f"<{len(mask_floats)}f", *mask_floats)
            mask_offset = len(bin_data)
            bin_data.extend(mask_bytes)
            buffer_views.append({"buffer": 0, "byteOffset": mask_offset, "byteLength": len(mask_bytes), "target": 34962})
            accessors.append({"bufferView": len(buffer_views) - 1, "byteOffset": 0, "componentType": 5126,
                              "count": len(m.mask_uvs), "type": "VEC2"})
            prim["attributes"]["TEXCOORD_1"] = len(accessors) - 1
        if len(m.vertex_alpha) == len(m.positions) or len(m.vertex_rgb) == len(m.positions):
            # glTF multiplies COLOR_0 into base colour and alpha (no >1 brightening: clamp)
            rgb = [tuple(min(c * m.color_scale, 1.0) for c in v) for v in m.vertex_rgb] or [(1.0, 1.0, 1.0)] * len(m.positions)
            alpha = m.vertex_alpha or [1.0] * len(m.positions)
            colour_floats = [f for (r, g, b), a in zip(rgb, alpha) for f in (r, g, b, a)]
            colour_bytes = struct.pack(f"<{len(colour_floats)}f", *colour_floats)
            colour_offset = len(bin_data)
            bin_data.extend(colour_bytes)
            buffer_views.append({"buffer": 0, "byteOffset": colour_offset, "byteLength": len(colour_bytes), "target": 34962})
            accessors.append({"bufferView": len(buffer_views) - 1, "byteOffset": 0, "componentType": 5126,
                              "count": len(m.positions), "type": "VEC4"})
            prim["attributes"]["COLOR_0"] = len(accessors) - 1
        if has_mat and m.texture_name:
            image = image_index.get(Path(m.texture_name).name)
            if image is not None:
                state = (image, m.blend, m.alpha_cutoff,
                         (mask_image, m.mask_channel) if mask_image is not None else None)
                if state not in material_index:
                    material_index[state] = len(material_index)
                prim["material"] = material_index[state]

        meshes_json.append({
            "name": m.name,
            "primitives": [prim],
        })

    gltf_dict = {
        "asset": {
            "version": "2.0",
            "generator": "Dragon Quest XI 3DS NW4C Model Tool",
        },
        "scene": 0,
        "scenes": [{"nodes": list(range(len(meshes_json)))}],
        "nodes": [
            {"mesh": i, "name": m["name"], **({"extras": {"dqxi_hidden": True}} if hidden else {})}
            for i, (m, hidden) in enumerate(zip(meshes_json, [g.hidden for g in valid_meshes]))
        ],
        "meshes": meshes_json,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{
            "uri": f"{model.name}.bin",
            "byteLength": len(bin_data),
        }],
    }
    if has_mat:
        gltf_dict["images"] = [{"uri": name} for name in texture_files]
        gltf_dict["textures"] = [{"sampler": 0, "source": i} for i in range(len(texture_files))]
        gltf_dict["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
        materials = []
        for (image, blend, cutoff, mask), _ in sorted(material_index.items(), key=lambda kv: kv[1]):
            mat = {
                "name": f"Material_{len(materials)}",
                "doubleSided": True,
                "pbrMetallicRoughness": {
                    "baseColorTexture": {"index": image},
                    "metallicFactor": 0.0,
                    "roughnessFactor": 0.6,
                },
            }
            if cutoff:
                mat["alphaMode"] = "MASK"
                mat["alphaCutoff"] = round(cutoff, 3)
            elif blend != "opaque":
                # glTF has no additive/multiply mode: blend, and keep the game's mode
                mat["alphaMode"] = "BLEND"
            extras = {}
            if blend != "opaque":
                extras["dqxi_blend"] = blend
            if mask is not None:
                # alpha *= channel of this image read through TEXCOORD_1
                extras["dqxi_mask"] = {"index": mask[0], "texCoord": 1, "channel": mask[1]}
                mat.setdefault("alphaMode", "BLEND")
            if extras:
                mat["extras"] = extras
            materials.append(mat)
        gltf_dict["materials"] = materials

    return gltf_dict, bytes(bin_data)


def export_to_obj(model: BchModel, out_path: Path):
    """Exports BchModel to standard Wavefront OBJ (.obj) and material library (.mtl)."""
    valid_meshes = [m for m in model.meshes if m.positions and m.indices]
    if not valid_meshes:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if model.textures:
        for tname, timg in model.textures:
            t_path = out_path.parent / f"{tname}.png"
            timg.save(t_path)
    obj_text, mtl_text = export_obj(model)
    out_path.write_text(obj_text, encoding="utf-8")
    out_path.with_suffix(".mtl").write_text(mtl_text, encoding="utf-8")


def export_to_gltf(model: BchModel, out_path: Path):
    """Exports BchModel to standard glTF 2.0 (.gltf) with companion binary (.bin)."""
    valid_meshes = [m for m in model.meshes if m.positions and m.indices]
    if not valid_meshes:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if model.textures:
        # always rewrite: a skipped write would keep PNGs from older, wrong decodes
        for tname, timg in model.textures:
            timg.save(out_path.parent / f"{tname}.png")
    bin_path = out_path.with_suffix(".bin")
    gltf_dict, bin_data = export_gltf(model)
    gltf_dict["buffers"][0]["uri"] = bin_path.name

    bin_path.write_bytes(bin_data)
    out_path.write_text(json.dumps(gltf_dict, indent=2), encoding="utf-8")


# Category mapping table from prefix/pack to clean human-readable name & category
NAME_MAP: dict[str, tuple[str, str]] = {
    # Characters (Playable & Key Party)
    "cha01000a_h": ("Characters", "Hero_TheLuminary"),
    "cha01000a_l": ("Characters", "Hero_TheLuminary_LowPoly"),
    "cha01100a_h": ("Characters", "Erik_TheThief"),
    "cha01200a_h": ("Characters", "Veronica_TheMage"),
    "cha01300a_h": ("Characters", "Serena_TheHealer"),
    "cha01400a_h": ("Characters", "Sylvando_TheEntertainer"),
    "cha01500a_h": ("Characters", "Rab_Grandpa"),
    "cha01600a_h": ("Characters", "Jade_TheMartialArtist"),
    "cha01700a_h": ("Characters", "Hendrik_TheKnight"),
    # Key NPCs
    "cha00001a_h": ("Characters", "Gemma_ChildhoodFriend"),
    "cha00002a_h": ("Characters", "King_Carnelian"),
    "cha00003a_h": ("Characters", "Jasper_Tactician"),
    "cha00004a_h": ("Characters", "Amber_HeroMother"),
    "cha00005a_h": ("Characters", "Chalky_HeroGrandfather"),
    "cha00006a_h": ("Characters", "Sandy_LoyalDog"),
    "cha00010a_h": ("Characters", "Prince_Faris_Gallopolis"),
    # Weapons
    "w0001a": ("Weapons", "Cobblestone_Sword"),
    "w0002a": ("Weapons", "Cypress_Stick"),
    "w0003a": ("Weapons", "Copper_Sword"),
    "w0004a": ("Weapons", "Soldier_Sword"),
    "w0010a": ("Weapons", "Iron_Broadsword"),
    "w0015a": ("Weapons", "Steel_Broadsword"),
    "w0020a": ("Weapons", "Platinum_Sword"),
    "w0025a": ("Weapons", "Zombie_Slayer"),
    "w0030a": ("Weapons", "Dragonsbane"),
    "w0035a": ("Weapons", "Falcon_Blade"),
    "w0040a": ("Weapons", "Miracle_Sword"),
    "w0045a": ("Weapons", "Erdrick_Sword"),
    "w0050a": ("Weapons", "Sword_of_Light"),
    "w0055a": ("Weapons", "Supreme_Sword_of_Light"),
    "w0100a": ("Weapons", "Cobblestone_Greatsword"),
    "w0200a": ("Weapons", "Bronze_Knife"),
    "w0300a": ("Weapons", "Oak_Staff"),
    "w0400a": ("Weapons", "Wizard_Staff"),
    "w0500a": ("Weapons", "Leather_Whip"),
    "w0600a": ("Weapons", "Iron_Claws"),
    "w0700a": ("Weapons", "Boomerang"),
    "w0800a": ("Weapons", "Leather_Shield"),
    "w0850a": ("Weapons", "Erdrick_Shield"),
    # Interactive Props & Gimmicks
    "g3101": ("Interactive_Props", "Wooden_Treasure_Chest"),
    "g3102": ("Interactive_Props", "Red_Treasure_Chest"),
    "g3103": ("Interactive_Props", "Gold_Treasure_Chest"),
    "g3201": ("Interactive_Props", "Breakable_Clay_Pot"),
    "g3301": ("Interactive_Props", "Breakable_Wooden_Barrel"),
    "g3801": ("Interactive_Props", "Campfire_Rest_Point"),
    "g3802": ("Interactive_Props", "Goddess_Save_Statue"),
    # Environments & Towns
    "b001_101a": ("Environments", "Cobblestone_Village"),
    "b001_102a": ("Environments", "Cobblestone_Tor"),
    "b002_101a": ("Environments", "Heliodor_Castle_Town"),
    "b002_102a": ("Environments", "Heliodor_Royal_Palace"),
    "b002_103a": ("Environments", "Heliodor_Sewers_Dungeon"),
    "b002_104a": ("Environments", "Manglegrove_Wilderness"),
    "b002_105a": ("Environments", "Kingsbarrow_Ruins"),
    "b003_101a": ("Environments", "Hotto_Steamy_Town"),
    "b003_102a": ("Environments", "Mount_Huji_Volcano"),
    "b004_101a": ("Environments", "Gallopolis_Sultanate"),
    "b005_101a": ("Environments", "Gondolia_Sea_Port"),
    "b006_101a": ("Environments", "Octagonia_Town"),
    "b007_101a": ("Environments", "Puerto_Valor_Coast"),
    "b008_101a": ("Environments", "Phnom_Nonh"),
    "b009_101a": ("Environments", "Sniflheim_Kingdom"),
    "b010_101a": ("Environments", "Arboria_Holy_Sanctuary"),
    "b011_101a": ("Environments", "Fortress_of_Fear"),
    # Mounts & Rides
    "r001": ("Mounts_and_Rides", "Hero_Travel_Horse"),
    "r002": ("Mounts_and_Rides", "Dragon_Rider_Mount"),
    "r003": ("Mounts_and_Rides", "Skull_Rider_Mount"),
    "r004": ("Mounts_and_Rides", "Iron_Maiden_Mount"),
    "r005": ("Mounts_and_Rides", "Demonrider_Mount"),
}

MONSTER_NAMES_PATH = PROJECT_ROOT / "tools" / "monster_names.json"
MONSTER_NAMES: dict[str, list[str]] = {}
if MONSTER_NAMES_PATH.is_file():
    try:
        MONSTER_NAMES = json.loads(MONSTER_NAMES_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass


def resolve_model_info(stem: str, path: str) -> tuple[str, str]:
    """Resolves category and human-readable name for a model file."""
    if stem in NAME_MAP:
        return NAME_MAP[stem]

    if path.startswith("/3d/bg/"):
        return ("Environments", f"Map_{stem}")
    elif stem.startswith("cha"):
        return ("Characters", f"Character_{stem}")
    elif stem.startswith("m"):
        base_code = stem
        suffix = ""
        if stem.endswith("_h"):
            base_code = stem[:-2]
            suffix = "_HighPoly"
        elif stem.endswith("_l"):
            base_code = stem[:-2]
            suffix = "_LowPoly"

        if base_code in MONSTER_NAMES:
            english_name = MONSTER_NAMES[base_code][0]
            clean_name = f"{english_name}{suffix}_{stem}"
            return ("Monsters", clean_name)
        return ("Monsters", f"Monster_{stem}")
    elif stem.startswith("w"):
        return ("Weapons", f"Weapon_{stem}")
    elif stem.startswith("g"):
        return ("Interactive_Props", f"Prop_{stem}")
    elif stem.startswith("r"):
        return ("Mounts_and_Rides", f"Mount_{stem}")
    elif stem.startswith("ani"):
        return ("Animation_Rigs", f"Rig_{stem}")
    return ("General_Models", stem)


def read_romfs():
    sys.path.insert(0, "../reference project")
    from dq11tool.ctr.formats import open_image
    f, ncsd, ncch = open_image(r"..\reference project\DQXI.3ds")
    return f, ncch.romfs()


def batch_extract(out_dir: Path, limit: int | None = None) -> int:
    """Extracts NW4C 3D models across all categories with human-readable organization."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_cat_dir = out_dir / "by_category"
    by_cat_dir.mkdir(parents=True, exist_ok=True)

    f, romfs = read_romfs()

    # Prioritize rich playable characters, all 446 authentic monsters, weapons, props, and towns
    target_stems = [
        # Party (all costumes and variations)
        "cha01000a_h", "cha01000b_h", "cha01000c_h", "cha01000d_h",
        "cha01100a_h", "cha01100b_h", "cha01100c_h",
        "cha01200a_h", "cha01200b_h", "cha01200c_h",
        "cha01300a_h", "cha01300b_h", "cha01300c_h",
        "cha01400a_h", "cha01400b_h", "cha01400c_h",
        "cha01500a_h", "cha01500b_h", "cha01500c_h",
        "cha01600a_h", "cha01600b_h", "cha01600c_h",
        "cha01700a_h", "cha01700b_h", "cha01700c_h",
        # Key NPCs
        "cha00001a_h", "cha00002a_h", "cha00003a_h", "cha00004a_h",
        "cha00005a_h", "cha00006a_h", "cha00010a_h",
    ]
    # Add all authentic monsters from monster_names database
    target_stems.extend([f"{m}_h" for m in MONSTER_NAMES.keys()])

    # Weapons
    target_stems.extend([
        "w0001a", "w0002a", "w0003a", "w0004a", "w0010a", "w0015a",
        "w0020a", "w0025a", "w0030a", "w0035a", "w0040a", "w0045a",
        "w0050a", "w0055a", "w0100a", "w0200a", "w0300a", "w0400a",
        "w0500a", "w0600a", "w0700a", "w0800a", "w0850a",
    ])
    # Props
    target_stems.extend(["g3101", "g3102", "g3103", "g3201", "g3301", "g3801", "g3802"])
    # Backgrounds
    target_stems.extend([
        "b001_101a", "b001_102a", "b002_101a", "b002_102a", "b002_103a",
        "b003_101a", "b004_101a", "b005_101a", "b006_101a", "b007_101a",
        "b008_101a", "b009_101a", "b010_101a", "b011_101a",
    ])
    # Mounts
    target_stems.extend(["r001", "r002", "r003", "r004", "r005"])

    # Map files by stem
    file_map: dict[str, any] = {}
    for rf in romfs.files:
        stem = Path(rf.path).stem
        if rf.path.startswith("/3d/model/") and rf.path.endswith(".pack"):
            file_map[stem] = rf
        elif rf.path.startswith("/3d/bg/") and rf.path.endswith(".pack"):
            file_map[stem] = rf

    # Build queue: priority targets first, then remaining
    queue = []
    for stem in target_stems:
        if stem in file_map and file_map[stem] not in queue:
            queue.append(file_map[stem])

    for stem, rf in file_map.items():
        if rf not in queue:
            queue.append(rf)

    if limit:
        queue = queue[:limit]

    print(f"Reading {len(queue)} RomFS 3D model containers...")
    tasks = []
    for rf in queue:
        stem = Path(rf.path).stem
        cat, readable_name = resolve_model_info(stem, rf.path)
        data = romfs.read_file(rf)
        bch_data = None

        if pack.Pack.is_pack(data):
            p = pack.Pack.parse(data)
            for e in p.entries:
                if e.name.endswith(".bch") and e.data[:4] == b"BCH\0":
                    bch_data = e.data
                    break
        elif data[:4] == b"BCH\0":
            bch_data = data

        if bch_data:
            tasks.append((rf.path, cat, readable_name, bch_data))

    f.close()
    print(f"Parsing and exporting {len(tasks)} valid 3D models with multi-threading...")

    def _worker(item):
        rf_path, cat, readable_name, bch_data = item
        target_dir = by_cat_dir / cat / readable_name
        try:
            parser = BchParser(bch_data)
            models = parser.parse_models(readable_name)
            entries = []
            for m in models:
                if m.meshes:
                    export_to_obj(m, target_dir / f"{readable_name}.obj")
                    export_to_gltf(m, target_dir / f"{readable_name}.gltf")
                    total_verts = sum(len(g.positions) for g in m.meshes)
                    total_tris = sum(len(g.indices) // 3 for g in m.meshes)
                    all_pos = [p for g in m.meshes for p in g.positions]
                    min_x = min(p[0] for p in all_pos) if all_pos else 0
                    max_x = max(p[0] for p in all_pos) if all_pos else 0
                    min_y = min(p[1] for p in all_pos) if all_pos else 0
                    max_y = max(p[1] for p in all_pos) if all_pos else 0
                    min_z = min(p[2] for p in all_pos) if all_pos else 0
                    max_z = max(p[2] for p in all_pos) if all_pos else 0
                    entries.append({
                        "category": cat,
                        "readable_name": readable_name,
                        "romfs_path": rf_path,
                        "meshes_count": len(m.meshes),
                        "total_vertices": total_verts,
                        "total_triangles": total_tris,
                        "bbox_extent": f"X[{min_x:.2f}, {max_x:.2f}] Y[{min_y:.2f}, {max_y:.2f}] Z[{min_z:.2f}, {max_z:.2f}]",
                        "folder": f"by_category/{cat}/{readable_name}/",
                    })
            return entries
        except Exception as err:
            print(f"  [ERROR] {rf_path}: {err}")
            return []

    from concurrent.futures import ThreadPoolExecutor
    catalog_entries = []
    total_exported = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for idx, res in enumerate(pool.map(_worker, tasks)):
            if res:
                catalog_entries.extend(res)
                total_exported += len(res)
            if (idx + 1) % 50 == 0 or idx + 1 == len(tasks):
                print(f"  [{idx+1}/{len(tasks)}] Exported models (Total: {total_exported})")

    # Generate MODELS_CATALOG.md
    generate_catalog(out_dir, catalog_entries)
    print(f"3D Model extraction complete! Exported {total_exported} models into {out_dir}")
    return total_exported


def generate_catalog(out_dir: Path, entries: list[dict]):
    """Generates detailed Markdown catalog for all extracted 3D models."""
    catalog_path = out_dir / "MODELS_CATALOG.md"
    lines = [
        "# Dragon Quest XI (3DS) - 3D Models & Meshes Catalog",
        "",
        "This catalog documents the extracted NintendoWare for CTR (NW4C) BCH 3D models from retail *Dragon Quest XI* (Nintendo 3DS).",
        "All models are decoded with authentic vertex positions, normals, texture coordinates, and index buffers,",
        "exported into standard **glTF 2.0** (`.gltf`, `.bin`) and **Wavefront OBJ** (`.obj`, `.mtl`) formats.",
        "",
        f"**Total Documented Models**: {len(entries)}",
        "",
        "## Model Categories Overview",
        "",
        "| Category | Models Count | Description |",
        "| :--- | :--- | :--- |",
    ]

    by_cat: dict[str, list[dict]] = {}
    for e in entries:
        by_cat.setdefault(e["category"], []).append(e)

    cat_descriptions = {
        "Characters": "Playable party members (Hero, Erik, Veronica, Serena, Sylvando, Rab, Jade, Hendrik) and key story NPCs",
        "Monsters": "Field and battle monsters, bosses, metal slimes, dragons, and dungeon fiends",
        "Weapons": "Swords, greatswords, daggers, wands, staves, whips, claws, boomerangs, and shields",
        "Interactive_Props": "Treasure chests, pots, barrels, campfires, goddess statues, and interactive dungeon objects",
        "Environments": "3D towns, villages, castles, dungeons, and overworld field geometry chunks",
        "Mounts_and_Rides": "Rideable monster mounts and the Hero's travel horse",
        "Animation_Rigs": "Skeletal animation rigs and technical bone attachment dummy models",
    }

    for cat, items in by_cat.items():
        desc = cat_descriptions.get(cat, "3D model assets")
        lines.append(f"| **{cat}** | {len(items)} | {desc} |")

    lines.append("")

    for cat, items in by_cat.items():
        lines.extend([
            f"## {cat}",
            "",
            "| Human-Readable Model Name | Meshes | Vertices | Triangles | Bounding Box Extent (Meters) | Directory |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for it in items:
            lines.append(
                f"| **{it['readable_name']}** | {it['meshes_count']} | {it['total_vertices']:,} | {it['total_triangles']:,} | `{it['bbox_extent']}` | [`{it['readable_name']}`]({it['folder']}) |"
            )
        lines.append("")

    catalog_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="DQXI 3DS NW4C BCH 3D Model Decompiler")
    sub = parser.add_subparsers(dest="command")

    ext_p = sub.add_parser("extract", help="Batch extract 3D models from RomFS to glTF 2.0 and OBJ")
    ext_p.add_argument("--limit", type=int, default=None, help="Limit number of models to process")
    ext_p.add_argument("--out", type=Path, default=MODELS_OUT, help="Target output directory")

    conv_p = sub.add_parser("convert", help="Convert single BCH or Pack to glTF/OBJ")
    conv_p.add_argument("input", type=Path, help="Input .bch or .pack file")
    conv_p.add_argument("--out", type=Path, default=MODELS_OUT, help="Target output directory")

    info_p = sub.add_parser("info", help="Inspect BCH model file metadata")
    info_p.add_argument("input", type=Path, help="Input .bch or .pack file")

    args = parser.parse_args()

    if args.command == "extract":
        count = batch_extract(args.out, args.limit)
        return 0 if count > 0 else 1
    elif args.command == "convert":
        data = args.input.read_bytes()
        stem = args.input.stem
        if pack.Pack.is_pack(data):
            p = pack.Pack.parse(data)
            data = next(e.data for e in p.entries if e.data[:4] == b"BCH\0")
        parser = BchParser(data)
        cat, readable_name = resolve_model_info(stem, "")
        models = parser.parse_models(readable_name)
        target_dir = args.out / cat / readable_name
        for m in models:
            export_to_obj(m, target_dir / f"{readable_name}.obj")
            export_to_gltf(m, target_dir / f"{readable_name}.gltf")
            print(f"Exported {readable_name} ({len(m.meshes)} meshes) to {target_dir}")
        return 0
    elif args.command == "info":
        data = args.input.read_bytes()
        if pack.Pack.is_pack(data):
            p = pack.Pack.parse(data)
            data = next(e.data for e in p.entries if e.data[:4] == b"BCH\0")
        parser = BchParser(data)
        models = parser.parse_models(args.input.stem)
        print(f"BCH File: {args.input}")
        for m in models:
            total_vtx = sum(len(g.positions) for g in m.meshes)
            total_tri = sum(len(g.indices) // 3 for g in m.meshes)
            print(f"  Model: {m.name} | Meshes: {len(m.meshes)} | Total Vertices: {total_vtx} | Total Triangles: {total_tri}")
        return 0
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

