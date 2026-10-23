//! Wavefront OBJ loading plus robust bounds.
//!
//! Ported from the Python viewer: the extracted environment meshes contain a
//! handful of corrupt vertices (values around 1e30 or NaN) that must not be
//! allowed to blow up camera framing.

use std::collections::HashMap;
use std::path::Path;

use crate::math::Vec3;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Bounds {
    pub min: Vec3,
    pub max: Vec3,
}

impl Bounds {
    pub fn size(&self) -> Vec3 {
        self.max.sub(self.min)
    }
    pub fn center(&self) -> Vec3 {
        self.min.add(self.max).scale(0.5)
    }
    pub fn max_extent(&self) -> f32 {
        let s = self.size();
        s.x.max(s.y).max(s.z)
    }
    pub fn radius(&self) -> f32 {
        let r = self.max_extent() * 0.5;
        if r.is_finite() && r > 0.0 {
            r
        } else {
            1.0
        }
    }
}

/// How the game blends a draw into the frame (`dqxi_blend` in the MTL).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Blend {
    #[default]
    Opaque,
    /// src*a + dst*(1-a)
    Alpha,
    /// src*a + dst: glows, mist, light shafts
    Additive,
    /// src*dst: shadows and dirt decals
    Multiply,
}

impl Blend {
    fn parse(word: &str) -> Self {
        match word {
            "alpha" => Blend::Alpha,
            "additive" => Blend::Additive,
            "multiply" => Blend::Multiply,
            _ => Blend::Opaque,
        }
    }
}

/// Floats per GPU vertex: position 3, normal 3, uv 2, mask uv 2, vertex alpha 1,
/// vertex colour 3 (baked lighting).
pub const STRIDE: usize = 14;

/// Which channel of the mask texture multiplies the alpha (`dqxi_mask_channel`).
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum MaskChannel {
    #[default]
    None,
    Red,
    OneMinusRed,
    Alpha,
    OneMinusAlpha,
}

impl MaskChannel {
    fn parse(word: &str) -> Self {
        match word {
            "red" | "green" | "blue" => MaskChannel::Red,
            "one_minus_red" | "one_minus_green" | "one_minus_blue" => MaskChannel::OneMinusRed,
            "alpha" => MaskChannel::Alpha,
            "one_minus_alpha" => MaskChannel::OneMinusAlpha,
            _ => MaskChannel::None,
        }
    }

    /// shader code: 0 none, 1 red, 2 1-red, 3 alpha, 4 1-alpha
    pub fn code(self) -> f32 {
        self as u8 as f32
    }
}

#[derive(Clone)]
pub struct MeshGroup {
    pub material: String,
    pub color: [f32; 3],
    pub texture_path: Option<std::path::PathBuf>,
    pub blend: Blend,
    /// alpha-test threshold (0 = texture alpha only cuts fully clear texels)
    pub alpha_cutoff: f32,
    /// hidden by default in game, e.g. alternate hand poses (`dqxi_hidden`)
    pub hidden: bool,
    /// baked vertex lighting: draw unshaded with texture * vertex colour * this scale
    /// (0 = the group has no vertex colours)
    pub color_scale: f32,
    /// second texture whose channel multiplies the alpha, read through the mask UVs
    pub mask_path: Option<std::path::PathBuf>,
    pub mask_channel: MaskChannel,
    pub index_start: usize,
    pub index_count: usize,
}

#[derive(Clone)]
struct MtlEntry {
    texture: Option<std::path::PathBuf>,
    color: [f32; 3],
    blend: Blend,
    alpha_cutoff: f32,
    hidden: bool,
    mask: Option<std::path::PathBuf>,
    mask_channel: MaskChannel,
    color_scale: f32,
}

impl Default for MtlEntry {
    fn default() -> Self {
        Self {
            texture: None,
            color: [0.80, 0.79, 0.76],
            blend: Blend::Opaque,
            alpha_cutoff: 0.0,
            hidden: false,
            mask: None,
            mask_channel: MaskChannel::None,
            color_scale: 1.0,
        }
    }
}

