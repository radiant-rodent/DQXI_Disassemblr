//! DQXI Explorer & Level Editor - native, GPU-accelerated project browser and editor.

mod app;
mod data;
mod math;
mod render;
mod theme;
mod ui;
mod utils;
#[cfg(test)]
mod tests;

use eframe::egui;

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        depth_buffer: 24,   // the 3D viewport needs a real depth buffer
        multisampling: 4,   // smooth mesh edges
        viewport: egui::ViewportBuilder::default()
            .with_title("DQXI Explorer & Level Editor \u{2014} Dragon Quest XI (3DS)")
            .with_inner_size([1560.0, 940.0])
            .with_min_inner_size([1120.0, 700.0])
            .with_icon(std::sync::Arc::new(icon())),
        ..Default::default()
    };
    eframe::run_native(
        "dqxi-explorer",
        options,
        Box::new(|cc| Ok(Box::new(app::ViewerApp::new(cc)))),
    )
}

/// A small gold diamond icon, drawn by hand (no image dependency needed).
fn icon() -> egui::IconData {
    let size = 64usize;
    let mut rgba = vec![0u8; size * size * 4];
    let accent = [0xe8u8, 0xb8, 0x4b];
    let panel = [0x17u8, 0x1a, 0x21];
    let center = 32.0f32;
    for y in 0..size {
        for x in 0..size {
            let dx = (x as f32 - center).abs();
            let dy = (y as f32 - center).abs();
            let index = (y * size + x) * 4;
            let rounded = dx > 29.0 || dy > 29.0;
            if rounded {
                continue;
            }
            let diamond = dx + dy;
            let (color, alpha) = if dx > 27.0 || dy > 27.0 {
                (accent, 255)
            } else if diamond < 14.0 {
                (accent, 255)
            } else if diamond < 20.0 {
                (accent, 255)
            } else {
                (panel, 255)
            };
            rgba[index] = color[0];
            rgba[index + 1] = color[1];
            rgba[index + 2] = color[2];
            rgba[index + 3] = alpha;
        }
    }
    egui::IconData {
        rgba,
        width: size as u32,
        height: size as u32,
    }
}

