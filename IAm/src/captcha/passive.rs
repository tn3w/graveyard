//! Passive Bot Detection Module (Compact Format v2.1)
//!
//! Parses minified client data with bitmaps and compressed arrays.

#![allow(dead_code)]

use actix_web::{web, HttpRequest, HttpResponse};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::RwLock;
use std::time::{Duration, Instant};

#[derive(Clone, Debug)]
pub struct PassiveModeConfig {
    pub threshold: f64,
    pub passive_allowed: bool, // Whether passive verification is allowed for this site
}

impl Default for PassiveModeConfig {
    fn default() -> Self {
        Self {
            threshold: 0.4,
            passive_allowed: true,
        }
    }
}

#[derive(Default)]
struct IpHistory {
    request_count: u32,
    first_seen: Option<Instant>,
    last_seen: Option<Instant>,
    scores: Vec<f64>,
}

pub struct PassiveState {
    configs: RwLock<HashMap<String, PassiveModeConfig>>,
    ip_history: RwLock<HashMap<String, IpHistory>>,
}

impl PassiveState {
    pub fn new() -> Self {
        Self {
            configs: RwLock::new(HashMap::new()),
            ip_history: RwLock::new(HashMap::new()),
        }
    }

    pub fn configure_site(&self, site_key: String, config: PassiveModeConfig) {
        self.configs.write().unwrap().insert(site_key, config);
    }

    pub fn get_config(&self, site_key: &str) -> Option<PassiveModeConfig> {
        self.configs.read().unwrap().get(site_key).cloned()
    }

    fn update_ip_history(&self, ip: &str, score: f64) {
        let mut history = self.ip_history.write().unwrap();
        let entry = history.entry(ip.to_string()).or_default();
        entry.request_count += 1;
        let now = Instant::now();
        if entry.first_seen.is_none() {
            entry.first_seen = Some(now);
        }
        entry.last_seen = Some(now);
        entry.scores.push(score);
        if entry.scores.len() > 100 {
            entry.scores.remove(0);
        }
    }

    fn get_ip_score_modifier(&self, ip: &str) -> f64 {
        let history = self.ip_history.read().unwrap();
        if let Some(entry) = history.get(ip) {
            if let (Some(first), Some(last)) = (entry.first_seen, entry.last_seen) {
                let duration = last.duration_since(first).as_secs_f64();
                if duration > 0.0 && entry.request_count as f64 / duration > 0.5 {
                    return 0.15;
                }
            }
            if entry.scores.len() >= 3 {
                let recent: Vec<_> = entry.scores.iter().rev().take(3).collect();
                let mean: f64 = recent.iter().copied().copied().sum::<f64>() / recent.len() as f64;
                let variance: f64 =
                    recent.iter().map(|&&s| (s - mean).powi(2)).sum::<f64>() / recent.len() as f64;
                if variance < 0.001 {
                    return 0.05;
                }
            }
        }
        0.0
    }

    pub fn cleanup_old_entries(&self) {
        let mut history = self.ip_history.write().unwrap();
        let cutoff = Instant::now() - Duration::from_secs(86400);
        history.retain(|_, v| v.last_seen.map(|t| t > cutoff).unwrap_or(false));
    }
}

// ============================================================================
// Compact Request Format
// ============================================================================

#[derive(Debug, Deserialize)]
pub struct PassiveVerifyRequest {
    pub site_key: String,
    pub d: CompactData,
}

/// Compact data format from client v2.1
/// a: [a0_bitmap, a1_bitmap, a2_bitmap, navigator_proto_name]
/// n: [platform, plugins_count, languages_count, cookies_enabled, dnt, cores, languages[]]
/// c: [c0_bitmap, canvas_data_len, webgl_renderer, sample_rate]
/// f: features_bitmap
/// t: [calc_time, perf_now]
/// x: tampering_bitmap
/// p: [p0_bitmap, override_count, proto_inconsistencies, navigator_tostring]
/// e: [exec_mean, exec_variance, memory_limit]
/// m: [move_count, click_count, key_count, [x,y,t,...], scroll_count, focus_changes]
/// d: [devtools_bitmap, width_diff, height_diff, open_count, was_open]
/// s: [screen_width, screen_height, color_depth, avail_width, avail_height]
/// z: [timezone, touch_bitmap, doc_state_bitmap, visibility_changes]
/// b: [sb0_bitmap, sb1_bitmap] - sophisticated bot detection
#[derive(Debug, Deserialize)]
pub struct CompactData {
    /// Automation bitmaps: [a0, a1, a2, navigator_proto_name]
    pub a: (i64, i64, i64, Option<String>),
    /// Navigator: [platform, plugins, langs_count, cookies, dnt, cores, languages[]]
    pub n: (
        Option<String>,
        Option<u32>,
        Option<u32>,
        Option<u8>,
        Option<String>,
        Option<u32>,
        Option<Vec<String>>,
    ),
    /// Canvas/WebGL/Audio: [c0_bitmap, canvas_data_len, webgl_renderer, sample_rate]
    pub c: (i64, Option<u32>, Option<String>, Option<u32>),
    /// Features bitmap
    pub f: i64,
    /// Timing: [calc_time, perf_now]
    pub t: (Option<f64>, Option<f64>),
    /// Tampering bitmap
    pub x: i64,
    /// Property integrity: [p0_bitmap, override_count, proto_issues, nav_tostring]
    pub p: (i64, Option<u32>, Option<u32>, Option<String>),
    /// Performance: [exec_mean, exec_variance, memory_limit]
    pub e: (Option<f64>, Option<f64>, Option<u64>),
    /// Mouse/interaction: [move_count, click_count, key_count, coords[], scroll_count, focus_changes]
    pub m: (
        Option<u32>,
        Option<u32>,
        Option<u32>,
        Option<Vec<f64>>,
        Option<u32>,
        Option<u32>,
    ),
    /// DevTools: [bitmap, width_diff, height_diff, open_count, was_open]
    pub d: (i64, Option<i32>, Option<i32>, Option<u32>, Option<u8>),
    /// Screen: [width, height, color_depth, avail_width, avail_height]
    pub s: Option<(
        Option<u32>,
        Option<u32>,
        Option<u32>,
        Option<u32>,
        Option<u32>,
    )>,
    /// Extra: [timezone, touch_bitmap, doc_state_bitmap, visibility_changes]
    pub z: Option<(Option<i32>, Option<u8>, Option<u8>, Option<u32>)>,
    /// Sophisticated bot detection: [sb0_bitmap, sb1_bitmap, sb2_bitmap]
    pub b: Option<(i64, i64, i64)>,
}

#[derive(Debug, Serialize)]
pub struct PassiveVerifyResponse {
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub verified_token: Option<String>,
}

