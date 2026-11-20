//! Restructuring an NPC's dialogue in the Level Editor: add, remove and reorder conversations, blocks and lines,
//! and turn a line into a Yes / No question with its two answer blocks.
//!
//! The game's files are only edited line by line elsewhere; here the character's whole talk tree becomes a model
//! (`python -m tools.npc_ie_edit dump`), is edited freely and written back by `tools/npc_talk.py set-structure`,
//! which rewrites that one character's tree at the end of the region's `npc_ie` bank (nothing else moves) and stages
//! the pack. The models of a region live in `build/npc_structure/param_region_rNNN_npc_ie.json`.

use eframe::egui;
use serde_json::{json, Value};

use crate::app::ViewerApp;
use crate::theme;
use crate::ui::panels::editor::{chapter_name, chapter_stages, stage_label};

const YES: &str = "\u{3010}\u{306f}\u{3044}\u{306e}\u{5834}\u{5408}\u{3011}"; // 【はいの場合】
const NO: &str = "\u{3010}\u{3044}\u{3044}\u{3048}\u{306e}\u{5834}\u{5408}\u{3011}"; // 【いいえの場合】

#[derive(Clone, Default)]
pub struct Custom {
    pub model: Value,
    /// what is staged in the mod (None: never saved)
    pub saved: Option<Value>,
}

fn structure_file(root: &std::path::Path, region1: i32) -> std::path::PathBuf {
    root.join("build").join("npc_structure").join(format!("param_region_r{region1:03}_npc_ie.json"))
}

/// Loads the region's saved custom structures once.
pub fn ensure_loaded(app: &mut ViewerApp, region1: i32) {
    if !app.panels.editor.talk_custom_loaded.insert(region1) {
        return;
    }
    let Some(doc) = std::fs::read(structure_file(&app.dirs.root, region1)).ok().and_then(|b| serde_json::from_slice::<Value>(&b).ok()) else { return };
    for (char, model) in doc.as_object().into_iter().flatten() {
        if let Ok(c) = char.parse::<i64>() {
            app.panels.editor.talk_custom.insert((region1, c), Custom { model: model.clone(), saved: Some(model.clone()) });
        }
    }
}

fn new_line(text: &str) -> Value {
    json!({"speaker": "", "text": text, "kind": 0, "b8": 0, "b9": 255, "b11": 0, "child_n": 0, "child": "", "tail": 0})
}

fn new_talk() -> Value {
    json!({"group": 0, "min": 0, "time": 15, "first": 0, "redirect": 0x4000_FFFFu32,
           "variants": [{"label": null, "lines": [new_line("\u{300c}\u{2026}\u{2026}\u{3002}")]}]})
}

/// Reads the character's tree from the game file (`tools/npc_ie_edit.py dump`) and overlays the line texts that are
/// being edited in this session, so nothing typed so far is lost.
pub fn start(app: &mut ViewerApp, region1: i32, id: i64, character: &Value) -> Result<(), String> {
    let out = std::process::Command::new("python")
        .args(["-m", "tools.npc_ie_edit", "dump", "--region", &region1.to_string(), "--char", &id.to_string()])
        .current_dir(&app.dirs.root)
        .output()
        .map_err(|e| format!("could not run python: {e}"))?;
    if !out.status.success() {
        return Err(String::from_utf8_lossy(&out.stderr).trim().to_string());
    }
    let mut model: Value = serde_json::from_slice(&out.stdout).map_err(|e| format!("bad dump: {e}"))?;
    for (t, talk) in character["talks"].as_array().into_iter().flatten().enumerate() {
        for (v, variant) in talk["variants"].as_array().into_iter().flatten().enumerate() {
            for (k, line) in variant.as_array().into_iter().flatten().enumerate() {
                let slot = &mut model["talks"][t]["variants"][v]["lines"][k];
                if !slot.is_object() {
                    continue;
                }
                if let Some(text) = line["e"].as_u64().and_then(|e| app.panels.dialogues.line_text(e as usize)) {
                    slot["text"] = Value::String(text);
                }
                if let Some(name) = line["s"].as_u64().and_then(|s| app.panels.dialogues.line_text(s as usize)) {
                    slot["speaker"] = Value::String(name);
                }
            }
        }
    }
    app.panels.editor.talk_custom.insert((region1, id), Custom { model, saved: None });
    Ok(())
}

