use axum::{
    extract::FromRequestParts,
    http::{request::Parts, StatusCode},
    response::{IntoResponse, Response},
    Json,
};
use serde::Serialize;

use crate::auth::{verify_token, TokenType};

#[derive(Debug, Clone)]
pub struct AuthenticatedUser {
    pub user_id: String,
    pub device_id: String,
}

#[derive(Debug, Serialize)]
struct ErrorResponse {
    error: String,
}

impl<S> FromRequestParts<S> for AuthenticatedUser
where
    S: Send + Sync,
{
    type Rejection = Response;

    async fn from_request_parts(
        parts: &mut Parts,
        _state: &S,
    ) -> Result<Self, Self::Rejection> {
        let authorization = parts
            .headers
            .get("authorization")
            .and_then(|value| value.to_str().ok())
            .ok_or_else(|| {
                (
                    StatusCode::UNAUTHORIZED,
                    Json(ErrorResponse {
                        error: "Missing authorization header".to_string(),
                    }),
                )
                    .into_response()
            })?;

        let token = authorization
            .strip_prefix("Bearer ")
            .ok_or_else(|| {
                (
                    StatusCode::UNAUTHORIZED,
                    Json(ErrorResponse {
                        error: "Invalid authorization format".to_string(),
                    }),
                )
                    .into_response()
            })?;

        let claims = verify_token(token).map_err(|error| {
            (
                StatusCode::UNAUTHORIZED,
                Json(ErrorResponse {
                    error: format!("Invalid token: {}", error),
                }),
            )
                .into_response()
        })?;

        if claims.token_type != TokenType::Access {
            return Err((
                StatusCode::UNAUTHORIZED,
                Json(ErrorResponse {
                    error: "Invalid token type".to_string(),
                }),
            )
                .into_response());
        }

        Ok(AuthenticatedUser {
            user_id: claims.sub,
            device_id: claims.device_id,
        })
    }
}

pub fn rate_limit_key_for_user(user_id: &str, endpoint: &str) -> String {
    format!("user:{}:{}", user_id, endpoint)
}

