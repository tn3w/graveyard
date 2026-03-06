//! Stateless CAPTCHA HTTP Handlers - single verification at end

use super::crypto::CaptchaCrypto;
use super::generator::{
    CaptchaChallenge, CaptchaGenerator, IMAGE_SIZE, REFERENCE_HEIGHT, REFERENCE_WIDTH,
};
use actix_web::{web, HttpResponse};
use image::{ImageBuffer, RgbaImage};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::Cursor;
use std::sync::RwLock;

const CHALLENGE_TTL: u64 = 300;
const VERIFIED_TOKEN_TTL: u64 = 120;

pub struct CaptchaState {
    pub generator: CaptchaGenerator,
    pub crypto: CaptchaCrypto,
    sites: RwLock<HashMap<String, String>>, // site_key -> secret_key
}

impl CaptchaState {
    pub fn new(secret_key: &str) -> Self {
        let generator = CaptchaGenerator::new();
        generator.setup();
        Self {
            generator,
            crypto: CaptchaCrypto::new(secret_key),
            sites: RwLock::new(HashMap::new()),
        }
    }

    pub fn register_site(&self, site_key: String, secret_key: String) {
        self.sites.write().unwrap().insert(site_key, secret_key);
    }

    pub fn is_valid_site(&self, site_key: &str) -> bool {
        self.sites.read().unwrap().contains_key(site_key)
    }

    pub fn get_secret(&self, site_key: &str) -> Option<String> {
        self.sites.read().unwrap().get(site_key).cloned()
    }

    pub fn verify_captcha(&self, token: &str, site_key: &str) -> Result<bool, &'static str> {
        self.crypto
            .verify_completed(token, site_key, VERIFIED_TOKEN_TTL)
    }
}

#[derive(Deserialize)]
pub struct ChallengeRequest {
    pub site_key: String,
}

#[derive(Serialize)]
pub struct ChallengeResponse {
    pub token: String,
    pub image: String,
    pub scene_counts: Vec<u8>, // Scene count for each round
    pub total_rounds: u8,
    pub prompt: String,
}

#[derive(Deserialize)]
pub struct SubmitRequest {
    pub token: String,
    pub site_key: String,
    pub answers: Vec<u8>, // User's selected scene for each round
}

#[derive(Serialize)]
pub struct SubmitResponse {
    pub success: bool,
    pub verified_token: Option<String>,
    pub error: Option<String>,
}

#[derive(Deserialize)]
pub struct VerifyRequest {
    pub token: String,
    pub secret_key: String,
    pub site_key: String,
}

