use axum::{Extension, Json, http::StatusCode};
use serde::Serialize;
use sqlx::SqlitePool;

use crate::middleware::AuthenticatedUser;
use crate::models::Device;

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

pub async fn list_devices(
    Extension(pool): Extension<SqlitePool>,
    user: AuthenticatedUser,
) -> Result<Json<Vec<Device>>, (StatusCode, Json<ErrorResponse>)> {
    let devices = Device::find_by_user(&pool, &user.user_id)
        .await
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?;

    Ok(Json(devices))
}

pub async fn delete_device(
    Extension(pool): Extension<SqlitePool>,
    user: AuthenticatedUser,
    axum::extract::Path(device_id): axum::extract::Path<String>,
) -> Result<StatusCode, (StatusCode, Json<ErrorResponse>)> {
    let device = Device::find_by_id(&pool, &device_id)
        .await
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?
        .ok_or_else(|| {
            (
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "Device not found".to_string(),
                }),
            )
        })?;

    if device.user_id != user.user_id {
        return Err((
            StatusCode::FORBIDDEN,
            Json(ErrorResponse {
                error: "Cannot delete device belonging to another user".to_string(),
            }),
        ));
    }

    if device.id == user.device_id {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Cannot delete current device".to_string(),
            }),
        ));
    }

    Device::delete(&pool, &device_id)
        .await
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?;

    Ok(StatusCode::NO_CONTENT)
}
