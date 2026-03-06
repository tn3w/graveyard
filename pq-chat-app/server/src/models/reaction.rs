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
pub struct Reaction {
    pub id: String,
    pub message_id: String,
    pub user_id: String,
    pub emoji: String,
    pub created_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct AddReactionRequest {
    pub emoji: String,
}

impl Reaction {
    pub async fn create(
        pool: &sqlx::SqlitePool,
        message_id: String,
        user_id: String,
        emoji: String,
    ) -> Result<Self, sqlx::Error> {
        if let Some(existing) = Self::find_by_user_and_message(
            pool,
            &user_id,
            &message_id,
            &emoji,
        )
        .await?
        {
            return Ok(existing);
        }

        let id = uuid::Uuid::new_v4().to_string();
        let created_at = current_timestamp();

        sqlx::query_as::<_, Reaction>(
            "INSERT INTO reactions (id, message_id, user_id, emoji, created_at)
             VALUES (?, ?, ?, ?, ?)
             RETURNING id, message_id, user_id, emoji, created_at",
        )
        .bind(&id)
        .bind(&message_id)
        .bind(&user_id)
        .bind(&emoji)
        .bind(created_at)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_id(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, Reaction>(
            "SELECT id, message_id, user_id, emoji, created_at
             FROM reactions
             WHERE id = ?",
        )
        .bind(id)
        .fetch_optional(pool)
        .await
    }

    pub async fn find_by_message(
        pool: &sqlx::SqlitePool,
        message_id: &str,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, Reaction>(
            "SELECT id, message_id, user_id, emoji, created_at
             FROM reactions
             WHERE message_id = ?
             ORDER BY created_at ASC",
        )
        .bind(message_id)
        .fetch_all(pool)
        .await
    }

    pub async fn delete(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<(), sqlx::Error> {
        sqlx::query("DELETE FROM reactions WHERE id = ?")
            .bind(id)
            .execute(pool)
            .await?;

        Ok(())
    }

    pub async fn find_by_user_and_message(
        pool: &sqlx::SqlitePool,
        user_id: &str,
        message_id: &str,
        emoji: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, Reaction>(
            "SELECT id, message_id, user_id, emoji, created_at
             FROM reactions
             WHERE user_id = ? AND message_id = ? AND emoji = ?",
        )
        .bind(user_id)
        .bind(message_id)
        .bind(emoji)
        .fetch_optional(pool)
        .await
    }
}
