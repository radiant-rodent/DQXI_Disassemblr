# BCH models: growing and replacing geometry (CL3)

## What is proven

`tools/bch_writer.py` (`draw_calls`, `reloc_entries`, `grow_draw`) replaces the vertex and index buffers of **one draw call** of a retail BCH with buffers of **any size**.

Format facts used (checked on `3d/bg/b002_105a/b002_105a.bch`, 27 draws):

* Header (`BCH\0`, `<4sBBH6I6I`): section offsets `hdr, str, cmd, data, data_ext, reloc` then their lengths. Sections follow in that order; here `data_ext` is empty and starts where the relocation table starts.
* A draw is a PICA command sequence in the command section: **0x203** = vertex buffer address, **0x227** = index buffer address, **0x228** = index count, **0x205** carries the vertex stride in bits 16-23, **0x22F** = draw. The command words are `[parameter, header]` pairs (header: register in bits 0-15, extra count in bits 20-30, bit 31 = consecutive).
* The address words store **section-relative offsets** into the raw-data section; the relocation table (one u32 per entry: bits 0-24 pointer location >> 2 in the *source* section (bits 29-31), bits 25-28 target section) says which words get the section base added at load time. Target 6 = vertex data, 7 = 16-bit index data, 8 = 8-bit index data. So the width of an index buffer is a property of the **relocation entry**, not of the command word.
* Vertex position = three floats at the start of each vertex (`model_patch.py` relies on it).

`grow_draw(bch, draw, vbo, indices)`: appends the new vertex buffer and index list to the end of the raw-data section (4-byte aligned), rewrites the three command words, retargets the index relocation to section 7 when 8-bit indices no longer suffice, and moves `data_ext_off` / `reloc_off` and grows `data_len` in the header.

## Emulator proof

The first draw of the house (754 vertices, 1,356 indices) replaced by itself plus a copy lifted by +3.5 in y (1,508 vertices, 2,712 indices, file 192,432 -> 240,080 bytes), written into a cloned level slot (`tools/new_map.py`, `patch_asset.rebuild_pack`) and entered in the game: the room renders normally and the lifted copy of the wall shell is visible as extra beams and walls above the room (`out/emu/probe/take_46116`). The parser (`BchParser`) reads the grown file back with the new counts and the same 27 meshes.

## Not yet

* **A new draw call** (a new mesh with its own material, instead of growing an existing draw): needs a copy of the command sequence for a draw, a new entry in the mesh / sub-mesh tables of the content section and its relocations.
* **New materials and textures** (texture conversion to PICA formats, material blocks).
* **An OBJ importer that handles several materials, UVs and normals** (see below for what `tools/model_import.py` does today).
* Matching **collision** (`tools/rcb_tool.py`) for new geometry.
* The Models panel "Import model..." button.

## PROVEN: OBJ import (`tools/model_import.py`)

`python -m tools.model_import model.bch room.obj --draw 0 --out new.bch` replaces draw N with the OBJ mesh: positions from the OBJ (three floats at the start of each vertex record), polygons fanned into triangles, every other attribute of a vertex (normal, UV, colour) copied from the **nearest original vertex** of that draw, so the draw keeps its material / texture / vertex format. Emulator: an 8-vertex, 12-triangle box (`out/coltest/box.obj`, 4 x 4 x 6) imported over the first draw of the house (the shell, 754 vertices) and entered through a cloned slot: a large wooden-textured block stands in the room (`out/emu/probe/take_46228`), the other 26 meshes unchanged. Limits: one draw per import; UVs / normals come from the nearest original vertex rather than from the OBJ (textures look stretched on new shapes); no new material or texture yet; at most 65,535 vertices per draw; collision (`rcb_tool`) must be updated by hand.

## PROVEN: texture coordinates from the OBJ

