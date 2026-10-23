//! OpenGL renderer for the model viewport.
//!
//! Everything happens on the GPU: a real depth buffer (no painter's algorithm),
//! per-pixel two-sided lighting, MSAA from the eframe window, and a scale-aware
//! ground grid. Drawing a 20k triangle environment is a single draw call.

use std::path::Path;
use std::sync::Arc;

use eframe::glow::{self, HasContext};

use crate::math::Vec3;
use crate::render::camera::Camera;
use crate::render::mesh::{Blend, Mesh, STRIDE};

const MESH_VS: &str = r#"#version 330 core
layout(location = 0) in vec3 a_pos;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;
layout(location = 3) in vec2 a_mask_uv;
layout(location = 4) in float a_alpha;
layout(location = 5) in vec3 a_rgb;
uniform mat4 u_mvp;
uniform mat4 u_model;
out vec3 v_normal;
out vec3 v_world;
out vec2 v_uv;
out vec2 v_mask_uv;
out float v_alpha;
out vec3 v_rgb;
void main() {
    vec4 world = u_model * vec4(a_pos, 1.0);
    v_world = world.xyz;
    v_normal = mat3(u_model) * a_normal;
    v_uv = a_uv;
    v_mask_uv = a_mask_uv;
    v_alpha = a_alpha;
    v_rgb = a_rgb;
    gl_Position = u_mvp * vec4(a_pos, 1.0);
}"#;

const MESH_FS: &str = r#"#version 330 core
in vec3 v_normal;
in vec3 v_world;
in vec2 v_uv;
in vec2 v_mask_uv;
in float v_alpha;
in vec3 v_rgb;
uniform vec3 u_color;
uniform vec3 u_eye;
uniform float u_flat;
uniform float u_highlight;
uniform float u_use_texture;
uniform float u_alpha_cutoff;
uniform float u_unlit;
uniform float u_color_scale;    // > 0: baked vertex lighting, colour = tex * rgb * scale
uniform sampler2D u_texture;
uniform sampler2D u_mask;
uniform float u_mask_channel;   // 0 none, 1 red, 2 1-red, 3 alpha, 4 1-alpha
out vec4 frag;
void main() {
    vec3 base = u_color;
    float alpha = 1.0;
    if (u_use_texture > 0.5) {
        vec4 tex = texture(u_texture, v_uv);
        alpha = tex.a;
        if (u_mask_channel > 0.5) {
            // the game's alpha combiner reads this channel of a second texture
            vec4 m = texture(u_mask, v_mask_uv);
            float c = u_mask_channel < 2.5 ? m.r : m.a;
            alpha = (u_mask_channel == 2.0 || u_mask_channel == 4.0) ? 1.0 - c : c;
        }
        alpha *= v_alpha;                         // per-vertex fade (1 when not exported)
        if (alpha <= max(u_alpha_cutoff, 0.02)) discard;
        base *= tex.rgb;
    }
    if (u_color_scale > 0.0) {                    // the game's own baked lighting
        base = clamp(base * v_rgb * u_color_scale, 0.0, 1.0);
        frag = vec4(mix(base, vec3(0.95, 0.72, 0.25), u_highlight * 0.45), alpha);
        return;
    }
    if (u_unlit > 0.5) {                          // additive / multiply: no shading
        frag = vec4(base, alpha);
        return;
    }
    vec3 n = normalize(v_normal);
    vec3 v = normalize(u_eye - v_world);
    if (dot(n, v) < 0.0) { n = -n; }              // two sided
    vec3 key = normalize(vec3(0.45, 0.78, 0.55));
    vec3 fill = normalize(vec3(-0.55, -0.25, -0.7));
    float d1 = max(dot(n, key), 0.0);
    float d2 = max(dot(n, fill), 0.0);
    float rim = pow(1.0 - max(dot(n, v), 0.0), 2.5);
    vec3 lit = base * (0.30 + 0.70 * d1 + 0.22 * d2)
             + vec3(0.20) * pow(max(dot(n, normalize(key + v)), 0.0), 48.0)
             + base * rim * 0.10;
    lit = mix(lit, base, u_flat);
    lit = mix(lit, vec3(0.95, 0.72, 0.25), u_highlight * 0.45);
    frag = vec4(lit, alpha);
}"#;

