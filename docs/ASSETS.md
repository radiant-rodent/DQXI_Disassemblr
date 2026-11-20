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
| Images packed in BCH (UI, 2D mode, 2D battle) | PNG + `.meta.json` in named packs | `tools/export_bch_assets.py` |
| Animations in BCH (motions, cutscenes, cameras) | JSON keyframe curves (`game_assets/animations/`) | `tools/export_bch_assets.py` (needs `tools/spica_ref`) |
| 2D-mode maps and objects | rendered PNG (`2d_maps`) + `scene2d.json` | `tools/map2d.py export` |

**BCH files are split by content.** Only 4,779 of the 10,542 BCH files hold meshes (`--models`). The rest:
3,773 image-only files (UI icons and art, 2D sprites and tile sheets, 2D battle graphics, effect sheets) and 1,999
animation files (1,989 animation-only, 10 with images too), plus one shader container (`syscmn/shader.bch`, 36
compiled GPU shaders, no standard format). `tools/export_bch_assets.py` exports all of them and writes
`game_assets/bch_index.json` (kind, contents and outputs of every BCH), which `tools/progress.py` counts from.

Image packs (the Textures panel groups by the first folder below `game_assets/textures/` or `.../ui/`):
`ui/<folder>` (joins the UI pack of that name: `item`, `tutorial`, `story`, `dive`, `location`, `training`,
`credit`, `common_2d`), `2d_sprites`, `2d_tilesets`, `2d_maps`, `2d_battle_enemies`, `2d_battle_backgrounds`,
`2d_battle_effects`, `2d_battle_enemy_anims`, `2d_battle_common`, `2d_effects`, `2d_weather`, `2d_common`,
`misc_bch`. Animations: `animations/motions/<set>.json` (one file per `3d/motion/<set>`, each BCH of the set under
`files`), `animations/cutscenes/<kind>/[<scene>/]<shot>.json`, `animations/battle/`, `animations/misc/`. Each
animation lists its frames, looping flag and per-target curves (`keys` = `[frame, value]` or
`[frame, value, in-slope, out-slope]`; defaults omitted, floats rounded to 5 decimals) or per-frame quaternion /
matrix / bool tracks. The JSON is ~2.3x the binary size (911 MB for 394 MB of BCH).

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
DccMaya/SoftImage/3dsMax formula) and its sampler wrap (`"wrap"`, per unit `[U, V]`). Wrap
matters: the mirrored half of a face (and of most bodies and hair) uses negative U and the eye
atlas wraps U with Mirror, so both eyes read the same cell, flipped. Read with Repeat, the second
eye lands in the atlas's opposite column, a different eye/brow. Ordinary draws carry the wrap
as `dqxi_wrap <u> <v>` in the MTL and as glTF samplers; the viewer sets GL wrap from it. About 120 face draws default to a translated eye or mouth
cell; ordinary draws get their unit-0 transform baked into the exported UVs.

### Hand poses and other hidden parts

Characters carry several hand meshes per side (`L_Hand01_MS` ... `L_Hand05_MS`, open hand, fist,
grip...) and the game shows one at a time. All are flagged visible in the model file; the motion
files that animate them start with `01` shown and the others hidden, so the exporter marks
numbered variants above `01` as hidden: `dqxi_hidden 1` in the MTL, `extras.dqxi_hidden` on the
glTF node. They stay in the files (editing round-trips); the viewer's "Hand variants" checkbox
shows them, and Open in Blender imports them hidden.

Expressions are texture-coordinate animations in `game_data/packs/3d/motion/`: unit 0 slides the
eye atlas, unit 1 the mouth atlas. `python -m tools.face_expressions scan` catalogues all of them
into `game_assets/models/face_expressions.json` (2,855 animations, 185 distinct eye/mouth poses),
and `bake` writes a model's face for any pose:

```powershell
python -m tools.face_expressions bake game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch `
    --eyes 0,0.797 --mouth 0,0.75 --out face.png
