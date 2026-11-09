#!/usr/bin/env python3
"""One entry point for the editor's asset Export/Replace workflows.

The Rust panels do not re-implement any format logic: they call this tool and
show its warnings. Each family follows the same contract:

  export   copy the editable standard-format file out for an external editor
  replace  import the edited file, encode it back into the *original* 3DS
           format, validate hardware limits, optionally write a preview of
           what the console will actually read, and optionally stage the
           containing pack into ``mod/romfs`` (LayeredFS).
  inspect  describe the source asset and its 3DS limits

Families
--------
  texture        game_assets/textures/**/*.png        -> BFLIM inside a UI SARC
  model-texture  one embedded BCH texture (by name)   -> BCH (same size)
  model          an edited OBJ (positions or indices) -> BCH (same size)
  audio          game_assets/audio/**/*.wav           -> BCSTM (DSP-ADPCM)
  layout         game_assets/layouts/**/*.json        -> BFLYT/BFLAN inside a SARC
  map            editor_projects/<map>.json           -> level3d.bxon level pack

Every command prints one JSON object on the last line when ``--json`` is used,
so the UI can parse it without scraping prose.

Examples
--------
    python tools/asset_replace.py inspect --family texture \
        --asset arcs/ui/battle_2d/battle_2d/timg/icon_target_2d.png
    python tools/asset_replace.py export --family texture --asset ... --out build/exports
    python tools/asset_replace.py replace --family texture --asset ... \
        --file my_icon.png --stage --preview
    python tools/asset_replace.py replace --family audio \
        --asset romfs/sound/str/BGM_B01.dspadpcm.wav --file new.wav --stage --preview
    python tools/asset_replace.py replace --family map --asset b001_101a \
        --file editor_projects/b001_101a.json --stage
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

GAME_DATA = PROJECT_ROOT / "game_data"
ASSETS = PROJECT_ROOT / "game_assets"
BUILD = PROJECT_ROOT / "build"
# Default scratch space; the panels show these paths and let the modder change them.
EDIT_DIR = BUILD / "asset_edits"
EXPORT_DIR = BUILD / "exports"


class FamilyError(RuntimeError):
    """A problem the modder can fix (wrong dimensions, missing file, ...)."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _require(path: Path, what: str) -> Path:
    if not path.is_file():
        raise FamilyError(f"{what} not found: {path.relative_to(PROJECT_ROOT)}")
    return path


def _pack_for_bch(bch: Path) -> tuple[str, str]:
    """BCH at game_data/packs/<a>/<b>/<name>.bch -> pack <a>/<b>.pack, member <name>.bch."""
    try:
        rel = bch.relative_to(GAME_DATA / "packs")
    except ValueError as exc:
        raise FamilyError(f"{bch} is not under game_data/packs") from exc
    pack = rel.parent.parent / (rel.parent.name + ".pack")
    return pack.as_posix(), rel.name


def _arc_file_for(member_rel: Path) -> tuple[Path, str]:
    """The SARC file that holds an extracted member, plus the member path inside it."""
    parts = member_rel.parts
    for i in range(len(parts) - 1, 0, -1):
        arc = (GAME_DATA / "packs" / Path(*parts[:i])).with_suffix(".arc")
        if arc.is_file():
            return arc, Path(*parts[i:]).as_posix()
    raise FamilyError(f"no SARC archive found for {member_rel.as_posix()}")


def _arc_for_member(member_rel: Path) -> tuple[str, str, str]:
    """Find the SARC and PACK that hold an extracted member.

    ``ui/battle_2d/battle_2d/timg/x.bflim`` lives in
    ``game_data/packs/ui/battle_2d/battle_2d.arc`` inside
    ``game_data/romfs/ui/battle_2d.pack`` (member ``battle_2d.arc``).
    Returns ``(pack_relative_path, arc_member_name, member_path_in_sarc)``.
    """
    arc, inner = _arc_file_for(member_rel)
    rel = arc.relative_to(GAME_DATA / "packs")
    pack = rel.parent.parent / (rel.parent.name + ".pack")
    return pack.as_posix(), rel.name, inner


