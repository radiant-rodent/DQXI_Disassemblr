//! The game's talk window, drawn from the game's own layout files with the game's fonts.
//!
//! * 3D mode: `ui/common_3d` layout `win_talk_3d` (text panes `txt1` / `txt_l1`: font 3D14 at 15 x 16, line space 6,
//!   350 x 66, three lines; name pane `txt_name_l`: font 3D12 at 13 x 15).
//! * 2D mode: `ui/common_2d` layout `win_talk_2d` (text panes `txt` / `txt_l`: font 2D14 at 15 x 16, line space 3,
//!   320 x 56, three lines; name pane: font 2D9 at 11 x 11).
//!
//! A line with a speaker uses the "left" half of the layout: the part `win_talk_base_*` (window + name plate) with
//! the name plate sized by the game's `win_talk_base_*_name<N>` animation for a name of N characters (2..12), which
//! sets the size of `win_left1` / `win_left2`. A line without a speaker uses the plain window `win`.
//! Furigana (`{ruby:base|reading}`) is drawn by `Ui_LayoutText_BuildHorizontalRubyQuads` in the game: the reading
//! in the same font, scaled down and centred above the base text. The scale used here (half size) is an estimate.
//! Not drawn in 2D mode: emulator screenshots of the 2D talk window (out/emu/probe/e2d_baseline_*) show the same
//! priest line without any reading, while 3D mode shows them (its lines are 6 px apart, 2D: 3 px).

use std::collections::HashMap;
use std::path::Path;
use std::sync::Arc;

use eframe::egui;

use crate::app::ViewerApp;
use crate::data::dialogues::{self, Piece};
use crate::data::game_font::GameFont;
use crate::data::layout_scene::{self, Scene, TextDraw};
use crate::theme;

