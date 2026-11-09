---
lane: argon
---
Import brand-new geometry: a BCH writer that is not limited to the original vertex count.

Read first: docs/CUSTOM_LEVEL_PLAN.md (the target scenario and the state of every piece), orchestration/WORKER_RULES.md,
docs/EDITING.md. Existing tools to reuse: tools/level_records.py (duplicate/delete level records, guided decoder),
tools/bxon_struct.py, tools/map_tool.py, tools/asset_replace.py, tools/script_build.py, tools/text_tool.py,
tools/model_patch.py, tools/patch_asset.py. The user's earlier translation project at ../3DS_Translate
(read-only) has the Azahar emulator, tools/emu harness inputs and docs/AGENT_GUIDE.md: use them for every emulator proof.
A package is done only when its proof passes in the emulator (`python tests/emu/run_cases.py <case>`), and the editor
(viewer_rs, cargo build --release and cargo test --release) still builds. Add your case to tests/emu/run_cases.py.

Owns: tools/bch_writer.py, tools/model_import.py, docs/MODEL_IMPORT.md, viewer_rs/src/ui/panels/models.rs (import button only).

tools/model_patch.py can only rewrite vertex positions/indices in place (same counts). A custom room needs real new meshes.

1. Study the BCH layout (third_party/SPICA reads it, tools/model_tool.py decodes it): header, content tables, relocation table, vertex buffers (PICA attribute
   formats), index buffers, submeshes, materials (texture mapper units, TEV stages from the existing material_map), skeleton. The engine also needs
   model-level metadata the retail models carry.
2. tools/bch_writer.py: build a BCH from scratch or by cloning a retail template and replacing meshes, rewriting every pointer/relocation, with
   verification by reading it back with SPICA (tools/spica_ref rig / obj commands) and comparing.
3. tools/model_import.py: import an OBJ/glTF (positions, normals, UVs, vertex colours, materials with textures) into a map-background model; texture
   conversion through tools/texture_tool.py to PICA formats within the 3DS limits (power-of-two sizes, VRAM budget); check the hardware limits
   (vertex counts per draw, bone palette size 20, index range) and report them.
4. Models panel: 'Import model...' that runs it, with a preview of the result.

Proof (emulator case model_import_room): a room built in Blender (more vertices than the original) replaces a retail map background and renders in game
without corruption; a textured version shows its texture.
