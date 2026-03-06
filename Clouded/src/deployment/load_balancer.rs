use crate::deployment::errors::LoadBalancerError;
use crate::deployment::instance_pool::InstancePool;
use crate::deployment::types::{
    HealthStatus, HttpRequest, HttpResponse, InstanceId, ServiceId,
    ServiceInstance,
};
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

pub struct LoadBalancer {
    instance_pools: Arc<RwLock<HashMap<ServiceId, InstancePool>>>,
}

impl LoadBalancer {
    pub fn new() -> Self {
        Self {
            instance_pools: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn add_instance(
        &self,
        service_id: ServiceId,
        instance: ServiceInstance,
    ) -> Result<(), LoadBalancerError> {
        let mut pools = self.instance_pools.write().unwrap();
        let pool = pools
            .entry(service_id)
            .or_insert_with(|| InstancePool::new(service_id));
        pool.add_instance(instance)
    }

    pub fn remove_instance(
        &self,
        service_id: ServiceId,
        instance_id: InstanceId,
    ) -> Result<(), LoadBalancerError> {
        let mut pools = self.instance_pools.write().unwrap();
        let pool = pools
            .get_mut(&service_id)
            .ok_or(LoadBalancerError::ServiceNotFound)?;
        pool.remove_instance(instance_id)
    }

    pub fn update_instance_health(
        &self,
        service_id: ServiceId,
        instance_id: InstanceId,
        health_status: HealthStatus,
    ) -> Result<(), LoadBalancerError> {
        let mut pools = self.instance_pools.write().unwrap();
        let pool = pools
            .get_mut(&service_id)
            .ok_or(LoadBalancerError::ServiceNotFound)?;
        pool.update_instance_health(instance_id, health_status)
    }

    pub fn select_instance(
        &self,
        service_id: ServiceId,
    ) -> Result<ServiceInstance, LoadBalancerError> {
        let pools = self.instance_pools.read().unwrap();
        let pool = pools
            .get(&service_id)
            .ok_or(LoadBalancerError::ServiceNotFound)?;
        
        pool.select_next_healthy_instance()
            .cloned()
            .ok_or(LoadBalancerError::NoHealthyInstances)
    }

    pub async fn route_request(
        &self,
        service_id: ServiceId,
        request: HttpRequest,
    ) -> Result<HttpResponse, LoadBalancerError> {
        let instance = self.select_instance(service_id)?;
        
        let response = self
            .forward_request_to_instance(&instance, request)
            .await?;
        
        Ok(response)
    }

    async fn forward_request_to_instance(
        &self,
        instance: &ServiceInstance,
        request: HttpRequest,
    ) -> Result<HttpResponse, LoadBalancerError> {
        let client = reqwest::Client::new();
        let url = format!(
            "http://{}{}",
            instance.address,
            request.path
        );
        
        let mut request_builder = match request.method.as_str() {
            "GET" => client.get(&url),
            "POST" => client.post(&url),
            "PUT" => client.put(&url),
            "DELETE" => client.delete(&url),
            "PATCH" => client.patch(&url),
            "HEAD" => client.head(&url),
            _ => {
                return Err(LoadBalancerError::RoutingFailed(
                    format!("Unsupported HTTP method: {}", request.method)
                ))
            }
        };
        
        for (key, value) in request.headers {
            request_builder = request_builder.header(key, value);
        }
        
        if let Some(body) = request.body {
            request_builder = request_builder.body(body);
        }
        
        let response = request_builder
            .send()
            .await
            .map_err(|error| {
                LoadBalancerError::RoutingFailed(
                    format!("Failed to forward request: {}", error)
                )
            })?;
        
        let status = response.status().as_u16();
        let mut headers = HashMap::new();
        
        for (key, value) in response.headers() {
            if let Ok(value_string) = value.to_str() {
                headers.insert(
                    key.as_str().to_string(),
                    value_string.to_string()
                );
            }
        }
        
        let body = response
            .bytes()
            .await
            .map_err(|error| {
                LoadBalancerError::RoutingFailed(
                    format!("Failed to read response body: {}", error)
                )
            })?
            .to_vec();
        
        Ok(HttpResponse {
            status,
            headers,
            body: Some(body),
        })
    }

    pub fn get_service_pool(
        &self,
        service_id: ServiceId,
    ) -> Result<Vec<ServiceInstance>, LoadBalancerError> {
        let pools = self.instance_pools.read().unwrap();
        let pool = pools
            .get(&service_id)
            .ok_or(LoadBalancerError::ServiceNotFound)?;
        Ok(pool.get_all_instances().to_vec())
    }

    pub fn has_healthy_instances(
        &self,
        service_id: ServiceId,
    ) -> Result<bool, LoadBalancerError> {
        let pools = self.instance_pools.read().unwrap();
        let pool = pools
            .get(&service_id)
            .ok_or(LoadBalancerError::ServiceNotFound)?;
        Ok(pool.has_healthy_instances())
    }
}

impl Default for LoadBalancer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::deployment::types::{DeploymentSlot, HttpRequest};
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
    fn test_new_load_balancer_has_no_pools() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let result = load_balancer.select_instance(service_id);
        
        assert!(matches!(result, Err(LoadBalancerError::ServiceNotFound)));
    }