#[derive(Default)]
pub struct TalkPreview {
    /// (2D mode, name length or 0 = no speaker) -> window scene
    scenes: HashMap<(bool, usize), Arc<Scene>>,
    fonts: HashMap<String, Option<Arc<GameFont>>>,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Run {
    Char(char),
    /// a value the game fills in ({PLAYER}, item names, numbers ...)
    Var(u8),
    Ruby(String, String),
}

/// Tagged text -> message boxes -> lines -> runs. `{CR}` followed by a line break is that one break.
pub fn pages(tagged: &str) -> Vec<Vec<Vec<Run>>> {
    let mut pages: Vec<Vec<Vec<Run>>> = vec![vec![Vec::new()]];
    let mut plain = String::new();
    let flush = |plain: &mut String, pages: &mut Vec<Vec<Vec<Run>>>| {
        if plain.is_empty() {
            return;
        }
        let list = dialogues::pieces(plain).unwrap_or_else(|_| plain.chars().map(Piece::Text).collect());
        plain.clear();
        for piece in list {
            match piece {
                Piece::Page => pages.push(vec![Vec::new()]),
                Piece::Newline => {
                    if let Some(page) = pages.last_mut() {
                        page.push(Vec::new());
                    }
                }
                Piece::Cr => {}
                Piece::Text(c) => {
                    if let Some(line) = pages.last_mut().and_then(|p| p.last_mut()) {
                        line.push(Run::Char(c));
                    }
                }
                Piece::Var(slot) => {
                    if let Some(line) = pages.last_mut().and_then(|p| p.last_mut()) {
                        line.push(Run::Var(slot));
                    }
                }
            }
        }
    };
    let mut rest = tagged;
    while let Some(at) = rest.find("{ruby:") {
        let Some(end) = rest[at..].find('}') else { break };
        plain.push_str(&rest[..at]);
        flush(&mut plain, &mut pages);
        let body = &rest[at + 6..at + end];
        let (base, reading) = body.split_once('|').unwrap_or((body, ""));
        if let Some(line) = pages.last_mut().and_then(|p| p.last_mut()) {
            line.push(Run::Ruby(base.to_string(), reading.to_string()));
        }
        rest = &rest[at + end + 1..];
    }
    plain.push_str(rest);
    flush(&mut plain, &mut pages);
    pages
}

/// Number of characters the name plate is sized for.
fn name_len(speaker: &str) -> usize {
    pages(speaker)
        .first()
        .and_then(|p| p.first())
        .map(|line| {
            line.iter()
                .map(|r| match r {
                    Run::Ruby(base, _) => base.chars().count(),
                    Run::Var(_) => 4,
                    Run::Char(_) => 1,
                })
                .sum()
        })
        .unwrap_or(0)
}

fn load_json(path: &Path) -> Option<serde_json::Value> {
    serde_json::from_str(&std::fs::read_to_string(path).ok()?).ok()
}

fn unhex(hex: &str) -> Vec<u8> {
    (0..hex.len() / 2).filter_map(|i| u8::from_str_radix(hex.get(2 * i..2 * i + 2)?, 16).ok()).collect()
}

/// Pane sizes a `name<N>` animation sets: (pane, width). Each `pai1` entry is the pane name followed by an `FLPA`
/// block whose target byte 8 means "size x" and whose single key holds the value.
fn anim_widths(anim: &serde_json::Value) -> Vec<(String, f32)> {
    let mut out = Vec::new();
    for sec in anim["raw_sections"].as_array().into_iter().flatten().filter(|s| s["magic"] == "pai1") {
        let p = unhex(sec["payload_hex"].as_str().unwrap_or(""));
        let mut i = 0;
        while let Some(pos) = p[i..].windows(4).position(|w| w == b"FLPA") {
            let at = i + pos;
            // the pane name is the 28-byte field ending 8 bytes before the tag
            let name_at = at.saturating_sub(36);
            let name: String = p[name_at..at.saturating_sub(8)].iter().take_while(|b| **b != 0).map(|b| *b as char).collect();
            // FLPA: count, offset, (index, target, curve type), key count, key offset, then the key (frame, value, slope)
            if p.get(at + 13) == Some(&8) && at + 32 <= p.len() {
                let v = f32::from_le_bytes([p[at + 28], p[at + 29], p[at + 30], p[at + 31]]);
                out.push((name, v));
            }
            i = at + 4;
        }
    }
    out
}

/// Sets the width of named panes in a layout JSON (the pane header's size x, payload offset 0x44).
fn resize_panes(layout: &mut serde_json::Value, widths: &[(String, f32)]) {
    let Some(secs) = layout["raw_sections"].as_array_mut() else { return };
    for sec in secs {
        let Some(hex) = sec["payload_hex"].as_str() else { continue };
        if hex.len() < 0x4C * 2 {
            continue;
        }
        let head = unhex(&hex[8..0x1C * 2]);
        let name: String = head.iter().take_while(|b| **b != 0).map(|b| *b as char).collect();
        if let Some((_, w)) = widths.iter().find(|(n, _)| *n == name) {
            let bytes: String = w.to_le_bytes().iter().map(|b| format!("{b:02x}")).collect();
            let patched = format!("{}{}{}", &hex[..0x44 * 2], bytes, &hex[0x48 * 2..]);
            sec["payload_hex"] = serde_json::Value::String(patched);
        }
    }
}

/// Scene key of the Yes / No window (`win_yesno_3d` / `win_yesno_2d`: its place on the screen, the two answers and
/// the cursor are all in the layout itself).
const YESNO: usize = 99;

fn build_scene(root: &Path, mode2d: bool, name_chars: usize) -> Scene {
    let suffix = if mode2d { "2d" } else { "3d" };
    let dir = root.join("game_assets/layouts/arcs/ui").join(format!("common_{suffix}")).join(format!("common_{suffix}"));
    if name_chars == YESNO {
        return match load_json(&dir.join("blyt").join(format!("win_yesno_{suffix}.bflyt.json"))) {
            Some(json) => layout_scene::build(&json, &mut |part| load_json(&dir.join("blyt").join(format!("{part}.bflyt.json")))),
            None => Scene::default(),
        };
    }
    let Some(json) = load_json(&dir.join("blyt").join(format!("win_talk_{suffix}.bflyt.json"))) else {
        return Scene::default();
    };
    let widths = if name_chars > 0 {
        let n = name_chars.clamp(2, 12);
        load_json(&dir.join("anim").join(format!("win_talk_base_{suffix}_name{n}.bflan.json"))).map(|a| anim_widths(&a)).unwrap_or_default()
    } else {
        Vec::new()
    };
    layout_scene::build(&json, &mut |part| {
        let mut v = load_json(&dir.join("blyt").join(format!("{part}.bflyt.json")))?;
        resize_panes(&mut v, &widths);
        Some(v)
    })
}

/// Panes of the window for a line without / with a speaker.
fn wanted(pane: &str, named: bool) -> bool {
    if named {
        matches!(pane, "win_bottom" | "win_left1" | "win_left2" | "txt_name_l" | "txt_l1" | "txt_l" | "icon_next_l")
    } else {
        matches!(pane, "win" | "txt1" | "txt" | "icon_next")
    }
}

struct Fonts<'a> {
    app: &'a mut ViewerApp,
}

