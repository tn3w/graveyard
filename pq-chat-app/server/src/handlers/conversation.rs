use axum::{Extension, Json, http::StatusCode};
use serde::Serialize;
use sqlx::SqlitePool;

use crate::middleware::AuthenticatedUser;
use crate::models::{Conversation, CreateConversationRequest, User};

#[derive(Debug, Serialize)]
pub struct ErrorResponse {
    pub error: String,
}

pub async fn create_conversation(
    Extension(pool): Extension<SqlitePool>,
    user: AuthenticatedUser,
    Json(request): Json<CreateConversationRequest>,
) -> Result<(StatusCode, Json<Conversation>), (StatusCode, Json<ErrorResponse>)> {
    if request.participant_user_id == user.user_id {
        return Err((
            StatusCode::BAD_REQUEST,
            Json(ErrorResponse {
                error: "Cannot create conversation with yourself".to_string(),
            }),
        ));
    }

    let other_user = User::find_by_id(&pool, &request.participant_user_id)
        .await
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?
        .ok_or_else(|| {
            (
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "User not found".to_string(),
                }),
            )
        })?;

    let conversation = Conversation::create(
        &pool,
        user.user_id.clone(),
        other_user.id,
    )
    .await
    .map_err(|error| {
        (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(ErrorResponse {
                error: format!("Failed to create conversation: {}", error),
            }),
        )
    })?;

    Ok((StatusCode::CREATED, Json(conversation)))
}

pub async fn list_conversations(
    Extension(pool): Extension<SqlitePool>,
    user: AuthenticatedUser,
) -> Result<Json<Vec<Conversation>>, (StatusCode, Json<ErrorResponse>)> {
    let conversations = Conversation::find_for_user(&pool, &user.user_id)
        .await
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?;

    Ok(Json(conversations))
}

pub async fn get_conversation(
    Extension(pool): Extension<SqlitePool>,
    user: AuthenticatedUser,
    axum::extract::Path(conversation_id): axum::extract::Path<String>,
) -> Result<Json<Conversation>, (StatusCode, Json<ErrorResponse>)> {
    let conversation = Conversation::find_by_id(&pool, &conversation_id)
        .await
        .map_err(|error| {
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(ErrorResponse {
                    error: format!("Database error: {}", error),
                }),
            )
        })?
        .ok_or_else(|| {
            (
                StatusCode::NOT_FOUND,
                Json(ErrorResponse {
                    error: "Conversation not found".to_string(),
                }),
            )
        })?;

    if conversation.participant_user_id_1 != user.user_id 
        && conversation.participant_user_id_2 != user.user_id 
    {
        return Err((
            StatusCode::FORBIDDEN,
            Json(ErrorResponse {
                error: "Not a participant in this conversation".to_string(),
            }),
        ));
    }

    Ok(Json(conversation))
}
