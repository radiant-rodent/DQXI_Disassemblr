//! Paths, formatting, background worker pool and image caches.

use std::collections::{HashMap, HashSet, VecDeque};
use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::{Arc, Mutex};

use eframe::egui;

// ---------------------------------------------------------------------------
// project layout
// ---------------------------------------------------------------------------
pub fn project_root() -> PathBuf {
    if let Ok(p) = std::env::var("DQXI_PROJECT_ROOT") {
        let p = PathBuf::from(p);
        if p.exists() {
            return p;
        }
    }
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let mut candidate = manifest.as_path();
    while let Some(parent) = candidate.parent() {
        if parent.join("game_textures").exists() && parent.join("decomp").exists() {
            return parent.to_path_buf();
        }
        candidate = parent;
    }
    if let Ok(exe) = std::env::current_exe() {
        let mut dir = exe.as_path();
        while let Some(parent) = dir.parent() {
            if parent.join("game_textures").exists() {
                return parent.to_path_buf();
            }
            dir = parent;
        }
    }
    PathBuf::from(r".")
}

#[derive(Clone)]
pub struct Dirs {
    pub root: PathBuf,
    pub textures: PathBuf,
    pub models: PathBuf,
    pub layouts: PathBuf,
    pub scripts: PathBuf,
    pub tables: PathBuf,
    pub audio: PathBuf,
    pub decomp: PathBuf,
    pub src: PathBuf,
    pub asm: PathBuf,
    pub original: PathBuf,
    pub build: PathBuf,
    pub raw: PathBuf,
    pub dialogue_db: PathBuf,
    pub level2d: PathBuf,
    pub level3d: PathBuf,
    pub thumbs: PathBuf,
}

impl Dirs {
    pub fn detect() -> Self {
        let root = project_root();
        let reference = PathBuf::from(r"..\reference project");
        let local = std::env::var("LOCALAPPDATA").unwrap_or_else(|_| ".".into());
        let assets = root.join("game_assets");
        let choose = |new: PathBuf, old: PathBuf| if new.exists() { new } else { old };
        Self {
            textures: choose(assets.join("textures"), root.join("game_textures")),
            models: choose(assets.join("models"), root.join("game_models")),
            layouts: choose(assets.join("layouts"), root.join("game_layouts")),
            scripts: choose(assets.join("scripts"), root.join("game_scripts")),
            tables: choose(assets.join("tables"), root.join("game_tables")),
            audio: choose(assets.join("audio"), root.join("game_audio")),
            decomp: root.join("decomp"),
            src: root.join("src"),
            asm: root.join("asm"),
            original: root.join("original"),
            build: root.join("build"),
            raw: root.join("game_data").join("romfs"),
            dialogue_db: reference.join("workspace/project.db"),
            level2d: reference.join("workspace/extracted/romfs/level2d"),
            level3d: reference.join("workspace/extracted/romfs/level3d"),
            thumbs: PathBuf::from(local).join("DQXI_Explorer/thumbs_rs"),
            root,
        }
    }
}

// ---------------------------------------------------------------------------
// formatting
// ---------------------------------------------------------------------------
pub fn human_size(bytes: u64) -> String {
    let mut n = bytes as f64;
    for unit in ["B", "KB", "MB", "GB", "TB"] {
        if n < 1024.0 || unit == "TB" {
            return if unit == "B" {
                format!("{bytes} B")
            } else {
                format!("{n:.1} {unit}")
            };
        }
        n /= 1024.0;
    }
    format!("{n:.1} TB")
}

pub fn human_count(n: usize) -> String {
    let s = n.to_string();
    let mut out = String::new();
    for (i, c) in s.chars().enumerate() {
        if i > 0 && (s.len() - i) % 3 == 0 {
            out.push(',');
        }
        out.push(c);
    }
    out
}

/// East Asian glyphs take two columns in a monospace font; count them as such so
/// truncation budgets (and any remaining padded rows) line up visually.
fn is_wide(c: char) -> bool {
    let cp = c as u32;
    matches!(cp,
        0x1100..=0x115F
        | 0x2E80..=0x303E
        | 0x3041..=0x33FF
        | 0x3400..=0x4DBF
        | 0x4E00..=0x9FFF
        | 0xA000..=0xA4CF
        | 0xAC00..=0xD7A3
        | 0xF900..=0xFAFF
        | 0xFE30..=0xFE6F
        | 0xFF00..=0xFF60
        | 0xFFE0..=0xFFE6
        | 0x1F300..=0x1F64F
        | 0x20000..=0x3FFFD)
}