/// Response for backend verification of passive tokens (includes score)
#[derive(Debug, Serialize)]
pub struct PassiveVerifyBackendResponse {
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub score: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

// ============================================================================
// Bitmap bit positions
// ============================================================================

// a0 bitmap: automation tools
const A0_CALL_PHANTOM: i64 = 1 << 0;
const A0_PHANTOM: i64 = 1 << 1;
const A0_NIGHTMARE: i64 = 1 << 2;
const A0_DOM_AUTOMATION: i64 = 1 << 3;
const A0_DOM_AUTOMATION_CONTROLLER: i64 = 1 << 4;
const A0_SELENIUM_UNDERSCORE: i64 = 1 << 5;
const A0_SELENIUM: i64 = 1 << 6;
const A0_WEBDRIVER: i64 = 1 << 7;
const A0_WEBDRIVER_SCRIPT_FN: i64 = 1 << 8;
const A0_DRIVER_EVALUATE: i64 = 1 << 9;
const A0_WEBDRIVER_EVALUATE: i64 = 1 << 10;
const A0_NAV_WEBDRIVER: i64 = 1 << 11;
const A0_HEADLESS: i64 = 1 << 12;
const A0_CYPRESS: i64 = 1 << 13;
const A0_CYPRESS_UNDERSCORE: i64 = 1 << 14;
const A0_PLAYWRIGHT_EVALUATE: i64 = 1 << 15;
const A0_PLAYWRIGHT_RESUME: i64 = 1 << 16;
const A0_PLAYWRIGHT: i64 = 1 << 17;
const A0_PUPPETEER: i64 = 1 << 18;
const A0_NIGHTMARE_BUFFER: i64 = 1 << 19;
const A0_EMIT_SPAWN: i64 = 1 << 20;
const A0_WEBDRIVER_ATTR: i64 = 1 << 21;
const A0_AWESOMIUM: i64 = 1 << 22;
const A0_GEB: i64 = 1 << 23;

// a1 bitmap: enhanced automation detection
const A1_WEBDRIVER_OVERRIDDEN: i64 = 1 << 0;
const A1_WEBDRIVER_HAS_GETTER: i64 = 1 << 1;
const A1_WEBDRIVER_HAS_VALUE: i64 = 1 << 2;
const A1_WEBDRIVER_CONFIGURABLE: i64 = 1 << 3;
const A1_WEBDRIVER_ENUMERABLE: i64 = 1 << 4;
const A1_HAS_CDC: i64 = 1 << 5;
const A1_CHROME_RUNTIME_CONNECT: i64 = 1 << 6;
const A1_STACK_HAS_AUTOMATION: i64 = 1 << 7;
const A1_STACK_HAS_EVAL: i64 = 1 << 8;
const A1_CDP_INJECTION: i64 = 1 << 9;
const A1_NAV_PROTO_MODIFIED: i64 = 1 << 10;
const A1_SELENIUM_ATTRS: i64 = 1 << 11;
const A1_NAV_CONFIGURABLE: i64 = 1 << 12;
const A1_FN_TOSTRING_TAMPERED: i64 = 1 << 13;
const A1_CDP_BINDING: i64 = 1 << 14;
const A1_CDC_PATTERN: i64 = 1 << 15;

// a2 bitmap: overrides
const A2_HAS_CHROME: i64 = 1 << 0;
const A2_HAS_PERMISSIONS: i64 = 1 << 1;
const A2_HAS_LANGUAGES: i64 = 1 << 2;
const A2_HAS_CONNECTION: i64 = 1 << 3;
const A2_HAS_BATTERY: i64 = 1 << 4;

// x bitmap: tampering
const X_TOSTRING_NATIVE: i64 = 1 << 0;
const X_SETTIMEOUT_NATIVE: i64 = 1 << 1;
const X_SETINTERVAL_NATIVE: i64 = 1 << 2;
const X_DATENOW_NATIVE: i64 = 1 << 3;
const X_MATHRANDOM_NATIVE: i64 = 1 << 4;
const X_ARRAY_PUSH_NATIVE: i64 = 1 << 5;
const X_JSON_STRINGIFY_NATIVE: i64 = 1 << 6;
const X_OBJECT_KEYS_NATIVE: i64 = 1 << 7;

// p0 bitmap: property integrity
const P0_DEFINE_PROPERTY_NATIVE: i64 = 1 << 0;
const P0_GET_OWN_PROP_DESC_NATIVE: i64 = 1 << 1;
const P0_REFLECT_GET_NATIVE: i64 = 1 << 2;
const P0_HAS_PERMISSIONS_QUERY: i64 = 1 << 3;
const P0_PERMISSIONS_QUERY_NATIVE: i64 = 1 << 4;
const P0_HAS_CHROME_OBJECT: i64 = 1 << 5;
const P0_CHROME_APP: i64 = 1 << 6;
const P0_CHROME_RUNTIME: i64 = 1 << 7;
const P0_CHROME_CSI: i64 = 1 << 8;
const P0_CHROME_LOAD_TIMES: i64 = 1 << 9;
const P0_NAV_IS_PROXY: i64 = 1 << 10;
const P0_NAV_TOSTRING_ERROR: i64 = 1 << 11;
const P0_NAV_INSTANCEOF_PROXY: i64 = 1 << 12;
const P0_NAV_TOSTRINGTAG_WRONG: i64 = 1 << 13;
const P0_NAV_GETTER_TAMPERED: i64 = 1 << 14;
const P0_REFLECT_GET_TAMPERED: i64 = 1 << 15;

// sb0 bitmap: sophisticated bot detection (Chromium/Selenium)
const SB0_CDC_VARS: i64 = 1 << 0;
const SB0_SELENIUM_UNWRAPPED: i64 = 1 << 1;
const SB0_EMPTY_PLUGINS_DESKTOP: i64 = 1 << 2;
const SB0_INVALID_PLUGIN_ARRAY: i64 = 1 << 3;
const SB0_MISSING_PLUGIN_REFRESH: i64 = 1 << 4;
const SB0_INVALID_MIME_ARRAY: i64 = 1 << 5;
const SB0_PERMISSIONS_QUERY_TAMPERED: i64 = 1 << 6;
const SB0_CHROME_MISSING_CSI_LOADTIMES: i64 = 1 << 7;
const SB0_CHROME_RUNTIME_CONNECT_ERROR: i64 = 1 << 8;
const SB0_NOTIFICATION_DENIED_VISIBLE: i64 = 1 << 9;
const SB0_ZERO_OUTER_DIMENSIONS: i64 = 1 << 10;
const SB0_MISSING_SPEECH_SYNTHESIS: i64 = 1 << 11;
const SB0_TIMEZONE_INCONSISTENCY: i64 = 1 << 12;
const SB0_SWIFTSHADER_RENDERER: i64 = 1 << 13;
const SB0_GOOGLE_SWIFTSHADER: i64 = 1 << 14;
const SB0_MISSING_BLUETOOTH: i64 = 1 << 15;

// sb1 bitmap: sophisticated bot detection (stealth/advanced)
const SB1_STEALTH_IFRAME: i64 = 1 << 0;
const SB1_WEBDRIVER_ON_NAV_INSTANCE: i64 = 1 << 1;
const SB1_PUPPETEER_STACK: i64 = 1 << 2;
const SB1_UNIFORM_PERF_NOW: i64 = 1 << 3;
const SB1_MISSING_PERF_OBSERVER: i64 = 1 << 4;
const SB1_PROXY_WINDOW: i64 = 1 << 5;
const SB1_SCREEN_AVAIL_MATCH: i64 = 1 << 6;
const SB1_MISSING_MEDIA_DEVICES: i64 = 1 << 7;
const SB1_ZERO_RTT: i64 = 1 << 8;
const SB1_MISSING_CHROME_APP: i64 = 1 << 9;
const SB1_DOC_CDC_KEYS: i64 = 1 << 10;
const SB1_FAKE_WEBDRIVER_GETTER: i64 = 1 << 11;
const SB1_HEADLESS_WITH_PLUGINS: i64 = 1 << 12;
const SB1_MISSING_CLIENT_INFO: i64 = 1 << 13;
const SB1_INVALID_PERMISSIONS_PROTO: i64 = 1 << 14;
const SB1_INVALID_DEVICE_MEMORY: i64 = 1 << 15;

// sb2 bitmap: harder to evade signals (targeting undetected-chromedriver)
const SB2_WEBDRIVER_UNDEFINED: i64 = 1 << 0;
const SB2_WEBDRIVER_REFLECT_UNDEFINED: i64 = 1 << 1;
const SB2_POINTER_MEDIA_MISMATCH: i64 = 1 << 2;
const SB2_NOTIFICATION_NOT_NATIVE: i64 = 1 << 3;
const SB2_RAF_TIMING_ISSUE: i64 = 1 << 4;
const SB2_NAV_TIMING_ZERO_DCL: i64 = 1 << 5;
const SB2_NAV_TIMING_ZERO_LOAD: i64 = 1 << 6;
const SB2_SELENIUM_CONSOLE_HELPERS: i64 = 1 << 7;
const SB2_CDC_WINDOW_PROPS: i64 = 1 << 8;
const SB2_CDC_PROTO_PROPS: i64 = 1 << 9;
const SB2_SCREEN_EXTENDED_MISMATCH: i64 = 1 << 10;
const SB2_MISSING_SHARED_WORKER: i64 = 1 << 11;
const SB2_MISSING_BROADCAST_CHANNEL: i64 = 1 << 12;
const SB2_MISSING_USB_API: i64 = 1 << 13;
const SB2_MISSING_SERIAL_API: i64 = 1 << 14;
const SB2_MISSING_HID_API: i64 = 1 << 15;

// f bitmap: features
const F_LOCAL_STORAGE: i64 = 1 << 0;
const F_SESSION_STORAGE: i64 = 1 << 1;
const F_WEBSOCKETS: i64 = 1 << 2;
const F_WEBGL: i64 = 1 << 3;
const F_WEBGL2: i64 = 1 << 4;
const F_WEBASSEMBLY: i64 = 1 << 5;
const F_INDEXEDDB: i64 = 1 << 6;
const F_NOTIFICATION: i64 = 1 << 7;
const F_FETCH: i64 = 1 << 8;
const F_PROMISE: i64 = 1 << 9;
const F_INTL: i64 = 1 << 10;
const F_SHARED_ARRAY_BUFFER: i64 = 1 << 11;

// c0 bitmap: canvas/webgl/audio
const C0_CANVAS_SUPPORTED: i64 = 1 << 0;
const C0_CANVAS_ERROR: i64 = 1 << 1;
const C0_CANVAS_EMPTY: i64 = 1 << 2;
const C0_WEBGL_SUPPORTED: i64 = 1 << 3;
const C0_WEBGL_ERROR: i64 = 1 << 4;
const C0_AUDIO_SUPPORTED: i64 = 1 << 5;
const C0_AUDIO_ERROR: i64 = 1 << 6;
const C0_WEBGL_RENDERER_MISMATCH: i64 = 1 << 7;

// d bitmap: devtools detection methods
const D_SIZE_DIFF: i64 = 1 << 0;
const D_FIREBUG: i64 = 1 << 1;
const D_CONSOLE_TIMING: i64 = 1 << 2;
const D_ELEMENT_INSPECT: i64 = 1 << 3;
const D_REGEX_TOSTRING: i64 = 1 << 4;

// ============================================================================
// Analysis
// ============================================================================

struct AnalysisContext {
    score: f64,
    reasons: Vec<String>,
}

impl AnalysisContext {
    fn new() -> Self {
        Self {
            score: 0.0,
            reasons: Vec::new(),
        }
    }