const LINE_VS: &str = r#"#version 330 core
layout(location = 0) in vec3 a_pos;
layout(location = 1) in vec3 a_color;
uniform mat4 u_mvp;
out vec3 v_color;
void main() {
    v_color = a_color;
    gl_Position = u_mvp * vec4(a_pos, 1.0);
}"#;

const LINE_FS: &str = r#"#version 330 core
in vec3 v_color;
uniform float u_alpha;
out vec4 frag;
void main() { frag = vec4(v_color, u_alpha); }"#;

const BG_VS: &str = r#"#version 330 core
layout(location = 0) in vec2 a_pos;
void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }"#;

const BG_FS: &str = r#"#version 330 core
uniform vec3 u_color;
out vec4 frag;
void main() { frag = vec4(u_color, 1.0); }"#;

#[derive(Clone, Copy, Debug)]
pub struct RenderOptions {
    pub wireframe: bool,
    pub show_grid: bool,
    pub show_axes: bool,
    pub flat: bool,
    pub highlight: bool,
    /// draw parts the game hides by default (alternate hand poses)
    pub show_hidden: bool,
    pub background: [f32; 3],
}

impl Default for RenderOptions {
    fn default() -> Self {
        Self {
            wireframe: false,
            show_grid: true,
            show_axes: true,
            flat: false,
            highlight: false,
            show_hidden: false,
            background: [0.078, 0.086, 0.106],
        }
    }
}

struct Buffers {
    vao: glow::VertexArray,
    vbo: glow::Buffer,
    ebo: glow::Buffer,
    index_count: i32,
    vertex_count: i32,
}

struct GpuGroup {
    texture: Option<glow::Texture>,
    color: [f32; 3],
    blend: Blend,
    alpha_cutoff: f32,
    hidden: bool,
    mask: Option<glow::Texture>,
    mask_channel: f32,
    color_scale: f32,
    index_start: i32,
    index_count: i32,
}

impl Buffers {
    unsafe fn destroy(&self, gl: &glow::Context) {
        unsafe {
            gl.delete_vertex_array(self.vao);
            gl.delete_buffer(self.vbo);
            gl.delete_buffer(self.ebo);
        }
    }
}

pub struct GlRenderer {
    gl: Arc<glow::Context>,
    mesh_prog: glow::Program,
    mesh_mvp: glow::UniformLocation,
    mesh_model: glow::UniformLocation,
    mesh_color: glow::UniformLocation,
    mesh_eye: glow::UniformLocation,
    mesh_flat: glow::UniformLocation,
    mesh_highlight: glow::UniformLocation,
    mesh_use_texture: glow::UniformLocation,
    mesh_texture: glow::UniformLocation,
    mesh_alpha_cutoff: glow::UniformLocation,
    mesh_mask: glow::UniformLocation,
    mesh_mask_channel: glow::UniformLocation,
    mesh_color_scale: glow::UniformLocation,
    mesh_unlit: glow::UniformLocation,
    line_prog: glow::Program,
    line_mvp: glow::UniformLocation,
    line_alpha: glow::UniformLocation,
    bg_prog: glow::Program,
    bg_color: glow::UniformLocation,
    bg_vao: glow::VertexArray,
    mesh: Option<Buffers>,
    groups: Vec<GpuGroup>,
    lines: Option<Buffers>,
    axes: Option<Buffers>,
    mesh_color_value: [f32; 3],
    pub uploaded_id: u64,
    pub mesh_label: String,
    pub error: Option<String>,
    pub last_drawn: usize,
    pub last_paints: u64,
    pub version: String,
}

