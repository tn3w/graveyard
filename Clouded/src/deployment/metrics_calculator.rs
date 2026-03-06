use crate::deployment::errors::DeploymentError;
use crate::deployment::types::{
    DeploymentMetrics, DeploymentResult, DeploymentStatus, ServiceId, TimeRange,
};
use std::sync::{Arc, RwLock};
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct MetricsCalculator {
    deployment_history: Arc<RwLock<Vec<DeploymentResult>>>,
}

impl MetricsCalculator {
    pub fn new() -> Self {
        Self {
            deployment_history: Arc::new(RwLock::new(Vec::new())),
        }
    }

    pub fn record_deployment(
        &self,
        deployment_result: DeploymentResult,
    ) -> Result<(), DeploymentError> {
        let mut history = self.deployment_history.write().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire write lock on deployment history: {}",
                error
            ))
        })?;

        history.push(deployment_result);
        Ok(())
    }

    pub fn calculate_metrics(
        &self,
        service_id: ServiceId,
        time_range: TimeRange,
    ) -> Result<DeploymentMetrics, DeploymentError> {
        let history = self.deployment_history.read().map_err(|error| {
            DeploymentError::LogStorageError(format!(
                "Failed to acquire read lock on deployment history: {}",
                error
            ))
        })?;

        let filtered_deployments: Vec<&DeploymentResult> = history
            .iter()
            .filter(|deployment| {
                self.matches_service_and_time(deployment, service_id, &time_range)
            })
            .collect();

        if filtered_deployments.is_empty() {
            return Ok(DeploymentMetrics {
                total_deployments: 0,
                successful_deployments: 0,
                failed_deployments: 0,
                average_duration: Duration::from_secs(0),
                error_rate: 0.0,
            });
        }

        let total_deployments = filtered_deployments.len() as u64;
        let successful_deployments = self.count_successful(&filtered_deployments);
        let failed_deployments = self.count_failed(&filtered_deployments);
        let average_duration = self.calculate_average_duration(&filtered_deployments);
        let error_rate = self.calculate_error_rate(
            failed_deployments,
            total_deployments,
        );

        Ok(DeploymentMetrics {
            total_deployments,
            successful_deployments,
            failed_deployments,
            average_duration,
            error_rate,
        })
    }

    fn matches_service_and_time(
        &self,
        deployment: &DeploymentResult,
        service_id: ServiceId,
        _time_range: &TimeRange,
    ) -> bool {
        deployment.service_id == service_id
    }

    fn count_successful(&self, deployments: &[&DeploymentResult]) -> u64 {
        deployments
            .iter()
            .filter(|deployment| deployment.status == DeploymentStatus::Completed)
            .count() as u64
    }

    fn count_failed(&self, deployments: &[&DeploymentResult]) -> u64 {
        deployments
            .iter()
            .filter(|deployment| {
                deployment.status == DeploymentStatus::Failed
                    || deployment.status == DeploymentStatus::RolledBack
            })
            .count() as u64
    }

    fn calculate_average_duration(
        &self,
        deployments: &[&DeploymentResult],
    ) -> Duration {
        if deployments.is_empty() {
            return Duration::from_secs(0);
        }

        let total_duration: Duration = deployments
            .iter()
            .map(|deployment| deployment.duration)
            .sum();

        total_duration / deployments.len() as u32
    }

    fn calculate_error_rate(
        &self,
        failed_count: u64,
        total_count: u64,
    ) -> f64 {
        if total_count == 0 {
            return 0.0;
        }

        (failed_count as f64) / (total_count as f64)
    }
}

