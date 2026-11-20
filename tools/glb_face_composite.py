"""Swaps baked face composites into a rigged .glb.

SpicaRef's glTF writer samples one texture unit of a multi-texture face material (the eye atlas), so the
mouth lands on the atlas' black separator. tools/model_tool.py already bakes eyes + mouth + skin into one
`<skin>_composite.png` with its own per-corner UVs; this copies those onto the matching glb primitive
(same triangles, found by comparing corner positions): the primitive is un-welded to one vertex per corner
and gets the composite as its base colour.

    python tools/glb_face_composite.py game_assets/blender/cha01000a_h.glb
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "game_assets" / "models"
DTYPE = {5126: "<f4", 5123: "<u2", 5125: "<u4", 5121: "u1"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_acc(g: dict, blob: bytes, i: int) -> np.ndarray:
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    n = NCOMP[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    arr = np.frombuffer(blob, dtype=DTYPE[a["componentType"]], count=a["count"] * n, offset=off)
    if bv.get("byteStride") and bv["byteStride"] != n * arr.itemsize:
        raise ValueError("strided accessor")
    return arr.reshape(a["count"], n)


def apply(glb: Path) -> str:
    stem = glb.stem
    src = next(iter(MODELS.rglob(f"{stem}.gltf")), None)
    if src is None:
        return ""
    sg = json.loads(src.read_text(encoding="utf-8"))
    sblob = (src.with_suffix(".bin")).read_bytes()
    # model_tool primitives whose material samples a *_composite image
    comp = []
    for m in sg["meshes"]:
        for p in m["primitives"]:
            tex = sg["materials"][p["material"]]["pbrMetallicRoughness"].get("baseColorTexture")
            if tex is None:
                continue
            t = sg["textures"][tex["index"]]
            uri = sg["images"][t["source"]]["uri"]
            if uri.endswith("_composite.png") and (src.parent / uri).is_file():
                comp.append((p, uri, t.get("sampler")))
    if not comp:
        return ""

    d = glb.read_bytes()
    jlen = struct.unpack("<I", d[12:16])[0]
    g = json.loads(d[20:20 + jlen])
    blen = struct.unpack("<I", d[20 + jlen:24 + jlen])[0]
    blob = bytearray(d[28 + jlen:28 + jlen + blen])

    def add_view(data: bytes, target: int | None = None) -> int:
        while len(blob) % 4:
            blob.append(0)
        view = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if target:
            view["target"] = target
        blob.extend(data)
        g["bufferViews"].append(view)
        return len(g["bufferViews"]) - 1

    def add_acc(arr: np.ndarray, ctype: int, typ: str, target: int, minmax: bool = False) -> int:
        a = {"bufferView": add_view(arr.tobytes(), target), "componentType": ctype, "count": len(arr), "type": typ}
        if minmax:
            a["min"], a["max"] = arr.min(0).tolist(), arr.max(0).tolist()
        g["accessors"].append(a)
        return len(g["accessors"]) - 1

    done = []
    for sp, uri, sampler in comp:
        sidx = read_acc(sg, sblob, sp["indices"])[:, 0]
        spos = read_acc(sg, sblob, sp["attributes"]["POSITION"])[sidx]
        suv = read_acc(sg, sblob, sp["attributes"]["TEXCOORD_0"])[sidx].astype("<f4")
        target = None
        for m in g["meshes"]:
            for p in m["primitives"]:
                if "JOINTS_0" not in p["attributes"]:
                    continue
                idx = read_acc(g, bytes(blob), p["indices"])[:, 0]
                if len(idx) != len(sidx):
                    continue
                pos = read_acc(g, bytes(blob), p["attributes"]["POSITION"])
                if np.abs(pos[idx] - spos).max() < 1e-4:
                    target = (m, p, idx)
                    break
            if target:
                break
        if target is None:
            continue
        m, p, idx = target
        for key in ("POSITION", "NORMAL", "JOINTS_0", "WEIGHTS_0"):
            if key not in p["attributes"]:
                continue
            ai = p["attributes"][key]
            a = g["accessors"][ai]
            arr = read_acc(g, bytes(blob), ai)[idx]
            p["attributes"][key] = add_acc(np.ascontiguousarray(arr), a["componentType"], a["type"], 34962, key == "POSITION")
        p["attributes"]["TEXCOORD_0"] = add_acc(np.ascontiguousarray(suv), 5126, "VEC2", 34962)
        p["indices"] = add_acc(np.arange(len(idx), dtype="<u4").reshape(-1, 1), 5125, "SCALAR", 34963)
        # composite image + texture + a material copy
        img_view = add_view((src.parent / uri).read_bytes())
        g.setdefault("images", []).append({"name": uri[:-4], "mimeType": "image/png", "bufferView": img_view})
        samplers = g.setdefault("samplers", [])
        samplers.append({k: v for k, v in sg["samplers"][sampler or 0].items()})
        g["textures"].append({"source": len(g["images"]) - 1, "sampler": len(samplers) - 1})
        mat = json.loads(json.dumps(g["materials"][p["material"]]))
        mat["pbrMetallicRoughness"]["baseColorTexture"] = {"index": len(g["textures"]) - 1}
        g["materials"].append(mat)
        p["material"] = len(g["materials"]) - 1
        done.append(m.get("name", "?"))
    if not done:
        return ""

    g["buffers"][0]["byteLength"] = len(blob)
    js = json.dumps(g, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    while len(blob) % 4:
        blob.append(0)
    out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(blob))
    out += struct.pack("<I", len(js)) + b"JSON" + js + struct.pack("<I", len(blob)) + b"BIN\x00" + bytes(blob)
    glb.write_bytes(out)
    return "baked face composite on " + ", ".join(done)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(apply(Path(a)) or "nothing to do")