def _convert_bch(bch: Path, target: Path, stem: str | None = None,
                 source_path: Path | None = None) -> Path:
    """Exports one BCH to glTF + OBJ + embedded PNGs in ``target``.

    ``source_path`` lets a preview of patched bytes keep the original model's
    identity (bone/skin manifests are keyed by the retail path).
    """
    from tools.model_tool import BchParser, export_to_gltf, export_to_obj

    stem = stem or bch.stem
    target.mkdir(parents=True, exist_ok=True)
    parser = BchParser(bch.read_bytes(), source_path=source_path or bch)
    models = parser.parse_models(stem)
    if not models:
        raise FamilyError(f"{bch.name} has no mesh models to export")
    # A BCH can contain several sub-models (character + weapon, etc.); never
    # overwrite one with another - suffix them, and return the first for the
    # viewport preview.
    multiple = len(models) > 1
    first = None
    for index, model in enumerate(models):
        name = f"{stem}_{index}" if multiple else stem
        obj = target / f"{name}.obj"
        export_to_obj(model, obj)
        export_to_gltf(model, target / f"{name}.gltf")
        first = first or obj
    return first or (target / f"{stem}.obj")


def _stage_pack(pack_rel: str, member: str, replacement: Path, mod: Path) -> dict:
    from tools.export_mod import stage_member

    return stage_member(pack_rel, member, replacement, mod, work_dir=BUILD / "staged")


def _display_path(path: Path) -> str:
    """Project-relative when inside the workspace, absolute otherwise (export dirs)."""
    try:
        return str(Path(path).relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _save_binary(kind: str, stem: str, suffix: str, data: bytes) -> Path:
    out = EDIT_DIR / kind / f"{stem}{suffix}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def _report(ok: bool, family: str, action: str, **extra) -> dict:
    out = {"ok": ok, "family": family, "action": action}
    out.update(extra)
    return out


# ---------------------------------------------------------------------------
# textures (BFLIM / PNG)
# ---------------------------------------------------------------------------
def _texture_paths(asset: str) -> tuple[Path, Path, Path]:
    """(PNG in game_assets/textures, source BFLIM, path relative to game_data/arcs)."""
    png = ASSETS / "textures" / asset
    source_rel = Path(asset).with_suffix(".bflim")
    bflim = GAME_DATA / source_rel
    try:
        member_rel = source_rel.relative_to("arcs")
    except ValueError as exc:
        raise FamilyError(f"texture asset {asset!r} is not under game_assets/textures/arcs") from exc
    return png, bflim, member_rel


def inspect_texture(asset: str) -> dict:
    from tools import texture_tool

    png, bflim, member_rel = _texture_paths(asset)
    _require(png, "texture PNG")
    _require(bflim, "source BFLIM")
    info = texture_tool.bflim_info(bflim.read_bytes())
    mips = texture_tool.bflim_mip_count(bflim.read_bytes())
    warnings = []
    if info["format"] in (10, 11):
        warnings.append(f"{info['format_name']} is lossy (4 bits per pixel)")
    if mips > 1:
        warnings.append(f"{mips} mip levels; only the base level is editable")
    if info["width"] > 2048 or info["height"] > 2048:
        warnings.append("larger than the 3DS 2048 px texture limit")
    pack, arc_member, inner = _arc_for_member(member_rel)
    return _report(
        True, "texture", "inspect",
        asset=asset, source=str(bflim.relative_to(PROJECT_ROOT)),
        width=info["width"], height=info["height"],
        format=info["format_name"], format_id=info["format"],
        mip_levels=mips, vram_bytes=info["width"] * info["height"] * 4,
        pack=pack, arc_member=arc_member, member=inner,
        warnings=warnings,
    )


def export_texture(asset: str, out_dir: Path) -> dict:
    png, bflim, member_rel = _texture_paths(asset)
    _require(png, "texture PNG")
    target = out_dir / "textures" / asset
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(png, target)
    meta = png.with_name(png.stem + ".meta.json")
    if meta.is_file():
        shutil.copy2(meta, target.with_name(target.stem + ".meta.json"))
    info = inspect_texture(asset)
    return _report(True, "texture", "export", asset=asset,
                   exported=_display_path(target),
                   **{k: info[k] for k in ("width", "height", "format", "mip_levels", "warnings")})


def replace_texture(asset: str, edited: Path, stage: bool, preview: bool, allow_resize: bool, mod: Path) -> dict:
    import numpy as np
    from PIL import Image

    from tools import sarc_tool, texture_tool

    _png, bflim, member_rel = _texture_paths(asset)
    _require(bflim, "source BFLIM")
    _require(edited, "replacement PNG")
    original = bflim.read_bytes()
    warnings, errors = texture_tool.validate_bflim_replacement(
        original, edited, allow_resize=allow_resize)
    if errors:
        raise FamilyError("; ".join(errors))
    info = texture_tool.bflim_info(original)
    with Image.open(edited) as img:
        img = img.convert("RGBA")
        if allow_resize and img.size != (info["width"], info["height"]):
            # Store the edited size: the BFLIM header carries it and the payload
            # is re-tiled for it, so a grown texture is a valid file.  The pane
            # that draws it keeps its own size, so the game scales the picture.
            info = dict(info, width=img.width, height=img.height)
        rebuilt = texture_tool.encode_bflim(np.asarray(img, dtype=np.uint8), info,
                                            footer_template=original)
    if len(rebuilt) != len(original) and not allow_resize:
        raise FamilyError(
            f"re-encoded BFLIM is {len(rebuilt)} bytes, original {len(original)}; "
            "pass --allow-resize to store a different image size"
        )
    out_bflim = _save_binary("textures", Path(asset).stem, ".bflim", rebuilt)
    pack, arc_member, inner = _arc_for_member(member_rel)
    # Rebuild the archive that holds this BFLIM, then stage its PACK.
    arc_file, _inner = _arc_file_for(member_rel)
    new_arc = sarc_tool.replace_member(_require(arc_file, "source SARC").read_bytes(), inner, rebuilt)
    arc_out = _save_binary("textures", Path(asset).stem, f"_{Path(arc_member).stem}.arc", new_arc)
    result = _report(True, "texture", "replace", asset=asset,
                     warnings=warnings, encoded=str(out_bflim.relative_to(PROJECT_ROOT)),
                     pack=pack, arc_member=arc_member, member=inner, bytes=len(rebuilt))
    if stage:
        result["staged"] = _stage_pack(pack, arc_member, arc_out, mod)
    if preview:
        rgba, _ = texture_tool.decode_bflim(rebuilt)
        preview_png = EDIT_DIR / "textures" / f"{Path(asset).stem}.preview.png"
        preview_png.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba, "RGBA").save(preview_png)
        result["preview"] = _display_path(preview_png)
        result["preview_note"] = (
            "decoded from the encoded BFLIM, so ETC1/quantisation artefacts are visible "
            "(that is what the 3DS shows)"
        )
    return result


