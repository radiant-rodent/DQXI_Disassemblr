//! Shared UI helpers: text views with syntax colouring, JSON tree, images.

pub mod asset_jobs;
pub mod panels;
pub mod shell;
pub mod tour;

use std::collections::HashMap;

use eframe::egui;

use crate::theme;

// ---------------------------------------------------------------------------
// headers and key/value rows
// ---------------------------------------------------------------------------
pub fn section_header(ui: &mut egui::Ui, title: &str, subtitle: &str) {
    ui.label(theme::heading(title));
    if !subtitle.is_empty() {
        ui.label(theme::faint_label(subtitle));
    }
    ui.add_space(2.0);
}

pub fn kv_rows(ui: &mut egui::Ui, rows: &[(&str, String)]) {
    egui::Grid::new(ui.next_auto_id())
        .num_columns(2)
        .spacing([12.0, 3.0])
        .striped(true)
        .show(ui, |ui| {
            for (key, value) in rows {
                ui.label(theme::faint_label(*key));
                ui.label(egui::RichText::new(value).color(theme::TEXT).size(12.0));
                ui.end_row();
            }
        });
}

// ---------------------------------------------------------------------------
// syntax highlighting
// ---------------------------------------------------------------------------
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Lang {
    Plain,
    C,
    Asm,
    Nut,
    Json,
}

impl Lang {
    pub fn from_ext(ext: &str) -> Self {
        match ext.to_ascii_lowercase().as_str() {
            "c" | "h" | "cpp" => Lang::C,
            "s" | "asm" => Lang::Asm,
            "nut" => Lang::Nut,
            "json" => Lang::Json,
            _ => Lang::Plain,
        }
    }
}

fn is_ident(c: char) -> bool {
    c.is_alphanumeric() || c == '_' || c == '.' || c == '$'
}

/// Colour one source line into an egui layout job.
pub fn highlight_line(line: &str, lang: Lang) -> egui::text::LayoutJob {
    let mut job = egui::text::LayoutJob::default();
    job.wrap.max_width = f32::INFINITY;
    let font = egui::FontId::monospace(12.5);
    let push = |job: &mut egui::text::LayoutJob, text: &str, color: egui::Color32| {
        if text.is_empty() {
            return;
        }
        job.append(
            text,
            0.0,
            egui::TextFormat {
                font_id: font.clone(),
                color,
                ..Default::default()
            },
        );
    };
    if lang == Lang::Plain {
        push(&mut job, line, theme::MONO);
        return job;
    }

    let chars: Vec<char> = line.chars().collect();
    let mut i = 0usize;
    while i < chars.len() {
        let c = chars[i];
        // comments
        let comment = match lang {
            Lang::Asm => c == '@' || (c == '/' && chars.get(i + 1) == Some(&'/')),
            Lang::Nut => c == '/' && chars.get(i + 1) == Some(&'/'),
            _ => (c == '/' && chars.get(i + 1) == Some(&'/'))
                || (c == '/' && chars.get(i + 1) == Some(&'*')),
        };
        if comment {
            let rest: String = chars[i..].iter().collect();
            push(&mut job, &rest, theme::COL_COMMENT);
            break;
        }
        if c == '#' && lang == Lang::C {
            let rest: String = chars[i..].iter().collect();
            push(&mut job, &rest, theme::COL_COMMENT);
            break;
        }
        // strings
        if c == '"' || (c == '\'' && lang != Lang::C) {
            let quote = c;
            let mut j = i + 1;
            while j < chars.len() && chars[j] != quote {
                j += 1;
            }
            let text: String = chars[i..(j + 1).min(chars.len())].iter().collect();
            push(&mut job, &text, theme::COL_STRING);
            i = j + 1;
            continue;
        }
        // numbers (incl. 0x)
        if c.is_ascii_digit() {
            let mut j = i;
            while j < chars.len()
                && (chars[j].is_ascii_hexdigit() || matches!(chars[j], 'x' | '.' | 'f' | 'u' | 'l'))
            {
                j += 1;
            }
            let text: String = chars[i..j].iter().collect();
            let color = if text.starts_with("0x") {
                theme::COL_ADDR
            } else {
                theme::COL_NUMBER
            };
            push(&mut job, &text, color);
            i = j;
            continue;
        }
        if c.is_alphabetic() || c == '_' || c == '.' || c == '$' {
            let mut j = i;
            while j < chars.len() && is_ident(chars[j]) {
                j += 1;
            }
            let word: String = chars[i..j].iter().collect();
            let lower = word.to_lowercase();
            let color = if KEYWORDS.contains(&lower.as_str()) {
                theme::COL_KEYWORD
            } else if TYPES.contains(&lower.as_str()) {
                theme::COL_TYPE
            } else if lang == Lang::Asm && ASM_WORDS.contains(&lower.as_str()) {
                theme::COL_KEYWORD
            } else if lang == Lang::Json && JSON_LITERALS.contains(&lower.as_str()) {
                theme::COL_KEYWORD
            } else {
                theme::MONO
            };
            push(&mut job, &word, color);
            i = j;
            continue;
        }
        push(&mut job, &c.to_string(), theme::COL_PUNCT);
        i += 1;
    }
    job
}