impl GlRenderer {
    pub fn new(gl: Arc<glow::Context>) -> Result<Self, String> {
        unsafe {
            let mesh_prog = build_program(&gl, MESH_VS, MESH_FS)?;
            let line_prog = build_program(&gl, LINE_VS, LINE_FS)?;
            let bg_prog = build_program(&gl, BG_VS, BG_FS)?;

            // single oversized triangle covers any viewport during the bg pass
            let bg_vao = gl.create_vertex_array().map_err(|e| e.to_string())?;
            let bg_vbo = gl.create_buffer().map_err(|e| e.to_string())?;
            gl.bind_vertex_array(Some(bg_vao));
            gl.bind_buffer(glow::ARRAY_BUFFER, Some(bg_vbo));
            let verts: [f32; 6] = [-1.0, -1.0, 3.0, -1.0, -1.0, 3.0];
            gl.buffer_data_u8_slice(glow::ARRAY_BUFFER, as_bytes(&verts), glow::STATIC_DRAW);
            gl.enable_vertex_attrib_array(0);
            gl.vertex_attrib_pointer_f32(0, 2, glow::FLOAT, false, 8, 0);
            gl.bind_vertex_array(None);

            Ok(Self {
                mesh_mvp: uniform(&gl, mesh_prog, "u_mvp")?,
                mesh_model: uniform(&gl, mesh_prog, "u_model")?,
                mesh_color: uniform(&gl, mesh_prog, "u_color")?,
                mesh_eye: uniform(&gl, mesh_prog, "u_eye")?,
                mesh_flat: uniform(&gl, mesh_prog, "u_flat")?,
                mesh_highlight: uniform(&gl, mesh_prog, "u_highlight")?,
                mesh_use_texture: uniform(&gl, mesh_prog, "u_use_texture")?,
                mesh_texture: uniform(&gl, mesh_prog, "u_texture")?,
                mesh_alpha_cutoff: uniform(&gl, mesh_prog, "u_alpha_cutoff")?,
                mesh_mask: uniform(&gl, mesh_prog, "u_mask")?,
                mesh_mask_channel: uniform(&gl, mesh_prog, "u_mask_channel")?,
                mesh_color_scale: uniform(&gl, mesh_prog, "u_color_scale")?,
                mesh_unlit: uniform(&gl, mesh_prog, "u_unlit")?,
                line_mvp: uniform(&gl, line_prog, "u_mvp")?,
                line_alpha: uniform(&gl, line_prog, "u_alpha")?,
                bg_color: uniform(&gl, bg_prog, "u_color")?,
                mesh_prog,
                line_prog,
                bg_prog,
                bg_vao,
                mesh: None,
                groups: Vec::new(),
                lines: None,
                axes: None,
                mesh_color_value: [0.8, 0.79, 0.76],
                uploaded_id: 0,
                mesh_label: String::new(),
                error: None,
                last_drawn: 0,
                last_paints: 0,
                version: gl.get_parameter_string(glow::VERSION),
                gl,
            })
        }
    }

    pub fn has_mesh(&self) -> bool {
        self.mesh.is_some()
    }

    /// Upload a mesh and rebuild the matching ground grid / axes.
    pub fn upload(&mut self, id: u64, mesh: &Mesh) -> Result<(), String> {
        unsafe {
            if let Some(old) = self.mesh.take() {
                old.destroy(&self.gl);
            }
            if let Some(old) = self.lines.take() {
                old.destroy(&self.gl);
            }
            if let Some(old) = self.axes.take() {
                old.destroy(&self.gl);
            }
            for group in self.groups.drain(..) {
                for tex in [group.texture, group.mask].into_iter().flatten() {
                    self.gl.delete_texture(tex);
                }
            }
            self.mesh = Some(self.upload_mesh(&mesh.vertices, &mesh.indices)?);
            for group in &mesh.groups {
                let texture = group
                    .texture_path
                    .as_deref()
                    .and_then(|path| self.load_texture(path).ok());
                self.groups.push(GpuGroup {
                    texture,
                    color: group.color,
                    blend: group.blend,
                    alpha_cutoff: group.alpha_cutoff,
                    hidden: group.hidden,
                    mask: group.mask_path.as_deref().and_then(|path| self.load_texture(path).ok()),
                    mask_channel: group.mask_channel.code(),
                    color_scale: group.color_scale,
                    index_start: group.index_start as i32,
                    index_count: group.index_count as i32,
                });
            }
            if self.groups.is_empty() {
                self.groups.push(GpuGroup {
                    texture: None,
                    color: mesh.color,
                    blend: Blend::Opaque,
                    alpha_cutoff: 0.0,
                    hidden: false,
                    mask: None,
                    mask_channel: 0.0,
                    color_scale: 0.0,
                    index_start: 0,
                    index_count: mesh.indices.len() as i32,
                });
            }
            let (grid, axes) = self.grid_geometry(&mesh.bounds);
            self.lines = Some(self.upload_vertices(&grid, &[])?);
            self.axes = Some(self.upload_vertices(&axes, &[])?);
        }
        self.mesh_label = mesh.name.clone();
        self.mesh_color_value = mesh.color;
        self.uploaded_id = id;
        Ok(())
    }

