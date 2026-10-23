# Assets

## Source of truth

`game_data/` is the exact extracted game. It is never overwritten by conversion tools.

| Path | Meaning |
|---|---|
| `game_data/romfs/` | byte-for-byte RomFS files, including original archives |
| `game_data/packs/` | every PACK/PACA entry, using the name stored in the archive |
| `game_data/arcs/` | every SARC entry (`bflyt`, `bflan`, `bflim`) |
| `game_data/manifest.json` | counts, per-file records, archive records |
| `audit/pack_manifest.json` | source archive inventory |
| `audit/pack_members.jsonl` | flat member inventory |

## Standard formats

| Family | Output | Tool |
|---|---|---|
| Textures | PNG + `.meta.json` | `tools/convert_assets.py --textures` |
| Models | glTF 2.0, OBJ, MTL, embedded PNG | `--models` |
| Layouts | JSON (panes, textures, raw sections) | `--layouts` |
| Scripts | Squirrel disassembly `.nut` + read-only `script.decompiled.nut` | `--scripts`, then `tools/squirrel_decompile.py --all` |
| Tables | structural JSON | `--tables` |
| Audio | 16-bit PCM WAV | `--audio` |
| Maps | `scene.json` + `structure.json` | `tools/map_tool.py export` |

Each family writes a `*_summary.json` with output count and errors. A non-zero error list is a
real failure; fix it rather than ignoring it.

## Models

Only BCH files that expose mesh data produce model outputs. Many of the 10,542 BCH files are
texture-only/2D backgrounds, animation rigs, or empty resources. `game_assets/models_summary.json`
records the source/output relationship; the source path is preserved in the output tree.

Textures embedded in BCH files are decoded next to the model. The extracted BFLIM library is
separate because UI packs and model packs are different sources.

BCH textures use every PICA200 format: ETC1/ETC1A4 for most, but also RGB565, RGBA5551, RGBA4,
RGBA8, RGB8, LA8, LA4, L8, A8, L4, A4 and HiLo8. `tools/texture_tool.decode_tiled` decodes all
of them; the format comes from the texture header (byte `+0x18`). Some textures live in the BCH
"RawExt" section rather than "RawData"; the parser resolves the relocation table with SPICA's full
section list, so texture and buffer addresses are absolute file offsets.

Exported glTF files store `1 - v` texture coordinates (glTF's UV origin is top-left; BCH and OBJ
use bottom-left). Import either the `.gltf` or the `.obj`; both show textures the right way up.

### Bone placement (faces, eyes, props)

Draws are skinned three ways. *Smooth* draws are stored in model space. *Rigid* and unskinned
draws are stored relative to a bone: a character's face and eyes sit on the head bone, map lamps
and decals on their own bones. Without applying the bone's world matrix they all land at the
origin (faces at the character's feet). The exporter applies SPICA's rule: each vertex is moved by
the world matrix of `palette[BoneIndex]`, taken from `game_assets/models/skin_map.json.gz`.
`tools/model_patch.py` applies the inverse when writing edits back, so edits made on the placed
model land where you made them.

### Layered character faces

Face materials combine up to three textures on the GPU, most often
`colour = (Texture0(UV0) + Texture1(UV1)) * Texture2(UV2)`-style recipes: eye and mouth cells from
an atlas with a black background, added onto the skin texture (the game animates which atlas cells
show). There are several recipes (Add/AddMult, Add/Modulate with a reflection map, MultAdd for
gold faces, swapped units). An OBJ/glTF material has one diffuse texture, so the exporter evaluates the first two combiner
stages (`"tev"` in `material_map.json.gz`) per texel and bakes the result into
`<skin>_composite.png`. Lighting and constant colours count as white, reflection maps as neutral.
The skin unit is the texture named `*_face`, or (monsters, `m135a_01_high`) the one the second
stage multiplies in.

The skin UVs of a face overlap 2.4-5x (one skin patch serves many triangles; the eye and mouth
detail comes only from UV0/UV1), so the bake cannot reuse them: overlapping triangles would
overwrite each other and smear the eyes. Instead every face triangle gets its own spot in the
composite, laid out by its 3D shape and shelf-packed with padding. The OBJ addresses it with
per-corner `vt` indices, so `v` lines and their order stay exactly as in the BCH (model_patch
still lines up); glTF gets an unwelded copy of those meshes.

Each unit is sampled through the material's texture-coordinate transform (`"uv_coords"`, SPICA's
DccMaya/SoftImage/3dsMax formula). About 120 face draws default to a translated eye or mouth
cell; ordinary draws get their unit-0 transform baked into the exported UVs.

