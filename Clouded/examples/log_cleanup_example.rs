use clouded::deployment::log_cleanup::LogCleanupTask;
use clouded::deployment::log_storage::LogStorage;
use std::sync::Arc;
use std::time::Duration;

#[tokio::main]
async fn main() {
    let log_storage = Arc::new(LogStorage::new());

    let cleanup_task = LogCleanupTask::new(
        log_storage.clone(),
        30,
        Duration::from_secs(24 * 60 * 60),
    );

    let cleanup_handle = cleanup_task.spawn();

    println!("Log cleanup task started");
    println!("Logs older than 30 days will be removed daily");

    tokio::signal::ctrl_c()
        .await
        .expect("Failed to listen for ctrl-c");

    cleanup_handle.abort();
    println!("Log cleanup task stopped");
}
