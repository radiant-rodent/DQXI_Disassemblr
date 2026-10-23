# Rebuild and Patch

## Baseline ROM

The retail baseline is immutable. Verify it with:

```powershell
python tools/verify.py
```

`build/code.bin`, `build/code.compressed.bin`, and `build/DQXI.3ds` are produced by:

```powershell
python tools/build.py
python tools/recompile_game.py
```

`recompile_game.py` refuses to pass unless every hash matches retail.

## Level patch

1. Edit and export in the editor (`Export BXON`).
2. Rebuild the PACK and a modified ROM:

```powershell
python tools/patch_game.py --map b001_101a
```

What it does:

- reads `game_assets/maps/<map>/level3d.patched.bxon`;
- replaces the `level3d.bxon` member in the original `level3d/<map>.pack`;
- copies `original/romfs.bin` and writes the PACK at its exact offset if it fits there
  (a smaller PACK also shrinks the file entry), or appends it when it grew (see below);
- builds `build/patched_input/` with hard links for unchanged containers;
- calls `tools/repack_rom.py --modified` and writes `build/DQXI_patched.3ds`.

## Files that grow

`tools/patch_asset.py` and `tools/patch_game.py` accept a rebuilt PACK of any size
(`write_romfs_file` in `tools/patch_asset.py`):

1. A PACK that fits its old RomFS slot is written there; the rest of the slot is zeroed.
2. A larger PACK is appended, 16-byte aligned, at the end of the level-3 data region. The file
   metadata entry gets the new data offset and size; the old slot keeps its retail bytes and
   is no longer referenced.
3. `romfs_hash.resize_data` grows the level-3 size in the IVFC header, recomputes the Level 1/2
   and master sizes and logical offsets, and moves the hash levels behind the new data end.
   `romfs_hash.rebuild` then fills in every hash level. The result is a complete `romfs.bin`
   that is larger than retail.
4. `tools/repack_rom.py --modified` accepts a RomFS of any media-unit-aligned size. It writes
   the new RomFS size, NCCH content size, RomFS hash-region size and RomFS superblock hash into
   the NCCH header. It also resizes partition 0 in the NCSD partition table, moves the
   Manual/Update partitions by the size difference, updates the card info "filled size", and
   takes the room from the trailing `0xFF` padding, so the image stays 4 GiB (about 1.46 GiB
   of room). For the retail RomFS all of these fields come out unchanged, so the plain repack
   still matches the retail SHA-256.

The retail RSA signatures over the NCSD and NCCH headers cannot be regenerated, so they no
longer match a modified image (emulators and CFW don't check them). Grown-file images pass
`romfs_hash.verify` and the layout checks, but have **not been boot-tested in an emulator
yet**: boot one in Citra/Azahar before relying on it.

## RomFS hash tree status

`tools/patch_game.py` and `tools/patch_asset.py` call `tools/romfs_hash.py` after writing the
modified PACK. It recomputes Level 2 (data block hashes), Level 1 (Level 2 block hashes), and
the master hashes, then verifies them before repacking. It streams the image, so it doesn't
load the whole 2.7 GB file into memory. The original image and the patched images (same-size
and grown) all pass this check.

## Native code patch

The assembly tree is still canonical:

```powershell
python tools/build.py
```

`tools/build.py` reassembles `asm/` and compresses with the CTR BLZ codec. Any source-replacement
path must keep the same verification gate. See `docs/CODE.md`.

## Safety

- Work on copies; the retail image and `..\reference project` are read-only.
- Keep `editor_projects/` under version control for level work.
- A PACK that grows is appended to the RomFS automatically; boot-test such images in an emulator.

## Verify the hash tree directly

```powershell
python tools/romfs_hash.py --verify original/romfs.bin
python tools/romfs_hash.py --verify build/patched/romfs.bin
```

Expected: `bad_level2=0`, `bad_level1=0`, `bad_master=0`, `ok=True`.

## Generic asset patch

```powershell
python tools/patch_asset.py --pack 3d/model/ani00000a_h.pack \
  --member ani00000a_h.bch --replacement build\model_patch_test\patched.bch
```

This replaces one member in a PACK, patches a copy of `romfs.bin`, rebuilds/verifies the IVFC
tree, and repacks `build/DQXI_asset_patched.3ds`. A same-size member keeps the PACK's exact
layout; a member of a different size re-lays the PACK out, and a PACK that grew is appended to
the RomFS as described in [Files that grow](#files-that-grow). See
`build/ASSET_PATCH_REPORT.json` (`"relocated": true` when the PACK was appended).
`test_grown_member_is_appended_to_romfs` covers the growing path.
