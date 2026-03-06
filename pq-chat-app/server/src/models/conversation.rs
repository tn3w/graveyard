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
pub struct Conversation {
    pub id: String,
    pub participant_user_id_1: String,
    pub participant_user_id_2: String,
    pub created_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct CreateConversationRequest {
    pub participant_user_id: String,
}

impl Conversation {
    pub async fn create(
        pool: &sqlx::SqlitePool,
        user_id_1: String,
        user_id_2: String,
    ) -> Result<Self, sqlx::Error> {
        let (participant_1, participant_2) = if user_id_1 < user_id_2 {
            (user_id_1, user_id_2)
        } else {
            (user_id_2, user_id_1)
        };

        let id = uuid::Uuid::new_v4().to_string();
        let created_at = current_timestamp();

        sqlx::query_as::<_, Conversation>(
            "INSERT INTO conversations 
             (id, participant_user_id_1, participant_user_id_2, created_at)
             VALUES (?, ?, ?, ?)
             ON CONFLICT(participant_user_id_1, participant_user_id_2) 
             DO UPDATE SET created_at = created_at
             RETURNING id, participant_user_id_1, participant_user_id_2, 
                       created_at",
        )
        .bind(&id)
        .bind(&participant_1)
        .bind(&participant_2)
        .bind(created_at)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_id(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, Conversation>(
            "SELECT id, participant_user_id_1, participant_user_id_2, 
                    created_at
             FROM conversations
             WHERE id = ?",
        )
        .bind(id)
        .fetch_optional(pool)
        .await
    }

    #[allow(dead_code)]
    pub async fn find_by_users(
        pool: &sqlx::SqlitePool,
        user_id_1: &str,
        user_id_2: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        let (participant_1, participant_2) = if user_id_1 < user_id_2 {
            (user_id_1, user_id_2)
        } else {
            (user_id_2, user_id_1)
        };

        sqlx::query_as::<_, Conversation>(
            "SELECT id, participant_user_id_1, participant_user_id_2, 
                    created_at
             FROM conversations
             WHERE participant_user_id_1 = ? AND participant_user_id_2 = ?",
        )
        .bind(participant_1)
        .bind(participant_2)
        .fetch_optional(pool)
        .await
    }

    pub async fn find_for_user(
        pool: &sqlx::SqlitePool,
        user_id: &str,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, Conversation>(
            "SELECT id, participant_user_id_1, participant_user_id_2, 
                    created_at
             FROM conversations
             WHERE participant_user_id_1 = ? OR participant_user_id_2 = ?
             ORDER BY created_at DESC",
        )
        .bind(user_id)
        .bind(user_id)
        .fetch_all(pool)
        .await
    }

    pub fn get_other_participant(&self, user_id: &str) -> &str {
        if self.participant_user_id_1 == user_id {
            &self.participant_user_id_2
        } else {
            &self.participant_user_id_1
        }
    }
}