const KEYWORDS: &[&str] = &[
    "if", "else", "for", "while", "return", "goto", "switch", "case", "default", "break",
    "continue", "struct", "union", "enum", "typedef", "static", "const", "volatile", "extern",
    "inline", "void", "sizeof", "do", "using", "namespace", "class", "template", "new", "delete",
    "nullptr", "true", "false", "def", "elif", "import", "from", "as", "with", "lambda", "none",
    "not", "and", "or", "in", "is", "pass", "yield", "raise", "try", "except", "finally", "global",
    "assert", "del", "print", "function", "local", "foreach", "table", "this", "typeof", "clone",
    "resume", "base", "constructor", "class",
];
const TYPES: &[&str] = &[
    "u8", "u16", "u32", "u64", "s8", "s16", "s32", "s64", "f32", "f64", "int", "long", "short",
    "char", "float", "double", "unsigned", "signed", "size_t", "bool", "result", "str", "bytes",
    "list", "dict", "tuple", "set", "object", "int8_t", "uint8_t", "int16_t", "uint16_t",
    "int32_t", "uint32_t", "int64_t", "uint64_t",
];
const ASM_WORDS: &[&str] = &[
    "push", "pop", "mov", "movs", "movw", "ldr", "str", "add", "sub", "b", "bl", "bx", "blx", "cmp",
    "bne", "beq", "nop", "mvn", "lsl", "lsr", "and", "orr", "eor", "cbz", "cbnz", "it", "section",
    "global", "word", "byte", "align",
];
const JSON_LITERALS: &[&str] = &["true", "false", "null"];

// ---------------------------------------------------------------------------
// text view (virtualised, with line numbers)
// ---------------------------------------------------------------------------
pub struct TextState {
    pub lang: Lang,
    pub lines: Vec<String>,
    pub find: String,
    pub find_regions: Vec<(usize, std::ops::Range<usize>)>,
    pub scroll_to: Option<usize>,
    pub lines_count: usize,
}

impl Default for TextState {
    fn default() -> Self {
        Self {
            lang: Lang::Plain,
            lines: Vec::new(),
            find: String::new(),
            find_regions: Vec::new(),
            scroll_to: None,
            lines_count: 0,
        }
    }
}

impl TextState {
    pub fn set(&mut self, text: &str, lang: Lang) {
        self.lines = text.lines().map(|l| l.to_string()).collect();
        self.lang = lang;
        self.lines_count = self.lines.len();
        self.find_regions.clear();
    }
}

pub fn text_view(ui: &mut egui::Ui, id: &str, state: &TextState, line_numbers: bool) {
    // Source/dialogue views are intentionally copyable, unlike list rows.
    ui.style_mut().interaction.selectable_labels = true;
    let row_height = 15.0;
    let total = state.lines.len();
    let gutter = if line_numbers { 62.0 } else { 0.0 };
    let mut scroll = egui::ScrollArea::vertical().id_salt(id).auto_shrink([false, false]);
    if let Some(line) = state.scroll_to {
        scroll = scroll.vertical_scroll_offset((line as f32 / total.max(1) as f32) * total as f32 * row_height);
    }
    scroll.show_rows(ui, row_height, total, |ui, range| {
        for index in range {
            let line = &state.lines[index];
            let layout = highlight_line(line, state.lang);
            if line_numbers {
                ui.horizontal(|ui| {
                    ui.add_sized(
                        [gutter - 8.0, row_height],
                        egui::Label::new(
                            egui::RichText::new(format!("{}", index + 1))
                                .monospace()
                                .color(theme::TEXT_FAINT)
                                .size(11.0),
                        ),
                    );
                    ui.label(layout);
                });
            } else {
                ui.label(layout);
            }
        }
    });
}

