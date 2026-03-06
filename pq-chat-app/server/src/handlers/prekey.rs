use axum::{Extension, Json, extract::Path, http::StatusCode};
use serde::Serialize;
use sqlx::SqlitePool;

use crate::models::prekey::{
    OneTimePrekey, PrekeyBundle, PrekeyBundleResponse, 
    UploadPrekeyBundleRequest,
};
use crate::models::Device;

const MAX_ONE_TIME_PREKEYS: usize = 100;
const MIN_IDENTITY_KEY_SIZE: usize = 32;
const MAX_IDENTITY_KEY_SIZE: usize = 2048;
const MIN_SIGNED_PREKEY_SIZE: usize = 32;
const MAX_SIGNED_PREKEY_SIZE: usize = 2048;
const MIN_SIGNATURE_SIZE: usize = 64;
const MAX_SIGNATURE_SIZE: usize = 256;

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

#[derive(Debug, Serialize)]
pub struct UploadResponse {
    pub message: String,
    pub one_time_prekeys_uploaded: usize,
}

fn validate_prekey_bundle(
    request: &UploadPrekeyBundleRequest,
) -> Result<(), String> {
    if request.identity_key.len() < MIN_IDENTITY_KEY_SIZE {
        return Err(format!(
            "Identity key too small: {} bytes (minimum {})",
            request.identity_key.len(),
            MIN_IDENTITY_KEY_SIZE
        ));
    }

    if request.identity_key.len() > MAX_IDENTITY_KEY_SIZE {
        return Err(format!(
            "Identity key too large: {} bytes (maximum {})",
            request.identity_key.len(),
            MAX_IDENTITY_KEY_SIZE
        ));
    }

    if request.signed_prekey.len() < MIN_SIGNED_PREKEY_SIZE {
        return Err(format!(
            "Signed prekey too small: {} bytes (minimum {})",
            request.signed_prekey.len(),
            MIN_SIGNED_PREKEY_SIZE
        ));
    }

    if request.signed_prekey.len() > MAX_SIGNED_PREKEY_SIZE {
        return Err(format!(
            "Signed prekey too large: {} bytes (maximum {})",
            request.signed_prekey.len(),
            MAX_SIGNED_PREKEY_SIZE
        ));
    }

    if request.signed_prekey_signature.len() < MIN_SIGNATURE_SIZE {
        return Err(format!(
            "Signature too small: {} bytes (minimum {})",
            request.signed_prekey_signature.len(),
            MIN_SIGNATURE_SIZE
        ));
    }

    if request.signed_prekey_signature.len() > MAX_SIGNATURE_SIZE {
        return Err(format!(
            "Signature too large: {} bytes (maximum {})",
            request.signed_prekey_signature.len(),
            MAX_SIGNATURE_SIZE
        ));
    }

    if request.one_time_prekeys.len() > MAX_ONE_TIME_PREKEYS {
        return Err(format!(
            "Too many one-time prekeys: {} (maximum {})",
            request.one_time_prekeys.len(),
            MAX_ONE_TIME_PREKEYS
        ));
    }

    for (index, prekey) in request.one_time_prekeys.iter().enumerate() {
        if prekey.len() < MIN_SIGNED_PREKEY_SIZE {
            return Err(format!(
                "One-time prekey {} too small: {} bytes (minimum {})",
                index,
                prekey.len(),
                MIN_SIGNED_PREKEY_SIZE
            ));
        }

        if prekey.len() > MAX_SIGNED_PREKEY_SIZE {
            return Err(format!(
                "One-time prekey {} too large: {} bytes (maximum {})",
                index,
                prekey.len(),
                MAX_SIGNED_PREKEY_SIZE
            ));
        }
    }

    Ok(())
}

pub async fn upload_prekey_bundle(
    Extension(pool): Extension<SqlitePool>,
    Path(device_id): Path<String>,
    Json(request): Json<UploadPrekeyBundleRequest>,
) -> Result<Json<UploadResponse>, (StatusCode, Json<ErrorResponse>)> {
    validate_prekey_bundle(&request).map_err(|error| {
        tracing::warn!(device_id = device_id, error = error, 
                      "Invalid prekey bundle");
        (
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse { error }),
        )
    })?;

    let device = Device::find_by_id(&pool, &device_id)
        .await
        .map_err(|error| {
            tracing::error!(device_id = device_id, error = %error, 
                           "Database error");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Database error".to_string(),
                }),
            )
        })?
        .ok_or_else(|| {
            tracing::warn!(device_id = device_id, "Device not found");
            (
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "Device not found".to_string(),
                }),
            )
        })?;

    PrekeyBundle::create(
        &pool,
        device.id.clone(),
        request.identity_key,
        request.signed_prekey,
        request.signed_prekey_signature,
        request.signed_prekey_timestamp,
    )
    .await
    .map_err(|error| {
        tracing::error!(device_id = device_id, error = %error, 
                       "Failed to store prekey bundle");
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: "Failed to store prekey bundle".to_string(),
            }),
        )
    })?;

    let one_time_count = request.one_time_prekeys.len();
    
    if !request.one_time_prekeys.is_empty() {
        OneTimePrekey::create_batch(
            &pool,
            device.id.clone(),
            request.one_time_prekeys,
        )
        .await
        .map_err(|error| {
            tracing::error!(device_id = device_id, error = %error, 
                           "Failed to store one-time prekeys");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Failed to store one-time prekeys".to_string(),
                }),
            )
        })?;
    }

    tracing::info!(
        device_id = device_id,
        one_time_prekeys = one_time_count,
        "Prekey bundle uploaded successfully"
    );

    Ok(Json(UploadResponse {
        message: "Prekey bundle uploaded successfully".to_string(),
        one_time_prekeys_uploaded: one_time_count,
    }))
}

pub async fn fetch_prekey_bundle(
    Extension(pool): Extension<SqlitePool>,
    Path(device_id): Path<String>,
) -> Result<Json<PrekeyBundleResponse>, (StatusCode, Json<ErrorResponse>)> {
    let bundle = PrekeyBundle::find_by_device(&pool, &device_id)
        .await
        .map_err(|error| {
            tracing::error!(device_id = device_id, error = %error, 
                           "Database error");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Database error".to_string(),
                }),
            )
        })?
        .ok_or_else(|| {
            tracing::warn!(device_id = device_id, 
                          "Prekey bundle not found");
            (
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "Prekey bundle not found".to_string(),
                }),
            )
        })?;

    let one_time_prekey = OneTimePrekey::consume_one(&pool, &device_id)
        .await
        .map_err(|error| {
            tracing::error!(device_id = device_id, error = %error, 
                           "Failed to consume one-time prekey");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: "Failed to fetch one-time prekey".to_string(),
                }),
            )
        })?
        .map(|k| k.prekey);

    tracing::info!(
        device_id = device_id,
        has_one_time_prekey = one_time_prekey.is_some(),
        "Prekey bundle fetched"
    );

    Ok(Json(PrekeyBundleResponse {
        identity_key: bundle.identity_key,
        signed_prekey: bundle.signed_prekey,
        signed_prekey_signature: bundle.signed_prekey_signature,
        signed_prekey_timestamp: bundle.signed_prekey_timestamp,
        one_time_prekey,
    }))
}
