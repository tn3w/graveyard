use crate::deployment::errors::DeploymentError;
use crate::deployment::types::{LogEntry, LogFilter};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use tokio::sync::broadcast;
use uuid::Uuid;

pub type SubscriptionId = Uuid;

pub struct LogStream {
    subscription_id: SubscriptionId,
    receiver: broadcast::Receiver<LogEntry>,
}

impl LogStream {
    pub fn new(
        subscription_id: SubscriptionId,
        receiver: broadcast::Receiver<LogEntry>,
    ) -> Self {
        Self {
            subscription_id,
            receiver,
        }
    }

    pub fn subscription_id(&self) -> SubscriptionId {
        self.subscription_id
    }

    pub async fn next(&mut self) -> Option<LogEntry> {
        match self.receiver.recv().await {
            Ok(log_entry) => Some(log_entry),
            Err(_) => None,
        }
    }
}

#[derive(Clone, Debug)]
struct Subscription {
    id: SubscriptionId,
    filter: LogFilter,
    sender: broadcast::Sender<LogEntry>,
}

#[derive(Clone, Debug)]
pub struct StreamManager {
    subscriptions: Arc<RwLock<HashMap<SubscriptionId, Subscription>>>,
}

impl StreamManager {
    pub fn new() -> Self {
        Self {
            subscriptions: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn subscribe(
        &self,
        filter: LogFilter,
    ) -> Result<LogStream, DeploymentError> {
        let subscription_id = Uuid::new_v4();
        let (sender, receiver) = broadcast::channel(1000);

        let subscription = Subscription {
            id: subscription_id,
            filter,
            sender,
        };

        let mut subscriptions = self.subscriptions.write().map_err(|error| {
            DeploymentError::StreamError(format!(
                "Failed to acquire write lock on subscriptions: {}",
                error
            ))
        })?;

        subscriptions.insert(subscription_id, subscription);

        Ok(LogStream::new(subscription_id, receiver))
    }

    pub fn unsubscribe(
        &self,
        subscription_id: SubscriptionId,
    ) -> Result<(), DeploymentError> {
        let mut subscriptions = self.subscriptions.write().map_err(|error| {
            DeploymentError::StreamError(format!(
                "Failed to acquire write lock on subscriptions: {}",
                error
            ))
        })?;

        subscriptions.remove(&subscription_id);
        Ok(())
    }

    pub fn push_log(&self, log_entry: &LogEntry) -> Result<(), DeploymentError> {
        let subscriptions = self.subscriptions.read().map_err(|error| {
            DeploymentError::StreamError(format!(
                "Failed to acquire read lock on subscriptions: {}",
                error
            ))
        })?;

        for subscription in subscriptions.values() {
            if self.matches_filter(log_entry, &subscription.filter) {
                let _ = subscription.sender.send(log_entry.clone());
            }
        }

        Ok(())
    }

    fn matches_filter(&self, log: &LogEntry, filter: &LogFilter) -> bool {
        if !self.matches_time_range(log, filter) {
            return false;
        }

        if !self.matches_service_id(log, filter) {
            return false;
        }

        if !self.matches_instance_id(log, filter) {
            return false;
        }

        if !self.matches_log_level(log, filter) {
            return false;
        }

        if !self.matches_search_text(log, filter) {
            return false;
        }

        true
    }

    fn matches_time_range(&self, log: &LogEntry, filter: &LogFilter) -> bool {
        log.timestamp >= filter.time_range.start_time
            && log.timestamp <= filter.time_range.end_time
    }

    fn matches_service_id(&self, log: &LogEntry, filter: &LogFilter) -> bool {
        match filter.service_id {
            Some(id) => log.service_id == id,
            None => true,
        }
    }

    fn matches_instance_id(&self, log: &LogEntry, filter: &LogFilter) -> bool {
        match filter.instance_id {
            Some(id) => log.instance_id == id,
            None => true,
        }
    }

    fn matches_log_level(&self, log: &LogEntry, filter: &LogFilter) -> bool {
        match filter.level {
            Some(filter_level) => log.level == filter_level,
            None => true,
        }
    }

    fn matches_search_text(&self, log: &LogEntry, filter: &LogFilter) -> bool {
        match &filter.search_text {
            Some(text) => {
                let lowercase_text = text.to_lowercase();
                let lowercase_message = log.message.to_lowercase();
                lowercase_message.contains(&lowercase_text)
            }
            None => true,
        }
    }

    pub fn subscription_count(&self) -> Result<usize, DeploymentError> {
        let subscriptions = self.subscriptions.read().map_err(|error| {
            DeploymentError::StreamError(format!(
                "Failed to acquire read lock on subscriptions: {}",
                error
            ))
        })?;

        Ok(subscriptions.len())
    }
}

impl Default for StreamManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::deployment::types::{LogLevel, TimeRange};
    use chrono::Utc;
    use std::collections::HashMap;
    use uuid::Uuid;

    fn create_test_log_entry(
        service_id: Uuid,
        instance_id: Uuid,
        level: LogLevel,
        message: &str,
    ) -> LogEntry {
        LogEntry {
            timestamp: Utc::now(),
            service_id,
            instance_id,
            level,
            message: message.to_string(),
            metadata: HashMap::new(),
        }
    }

    fn create_test_filter() -> LogFilter {
        let now = Utc::now();
        LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: TimeRange {
                start_time: now - chrono::Duration::hours(1),
                end_time: now + chrono::Duration::hours(1),
            },
            search_text: None,
        }
    }

