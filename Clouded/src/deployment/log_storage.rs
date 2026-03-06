use crate::deployment::errors::DeploymentError;
use crate::deployment::metrics_calculator::MetricsCalculator;
use crate::deployment::stream_manager::{LogStream, StreamManager};
use crate::deployment::types::{
    DeploymentMetrics, InstanceId, LogEntry, LogFilter, ServiceId, TimeRange,
};
use chrono::{DateTime, Utc};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

#[derive(Debug, Clone)]
pub struct LogStorage {
    logs: Arc<RwLock<Vec<LogEntry>>>,
    time_index: Arc<RwLock<HashMap<i64, Vec<usize>>>>,
    stream_manager: StreamManager,
    metrics_calculator: MetricsCalculator,
}

impl LogStorage {
    pub fn new() -> Self {
        Self {
            logs: Arc::new(RwLock::new(Vec::new())),
            time_index: Arc::new(RwLock::new(HashMap::new())),
            stream_manager: StreamManager::new(),
            metrics_calculator: MetricsCalculator::new(),
        }
    }

    pub fn ingest_log(&self, log_entry: LogEntry) -> Result<(), DeploymentError> {
        let timestamp_key = log_entry.timestamp.timestamp();
        
        let mut logs = self.logs.write().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire write lock on logs: {}",
                error
            ))
        })?;
        
        let log_index = logs.len();
        logs.push(log_entry.clone());
        
        let mut time_index = self.time_index.write().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire write lock on time index: {}",
                error
            ))
        })?;
        
        time_index
            .entry(timestamp_key)
            .or_insert_with(Vec::new)
            .push(log_index);
        
        self.stream_manager.push_log(&log_entry)?;
        
        Ok(())
    }

    pub fn get_all_logs(&self) -> Result<Vec<LogEntry>, DeploymentError> {
        let logs = self.logs.read().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire read lock on logs: {}",
                error
            ))
        })?;
        
        Ok(logs.clone())
    }

    pub fn get_logs_by_service(
        &self,
        service_id: ServiceId,
    ) -> Result<Vec<LogEntry>, DeploymentError> {
        let logs = self.logs.read().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire read lock on logs: {}",
                error
            ))
        })?;
        
        let filtered_logs: Vec<LogEntry> = logs
            .iter()
            .filter(|log| log.service_id == service_id)
            .cloned()
            .collect();
        
        Ok(filtered_logs)
    }

    pub fn get_logs_by_instance(
        &self,
        instance_id: InstanceId,
    ) -> Result<Vec<LogEntry>, DeploymentError> {
        let logs = self.logs.read().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire read lock on logs: {}",
                error
            ))
        })?;
        
        let filtered_logs: Vec<LogEntry> = logs
            .iter()
            .filter(|log| log.instance_id == instance_id)
            .cloned()
            .collect();
        
        Ok(filtered_logs)
    }

    pub fn get_logs_by_time_range(
        &self,
        start_time: DateTime<Utc>,
        end_time: DateTime<Utc>,
    ) -> Result<Vec<LogEntry>, DeploymentError> {
        let logs = self.logs.read().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire read lock on logs: {}",
                error
            ))
        })?;
        
        let filtered_logs: Vec<LogEntry> = logs
            .iter()
            .filter(|log| {
                log.timestamp >= start_time && log.timestamp <= end_time
            })
            .cloned()
            .collect();
        
        Ok(filtered_logs)
    }

    pub fn count_logs(&self) -> Result<usize, DeploymentError> {
        let logs = self.logs.read().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire read lock on logs: {}",
                error
            ))
        })?;
        
        Ok(logs.len())
    }

    pub fn query_logs(
        &self,
        filter: LogFilter,
    ) -> Result<Vec<LogEntry>, DeploymentError> {
        let logs = self.logs.read().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire read lock on logs: {}",
                error
            ))
        })?;

        let filtered_logs: Vec<LogEntry> = logs
            .iter()
            .filter(|log| self.matches_filter(log, &filter))
            .cloned()
            .collect();

        Ok(filtered_logs)
    }

    fn matches_filter(&self, log: &LogEntry, filter: &LogFilter) -> bool {
        if !self.matches_time_range(log, &filter.time_range) {
            return false;
        }

        if !self.matches_service_id(log, &filter.service_id) {
            return false;
        }

        if !self.matches_instance_id(log, &filter.instance_id) {
            return false;
        }

        if !self.matches_log_level(log, &filter.level) {
            return false;
        }

        if !self.matches_search_text(log, &filter.search_text) {
            return false;
        }

        true
    }

    fn matches_time_range(
        &self,
        log: &LogEntry,
        time_range: &TimeRange,
    ) -> bool {
        log.timestamp >= time_range.start_time
            && log.timestamp <= time_range.end_time
    }

    fn matches_service_id(
        &self,
        log: &LogEntry,
        service_id: &Option<ServiceId>,
    ) -> bool {
        match service_id {
            Some(id) => log.service_id == *id,
            None => true,
        }
    }

    fn matches_instance_id(
        &self,
        log: &LogEntry,
        instance_id: &Option<InstanceId>,
    ) -> bool {
        match instance_id {
            Some(id) => log.instance_id == *id,
            None => true,
        }
    }

    fn matches_log_level(
        &self,
        log: &LogEntry,
        level: &Option<crate::deployment::types::LogLevel>,
    ) -> bool {
        match level {
            Some(filter_level) => log.level == *filter_level,
            None => true,
        }
    }

    fn matches_search_text(
        &self,
        log: &LogEntry,
        search_text: &Option<String>,
    ) -> bool {
        match search_text {
            Some(text) => {
                let lowercase_text = text.to_lowercase();
                let lowercase_message = log.message.to_lowercase();
                lowercase_message.contains(&lowercase_text)
            }
            None => true,
        }
    }

    pub fn cleanup_old_logs(
        &self,
        retention_days: u32,
    ) -> Result<usize, DeploymentError> {
        let cutoff_time = Utc::now() - chrono::Duration::days(retention_days as i64);
        
        let mut logs = self.logs.write().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire write lock on logs: {}",
                error
            ))
        })?;
        
        let initial_count = logs.len();
        logs.retain(|log| log.timestamp >= cutoff_time);
        let removed_count = initial_count - logs.len();
        
        let mut time_index = self.time_index.write().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire write lock on time index: {}",
                error
            ))
        })?;
        
        time_index.retain(|timestamp_key, _| {
            let timestamp = DateTime::from_timestamp(*timestamp_key, 0)
                .unwrap_or_else(|| Utc::now());
            timestamp >= cutoff_time
        });
        
        Ok(removed_count)
    }

    pub fn stream_logs(
        &self,
        filter: LogFilter,
    ) -> Result<LogStream, DeploymentError> {
        self.stream_manager.subscribe(filter)
    }

    pub fn record_deployment(
        &self,
        deployment_result: crate::deployment::types::DeploymentResult,
    ) -> Result<(), DeploymentError> {
        self.metrics_calculator.record_deployment(deployment_result)
    }

    pub fn get_deployment_metrics(
        &self,
        service_id: ServiceId,
        time_range: TimeRange,
    ) -> Result<DeploymentMetrics, DeploymentError> {
        self.metrics_calculator.calculate_metrics(service_id, time_range)
    }
}