/// Writes the region's custom structures and rebuilds the bank into the mod.
fn save(app: &mut ViewerApp, region1: i32) {
    let doc: serde_json::Map<String, Value> = app
        .panels
        .editor
        .talk_custom
        .iter()
        .filter(|((r, _), _)| *r == region1)
        .map(|((_, c), custom)| (c.to_string(), custom.model.clone()))
        .collect();
    let file = app.dirs.root.join("build").join(format!("npc_structure_edits_r{region1:03}.json"));
    let _ = std::fs::create_dir_all(app.dirs.root.join("build"));
    if let Err(e) = std::fs::write(&file, serde_json::to_vec(&Value::Object(doc)).unwrap_or_default()) {
        app.status = format!("structure not saved: {e}");
        return;
    }
    let out = std::process::Command::new("python")
        .arg(app.dirs.root.join("tools").join("npc_talk.py"))
        .args(["set-structure", "--region", &region1.to_string(), "--json"])
        .arg(&file)
        .current_dir(&app.dirs.root)
        .output();
    app.status = match out {
        Ok(o) if o.status.success() => {
            for ((r, _), custom) in app.panels.editor.talk_custom.iter_mut() {
                if *r == region1 {
                    custom.saved = Some(custom.model.clone());
                }
            }
            "Dialogue structure written to the mod (param/region pack)".to_string()
        }
        Ok(o) => format!("structure not saved: {}", String::from_utf8_lossy(&o.stderr).lines().last().unwrap_or("").trim()),
        Err(e) => format!("could not run python: {e}"),
    };
}

fn lines_mut(model: &mut Value, t: usize, v: usize) -> Option<&mut Vec<Value>> {
    model["talks"][t]["variants"][v]["lines"].as_array_mut()
}

/// Keeps "what follows" sensible after lines were added or removed: every line but the last leads to the next one,
/// the last one ends the block unless it asks a question.
fn fix_kinds(lines: &mut [Value]) {
    let n = lines.len();
    for (i, line) in lines.iter_mut().enumerate() {
        let kind = line["kind"].as_u64().unwrap_or(0);
        if i + 1 < n && kind == 0 {
            line["kind"] = json!(1);
        } else if i + 1 == n && kind == 1 {
            line["kind"] = json!(0);
        }
    }
}

