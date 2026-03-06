mod common;

use axum::{body::Body, http::{Request, StatusCode}};
use chat_server::rate_limiter::RateLimiter;
use common::{register_and_login, setup_test_app};
use serde_json::json;
use tokio::time::{sleep, Duration};
use tower::ServiceExt;

#[tokio::test]
async fn test_rate_limiter_allows_within_limit() {
    let limiter = RateLimiter::new(10.0, 10.0);

    for _ in 0..10 {
        assert!(limiter.check_rate_limit("user1").await);
    }
}

#[tokio::test]
async fn test_rate_limiter_blocks_over_limit() {
    let limiter = RateLimiter::new(5.0, 1.0);

    for _ in 0..5 {
        assert!(limiter.check_rate_limit("user1").await);
    }

    assert!(!limiter.check_rate_limit("user1").await);
}

#[tokio::test]
async fn test_rate_limiter_refills_over_time() {
    let limiter = RateLimiter::new(2.0, 10.0);

    assert!(limiter.check_rate_limit("user1").await);
    assert!(limiter.check_rate_limit("user1").await);
    assert!(!limiter.check_rate_limit("user1").await);

    sleep(Duration::from_millis(150)).await;

    assert!(limiter.check_rate_limit("user1").await);
}

#[tokio::test]
async fn test_rate_limiter_separate_keys() {
    let limiter = RateLimiter::new(2.0, 1.0);

    assert!(limiter.check_rate_limit("user1").await);
    assert!(limiter.check_rate_limit("user1").await);
    assert!(!limiter.check_rate_limit("user1").await);

    assert!(limiter.check_rate_limit("user2").await);
    assert!(limiter.check_rate_limit("user2").await);
    assert!(!limiter.check_rate_limit("user2").await);
}

#[tokio::test]
async fn test_rate_limiter_reset() {
    let limiter = RateLimiter::new(2.0, 1.0);

    assert!(limiter.check_rate_limit("user1").await);
    assert!(limiter.check_rate_limit("user1").await);
    assert!(!limiter.check_rate_limit("user1").await);

    limiter.reset("user1").await;

    assert!(limiter.check_rate_limit("user1").await);
}

#[tokio::test]
async fn test_message_rate_limiting() {
    let (app, _pool) = setup_test_app().await;
    let (token1, _user1_id, _device1) = register_and_login(app.clone(), "sender").await;
    let (_token2, user2_id, _device2) = register_and_login(app.clone(), "recipient").await;

    let conversation_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/conversations")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token1))
                .body(Body::from(
                    json!({"participant_user_id": user2_id}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(conversation_response.into_body(), usize::MAX)
        .await
        .unwrap();
    let conversation: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let conversation_id = conversation["id"].as_str().unwrap();

    for i in 0..1000 {
        let response = app
            .clone()
            .oneshot(
                Request::builder()
                    .method("POST")
                    .uri("/messages")
                    .header("authorization", format!("Bearer {}", token1))
                    .header("content-type", "application/json")
                    .body(Body::from(
                        json!({
                            "conversation_id": conversation_id,
                            "encrypted_content": vec![i as u8]
                        })
                        .to_string(),
                    ))
                    .unwrap(),
            )
            .await
            .unwrap();

        if i < 100 {
            assert_eq!(response.status(), StatusCode::CREATED);
        }
    }
}
