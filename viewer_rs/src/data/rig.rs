//! Skeleton, skin weights and skeletal animations of one model, read from the
//! `DQRG` file written by `SpicaRef rig <model.bch> <motion.bch> <out.bin>`.

use std::collections::HashMap;
use std::path::Path;

use crate::render::mesh::STRIDE;

/// Row-vector 4x3 matrix: three rows of rotation/scale, then translation.
pub type M43 = [f32; 12];

const IDENTITY: M43 = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0];

pub struct Bone {
    pub name: String,
    pub parent: i16,
    pub bind_local: M43,
    pub inv_bind: M43,
}

struct RigVertex {
    bone: [u8; 4],
    weight: [f32; 4],
}

pub struct Track {
    pub bone: usize,
    pub frames: Vec<M43>,
}

pub struct Animation {
    pub name: String,
    pub frames: f32,
    pub looping: bool,
    pub tracks: Vec<Track>,
}

pub struct Rig {
    pub bones: Vec<Bone>,
    pub animations: Vec<Animation>,
    verts: Vec<RigVertex>,
    pos: Vec<[f32; 3]>,
    cells: HashMap<[i32; 3], Vec<usize>>,
}

struct Reader<'a> {
    data: &'a [u8],
    at: usize,
}

impl Reader<'_> {
    fn take(&mut self, n: usize) -> Result<&[u8], String> {
        let end = self.at.checked_add(n).filter(|e| *e <= self.data.len()).ok_or("rig file truncated")?;
        let out = &self.data[self.at..end];
        self.at = end;
        Ok(out)
    }
    fn u16(&mut self) -> Result<u16, String> {
        Ok(u16::from_le_bytes(self.take(2)?.try_into().unwrap()))
    }
    fn u32(&mut self) -> Result<u32, String> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    fn f32(&mut self) -> Result<f32, String> {
        Ok(f32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    fn string(&mut self) -> Result<String, String> {
        let n = self.u16()? as usize;
        Ok(String::from_utf8_lossy(self.take(n)?).into_owned())
    }
    fn m43(&mut self) -> Result<M43, String> {
        let mut m = [0.0; 12];
        for v in &mut m {
            *v = self.f32()?;
        }
        Ok(m)
    }
}

/// Cell edge for matching exported vertices to rig vertices; the two sides
/// compute the same bind positions up to float rounding.
const CELL: f32 = 1e-3;
const MATCH_DISTANCE: f32 = 2e-4;

fn cell_of(p: [f32; 3]) -> [i32; 3] {
    [(p[0] / CELL).floor() as i32, (p[1] / CELL).floor() as i32, (p[2] / CELL).floor() as i32]
}

/// `a` then `b` (row vectors: p * a * b).
fn mul(a: &M43, b: &M43) -> M43 {
    let mut o = [0.0; 12];
    for r in 0..3 {
        for c in 0..3 {
            o[r * 3 + c] = a[r * 3] * b[c] + a[r * 3 + 1] * b[3 + c] + a[r * 3 + 2] * b[6 + c];
        }
    }
    for c in 0..3 {
        o[9 + c] = a[9] * b[c] + a[10] * b[3 + c] + a[11] * b[6 + c] + b[9 + c];
    }
    o
}

fn lerp(a: &M43, b: &M43, t: f32) -> M43 {
    let mut o = [0.0; 12];
    for i in 0..12 {
        o[i] = a[i] + (b[i] - a[i]) * t;
    }
    o
}

impl Rig {
    pub fn load(path: &Path) -> Result<Rig, String> {
        let data = std::fs::read(path).map_err(|e| format!("{path:?}: {e}"))?;
        let mut r = Reader { data: &data, at: 0 };
        if r.take(4)? != b"DQRG" {
            return Err("not a DQRG file".into());
        }
        let mut bones = Vec::new();
        for _ in 0..r.u32()? {
            let name = r.string()?;
            let parent = i16::from_le_bytes(r.take(2)?.try_into().unwrap());
            bones.push(Bone { name, parent, bind_local: r.m43()?, inv_bind: r.m43()? });
        }
        let count = r.u32()? as usize;
        let mut verts = Vec::with_capacity(count);
        let mut pos = Vec::with_capacity(count);
        let mut cells: HashMap<[i32; 3], Vec<usize>> = HashMap::with_capacity(count);
        for i in 0..count {
            let p = [r.f32()?, r.f32()?, r.f32()?];
            let bone: [u8; 4] = r.take(4)?.try_into().unwrap();
            let weight = [r.f32()?, r.f32()?, r.f32()?, r.f32()?];
            cells.entry(cell_of(p)).or_default().push(i);
            pos.push(p);
            verts.push(RigVertex { bone, weight });
        }
        let mut animations = Vec::new();
        for _ in 0..r.u32()? {
            let name = r.string()?;
            let frames = r.f32()?;
            let looping = r.take(1)?[0] != 0;
            let mut tracks = Vec::new();
            for _ in 0..r.u32()? {
                let bone = r.u16()? as usize;
                let n = r.u32()? as usize;
                let mut list = Vec::with_capacity(n);
                for _ in 0..n {
                    list.push(r.m43()?);
                }
                tracks.push(Track { bone, frames: list });
            }
            animations.push(Animation { name, frames, looping, tracks });
        }
        Ok(Rig { bones, animations, verts, pos, cells })
    }

    /// The rig vertex at `p` (within float rounding), if any.
    fn nearest(&self, p: [f32; 3]) -> Option<usize> {
        let c = cell_of(p);
        let mut best: Option<(f32, usize)> = None;
        for dx in -1..=1 {
            for dy in -1..=1 {
                for dz in -1..=1 {
                    let Some(list) = self.cells.get(&[c[0] + dx, c[1] + dy, c[2] + dz]) else { continue };
                    for &i in list {
                        let q = self.pos[i];
                        let d = (q[0] - p[0]).abs().max((q[1] - p[1]).abs()).max((q[2] - p[2]).abs());
                        if d <= MATCH_DISTANCE && best.is_none_or(|(bd, _)| d < bd) {
                            best = Some((d, i));
                        }
                    }
                }
            }
        }
        best.map(|(_, i)| i)
    }

    /// Maps each GPU vertex of `vertices` (`STRIDE` floats each) to its skin
    /// weights by bind-pose position.
    pub fn bind_to(&self, vertices: &[f32]) -> Skin {
        let n = vertices.len() / STRIDE;
        let mut map = Vec::with_capacity(n);
        let mut matched = 0;
        for i in 0..n {
            let p = [vertices[i * STRIDE], vertices[i * STRIDE + 1], vertices[i * STRIDE + 2]];
            let found = self.nearest(p);
            matched += found.is_some() as usize;
            map.push(found.map(|v| v as u32).unwrap_or(u32::MAX));
        }
        Skin { map, matched, bind: vertices.to_vec() }
    }

    /// World matrices of every bone at `frame` of animation `anim`
    /// (`None` = bind pose), already multiplied by the inverse bind pose.
    pub fn skin_matrices(&self, anim: Option<usize>, frame: f32) -> Vec<M43> {
        let n = self.bones.len();
        let mut local: Vec<M43> = self.bones.iter().map(|b| b.bind_local).collect();
        if let Some(a) = anim.and_then(|i| self.animations.get(i)) {
            for t in &a.tracks {
                if t.frames.is_empty() || t.bone >= n {
                    continue;
                }
                let f = frame.max(0.0);
                let i = (f.floor() as usize).min(t.frames.len() - 1);
                let j = (i + 1).min(t.frames.len() - 1);
                local[t.bone] = lerp(&t.frames[i], &t.frames[j], f - f.floor());
            }
        }
        let mut world: Vec<Option<M43>> = vec![None; n];
        fn resolve(i: usize, bones: &[Bone], local: &[M43], world: &mut [Option<M43>], depth: usize) -> M43 {
            if let Some(w) = world[i] {
                return w;
            }
            let parent = bones[i].parent;
            let w = if parent < 0 || parent as usize >= bones.len() || depth > bones.len() {
                local[i]
            } else {
                mul(&local[i], &resolve(parent as usize, bones, local, world, depth + 1))
            };
            world[i] = Some(w);
            w
        }
        (0..n)
            .map(|i| {
                let w = resolve(i, &self.bones, &local, &mut world, 0);
                mul(&self.bones[i].inv_bind, &w)
            })
            .collect()
    }
}

pub struct Skin {
    map: Vec<u32>,
    pub matched: usize,
    bind: Vec<f32>,
}

impl Skin {
    pub fn total(&self) -> usize {
        self.map.len()
    }

    /// A GPU vertex array with the skeleton posed by `matrices`.
    pub fn pose(&self, rig: &Rig, matrices: &[M43]) -> Vec<f32> {
        let mut out = self.bind.clone();
        for (i, &v) in self.map.iter().enumerate() {
            let Some(rv) = rig.verts.get(v as usize) else { continue };
            let o = i * STRIDE;
            let p = [self.bind[o], self.bind[o + 1], self.bind[o + 2]];
            let nrm = [self.bind[o + 3], self.bind[o + 4], self.bind[o + 5]];
            let (mut np, mut nn) = ([0.0f32; 3], [0.0f32; 3]);
            let mut total = 0.0;
            for k in 0..4 {
                let w = rv.weight[k];
                if w <= 0.0 {
                    continue;
                }
                let m = matrices.get(rv.bone[k] as usize).unwrap_or(&IDENTITY);
                total += w;
                for c in 0..3 {
                    np[c] += w * (p[0] * m[c] + p[1] * m[3 + c] + p[2] * m[6 + c] + m[9 + c]);
                    nn[c] += w * (nrm[0] * m[c] + nrm[1] * m[3 + c] + nrm[2] * m[6 + c]);
                }
            }
            if total <= 0.0 {
                continue;
            }
            let len = (nn[0] * nn[0] + nn[1] * nn[1] + nn[2] * nn[2]).sqrt().max(1e-6);
            out[o..o + 3].copy_from_slice(&np.map(|x| x / total));
            out[o + 3..o + 6].copy_from_slice(&nn.map(|x| x / len));
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Runs the real exporter on a retail character; skipped when the game data
    /// or the SpicaRef build is not present.
    #[test]
    fn a_character_skins_and_animates_without_exploding() {
        let root = crate::utils::project_root();
        let exe = root.join("tools/spica_ref/bin/Release/net9.0/SpicaRef.exe");
        let model = root.join("game_data/packs/3d/model/cha01000a_h/cha01000a_h.bch");
        let motion = root.join("game_data/packs/3d/motion/pc001_001_fld/motion_fld.bch");
        let obj = root.join("game_assets/models/packs/3d/model/cha01000a_h/cha01000a_h/cha01000a_h.obj");
        if !(exe.is_file() && model.is_file() && motion.is_file() && obj.is_file()) {
            return;
        }
        let out = std::env::temp_dir().join("dqxi_rig_test.bin");
        let status = std::process::Command::new(&exe).arg("rig").arg(&model).arg(&motion).arg(&out).output().unwrap();
        assert!(status.status.success());
        let rig = Rig::load(&out).unwrap();
        let mesh = crate::render::mesh::load_obj(&obj).unwrap();
        let skin = rig.bind_to(&mesh.vertices);
        assert!(skin.matched * 10 >= skin.total() * 9, "only {} of {} vertices matched", skin.matched, skin.total());
        // the bind pose must reproduce the mesh
        let bind = skin.pose(&rig, &rig.skin_matrices(None, 0.0));
        let worst = bind
            .chunks(STRIDE)
            .zip(mesh.vertices.chunks(STRIDE))
            .flat_map(|(a, b)| (0..3).map(move |k| (a[k] - b[k]).abs()))
            .fold(0.0f32, f32::max);
        assert!(worst < 0.01, "bind pose drifted by {worst}");
        // every animation poses inside a sane box
        let size = mesh.bounds.max_extent();
        for (i, a) in rig.animations.iter().enumerate().filter(|(_, a)| a.tracks.len() > 8).take(10) {
            let posed = skin.pose(&rig, &rig.skin_matrices(Some(i), a.frames / 2.0));
            for v in posed.chunks(STRIDE) {
                assert!(v[0].abs() < size * 5.0 && v[1].abs() < size * 5.0 && v[2].abs() < size * 5.0, "{} exploded", a.name);
            }
        }
    }
}
