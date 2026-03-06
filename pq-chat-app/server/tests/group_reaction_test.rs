mod common;

use axum::{body::Body, http::{Request, StatusCode}};
use common::{create_conversation, create_group, register_and_login, send_message, setup_test_app};
use serde_json::json;
use tower::ServiceExt;

#[tokio::test]
async fn test_create_group_success() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;

    let group_id = create_group(app, &token, "Test Group", vec![]).await;
    assert!(!group_id.is_empty());
}

#[tokio::test]
async fn test_create_group_empty_name() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/groups")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(
                    json!({"name": "", "member_ids": []}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_list_groups() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;

    create_group(app.clone(), &token, "Group 1", vec![]).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/groups")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let groups: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
    assert_eq!(groups.len(), 1);
}

#[tokio::test]
async fn test_add_group_member() {
    let (app, _pool) = setup_test_app().await;
    let (token1, _user1_id, _device1) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2) = register_and_login(app.clone(), "user2").await;

    let group_id = create_group(app.clone(), &token1, "Test Group", vec![]).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/groups/{}/members/{}", group_id, user2_id))
                .header("authorization", format!("Bearer {}", token1))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn test_remove_group_member() {
    let (app, _pool) = setup_test_app().await;
    let (token1, _user1_id, _device1) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2) = register_and_login(app.clone(), "user2").await;

    let group_id = create_group(app.clone(), &token1, "Test Group", vec![user2_id.clone()]).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/groups/{}/members/{}", group_id, user2_id))
                .header("authorization", format!("Bearer {}", token1))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn test_send_group_message_success() {
    let (app, _pool) = setup_test_app().await;
    let (token1, _user1_id, device1) = register_and_login(app.clone(), "user1").await;
    let (token2, user2_id, device2) = register_and_login(app.clone(), "user2").await;

    let group_id = create_group(app.clone(), &token1, "Test Group", vec![user2_id]).await;

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/groups/messages")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token1))
                .body(Body::from(
                    json!({
                        "group_id": group_id,
                        "encrypted_contents": [
                            {"recipient_device_id": device1, "encrypted_content": [1, 2, 3]},
                            {"recipient_device_id": device2, "encrypted_content": [4, 5, 6]}
                        ]
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/messages")
                .header("authorization", format!("Bearer {}", token2))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let response: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let messages = response["messages"].as_array().unwrap();
    assert_eq!(messages.len(), 1);
}

#[tokio::test]
async fn test_send_group_message_not_member() {
    let (app, _pool) = setup_test_app().await;
    let (token1, _user1_id, _device1) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, device2) = register_and_login(app.clone(), "user2").await;
    let (token3, _user3_id, _device3) = register_and_login(app.clone(), "user3").await;

    let group_id = create_group(app.clone(), &token1, "Test Group", vec![user2_id]).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/groups/messages")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token3))
                .body(Body::from(
                    json!({
                        "group_id": group_id,
                        "encrypted_contents": [
                            {"recipient_device_id": device2, "encrypted_content": [1, 2, 3]}
                        ]
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::FORBIDDEN);
}

#[tokio::test]
async fn test_add_reaction_success() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token, &user2_id).await;
    let message_id = send_message(app.clone(), &token, &conversation_id, vec![1, 2, 3]).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/messages/{}/reactions", message_id))
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(json!({"emoji": "👍"}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CREATED);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let reaction: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(reaction["emoji"], "👍");
}

#[tokio::test]
async fn test_add_reaction_empty_emoji() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/messages/some-message-id/reactions")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(json!({"emoji": ""}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_get_reactions() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token, &user2_id).await;
    let message_id = send_message(app.clone(), &token, &conversation_id, vec![1, 2, 3]).await;

    app.clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/messages/{}/reactions", message_id))
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(json!({"emoji": "👍"}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(format!("/messages/{}/reactions", message_id))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let reactions: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
    assert_eq!(reactions.len(), 1);
}

#[tokio::test]
async fn test_remove_reaction() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token, &user2_id).await;
    let message_id = send_message(app.clone(), &token, &conversation_id, vec![1, 2, 3]).await;

    let reaction_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/messages/{}/reactions", message_id))
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(json!({"emoji": "👍"}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(reaction_response.into_body(), usize::MAX)
        .await
        .unwrap();
    let reaction: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let reaction_id = reaction["id"].as_str().unwrap();

    let response = app
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/reactions/{}", reaction_id))
                .header("authorization", format!("Bearer {}", token))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn test_remove_reaction_forbidden() {
    let (app, _pool) = setup_test_app().await;
    let (token1, _user1_id, _device1) = register_and_login(app.clone(), "user1").await;
    let (token2, user2_id, _device2) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token1, &user2_id).await;
    let message_id = send_message(app.clone(), &token1, &conversation_id, vec![1, 2, 3]).await;

    let reaction_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/messages/{}/reactions", message_id))
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token1))
                .body(Body::from(json!({"emoji": "👍"}).to_string()))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(reaction_response.into_body(), usize::MAX)
        .await
        .unwrap();
    let reaction: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let reaction_id = reaction["id"].as_str().unwrap();

    let response = app
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri(format!("/reactions/{}", reaction_id))
                .header("authorization", format!("Bearer {}", token2))
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::FORBIDDEN);
}
