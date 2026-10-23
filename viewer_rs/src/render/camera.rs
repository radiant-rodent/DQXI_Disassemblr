//! Orbit camera.
//!
//! Drag conventions (both axes follow the mouse, i.e. you "grab" the model):
//! * drag right rotates the model to the right,
//! * drag down tips the model's top towards you (the camera rises).
//! `invert_horizontal` / `invert_vertical` flip either axis for people who
//! prefer the camera to follow the mouse instead.
//! Right/middle-drag pans, wheel zooms towards the cursor.

use crate::math::{Mat4, Vec3};
use crate::render::mesh::Bounds;

#[derive(Clone, Copy, Debug)]
pub struct Camera {
    pub azimuth: f32,   // degrees, rotation around Y
    pub elevation: f32, // degrees, +/- 89
    pub distance: f32,
    pub target: Vec3,
    pub fov: f32,
    pub invert_horizontal: bool,
    pub invert_vertical: bool,
    pub ortho: bool,
}

impl Default for Camera {
    fn default() -> Self {
        Self {
            azimuth: 35.0,
            elevation: 18.0,
            distance: 3.0,
            target: Vec3::zero(),
            fov: 42.0,
            invert_horizontal: false,
            invert_vertical: false,
            ortho: false,
        }
    }
}

impl Camera {
    pub fn frame(&mut self, bounds: &Bounds) {
        let radius = bounds.radius();
        self.target = bounds.center();
        self.distance = (radius * 2.9).max(1e-4);
    }

    pub fn eye(&self) -> Vec3 {
        let az = self.azimuth.to_radians();
        let el = self.elevation.to_radians();
        let dir = Vec3::new(el.cos() * az.sin(), el.sin(), el.cos() * az.cos());
        self.target.add(dir.scale(self.distance))
    }

    pub fn view_matrix(&self) -> Mat4 {
        Mat4::look_at(self.eye(), self.target, Vec3::new(0.0, 1.0, 0.0))
    }

    pub fn proj_matrix(&self, aspect: f32) -> Mat4 {
        let near = (self.distance * 0.005).max(1e-4);
        let far = (self.distance * 12.0).max(100.0);
        Mat4::perspective(self.fov, aspect.max(1e-4), near, far)
    }

    /// Mouse drag in points. `dx` right, `dy` down.
    pub fn orbit(&mut self, dx: f32, dy: f32) {
        let k = 0.4;
        let horizontal = if self.invert_horizontal { dx } else { -dx };
        let vertical = if self.invert_vertical { -dy } else { dy };
        self.azimuth = (self.azimuth + horizontal * k) % 360.0;
        self.elevation = (self.elevation + vertical * k).clamp(-89.0, 89.0);
    }

    /// Pan so the model follows the mouse.
    pub fn pan(&mut self, dx: f32, dy: f32, viewport_h: f32) {
        let scale = (self.distance * 2.0 * (self.fov.to_radians() * 0.5).tan())
            / viewport_h.max(1.0);
        let right = {
            let f = self.target.sub(self.eye()).normalized();
            f.cross(Vec3::new(0.0, 1.0, 0.0)).normalized()
        };
        let up = right
            .cross(self.target.sub(self.eye()).normalized())
            .normalized();
        self.target = self
            .target
            .sub(right.scale(dx * scale))
            .add(up.scale(dy * scale));
    }

    /// Zoom by a scroll delta in points (positive = towards the target).
    ///
    /// egui spreads one wheel notch (~50 pt) over several frames, and touchpads
    /// send many tiny deltas. An exponential factor makes the result depend only
    /// on the total distance scrolled, not on how it was split into frames:
    /// one notch is a steady ~12% step either way.
    pub fn zoom(&mut self, scroll: f32) {
        const PER_POINT: f32 = 0.0025;
        let factor = (-scroll * PER_POINT).exp();
        self.distance = (self.distance * factor).clamp(1e-4, 1e7);
    }

    /// One discrete zoom step for buttons/keys (`steps` > 0 zooms in).
    pub fn zoom_steps(&mut self, steps: f32) {
        self.zoom(steps * 50.0);
    }

    pub fn mvp(&self, aspect: f32) -> Mat4 {
        self.proj_matrix(aspect).mul(self.view_matrix())
    }
}