#[derive(Clone)]
pub struct Mesh {
    pub name: String,
    pub material: String,
    pub color: [f32; 3],
    /// Interleaved (position, normal, uv, mask uv) tuples: `STRIDE` floats per vertex.
    pub vertices: Vec<f32>,
    pub indices: Vec<u32>,
    pub groups: Vec<MeshGroup>,
    pub vertex_count: usize,
    pub triangle_count: usize,
    pub parts: usize,
    pub bounds: Bounds,
    pub raw_bounds: Bounds,
    pub non_finite: usize,
    pub outliers: usize,
}

impl Mesh {
    pub fn dims_text(&self) -> String {
        let s = self.bounds.size();
        format!("{:.3} x {:.3} x {:.3}", s.x, s.y, s.z)
    }
}

/// Parsed-but-unprocessed OBJ data.
struct Raw {
    verts: Vec<[f64; 3]>,
    normals: Vec<[f32; 3]>,
    uvs: Vec<[f32; 2]>,
    /// `dqxi_vt_mask` per vertex index, for objects that have a mask texture
    mask_uvs: HashMap<usize, [f32; 2]>,
    /// `dqxi_va` per vertex index, for objects whose alpha fades per vertex
    alphas: HashMap<usize, f32>,
    /// `dqxi_vc` per vertex index, for objects with baked vertex lighting
    colours: HashMap<usize, [f32; 3]>,
    groups: Vec<RawGroup>,
    parts: usize,
}

struct RawGroup {
    material: String,
    /// (position index, texcoord index or -1) per corner
    faces: Vec<[(i64, i64); 3]>,
}

pub fn load_obj(path: &Path) -> Result<Mesh, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("{path:?}: {e}"))?;
    let raw = parse(&text);
    if raw.verts.is_empty() {
        return Err(format!("no vertices in {path:?}"));
    }
    let mtl = read_mtl_map(path);
    let first_material = raw
        .groups
        .first()
        .map(|g| g.material.clone())
        .unwrap_or_else(|| "default_mat".to_string());
    let material = first_material.clone();
    let color = mtl.get(&first_material).map(|m| m.color).unwrap_or([0.80, 0.79, 0.76]);

    let n = raw.verts.len();
    let (bounds, raw_bounds, non_finite, outliers) = robust_bounds(&raw.verts);

    // vertex normals from the OBJ when they line up, else flat per-face normals later
    let has_normals = raw.normals.len() == n;
    let has_uvs = raw.uvs.len() == n;
    // A GPU vertex is a (position, texcoord) pair: baked faces give one corner of a
    // shared position its own texcoord. Plain exports have v == vt, so nothing splits.
    let mut vertices: Vec<f32> = Vec::with_capacity(n * STRIDE);
    let mut slots: HashMap<(usize, i64), u32> = HashMap::with_capacity(n);
    let mut vertex_of = |v: usize, t: i64, vertices: &mut Vec<f32>| -> u32 {
        *slots.entry((v, t)).or_insert_with(|| {
            let (px, py, pz) = sanitize(raw.verts[v]);
            let nrm = if has_normals { raw.normals[v] } else { [0.0, 1.0, 0.0] };
            let uv = if t >= 0 && (t as usize) < raw.uvs.len() {
                raw.uvs[t as usize]
            } else if has_uvs {
                raw.uvs[v]
            } else {
                [0.0, 0.0]
            };
            let mask_uv = raw.mask_uvs.get(&v).copied().unwrap_or([0.0, 0.0]);
            let alpha = raw.alphas.get(&v).copied().unwrap_or(1.0);
            let rgb = raw.colours.get(&v).copied().unwrap_or([1.0, 1.0, 1.0]);
            vertices.extend_from_slice(&[
                px, py, pz, nrm[0], nrm[1], nrm[2], uv[0], uv[1], mask_uv[0], mask_uv[1], alpha, rgb[0], rgb[1],
                rgb[2],
            ]);
            (vertices.len() / STRIDE - 1) as u32
        })
    };

    let mut indices: Vec<u32> = Vec::with_capacity(raw.groups.iter().map(|g| g.faces.len() * 3).sum());
    let mut groups: Vec<MeshGroup> = Vec::new();
    let mut triangles = 0usize;
    for raw_group in &raw.groups {
        let start = indices.len();
        let mut lit = false;
        for f in &raw_group.faces {
            if f.iter().any(|&(i, _)| i < 0 || i as usize >= n) {
                continue;
            }
            let (a, b, c) = (f[0].0 as usize, f[1].0 as usize, f[2].0 as usize);
            if a == b || b == c || a == c {
                continue;
            }
            for &(v, t) in f {
                lit |= raw.colours.contains_key(&(v as usize));
                let index = vertex_of(v as usize, t, &mut vertices);
                indices.push(index);
            }
            triangles += 1;
        }
        if indices.len() > start {
            let entry = mtl
                .get(&raw_group.material)
                .cloned()
                .unwrap_or(MtlEntry { color, ..MtlEntry::default() });
            groups.push(MeshGroup {
                material: raw_group.material.clone(),
                color: entry.color,
                texture_path: entry.texture,
                blend: entry.blend,
                alpha_cutoff: entry.alpha_cutoff,
                hidden: entry.hidden,
                color_scale: if lit { entry.color_scale } else { 0.0 },
                mask_path: entry.mask,
                mask_channel: entry.mask_channel,
                index_start: start,
                index_count: indices.len() - start,
            });
        }
    }

    let vertex_count = vertices.len() / STRIDE;

    // fill in flat normals for meshes that shipped without them
    let mut mesh = Mesh {
        name: path
            .file_stem()
            .map(|s| s.to_string_lossy().into_owned())
            .unwrap_or_default(),
        material,
        color,
        vertices,
        indices,
        groups,
        vertex_count,
        triangle_count: triangles,
        parts: raw.parts.max(1),
        bounds,
        raw_bounds,
        non_finite,
        outliers,
    };
    if !has_normals {
        mesh.compute_flat_normals();
    }
    Ok(mesh)
}

