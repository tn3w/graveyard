use crate::deployment::errors::MappingError;
use crate::deployment::types::{DomainMapping, ServiceId};
use chrono::Utc;
use std::collections::HashMap;
use std::sync::{Arc, RwLock};

pub struct DomainMappingManager {
    domain_mappings: Arc<RwLock<HashMap<String, ServiceId>>>,
    service_validator: Arc<dyn ServiceValidator>,
}

pub trait ServiceValidator: Send + Sync {
    fn service_exists(&self, service_id: ServiceId) -> bool;
}

impl DomainMappingManager {
    pub fn new(service_validator: Arc<dyn ServiceValidator>) -> Self {
        Self {
            domain_mappings: Arc::new(RwLock::new(HashMap::new())),
            service_validator,
        }
    }

    pub fn add_domain_mapping(
        &self,
        domain: String,
        service_id: ServiceId,
    ) -> Result<DomainMapping, MappingError> {
        self.validate_domain_format(&domain)?;
        self.validate_service_exists(service_id)?;

        let mut mappings = self.domain_mappings.write().unwrap();

        if mappings.contains_key(&domain) {
            return Err(MappingError::DomainAlreadyMapped(domain));
        }

        let now = Utc::now();
        mappings.insert(domain.clone(), service_id);

        Ok(DomainMapping {
            domain,
            service_id,
            created_at: now,
            updated_at: now,
        })
    }

    pub fn remove_domain_mapping(
        &self,
        domain: &str,
    ) -> Result<(), MappingError> {
        let mut mappings = self.domain_mappings.write().unwrap();

        if mappings.remove(domain).is_none() {
            return Err(MappingError::DomainNotFound(domain.to_string()));
        }

        Ok(())
    }

    pub fn update_domain_mapping(
        &self,
        domain: String,
        service_id: ServiceId,
    ) -> Result<DomainMapping, MappingError> {
        self.validate_domain_format(&domain)?;
        self.validate_service_exists(service_id)?;

        let mut mappings = self.domain_mappings.write().unwrap();

        if !mappings.contains_key(&domain) {
            return Err(MappingError::DomainNotFound(domain));
        }

        mappings.insert(domain.clone(), service_id);

        Ok(DomainMapping {
            domain,
            service_id,
            created_at: Utc::now(),
            updated_at: Utc::now(),
        })
    }

    pub fn get_service_for_domain(
        &self,
        domain: &str,
    ) -> Option<ServiceId> {
        let mappings = self.domain_mappings.read().unwrap();
        mappings.get(domain).copied()
    }

    pub fn get_all_mappings(&self) -> Vec<(String, ServiceId)> {
        let mappings = self.domain_mappings.read().unwrap();
        mappings
            .iter()
            .map(|(domain, service_id)| (domain.clone(), *service_id))
            .collect()
    }

    fn validate_domain_format(&self, domain: &str) -> Result<(), MappingError> {
        if domain.is_empty() {
            return Err(MappingError::InvalidDomain(
                "Domain cannot be empty".to_string()
            ));
        }

        if domain.len() > 253 {
            return Err(MappingError::InvalidDomain(
                "Domain exceeds maximum length of 253 characters".to_string()
            ));
        }

        if domain.starts_with('.') || domain.ends_with('.') {
            return Err(MappingError::InvalidDomain(
                "Domain cannot start or end with a dot".to_string()
            ));
        }

        if domain.contains("..") {
            return Err(MappingError::InvalidDomain(
                "Domain cannot contain consecutive dots".to_string()
            ));
        }

        let labels: Vec<&str> = domain.split('.').collect();

        for label in labels {
            if label.is_empty() {
                return Err(MappingError::InvalidDomain(
                    "Domain contains empty label".to_string()
                ));
            }

            if label.len() > 63 {
                return Err(MappingError::InvalidDomain(
                    "Domain label exceeds maximum length of 63 characters"
                        .to_string()
                ));
            }

            if label.starts_with('-') || label.ends_with('-') {
                return Err(MappingError::InvalidDomain(
                    "Domain label cannot start or end with hyphen".to_string()
                ));
            }

            for character in label.chars() {
                if !character.is_ascii_alphanumeric() && character != '-' {
                    return Err(MappingError::InvalidDomain(format!(
                        "Domain contains invalid character: {}",
                        character
                    )));
                }
            }
        }

        Ok(())
    }

