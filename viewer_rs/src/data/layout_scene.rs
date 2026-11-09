//! BFLYT scene: the pane tree with its real transforms, materials, windows and parts,
//! flattened into quads the layout panel paints in game order.
//!
//! Everything is read from the layout JSON's `raw_sections` (the exact section bytes),
//! so the preview follows the binary the console reads, not a re-interpretation:
//!
//! * children are placed relative to their parent's origin (`pas1`/`pae1` nesting);
//! * the pane's base-position byte picks which corner/edge sits on that origin
//!   (bits 0-1 horizontal: 0 centre, 1 left, 2 right; bits 2-3 vertical: 0 centre,
//!   1 top, 2 bottom). Layout space is y-up with (0,0) at the screen centre;
//! * flags bit 0 = visible, bit 1 = alpha is passed on to the children;
//! * pictures use their material's first texture map and the pane's own UVs and
//!   vertex colours; windows draw content plus 1/4/8 frame pieces; parts (`prt1`)
//!   embed another layout of the same archive, loaded through a callback.
//!
//! Not modelled: the game font (text uses the editor font at the pane's font size),
//! TEV colour combiners, X/Y rotation, and animations (panes show their rest state).

use eframe::egui::{Color32, Pos2};
use serde_json::Value;

/// One textured or coloured quad. Corners are TL, TR, BL, BR in layout space (y-up).
#[derive(Clone, Debug)]
pub struct Quad {
    pub pane: String,
    pub kind: String,
    pub corners: [Pos2; 4],
    pub uv: [Pos2; 4],
    pub colors: [Color32; 4],
    pub texture: Option<String>,
    pub text: Option<TextDraw>,
    /// False when the pane (or an ancestor) has its visible flag cleared.
    pub visible: bool,
    /// Part nesting depth (0 = this layout).
    pub depth: usize,
    /// Outline only (null panes, bounding panes, parts).
    pub frame_only: bool,
}

#[derive(Clone, Debug)]
pub struct TextDraw {
    pub text: String,
    /// Glyph height in layout units (already scaled by the pane transform).
    pub size: f32,
    pub top: Color32,
    pub bottom: Color32,
    /// Glyph width in layout units (font size x, scaled).
    pub size_x: f32,
    /// Extra spacing between characters / lines, in layout units.
    pub char_space: f32,
    pub line_space: f32,
    /// Font file from the layout's `fnl1` list, e.g. `2D9.bffnt`.
    pub font: Option<String>,
    /// 0 centre, 1 left/top, 2 right/bottom: where the text block sits in the pane.
    pub h_align: u8,
    pub v_align: u8,
    /// Line alignment inside the block: 0 follow `h_align`, 1 left, 2 centre, 3 right.
    pub line_align: u8,
}

#[derive(Clone, Debug, Default)]
pub struct Scene {
    pub width: f32,
    pub height: f32,
    pub quads: Vec<Quad>,
    pub warnings: Vec<String>,
}

#[derive(Clone, Copy, Debug)]
struct Affine {
    a: f32,
    b: f32,
    c: f32,
    d: f32,
    tx: f32,
    ty: f32,
}

impl Affine {
    const IDENTITY: Affine = Affine { a: 1.0, b: 0.0, c: 0.0, d: 1.0, tx: 0.0, ty: 0.0 };

    fn local(t: [f32; 2], rot_deg: f32, s: [f32; 2]) -> Affine {
        let (sin, cos) = rot_deg.to_radians().sin_cos();
        Affine { a: cos * s[0], b: sin * s[0], c: -sin * s[1], d: cos * s[1], tx: t[0], ty: t[1] }
    }

    fn then(self, child: Affine) -> Affine {
        Affine {
            a: self.a * child.a + self.c * child.b,
            b: self.b * child.a + self.d * child.b,
            c: self.a * child.c + self.c * child.d,
            d: self.b * child.c + self.d * child.d,
            tx: self.a * child.tx + self.c * child.ty + self.tx,
            ty: self.b * child.tx + self.d * child.ty + self.ty,
        }
    }

    fn apply(&self, x: f32, y: f32) -> Pos2 {
        Pos2::new(self.a * x + self.c * y + self.tx, self.b * x + self.d * y + self.ty)
    }

    fn scale_x(&self) -> f32 {
        (self.a * self.a + self.b * self.b).sqrt()
    }

    fn scale_y(&self) -> f32 {
        (self.c * self.c + self.d * self.d).sqrt()
    }
}

