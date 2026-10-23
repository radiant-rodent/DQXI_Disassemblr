//! Unit tests for the pieces that are easy to regress:
//! orbit-drag direction, corrupt-vertex salvage, area-id mapping and formatting.

use crate::data::areas::area_of;
use crate::render::camera::Camera;
use crate::render::mesh::load_obj;
use crate::utils::human_size;

#[test]
fn both_drag_axes_follow_the_mouse() {
    let mut camera = Camera::default();
    let (az0, el0) = (camera.azimuth, camera.elevation);
    // dragging right (positive dx) turns the model to the right
    camera.orbit(50.0, 0.0);
    assert!(camera.azimuth < az0, "dragging right must turn the model right");
    // dragging down (positive dy) tips the top towards the viewer
    camera.orbit(0.0, 50.0);
    assert!(
        camera.elevation > el0,
        "dragging down must tip the model's top towards you"
    );
}

#[test]
fn invert_flags_flip_one_axis_each() {
    let mut camera = Camera::default();
    camera.invert_horizontal = true;
    let (az0, el0) = (camera.azimuth, camera.elevation);
    camera.orbit(50.0, 0.0);
    assert!(camera.azimuth > az0, "horizontal is inverted on request");
    camera.invert_vertical = true;
    camera.orbit(0.0, 50.0);
    assert!(camera.elevation < el0, "vertical is inverted on request");
}

#[test]
fn elevation_is_clamped() {
    let mut camera = Camera::default();
    for _ in 0..100 {
        camera.orbit(0.0, 90.0);
    }
    assert!(camera.elevation <= 89.0);
    for _ in 0..200 {
        camera.orbit(0.0, -90.0);
    }
    assert!(camera.elevation >= -89.0);
}

#[test]
fn corrupt_vertices_do_not_blow_up_the_framing() {
    let dir = std::env::temp_dir().join("dqxi_viewer_tests");
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("stray.obj");
    let mut text = String::from("o body\n");
    // a sane 10x10 vertex grid of unit quads (like a real environment mesh)
    for y in 0..10 {
        for x in 0..10 {
            text.push_str(&format!("v {} {} 0\n", x as f64 * 2.0, y as f64 * 2.0));
        }
    }
    for y in 0..9 {
        for x in 0..9 {
            let a = y * 10 + x + 1;
            text.push_str(&format!("f {} {} {}\n", a, a + 1, a + 10));
        }
    }
    // plus a handful of corrupt vertices, as shipped in some environment exports
    for i in 0..12 {
        text.push_str(&format!("v 2e30 {} 1e30\n", i as f64));
    }
    std::fs::write(&path, text).unwrap();

    let mesh = load_obj(&path).expect("mesh");
    let extent = mesh.bounds.max_extent();
    assert!(
        extent > 17.0 && extent < 25.0,
        "framing must ignore stray vertices (extent {extent})"
    );
    assert!(mesh.bounds.radius().is_finite());
    assert!(mesh.outliers >= 8, "stray vertices should be reported");
    assert_eq!(mesh.triangle_count, 81);
}

#[test]
fn obj_material_groups_keep_textures_and_uvs() {
    let dir = std::env::temp_dir().join("dqxi_viewer_material_test");
    std::fs::create_dir_all(&dir).unwrap();
    let obj = dir.join("two_mats.obj");
    let mtl = dir.join("two_mats.mtl");
    let png = dir.join("floor.png");
    image::RgbaImage::from_pixel(2, 2, image::Rgba([120, 160, 200, 255]))
        .save(&png)
        .unwrap();
    std::fs::write(
        &mtl,
        "newmtl floor_mat\nKd 0.8 0.8 0.8\nmap_Kd floor.png\n\
         newmtl wall_mat\nKd 0.6 0.6 0.6\n",
    )
    .unwrap();
    std::fs::write(
        &obj,
        "mtllib two_mats.mtl\n\
         v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n\
         vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n\
         usemtl floor_mat\nf 1/1 2/2 3/3\n\
         usemtl wall_mat\nf 1/1 3/3 4/4\n",
    )
    .unwrap();
    let mesh = load_obj(&obj).expect("mesh");
    assert_eq!(mesh.groups.len(), 2);
    assert_eq!(mesh.groups[0].material, "floor_mat");
    assert_eq!(mesh.groups[1].material, "wall_mat");
    assert_eq!(mesh.groups[0].index_count, 3);
    assert_eq!(mesh.groups[1].index_count, 3);
    assert_eq!(mesh.groups[0].texture_path.as_deref(), Some(png.as_path()));
    assert!(mesh.vertices.len() >= 4 * crate::render::mesh::STRIDE);
    // UVs are flipped into texture space and survive the merge.
    assert!((mesh.vertices[2 * crate::render::mesh::STRIDE + 5] - 1.0).abs() < 1e-6);
}

