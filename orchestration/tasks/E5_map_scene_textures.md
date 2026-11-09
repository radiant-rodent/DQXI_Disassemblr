---
lane: argon
after: K2_misname_sweep
---

# E5_map_scene_textures - show a map's 3D scenery textures in the editor

In DQXI Studio (`viewer_rs/`), Maps -> a map -> Textures lists only the minimap/screenshot
textures (`game_assets/textures/arcs/ui/map/<area>_2d|_3d/`). The textures of the map's 3D
scenery (walls, ground, props) live inside the background BCH
(`scene.json` -> `background_bch`, e.g. `game_data/packs/3d/bg/b001_101a/b001_101a.bch`) and
are never exported, so a modder cannot see or replace them from the map.

Owns: `tools/map_textures.py` (new), `game_assets/textures/maps/**` (generated),
`viewer_rs/src/data/areas.rs`, `viewer_rs/src/data/textures.rs`,
`viewer_rs/src/ui/panels/maps.rs`, `tests/test_map_textures.py` (new), `tools/regen_all.ps1`
(one line), `docs/ASSETS.md` (a short section), done report, AGENT_LOG.md.

## Steps

1. `tools/map_textures.py export [--map ID] [--all]`: for each map's background BCH, decode every
   texture with the existing decoder in `tools/bch_texture_patch.py` (`texture_infos`, PICA200
   formats) and write `game_assets/textures/maps/<map>/<texture>.png` + `.meta.json`
   (width, height, format_name, source bch, texture name). Skip unchanged outputs (fast reruns).
   Add it to `tools/regen_all.ps1`.
2. Editor: the texture index already groups by the first folder below `arcs/ui/map/maps/`
   (`pack_of_rel` in `data/textures.rs`), so `maps/<map>/` becomes pack `<map>` and the Maps panel
   matches it. Verify that, and label these as "scene" vs "minimap" textures in the Maps texture
   tab. Replacing one should go through the existing BCH replace path
   (`tools/asset_replace.py replace --family model-texture` / `bch_texture_patch.py`); wire the
   tab's replace action to it if the textures panel does not already handle the family.
3. Tests: python test exporting one map (count = number of textures in its BCH, PNG sizes match
   the infos); a Rust test that `b001_101a` gets scene textures. Run
   `cargo test --manifest-path viewer_rs/Cargo.toml` and the python test.

## Done when

- Maps -> b001_101a -> Textures shows its scene textures (state how many) next to the minimap ones.
- `cargo test` and the new python test pass; `python tools/build.py` still prints the bit-match
  PASS (you do not touch code, but confirm). Do not rebuild the release exe if it is locked by a
  running editor; say so.