# ---------------------------------------------------------------------------
# BCH models (geometry and embedded textures)
# ---------------------------------------------------------------------------
def _bch_path(asset: str) -> Path:
    path = GAME_DATA / "packs" / asset
    if path.suffix.lower() != ".bch":
        raise FamilyError("model asset must be a .bch path under game_data/packs")
    return path


def inspect_model(asset: str, texture: str | None = None) -> dict:
    from tools.bch_texture_patch import texture_infos

    bch = _require(_bch_path(asset), "model BCH")
    infos = texture_infos(bch.read_bytes())
    textures = [
        {k: t[k] for k in ("name", "width", "height", "format_name", "mip_levels", "base_size")}
        for t in infos
    ]
    warnings = []
    if any(t["mip_levels"] > 1 for t in infos):
        warnings.append("some textures have mip chains; only the base level is replaced")
    selectable = [t for t in infos if texture is None or t["name"].lower() == texture.lower()]
    if texture and not selectable:
        raise FamilyError(f"texture {texture!r} is not embedded in {bch.name}")
    pack, member = _pack_for_bch(bch)
    return _report(True, "model", "inspect", asset=asset, pack=pack, member=member,
                   textures=textures, texture=selectable[0] if selectable else None,
                   warnings=warnings)


def export_model(asset: str, out_dir: Path) -> dict:
    """Re-exports the source BCH to glTF/OBJ with the project's proven converter."""
    bch = _require(_bch_path(asset), "model BCH")
    target = out_dir / "models" / bch.stem
    obj = _convert_bch(bch, target)
    gltf = obj.with_suffix(".gltf")
    return _report(True, "model", "export", asset=asset,
                   exported_dir=_display_path(target),
                   gltf=_display_path(gltf) if gltf.is_file() else None,
                   obj=_display_path(obj) if obj.is_file() else None)


