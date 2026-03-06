use crate::deployment::errors::LoadBalancerError;
use crate::deployment::types::{
    HealthStatus, InstanceId, ServiceId, ServiceInstance,
};
use std::sync::atomic::{AtomicUsize, Ordering};

pub struct InstancePool {
    pub service_id: ServiceId,
    instances: Vec<ServiceInstance>,
    round_robin_index: AtomicUsize,
}

impl InstancePool {
    pub fn new(service_id: ServiceId) -> Self {
        Self {
            service_id,
            instances: Vec::new(),
            round_robin_index: AtomicUsize::new(0),
        }
    }

    pub fn add_instance(
        &mut self,
        instance: ServiceInstance,
    ) -> Result<(), LoadBalancerError> {
        if self.instances.iter().any(|i| i.instance_id == instance.instance_id) {
            return Err(LoadBalancerError::PoolUpdateFailed(
                "Instance already exists in pool".to_string(),
            ));
        }
        self.instances.push(instance);
        Ok(())
    }

    pub fn remove_instance(
        &mut self,
        instance_id: InstanceId,
    ) -> Result<(), LoadBalancerError> {
        let initial_length = self.instances.len();
        self.instances.retain(|i| i.instance_id != instance_id);
        
        if self.instances.len() == initial_length {
            return Err(LoadBalancerError::InstanceNotFound);
        }
        
        if !self.instances.is_empty() {
            let current_index = self.round_robin_index.load(Ordering::Relaxed);
            if current_index >= self.instances.len() {
                self.round_robin_index.store(0, Ordering::Relaxed);
            }
        }
        
        Ok(())
    }

    pub fn update_instance_health(
        &mut self,
        instance_id: InstanceId,
        health_status: HealthStatus,
    ) -> Result<(), LoadBalancerError> {
        let instance = self
            .instances
            .iter_mut()
            .find(|i| i.instance_id == instance_id)
            .ok_or(LoadBalancerError::InstanceNotFound)?;
        
        instance.health_status = health_status;
        Ok(())
    }

    pub fn select_next_healthy_instance(&self) -> Option<&ServiceInstance> {
        let healthy_instances: Vec<&ServiceInstance> = self
            .instances
            .iter()
            .filter(|i| i.health_status == HealthStatus::Healthy)
            .collect();

        if healthy_instances.is_empty() {
            return None;
        }

        let index = self
            .round_robin_index
            .fetch_add(1, Ordering::Relaxed) % healthy_instances.len();
        
        Some(healthy_instances[index])
    }

    pub fn get_all_instances(&self) -> &[ServiceInstance] {
        &self.instances
    }

    pub fn get_healthy_instance_count(&self) -> usize {
        self.instances
            .iter()
            .filter(|i| i.health_status == HealthStatus::Healthy)
            .count()
    }

    pub fn has_healthy_instances(&self) -> bool {
        self.instances
            .iter()
            .any(|i| i.health_status == HealthStatus::Healthy)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::deployment::types::DeploymentSlot;
    use std::net::SocketAddr;
    use uuid::Uuid;

    fn create_test_instance(
        health_status: HealthStatus,
    ) -> ServiceInstance {
        ServiceInstance {
            instance_id: Uuid::new_v4(),
            address: "127.0.0.1:8080".parse::<SocketAddr>().unwrap(),
            health_status,
            slot: DeploymentSlot::Slot1,
        }
    }

    #[test]
    fn test_new_pool_is_empty() {
        let service_id = Uuid::new_v4();
        let pool = InstancePool::new(service_id);
        
        assert_eq!(pool.service_id, service_id);
        assert_eq!(pool.get_all_instances().len(), 0);
        assert!(!pool.has_healthy_instances());
    }

    #[test]
    fn test_add_instance_success() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        let instance = create_test_instance(HealthStatus::Healthy);
        
        let result = pool.add_instance(instance.clone());
        
        assert!(result.is_ok());
        assert_eq!(pool.get_all_instances().len(), 1);
        assert_eq!(pool.get_all_instances()[0].instance_id, instance.instance_id);
    }

    #[test]
    fn test_add_duplicate_instance_fails() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        let instance = create_test_instance(HealthStatus::Healthy);
        
        pool.add_instance(instance.clone()).unwrap();
        let result = pool.add_instance(instance);
        