// ---------------------------------------------------------------------------
// JSON tree
// ---------------------------------------------------------------------------
pub fn json_tree(ui: &mut egui::Ui, value: &serde_json::Value, id: &str, depth: usize) {
    match value {
        serde_json::Value::Object(map) => {
            if map.is_empty() {
                ui.label(theme::faint_label("{}"));
                return;
            }
            let mut shown = 0;
            for (key, child) in map {
                if shown >= 400 {
                    ui.label(theme::faint_label(format!("\u{2026} {} more fields", map.len() - shown)));
                    break;
                }
                shown += 1;
                tree_entry(ui, key, child, &format!("{id}/{key}"), depth);
            }
        }
        serde_json::Value::Array(items) => {
            let mut shown = 0;
            for (i, child) in items.iter().enumerate() {
                if shown >= 400 {
                    ui.label(theme::faint_label(format!("\u{2026} {} more items", items.len() - shown)));
                    break;
                }
                shown += 1;
                tree_entry(ui, &format!("[{i}]"), child, &format!("{id}/{i}"), depth);
            }
        }
        other => {
            ui.label(scalar_text(other));
        }
    }
}

fn tree_entry(ui: &mut egui::Ui, key: &str, value: &serde_json::Value, id: &str, depth: usize) {
    match value {
        serde_json::Value::Object(map) => {
            egui::CollapsingHeader::new(
                egui::RichText::new(format!("{key}  {{{}}}", map.len())).color(theme::INFO),
            )
            .id_salt(id)
            .default_open(depth < 2)
            .show(ui, |ui| json_tree(ui, value, id, depth + 1));
        }
        serde_json::Value::Array(items) => {
            egui::CollapsingHeader::new(
                egui::RichText::new(format!("{key}  [{}]", items.len())).color(theme::INFO),
            )
            .id_salt(id)
            .default_open(depth < 2)
            .show(ui, |ui| json_tree(ui, value, id, depth + 1));
        }
        other => {
            ui.horizontal(|ui| {
                ui.label(egui::RichText::new(key).color(theme::TEXT_DIM).size(12.0));
                ui.label(scalar_text(other));
            });
        }
    }
}

fn scalar_text(value: &serde_json::Value) -> egui::RichText {
    match value {
        serde_json::Value::String(s) => {
            egui::RichText::new(format!("\"{}\"", crate::utils::elide(s, 160)))
                .color(theme::COL_STRING)
                .size(12.0)
        }
        serde_json::Value::Number(n) => egui::RichText::new(n.to_string())
            .color(theme::COL_NUMBER)
            .size(12.0),
        serde_json::Value::Bool(b) => egui::RichText::new(b.to_string())
            .color(theme::COL_KEYWORD)
            .size(12.0),
        serde_json::Value::Null => theme::faint_label("null"),
        other => theme::dim_label(other.to_string()),
    }
}

// ---------------------------------------------------------------------------
// images
// ---------------------------------------------------------------------------
pub fn image_widget<'a>(
    handle: &'a egui::TextureHandle,
    size: egui::Vec2,
) -> egui::Image<'a> {
    egui::Image::from_texture(egui::load::SizedTexture::new(handle.id(), size))
}

/// Tiled thumbnail grid; returns the clicked index (if any).
pub fn thumb_grid(
    ui: &mut egui::Ui,
    id: &str,
    count: usize,
    cell: egui::Vec2,
    mut draw_cell: impl FnMut(&mut egui::Ui, usize, egui::Rect),
) -> Option<usize> {
    let mut clicked = None;
    let spacing = 8.0;
    let columns = ((ui.available_width() + spacing) / (cell.x + spacing)).floor().max(1.0) as usize;
    let rows = count.div_ceil(columns);
    let row_height = cell.y + spacing + 16.0;
    egui::ScrollArea::vertical()
        .id_salt(id)
        .auto_shrink([false, false])
        .show_rows(ui, row_height, rows, |ui, range| {
            for row in range {
                ui.horizontal(|ui| {
                    for col in 0..columns {
                        let index = row * columns + col;
                        if index >= count {
                            break;
                        }
                        let (rect, response) = ui.allocate_exact_size(cell, egui::Sense::click());
                        draw_cell(ui, index, rect);
                        if response.clicked() {
                            clicked = Some(index);
                        }
                        if response.double_clicked() {
                            clicked = Some(index);
                        }
                    }
                });
            }
        });
    clicked
}

/// Zoomable, pannable image pane.
pub struct ImagePaneState {
    pub zoom: f32,
    pub offset: egui::Vec2,
    pub fit: bool,
}

impl Default for ImagePaneState {
    fn default() -> Self {
        Self {
            zoom: 1.0,
            offset: egui::Vec2::ZERO,
            fit: true,
        }
    }
}