    fn validate_service_exists(
        &self,
        service_id: ServiceId,
    ) -> Result<(), MappingError> {
        if !self.service_validator.service_exists(service_id) {
            return Err(MappingError::ServiceNotFound);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use uuid::Uuid;

    struct MockServiceValidator {
        valid_services: Vec<ServiceId>,
    }

    impl ServiceValidator for MockServiceValidator {
        fn service_exists(&self, service_id: ServiceId) -> bool {
            self.valid_services.contains(&service_id)
        }
    }

    fn create_manager_with_services(
        services: Vec<ServiceId>,
    ) -> DomainMappingManager {
        let validator = Arc::new(MockServiceValidator {
            valid_services: services,
        });
        DomainMappingManager::new(validator)
    }

    #[test]
    fn test_add_domain_mapping_success() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "example.com".to_string(),
            service_id,
        );

        assert!(result.is_ok());
        let mapping = result.unwrap();
        assert_eq!(mapping.domain, "example.com");
        assert_eq!(mapping.service_id, service_id);
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_empty() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping("".to_string(), service_id);

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_starts_with_dot() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            ".example.com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_ends_with_dot() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "example.com.".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_consecutive_dots() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "example..com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_label_too_long() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let long_label = "a".repeat(64);
        let domain = format!("{}.com", long_label);

        let result = manager.add_domain_mapping(domain, service_id);

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_total_too_long() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let domain = format!("{}.com", "a".repeat(250));

        let result = manager.add_domain_mapping(domain, service_id);

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_label_starts_with_hyphen() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "-example.com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_label_ends_with_hyphen() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "example-.com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_invalid_domain_special_characters() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "example@.com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_add_domain_mapping_service_not_found() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![]);

        let result = manager.add_domain_mapping(
            "example.com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::ServiceNotFound)));
    }

    #[test]
    fn test_add_domain_mapping_already_mapped() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = manager.add_domain_mapping(
            "example.com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::DomainAlreadyMapped(_))));
    }

    #[test]
    fn test_remove_domain_mapping_success() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = manager.remove_domain_mapping("example.com");

        assert!(result.is_ok());
        assert!(manager.get_service_for_domain("example.com").is_none());
    }

    #[test]
    fn test_remove_domain_mapping_not_found() {
        let manager = create_manager_with_services(vec![]);

        let result = manager.remove_domain_mapping("example.com");

        assert!(matches!(result, Err(MappingError::DomainNotFound(_))));
    }

    #[test]
    fn test_update_domain_mapping_success() {
        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let manager = create_manager_with_services(
            vec![service_id1, service_id2]
        );

        manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();

        let result = manager.update_domain_mapping(
            "example.com".to_string(),
            service_id2,
        );

        assert!(result.is_ok());
        let mapping = result.unwrap();
        assert_eq!(mapping.service_id, service_id2);
        assert_eq!(
            manager.get_service_for_domain("example.com"),
            Some(service_id2)
        );
    }

