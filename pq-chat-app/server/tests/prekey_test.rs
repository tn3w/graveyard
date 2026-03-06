mod common;

use axum::{body::Body, http::{Request, StatusCode}};
use common::TestContext;
use serde_json::json;
use tower::ServiceExt;

const TEST_PASSWORD: &str = "ValidPass123!";

#[tokio::test]
async fn test_upload_prekey_bundle() {
    let context = TestContext::new().await;
    let user = context.create_test_user("alice", TEST_PASSWORD).await;
    let device = context.create_test_device(&user.id).await;

    let identity_key = vec![1u8; 32];
    let signed_prekey = vec![2u8; 32];
    let signature = vec![3u8; 64];
    let timestamp = 1234567890i64;
    let one_time_prekeys = vec![vec![4u8; 32], vec![5u8; 32]];

    let request_body = json!({
        "identity_key": identity_key,
        "signed_prekey": signed_prekey,
        "signed_prekey_signature": signature,
        "signed_prekey_timestamp": timestamp,
        "one_time_prekeys": one_time_prekeys,
    });

    let request = Request::builder()
        .method("POST")
        .uri(format!("/prekeys/{}", device.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&request_body).unwrap()))
        .unwrap();

    let response = context.app.clone().oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK);

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let response_json: serde_json::Value = 
        serde_json::from_slice(&body).unwrap();
    
    assert_eq!(response_json["one_time_prekeys_uploaded"], 2);
}

#[tokio::test]
async fn test_fetch_prekey_bundle() {
    let context = TestContext::new().await;
    let user = context.create_test_user("bob", TEST_PASSWORD).await;
    let device = context.create_test_device(&user.id).await;

    let identity_key = vec![1u8; 32];
    let signed_prekey = vec![2u8; 32];
    let signature = vec![3u8; 64];
    let timestamp = 1234567890i64;
    let one_time_prekeys = vec![vec![4u8; 32], vec![5u8; 32]];

    let upload_body = json!({
        "identity_key": identity_key,
        "signed_prekey": signed_prekey,
        "signed_prekey_signature": signature,
        "signed_prekey_timestamp": timestamp,
        "one_time_prekeys": one_time_prekeys,
    });

    let upload_request = Request::builder()
        .method("POST")
        .uri(format!("/prekeys/{}", device.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&upload_body).unwrap()))
        .unwrap();

    context.app.clone().oneshot(upload_request).await.unwrap();

    let fetch_request = Request::builder()
        .method("GET")
        .uri(format!("/prekeys/{}", device.id))
        .body(Body::empty())
        .unwrap();

    let response = context.app.clone().oneshot(fetch_request).await.unwrap();
    assert_eq!(response.status(), StatusCode::OK);

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let bundle: serde_json::Value = serde_json::from_slice(&body).unwrap();

    let bundle_identity: Vec<u8> = serde_json::from_value(
        bundle["identity_key"].clone()
    ).unwrap();
    let bundle_signed: Vec<u8> = serde_json::from_value(
        bundle["signed_prekey"].clone()
    ).unwrap();
    let bundle_signature: Vec<u8> = serde_json::from_value(
        bundle["signed_prekey_signature"].clone()
    ).unwrap();

    assert_eq!(bundle_identity, identity_key);
    assert_eq!(bundle_signed, signed_prekey);
    assert_eq!(bundle_signature, signature);
    assert_eq!(bundle["signed_prekey_timestamp"], timestamp);
    assert!(bundle["one_time_prekey"].is_array());
}

