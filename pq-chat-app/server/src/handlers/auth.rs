use axum::{Extension, Json, http::StatusCode};
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;

use crate::auth::{
    create_access_token, create_refresh_token, get_refresh_token_expiration,
    hash_password, verify_password, verify_token, TokenType,
};
use crate::models::{CreateUserRequest, Device, RefreshToken, User};
use crate::rate_limiter::RateLimiter;

const MIN_PASSWORD_LENGTH: usize = 12;
const MAX_PASSWORD_LENGTH: usize = 128;
const MIN_USERNAME_LENGTH: usize = 3;
const MAX_USERNAME_LENGTH: usize = 32;

fn is_password_strong(password: &str) -> bool {
    let has_uppercase = password.chars().any(|c| c.is_uppercase());
    let has_lowercase = password.chars().any(|c| c.is_lowercase());
    let has_digit = password.chars().any(|c| c.is_numeric());
    let has_special = password.chars().any(|c| !c.is_alphanumeric());
    
    has_uppercase && has_lowercase && has_digit && has_special
}

fn is_username_valid(username: &str) -> bool {
    username.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-')
}

#[derive(Debug, Serialize)]
pub struct AuthResponse {
    pub access_token: String,
    pub refresh_token: String,
    pub user_id: String,
    pub device_id: String,
}

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

pub async fn register(
    Extension(pool): Extension<SqlitePool>,
    Extension(rate_limiter): Extension<RateLimiter>,
    Json(request): Json<CreateUserRequest>,
) -> Result<Json<AuthResponse>, (StatusCode, Json<ErrorResponse>)> {
    let rate_key = format!("register:{}", request.username);
    if !rate_limiter.check_rate_limit(&rate_key).await {
        tracing::warn!(
            username = request.username,
            "Registration rate limit exceeded"
        );
        return Err((
            StatusCode::TOO_MANY_REQUESTS,
            Json(ErrorResponse {
                error: "Too many registration attempts".to_string(),
            }),
        ));
    }

    if request.username.is_empty() || request.password.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Username and password required".to_string(),
            }),
        ));
    }

    if request.username.len() < MIN_USERNAME_LENGTH {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: format!(
                    "Username must be at least {} characters",
                    MIN_USERNAME_LENGTH
                ).to_string(),
            }),
        ));
    }

    if request.username.len() > MAX_USERNAME_LENGTH {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: format!(
                    "Username must not exceed {} characters",
                    MAX_USERNAME_LENGTH
                ).to_string(),
            }),
        ));
    }

    if !is_username_valid(&request.username) {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Username must contain only alphanumeric characters, underscores, and hyphens".to_string(),
            }),
        ));
    }

    if request.password.len() < MIN_PASSWORD_LENGTH {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: format!(
                    "Password must be at least {} characters",
                    MIN_PASSWORD_LENGTH
                ).to_string(),
            }),
        ));
    }

    if request.password.len() > MAX_PASSWORD_LENGTH {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: format!(
                    "Password must not exceed {} characters",
                    MAX_PASSWORD_LENGTH
                ).to_string(),
            }),
        ));
    }

    if !is_password_strong(&request.password) {
        tracing::warn!(
            username = request.username,
            "Registration failed: weak password"
        );
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Password must contain uppercase, lowercase, digit, and special character".to_string(),
            }),
        ));
    }

    let existing_user = User::find_by_username(&pool, &request.username)
        .await
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?;

    if existing_user.is_some() {
        return Err((
            StatusCode::CONFLICT,
            Json(ErrorResponse {
                error: "Username already exists".to_string(),
            }),
        ));
    }

    let password_hash = hash_password(&request.password).map_err(|error| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("Password hashing failed: {}", error),
            }),
        )
    })?;

    let user = User::create(&pool, request.username.clone(), password_hash)
        .await
        .map_err(|error| {
            tracing::error!(
                username = request.username,
                error = %error,
                "User creation failed"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("User creation failed: {}", error),
                }),
            )
        })?;

    tracing::info!(
        user_id = user.id,
        username = request.username,
        "User registered successfully"
    );

    Ok(Json(AuthResponse {
        access_token: String::new(),
        refresh_token: String::new(),
        user_id: user.id,
        device_id: String::new(),
    }))
}

