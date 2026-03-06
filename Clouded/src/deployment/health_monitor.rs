use crate::deployment::errors::DeploymentError;
use crate::deployment::health_checker::HealthChecker;
use crate::deployment::types::{HealthStatus, InstanceId};
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::RwLock;
use tokio::time::interval;

const MAX_RESTART_ATTEMPTS: u32 = 3;

pub struct InstanceInfo {
    pub instance_id: InstanceId,
    pub address: String,
}

#[derive(Debug, Clone)]
struct RestartState {
    restart_attempts: u32,
    last_unhealthy_status: bool,
}

impl Default for RestartState {
    fn default() -> Self {
        Self {
            restart_attempts: 0,
            last_unhealthy_status: false,
        }
    }
}

pub trait InstanceRestarter: Send + Sync {
    fn restart_instance(
        &self,
        instance_id: InstanceId,
    ) -> Result<(), DeploymentError>;
}

pub struct HealthMonitor {
    health_checker: Arc<HealthChecker>,
    instances: Arc<RwLock<HashMap<InstanceId, String>>>,
    restart_states: Arc<RwLock<HashMap<InstanceId, RestartState>>>,
    instance_restarter: Option<Arc<dyn InstanceRestarter>>,
    check_interval: Duration,
}

impl HealthMonitor {
    pub fn new(
        health_checker: Arc<HealthChecker>,
        check_interval: Duration,
    ) -> Self {
        Self {
            health_checker,
            instances: Arc::new(RwLock::new(HashMap::new())),
            restart_states: Arc::new(RwLock::new(HashMap::new())),
            instance_restarter: None,
            check_interval,
        }
    }

    pub fn with_restarter(
        mut self,
        restarter: Arc<dyn InstanceRestarter>,
    ) -> Self {
        self.instance_restarter = Some(restarter);
        self
    }

    pub async fn register_instance(
        &self,
        instance_id: InstanceId,
        address: String,
    ) {
        let mut instances = self.instances.write().await;
        instances.insert(instance_id, address);
    }

    pub async fn unregister_instance(&self, instance_id: InstanceId) {
        let mut instances = self.instances.write().await;
        instances.remove(&instance_id);

        let mut restart_states = self.restart_states.write().await;
        restart_states.remove(&instance_id);
    }

    pub async fn get_all_health_statuses(
        &self,
    ) -> HashMap<InstanceId, HealthStatus> {
        let instances = self.instances.read().await;
        let mut statuses = HashMap::new();

        for instance_id in instances.keys() {
            let status = self.health_checker.get_health_status(*instance_id).await;
            statuses.insert(*instance_id, status);
        }

        statuses
    }

    pub async fn get_restart_attempts(&self, instance_id: InstanceId) -> u32 {
        let restart_states = self.restart_states.read().await;
        restart_states
            .get(&instance_id)
            .map(|state| state.restart_attempts)
            .unwrap_or(0)
    }

    async fn handle_unhealthy_instance(
        &self,
        instance_id: InstanceId,
    ) -> Result<(), DeploymentError> {
        let mut restart_states = self.restart_states.write().await;
        let state = restart_states.entry(instance_id).or_insert_with(Default::default);

        if !state.last_unhealthy_status {
            state.last_unhealthy_status = true;
            state.restart_attempts = 0;
        }

        if state.restart_attempts >= MAX_RESTART_ATTEMPTS {
            drop(restart_states);
            println!(
                "Instance {} failed after {} restart attempts, alerting user",
                instance_id, MAX_RESTART_ATTEMPTS
            );
            return Ok(());
        }

        state.restart_attempts += 1;
        let current_attempts = state.restart_attempts;
        drop(restart_states);

        if let Some(restarter) = &self.instance_restarter {
            println!(
                "Attempting to restart instance {} (attempt {}/{})",
                instance_id, current_attempts, MAX_RESTART_ATTEMPTS
            );

            match restarter.restart_instance(instance_id) {
                Ok(()) => {
                    println!("Successfully restarted instance {}", instance_id);
                    self.health_checker.reset_instance_state(instance_id).await;
                }
                Err(error) => {
                    eprintln!(
                        "Failed to restart instance {}: {}",
                        instance_id, error
                    );
                }
            }
        }

        Ok(())
    }

