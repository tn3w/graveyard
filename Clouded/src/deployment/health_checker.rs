use crate::deployment::errors::DeploymentError;
use crate::deployment::types::{HealthStatus, InstanceId};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;

const CONSECUTIVE_FAILURE_THRESHOLD: u32 = 3;
const HEALTH_CHECK_TIMEOUT: Duration = Duration::from_secs(5);

#[derive(Debug, Clone)]
pub struct HealthCheckConfig {
    pub endpoint: String,
    pub timeout: Duration,
    pub failure_threshold: u32,
}

impl Default for HealthCheckConfig {
    fn default() -> Self {
        Self {
            endpoint: "/health".to_string(),
            timeout: HEALTH_CHECK_TIMEOUT,
            failure_threshold: CONSECUTIVE_FAILURE_THRESHOLD,
        }
    }
}

#[derive(Debug)]
struct InstanceHealthState {
    consecutive_failures: u32,
    current_status: HealthStatus,
}

impl Default for InstanceHealthState {
    fn default() -> Self {
        Self {
            consecutive_failures: 0,
            current_status: HealthStatus::Unknown,
        }
    }
}

pub struct HealthChecker {
    client: reqwest::Client,
    instance_states: Arc<RwLock<HashMap<InstanceId, InstanceHealthState>>>,
    config: HealthCheckConfig,
}

impl HealthChecker {
    pub fn new(config: HealthCheckConfig) -> Self {
        let client = reqwest::Client::builder()
            .timeout(config.timeout)
            .build()
            .expect("Failed to create HTTP client");

        Self {
            client,
            instance_states: Arc::new(RwLock::new(HashMap::new())),
            config,
        }
    }

    pub async fn check_health(
        &self,
        instance_id: InstanceId,
        instance_address: &str,
    ) -> Result<HealthStatus, DeploymentError> {
        let health_url = format!("http://{}{}", instance_address, self.config.endpoint);

        let check_result = self.perform_health_check(&health_url).await;

        let new_status = self.update_instance_state(instance_id, check_result).await;

        Ok(new_status)
    }

    async fn perform_health_check(&self, url: &str) -> bool {
        match self.client.get(url).send().await {
            Ok(response) => response.status().is_success(),
            Err(_) => false,
        }
    }

    async fn update_instance_state(
        &self,
        instance_id: InstanceId,
        check_passed: bool,
    ) -> HealthStatus {
        let mut states = self.instance_states.write().await;
        let state = states.entry(instance_id).or_insert_with(Default::default);

        if check_passed {
            state.consecutive_failures = 0;
            state.current_status = HealthStatus::Healthy;
        } else {
            state.consecutive_failures += 1;

            if state.consecutive_failures >= self.config.failure_threshold {
                state.current_status = HealthStatus::Unhealthy;
            }
        }

        state.current_status
    }

    pub async fn get_health_status(
        &self,
        instance_id: InstanceId,
    ) -> HealthStatus {
        let states = self.instance_states.read().await;
        states
            .get(&instance_id)
            .map(|state| state.current_status)
            .unwrap_or(HealthStatus::Unknown)
    }

    pub async fn get_consecutive_failures(
        &self,
        instance_id: InstanceId,
    ) -> u32 {
        let states = self.instance_states.read().await;
        states
            .get(&instance_id)
            .map(|state| state.consecutive_failures)
            .unwrap_or(0)
    }

    pub async fn reset_instance_state(&self, instance_id: InstanceId) {
        let mut states = self.instance_states.write().await;
        states.remove(&instance_id);
    }

    pub async fn check_multiple_instances(
        &self,
        instances: &[(InstanceId, String)],
    ) -> Result<HashMap<InstanceId, HealthStatus>, DeploymentError> {
        let mut results = HashMap::new();

        for (instance_id, address) in instances {
            let status = self.check_health(*instance_id, address).await?;
            results.insert(*instance_id, status);
        }

        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;

    #[tokio::test]
    async fn test_initial_status_is_unknown() {
        let checker = HealthChecker::new(HealthCheckConfig::default());
        let instance_id = Uuid::new_v4();

        let status = checker.get_health_status(instance_id).await;

        assert_eq!(status, HealthStatus::Unknown);
    }

    #[tokio::test]
    async fn test_consecutive_failures_tracked() {
        let checker = HealthChecker::new(HealthCheckConfig::default());
        let instance_id = Uuid::new_v4();

        checker.update_instance_state(instance_id, false).await;
        assert_eq!(checker.get_consecutive_failures(instance_id).await, 1);

        checker.update_instance_state(instance_id, false).await;
        assert_eq!(checker.get_consecutive_failures(instance_id).await, 2);

        checker.update_instance_state(instance_id, false).await;
        assert_eq!(checker.get_consecutive_failures(instance_id).await, 3);
    }

    #[tokio::test]
    async fn test_status_transitions_to_unhealthy_after_threshold() {
        let checker = HealthChecker::new(HealthCheckConfig::default());
        let instance_id = Uuid::new_v4();

        let status1 = checker.update_instance_state(instance_id, false).await;
        assert_eq!(status1, HealthStatus::Unknown);

        let status2 = checker.update_instance_state(instance_id, false).await;
        assert_eq!(status2, HealthStatus::Unknown);

        let status3 = checker.update_instance_state(instance_id, false).await;
        assert_eq!(status3, HealthStatus::Unhealthy);
    }

    #[tokio::test]
    async fn test_successful_check_resets_failures() {
        let checker = HealthChecker::new(HealthCheckConfig::default());
        let instance_id = Uuid::new_v4();

        checker.update_instance_state(instance_id, false).await;
        checker.update_instance_state(instance_id, false).await;
        assert_eq!(checker.get_consecutive_failures(instance_id).await, 2);

        let status = checker.update_instance_state(instance_id, true).await;
        assert_eq!(status, HealthStatus::Healthy);
        assert_eq!(checker.get_consecutive_failures(instance_id).await, 0);
    }

    #[tokio::test]
    async fn test_status_transitions_to_healthy() {
        let checker = HealthChecker::new(HealthCheckConfig::default());
        let instance_id = Uuid::new_v4();

        let status = checker.update_instance_state(instance_id, true).await;
        assert_eq!(status, HealthStatus::Healthy);
    }

    #[tokio::test]
    async fn test_reset_instance_state() {
        let checker = HealthChecker::new(HealthCheckConfig::default());
        let instance_id = Uuid::new_v4();

        checker.update_instance_state(instance_id, false).await;
        checker.update_instance_state(instance_id, false).await;
        assert_eq!(checker.get_consecutive_failures(instance_id).await, 2);

        checker.reset_instance_state(instance_id).await;
        assert_eq!(checker.get_health_status(instance_id).await, HealthStatus::Unknown);
        assert_eq!(checker.get_consecutive_failures(instance_id).await, 0);
    }

    #[tokio::test]
    async fn test_custom_failure_threshold() {
        let config = HealthCheckConfig {
            endpoint: "/health".to_string(),
            timeout: Duration::from_secs(5),
            failure_threshold: 5,
        };
        let checker = HealthChecker::new(config);
        let instance_id = Uuid::new_v4();

        for _ in 0..4 {
            let status = checker.update_instance_state(instance_id, false).await;
            assert_eq!(status, HealthStatus::Unknown);
        }

        let status = checker.update_instance_state(instance_id, false).await;
        assert_eq!(status, HealthStatus::Unhealthy);
    }
}
