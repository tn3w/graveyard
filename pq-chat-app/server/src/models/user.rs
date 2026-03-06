use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use std::time::{SystemTime, UNIX_EPOCH};

fn current_timestamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct User {
    pub id: String,
    pub username: String,
    #[serde(skip_serializing)]
    pub password_hash: String,
    pub created_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct CreateUserRequest {
    pub username: String,
    pub password: String,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct LoginRequest {
    pub username: String,
    pub password: String,
}

impl User {
    pub async fn create(
        pool: &sqlx::SqlitePool,
        username: String,
        password_hash: String,
    ) -> Result<Self, sqlx::Error> {
        let id = uuid::Uuid::new_v4().to_string();
        let created_at = current_timestamp();

        sqlx::query_as::<_, User>(
            "INSERT INTO users (id, username, password_hash, created_at)
             VALUES (?, ?, ?, ?)
             RETURNING id, username, password_hash, created_at",
        )
        .bind(&id)
        .bind(&username)
        .bind(&password_hash)
        .bind(created_at)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_username(
        pool: &sqlx::SqlitePool,
        username: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, User>(
            "SELECT id, username, password_hash, created_at
             FROM users
             WHERE username = ?",
        )
        .bind(username)
        .fetch_optional(pool)
        .await
    }

    pub async fn find_by_id(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, User>(
            "SELECT id, username, password_hash, created_at
             FROM users
             WHERE id = ?",
        )
        .bind(id)
        .fetch_optional(pool)
        .await
    }
}