    async fn handle_healthy_instance(&self, instance_id: InstanceId) {
        let mut restart_states = self.restart_states.write().await;
        let state = restart_states.entry(instance_id).or_insert_with(Default::default);

        if state.last_unhealthy_status {
            println!("Instance {} recovered to healthy state", instance_id);
        }

        state.last_unhealthy_status = false;
        state.restart_attempts = 0;
    }

    pub async fn start(self) -> Result<(), DeploymentError> {
        let mut check_timer = interval(self.check_interval);

        loop {
            check_timer.tick().await;

            let instances_snapshot = {
                let instances = self.instances.read().await;
                instances.clone()
            };

            for (instance_id, address) in instances_snapshot {
                match self.health_checker.check_health(instance_id, &address).await {
                    Ok(status) => {
                        match status {
                            HealthStatus::Unhealthy => {
                                println!(
                                    "Instance {} is unhealthy at {}",
                                    instance_id, address
                                );
                                if let Err(error) = self.handle_unhealthy_instance(instance_id).await {
                                    eprintln!(
                                        "Error handling unhealthy instance {}: {}",
                                        instance_id, error
                                    );
                                }
                            }
                            HealthStatus::Healthy => {
                                self.handle_healthy_instance(instance_id).await;
                            }
                            HealthStatus::Unknown => {}
                        }
                    }
                    Err(error) => {
                        eprintln!(
                            "Health check failed for instance {}: {}",
                            instance_id, error
                        );
                    }
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
    use crate::deployment::health_checker::HealthCheckConfig;
    use std::sync::Mutex;
    use tokio::time::Duration as TokioDuration;
    use uuid::Uuid;

    struct MockRestarter {
        restart_calls: Arc<Mutex<Vec<InstanceId>>>,
        should_fail: bool,
    }

    impl MockRestarter {
        fn new() -> Self {
            Self {
                restart_calls: Arc::new(Mutex::new(Vec::new())),
                should_fail: false,
            }
        }

        fn with_failure() -> Self {
            Self {
                restart_calls: Arc::new(Mutex::new(Vec::new())),
                should_fail: true,
            }
        }

        fn get_restart_calls(&self) -> Vec<InstanceId> {
            self.restart_calls.lock().unwrap().clone()
        }
    }

    impl InstanceRestarter for MockRestarter {
        fn restart_instance(
            &self,
            instance_id: InstanceId,
        ) -> Result<(), DeploymentError> {
            self.restart_calls.lock().unwrap().push(instance_id);
            if self.should_fail {
                Err(DeploymentError::InstanceStartFailed(
                    "Mock restart failure".to_string(),
                ))
            } else {
                Ok(())
            }
        }
    }

    #[tokio::test]
    async fn test_register_and_unregister_instance() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let monitor = HealthMonitor::new(
            health_checker,
            TokioDuration::from_secs(10),
        );

        let instance_id = Uuid::new_v4();
        let address = "127.0.0.1:8080".to_string();

        monitor.register_instance(instance_id, address.clone()).await;

        let instances = monitor.instances.read().await;
        assert_eq!(instances.get(&instance_id), Some(&address));
        drop(instances);

        monitor.unregister_instance(instance_id).await;

        let instances = monitor.instances.read().await;
        assert_eq!(instances.get(&instance_id), None);
    }

    #[tokio::test]
    async fn test_get_all_health_statuses() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_secs(10),
        );

        let instance1 = Uuid::new_v4();
        let instance2 = Uuid::new_v4();

        monitor.register_instance(instance1, "127.0.0.1:8080".to_string()).await;
        monitor.register_instance(instance2, "127.0.0.1:8081".to_string()).await;

        let statuses = monitor.get_all_health_statuses().await;

        assert_eq!(statuses.len(), 2);
        assert_eq!(statuses.get(&instance1), Some(&HealthStatus::Unknown));
        assert_eq!(statuses.get(&instance2), Some(&HealthStatus::Unknown));
    }

    #[tokio::test]
    async fn test_monitor_runs_periodically() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_millis(100),
        );

        let instance_id = Uuid::new_v4();
        monitor.register_instance(instance_id, "127.0.0.1:8080".to_string()).await;

        let task_handle = tokio::spawn(async move {
            monitor.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(250)).await;

        task_handle.abort();

        let failures = health_checker.get_consecutive_failures(instance_id).await;
        assert!(failures >= 2);
    }

    #[tokio::test]
    async fn test_empty_instance_list() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let monitor = HealthMonitor::new(
            health_checker,
            TokioDuration::from_millis(100),
        );

        let statuses = monitor.get_all_health_statuses().await;
        assert_eq!(statuses.len(), 0);