#[test]
fn area_ids_cover_map_scene_meshes() {
    assert_eq!(area_of("b001_101a_2d").as_deref(), Some("b001_101a"));
    assert_eq!(area_of("Map_b001_101a_cs").as_deref(), Some("b001_101a"));
    assert_eq!(area_of("Map_b005_106a").as_deref(), Some("b005_106a"));
    assert_eq!(area_of("a_010_cs_010").as_deref(), Some("a010"));
    assert_eq!(area_of("Hero_TheLuminary"), None);
    assert_eq!(area_of("b000_000"), None);
}

#[test]
fn sizes_are_human_readable() {
    assert_eq!(human_size(0), "0 B");
    assert_eq!(human_size(1023), "1023 B");
    assert_eq!(human_size(1024), "1.0 KB");
    assert_eq!(human_size(1024 * 1024 * 3 / 2), "1.5 MB");
}

#[test]
fn editor_scene_json_round_trips() {
    let text = r#"{
      "id": "b001_101a",
      "source": "game_data/packs/level3d/b001_101a/level3d.bxon",
      "background_bch": "game_data/packs/3d/bg/b001_101a/b001_101a.bch",
      "objects": [{
        "id": "000_0x194C", "kind": "placement",
        "position": [14.75, 2.0, -4.75], "scale": [2.0, 4.0, 2.0],
        "rotation": [0.0, 0.0, 0.0], "record_offset": "0x194C",
        "field_offsets": {
          "position": ["0x194C", "0x1950", "0x1954"],
          "scale": ["0x197C", "0x1980", "0x1984"],
          "rotation": ["0x19AC", "0x19B0", "0x19B4"]
        }
      }]
    }"#;
    let scene: crate::ui::panels::editor::Scene = serde_json::from_str(text).expect("scene");
    assert_eq!(scene.id, "b001_101a");
    assert_eq!(scene.objects.len(), 1);
    assert_eq!(scene.objects[0].position[0], 14.75);
    let encoded = serde_json::to_string(&scene).expect("serialize");
    let again: crate::ui::panels::editor::Scene = serde_json::from_str(&encoded).expect("reparse");
    assert_eq!(again.objects[0].scale, [2.0, 4.0, 2.0]);
}

#[test]
fn editor_float_patch_is_bounded_and_exact() {
    let mut bytes = vec![0u8; 32];
    let edits = vec![("0x04".to_string(), 14.75f32), ("0x10".to_string(), -3.5f32)];
    let count = crate::ui::panels::editor::apply_float_edits(&mut bytes, &edits).expect("patch");
    assert_eq!(count, 2);
    assert_eq!(f32::from_le_bytes(bytes[4..8].try_into().unwrap()), 14.75);
    assert_eq!(f32::from_le_bytes(bytes[16..20].try_into().unwrap()), -3.5);
    let bad = vec![("0x20".to_string(), 1.0f32)];
    assert!(crate::ui::panels::editor::apply_float_edits(&mut bytes, &bad).is_err());
}

#[test]
fn waveform_covers_the_whole_track() {
    let path = crate::utils::project_root().join("game_assets/audio/romfs/sound/str/BGM_B01.dspadpcm.wav");
    if !path.is_file() {
        return;
    }
    let (mins, maxs) = crate::utils::waveform_peaks(&path, 100);
    assert_eq!(mins.len(), 100);
    assert_eq!(maxs.len(), 100);
    assert!(mins.iter().skip(90).any(|v| *v < -0.001), "last tenth of waveform must contain audio");
    assert!(maxs.iter().skip(90).any(|v| *v > 0.001), "last tenth of waveform must contain audio");
}

#[test]
fn wav_duration_matches_known_track() {    let path = crate::utils::project_root().join("game_assets/audio/romfs/sound/str/BGM_B01.dspadpcm.wav");
    if !path.is_file() {
        return;
    }
    let info = crate::utils::read_wav_info(&path).expect("wav header");
    assert_eq!(info.rate, 32728);
    assert_eq!(info.channels, 2, "info={info:?}");
    assert!(info.frames > 1_900_000, "info={info:?}");
    assert!((info.duration() - 59.87).abs() < 0.1, "duration={}", info.duration());
    assert_ne!(info.duration_text(), "--:--");
}

