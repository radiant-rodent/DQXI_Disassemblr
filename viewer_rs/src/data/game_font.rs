//! The game's BFFNT fonts as exported by `tools/font_tool.py` (`game_assets/fonts/`):
//! glyph sheets plus a glyph map, so layout text can be drawn with the real glyphs.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use eframe::egui::{Pos2, Rect};

#[derive(Clone, Debug)]
pub struct Glyph {
    pub index: u32,
    pub left: f32,
    pub glyph_w: f32,
    pub char_w: f32,
}

#[derive(Clone, Debug)]
pub struct GameFont {
    pub cell_w: f32,
    pub cell_h: f32,
    pub cols: u32,
    pub rows: u32,
    pub sheet_w: f32,
    pub sheet_h: f32,
    pub line_feed: f32,
    pub width: f32,
    pub height: f32,
    pub sheets: Vec<PathBuf>,
    default: Glyph,
    glyphs: HashMap<u32, Glyph>,
}

/// One glyph placed in text space: `rect` in font pixels from the line origin
/// (y-down), `uv` on sheet `sheet`.
pub struct Placed {
    pub sheet: usize,
    pub rect: Rect,
    pub uv: Rect,
}

impl GameFont {
    /// `font` is the layout's font name (`2D9.bffnt`); None when it was not exported.
    pub fn load(root: &Path, font: &str) -> Option<GameFont> {
        let stem = Path::new(font).file_stem()?.to_string_lossy().into_owned();
        let dir = root.join("game_assets").join("fonts");
        let meta: serde_json::Value =
            serde_json::from_str(&std::fs::read_to_string(dir.join(format!("{stem}.font.json"))).ok()?).ok()?;
        let num = |k: &str| meta.get(k).and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
        let triple = |v: &serde_json::Value, i: usize| v.get(i).and_then(|x| x.as_f64()).unwrap_or(0.0) as f32;
        let d = meta.get("default").cloned().unwrap_or_default();
        let glyphs = meta
            .get("glyphs")
            .and_then(|g| g.as_object())
            .map(|g| {
                g.iter()
                    .filter_map(|(cp, v)| {
                        Some((
                            cp.parse::<u32>().ok()?,
                            Glyph { index: v.get(0)?.as_u64()? as u32, left: triple(v, 1), glyph_w: triple(v, 2), char_w: triple(v, 3) },
                        ))
                    })
                    .collect()
            })
            .unwrap_or_default();
        let sheets = (0..num("sheets") as usize).map(|i| dir.join(format!("{stem}_sheet{i}.png"))).collect();
        Some(GameFont {
            cell_w: num("cell_w"),
            cell_h: num("cell_h"),
            cols: num("cols") as u32,
            rows: num("rows") as u32,
            sheet_w: num("sheet_w"),
            sheet_h: num("sheet_h"),
            line_feed: num("line_feed"),
            width: num("width"),
            height: num("height"),
            sheets,
            default: Glyph { index: 0, left: triple(&d, 0), glyph_w: triple(&d, 1), char_w: triple(&d, 2) },
            glyphs,
        })
    }

    pub fn glyph(&self, ch: char) -> Option<&Glyph> {
        self.glyphs.get(&(ch as u32))
    }

    /// Advance of one character in font pixels.
    pub fn advance(&self, ch: char) -> f32 {
        self.glyph(ch).unwrap_or(&self.default).char_w
    }

    /// Glyphs of one line, starting at x = 0 (font pixels, `char_space` in font pixels).
    pub fn place_line(&self, line: &str, char_space: f32) -> (Vec<Placed>, f32) {
        let mut x = 0.0;
        let mut out = Vec::new();
        let per_sheet = (self.cols * self.rows).max(1);
        for ch in line.chars() {
            let Some(g) = self.glyph(ch) else {
                x += self.default.char_w + char_space;
                continue;
            };
            let sheet = (g.index / per_sheet) as usize;
            let cell = g.index % per_sheet;
            let (cx, cy) = ((cell % self.cols) as f32 * (self.cell_w + 1.0), (cell / self.cols) as f32 * (self.cell_h + 1.0));
            // The DQXI sheets store each glyph with its left bearing already in the cell
            // (ink spans columns 0..left+glyph_w), so the whole cell goes at the pen position.
            if g.glyph_w > 0.0 {
                out.push(Placed {
                    sheet,
                    rect: Rect::from_min_size(Pos2::new(x, 0.0), eframe::egui::vec2(self.cell_w, self.cell_h)),
                    uv: Rect::from_min_max(
                        Pos2::new(cx / self.sheet_w, cy / self.sheet_h),
                        Pos2::new((cx + self.cell_w) / self.sheet_w, (cy + self.cell_h) / self.sheet_h),
                    ),
                });
            }
            x += g.char_w + char_space;
        }
        (out, (x - char_space).max(0.0))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn battle_font_places_kana() {
        let root = crate::utils::Dirs::detect().root;
        let Some(font) = GameFont::load(&root, "2D9.bffnt") else { return };
        assert_eq!(font.cell_w, 10.0);
        assert!(font.glyph('あ').is_some(), "2D9 draws hiragana");
        let (glyphs, width) = font.place_line("行動内容を見る", 0.0);
        assert_eq!(glyphs.len(), 7);
        assert!(width > 50.0 && width < 90.0, "seven ~10px glyphs, got {width}");
        assert!(glyphs.iter().all(|g| g.uv.max.x <= 1.0 && g.uv.max.y <= 1.0));
    }
}