    fn upload_mesh(&self, data: &[f32], indices: &[u32]) -> Result<Buffers, String> {
        unsafe {
            let vao = self.gl.create_vertex_array().map_err(|e| e.to_string())?;
            let vbo = self.gl.create_buffer().map_err(|e| e.to_string())?;
            let ebo = self.gl.create_buffer().map_err(|e| e.to_string())?;
            self.gl.bind_vertex_array(Some(vao));
            self.gl.bind_buffer(glow::ARRAY_BUFFER, Some(vbo));
            self.gl
                .buffer_data_u8_slice(glow::ARRAY_BUFFER, as_bytes(data), glow::STATIC_DRAW);
            self.gl.bind_buffer(glow::ELEMENT_ARRAY_BUFFER, Some(ebo));
            self.gl
                .buffer_data_u8_slice(glow::ELEMENT_ARRAY_BUFFER, as_bytes(indices), glow::STATIC_DRAW);
            let stride = (STRIDE * 4) as i32;
            for (location, size, offset) in [(0, 3, 0), (1, 3, 12), (2, 2, 24), (3, 2, 32), (4, 1, 40), (5, 3, 44)] {
                self.gl.enable_vertex_attrib_array(location);
                self.gl
                    .vertex_attrib_pointer_f32(location, size, glow::FLOAT, false, stride, offset);
            }
            self.gl.bind_vertex_array(None);
            Ok(Buffers {
                vao,
                vbo,
                ebo,
                index_count: indices.len() as i32,
                vertex_count: (data.len() / STRIDE) as i32,
            })
        }
    }

    fn load_texture(&self, path: &Path) -> Result<glow::Texture, String> {
        let image = image::open(path)
            .map_err(|e| format!("{path:?}: {e}"))?
            .to_rgba8();
        let (width, height) = image.dimensions();
        unsafe {
            let texture = self.gl.create_texture().map_err(|e| e.to_string())?;
            self.gl.bind_texture(glow::TEXTURE_2D, Some(texture));
            self.gl.tex_parameter_i32(
                glow::TEXTURE_2D,
                glow::TEXTURE_MIN_FILTER,
                glow::LINEAR_MIPMAP_LINEAR as i32,
            );
            self.gl.tex_parameter_i32(
                glow::TEXTURE_2D,
                glow::TEXTURE_MAG_FILTER,
                glow::LINEAR as i32,
            );
            self.gl.tex_parameter_i32(
                glow::TEXTURE_2D,
                glow::TEXTURE_WRAP_S,
                glow::REPEAT as i32,
            );
            self.gl.tex_parameter_i32(
                glow::TEXTURE_2D,
                glow::TEXTURE_WRAP_T,
                glow::REPEAT as i32,
            );
            self.gl.tex_image_2d(
                glow::TEXTURE_2D,
                0,
                glow::RGBA as i32,
                width as i32,
                height as i32,
                0,
                glow::RGBA,
                glow::UNSIGNED_BYTE,
                glow::PixelUnpackData::Slice(Some(image.as_raw())),
            );
            self.gl.generate_mipmap(glow::TEXTURE_2D);
            self.gl.bind_texture(glow::TEXTURE_2D, None);
            Ok(texture)
        }
    }