def replace_model_geometry(asset: str, edited: Path, indices: bool, stage: bool, preview: bool,
                           mod: Path) -> dict:
    from tools import model_patch

    bch = _require(_bch_path(asset), "model BCH")
    _require(edited, "edited OBJ")
    raw = bch.read_bytes()
    warnings = []
    if indices:
        groups = model_patch.obj_indices(edited)
        if not groups:
            raise FamilyError("the OBJ has no face groups to import")
        patched, report = model_patch.apply_indices(raw, groups, source_path=bch)
        warnings.append("triangle topology must keep the original index count; order is preserved")
    else:
        positions = model_patch.obj_positions(edited)
        if not positions:
            raise FamilyError("the OBJ has no vertices")
        if any(not all(map(math.isfinite, p)) for p in positions):
            raise FamilyError("the OBJ contains a non-finite vertex; Blender wrote NaN/inf")
        patched, report = model_patch.apply_positions(raw, positions, source_path=bch)
        warnings.append(
            "vertex positions must keep the original vertex count and order; the BCH vertex "
            "format (attribute types, strides, de-interleaving) and every other buffer are untouched"
        )
    if len(patched) != len(raw):
        raise FamilyError("the patch changed the BCH size; only same-size geometry edits are supported")
    out = _save_binary("models", bch.stem, ".bch", patched)
    pack, member = _pack_for_bch(bch)
    result = _report(True, "model", "replace", asset=asset, mode="indices" if indices else "positions",
                     warnings=warnings, report=report,
                     encoded=str(out.relative_to(PROJECT_ROOT)), pack=pack, member=member, bytes=len(patched))
    if stage:
        result["staged"] = _stage_pack(pack, member, out, mod)
    if preview:
        result["preview"] = _model_preview(bch.stem, patched, bch)
    return result


def replace_model_texture(asset: str, texture: str, edited: Path, stage: bool, preview: bool,
                          allow_resize: bool, mod: Path) -> dict:
    from PIL import Image

    from tools import bch_texture_patch

    bch = _require(_bch_path(asset), "model BCH")
    _require(edited, "replacement PNG")
    raw = bch.read_bytes()
    infos = {t["name"].lower(): t for t in bch_texture_patch.texture_infos(raw)}
    info = infos.get(texture.lower())
    if info is None:
        raise FamilyError(f"texture {texture!r} is not embedded in {bch.name}")
    with Image.open(edited) as img:
        warnings = []
        if img.size != (info["width"], info["height"]):
            if not allow_resize:
                raise FamilyError(
                    f"PNG is {img.width}x{img.height} but {texture} is {info['width']}x{info['height']}; "
                    "export the embedded texture and keep its size"
                )
            warnings.append("the PNG was scaled to the original texture size")
    patched = bch_texture_patch.replace_texture(raw, texture, edited, allow_resize=allow_resize)
    with Image.open(edited) as img:
        _, encode_warnings = bch_texture_patch.encode_for_info(info, img)
    warnings.extend(encode_warnings)
    if len(patched) != len(raw):
        raise FamilyError("texture replacement changed the BCH size")
    out = _save_binary("models", f"{bch.stem}_{texture}", ".bch", patched)
    pack, member = _pack_for_bch(bch)
    result = _report(True, "model-texture", "replace", asset=asset, texture=texture,
                     warnings=warnings, format=info["format_name"],
                     encoded=str(out.relative_to(PROJECT_ROOT)), pack=pack, member=member, bytes=len(patched))
    if stage:
        result["staged"] = _stage_pack(pack, member, out, mod)
    if preview:
        result["preview"] = _model_preview(f"{bch.stem}_{texture}", patched, bch)
    return result


def _model_preview(stem: str, bch_bytes: bytes, source: Path) -> str:
    target = EDIT_DIR / "models" / stem
    target.mkdir(parents=True, exist_ok=True)
    temporary = target / f"{stem}.bch"
    temporary.write_bytes(bch_bytes)
    obj = _convert_bch(temporary, target, stem, source_path=source)
    return _display_path(obj)


# ---------------------------------------------------------------------------
# audio (BCSTM / WAV)
# ---------------------------------------------------------------------------
def _audio_paths(asset: str) -> tuple[Path, Path]:
    wav = ASSETS / "audio" / asset
    if wav.suffix.lower() != ".wav":
        raise FamilyError("audio asset must be a .wav path under game_assets/audio")
    rel = Path(asset)
    original = GAME_DATA / (rel.with_suffix(".bcstm")).as_posix()
    return wav, original


def inspect_audio(asset: str) -> dict:
    from tools.audio_tool import parse_bcstm_info

    wav, bcstm = _audio_paths(asset)
    _require(bcstm, "source BCSTM")
    info, _ = parse_bcstm_info(bcstm.read_bytes())
    codec = {0: "PCM8", 1: "PCM16", 2: "DSP-ADPCM"}.get(info.codec, "unknown")
    warnings = []
    if info.codec == 2:
        warnings.append("DSP-ADPCM is re-encoded from the WAV; it is lossy (about -40 dB noise)")
    if info.loop:
        warnings.append(f"the stream loops from sample {info.loop_start}; the loop point is kept")
    return _report(True, "audio", "inspect", asset=asset,
                   source=str(bcstm.relative_to(PROJECT_ROOT)), codec=codec,
                   sample_rate=info.sample_rate, channels=info.channels,
                   total_samples=info.total_samples, loop=info.loop,
                   warnings=warnings)