    fn add(&mut self, reason: &str, score: f64) {
        self.reasons.push(reason.to_string());
        self.score = (self.score + score).min(1.0);
    }
}

fn bit(v: i64, mask: i64) -> bool {
    (v & mask) != 0
}

fn analyze_automation(d: &CompactData, ctx: &mut AnalysisContext) {
    let a0 = d.a.0;
    let a1 = d.a.1;

    // Direct automation indicators
    let indicators = [
        (bit(a0, A0_WEBDRIVER), "webdriver"),
        (bit(a0, A0_NAV_WEBDRIVER), "navigator.webdriver"),
        (bit(a0, A0_SELENIUM), "selenium"),
        (bit(a0, A0_SELENIUM_UNDERSCORE), "_selenium"),
        (bit(a0, A0_CALL_PHANTOM), "callPhantom"),
        (bit(a0, A0_PHANTOM), "_phantom"),
        (bit(a0, A0_NIGHTMARE), "__nightmare"),
        (bit(a0, A0_PLAYWRIGHT_EVALUATE), "__playwright_evaluate"),
        (bit(a0, A0_PLAYWRIGHT), "playwright"),
        (bit(a0, A0_PUPPETEER), "puppeteer"),
        (bit(a0, A0_CYPRESS), "Cypress"),
        (bit(a0, A0_CYPRESS_UNDERSCORE), "__cypress"),
        (bit(a0, A0_WEBDRIVER_EVALUATE), "__webdriver_evaluate"),
        (bit(a0, A0_DRIVER_EVALUATE), "__driver_evaluate"),
        (
            bit(a0, A0_DOM_AUTOMATION_CONTROLLER),
            "domAutomationController",
        ),
    ];

    for (detected, name) in indicators {
        if detected {
            ctx.add(&format!("Automation: {}", name), 0.5);
            return;
        }
    }

    // Enhanced detection
    if bit(a1, A1_WEBDRIVER_OVERRIDDEN) {
        ctx.add("webdriver property overridden", 0.45);
    }
    if bit(a1, A1_WEBDRIVER_HAS_GETTER) {
        ctx.add("webdriver has custom getter", 0.4);
    }
    if bit(a1, A1_WEBDRIVER_CONFIGURABLE) {
        ctx.add("webdriver is configurable", 0.35);
    }
    if bit(a1, A1_HAS_CDC) {
        ctx.add("CDP artifacts detected", 0.5);
    }
    if bit(a1, A1_CDP_INJECTION) {
        ctx.add("CDP script injection detected", 0.5);
    }
    if bit(a1, A1_NAV_PROTO_MODIFIED) {
        ctx.add("Navigator prototype modified", 0.45);
    }
    if bit(a1, A1_STACK_HAS_AUTOMATION) {
        ctx.add("Stack has automation references", 0.4);
    }
    // Note: A1_STACK_HAS_EVAL is NOT checked here because normal Chromium browsers
    // legitimately have 'eval' and '<anonymous>' in their stack traces due to
    // browser extensions, devtools, and internal browser code. This is not a
    // reliable CDP indicator on its own.
    if bit(a1, A1_SELENIUM_ATTRS) {
        ctx.add("Selenium attributes in DOM", 0.4);
    }
    // Note: A1_NAV_CONFIGURABLE removed - navigator being configurable is normal in modern browsers
    if bit(a1, A1_FN_TOSTRING_TAMPERED) {
        ctx.add("Function.prototype.toString tampered", 0.35);
    }
    if bit(a1, A1_CDP_BINDING) {
        ctx.add("CDP binding artifacts detected", 0.45);
    }
    if bit(a1, A1_CDC_PATTERN) {
        ctx.add("CDC pattern in window keys", 0.5);
    }
    if bit(a0, A0_HEADLESS) {
        ctx.add("Headless browser detected", 0.4);
    }
}

fn analyze_navigator(d: &CompactData, ctx: &mut AnalysisContext, req: &HttpRequest) {
    let (platform, plugins, _langs_count, _cookies, _dnt, cores, _langs) = &d.n;

    // Check UA from request header
    if let Some(header_ua) = req
        .headers()
        .get("user-agent")
        .and_then(|h| h.to_str().ok())
    {
        if let Some(plat) = platform {
            let plat_lower = plat.to_lowercase();
            let ua_lower = header_ua.to_lowercase();
            let consistent = (plat_lower.contains("win") && ua_lower.contains("windows"))
                || (plat_lower.contains("mac") && ua_lower.contains("mac"))
                || (plat_lower.contains("linux") && ua_lower.contains("linux"))
                || (plat_lower.contains("android") && ua_lower.contains("android"))
                || (plat_lower.contains("iphone") && ua_lower.contains("iphone"));
            if !consistent && !plat.is_empty() {
                ctx.add("Platform inconsistent with UA", 0.35);
            }
        }
    }

    if *cores == Some(1) {
        ctx.add("Suspicious hardware concurrency: 1", 0.05);
    }

    if *plugins == Some(0) {
        if let Some(header_ua) = req
            .headers()
            .get("user-agent")
            .and_then(|h| h.to_str().ok())
        {
            if !header_ua.to_lowercase().contains("mobile") {
                ctx.add("No plugins in desktop browser", 0.1);
            }
        }
    }
}

fn analyze_property_integrity(d: &CompactData, ctx: &mut AnalysisContext) {
    let p0 = d.p.0;
    let overrides = d.p.1.unwrap_or(0);
    let proto_issues = d.p.2.unwrap_or(0);

    if !bit(p0, P0_DEFINE_PROPERTY_NATIVE) {
        ctx.add("Object.defineProperty tampered", 0.4);
    }
    if overrides > 0 {
        let score = match overrides {
            1 => 0.3,
            2 => 0.4,
            _ => 0.5,
        };
        ctx.add(&format!("Navigator overrides: {}", overrides), score);
    }
    if proto_issues > 0 {
        ctx.add(&format!("Prototype inconsistencies: {}", proto_issues), 0.3);
    }
    if !bit(p0, P0_GET_OWN_PROP_DESC_NATIVE) {
        ctx.add("getOwnPropertyDescriptor tampered", 0.35);
    }
    if !bit(p0, P0_REFLECT_GET_NATIVE) {
        ctx.add("Reflect.get tampered", 0.35);
    }
    if bit(p0, P0_NAV_IS_PROXY) {
        ctx.add("Navigator is Proxy", 0.45);
    }
    if bit(p0, P0_NAV_TOSTRING_ERROR) {
        ctx.add("Navigator.toString error", 0.3);
    }
    if bit(p0, P0_HAS_CHROME_OBJECT) && !bit(p0, P0_CHROME_CSI) && !bit(p0, P0_CHROME_LOAD_TIMES) {
        ctx.add("Chrome object missing csi/loadTimes", 0.1);
    }
    if bit(p0, P0_HAS_PERMISSIONS_QUERY) && !bit(p0, P0_PERMISSIONS_QUERY_NATIVE) {
        ctx.add("permissions.query not native", 0.3);
    }
    if bit(p0, P0_NAV_INSTANCEOF_PROXY) {
        ctx.add("Navigator instanceof Proxy", 0.4);
    }
    if bit(p0, P0_NAV_TOSTRINGTAG_WRONG) {
        ctx.add("Navigator Symbol.toStringTag wrong", 0.35);
    }
    if bit(p0, P0_NAV_GETTER_TAMPERED) {
        ctx.add("Navigator property getters tampered", 0.4);
    }
    if bit(p0, P0_REFLECT_GET_TAMPERED) {
        ctx.add("Reflect.get tampered (stealth plugin)", 0.4);
    }

    // Check navigator proto name (now at index 3 in 'a' tuple)
    if let Some(npn) = &d.a.3 {
        if npn != "Navigator" {
            ctx.add(&format!("Suspicious navigator proto: {}", npn), 0.3);
        }
    }
}

fn analyze_tampering(d: &CompactData, ctx: &mut AnalysisContext) {
    let x = d.x;
    let mut tampered = Vec::new();

    if !bit(x, X_TOSTRING_NATIVE) {
        tampered.push("toString");
    }
    if !bit(x, X_SETTIMEOUT_NATIVE) {
        tampered.push("setTimeout");
    }
    if !bit(x, X_SETINTERVAL_NATIVE) {
        tampered.push("setInterval");
    }
    if !bit(x, X_DATENOW_NATIVE) {
        tampered.push("Date.now");
    }
    if !bit(x, X_MATHRANDOM_NATIVE) {
        tampered.push("Math.random");
    }

    if !tampered.is_empty() {
        ctx.add(
            &format!("Tampered: {}", tampered.join(", ")),
            0.2 * tampered.len().min(2) as f64,
        );
    }
}

fn analyze_canvas_webgl(d: &CompactData, ctx: &mut AnalysisContext) {
    let c0 = d.c.0;

    if bit(c0, C0_CANVAS_SUPPORTED) && bit(c0, C0_CANVAS_EMPTY) {
        ctx.add("Canvas returns empty data", 0.2);
    }

    if let Some(renderer) = &d.c.2 {
        let r_lower = renderer.to_lowercase();
        if r_lower.contains("swiftshader") || r_lower.contains("llvmpipe") {
            ctx.add("Software renderer detected", 0.1);
        }
    }
}

fn analyze_features(d: &CompactData, ctx: &mut AnalysisContext) {
    let f = d.f;
    let mut missing = 0;

    if !bit(f, F_LOCAL_STORAGE) {
        missing += 1;
    }
    if !bit(f, F_SESSION_STORAGE) {
        missing += 1;
    }
    if !bit(f, F_WEBSOCKETS) {
        missing += 1;
    }

    if missing > 0 {
        ctx.add(
            &format!("Missing {} critical features", missing),
            missing as f64 * 0.1,
        );
    }

    let has_advanced = bit(f, F_WEBGL2) || bit(f, F_WEBASSEMBLY);
    let missing_basic = !bit(f, F_LOCAL_STORAGE) || !bit(f, F_WEBSOCKETS);
    if has_advanced && missing_basic {
        ctx.add("Inconsistent feature support", 0.15);
    }
}

fn analyze_devtools(d: &CompactData, ctx: &mut AnalysisContext) {
    let (dt_bitmap, dw, dh, open_count, was_open) = &d.d;

    // Check devtools detection bitmap
    if bit(*dt_bitmap, D_SIZE_DIFF) {
        ctx.add("DevTools size difference detected", 0.05);
    }
    if bit(*dt_bitmap, D_FIREBUG) {
        ctx.add("Firebug detected", 0.1);
    }
    if bit(*dt_bitmap, D_CONSOLE_TIMING) {
        ctx.add("Console timing anomaly", 0.05);
    }
    if bit(*dt_bitmap, D_ELEMENT_INSPECT) {
        ctx.add("Element inspection detected", 0.05);
    }
    if bit(*dt_bitmap, D_REGEX_TOSTRING) {
        ctx.add("Regex toString devtools detection", 0.05);
    }

    // Check window size differences
    if dw.unwrap_or(0) > 200 || dh.unwrap_or(0) > 200 {
        ctx.add("DevTools likely open (size)", 0.1);
    }

    // Check if devtools was opened multiple times
    if let Some(count) = open_count {
        if *count > 2 {
            ctx.add(&format!("DevTools opened {} times", count), 0.05);
        }
    }

    // Check if devtools was ever open
    if *was_open == Some(1) {
        ctx.add("DevTools was open during session", 0.05);
    }
}

fn analyze_screen(d: &CompactData, ctx: &mut AnalysisContext) {
    let Some((width, height, depth, avail_w, avail_h)) = &d.s else {
        return;
    };

    let w = width.unwrap_or(0);
    let h = height.unwrap_or(0);
    let cd = depth.unwrap_or(0);
    let _aw = avail_w.unwrap_or(0);
    let _ah = avail_h.unwrap_or(0);

    // Check for suspicious screen dimensions
    if w == 0 || h == 0 {
        ctx.add("Missing screen dimensions", 0.15);
    }

    // Check for common headless/VM screen sizes
    if (w == 800 && h == 600) || (w == 1024 && h == 768) {
        ctx.add(&format!("Common VM screen size: {}x{}", w, h), 0.05);
    }

    // Check color depth
    if cd < 24 && cd > 0 {
        ctx.add(&format!("Low color depth: {}", cd), 0.05);
    }

    // Note: screen.availWidth/availHeight refer to OS-level available space
    // (excluding OS taskbars/docks), NOT browser UI elements like vertical tab bars.
    // Many legitimate setups have avail == screen:
    // - Auto-hiding taskbars/docks
    // - Fullscreen mode
    // - Linux/tiling WMs without traditional taskbars
    // - macOS with auto-hide dock
    // This is NOT a reliable bot indicator on its own, so we don't flag it.
}

fn analyze_extra(d: &CompactData, ctx: &mut AnalysisContext, has_indicators: bool) {
    let Some((tz, touch, doc_state, vis_changes)) = &d.z else {
        return;
    };

    // Touch bitmap: bit 0 = ontouchstart, bit 1 = maxTouchPoints > 0
    let touch_val = touch.unwrap_or(0);
    let has_touchstart = (touch_val & 1) != 0;
    let has_touchpoints = (touch_val & 2) != 0;

    // Inconsistent touch support
    if has_touchstart != has_touchpoints && has_indicators {
        ctx.add("Inconsistent touch support", 0.1);
    }

    // Document state bitmap: bit 0 = hidden, bit 1 = hasFocus, bit 2 = visible
    let ds = doc_state.unwrap_or(0);
    let is_hidden = (ds & 1) != 0;
    let has_focus = (ds & 2) != 0;
    let is_visible = (ds & 4) != 0;

    // Document hidden but has focus is suspicious
    if is_hidden && has_focus && has_indicators {
        ctx.add("Document hidden but has focus", 0.15);
    }

    // Not visible but not hidden is inconsistent
    if !is_visible && !is_hidden && has_indicators {
        ctx.add("Inconsistent visibility state", 0.1);
    }

    // High visibility changes might indicate automation
    if let Some(vc) = vis_changes {
        if *vc > 10 && has_indicators {
            ctx.add(&format!("High visibility changes: {}", vc), 0.1);
        }
    }

    // Timezone check (optional, just log unusual values)
    if let Some(t) = tz {
        // Timezone offset in minutes, valid range roughly -720 to +840
        if *t < -720 || *t > 840 {
            ctx.add(&format!("Invalid timezone offset: {}", t), 0.1);
        }
    }
}

/// Analyze sophisticated Chromium/Selenium bot detection signals
fn analyze_sophisticated_bot(d: &CompactData, ctx: &mut AnalysisContext) {
    let Some((sb0, sb1, sb2)) = d.b else { return };

    // === SB0: Chromium/Selenium specific detection ===

    // High confidence indicators (direct automation artifacts)
    if bit(sb0, SB0_CDC_VARS) {
        ctx.add("Chromedriver $cdc_ variables detected", 0.5);
    }
    if bit(sb0, SB0_SELENIUM_UNWRAPPED) {
        ctx.add("Selenium unwrapped/evaluate detected", 0.5);
    }

    // Medium confidence indicators
    if bit(sb0, SB0_INVALID_PLUGIN_ARRAY) {
        ctx.add("Invalid PluginArray prototype", 0.4);
    }
    if bit(sb0, SB0_INVALID_MIME_ARRAY) {
        ctx.add("Invalid MimeTypeArray prototype", 0.35);
    }
    if bit(sb0, SB0_MISSING_PLUGIN_REFRESH) {
        ctx.add("Missing plugins.refresh method", 0.3);
    }
    if bit(sb0, SB0_PERMISSIONS_QUERY_TAMPERED) {
        ctx.add("permissions.query tampered", 0.35);
    }

    // Chrome object inconsistencies
    if bit(sb0, SB0_CHROME_MISSING_CSI_LOADTIMES) {
        ctx.add("Chrome object missing csi/loadTimes", 0.25);
    }
    if bit(sb0, SB0_CHROME_RUNTIME_CONNECT_ERROR) {
        ctx.add("Chrome runtime.connect error mismatch", 0.2);
    }

    // Headless indicators
    if bit(sb0, SB0_ZERO_OUTER_DIMENSIONS) {
        ctx.add("Zero outer window dimensions (headless)", 0.4);
    }
    if bit(sb0, SB0_SWIFTSHADER_RENDERER) {
        ctx.add("SwiftShader/software renderer detected", 0.25);
    }
    if bit(sb0, SB0_GOOGLE_SWIFTSHADER) {
        ctx.add("Google Inc. + SwiftShader (headless Chrome)", 0.35);
    }
    if bit(sb0, SB0_MISSING_SPEECH_SYNTHESIS) {
        ctx.add("Missing speechSynthesis in Chrome", 0.2);
    }

    // Environment inconsistencies
    if bit(sb0, SB0_TIMEZONE_INCONSISTENCY) {
        ctx.add("Timezone/Intl inconsistency", 0.25);
    }
    if bit(sb0, SB0_NOTIFICATION_DENIED_VISIBLE) {
        ctx.add("Notification denied on visible document", 0.15);
    }
    if bit(sb0, SB0_EMPTY_PLUGINS_DESKTOP) {
        ctx.add("Empty plugins on desktop browser", 0.15);
    }
    if bit(sb0, SB0_MISSING_BLUETOOTH) {
        ctx.add("Missing Bluetooth API in modern Chrome", 0.1);
    }

    // === SB1: Stealth/Advanced detection ===

    // High confidence stealth indicators
    if bit(sb1, SB1_STEALTH_IFRAME) {
        ctx.add("Stealth iframe srcdoc injection detected", 0.45);
    }
    if bit(sb1, SB1_PUPPETEER_STACK) {
        ctx.add("Puppeteer/Playwright in stack trace", 0.5);
    }
    if bit(sb1, SB1_FAKE_WEBDRIVER_GETTER) {
        ctx.add("Fake webdriver getter detected", 0.45);
    }
    if bit(sb1, SB1_DOC_CDC_KEYS) {
        ctx.add("Document has cdc/selenium keys", 0.45);
    }

    // Medium confidence indicators
    if bit(sb1, SB1_WEBDRIVER_ON_NAV_INSTANCE) {
        ctx.add("webdriver on navigator instance (not proto)", 0.4);
    }
    if bit(sb1, SB1_PROXY_WINDOW) {
        ctx.add("Window wrapped in Proxy", 0.35);
    }
    if bit(sb1, SB1_UNIFORM_PERF_NOW) {
        ctx.add("Suspicious performance.now() uniformity", 0.3);
    }
    if bit(sb1, SB1_INVALID_PERMISSIONS_PROTO) {
        ctx.add("Invalid Permissions prototype", 0.3);
    }
    if bit(sb1, SB1_INVALID_DEVICE_MEMORY) {
        ctx.add("Invalid deviceMemory value", 0.25);
    }

    // Inconsistency indicators
    if bit(sb1, SB1_HEADLESS_WITH_PLUGINS) {
        ctx.add("Headless UA but has plugins (inconsistent)", 0.35);
    }
    if bit(sb1, SB1_MISSING_CHROME_APP) {
        ctx.add("Chrome UA but missing chrome.app", 0.2);
    }
    if bit(sb1, SB1_MISSING_CLIENT_INFO) {
        ctx.add("Missing clientInformation in Chrome", 0.15);
    }
    if bit(sb1, SB1_MISSING_MEDIA_DEVICES) {
        ctx.add("Missing MediaDevices in Chrome desktop", 0.2);
    }
    if bit(sb1, SB1_MISSING_PERF_OBSERVER) {
        ctx.add("Missing PerformanceObserver in Chrome", 0.15);
    }
    if bit(sb1, SB1_ZERO_RTT) {
        ctx.add("Zero connection RTT", 0.15);
    }

    // === SB2: Harder to evade signals (targeting undetected-chromedriver) ===

    // Webdriver value checks (UC often returns undefined instead of false)
    if bit(sb2, SB2_WEBDRIVER_UNDEFINED) {
        ctx.add("webdriver returns undefined (should be false)", 0.4);
    }
    if bit(sb2, SB2_WEBDRIVER_REFLECT_UNDEFINED) {
        ctx.add("webdriver via Reflect returns undefined", 0.35);
    }

    // Media/pointer checks
    if bit(sb2, SB2_POINTER_MEDIA_MISMATCH) {
        ctx.add("Pointer media query mismatch", 0.25);
    }

    // Native code checks
    if bit(sb2, SB2_NOTIFICATION_NOT_NATIVE) {
        ctx.add("Notification constructor not native", 0.3);
    }

    // Timing checks
    if bit(sb2, SB2_RAF_TIMING_ISSUE) {
        ctx.add("requestAnimationFrame timing issue", 0.2);
    }
    if bit(sb2, SB2_NAV_TIMING_ZERO_DCL) {
        ctx.add("Navigation timing: zero DOMContentLoaded", 0.25);
    }
    if bit(sb2, SB2_NAV_TIMING_ZERO_LOAD) {
        ctx.add("Navigation timing: zero load on complete doc", 0.25);
    }

    // Selenium/CDP artifacts
    if bit(sb2, SB2_SELENIUM_CONSOLE_HELPERS) {
        ctx.add("Selenium console helpers detected", 0.35);
    }
    if bit(sb2, SB2_CDC_WINDOW_PROPS) {
        ctx.add("CDC properties in window", 0.45);
    }
    if bit(sb2, SB2_CDC_PROTO_PROPS) {
        ctx.add("CDC properties in window prototype", 0.45);
    }

    // Screen/display checks
    if bit(sb2, SB2_SCREEN_EXTENDED_MISMATCH) {
        ctx.add("Screen isExtended mismatch", 0.2);
    }

    // Missing APIs (common in headless/automation)
    let missing_apis = [
        (bit(sb2, SB2_MISSING_SHARED_WORKER), "SharedWorker"),
        (bit(sb2, SB2_MISSING_BROADCAST_CHANNEL), "BroadcastChannel"),
        (bit(sb2, SB2_MISSING_USB_API), "USB"),
        (bit(sb2, SB2_MISSING_SERIAL_API), "Serial"),
        (bit(sb2, SB2_MISSING_HID_API), "HID"),
    ];
    let missing_count = missing_apis.iter().filter(|(b, _)| *b).count();
    if missing_count >= 3 {
        ctx.add(
            &format!("Missing {} browser APIs (automation)", missing_count),
            0.35,
        );
    } else if missing_count >= 2 {
        ctx.add(&format!("Missing {} browser APIs", missing_count), 0.2);
    }
}

/// Server-side mouse movement analysis from compressed data
fn analyze_mouse(d: &CompactData, ctx: &mut AnalysisContext, _has_indicators: bool) {
    let (move_count, click_count, key_count, coords, scroll_count, focus_changes) = &d.m;
    let mc = move_count.unwrap_or(0);
    let sc = scroll_count.unwrap_or(0);
    let fc = focus_changes.unwrap_or(0);
    let cc = click_count.unwrap_or(0);
    let kc = key_count.unwrap_or(0);

    // No interaction at all is suspicious
    if mc == 0 && sc == 0 && cc == 0 && kc == 0 {
        ctx.add("No user interaction detected", 0.25);
        return;
    }

    if mc == 0 {
        ctx.add("No mouse movement", 0.2);
        return;
    }

    if mc < 10 {
        ctx.add(&format!("Very few movements: {}", mc), 0.15);
    }

    // Check for suspicious focus patterns (too many focus changes might indicate automation)
    if fc > 20 {
        ctx.add(&format!("Excessive focus changes: {}", fc), 0.1);
    }

    let Some(coords) = coords else { return };
    if coords.len() < 15 {
        return;
    } // Need at least 5 points (x,y,t each)

    // Parse flattened coords [x,y,t,x,y,t,...]
    let mut points: Vec<(f64, f64, f64)> = Vec::new();
    let mut i = 0;
    while i + 2 < coords.len() {
        points.push((coords[i], coords[i + 1], coords[i + 2]));
        i += 3;
    }

    if points.len() < 5 {
        return;
    }

    // Calculate intervals and velocities
    let mut intervals: Vec<f64> = Vec::new();
    let mut velocities: Vec<f64> = Vec::new();
    let mut teleport_count = 0;
    let mut zero_interval_count = 0;

    for i in 1..points.len() {
        let (x1, y1, t1) = points[i - 1];
        let (x2, y2, t2) = points[i];
        let dt = t2 - t1;

        if dt > 0.0 {
            intervals.push(dt);
            let dx = x2 - x1;
            let dy = y2 - y1;
            let dist = (dx * dx + dy * dy).sqrt();
            velocities.push(dist / dt);

            if dist > 200.0 && dt < 20.0 {
                teleport_count += 1;
            }
        }
        if dt == 0.0 {
            zero_interval_count += 1;
        }
    }

    if intervals.is_empty() {
        return;
    }

    // Teleportation detection - ALWAYS check (behavioral, can't be faked)
    if teleport_count > 0 {
        ctx.add(&format!("Mouse teleportation: {}", teleport_count), 0.35);
    }

    // Zero interval detection
    if zero_interval_count > 5 {
        ctx.add(
            &format!("Zero-interval events: {}", zero_interval_count),
            0.3,
        );
    }

    // Calculate interval statistics
    let avg_interval = intervals.iter().sum::<f64>() / intervals.len() as f64;
    let interval_var = intervals
        .iter()
        .map(|&i| (i - avg_interval).powi(2))
        .sum::<f64>()
        / intervals.len() as f64;
    let interval_std = interval_var.sqrt();
    let cv = if avg_interval > 0.0 {
        interval_std / avg_interval
    } else {
        0.0
    }; // Coefficient of variation

    // Calculate interval uniformity via buckets
    let mut interval_buckets: HashMap<i64, u32> = HashMap::new();
    for &iv in &intervals {
        let bucket = (iv / 10.0).round() as i64 * 10;
        *interval_buckets.entry(bucket).or_insert(0) += 1;
    }
    let max_bucket_count = interval_buckets.values().max().copied().unwrap_or(0);
    let uniform_ratio = max_bucket_count as f64 / intervals.len() as f64;

    // BEHAVIORAL DETECTION - These can't be faked by undetected-chromedriver
    // Real human mouse movement has high variance in timing (CV typically > 0.3)
    // Selenium ActionChains produces very uniform timing (CV < 0.2)

    // Key insight: Real users at 60Hz have ~16ms intervals which look uniform,
    // but that's FAST movement. Bots have ~250-300ms intervals which is SLOW.
    // We only flag uniform timing if it's also SLOW (avg > 100ms).

    // Check coefficient of variation - low CV with slow intervals means robotic
    if cv < 0.15 && avg_interval > 100.0 && intervals.len() >= 10 {
        ctx.add(
            &format!("Robotic timing pattern: CV={:.2} (too uniform)", cv),
            0.45,
        );
    } else if cv < 0.20 && avg_interval > 150.0 && intervals.len() >= 10 {
        ctx.add(&format!("Suspicious timing uniformity: CV={:.2}", cv), 0.3);
    }

    // Check for very uniform intervals - only flag if SLOW (not 60Hz natural movement)
    // Real users at 60Hz have avg ~16ms, bots have avg ~250-300ms
    if uniform_ratio > 0.7 && avg_interval > 100.0 && intervals.len() >= 10 {
        // High uniform ratio with slow intervals is very suspicious
        let score = if uniform_ratio > 0.9 { 0.5 } else { 0.4 };
        ctx.add(
            &format!(
                "Uniform slow intervals: {:.0}% in same bucket, avg={:.0}ms",
                uniform_ratio * 100.0,
                avg_interval
            ),
            score,
        );
    }

    // Check for robotic timing with specific patterns
    // Selenium typically produces intervals around 250-300ms with low std dev
    if avg_interval > 200.0 && avg_interval < 400.0 && interval_std < 50.0 && intervals.len() >= 10
    {
        ctx.add(
            &format!(
                "Selenium-like timing: avg={:.0}ms std={:.1}ms",
                avg_interval, interval_std
            ),
            0.4,
        );
    }

    // Check for perfectly regular intervals (same interval repeated)
    // Bots often have intervals that are exact multiples of a base value
    // Find the most common interval (mode) rather than using the first one
    if intervals.len() >= 10 {
        let mut interval_counts: HashMap<i64, u32> = HashMap::new();
        for &iv in &intervals {
            if iv > 50.0 && iv < 1000.0 {
                // Only consider reasonable intervals
                let rounded = (iv / 5.0).round() as i64 * 5; // Round to nearest 5ms
                *interval_counts.entry(rounded).or_insert(0) += 1;
            }
        }

        if let Some((&mode_interval, &mode_count)) = interval_counts.iter().max_by_key(|(_, &c)| c)
        {
            let mode_ratio = mode_count as f64 / intervals.len() as f64;
            // If 70%+ of intervals are the same value (within 5ms), that's robotic
            if mode_ratio > 0.7 && mode_interval > 100 {
                ctx.add(
                    &format!(
                        "Machine-precise intervals: {:.0}% at ~{}ms",
                        mode_ratio * 100.0,
                        mode_interval
                    ),
                    0.45,
                );
            }
        }
    }

    // Check for perfectly linear movement (no curves)
    if points.len() >= 10 {
        let mut direction_changes = 0;
        for i in 2..points.len() {
            let (x0, y0, _) = points[i - 2];
            let (x1, y1, _) = points[i - 1];
            let (x2, y2, _) = points[i];

            let dx1 = x1 - x0;
            let dy1 = y1 - y0;
            let dx2 = x2 - x1;
            let dy2 = y2 - y1;

            // Cross product to detect direction change
            let cross = dx1 * dy2 - dy1 * dx2;
            if cross.abs() > 5.0 {
                // Threshold for meaningful direction change
                direction_changes += 1;
            }
        }

        let direction_change_ratio = direction_changes as f64 / (points.len() - 2) as f64;

        // Real humans have lots of micro-corrections (ratio > 0.3)
        // Bots often move in straight lines or simple curves (ratio < 0.1)
        if direction_change_ratio < 0.1 && points.len() >= 15 {
            ctx.add(
                &format!(
                    "Too linear movement: {:.0}% direction changes",
                    direction_change_ratio * 100.0
                ),
                0.35,
            );
        }
    }

    // Check for movement starting at origin (0,0) - common bot artifact
    // Real users never start mouse movement at exactly (0,0)
    let origin_points = points
        .iter()
        .filter(|(x, y, _)| *x < 2.0 && *y < 2.0)
        .count();
    if origin_points >= 1 {
        ctx.add(
            &format!("Movement at origin (0,0): {} points", origin_points),
            0.35,
        );
    }

    // Check for teleportation to origin (large jump to near 0,0)
    for i in 1..points.len() {
        let (x1, y1, _) = points[i - 1];
        let (x2, y2, _) = points[i];
        if x1 > 100.0 && y1 > 100.0 && x2 < 10.0 && y2 < 10.0 {
            ctx.add("Teleport to origin detected", 0.4);
            break;
        }
    }

    // Check for bezier-like smooth acceleration (too perfect)
    // Real humans have jerky, irregular acceleration
    if points.len() >= 15 {
        let mut smooth_segments = 0;
        for i in 3..points.len() {
            let (x0, y0, _) = points[i - 3];
            let (x1, y1, _) = points[i - 2];
            let (x2, y2, _) = points[i - 1];
            let (x3, y3, _) = points[i];

            // Calculate second derivatives (acceleration)
            let ddx1 = (x2 - x1) - (x1 - x0);
            let ddy1 = (y2 - y1) - (y1 - y0);
            let ddx2 = (x3 - x2) - (x2 - x1);
            let ddy2 = (y3 - y2) - (y2 - y1);

            // Check if acceleration is very consistent (bezier signature)
            let acc_diff = ((ddx2 - ddx1).powi(2) + (ddy2 - ddy1).powi(2)).sqrt();
            if acc_diff < 2.0 {
                smooth_segments += 1;
            }
        }

        let smooth_ratio = smooth_segments as f64 / (points.len() - 3) as f64;
        if smooth_ratio > 0.8 {
            ctx.add(
                &format!(
                    "Bezier-like smooth curve: {:.0}% consistent acceleration",
                    smooth_ratio * 100.0
                ),
                0.4,
            );
        }
    }

    // Velocity analysis - humans have variable velocity
    if !velocities.is_empty() && velocities.len() >= 10 {
        let avg_vel = velocities.iter().sum::<f64>() / velocities.len() as f64;
        let vel_var = velocities
            .iter()
            .map(|&v| (v - avg_vel).powi(2))
            .sum::<f64>()
            / velocities.len() as f64;
        let vel_std = vel_var.sqrt();
        let vel_cv = if avg_vel > 0.0 {
            vel_std / avg_vel
        } else {
            0.0
        };

        // Low velocity CV means constant speed (robotic)
        if vel_cv < 0.3 {
            ctx.add(&format!("Constant velocity: CV={:.2}", vel_cv), 0.25);
        }
    }
}

fn analyze_request_headers(req: &HttpRequest, ctx: &mut AnalysisContext) {
    let headers = req.headers();

    let important = ["accept", "accept-language", "accept-encoding"];
    let missing: Vec<&str> = important
        .iter()
        .filter(|h| !headers.contains_key(**h))
        .copied()
        .collect();
    if !missing.is_empty() {
        ctx.add(&format!("Missing headers: {}", missing.join(", ")), 0.2);
    }

    if let Some(ua) = headers.get("user-agent").and_then(|h| h.to_str().ok()) {
        let ua_lower = ua.to_lowercase();
        let bot_sigs = [
            "bot",
            "crawler",
            "spider",
            "scraper",
            "headless",
            "phantom",
            "selenium",
            "webdriver",
            "puppeteer",
            "playwright",
            "cypress",
        ];
        for sig in bot_sigs {
            if ua_lower.contains(sig) {
                ctx.add(&format!("Bot signature in UA: {}", sig), 0.3);
                break;
            }
        }
    }
}

fn analyze_performance(d: &CompactData, ctx: &mut AnalysisContext, has_indicators: bool) {
    let (mean, variance, _mem) = &d.e;

    if let (Some(m), Some(v)) = (mean, variance) {
        if *v < 0.001 && *m > 0.0 && has_indicators {
            ctx.add(&format!("Consistent exec times: var={}", v), 0.2);
        }
    }
}

pub fn analyze_compact_data(
    req: &HttpRequest,
    d: &CompactData,
    ip_modifier: f64,
) -> (f64, Vec<String>) {
    let mut ctx = AnalysisContext::new();

    analyze_automation(d, &mut ctx);
    let has_indicators = ctx.score > 0.0;

    analyze_navigator(d, &mut ctx, req);
    analyze_property_integrity(d, &mut ctx);
    analyze_tampering(d, &mut ctx);
    analyze_canvas_webgl(d, &mut ctx);
    analyze_features(d, &mut ctx);
    analyze_mouse(d, &mut ctx, has_indicators);
    analyze_performance(d, &mut ctx, has_indicators);
    analyze_devtools(d, &mut ctx);
    analyze_screen(d, &mut ctx);
    analyze_extra(d, &mut ctx, has_indicators);
    analyze_sophisticated_bot(d, &mut ctx);
    analyze_request_headers(req, &mut ctx);

    ctx.score = (ctx.score + ip_modifier).min(1.0);
    (ctx.score, ctx.reasons)
}

// ============================================================================
// HTTP Handler
// ============================================================================

pub async fn passive_verify(
    req: HttpRequest,
    state: web::Data<PassiveState>,
    captcha_state: web::Data<super::CaptchaState>,
    body: web::Json<PassiveVerifyRequest>,
) -> HttpResponse {
    if !captcha_state.is_valid_site(&body.site_key) {
        return HttpResponse::BadRequest().json(PassiveVerifyResponse {
            success: false,
            verified_token: None,
        });
    }

    let config = state.get_config(&body.site_key).unwrap_or_default();

    if !config.passive_allowed {
        return HttpResponse::Ok().json(PassiveVerifyResponse {
            success: false,
            verified_token: None,
        });
    }

    let client_ip = req
        .connection_info()
        .realip_remote_addr()
        .unwrap_or("unknown")
        .to_string();
    let ip_modifier = state.get_ip_score_modifier(&client_ip);

    let (score, _reasons) = analyze_compact_data(&req, &body.d, ip_modifier);
    state.update_ip_history(&client_ip, score);

    let require_challenge = score >= config.threshold;
    let verified_token = if !require_challenge {
        // Generate token with encrypted score
        Some(captcha_state.crypto.generate_passive_verified_token(&body.site_key, score))
    } else {
        None
    };

    HttpResponse::Ok().json(PassiveVerifyResponse {
        success: !require_challenge,
        verified_token,
    })
}

pub fn configure_passive_routes(cfg: &mut web::ServiceConfig) {
    cfg.route("/captcha/passive", web::post().to(passive_verify));
}
