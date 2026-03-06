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
pub struct GroupChat {
    pub id: String,
    pub name: String,
    pub created_by: String,
    pub created_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct GroupMember {
    pub group_id: String,
    pub user_id: String,
    pub joined_at: i64,
}

#[derive(Debug, Deserialize)]
pub struct CreateGroupRequest {
    pub name: String,
    pub member_ids: Vec<String>,
}

impl GroupChat {
    pub async fn create(
        pool: &sqlx::SqlitePool,
        name: String,
        created_by: String,
    ) -> Result<Self, sqlx::Error> {
        let id = uuid::Uuid::new_v4().to_string();
        let created_at = current_timestamp();

        sqlx::query_as::<_, GroupChat>(
            "INSERT INTO group_chats (id, name, created_by, created_at)
             VALUES (?, ?, ?, ?)
             RETURNING id, name, created_by, created_at",
        )
        .bind(&id)
        .bind(&name)
        .bind(&created_by)
        .bind(created_at)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_id(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, GroupChat>(
            "SELECT id, name, created_by, created_at
             FROM group_chats
             WHERE id = ?",
        )
        .bind(id)
        .fetch_optional(pool)
        .await
    }

    pub async fn find_for_user(
        pool: &sqlx::SqlitePool,
        user_id: &str,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, GroupChat>(
            "SELECT g.id, g.name, g.created_by, g.created_at
             FROM group_chats g
             INNER JOIN group_members gm ON g.id = gm.group_id
             WHERE gm.user_id = ?
             ORDER BY g.created_at DESC",
        )
        .bind(user_id)
        .fetch_all(pool)
        .await
    }
}

impl GroupMember {
    pub async fn add(
        pool: &sqlx::SqlitePool,
        group_id: String,
        user_id: String,
    ) -> Result<Self, sqlx::Error> {
        let joined_at = current_timestamp();

        sqlx::query_as::<_, GroupMember>(
            "INSERT INTO group_members (group_id, user_id, joined_at)
             VALUES (?, ?, ?)
             RETURNING group_id, user_id, joined_at",
        )
        .bind(&group_id)
        .bind(&user_id)
        .bind(joined_at)
        .fetch_one(pool)
        .await
    }

    pub async fn add_batch(
        pool: &sqlx::SqlitePool,
        group_id: String,
        user_ids: Vec<String>,
    ) -> Result<(), sqlx::Error> {
        if user_ids.is_empty() {
            return Ok(());
        }

        let joined_at = current_timestamp();
        let placeholders = user_ids
            .iter()
            .map(|_| "(?, ?, ?)")
            .collect::<Vec<_>>()
            .join(", ");

        let query_string = format!(
            "INSERT INTO group_members (group_id, user_id, joined_at) VALUES {}",
            placeholders
        );

        let mut query = sqlx::query(&query_string);
        for user_id in &user_ids {
            query = query.bind(&group_id).bind(user_id).bind(joined_at);
        }

        query.execute(pool).await?;
        Ok(())
    }

    pub async fn find_by_group(
        pool: &sqlx::SqlitePool,
        group_id: &str,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, GroupMember>(
            "SELECT group_id, user_id, joined_at
             FROM group_members
             WHERE group_id = ?
             ORDER BY joined_at ASC",
        )
        .bind(group_id)
        .fetch_all(pool)
        .await
    }

    pub async fn remove(
        pool: &sqlx::SqlitePool,
        group_id: &str,
        user_id: &str,
    ) -> Result<(), sqlx::Error> {
        sqlx::query(
            "DELETE FROM group_members 
             WHERE group_id = ? AND user_id = ?",
        )
        .bind(group_id)
        .bind(user_id)
        .execute(pool)
        .await?;

        Ok(())
    }
}