pub fn display_width(text: &str) -> usize {
    text.chars().map(|c| if is_wide(c) { 2 } else { 1 }).sum()
}

pub fn elide(text: &str, width: usize) -> String {
    let flat: String = text
        .chars()
        .map(|c| if c == '\n' || c == '\r' { ' ' } else { c })
        .collect();
    if display_width(&flat) <= width {
        return flat;
    }
    let mut out = String::new();
    let mut used = 0usize;
    for c in flat.chars() {
        let w = if is_wide(c) { 2 } else { 1 };
        if used + w > width.saturating_sub(1) {
            break;
        }
        out.push(c);
        used += w;
    }
    out.push('\u{2026}');
    out
}

pub fn read_text(path: &Path) -> Result<String, String> {
    let bytes = std::fs::read(path).map_err(|e| format!("{path:?}: {e}"))?;
    Ok(String::from_utf8_lossy(&bytes).into_owned())
}

// ---------------------------------------------------------------------------
// worker pool
// ---------------------------------------------------------------------------
type Job = Box<dyn FnOnce() + Send + 'static>;

pub struct Pool {
    tx: Sender<Job>,
    workers: usize,
}

impl Pool {
    pub fn new(workers: usize) -> Self {
        let (tx, rx) = channel::<Job>();
        let rx = Arc::new(Mutex::new(rx));
        for i in 0..workers {
            let rx = rx.clone();
            std::thread::Builder::new()
                .name(format!("dqxi-worker-{i}"))
                .spawn(move || loop {
                    let job = {
                        let guard = rx.lock().unwrap();
                        guard.recv()
                    };
                    match job {
                        Ok(job) => job(),
                        Err(_) => break,
                    }
                })
                .expect("spawn worker");
        }
        Self { tx, workers }
    }

    pub fn submit(&self, job: impl FnOnce() + Send + 'static) {
        let _ = self.tx.send(Box::new(job));
    }

    pub fn workers(&self) -> usize {
        self.workers
    }
}

// ---------------------------------------------------------------------------
// image caches (thumbnails + full size previews)
// ---------------------------------------------------------------------------
pub fn decode_image(path: &Path, max_px: Option<usize>) -> Result<egui::ColorImage, String> {
    let img = image::open(path).map_err(|e| format!("{path:?}: {e}"))?;
    let img = match max_px {
        Some(px) => {
            let (w, h) = (img.width(), img.height());
            let longest = w.max(h);
            if longest > px as u32 {
                let scale = px as f32 / longest as f32;
                img.resize(
                    ((w as f32 * scale).round() as u32).max(1),
                    ((h as f32 * scale).round() as u32).max(1),
                    image::imageops::FilterType::Triangle,
                )
            } else {
                img
            }
        }
        None => img,
    };
    let rgba = img.to_rgba8();
    let size = [rgba.width() as usize, rgba.height() as usize];
    Ok(egui::ColorImage::from_rgba_unmultiplied(size, rgba.as_raw()))
}

/// Threaded image cache holding egui textures, with a disk cache on the side.
pub struct ImageCache {
    max_px: Option<usize>,
    capacity: usize,
    dir: Option<PathBuf>,
    textures: HashMap<String, egui::TextureHandle>,
    order: VecDeque<String>,
    pending: HashSet<String>,
    tx: Sender<(String, Result<egui::ColorImage, String>)>,
    rx: Receiver<(String, Result<egui::ColorImage, String>)>,
    pub failures: HashMap<String, String>,
    pub ready: usize,
    pub queued: usize,
}

impl ImageCache {
    pub fn new(max_px: Option<usize>, capacity: usize, dir: Option<PathBuf>) -> Self {
        let (tx, rx) = channel();
        Self {
            max_px,
            capacity,
            dir,
            textures: HashMap::new(),
            order: VecDeque::new(),
            pending: HashSet::new(),
            tx,
            rx,
            failures: HashMap::new(),
            ready: 0,
            queued: 0,
        }
    }

