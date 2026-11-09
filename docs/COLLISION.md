# Collision (CL2) - where it lives and what is known

Collision is **not** in `level3d.bxon`. Every level has binary files next to its background model in the 3D bg pack:
`game_data/packs/3d/bg/<level>/<level>_chit.rcb`, `_yhit.rcb` and (some levels) `_vhit.rcb`, `_02_chit.rcb` ... 1,213 `.rcb` files in all.
The names read: **chit** = character hit (walls/solid), **yhit** = floor / height, **vhit** = view/camera hit (guess from the suffixes; to be confirmed by perturbing one).

## Header (`rcbl`, 0x54 bytes), from `b002_105a_chit.rcb` (2,916 bytes, the Heliodor church) and `_yhit.rcb` (1,620 bytes)

| offset | value | meaning |
|---|---|---|
| +0x00 | `rcbl` (0x6C626372) | magic |
| +0x04 | 0xB64 / 0x654 | file size |
| +0x08 / +0x0C | 0x3E8 / 0x3EA | format version / flags |
| +0x14 | 0x54 | header size = start of the node table |
| +0x18..0x2C | floats | bounding box min / max (church: (-4, 0, -5) to (5, 3, 5), the nave) |
| +0x30 | 12 / 5 | element count (chit 12, yhit 5; looks like the number of collision shapes) |
| +0x34.. | 0x90000, 4, 0x54 ... | counts and offsets (not decoded) |
| +0x48 / +0x4C | 0xAB8 / 0xAB8 | offset of the string table (file end minus 172 bytes) |

After the header: a node table (`0xFFFF0004, 0x00040002, offset, offset` style headers, each followed by bounding-box floats and
plane-like float groups such as (-0.707, 0.707) normals and 3.0 / -2.5 / 5.0 extents), index lists (`0x00010000 0x02B00002 ...`), then a **string
table** of shape / material names: `kyoton_f03s`, `kyoton_f06s`, `lambert1`, `floorS05`, `Shape5`, `b002_a_asset_car_05Shape`, `pPlane19Shape` ...
(Maya names: the collision was authored as named meshes). So the file is a BVH/octree over named collision meshes.

## Not yet known

The node layout, whether the leaves are triangles or planes, and how to emit a new file. Needed for the proof (`collision_wall`):
move a wall in a known level's `_chit.rcb` and check in the emulator that the player is blocked, then write a generator from a triangle soup.
Next step: diff `_chit.rcb` of two near-identical levels (the `a`/`c` variants of the same area) and perturb one float of the box table in `b002_105a_chit.rcb`
(the church nave, reachable from the Player save start with the fast probe) to see which edge moves.

## Emulator attempts (Player save, Heliodor church, walk right into the nave wall, `tools/emu/level_probe.py build_mod_members`)

The hero stops at the right wall (x about 4.8). The same stop happened with the original files and with `b002_105a_chit.rcb` header count zeroed, its magic zeroed, `_yhit.rcb` count zeroed, and both magics zeroed (all staged as `3d/bg/b002_105a.pack` in the LayeredFS export, which was verified to contain the pack). So **none of those edits changed the game**: either the game does not read the modded `3d/bg` pack for this level in this setup (the level3d pack route does work), or the church collision comes from another source, or the files are read lazily/cached. Open checks, in order: (1) a positive control that the bg pack mod is applied at all (a visible edit of `b002_105a.bch`); (2) whether the church uses `b002_105a` bg at all (the `c` level variant has no bg pack of its own); (3) only then the rcb format.

## Correction and new results (the church is `b002_101a`, not `b002_105a`)

`b002_105a` is a **house** (bookshelf, window; seen in the editor). The Player save's "current area id" is 109 = `b002_101a`, the Heliodor church (bg pack `3d/bg/b002_101a`: `.bch`, `_chit.rcb`, `_yhit.rcb`). Every earlier church test that edited `b002_105a` (the gimmick tests in LEVEL_FORMAT.md and the first rcb tests above) touched the wrong level and is void. Redone on `b002_101a`:

* The bg pack mod **is** loaded: truncating `b002_101a.bch` plus zeroing the rcb magics crashes the game (`unmapped Read16 @ 0x4`, `tools/emu/level_probe.py build_mod_members`).
* Zeroing only the magic of `_chit.rcb`, `_yhit.rcb` or both changes nothing (the magic is not checked).
* **Zeroing the count at `+0x30` of `_chit.rcb` makes the whole church environment disappear** (black scene, the characters still drawn). So `_chit.rcb` is consumed by the background renderer (a chunk / culling table naming the mesh shapes), not only by collision.
* Zeroing the count of `_yhit.rcb` changes nothing visible; the player was still stopped at the right wall in every variant I could see. Wall collision therefore comes from somewhere else (the other `+0x30` data, `_vhit`, or the level3d arrays), or the player stop in the black runs cannot be read because the camera follows the hero. The minimap does not show the interior, so it cannot be used.