#[test]
fn editor_rejects_non_finite_transforms() {
    let mut obj = crate::ui::panels::editor::SceneObject {
        id: "x".into(),
        kind: "placement".into(),
        position: [0.0, f32::NAN, 0.0],
        scale: [1.0, 1.0, 1.0],
        rotation: [0.0, 0.0, 0.0],
        record_offset: "0x0".into(),
        field_offsets: Default::default(),
    };
    assert!(crate::ui::panels::editor::validate_objects(&[obj.clone()]).is_err());
    obj.position[1] = 1.0;
    assert!(crate::ui::panels::editor::validate_objects(&[obj]).is_ok());
}

/// Prints how long each boot index takes on the real asset tree.
/// `cargo test --release boot_timings -- --ignored --nocapture`
#[test]
#[ignore]
fn boot_timings() {
    use crate::data::*;
    let dirs = crate::utils::Dirs::detect();
    let t = std::time::Instant::now();
    let mut lap = |label: &str| {
        println!("{label:>12}: {:>7.2}s", t.elapsed().as_secs_f32());
    };
    let mut textures = textures::TextureIndex::default();
    textures.ensure(&dirs);
    lap("textures");
    let mut models = models::ModelIndex::default();
    models.ensure(&dirs);
    lap("models");
    let mut layouts = layouts::LayoutIndex::default();
    layouts.ensure(&dirs);
    lap("layouts");
    let mut scripts = scripts::ScriptIndex::default();
    scripts.ensure(&dirs);
    lap("scripts");
    let mut tables = tables::TableIndex::default();
    tables.ensure(&dirs);
    lap("tables");
    let mut audio = audio::AudioIndex::default();
    audio.ensure(&dirs);
    lap("audio");
    let mut dialogues = dialogues::DialogueDb::new(dirs.dialogue_db.clone());
    dialogues.stats();
    lap("dialogues");
    let mut areas = areas::AreaIndex::default();
    areas.ensure(&dirs, &textures, &scripts, &audio, &layouts, &models, &mut dialogues);
    lap("areas");
}


/// One wheel notch zooms the same amount whether egui delivers it in one
/// frame or spread over many, and a notch is a modest step, not a jump.
#[test]
fn zoom_is_independent_of_scroll_splitting() {
    let mut once = Camera::default();
    once.zoom(50.0);
    let mut split = Camera::default();
    for _ in 0..25 {
        split.zoom(2.0);
    }
    assert!((once.distance - split.distance).abs() < 1e-4);
    let step = once.distance / Camera::default().distance;
    assert!(step > 0.8 && step < 0.95, "one notch should be a ~12% step, got {step}");
    let mut back = once;
    back.zoom(-50.0);
    assert!((back.distance - Camera::default().distance).abs() < 1e-4, "zoom in/out must be symmetric");
}

/// The Expression picker bakes from the right source file and lists the
/// default pose first, then the catalogued ones.
#[test]
fn expression_picker_finds_source_and_poses() {
    use crate::ui::panels::models::{load_poses, source_bch};
    let dirs = crate::utils::Dirs::detect();
    let bch = source_bch(&dirs.root, "packs/3d/model/cha01000a_h/cha01000a_h", "cha01000a_h").unwrap();
    assert!(bch.ends_with("game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch"));
    let poses = load_poses(&dirs.models);
    assert_eq!(poses[0].eyes, (0.0, 0.0));
    assert_eq!(poses[0].mouth, (0.0, 0.0));
    if dirs.models.join("face_expressions.json").is_file() {
        assert!(bch.is_file(), "source BCH must exist: {bch:?}");
        assert!(poses.len() > 1, "catalogued poses must be listed");
        assert!(poses[1..].iter().all(|p| p.eyes != (0.0, 0.0) || p.mouth != (0.0, 0.0)));
    }
}

/// Every "How do I" command on the Overview names a tool that exists.
#[test]
fn how_do_i_commands_point_at_real_tools() {
    let dirs = crate::utils::Dirs::detect();
    for (task, command) in crate::ui::panels::overview::HOW_DO_I {
        for word in command.split_whitespace() {
            if word.starts_with("tools/") || word.starts_with("tests/") {
                assert!(dirs.root.join(word).is_file(), "{task}: {word} does not exist");
            }
        }
    }
}