impl Fonts<'_> {
    fn get(&mut self, ctx: &egui::Context, name: &str) -> Option<(Arc<GameFont>, Vec<egui::TextureId>)> {
        let root = self.app.dirs.root.clone();
        let font = self.app.panels.editor.talk_preview.fonts.entry(name.to_string()).or_insert_with(|| GameFont::load(&root, name).map(Arc::new)).clone()?;
        let sheets: Vec<egui::TextureId> = font.sheets.iter().filter_map(|p| self.app.font_tex.get(ctx, &self.app.pool, p).map(|h| h.id())).collect();
        (sheets.len() == font.sheets.len()).then_some((font, sheets))
    }
}

/// Glyphs of `text` at `origin` (screen), font pixel scale (sx, sy); returns the advance in screen pixels.
#[allow(clippy::too_many_arguments)]
fn glyphs(meshes: &mut [egui::Mesh], font: &GameFont, text: &str, origin: egui::Pos2, sx: f32, sy: f32, char_space: f32, top: egui::Color32, bottom: egui::Color32) -> f32 {
    let (placed, width) = font.place_line(text, char_space);
    for g in placed {
        let Some(mesh) = meshes.get_mut(g.sheet) else { continue };
        let r = egui::Rect::from_min_max(
            egui::pos2(origin.x + g.rect.min.x * sx, origin.y + g.rect.min.y * sy),
            egui::pos2(origin.x + g.rect.max.x * sx, origin.y + g.rect.max.y * sy),
        );
        let base = mesh.vertices.len() as u32;
        // keep half a texel away from the next cell of the sheet: smoothing would pull in a sliver of its glyph
        let uv = egui::Rect::from_min_max(g.uv.min, g.uv.max - egui::vec2(0.5 / font.sheet_w.max(1.0), 0.5 / font.sheet_h.max(1.0)));
        for (pos, uv, color) in [
            (r.left_top(), uv.left_top(), top),
            (r.right_top(), uv.right_top(), top),
            (r.left_bottom(), uv.left_bottom(), bottom),
            (r.right_bottom(), uv.right_bottom(), bottom),
        ] {
            mesh.vertices.push(egui::epaint::Vertex { pos, uv, color });
        }
        mesh.indices.extend_from_slice(&[base, base + 1, base + 2, base + 2, base + 1, base + 3]);
    }
    width * sx
}

/// What a `{PLAYER}`-like value shows as in the preview.
fn var_text(slot: u8) -> String {
    match dialogues::ARG_NAMES.iter().find(|(_, s)| *s == slot) {
        Some(("PLAYER", _)) => "\u{30a4}\u{30ec}\u{30d6}\u{30f3}".to_string(), // イレブン, the hero's default name
        Some((name, _)) => format!("<{name}>"),
        None => "<?>".to_string(),
    }
}

/// Draws lines of runs into a text pane. Returns (lines that fit the pane, widest line in layout units).
fn draw_lines(painter: &egui::Painter, pane: egui::Rect, text: &TextDraw, font: &GameFont, sheets: &[egui::TextureId], lines: &[Vec<Run>], scale: f32, ruby: bool) -> (usize, f32) {
    if font.height <= 0.0 || font.width <= 0.0 {
        return (0, 0.0);
    }
    let sx = text.size_x / font.width * scale;
    let sy = text.size / font.height * scale;
    let char_space = if sx > 0.0 { text.char_space * scale / sx } else { 0.0 };
    let line_h = font.line_feed * sy + text.line_space * scale;
    let fit = (((pane.height() + text.line_space * scale) / line_h).floor() as usize).max(1);
    let mut meshes: Vec<egui::Mesh> = sheets.iter().map(|id| egui::Mesh::with_texture(*id)).collect();
    let block_h = line_h * lines.len().min(fit) as f32 - text.line_space * scale;
    let y0 = match text.v_align {
        1 => pane.top(),
        2 => pane.bottom() - block_h,
        _ => pane.center().y - block_h / 2.0,
    };
    let mut widest = 0.0f32;
    for (i, line) in lines.iter().enumerate().take(fit) {
        // measure first (alignment), then draw
        let measure = |run: &Run| -> f32 {
            let s = match run {
                Run::Char(c) => c.to_string(),
                Run::Var(slot) => var_text(*slot),
                Run::Ruby(base, _) => base.clone(),
            };
            font.place_line(&s, char_space).1 * sx + char_space * sx
        };
        let width: f32 = line.iter().map(measure).sum();
        widest = widest.max(width / scale.max(0.001));
        let mut x = match text.h_align {
            1 => pane.left(),
            2 => pane.right() - width,
            _ => pane.center().x - width / 2.0,
        };
        let y = y0 + i as f32 * line_h;
        for run in line {
            match run {
                Run::Char(c) => {
                    x += glyphs(&mut meshes, font, &c.to_string(), egui::pos2(x, y), sx, sy, char_space, text.top, text.bottom) + char_space * sx;
                }
                Run::Var(slot) => {
                    let tint = egui::Color32::from_rgb(255, 214, 120);
                    x += glyphs(&mut meshes, font, &var_text(*slot), egui::pos2(x, y), sx, sy, char_space, tint, tint) + char_space * sx;
                }
                Run::Ruby(base, reading) => {
                    let w = glyphs(&mut meshes, font, base, egui::pos2(x, y), sx, sy, char_space, text.top, text.bottom);
                    if !ruby {
                        x += w + char_space * sx;
                        continue;
                    }
                    // the reading: same font at half size, centred above the base
                    let (rx, ry) = (sx * 0.5, sy * 0.5);
                    let rw = font.place_line(reading, 0.0).1 * rx;
                    let top = y - font.height * ry * 0.82;
                    glyphs(&mut meshes, font, reading, egui::pos2(x + (w - rw) / 2.0, top), rx, ry, 0.0, text.top, text.bottom);
                    x += w + char_space * sx;
                }
            }
        }
    }
    for mesh in meshes {
        painter.add(egui::Shape::mesh(mesh));
    }
    (fit, widest)
}

