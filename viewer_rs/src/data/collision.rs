//! Collision shapes of a level: `3d/bg/<level>/<level>_chit.rcb` (docs/COLLISION.md, tools/rcb_tool.py).

use std::path::Path;

#[derive(Clone, Debug, Default)]
pub struct Shape {
    pub name: String,
    pub vertices: Vec<[f32; 3]>,
    pub triangles: Vec<[u16; 3]>,
    /// surface attribute of the first triangle (0 = wall, 688 / 691 = floor in the church)
    pub attribute: u16,
}

impl Shape {
    pub fn bounds(&self) -> ([f32; 3], [f32; 3]) {
        let mut min = [f32::MAX; 3];
        let mut max = [f32::MIN; 3];
        for v in &self.vertices {
            for a in 0..3 {
                min[a] = min[a].min(v[a]);
                max[a] = max[a].max(v[a]);
            }
        }
        (min, max)
    }
}

fn u16_at(d: &[u8], o: usize) -> Option<u16> {
    Some(u16::from_le_bytes(d.get(o..o + 2)?.try_into().ok()?))
}

fn u32_at(d: &[u8], o: usize) -> Option<u32> {
    Some(u32::from_le_bytes(d.get(o..o + 4)?.try_into().ok()?))
}

fn f32_at(d: &[u8], o: usize) -> Option<f32> {
    Some(f32::from_le_bytes(d.get(o..o + 4)?.try_into().ok()?))
}

/// Parses an `rcbl` file; `None` if it does not look like one.
pub fn parse(d: &[u8]) -> Option<Vec<Shape>> {
    if d.get(0..4)? != b"rcbl" {
        return None;
    }
    let count = u32_at(d, 0x30)? as usize;
    let names = u16_at(d, 0x36)? as usize;
    let table = u32_at(d, 0x48)? as usize;
    let mut labels = Vec::new();
    for n in 0..names {
        let at = u32_at(d, table + 4 * n)? as usize;
        let end = d.get(at..)?.iter().position(|b| *b == 0)? + at;
        labels.push(String::from_utf8_lossy(&d[at..end]).to_string());
    }
    let mut out = Vec::new();
    for i in 0..count.min(4096) {
        let o = 0x54 + 96 * i;
        let id = u32_at(d, o)? as usize & 0xFFFF;
        let counts = u32_at(d, o + 4)?;
        let (nv, nt) = ((counts >> 16) as usize, (counts & 0xFFFF) as usize);
        let va = u32_at(d, o + 8)? as usize;
        let ia = u32_at(d, o + 12)? as usize;
        let mut shape = Shape { name: labels.get(id).cloned().unwrap_or_default(), ..Default::default() };
        for k in 0..nv {
            let p = va + 12 * k;
            shape.vertices.push([f32_at(d, p)?, f32_at(d, p + 4)?, f32_at(d, p + 8)?]);
        }
        for k in 0..nt {
            let p = ia + 8 * k;
            let tri = [u16_at(d, p)?, u16_at(d, p + 2)?, u16_at(d, p + 4)?];
            if tri.iter().all(|v| (*v as usize) < nv) {
                if shape.triangles.is_empty() {
                    shape.attribute = u16_at(d, p + 6)?;
                }
                shape.triangles.push(tri);
            }
        }
        out.push(shape);
    }
    Some(out)
}

/// The wall collision of a level (variants without their own background pack use the `a` pack).
pub fn load(root: &Path, level: &str) -> Option<Vec<Shape>> {
    let bg = root.join("game_data/packs/3d/bg");
    let mut names = vec![level.to_string()];
    if level.len() > 1 {
        names.push(format!("{}a", &level[..level.len() - 1]));
    }
    for name in names {
        let path = bg.join(&name).join(format!("{name}_chit.rcb"));
        if let Ok(bytes) = std::fs::read(&path) {
            if let Some(shapes) = parse(&bytes) {
                return Some(shapes);
            }
        }
    }
    None
}
