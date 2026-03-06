use sqlx::sqlite::{SqlitePool, SqlitePoolOptions};
use std::time::Duration;

pub async fn create_connection_pool(
    database_url: &str,
) -> Result<SqlitePool, sqlx::Error> {
    SqlitePoolOptions::new()
        .max_connections(20)
        .idle_timeout(Duration::from_secs(30))
        .acquire_timeout(Duration::from_secs(30))
        .connect_with(
            sqlx::sqlite::SqliteConnectOptions::new()
                .filename(database_url)
                .create_if_missing(true)
                .busy_timeout(Duration::from_secs(30))
                .journal_mode(sqlx::sqlite::SqliteJournalMode::Wal),
        )
        .await
}

pub async fn run_migrations(
    pool: &SqlitePool,
) -> Result<(), sqlx::migrate::MigrateError> {
    sqlx::migrate!("./migrations").run(pool).await
}
