//! CAPTCHA Image Generator
//!
//! Generates visual challenges where users must identify which scene contains
//! the target icon above the fullest cup.

use image::{ImageBuffer, Rgba, RgbaImage};
use imageproc::geometric_transformations::{rotate_about_center, Interpolation};
use rand::prelude::*;
use rand::rngs::SmallRng;
use rayon::prelude::*;
use resvg::tiny_skia::Pixmap;
use resvg::usvg::{Options, Transform, Tree};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use std::sync::{Arc, RwLock};

pub const ICON_DIR: &str = "icons/fontawesome";
pub const MIN_SCENES: usize = 5;
pub const MAX_SCENES: usize = 9;
pub const IMAGE_SIZE: u32 = 200;
pub const REFERENCE_WIDTH: u32 = 133;
pub const REFERENCE_HEIGHT: u32 = 200;

const ICON_CACHE_FILE: &str = "icons/icon_cache.bin";
const ICON_SIZES: [u32; 2] = [22, 28];
const BRIGHTNESS_LEVELS: [f32; 11] = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];

#[derive(Serialize, Deserialize)]
struct CacheData {
    icons: HashMap<(String, u8, u32), Vec<u8>>,
    names: Vec<String>,
}

pub struct IconCache {
    icon_dir: PathBuf,
    cache: HashMap<(String, u8, u32), Vec<u8>>,
    icon_names: Vec<String>,
}

impl IconCache {
    pub fn new(icon_dir: &str) -> Self {
        Self {
            icon_dir: PathBuf::from(icon_dir),
            cache: HashMap::new(),
            icon_names: Vec::new(),
        }
    }

    pub fn ensure_icons(&mut self) -> bool {
        if !self.icon_dir.exists() {
            eprintln!("Icon directory not found: {:?}", self.icon_dir);
            return false;
        }
        self.load_icon_names();
        if self.icon_names.is_empty() {
            eprintln!("No SVG icons found in {:?}", self.icon_dir);
            return false;
        }
        if self.load_cache() {
            println!("Loaded icon cache: {} entries", self.cache.len());
            true
        } else {
            println!("Building icon cache (first run)...");
            self.build_cache();
            true
        }
    }

    fn load_icon_names(&mut self) {
        if let Ok(entries) = fs::read_dir(&self.icon_dir) {
            self.icon_names = entries
                .filter_map(|e| e.ok())
                .filter(|e| e.path().extension().map_or(false, |ext| ext == "svg"))
                .filter_map(|e| {
                    e.path()
                        .file_stem()
                        .map(|s| s.to_string_lossy().to_string())
                })
                .collect();
        }
    }

    fn load_cache(&mut self) -> bool {
        let cache_path = Path::new(ICON_CACHE_FILE);
        if !cache_path.exists() {
            return false;
        }
        match fs::read(cache_path) {
            Ok(data) => match bincode::deserialize::<CacheData>(&data) {
                Ok(cache_data) => {
                    self.cache = cache_data.icons;
                    if !cache_data.names.is_empty() {
                        self.icon_names = cache_data.names;
                    }
                    true
                }
                Err(e) => {
                    eprintln!("Cache deserialize failed: {}", e);
                    false
                }
            },
            Err(e) => {
                eprintln!("Cache read failed: {}", e);
                false
            }
        }
    }

    fn save_cache(&self) {
        let cache_data = CacheData {
            icons: self.cache.clone(),
            names: self.icon_names.clone(),
        };
        if let Some(parent) = Path::new(ICON_CACHE_FILE).parent() {
            fs::create_dir_all(parent).ok();
        }
        match bincode::serialize(&cache_data) {
            Ok(data) => {
                if let Err(e) = fs::write(ICON_CACHE_FILE, data) {
                    eprintln!("Failed to save cache: {}", e);
                }
            }
            Err(e) => eprintln!("Failed to serialize cache: {}", e),
        }
    }

