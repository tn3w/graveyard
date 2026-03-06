mod database;
mod models;
mod auth;
mod handlers;
mod middleware;
mod websocket;
mod cache;
mod rate_limiter;
mod security_headers;

use axum::{
    http::StatusCode,
    routing::{get, post, delete},
    Extension,
    Router,
    middleware as axum_middleware,
};
use cache::AppCache;
use rate_limiter::RateLimiter;
use std::net::SocketAddr;
use tower_http::cors::CorsLayer;
use websocket::ConnectionManager;
use sqlx::SqlitePool;

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    auth::initialize_jwt_secret();

    let database_url = std::env::var("DATABASE_URL")
        .unwrap_or_else(|_| "sqlite:chat.db".to_string());

    let pool = database::create_connection_pool(&database_url)
        .await
        .expect("Failed to create database pool");

    database::run_migrations(&pool)
        .await
        .expect("Failed to run migrations");

    tracing::info!("Database initialized successfully");

    let connection_manager = ConnectionManager::new();
    let app_cache = AppCache::new();
    let rate_limiter = RateLimiter::new(5.0, 0.1);

    let application = Router::new()
        .route("/health", get(health_check))
        .route("/ws", get(websocket::websocket_handler))
        .route("/auth/register", post(handlers::auth::register))
        .route("/auth/login", post(handlers::auth::login))
        .route("/auth/refresh", post(handlers::auth::refresh))
        .route("/auth/logout", post(handlers::auth::logout))
        .route("/devices", get(handlers::device::list_devices))
        .route("/devices/:device_id", delete(handlers::device::delete_device))
        .route("/prekeys/:device_id", post(handlers::prekey::upload_prekey_bundle))
        .route("/prekeys/:device_id", get(handlers::prekey::fetch_prekey_bundle))
        .route("/conversations", post(handlers::conversation::create_conversation))
        .route("/conversations", get(handlers::conversation::list_conversations))
        .route("/conversations/:conversation_id", get(handlers::conversation::get_conversation))
        .route("/users/me", get(handlers::user::get_profile))
        .route("/users", get(handlers::user::search_users))
        .route("/users/:user_id/devices", get(handlers::user::get_user_devices))
        .route("/messages", post(handlers::message::send_message))
        .route("/messages/multi-device", post(handlers::message::send_multi_device_message))
        .route("/messages", get(handlers::message::get_messages))
        .route("/messages/cursor", get(handlers::message::get_messages_cursor))
        .route("/messages/:message_id", post(handlers::message::edit_message))
        .route("/messages/:message_id/reactions", post(handlers::reaction::add_reaction))
        .route("/messages/:message_id/reactions", get(handlers::reaction::get_reactions))
        .route("/groups/messages", post(handlers::message::send_group_message))
        .route("/groups", post(handlers::group::create_group))
        .route("/groups", get(handlers::group::list_groups))
        .route("/groups/:group_id/members", get(handlers::group::get_group_members))
        .route("/groups/:group_id/members/:user_id", post(handlers::group::add_group_member))
        .route("/groups/:group_id/members/:user_id", delete(handlers::group::remove_group_member))
        .route("/reactions/:reaction_id", delete(handlers::reaction::remove_reaction))
        .layer(axum_middleware::from_fn(security_headers::add_security_headers))
        .layer(Extension(connection_manager))
        .layer(Extension(app_cache))
        .layer(Extension(rate_limiter))
        .layer(Extension(pool))
        .layer(tower_http::trace::TraceLayer::new_for_http())
        .layer(CorsLayer::permissive());

    let address = SocketAddr::from(([0, 0, 0, 0], 3000));
    let listener = tokio::net::TcpListener::bind(address)
        .await
        .expect("Failed to bind to address");

    tracing::info!("Server listening on {}", address);

    axum::serve(listener, application)
        .await
        .expect("Server failed");
}

async fn health_check(
    Extension(pool): Extension<SqlitePool>,
) -> Result<&'static str, StatusCode> {
    sqlx::query("SELECT 1")
        .execute(&pool)
        .await
        .map_err(|error| {
            tracing::error!("Health check failed: {}", error);
            StatusCode::SERVICE_UNAVAILABLE
        })?;

    Ok("ok")
}