impl Mesh {
    /// Face normals for meshes without explicit `vn` data.
    pub fn compute_flat_normals(&mut self) {
        let acc = &mut self.vertices;
        let mut normals = vec![Vec3::zero(); self.vertex_count];
        for tri in self.indices.chunks_exact(3) {
            let a = vertex(acc, tri[0] as usize);
            let b = vertex(acc, tri[1] as usize);
            let c = vertex(acc, tri[2] as usize);
            let n = b.sub(a).cross(c.sub(a));
            for &i in tri {
                let slot = &mut normals[i as usize];
                *slot = slot.add(n);
            }
        }
        for (i, n) in normals.iter().enumerate() {
            let n = n.normalized();
            acc[i * STRIDE + 3] = n.x;
            acc[i * STRIDE + 4] = n.y;
            acc[i * STRIDE + 5] = n.z;
        }
    }
}

fn vertex(data: &[f32], i: usize) -> Vec3 {
    Vec3::new(data[i * STRIDE], data[i * STRIDE + 1], data[i * STRIDE + 2])
}

fn parse(text: &str) -> Raw {
    let mut verts: Vec<[f64; 3]> = Vec::new();
    let mut normals: Vec<[f32; 3]> = Vec::new();
    let mut uvs: Vec<[f32; 2]> = Vec::new();
    let mut groups: Vec<RawGroup> = vec![RawGroup {
        material: "default_mat".to_string(),
        faces: Vec::new(),
    }];
    let mut parts = 0usize;
    let mut mask_uvs: HashMap<usize, [f32; 2]> = HashMap::new();
    let mut object_start = 0usize;
    let mut mask_next = 0usize;
    let mut alphas: HashMap<usize, f32> = HashMap::new();
    let mut alpha_next = 0usize;
    let mut colours: HashMap<usize, [f32; 3]> = HashMap::new();
    let mut colour_next = 0usize;
    for line in text.lines() {
        let mut it = line.split_whitespace();
        let Some(tag) = it.next() else { continue };
        match tag {
            "v" => {
                let p: Vec<f64> = it.take(3).filter_map(|t| t.parse().ok()).collect();
                if p.len() == 3 {
                    verts.push([p[0], p[1], p[2]]);
                }
            }
            "vn" => {
                let p: Vec<f32> = it.take(3).filter_map(|t| t.parse().ok()).collect();
                if p.len() == 3 {
                    normals.push([p[0], p[1], p[2]]);
                }
            }
            "vt" => {
                let p: Vec<f32> = it.take(2).filter_map(|t| t.parse().ok()).collect();
                if p.len() == 2 {
                    // OBJ's V axis points up; the renderer samples top-left first.
                    uvs.push([p[0], 1.0 - p[1]]);
                }
            }
            "usemtl" => {
                let material = it.next().unwrap_or("default_mat").to_string();
                if groups.last().map(|g| g.faces.is_empty() && g.material == "default_mat").unwrap_or(false) {
                    if let Some(g) = groups.last_mut() {
                        g.material = material;
                    }
                } else {
                    groups.push(RawGroup { material, faces: Vec::new() });
                }
            }
            "o" | "g" => {
                parts += 1;
                object_start = verts.len();
                mask_next = 0;
                alpha_next = 0;
                colour_next = 0;
            }
            "dqxi_vc" => {
                let p: Vec<f32> = it.take(3).filter_map(|t| t.parse().ok()).collect();
                if p.len() == 3 {
                    colours.insert(object_start + colour_next, [p[0], p[1], p[2]]);
                }
                colour_next += 1;
            }
            "dqxi_va" => {
                if let Some(a) = it.next().and_then(|t| t.parse::<f32>().ok()) {
                    alphas.insert(object_start + alpha_next, a.clamp(0.0, 1.0));
                }
                alpha_next += 1;
            }
            "dqxi_vt_mask" => {
                let p: Vec<f32> = it.take(2).filter_map(|t| t.parse().ok()).collect();
                if p.len() == 2 {
                    mask_uvs.insert(object_start + mask_next, [p[0], 1.0 - p[1]]);
                }
                mask_next += 1;
            }
            "f" => {
                let n = verts.len() as i64;
                let nt = uvs.len() as i64;
                let idx: Vec<(i64, i64)> = it
                    .filter_map(|tok| {
                        let mut parts = tok.split('/');
                        let v = parts.next()?.parse::<i64>().ok()?;
                        let t = parts.next().and_then(|t| t.parse::<i64>().ok());
                        let v = if v > 0 { v - 1 } else { n + v };
                        let t = match t {
                            Some(t) if t > 0 => t - 1,
                            Some(t) if t < 0 => nt + t,
                            _ => -1,
                        };
                        Some((v, t))
                    })
                    .collect();
                let group = groups.last_mut().unwrap();
                for k in 1..idx.len().saturating_sub(1) {
                    group.faces.push([idx[0], idx[k], idx[k + 1]]);
                }
            }
            _ => {}
        }
    }
    Raw {
        verts,
        normals,
        uvs,
        mask_uvs,
        alphas,
        colours,
        groups,
        parts,
    }
}

