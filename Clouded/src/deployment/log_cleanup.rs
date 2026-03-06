use crate::deployment::errors::DeploymentError;
use crate::deployment::log_storage::LogStorage;
use std::sync::Arc;
use std::time::Duration;
use tokio::time::interval;

pub struct LogCleanupTask {
    log_storage: Arc<LogStorage>,
    retention_days: u32,
    cleanup_interval: Duration,
}

impl LogCleanupTask {
    pub fn new(
        log_storage: Arc<LogStorage>,
        retention_days: u32,
        cleanup_interval: Duration,
    ) -> Self {
        Self {
            log_storage,
            retention_days,
            cleanup_interval,
        }
    }

    pub async fn start(self) -> Result<(), DeploymentError> {
        let mut cleanup_timer = interval(self.cleanup_interval);

        loop {
            cleanup_timer.tick().await;

            match self.log_storage.cleanup_old_logs(self.retention_days) {
                Ok(removed_count) => {
                    if removed_count > 0 {
                        println!(
                            "Log cleanup: removed {} old log entries",
                            removed_count
                        );
                    }
                }
                Err(error) => {
                    eprintln!("Log cleanup failed: {}", error);
                }
            }
        }
    }

    pub fn spawn(self) -> tokio::task::JoinHandle<Result<(), DeploymentError>> {
        tokio::spawn(async move { self.start().await })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::deployment::types::{InstanceId, LogEntry, LogLevel, ServiceId};
    use chrono::Utc;
    use std::collections::HashMap;
    use tokio::time::Duration as TokioDuration;
    use uuid::Uuid;

    fn create_test_log_entry(
        service_id: ServiceId,
        instance_id: InstanceId,
        level: LogLevel,
        message: &str,
        timestamp: chrono::DateTime<Utc>,
    ) -> LogEntry {
        LogEntry {
            timestamp,
            service_id,
            instance_id,
            level,
            message: message.to_string(),
            metadata: HashMap::new(),
        }
    }

    #[tokio::test]
    async fn test_cleanup_task_removes_old_logs() {
        let log_storage = Arc::new(LogStorage::new());
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let old_time = Utc::now() - chrono::Duration::days(35);
        let recent_time = Utc::now() - chrono::Duration::days(10);

        log_storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Old message",
                old_time,
            ))
            .unwrap();

        log_storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Recent message",
                recent_time,
            ))
            .unwrap();

        assert_eq!(log_storage.count_logs().unwrap(), 2);

        let cleanup_task = LogCleanupTask::new(
            log_storage.clone(),
            30,
            TokioDuration::from_millis(100),
        );

        let task_handle = tokio::spawn(async move {
            cleanup_task.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(200)).await;

        task_handle.abort();

        assert_eq!(log_storage.count_logs().unwrap(), 1);

        let logs = log_storage.get_all_logs().unwrap();
        assert_eq!(logs[0].message, "Recent message");
    }

    #[tokio::test]
    async fn test_cleanup_task_runs_periodically() {
        let log_storage = Arc::new(LogStorage::new());
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let old_time = Utc::now() - chrono::Duration::days(35);

        log_storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Old message 1",
                old_time,
            ))
            .unwrap();

        assert_eq!(log_storage.count_logs().unwrap(), 1);

        let cleanup_task = LogCleanupTask::new(
            log_storage.clone(),
            30,
            TokioDuration::from_millis(100),
        );

        let task_handle = tokio::spawn(async move {
            cleanup_task.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(150)).await;

        assert_eq!(log_storage.count_logs().unwrap(), 0);

        log_storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Old message 2",
                old_time,
            ))
            .unwrap();

        assert_eq!(log_storage.count_logs().unwrap(), 1);

        tokio::time::sleep(TokioDuration::from_millis(150)).await;

        task_handle.abort();

        assert_eq!(log_storage.count_logs().unwrap(), 0);
    }

    #[tokio::test]
    async fn test_cleanup_task_handles_empty_storage() {
        let log_storage = Arc::new(LogStorage::new());

        assert_eq!(log_storage.count_logs().unwrap(), 0);

        let cleanup_task = LogCleanupTask::new(
            log_storage.clone(),
            30,
            TokioDuration::from_millis(100),
        );

        let task_handle = tokio::spawn(async move {
            cleanup_task.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(200)).await;

        task_handle.abort();

        assert_eq!(log_storage.count_logs().unwrap(), 0);
    }
}
