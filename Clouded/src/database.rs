use sqlx::{SqlitePool, sqlite::SqlitePoolOptions};
use crate::models::{User, RegistrationToken, RefreshToken};

pub async fn init_database() -> Result<SqlitePool, sqlx::Error> {
    let pool = SqlitePoolOptions::new()
        .max_connections(5)
        .connect("sqlite:app.db?mode=rwc")
        .await?;
    
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            totp_secret TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )"
    )
    .execute(&pool)
    .await?;
    
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS registration_tokens (
            token TEXT PRIMARY KEY,
            used BOOLEAN NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )"
    )
    .execute(&pool)
    .await?;
    
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS refresh_tokens (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"
    )
    .execute(&pool)
    .await?;
    
    sqlx::query(
        "CREATE TABLE IF NOT EXISTS webauthn_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            credential_id BLOB NOT NULL,
            public_key BLOB NOT NULL,
            counter INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"
    )
    .execute(&pool)
    .await?;
    
    Ok(pool)
}

pub async fn ensure_registration_token(
    pool: &SqlitePool
) -> Result<Option<String>, sqlx::Error> {
    let user_count: i64 = sqlx::query_scalar("SELECT COUNT(*) FROM users")
        .fetch_one(pool)
        .await?;
    
    if user_count > 0 {
        return Ok(None);
    }
    
    let existing: Option<RegistrationToken> = sqlx::query_as(
        "SELECT * FROM registration_tokens WHERE used = 0 LIMIT 1"
    )
    .fetch_optional(pool)
    .await?;
    
    if let Some(token) = existing {
        return Ok(Some(token.token));
    }
    
    let token = uuid::Uuid::new_v4().to_string();
    let now = chrono::Utc::now().timestamp();
    
    sqlx::query(
        "INSERT INTO registration_tokens (token, used, created_at) VALUES (?, 0, ?)"
    )
    .bind(&token)
    .bind(now)
    .execute(pool)
    .await?;
    
    Ok(Some(token))
}

pub async fn get_user_by_username(
    pool: &SqlitePool,
    username: &str
) -> Result<Option<User>, sqlx::Error> {
    sqlx::query_as("SELECT * FROM users WHERE username = ?")
        .bind(username)
        .fetch_optional(pool)
        .await
}

pub async fn get_user_by_id(
    pool: &SqlitePool,
    user_id: i64
) -> Result<Option<User>, sqlx::Error> {
    sqlx::query_as("SELECT * FROM users WHERE id = ?")
        .bind(user_id)
        .fetch_optional(pool)
        .await
}

pub async fn create_user(
    pool: &SqlitePool,
    username: &str,
    password_hash: &str,
    totp_secret: &str
) -> Result<i64, sqlx::Error> {
    let now = chrono::Utc::now().timestamp();
    
    let result = sqlx::query(
        "INSERT INTO users (username, password_hash, totp_secret, created_at)
         VALUES (?, ?, ?, ?)"
    )
    .bind(username)
    .bind(password_hash)
    .bind(totp_secret)
    .bind(now)
    .execute(pool)
    .await?;
    
    Ok(result.last_insert_rowid())
}

pub async fn mark_token_used(
    pool: &SqlitePool,
    token: &str
) -> Result<(), sqlx::Error> {
    sqlx::query("UPDATE registration_tokens SET used = 1 WHERE token = ?")
        .bind(token)
        .execute(pool)
        .await?;
    
    Ok(())
}

pub async fn verify_registration_token(
    pool: &SqlitePool,
    token: &str
) -> Result<bool, sqlx::Error> {
    let result: Option<RegistrationToken> = sqlx::query_as(
        "SELECT * FROM registration_tokens WHERE token = ? AND used = 0"
    )
    .bind(token)
    .fetch_optional(pool)
    .await?;
    
    Ok(result.is_some())
}

pub async fn store_refresh_token(
    pool: &SqlitePool,
    token: &str,
    user_id: i64,
    expires_at: i64
) -> Result<(), sqlx::Error> {
    let now = chrono::Utc::now().timestamp();
    
    sqlx::query(
        "INSERT INTO refresh_tokens (token, user_id, expires_at, created_at)
         VALUES (?, ?, ?, ?)"
    )
    .bind(token)
    .bind(user_id)
    .bind(expires_at)
    .bind(now)
    .execute(pool)
    .await?;
    
    Ok(())
}

pub async fn get_refresh_token(
    pool: &SqlitePool,
    token: &str
) -> Result<Option<RefreshToken>, sqlx::Error> {
    sqlx::query_as("SELECT * FROM refresh_tokens WHERE token = ?")
        .bind(token)
        .fetch_optional(pool)
        .await
}

pub async fn delete_refresh_token(
    pool: &SqlitePool,
    token: &str
) -> Result<(), sqlx::Error> {
    sqlx::query("DELETE FROM refresh_tokens WHERE token = ?")
        .bind(token)
        .execute(pool)
        .await?;
    
    Ok(())
}