    pub fn build_cache(&mut self) {
        self.load_icon_names();
        let _total = self.icon_names.len() * ICON_SIZES.len() * BRIGHTNESS_LEVELS.len();

        for icon_name in &self.icon_names.clone() {
            let svg_path = self.icon_dir.join(format!("{}.svg", icon_name));
            let svg_content = match fs::read_to_string(&svg_path) {
                Ok(c) => c,
                Err(_) => continue,
            };
            for &size in &ICON_SIZES {
                for &brightness in &BRIGHTNESS_LEVELS {
                    let bright_key = (brightness * 10.0).round() as u8;
                    let key = (icon_name.clone(), bright_key, size);
                    if let Some(img) = self.render_svg(&svg_content, brightness, size) {
                        self.cache.insert(key, img.into_raw());
                    } else {
                        let mut fallback = vec![0u8; (size * size * 4) as usize];
                        let g = (50.0 + brightness * 180.0) as u8;
                        for y in 4..size - 4 {
                            for x in 4..size - 4 {
                                let idx = ((y * size + x) * 4) as usize;
                                fallback[idx] = g;
                                fallback[idx + 1] = g;
                                fallback[idx + 2] = g;
                                fallback[idx + 3] = 255;
                            }
                        }
                        self.cache.insert(key, fallback);
                    }
                }
            }
        }
        self.save_cache();
    }