fn sanitize(v: [f64; 3]) -> (f32, f32, f32) {
    let f = |x: f64| {
        if x.is_finite() && x.abs() < 1e6 {
            x as f32
        } else {
            0.0
        }
    };
    (f(v[0]), f(v[1]), f(v[2]))
}

/// Full finite bounds plus clipped bounds that ignore stray junk vertices.
fn robust_bounds(verts: &[[f64; 3]]) -> (Bounds, Bounds, usize, usize) {
    let mut min = [f64::INFINITY; 3];
    let mut max = [f64::NEG_INFINITY; 3];
    let mut non_finite = 0usize;
    let mut finite: Vec<[f64; 3]> = Vec::with_capacity(verts.len());
    for v in verts {
        if v.iter().all(|c| c.is_finite()) {
            for a in 0..3 {
                min[a] = min[a].min(v[a]);
                max[a] = max[a].max(v[a]);
            }
            finite.push(*v);
        } else {
            non_finite += 1;
        }
    }
    let raw = if finite.is_empty() {
        Bounds {
            min: Vec3::zero(),
            max: Vec3::zero(),
        }
    } else {
        Bounds {
            min: Vec3::new(min[0] as f32, min[1] as f32, min[2] as f32),
            max: Vec3::new(max[0] as f32, max[1] as f32, max[2] as f32),
        }
    };
    if finite.len() < 64 {
        return (raw, raw, non_finite, 0);
    }

    // clip at 2% / 5% / 10% until the box looks sane again
    let mut clipped: Option<(Vec3, Vec3)> = None;
    for pct in [2.0f64, 5.0, 10.0] {
        let lo = percentile(&finite, pct);
        let hi = percentile(&finite, 100.0 - pct);
        let b = (
            Vec3::new(lo[0] as f32, lo[1] as f32, lo[2] as f32),
            Vec3::new(hi[0] as f32, hi[1] as f32, hi[2] as f32),
        );
        let extent = b.1.sub(b.0).x.max(b.1.sub(b.0).y).max(b.1.sub(b.0).z);
        clipped = Some(b);
        if extent.is_finite() && extent <= 1e6 {
            break;
        }
    }
    let mut bounds = raw;
    let mut outliers = 0usize;
    if let Some((lo, hi)) = clipped {
        let full = raw.size();
        let clip = hi.sub(lo);
        let suspicious = full.x > clip.x * 8.0 + 1e-6
            || full.y > clip.y * 8.0 + 1e-6
            || full.z > clip.z * 8.0 + 1e-6;
        if suspicious {
            bounds = Bounds { min: lo, max: hi };
            let l = [lo.x as f64, lo.y as f64, lo.z as f64];
            let h = [hi.x as f64, hi.y as f64, hi.z as f64];
            outliers = finite
                .iter()
                .filter(|v| (0..3).any(|a| v[a] < l[a] || v[a] > h[a]))
                .count();
        }
    }
    // the percentile sweep can still be fooled when a large share of the vertices
    // is corrupt: fall back to splitting the value range at its biggest gap
    if !bounds.max_extent().is_finite() || bounds.max_extent() > 1e6 {
        let (lo, hi) = gap_split(&finite);
        let sane = |v: [f64; 3]| v.iter().all(|c| c.is_finite() && c.abs() < 1e6);
        if sane(lo) && sane(hi) {
            bounds = Bounds {
                min: Vec3::new(lo[0] as f32, lo[1] as f32, lo[2] as f32),
                max: Vec3::new(hi[0] as f32, hi[1] as f32, hi[2] as f32),
            };
            let l = [bounds.min.x as f64, bounds.min.y as f64, bounds.min.z as f64];
            let h = [bounds.max.x as f64, bounds.max.y as f64, bounds.max.z as f64];
            outliers = finite
                .iter()
                .filter(|v| (0..3).any(|a| v[a] < l[a] || v[a] > h[a]))
                .count();
        }
    }
    (bounds, raw, non_finite, outliers)
}

