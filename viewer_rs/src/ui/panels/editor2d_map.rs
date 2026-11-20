//! Tile and collision data of the Level Editor's 2D view (the editable part of the map itself).
//!
//! * Tiles: `game_assets/maps2d/<background>/` from `python tools/map2d.py export`: `chipmap.json` (grids, layers,
//!   chips), `indices.bin` (the CHIP file's Indices section: u16 chip id per cell, layer after layer) and the two
//!   tile sheets per time of day (`rgb_<time>.png` 16 px ground tiles, `rgba_<time>.png` 8 px overlay tiles).
//!   The map picture is composed here from those, so a changed cell shows at once.
//! * Collision: the walk grids of `level2d/<level>/leveldmap.bxon`, listed in `scene2d.json` under `collision`
//!   (one flag byte per 8 px cell, bit 1 = blocked).
//!
//! Saving: the changed cells go into the `level2d` section of the project file as `tiles` (index in Indices, chip)
//! and `cells` (file offset of the flag byte, value); `tools/asset_replace.py` writes them into the `.chp` and
//! `leveldmap.bxon` with same-size writes and stages `2d/bg/<background>.pack` and `level2d/<level>.pack`.

use std::path::Path;

use eframe::egui;

pub const EMPTY: u16 = 0xFFFF;

#[derive(Clone, Copy, Debug)]
pub struct Layer {
    /// 16 px ground layer (rgb sheet) or 8 px overlay layer (rgba sheet)
    pub base: bool,
    /// first index of the layer in `ids`
    pub start: usize,
}

/// Cell grid of a layer in map pixels.
#[derive(Clone, Copy, Debug)]
pub struct Geom {
    pub cell: usize,
    pub ox: usize,
    pub oy: usize,
    pub cols: usize,
    pub rows: usize,
}

pub struct TileMap {
    pub bg: String,
    pub width: usize,
    pub height: usize,
    base: (usize, usize),
    overlay: (usize, usize, usize, usize),
    pub layers: Vec<Layer>,
    /// per chip: sheet column, sheet row, attribute, animation, flags
    pub chips: Vec<[u8; 5]>,
    pub ids: Vec<u16>,
    pub original: Vec<u16>,
    /// chips of the game file; the ones behind them were created in the editor (a sheet tile in an orientation the
    /// map did not have) and are appended to the map's chip table on save
    pub retail_chips: usize,
    rgb: Option<egui::ColorImage>,
    rgba: Option<egui::ColorImage>,
    pub rgb_tex: Option<egui::TextureHandle>,
    pub rgba_tex: Option<egui::TextureHandle>,
    pub time: String,
    image: egui::ColorImage,
    pub tex: Option<egui::TextureHandle>,
    /// show only this layer
    pub solo: Option<usize>,
}

fn load_sheet(dir: &Path, kind: &str, time: &str) -> Option<egui::ColorImage> {
    [time, "daytime"].iter().find_map(|t| {
        let img = crate::utils::decode_image(&dir.join(format!("{kind}_{t}.png")), None).ok()?;
        // a 16x16 sheet is the placeholder of a time of day the map has no tiles for
        (img.size[0] > 16).then_some(img)
    })
}