/// The custom-structure editor of one character (shown instead of the game's conversation list).
pub fn section(app: &mut ViewerApp, ui: &mut egui::Ui, talks: &Value, region: i32, id: i64) {
    let key = (region + 1, id);
    let Some(custom) = app.panels.editor.talk_custom.get(&key).cloned() else { return };
    let mut model = custom.model.clone();
    let mode2d = app.panels.editor.view2d.on;
    let mut drop_custom = false;
    let mut do_save = false;

    egui::Frame::new().fill(theme::BG_RAISED).corner_radius(4.0).inner_margin(egui::Margin::symmetric(8, 5)).show(ui, |ui| {
        ui.set_width(ui.available_width());
        ui.label(egui::RichText::new("Custom structure").color(theme::ACCENT).strong());
        ui.label(theme::faint_label("This character's conversations are rewritten as a whole: add, remove and reorder conversations, blocks and lines. The game plays the LAST conversation whose condition matches."));
        ui.horizontal_wrapped(|ui| {
            let dirty = custom.saved.as_ref() != Some(&model);
            if ui.add_enabled(dirty, egui::Button::new("Save structure to mod")).on_hover_text("Rewrites this region's npc_ie bank with the custom characters and stages the pack").clicked() {
                do_save = true;
            }
            if ui.button("Back to the game's structure").on_hover_text("Drop the custom structure of this character (the mod keeps the old file until you save)").clicked() {
                drop_custom = true;
            }
            if dirty {
                ui.label(egui::RichText::new("\u{25cf} unsaved").color(theme::ACCENT).size(11.0));
            }
        });
        ui.label(theme::faint_label("Written by tools/npc_ie_edit.py. Emulator-proven: a new conversation with a Yes / No question and its answer block plays in the game (tools/emu/add_probe.py)."));
    });

    let talk_count = model["talks"].as_array().map(|a| a.len()).unwrap_or(0);
    // operations collected while drawing, applied afterwards
    enum Op {
        DupTalk(usize),
        DelTalk(usize),
        MoveTalk(usize, bool),
        AddBlock(usize),
        AddYesNo(usize),
        DelBlock(usize, usize),
        AddLine(usize, usize),
        DelLine(usize, usize, usize),
        MoveLine(usize, usize, usize, bool),
    }
    let mut ops: Vec<Op> = Vec::new();
    for t in 0..talk_count {
        let (group, min, time) = (model["talks"][t]["group"].as_u64().unwrap_or(0), model["talks"][t]["min"].as_u64().unwrap_or(0), model["talks"][t]["time"].as_u64().unwrap_or(15));
        let when = if group == 0 && min == 0 { "always".to_string() } else { format!("\u{201c}{}\u{201d}, {}", chapter_name(talks, group), stage_label(min)) };
        egui::CollapsingHeader::new(egui::RichText::new(format!("Conversation {t}  \u{b7}  {when}")).color(theme::TEXT_DIM)).id_salt(("ctalk", id, t)).default_open(talk_count <= 2).show(ui, |ui| {
            ui.horizontal_wrapped(|ui| {
                ui.label(theme::faint_label("Plays once the chapter"));
                let chapters = talks["scenarios"].as_array().map(|a| a.len()).unwrap_or(0);
                let mut g = group;
                egui::ComboBox::from_id_salt(("ctalk_chapter", id, t)).selected_text(chapter_name(talks, g)).width(200.0).show_ui(ui, |ui| {
                    for c in 0..chapters as u64 {
                        ui.selectable_value(&mut g, c, format!("{c}  {}  {}", chapter_name(talks, c), talks["scenarios"][c as usize]["title"].as_str().unwrap_or("")));
                    }
                });
                ui.label(theme::faint_label("has reached"));
                let mut m = min;
                egui::ComboBox::from_id_salt(("ctalk_stage", id, t)).selected_text(stage_label(m)).width(140.0).show_ui(ui, |ui| {
                    for (stage, text) in chapter_stages(talks, g) {
                        let short: String = text.chars().take(34).collect();
                        ui.selectable_value(&mut m, stage, format!("{}  {short}", stage_label(stage))).on_hover_text(text);
                    }
                });
                ui.add(egui::DragValue::new(&mut m).range(0..=255)).on_hover_text("stage number");
                let mut tm = time;
                for (bit, name) in [(1u64, "morning"), (2, "day"), (4, "evening"), (8, "night")] {
                    let mut on = tm & bit != 0;
                    if ui.checkbox(&mut on, name).changed() {
                        tm = if on { tm | bit } else { tm & !bit };
                    }
                }
                model["talks"][t]["group"] = json!(g);
                model["talks"][t]["min"] = json!(m);
                model["talks"][t]["time"] = json!(tm);
            });
            ui.horizontal_wrapped(|ui| {
                if ui.small_button("Duplicate conversation").clicked() {
                    ops.push(Op::DupTalk(t));
                }
                if ui.add_enabled(t > 0, egui::Button::new("\u{25b2}").small()).on_hover_text("Earlier (lower priority)").clicked() {
                    ops.push(Op::MoveTalk(t, true));
                }
                if ui.add_enabled(t + 1 < talk_count, egui::Button::new("\u{25bc}").small()).on_hover_text("Later (wins over the ones before it)").clicked() {
                    ops.push(Op::MoveTalk(t, false));
                }
                if ui.small_button("Delete conversation").clicked() {
                    ops.push(Op::DelTalk(t));
                }
            });
            let block_count = model["talks"][t]["variants"].as_array().map(|a| a.len()).unwrap_or(0);
            for v in 0..block_count {
                ui.add_space(4.0);
                ui.horizontal_wrapped(|ui| {
                    let mut label = model["talks"][t]["variants"][v]["label"].as_str().unwrap_or("").to_string();
                    ui.label(egui::RichText::new(if label.is_empty() { "Block (plain)" } else { "Block" }).color(theme::ACCENT).size(11.5));
                    let hint = "name, e.g. \u{3010}\u{306f}\u{3044}\u{306e}\u{5834}\u{5408}\u{3011}; empty = plain";
                    if ui.add(egui::TextEdit::singleline(&mut label).id_salt(("clabel", id, t, v)).desired_width(170.0).hint_text(hint)).changed() {
                        model["talks"][t]["variants"][v]["label"] = if label.is_empty() { Value::Null } else { Value::String(label.clone()) };
                    }
                    ui.label(theme::faint_label(if label == YES {
                        "plays after Yes"
                    } else if label == NO {
                        "plays after No"
                    } else if label.is_empty() {
                        "plain blocks play in turn when you talk again"
                    } else {
                        "a script picks it by this name (IEChangeBlock)"
                    }));
                    if ui.small_button("Delete block").clicked() {
                        ops.push(Op::DelBlock(t, v));
                    }
                });
                let line_count = model["talks"][t]["variants"][v]["lines"].as_array().map(|a| a.len()).unwrap_or(0);
                for k in 0..line_count {
                    let page_id = ui.make_persistent_id(("cline_page", id, t, v, k));
                    let mut page: usize = ui.data(|d| d.get_temp(page_id).unwrap_or(0));
                    egui::Frame::new().fill(theme::BG_INPUT).corner_radius(4.0).inner_margin(egui::Margin::symmetric(8, 6)).show(ui, |ui| {
                        ui.set_width(ui.available_width());
                        let line = model["talks"][t]["variants"][v]["lines"][k].clone();
                        let mut speaker = line["speaker"].as_str().unwrap_or("").to_string();
                        let mut text = line["text"].as_str().unwrap_or("").to_string();
                        let mut kind = line["kind"].as_u64().unwrap_or(0);
                        ui.horizontal_wrapped(|ui| {
                            ui.label(theme::faint_label("speaker"));
                            ui.add(egui::TextEdit::singleline(&mut speaker).id_salt(("cspeaker", id, t, v, k)).desired_width(110.0).hint_text("none"));
                            ui.label(theme::faint_label("then"));
                            let name = |k: u64| match k {
                                0 => "the block ends".to_string(),
                                1 => "the next line".to_string(),
                                3 => "asks Yes / No".to_string(),
                                other => format!("marker {other} (not decoded)"),
                            };
                            egui::ComboBox::from_id_salt(("ckind", id, t, v, k)).selected_text(name(kind)).width(120.0).show_ui(ui, |ui| {
                                for option in [0u64, 1, 3] {
                                    ui.selectable_value(&mut kind, option, name(option));
                                }
                            });
                            if ui.add_enabled(k > 0, egui::Button::new("\u{25b2}").small()).clicked() {
                                ops.push(Op::MoveLine(t, v, k, true));
                            }
                            if ui.add_enabled(k + 1 < line_count, egui::Button::new("\u{25bc}").small()).clicked() {
                                ops.push(Op::MoveLine(t, v, k, false));
                            }
                            if ui.small_button("Delete line").clicked() {
                                ops.push(Op::DelLine(t, v, k));
                            }
                        });
                        let width = ui.available_width();
                        let shown = crate::ui::talk_preview::show(app, ui, mode2d, &speaker, &text, page, width, kind == 3);
                        if shown.pages > 1 {
                            ui.horizontal(|ui| {
                                if ui.add_enabled(page > 0, egui::Button::new("\u{25c0}").small()).clicked() {
                                    page -= 1;
                                }
                                ui.label(theme::faint_label(format!("box {} of {}", page.min(shown.pages - 1) + 1, shown.pages)));
                                if ui.add_enabled(page + 1 < shown.pages, egui::Button::new("\u{25b6}").small()).clicked() {
                                    page += 1;
                                }
                            });
                        }
                        for note in &shown.notes {
                            ui.label(egui::RichText::new(note).color(theme::WARN).size(11.0));
                        }
                        ui.add(egui::TextEdit::multiline(&mut text).id_salt(("ctext", id, t, v, k)).desired_rows(2).desired_width(f32::INFINITY).font(egui::TextStyle::Monospace));
                        if let Err(e) = crate::data::dialogues::pieces(&text) {
                            ui.label(egui::RichText::new(e).color(theme::ERR).size(11.0));
                        }
                        let slot = &mut model["talks"][t]["variants"][v]["lines"][k];
                        slot["speaker"] = Value::String(speaker);
                        slot["text"] = Value::String(text);
                        slot["kind"] = json!(kind);
                    });
                    ui.data_mut(|d| d.insert_temp(page_id, page));
                    ui.add_space(3.0);
                }
                if ui.small_button("+ Line").clicked() {
                    ops.push(Op::AddLine(t, v));
                }
            }
            ui.add_space(4.0);
            ui.horizontal_wrapped(|ui| {
                if ui.button("+ Block").on_hover_text("Another plain block (played in turn), or name it for a script").clicked() {
                    ops.push(Op::AddBlock(t));
                }
                if ui.button("+ Yes / No question").on_hover_text("Makes the last line of the first block ask Yes / No and adds the two answer blocks").clicked() {
                    ops.push(Op::AddYesNo(t));
                }
            });
        });
    }
    if ui.button("+ Conversation").on_hover_text("A new conversation at the end: it wins over the earlier ones when its condition matches").clicked() {
        if let Some(list) = model["talks"].as_array_mut() {
            list.push(new_talk());
        } else {
            model["talks"] = json!([new_talk()]);
        }
    }

    for op in ops {
        match op {
            Op::DupTalk(t) => {
                if let Some(list) = model["talks"].as_array_mut() {
                    let copy = list[t].clone();
                    list.insert(t + 1, copy);
                }
            }
            Op::DelTalk(t) => {
                if let Some(list) = model["talks"].as_array_mut() {
                    list.remove(t);
                }
            }
            Op::MoveTalk(t, up) => {
                if let Some(list) = model["talks"].as_array_mut() {
                    list.swap(t, if up { t - 1 } else { t + 1 });
                }
            }
            Op::AddBlock(t) => {
                if let Some(list) = model["talks"][t]["variants"].as_array_mut() {
                    list.push(json!({"label": null, "lines": [new_line("\u{300c}\u{2026}\u{2026}\u{3002}")]}));
                }
            }
            Op::AddYesNo(t) => {
                if let Some(list) = model["talks"][t]["variants"].as_array_mut() {
                    if list.is_empty() {
                        list.push(json!({"label": null, "lines": [new_line("\u{300c}\u{2026}\u{2026}\u{ff1f}")]}));
                    }
                    if let Some(last) = list[0]["lines"].as_array_mut().and_then(|l| l.last_mut()) {
                        last["kind"] = json!(3);
                    }
                    for label in [YES, NO] {
                        if !list.iter().any(|b| b["label"].as_str() == Some(label)) {
                            list.push(json!({"label": label, "lines": [new_line("\u{300c}\u{2026}\u{2026}\u{3002}")]}));
                        }
                    }
                }
            }
            Op::DelBlock(t, v) => {
                if let Some(list) = model["talks"][t]["variants"].as_array_mut() {
                    list.remove(v);
                }
            }
            Op::AddLine(t, v) => {
                if let Some(lines) = lines_mut(&mut model, t, v) {
                    lines.push(new_line("\u{300c}\u{2026}\u{2026}\u{3002}"));
                    fix_kinds(lines);
                }
            }
            Op::DelLine(t, v, k) => {
                if let Some(lines) = lines_mut(&mut model, t, v) {
                    lines.remove(k);
                    fix_kinds(lines);
                }
            }
            Op::MoveLine(t, v, k, up) => {
                if let Some(lines) = lines_mut(&mut model, t, v) {
                    let other = if up { k - 1 } else { k + 1 };
                    // the "what follows" markers stay with their position, the content moves
                    let (ka, kb) = (lines[k]["kind"].clone(), lines[other]["kind"].clone());
                    lines.swap(k, other);
                    lines[k]["kind"] = ka;
                    lines[other]["kind"] = kb;
                }
            }
        }
    }

    if drop_custom {
        app.panels.editor.talk_custom.remove(&key);
        // the saved file loses the character too
        if custom.saved.is_some() {
            save(app, region + 1);
        }
        return;
    }
    if let Some(entry) = app.panels.editor.talk_custom.get_mut(&key) {
        entry.model = model;
    }
    if do_save {
        save(app, region + 1);
    }
}