    /// Get (or start decoding) an image. Returns `None` while it is decoded
    /// in the background.
    pub fn get(&mut self, ctx: &egui::Context, pool: &Pool, path: &Path) -> Option<egui::TextureHandle> {
        let key = path.to_string_lossy().into_owned();
        if let Some(handle) = self.textures.get(&key) {
            return Some(handle.clone());
        }
        if self.pending.contains(&key) {
            return None;
        }
        self.pending.insert(key.clone());
        self.queued += 1;
        let tx = self.tx.clone();
        let max_px = self.max_px;
        let disk = self.disk_path(&key);
        let path_owned = path.to_path_buf();
        let ctx = ctx.clone();
        pool.submit(move || {
            let result = match disk.as_deref().map(load_cached) {
                Some(Some(image)) => Ok(image),
                _ => match decode_image(&path_owned, max_px) {
                    Ok(image) => {
                        if let Some(disk) = &disk {
                            save_cached(disk, &image);
                        }
                        Ok(image)
                    }
                    Err(e) => Err(e),
                },
            };
            let _ = tx.send((key, result));
            ctx.request_repaint();
        });
        None
    }

    /// Insert a texture built by the caller (e.g. a generated waveform).
    pub fn insert(&mut self, ctx: &egui::Context, key: &str, image: egui::ColorImage) -> egui::TextureHandle {
        let handle = ctx.load_texture(key, image, egui::TextureOptions::LINEAR);
        self.textures.insert(key.to_string(), handle.clone());
        self.order.push_back(key.to_string());
        self.evict();
        handle
    }

    pub fn has(&self, path: &Path) -> bool {
        self.textures.contains_key(path.to_string_lossy().as_ref())
    }

    pub fn poll(&mut self, ctx: &egui::Context) -> bool {
        let mut arrived = false;
        while let Ok((key, result)) = self.rx.try_recv() {
            self.pending.remove(&key);
            self.queued = self.queued.saturating_sub(1);
            match result {
                Ok(image) => {
                    let handle = ctx.load_texture(&key, image, egui::TextureOptions::LINEAR);
                    self.textures.insert(key.clone(), handle);
                    self.order.push_back(key);
                    self.ready += 1;
                    arrived = true;
                }
                Err(e) => {
                    self.failures.insert(key, e);
                }
            }
        }
        if arrived {
            self.evict();
        }
        arrived
    }

    pub fn is_pending(&self) -> bool {
        !self.pending.is_empty()
    }

    fn evict(&mut self) {
        while self.textures.len() > self.capacity {
            match self.order.pop_front() {
                Some(old) => {
                    if !self.order.contains(&old) {
                        self.textures.remove(&old);
                    }
                }
                None => break,
            }
        }
    }

    fn disk_path(&self, key: &str) -> Option<PathBuf> {
        let dir = self.dir.as_ref()?;
        let mut hash: u64 = 0xcbf2_9ce4_8422_2325;
        for byte in key.as_bytes() {
            hash ^= *byte as u64;
            hash = hash.wrapping_mul(0x100_0000_01b3);
        }
        let stamp = std::fs::metadata(key)
            .map(|m| m.len() ^ m.modified().map(|t| t.duration_since(std::time::UNIX_EPOCH).map(|d| d.as_nanos() as u64).unwrap_or(0)).unwrap_or(0))
            .unwrap_or(0);
        Some(dir.join(format!("{:016x}{:016x}.png", hash, stamp)))
    }
}

fn load_cached(path: &Path) -> Option<egui::ColorImage> {
    let img = image::open(path).ok()?;
    let rgba = img.to_rgba8();
    Some(egui::ColorImage::from_rgba_unmultiplied(
        [rgba.width() as usize, rgba.height() as usize],
        rgba.as_raw(),
    ))
}

fn save_cached(path: &Path, image: &egui::ColorImage) {
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let Some(buffer) = image::RgbaImage::from_raw(
        image.size[0] as u32,
        image.size[1] as u32,
        image.as_raw().to_vec(),
    ) else {
        return;
    };
    let tmp = path.with_extension("tmp");
    if buffer.save(&tmp).is_ok() {
        let _ = std::fs::rename(&tmp, path);
    }
}

// ---------------------------------------------------------------------------
// WAV helpers (used by the audio panel)
// ---------------------------------------------------------------------------
#[derive(Clone, Debug, Default)]
pub struct WavInfo {
    pub channels: u16,
    pub rate: u32,
    pub frames: u32,
    pub width: u16,
    pub data_offset: u64,
    pub data_len: u64,
}