impl TileMap {
    pub fn load(ctx: &egui::Context, root: &Path, bg: &str, time: &str) -> Option<Self> {
        let dir = root.join("game_assets/maps2d").join(bg);
        let meta: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(dir.join("chipmap.json")).ok()?).ok()?;
        let n = |v: &serde_json::Value| v.as_u64().unwrap_or(0) as usize;
        let raw = std::fs::read(dir.join("indices.bin")).ok()?;
        let ids: Vec<u16> = raw.chunks_exact(2).map(|c| u16::from_le_bytes([c[0], c[1]])).collect();
        let layers: Vec<Layer> = meta["layers"]
            .as_array()?
            .iter()
            .map(|l| Layer { base: l["kind"].as_str() == Some("base"), start: n(&l["start"]) })
            .collect();
        let chips: Vec<[u8; 5]> = meta["chips"]
            .as_array()?
            .iter()
            .map(|c| {
                let mut out = [0u8; 5];
                for (i, slot) in out.iter_mut().enumerate() {
                    *slot = c.get(i).and_then(|v| v.as_u64()).unwrap_or(0) as u8;
                }
                out
            })
            .collect();
        let (width, height) = (n(&meta["width"]), n(&meta["height"]));
        let mut map = Self {
            bg: bg.to_string(),
            width,
            height,
            base: (n(&meta["base"][0]), n(&meta["base"][1])),
            overlay: (n(&meta["overlay"][0]), n(&meta["overlay"][1]), n(&meta["overlay"][2]), n(&meta["overlay"][3])),
            layers,
            chips,
            original: ids.clone(),
            ids,
            retail_chips: 0,
            rgb: None,
            rgba: None,
            rgb_tex: None,
            rgba_tex: None,
            time: String::new(),
            image: egui::ColorImage::filled([width.max(1), height.max(1)], egui::Color32::BLACK),
            tex: None,
            solo: None,
        };
        // a layer must fit into the index list
        map.layers.retain(|l| {
            let g = if l.base { (map.base.0, map.base.1) } else { (map.overlay.2, map.overlay.3) };
            l.start + g.0 * g.1 <= map.ids.len()
        });
        map.retail_chips = map.chips.len();
        map.set_time(ctx, root, time);
        Some(map)
    }

    /// Loads the tile sheets of a time of day and redraws the whole map.
    pub fn set_time(&mut self, ctx: &egui::Context, root: &Path, time: &str) {
        if self.time == time && self.tex.is_some() {
            return;
        }
        self.time = time.to_string();
        let dir = root.join("game_assets/maps2d").join(&self.bg);
        self.rgb = load_sheet(&dir, "rgb", time);
        self.rgba = load_sheet(&dir, "rgba", time);
        self.rgb_tex = self.rgb.clone().map(|i| ctx.load_texture(format!("map2d/{}/rgb", self.bg), i, egui::TextureOptions::NEAREST));
        self.rgba_tex = self.rgba.clone().map(|i| ctx.load_texture(format!("map2d/{}/rgba", self.bg), i, egui::TextureOptions::NEAREST));
        self.redraw(ctx);
    }

    pub fn redraw(&mut self, ctx: &egui::Context) {
        self.compose(0, 0, self.width, self.height);
        self.tex = Some(ctx.load_texture(format!("map2d/{}/map", self.bg), self.image.clone(), egui::TextureOptions::NEAREST));
    }

    pub fn geom(&self, layer: usize) -> Geom {
        match self.layers.get(layer) {
            Some(l) if !l.base => Geom { cell: 8, ox: self.overlay.0, oy: self.overlay.1, cols: self.overlay.2, rows: self.overlay.3 },
            _ => Geom { cell: 16, ox: 0, oy: 0, cols: self.base.0, rows: self.base.1 },
        }
    }

    pub fn layer_name(&self, layer: usize) -> String {
        let Some(l) = self.layers.get(layer) else { return String::new() };
        let nth = self.layers[..layer].iter().filter(|o| o.base == l.base).count() + 1;
        if l.base {
            if nth == 1 { "Ground (16 px)".into() } else { format!("Ground {nth} (16 px)") }
        } else {
            format!("Overlay {nth} (8 px)")
        }
    }

    /// Cell of a layer under a map pixel.
    pub fn cell_at(&self, layer: usize, px: f32, py: f32) -> Option<(usize, usize)> {
        let g = self.geom(layer);
        let (cx, cy) = ((px / g.cell as f32).floor() as i64 - g.ox as i64, (py / g.cell as f32).floor() as i64 - g.oy as i64);
        (cx >= 0 && cy >= 0 && (cx as usize) < g.cols && (cy as usize) < g.rows).then_some((cx as usize, cy as usize))
    }

    pub fn index(&self, layer: usize, cx: usize, cy: usize) -> usize {
        self.layers[layer].start + cy * self.geom(layer).cols + cx
    }

    pub fn get(&self, layer: usize, cx: usize, cy: usize) -> u16 {
        self.ids.get(self.index(layer, cx, cy)).copied().unwrap_or(EMPTY)
    }

    /// What "no tile" is on a layer: the first ground layer has no empty cell, its chip 0 is the plain ground.
    pub fn blank(&self, layer: usize) -> u16 {
        if layer == 0 && self.layers.first().is_some_and(|l| l.base) { 0 } else { EMPTY }
    }

    /// Sets one cell; returns (index, old, new) when it changed.
    pub fn set(&mut self, layer: usize, cx: usize, cy: usize, chip: u16) -> Option<(usize, u16, u16)> {
        let g = self.geom(layer);
        if cx >= g.cols || cy >= g.rows || layer >= self.layers.len() {
            return None;
        }
        let i = self.index(layer, cx, cy);
        let old = self.ids[i];
        if old == chip {
            return None;
        }
        self.ids[i] = chip;
        self.refresh((g.ox + cx) * g.cell, (g.oy + cy) * g.cell, g.cell, g.cell);
        Some((i, old, chip))
    }

    /// Writes a value by its index in `ids` (undo / redo / loading saved edits).
    pub fn set_index(&mut self, index: usize, chip: u16) {
        if index >= self.ids.len() {
            return;
        }
        self.ids[index] = chip;
        if let Some(layer) = (0..self.layers.len()).rev().find(|l| self.layers[*l].start <= index) {
            let g = self.geom(layer);
            let rel = index - self.layers[layer].start;
            if g.cols > 0 && rel < g.cols * g.rows {
                self.refresh((g.ox + rel % g.cols) * g.cell, (g.oy + rel / g.cols) * g.cell, g.cell, g.cell);
            }
        }
    }

    pub fn changed(&self) -> Vec<(usize, u16)> {
        self.ids.iter().zip(&self.original).enumerate().filter(|(_, (a, b))| a != b).map(|(i, (a, _))| (i, *a)).collect()
    }

    pub fn change_count(&self) -> usize {
        self.ids.iter().zip(&self.original).filter(|(a, b)| a != b).count()
    }

    /// Recomposes a pixel rectangle and uploads it.
    fn refresh(&mut self, x: usize, y: usize, w: usize, h: usize) {
        let (x1, y1) = ((x + w).min(self.width), (y + h).min(self.height));
        if x >= x1 || y >= y1 {
            return;
        }
        self.compose(x, y, x1, y1);
        let mut part = egui::ColorImage::filled([x1 - x, y1 - y], egui::Color32::BLACK);
        for row in y..y1 {
            let src = row * self.width + x;
            let dst = (row - y) * (x1 - x);
            part.pixels[dst..dst + (x1 - x)].copy_from_slice(&self.image.pixels[src..src + (x1 - x)]);
        }
        if let Some(tex) = &mut self.tex {
            tex.set_partial([x, y], part, egui::TextureOptions::NEAREST);
        }
    }

    /// Source pixel of a chip for the tile pixel (u, v): the chip's orientation (flags & 0x0E) is a lookup of the
    /// eight ways to place a square tile (tools/map2d.py `transform`).
    fn chip_pixel(&self, chip: u16, base: bool, u: usize, v: usize) -> Option<egui::Color32> {
        let e = self.chips.get(chip as usize)?;
        let s = if base { 16 } else { 8 };
        let m = s - 1;
        let (su, sv) = match e[4] & 0x0E {
            2 => (m - v, u),
            4 => (m - u, m - v),
            6 => (v, m - u),
            8 => (m - u, v),
            10 => (u, m - v),
            12 => (v, u),
            14 => (m - v, m - u),
            _ => (u, v),
        };
        let sheet = if base { self.rgb.as_ref()? } else { self.rgba.as_ref()? };
        let (x, y) = (e[0] as usize * s + su, e[1] as usize * s + sv);
        (x < sheet.size[0] && y < sheet.size[1]).then(|| sheet.pixels[y * sheet.size[0] + x])
    }

    fn compose(&mut self, x0: usize, y0: usize, x1: usize, y1: usize) {
        let w = self.width;
        for y in y0..y1 {
            for x in x0..x1 {
                self.image.pixels[y * w + x] = egui::Color32::BLACK;
            }
        }
        for li in 0..self.layers.len() {
            if self.solo.is_some_and(|s| s != li) {
                continue;
            }
            let layer = self.layers[li];
            let g = self.geom(li);
            if g.cols == 0 {
                continue;
            }
            for y in y0..y1 {
                let cy = y / g.cell;
                if cy < g.oy || cy - g.oy >= g.rows {
                    continue;
                }
                for x in x0..x1 {
                    let cx = x / g.cell;
                    if cx < g.ox || cx - g.ox >= g.cols {
                        continue;
                    }
                    let chip = self.ids[layer.start + (cy - g.oy) * g.cols + (cx - g.ox)];
                    if chip == EMPTY {
                        continue;
                    }
                    let Some(src) = self.chip_pixel(chip, layer.base, x % g.cell, y % g.cell) else { continue };
                    let dst = &mut self.image.pixels[y * w + x];
                    if layer.base || src.a() == 255 {
                        *dst = egui::Color32::from_rgb(src.r(), src.g(), src.b());
                    } else if src.a() > 0 {
                        // premultiplied source over an opaque destination
                        let k = 255 - src.a() as u32;
                        let mix = |s: u8, d: u8| (s as u32 + d as u32 * k / 255).min(255) as u8;
                        *dst = egui::Color32::from_rgb(mix(src.r(), dst.r()), mix(src.g(), dst.g()), mix(src.b(), dst.b()));
                    }
                }
            }
        }
    }

    /// Sheet texture and the four UV corners (top-left, top-right, bottom-right, bottom-left of the drawn tile).
    pub fn chip_uv(&self, chip: u16, base: bool) -> Option<(egui::TextureId, [egui::Pos2; 4])> {
        let e = self.chips.get(chip as usize)?;
        self.tile_uv(e[0], e[1], e[4], base)
    }

    /// Tiles of a sheet: (columns, rows).
    pub fn sheet_tiles(&self, base: bool) -> (usize, usize) {
        let s = if base { 16 } else { 8 };
        match if base { self.rgb.as_ref() } else { self.rgba.as_ref() } {
            Some(img) => ((img.size[0] / s).min(256), (img.size[1] / s).min(256)),
            None => (0, 0),
        }
    }

    /// The chip that shows sheet tile (col, row) in an orientation (0..7): an existing one, else a new chip.
    pub fn chip_for(&mut self, col: u8, row: u8, orientation: u8, base: bool) -> Option<u16> {
        let flags = ((orientation & 7) << 1) | if base { 0 } else { 0x10 };
        if let Some(i) = self.chips.iter().position(|e| e[0] == col && e[1] == row && e[4] & 0x1E == flags) {
            return Some(i as u16);
        }
        if self.chips.len() >= 0xFFFE {
            return None;
        }
        self.chips.push([col, row, 0, 0, flags]);
        Some((self.chips.len() - 1) as u16)
    }

    /// Chips created in the editor that the map uses, and the chip id each one gets in the saved file (new chips
    /// nobody uses are not written).
    pub fn new_chips(&self) -> (Vec<[u8; 5]>, std::collections::HashMap<u16, u16>) {
        let mut used: Vec<u16> = self.ids.iter().copied().filter(|c| *c != EMPTY && (*c as usize) >= self.retail_chips && (*c as usize) < self.chips.len()).collect();
        used.sort();
        used.dedup();
        let remap = used.iter().enumerate().map(|(i, c)| (*c, (self.retail_chips + i) as u16)).collect();
        (used.iter().map(|c| self.chips[*c as usize]).collect(), remap)
    }

    /// Sheet tile (col, row) with chip flags `flags`: texture and UV corners.
    pub fn tile_uv(&self, col: u8, row: u8, flags: u8, base: bool) -> Option<(egui::TextureId, [egui::Pos2; 4])> {
        let e = [col, row, 0, 0, flags];
        let tex = if base { self.rgb_tex.as_ref()? } else { self.rgba_tex.as_ref()? };
        let s = if base { 16.0 } else { 8.0 };
        let [tw, th] = tex.size();
        let (x0, y0) = (e[0] as f32 * s / tw as f32, e[1] as f32 * s / th as f32);
        let (x1, y1) = (x0 + s / tw as f32, y0 + s / th as f32);
        let (tl, tr, br, bl) = (egui::pos2(x0, y0), egui::pos2(x1, y0), egui::pos2(x1, y1), egui::pos2(x0, y1));
        // which source corner ends up at each drawn corner
        let uv = match e[4] & 0x0E {
            2 => [tr, br, bl, tl],
            4 => [br, bl, tl, tr],
            6 => [bl, tl, tr, br],
            8 => [tr, tl, bl, br],
            10 => [bl, br, tr, tl],
            12 => [tl, bl, br, tr],
            14 => [br, tr, tl, bl],
            _ => [tl, tr, br, bl],
        };
        Some((tex.id(), uv))
    }

    /// Chips of one sheet (ground or overlay), in sheet order.
    pub fn palette(&self, base: bool) -> Vec<u16> {
        let mut used = vec![false; self.chips.len()];
        for (li, l) in self.layers.iter().enumerate() {
            if l.base != base {
                continue;
            }
            let g = self.geom(li);
            for id in &self.original[l.start..l.start + g.cols * g.rows] {
                if let Some(u) = used.get_mut(*id as usize) {
                    *u = true;
                }
            }
        }
        let mut out: Vec<u16> = (0..self.chips.len() as u16).filter(|c| used[*c as usize]).collect();
        out.sort_by_key(|c| {
            let e = self.chips[*c as usize];
            (e[1], e[0], e[4])
        });
        out
    }
}