struct Material {
    texture: Option<usize>,
    white: Color32,
}

struct Ctx<'a> {
    textures: Vec<String>,
    materials: Vec<Material>,
    texts: Vec<String>,
    fonts: Vec<String>,
    load_part: &'a mut dyn FnMut(&str) -> Option<Value>,
}

fn u16_at(b: &[u8], o: usize) -> u16 {
    b.get(o..o + 2).map(|s| u16::from_le_bytes([s[0], s[1]])).unwrap_or(0)
}
fn i16_at(b: &[u8], o: usize) -> i16 {
    u16_at(b, o) as i16
}
fn u32_at(b: &[u8], o: usize) -> u32 {
    b.get(o..o + 4).map(|s| u32::from_le_bytes([s[0], s[1], s[2], s[3]])).unwrap_or(0)
}
fn f32_at(b: &[u8], o: usize) -> f32 {
    f32::from_bits(u32_at(b, o))
}
fn rgba_at(b: &[u8], o: usize) -> Color32 {
    match b.get(o..o + 4) {
        Some(s) => Color32::from_rgba_unmultiplied(s[0], s[1], s[2], s[3]),
        None => Color32::WHITE,
    }
}
fn cstr(b: &[u8]) -> String {
    let end = b.iter().position(|&c| c == 0).unwrap_or(b.len());
    String::from_utf8_lossy(&b[..end]).into_owned()
}
fn tint(c: Color32, alpha: f32, white: Color32) -> Color32 {
    let m = |x: u8, y: u8| ((x as u32 * y as u32) / 255) as u8;
    Color32::from_rgba_unmultiplied(
        m(c.r(), white.r()),
        m(c.g(), white.g()),
        m(c.b(), white.b()),
        ((m(c.a(), white.a()) as f32) * alpha).round().clamp(0.0, 255.0) as u8,
    )
}

const PANES: [&str; 6] = ["pan1", "pic1", "txt1", "wnd1", "bnd1", "prt1"];

/// Section list (magic, payload without the 8-byte section header).
fn sections(json: &Value) -> Vec<(String, Vec<u8>)> {
    json.get("raw_sections")
        .and_then(|v| v.as_array())
        .map(|list| {
            list.iter()
                .map(|s| {
                    let magic = s.get("magic").and_then(|v| v.as_str()).unwrap_or("").to_string();
                    let hex = s.get("payload_hex").and_then(|v| v.as_str()).unwrap_or("");
                    let bytes = (0..hex.len() / 2)
                        .filter_map(|i| u8::from_str_radix(&hex[2 * i..2 * i + 2], 16).ok())
                        .collect();
                    (magic, bytes)
                })
                .collect()
        })
        .unwrap_or_default()
}

fn materials(secs: &[(String, Vec<u8>)]) -> Vec<Material> {
    let Some((_, p)) = secs.iter().find(|(m, _)| m == "mat1") else { return Vec::new() };
    let count = u16_at(p, 0) as usize;
    (0..count)
        .map(|i| {
            // offsets are relative to the section start; the payload starts 8 bytes in
            let at = (u32_at(p, 4 + 4 * i) as usize).saturating_sub(8);
            let flags = u32_at(p, at + 36);
            let texture = (flags & 3 != 0).then(|| u16_at(p, at + 40) as usize);
            Material { texture, white: rgba_at(p, at + 32) }
        })
        .collect()
}

/// Build the scene of one layout. `load_part(name)` returns the JSON of the layout a
/// `prt1` pane embeds (another `*.bflyt.json` of the same archive), or None.
pub fn build(json: &Value, load_part: &mut dyn FnMut(&str) -> Option<Value>) -> Scene {
    let mut scene = Scene { width: 320.0, height: 240.0, ..Scene::default() };
    if let Some(l) = json.get("layout") {
        scene.width = l.get("width").and_then(|v| v.as_f64()).unwrap_or(320.0) as f32;
        scene.height = l.get("height").and_then(|v| v.as_f64()).unwrap_or(240.0) as f32;
    }
    if json.get("raw_sections").is_none() {
        scene.warnings.push("this layout JSON has no raw_sections; re-extract it".into());
        return scene;
    }
    let mut out = Vec::new();
    emit_layout(json, Affine::IDENTITY, 1.0, true, 0, load_part, &mut out, &mut scene.warnings);
    scene.quads = out;
    scene
}

