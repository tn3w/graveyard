#![windows_subsystem = "windows"]

#[cfg(target_os = "linux")]
use minifb::Icon;
use minifb::{Key, MouseButton, MouseMode, Window, WindowOptions};
use rodio::{stream::OutputStream, stream::OutputStreamBuilder, Decoder, Sink};
use rusttype::{point, Font, Scale};
use std::{fs::File, io::BufReader, path::PathBuf, sync::Arc, time::Instant};

const BG: u32 = 0x121212;
const WHITE: u32 = 0xf0f0f0;
const GRAY: u32 = 0x606060;
const ACCENT: u32 = 0x909090;
const BTN_BG: u32 = 0x1e1e1e;
const BAR_BG: u32 = 0x252525;
const BAR_FG: u32 = 0x707070;
const GREEN: u32 = 0x4a9f4a;

const FONT_DATA: &[u8] = include_bytes!("../assets/font.ttf");
#[cfg(target_os = "linux")]
const ICON_ARGB: &[u64] = include!("../assets/icon_argb.rs");
#[cfg(windows)]
const ICON_ICO: &[u8] = include_bytes!("../assets/icon.ico");

fn main() {
    let font = Font::try_from_bytes(FONT_DATA);
    let mut app = App::new();
    let mut width = 1024usize;
    let mut height = 600usize;
    let mut buffer: Vec<u32> = vec![BG; width * height];
    let mut window = Window::new(
        "Lyrics Prompter",
        width,
        height,
        WindowOptions {
            resize: true,
            ..Default::default()
        },
    )
    .unwrap();
    window.set_target_fps(60);

    #[cfg(windows)]
    setup_window(&window);

    #[cfg(target_os = "linux")]
    window.set_icon(Icon::Buffer(ICON_ARGB.as_ptr(), ICON_ARGB.len() as u32));

    let mut prev_mouse_down = false;

    while window.is_open() && !window.is_key_down(Key::Escape) {
        let (new_width, new_height) = window.get_size();
        if new_width != width || new_height != height {
            width = new_width.max(200);
            height = new_height.max(200);
            buffer.resize(width * height, BG);
        }
        buffer.fill(BG);

        let mouse = window.get_mouse_pos(MouseMode::Clamp).unwrap_or((0.0, 0.0));
        let mouse_down = window.get_mouse_down(MouseButton::Left);
        let clicked = mouse_down && !prev_mouse_down;
        prev_mouse_down = mouse_down;

        let status_top = 8;
        let lrc_status = app.lrc_name.as_deref().unwrap_or("No lyrics loaded");
        let audio_status = app.audio_name.as_deref().unwrap_or("No audio (optional)");
        let status_text = format!("LRC: {}  |  Audio: {}", lrc_status, audio_status);
        draw_text_centered(
            &mut buffer,
            width,
            height,
            &status_text,
            status_top,
            14.0,
            GRAY,
            font.as_ref(),
        );

        let elapsed = app.get_elapsed() + 0.5;
        let idx = find_current_index(&app.lines, elapsed);

        let (prev, curr, next, countdown, progress) = if app.lines.is_empty() {
            ("", "Load an LRC file to start", "", 0.0, 0.0)
        } else if idx.is_none() {
            let time_to_first = (app.lines[0].time - elapsed).max(0.0);
            if time_to_first <= 1.0 {
                let first = app.lines[0].text.as_str();
                let second = app.lines.get(1).map(|l| l.text.as_str()).unwrap_or("");
                ("", first, second, time_to_first, 0.0)
            } else {
                let first = app.lines[0].text.as_str();
                ("", "\u{266A} \u{266A} \u{266A}", first, time_to_first, 0.0)
            }
        } else {
            let i = idx.unwrap();
            let prev = if i > 0 {
                app.lines[i - 1].text.as_str()
            } else {
                ""
            };
            let curr = app.lines[i].text.as_str();
            let next = app.lines.get(i + 1).map(|l| l.text.as_str()).unwrap_or("");
            let countdown = app
                .lines
                .get(i + 1)
                .map(|n| (n.time - elapsed).max(0.0))
                .unwrap_or(0.0);
            let progress = app
                .lines
                .get(i + 1)
                .map(|next_line| {
                    let curr_time = app.lines[i].time;
                    ((elapsed - curr_time) / (next_line.time - curr_time)).clamp(0.0, 1.0)
                })
                .unwrap_or(0.0);
            (prev, curr, next, countdown, progress)
        };

        let main_size = calc_font_size(curr, width, height, font.as_ref());
        let small_size = (main_size * 0.32).max(20.0);
        let curr_lines = wrap_text(curr, width as f32 * 0.95, main_size, font.as_ref());
        let curr_height = curr_lines.len() as f32 * main_size * 1.1;

        let content_top = 40;
        let bar_area = 90;
        let avail = height - content_top - bar_area;

        draw_text_centered(
            &mut buffer,
            width,
            height,
            prev,
            content_top,
            small_size,
            GRAY,
            font.as_ref(),
        );

        let main_top = content_top + avail / 3;
        let alpha = ((1.0 - progress) * 255.0) as u8;
        let curr_color = blend(WHITE, BG, alpha.max(120));
        draw_text_centered(
            &mut buffer,
            width,
            height,
            curr,
            main_top,
            main_size,
            curr_color,
            font.as_ref(),
        );

        let next_top = main_top + curr_height as usize + 30;
        let next_alpha = (progress * 180.0) as u8;
        let next_color = blend(ACCENT, BG, next_alpha.max(40));
        draw_text_centered(
            &mut buffer,
            width,
            height,
            next,
            next_top,
            small_size,
            next_color,
            font.as_ref(),
        );

        let bar_width = (width as f32 * 0.5) as usize;
        let bar_left = (width - bar_width) / 2;
        let bar_top = height - 70;
        draw_rect(&mut buffer, width, bar_left, bar_top, bar_width, 4, BAR_BG);
        let filled = (bar_width as f32 * progress) as usize;
        if filled > 0 {
            draw_rect(&mut buffer, width, bar_left, bar_top, filled, 4, BAR_FG);
        }

        let time_str = format!("{:.1}s", countdown);
        draw_text_centered(
            &mut buffer,
            width,
            height,
            &time_str,
            bar_top + 10,
            18.0,
            GRAY,
            font.as_ref(),
        );

        let has_lrc = !app.lines.is_empty();
        let has_audio = app.audio_path.is_some();
        let play_label = if has_audio {
            "Play"
        } else if has_lrc {
            "Lyrics"
        } else {
            "Play"
        };

        let btns = [
            ("Load LRC", if has_lrc { GREEN } else { ACCENT }),
            ("Load Audio", if has_audio { GREEN } else { ACCENT }),
            (play_label, ACCENT),
            ("Pause", ACCENT),
            ("Stop", ACCENT),
            ("Fullscreen", ACCENT),
        ];
        let btn_width = 90;
        let btn_height = 26;
        let gap = 8;
        let total_width = btns.len() * btn_width + (btns.len() - 1) * gap;
        let start_left = (width - total_width) / 2;
        let btn_top = height - 38;

        for (idx, (label, color)) in btns.iter().enumerate() {
            let btn_left = start_left + idx * (btn_width + gap);
            draw_button(
                &mut buffer,
                width,
                btn_left,
                btn_top,
                btn_width,
                btn_height,
                label,
                *color,
                font.as_ref(),
            );
            if clicked
                && in_rect(
                    mouse,
                    btn_left as f32,
                    btn_top as f32,
                    btn_width as f32,
                    btn_height as f32,
                )
            {
                match idx {
                    0 => app.load_lrc(),
                    1 => app.load_audio(),
                    2 => app.play(),
                    3 => app.pause(),
                    4 => app.stop(),
                    5 => app.fullscreen = !app.fullscreen,
                    _ => {}
                }
                if idx == 5 {
                    set_fullscreen(&window, app.fullscreen);
                }
            }
        }

        window.update_with_buffer(&buffer, width, height).unwrap();
    }
}