    #[test]
    fn test_add_instance_creates_pool_if_not_exists() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        let instance = create_test_instance(HealthStatus::Healthy);
        
        let result = load_balancer.add_instance(service_id, instance);
        
        assert!(result.is_ok());
        assert!(load_balancer.has_healthy_instances(service_id).unwrap());
    }

    #[test]
    fn test_add_multiple_instances_to_same_service() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        
        let pool = load_balancer.get_service_pool(service_id).unwrap();
        assert_eq!(pool.len(), 2);
    }

    #[test]
    fn test_remove_instance_success() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        let instance = create_test_instance(HealthStatus::Healthy);
        let instance_id = instance.instance_id;
        
        load_balancer.add_instance(service_id, instance).unwrap();
        let result = load_balancer.remove_instance(service_id, instance_id);
        
        assert!(result.is_ok());
        let pool = load_balancer.get_service_pool(service_id).unwrap();
        assert_eq!(pool.len(), 0);
    }

    #[test]
    fn test_remove_instance_from_nonexistent_service_fails() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        let instance_id = Uuid::new_v4();
        
        let result = load_balancer.remove_instance(service_id, instance_id);
        
        assert!(matches!(result, Err(LoadBalancerError::ServiceNotFound)));
    }

    #[test]
    fn test_update_instance_health_success() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        let instance = create_test_instance(HealthStatus::Healthy);
        let instance_id = instance.instance_id;
        
        load_balancer.add_instance(service_id, instance).unwrap();
        let result = load_balancer.update_instance_health(
            service_id,
            instance_id,
            HealthStatus::Unhealthy,
        );
        
        assert!(result.is_ok());
        let pool = load_balancer.get_service_pool(service_id).unwrap();
        assert_eq!(pool[0].health_status, HealthStatus::Unhealthy);
    }

    #[test]
    fn test_select_instance_round_robin() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id2 = instance2.instance_id;
        let id3 = instance3.instance_id;
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        load_balancer.add_instance(service_id, instance3).unwrap();
        
        let selected1 = load_balancer.select_instance(service_id).unwrap();
        let selected2 = load_balancer.select_instance(service_id).unwrap();
        let selected3 = load_balancer.select_instance(service_id).unwrap();
        let selected4 = load_balancer.select_instance(service_id).unwrap();
        
        assert_eq!(selected1.instance_id, id1);
        assert_eq!(selected2.instance_id, id2);
        assert_eq!(selected3.instance_id, id3);
        assert_eq!(selected4.instance_id, id1);
    }

    #[test]
    fn test_select_instance_filters_unhealthy() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Unhealthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id3 = instance3.instance_id;
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        load_balancer.add_instance(service_id, instance3).unwrap();
        
        let selected1 = load_balancer.select_instance(service_id).unwrap();
        let selected2 = load_balancer.select_instance(service_id).unwrap();
        let selected3 = load_balancer.select_instance(service_id).unwrap();
        
        assert_eq!(selected1.instance_id, id1);
        assert_eq!(selected2.instance_id, id3);
        assert_eq!(selected3.instance_id, id1);
    }

    #[test]
    fn test_select_instance_no_healthy_instances() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Unhealthy);
        let instance2 = create_test_instance(HealthStatus::Unhealthy);
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        
        let result = load_balancer.select_instance(service_id);
        
        assert!(matches!(
            result,
            Err(LoadBalancerError::NoHealthyInstances)
        ));
    }

    #[test]
    fn test_has_healthy_instances() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Unhealthy);
        load_balancer.add_instance(service_id, instance1).unwrap();
        
        assert!(!load_balancer.has_healthy_instances(service_id).unwrap());
        
        let instance2 = create_test_instance(HealthStatus::Healthy);
        load_balancer.add_instance(service_id, instance2).unwrap();
        
        assert!(load_balancer.has_healthy_instances(service_id).unwrap());
    }

    #[test]
    fn test_get_service_pool_nonexistent_service() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let result = load_balancer.get_service_pool(service_id);
        
        assert!(matches!(result, Err(LoadBalancerError::ServiceNotFound)));
    }

    #[test]
    fn test_concurrent_access_to_pools() {
        use std::thread;
        
        let load_balancer = Arc::new(LoadBalancer::new());
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        
        let mut handles = vec![];
        
        for _ in 0..10 {
            let lb = Arc::clone(&load_balancer);
            let handle = thread::spawn(move || {
                for _ in 0..100 {
                    let _ = lb.select_instance(service_id);
                }
            });
            handles.push(handle);
        }
        
        for handle in handles {
            handle.join().unwrap();
        }
        
        assert!(load_balancer.has_healthy_instances(service_id).unwrap());
    }

    #[test]
    fn test_health_transition_removes_instance_from_rotation() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id2 = instance2.instance_id;
        let id3 = instance3.instance_id;
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        load_balancer.add_instance(service_id, instance3).unwrap();
        
        let selected1 = load_balancer.select_instance(service_id).unwrap();
        assert_eq!(selected1.instance_id, id1);
        
        load_balancer.update_instance_health(
            service_id,
            id2,
            HealthStatus::Unhealthy,
        ).unwrap();
        
        let selected2 = load_balancer.select_instance(service_id).unwrap();
        let selected3 = load_balancer.select_instance(service_id).unwrap();
        let selected4 = load_balancer.select_instance(service_id).unwrap();
        
        assert_eq!(selected2.instance_id, id3);
        assert_eq!(selected3.instance_id, id1);
        assert_eq!(selected4.instance_id, id3);
    }

    #[test]
    fn test_health_transition_adds_instance_back_to_rotation() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Unhealthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id2 = instance2.instance_id;
        let id3 = instance3.instance_id;
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        load_balancer.add_instance(service_id, instance3).unwrap();
        
        let selected1 = load_balancer.select_instance(service_id).unwrap();
        let selected2 = load_balancer.select_instance(service_id).unwrap();
        
        assert_eq!(selected1.instance_id, id1);
        assert_eq!(selected2.instance_id, id3);
        
        load_balancer.update_instance_health(
            service_id,
            id2,
            HealthStatus::Healthy,
        ).unwrap();
        
        let mut selected_ids = vec![];
        for _ in 0..6 {
            let selected = load_balancer.select_instance(service_id).unwrap();
            selected_ids.push(selected.instance_id);
        }
        
        assert!(selected_ids.contains(&id1));
        assert!(selected_ids.contains(&id2));
        assert!(selected_ids.contains(&id3));
        
        let id1_count = selected_ids.iter().filter(|&&id| id == id1).count();
        let id2_count = selected_ids.iter().filter(|&&id| id == id2).count();
        let id3_count = selected_ids.iter().filter(|&&id| id == id3).count();
        
        assert_eq!(id1_count, 2);
        assert_eq!(id2_count, 2);
        assert_eq!(id3_count, 2);
    }

    #[test]
    fn test_multiple_health_transitions_affect_routing() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id2 = instance2.instance_id;
        let id3 = instance3.instance_id;
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        load_balancer.add_instance(service_id, instance3).unwrap();
        
        load_balancer.update_instance_health(
            service_id,
            id1,
            HealthStatus::Unhealthy,
        ).unwrap();
        load_balancer.update_instance_health(
            service_id,
            id3,
            HealthStatus::Unhealthy,
        ).unwrap();
        
        let selected1 = load_balancer.select_instance(service_id).unwrap();
        let selected2 = load_balancer.select_instance(service_id).unwrap();
        
        assert_eq!(selected1.instance_id, id2);
        assert_eq!(selected2.instance_id, id2);
        
        load_balancer.update_instance_health(
            service_id,
            id1,
            HealthStatus::Healthy,
        ).unwrap();
        
        let mut selected_ids = vec![];
        for _ in 0..4 {
            let selected = load_balancer.select_instance(service_id).unwrap();
            selected_ids.push(selected.instance_id);
        }
        
        assert!(selected_ids.contains(&id1));
        assert!(selected_ids.contains(&id2));
        assert!(!selected_ids.contains(&id3));
        
        let id1_count = selected_ids.iter().filter(|&&id| id == id1).count();
        let id2_count = selected_ids.iter().filter(|&&id| id == id2).count();
        
        assert_eq!(id1_count, 2);
        assert_eq!(id2_count, 2);
    }

    #[test]
    fn test_all_instances_become_unhealthy_then_recover() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id2 = instance2.instance_id;
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        
        load_balancer.update_instance_health(
            service_id,
            id1,
            HealthStatus::Unhealthy,
        ).unwrap();
        load_balancer.update_instance_health(
            service_id,
            id2,
            HealthStatus::Unhealthy,
        ).unwrap();
        
        let result = load_balancer.select_instance(service_id);
        assert!(matches!(
            result,
            Err(LoadBalancerError::NoHealthyInstances)
        ));
        
        load_balancer.update_instance_health(
            service_id,
            id1,
            HealthStatus::Healthy,
        ).unwrap();
        
        let selected = load_balancer.select_instance(service_id).unwrap();
        assert_eq!(selected.instance_id, id1);
    }

    #[test]
    fn test_dynamic_pool_updates_comprehensive() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Healthy);
        let instance2 = create_test_instance(HealthStatus::Healthy);
        let instance3 = create_test_instance(HealthStatus::Healthy);
        let instance4 = create_test_instance(HealthStatus::Healthy);
        
        let id1 = instance1.instance_id;
        let id2 = instance2.instance_id;
        let id3 = instance3.instance_id;
        let id4 = instance4.instance_id;
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        load_balancer.add_instance(service_id, instance3).unwrap();
        load_balancer.add_instance(service_id, instance4).unwrap();
        
        assert!(load_balancer.has_healthy_instances(service_id).unwrap());
        
        load_balancer.update_instance_health(
            service_id,
            id2,
            HealthStatus::Unhealthy,
        ).unwrap();
        load_balancer.update_instance_health(
            service_id,
            id4,
            HealthStatus::Unhealthy,
        ).unwrap();
        
        let mut selected_ids = vec![];
        for _ in 0..4 {
            let selected = load_balancer.select_instance(service_id).unwrap();
            selected_ids.push(selected.instance_id);
        }
        
        assert!(selected_ids.contains(&id1));
        assert!(!selected_ids.contains(&id2));
        assert!(selected_ids.contains(&id3));
        assert!(!selected_ids.contains(&id4));
        
        load_balancer.update_instance_health(
            service_id,
            id2,
            HealthStatus::Healthy,
        ).unwrap();
        
        selected_ids.clear();
        for _ in 0..6 {
            let selected = load_balancer.select_instance(service_id).unwrap();
            selected_ids.push(selected.instance_id);
        }
        
        assert!(selected_ids.contains(&id1));
        assert!(selected_ids.contains(&id2));
        assert!(selected_ids.contains(&id3));
        assert!(!selected_ids.contains(&id4));
        
        load_balancer.update_instance_health(
            service_id,
            id1,
            HealthStatus::Unhealthy,
        ).unwrap();
        load_balancer.update_instance_health(
            service_id,
            id3,
            HealthStatus::Unhealthy,
        ).unwrap();
        
        selected_ids.clear();
        for _ in 0..3 {
            let selected = load_balancer.select_instance(service_id).unwrap();
            selected_ids.push(selected.instance_id);
        }
        
        assert!(!selected_ids.contains(&id1));
        assert!(selected_ids.contains(&id2));
        assert!(!selected_ids.contains(&id3));
        assert!(!selected_ids.contains(&id4));
        
        load_balancer.update_instance_health(
            service_id,
            id1,
            HealthStatus::Healthy,
        ).unwrap();
        load_balancer.update_instance_health(
            service_id,
            id3,
            HealthStatus::Healthy,
        ).unwrap();
        load_balancer.update_instance_health(
            service_id,
            id4,
            HealthStatus::Healthy,
        ).unwrap();
        
        selected_ids.clear();
        for _ in 0..8 {
            let selected = load_balancer.select_instance(service_id).unwrap();
            selected_ids.push(selected.instance_id);
        }
        
        assert!(selected_ids.contains(&id1));
        assert!(selected_ids.contains(&id2));
        assert!(selected_ids.contains(&id3));
        assert!(selected_ids.contains(&id4));
        
        let id1_count = selected_ids.iter().filter(|&&id| id == id1).count();
        let id2_count = selected_ids.iter().filter(|&&id| id == id2).count();
        let id3_count = selected_ids.iter().filter(|&&id| id == id3).count();
        let id4_count = selected_ids.iter().filter(|&&id| id == id4).count();
        
        assert_eq!(id1_count, 2);
        assert_eq!(id2_count, 2);
        assert_eq!(id3_count, 2);
        assert_eq!(id4_count, 2);
    }

    #[tokio::test]
    async fn test_route_request_no_healthy_instances_returns_error() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let instance1 = create_test_instance(HealthStatus::Unhealthy);
        let instance2 = create_test_instance(HealthStatus::Unhealthy);
        
        load_balancer.add_instance(service_id, instance1).unwrap();
        load_balancer.add_instance(service_id, instance2).unwrap();
        
        let request = HttpRequest {
            method: "GET".to_string(),
            path: "/test".to_string(),
            headers: HashMap::new(),
            body: None,
        };
        
        let result = load_balancer.route_request(service_id, request).await;
        
        assert!(matches!(
            result,
            Err(LoadBalancerError::NoHealthyInstances)
        ));
    }

    #[tokio::test]
    async fn test_route_request_service_not_found() {
        let load_balancer = LoadBalancer::new();
        let service_id = Uuid::new_v4();
        
        let request = HttpRequest {
            method: "GET".to_string(),
            path: "/test".to_string(),
            headers: HashMap::new(),
            body: None,
        };
        
        let result = load_balancer.route_request(service_id, request).await;
        
        assert!(matches!(
            result,
            Err(LoadBalancerError::ServiceNotFound)
        ));
    }
}
