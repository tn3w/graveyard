use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, FromRow)]
pub struct User {
    pub id: i64,
    pub username: String,
    pub password_hash: String,
    pub totp_secret: String,
    pub created_at: i64,
}

#[derive(Debug, FromRow)]
pub struct RegistrationToken {
    pub token: String,
    pub used: bool,
    pub created_at: i64,
}

#[derive(Debug, FromRow)]
pub struct RefreshToken {
    pub token: String,
    pub user_id: i64,
    pub expires_at: i64,
    pub created_at: i64,
}

#[derive(Debug, FromRow)]
pub struct WebauthnCredential {
    pub id: i64,
    pub user_id: i64,
    pub credential_id: Vec<u8>,
    pub public_key: Vec<u8>,
    pub counter: i64,
    pub created_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct RegisterRequest {
    pub token: String,
    pub username: String,
    pub password: String,
    pub captcha_token: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct RegisterResponse {
    pub totp_secret: String,
    pub totp_uri: String,
    pub webauthn_options: serde_json::Value,
}

#[derive(Debug, Deserialize)]
pub struct VerifyTotpSetupRequest {
    pub username: String,
    pub totp_code: String,
}

#[derive(Debug, Serialize)]
pub struct VerifyTotpSetupResponse {
    pub valid: bool,
}

#[derive(Debug, Deserialize)]
pub struct LoginStep1Request {
    pub username: String,
    pub password: String,
    pub captcha_token: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct LoginStep1Response {
    pub session_token: String,
    pub requires_totp: bool,
    pub requires_webauthn: bool,
}

#[derive(Debug, Deserialize)]
pub struct LoginStep2TotpRequest {
    pub session_token: String,
    pub totp_code: String,
}

#[derive(Debug, Deserialize)]
pub struct LoginStep2WebauthnStartRequest {
    pub session_token: String,
}

#[derive(Debug, Serialize)]
pub struct LoginStep2WebauthnStartResponse {
    pub options: serde_json::Value,
}

#[derive(Debug, Deserialize)]
pub struct LoginStep2WebauthnFinishRequest {
    pub session_token: String,
    pub credential: serde_json::Value,
}

#[derive(Debug, Serialize)]
pub struct TokenResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub token_type: String,
    pub expires_in: i64,
}

#[derive(Debug, Deserialize)]
pub struct RefreshTokenRequest {
    pub refresh_token: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: i64,
    pub iat: i64,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct SessionClaims {
    pub user_id: i64,
    pub username: String,
    pub step1_complete: bool,
    pub exp: i64,
}
