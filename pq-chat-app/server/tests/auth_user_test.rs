mod common;

use axum::{body::Body, http::{Request, StatusCode}};
use common::{register_and_login, register_and_login_with_password, setup_test_app};
use serde_json::json;
use tower::ServiceExt;

#[tokio::test]
async fn test_register_success() {
    let (app, _pool) = setup_test_app().await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/register")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"username": "testuser", "password": "ValidPass123!"})
                        .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::OK);
    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let json: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert!(json["user_id"].is_string());
}

#[tokio::test]
async fn test_register_duplicate_username() {
    let (app, _pool) = setup_test_app().await;
    let payload = json!({"username": "testuser", "password": "ValidPass123!"})
        .to_string();

    app.clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/register")
                .header("content-type", "application/json")
                .body(Body::from(payload.clone()))
                .unwrap(),
        )
        .await
        .unwrap();

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/register")
                .header("content-type", "application/json")
                .body(Body::from(payload))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::CONFLICT);
}

#[tokio::test]
async fn test_register_short_password() {
    let (app, _pool) = setup_test_app().await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/register")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"username": "testuser", "password": "short"}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_login_success() {
    let (app, _pool) = setup_test_app().await;
    let (token, user_id, device_id) = register_and_login(app, "testuser").await;

    assert!(!token.is_empty());
    assert!(!user_id.is_empty());
    assert!(!device_id.is_empty());
}

#[tokio::test]
async fn test_login_invalid_credentials() {
    let (app, _pool) = setup_test_app().await;

    let response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/login")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "username": "nonexistent",
                        "password": "WrongPass123!",
                        "public_key": vec![0u8; 32]
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_list_devices_authenticated() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "testuser").await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/devices")
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
    let devices: Vec<serde_json::Value> = serde_json::from_slice(&body).unwrap();
    assert_eq!(devices.len(), 1);
}

#[tokio::test]
async fn test_list_devices_unauthenticated() {
    let (app, _pool) = setup_test_app().await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/devices")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_refresh_token_flow() {
    let (app, _pool) = setup_test_app().await;

    let (_, _, _) = register_and_login_with_password(app.clone(), "testuser", "ValidPass123!").await;

    let valid_public_key = vec![
        0x86, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6b,
    ];

    let login_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/login")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({
                        "username": "testuser",
                        "password": "ValidPass123!",
                        "public_key": valid_public_key
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(login_response.into_body(), usize::MAX)
        .await
        .unwrap();
    let login_data: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let refresh_token = login_data["refresh_token"].as_str().unwrap();

    let refresh_response = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/refresh")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"refresh_token": refresh_token}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(refresh_response.status(), StatusCode::OK);
}

#[tokio::test]
async fn test_get_profile() {
    let (app, _pool) = setup_test_app().await;
    let (token, _user_id, _device_id) = register_and_login(app.clone(), "testuser").await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/users/me")
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
    let profile: serde_json::Value = serde_json::from_slice(&body).unwrap();
    assert_eq!(profile["username"], "testuser");
}

#[tokio::test]
async fn test_search_users() {
    let (app, _pool) = setup_test_app().await;
    register_and_login(app.clone(), "alice").await;
    register_and_login(app.clone(), "bob").await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/users")
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
    let users = response["users"].as_array().unwrap();
    assert_eq!(users.len(), 2);
}

#[tokio::test]
async fn test_search_users_with_pagination() {
    let (app, _pool) = setup_test_app().await;

    for i in 0..10 {
        register_and_login(app.clone(), &format!("user{:02}", i)).await;
    }

    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/users?limit=5&offset=0")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let response: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let users = response["users"].as_array().unwrap();
    assert_eq!(users.len(), 5);

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/users?limit=5&offset=5")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let response: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let users = response["users"].as_array().unwrap();
    assert_eq!(users.len(), 5);
}

#[tokio::test]
async fn test_search_users_with_filter() {
    let (app, _pool) = setup_test_app().await;
    register_and_login(app.clone(), "alice").await;
    register_and_login(app.clone(), "bob").await;
    register_and_login(app.clone(), "alicia").await;

    let response = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/users?search=ali")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let response: serde_json::Value = serde_json::from_slice(&body).unwrap();
    let users = response["users"].as_array().unwrap();
    assert_eq!(users.len(), 2);
}