/// The script index lists each disassembly once and finds its decompiled sibling.
#[test]
fn scripts_pair_disassembly_with_decompiled_view() {
    use crate::data::scripts::{decompiled_path, is_decompiled, ScriptIndex};
    let dirs = crate::utils::Dirs::detect();
    let mut scripts = ScriptIndex::default();
    scripts.ensure(&dirs);
    assert!(scripts.items.iter().all(|s| !is_decompiled(&s.path)));
    let Some(a000) = scripts.items.iter().find(|s| s.path.ends_with("a_000/script.nut")) else {
        return; // assets not converted on this machine
    };
    let Some(dec) = decompiled_path(&a000.path) else { return };
    let text = scripts.text(&dec);
    let outline = scripts.outline_decompiled(&text);
    assert!(outline.iter().any(|(name, args, _)| name == "StartEventArg" && args == "func, ..."));
}

#[test]
fn obj_corner_uvs_split_vertices_and_hidden_parts_are_flagged() {
    // a baked face gives a shared position a different texcoord per triangle;
    // the MTL marks game-hidden parts (alternate hand poses)
    let dir = std::env::temp_dir().join("dqxi_viewer_corner_uv_test");
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(
        dir.join("quad.mtl"),
        "newmtl Face\n  Kd 0.8 0.8 0.8\nnewmtl Hand02\n  Kd 0.8 0.8 0.8\n  dqxi_hidden 1\n",
    )
    .unwrap();
    let obj = dir.join("quad.obj");
    std::fs::write(
        &obj,
        "mtllib quad.mtl\nv 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n\
         vt 0 0\nvt 0.5 0\nvt 0.5 0.5\nvt 0.5 0.5\nvt 1 1\nvt 0.5 1\n\
         usemtl Face\nf 1/1 2/2 3/3\nf 1/4 3/5 4/6\nusemtl Hand02\nf 1/1 2/2 3/3\n",
    )
    .unwrap();
    let mesh = load_obj(&obj).unwrap();
    assert_eq!(mesh.triangle_count, 3);
    // positions 1 and 3 carry two different texcoords each -> 4 + 2 GPU vertices
    assert_eq!(mesh.vertex_count, 6);
    let hidden: Vec<bool> = mesh.groups.iter().map(|g| g.hidden).collect();
    assert_eq!(hidden, vec![false, true]);
    // plain exports (v == vt) keep one vertex per position
    std::fs::write(&obj, "v 0 0 0\nv 1 0 0\nv 1 1 0\nvt 0 0\nvt 1 0\nvt 1 1\nf 1/1 2/2 3/3\n").unwrap();
    assert_eq!(load_obj(&obj).unwrap().vertex_count, 3);
}

#[test]
fn real_map_export_carries_its_blend_modes() {
    // b001_101a has additive and alpha-tested draws in material_map.json.gz
    use crate::render::mesh::Blend;
    let obj = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../game_assets/models/packs/3d/bg/b001_101a/b001_101a/b001_101a.obj");
    if !obj.exists() {
        eprintln!("skipped: {} not extracted", obj.display());
        return;
    }
    let mesh = load_obj(&obj).unwrap();
    let additive = mesh.groups.iter().filter(|g| g.blend == Blend::Additive).count();
    let opaque = mesh.groups.iter().filter(|g| g.blend == Blend::Opaque).count();
    assert!(additive > 0, "no additive groups parsed");
    assert!(opaque > 0, "no opaque groups parsed");
    assert!(mesh.groups.iter().any(|g| g.alpha_cutoff > 0.0), "no alpha-tested groups parsed");
}