#[allow(clippy::too_many_arguments)]
fn emit_layout(
    json: &Value,
    base: Affine,
    alpha: f32,
    visible: bool,
    depth: usize,
    load_part: &mut dyn FnMut(&str) -> Option<Value>,
    out: &mut Vec<Quad>,
    warnings: &mut Vec<String>,
) {
    let secs = sections(json);
    let list = |key: &str| -> Vec<String> {
        json.get(key)
            .and_then(|v| v.as_array())
            .map(|a| a.iter().map(|v| v.as_str().unwrap_or("").to_string()).collect())
            .unwrap_or_default()
    };
    let texts = json
        .get("panes")
        .and_then(|v| v.as_array())
        .map(|a| a.iter().map(|p| p.get("text").and_then(|t| t.as_str()).unwrap_or("").to_string()).collect())
        .unwrap_or_default();
    let mut ctx = Ctx { textures: list("textures"), materials: materials(&secs), texts, fonts: list("fonts"), load_part };

    // parent stack: (transform at the parent's origin, alpha, visible, alpha passes on)
    let mut stack: Vec<(Affine, f32, bool)> = vec![(base, alpha, visible)];
    let mut last: (Affine, f32, bool) = (base, alpha, visible);
    let mut pane_index = 0usize;
    for (magic, p) in &secs {
        match magic.as_str() {
            "pas1" => stack.push(last),
            "pae1" => {
                if stack.len() > 1 {
                    stack.pop();
                }
            }
            m if PANES.contains(&m) => {
                let (parent, parent_alpha, parent_visible) = *stack.last().unwrap();
                let flags = p.first().copied().unwrap_or(1);
                let base_pos = p.get(1).copied().unwrap_or(0);
                let own_alpha = p.get(2).copied().unwrap_or(255) as f32 / 255.0;
                let name = cstr(&p[4.min(p.len())..0x1C.min(p.len())]);
                let t = [f32_at(p, 0x24), f32_at(p, 0x28)];
                let rot = f32_at(p, 0x38);
                let s = [f32_at(p, 0x3C), f32_at(p, 0x40)];
                let size = [f32_at(p, 0x44), f32_at(p, 0x48)];
                let xf = parent.then(Affine::local(t, rot, s));
                let vis = parent_visible && flags & 1 != 0;
                let a = parent_alpha * own_alpha;
                // children inherit alpha only when bit 1 is set
                last = (xf, if flags & 2 != 0 { a } else { parent_alpha }, vis);
                let (x0, x1) = match base_pos & 3 {
                    1 => (0.0, size[0]),
                    2 => (-size[0], 0.0),
                    _ => (-size[0] / 2.0, size[0] / 2.0),
                };
                let (y0, y1) = match (base_pos >> 2) & 3 {
                    1 => (-size[1], 0.0),
                    2 => (0.0, size[1]),
                    _ => (-size[1] / 2.0, size[1] / 2.0),
                };
                let rect = Rect4 { xf, x0, x1, y0, y1 };
                let text = ctx.texts.get(pane_index).cloned().unwrap_or_default();
                pane_index += 1;
                emit_pane(m, &name, p, &rect, a, vis, depth, &text, &mut ctx, out, warnings);
            }
            _ => {}
        }
    }
}

/// A pane's rectangle in its own space plus the transform to layout space.
struct Rect4 {
    xf: Affine,
    x0: f32,
    x1: f32,
    y0: f32,
    y1: f32,
}

impl Rect4 {
    /// TL, TR, BL, BR of the sub-rectangle [x0,x1]x[y0,y1] (y-up: top = y1).
    fn corners(&self, x0: f32, x1: f32, y0: f32, y1: f32) -> [Pos2; 4] {
        [self.xf.apply(x0, y1), self.xf.apply(x1, y1), self.xf.apply(x0, y0), self.xf.apply(x1, y0)]
    }
    fn all(&self) -> [Pos2; 4] {
        self.corners(self.x0, self.x1, self.y0, self.y1)
    }
}

const FULL_UV: [Pos2; 4] = [Pos2::new(0.0, 0.0), Pos2::new(1.0, 0.0), Pos2::new(0.0, 1.0), Pos2::new(1.0, 1.0)];