impl WavInfo {
    pub fn duration(&self) -> f32 {
        if self.rate == 0 {
            0.0
        } else {
            self.frames as f32 / self.rate as f32
        }
    }

    pub fn duration_text(&self) -> String {
        if self.frames == 0 || self.rate == 0 {
            return "--:--".into();
        }
        let total = self.duration().floor() as u32;
        if total >= 3600 {
            format!("{}:{:02}:{:02}", total / 3600, (total / 60) % 60, total % 60)
        } else {
            format!("{}:{:02}", total / 60, total % 60)
        }
    }
}

pub fn read_wav_info(path: &Path) -> Result<WavInfo, String> {
    use std::io::Read;

    let mut file = std::fs::File::open(path).map_err(|e| format!("{path:?}: {e}"))?;
    let file_len = file.metadata().map_err(|e| format!("{path:?}: {e}"))?.len();
    // WAV headers and all common metadata chunks are at the front. Reading the whole
    // 8 MB+ stream just to show its duration was both slow and unnecessary.
    let mut head = vec![0u8; 256 * 1024];
    let n = file.read(&mut head).map_err(|e| format!("{path:?}: {e}"))?;
    head.truncate(n);
    let bytes = head.as_slice();
    if bytes.len() < 44 || &bytes[0..4] != b"RIFF" || &bytes[8..12] != b"WAVE" {
        return Err("not a RIFF/WAVE file".into());
    }
    let mut info = WavInfo::default();
    let mut pos = 12usize;
    while pos + 8 <= bytes.len() {
        let id = &bytes[pos..pos + 4];
        let size = u32::from_le_bytes(bytes[pos + 4..pos + 8].try_into().unwrap()) as usize;
        let body = pos + 8;
        match id {
            b"fmt " if body + 16 <= bytes.len() => {
                info.channels = u16::from_le_bytes(bytes[body + 2..body + 4].try_into().unwrap());
                info.rate = u32::from_le_bytes(bytes[body + 4..body + 8].try_into().unwrap());
                info.width = u16::from_le_bytes(bytes[body + 14..body + 16].try_into().unwrap());
            }
            b"data" => {
                info.data_offset = body as u64;
                // Trust the declared data size, but never past EOF.
                info.data_len = (size as u64).min(file_len.saturating_sub(body as u64));
                if info.width > 0 && info.channels > 0 {
                    let block_align = (info.width as u64 / 8) * info.channels as u64;
                    if block_align > 0 {
                        info.frames = (info.data_len / block_align) as u32;
                    }
                }
                break;
            }
            _ => {}
        }
        pos = body + size + (size % 2);
    }
    Ok(info)
}

/// Min/max peaks for the waveform display (one bucket per pixel column).
pub fn waveform_peaks(path: &Path, buckets: usize) -> (Vec<f32>, Vec<f32>) {
    let Ok(bytes) = std::fs::read(path) else {
        return (vec![], vec![]);
    };
    let Ok(info) = read_wav_info(path) else {
        return (vec![], vec![]);
    };
    let width = info.width.max(1) as usize;
    let frame_bytes = (width / 8).max(1) * info.channels.max(1) as usize;
    let frames = info.frames as usize;
    if frames == 0 {
        return (vec![], vec![]);
    }
    let buckets = buckets.clamp(16, 4096);
    let per_bucket = (frames / buckets).max(1);
    let mut mins = Vec::with_capacity(buckets);
    let mut maxs = Vec::with_capacity(buckets);
    let start = info.data_offset as usize;
    for b in 0..buckets {
        let from = start + b * per_bucket * frame_bytes;
        let to = (start + (b + 1) * per_bucket * frame_bytes).min(bytes.len());
        if from >= to {
            mins.push(0.0);
            maxs.push(0.0);
            continue;
        }
        let slice = &bytes[from..to];
        let (mut lo, mut hi) = (f32::MAX, f32::MIN);
        for sample in slice.chunks_exact(frame_bytes) {
            let value = if width == 8 {
                (sample[0] as f32 - 128.0) / 128.0
            } else {
                let s = i16::from_le_bytes([sample[0], sample[1]]);
                s as f32 / 32768.0
            };
            lo = lo.min(value);
            hi = hi.max(value);
        }
        if lo == f32::MAX {
            lo = 0.0;
            hi = 0.0;
        }
        mins.push(lo);
        maxs.push(hi);
    }
    (mins, maxs)
}
