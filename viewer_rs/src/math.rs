//! Minimal 3D math (no external crates).

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Vec3 {
    pub x: f32,
    pub y: f32,
    pub z: f32,
}

impl Vec3 {
    pub const fn new(x: f32, y: f32, z: f32) -> Self {
        Self { x, y, z }
    }
    pub const fn zero() -> Self {
        Self::new(0.0, 0.0, 0.0)
    }
    pub fn sub(self, o: Self) -> Self {
        Self::new(self.x - o.x, self.y - o.y, self.z - o.z)
    }
    pub fn add(self, o: Self) -> Self {
        Self::new(self.x + o.x, self.y + o.y, self.z + o.z)
    }
    pub fn scale(self, s: f32) -> Self {
        Self::new(self.x * s, self.y * s, self.z * s)
    }
    pub fn dot(self, o: Self) -> f32 {
        self.x * o.x + self.y * o.y + self.z * o.z
    }
    pub fn cross(self, o: Self) -> Self {
        Self::new(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )
    }
    pub fn length(self) -> f32 {
        self.dot(self).sqrt()
    }
    pub fn normalized(self) -> Self {
        let l = self.length();
        if l > 1e-20 {
            self.scale(1.0 / l)
        } else {
            Self::zero()
        }
    }
    pub fn lerp(self, o: Self, t: f32) -> Self {
        self.add(o.sub(self).scale(t))
    }
}

/// Column-major 4x4 matrix (OpenGL layout).
#[derive(Clone, Copy, Debug)]
pub struct Mat4(pub [f32; 16]);

impl Mat4 {
    pub const fn identity() -> Self {
        let mut m = [0.0; 16];
        m[0] = 1.0;
        m[5] = 1.0;
        m[10] = 1.0;
        m[15] = 1.0;
        Self(m)
    }

    pub fn mul(self, o: Self) -> Self {
        let a = self.0;
        let b = o.0;
        let mut r = [0.0f32; 16];
        for col in 0..4 {
            for row in 0..4 {
                let mut sum = 0.0;
                for k in 0..4 {
                    sum += a[k * 4 + row] * b[col * 4 + k];
                }
                r[col * 4 + row] = sum;
            }
        }
        Self(r)
    }

    pub fn perspective(fov_y_deg: f32, aspect: f32, near: f32, far: f32) -> Self {
        let f = 1.0 / (fov_y_deg.to_radians() * 0.5).tan();
        let mut m = [0.0f32; 16];
        m[0] = f / aspect.max(1e-6);
        m[5] = f;
        m[10] = (far + near) / (near - far);
        m[11] = -1.0;
        m[14] = (2.0 * far * near) / (near - far);
        Self(m)
    }

    pub fn look_at(eye: Vec3, center: Vec3, up: Vec3) -> Self {
        let f = center.sub(eye).normalized();
        let s = f.cross(up).normalized();
        let u = s.cross(f);
        let mut m = Mat4::identity();
        m.0[0] = s.x;
        m.0[4] = s.y;
        m.0[8] = s.z;
        m.0[1] = u.x;
        m.0[5] = u.y;
        m.0[9] = u.z;
        m.0[2] = -f.x;
        m.0[6] = -f.y;
        m.0[10] = -f.z;
        m.0[12] = -s.dot(eye);
        m.0[13] = -u.dot(eye);
        m.0[14] = f.dot(eye);
        m
    }

    pub fn from_trs(translation: Vec3, scale: f32) -> Self {
        let mut m = Mat4::identity();
        m.0[0] = scale;
        m.0[5] = scale;
        m.0[10] = scale;
        m.0[12] = translation.x;
        m.0[13] = translation.y;
        m.0[14] = translation.z;
        m
    }
}
