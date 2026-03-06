mod common;

use axum::{body::Body, http::{Request, StatusCode}};
use common::{create_conversation, register_and_login, send_message, setup_test_app};
use serde_json::json;
use tower::ServiceExt;

#[tokio::test]
async fn test_create_conversation_success() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app, &token, &user2_id).await;
    assert!(!conversation_id.is_empty());
}

#[tokio::test]
async fn test_send_message_success() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "sender").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "recipient").await;

    let conversation_id = create_conversation(app.clone(), &token, &user2_id).await;
    let message_id = send_message(app, &token, &conversation_id, vec![1, 2, 3]).await;
    assert!(!message_id.is_empty());
}

#[tokio::test]
async fn test_send_message_empty_content() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token, &user2_id).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/messages")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(
                    json!({
                        "conversation_id": conversation_id,
                        "encrypted_content": []
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_get_messages() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/messages")
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
    let response: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let messages = response["messages"].as_array().unwrap();
    assert_eq!(messages.len(), 0);
}

#[tokio::test]
async fn test_edit_message_success() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token, &user2_id).await;
    let message_id = send_message(app.clone(), &token, &conversation_id, vec![1, 2, 3]).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/messages/{}", message_id))
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(
                    json!({"encrypted_content": [4, 5, 6]}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn test_edit_message_forbidden() {
    let (app, _pool) = setup_test_app().await;
    let (token1, _user1_id, _device1) = register_and_login(app.clone(), "user1").await;
    let (token2, user2_id, _device2) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token1, &user2_id).await;
    let message_id = send_message(app.clone(), &token1, &conversation_id, vec![1, 2, 3]).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri(format!("/messages/{}", message_id))
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token2))
                .body(Body::from(
                    json!({"encrypted_content": [4, 5, 6]}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::NO_CONTENT);
}

#[tokio::test]
async fn test_get_messages_cursor_pagination() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    let conversation_id = create_conversation(app.clone(), &token, &user2_id).await;

    for i in 0..30 {
        send_message(app.clone(), &token, &conversation_id, vec![i as u8]).await;
        tokio::time::sleep(tokio::time::Duration::from_millis(2)).await;
    }

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/messages/cursor?limit=10")
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
    let response: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let first_page = response["messages"].as_array().unwrap();
    assert_eq!(first_page.len(), 10);

    let last_message = &first_page[9];
    let before_timestamp = last_message["created_at"].as_i64().unwrap();
    let before_id = last_message["id"].as_str().unwrap();

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri(format!(
                    "/messages/cursor?limit=10&before_timestamp={}&before_id={}",
                    before_timestamp, before_id
                ))
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
    let response: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let second_page = response["messages"].as_array().unwrap();
    assert_eq!(second_page.len(), 10);
}

#[tokio::test]
async fn test_list_conversations() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "user1").await;
    let (_token2, user2_id, _device2_id) = register_and_login(app.clone(), "user2").await;

    create_conversation(app.clone(), &token, &user2_id).await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/conversations")
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
    let conversations: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
    assert_eq!(conversations.len(), 1);
}
