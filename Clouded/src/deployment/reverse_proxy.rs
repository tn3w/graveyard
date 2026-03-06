use crate::deployment::domain_mapping_manager::DomainMappingManager;
use crate::deployment::errors::ProxyError;
use crate::deployment::load_balancer::LoadBalancer;
use crate::deployment::types::{HttpRequest, HttpResponse, ServiceId};
use std::sync::Arc;

pub struct ReverseProxy {
    domain_mapping_manager: Arc<DomainMappingManager>,
    load_balancer: Arc<LoadBalancer>,
}

impl ReverseProxy {
    pub fn new(
        domain_mapping_manager: Arc<DomainMappingManager>,
        load_balancer: Arc<LoadBalancer>,
    ) -> Self {
        Self {
            domain_mapping_manager,
            load_balancer,
        }
    }

    pub async fn handle_request(
        &self,
        request: HttpRequest,
        host: &str,
    ) -> Result<HttpResponse, ProxyError> {
        let service_id = self.resolve_service(host)?;
        
        self.load_balancer
            .route_request(service_id, request)
            .await
            .map_err(|error| {
                ProxyError::RoutingFailed(format!(
                    "Failed to route request: {}",
                    error
                ))
            })
    }

    pub fn resolve_service(&self, host: &str) -> Result<ServiceId, ProxyError> {
        let normalized_host = self.normalize_host(host);
        
        self.domain_mapping_manager
            .get_service_for_domain(&normalized_host)
            .ok_or(ProxyError::ServiceNotFound)
    }

    fn normalize_host(&self, host: &str) -> String {
        host.split(':')
            .next()
            .unwrap_or(host)
            .to_lowercase()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::deployment::domain_mapping_manager::{
        DomainMappingManager, ServiceValidator,
    };
    use crate::deployment::types::{
        DeploymentSlot, HealthStatus, ServiceInstance,
    };
    use std::collections::HashMap;
    use std::net::SocketAddr;
    use uuid::Uuid;

    struct MockServiceValidator {
        valid_services: Vec<ServiceId>,
    }

    impl ServiceValidator for MockServiceValidator {
        fn service_exists(&self, service_id: ServiceId) -> bool {
            self.valid_services.contains(&service_id)
        }
    }

    fn create_test_proxy(
        services: Vec<ServiceId>,
    ) -> (ReverseProxy, Vec<ServiceId>) {
        let validator = Arc::new(MockServiceValidator {
            valid_services: services.clone(),
        });
        let domain_manager = Arc::new(DomainMappingManager::new(validator));
        let load_balancer = Arc::new(LoadBalancer::new());

        let proxy = ReverseProxy::new(domain_manager, load_balancer);
        (proxy, services)
    }

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
    fn test_resolve_service_success() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("example.com");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_resolve_service_not_found() {
        let (proxy, _) = create_test_proxy(vec![]);

        let result = proxy.resolve_service("example.com");

        assert!(matches!(result, Err(ProxyError::ServiceNotFound)));
    }

    #[test]
    fn test_resolve_service_with_port() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("example.com:8080");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_resolve_service_case_insensitive() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("EXAMPLE.COM");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_resolve_service_mixed_case() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("ExAmPlE.CoM");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_resolve_service_subdomain() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("api.example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("api.example.com");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_resolve_service_multiple_mappings() {
        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id1, service_id2]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();
        proxy
            .domain_mapping_manager
            .add_domain_mapping("test.com".to_string(), service_id2)
            .unwrap();

        let result1 = proxy.resolve_service("example.com");
        let result2 = proxy.resolve_service("test.com");

        assert_eq!(result1.unwrap(), service_id1);
        assert_eq!(result2.unwrap(), service_id2);
    }

    #[test]
    fn test_normalize_host_removes_port() {
        let (proxy, _) = create_test_proxy(vec![]);

        let normalized = proxy.normalize_host("example.com:8080");

        assert_eq!(normalized, "example.com");
    }

