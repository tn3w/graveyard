mod auth;
mod captcha;
mod handlers;
mod templates;

use actix_files::Files;
use actix_session::{config::PersistentSession, storage::CookieSessionStore, SessionMiddleware};
use actix_web::{
    cookie::{time::Duration, Key, SameSite},
    web, App, HttpServer,
};
use sqlx::sqlite::SqlitePoolOptions;
use std::sync::Arc;

#[tokio::main]
async fn main() -> std::io::Result<()> {
    dotenvy::dotenv().ok();

    let database_url =
        std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:auth.db?mode=rwc".to_string());
    let jwt_secret = std::env::var("JWT_SECRET").unwrap_or_else(|_| {
        use rand::Rng;
        let secret: [u8; 64] = rand::rng().random();
        base64::Engine::encode(&base64::engine::general_purpose::STANDARD, secret)
    });
    let session_key = std::env::var("SESSION_KEY").unwrap_or_else(|_| {
        use rand::Rng;
        let key: [u8; 64] = rand::rng().random();
        base64::Engine::encode(&base64::engine::general_purpose::STANDARD, key)
    });
    let captcha_secret = std::env::var("CAPTCHA_SECRET").unwrap_or_else(|_| {
        use rand::Rng;
        let secret: [u8; 32] = rand::rng().random();
        base64::Engine::encode(&base64::engine::general_purpose::STANDARD, secret)
    });

    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect(&database_url)
        .await
        .expect("Failed to create pool");

    auth::init_db(&pool)
        .await
        .expect("Failed to initialize database");

    let webauthn = auth::create_webauthn();
    let app_state = web::Data::new(auth::AppState {
        db: pool,
        jwt_secret,
        webauthn: Arc::new(webauthn),
    });

    // Initialize captcha service
    let captcha_state = web::Data::new(captcha::CaptchaState::new(&captcha_secret));
    // Register default site (in production, load from config/db)
    // Generate random site key and API key if not provided
    let site_key = std::env::var("CAPTCHA_SITE_KEY").unwrap_or_else(|_| {
        use rand::Rng;
        let mut rng = rand::rng();
        let chars: Vec<char> = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            .chars()
            .collect();
        (0..32)
            .map(|_| chars[rng.random_range(0..chars.len())])
            .collect()
    });
    let site_secret = std::env::var("CAPTCHA_SITE_SECRET").unwrap_or_else(|_| {
        use rand::Rng;
        let mut rng = rand::rng();
        let chars: Vec<char> = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
            .chars()
            .collect();
        (0..64)
            .map(|_| chars[rng.random_range(0..chars.len())])
            .collect()
    });
    println!("CAPTCHA Site Key: {}", site_key);
    println!("CAPTCHA API Key: {}", site_secret);
    captcha_state.register_site(site_key.clone(), site_secret);

    // Initialize passive mode state
    let passive_state = web::Data::new(captcha::PassiveState::new());
    // Configure passive mode for the site
    let passive_threshold: f64 = std::env::var("CAPTCHA_PASSIVE_THRESHOLD")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(0.4);
    let passive_allowed = std::env::var("CAPTCHA_PASSIVE_ALLOWED")
        .map(|s| s == "true" || s == "1")
        .unwrap_or(true);

    passive_state.configure_site(
        site_key,
        captcha::PassiveModeConfig {
            threshold: passive_threshold,
            passive_allowed,
        },
    );

    let key_bytes =
        base64::Engine::decode(&base64::engine::general_purpose::STANDARD, &session_key)
            .unwrap_or_else(|_| vec![0u8; 64]);
    let cookie_key = Key::from(&key_bytes);

    println!("Starting server at http://127.0.0.1:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .app_data(captcha_state.clone())
            .app_data(passive_state.clone())
            .wrap(
                SessionMiddleware::builder(CookieSessionStore::default(), cookie_key.clone())
                    .cookie_secure(false)
                    .cookie_same_site(SameSite::Strict)
                    .cookie_http_only(true)
                    .session_lifecycle(PersistentSession::default().session_ttl(Duration::hours(1)))
                    .build(),
            )
            .service(Files::new("/static", "static").show_files_listing())
            .configure(handlers::configure_routes)
            .configure(captcha::configure_captcha_routes)
            .configure(captcha::configure_passive_routes)
    })
    .bind("127.0.0.1:8080")?
    .run()
    .await
}