/// Draws one chip into a screen rect.
pub fn paint_chip(painter: &egui::Painter, map: &TileMap, chip: u16, base: bool, rect: egui::Rect, tint: egui::Color32) {
    paint_uv(painter, map.chip_uv(chip, base), rect, tint);
}

/// Draws a sheet tile in an orientation (0..7) into a screen rect.
pub fn paint_tile(painter: &egui::Painter, map: &TileMap, col: u8, row: u8, orientation: u8, base: bool, rect: egui::Rect, tint: egui::Color32) {
    paint_uv(painter, map.tile_uv(col, row, (orientation & 7) << 1, base), rect, tint);
}

fn paint_uv(painter: &egui::Painter, quad: Option<(egui::TextureId, [egui::Pos2; 4])>, rect: egui::Rect, tint: egui::Color32) {
    let Some((tex, uv)) = quad else { return };
    let mut mesh = egui::Mesh::with_texture(tex);
    let corners = [rect.left_top(), rect.right_top(), rect.right_bottom(), rect.left_bottom()];
    for (pos, uv) in corners.into_iter().zip(uv) {
        mesh.vertices.push(egui::epaint::Vertex { pos, uv, color: tint });
    }
    mesh.indices.extend_from_slice(&[0, 1, 2, 0, 2, 3]);
    painter.add(egui::Shape::mesh(mesh));
}

