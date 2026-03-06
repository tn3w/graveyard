use axum::{
    extract::{Extension, Path, Query},
    http::StatusCode,
    Json,
};
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;

use crate::cache::AppCache;
use crate::middleware::AuthenticatedUser;
use crate::models::{Device, User};

#[derive(Debug, Serialize)]
pub struct UserProfileResponse {
    id: String,
    username: String,
    created_at: i64,
    devices: Option<Vec<DeviceInfo>>,
}

#[derive(Debug, Serialize)]
pub struct UsersListResponse {
    users: Vec<UserProfileResponse>,
}

impl From<User> for UserProfileResponse {
    fn from(user: User) -> Self {
        Self {
            id: user.id,
            username: user.username,
            created_at: user.created_at,
            devices: None,
        }
    }
}

pub async fn get_profile(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(cache): Extension<AppCache>,
) -> Result<Json<UserProfileResponse>, StatusCode> {
    if let Some(cached_user) = cache.get_user(&auth.user_id).await {
        return Ok(Json((*cached_user).clone().into()));
    }

    let user = User::find_by_id(&pool, &auth.user_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to find user {}: {}", auth.user_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?
        .ok_or(StatusCode::NOT_FOUND)?;

    cache.set_user(user.id.clone(), user.clone()).await;

    Ok(Json(user.into()))
}

#[derive(Debug, Deserialize)]
pub struct SearchUsersQuery {
    #[serde(default = "default_limit")]
    pub limit: i64,
    #[serde(default)]
    pub offset: i64,
    pub search: Option<String>,
}

fn default_limit() -> i64 {
    50
}

pub async fn search_users(
    Query(query): Query<SearchUsersQuery>,
    Extension(pool): Extension<SqlitePool>,
) -> Result<Json<UsersListResponse>, StatusCode> {
    let limit = query.limit.clamp(1, 100);
    let offset = query.offset.max(0);

    let users = if let Some(search_term) = query.search {
        let pattern = format!("%{}%", search_term);
        sqlx::query_as::<_, User>(
            "SELECT id, username, password_hash, created_at
             FROM users
             WHERE username LIKE ?
             ORDER BY username ASC
             LIMIT ? OFFSET ?",
        )
        .bind(&pattern)
        .bind(limit)
        .bind(offset)
        .fetch_all(&pool)
        .await
    } else {
        sqlx::query_as::<_, User>(
            "SELECT id, username, password_hash, created_at
             FROM users
             ORDER BY username ASC
             LIMIT ? OFFSET ?",
        )
        .bind(limit)
        .bind(offset)
        .fetch_all(&pool)
        .await
    }
    .map_err(|error| {
        tracing::error!("Failed to search users: {}", error);
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    let mut response_users = Vec::new();
    
    for user in users {
        let devices = Device::find_by_user(&pool, &user.id)
            .await
            .ok()
            .map(|devs| {
                devs.into_iter()
                    .map(|d| DeviceInfo {
                        id: d.id,
                        public_key: d.public_key,
                        last_seen: d.last_seen,
                    })
                    .collect()
            });
        
        response_users.push(UserProfileResponse {
            id: user.id,
            username: user.username,
            created_at: user.created_at,
            devices,
        });
    }

    Ok(Json(UsersListResponse { users: response_users }))
}

#[derive(Debug, Serialize, Clone)]
pub struct DeviceInfo {
    id: String,
    public_key: Vec<u8>,
    last_seen: i64,
}

pub async fn get_user_devices(
    _auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Path(user_id): Path<String>,
) -> Result<Json<Vec<DeviceInfo>>, StatusCode> {
    let devices = Device::find_by_user(&pool, &user_id)
        .await
        .map_err(|error| {
            tracing::error!(
                "Failed to retrieve devices for user {}: {}",
                user_id,
                error
            );
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let response: Vec<DeviceInfo> = devices
        .into_iter()
        .map(|d| DeviceInfo {
            id: d.id,
            public_key: d.public_key,
            last_seen: d.last_seen,
        })
        .collect();

    Ok(Json(response))
}