    #[test]
    fn test_update_domain_mapping_not_found() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.update_domain_mapping(
            "example.com".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::DomainNotFound(_))));
    }

    #[test]
    fn test_update_domain_mapping_invalid_domain() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = manager.update_domain_mapping(
            "".to_string(),
            service_id,
        );

        assert!(matches!(result, Err(MappingError::InvalidDomain(_))));
    }

    #[test]
    fn test_update_domain_mapping_service_not_found() {
        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id1]);

        manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();

        let result = manager.update_domain_mapping(
            "example.com".to_string(),
            service_id2,
        );

        assert!(matches!(result, Err(MappingError::ServiceNotFound)));
    }

    #[test]
    fn test_get_service_for_domain_exists() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        manager
            .add_domain_mapping("example.com".to_string(), service_id)
            .unwrap();

        let result = manager.get_service_for_domain("example.com");

        assert_eq!(result, Some(service_id));
    }

    #[test]
    fn test_get_service_for_domain_not_found() {
        let manager = create_manager_with_services(vec![]);

        let result = manager.get_service_for_domain("example.com");

        assert!(result.is_none());
    }

    #[test]
    fn test_get_all_mappings_empty() {
        let manager = create_manager_with_services(vec![]);

        let mappings = manager.get_all_mappings();

        assert_eq!(mappings.len(), 0);
    }

    #[test]
    fn test_get_all_mappings_multiple() {
        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let manager = create_manager_with_services(
            vec![service_id1, service_id2]
        );

        manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();
        manager
            .add_domain_mapping("test.com".to_string(), service_id2)
            .unwrap();

        let mappings = manager.get_all_mappings();

        assert_eq!(mappings.len(), 2);
        assert!(mappings.contains(&("example.com".to_string(), service_id1)));
        assert!(mappings.contains(&("test.com".to_string(), service_id2)));
    }

    #[test]
    fn test_valid_subdomain() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "api.example.com".to_string(),
            service_id,
        );

        assert!(result.is_ok());
    }

    #[test]
    fn test_valid_deep_subdomain() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "api.v1.example.com".to_string(),
            service_id,
        );

        assert!(result.is_ok());
    }

    #[test]
    fn test_valid_domain_with_hyphens() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "my-api.example-site.com".to_string(),
            service_id,
        );

        assert!(result.is_ok());
    }

    #[test]
    fn test_valid_domain_with_numbers() {
        let service_id = Uuid::new_v4();
        let manager = create_manager_with_services(vec![service_id]);

        let result = manager.add_domain_mapping(
            "api2.example123.com".to_string(),
            service_id,
        );

        assert!(result.is_ok());
    }

    #[test]
    fn test_concurrent_access() {
        use std::sync::Arc;
        use std::thread;

        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let manager = Arc::new(create_manager_with_services(
            vec![service_id1, service_id2]
        ));

        let manager_clone1 = Arc::clone(&manager);
        let handle1 = thread::spawn(move || {
            for i in 0..100 {
                let domain = format!("test{}.com", i);
                let _ = manager_clone1.add_domain_mapping(domain, service_id1);
            }
        });

        let manager_clone2 = Arc::clone(&manager);
        let handle2 = thread::spawn(move || {
            for i in 100..200 {
                let domain = format!("test{}.com", i);
                let _ = manager_clone2.add_domain_mapping(domain, service_id2);
            }
        });

        handle1.join().unwrap();
        handle2.join().unwrap();

        let mappings = manager.get_all_mappings();
        assert_eq!(mappings.len(), 200);
    }

    #[test]
    fn test_hot_updates_allow_concurrent_reads() {
        use std::sync::Arc;
        use std::thread;
        use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};

        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let manager = Arc::new(create_manager_with_services(
            vec![service_id1, service_id2]
        ));

        manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();

        let stop_flag = Arc::new(AtomicBool::new(false));
        let read_count = Arc::new(AtomicUsize::new(0));

        let manager_reader = Arc::clone(&manager);
        let stop_reader = Arc::clone(&stop_flag);
        let count_reader = Arc::clone(&read_count);
        let reader_handle = thread::spawn(move || {
            while !stop_reader.load(Ordering::Relaxed) {
                let result = manager_reader
                    .get_service_for_domain("example.com");
                assert!(result.is_some());
                count_reader.fetch_add(1, Ordering::Relaxed);
            }
        });

        let manager_updater = Arc::clone(&manager);
        let updater_handle = thread::spawn(move || {
            for _ in 0..100 {
                let _ = manager_updater.update_domain_mapping(
                    "example.com".to_string(),
                    service_id2,
                );
                thread::sleep(std::time::Duration::from_micros(10));
                let _ = manager_updater.update_domain_mapping(
                    "example.com".to_string(),
                    service_id1,
                );
                thread::sleep(std::time::Duration::from_micros(10));
            }
        });

        updater_handle.join().unwrap();
        stop_flag.store(true, Ordering::Relaxed);
        reader_handle.join().unwrap();

        let total_reads = read_count.load(Ordering::Relaxed);
        assert!(total_reads > 0);

        let final_service = manager
            .get_service_for_domain("example.com")
            .unwrap();
        assert_eq!(final_service, service_id1);
    }

    #[test]
    fn test_hot_updates_do_not_block_reads() {
        use std::sync::Arc;
        use std::thread;
        use std::time::{Duration, Instant};

        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let manager = Arc::new(create_manager_with_services(
            vec![service_id1, service_id2]
        ));

        for i in 0..10 {
            let domain = format!("test{}.com", i);
            manager
                .add_domain_mapping(domain, service_id1)
                .unwrap();
        }

        let manager_reader = Arc::clone(&manager);
        let reader_handle = thread::spawn(move || {
            let start = Instant::now();
            for _ in 0..1000 {
                for i in 0..10 {
                    let domain = format!("test{}.com", i);
                    let _ = manager_reader.get_service_for_domain(&domain);
                }
            }
            start.elapsed()
        });

        let manager_updater = Arc::clone(&manager);
        let updater_handle = thread::spawn(move || {
            for _ in 0..100 {
                for i in 0..10 {
                    let domain = format!("test{}.com", i);
                    let _ = manager_updater.update_domain_mapping(
                        domain,
                        service_id2,
                    );
                }
                thread::sleep(Duration::from_micros(100));
            }
        });

        let read_duration = reader_handle.join().unwrap();
        updater_handle.join().unwrap();

        assert!(read_duration < Duration::from_secs(5));
    }

    #[test]
    fn test_multiple_concurrent_readers_during_updates() {
        use std::sync::Arc;
        use std::thread;

        let service_id1 = Uuid::new_v4();
        let service_id2 = Uuid::new_v4();
        let manager = Arc::new(create_manager_with_services(
            vec![service_id1, service_id2]
        ));

        manager
            .add_domain_mapping("example.com".to_string(), service_id1)
            .unwrap();

        let mut handles = vec![];

        for _ in 0..5 {
            let manager_clone = Arc::clone(&manager);
            let handle = thread::spawn(move || {
                for _ in 0..1000 {
                    let result = manager_clone
                        .get_service_for_domain("example.com");
                    assert!(result.is_some());
                }
            });
            handles.push(handle);
        }

        let manager_updater = Arc::clone(&manager);
        let updater_handle = thread::spawn(move || {
            for _ in 0..500 {
                let _ = manager_updater.update_domain_mapping(
                    "example.com".to_string(),
                    service_id2,
                );
                let _ = manager_updater.update_domain_mapping(
                    "example.com".to_string(),
                    service_id1,
                );
            }
        });

        for handle in handles {
            handle.join().unwrap();
        }
        updater_handle.join().unwrap();

        let final_service = manager
            .get_service_for_domain("example.com")
            .unwrap();
        assert_eq!(final_service, service_id1);
    }
}