struct LrcLine {
    time: f32,
    text: String,
}

struct App {
    lines: Vec<LrcLine>,
    lrc_name: Option<String>,
    audio_path: Option<PathBuf>,
    audio_name: Option<String>,
    sink: Option<Arc<Sink>>,
    _stream: Option<OutputStream>,
    start_time: Option<Instant>,
    paused_at: Option<f32>,
    fullscreen: bool,
    lyrics_only: bool,
}

impl App {
    fn new() -> Self {
        Self {
            lines: vec![],
            lrc_name: None,
            audio_path: None,
            audio_name: None,
            sink: None,
            _stream: None,
            start_time: None,
            paused_at: None,
            fullscreen: false,
            lyrics_only: false,
        }
    }

    fn load_lrc(&mut self) {
        if let Some(path) = rfd::FileDialog::new()
            .add_filter("LRC", &["lrc"])
            .pick_file()
        {
            if let Ok(content) = std::fs::read_to_string(&path) {
                self.lines = parse_lrc(&content);
                self.lrc_name = path.file_name().map(|n| n.to_string_lossy().to_string());
            }
        }
    }

    fn load_audio(&mut self) {
        if let Some(path) = rfd::FileDialog::new()
            .add_filter("Audio", &["mp3", "wav", "ogg", "flac"])
            .pick_file()
        {
            self.audio_name = path.file_name().map(|n| n.to_string_lossy().to_string());
            self.audio_path = Some(path);
        }
    }