// ------------------------------------------------------------------------------------------------- answers
/// The event whose Yes / No steps are being edited (`tools/event_actions.py`).
#[derive(Clone, Default)]
pub struct EventEdit {
    pub area: String,
    pub event: String,
    /// `show` result: asks, has_no, yes[], no[], edited
    pub data: Value,
    /// the step being composed: kind, first number, second number
    pub new: (usize, i64, i64),
    pub message: String,
}

/// Steps that can be added to a branch: (label, hint for the two numbers, code).
const STEP_KINDS: [(&str, &str, &str); 6] = [
    ("Set game flag", "flag, value", "SetGlobalGameFlag({a}, {b});"),
    ("Set chapter stage", "chapter number, stage", "SetScenarioFlag({a}, {b});"),
    ("Set quest stage", "quest, stage", "SetQuestFlag({a}, {b});"),
    ("Show level group", "group", "SetLevelGroupEnable({a}, true);"),
    ("Hide level group", "group", "SetLevelGroupEnable({a}, false);"),
    ("Give item", "item id, count", "AutoAddItemInParty({a}, {b});"),
];

fn run_tool(app: &ViewerApp, args: &[&str]) -> Result<Value, String> {
    let out = std::process::Command::new("python")
        .arg(app.dirs.root.join("tools").join("event_actions.py"))
        .args(args)
        .current_dir(&app.dirs.root)
        .output()
        .map_err(|e| format!("could not run python: {e}"))?;
    if !out.status.success() {
        return Err(String::from_utf8_lossy(&out.stderr).lines().last().unwrap_or("failed").trim().to_string());
    }
    serde_json::from_slice(&out.stdout).map_err(|e| format!("bad answer from the tool: {e}"))
}