#[allow(clippy::type_complexity)]
fn gap_split(values: &[[f64; 3]]) -> ([f64; 3], [f64; 3]) {
    let mut lo = [f64::MAX; 3];
    let mut hi = [f64::MIN; 3];
    for axis in 0..3 {
        let mut column: Vec<f64> = values.iter().map(|v| v[axis]).collect();
        column.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let median = column[column.len() / 2];
        let mut best_gap = 0.0f64;
        let mut best_index = 0usize;
        let mut gaps: Vec<f64> = Vec::with_capacity(column.len().saturating_sub(1));
        for i in 1..column.len() {
            let gap = column[i] - column[i - 1];
            gaps.push(gap);
            if gap > best_gap {
                best_gap = gap;
                best_index = i;
            }
        }
        let mut sorted_gaps = gaps.clone();
        sorted_gaps.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        let median_gap = sorted_gaps.get(sorted_gaps.len() / 2).copied().unwrap_or(0.0);
        // keep the side of the biggest gap that contains the median
        let (start, end) = if best_gap > median_gap * 8.0 + 1e-9 {
            if median < column[best_index] {
                (0, best_index)
            } else {
                (best_index, column.len())
            }
        } else {
            (0, column.len())
        };
        let slice = &column[start..end.max(start + 1).min(column.len())];
        lo[axis] = slice.iter().copied().fold(f64::MAX, f64::min);
        hi[axis] = slice.iter().copied().fold(f64::MIN, f64::max);
    }
    (lo, hi)
}