def export_audio(asset: str, out_dir: Path) -> dict:
    wav, _bcstm = _audio_paths(asset)
    _require(wav, "audio WAV")
    target = out_dir / "audio" / asset
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(wav, target)
    info = inspect_audio(asset)
    return _report(True, "audio", "export", asset=asset,
                   exported=_display_path(target),
                   **{k: info[k] for k in ("codec", "sample_rate", "channels", "total_samples", "warnings")})


def replace_audio(asset: str, edited: Path, codec: str, stage: bool, preview: bool, mod: Path) -> dict:
    import numpy as np

    from tools import audio_tool
    from tools.bcstm_encode import build_bcstm, build_bcstm_dsp, wav_to_pcm16

    _wav, bcstm = _audio_paths(asset)
    _require(bcstm, "source BCSTM")
    _require(edited, "replacement WAV")
    template = bcstm.read_bytes()
    info, _ = audio_tool.parse_bcstm_info(template)
    pcm, rate, channels = wav_to_pcm16(edited)
    warnings = []
    if channels != info.channels:
        raise FamilyError(
            f"the WAV is {channels} channel(s) but the stream is {info.channels}; "
            f"mix it to {info.channels} channel(s) first"
        )
    if rate != info.sample_rate:
        warnings.append(f"resampled from {rate} Hz to the stream's {info.sample_rate} Hz")
    if codec == "dspadpcm":
        rebuilt = build_bcstm_dsp(template, pcm, rate, channels)
        warnings.append("DSP-ADPCM is lossy; the preview is the decoded encoded stream")
    else:
        rebuilt = build_bcstm(template, pcm, rate, channels)
        warnings.append("PCM16 is lossless but ~4x larger than the retail DSP-ADPCM stream")
    if len(rebuilt) > len(template):
        warnings.append(
            f"the stream grew by {len(rebuilt) - len(template):,} bytes; a Luma LayeredFS file "
            "handles that, but a same-slot RomFS patch does not (use tools/export_mod.py)"
        )
    out = _save_binary("audio", Path(asset).name, ".bcstm", rebuilt)
    result = _report(True, "audio", "replace", asset=asset, codec=codec,
                     warnings=warnings, encoded=str(out.relative_to(PROJECT_ROOT)),
                     bytes=len(rebuilt), original_bytes=len(template))
    if stage:
        # asset already starts with "romfs/" (it mirrors game_data/romfs)
        target = mod / Path(asset).with_suffix(".bcstm")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(rebuilt)
        result["staged"] = {"mod_file": _display_path(target), "bytes": len(rebuilt)}
    if preview:
        pcm16, rate2, channels2 = audio_tool.decode_bcstm(rebuilt)
        preview_wav = EDIT_DIR / "audio" / (Path(asset).name + ".preview.wav")
        preview_wav.parent.mkdir(parents=True, exist_ok=True)
        audio_tool.bcstm_to_wav_bytes(rebuilt)  # validates the container
        with open(preview_wav, "wb") as fh:
            import wave

            with wave.open(fh, "wb") as wf:
                wf.setnchannels(channels2)
                wf.setsampwidth(2)
                wf.setframerate(rate2)
                wf.writeframes(pcm16)
        result["preview"] = _display_path(preview_wav)
    return result


# ---------------------------------------------------------------------------
# UI layouts (BFLYT / BFLAN)
# ---------------------------------------------------------------------------
def _layout_paths(asset: str) -> tuple[Path, Path, Path]:
    """(JSON in game_assets/layouts, source BFLYT/BFLAN, path relative to game_data/arcs)."""
    json_path = ASSETS / "layouts" / asset
    source_rel = Path(asset)
    if source_rel.suffix != ".json":
        raise FamilyError("layout asset must be a .json exported by layout_tool")
    binary = GAME_DATA / source_rel.with_suffix("")
    try:
        member_rel = source_rel.with_suffix("").relative_to("arcs")
    except ValueError as exc:
        raise FamilyError(f"layout asset {asset!r} is not under game_assets/layouts/arcs") from exc
    return json_path, binary, member_rel