    fn play(&mut self) {
        if let Some(paused) = self.paused_at.take() {
            if self.lyrics_only {
                self.start_time = Some(Instant::now() - std::time::Duration::from_secs_f32(paused));
                return;
            }
            if let Some(sink) = &self.sink {
                sink.play();
                self.start_time = Some(Instant::now() - std::time::Duration::from_secs_f32(paused));
            }
            return;
        }

        if self.audio_path.is_none() && !self.lines.is_empty() {
            self.lyrics_only = true;
            self.start_time = Some(Instant::now());
            return;
        }

        let Some(path) = &self.audio_path else { return };
        let Ok(file) = File::open(path) else { return };
        let Ok(stream) = OutputStreamBuilder::open_default_stream() else {
            return;
        };
        let Ok(source) = Decoder::new(BufReader::new(file)) else {
            return;
        };
        let sink = Sink::connect_new(&stream.mixer());
        sink.append(source);
        sink.play();
        self.sink = Some(Arc::new(sink));
        self._stream = Some(stream);
        self.start_time = Some(Instant::now());
        self.lyrics_only = false;
    }

    fn pause(&mut self) {
        if self.lyrics_only {
            self.paused_at = Some(self.get_elapsed());
            return;
        }
        if let Some(sink) = &self.sink {
            sink.pause();
            self.paused_at = Some(self.get_elapsed());
        }
    }

    fn stop(&mut self) {
        if let Some(sink) = &self.sink {
            sink.stop();
        }
        self.sink = None;
        self._stream = None;
        self.start_time = None;
        self.paused_at = None;
        self.lyrics_only = false;
    }

    fn get_elapsed(&self) -> f32 {
        self.paused_at.unwrap_or_else(|| {
            self.start_time
                .map(|t| t.elapsed().as_secs_f32())
                .unwrap_or(0.0)
        })
    }
}

fn parse_lrc(content: &str) -> Vec<LrcLine> {
    content
        .lines()
        .filter_map(|line| {
            let line = line.trim();
            if !line.starts_with('[') {
                return None;
            }
            let end = line.find(']')?;
            let ts = &line[1..end];
            let parts: Vec<&str> = ts.split(':').collect();
            if parts.len() != 2 {
                return None;
            }
            let mins: f32 = parts[0].parse().ok()?;
            let secs: f32 = parts[1].parse().ok()?;
            let text = line[end + 1..].trim().to_string();
            if text.is_empty() {
                return None;
            }
            Some(LrcLine {
                time: mins * 60.0 + secs,
                text,
            })
        })
        .collect()
}

fn find_current_index(lines: &[LrcLine], time: f32) -> Option<usize> {
    if lines.is_empty() || time < lines[0].time {
        return None;
    }
    lines
        .iter()
        .enumerate()
        .rev()
        .find(|(_, line)| time >= line.time)
        .map(|(idx, _)| idx)
}

fn calc_font_size(text: &str, width: usize, height: usize, font: Option<&Font>) -> f32 {
    let Some(font) = font else { return 60.0 };
    let max_width = width as f32 * 0.95;
    let max_height = height as f32 * 0.3;
    let mut size = 300.0f32;
    while size > 30.0 {
        let lines = wrap_text(text, max_width, size, Some(font));
        let total = lines.len() as f32 * size * 1.1;
        if total <= max_height && lines.len() <= 2 {
            return size;
        }
        size -= 5.0;
    }
    30.0
}

fn draw_rect(
    buf: &mut [u32],
    buf_width: usize,
    left: usize,
    top: usize,
    width: usize,
    height: usize,
    color: u32,
) {
    let buf_height = buf.len() / buf_width;
    for dy in 0..height {
        for dx in 0..width {
            let px = left + dx;
            let py = top + dy;
            if px < buf_width && py < buf_height {
                buf[py * buf_width + px] = color;
            }
        }
    }
}