fn percentile(values: &[[f64; 3]], pct: f64) -> [f64; 3] {
    let mut out = [0.0f64; 3];
    for a in 0..3 {
        let mut col: Vec<f64> = values.iter().map(|v| v[a]).collect();
        col.sort_by(|x, y| x.partial_cmp(y).unwrap_or(std::cmp::Ordering::Equal));
        let idx = ((pct / 100.0) * (col.len() - 1) as f64).round() as usize;
        out[a] = col[idx.min(col.len() - 1)];
    }
    out
}

// ---------------------------------------------------------------------------
// materials
// ---------------------------------------------------------------------------
fn mtl_path(obj: &Path) -> std::path::PathBuf {
    obj.with_extension("mtl")
}

fn read_mtl_map(obj: &Path) -> HashMap<String, MtlEntry> {
    let mut out = HashMap::new();
    let Ok(text) = std::fs::read_to_string(mtl_path(obj)) else {
        return out;
    };
    let mut name = "default_mat".to_string();
    let mut entry = MtlEntry::default();
    for line in text.lines() {
        let mut it = line.split_whitespace();
        match it.next() {
            Some("newmtl") => {
                out.insert(std::mem::take(&mut name), std::mem::take(&mut entry));
                name = it.next().unwrap_or("default_mat").to_string();
            }
            Some("Kd") => {
                let v: Vec<f32> = it.take(3).filter_map(|t| t.parse().ok()).collect();
                if v.len() == 3 {
                    // exported materials are flat grey: give untinted meshes a little warmth
                    entry.color = [v[0] * 0.98, v[1] * 0.97, v[2] * 0.94];
                }
            }
            Some("dqxi_blend") => entry.blend = Blend::parse(it.next().unwrap_or("")),
            Some("dqxi_hidden") => entry.hidden = it.next() == Some("1"),
            Some("dqxi_color_scale") => {
                entry.color_scale = it.next().and_then(|t| t.parse().ok()).unwrap_or(1.0);
            }
            Some("dqxi_mask_channel") => entry.mask_channel = MaskChannel::parse(it.next().unwrap_or("")),
            Some("dqxi_mask_map") => {
                let file = it.collect::<Vec<_>>().join(" ");
                let full = obj.parent().unwrap_or_else(|| Path::new(".")).join(&file);
                if !file.is_empty() && full.exists() {
                    entry.mask = Some(full);
                }
            }
            Some("dqxi_alpha_cutoff") => {
                entry.alpha_cutoff = it.next().and_then(|t| t.parse().ok()).unwrap_or(0.0);
            }
            Some("map_Kd") => {
                let file = it.collect::<Vec<_>>().join(" ");
                if !file.is_empty() {
                    let p = Path::new(&file);
                    let full = if p.is_absolute() {
                        p.to_path_buf()
                    } else {
                        obj.parent().unwrap_or_else(|| Path::new(".")).join(p)
                    };
                    if full.exists() {
                        entry.texture = Some(full);
                    }
                }
            }
            _ => {}
        }
    }
    out.insert(name, entry);
    out
}

/// Load every `.obj` inside a model directory (the export ships exactly one).
pub fn load_first_obj(dir: &Path) -> Result<Mesh, String> {
    let mut objs: Vec<std::path::PathBuf> = std::fs::read_dir(dir)
        .map_err(|e| format!("{dir:?}: {e}"))?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().map(|x| x.eq_ignore_ascii_case("obj")).unwrap_or(false))
        .collect();
    objs.sort();
    let obj = objs.first().ok_or_else(|| format!("no .obj in {dir:?}"))?;
    load_obj(obj)
}