impl Default for LogStorage {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::deployment::types::LogLevel;
    use std::collections::HashMap;
    use uuid::Uuid;

    fn create_test_log_entry(
        service_id: ServiceId,
        instance_id: InstanceId,
        level: LogLevel,
        message: &str,
        timestamp: DateTime<Utc>,
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

    #[test]
    fn test_ingest_log_stores_entry() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();
        
        let log_entry = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Test message",
            timestamp,
        );
        
        let result = storage.ingest_log(log_entry.clone());
        assert!(result.is_ok());
        
        let logs = storage.get_all_logs().unwrap();
        assert_eq!(logs.len(), 1);
        assert_eq!(logs[0].message, "Test message");
    }

    #[test]
    fn test_ingest_multiple_logs() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();
        
        for index in 0..5 {
            let log_entry = create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                &format!("Message {}", index),
                timestamp,
            );
            storage.ingest_log(log_entry).unwrap();
        }
        
        let logs = storage.get_all_logs().unwrap();
        assert_eq!(logs.len(), 5);
    }

    #[test]
    fn test_get_logs_by_service() {
        let storage = LogStorage::new();
        let service_id_1 = Uuid::new_v4();
        let service_id_2 = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();
        
        storage
            .ingest_log(create_test_log_entry(
                service_id_1,
                instance_id,
                LogLevel::Info,
                "Service 1 message",
                timestamp,
            ))
            .unwrap();
        
        storage
            .ingest_log(create_test_log_entry(
                service_id_2,
                instance_id,
                LogLevel::Info,
                "Service 2 message",
                timestamp,
            ))
            .unwrap();
        
        let logs = storage.get_logs_by_service(service_id_1).unwrap();
        assert_eq!(logs.len(), 1);
        assert_eq!(logs[0].message, "Service 1 message");
    }

    #[test]
    fn test_get_logs_by_instance() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id_1 = Uuid::new_v4();
        let instance_id_2 = Uuid::new_v4();
        let timestamp = Utc::now();
        
        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id_1,
                LogLevel::Info,
                "Instance 1 message",
                timestamp,
            ))
            .unwrap();
        
        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id_2,
                LogLevel::Info,
                "Instance 2 message",
                timestamp,
            ))
            .unwrap();
        
        let logs = storage.get_logs_by_instance(instance_id_1).unwrap();
        assert_eq!(logs.len(), 1);
        assert_eq!(logs[0].message, "Instance 1 message");
    }

    #[test]
    fn test_get_logs_by_time_range() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        
        let time_1 = Utc::now();
        let time_2 = time_1 + chrono::Duration::hours(1);
        let time_3 = time_2 + chrono::Duration::hours(1);
        
        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 1",
                time_1,
            ))
            .unwrap();
        
        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 2",
                time_2,
            ))
            .unwrap();
        
        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 3",
                time_3,
            ))
            .unwrap();
        
        let logs = storage
            .get_logs_by_time_range(
                time_1,
                time_2 + chrono::Duration::minutes(30),
            )
            .unwrap();
        
        assert_eq!(logs.len(), 2);
    }

    #[test]
    fn test_count_logs() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();
        
        assert_eq!(storage.count_logs().unwrap(), 0);
        
        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 1",
                timestamp,
            ))
            .unwrap();
        
        assert_eq!(storage.count_logs().unwrap(), 1);
        
        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 2",
                timestamp,
            ))
            .unwrap();
        
        assert_eq!(storage.count_logs().unwrap(), 2);
    }

    #[test]
    fn test_empty_storage_returns_empty_results() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        
        assert_eq!(storage.get_all_logs().unwrap().len(), 0);
        assert_eq!(storage.get_logs_by_service(service_id).unwrap().len(), 0);
        assert_eq!(
            storage.get_logs_by_instance(instance_id).unwrap().len(),
            0
        );
    }

    #[test]
    fn test_query_logs_with_service_id_filter() {
        let storage = LogStorage::new();
        let service_id_1 = Uuid::new_v4();
        let service_id_2 = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id_1,
                instance_id,
                LogLevel::Info,
                "Service 1 message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id_2,
                instance_id,
                LogLevel::Info,
                "Service 2 message",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: Some(service_id_1),
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 1);
        assert_eq!(logs[0].message, "Service 1 message");
    }

    #[test]
    fn test_query_logs_with_instance_id_filter() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id_1 = Uuid::new_v4();
        let instance_id_2 = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id_1,
                LogLevel::Info,
                "Instance 1 message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id_2,
                LogLevel::Info,
                "Instance 2 message",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: Some(instance_id_1),
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 1);
        assert_eq!(logs[0].message, "Instance 1 message");
    }

    #[test]
    fn test_query_logs_with_log_level_filter() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Info message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Error,
                "Error message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Warning,
                "Warning message",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: Some(LogLevel::Error),
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 1);
        assert_eq!(logs[0].message, "Error message");
    }

    #[test]
    fn test_query_logs_with_time_range_filter() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let time_1 = Utc::now();
        let time_2 = time_1 + chrono::Duration::hours(1);
        let time_3 = time_2 + chrono::Duration::hours(1);

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 1",
                time_1,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 2",
                time_2,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Message 3",
                time_3,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: time_1,
                end_time: time_2 + chrono::Duration::minutes(30),
            },
            search_text: None,
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 2);
    }

    #[test]
    fn test_query_logs_with_search_text_filter() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Deployment started successfully",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Error,
                "Deployment failed with error",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Health check passed",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: Some("deployment".to_string()),
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 2);
    }

    #[test]
    fn test_query_logs_with_case_insensitive_search() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "DEPLOYMENT STARTED",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: Some("deployment".to_string()),
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 1);
    }

    #[test]
    fn test_query_logs_with_multiple_filters() {
        let storage = LogStorage::new();
        let service_id_1 = Uuid::new_v4();
        let service_id_2 = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id_1,
                instance_id,
                LogLevel::Error,
                "Service 1 error message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id_1,
                instance_id,
                LogLevel::Info,
                "Service 1 info message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id_2,
                instance_id,
                LogLevel::Error,
                "Service 2 error message",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: Some(service_id_1),
            instance_id: None,
            level: Some(LogLevel::Error),
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: Some("error".to_string()),
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 1);
        assert_eq!(logs[0].message, "Service 1 error message");
    }

    #[test]
    fn test_query_logs_with_no_matches() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Test message",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: Some("nonexistent".to_string()),
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 0);
    }

    #[test]
    fn test_query_logs_with_empty_search_text() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Test message",
                timestamp,
            ))
            .unwrap();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: Some("".to_string()),
        };

        let logs = storage.query_logs(filter).unwrap();
        assert_eq!(logs.len(), 1);
    }

    #[test]
    fn test_cleanup_old_logs_removes_expired_logs() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let old_time = Utc::now() - chrono::Duration::days(35);
        let recent_time = Utc::now() - chrono::Duration::days(10);

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Old message",
                old_time,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Recent message",
                recent_time,
            ))
            .unwrap();

        assert_eq!(storage.count_logs().unwrap(), 2);

        let removed_count = storage.cleanup_old_logs(30).unwrap();
        assert_eq!(removed_count, 1);
        assert_eq!(storage.count_logs().unwrap(), 1);

        let logs = storage.get_all_logs().unwrap();
        assert_eq!(logs[0].message, "Recent message");
    }

    #[test]
    fn test_cleanup_old_logs_keeps_recent_logs() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let recent_time_1 = Utc::now() - chrono::Duration::days(10);
        let recent_time_2 = Utc::now() - chrono::Duration::days(5);

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Recent message 1",
                recent_time_1,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Recent message 2",
                recent_time_2,
            ))
            .unwrap();

        assert_eq!(storage.count_logs().unwrap(), 2);

        let removed_count = storage.cleanup_old_logs(30).unwrap();
        assert_eq!(removed_count, 0);
        assert_eq!(storage.count_logs().unwrap(), 2);
    }

    #[test]
    fn test_cleanup_old_logs_with_empty_storage() {
        let storage = LogStorage::new();

        let removed_count = storage.cleanup_old_logs(30).unwrap();
        assert_eq!(removed_count, 0);
        assert_eq!(storage.count_logs().unwrap(), 0);
    }

    #[test]
    fn test_cleanup_old_logs_removes_all_expired() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let old_time_1 = Utc::now() - chrono::Duration::days(40);
        let old_time_2 = Utc::now() - chrono::Duration::days(35);
        let old_time_3 = Utc::now() - chrono::Duration::days(31);

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Old message 1",
                old_time_1,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Old message 2",
                old_time_2,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Old message 3",
                old_time_3,
            ))
            .unwrap();

        assert_eq!(storage.count_logs().unwrap(), 3);

        let removed_count = storage.cleanup_old_logs(30).unwrap();
        assert_eq!(removed_count, 3);
        assert_eq!(storage.count_logs().unwrap(), 0);
    }

    #[test]
    fn test_cleanup_old_logs_with_boundary_timestamp() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let cutoff_time = Utc::now() - chrono::Duration::days(30);
        let just_before_cutoff = cutoff_time - chrono::Duration::hours(1);
        let just_after_cutoff = cutoff_time + chrono::Duration::hours(1);

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Before cutoff",
                just_before_cutoff,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "After cutoff",
                just_after_cutoff,
            ))
            .unwrap();

        assert_eq!(storage.count_logs().unwrap(), 2);

        let removed_count = storage.cleanup_old_logs(30).unwrap();
        assert_eq!(removed_count, 1);
        assert_eq!(storage.count_logs().unwrap(), 1);

        let logs = storage.get_all_logs().unwrap();
        assert_eq!(logs[0].message, "After cutoff");
    }

    #[tokio::test]
    async fn test_stream_logs_receives_new_entries() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let mut stream = storage.stream_logs(filter).unwrap();

        let log_entry = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Streamed message",
            timestamp,
        );

        storage.ingest_log(log_entry).unwrap();

        let received = stream.next().await;
        assert!(received.is_some());
        assert_eq!(received.unwrap().message, "Streamed message");
    }

    #[tokio::test]
    async fn test_stream_logs_filters_by_service_id() {
        let storage = LogStorage::new();
        let service_id_1 = Uuid::new_v4();
        let service_id_2 = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        let filter = crate::deployment::types::LogFilter {
            service_id: Some(service_id_1),
            instance_id: None,
            level: None,
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let mut stream = storage.stream_logs(filter).unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id_1,
                instance_id,
                LogLevel::Info,
                "Service 1 message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id_2,
                instance_id,
                LogLevel::Info,
                "Service 2 message",
                timestamp,
            ))
            .unwrap();

        let received = stream.next().await;
        assert!(received.is_some());
        assert_eq!(received.unwrap().message, "Service 1 message");
    }

    #[tokio::test]
    async fn test_stream_logs_filters_by_log_level() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let timestamp = Utc::now();

        let filter = crate::deployment::types::LogFilter {
            service_id: None,
            instance_id: None,
            level: Some(LogLevel::Error),
            time_range: crate::deployment::types::TimeRange {
                start_time: timestamp - chrono::Duration::hours(1),
                end_time: timestamp + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let mut stream = storage.stream_logs(filter).unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Info,
                "Info message",
                timestamp,
            ))
            .unwrap();

        storage
            .ingest_log(create_test_log_entry(
                service_id,
                instance_id,
                LogLevel::Error,
                "Error message",
                timestamp,
            ))
            .unwrap();

        let received = stream.next().await;
        assert!(received.is_some());
        assert_eq!(received.unwrap().message, "Error message");
    }

    #[test]
    fn test_get_deployment_metrics_with_no_deployments() {
        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let time_range = crate::deployment::types::TimeRange {
            start_time: Utc::now() - chrono::Duration::hours(24),
            end_time: Utc::now(),
        };

        let metrics = storage
            .get_deployment_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 0);
        assert_eq!(metrics.successful_deployments, 0);
        assert_eq!(metrics.failed_deployments, 0);
        assert_eq!(metrics.error_rate, 0.0);
    }

    #[test]
    fn test_record_and_get_deployment_metrics() {
        use crate::deployment::types::{DeploymentResult, DeploymentStatus};
        use std::time::Duration;

        let storage = LogStorage::new();
        let service_id = Uuid::new_v4();
        let time_range = crate::deployment::types::TimeRange {
            start_time: Utc::now() - chrono::Duration::hours(24),
            end_time: Utc::now(),
        };

        let deployment_1 = DeploymentResult {
            service_id,
            deployment_id: Uuid::new_v4(),
            instances: vec![],
            duration: Duration::from_secs(100),
            status: DeploymentStatus::Completed,
        };

        let deployment_2 = DeploymentResult {
            service_id,
            deployment_id: Uuid::new_v4(),
            instances: vec![],
            duration: Duration::from_secs(200),
            status: DeploymentStatus::Failed,
        };

        storage.record_deployment(deployment_1).unwrap();
        storage.record_deployment(deployment_2).unwrap();

        let metrics = storage
            .get_deployment_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 2);
        assert_eq!(metrics.successful_deployments, 1);
        assert_eq!(metrics.failed_deployments, 1);
        assert_eq!(metrics.average_duration.as_secs(), 150);
        assert_eq!(metrics.error_rate, 0.5);
    }
}
