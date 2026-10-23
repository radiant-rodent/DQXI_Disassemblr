//! Overview dashboard.

use eframe::egui;

use crate::app::{Section, ViewerApp};
use crate::theme;
use crate::utils::human_count;

#[derive(Default)]
pub struct OverviewPanel;

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.label(theme::heading("Dragon Quest XI (3DS) \u{2014} Project Explorer"));
    ui.label(theme::faint_label(
        "Browse every extracted asset, script, table and decompiled function, then change them with the tools below.",
    ));
    ui.add_space(8.0);

    if !app.booted() {
        ui.label(theme::dim_label("building indexes\u{2026}"));
        return;
    }
    // gather everything before drawing so no data borrow is held across closures
    let stats = app
        .data
        .as_mut()
        .map(|d| d.dialogues.stats())
        .unwrap_or_default();
    let cards: Vec<(&'static str, String, &'static str, Section)> = {
        let Some(data) = app.data.as_deref() else { return };
        vec![
            ("TEXTURES", human_count(data.textures.items.len()), "PNG + metadata", Section::Textures),
            ("MODELS", human_count(data.models.items.len()), "OBJ / glTF meshes", Section::Models),
            ("LAYOUTS", human_count(data.layouts.items.len()), "BFLYT / BFLAN JSON", Section::Layouts),
            ("SCRIPTS", human_count(data.scripts.items.len()), "Squirrel disassembly", Section::Scripts),
            ("TABLES", human_count(data.tables.items.len()), "BXON parameter JSON", Section::Tables),
        ]
    };

    let mut go: Option<Section> = None;
    ui.horizontal(|ui| {
        for (title, value, subtitle, section) in cards {
            let (rect, response) = ui.allocate_exact_size(egui::vec2(196.0, 78.0), egui::Sense::click());
            let painter = ui.painter_at(rect);
            let hovered = response.hovered();
            painter.rect_filled(rect, 4.0, if hovered { theme::BG_HOVER } else { theme::BG_RAISED });
            painter.text(
                rect.left_top() + egui::vec2(12.0, 10.0),
                egui::Align2::LEFT_TOP,
                title,
                egui::FontId::proportional(10.0),
                theme::TEXT_DIM,
            );
            painter.text(
                rect.left_top() + egui::vec2(12.0, 24.0),
                egui::Align2::LEFT_TOP,
                value,
                egui::FontId::proportional(24.0),
                theme::ACCENT,
            );
            painter.text(
                rect.left_top() + egui::vec2(12.0, 54.0),
                egui::Align2::LEFT_TOP,
                subtitle,
                egui::FontId::proportional(11.0),
                theme::TEXT_FAINT,
            );
            if response.clicked() {
                go = Some(section);
            }
        }
    });
    if let Some(section) = go {
        app.go(section);
    }

    ui.add_space(12.0);
    let mut quick: Option<Section> = None;
    ui.horizontal(|ui| {
        ui.label(theme::heading("Quick actions"));
        ui.add_space(8.0);
        for (label, section) in [
            ("Browse textures", Section::Textures),
            ("View 3D models", Section::Models),
            ("Preview UI layouts", Section::Layouts),
            ("Read dialogues", Section::Dialogues),
            ("Look at a map", Section::Maps),
            ("Global search", Section::Search),
        ] {
            if ui.button(label).clicked() {
                quick = Some(section);
            }
        }
    });
    if let Some(section) = quick {
        app.go(section);
    }

    ui.add_space(12.0);
    how_do_i(app, ui);

    ui.add_space(12.0);
    let mut state_rows: Vec<(&str, String)> = Vec::new();
    if let Some(meta) = crate::data::load_json(&app.dirs.original.join("metadata.json")) {
        for key in ["title_id", "product_code", "title", "region"] {
            if let Some(value) = meta.get(key) {
                state_rows.push((key, value.to_string().trim_matches('"').to_string()));
            }
        }
    }
    state_rows.push((
        "baseline hashes",
        if app.dirs.original.join("hashes.sha256").exists() { "present".into() } else { "missing".into() },
    ));
    let build = app.dirs.build.join("code.bin");
    state_rows.push((
        "built code.bin",
        if build.exists() { crate::utils::human_size(crate::data::file_size(&build)) } else { "not built".into() },
    ));
    state_rows.push((
        "dialogue database",
        if app.dirs.dialogue_db.exists() { "found".into() } else { "missing".into() },
    ));
    state_rows.push(("project root", app.dirs.root.to_string_lossy().into_owned()));
    let counts: Vec<(&'static str, String)> = {
        let Some(data) = app.data.as_deref() else { return };
        vec![
            ("texture packs", human_count(data.textures.packs().len())),
            ("textures", human_count(data.textures.items.len())),
            ("models", human_count(data.models.items.len())),
            ("layout files", human_count(data.layouts.items.len())),
            ("scripts", human_count(data.scripts.items.len())),
            ("tables", human_count(data.tables.items.len())),
            ("audio streams", human_count(data.audio.streams.len())),
            ("sound archives", human_count(data.audio.archives.len())),
            ("decompiled functions", human_count(data.code.functions.len())),
            ("dialogue entries", human_count(stats.sources)),
            ("PC text rows", human_count(stats.pc_rows)),
            ("map areas", human_count(data.areas.areas.len())),
        ]
    };
    ui.columns(2, |columns| {
        columns[0].label(theme::heading("Project state"));
        crate::ui::kv_rows(&mut columns[0], &state_rows);
        columns[1].label(theme::heading("Counts"));
        crate::ui::kv_rows(&mut columns[1], &counts);
    });
}