    #[test]
    fn test_normalize_host_lowercase() {
        let (proxy, _) = create_test_proxy(vec![]);

        let normalized = proxy.normalize_host("EXAMPLE.COM");

        assert_eq!(normalized, "example.com");
    }

    #[test]
    fn test_normalize_host_no_port() {
        let (proxy, _) = create_test_proxy(vec![]);

        let normalized = proxy.normalize_host("example.com");

        assert_eq!(normalized, "example.com");
    }

    #[test]
    fn test_normalize_host_https_port() {
        let (proxy, _) = create_test_proxy(vec![]);

        let normalized = proxy.normalize_host("example.com:443");

        assert_eq!(normalized, "example.com");
    }

    #[test]
    fn test_normalize_host_http_port() {
        let (proxy, _) = create_test_proxy(vec![]);

        let normalized = proxy.normalize_host("example.com:80");

        assert_eq!(normalized, "example.com");
    }

    #[tokio::test]
    async fn test_handle_request_service_not_found() {
        let (proxy, _) = create_test_proxy(vec![]);

        let request = HttpRequest {
            method: "GET".to_string(),
            path: "/test".to_string(),
            headers: HashMap::new(),
            body: None,
        };

        let result = proxy.handle_request(request, "example.com").await;

        assert!(matches!(result, Err(ProxyError::ServiceNotFound)));
    }

    #[tokio::test]
    async fn test_handle_request_no_healthy_instances() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let instance = create_test_instance(HealthStatus::Unhealthy);
        proxy
            .load_balancer
            .add_instance(service_id, instance)
            .unwrap();

        let request = HttpRequest {
            method: "GET".to_string(),
            path: "/test".to_string(),
            headers: HashMap::new(),
            body: None,
        };

        let result = proxy.handle_request(request, "example.com").await;

