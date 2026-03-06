pub mod captcha;
pub mod models;
pub mod auth;
pub mod database;
pub mod handlers;
pub mod deployment;

use sqlx::SqlitePool;
use std::sync::Arc;

#[derive(Clone)]
pub struct AppState {
    pub db: SqlitePool,
    pub jwt_secret: String,
    pub webauthn: Arc<webauthn_rs::Webauthn>,
    pub captcha: Arc<captcha::CaptchaCrypto>,
    pub captcha_generator: Arc<captcha::CaptchaGenerator>,
}