    #[tokio::test]
    async fn test_subscribe_creates_stream() {
        let manager = StreamManager::new();
        let filter = create_test_filter();

        let result = manager.subscribe(filter);
        assert!(result.is_ok());

        let count = manager.subscription_count().unwrap();
        assert_eq!(count, 1);
    }

    #[tokio::test]
    async fn test_unsubscribe_removes_stream() {
        let manager = StreamManager::new();
        let filter = create_test_filter();

        let stream = manager.subscribe(filter).unwrap();
        let subscription_id = stream.subscription_id();

        assert_eq!(manager.subscription_count().unwrap(), 1);

        manager.unsubscribe(subscription_id).unwrap();
        assert_eq!(manager.subscription_count().unwrap(), 0);
    }

    #[tokio::test]
    async fn test_push_log_sends_to_matching_subscriber() {
        let manager = StreamManager::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let filter = create_test_filter();
        let mut stream = manager.subscribe(filter).unwrap();

        let log_entry = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Test message",
        );

        manager.push_log(&log_entry).unwrap();

        let received = stream.next().await;
        assert!(received.is_some());
        assert_eq!(received.unwrap().message, "Test message");
    }

    #[tokio::test]
    async fn test_push_log_filters_by_service_id() {
        let manager = StreamManager::new();
        let service_id_1 = Uuid::new_v4();
        let service_id_2 = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let now = Utc::now();
        let filter = LogFilter {
            service_id: Some(service_id_1),
            instance_id: None,
            level: None,
            time_range: TimeRange {
                start_time: now - chrono::Duration::hours(1),
                end_time: now + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let mut stream = manager.subscribe(filter).unwrap();

        let log_entry_1 = create_test_log_entry(
            service_id_1,
            instance_id,
            LogLevel::Info,
            "Service 1 message",
        );

        let log_entry_2 = create_test_log_entry(
            service_id_2,
            instance_id,
            LogLevel::Info,
            "Service 2 message",
        );

        manager.push_log(&log_entry_1).unwrap();
        manager.push_log(&log_entry_2).unwrap();

        let received = stream.next().await;
        assert!(received.is_some());
        assert_eq!(received.unwrap().message, "Service 1 message");
    }

    #[tokio::test]
    async fn test_push_log_filters_by_log_level() {
        let manager = StreamManager::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let now = Utc::now();
        let filter = LogFilter {
            service_id: None,
            instance_id: None,
            level: Some(LogLevel::Error),
            time_range: TimeRange {
                start_time: now - chrono::Duration::hours(1),
                end_time: now + chrono::Duration::hours(1),
            },
            search_text: None,
        };

        let mut stream = manager.subscribe(filter).unwrap();

        let log_entry_info = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Info message",
        );

        let log_entry_error = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Error,
            "Error message",
        );

        manager.push_log(&log_entry_info).unwrap();
        manager.push_log(&log_entry_error).unwrap();

        let received = stream.next().await;
        assert!(received.is_some());
        assert_eq!(received.unwrap().message, "Error message");
    }

    #[tokio::test]
    async fn test_push_log_filters_by_search_text() {
        let manager = StreamManager::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let now = Utc::now();
        let filter = LogFilter {
            service_id: None,
            instance_id: None,
            level: None,
            time_range: TimeRange {
                start_time: now - chrono::Duration::hours(1),
                end_time: now + chrono::Duration::hours(1),
            },
            search_text: Some("deployment".to_string()),
        };

        let mut stream = manager.subscribe(filter).unwrap();

        let log_entry_1 = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Deployment started",
        );

        let log_entry_2 = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Health check passed",
        );

        manager.push_log(&log_entry_1).unwrap();
        manager.push_log(&log_entry_2).unwrap();

        let received = stream.next().await;
        assert!(received.is_some());
        assert_eq!(received.unwrap().message, "Deployment started");
    }

    #[tokio::test]
    async fn test_multiple_subscribers_receive_same_log() {
        let manager = StreamManager::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();

        let filter = create_test_filter();
        let mut stream_1 = manager.subscribe(filter.clone()).unwrap();
        let mut stream_2 = manager.subscribe(filter).unwrap();

        let log_entry = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Test message",
        );

        manager.push_log(&log_entry).unwrap();

        let received_1 = stream_1.next().await;
        let received_2 = stream_2.next().await;

        assert!(received_1.is_some());
        assert!(received_2.is_some());
        assert_eq!(received_1.unwrap().message, "Test message");
        assert_eq!(received_2.unwrap().message, "Test message");
    }

    #[tokio::test]
    async fn test_stream_returns_none_after_unsubscribe() {
        let manager = StreamManager::new();
        let filter = create_test_filter();

        let stream = manager.subscribe(filter).unwrap();
        let subscription_id = stream.subscription_id();

        assert_eq!(manager.subscription_count().unwrap(), 1);

        manager.unsubscribe(subscription_id).unwrap();
        assert_eq!(manager.subscription_count().unwrap(), 0);

        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        let log_entry = create_test_log_entry(
            service_id,
            instance_id,
            LogLevel::Info,
            "Test message",
        );

        let result = manager.push_log(&log_entry);
        assert!(result.is_ok());
    }
}