#[derive(Serialize)]
pub struct VerifyResponse {
    pub success: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub score: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

pub fn configure_captcha_routes(cfg: &mut web::ServiceConfig) {
    cfg.route("/iam-captcha.js", web::get().to(serve_js))
        .route("/iam-captcha.css", web::get().to(serve_css))
        .route("/iam-passive.js", web::get().to(serve_passive_js))
        .route("/captcha/challenge", web::post().to(get_challenge))
        .route("/captcha/submit", web::post().to(submit_answer))
        .route("/captcha/verify", web::post().to(verify_token));
}

async fn serve_js() -> HttpResponse {
    match std::fs::read_to_string("static/iam-captcha.js") {
        Ok(content) => HttpResponse::Ok()
            .content_type("application/javascript")
            .insert_header(("Cache-Control", "public, max-age=3600"))
            .body(content),
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

async fn serve_css() -> HttpResponse {
    match std::fs::read_to_string("static/iam-captcha.css") {
        Ok(content) => HttpResponse::Ok()
            .content_type("text/css")
            .insert_header(("Cache-Control", "public, max-age=3600"))
            .body(content),
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

async fn serve_passive_js() -> HttpResponse {
    match std::fs::read_to_string("static/iam-passive.js") {
        Ok(content) => HttpResponse::Ok()
            .content_type("application/javascript")
            .insert_header(("Cache-Control", "public, max-age=3600"))
            .body(content),
        Err(_) => HttpResponse::NotFound().finish(),
    }
}

async fn get_challenge(
    state: web::Data<CaptchaState>,
    body: web::Json<ChallengeRequest>,
) -> HttpResponse {
    if !state.is_valid_site(&body.site_key) {
        return HttpResponse::BadRequest().json(serde_json::json!({"error": "Invalid site key"}));
    }

    let mut rng = rand::rng();
    let total_rounds: u8 = rand::Rng::random_range(&mut rng, 1..=3);

    // Generate all challenges upfront
    let mut challenges: Vec<CaptchaChallenge> = Vec::with_capacity(total_rounds as usize);
    let mut correct_scenes: Vec<u8> = Vec::with_capacity(total_rounds as usize);

    for _ in 0..total_rounds {
        let challenge = state.generator.create_challenge();
        correct_scenes.push(challenge.correct_scene as u8);
        challenges.push(challenge);
    }

    // Create token with all correct answers encrypted
    let token = state
        .crypto
        .create_token(&correct_scenes, &body.site_key, CHALLENGE_TTL);

    // Build combined image: ref1|scenes1...|ref2|scenes2...|...
    let mut total_width = 0u32;
    let mut round_widths: Vec<u32> = Vec::new();
    for c in &challenges {
        let w = REFERENCE_WIDTH + (c.scene_count as u32 * IMAGE_SIZE);
        round_widths.push(w);
        total_width += w;
    }

    let height = REFERENCE_HEIGHT.max(IMAGE_SIZE);
    let mut combined: RgbaImage = ImageBuffer::new(total_width, height);
    let mut x_offset = 0u32;
    let mut scene_counts: Vec<u8> = Vec::new();

    for challenge in &challenges {
        scene_counts.push(challenge.scene_count as u8);

        // Reference image
        let reference = state.generator.generate_reference(challenge);
        if let Ok(ref_img) = image::load_from_memory(&reference) {
            let ref_rgba = ref_img.to_rgba8();
            for (x, y, pixel) in ref_rgba.enumerate_pixels() {
                if x_offset + x < total_width && y < height {
                    combined.put_pixel(x_offset + x, y, *pixel);
                }
            }
        }
        x_offset += REFERENCE_WIDTH;

        // Scene images
        let scenes = state.generator.generate_all_scenes(challenge);
        for (scene_bytes, _) in &scenes {
            if let Ok(scene_img) = image::load_from_memory(scene_bytes) {
                let scene_rgba = scene_img.to_rgba8();
                for (x, y, pixel) in scene_rgba.enumerate_pixels() {
                    if x_offset + x < total_width && y < height {
                        combined.put_pixel(x_offset + x, y, *pixel);
                    }
                }
            }
            x_offset += IMAGE_SIZE;
        }
    }

    // Encode to PNG
    let mut png_bytes = Vec::new();
    image::write_buffer_with_format(
        &mut Cursor::new(&mut png_bytes),
        combined.as_raw(),
        combined.width(),
        combined.height(),
        image::ColorType::Rgba8,
        image::ImageFormat::Png,
    )
    .unwrap();

    HttpResponse::Ok().json(ChallengeResponse {
        token,
        image: base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &png_bytes),
        scene_counts,
        total_rounds,
        prompt: format!(
            "Find the scene with the target icon above the fullest cup (1 of {})",
            total_rounds
        ),
    })
}

async fn submit_answer(
    state: web::Data<CaptchaState>,
    body: web::Json<SubmitRequest>,
) -> HttpResponse {
    // Verify token and get correct answers
    let correct = match state.crypto.verify_token(&body.token, &body.site_key) {
        Ok(c) => c,
        Err(e) => {
            return HttpResponse::BadRequest().json(SubmitResponse {
                success: false,
                verified_token: None,
                error: Some(e.to_string()),
            })
        }
    };

    // Check all answers match
    if body.answers.len() != correct.len() {
        return HttpResponse::BadRequest().json(SubmitResponse {
            success: false,
            verified_token: None,
            error: Some("Wrong number of answers".into()),
        });
    }

    for (i, (&user_ans, &correct_ans)) in body.answers.iter().zip(correct.iter()).enumerate() {
        if user_ans != correct_ans {
            return HttpResponse::Ok().json(SubmitResponse {
                success: false,
                verified_token: None,
                error: Some(format!("Incorrect answer for round {}", i + 1)),
            });
        }
    }

    // All correct - generate verified token
    let verified_token = state.crypto.generate_verified_token(&body.site_key);
    HttpResponse::Ok().json(SubmitResponse {
        success: true,
        verified_token: Some(verified_token),
        error: None,
    })
}

async fn verify_token(
    state: web::Data<CaptchaState>,
    body: web::Json<VerifyRequest>,
) -> HttpResponse {
    let expected = match state.get_secret(&body.site_key) {
        Some(s) => s,
        None => {
            return HttpResponse::BadRequest().json(VerifyResponse {
                success: false,
                score: None,
                error: Some("Invalid site key".into()),
            })
        }
    };

    if expected != body.secret_key {
        return HttpResponse::Unauthorized().json(VerifyResponse {
            success: false,
            score: None,
            error: Some("Invalid secret key".into()),
        });
    }

    // Try to extract score from passive token first
    match state
        .crypto
        .verify_passive_token(&body.token, &body.site_key, VERIFIED_TOKEN_TTL)
    {
        Ok(score) => HttpResponse::Ok().json(VerifyResponse {
            success: true,
            score: Some(score),
            error: None,
        }),
        Err(_) => {
            // Fall back to regular verification (visual captcha)
            match state
                .crypto
                .verify_completed(&body.token, &body.site_key, VERIFIED_TOKEN_TTL)
            {
                Ok(true) => HttpResponse::Ok().json(VerifyResponse {
                    success: true,
                    score: Some(0.0), // Visual captcha completion = 0 score (human)
                    error: None,
                }),
                Ok(false) => HttpResponse::Ok().json(VerifyResponse {
                    success: false,
                    score: None,
                    error: Some("Failed".into()),
                }),
                Err(e) => HttpResponse::Ok().json(VerifyResponse {
                    success: false,
                    score: None,
                    error: Some(e.to_string()),
                }),
            }
        }
    }
}