    fn upload_vertices(&self, data: &[f32], indices: &[u32]) -> Result<Buffers, String> {
        unsafe {
            let vao = self.gl.create_vertex_array().map_err(|e| e.to_string())?;
            let vbo = self.gl.create_buffer().map_err(|e| e.to_string())?;
            let ebo = self.gl.create_buffer().map_err(|e| e.to_string())?;
            self.gl.bind_vertex_array(Some(vao));
            self.gl.bind_buffer(glow::ARRAY_BUFFER, Some(vbo));
            self.gl
                .buffer_data_u8_slice(glow::ARRAY_BUFFER, as_bytes(data), glow::STATIC_DRAW);
            self.gl.bind_buffer(glow::ELEMENT_ARRAY_BUFFER, Some(ebo));
            self.gl
                .buffer_data_u8_slice(glow::ELEMENT_ARRAY_BUFFER, as_bytes(indices), glow::STATIC_DRAW);
            self.gl.enable_vertex_attrib_array(0);
            self.gl
                .vertex_attrib_pointer_f32(0, 3, glow::FLOAT, false, 24, 0);
            self.gl.enable_vertex_attrib_array(1);
            self.gl
                .vertex_attrib_pointer_f32(1, 3, glow::FLOAT, false, 24, 12);
            self.gl.bind_vertex_array(None);
            Ok(Buffers {
                vao,
                vbo,
                ebo,
                index_count: indices.len() as i32,
                vertex_count: (data.len() / 6) as i32,
            })
        }
    }

    /// A grid sized to the model, plus coloured origin axes.
    fn grid_geometry(&self, bounds: &crate::render::mesh::Bounds) -> (Vec<f32>, Vec<f32>) {
        let radius = bounds.radius().max(1e-3);
        let step = 10f32.powf((radius.max(0.5) / 4.0).log10().floor());
        let extent = (radius * 1.6 / step).ceil() * step;
        let divisions = (extent / step).round().clamp(1.0, 60.0) as i32;
        let base_y = bounds.min.y.min(0.0) - step * 0.001;
        let mut grid: Vec<f32> = Vec::new();
        let mut push = |a: Vec3, b: Vec3, c: [f32; 3]| {
            grid.extend_from_slice(&[a.x, a.y, a.z, c[0], c[1], c[2]]);
            grid.extend_from_slice(&[b.x, b.y, b.z, c[0], c[1], c[2]]);
        };
        let color = [0.42f32, 0.46, 0.54];
        let axis_color = [0.85f32, 0.88, 0.95];
        for i in -divisions..=divisions {
            let t = i as f32 * step;
            let c = if i == 0 { axis_color } else { color };
            push(Vec3::new(t, base_y, -extent), Vec3::new(t, base_y, extent), c);
            push(Vec3::new(-extent, base_y, t), Vec3::new(extent, base_y, t), c);
        }
        let mut axes: Vec<f32> = Vec::new();
        let mut push_axis = |a: Vec3, b: Vec3, c: [f32; 3]| {
            axes.extend_from_slice(&[a.x, a.y, a.z, c[0], c[1], c[2]]);
            axes.extend_from_slice(&[b.x, b.y, b.z, c[0], c[1], c[2]]);
        };
        let o = Vec3::new(0.0, base_y, 0.0);
        let l = radius * 0.85;
        push_axis(o, Vec3::new(l, base_y, 0.0), [0.91, 0.35, 0.32]);
        push_axis(o, Vec3::new(0.0, base_y + l, 0.0), [0.37, 0.83, 0.60]);
        push_axis(o, Vec3::new(0.0, base_y, l), [0.45, 0.65, 0.98]);
        (grid, axes)
    }