    fn render_svg(&self, svg_content: &str, brightness: f32, size: u32) -> Option<RgbaImage> {
        let intensity = (30.0 + brightness * 210.0) as u8;
        let color = format!("#{:02x}{:02x}{:02x}", intensity, intensity, intensity);
        let mut svg = svg_content.to_string();
        if !svg.contains("fill=\"") {
            svg = svg.replace("<path ", &format!("<path fill=\"{}\" ", color));
        } else {
            let re = regex_lite::Regex::new(r#"fill="[^"]*""#).ok()?;
            svg = re
                .replace_all(&svg, &format!("fill=\"{}\"", color))
                .to_string();
        }
        svg = svg.replace("currentColor", &color);
        let tree = Tree::from_str(&svg, &Options::default()).ok()?;
        let mut pixmap = Pixmap::new(size, size)?;
        let tree_size = tree.size();
        let scale = (size as f32 / tree_size.width()).min(size as f32 / tree_size.height());
        let offset_x = (size as f32 - tree_size.width() * scale) / 2.0;
        let offset_y = (size as f32 - tree_size.height() * scale) / 2.0;
        let transform = Transform::from_scale(scale, scale).post_translate(offset_x, offset_y);
        resvg::render(&tree, transform, &mut pixmap.as_mut());
        let data = pixmap.data();
        let mut img = RgbaImage::new(size, size);
        for (i, pixel) in img.pixels_mut().enumerate() {
            let idx = i * 4;
            *pixel = Rgba([data[idx], data[idx + 1], data[idx + 2], data[idx + 3]]);
        }
        Some(img)
    }

    pub fn get_icon(&self, icon_name: &str, brightness: f32, size: u32) -> Option<RgbaImage> {
        let bright_key = (brightness * 10.0).round() as u8;
        let key = (icon_name.to_string(), bright_key, size);
        if let Some(data) = self.cache.get(&key) {
            return ImageBuffer::from_raw(size, size, data.clone());
        }
        let svg_path = self.icon_dir.join(format!("{}.svg", icon_name));
        if let Ok(svg_content) = fs::read_to_string(&svg_path) {
            return self.render_svg(&svg_content, brightness, size);
        }
        None
    }

    pub fn get_random_icons(&self, n: usize) -> Vec<String> {
        let mut rng = SmallRng::from_os_rng();
        self.icon_names
            .choose_multiple(&mut rng, n.min(self.icon_names.len()))
            .cloned()
            .collect()
    }

    pub fn get_random_icon(&self) -> Option<String> {
        let mut rng = SmallRng::from_os_rng();
        self.icon_names.choose(&mut rng).cloned()
    }
}

// Drawing utilities
pub fn create_wood_background(width: u32, height: u32) -> RgbaImage {
    let mut rng = SmallRng::from_os_rng();
    let mut data = vec![0u8; (width * height * 4) as usize];
    let mut grain_row = vec![0f32; width as usize];
    for x in 0..width {
        grain_row[x as usize] = (x as f32 * 0.05).sin() * 0.1;
    }
    for y in 0..height {
        let y_grain = (y as f32 * 0.3).sin() * 0.1 + 0.9;
        let row_offset = (y * width * 4) as usize;
        for x in 0..width {
            let factor = (y_grain + grain_row[x as usize]) * rng.random_range(0.85..1.15f32);
            let idx = row_offset + (x * 4) as usize;
            data[idx] = (140.0 * factor).clamp(0.0, 255.0) as u8;
            data[idx + 1] = (90.0 * factor).clamp(0.0, 255.0) as u8;
            data[idx + 2] = (50.0 * factor).clamp(0.0, 255.0) as u8;
            data[idx + 3] = 255;
        }
    }
    ImageBuffer::from_raw(width, height, data).unwrap()
}

pub fn draw_cup_2d(
    img: &mut RgbaImage,
    cx: i32,
    cy: i32,
    width: i32,
    height: i32,
    fill_level: f32,
    liquid_color: [u8; 4],
) {
    let bw = (width as f32 * 0.75) as i32;
    let (hh, tw, bwh) = (height / 2, width / 2, bw / 2);
    let (lt, rt, lb, rb) = (
        (cx - tw, cy - hh),
        (cx + tw, cy - hh),
        (cx - bwh, cy + hh),
        (cx + bwh, cy + hh),
    );
    draw_filled_trapezoid(img, lt, rt, rb, lb, [200, 210, 220, 180]);
    if fill_level > 0.05 {
        let lh = (height as f32 * fill_level * 0.85) as i32;
        let lty = cy + hh - lh;
        let ltw = ((bw as f32 + (width - bw) as f32 * lh as f32 / height as f32) / 2.0) as i32;
        draw_filled_trapezoid(
            img,
            (cx - ltw + 2, lty),
            (cx + ltw - 2, lty),
            (cx + bwh - 2, cy + hh - 2),
            (cx - bwh + 2, cy + hh - 2),
            liquid_color,
        );
    }
    draw_line(img, lt, rt, [230, 235, 240, 255]);
    draw_line(img, lt, lb, [150, 160, 170, 255]);
    draw_line(img, rt, rb, [150, 160, 170, 255]);
    draw_line(img, lb, rb, [150, 160, 170, 255]);
}

fn draw_filled_trapezoid(
    img: &mut RgbaImage,
    tl: (i32, i32),
    tr: (i32, i32),
    br: (i32, i32),
    bl: (i32, i32),
    color: [u8; 4],
) {
    let min_y = tl.1.min(tr.1).min(bl.1).min(br.1).max(0);
    let max_y =
        tl.1.max(tr.1)
            .max(bl.1)
            .max(br.1)
            .min(img.height() as i32 - 1);
    for y in min_y..=max_y {
        let t = if max_y != min_y {
            (y - min_y) as f32 / (max_y - min_y) as f32
        } else {
            0.0
        };
        let (left_x, right_x) = (
            lerp(tl.0 as f32, bl.0 as f32, t) as i32,
            lerp(tr.0 as f32, br.0 as f32, t) as i32,
        );
        for x in left_x.max(0)..=right_x.min(img.width() as i32 - 1) {
            if y >= 0 && y < img.height() as i32 {
                blend_pixel(img, x as u32, y as u32, color);
            }
        }
    }
}

#[inline]
fn lerp(a: f32, b: f32, t: f32) -> f32 {
    a + (b - a) * t
}

#[inline(always)]
fn blend_pixel(img: &mut RgbaImage, x: u32, y: u32, color: [u8; 4]) {
    if x >= img.width() || y >= img.height() {
        return;
    }
    let alpha = color[3] as u32;
    if alpha == 0 {
        return;
    }
    if alpha == 255 {
        img.put_pixel(x, y, Rgba(color));
        return;
    }
    let inv_alpha = 255 - alpha;
    let pixel = img.get_pixel(x, y);
    let r = ((color[0] as u32 * alpha + pixel[0] as u32 * inv_alpha) / 255) as u8;
    let g = ((color[1] as u32 * alpha + pixel[1] as u32 * inv_alpha) / 255) as u8;
    let b = ((color[2] as u32 * alpha + pixel[2] as u32 * inv_alpha) / 255) as u8;
    let a = (alpha + (pixel[3] as u32 * inv_alpha) / 255).min(255) as u8;
    img.put_pixel(x, y, Rgba([r, g, b, a]));
}

fn draw_line(img: &mut RgbaImage, p1: (i32, i32), p2: (i32, i32), color: [u8; 4]) {
    let (dx, dy) = ((p2.0 - p1.0).abs(), (p2.1 - p1.1).abs());
    let (sx, sy) = (
        if p1.0 < p2.0 { 1 } else { -1 },
        if p1.1 < p2.1 { 1 } else { -1 },
    );
    let (mut x, mut y, mut err) = (p1.0, p1.1, dx - dy);
    loop {
        if x >= 0 && x < img.width() as i32 && y >= 0 && y < img.height() as i32 {
            blend_pixel(img, x as u32, y as u32, color);
        }
        if x == p2.0 && y == p2.1 {
            break;
        }
        let e2 = 2 * err;
        if e2 > -dy {
            err -= dy;
            x += sx;
        }
        if e2 < dx {
            err += dx;
            y += sy;
        }
    }
}

pub fn overlay_image(base: &mut RgbaImage, overlay: &RgbaImage, x: i32, y: i32) {
    let (base_w, base_h) = (base.width() as i32, base.height() as i32);
    let (overlay_w, overlay_h) = (overlay.width() as i32, overlay.height() as i32);
    let (start_ox, start_oy) = ((-x).max(0) as u32, (-y).max(0) as u32);
    let (end_ox, end_oy) = (
        (base_w - x).min(overlay_w) as u32,
        (base_h - y).min(overlay_h) as u32,
    );
    if start_ox >= end_ox || start_oy >= end_oy {
        return;
    }
    for oy in start_oy..end_oy {
        let by = (y + oy as i32) as u32;
        for ox in start_ox..end_ox {
            let src = overlay.get_pixel(ox, oy);
            if src[3] > 0 {
                blend_pixel(base, (x + ox as i32) as u32, by, src.0);
            }
        }
    }
}

pub fn rotate_image(img: &RgbaImage, angle_degrees: f32) -> RgbaImage {
    rotate_about_center(
        img,
        angle_degrees.to_radians(),
        Interpolation::Bilinear,
        Rgba([0, 0, 0, 0]),
    )
}

pub fn apply_light_wash(img: &mut RgbaImage, cx: i32, cy: i32) {
    let mut rng = SmallRng::from_os_rng();
    let (radius, strength) = (45.0f32, 140.0f32);
    let (lx, ly) = (cx + rng.random_range(-8..=8), cy + rng.random_range(-8..=8));
    let (min_x, max_x) = (
        (lx - 45).max(0) as u32,
        ((lx + 45) as u32).min(img.width() - 1),
    );
    let (min_y, max_y) = (
        (ly - 45).max(0) as u32,
        ((ly + 45) as u32).min(img.height() - 1),
    );
    for y in min_y..=max_y {
        let dy_sq = (y as f32 - ly as f32).powi(2);
        for x in min_x..=max_x {
            let dist_sq = (x as f32 - lx as f32).powi(2) + dy_sq;
            if dist_sq >= radius * radius {
                continue;
            }
            let wash = (1.0 - dist_sq.sqrt() / radius).powf(1.5) * strength;
            let pixel = img.get_pixel(x, y);
            img.put_pixel(
                x,
                y,
                Rgba([
                    (pixel[0] as f32 + wash).min(255.0) as u8,
                    (pixel[1] as f32 + wash * 0.95).min(255.0) as u8,
                    (pixel[2] as f32 + wash * 0.7).min(255.0) as u8,
                    pixel[3],
                ]),
            );
        }
    }
}

pub fn apply_distortions(img: &RgbaImage, quality: u8) -> RgbaImage {
    let mut rng = SmallRng::from_os_rng();
    let (width, height) = (img.width(), img.height());
    let cs = [
        rng.random_range(-10..=10i16),
        rng.random_range(-10..=10i16),
        rng.random_range(-10..=10i16),
    ];
    let mut data = img.as_raw().clone();
    for chunk in data.chunks_exact_mut(4) {
        let noise = rng.random_range(-8..=8i16);
        chunk[0] = (chunk[0] as i16 + noise + cs[0]).clamp(0, 255) as u8;
        chunk[1] = (chunk[1] as i16 + noise + cs[1]).clamp(0, 255) as u8;
        chunk[2] = (chunk[2] as i16 + noise + cs[2]).clamp(0, 255) as u8;
    }
    jpeg_compress(
        &ImageBuffer::from_raw(width, height, data).unwrap(),
        quality,
    )
}

fn jpeg_compress(img: &RgbaImage, quality: u8) -> RgbaImage {
    let (width, height) = (img.width(), img.height());
    let mut rgb_data = Vec::with_capacity((width * height * 3) as usize);
    for chunk in img.as_raw().chunks_exact(4) {
        rgb_data.extend_from_slice(&chunk[..3]);
    }
    let mut jpeg_data = Vec::with_capacity((width * height) as usize);
    image::codecs::jpeg::JpegEncoder::new_with_quality(&mut jpeg_data, quality)
        .encode(&rgb_data, width, height, image::ExtendedColorType::Rgb8)
        .expect("JPEG encode failed");
    image::load_from_memory_with_format(&jpeg_data, image::ImageFormat::Jpeg)
        .expect("JPEG decode failed")
        .to_rgba8()
}

/// Result of generating a single scene
#[derive(Clone, Serialize, Deserialize)]
pub struct SceneResult {
    pub scene: usize,
    pub fills: Vec<f32>,
    pub fullest: usize,
    pub target_cup: usize,
    pub correct: bool,
}

/// Complete captcha challenge data
#[derive(Clone, Serialize, Deserialize)]
pub struct CaptchaChallenge {
    pub correct_scene: usize,
    pub scene_count: usize,
    pub target_icon: String,
    pub target_brightness: f32,
}

/// Thread-safe captcha generator
pub struct CaptchaGenerator {
    icon_cache: Arc<RwLock<IconCache>>,
    liquid_colors: Vec<[u8; 4]>,
    fill_presets: Vec<Vec<f32>>,
}

impl CaptchaGenerator {
    pub fn new() -> Self {
        Self {
            icon_cache: Arc::new(RwLock::new(IconCache::new(ICON_DIR))),
            liquid_colors: vec![
                [230, 80, 30, 220],
                [50, 180, 80, 220],
                [200, 60, 130, 220],
                [70, 130, 230, 220],
                [180, 50, 50, 220],
                [50, 180, 180, 220],
            ],
            fill_presets: vec![
                vec![0.2, 0.4, 0.65, 0.88],
                vec![0.18, 0.42, 0.6, 0.9],
                vec![0.22, 0.38, 0.68, 0.85],
                vec![0.25, 0.45, 0.62, 0.92],
                vec![0.15, 0.48, 0.7, 0.87],
                vec![0.28, 0.5, 0.72, 0.95],
            ],
        }
    }