pub fn image_pane(
    ui: &mut egui::Ui,
    handle: &egui::TextureHandle,
    state: &mut ImagePaneState,
    background: egui::Color32,
) -> egui::Response {
    let size = ui.available_size();
    let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click_and_drag());
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 0.0, background);
    let tex_size = handle.size_vec2();
    if tex_size.x <= 0.0 || tex_size.y <= 0.0 {
        return response;
    }
    if state.fit {
        let scale = ((rect.width() - 12.0) / tex_size.x)
            .min((rect.height() - 12.0) / tex_size.y)
            .min(8.0);
        state.zoom = scale.max(0.01);
    }
    if response.dragged() {
        state.offset += response.drag_delta();
        state.fit = false;
    }
    let scroll = ui.input(|i| i.smooth_scroll_delta.y);
    if response.hovered() && scroll != 0.0 {
        let pointer = ui.input(|i| i.pointer.hover_pos());
        wheel_zoom(&mut state.zoom, &mut state.offset, scroll, rect.center(), pointer);
        state.fit = false;
    }
    if response.double_clicked() {
        state.fit = true;
        state.offset = egui::Vec2::ZERO;
    }
    let draw_size = tex_size * state.zoom;
    let center = rect.center() + state.offset;
    let draw_rect = egui::Rect::from_center_size(center, draw_size);
    let uv = egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(1.0, 1.0));
    painter.image(handle.id(), draw_rect, uv, egui::Color32::WHITE);
    response
}

/// Mouse-wheel zoom for 2D views drawn at `origin + offset` with scale `zoom`.
///
/// egui spreads one wheel notch over several frames of `smooth_scroll_delta`, so the factor
/// follows the distance scrolled (about 10% per notch) instead of a fixed step per frame, which
/// used to jump from very close to very far in one notch. The point under the pointer stays put.
pub fn wheel_zoom(zoom: &mut f32, offset: &mut egui::Vec2, scroll: f32, origin: egui::Pos2,
                  pointer: Option<egui::Pos2>) {
    let old = *zoom;
    let new = (old * wheel_zoom_factor(scroll)).clamp(0.02, 16.0);
    if let Some(p) = pointer {
        let centre = origin + *offset;
        *offset = (p - origin) - (p - centre) * (new / old);
    }
    *zoom = new;
}

pub fn wheel_zoom_factor(scroll: f32) -> f32 {
    (scroll * 0.002).exp()
}

/// Waveform drawn straight onto the painter.
/// Min/max waveform. `playhead` (0..1) draws the current position; the
/// response is click-and-drag sensitive so callers can seek with
/// [`waveform_seek_fraction`].
pub fn waveform(
    ui: &mut egui::Ui,
    mins: &[f32],
    maxs: &[f32],
    duration: f32,
    playhead: Option<f32>,
) -> egui::Response {
    let size = ui.available_size();
    let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click_and_drag());
    let painter = ui.painter_at(rect);
    painter.rect_filled(rect, 0.0, theme::BG_INPUT);
    let mid = rect.center().y;
    painter.line_segment(
        [egui::pos2(rect.left() + 4.0, mid), egui::pos2(rect.right() - 4.0, mid)],
        egui::Stroke::new(1.0, theme::BORDER),
    );
    if mins.is_empty() {
        painter.text(
            rect.center(),
            egui::Align2::CENTER_CENTER,
            "no waveform",
            egui::FontId::proportional(12.0),
            theme::TEXT_FAINT,
        );
        return response;
    }
    // One filled rect per whole pixel column, each spanning the min/max of the
    // bins it covers: no sub-pixel line positions, so no anti-aliasing seams.
    let left = rect.left() + 4.0;
    let columns = ((rect.width() - 8.0).floor() as usize).max(1);
    let scale = rect.height() * 0.42;
    let bins = mins.len().min(maxs.len());
    for c in 0..columns {
        let from = c * bins / columns;
        let to = (((c + 1) * bins).div_ceil(columns)).clamp(from + 1, bins);
        let mut lo = f32::MAX;
        let mut hi = f32::MIN;
        for i in from..to {
            lo = lo.min(mins[i]);
            hi = hi.max(maxs[i]);
        }
        let x = (left + c as f32).round();
        let top = mid - hi * scale;
        let bottom = (mid - lo * scale).max(top + 1.0);
        painter.rect_filled(
            egui::Rect::from_min_max(egui::pos2(x, top), egui::pos2(x + 1.0, bottom)),
            0.0,
            theme::INFO,
        );
    }
    if let Some(fraction) = playhead {
        let x = rect.left() + 4.0 + fraction.clamp(0.0, 1.0) * (rect.width() - 8.0);
        painter.line_segment(
            [egui::pos2(x, rect.top() + 2.0), egui::pos2(x, rect.bottom() - 18.0)],
            egui::Stroke::new(2.0, theme::ACCENT),
        );
    }
    if response.hovered() {
        ui.ctx().set_cursor_icon(egui::CursorIcon::PointingHand);
    }
    if duration > 0.0 {
        for fraction in [0.0f32, 0.25, 0.5, 0.75, 1.0] {
            let x = rect.left() + 4.0 + fraction * (rect.width() - 8.0);
            painter.line_segment(
                [egui::pos2(x, rect.bottom() - 16.0), egui::pos2(x, rect.bottom() - 10.0)],
                egui::Stroke::new(1.0, theme::BORDER_LIGHT),
            );
            let seconds = duration * fraction;
            painter.text(
                egui::pos2(x, rect.bottom() - 9.0),
                egui::Align2::CENTER_TOP,
                format!("{}:{:02}", (seconds as u32) / 60, (seconds as u32) % 60),
                egui::FontId::proportional(10.0),
                theme::TEXT_FAINT,
            );
        }
    }
    response
}