def inspect_layout(asset: str) -> dict:
    from tools import layout_tool

    json_path, binary, member_rel = _layout_paths(asset)
    _require(json_path, "layout JSON")
    _require(binary, "source layout")
    doc = json.loads(json_path.read_text(encoding="utf-8"))
    pack, arc_member, inner = _arc_for_member(member_rel)
    warnings = []
    if doc.get("format") == "BFLYT" and doc.get("raw_sections"):
        pane_sections = [s for s in doc["raw_sections"] if s.get("magic") in layout_tool.PANE_MAGICS]
        if len(pane_sections) != len(doc.get("panes", [])):
            warnings.append("pane count in JSON differs from the raw sections; edits will be refused")
    if doc.get("format") == "BFLAN":
        warnings.append("BFLAN keyframe payloads are edited as raw sections; the Panes view is preview-only")
    return _report(True, "layout", "inspect", asset=asset, format=doc.get("format"),
                   panes=len(doc.get("panes", [])), pack=pack, arc_member=arc_member,
                   member=inner, source=str(binary.relative_to(PROJECT_ROOT)), warnings=warnings)


def export_layout(asset: str, out_dir: Path) -> dict:
    json_path, _binary, _rel = _layout_paths(asset)
    _require(json_path, "layout JSON")
    target = out_dir / "layouts" / asset
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(json_path, target)
    info = inspect_layout(asset)
    return _report(True, "layout", "export", asset=asset,
                   exported=_display_path(target),
                   **{k: info[k] for k in ("format", "panes", "warnings")})