### Hand poses and other hidden parts

Characters carry several hand meshes per side (`L_Hand01_MS` ... `L_Hand05_MS`, open hand, fist,
grip...) and the game shows one at a time. All are flagged visible in the model file; the motion
files that animate them start with `01` shown and the others hidden, so the exporter marks
numbered variants above `01` as hidden: `dqxi_hidden 1` in the MTL, `extras.dqxi_hidden` on the
glTF node. They stay in the files (editing round-trips); the viewer's "Hand variants" checkbox
shows them, and Open in Blender imports them hidden.

Expressions are texture-coordinate animations in `game_data/packs/3d/motion/`: unit 0 slides the
eye atlas, unit 1 the mouth atlas. `python tools/face_expressions.py scan` catalogues all of them
into `game_assets/models/face_expressions.json` (2,855 animations, 185 distinct eye/mouth poses),
and `bake` writes a model's face for any pose:

```powershell
python tools/face_expressions.py bake game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch `
    --eyes 0,0.797 --mouth 0,0.75 --out face.png
```

### Transparency and blending

`material_map.json.gz` also stores each draw's blend function (`"blend"`), alpha test
(`"alpha_test"`, e.g. `Greater,128`) and alpha combiner (`"tev_alpha"`). The exporter maps them to

| game blend (src, dst) | export | typical use |
| --- | --- | --- |
| `One,Zero` | opaque (with alpha test: cut-out) | walls, foliage cards |
| `SourceAlpha,OneMinusSourceAlpha` | `alpha` | glass, hair tips |
| `SourceAlpha,One` | `additive` | mist, glow, light shafts (black = invisible) |
| `DestinationColor,Zero` | `multiply` | shadow and dirt decals |

The MTL carries `dqxi_blend <mode>` and `dqxi_alpha_cutoff <0..1>` (plus `map_d` for alpha);
glTF uses `alphaMode` MASK/BLEND and `extras.dqxi_blend`, since glTF has no additive mode.
About 23k draws are alpha-tested, 10k additive and 5k alpha-blended.

**Which texture, and masks.** The exported diffuse is the texture the *colour* combiner samples
through its UVs (`"tev_color_ops"`; environment/projection-mapped units skipped, reflection-named
ones only as a last resort), read through that unit's UV set and texture transform. Terrain decals
often take their transparency from a second texture's channel instead (`"tev_alpha_ops"`, e.g.
`Texture0:Red` on a black/white `*_nuki*` mask, `OneMinusRed` for smoke). Those draws export the
mask too: `dqxi_mask_map` / `dqxi_mask_channel` in the MTL plus per-vertex `dqxi_vt_mask` UVs in the
OBJ, and `TEXCOORD_1` + `extras.dqxi_mask` in glTF; the viewer multiplies the channel into alpha.
Blended draws whose alpha combiner reads vertex alpha (`PrimaryColor:Alpha`: mist, cloud and water
overlays fading at their edges) export it per vertex: `dqxi_va` lines in the OBJ, `COLOR_0` (white,
alpha = fade) in glTF. Draws whose colour combiner reads vertex RGB (baked map lighting; usually
stage 1 scaled x2) export `min(rgb * stage0_scale, 1)` per vertex (`dqxi_vc`) and the stage-1
scale per material (`dqxi_color_scale`); the viewer draws them as `clamp(texture * rgb * scale)`
without its own shading, glTF gets the clamped product in `COLOR_0`.

### In-game names

`python tools/build_model_names.py` writes `game_assets/models/model_names.json`
(model id -> English name) and `game_assets/maps/area_names.json` (area code -> place name):

- monsters from `enemy_base`;
- weapons and other equipment from `syscmn/item`: `+0x24` holds the field and battle model rows of
  `res_model3d`, the low byte of `+0x28` the colour variant (`a`, `b`, `c`, ...). Example: item
  "Flametang boomerang" -> `w1003b` (field) and `w1603b` (battle);
- places from `syscmn/level_area` (`b001` = Heliodor Castle, `f001` = Heliodor, ...).

English text comes from the read-only translation workspace when present, otherwise the Japanese
name is used. The viewer shows these names in the model list and the Maps section.

### Texture audit

`python tools/audit_model_textures.py` checks every BCH texture pixel by pixel against the SPICA
reference reader, checks the PNGs next to every exported model, and checks material assignments.
The report is `audit/MODEL_TEXTURE_AUDIT.json`. `--dump` rebuilds `tools/spica_ref` and the
reference images first (needs the .NET 9 SDK).

## Tables

`game_assets/tables/` is a structural decode. It is more useful than the old strings-only JSON,
but field names are path-based (`+0x04`, `$array`, `count`, `element_size`) because the original
schema is not stored in BXON. Treat it as an editable data graph, not as a hand-authored schema.

The Level3D/Level2D/LevelDMap tables are exported under `game_assets/maps/` instead, because
they are level data rather than parameter databases.

## Scripts

`game_assets/scripts/packs/script/<name>/script.nut` is the disassembly of `script.cnut`: literals,
locals, line info and one `[pc] OPCODE a b c d` line per instruction. It round-trips byte for byte
through `tools/sqbin.py` and is the file you edit.

`script.decompiled.nut` beside it is readable pseudo-source written by
`python tools/squirrel_decompile.py --all` (one script: `python tools/squirrel_decompile.py
game_data/packs/script/a_000/script.cnut`). The scripts use Squirrel 2.2 bytecode, so the
decompiler matches the 2.2 compiler's patterns: it rebuilds expressions from register writes
(calls, member access, arithmetic, comparisons, `&&`/`||`, `?:`, table literals with their
functions), names locals from the local-variable info, and structures if/else, while/for,
switch, break/continue and return. A bare name such as `WaitFrame(30)` means `this.WaitFrame`;
`delegate a : b` is 2.2 syntax. Anything it cannot structure is printed as an `ASM FALLBACK`
comment block holding the raw instructions (pc numbers match `script.nut`), and `$rN` names a
VM register it could not express, so the output is never wrong, only less pretty. Today all
769 scripts (8,960 functions) structure fully with no fallback block; the per-opcode coverage
is in `audit/SCRIPT_DECOMPILE.md` / `.json`.

The decompiled file is **read-only**: there is no compiler back to bytecode, so edit
`script.nut`. The viewer's Scripts section shows the decompiled view by default with a
Decompiled / Disassembly toggle; `tools/verify_assets.py` and the viewers skip
`*.decompiled.nut` when counting scripts.

## Round-trip tools

- textures: `python tools/texture_tool.py rebuild PNG --orig BFLIM --out OUT.bflim`
- BCH model textures: `python tools/bch_texture_patch.py --bch model.bch --texture NAME --png new.png --out patched.bch`
- audio: `python tools/bcstm_encode.py --template original.bcstm --wav new.wav --out patched.bcstm`
- layouts: `python tools/layout_tool.py rebuild JSON --out out.bflyt`
- scripts: `tools/sqbin.py` has both binary and text assembly support (decompiled view is
  read-only; see [Scripts](#scripts))
- tables: string-table JSON round-trips through `Bxon.build_from_json`; a general semantic
  object-graph writer is still planned
- levels: `tools/patch_game.py`

## Re-running one family

```powershell
python tools/convert_assets.py --textures
python tools/convert_assets.py --models --workers 12   # processes, ~135 s on 12 cores
python tools/convert_assets.py --audio --workers 6
```

Heavy conversions are safe to re-run; outputs are replaced per source file.

## Same-size table edits

For now, table edits use exact byte offsets from the structural JSON:

```json
{
  "source": "game_data/packs/gamecmn/achievement.bxon",
  "edits": [
    {"offset": "0x1234", "type": "u32", "value": 42},
    {"offset": "0x1238", "type": "f32", "value": 1.5}
  ]
}
```

```powershell
python tools/bxon_patch.py project.json --out patched.bxon
```

This preserves the object graph and file size. String-table JSON can be rebuilt bit-identically;
a general semantic object-graph writer is still future work.

## Model position editing

`tools/model_tool.py` now exports OBJ vertices with round-trip float formatting. To edit a model:

```powershell
python tools/model_tool.py convert path\to\model.bch --out game_assets\models_edit
# edit the .obj in Blender/any editor, keep vertex order and count
python tools/model_patch.py original.bch edited.obj --out patched.bch
python tools/patch_asset.py --pack 3d/model/name.pack --member name.bch --replacement patched.bch
```

`model_patch` writes edited OBJ vertex positions or triangle indices back into the original BCH in
place. Topology edits must keep the same vertex/index counts; materials, textures, normals, UVs
and every buffer offset are preserved. A no-op OBJ edit is byte-identical to the original BCH,
including layered duplicate meshes. Bone-placed draws are moved back into bone space for you, so
edit the exported model as it looks.

## Texture assignment in exported models

Every embedded BCH texture is written next to the model, and every mesh is mapped to its real
material texture. The exporter resolves the BCH relocation table, then walks the inline model
mesh table (including per-mesh submesh counts) to obtain each draw's material index. Material
entries provide a `MaterialName@ModelName` reference; the material name is matched against the
embedded texture names with DQXI-specific normalization (`body` / `body_high` / `Body_high_MT`,
`ko_b001_puddle01` / `ba_b001_puddle01`).

This is a structural mapping, not a texture-list cycle. When a material name has no valid
texture (for example `lambert1` or a shader-only material), that mesh is left untextured instead
of receiving an arbitrary image.

The viewport uses the same data: OBJ `usemtl` groups and UVs are loaded, MTL `map_Kd` images are
uploaded, and each material group is drawn with its own texture.

Static exports collapse exact duplicate geometry. BCH models frequently contain the same quad or
mesh several times for layered effects (torch, fire, light, alpha passes). Those are meaningful in
game but appear as duplicate objects with different textures in Blender/OBJ viewers, so the
exporter keeps the first copy and drops later ones with identical positions and indices.


## Exact material and bone manifests

`game_assets/models/material_map.json.gz` stores, for every extracted BCH path and draw, the
material name and its `Texture0/1/2` names; `skin_map.json.gz` stores each rigid/unskinned draw's
bone palette. Both come from the vendored SPICA reader (`third_party/SPICA`, public domain) via
`tools/spica_ref`:

```powershell
dotnet build tools/spica_ref -c Release
tools/spica_ref/bin/Release/net9.0/SpicaRef.exe materials build/all_bch.txt build/material_map.json .
tools/spica_ref/bin/Release/net9.0/SpicaRef.exe skin      build/all_bch.txt build/skin_map.json .
tools/spica_ref/bin/Release/net9.0/SpicaRef.exe obj       path/to/model.bch reference.obj
```

(`build/all_bch.txt` lists the BCH paths; gzip the JSON into `game_assets/models/`.) Every entry
carries `vbo`/`ibo`, the file offsets of the draw's vertex and index buffers, and the exporter
matches draws on that pair: SPICA's model -> mesh -> submesh order is not always the order of the
draw commands. `obj` writes SPICA's own placement of one model, handy for checking an export.
If a manifest is absent, the structural suffix matcher is used and bone placement is skipped.

- material colour: `python tools/model_material.py model.bch --material 0 --rgba 255,128,64,255 --out patched.bch`
- topology: `python tools/model_patch.py model.bch edited.obj --indices --out patched.bch`
