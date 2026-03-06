use actix_web::{web, HttpRequest, HttpResponse, ResponseError};
use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2, Params,
};
use chrono::{Duration, Utc};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use rand::Rng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use sqlx::SqlitePool;
use std::fmt;
use std::sync::Arc;
use url::Url;
use webauthn_rs::prelude::*;

const ACCESS_TOKEN_EXPIRY_MINUTES: i64 = 15;
const REFRESH_TOKEN_EXPIRY_DAYS: i64 = 7;

// ============================================================================
// Error Types
// ============================================================================

#[derive(Debug)]
pub enum AuthError {
    DatabaseError(String),
    InvalidCredentials,
    UserExists,
    UserNotFound,
    InvalidToken,
    TokenExpired,
    InvalidMfa,
    WebAuthnError(String),
    InternalError(String),
}

impl fmt::Display for AuthError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AuthError::DatabaseError(e) => write!(f, "Database error: {}", e),
            AuthError::InvalidCredentials => write!(f, "Invalid credentials"),
            AuthError::UserExists => write!(f, "User already exists"),
            AuthError::UserNotFound => write!(f, "User not found"),
            AuthError::InvalidToken => write!(f, "Invalid token"),
            AuthError::TokenExpired => write!(f, "Token expired"),
            AuthError::InvalidMfa => write!(f, "Invalid MFA code"),
            AuthError::WebAuthnError(e) => write!(f, "WebAuthn error: {}", e),
            AuthError::InternalError(e) => write!(f, "Internal error: {}", e),
        }
    }
}

impl ResponseError for AuthError {
    fn error_response(&self) -> HttpResponse {
        match self {
            AuthError::InvalidCredentials | AuthError::InvalidToken | AuthError::InvalidMfa => {
                HttpResponse::Unauthorized().json(serde_json::json!({"error": self.to_string()}))
            }
            AuthError::UserExists => {
                HttpResponse::Conflict().json(serde_json::json!({"error": self.to_string()}))
            }
            AuthError::UserNotFound => {
                HttpResponse::NotFound().json(serde_json::json!({"error": self.to_string()}))
            }
            AuthError::TokenExpired => HttpResponse::Unauthorized()
                .json(serde_json::json!({"error": self.to_string(), "token_expired": true})),
            _ => HttpResponse::InternalServerError()
                .json(serde_json::json!({"error": "Internal server error"})),
        }
    }
}

impl From<sqlx::Error> for AuthError {
    fn from(e: sqlx::Error) -> Self {
        AuthError::DatabaseError(e.to_string())
    }
}

impl From<argon2::password_hash::Error> for AuthError {
    fn from(_: argon2::password_hash::Error) -> Self {
        AuthError::InvalidCredentials
    }
}

impl From<jsonwebtoken::errors::Error> for AuthError {
    fn from(_: jsonwebtoken::errors::Error) -> Self {
        AuthError::InvalidToken
    }
}

// ============================================================================
// Models & State
// ============================================================================