/// Common edits for someone new to the project: what to run, one click to copy
/// it. Each line matches a row of docs/EDITING.md.
pub(crate) const HOW_DO_I: &[(&str, &str)] = &[
    ("Change an item's price", "python tools/table_edit.py set syscmn/item.json \"Medicinal herb\" buy_price 5 --out build/item.bxon"),
    ("Put an edited file back into the game", "python tools/patch_asset.py --pack syscmn.pack --member item.bxon --replacement build/item.bxon"),
    ("Edit a model in Blender", "Models \u{2192} Open in Blender, then: python tools/model_patch.py ORIGINAL.bch EDITED.obj --out patched.bch"),
    ("Move an object in a level", "Level Editor \u{2192} drag it \u{2192} Export BXON, then: python tools/patch_game.py --map <map>"),
    ("Replace a model texture", "python tools/bch_texture_patch.py --bch model.bch --texture NAME --png new.png --out patched.bch"),
    ("Replace music", "python tools/bcstm_encode.py --template original.bcstm --wav new.wav --out patched.bcstm"),
    ("Check nothing broke", "python tests/run_all.py"),
];

fn how_do_i(app: &mut ViewerApp, ui: &mut egui::Ui) {
    ui.horizontal(|ui| {
        ui.label(theme::heading("How do I\u{2026}"));
        if ui.button("Open the editing guide").on_hover_text("docs/EDITING.md").clicked() {
            let guide = app.dirs.root.join("docs").join("EDITING.md");
            app.status = match std::process::Command::new("explorer").arg(&guide).spawn() {
                Ok(_) => "opened docs/EDITING.md".into(),
                Err(e) => format!("cannot open {}: {e}", guide.display()),
            };
        }
    });
    egui::Grid::new("how_do_i").num_columns(3).spacing([12.0, 4.0]).show(ui, |ui| {
        for (task, command) in HOW_DO_I {
            ui.label(*task);
            ui.label(theme::mono(*command));
            if ui.small_button("Copy").on_hover_text("copy to clipboard").clicked() {
                ui.ctx().copy_text(command.to_string());
                app.status = format!("copied: {command}");
            }
            ui.end_row();
        }
    });
}