/// Where (0..1) a click or drag on a [`waveform`] landed, if it did.
pub fn waveform_seek_fraction(response: &egui::Response) -> Option<f32> {
    if !(response.clicked() || response.dragged()) {
        return None;
    }
    let pos = response.interact_pointer_pos()?;
    let rect = response.rect;
    Some(((pos.x - rect.left() - 4.0) / (rect.width() - 8.0).max(1.0)).clamp(0.0, 1.0))
}

pub type LayoutCache = HashMap<usize, egui::text::LayoutJob>;


#[cfg(test)]
mod zoom_tests {
    use super::*;

    #[test]
    fn a_wheel_notch_zooms_the_same_however_it_is_split_into_frames() {
        let whole = wheel_zoom_factor(50.0);
        let split = wheel_zoom_factor(20.0) * wheel_zoom_factor(20.0) * wheel_zoom_factor(10.0);
        assert!((whole - split).abs() < 1e-5);
        assert!(whole > 1.05 && whole < 1.2, "one notch should be a small step, got {whole}");
    }

    #[test]
    fn the_point_under_the_pointer_stays_put() {
        let (origin, pointer) = (egui::pos2(100.0, 100.0), egui::pos2(160.0, 70.0));
        let (mut zoom, mut offset) = (2.0, egui::vec2(10.0, -5.0));
        let before = (pointer - (origin + offset)) / zoom; // layout point under the pointer
        wheel_zoom(&mut zoom, &mut offset, -120.0, origin, Some(pointer));
        let after = (pointer - (origin + offset)) / zoom;
        assert!((before - after).length() < 1e-3);
    }
}

// ---------------------------------------------------------------------------
// keyboard navigation for lists
// ---------------------------------------------------------------------------

/// Up/Down/PageUp/PageDown/Home/End over a list: the newly selected item and its
/// row, or `None` when no navigation key was pressed (or a text field has focus).
pub fn list_nav<T: PartialEq + Clone>(ctx: &egui::Context, list: &[T], selected: Option<&T>) -> Option<(T, usize)> {
    if list.is_empty() || ctx.egui_wants_keyboard_input() {
        return None;
    }
    let (up, down, page_up, page_down, home, end) = ctx.input(|i| {
        (
            i.key_pressed(egui::Key::ArrowUp),
            i.key_pressed(egui::Key::ArrowDown),
            i.key_pressed(egui::Key::PageUp),
            i.key_pressed(egui::Key::PageDown),
            i.key_pressed(egui::Key::Home),
            i.key_pressed(egui::Key::End),
        )
    });
    if !(up || down || page_up || page_down || home || end) {
        return None;
    }
    let last = list.len() - 1;
    let current = selected.and_then(|s| list.iter().position(|x| x == s));
    let row = match current {
        None => {
            if end || up || page_up {
                last
            } else {
                0
            }
        }
        Some(c) => {
            if home {
                0
            } else if end {
                last
            } else if down {
                (c + 1).min(last)
            } else if up {
                c.saturating_sub(1)
            } else if page_down {
                (c + 15).min(last)
            } else {
                c.saturating_sub(15)
            }
        }
    };
    Some((list[row].clone(), row))
}

/// Lets a keyboard move scroll a table to the selected row.
pub trait TableNav {
    fn nav_scroll(self, row: Option<usize>) -> Self;
}

impl TableNav for egui_extras::TableBuilder<'_> {
    fn nav_scroll(self, row: Option<usize>) -> Self {
        match row {
            Some(r) => self.scroll_to_row(r, None),
            None => self,
        }
    }
}