pub struct Shown {
    pub pages: usize,
    /// what the game would do differently from what the author probably wants
    pub notes: Vec<String>,
}

/// Draws message box `page` of `tagged` in the game's talk window, `width` screen pixels wide.
/// `yesno`: the line ends in a Yes / No question, so the answer window is up on the last box.
#[allow(clippy::too_many_arguments)]
pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui, mode2d: bool, speaker: &str, tagged: &str, page: usize, width: f32, yesno: bool) -> Shown {
    let all = pages(tagged);
    let page = page.min(all.len().saturating_sub(1));
    let lines = all.get(page).cloned().unwrap_or_default();
    let named = !speaker.trim().is_empty();
    let key = (mode2d, if named { name_len(speaker).clamp(2, 12) } else { 0 });
    let root = app.dirs.root.clone();
    let scene = app.panels.editor.talk_preview.scenes.entry(key).or_insert_with(|| Arc::new(build_scene(&root, mode2d, key.1))).clone();
    let mut notes = Vec::new();
    let asking = yesno && page + 1 >= all.len();
    let answers = asking.then(|| app.panels.editor.talk_preview.scenes.entry((mode2d, YESNO)).or_insert_with(|| Arc::new(build_scene(&root, mode2d, YESNO))).clone());
    // (quad, belongs to the Yes / No window)
    let quads: Vec<(&layout_scene::Quad, bool)> = scene
        .quads
        .iter()
        .filter(|q| wanted(&q.pane, named))
        .map(|q| (q, false))
        .chain(answers.iter().flat_map(|s| s.quads.iter().filter(|q| q.visible).map(|q| (q, true))))
        .collect();
    if quads.is_empty() {
        ui.label(theme::faint_label("The game's talk window layout is not extracted (game_assets/layouts/arcs/ui/common_3d and common_2d)."));
        return Shown { pages: all.len(), notes };
    }
    // frame the window: its drawn quads, in layout space (y up)
    let mut lo = egui::pos2(f32::MAX, f32::MAX);
    let mut hi = egui::pos2(f32::MIN, f32::MIN);
    for (q, _) in quads.iter().filter(|(q, _)| !q.frame_only && !q.pane.starts_with("icon_next")) {
        for c in q.corners {
            lo = lo.min(c);
            hi = hi.max(c);
        }
    }
    let (bw, bh) = ((hi.x - lo.x).max(1.0), (hi.y - lo.y).max(1.0));
    let margin = 4.0;
    let scale = ((width - 2.0) / (bw + 2.0 * margin)).clamp(0.25, 4.0);
    let (rect, _) = ui.allocate_exact_size(egui::vec2((bw + 2.0 * margin) * scale, (bh + 2.0 * margin) * scale), egui::Sense::hover());
    let painter = ui.painter_at(rect);
    // behind the window: the field would show through the window's own transparency
    painter.rect_filled(rect, 2.0, if mode2d { egui::Color32::from_rgb(52, 84, 52) } else { egui::Color32::from_rgb(58, 74, 96) });
    let to_screen = |p: egui::Pos2| egui::pos2(rect.left() + (p.x - lo.x + margin) * scale, rect.top() + (hi.y - p.y + margin) * scale);
    let ctx = ui.ctx().clone();
    let more = page + 1 < all.len();
    for (q, answer) in &quads {
        let pts = q.corners.map(to_screen);
        if q.pane.starts_with("icon_next") && !more {
            continue;
        }
        if !q.frame_only {
            let texture = q.texture.as_ref().and_then(|name| {
                let path = app.data.as_deref()?.textures.resolve(name)?.path.clone();
                app.layout_tex.get(&ctx, &app.pool, &path).map(|h| h.id())
            });
            if q.texture.is_some() && texture.is_none() {
                ctx.request_repaint();
                continue;
            }
            let mut mesh = match texture {
                Some(id) => egui::Mesh::with_texture(id),
                None => egui::Mesh::default(),
            };
            for i in 0..4 {
                let uv = if texture.is_some() { q.uv[i] } else { egui::pos2(0.0, 0.0) };
                mesh.vertices.push(egui::epaint::Vertex { pos: pts[i], uv, color: q.colors[i] });
            }
            mesh.indices.extend_from_slice(&[0, 1, 2, 2, 1, 3]);
            painter.add(egui::Shape::mesh(mesh));
        }
        let Some(text) = &q.text else { continue };
        let Some(font_name) = &text.font else { continue };
        let Some((font, sheets)) = (Fonts { app: &mut *app }).get(&ctx, font_name) else {
            ctx.request_repaint();
            continue;
        };
        let pane = egui::Rect::from_points(&pts);
        if *answer {
            // "はい" / "いいえ" as the layout has them
            let own = pages(&text.text).into_iter().next().unwrap_or_default();
            draw_lines(&painter, pane, text, &font, &sheets, &own, scale, false);
        } else if q.pane == "txt_name_l" {
            let name_lines = pages(speaker).into_iter().next().unwrap_or_default();
            draw_lines(&painter, pane, text, &font, &sheets, &name_lines[..name_lines.len().min(1)], scale, false);
        } else {
            // the real 2D talk window draws no furigana (emulator screenshot out/emu/probe/e2d_baseline_41289/act0.png,
            // priest line with 神 / 聖 / 加護); 3D mode does
            let ruby = !mode2d;
            if !ruby && lines.iter().flatten().any(|r| matches!(r, Run::Ruby(..))) {
                notes.push("the game's 2D talk window shows no furigana (checked in the emulator); 3D mode does".into());
            }
            let (fit, widest) = draw_lines(&painter, pane, text, &font, &sheets, &lines, scale, ruby);
            if lines.len() > fit {
                notes.push(format!("{} lines in this box: the window shows {fit}, the rest scrolls in after a button press", lines.len()));
            }
            let room = pane.width() / scale;
            if widest > room + 0.5 {
                notes.push(format!("the widest line is {widest:.0} px, the text pane is {room:.0} px wide: it runs out of the window"));
            }
            let missing: Vec<char> = lines
                .iter()
                .flatten()
                .flat_map(|r| match r {
                    Run::Char(c) => vec![*c],
                    Run::Ruby(b, r) => b.chars().chain(r.chars()).collect(),
                    Run::Var(_) => Vec::new(),
                })
                .filter(|c| !c.is_whitespace() && font.glyph(*c).is_none())
                .collect();
            if !missing.is_empty() {
                let mut list: Vec<char> = missing;
                list.sort();
                list.dedup();
                notes.push(format!("not in the game's font {}: {}", font_name.trim_end_matches(".bffnt"), list.iter().collect::<String>()));
            }
        }
    }
    Shown { pages: all.len(), notes }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pages_keep_ruby_and_break_lines() {
        let p = pages("\u{300c}{PLAYER}{CR}\n\u{3000}{ruby:\u{6226}|\u{305f}\u{305f}\u{304b}}\u{3046}{PAGE}b");
        assert_eq!(p.len(), 2);
        assert_eq!(p[0].len(), 2);
        assert!(matches!(p[0][0][1], Run::Var(_)));
        assert_eq!(p[0][1][1], Run::Ruby("\u{6226}".into(), "\u{305f}\u{305f}\u{304b}".into()));
        assert_eq!(name_len("\u{30cb}\u{30de}{ruby:\u{5927}\u{5e2b}|\u{305f}\u{3044}\u{3057}}"), 4);
    }

    #[test]
    fn name_animation_sets_plate_widths() {
        let root = crate::utils::Dirs::detect().root;
        let path = root.join("game_assets/layouts/arcs/ui/common_3d/common_3d/anim/win_talk_base_3d_name5.bflan.json");
        let Some(anim) = load_json(&path) else { return };
        let w = anim_widths(&anim);
        assert!(w.contains(&("win_left1".to_string(), 103.0)), "{w:?}");
        assert!(w.contains(&("win_left2".to_string(), 255.0)), "{w:?}");
    }
}


