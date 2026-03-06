use axum::{
    extract::{Extension, Path},
    http::StatusCode,
    Json,
};
use serde::Serialize;
use sqlx::SqlitePool;

use crate::middleware::AuthenticatedUser;
use crate::models::{AddReactionRequest, Message, Reaction};
use crate::websocket::{ConnectionManager, WebSocketEvent};

#[derive(Debug, Serialize)]
pub struct ReactionResponse {
    id: String,
    message_id: String,
    user_id: String,
    emoji: String,
    created_at: i64,
}

impl From<Reaction> for ReactionResponse {
    fn from(reaction: Reaction) -> Self {
        Self {
            id: reaction.id,
            message_id: reaction.message_id,
            user_id: reaction.user_id,
            emoji: reaction.emoji,
            created_at: reaction.created_at,
        }
    }
}

pub async fn add_reaction(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(manager): Extension<ConnectionManager>,
    Path(message_id): Path<String>,
    Json(request): Json<AddReactionRequest>,
) -> Result<(StatusCode, Json<ReactionResponse>), StatusCode> {
    if request.emoji.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let reaction = Reaction::create(
        &pool,
        message_id.clone(),
        auth.user_id.clone(),
        request.emoji.clone(),
    )
    .await
    .map_err(|error| {
        tracing::error!(
            "Failed to create reaction for message {} by user {}: {}",
            message_id,
            auth.user_id,
            error
        );
        StatusCode::INTERNAL_SERVER_ERROR
    })?;

    let event = WebSocketEvent::Reaction {
        reaction_id: reaction.id.clone(),
        message_id: reaction.message_id.clone(),
        user_id: reaction.user_id.clone(),
        emoji: reaction.emoji.clone(),
        timestamp: reaction.created_at,
    };

    if let Ok(json) = serde_json::to_string(&event) {
        if let Ok(Some(message)) = Message::find_by_id(&pool, &message_id).await {
            if let Some(conv_id) = &message.conversation_id {
                if let Ok(Some(conv)) = 
                    crate::models::Conversation::find_by_id(&pool, conv_id).await 
                {
                    if let Ok(devices1) = 
                        crate::models::Device::find_by_user(
                            &pool, 
                            &conv.participant_user_id_1
                        ).await 
                    {
                        for device in devices1 {
                            manager.send_to_device(&device.id, &json).await;
                        }
                    }
                    if let Ok(devices2) = 
                        crate::models::Device::find_by_user(
                            &pool, 
                            &conv.participant_user_id_2
                        ).await 
                    {
                        for device in devices2 {
                            manager.send_to_device(&device.id, &json).await;
                        }
                    }
                }
            }
        }
    }

    Ok((StatusCode::CREATED, Json(reaction.into())))
}

pub async fn get_reactions(
    Extension(pool): Extension<SqlitePool>,
    Path(message_id): Path<String>,
) -> Result<Json<Vec<ReactionResponse>>, StatusCode> {
    let reactions = Reaction::find_by_message(&pool, &message_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to get reactions for message {}: {}", message_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let response: Vec<ReactionResponse> = reactions.into_iter().map(Into::into).collect();
    Ok(Json(response))
}

pub async fn remove_reaction(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Path(reaction_id): Path<String>,
) -> Result<StatusCode, StatusCode> {
    let reaction = Reaction::find_by_id(&pool, &reaction_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to find reaction {}: {}", reaction_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?
        .ok_or(StatusCode::NOT_FOUND)?;

    if reaction.user_id != auth.user_id {
        return Err(StatusCode::FORBIDDEN);
    }

    Reaction::delete(&pool, &reaction_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to delete reaction {}: {}", reaction_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    Ok(StatusCode::NO_CONTENT)
}