    /// Draw one frame into the current framebuffer viewport.
    ///
    /// `viewport` is `[x, y_from_bottom, width, height]` in physical pixels.
    pub fn paint(
        &mut self,
        viewport: [i32; 4],
        camera: &Camera,
        opts: &RenderOptions,
    ) {
        let gl = self.gl.clone();
        self.last_paints += 1;
        let aspect = viewport[2] as f32 / viewport[3].max(1) as f32;
        let view = camera.view_matrix();
        let mvp = camera.proj_matrix(aspect).mul(view);
        let eye = camera.eye();
        unsafe {
            gl.viewport(viewport[0], viewport[1], viewport[2], viewport[3]);
            gl.clear(glow::DEPTH_BUFFER_BIT);
            gl.disable(glow::CULL_FACE);
            gl.depth_mask(true);
            gl.depth_func(glow::LEQUAL);

            // background
            gl.disable(glow::DEPTH_TEST);
            gl.disable(glow::BLEND);
            gl.use_program(Some(self.bg_prog));
            gl.uniform_3_f32(Some(&self.bg_color), opts.background[0], opts.background[1], opts.background[2]);
            gl.bind_vertex_array(Some(self.bg_vao));
            gl.draw_arrays(glow::TRIANGLES, 0, 3);

            // grid + axes
            gl.enable(glow::BLEND);
            gl.blend_func(glow::SRC_ALPHA, glow::ONE_MINUS_SRC_ALPHA);
            gl.enable(glow::DEPTH_TEST);
            gl.use_program(Some(self.line_prog));
            gl.uniform_matrix_4_f32_slice(Some(&self.line_mvp), false, &mvp.0);
            if opts.show_grid {
                if let Some(b) = &self.lines {
                    gl.uniform_1_f32(Some(&self.line_alpha), 0.5);
                    gl.bind_vertex_array(Some(b.vao));
                    gl.draw_arrays(glow::LINES, 0, b.vertex_count);
                }
            }
            if opts.show_axes {
                if let Some(b) = &self.axes {
                    gl.uniform_1_f32(Some(&self.line_alpha), 0.95);
                    gl.bind_vertex_array(Some(b.vao));
                    gl.line_width(2.0);
                    gl.draw_arrays(glow::LINES, 0, b.vertex_count);
                    gl.line_width(1.0);
                }
            }

            // mesh
            if let Some(b) = &self.mesh {
                gl.disable(glow::BLEND);
                gl.use_program(Some(self.mesh_prog));
                gl.uniform_matrix_4_f32_slice(Some(&self.mesh_mvp), false, &mvp.0);
                let model = crate::math::Mat4::identity();
                gl.uniform_matrix_4_f32_slice(Some(&self.mesh_model), false, &model.0);
                gl.uniform_3_f32(Some(&self.mesh_eye), eye.x, eye.y, eye.z);
                let color = self.mesh_color_value;
                gl.uniform_3_f32(Some(&self.mesh_color), color[0], color[1], color[2]);
                gl.uniform_1_f32(Some(&self.mesh_flat), if opts.flat { 1.0 } else { 0.0 });
                gl.uniform_1_f32(
                    Some(&self.mesh_highlight),
                    if opts.highlight { 1.0 } else { 0.0 },
                );
                gl.polygon_mode(
                    glow::FRONT_AND_BACK,
                    if opts.wireframe { glow::LINE } else { glow::FILL },
                );
                gl.bind_vertex_array(Some(b.vao));
                gl.uniform_1_i32(Some(&self.mesh_texture), 0);
                let mut drawn = 0i32;
                // the game's order: opaque first, then see-through draws without depth writes
                let passes = [Blend::Opaque, Blend::Alpha, Blend::Multiply, Blend::Additive];
                for (pass, group) in passes
                    .iter()
                    .flat_map(|pass| self.groups.iter().filter(move |g| g.blend == *pass).map(move |g| (*pass, g)))
                {
                    if group.index_count <= 0 || (group.hidden && !opts.show_hidden) {
                        continue;
                    }
                    match pass {
                        Blend::Opaque => {
                            gl.disable(glow::BLEND);
                            gl.depth_mask(true);
                        }
                        Blend::Alpha => {
                            gl.enable(glow::BLEND);
                            gl.blend_func(glow::SRC_ALPHA, glow::ONE_MINUS_SRC_ALPHA);
                            gl.depth_mask(false);
                        }
                        Blend::Additive => {
                            gl.enable(glow::BLEND);
                            gl.blend_func(glow::SRC_ALPHA, glow::ONE);
                            gl.depth_mask(false);
                        }
                        Blend::Multiply => {
                            gl.enable(glow::BLEND);
                            gl.blend_func(glow::DST_COLOR, glow::ZERO);
                            gl.depth_mask(false);
                        }
                    }
                    let unlit = matches!(pass, Blend::Additive | Blend::Multiply) && !opts.wireframe;
                    gl.uniform_1_f32(Some(&self.mesh_unlit), if unlit { 1.0 } else { 0.0 });
                    gl.uniform_1_f32(Some(&self.mesh_alpha_cutoff), group.alpha_cutoff);
                    gl.uniform_1_i32(Some(&self.mesh_mask), 1);
                    // flat shading / wireframe inspect geometry, so they keep the viewer's own light
                    let baked = if opts.flat || opts.wireframe { 0.0 } else { group.color_scale };
                    gl.uniform_1_f32(Some(&self.mesh_color_scale), baked);
                    match group.mask {
                        Some(mask) => {
                            gl.active_texture(glow::TEXTURE1);
                            gl.bind_texture(glow::TEXTURE_2D, Some(mask));
                            gl.active_texture(glow::TEXTURE0);
                            gl.uniform_1_f32(Some(&self.mesh_mask_channel), group.mask_channel);
                        }
                        None => gl.uniform_1_f32(Some(&self.mesh_mask_channel), 0.0),
                    }
                    gl.uniform_3_f32(
                        Some(&self.mesh_color),
                        group.color[0],
                        group.color[1],
                        group.color[2],
                    );
                    match group.texture {
                        Some(tex) => {
                            gl.uniform_1_f32(Some(&self.mesh_use_texture), 1.0);
                            gl.active_texture(glow::TEXTURE0);
                            gl.bind_texture(glow::TEXTURE_2D, Some(tex));
                        }
                        None => {
                            gl.uniform_1_f32(Some(&self.mesh_use_texture), 0.0);
                            gl.bind_texture(glow::TEXTURE_2D, None);
                        }
                    }
                    gl.draw_elements(
                        glow::TRIANGLES,
                        group.index_count,
                        glow::UNSIGNED_INT,
                        group.index_start * 4,
                    );
                    drawn += group.index_count;
                }
                self.last_drawn = (drawn / 3).max(0) as usize;
                gl.depth_mask(true);
                gl.disable(glow::BLEND);
                gl.bind_texture(glow::TEXTURE_2D, None);
                gl.polygon_mode(glow::FRONT_AND_BACK, glow::FILL);
            }

            // leave egui a clean slate
            gl.bind_vertex_array(None);
            gl.use_program(None);
            gl.disable(glow::DEPTH_TEST);
            gl.disable(glow::BLEND);
        }
    }
}

