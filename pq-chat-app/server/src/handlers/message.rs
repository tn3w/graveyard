use axum::{
    extract::{Extension, Path, Query},
    http::StatusCode,
    Json,
};
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::middleware::{rate_limit_key_for_user, AuthenticatedUser};
use crate::models::{
    Device, EditMessageRequest, GroupMember, Message, SendGroupMessageRequest,
    SendMessageRequest,
};
use crate::rate_limiter::RateLimiter;
use crate::websocket::{ConnectionManager, WebSocketEvent};

fn current_timestamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

#[derive(Debug, Deserialize)]
pub struct MessageQuery {
    #[serde(default = "default_limit")]
    limit: i64,
    #[serde(default)]
    offset: i64,
}

#[derive(Debug, Deserialize)]
pub struct MessageCursorQuery {
    #[serde(default = "default_limit")]
    limit: i64,
    before_timestamp: Option<i64>,
    before_id: Option<String>,
}

fn default_limit() -> i64 {
    50
}

const MAX_MESSAGE_SIZE: usize = 10 * 1024 * 1024;

#[derive(Debug, Serialize)]
pub struct MessageResponse {
    id: String,
    encrypted_content: Vec<u8>,
    created_at: i64,
    edited_at: Option<i64>,
    conversation_id: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct MessagesListResponse {
    messages: Vec<MessageResponse>,
}

impl From<Message> for MessageResponse {
    fn from(message: Message) -> Self {
        Self {
            id: message.id,
            encrypted_content: message.encrypted_content,
            created_at: message.created_at,
            edited_at: message.edited_at,
            conversation_id: message.conversation_id,
        }
    }
}

pub async fn send_message(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(manager): Extension<ConnectionManager>,
    Extension(rate_limiter): Extension<RateLimiter>,
    Json(request): Json<SendMessageRequest>,
) -> Result<(StatusCode, Json<MessageResponse>), StatusCode> {
    let rate_key = rate_limit_key_for_user(&auth.user_id, "send_message");
    if !rate_limiter.check_rate_limit(&rate_key).await {
        return Err(StatusCode::TOO_MANY_REQUESTS);
    }

    if request.encrypted_content.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    if request.encrypted_content.len() > MAX_MESSAGE_SIZE {
        return Err(StatusCode::PAYLOAD_TOO_LARGE);
    }

    let conversation = crate::models::Conversation::find_by_id(
        &pool, 
        &request.conversation_id
    )
    .await
    .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?
    .ok_or(StatusCode::NOT_FOUND)?;

    if conversation.participant_user_id_1 != auth.user_id 
        && conversation.participant_user_id_2 != auth.user_id 
    {
        return Err(StatusCode::FORBIDDEN);
    }

    let recipient_user_id = conversation.get_other_participant(&auth.user_id);
    let routing_token = format!("rt_{}", uuid::Uuid::new_v4());

    let message = Message::create(
        &pool,
        routing_token,
        request.encrypted_content.clone(),
        Some(request.conversation_id.clone()),
    )
    .await
    .map_err(|error| {
        tracing::error!(
            "Failed to create message in conversation {}: {}",
            request.conversation_id,
            error
        );
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    let recipient_devices = Device::find_by_user(&pool, recipient_user_id)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    let event = WebSocketEvent::Message {
        message_id: message.id.clone(),
        sender_device_id: auth.device_id.clone(),
        recipient_device_id: String::new(),
        encrypted_content: message.encrypted_content.clone(),
        timestamp: message.created_at,
    };

    if let Ok(json) = serde_json::to_string(&event) {
        for device in recipient_devices {
            manager.send_to_device(&device.id, &json).await;
        }
    }

    Ok((StatusCode::CREATED, Json(message.into())))
}

#[derive(Debug, Deserialize)]
pub struct SendMultiDeviceMessageRequest {
    pub recipient_user_id: String,
    pub encrypted_contents: Vec<EncryptedContent>,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct EncryptedContent {
    pub recipient_device_id: String,
    pub encrypted_content: Vec<u8>,
}

pub async fn send_multi_device_message(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(manager): Extension<ConnectionManager>,
    Extension(rate_limiter): Extension<RateLimiter>,
    Json(request): Json<SendMultiDeviceMessageRequest>,
) -> Result<StatusCode, StatusCode> {
    let rate_key = rate_limit_key_for_user(&auth.user_id, "send_message");
    if !rate_limiter.check_rate_limit(&rate_key).await {
        return Err(StatusCode::TOO_MANY_REQUESTS);
    }

    if request.encrypted_contents.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    for content in &request.encrypted_contents {
        if content.encrypted_content.is_empty() {
            return Err(StatusCode::BAD_REQUEST);
        }
        if content.encrypted_content.len() > MAX_MESSAGE_SIZE {
            return Err(StatusCode::PAYLOAD_TOO_LARGE);
        }
    }

    let recipient_devices = Device::find_by_user(&pool, &request.recipient_user_id)
        .await
        .map_err(|error| {
            tracing::error!(
                "Failed to find devices for user {}: {}",
                request.recipient_user_id,
                error
            );
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let recipient_device_ids: std::collections::HashSet<String> = 
        recipient_devices.iter().map(|d| d.id.clone()).collect();

    for content in &request.encrypted_contents {
        if !recipient_device_ids.contains(&content.recipient_device_id) {
            return Err(StatusCode::BAD_REQUEST);
        }
    }

    let routing_token = format!("rt_{}", uuid::Uuid::new_v4());

    let valid_contents: Vec<(String, Vec<u8>, Option<String>, Option<String>)> = 
        request
            .encrypted_contents
            .into_iter()
            .map(|c| (c.recipient_device_id, c.encrypted_content, None, None))
            .collect();

    if valid_contents.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let messages = Message::create_batch(
        &pool,
        routing_token,
        valid_contents,
    )
    .await
    .map_err(|error| {
        tracing::error!(
            "Failed to create multi-device messages: {}",
            error
        );
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    for message in messages {
        let event = WebSocketEvent::Message {
            message_id: message.id.clone(),
            sender_device_id: auth.device_id.clone(),
            recipient_device_id: String::new(),
            encrypted_content: message.encrypted_content.clone(),
            timestamp: message.created_at,
        };

        if let Ok(json) = serde_json::to_string(&event) {
            for device in &recipient_devices {
                manager.send_to_device(&device.id, &json).await;
            }
        }
    }

    Ok(StatusCode::CREATED)
}

pub async fn get_messages(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Query(query): Query<MessageQuery>,
) -> Result<Json<MessagesListResponse>, StatusCode> {
    let messages = sqlx::query_as::<_, Message>(
        "SELECT DISTINCT m.id, m.routing_token, m.sealed_sender_version, 
                m.recipient_device_id, m.encrypted_content, m.created_at, 
                m.edited_at, m.conversation_id, m.group_id
         FROM messages m
         LEFT JOIN conversations c ON m.conversation_id = c.id
         LEFT JOIN devices d ON m.recipient_device_id = d.id
         LEFT JOIN group_members gm ON m.group_id = gm.group_id
         WHERE (c.participant_user_id_1 = ? 
                OR c.participant_user_id_2 = ?)
            OR (m.group_id IS NOT NULL AND d.user_id = ?)
            OR (m.conversation_id IS NULL AND m.group_id IS NULL 
                AND m.recipient_device_id = ?)
         ORDER BY m.created_at DESC
         LIMIT ? OFFSET ?",
    )
    .bind(&auth.user_id)
    .bind(&auth.user_id)
    .bind(&auth.user_id)
    .bind(&auth.device_id)
    .bind(query.limit)
    .bind(query.offset)
    .fetch_all(&pool)
    .await
    .map_err(|error| {
        tracing::error!(
            "Failed to retrieve messages for user {}: {}",
            auth.user_id,
            error
        );
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    let response_messages: Vec<MessageResponse> = messages
        .into_iter()
        .map(|m| m.into())
        .collect();

    Ok(Json(MessagesListResponse { messages: response_messages }))
}

pub async fn get_messages_cursor(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Query(query): Query<MessageCursorQuery>,
) -> Result<Json<MessagesListResponse>, StatusCode> {
    let messages = match (query.before_timestamp, query.before_id) {
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
                            AND m.recipient_device_id = ?))
                   AND (m.created_at < ? 
                        OR (m.created_at = ? AND m.id < ?))
                 ORDER BY m.created_at DESC, m.id DESC
                 LIMIT ?",
            )
            .bind(&auth.user_id)
            .bind(&auth.user_id)
            .bind(&auth.user_id)
            .bind(&auth.device_id)
            .bind(timestamp)
            .bind(timestamp)
            .bind(&id)
            .bind(query.limit)
            .fetch_all(&pool)
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
                           AND m.recipient_device_id = ?)
                 ORDER BY m.created_at DESC, m.id DESC
                 LIMIT ?",
            )
            .bind(&auth.user_id)
            .bind(&auth.user_id)
            .bind(&auth.user_id)
            .bind(&auth.device_id)
            .bind(query.limit)
            .fetch_all(&pool)
            .await
        }
    }
    .map_err(|error| {
        tracing::error!(
            "Failed to retrieve messages for user {}: {}",
            auth.user_id,
            error
        );
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    let response_messages: Vec<MessageResponse> = messages
        .into_iter()
        .map(|m| m.into())
        .collect();

    Ok(Json(MessagesListResponse { messages: response_messages }))
}

pub async fn edit_message(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(manager): Extension<ConnectionManager>,
    Path(message_id): Path<String>,
    Json(request): Json<EditMessageRequest>,
) -> Result<StatusCode, StatusCode> {
    if request.encrypted_content.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    if request.encrypted_content.len() > MAX_MESSAGE_SIZE {
        return Err(StatusCode::PAYLOAD_TOO_LARGE);
    }

    let message = Message::find_by_id(&pool, &message_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to find message {}: {}", message_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?
        .ok_or(StatusCode::NOT_FOUND)?;

    let conversation = if let Some(conv_id) = &message.conversation_id {
        crate::models::Conversation::find_by_id(&pool, conv_id)
            .await
            .ok()
            .flatten()
    } else {
        None
    };

    if let Some(conv) = &conversation {
        if conv.participant_user_id_1 != auth.user_id 
            && conv.participant_user_id_2 != auth.user_id 
        {
            return Err(StatusCode::FORBIDDEN);
        }
    } else {
        return Err(StatusCode::FORBIDDEN);
    }

    Message::update_content(&pool, &message_id, request.encrypted_content.clone())
        .await
        .map_err(|error| {
            tracing::error!("Failed to update message {}: {}", message_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let edited_at = current_timestamp();
    let event = WebSocketEvent::MessageEdited {
        message_id: message_id.clone(),
        encrypted_content: request.encrypted_content,
        edited_at,
    };

    if let (Ok(json), Some(conv)) = (serde_json::to_string(&event), conversation) {
        let recipient_user_id = conv.get_other_participant(&auth.user_id);
        if let Ok(devices) = Device::find_by_user(&pool, recipient_user_id).await {
            for device in devices {
                manager.send_to_device(&device.id, &json).await;
            }
        }
    }

    Ok(StatusCode::NO_CONTENT)
}

pub async fn send_group_message(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(manager): Extension<ConnectionManager>,
    Extension(rate_limiter): Extension<RateLimiter>,
    Json(request): Json<SendGroupMessageRequest>,
) -> Result<StatusCode, StatusCode> {
    let rate_key = rate_limit_key_for_user(&auth.user_id, "send_group_message");
    if !rate_limiter.check_rate_limit(&rate_key).await {
        return Err(StatusCode::TOO_MANY_REQUESTS);
    }

    if request.encrypted_contents.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    for content in &request.encrypted_contents {
        if content.encrypted_content.is_empty() {
            return Err(StatusCode::BAD_REQUEST);
        }
        if content.encrypted_content.len() > MAX_MESSAGE_SIZE {
            return Err(StatusCode::PAYLOAD_TOO_LARGE);
        }
    }

    let members = GroupMember::find_by_group(&pool, &request.group_id)
        .await
        .map_err(|error| {
            tracing::error!(
                "Failed to find members for group {}: {}",
                request.group_id,
                error
            );
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let is_member = members.iter().any(|m| m.user_id == auth.user_id);
    if !is_member {
        return Err(StatusCode::FORBIDDEN);
    }

    let devices = Device::find_by_group_members(&pool, &request.group_id)
        .await
        .map_err(|error| {
            tracing::error!(
                "Failed to find devices for group {}: {}",
                request.group_id,
                error
            );
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let routing_token = format!("rt_{}", uuid::Uuid::new_v4());

    let valid_contents: Vec<(String, Vec<u8>, Option<String>, Option<String>)> = 
        request
            .encrypted_contents
            .into_iter()
            .map(|c| {
                (
                    c.recipient_device_id,
                    c.encrypted_content,
                    None,
                    Some(request.group_id.clone()),
                )
            })
            .collect();

    if valid_contents.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let messages = Message::create_batch(
        &pool,
        routing_token,
        valid_contents,
    )
    .await
    .map_err(|error| {
        tracing::error!(
            "Failed to create group messages for group {}: {}",
            request.group_id,
            error
        );
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    for message in messages {
        let event = WebSocketEvent::Message {
            message_id: message.id.clone(),
            sender_device_id: auth.device_id.clone(),
            recipient_device_id: String::new(),
            encrypted_content: message.encrypted_content.clone(),
            timestamp: message.created_at,
        };

        if let Ok(json) = serde_json::to_string(&event) {
            for device in &devices {
                manager.send_to_device(&device.id, &json).await;
            }
        }
    }

    Ok(StatusCode::CREATED)
}