def replace_layout(asset: str, edited: Path, stage: bool, preview: bool, mod: Path) -> dict:
    from tools import layout_tool, sarc_tool

    json_path, binary, member_rel = _layout_paths(asset)
    _require(binary, "source layout")
    _require(edited, "edited layout JSON")
    try:
        doc = json.loads(edited.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FamilyError(f"{edited.name} is not valid JSON: {exc}") from exc
    original = binary.read_bytes()
    try:
        if doc.get("format") == "BFLAN" or binary.suffix.lower() == ".bflan":
            rebuilt = layout_tool.build_bflan(doc)
            notes = ["BFLAN raw sections are rebuilt; tag/frame edits are not interpreted"]
        else:
            doc = layout_tool.complete(doc, original)
            rebuilt = layout_tool.build_bflyt(doc)
            notes = doc.get("_warnings", [])
    except ValueError as exc:
        raise FamilyError(str(exc)) from exc
    warnings = list(notes)
    if len(rebuilt) != len(original):
        # A longer pane string grows its BFLYT section; SARC and PACK are rebuilt
        # at the new size below, so this is a normal mod (LayeredFS takes any
        # size, and the .3ds target relocates the grown pack in the RomFS).
        warnings.append(
            f"rebuilt layout is {len(rebuilt):,} bytes (retail {len(original):,}); "
            "the archive and pack are rebuilt at the new size"
        )
    out = _save_binary("layouts", binary.stem, binary.suffix, rebuilt)
    pack, arc_member, inner = _arc_for_member(member_rel)
    arc_file, _inner = _arc_file_for(member_rel)
    new_arc = sarc_tool.replace_member(_require(arc_file, "source SARC").read_bytes(), inner, rebuilt)
    arc_out = _save_binary("layouts", binary.stem, f"_{Path(arc_member).stem}.arc", new_arc)
    result = _report(True, "layout", "replace", asset=asset, warnings=warnings,
                     encoded=str(out.relative_to(PROJECT_ROOT)), pack=pack,
                     arc_member=arc_member, member=inner, bytes=len(rebuilt))
    if stage:
        result["staged"] = _stage_pack(pack, arc_member, arc_out, mod)
    if preview:
        parsed = (layout_tool.parse_bflan(rebuilt) if rebuilt[:4] == b"FLAN"
                  else layout_tool.parse_bflyt(rebuilt))
        preview_json = EDIT_DIR / "layouts" / f"{binary.stem}.preview.json"
        preview_json.parent.mkdir(parents=True, exist_ok=True)
        preview_json.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
        result["preview"] = _display_path(preview_json)
    return result


# ---------------------------------------------------------------------------
# maps (level3d placements)
# ---------------------------------------------------------------------------
def _map_paths(map_id: str) -> tuple[Path, Path]:
    scene = ASSETS / "maps" / map_id / "scene.json"
    source = GAME_DATA / "packs" / "level3d" / map_id / "level3d.bxon"
    return scene, source


def inspect_map(map_id: str) -> dict:
    from tools.map_tool import decode_map

    scene, source = _map_paths(map_id)
    _require(scene, "decoded map scene")
    _require(source, "level3d source")
    doc = json.loads(scene.read_text(encoding="utf-8"))
    return _report(True, "map", "inspect", asset=map_id,
                   objects=len(doc.get("objects", [])), source=str(source.relative_to(PROJECT_ROOT)),
                   background=doc.get("background_bch"),
                   warnings=[] if doc.get("objects") else ["this map has no recovered placement records"])


def export_map(map_id: str, out_dir: Path) -> dict:
    scene, _source = _map_paths(map_id)
    _require(scene, "decoded map scene")
    target = out_dir / "maps" / map_id / "scene.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(scene, target)
    info = inspect_map(map_id)
    return _report(True, "map", "export", asset=map_id,
                   exported=_display_path(target), objects=info["objects"])


def replace_map(map_id: str, project: Path, stage: bool, preview: bool, mod: Path) -> dict:
    from tools import bxon_struct  # noqa: F401  (validates import path early)

    _scene, source = _map_paths(map_id)
    _require(source, "level3d source")
    _require(project, "map project JSON")
    doc = json.loads(project.read_text(encoding="utf-8"))
    edits = doc.get("edits") or []
    raw = bytearray(source.read_bytes())
    warnings = []
    if not edits:
        warnings.append("the project has no changed transforms; the BXON is rebuilt unchanged")
    from tools.map_tool import write_edit

    for edit in edits:
        offset = int(str(edit["offset"]), 16)
        if offset + 4 > len(raw):
            raise FamilyError(f"offset 0x{offset:X} is outside the {len(raw)}-byte level3d.bxon")
        if edit.get("type", "f32") == "f32" and not (-1e7 < float(edit["value"]) < 1e7):
            raise FamilyError(f"offset 0x{offset:X}: implausible value {edit['value']}")
        try:
            write_edit(raw, offset, edit)
        except ValueError as exc:
            raise FamilyError(str(exc)) from exc
    ops = doc.get("ops") or []
    if ops:
        from tools import level_records

        try:
            patched, results = level_records.apply_ops(bytes(raw), ops)
        except level_records.RecordError as exc:
            raise FamilyError(f"record operation refused: {exc}") from exc
        warnings.append(f"{len(ops)} record operation(s) applied; the level grew by {len(patched) - len(raw):,} bytes")
        warnings.append("Emulator-proven: an NPC record appended to its own array loads and appears in game "
                        "(docs/LEVEL_FORMAT.md). Also proven: deleting actor records (an array element is removed, or the layer-mask byte +0x5F of a lone record is zeroed so the game skips it), exits and collision. Not yet proven: 68/120-byte placements.")
        if any(o["op"] == "delete" for o in ops):
            warnings.append("deleted records shift the index of later records; scripts that refer to them by index may need a check")
    else:
        patched = bytes(raw)
    out = ASSETS / "maps" / map_id / "level3d.patched.bxon"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(patched)
    result = _report(True, "map", "replace", asset=map_id, edits=len(edits),
                     warnings=warnings, encoded=str(out.relative_to(PROJECT_ROOT)),
                     changed=patched != source.read_bytes(), bytes=len(patched))
    moves = [m for m in (doc.get("collision") or []) if m.get("drop") or any(abs(float(v)) > 1e-6 for v in m.get("delta", []))]
    boxes = doc.get("collision_boxes") or []
    if moves or boxes:
        from tools import rcb_tool

        bg = rcb_tool.bg_name(map_id)
        src = PROJECT_ROOT / "game_data" / "packs" / "3d" / "bg" / bg / f"{bg}_chit.rcb"
        _require(src, "collision file")
        blob = bytearray(src.read_bytes())
        for m in moves:
            if m.get("delta") and any(abs(float(v)) > 1e-6 for v in m["delta"]):
                rcb_tool.translate_shape(blob, int(m["shape"]), *[float(v) for v in m["delta"]])
        for m in moves:
            if m.get("drop"):
                rcb_tool.drop_shape(blob, int(m["shape"]))
        blob = bytearray(blob)
        for box in boxes:
            blob = bytearray(rcb_tool.add_box(bytes(blob), tuple(float(v) for v in box["lo"]), tuple(float(v) for v in box["hi"])))
        coll_out = ASSETS / "maps" / map_id / f"{bg}_chit.patched.rcb"
        coll_out.write_bytes(bytes(blob))
        result["collision"] = {"shapes_moved": len(moves), "boxes_added": len(boxes), "file": str(coll_out.relative_to(PROJECT_ROOT))}
        if stage:
            from tools.export_mod import stage_member

            result["collision"]["staged"] = stage_member(f"3d/bg/{bg}.pack", f"{bg}_chit.rcb", coll_out, mod)
        warnings.append(f"{len(moves)} collision shape edit(s) (moved / deleted) in {bg}_chit.rcb (proven in the emulator: docs/COLLISION.md)")
    if stage:
        from tools.patch_game import rebuild_pack

        pack = GAME_DATA / "romfs" / "level3d" / f"{map_id}.pack"
        _require(pack, "level3d pack")
        target = mod / "romfs" / "level3d" / f"{map_id}.pack"
        target.parent.mkdir(parents=True, exist_ok=True)
        built = rebuild_pack(pack, out, target)
        result["staged"] = {"mod_file": _display_path(target), "bytes": len(built)}
    if preview:
        preview_json = EDIT_DIR / "maps" / f"{map_id}.preview.json"
        preview_json.parent.mkdir(parents=True, exist_ok=True)
        preview_json.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        result["preview"] = _display_path(preview_json)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["inspect", "export", "replace"])
    ap.add_argument("--family", required=True,
                    choices=["texture", "model", "model-texture", "audio", "layout", "map"])
    ap.add_argument("--asset", required=True,
                    help="path relative to the standard-format library (or the map id for maps)")
    ap.add_argument("--file", type=Path, help="edited file to import")
    ap.add_argument("--texture", help="embedded BCH texture name (model-texture)")
    ap.add_argument("--indices", action="store_true", help="OBJ faces replace triangle indices (model)")
    ap.add_argument("--codec", choices=["dspadpcm", "pcm16"], default="dspadpcm")
    ap.add_argument("--out", type=Path, default=EXPORT_DIR,
                    help=f"export destination (default {EXPORT_DIR.relative_to(PROJECT_ROOT)})")
    ap.add_argument("--stage", action="store_true", help="write the containing PACK into mod/romfs")
    ap.add_argument("--preview", action="store_true", help="write a preview of the encoded asset")
    ap.add_argument("--allow-resize", action="store_true", help="scale a differently sized PNG")
    ap.add_argument("--mod", type=Path, default=PROJECT_ROOT / "mod")
    ap.add_argument("--json", action="store_true", help="print a JSON result on the last line")
    args = ap.parse_args(argv)
    if args.action == "replace" and args.file is None:
        ap.error("--file is required for replace")
    # Report paths relative to the project; resolve user-supplied ones first.
    args.out = args.out if args.out.is_absolute() else (PROJECT_ROOT / args.out)
    args.mod = args.mod if args.mod.is_absolute() else (PROJECT_ROOT / args.mod)
    if args.file is not None and not args.file.is_absolute():
        args.file = (PROJECT_ROOT / args.file).resolve()

    try:
        if args.action == "inspect":
            result = {
                "texture": lambda: inspect_texture(args.asset),
                "model": lambda: inspect_model(args.asset, args.texture),
                "model-texture": lambda: inspect_model(args.asset, args.texture),
                "audio": lambda: inspect_audio(args.asset),
                "layout": lambda: inspect_layout(args.asset),
                "map": lambda: inspect_map(args.asset),
            }[args.family]()
        elif args.action == "export":
            result = {
                "texture": lambda: export_texture(args.asset, args.out),
                "model": lambda: export_model(args.asset, args.out),
                "model-texture": lambda: export_model(args.asset, args.out),
                "audio": lambda: export_audio(args.asset, args.out),
                "layout": lambda: export_layout(args.asset, args.out),
                "map": lambda: export_map(args.asset, args.out),
            }[args.family]()
        else:
            if args.family == "texture":
                result = replace_texture(args.asset, args.file, args.stage, args.preview,
                                         args.allow_resize, args.mod)
            elif args.family == "model":
                result = replace_model_geometry(args.asset, args.file, args.indices,
                                                args.stage, args.preview, args.mod)
            elif args.family == "model-texture":
                if not args.texture:
                    ap.error("--texture is required to replace a model texture")
                result = replace_model_texture(args.asset, args.texture, args.file, args.stage,
                                               args.preview, args.allow_resize, args.mod)
            elif args.family == "audio":
                result = replace_audio(args.asset, args.file, args.codec, args.stage,
                                       args.preview, args.mod)
            elif args.family == "layout":
                result = replace_layout(args.asset, args.file, args.stage, args.preview, args.mod)
            else:
                result = replace_map(args.asset, args.file, args.stage, args.preview, args.mod)
    except FamilyError as exc:
        result = _report(False, args.family, args.action, error=str(exc))
    except (OSError, ValueError, KeyError) as exc:
        result = _report(False, args.family, args.action, error=f"{type(exc).__name__}: {exc}")

    for warning in result.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    if result.get("error"):
        print(f"error: {result['error']}", file=sys.stderr)
    if result.get("staged"):
        print(f"staged {result['staged']['mod_file']}")
    if result.get("preview"):
        print(f"preview {result['preview']}")
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