Open: where the nave wall blocks the player. Next experiment: restore the renderer data, set the `_yhit.rcb` box (`+0x18..+0x2C`) to a tiny volume and then to a huge one, and use the level3d `+0x178`/`+0x100` arrays (zero their counts one at a time) while walking into a wall in a visible scene.

## CORRECTION (user observation): `_chit.rcb` IS the wall collision

The black scenes of the `chit` and `cy` runs were **not** the renderer losing the church: the hero walked **out through the wall into the void** and the camera followed, so the screen showed empty space. So with the shape count at `+0x30` of `b002_101a_chit.rcb` set to 0, **the walls no longer block the player** (proven in the emulator, user-confirmed by watching the run). The same edit on `_yhit.rcb` changed nothing (floor/height data; the hero kept the same height), and zeroing a file's magic changes nothing. Result:

* `3d/bg/<level>/<level>_chit.rcb` = solid wall / character collision. Header count `+0x30` is the number of collision shapes; 0 disables collision entirely.
* `_yhit.rcb` = floor / height (not shown to block anything).
* Editing these files reaches the game through the normal LayeredFS path (`3d/bg/<level>.pack`), exactly like level3d.

So collision CAN be edited. Still to do: remove only one wall (drop shapes by name), move a wall (the AABB/plane floats), add a wall (generator for new shapes; needs the node format), and surface it in the editor as a collision overlay.

Also tested on `b002_101a_yhit.rcb`: bounding box (`+0x18..+0x2F`) set to all zeros and to +-100: the hero still stops at the nave wall, so the yhit box does not decide wall collision.

## PROVEN: collision can be moved (Heliodor church, `b002_101a_chit.rcb`)

`tools/rcb_tool.py` decodes the file. Header: `+0x30` = shape count (19 in the church), `+0x34` u16 = name count, `+0x48` = string table (an array of name offsets, then the names). Then one **96-byte record per shape** from `0x54`:

| bytes | meaning |
|---|---|
| +0 | `0xFFFF0000 | name index` |
| +4 | `(vertex count << 16) | triangle count` |
| +8 / +12 | offset of the vertex array (12 bytes: x y z floats) / of the triangle array (8 bytes: u16 a, b, c, u16 surface attribute) |
| +16..+95 | 20 floats of bounds: sphere centre (0-2) and radius (3), box min (4-6) and max (7-9), orientation (10-13), oriented-box centre (14-16) and half extents (17-19) |

The decoded vertices match the header bounding box exactly in both test levels. The church has: the floor (attribute 688/691), the left/right/front/back wall pieces (attribute 0, shapes 3-8), the altar steps and the pews (`pCubeShape23..27`, `17`, `24`). 

**Emulator proof:** `translate_shape` on shapes 3 and 7 (the right wall) by -4 in x: the hero walking right now stops about 2 units right of the nave centre, clearly short of the visible wall. Moving only the vertices (first try) made the wall collide **nowhere** (the hero walked out into the void), because the shape's stored bounds stayed behind and the game culls by them: both must move.

Open: dropping a shape (triangle count 0 for one shape), adding a shape (needs new vertex / triangle blocks and a header record, file grows), the floor `_yhit.rcb` (not shown to affect anything), `_vhit.rcb`, and the editor overlay.

## In the editor

Level Editor > Inspector > **Collision** group: pick a shape (it is highlighted in the viewport), set its X/Y/Z offset; **Save to mod** writes `editor_projects/<level>.json` with a `collision: [{shape, delta}]` list, and `tools/asset_replace.py replace_map` applies `rcb_tool.translate_shape` to the original `_chit.rcb` and stages `mod/romfs/3d/bg/<bg>.pack` (checked headless: shapes 3 and 7 of `b002_101a` moved by -4 appear in the staged pack; the same edit made by hand was proven in the emulator). Not yet in the editor: undo for collision moves, deleting / adding / resizing shapes, `_yhit` / `_vhit`.

## PROVEN: one shape can be removed