```

### Skeletal animation: pose rules and which clips fit which rig

DQXI motions are authored on a *reduced* skeleton. Evaluating them on the model's full bone hierarchy
(what SPICA's DAE exporter and our viewer did before) floats heads on sticks and detaches arms. The
rules, verified by rendering own-family clips (hero `pc001_*`, monster `m043_*`) against the bind pose:

1. An animated bone's transform is relative to its nearest **animated** ancestor; bones without a
   track in between (shoulders, clavicles, thighs, extra spine segments) are skipped.
2. Those untracked in-between bones keep their rest offset from their parent and **rotate like aim
   constraints** so their animated children land where the clip puts them (the hero's arm sits exactly
   one rest shoulder length from the shoulder joint, in a new direction).
3. An axis a track does not key keeps the bone's rest value, taken relative to the effective parent of
   rule 1 (`Pose.Decompose` of bind(bone) · bind(parent)⁻¹).

`tools/spica_ref/Compat.cs` (`Compat.MakePlan` / `Compat.Evaluate`) implements this once; `SpicaRef rig`
(viewer), `SpicaRef gltf` (Blender) and the compatibility test all use it. Debug aids:
`SpicaRef posedobj <model> <anim.bch> <index> <frame> out.obj` (env `DQXI_POSE=plain` for the old
evaluation), `compatdiag`, `chan`.

Which clips work on which rig is in `game_assets/animations/compat.json` (4,127 models, grouped into
distinct skeletons; per skeleton: motion set → `"*"` or the working clip names; `cs/<path>` keys are
cutscene or model files with embedded clips). `SpicaRef compat` poses every skeleton with every clip whose
tracks are ≥ 90 % its bones (2.8 M pairs, ~4 min) and compares against the clip's *reference rig* (the one
it fits best, normally its own family): a clip works when its skinned bone segments keep their lengths as
well as on the reference (Δ ≤ 0.15) and limbs and animated bone orientations point within 20° of the
reference pose. Own-family clips legitimately stretch (squash, weapons, props), so nothing is judged
against zero. The viewer's animation row lists only the sets and clips from this table.

```powershell
python tools/anim_compat.py lists      # after SpicaRef skeletons build/anim_compat/list.txt ...
tools/spica_ref/bin/Release/net9.0/SpicaRef.exe compat build/anim_compat/models.txt `
    build/anim_compat/animfiles.txt build/anim_compat/compat_full.json
python tools/anim_compat.py write      # -> game_assets/animations/compat.json
```

### Rigged models for Blender

`python tools/export_glb.py <model>` (or Models → animation row → **Rigged → Blender**) writes
`game_assets/blender/<model>.glb`: the game's joints as an armature, one vertex group per joint on every
mesh (Weight Paint mode), textures, and the working clips as actions named `<set>/<clip>` (own family
sets, one outfit variant each, by default; `--sets`, `--all`, `--cutscenes`, `--list`). The hero's
default export is 820 clips / 52 MB. Textures are the raw SPICA ones: the layered face (eye/mouth atlas
cells) is not baked yet, so the mouth shows as a dark atlas cell. Alternate hand meshes import hidden (`dqxi_hidden`), outline
shells are left out unless `--outlines`. The viewer's animation cache is `build/rig_cache/*__v2.bin`;
bump `RIG_CACHE_VERSION` in `model_anim.rs` when `SpicaRef rig` output changes.

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

`python -m tools.build_model_names` writes `game_assets/models/model_names.json`
(model id -> English name) and `game_assets/maps/area_names.json` (area code -> place name):

- monsters from `enemy_base`;
- weapons and other equipment from `syscmn/item`: `+0x24` holds the field and battle model rows of
  `res_model3d`, the low byte of `+0x28` the colour variant (`a`, `b`, `c`, ...). Example: item
  "Flametang boomerang" -> `w1003b` (field) and `w1603b` (battle);