fn blend(fg: u32, bg: u32, alpha: u8) -> u32 {
    let mix = |f: u32, b: u32| ((f * alpha as u32 + b * (255 - alpha as u32)) / 255) as u32;
    let red = mix((fg >> 16) & 0xff, (bg >> 16) & 0xff);
    let green = mix((fg >> 8) & 0xff, (bg >> 8) & 0xff);
    let blue = mix(fg & 0xff, bg & 0xff);
    (red << 16) | (green << 8) | blue
}

fn in_rect(pos: (f32, f32), left: f32, top: f32, width: f32, height: f32) -> bool {
    pos.0 >= left && pos.0 <= left + width && pos.1 >= top && pos.1 <= top + height
}

fn draw_text(
    buf: &mut [u32],
    buf_width: usize,
    buf_height: usize,
    text: &str,
    left: i32,
    top: i32,
    size: f32,
    color: u32,
    font: Option<&Font>,
) {
    let Some(font) = font else { return };
    let scale = Scale::uniform(size);
    let metrics = font.v_metrics(scale);
    let offset = point(left as f32, top as f32 + metrics.ascent);
    for glyph in font.layout(text, scale, offset) {
        if let Some(bb) = glyph.pixel_bounding_box() {
            glyph.draw(|gx, gy, val| {
                let px = (bb.min.x + gx as i32) as usize;
                let py = (bb.min.y + gy as i32) as usize;
                if px < buf_width && py < buf_height {
                    buf[py * buf_width + px] =
                        blend(color, buf[py * buf_width + px], (val * 255.0) as u8);
                }
            });
        }
    }
}

fn text_width(text: &str, size: f32, font: Option<&Font>) -> f32 {
    let Some(font) = font else {
        return text.len() as f32 * size * 0.5;
    };
    let scale = Scale::uniform(size);
    font.layout(text, scale, point(0.0, 0.0))
        .map(|g| g.position().x + g.unpositioned().h_metrics().advance_width)
        .last()
        .unwrap_or(0.0)
}

fn wrap_text(text: &str, max_width: f32, size: f32, font: Option<&Font>) -> Vec<String> {
    let words: Vec<&str> = text.split_whitespace().collect();
    if words.is_empty() {
        return vec![text.to_string()];
    }
    let mut lines = vec![];
    let mut current = String::new();
    for word in words {
        let test = if current.is_empty() {
            word.to_string()
        } else {
            format!("{} {}", current, word)
        };
        if text_width(&test, size, font) <= max_width {
            current = test;
        } else {
            if !current.is_empty() {
                lines.push(current);
            }
            current = word.to_string();
        }
    }
    if !current.is_empty() {
        lines.push(current);
    }
    if lines.is_empty() {
        lines.push(text.to_string());
    }
    lines
}

fn draw_text_centered(
    buf: &mut [u32],
    buf_width: usize,
    buf_height: usize,
    text: &str,
    top: usize,
    size: f32,
    color: u32,
    font: Option<&Font>,
) {
    let max_width = buf_width as f32 * 0.95;
    let lines = wrap_text(text, max_width, size, font);
    let line_height = size * 1.1;
    let total = lines.len() as f32 * line_height;
    let start = top as f32 - (total - line_height) / 2.0;
    for (idx, line) in lines.iter().enumerate() {
        let width = text_width(line, size, font);
        let left = ((buf_width as f32 - width) / 2.0).max(0.0) as i32;
        let line_top = start + idx as f32 * line_height;
        draw_text(
            buf,
            buf_width,
            buf_height,
            line,
            left,
            line_top as i32,
            size,
            color,
            font,
        );
    }
}

fn draw_button(
    buf: &mut [u32],
    buf_width: usize,
    left: usize,
    top: usize,
    width: usize,
    height: usize,
    label: &str,
    color: u32,
    font: Option<&Font>,
) {
    draw_rect(buf, buf_width, left, top, width, height, BTN_BG);
    let size = 13.0;
    let tw = text_width(label, size, font);
    let tx = left as i32 + ((width as f32 - tw) / 2.0) as i32;
    let ty = top as i32 + (height as i32 - 13) / 2;
    draw_text(
        buf,
        buf_width,
        buf.len() / buf_width,
        label,
        tx,
        ty,
        size,
        color,
        font,
    );
}