#[allow(clippy::too_many_arguments)]
fn emit_pane(
    kind: &str,
    name: &str,
    p: &[u8],
    rect: &Rect4,
    alpha: f32,
    visible: bool,
    depth: usize,
    text: &str,
    ctx: &mut Ctx,
    out: &mut Vec<Quad>,
    warnings: &mut Vec<String>,
) {
    let quad = |corners, uv, colors, texture: Option<String>, frame_only| Quad {
        pane: name.to_string(),
        kind: kind.to_string(),
        corners,
        uv,
        colors,
        texture,
        text: None,
        visible,
        depth,
        frame_only,
    };
    let material = |ctx: &Ctx, index: usize| -> (Option<String>, Color32) {
        match ctx.materials.get(index) {
            Some(m) => (m.texture.and_then(|t| ctx.textures.get(t).cloned()), m.white),
            None => (None, Color32::WHITE),
        }
    };
    match kind {
        "pic1" => {
            let colors = [0, 4, 8, 12].map(|o| rgba_at(p, 0x4C + o));
            let (texture, white) = material(ctx, u16_at(p, 0x5C) as usize);
            let uv = if p.get(0x5E).copied().unwrap_or(0) > 0 {
                [0, 8, 16, 24].map(|o| Pos2::new(f32_at(p, 0x60 + o), f32_at(p, 0x64 + o)))
            } else {
                FULL_UV
            };
            out.push(quad(rect.all(), uv, colors.map(|c| tint(c, alpha, white)), texture, false));
        }
        "wnd1" => emit_window(p, rect, alpha, ctx, out, &material, &quad),
        "txt1" => {
            let top = rgba_at(p, 0x60);
            let bottom = rgba_at(p, 0x64);
            let size = f32_at(p, 0x6C) * rect.xf.scale_y();
            let pos = p.get(0x54).copied().unwrap_or(0);
            let mut q = quad(rect.all(), FULL_UV, [Color32::TRANSPARENT; 4], None, true);
            q.text = Some(TextDraw {
                text: text.to_string(),
                size,
                size_x: f32_at(p, 0x68) * rect.xf.scale_x(),
                char_space: f32_at(p, 0x70) * rect.xf.scale_x(),
                line_space: f32_at(p, 0x74) * rect.xf.scale_y(),
                font: ctx.fonts.get(u16_at(p, 0x52) as usize).cloned(),
                top: tint(top, alpha, Color32::WHITE),
                bottom: tint(bottom, alpha, Color32::WHITE),
                h_align: pos & 3,
                v_align: (pos >> 2) & 3,
                line_align: p.get(0x55).copied().unwrap_or(0),
            });
            out.push(q);
        }
        "prt1" => {
            out.push(quad(rect.all(), FULL_UV, [Color32::TRANSPARENT; 4], None, true));
            let part = cstr(p.get(0x58..).unwrap_or(&[]));
            if depth >= 4 || part.is_empty() {
                return;
            }
            match (ctx.load_part)(&part) {
                Some(json) => {
                    let mag = [f32_at(p, 0x50), f32_at(p, 0x54)];
                    let mag = [if mag[0] == 0.0 { 1.0 } else { mag[0] }, if mag[1] == 0.0 { 1.0 } else { mag[1] }];
                    let base = rect.xf.then(Affine::local([0.0, 0.0], 0.0, mag));
                    emit_layout(&json, base, alpha, visible, depth + 1, ctx.load_part, out, warnings);
                }
                None => warnings.push(format!("part {name}: layout {part} not found")),
            }
        }
        _ => out.push(quad(rect.all(), FULL_UV, [Color32::TRANSPARENT; 4], None, true)),
    }
}