#[derive(Debug, Deserialize)]
pub struct LoginWithDeviceRequest {
    pub username: String,
    pub password: String,
    pub public_key: Vec<u8>,
}

pub async fn login(
    Extension(pool): Extension<SqlitePool>,
    Extension(rate_limiter): Extension<RateLimiter>,
    Json(request): Json<LoginWithDeviceRequest>,
) -> Result<Json<AuthResponse>, (StatusCode, Json<ErrorResponse>)> {
    let rate_key = format!("login:{}", request.username);
    if !rate_limiter.check_rate_limit(&rate_key).await {
        tracing::warn!(
            username = request.username,
            "Login rate limit exceeded"
        );
        return Err((
            StatusCode::TOO_MANY_REQUESTS,
            Json(ErrorResponse {
                error: "Too many login attempts".to_string(),
            }),
        ));
    }

    if request.username.is_empty() || request.password.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Username and password required".to_string(),
            }),
        ));
    }

    if request.public_key.is_empty() {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Device public key required".to_string(),
            }),
        ));
    }

    if request.public_key.len() < 32 || request.public_key.len() > 2048 {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Public key must be between 32 and 2048 bytes".to_string(),
            }),
        ));
    }

    let user = User::find_by_username(&pool, &request.username)
        .await
        .map_err(|error| {
            tracing::error!(
                username = request.username,
                error = %error,
                "Database error during login"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?
        .ok_or_else(|| {
            tracing::warn!(
                username = request.username,
                "Login failed: user not found"
            );
            (
                StatusCode::UNAUTHORIZED,
                Json(ErrorResponse {
                    error: "Invalid credentials".to_string(),
                }),
            )
        })?;

    let password_valid = verify_password(&request.password, &user.password_hash)
        .map_err(|error| {
            tracing::error!(
                username = request.username,
                error = %error,
                "Password verification error"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Password verification failed: {}", error),
                }),
            )
        })?;

    if !password_valid {
        tracing::warn!(
            username = request.username,
            user_id = user.id,
            "Login failed: invalid password"
        );
        return Err((
            StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                error: "Invalid credentials".to_string(),
            }),
        ));
    }

    let device = Device::create(&pool, user.id.clone(), request.public_key)
        .await
        .map_err(|error| {
            tracing::error!(
                username = request.username,
                user_id = user.id,
                error = %error,
                "Device creation failed"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Device creation failed: {}", error),
                }),
            )
        })?;

    let access_token = create_access_token(&user.id, &device.id)
        .map_err(|error| {
            tracing::error!(
                user_id = user.id,
                device_id = device.id,
                error = %error,
                "Access token creation failed"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Token creation failed: {}", error),
                }),
            )
        })?;

    let refresh_token = create_refresh_token(&user.id, &device.id)
        .map_err(|error| {
            tracing::error!(
                user_id = user.id,
                device_id = device.id,
                error = %error,
                "Refresh token creation failed"
            );
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Token creation failed: {}", error),
                }),
            )
        })?;

    let token_hash = hash_token(&refresh_token);
    let expires_at = get_refresh_token_expiration() as i64;

    RefreshToken::create(
        &pool,
        user.id.clone(),
        device.id.clone(),
        token_hash,
        expires_at,
    )
    .await
    .map_err(|error| {
        tracing::error!(
            user_id = user.id,
            device_id = device.id,
            error = %error,
            "Refresh token storage failed"
        );
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("Token storage failed: {}", error),
            }),
        )
    })?;

    tracing::info!(
        username = request.username,
        user_id = user.id,
        device_id = device.id,
        "User logged in successfully"
    );

    Ok(Json(AuthResponse {
        access_token,
        refresh_token,
        user_id: user.id,
        device_id: device.id,
    }))
}

