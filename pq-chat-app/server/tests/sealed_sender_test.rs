use axum::http::StatusCode;
use serde_json::json;
use axum::{body::Body, http::Request};
use tower::ServiceExt;

mod common;
use common::{setup_test_app, register_and_login};

#[tokio::test]
async fn test_message_without_sender_user_id() {
    let (app, _pool) = setup_test_app().await;

    let (token1, _user1_id, _) = register_and_login(app.clone(), "alice").await;
    let (_, user2_id, _) = register_and_login(app.clone(), "bob").await;

    let conversation_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/conversations")
                .header("Authorization", format!("Bearer {}", token1))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"participant_user_id": user2_id}).to_string()
                ))
                .unwrap()
        )
        .await
        .unwrap();

    assert_eq!(conversation_response.status(), StatusCode::CREATED);
    let body = axum::body::to_bytes(
        conversation_response.into_body(),
        usize::MAX
    ).await.unwrap();
    let conversation: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let conversation_id = conversation["id"].as_str().unwrap();

    let message_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/messages")
                .header("Authorization", format!("Bearer {}", token1))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "conversation_id": conversation_id,
                        "encrypted_content": vec![1, 2, 3, 4, 5]
                    }).to_string()
                ))
                .unwrap()
        )
        .await
        .unwrap();

    assert_eq!(message_response.status(), StatusCode::CREATED);
    let body = axum::body::to_bytes(
        message_response.into_body(),
        usize::MAX
    ).await.unwrap();
    let message: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert!(message.get("sender_user_id").is_none());
    assert!(message.get("sender_username").is_none());
    assert!(message["id"].is_string());
    assert!(message["encrypted_content"].is_array());
}

#[tokio::test]
async fn test_get_messages_without_sender_info() {
    let (app, _pool) = setup_test_app().await;

    let (token1, _user1_id, _) = register_and_login(app.clone(), "alice").await;
    let (token2, user2_id, _) = register_and_login(app.clone(), "bob").await;

    let conversation_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/conversations")
                .header("Authorization", format!("Bearer {}", token1))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"participant_user_id": user2_id}).to_string()
                ))
                .unwrap()
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(
        conversation_response.into_body(),
        usize::MAX
    ).await.unwrap();
    let conversation: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let conversation_id = conversation["id"].as_str().unwrap();

    app.clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/messages")
                .header("Authorization", format!("Bearer {}", token1))
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "conversation_id": conversation_id,
                        "encrypted_content": vec![1, 2, 3, 4, 5]
                    }).to_string()
                ))
                .unwrap()
        )
        .await
        .unwrap();

    let messages_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/messages")
                .header("Authorization", format!("Bearer {}", token2))
                .body(Body::empty())
                .unwrap()
        )
        .await
        .unwrap();

    assert_eq!(messages_response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(
        messages_response.into_body(),
        usize::MAX
    ).await.unwrap();
    let messages: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert!(messages["messages"].is_array());
    let message_list = messages["messages"].as_array().unwrap();
    assert_eq!(message_list.len(), 1);

    let message = &message_list[0];
    assert!(message.get("sender_user_id").is_none());
    assert!(message.get("sender_username").is_none());
    assert!(message["id"].is_string());
}