/// Window pane: inflated content quad plus frame pieces (1, 4 or 8 frames).
fn emit_window(
    p: &[u8],
    rect: &Rect4,
    alpha: f32,
    ctx: &Ctx,
    out: &mut Vec<Quad>,
    material: &dyn Fn(&Ctx, usize) -> (Option<String>, Color32),
    quad: &dyn Fn([Pos2; 4], [Pos2; 4], [Color32; 4], Option<String>, bool) -> Quad,
) {
    let inf = [0, 2, 4, 6].map(|o| i16_at(p, 0x4C + o) as f32); // l r t b
    let fs = [0, 2, 4, 6].map(|o| u16_at(p, 0x54 + o) as f32); // l r t b
    let frames = p.get(0x5C).copied().unwrap_or(0) as usize;
    let content = (u32_at(p, 0x60) as usize).saturating_sub(8);
    let table = (u32_at(p, 0x64) as usize).saturating_sub(8);
    let (x0, x1, y0, y1) = (rect.x0, rect.x1, rect.y0, rect.y1);

    // content
    let colors = [0, 4, 8, 12].map(|o| rgba_at(p, content + o));
    let (texture, white) = material(ctx, u16_at(p, content + 16) as usize);
    let uv = if p.get(content + 18).copied().unwrap_or(0) > 0 {
        [0, 8, 16, 24].map(|o| Pos2::new(f32_at(p, content + 20 + o), f32_at(p, content + 24 + o)))
    } else {
        FULL_UV
    };
    let c = rect.corners(x0 + fs[0] - inf[0], x1 - fs[1] + inf[1], y0 + fs[3] - inf[3], y1 - fs[2] + inf[2]);
    out.push(quad(c, uv, colors.map(|c| tint(c, alpha, white)), texture, false));

    if frames == 0 {
        return;
    }
    let frame = |i: usize| -> (Option<String>, Color32, u8) {
        let at = (u32_at(p, table + 4 * i) as usize).saturating_sub(8);
        let (t, w) = material(ctx, u16_at(p, at) as usize);
        (t, w, p.get(at + 2).copied().unwrap_or(0))
    };
    let col = |w: Color32| [tint(Color32::WHITE, alpha, w); 4];
    // UV rectangle helpers: (u0,u1,v0,v1) -> TL,TR,BL,BR
    let uvr = |u0: f32, u1: f32, v0: f32, v1: f32| {
        [Pos2::new(u0, v0), Pos2::new(u1, v0), Pos2::new(u0, v1), Pos2::new(u1, v1)]
    };
    // corners: LT, RT, LB, RB  (rect in pane space, UV)
    let corner_rects = [
        (x0, x0 + fs[0], y1 - fs[2], y1),
        (x1 - fs[1], x1, y1 - fs[2], y1),
        (x0, x0 + fs[0], y0, y0 + fs[3]),
        (x1 - fs[1], x1, y0, y0 + fs[3]),
    ];
    // a single frame is mirrored into the other three corners
    let mirrored = [uvr(0.0, 1.0, 0.0, 1.0), uvr(1.0, 0.0, 0.0, 1.0), uvr(0.0, 1.0, 1.0, 0.0), uvr(1.0, 0.0, 1.0, 0.0)];
    for (i, r) in corner_rects.iter().enumerate() {
        let (t, w, flip) = if frames >= 4 { frame(i) } else { frame(0) };
        let uv = if frames >= 4 { flip_uv(uvr(0.0, 1.0, 0.0, 1.0), flip) } else { mirrored[i] };
        out.push(quad(rect.corners(r.0, r.1, r.2, r.3), uv, col(w), t, false));
    }
    // edges: top, bottom, left, right. With 8 frames they have their own material;
    // otherwise the corner texture's inner row/column is stretched along the edge.
    let edges = [
        (x0 + fs[0], x1 - fs[1], y1 - fs[2], y1, 0usize, uvr(1.0, 1.0, 0.0, 1.0), 6usize),
        (x0 + fs[0], x1 - fs[1], y0, y0 + fs[3], 2, uvr(1.0, 1.0, 1.0, 0.0), 7),
        (x0, x0 + fs[0], y0 + fs[3], y1 - fs[2], 0, uvr(0.0, 1.0, 1.0, 1.0), 4),
        (x1 - fs[1], x1, y0 + fs[3], y1 - fs[2], 1, uvr(1.0, 0.0, 1.0, 1.0), 5),
    ];
    for (ex0, ex1, ey0, ey1, corner, uv, own) in edges {
        if ex1 <= ex0 || ey1 <= ey0 {
            continue;
        }
        let (t, w, uv) = if frames >= 8 {
            let (t, w, flip) = frame(own);
            (t, w, flip_uv(uvr(0.0, 1.0, 0.0, 1.0), flip))
        } else if frames >= 4 {
            let (t, w, flip) = frame(corner);
            (t, w, flip_uv(uv, flip))
        } else {
            let (t, w, _) = frame(0);
            (t, w, uv)
        };
        out.push(quad(rect.corners(ex0, ex1, ey0, ey1), uv, col(w), t, false));
    }
}