pub struct AppState {
    pub db: SqlitePool,
    pub jwt_secret: String,
    pub webauthn: Arc<Webauthn>,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct User {
    pub id: String,
    pub username: String,
    pub password_hash: String,
    pub totp_secret: Option<String>,
    pub totp_enabled: bool,
    pub webauthn_enabled: bool,
    pub mfa_dismissed: bool,
    pub created_at: String,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct RefreshToken {
    pub id: String,
    pub user_id: String,
    pub token_hash: String,
    pub expires_at: String,
    pub created_at: String,
    pub revoked: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, sqlx::FromRow)]
pub struct WebAuthnCredential {
    pub id: String,
    pub user_id: String,
    pub credential_id: String,
    pub credential_data: String,
    pub created_at: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub username: String,
    pub mfa_verified: bool,
    pub exp: usize,
    pub iat: usize,
    pub jti: String,
}

// Request/Response types
#[derive(Debug, Deserialize)]
pub struct RegisterRequest {
    pub username: String,
    pub password: String,
    pub captcha_token: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct RegisterResponse {
    pub message: String,
    pub access_token: String,
    pub refresh_token: String,
}

#[derive(Debug, Deserialize)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
    pub captcha_token: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct LoginResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub mfa_required: bool,
    pub mfa_setup_prompt: bool,
}

#[derive(Debug, Deserialize)]
pub struct TotpSetupRequest {
    pub code: String,
}

#[derive(Debug, Serialize)]
pub struct TotpSetupResponse {
    pub secret: String,
    pub qr_code: String,
    pub otpauth_url: String,
}

#[derive(Debug, Deserialize)]
pub struct TotpVerifyRequest {
    pub code: String,
}

#[derive(Debug, Deserialize)]
pub struct RefreshRequest {
    pub refresh_token: String,
}

#[derive(Debug, Serialize)]
pub struct TokenResponse {
    pub access_token: String,
    pub refresh_token: String,
}

#[derive(Debug, Serialize)]
pub struct UserResponse {
    pub id: String,
    pub username: String,
    pub totp_enabled: bool,
    pub webauthn_enabled: bool,
    pub mfa_dismissed: bool,
    pub created_at: String,
}

// ============================================================================
// WebAuthn Configuration
// ============================================================================

pub fn create_webauthn() -> Webauthn {
    let rp_id = "localhost";
    let rp_origin = Url::parse("http://localhost:8080").expect("Invalid URL");
    let builder = WebauthnBuilder::new(rp_id, &rp_origin)
        .expect("Failed to create WebauthnBuilder")
        .rp_name("Secure Auth System");
    builder.build().expect("Failed to build Webauthn")
}

// ============================================================================
// Password & Token Functions
// ============================================================================

pub fn hash_password(password: &str) -> Result<String, AuthError> {
    let salt = SaltString::generate(&mut OsRng);
    let params =
        Params::new(65536, 4, 4, None).map_err(|e| AuthError::InternalError(e.to_string()))?;
    let argon2 = Argon2::new(argon2::Algorithm::Argon2id, argon2::Version::V0x13, params);
    let hash = argon2
        .hash_password(password.as_bytes(), &salt)
        .map_err(|e| AuthError::InternalError(e.to_string()))?;
    Ok(hash.to_string())
}

pub fn verify_password(password: &str, hash: &str) -> Result<bool, AuthError> {
    let parsed_hash = PasswordHash::new(hash).map_err(|_| AuthError::InvalidCredentials)?;
    let argon2 = Argon2::default();
    Ok(argon2
        .verify_password(password.as_bytes(), &parsed_hash)
        .is_ok())
}

pub fn generate_access_token(
    user_id: &str,
    username: &str,
    mfa_verified: bool,
    secret: &str,
) -> Result<String, AuthError> {
    let now = Utc::now();
    let exp = now + Duration::minutes(ACCESS_TOKEN_EXPIRY_MINUTES);
    let claims = Claims {
        sub: user_id.to_string(),
        username: username.to_string(),
        mfa_verified,
        exp: exp.timestamp() as usize,
        iat: now.timestamp() as usize,
        jti: uuid::Uuid::new_v4().to_string(),
    };
    let token = encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes()),
    )?;
    Ok(token)
}

pub fn verify_access_token(token: &str, secret: &str) -> Result<Claims, AuthError> {
    let mut validation = Validation::default();
    validation.validate_exp = true;
    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation,
    )?;
    Ok(token_data.claims)
}

fn generate_refresh_token() -> String {
    let mut rng = rand::rng();
    let token: [u8; 32] = rng.random();
    base64::Engine::encode(&base64::engine::general_purpose::URL_SAFE_NO_PAD, token)
}

fn hash_refresh_token(token: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(token.as_bytes());
    let result = hasher.finalize();
    base64::Engine::encode(&base64::engine::general_purpose::STANDARD, result)
}