        assert!(result.is_err());
        assert_eq!(pool.get_all_instances().len(), 1);
    }

    #[test]
    fn test_remove_instance_success() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        let instance = create_test_instance(HealthStatus::Healthy);
        let instance_id = instance.instance_id;
        
        pool.add_instance(instance).unwrap();
        let result = pool.remove_instance(instance_id);
        
        assert!(result.is_ok());
        assert_eq!(pool.get_all_instances().len(), 0);
    }

    #[test]
    fn test_remove_nonexistent_instance_fails() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        let nonexistent_id = Uuid::new_v4();
        
        let result = pool.remove_instance(nonexistent_id);
        
        assert!(result.is_err());
    }

    #[test]
    fn test_update_instance_health_success() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        let instance = create_test_instance(HealthStatus::Healthy);
        let instance_id = instance.instance_id;
        
        pool.add_instance(instance).unwrap();
        let result = pool.update_instance_health(
            instance_id,
            HealthStatus::Unhealthy,
        );
        
        assert!(result.is_ok());
        assert_eq!(
            pool.get_all_instances()[0].health_status,
            HealthStatus::Unhealthy
        );
    }

    #[test]
    fn test_update_nonexistent_instance_health_fails() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        let nonexistent_id = Uuid::new_v4();
        
        let result = pool.update_instance_health(
            nonexistent_id,
            HealthStatus::Unhealthy,
        );
        
        assert!(result.is_err());
    }

    #[test]
    fn test_select_next_healthy_instance_round_robin() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id2 = instance2.instance_id;
        let id3 = instance3.instance_id;
        
        pool.add_instance(instance1).unwrap();
        pool.add_instance(instance2).unwrap();
        pool.add_instance(instance3).unwrap();
        
        let selected1 = pool.select_next_healthy_instance().unwrap();
        let selected2 = pool.select_next_healthy_instance().unwrap();
        let selected3 = pool.select_next_healthy_instance().unwrap();
        let selected4 = pool.select_next_healthy_instance().unwrap();
        
        assert_eq!(selected1.instance_id, id1);
        assert_eq!(selected2.instance_id, id2);
        assert_eq!(selected3.instance_id, id3);
        assert_eq!(selected4.instance_id, id1);
    }

    #[test]
    fn test_select_next_healthy_instance_skips_unhealthy() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Unhealthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id3 = instance3.instance_id;
        
        pool.add_instance(instance1).unwrap();
        pool.add_instance(instance2).unwrap();
        pool.add_instance(instance3).unwrap();
        
        let selected1 = pool.select_next_healthy_instance().unwrap();
        let selected2 = pool.select_next_healthy_instance().unwrap();
        let selected3 = pool.select_next_healthy_instance().unwrap();
        
        assert_eq!(selected1.instance_id, id1);
        assert_eq!(selected2.instance_id, id3);
        assert_eq!(selected3.instance_id, id1);
    }

    #[test]
    fn test_select_next_healthy_instance_returns_none_when_no_healthy() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        
        let instance1 = create_test_instance(HealthStatus::Unhealthy);
        let instance2 = create_test_instance(HealthStatus::Unhealthy);
        
        pool.add_instance(instance1).unwrap();
        pool.add_instance(instance2).unwrap();
        
        let selected = pool.select_next_healthy_instance();
        
        assert!(selected.is_none());
    }

    #[test]
    fn test_get_healthy_instance_count() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        
        pool.add_instance(create_test_instance(HealthStatus::Healthy)).unwrap();
        pool.add_instance(create_test_instance(HealthStatus::Unhealthy)).unwrap();
        pool.add_instance(create_test_instance(HealthStatus::Healthy)).unwrap();
        pool.add_instance(create_test_instance(HealthStatus::Unknown)).unwrap();
        
        assert_eq!(pool.get_healthy_instance_count(), 2);
    }

    #[test]
    fn test_has_healthy_instances() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        
        assert!(!pool.has_healthy_instances());
        
        pool.add_instance(create_test_instance(HealthStatus::Unhealthy)).unwrap();
        assert!(!pool.has_healthy_instances());
        
        pool.add_instance(create_test_instance(HealthStatus::Healthy)).unwrap();
        assert!(pool.has_healthy_instances());
    }

    #[test]
    fn test_remove_instance_resets_index_when_out_of_bounds() {
        let service_id = Uuid::new_v4();
        let mut pool = InstancePool::new(service_id);
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id3 = instance3.instance_id;
        
        pool.add_instance(instance1).unwrap();
        pool.add_instance(instance2).unwrap();
        pool.add_instance(instance3).unwrap();
        
        pool.select_next_healthy_instance();
        pool.select_next_healthy_instance();
        pool.select_next_healthy_instance();
        
        pool.remove_instance(id3).unwrap();
        
        let index = pool.round_robin_index.load(Ordering::Relaxed);
        assert_eq!(index, 0);
    }
}