        let task_handle = tokio::spawn(async move {
            monitor.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(200)).await;

        task_handle.abort();
    }

    #[tokio::test]
    async fn test_multiple_instances_monitored() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_millis(100),
        );

        let instance1 = Uuid::new_v4();
        let instance2 = Uuid::new_v4();
        let instance3 = Uuid::new_v4();

        monitor.register_instance(instance1, "127.0.0.1:8080".to_string()).await;
        monitor.register_instance(instance2, "127.0.0.1:8081".to_string()).await;
        monitor.register_instance(instance3, "127.0.0.1:8082".to_string()).await;

        let task_handle = tokio::spawn(async move {
            monitor.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(250)).await;

        task_handle.abort();

        let failures1 = health_checker.get_consecutive_failures(instance1).await;
        let failures2 = health_checker.get_consecutive_failures(instance2).await;
        let failures3 = health_checker.get_consecutive_failures(instance3).await;

        assert!(failures1 >= 2);
        assert!(failures2 >= 2);
        assert!(failures3 >= 2);
    }

    #[tokio::test]
    async fn test_automatic_restart_on_unhealthy() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let restarter = Arc::new(MockRestarter::new());
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_millis(100),
        )
        .with_restarter(restarter.clone());

        let instance_id = Uuid::new_v4();
        monitor.register_instance(instance_id, "127.0.0.1:8080".to_string()).await;

        let task_handle = tokio::spawn(async move {
            monitor.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(350)).await;

        task_handle.abort();

        let restart_calls = restarter.get_restart_calls();
        assert!(!restart_calls.is_empty());
        assert!(restart_calls.contains(&instance_id));
    }

    #[tokio::test]
    async fn test_restart_attempts_tracked() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let restarter = Arc::new(MockRestarter::new());
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_millis(100),
        )
        .with_restarter(restarter.clone());

        let instance_id = Uuid::new_v4();
        monitor.register_instance(instance_id, "127.0.0.1:8080".to_string()).await;

        let task_handle = tokio::spawn(async move {
            monitor.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(350)).await;

        task_handle.abort();

        let restart_calls = restarter.get_restart_calls();
        assert!(restart_calls.len() >= 1);
        assert!(restart_calls.len() <= MAX_RESTART_ATTEMPTS as usize);
    }

    #[tokio::test]
    async fn test_max_restart_attempts_limit() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let restarter = Arc::new(MockRestarter::with_failure());
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_millis(100),
        )
        .with_restarter(restarter.clone());

        let instance_id = Uuid::new_v4();
        monitor.register_instance(instance_id, "127.0.0.1:8080".to_string()).await;

        let task_handle = tokio::spawn(async move {
            monitor.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(500)).await;

        task_handle.abort();

        let restart_calls = restarter.get_restart_calls();
        assert_eq!(restart_calls.len(), MAX_RESTART_ATTEMPTS as usize);
    }

    #[tokio::test]
    async fn test_get_restart_attempts() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let restarter = Arc::new(MockRestarter::new());
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_millis(100),
        )
        .with_restarter(restarter.clone());

        let instance_id = Uuid::new_v4();
        monitor.register_instance(instance_id, "127.0.0.1:8080".to_string()).await;

        let initial_attempts = monitor.get_restart_attempts(instance_id).await;
        assert_eq!(initial_attempts, 0);

        let task_handle = tokio::spawn(async move {
            monitor.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(350)).await;

        task_handle.abort();
    }

    #[tokio::test]
    async fn test_unregister_clears_restart_state() {
        let health_checker = Arc::new(HealthChecker::new(
            HealthCheckConfig::default(),
        ));
        let restarter = Arc::new(MockRestarter::new());
        let monitor = HealthMonitor::new(
            health_checker.clone(),
            TokioDuration::from_millis(100),
        )
        .with_restarter(restarter.clone());

        let instance_id = Uuid::new_v4();
        monitor.register_instance(instance_id, "127.0.0.1:8080".to_string()).await;

        let task_handle = tokio::spawn(async move {
            let m = monitor;
            tokio::time::sleep(TokioDuration::from_millis(250)).await;
            m.unregister_instance(instance_id).await;
            let attempts = m.get_restart_attempts(instance_id).await;
            assert_eq!(attempts, 0);
            m.start().await
        });

        tokio::time::sleep(TokioDuration::from_millis(400)).await;

        task_handle.abort();
    }
}