pub async fn create_refresh_token(
    pool: &SqlitePool,
    user_id: &str,
) -> Result<(String, RefreshToken), AuthError> {
    let raw_token = generate_refresh_token();
    let token_hash = hash_refresh_token(&raw_token);
    let now = Utc::now();
    let expires_at = now + Duration::days(REFRESH_TOKEN_EXPIRY_DAYS);

    let refresh_token = RefreshToken {
        id: uuid::Uuid::new_v4().to_string(),
        user_id: user_id.to_string(),
        token_hash,
        expires_at: expires_at.to_rfc3339(),
        created_at: now.to_rfc3339(),
        revoked: false,
    };

    save_refresh_token(pool, &refresh_token).await?;
    Ok((raw_token, refresh_token))
}

pub async fn validate_refresh_token(
    pool: &SqlitePool,
    raw_token: &str,
) -> Result<RefreshToken, AuthError> {
    let token_hash = hash_refresh_token(raw_token);
    let token = get_refresh_token(pool, &token_hash)
        .await?
        .ok_or(AuthError::InvalidToken)?;

    let expires_at = chrono::DateTime::parse_from_rfc3339(&token.expires_at)
        .map_err(|_| AuthError::InternalError("Invalid date format".to_string()))?;

    if expires_at < Utc::now() {
        return Err(AuthError::TokenExpired);
    }

    Ok(token)
}

// ============================================================================
// Middleware
// ============================================================================

pub fn validate_token(req: &HttpRequest, state: &web::Data<AppState>) -> Result<Claims, AuthError> {
    let token = req
        .headers()
        .get("Authorization")
        .and_then(|h| h.to_str().ok())
        .and_then(|h| h.strip_prefix("Bearer "))
        .ok_or(AuthError::InvalidToken)?;
    verify_access_token(token, &state.jwt_secret)
}

// ============================================================================
// Database Operations
// ============================================================================

pub async fn init_db(pool: &SqlitePool) -> Result<(), AuthError> {
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled INTEGER DEFAULT 0,
            webauthn_enabled INTEGER DEFAULT 0,
            mfa_dismissed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        "#,
    )
    .execute(pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        "#,
    )
    .execute(pool)
    .await?;

    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            credential_id TEXT NOT NULL,
            credential_data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        "#,
    )
    .execute(pool)
    .await?;

    sqlx::query("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        .execute(pool)
        .await?;
    sqlx::query("CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id)")
        .execute(pool)
        .await?;
    sqlx::query("CREATE INDEX IF NOT EXISTS idx_webauthn_user_id ON webauthn_credentials(user_id)")
        .execute(pool)
        .await?;

    Ok(())
}