#[tokio::test]
async fn test_one_time_prekey_consumption() {
    let context = TestContext::new().await;
    let user = context.create_test_user("charlie", TEST_PASSWORD).await;
    let device = context.create_test_device(&user.id).await;

    let one_time_prekeys = vec![vec![1u8; 32], vec![2u8; 32], vec![3u8; 32]];

    let upload_body = json!({
        "identity_key": vec![10u8; 32],
        "signed_prekey": vec![20u8; 32],
        "signed_prekey_signature": vec![30u8; 64],
        "signed_prekey_timestamp": 1234567890i64,
        "one_time_prekeys": one_time_prekeys,
    });

    let upload_request = Request::builder()
        .method("POST")
        .uri(format!("/prekeys/{}", device.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&upload_body).unwrap()))
        .unwrap();

    context.app.clone().oneshot(upload_request).await.unwrap();

    let mut consumed_keys = Vec::new();

    for _ in 0..3 {
        let fetch_request = Request::builder()
            .method("GET")
            .uri(format!("/prekeys/{}", device.id))
            .body(Body::empty())
            .unwrap();

        let response = context.app.clone()
            .oneshot(fetch_request)
            .await
            .unwrap();
        
        let body = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        let bundle: serde_json::Value = serde_json::from_slice(&body).unwrap();

        if let Some(key) = bundle["one_time_prekey"].as_array() {
            consumed_keys.push(key.clone());
        }
    }

    assert_eq!(consumed_keys.len(), 3);

    let fetch_request = Request::builder()
        .method("GET")
        .uri(format!("/prekeys/{}", device.id))
        .body(Body::empty())
        .unwrap();

    let response = context.app.clone().oneshot(fetch_request).await.unwrap();
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let bundle: serde_json::Value = serde_json::from_slice(&body).unwrap();

    assert!(bundle["one_time_prekey"].is_null());
}

#[tokio::test]
async fn test_upload_invalid_prekey_bundle() {
    let context = TestContext::new().await;
    let user = context.create_test_user("dave", TEST_PASSWORD).await;
    let device = context.create_test_device(&user.id).await;

    let request_body = json!({
        "identity_key": vec![1u8; 16],
        "signed_prekey": vec![2u8; 32],
        "signed_prekey_signature": vec![3u8; 64],
        "signed_prekey_timestamp": 1234567890i64,
        "one_time_prekeys": [],
    });

    let request = Request::builder()
        .method("POST")
        .uri(format!("/prekeys/{}", device.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&request_body).unwrap()))
        .unwrap();

    let response = context.app.clone().oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_fetch_nonexistent_prekey_bundle() {
    let context = TestContext::new().await;
    let fake_device_id = "nonexistent-device-id";

    let request = Request::builder()
        .method("GET")
        .uri(format!("/prekeys/{}", fake_device_id))
        .body(Body::empty())
        .unwrap();

    let response = context.app.clone().oneshot(request).await.unwrap();
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_prekey_bundle_replacement() {
    let context = TestContext::new().await;
    let user = context.create_test_user("eve", TEST_PASSWORD).await;
    let device = context.create_test_device(&user.id).await;

    let first_bundle = json!({
        "identity_key": vec![1u8; 32],
        "signed_prekey": vec![2u8; 32],
        "signed_prekey_signature": vec![3u8; 64],
        "signed_prekey_timestamp": 1000i64,
        "one_time_prekeys": vec![vec![4u8; 32]],
    });

    let first_request = Request::builder()
        .method("POST")
        .uri(format!("/prekeys/{}", device.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&first_bundle).unwrap()))
        .unwrap();

    context.app.clone().oneshot(first_request).await.unwrap();

    let second_bundle = json!({
        "identity_key": vec![10u8; 32],
        "signed_prekey": vec![20u8; 32],
        "signed_prekey_signature": vec![30u8; 64],
        "signed_prekey_timestamp": 2000i64,
        "one_time_prekeys": vec![vec![40u8; 32]],
    });

    let second_request = Request::builder()
        .method("POST")
        .uri(format!("/prekeys/{}", device.id))
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_string(&second_bundle).unwrap()))
        .unwrap();

    context.app.clone().oneshot(second_request).await.unwrap();

    let fetch_request = Request::builder()
        .method("GET")
        .uri(format!("/prekeys/{}", device.id))
        .body(Body::empty())
        .unwrap();

    let response = context.app.clone().oneshot(fetch_request).await.unwrap();
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let bundle: serde_json::Value = serde_json::from_slice(&body).unwrap();

    let bundle_identity: Vec<u8> = serde_json::from_value(
        bundle["identity_key"].clone()
    ).unwrap();

    assert_eq!(bundle_identity, vec![10u8; 32]);
    assert_eq!(bundle["signed_prekey_timestamp"], 2000);
}