`rcb_tool.drop_shape` sets a shape's triangle count (low u16 of the word at +4 of its record) to 0. Emulator (Heliodor church, hero walks right at z = -3.5): dropping shape 7 (the wall plane x = 6.5, z -7..0) lets the hero walk out through the wall into the void; dropping shape 3 (the slab x 6..6.5, z 0..8, not in the hero's path) leaves the wall blocking as usual. So shapes are independent and removable one by one. In the editor: select a shape in the Collision group > **Delete shape** (undoable with Restore shape); Save to mod writes the project's `collision: [{shape, delta, drop}]` list and `asset_replace.replace_map` applies moves then drops (checked headless).

## PROVEN: a shape can be added (the file grows)

`rcb_tool.add_box(data, lo, hi)` appends one axis-aligned box: a 96-byte record at the end of the record table, 8 vertices and 12 triangles in front of the string table, every old vertex / triangle / name offset shifted, header count, file size, string-table offsets (+0x48 / +0x4C) and bounding box updated (the file grew from 5,784 to 6,072 bytes). Emulator (Heliodor church): a box x 1.5..2.5, y 0..3, z -5..-2 added in the hero's path: the game loads the larger file without trouble and the hero, walking right from the start, is stopped at the box (near the altar steps) instead of reaching the wall. The new record uses an identity orientation (0, 0, 0, 1), centre and half extents like the retail shapes. In the editor: Inspector > Collision > **Add box** (drag the min / max values; green wireframe), Save to mod writes `collision_boxes` and `asset_replace` appends them (checked headless on the church).

## Collision from an OBJ (`rcb_tool.add_mesh`, `from_obj`)

`add_box` is now a special case of `add_mesh(data, verts, tris)`: any triangle list becomes one new collision shape (96-byte record, vertices and triangles ahead of the string table, offsets shifted, header and bounds updated). `from_obj(data, obj)` empties every old shape (`drop_shape`) and adds the OBJ's faces as solid geometry, so a custom room can get its collision straight from its model: `python -c "from tools.rcb_tool import from_obj; ..."` on `b002_105a_chit.rcb` with `room.obj` gives 13 shapes with only the room's 20 triangles solid (2,916 -> 3,412 bytes). Emulator (cloned slot with the room model + this collision, hero walking right): the game loads, the camera follows and then stops scrolling, consistent with the hero being stopped by the new walls (`out/emu/probe/take_46681`); the hero is hidden behind the house front wall in that view, so this is supporting evidence, not a clean visual proof. The earlier add_box and drop_shape proofs show the same primitives working with the hero visible.

Second comparison (hero walking left in the cloned slot, room model, `out/emu/probe/room_cmp.png`): with the OBJ-generated collision (`room_chit.rcb`) the camera ends further left (the hero reached the new room's west wall at x = -5) than with the house's original collision (stopped earlier by the old partition), so the generated collision is in force and differs from the original. The hero is still hidden behind the front wall in both views, so a clean screenshot of the hero against a new wall remains to do (needs a camera angle or a room without a front wall).

Open-front room attempt (`out/coltest/open_room.obj` + `open_walls.obj`, `out/emu/probe/take_94731`): the custom room without a front wall renders with the hero visible inside it, but the house's other draws (partition, front wall) still stand and hide the hero again after he walks, so this is not the clean "hero stopped by a new wall" screenshot either. The decisive visual proofs for the collision primitives remain the earlier ones with the hero visible: moved wall (hero stops mid-nave), dropped shape (hero walks through that wall only), added box (hero stopped at an invisible box). To finish a clean full-room proof, replace every draw of the cloned model, not only the first two.

Checkerboard room comparison (`out/emu/probe/cc_cmp.png`, hero visible in the all-custom room, walking left; top row with the generated `open_chit.rcb`, bottom row with the house's original collision): the hero's path differs, but the "without" run uses the house's old obstacles (partition, furniture), not an unwalled room, so it does not isolate the left wall. The clean proof would be: the same room with an *empty* collision file (hero walks through the west wall into the void) versus the generated one (hero stops at x = -5). Not done; the earlier add / drop / move proofs remain the decisive ones.

## PROVEN (clean): collision generated from an OBJ keeps the hero in a custom room

All-custom checkerboard room (`out/coltest/full_room_tex.bch`), cloned slot, hero walking left (`out/emu/probe/cc_cmp2.png`): with the collision generated from the room's walls (`rcb_tool.from_obj`, `open_chit.rcb`) the hero stays inside the room; with an **empty** collision file (every shape dropped) the hero and his companion walk out of the room into the void. So generated collision is in force and is what keeps the player inside authored geometry.