    pub fn setup(&self) -> bool {
        let mut cache = self.icon_cache.write().unwrap();
        cache.ensure_icons()
    }

    /// Create a new challenge with random correct scene and scene count
    pub fn create_challenge(&self) -> CaptchaChallenge {
        let mut rng = SmallRng::from_os_rng();
        let scene_count = rng.random_range(MIN_SCENES..=MAX_SCENES);
        let cache = self.icon_cache.read().unwrap();
        CaptchaChallenge {
            correct_scene: rng.random_range(0..scene_count),
            scene_count,
            target_icon: cache
                .get_random_icon()
                .unwrap_or_else(|| "star".to_string()),
            target_brightness: rng.random_range(0.15..0.85),
        }
    }

    fn generate_positions(&self, rng: &mut SmallRng) -> Vec<(i32, i32)> {
        let mut positions = Vec::with_capacity(4);
        for _ in 0..4 {
            let mut found = false;
            for _ in 0..50 {
                let (x, y) = (rng.random_range(30..170), rng.random_range(45..180));
                if positions
                    .iter()
                    .all(|&(px, py): &(i32, i32)| (x - px).pow(2) + (y - py).pow(2) >= 2500)
                {
                    positions.push((x, y));
                    found = true;
                    break;
                }
            }
            if !found {
                positions.push((rng.random_range(30..170), rng.random_range(45..180)));
            }
        }
        positions
    }