pub async fn create_user(pool: &SqlitePool, user: &User) -> Result<(), AuthError> {
    sqlx::query(
        r#"
        INSERT INTO users (id, username, password_hash, totp_secret, totp_enabled, webauthn_enabled, mfa_dismissed, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
    .bind(&user.id)
    .bind(&user.username)
    .bind(&user.password_hash)
    .bind(&user.totp_secret)
    .bind(user.totp_enabled)
    .bind(user.webauthn_enabled)
    .bind(user.mfa_dismissed)
    .bind(&user.created_at)
    .bind(&user.updated_at)
    .execute(pool)
    .await
    .map_err(|e| {
        if e.to_string().contains("UNIQUE constraint failed") {
            AuthError::UserExists
        } else {
            AuthError::DatabaseError(e.to_string())
        }
    })?;
    Ok(())
}

pub async fn get_user_by_username(
    pool: &SqlitePool,
    username: &str,
) -> Result<Option<User>, AuthError> {
    let user = sqlx::query_as::<_, User>(
        "SELECT id, username, password_hash, totp_secret, totp_enabled, webauthn_enabled, mfa_dismissed, created_at, updated_at FROM users WHERE username = ?"
    )
    .bind(username)
    .fetch_optional(pool)
    .await?;
    Ok(user)
}

pub async fn get_user_by_id(pool: &SqlitePool, id: &str) -> Result<Option<User>, AuthError> {
    let user = sqlx::query_as::<_, User>(
        "SELECT id, username, password_hash, totp_secret, totp_enabled, webauthn_enabled, mfa_dismissed, created_at, updated_at FROM users WHERE id = ?"
    )
    .bind(id)
    .fetch_optional(pool)
    .await?;
    Ok(user)
}

pub async fn update_user_totp(
    pool: &SqlitePool,
    user_id: &str,
    secret: &str,
    enabled: bool,
) -> Result<(), AuthError> {
    let now = chrono::Utc::now().to_rfc3339();
    sqlx::query("UPDATE users SET totp_secret = ?, totp_enabled = ?, updated_at = ? WHERE id = ?")
        .bind(secret)
        .bind(enabled)
        .bind(&now)
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn update_user_webauthn(
    pool: &SqlitePool,
    user_id: &str,
    enabled: bool,
) -> Result<(), AuthError> {
    let now = chrono::Utc::now().to_rfc3339();
    sqlx::query("UPDATE users SET webauthn_enabled = ?, updated_at = ? WHERE id = ?")
        .bind(enabled)
        .bind(&now)
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn dismiss_mfa_prompt(pool: &SqlitePool, user_id: &str) -> Result<(), AuthError> {
    let now = chrono::Utc::now().to_rfc3339();
    sqlx::query("UPDATE users SET mfa_dismissed = 1, updated_at = ? WHERE id = ?")
        .bind(&now)
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(())
}

async fn save_refresh_token(pool: &SqlitePool, token: &RefreshToken) -> Result<(), AuthError> {
    sqlx::query(
        "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, created_at, revoked) VALUES (?, ?, ?, ?, ?, ?)",
    )
    .bind(&token.id)
    .bind(&token.user_id)
    .bind(&token.token_hash)
    .bind(&token.expires_at)
    .bind(&token.created_at)
    .bind(token.revoked)
    .execute(pool)
    .await?;
    Ok(())
}

async fn get_refresh_token(
    pool: &SqlitePool,
    token_hash: &str,
) -> Result<Option<RefreshToken>, AuthError> {
    let token = sqlx::query_as::<_, RefreshToken>(
        "SELECT id, user_id, token_hash, expires_at, created_at, revoked FROM refresh_tokens WHERE token_hash = ? AND revoked = 0",
    )
    .bind(token_hash)
    .fetch_optional(pool)
    .await?;
    Ok(token)
}

pub async fn revoke_refresh_token(pool: &SqlitePool, token_id: &str) -> Result<(), AuthError> {
    sqlx::query("UPDATE refresh_tokens SET revoked = 1 WHERE id = ?")
        .bind(token_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn revoke_all_user_tokens(pool: &SqlitePool, user_id: &str) -> Result<(), AuthError> {
    sqlx::query("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?")
        .bind(user_id)
        .execute(pool)
        .await?;
    Ok(())
}

pub async fn save_webauthn_credential(
    pool: &SqlitePool,
    cred: &WebAuthnCredential,
) -> Result<(), AuthError> {
    sqlx::query(
        "INSERT INTO webauthn_credentials (id, user_id, credential_id, credential_data, created_at) VALUES (?, ?, ?, ?, ?)",
    )
    .bind(&cred.id)
    .bind(&cred.user_id)
    .bind(&cred.credential_id)
    .bind(&cred.credential_data)
    .bind(&cred.created_at)
    .execute(pool)
    .await?;
    Ok(())
}

pub async fn get_webauthn_credentials(
    pool: &SqlitePool,
    user_id: &str,
) -> Result<Vec<WebAuthnCredential>, AuthError> {
    let creds = sqlx::query_as::<_, WebAuthnCredential>(
        "SELECT id, user_id, credential_id, credential_data, created_at FROM webauthn_credentials WHERE user_id = ?",
    )
    .bind(user_id)
    .fetch_all(pool)
    .await?;
    Ok(creds)
}

// ============================================================================
// Route Handlers
// ============================================================================

use actix_session::Session;
use totp_rs::{Algorithm, Secret, TOTP};

pub fn configure_auth_routes(cfg: &mut web::ServiceConfig) {
    cfg.route("/api/register", web::post().to(register))
        .route("/api/login", web::post().to(login))
        .route("/api/refresh", web::post().to(refresh_token))
        .route("/api/logout", web::post().to(logout))
        .route("/api/mfa/dismiss", web::post().to(dismiss_mfa))
        .route("/api/mfa/totp/setup", web::get().to(totp_setup))
        .route("/api/mfa/totp/enable", web::post().to(totp_enable))
        .route("/api/mfa/totp/verify", web::post().to(totp_verify))
        .route(
            "/api/mfa/webauthn/register/start",
            web::post().to(webauthn_register_start),
        )
        .route(
            "/api/mfa/webauthn/register/finish",
            web::post().to(webauthn_register_finish),
        )
        .route(
            "/api/mfa/webauthn/auth/start",
            web::post().to(webauthn_auth_start),
        )
        .route(
            "/api/mfa/webauthn/auth/finish",
            web::post().to(webauthn_auth_finish),
        )
        .route("/api/user", web::get().to(get_user));
}

async fn register(
    state: web::Data<AppState>,
    captcha_state: web::Data<crate::captcha::CaptchaState>,
    body: web::Json<RegisterRequest>,
) -> Result<HttpResponse, AuthError> {
    // Verify captcha
    let captcha_token = body
        .captcha_token
        .as_ref()
        .ok_or_else(|| AuthError::InternalError("Captcha required".to_string()))?;

    let site_key =
        std::env::var("CAPTCHA_SITE_KEY").unwrap_or_else(|_| "default_site_key".to_string());
    captcha_state
        .verify_captcha(captcha_token, &site_key)
        .map_err(|e| AuthError::InternalError(format!("Captcha verification failed: {}", e)))?;

    let username = body.username.trim();
    if username.len() < 3 || username.len() > 32 {
        return Err(AuthError::InternalError(
            "Username must be 3-32 characters".to_string(),
        ));
    }
    if !username.chars().all(|c| c.is_alphanumeric() || c == '_') {
        return Err(AuthError::InternalError(
            "Username can only contain alphanumeric characters and underscores".to_string(),
        ));
    }

    let password = body.password.trim();
    if password.len() < 12 {
        return Err(AuthError::InternalError(
            "Password must be at least 12 characters".to_string(),
        ));
    }
    if password.len() > 128 {
        return Err(AuthError::InternalError(
            "Password must be at most 128 characters".to_string(),
        ));
    }
    // Check for at least one special character
    let has_special = password.chars().any(|c| !c.is_alphanumeric());
    if !has_special {
        return Err(AuthError::InternalError(
            "Password must contain at least one special character".to_string(),
        ));
    }

    let password_hash = hash_password(password)?;
    let now = chrono::Utc::now().to_rfc3339();

    let user = User {
        id: uuid::Uuid::new_v4().to_string(),
        username: username.to_string(),
        password_hash,
        totp_secret: None,
        totp_enabled: false,
        webauthn_enabled: false,
        mfa_dismissed: false,
        created_at: now.clone(),
        updated_at: now,
    };

    create_user(&state.db, &user).await?;

    // Auto-login after registration
    let access_token = generate_access_token(&user.id, &user.username, false, &state.jwt_secret)?;
    let (refresh_tok, _) = create_refresh_token(&state.db, &user.id).await?;

    Ok(HttpResponse::Created().json(RegisterResponse {
        message: "Account created successfully".to_string(),
        access_token,
        refresh_token: refresh_tok,
    }))
}

async fn login(
    state: web::Data<AppState>,
    captcha_state: web::Data<crate::captcha::CaptchaState>,
    body: web::Json<LoginRequest>,
) -> Result<HttpResponse, AuthError> {
    // Verify captcha
    let captcha_token = body
        .captcha_token
        .as_ref()
        .ok_or_else(|| AuthError::InternalError("Captcha required".to_string()))?;

    let site_key =
        std::env::var("CAPTCHA_SITE_KEY").unwrap_or_else(|_| "default_site_key".to_string());
    captcha_state
        .verify_captcha(captcha_token, &site_key)
        .map_err(|e| AuthError::InternalError(format!("Captcha verification failed: {}", e)))?;

    let user = get_user_by_username(&state.db, &body.username)
        .await?
        .ok_or(AuthError::InvalidCredentials)?;

    if !verify_password(&body.password, &user.password_hash)? {
        return Err(AuthError::InvalidCredentials);
    }

    let has_mfa = user.totp_enabled || user.webauthn_enabled;
    let mfa_verified = !has_mfa;
    let mfa_setup_prompt = !has_mfa && !user.mfa_dismissed;

    let access_token =
        generate_access_token(&user.id, &user.username, mfa_verified, &state.jwt_secret)?;
    let (refresh_tok, _) = create_refresh_token(&state.db, &user.id).await?;

    Ok(HttpResponse::Ok().json(LoginResponse {
        access_token,
        refresh_token: refresh_tok,
        mfa_required: has_mfa,
        mfa_setup_prompt,
    }))
}

async fn refresh_token(
    state: web::Data<AppState>,
    body: web::Json<RefreshRequest>,
) -> Result<HttpResponse, AuthError> {
    let token = validate_refresh_token(&state.db, &body.refresh_token).await?;

    revoke_refresh_token(&state.db, &token.id).await?;

    let user = get_user_by_id(&state.db, &token.user_id)
        .await?
        .ok_or(AuthError::UserNotFound)?;

    let has_mfa = user.totp_enabled || user.webauthn_enabled;
    let access_token = generate_access_token(&user.id, &user.username, has_mfa, &state.jwt_secret)?;
    let (new_refresh_token, _) = create_refresh_token(&state.db, &user.id).await?;

    Ok(HttpResponse::Ok().json(TokenResponse {
        access_token,
        refresh_token: new_refresh_token,
    }))
}

async fn logout(req: HttpRequest, state: web::Data<AppState>) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;
    revoke_all_user_tokens(&state.db, &claims.sub).await?;
    Ok(HttpResponse::Ok().json(serde_json::json!({"message": "Logged out successfully"})))
}

async fn dismiss_mfa(
    req: HttpRequest,
    state: web::Data<AppState>,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;
    dismiss_mfa_prompt(&state.db, &claims.sub).await?;
    Ok(HttpResponse::Ok().json(serde_json::json!({"message": "MFA prompt dismissed"})))
}

async fn totp_setup(
    req: HttpRequest,
    state: web::Data<AppState>,
    session: Session,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let secret = Secret::generate_secret();
    let secret_encoded = secret.to_encoded().to_string();

    let totp = TOTP::new(
        Algorithm::SHA1,
        6,
        1,
        30,
        secret.to_bytes().unwrap(),
        Some("SecureAuth".to_string()),
        claims.username.clone(),
    )
    .map_err(|e| AuthError::InternalError(e.to_string()))?;

    let qr_code = totp
        .get_qr_base64()
        .map_err(|e| AuthError::InternalError(e.to_string()))?;

    session
        .insert("totp_setup_secret", &secret_encoded)
        .map_err(|_| AuthError::InternalError("Session error".to_string()))?;

    Ok(HttpResponse::Ok().json(TotpSetupResponse {
        secret: secret_encoded,
        qr_code,
        otpauth_url: totp.get_url(),
    }))
}

async fn totp_enable(
    req: HttpRequest,
    state: web::Data<AppState>,
    body: web::Json<TotpSetupRequest>,
    session: Session,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let secret_str: String = session
        .get("totp_setup_secret")
        .map_err(|_| AuthError::InternalError("Session error".to_string()))?
        .ok_or(AuthError::InternalError(
            "No TOTP setup in progress".to_string(),
        ))?;

    let secret = Secret::Encoded(secret_str.clone());
    let totp = TOTP::new(
        Algorithm::SHA1,
        6,
        1,
        30,
        secret
            .to_bytes()
            .map_err(|e| AuthError::InternalError(e.to_string()))?,
        Some("SecureAuth".to_string()),
        claims.username.clone(),
    )
    .map_err(|e| AuthError::InternalError(e.to_string()))?;

    if !totp
        .check_current(&body.code)
        .map_err(|e| AuthError::InternalError(e.to_string()))?
    {
        return Err(AuthError::InvalidMfa);
    }

    update_user_totp(&state.db, &claims.sub, &secret_str, true).await?;
    session.remove("totp_setup_secret");

    let access_token =
        generate_access_token(&claims.sub, &claims.username, true, &state.jwt_secret)?;

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "TOTP enabled successfully",
        "access_token": access_token
    })))
}

async fn totp_verify(
    req: HttpRequest,
    state: web::Data<AppState>,
    body: web::Json<TotpVerifyRequest>,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let user = get_user_by_id(&state.db, &claims.sub)
        .await?
        .ok_or(AuthError::UserNotFound)?;

    let secret_str = user.totp_secret.ok_or(AuthError::InvalidMfa)?;
    let secret = Secret::Encoded(secret_str);

    let totp = TOTP::new(
        Algorithm::SHA1,
        6,
        1,
        30,
        secret
            .to_bytes()
            .map_err(|e| AuthError::InternalError(e.to_string()))?,
        Some("SecureAuth".to_string()),
        user.username.clone(),
    )
    .map_err(|e| AuthError::InternalError(e.to_string()))?;

    if !totp
        .check_current(&body.code)
        .map_err(|e| AuthError::InternalError(e.to_string()))?
    {
        return Err(AuthError::InvalidMfa);
    }

    let access_token =
        generate_access_token(&claims.sub, &claims.username, true, &state.jwt_secret)?;
    let (refresh_tok, _) = create_refresh_token(&state.db, &claims.sub).await?;

    Ok(HttpResponse::Ok().json(TokenResponse {
        access_token,
        refresh_token: refresh_tok,
    }))
}

async fn webauthn_register_start(
    req: HttpRequest,
    state: web::Data<AppState>,
    session: Session,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let user_id = Uuid::parse_str(&claims.sub)
        .map_err(|_| AuthError::InternalError("Invalid user ID".to_string()))?;
    let existing_creds = get_webauthn_credentials(&state.db, &claims.sub).await?;

    let exclude_credentials: Vec<CredentialID> = existing_creds
        .iter()
        .filter_map(|c| {
            base64::Engine::decode(&base64::engine::general_purpose::STANDARD, &c.credential_id)
                .ok()
                .map(CredentialID::from)
        })
        .collect();

    let (ccr, reg_state) = state
        .webauthn
        .start_passkey_registration(
            user_id,
            &claims.username,
            &claims.username,
            Some(exclude_credentials),
        )
        .map_err(|e| AuthError::WebAuthnError(e.to_string()))?;

    let state_json =
        serde_json::to_string(&reg_state).map_err(|e| AuthError::InternalError(e.to_string()))?;
    session
        .insert("webauthn_reg_state", state_json)
        .map_err(|_| AuthError::InternalError("Session error".to_string()))?;

    Ok(HttpResponse::Ok().json(ccr))
}

async fn webauthn_register_finish(
    req: HttpRequest,
    state: web::Data<AppState>,
    session: Session,
    body: web::Json<RegisterPublicKeyCredential>,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let state_json: String = session
        .get("webauthn_reg_state")
        .map_err(|_| AuthError::InternalError("Session error".to_string()))?
        .ok_or(AuthError::WebAuthnError(
            "No registration in progress".to_string(),
        ))?;

    let reg_state: PasskeyRegistration =
        serde_json::from_str(&state_json).map_err(|e| AuthError::InternalError(e.to_string()))?;

    let passkey = state
        .webauthn
        .finish_passkey_registration(&body, &reg_state)
        .map_err(|e| AuthError::WebAuthnError(e.to_string()))?;

    let cred_id = base64::Engine::encode(
        &base64::engine::general_purpose::STANDARD,
        passkey.cred_id().as_ref(),
    );
    let cred_data =
        serde_json::to_string(&passkey).map_err(|e| AuthError::InternalError(e.to_string()))?;

    let credential = WebAuthnCredential {
        id: uuid::Uuid::new_v4().to_string(),
        user_id: claims.sub.clone(),
        credential_id: cred_id,
        credential_data: cred_data,
        created_at: chrono::Utc::now().to_rfc3339(),
    };

    save_webauthn_credential(&state.db, &credential).await?;
    update_user_webauthn(&state.db, &claims.sub, true).await?;
    session.remove("webauthn_reg_state");

    let access_token =
        generate_access_token(&claims.sub, &claims.username, true, &state.jwt_secret)?;

    Ok(HttpResponse::Ok().json(serde_json::json!({
        "message": "Security key registered successfully",
        "access_token": access_token
    })))
}

async fn webauthn_auth_start(
    req: HttpRequest,
    state: web::Data<AppState>,
    session: Session,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let creds = get_webauthn_credentials(&state.db, &claims.sub).await?;
    if creds.is_empty() {
        return Err(AuthError::WebAuthnError(
            "No security keys registered".to_string(),
        ));
    }

    let passkeys: Vec<Passkey> = creds
        .iter()
        .filter_map(|c| serde_json::from_str(&c.credential_data).ok())
        .collect();

    let (rcr, auth_state) = state
        .webauthn
        .start_passkey_authentication(&passkeys)
        .map_err(|e| AuthError::WebAuthnError(e.to_string()))?;

    let state_json =
        serde_json::to_string(&auth_state).map_err(|e| AuthError::InternalError(e.to_string()))?;
    session
        .insert("webauthn_auth_state", state_json)
        .map_err(|_| AuthError::InternalError("Session error".to_string()))?;

    Ok(HttpResponse::Ok().json(rcr))
}

async fn webauthn_auth_finish(
    req: HttpRequest,
    state: web::Data<AppState>,
    session: Session,
    body: web::Json<PublicKeyCredential>,
) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let state_json: String = session
        .get("webauthn_auth_state")
        .map_err(|_| AuthError::InternalError("Session error".to_string()))?
        .ok_or(AuthError::WebAuthnError(
            "No authentication in progress".to_string(),
        ))?;

    let auth_state: PasskeyAuthentication =
        serde_json::from_str(&state_json).map_err(|e| AuthError::InternalError(e.to_string()))?;

    state
        .webauthn
        .finish_passkey_authentication(&body, &auth_state)
        .map_err(|e| AuthError::WebAuthnError(e.to_string()))?;

    session.remove("webauthn_auth_state");

    let access_token =
        generate_access_token(&claims.sub, &claims.username, true, &state.jwt_secret)?;
    let (refresh_tok, _) = create_refresh_token(&state.db, &claims.sub).await?;

    Ok(HttpResponse::Ok().json(TokenResponse {
        access_token,
        refresh_token: refresh_tok,
    }))
}

async fn get_user(req: HttpRequest, state: web::Data<AppState>) -> Result<HttpResponse, AuthError> {
    let claims = validate_token(&req, &state)?;

    let user = get_user_by_id(&state.db, &claims.sub)
        .await?
        .ok_or(AuthError::UserNotFound)?;

    Ok(HttpResponse::Ok().json(UserResponse {
        id: user.id,
        username: user.username,
        totp_enabled: user.totp_enabled,
        webauthn_enabled: user.webauthn_enabled,
        mfa_dismissed: user.mfa_dismissed,
        created_at: user.created_at,
    }))
}