impl Default for MetricsCalculator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    use uuid::Uuid;

    fn create_test_deployment(
        service_id: ServiceId,
        status: DeploymentStatus,
        duration_secs: u64,
    ) -> DeploymentResult {
        DeploymentResult {
            service_id,
            deployment_id: Uuid::new_v4(),
            instances: vec![],
            duration: Duration::from_secs(duration_secs),
            status,
        }
    }

    fn create_time_range() -> TimeRange {
        TimeRange {
            start_time: Utc::now() - chrono::Duration::hours(24),
            end_time: Utc::now(),
        }
    }

    #[test]
    fn test_calculate_metrics_with_no_deployments() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 0);
        assert_eq!(metrics.successful_deployments, 0);
        assert_eq!(metrics.failed_deployments, 0);
        assert_eq!(metrics.average_duration, Duration::from_secs(0));
        assert_eq!(metrics.error_rate, 0.0);
    }

    #[test]
    fn test_calculate_metrics_with_all_successful_deployments() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                100,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                200,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                300,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 3);
        assert_eq!(metrics.successful_deployments, 3);
        assert_eq!(metrics.failed_deployments, 0);
        assert_eq!(metrics.average_duration, Duration::from_secs(200));
        assert_eq!(metrics.error_rate, 0.0);
    }

    #[test]
    fn test_calculate_metrics_with_all_failed_deployments() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Failed,
                50,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Failed,
                75,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 2);
        assert_eq!(metrics.successful_deployments, 0);
        assert_eq!(metrics.failed_deployments, 2);
        assert_eq!(metrics.average_duration.as_secs(), 62);
        assert_eq!(metrics.error_rate, 1.0);
    }

    #[test]
    fn test_calculate_metrics_with_mixed_deployments() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                100,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Failed,
                50,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                150,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::RolledBack,
                75,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 4);
        assert_eq!(metrics.successful_deployments, 2);
        assert_eq!(metrics.failed_deployments, 2);
        assert_eq!(metrics.average_duration.as_secs(), 93);
        assert_eq!(metrics.error_rate, 0.5);
    }

    #[test]
    fn test_calculate_metrics_filters_by_service_id() {
        let calculator = MetricsCalculator::new();
        let service_id_1 = Uuid::new_v4();
        let service_id_2 = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id_1,
                DeploymentStatus::Completed,
                100,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id_2,
                DeploymentStatus::Completed,
                200,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id_1,
                DeploymentStatus::Failed,
                50,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id_1, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 2);
        assert_eq!(metrics.successful_deployments, 1);
        assert_eq!(metrics.failed_deployments, 1);
    }

    #[test]
    fn test_calculate_metrics_with_rolled_back_status() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::RolledBack,
                100,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 1);
        assert_eq!(metrics.successful_deployments, 0);
        assert_eq!(metrics.failed_deployments, 1);
        assert_eq!(metrics.error_rate, 1.0);
    }

    #[test]
    fn test_calculate_metrics_with_pending_and_building_statuses() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Pending,
                10,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Building,
                20,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                100,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.total_deployments, 3);
        assert_eq!(metrics.successful_deployments, 1);
        assert_eq!(metrics.failed_deployments, 0);
    }

    #[test]
    fn test_calculate_average_duration_with_single_deployment() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                150,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert_eq!(metrics.average_duration, Duration::from_secs(150));
    }

    #[test]
    fn test_error_rate_calculation_precision() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();
        let time_range = create_time_range();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                100,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Completed,
                100,
            ))
            .unwrap();

        calculator
            .record_deployment(create_test_deployment(
                service_id,
                DeploymentStatus::Failed,
                100,
            ))
            .unwrap();

        let metrics = calculator
            .calculate_metrics(service_id, time_range)
            .unwrap();

        assert!((metrics.error_rate - 0.333333).abs() < 0.001);
    }

    #[test]
    fn test_record_deployment_stores_result() {
        let calculator = MetricsCalculator::new();
        let service_id = Uuid::new_v4();

        let deployment = create_test_deployment(
            service_id,
            DeploymentStatus::Completed,
            100,
        );

        let result = calculator.record_deployment(deployment);
        assert!(result.is_ok());

        let history = calculator.deployment_history.read().unwrap();
        assert_eq!(history.len(), 1);
    }
}