// ------------------------------------------------------------------------------------------------- collision
pub const BLOCKED: u8 = 1;

pub struct CollGrid {
    pub index: usize,
    pub x: usize,
    pub y: usize,
    pub w: usize,
    pub h: usize,
    /// file offset of the first cell in leveldmap.bxon (2 bytes per cell: flags, zone)
    pub offset: usize,
    pub flags: Vec<u8>,
    pub original: Vec<u8>,
    pub zones: Vec<u8>,
    pub tex: Option<egui::TextureHandle>,
}

fn unhex(s: &str) -> Vec<u8> {
    (0..s.len() / 2).filter_map(|i| u8::from_str_radix(s.get(2 * i..2 * i + 2)?, 16).ok()).collect()
}

pub fn flag_color(f: u8) -> egui::Color32 {
    if f == 0 {
        egui::Color32::TRANSPARENT
    } else if f == BLOCKED {
        egui::Color32::from_rgba_unmultiplied(235, 60, 60, 120)
    } else if f & BLOCKED != 0 {
        egui::Color32::from_rgba_unmultiplied(235, 60, 200, 130)
    } else {
        // other marks (stairs, counters ...): one hue per value
        let h = (f as u32 * 47) % 360;
        let (r, g, b) = match h / 60 {
            0 => (255, 200, 40),
            1 => (160, 255, 60),
            2 => (60, 255, 170),
            3 => (60, 200, 255),
            4 => (120, 120, 255),
            _ => (255, 140, 60),
        };
        egui::Color32::from_rgba_unmultiplied(r, g, b, 120)
    }
}