fn as_bytes<T>(data: &[T]) -> &[u8] {
    unsafe {
        std::slice::from_raw_parts(data.as_ptr() as *const u8, std::mem::size_of_val(data))
    }
}

unsafe fn build_program(gl: &glow::Context, vs: &str, fs: &str) -> Result<glow::Program, String> {
    unsafe {
        let program = gl.create_program().map_err(|e| e.to_string())?;
        let mut shaders = Vec::new();
        for (kind, src) in [(glow::VERTEX_SHADER, vs), (glow::FRAGMENT_SHADER, fs)] {
            let shader = gl.create_shader(kind).map_err(|e| e.to_string())?;
            gl.shader_source(shader, src);
            gl.compile_shader(shader);
            if !gl.get_shader_compile_status(shader) {
                return Err(format!("shader compile error: {}", gl.get_shader_info_log(shader)));
            }
            gl.attach_shader(program, shader);
            shaders.push(shader);
        }
        gl.link_program(program);
        if !gl.get_program_link_status(program) {
            return Err(format!("link error: {}", gl.get_program_info_log(program)));
        }
        for shader in shaders {
            gl.detach_shader(program, shader);
            gl.delete_shader(shader);
        }
        Ok(program)
    }
}

unsafe fn uniform(
    gl: &glow::Context,
    program: glow::Program,
    name: &str,
) -> Result<glow::UniformLocation, String> {
    unsafe {
        gl.get_uniform_location(program, name)
            .ok_or_else(|| format!("missing uniform {name}"))
    }
}