`BchParser` now keeps each draw's vertex layout (`MeshGeometry.layout`: PICA semantic, format, elements, scale, byte offset; e.g. the house shell: position 3 floats @0, UV0 2 floats @12, normal 3 bytes @20, colour 4 bytes @23 with scale 1/127, stride 28). `tools/model_import.py` reads `vt` / `vn`, builds one vertex per distinct (v, vt, vn) corner and writes the UV in the draw's own format (floats, scaled shorts or bytes). Emulator: the box with per-face 0..1 UVs (`out/coltest/box_uv.obj`) renders with the wood texture mapped by those UVs, visibly different from the nearest-vertex version (`out/emu/probe/take_46420`). Normals are written only when the draw's byte-normal scale is known (here the scale was not recovered, so the nearest original normal is kept); vertex colours come from the nearest original vertex.

## End-to-end: a hand-written room entered through a church exit (emulator)

`out/coltest/room.obj` (floor + four walls, 10 x 8 x 3, 20 vertices, UVs from the OBJ) -> `python -m tools.model_import b002_105a.bch room.obj --draw 0 --out room.bch` -> `tools/new_map.py` clone into the slot `b002_106a` with that model -> church exit (+0x68 record) set to map id 114 -> in the game the church door leads to the cloned house whose shell draw is now the OBJ room (`out/emu/probe/take_46572`): the new walls and floor show with the wood texture, the other 26 house meshes stay. Collision was not touched (the old house collision still applies). What is left for a finished custom room: a whole-scene import (every draw, not one), new materials / textures, matching collision, NPCs / chests placed through the Level Editor (already possible).

## Normals from the OBJ (written now)

Signed-byte normals (`format 0`, 3 elements) store a unit vector as `n * 127`: the decoded layout reports scale 1.0 because the vertex-shader uniform that would carry it is not recovered, but the raw bytes of the house shell are values like (-1, 0, 127) and (127, 0, 0). `tools/model_import.py` therefore writes `vn` as `round(n * 127)` for such draws (other formats use the draw's own scale). Emulator: the box with per-face normals (`out/coltest/box_n.bch`) renders with a lit top face and a darker front face, no corruption (`out/emu/probe/take_94529`). Vertex colours still come from the nearest original vertex.

## Whole-scene import (several draws from one OBJ)

`python -m tools.model_import model.bch scene.obj --out new.bch` (no `--draw`) maps every OBJ group named `draw<N>` (or `<N>_name`) to draw N and replaces each in turn (`import_scene`); `--draw N` still replaces one draw with the whole OBJ. Each import re-reads the draw table, which stays valid because only the data section grows. Emulator: `out/coltest/scene.obj` (a floor quad as `o draw0`, a wall panel as `o draw1`) over the house's first two draws, entered through the cloned slot: loads without corruption, the original shell is gone and the panel stands where draw 1 was (`out/emu/probe/take_94634`). Group names must be written by the author (the draw numbers are the order of `bch_writer list`); automatic splitting by material is not done.

## All 27 draws replaced (`out/coltest/full_room.obj`)

`o draw0` is the room (floor + back, left and right walls) and `o draw1..draw26` are one tiny triangle each far below the floor; `import_scene` writes all 27 draws (195,068 bytes) and the cloned slot, entered through the church exit, shows only the custom room: wood-textured floor and three walls, black void elsewhere, the hero and the level's NPCs / props standing in it (`out/emu/probe/take_94819`). So a retail background can be replaced completely by authored geometry. The wall collision generated for it (`open_chit.rcb`) was loaded in the same run; the camera view after walking left does not show the hero clearly enough to call it a clean collision proof.

## PROVEN: a custom texture on a custom room

`python tools/bch_texture_patch.py --bch full_room.bch --texture tj_b002_wood01 --png checker.png --out full_room_tex.bch` re-encodes a PNG (32 x 64, blue / yellow checkerboard) to the texture's own format (ETC1, same size) over the model's wood texture (the one draws 0 and 1 use; `--list` shows all embedded textures). Cloned slot + church exit: the custom room's floor and walls show the checkerboard in the game, the hero standing in it (`out/emu/probe/take_95017`). Limits: the texture keeps its original size and format (ETC1 is lossy, only the base mip level is replaced); a **new** material (a texture the model does not already contain, with its own material block) is still not possible. Workaround for a custom look: author the room's UVs onto an existing texture slot and replace that texture.