impl CollGrid {
    pub fn parse(list: &serde_json::Value) -> Vec<CollGrid> {
        let n = |v: &serde_json::Value| v.as_u64().unwrap_or(0) as usize;
        list.as_array()
            .map(|a| {
                a.iter()
                    .filter_map(|g| {
                        let flags = unhex(g["flags"].as_str()?);
                        let (w, h) = (n(&g["w"]), n(&g["h"]));
                        (flags.len() == w * h && w > 0).then(|| CollGrid {
                            index: n(&g["index"]),
                            x: n(&g["x"]),
                            y: n(&g["y"]),
                            w,
                            h,
                            offset: n(&g["offset"]),
                            original: flags.clone(),
                            flags,
                            zones: unhex(g["zones"].as_str().unwrap_or("")),
                            tex: None,
                        })
                    })
                    .collect()
            })
            .unwrap_or_default()
    }

    fn image(&self) -> egui::ColorImage {
        let mut img = egui::ColorImage::filled([self.w, self.h], egui::Color32::TRANSPARENT);
        for (p, f) in img.pixels.iter_mut().zip(&self.flags) {
            *p = flag_color(*f);
        }
        img
    }

    /// One texel per cell, drawn stretched over the grid.
    pub fn texture(&mut self, ctx: &egui::Context, level: &str) -> egui::TextureId {
        if self.tex.is_none() {
            self.tex = Some(ctx.load_texture(format!("coll2d/{level}/{}", self.index), self.image(), egui::TextureOptions::NEAREST));
        }
        self.tex.as_ref().map(|t| t.id()).unwrap_or_default()
    }

    pub fn cell_at(&self, cx: i64, cy: i64) -> Option<usize> {
        let (x, y) = (cx - self.x as i64, cy - self.y as i64);
        (x >= 0 && y >= 0 && (x as usize) < self.w && (y as usize) < self.h).then(|| y as usize * self.w + x as usize)
    }

    /// Sets a cell's flag byte; returns (cell, old, new) when it changed.
    pub fn set(&mut self, cell: usize, value: u8) -> Option<(usize, u8, u8)> {
        let old = *self.flags.get(cell)?;
        if old == value {
            return None;
        }
        self.flags[cell] = value;
        if let Some(tex) = &mut self.tex {
            let one = egui::ColorImage::filled([1, 1], flag_color(value));
            tex.set_partial([cell % self.w, cell / self.w], one, egui::TextureOptions::NEAREST);
        }
        Some((cell, old, value))
    }

    pub fn change_count(&self) -> usize {
        self.flags.iter().zip(&self.original).filter(|(a, b)| a != b).count()
    }
}