fn apply_ops(app: &mut ViewerApp, ops: Value, stage: bool) {
    let Some(edit) = app.panels.editor.event_edit.clone() else { return };
    let file = app.dirs.root.join("build").join("event_ops.json");
    let _ = std::fs::create_dir_all(app.dirs.root.join("build"));
    let _ = std::fs::write(&file, serde_json::to_vec(&ops).unwrap_or_default());
    let path = file.to_string_lossy().into_owned();
    let mut args = vec!["edit", "--area", edit.area.as_str(), "--event", edit.event.as_str(), "--json", path.as_str()];
    if stage {
        args.push("--stage");
    }
    let result = run_tool(app, &args);
    if let Some(e) = app.panels.editor.event_edit.as_mut() {
        match result {
            Ok(data) => {
                e.data = data;
                e.message = if stage { "Script written to the mod (script pack).".into() } else { "Compiled: the change builds. Not in the mod until you save.".into() };
            }
            Err(err) => e.message = err,
        }
    }
}

/// Editable "If Yes / If No" lists of an event. Returns false when this event is not the one being edited.
pub fn event_editor(app: &mut ViewerApp, ui: &mut egui::Ui, area: &str, event: &str) -> bool {
    let Some(edit) = app.panels.editor.event_edit.clone().filter(|e| e.area == area && e.event == event) else { return false };
    let mut ops: Vec<Value> = Vec::new();
    let mut stage = false;
    let mut close = false;
    let mut reset = false;
    let mut new = edit.new;
    if edit.data["asks"].as_bool() != Some(true) {
        ui.label(theme::faint_label("This event has no Yes / No branch of the usual shape; edit it in the script editor."));
    }
    for (branch, title) in [("yes", "If Yes"), ("no", "If No")] {
        if edit.data["asks"].as_bool() != Some(true) {
            break;
        }
        if branch == "no" && edit.data["has_no"].as_bool() != Some(true) {
            ui.label(theme::faint_label("If No: the event has no separate branch for it."));
            continue;
        }
        ui.label(egui::RichText::new(title).color(theme::INFO).strong().size(11.5));
        for (i, step) in edit.data[branch].as_array().into_iter().flatten().enumerate() {
            ui.horizontal(|ui| {
                ui.label(egui::RichText::new(format!("  \u{2022} {}", step["plain"].as_str().unwrap_or(""))).size(11.5).color(theme::TEXT_DIM))
                    .on_hover_text(step["text"].as_str().unwrap_or(""));
                if step["editable"].as_bool() == Some(true) && ui.small_button("\u{d7}").on_hover_text("Remove this step").clicked() {
                    ops.push(json!({"branch": branch, "op": "remove", "index": i}));
                }
            });
        }
    }
    if edit.data["asks"].as_bool() == Some(true) {
        ui.horizontal_wrapped(|ui| {
            egui::ComboBox::from_id_salt(("step_kind", event)).selected_text(STEP_KINDS[new.0.min(5)].0).show_ui(ui, |ui| {
                for (i, (label, _, _)) in STEP_KINDS.iter().enumerate() {
                    ui.selectable_value(&mut new.0, i, *label);
                }
            });
            let (_, hint, code) = STEP_KINDS[new.0.min(5)];
            ui.add(egui::DragValue::new(&mut new.1).range(0..=65535)).on_hover_text(hint);
            if code.contains("{b}") {
                ui.add(egui::DragValue::new(&mut new.2).range(0..=65535)).on_hover_text(hint);
            }
            let line = code.replace("{a}", &new.1.to_string()).replace("{b}", &new.2.to_string());
            if new.0 == 5 {
                ui.label(theme::faint_label(crate::ui::panels::editor::item_name(new.1 as u32)));
            }
            if ui.button("+ to Yes").on_hover_text(line.clone()).clicked() {
                ops.push(json!({"branch": "yes", "op": "add", "code": line}));
            }
            if edit.data["has_no"].as_bool() == Some(true) && ui.button("+ to No").on_hover_text(line.clone()).clicked() {
                ops.push(json!({"branch": "no", "op": "add", "code": line}));
            }
        });
    }
    ui.horizontal_wrapped(|ui| {
        let edited = edit.data["edited"].as_bool() == Some(true);
        if ui.add_enabled(edited, egui::Button::new("Save script to mod")).on_hover_text("Packs the edited area script into the mod").clicked() {
            stage = true;
        }
        if ui.add_enabled(edited, egui::Button::new("Discard script edits")).on_hover_text("Back to the game's script for this whole area").clicked() {
            reset = true;
        }
        if ui.button("Done").clicked() {
            close = true;
        }
    });
    if !edit.message.is_empty() {
        ui.label(egui::RichText::new(&edit.message).size(11.0).color(theme::TEXT_FAINT));
    }
    ui.label(theme::faint_label("Every change is compiled at once; one that does not build is refused. The Scripts editor keeps its own copy of an area's script: use one of the two for an area. Not yet tested in the emulator."));
    if let Some(e) = app.panels.editor.event_edit.as_mut() {
        e.new = new;
    }
    if !ops.is_empty() {
        apply_ops(app, Value::Array(ops), false);
    } else if stage {
        apply_ops(app, json!([]), true);
    } else if reset {
        let result = run_tool(app, &["reset", "--area", area]).and_then(|_| run_tool(app, &["show", "--area", area, "--event", event]));
        if let Some(e) = app.panels.editor.event_edit.as_mut() {
            match result {
                Ok(data) => {
                    e.data = data;
                    e.message = "Script edits of this area dropped.".into();
                }
                Err(err) => e.message = err,
            }
        }
    }
    if close {
        app.panels.editor.event_edit = None;
    }
    true
}

/// Starts editing the answers of an event.
pub fn open_event(app: &mut ViewerApp, area: &str, event: &str) {
    match run_tool(app, &["show", "--area", area, "--event", event]) {
        Ok(data) => app.panels.editor.event_edit = Some(EventEdit { area: area.to_string(), event: event.to_string(), data, new: (0, 0, 1), message: String::new() }),
        Err(e) => app.status = format!("could not read the event: {e}"),
    }
}