#[test]
fn obj_mask_map_and_uvs_reach_the_mesh() {
    // terrain decals: colour from one texture, alpha from a channel of a mask on its own UVs
    use crate::render::mesh::{MaskChannel, STRIDE};
    let dir = std::env::temp_dir().join("dqxi_viewer_mask_test");
    std::fs::create_dir_all(&dir).unwrap();
    image::RgbaImage::new(2, 2).save(dir.join("grass.png")).unwrap();
    image::RgbaImage::new(2, 2).save(dir.join("nuki.png")).unwrap();
    std::fs::write(
        dir.join("decal.mtl"),
        "newmtl Decal\n  map_Kd grass.png\n  dqxi_blend alpha\n  dqxi_mask_map nuki.png\n  dqxi_mask_channel red\n",
    )
    .unwrap();
    let obj = dir.join("decal.obj");
    std::fs::write(
        &obj,
        "mtllib decal.mtl\no ground\nv 9 9 9\no decal\nusemtl Decal\nv 0 0 0\nv 1 0 0\nv 1 1 0\n\
         vt 0 0\nvt 4 0\nvt 4 4\nvt 0 0\n\
         dqxi_vt_mask 0.25 0\ndqxi_vt_mask 0.5 0\ndqxi_vt_mask 0.5 1\nf 2/2 3/3 4/4\n",
    )
    .unwrap();
    let mesh = load_obj(&obj).unwrap();
    let group = &mesh.groups[0];
    assert_eq!(group.mask_channel, MaskChannel::Red);
    assert!(group.mask_path.as_ref().unwrap().ends_with("nuki.png"));
    // the decal's vertices carry the mask uvs (v flipped like ordinary uvs)
    let first = mesh.indices[0] as usize;
    assert!((mesh.vertices[first * STRIDE + 8] - 0.25).abs() < 1e-6);
    assert!((mesh.vertices[first * STRIDE + 9] - 1.0).abs() < 1e-6);
}

#[test]
fn obj_vertex_alpha_reaches_the_mesh() {
    use crate::render::mesh::STRIDE;
    let dir = std::env::temp_dir().join("dqxi_viewer_alpha_test");
    std::fs::create_dir_all(&dir).unwrap();
    let obj = dir.join("fade.obj");
    std::fs::write(
        &obj,
        "o solid\nv 5 5 5\nv 6 5 5\nv 6 6 5\nf 1 2 3\no fade\nv 0 0 0\nv 1 0 0\nv 1 1 0\n\
         dqxi_va 0.0\ndqxi_va 0.5\ndqxi_va 1.0\nf 4 5 6\n",
    )
    .unwrap();
    let mesh = load_obj(&obj).unwrap();
    let alpha = |i: usize| mesh.vertices[mesh.indices[i] as usize * STRIDE + 10];
    // first object has no dqxi_va lines -> opaque
    assert_eq!((alpha(0), alpha(1), alpha(2)), (1.0, 1.0, 1.0));
    assert_eq!((alpha(3), alpha(4), alpha(5)), (0.0, 0.5, 1.0));
}

#[test]
fn obj_vertex_lighting_and_scale_reach_the_mesh() {
    use crate::render::mesh::STRIDE;
    let dir = std::env::temp_dir().join("dqxi_viewer_vc_test");
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(dir.join("lit.mtl"), "newmtl Lit\n  Kd 0.8 0.8 0.8\n  dqxi_color_scale 2\nnewmtl Plain\n  Kd 0.8 0.8 0.8\n").unwrap();
    let obj = dir.join("lit.obj");
    std::fs::write(
        &obj,
        "mtllib lit.mtl\no lit\nusemtl Lit\nv 0 0 0\nv 1 0 0\nv 1 1 0\n\
         dqxi_vc 0.5 0.25 0.0\ndqxi_vc 0.5 0.5 0.5\ndqxi_vc 1 1 1\nf 1 2 3\n\
         o plain\nusemtl Plain\nv 5 5 5\nv 6 5 5\nv 6 6 5\nf 4 5 6\n",
    )
    .unwrap();
    let mesh = load_obj(&obj).unwrap();
    assert_eq!(mesh.groups[0].color_scale, 2.0);
    assert_eq!(mesh.groups[1].color_scale, 0.0, "a group without dqxi_vc keeps the viewer's shading");
    let v0 = mesh.indices[0] as usize * STRIDE;
    assert_eq!(&mesh.vertices[v0 + 11..v0 + 14], &[0.5, 0.25, 0.0]);
}

#[test]
fn models_are_grouped_by_kind() {
    use crate::data::models::category_of;
    assert_eq!(category_of("cha01000a_h", "model"), "Characters");
    assert_eq!(category_of("m001a_h", "model"), "Monsters");
    assert_eq!(category_of("w1603b", "model"), "Weapons");
    assert_eq!(category_of("g3101a", "model"), "Props");
    assert_eq!(category_of("ccg031", "model"), "Cutscene models");
    assert_eq!(category_of("ani00000a_h", "model"), "Animals");
    assert_eq!(category_of("r001a_h", "model"), "Mounts");
    assert_eq!(category_of("b001_101a", "bg"), "Maps");
}

#[test]
fn code_pager_clamps_and_counts_pages() {
    use crate::ui::panels::code::PAGE;
    assert_eq!(PAGE, 250);
    assert_eq!(18_787usize.div_ceil(PAGE), 76);
}
