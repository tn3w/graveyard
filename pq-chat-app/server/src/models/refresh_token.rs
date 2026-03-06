use serde::{Deserialize, Serialize};
use sqlx::{FromRow, SqlitePool};
use std::time::{SystemTime, UNIX_EPOCH};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct RefreshToken {
    pub id: String,
    pub user_id: String,
    pub device_id: String,
    pub token_hash: String,
    pub expires_at: i64,
    pub created_at: i64,
    pub revoked_at: Option<i64>,
}

impl RefreshToken {
    pub async fn create(
        pool: &SqlitePool,
        user_id: String,
        device_id: String,
        token_hash: String,
        expires_at: i64,
    ) -> Result<Self, sqlx::Error> {
        let id = Uuid::new_v4().to_string();
        let created_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        sqlx::query_as::<_, RefreshToken>(
            r#"
            INSERT INTO refresh_tokens (
                id, user_id, device_id, token_hash, 
                expires_at, created_at, revoked_at
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            RETURNING 
                id, user_id, device_id, token_hash, 
                expires_at, created_at, revoked_at
            "#,
        )
        .bind(&id)
        .bind(&user_id)
        .bind(&device_id)
        .bind(&token_hash)
        .bind(expires_at)
        .bind(created_at)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_hash(
        pool: &SqlitePool,
        token_hash: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, RefreshToken>(
            r#"
            SELECT 
                id, user_id, device_id, token_hash, 
                expires_at, created_at, revoked_at
            FROM refresh_tokens
            WHERE token_hash = ? AND revoked_at IS NULL
            "#,
        )
        .bind(token_hash)
        .fetch_optional(pool)
        .await
    }

    pub async fn revoke(
        pool: &SqlitePool,
        token_hash: &str,
    ) -> Result<(), sqlx::Error> {
        let revoked_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        sqlx::query(
            r#"
            UPDATE refresh_tokens
            SET revoked_at = ?
            WHERE token_hash = ?
            "#,
        )
        .bind(revoked_at)
        .bind(token_hash)
        .execute(pool)
        .await?;

        Ok(())
    }

    #[allow(dead_code)]
    pub async fn revoke_all_for_device(
        pool: &SqlitePool,
        device_id: &str,
    ) -> Result<(), sqlx::Error> {
        let revoked_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        sqlx::query(
            r#"
            UPDATE refresh_tokens
            SET revoked_at = ?
            WHERE device_id = ? AND revoked_at IS NULL
            "#,
        )
        .bind(revoked_at)
        .bind(device_id)
        .execute(pool)
        .await?;

        Ok(())
    }

    #[allow(dead_code)]
    pub async fn cleanup_expired(
        pool: &SqlitePool,
    ) -> Result<u64, sqlx::Error> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        let result = sqlx::query(
            r#"
            DELETE FROM refresh_tokens
            WHERE expires_at < ? OR revoked_at IS NOT NULL
            "#,
        )
        .bind(now)
        .execute(pool)
        .await?;

        Ok(result.rows_affected())
    }

    pub fn is_valid(&self) -> bool {
        if self.revoked_at.is_some() {
            return false;
        }

        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs() as i64;

        self.expires_at > now
    }
}