    /// Generate a single scene image as PNG bytes
    pub fn generate_scene(
        &self,
        challenge: &CaptchaChallenge,
        scene_idx: usize,
    ) -> (Vec<u8>, SceneResult) {
        let mut rng = SmallRng::from_os_rng();
        let mut img = create_wood_background(IMAGE_SIZE, IMAGE_SIZE);

        let mut fills = self.fill_presets[rng.random_range(0..self.fill_presets.len())].clone();
        fills.shuffle(&mut rng);

        let fullest = fills
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .map(|(i, _)| i)
            .unwrap_or(0);
        let target_cup = if scene_idx == challenge.correct_scene {
            fullest
        } else {
            let others: Vec<_> = (0..4).filter(|&i| i != fullest).collect();
            others[rng.random_range(0..others.len())]
        };

        let cache = self.icon_cache.read().unwrap();
        let mut icon_names = cache.get_random_icons(4);
        icon_names[target_cup] = challenge.target_icon.clone();

        let positions = self.generate_positions(&mut rng);
        let mut order: Vec<usize> = (0..4).collect();
        order.shuffle(&mut rng);
        let mut sorted_indices: Vec<usize> = (0..4).collect();
        sorted_indices.sort_by_key(|&i| positions[i].1);

        for i in sorted_indices {
            let orig_idx = order[i];
            let (cx, cy) = (
                positions[i].0 + rng.random_range(-3..=3),
                positions[i].1 + rng.random_range(-3..=3),
            );
            draw_cup_2d(
                &mut img,
                cx,
                cy,
                32,
                40,
                fills[orig_idx],
                self.liquid_colors[rng.random_range(0..self.liquid_colors.len())],
            );
            let bright = if orig_idx == target_cup {
                challenge.target_brightness
            } else {
                rng.random_range(0.1..0.9)
            };
            if let Some(icon_img) = cache.get_icon(&icon_names[orig_idx], bright, 22) {
                overlay_image(&mut img, &icon_img, cx - 11, cy - 45);
            }
        }

        let img = apply_distortions(&img, rng.random_range(50..=65));

        let mut png_bytes = Vec::new();
        image::write_buffer_with_format(
            &mut Cursor::new(&mut png_bytes),
            img.as_raw(),
            img.width(),
            img.height(),
            image::ColorType::Rgba8,
            image::ImageFormat::Png,
        )
        .unwrap();

        let result = SceneResult {
            scene: scene_idx,
            fills,
            fullest,
            target_cup,
            correct: scene_idx == challenge.correct_scene,
        };

        (png_bytes, result)
    }