        assert!(matches!(result, Err(ProxyError::RoutingFailed(_))));
    }

    #[test]
    fn test_resolve_service_supports_http_protocol() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("example.com:80");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_resolve_service_supports_https_protocol() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("example.com:443");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_resolve_service_different_subdomains() {
        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let service_id3 = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(
            vec![service_id1, service_id2, service_id3]
        );

        proxy
            .domain_mapping_manager
            .add_domain_mapping("api.example.com".to_string(), service_id1)
            .unwrap();
        proxy
            .domain_mapping_manager
            .add_domain_mapping("web.example.com".to_string(), service_id2)
            .unwrap();
        proxy
            .domain_mapping_manager
            .add_domain_mapping("admin.example.com".to_string(), service_id3)
            .unwrap();

        let result1 = proxy.resolve_service("api.example.com");
        let result2 = proxy.resolve_service("web.example.com");
        let result3 = proxy.resolve_service("admin.example.com");

        assert_eq!(result1.unwrap(), service_id1);
        assert_eq!(result2.unwrap(), service_id2);
        assert_eq!(result3.unwrap(), service_id3);
    }

    #[test]
    fn test_resolve_service_unmapped_subdomain_fails() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("api.example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("web.example.com");

        assert!(matches!(result, Err(ProxyError::ServiceNotFound)));
    }

    #[test]
    fn test_resolve_service_with_custom_port() {
        let service_id = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = proxy.resolve_service("example.com:3000");

        assert!(result.is_ok());
        assert_eq!(result.unwrap(), service_id);
    }

    #[test]
    fn test_concurrent_resolve_service() {
        use std::thread;

        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id1, service_id2]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example1.com".to_string(), service_id1)
            .unwrap();
        proxy
            .domain_mapping_manager
            .add_domain_mapping("example2.com".to_string(), service_id2)
            .unwrap();

        let proxy_arc = Arc::new(proxy);
        let mut handles = vec![];

        for i in 0..10 {
            let proxy_clone = Arc::clone(&proxy_arc);
            let handle = thread::spawn(move || {
                for _ in 0..100 {
                    let domain = if i % 2 == 0 {
                        "example1.com"
                    } else {
                        "example2.com"
                    };
                    let _ = proxy_clone.resolve_service(domain);
                }
            });
            handles.push(handle);
        }

        for handle in handles {
            handle.join().unwrap();
        }

        let result1 = proxy_arc.resolve_service("example1.com");
        let result2 = proxy_arc.resolve_service("example2.com");

        assert_eq!(result1.unwrap(), service_id1);
        assert_eq!(result2.unwrap(), service_id2);
    }

    #[test]
    fn test_hot_domain_mapping_updates_do_not_drop_connections() {
        use std::thread;
        use std::sync::atomic::{AtomicUsize, Ordering};

        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id1, service_id2]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();

        let proxy_arc = Arc::new(proxy);
        let success_count = Arc::new(AtomicUsize::new(0));
        let mut handles = vec![];

        for _ in 0..5 {
            let proxy_clone = Arc::clone(&proxy_arc);
            let count_clone = Arc::clone(&success_count);
            let handle = thread::spawn(move || {
                for _ in 0..1000 {
                    let result = proxy_clone.resolve_service("example.com");
                    if result.is_ok() {
                        count_clone.fetch_add(1, Ordering::Relaxed);
                    }
                }
            });
            handles.push(handle);
        }

        let proxy_updater = Arc::clone(&proxy_arc);
        let updater_handle = thread::spawn(move || {
            for _ in 0..500 {
                let _ = proxy_updater.domain_mapping_manager
                    .update_domain_mapping(
                        "example.com".to_string(),
                        service_id2,
                    );
                let _ = proxy_updater.domain_mapping_manager
                    .update_domain_mapping(
                        "example.com".to_string(),
                        service_id1,
                    );
            }
        });

        for handle in handles {
            handle.join().unwrap();
        }
        updater_handle.join().unwrap();

        let total_success = success_count.load(Ordering::Relaxed);
        assert_eq!(total_success, 5000);
    }

    #[test]
    fn test_domain_mapping_updates_apply_immediately() {
        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id1, service_id2]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();

        let result1 = proxy.resolve_service("example.com");
        assert_eq!(result1.unwrap(), service_id1);

        proxy
            .domain_mapping_manager
            .update_domain_mapping("example.com".to_string(), service_id2)
            .unwrap();

        let result2 = proxy.resolve_service("example.com");
        assert_eq!(result2.unwrap(), service_id2);
    }

    #[test]
    fn test_concurrent_updates_and_reads_maintain_consistency() {
        use std::thread;
        use std::collections::HashSet;

        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let (proxy, _) = create_test_proxy(vec![service_id1, service_id2]);

        proxy
            .domain_mapping_manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();

        let proxy_arc = Arc::new(proxy);
        let mut handles = vec![];

        for _ in 0..3 {
            let proxy_clone = Arc::clone(&proxy_arc);
            let handle = thread::spawn(move || {
                let mut seen_services = HashSet::new();
                for _ in 0..1000 {
                    if let Ok(service) = proxy_clone
                        .resolve_service("example.com")
                    {
                        seen_services.insert(service);
                    }
                }
                seen_services
            });
            handles.push(handle);
        }

        let proxy_updater = Arc::clone(&proxy_arc);
        let updater_handle = thread::spawn(move || {
            for _ in 0..100 {
                let _ = proxy_updater.domain_mapping_manager
                    .update_domain_mapping(
                        "example.com".to_string(),
                        service_id2,
                    );
                thread::sleep(std::time::Duration::from_micros(10));
                let _ = proxy_updater.domain_mapping_manager
                    .update_domain_mapping(
                        "example.com".to_string(),
                        service_id1,
                    );
                thread::sleep(std::time::Duration::from_micros(10));
            }
        });

        let mut all_seen_services = HashSet::new();
        for handle in handles {
            let seen = handle.join().unwrap();
            all_seen_services.extend(seen);
        }
        updater_handle.join().unwrap();

        assert!(
            all_seen_services.contains(&service_id1) ||
            all_seen_services.contains(&service_id2)
        );
    }
}