- places from `syscmn/level_area` (`b001` = Heliodor Castle, `f001` = Heliodor, ...).

English text comes from the read-only translation workspace when present, otherwise the Japanese
name is used. The viewer shows these names in the model list and the Maps section.

### Texture audit

`python -m tools.audit_model_textures` checks every BCH texture pixel by pixel against the SPICA
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
`python -m tools.squirrel_decompile --all` (one script: `python -m tools.squirrel_decompile
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

Both files are editable. The readable source is compiled by `tools/script_build.py` (unchanged
functions are copied byte-for-byte from retail; see [SCRIPTS.md](SCRIPTS.md)); the assembly listing
is the bit-exact tier. The viewer's Scripts section shows the readable view by default with a
Squirrel source / Assembly listing toggle; `tools/verify_assets.py` and the viewers skip
`*.decompiled.nut` when counting scripts.

## Round-trip tools

The editor-facing entry point is `tools/asset_replace.py`; it validates the edit, chooses the
original 3DS format, writes a preview and stages the containing PACK into `mod/romfs/`. Each
family also keeps its lower-level tool for scripting.

- all families: `python -m tools.asset_replace inspect|export|replace --family texture|model|model-texture|audio|layout|map ...`
- textures: `python -m tools.texture_tool rebuild PNG --orig BFLIM --out OUT.bflim`
- BCH model textures: `python -m tools.bch_texture_patch --bch model.bch --texture NAME --png new.png --out patched.bch`
- audio: `python -m tools.bcstm_encode --template original.bcstm --wav new.wav --out patched.bcstm --codec dspadpcm`
- DSP-ADPCM codec: `tools/dspadpcm_encode.py` (encoder + frame layout documented in its docstring)
- SARC archives: `tools/sarc_tool.py` (same-size in-place patch is byte-identical; a size-changing rebuild keeps every member and closes retail alignment gaps)
- layouts: `python -m tools.layout_tool rebuild JSON --out out.bflyt` (pane transforms and
  same-capacity text are written back into the raw sections)
- scripts: `tools/sqbin.py` has both binary and text assembly support (decompiled view is
  read-only; see [Scripts](#scripts))
- tables: string-table JSON round-trips through `Bxon.build_from_json`; a general semantic
  object-graph writer is still planned
- levels: `tools/patch_game.py` / the editor's **Save to mod**

`tools/texture_tool.encode_tiled` / `decode_tiled` cover every uncompressed PICA format exactly;
`tools/bch_texture_patch.py` now handles all of them, not only ETC1. The BCH texture round-trip is
byte-identical for RGB565/RGBA4/RGBA8/L8/…; ETC1 and ETC1A4 are re-encoded and therefore close,
not identical. See `tests/test_asset_replace.py` for the per-family evidence.

## Re-running one family

```powershell
python -m tools.convert_assets --textures
python -m tools.convert_assets --models --workers 12   # processes, ~135 s on 12 cores
python -m tools.convert_assets --audio --workers 6
python tools/export_bch_assets.py      # images + animations of every mesh-less BCH, ~5 min
python tools/map2d.py export           # 2D maps + 2D objects
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
python -m tools.bxon_patch project.json --out patched.bxon
```

This preserves the object graph and file size. String-table JSON can be rebuilt bit-identically;
a general semantic object-graph writer is still future work.

## Model position editing

`tools/model_tool.py` now exports OBJ vertices with round-trip float formatting. To edit a model:

```powershell
python -m tools.model_tool convert path\to\model.bch --out game_assets\models_edit
# edit the .obj in Blender/any editor, keep vertex order and count
python -m tools.model_patch original.bch edited.obj --out patched.bch
python -m tools.patch_asset --pack 3d/model/name.pack --member name.bch --replacement patched.bch
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

- material colour: `python -m tools.model_material model.bch --material 0 --rgba 255,128,64,255 --out patched.bch`
- topology: `python -m tools.model_patch model.bch edited.obj --indices --out patched.bch`
