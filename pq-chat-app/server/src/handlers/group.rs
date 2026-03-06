use axum::{
    extract::{Extension, Path},
    http::StatusCode,
    Json,
};
use serde::Serialize;
use sqlx::SqlitePool;

use crate::cache::AppCache;
use crate::middleware::AuthenticatedUser;
use crate::models::{CreateGroupRequest, GroupChat, GroupMember};

#[derive(Debug, Serialize)]
pub struct GroupResponse {
    id: String,
    name: String,
    created_by: String,
    created_at: i64,
}

impl From<GroupChat> for GroupResponse {
    fn from(group: GroupChat) -> Self {
        Self {
            id: group.id,
            name: group.name,
            created_by: group.created_by,
            created_at: group.created_at,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct GroupMemberResponse {
    group_id: String,
    user_id: String,
    joined_at: i64,
}

impl From<GroupMember> for GroupMemberResponse {
    fn from(member: GroupMember) -> Self {
        Self {
            group_id: member.group_id,
            user_id: member.user_id,
            joined_at: member.joined_at,
        }
    }
}

pub async fn create_group(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(cache): Extension<AppCache>,
    Json(request): Json<CreateGroupRequest>,
) -> Result<(StatusCode, Json<GroupResponse>), StatusCode> {
    if request.name.is_empty() {
        return Err(StatusCode::BAD_REQUEST);
    }

    let group = GroupChat::create(&pool, request.name, auth.user_id.clone())
        .await
        .map_err(|error| {
            tracing::error!("Failed to create group: {}", error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let mut all_members = vec![auth.user_id.clone()];
    for member_id in request.member_ids {
        if member_id != auth.user_id {
            all_members.push(member_id);
        }
    }

    GroupMember::add_batch(&pool, group.id.clone(), all_members)
        .await
        .map_err(|error| {
            tracing::error!("Failed to add members to group {}: {}", group.id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    cache.invalidate_group_members(&group.id).await;

    Ok((StatusCode::CREATED, Json(group.into())))
}

pub async fn list_groups(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
) -> Result<Json<Vec<GroupResponse>>, StatusCode> {
    let groups = GroupChat::find_for_user(&pool, &auth.user_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to list groups for user {}: {}", auth.user_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let response: Vec<GroupResponse> = groups.into_iter().map(Into::into).collect();
    Ok(Json(response))
}

pub async fn get_group_members(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(cache): Extension<AppCache>,
    Path(group_id): Path<String>,
) -> Result<Json<Vec<GroupMemberResponse>>, StatusCode> {
    if let Some(cached_members) = cache.get_group_members(&group_id).await {
        let is_member = cached_members.iter().any(|m| m.user_id == auth.user_id);
        if !is_member {
            return Err(StatusCode::FORBIDDEN);
        }
        let response: Vec<GroupMemberResponse> = cached_members
            .iter()
            .map(|m| m.clone().into())
            .collect();
        return Ok(Json(response));
    }

    let _group = GroupChat::find_by_id(&pool, &group_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to find group {}: {}", group_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?
        .ok_or(StatusCode::NOT_FOUND)?;

    let members = GroupMember::find_by_group(&pool, &group_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to find members for group {}: {}", group_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let is_member = members.iter().any(|m| m.user_id == auth.user_id);
    if !is_member {
        return Err(StatusCode::FORBIDDEN);
    }

    cache.set_group_members(group_id, members.clone()).await;

    let response: Vec<GroupMemberResponse> = members.into_iter().map(Into::into).collect();
    Ok(Json(response))
}

pub async fn add_group_member(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(cache): Extension<AppCache>,
    Path((group_id, user_id)): Path<(String, String)>,
) -> Result<StatusCode, StatusCode> {
    let group = GroupChat::find_by_id(&pool, &group_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to find group {}: {}", group_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?
        .ok_or(StatusCode::NOT_FOUND)?;

    if group.created_by != auth.user_id {
        return Err(StatusCode::FORBIDDEN);
    }

    GroupMember::add(&pool, group_id.clone(), user_id.clone())
        .await
        .map_err(|error| {
            tracing::error!("Failed to add user {} to group {}: {}", user_id, group_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    cache.invalidate_group_members(&group_id).await;

    Ok(StatusCode::NO_CONTENT)
}

pub async fn remove_group_member(
    auth: AuthenticatedUser,
    Extension(pool): Extension<SqlitePool>,
    Extension(cache): Extension<AppCache>,
    Path((group_id, user_id)): Path<(String, String)>,
) -> Result<StatusCode, StatusCode> {
    let group = GroupChat::find_by_id(&pool, &group_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to find group {}: {}", group_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?
        .ok_or(StatusCode::NOT_FOUND)?;

    if group.created_by != auth.user_id && user_id != auth.user_id {
        return Err(StatusCode::FORBIDDEN);
    }

    GroupMember::remove(&pool, &group_id, &user_id)
        .await
        .map_err(|error| {
            tracing::error!("Failed to remove user {} from group {}: {}", user_id, group_id, error);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    cache.invalidate_group_members(&group_id).await;

    Ok(StatusCode::NO_CONTENT)
}