/// NW4C texture flip: 0 none, 1 horizontal, 2 vertical, 3 rot90, 4 rot180, 5 rot270.
fn flip_uv(uv: [Pos2; 4], flip: u8) -> [Pos2; 4] {
    let [tl, tr, bl, br] = uv;
    match flip {
        1 => [tr, tl, br, bl],
        2 => [bl, br, tl, tr],
        3 => [bl, tl, br, tr],
        4 => [br, bl, tr, tl],
        5 => [tr, br, tl, bl],
        _ => uv,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn load(rel: &str) -> Option<Value> {
        let root = crate::utils::Dirs::detect().root;
        let path = root.join("game_assets/layouts").join(rel);
        serde_json::from_str(&std::fs::read_to_string(path).ok()?).ok()
    }

    /// battle_2d_lw: the two background pictures tile the 320x240 bottom screen exactly
    /// (left-top anchored at (-160,120), centred at (80,0)), and part panes pull in
    /// their window layouts.
    #[test]
    fn battle_layout_places_backgrounds_on_the_screen() {
        let dir = "arcs/ui/battle_2d/battle_2d/blyt/";
        let Some(json) = load(&format!("{dir}battle_2d_lw.bflyt.json")) else { return };
        let mut parts = 0;
        let scene = build(&json, &mut |name| {
            parts += 1;
            load(&format!("{dir}{name}.bflyt.json"))
        });
        let left = scene.quads.iter().find(|q| q.pane == "background_battle_left").expect("left");
        assert_eq!(left.corners[0], Pos2::new(-160.0, 120.0));
        assert_eq!(left.corners[3], Pos2::new(0.0, -120.0));
        assert_eq!(left.texture.as_deref(), Some("background_battle_left_3d.bflim"));
        let right = scene.quads.iter().find(|q| q.pane == "background_battle_right").expect("right");
        assert_eq!(right.corners[0], Pos2::new(0.0, 120.0));
        assert_eq!(right.corners[3], Pos2::new(160.0, -120.0));
        assert!(parts > 0, "prt1 panes ask for their layouts");
        let text = scene.quads.iter().find(|q| q.pane == "txt_state").and_then(|q| q.text.clone()).expect("text");
        assert_eq!(text.size, 11.0);
        assert_eq!(text.font.as_deref(), Some("2D9.bffnt"));
    }

    /// Debug aid: `DQXI_SCENE=arcs/.../x.bflyt.json cargo test dump_scene -- --ignored`
    /// writes the flattened quads to `out/layout_scene.json` (for an offline render).
    #[test]
    #[ignore]
    fn dump_scene() {
        let Ok(rel) = std::env::var("DQXI_SCENE") else { return };
        let json = load(&rel).expect("layout json");
        let dir = std::path::Path::new(&rel).parent().unwrap().to_path_buf();
        let scene = build(&json, &mut |name| load(&dir.join(format!("{name}.bflyt.json")).to_string_lossy()));
        let quads: Vec<Value> = scene
            .quads
            .iter()
            .map(|q| {
                serde_json::json!({
                    "pane": q.pane, "kind": q.kind, "visible": q.visible, "frame_only": q.frame_only,
                    "depth": q.depth, "texture": q.texture,
                    "corners": q.corners.iter().map(|p| [p.x, p.y]).collect::<Vec<_>>(),
                    "uv": q.uv.iter().map(|p| [p.x, p.y]).collect::<Vec<_>>(),
                    "colors": q.colors.iter().map(|c| c.to_srgba_unmultiplied()).collect::<Vec<_>>(),
                    "text": q.text.as_ref().map(|t| serde_json::json!({"text": t.text, "size": t.size,
                        "h": t.h_align, "v": t.v_align, "color": t.top.to_srgba_unmultiplied()})),
                })
            })
            .collect();
        let out = serde_json::json!({"width": scene.width, "height": scene.height, "warnings": scene.warnings, "quads": quads});
        let root = crate::utils::Dirs::detect().root;
        std::fs::write(root.join("out/layout_scene.json"), serde_json::to_string_pretty(&out).unwrap()).unwrap();
    }

    #[test]
    fn every_layout_builds_without_panicking() {
        let root = crate::utils::Dirs::detect().root.join("game_assets/layouts/arcs/ui/battle_2d");
        let Ok(walk) = std::fs::read_dir(root.join("battle_2d/blyt")) else { return };
        for entry in walk.flatten() {
            let json: Value = serde_json::from_str(&std::fs::read_to_string(entry.path()).unwrap()).unwrap();
            let scene = build(&json, &mut |_| None);
            assert!(scene.quads.iter().all(|q| q.corners.iter().all(|c| c.x.is_finite() && c.y.is_finite())));
        }
    }
}