fn hash_token(token: &str) -> String {
    token.to_string()
}

#[derive(Debug, Deserialize)]
pub struct RefreshTokenRequest {
    pub refresh_token: String,
}

pub async fn refresh(
    Extension(pool): Extension<SqlitePool>,
    Json(request): Json<RefreshTokenRequest>,
) -> Result<Json<AuthResponse>, (StatusCode, Json<ErrorResponse>)> {
    let claims = verify_token(&request.refresh_token).map_err(|error| {
        tracing::warn!(error = %error, "Invalid refresh token");
        (
            StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                error: "Invalid refresh token".to_string(),
            }),
        )
    })?;

    if claims.token_type != TokenType::Refresh {
        tracing::warn!("Token is not a refresh token");
        return Err((
            StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                error: "Invalid token type".to_string(),
            }),
        ));
    }

    let token_hash = hash_token(&request.refresh_token);
    let stored_token = RefreshToken::find_by_hash(&pool, &token_hash)
        .await
        .map_err(|error| {
            tracing::error!(error = %error, "Database error");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Database error".to_string(),
                }),
            )
        })?
        .ok_or_else(|| {
            tracing::warn!("Refresh token not found");
            (
                StatusCode::UNAUTHORIZED,
                Json(ErrorResponse {
                    error: "Invalid refresh token".to_string(),
                }),
            )
        })?;

    if !stored_token.is_valid() {
        tracing::warn!(
            user_id = stored_token.user_id,
            "Refresh token expired or revoked"
        );
        return Err((
            StatusCode::UNAUTHORIZED,
            Json(ErrorResponse {
                error: "Refresh token expired or revoked".to_string(),
            }),
        ));
    }

    RefreshToken::revoke(&pool, &token_hash)
        .await
        .map_err(|error| {
            tracing::error!(error = %error, "Failed to revoke old token");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Token revocation failed".to_string(),
                }),
            )
        })?;

    let access_token = create_access_token(&claims.sub, &claims.device_id)
        .map_err(|error| {
            tracing::error!(error = %error, "Access token creation failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Token creation failed".to_string(),
                }),
            )
        })?;

    let new_refresh_token = create_refresh_token(&claims.sub, &claims.device_id)
        .map_err(|error| {
            tracing::error!(error = %error, "Refresh token creation failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Token creation failed".to_string(),
                }),
            )
        })?;

    let new_token_hash = hash_token(&new_refresh_token);
    let expires_at = get_refresh_token_expiration() as i64;

    RefreshToken::create(
        &pool,
        claims.sub.clone(),
        claims.device_id.clone(),
        new_token_hash,
        expires_at,
    )
    .await
    .map_err(|error| {
        tracing::error!(error = %error, "Refresh token storage failed");
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "Token storage failed".to_string(),
            }),
        )
    })?;

    tracing::info!(
        user_id = claims.sub,
        device_id = claims.device_id,
        "Token refreshed successfully"
    );

    Ok(Json(AuthResponse {
        access_token,
        refresh_token: new_refresh_token,
        user_id: claims.sub,
        device_id: claims.device_id,
    }))
}

#[derive(Debug, Deserialize)]
pub struct LogoutRequest {
    pub refresh_token: String,
}

pub async fn logout(
    Extension(pool): Extension<SqlitePool>,
    Json(request): Json<LogoutRequest>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let token_hash = hash_token(&request.refresh_token);

    RefreshToken::revoke(&pool, &token_hash)
        .await
        .map_err(|error| {
            tracing::error!(error = %error, "Token revocation failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Logout failed".to_string(),
                }),
            )
        })?;

    tracing::info!("User logged out successfully");
    Ok(StatusCode::NO_CONTENT)
}
