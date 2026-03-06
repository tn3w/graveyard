use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use std::time::{SystemTime, UNIX_EPOCH};

fn current_timestamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

fn obfuscated_timestamp() -> i64 {
    let timestamp = current_timestamp();
    let mut rng = rand::thread_rng();
    use rand::Rng;
    let jitter = rng.gen_range(-300..=300);
    let rounded = (timestamp / 300) * 300;
    rounded + jitter
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Message {
    pub id: String,
    pub routing_token: String,
    pub sealed_sender_version: i32,
    pub recipient_device_id: Option<String>,
    pub encrypted_content: Vec<u8>,
    pub created_at: i64,
    pub edited_at: Option<i64>,
    pub conversation_id: Option<String>,
    pub group_id: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct SendMessageRequest {
    pub conversation_id: String,
    pub encrypted_content: Vec<u8>,
}

#[derive(Debug, Deserialize)]
pub struct EditMessageRequest {
    pub encrypted_content: Vec<u8>,
}

#[derive(Debug, Deserialize)]
pub struct SendGroupMessageRequest {
    pub group_id: String,
    pub encrypted_contents: Vec<GroupMessageContent>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct GroupMessageContent {
    pub recipient_device_id: String,
    pub encrypted_content: Vec<u8>,
}

impl Message {
    pub async fn create(
        pool: &sqlx::SqlitePool,
        routing_token: String,
        encrypted_content: Vec<u8>,
        conversation_id: Option<String>,
    ) -> Result<Self, sqlx::Error> {
        let id = uuid::Uuid::new_v4().to_string();
        let created_at = obfuscated_timestamp();
        let sealed_sender_version = 1;

        sqlx::query_as::<_, Message>(
            "INSERT INTO messages 
             (id, routing_token, sealed_sender_version, recipient_device_id, 
              encrypted_content, created_at, edited_at, conversation_id, 
              group_id)
             VALUES (?, ?, ?, NULL, ?, ?, NULL, ?, NULL)
             RETURNING id, routing_token, sealed_sender_version, 
                       recipient_device_id, encrypted_content, created_at, 
                       edited_at, conversation_id, group_id",
        )
        .bind(&id)
        .bind(&routing_token)
        .bind(sealed_sender_version)
        .bind(&encrypted_content)
        .bind(created_at)
        .bind(&conversation_id)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_id(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, Message>(
            "SELECT id, routing_token, sealed_sender_version, 
                    recipient_device_id, encrypted_content, created_at, 
                    edited_at, conversation_id, group_id
             FROM messages
             WHERE id = ?",
        )
        .bind(id)
        .fetch_optional(pool)
        .await
    }

    #[allow(dead_code)]
    pub async fn find_for_conversation(
        pool: &sqlx::SqlitePool,
        conversation_id: &str,
        limit: i64,
        offset: i64,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, Message>(
            "SELECT id, routing_token, sealed_sender_version, 
                    recipient_device_id, encrypted_content, created_at, 
                    edited_at, conversation_id, group_id
             FROM messages
             WHERE conversation_id = ?
             ORDER BY created_at DESC
             LIMIT ? OFFSET ?",
        )
        .bind(conversation_id)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool)
        .await
    }

    #[allow(dead_code)]
    pub async fn find_for_user(
        pool: &sqlx::SqlitePool,
        user_id: &str,
        limit: i64,
        offset: i64,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, Message>(
            "SELECT DISTINCT m.id, m.routing_token, 
                    m.sealed_sender_version, m.recipient_device_id, 
                    m.encrypted_content, m.created_at, m.edited_at, 
                    m.conversation_id, m.group_id
             FROM messages m
             LEFT JOIN conversations c ON m.conversation_id = c.id
             LEFT JOIN devices d ON m.recipient_device_id = d.id
             LEFT JOIN group_members gm ON m.group_id = gm.group_id
             WHERE (c.participant_user_id_1 = ? 
                    OR c.participant_user_id_2 = ?)
                OR (m.group_id IS NOT NULL AND d.user_id = ?)
                OR (m.conversation_id IS NULL AND m.group_id IS NULL 
                    AND d.user_id = ?)
             ORDER BY m.created_at DESC, m.rowid DESC
             LIMIT ? OFFSET ?",
        )
        .bind(user_id)
        .bind(user_id)
        .bind(user_id)
        .bind(user_id)
        .bind(limit)
        .bind(offset)
        .fetch_all(pool)
        .await
    }

    #[allow(dead_code)]
    pub async fn find_for_user_cursor(
        pool: &sqlx::SqlitePool,
        user_id: &str,
        limit: i64,
        before_timestamp: Option<i64>,
        before_id: Option<String>,
    ) -> Result<Vec<Self>, sqlx::Error> {
        match (before_timestamp, before_id) {
            (Some(timestamp), Some(id)) => {
                sqlx::query_as::<_, Message>(
                    "SELECT DISTINCT m.id, m.routing_token, 
                            m.sealed_sender_version, m.recipient_device_id, 
                            m.encrypted_content, m.created_at, m.edited_at, 
                            m.conversation_id, m.group_id
                     FROM messages m
                     LEFT JOIN conversations c ON m.conversation_id = c.id
                     LEFT JOIN devices d ON m.recipient_device_id = d.id
                     LEFT JOIN group_members gm ON m.group_id = gm.group_id
                     WHERE ((c.participant_user_id_1 = ? 
                             OR c.participant_user_id_2 = ?)
                            OR (m.group_id IS NOT NULL AND d.user_id = ?)
                            OR (m.conversation_id IS NULL AND m.group_id IS NULL 
                                AND d.user_id = ?))
                       AND (m.created_at < ? 
                            OR (m.created_at = ? AND m.id < ?))
                     ORDER BY m.created_at DESC, m.id DESC
                     LIMIT ?",
                )
                .bind(user_id)
                .bind(user_id)
                .bind(user_id)
                .bind(user_id)
                .bind(timestamp)
                .bind(timestamp)
                .bind(&id)
                .bind(limit)
                .fetch_all(pool)
                .await
            }
            _ => {
                sqlx::query_as::<_, Message>(
                    "SELECT DISTINCT m.id, m.routing_token, 
                            m.sealed_sender_version, m.recipient_device_id, 
                            m.encrypted_content, m.created_at, m.edited_at, 
                            m.conversation_id, m.group_id
                     FROM messages m
                     LEFT JOIN conversations c ON m.conversation_id = c.id
                     LEFT JOIN devices d ON m.recipient_device_id = d.id
                     LEFT JOIN group_members gm ON m.group_id = gm.group_id
                     WHERE (c.participant_user_id_1 = ? 
                            OR c.participant_user_id_2 = ?)
                           OR (m.group_id IS NOT NULL AND d.user_id = ?)
                           OR (m.conversation_id IS NULL AND m.group_id IS NULL 
                               AND d.user_id = ?)
                     ORDER BY m.created_at DESC, m.id DESC
                     LIMIT ?",
                )
                .bind(user_id)
                .bind(user_id)
                .bind(user_id)
                .bind(user_id)
                .bind(limit)
                .fetch_all(pool)
                .await
            }
        }
    }

    pub async fn update_content(
        pool: &sqlx::SqlitePool,
        id: &str,
        encrypted_content: Vec<u8>,
    ) -> Result<(), sqlx::Error> {
        let edited_at = obfuscated_timestamp();

        sqlx::query(
            "UPDATE messages 
             SET encrypted_content = ?, edited_at = ?
             WHERE id = ?",
        )
        .bind(&encrypted_content)
        .bind(edited_at)
        .bind(id)
        .execute(pool)
        .await?;

        Ok(())
    }

    pub async fn create_batch(
        pool: &sqlx::SqlitePool,
        routing_token: String,
        contents: Vec<(String, Vec<u8>, Option<String>, Option<String>)>,
    ) -> Result<Vec<Self>, sqlx::Error> {
        if contents.is_empty() {
            return Ok(Vec::new());
        }

        let created_at = obfuscated_timestamp();
        let sealed_sender_version = 1;
        let mut message_ids = Vec::new();

        for _ in &contents {
            message_ids.push(uuid::Uuid::new_v4().to_string());
        }

        let placeholders = contents
            .iter()
            .map(|_| "(?, ?, ?, ?, ?, ?, NULL, ?, ?)")
            .collect::<Vec<_>>()
            .join(", ");

        let query_string = format!(
            "INSERT INTO messages 
             (id, routing_token, sealed_sender_version, recipient_device_id, 
              encrypted_content, created_at, edited_at, conversation_id, 
              group_id)
             VALUES {}",
            placeholders
        );

        let mut query = sqlx::query(&query_string);

        for (i, (recipient_device_id, encrypted_content, conversation_id, 
                 group_id)) in contents.iter().enumerate() 
        {
            query = query
                .bind(&message_ids[i])
                .bind(&routing_token)
                .bind(sealed_sender_version)
                .bind(recipient_device_id)
                .bind(encrypted_content)
                .bind(created_at)
                .bind(conversation_id)
                .bind(group_id);
        }

        query.execute(pool).await?;

        let placeholders = message_ids
            .iter()
            .map(|_| "?")
            .collect::<Vec<_>>()
            .join(", ");

        let query_string = format!(
            "SELECT id, routing_token, sealed_sender_version, 
                    recipient_device_id, encrypted_content, created_at, 
                    edited_at, conversation_id, group_id
             FROM messages
             WHERE id IN ({})
             ORDER BY created_at DESC",
            placeholders
        );

        let mut query = sqlx::query_as::<_, Message>(&query_string);
        for id in &message_ids {
            query = query.bind(id);
        }

        query.fetch_all(pool).await
    }
}