    /// Generate reference icon image as PNG bytes
    pub fn generate_reference(&self, challenge: &CaptchaChallenge) -> Vec<u8> {
        let mut rng = SmallRng::from_os_rng();
        let mut img = create_wood_background(REFERENCE_WIDTH, REFERENCE_HEIGHT);

        let cache = self.icon_cache.read().unwrap();
        if let Some(mut icon_img) =
            cache.get_icon(&challenge.target_icon, challenge.target_brightness, 28)
        {
            icon_img = rotate_image(&icon_img, rng.random_range(-12.0..12.0f32));
            let icon_x = rng
                .random_range(15..(REFERENCE_WIDTH as i32 - icon_img.width() as i32 - 15).max(16));
            let icon_y = rng.random_range(
                15..(REFERENCE_HEIGHT as i32 - icon_img.height() as i32 - 15).max(16),
            );
            overlay_image(&mut img, &icon_img, icon_x, icon_y);
            apply_light_wash(
                &mut img,
                icon_x + icon_img.width() as i32 / 2,
                icon_y + icon_img.height() as i32 / 2,
            );
        }

        let img = apply_distortions(&img, rng.random_range(45..=55));

        let mut png_bytes = Vec::new();
        image::write_buffer_with_format(
            &mut Cursor::new(&mut png_bytes),
            img.as_raw(),
            img.width(),
            img.height(),
            image::ColorType::Rgba8,
            image::ImageFormat::Png,
        )
        .unwrap();

        png_bytes
    }

    /// Generate all scenes in parallel
    pub fn generate_all_scenes(&self, challenge: &CaptchaChallenge) -> Vec<(Vec<u8>, SceneResult)> {
        (0..challenge.scene_count)
            .into_par_iter()
            .map(|i| self.generate_scene(challenge, i))
            .collect()
    }
}

impl Default for CaptchaGenerator {
    fn default() -> Self {
        Self::new()
    }
}
