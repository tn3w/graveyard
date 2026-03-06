use axum::{routing::{delete, get, post}, Extension, Router, body::Body, http::Request};
use chat_server::{auth, cache::AppCache, handlers, rate_limiter::RateLimiter, websocket::ConnectionManager, models::{User, Device}};
use serde_json::json;
use sqlx::SqlitePool;
use tower::ServiceExt;

const TEST_PASSWORD: &str = "ValidPass123!";

#[allow(dead_code)]
pub async fn setup_test_app() -> (Router, SqlitePool) {
    std::env::set_var("JWT_SECRET", "test_secret_at_least_32_bytes_long_for_testing_purposes");
    auth::initialize_jwt_secret();

    let pool = SqlitePool::connect("sqlite::memory:")
        .await
        .expect("Failed to create test database");

    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("Failed to run migrations");

    let connection_manager = ConnectionManager::new();
    let app_cache = AppCache::new();
    let rate_limiter = RateLimiter::new(1000.0, 100.0);

    let app = Router::new()
        .route("/ws", get(chat_server::websocket::websocket_handler))
        .route("/auth/register", post(handlers::auth::register))
        .route("/auth/login", post(handlers::auth::login))
        .route("/auth/refresh", post(handlers::auth::refresh))
        .route("/auth/logout", post(handlers::auth::logout))
        .route("/devices", get(handlers::device::list_devices))
        .route("/devices/{device_id}", delete(handlers::device::delete_device))
        .route("/prekeys/{device_id}", post(handlers::prekey::upload_prekey_bundle))
        .route("/prekeys/{device_id}", get(handlers::prekey::fetch_prekey_bundle))
        .route("/conversations", post(handlers::conversation::create_conversation))
        .route("/conversations", get(handlers::conversation::list_conversations))
        .route("/conversations/{conversation_id}", get(handlers::conversation::get_conversation))
        .route("/users/me", get(handlers::user::get_profile))
        .route("/users", get(handlers::user::search_users))
        .route("/users/{user_id}/devices", get(handlers::user::get_user_devices))
        .route("/messages", post(handlers::message::send_message))
        .route("/messages/multi-device", post(handlers::message::send_multi_device_message))
        .route("/messages", get(handlers::message::get_messages))
        .route("/messages/cursor", get(handlers::message::get_messages_cursor))
        .route("/messages/{message_id}", post(handlers::message::edit_message))
        .route("/messages/{message_id}/reactions", post(handlers::reaction::add_reaction))
        .route("/messages/{message_id}/reactions", get(handlers::reaction::get_reactions))
        .route("/groups/messages", post(handlers::message::send_group_message))
        .route("/groups", post(handlers::group::create_group))
        .route("/groups", get(handlers::group::list_groups))
        .route("/groups/{group_id}/members", get(handlers::group::get_group_members))
        .route("/groups/{group_id}/members/{user_id}", post(handlers::group::add_group_member))
        .route("/groups/{group_id}/members/{user_id}", delete(handlers::group::remove_group_member))
        .route("/reactions/{reaction_id}", delete(handlers::reaction::remove_reaction))
        .layer(Extension(connection_manager))
        .layer(Extension(app_cache))
        .layer(Extension(rate_limiter))
        .layer(Extension(pool.clone()));

    (app, pool)
}

#[allow(dead_code)]
pub async fn register_and_login(
    app: Router,
    username: &str,
) -> (String, String, String) {
    register_and_login_with_password(app, username, TEST_PASSWORD).await
}

#[allow(dead_code)]
pub async fn register_and_login_with_password(
    app: Router,
    username: &str,
    password: &str,
) -> (String, String, String) {
    let _register_response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/auth/register")
                .header("content-type", "application/json")
                .body(Body::from(
                    json!({"username": username, "password": password}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    let valid_public_key = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
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
                        "username": username,
                        "password": password,
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
    let body_str = String::from_utf8_lossy(&body);
    let data: serde_json::Value = serde_json::from_slice(&body).unwrap_or_else(|e| {
        panic!("Failed to parse login response: {}. Body: {}", e, body_str);
    });

    if !data["access_token"].is_string() {
        panic!("access_token field missing. Response: {}", body_str);
    }

    (
        data["access_token"].as_str().unwrap().to_string(),
        data["user_id"].as_str().expect("user_id field missing").to_string(),
        data["device_id"].as_str().expect("device_id field missing").to_string(),
    )
}

#[allow(dead_code)]
pub async fn create_conversation(
    app: Router,
    token: &str,
    participant_user_id: &str,
) -> String {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/conversations")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(
                    json!({"participant_user_id": participant_user_id}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let conversation: serde_json::Value = serde_json::from_slice(&body).unwrap();
    conversation["id"].as_str().unwrap().to_string()
}

#[allow(dead_code)]
pub async fn send_message(
    app: Router,
    token: &str,
    conversation_id: &str,
    content: Vec<u8>,
) -> String {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/messages")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(
                    json!({
                        "conversation_id": conversation_id,
                        "encrypted_content": content
                    })
                    .to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let message: serde_json::Value = serde_json::from_slice(&body).unwrap();
    message["id"].as_str().unwrap().to_string()
}

#[allow(dead_code)]
pub async fn create_group(
    app: Router,
    token: &str,
    name: &str,
    member_ids: Vec<String>,
) -> String {
    let response = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/groups")
                .header("content-type", "application/json")
                .header("authorization", format!("Bearer {}", token))
                .body(Body::from(
                    json!({"name": name, "member_ids": member_ids}).to_string(),
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    let body = axum::body::to_bytes(response.into_body(), usize::MAX)
        .await
        .unwrap();
    let group: serde_json::Value = serde_json::from_slice(&body).unwrap();
    group["id"].as_str().unwrap().to_string()
}

pub struct TestContext {
    pub app: Router,
    pub pool: SqlitePool,
}

impl TestContext {
    pub async fn new() -> Self {
        let (app, pool) = setup_test_app().await;
        Self { app, pool }
    }

    pub async fn create_test_user(&self, username: &str, password: &str) -> User {
        let password_hash = chat_server::auth::hash_password(password).unwrap();
        User::create(&self.pool, username.to_string(), password_hash)
            .await
            .unwrap()
    }

    pub async fn create_test_device(&self, user_id: &str) -> Device {
        let public_key = vec![1u8; 32];
        Device::create(&self.pool, user_id.to_string(), public_key)
            .await
            .unwrap()
    }
}