#[cfg(windows)]
fn setup_window(window: &Window) {
    use std::ffi::c_void;
    #[link(name = "dwmapi")]
    extern "system" {
        fn DwmSetWindowAttribute(h: *mut c_void, a: u32, v: *const c_void, s: u32) -> i32;
    }
    #[link(name = "user32")]
    extern "system" {
        fn SendMessageW(h: *mut c_void, m: u32, w: usize, l: isize) -> isize;
        fn CreateIconFromResourceEx(
            p: *const u8,
            s: u32,
            i: i32,
            v: u32,
            x: i32,
            y: i32,
            f: u32,
        ) -> *mut c_void;
    }
    unsafe {
        let hwnd = window.get_window_handle() as *mut c_void;
        let dark: u32 = 1;
        DwmSetWindowAttribute(hwnd, 20, &dark as *const _ as _, 4);
        let entry = 6;
        let size = u32::from_le_bytes([
            ICON_ICO[entry + 8],
            ICON_ICO[entry + 9],
            ICON_ICO[entry + 10],
            ICON_ICO[entry + 11],
        ]);
        let offset = u32::from_le_bytes([
            ICON_ICO[entry + 12],
            ICON_ICO[entry + 13],
            ICON_ICO[entry + 14],
            ICON_ICO[entry + 15],
        ]) as usize;
        for (idx, sz) in [(0usize, 16i32), (1, 32)] {
            let icon = CreateIconFromResourceEx(
                ICON_ICO.as_ptr().add(offset),
                size,
                1,
                0x30000,
                sz,
                sz,
                0,
            );
            if !icon.is_null() {
                SendMessageW(hwnd, 0x80, idx, icon as isize);
            }
        }
    }
}

fn set_fullscreen(window: &Window, fullscreen: bool) {
    #[cfg(windows)]
    {
        use std::ffi::c_void;
        use std::mem::zeroed;
        #[repr(C)]
        struct Rect {
            left: i32,
            top: i32,
            right: i32,
            bottom: i32,
        }
        #[link(name = "user32")]
        extern "system" {
            fn GetWindowLongPtrW(hwnd: *mut c_void, idx: i32) -> isize;
            fn SetWindowLongPtrW(hwnd: *mut c_void, idx: i32, val: isize) -> isize;
            fn SetWindowPos(
                h: *mut c_void,
                a: *mut c_void,
                x: i32,
                y: i32,
                w: i32,
                h2: i32,
                f: u32,
            ) -> i32;
            fn GetMonitorInfoW(mon: *mut c_void, info: *mut MonitorInfo) -> i32;
            fn MonitorFromWindow(hwnd: *mut c_void, flags: u32) -> *mut c_void;
        }
        #[repr(C)]
        struct MonitorInfo {
            size: u32,
            monitor: Rect,
            work: Rect,
            flags: u32,
        }
        const GWL_STYLE: i32 = -16;
        const WS_OVERLAPPEDWINDOW: isize = 0x00CF0000;
        const WS_POPUP: isize = 0x80000000u32 as isize;
        unsafe {
            let hwnd = window.get_window_handle() as *mut c_void;
            let style = GetWindowLongPtrW(hwnd, GWL_STYLE);
            if fullscreen {
                let mon = MonitorFromWindow(hwnd, 1);
                let mut info: MonitorInfo = zeroed();
                info.size = std::mem::size_of::<MonitorInfo>() as u32;
                GetMonitorInfoW(mon, &mut info);
                SetWindowLongPtrW(hwnd, GWL_STYLE, (style & !WS_OVERLAPPEDWINDOW) | WS_POPUP);
                SetWindowPos(
                    hwnd,
                    std::ptr::null_mut(),
                    info.monitor.left,
                    info.monitor.top,
                    info.monitor.right - info.monitor.left,
                    info.monitor.bottom - info.monitor.top,
                    0x0040,
                );
            } else {
                SetWindowLongPtrW(hwnd, GWL_STYLE, style | WS_OVERLAPPEDWINDOW);
                SetWindowPos(hwnd, std::ptr::null_mut(), 100, 100, 1024, 600, 0x0040);
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
        use std::ffi::c_void;
        use std::process::Command;
        let handle = window.get_window_handle();
        if handle != std::ptr::null_mut() as *mut c_void {
            let window_id = handle as usize;
            if fullscreen {
                let _ = Command::new("wmctrl")
                    .args([
                        "-i",
                        "-r",
                        &format!("0x{:x}", window_id),
                        "-b",
                        "add,fullscreen",
                    ])
                    .spawn();
            } else {
                let _ = Command::new("wmctrl")
                    .args([
                        "-i",
                        "-r",
                        &format!("0x{:x}", window_id),
                        "-b",
                        "remove,fullscreen",
                    ])
                    .spawn();
            }
        }
    }
}
