use crate::deployment::errors::ConfigError;
use crate::deployment::types::{RepositoryId, ServiceId};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Configuration {
    pub services: HashMap<ServiceId, ServiceConfig>,
    pub github_connections: HashMap<RepositoryId, GitHubConnection>,
    pub domain_mappings: HashMap<String, ServiceId>,
    pub cloudflare_config: Option<CloudflareConfig>,
    pub system_settings: SystemSettings,
}

impl Configuration {
    pub fn new() -> Self {
        Self {
            services: HashMap::new(),
            github_connections: HashMap::new(),
            domain_mappings: HashMap::new(),
            cloudflare_config: None,
            system_settings: SystemSettings::default(),
        }
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        for (service_id, service_config) in &self.services {
            service_config.validate().map_err(|error| {
                ConfigError::ValidationFailed(format!(
                    "Service {} validation failed: {}",
                    service_id, error
                ))
            })?;
        }

        for (repository_id, github_connection) in &self.github_connections {
            github_connection.validate().map_err(|error| {
                ConfigError::ValidationFailed(format!(
                    "GitHub connection {} validation failed: {}",
                    repository_id, error
                ))
            })?;
        }

        for (domain, service_id) in &self.domain_mappings {
            if !self.services.contains_key(service_id) {
                return Err(ConfigError::ValidationFailed(format!(
                    "Domain {} maps to non-existent service {}",
                    domain, service_id
                )));
            }

            if domain.is_empty() {
                return Err(ConfigError::ValidationFailed(
                    "Domain cannot be empty".to_string(),
                ));
            }
        }

        if let Some(cloudflare_config) = &self.cloudflare_config {
            cloudflare_config.validate()?;
        }

        self.system_settings.validate()?;

        Ok(())
    }
}

impl Default for Configuration {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceConfig {
    pub service_id: ServiceId,
    pub name: String,
    pub repository_id: RepositoryId,
    pub instance_count: u32,
    pub health_check_endpoint: String,
    #[serde(with = "duration_serde")]
    pub health_check_interval: Duration,
    pub environment_variables: HashMap<String, String>,
    pub build_command: String,
    pub start_command: String,
    pub port: u16,
}

impl ServiceConfig {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.name.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Service name cannot be empty".to_string(),
            ));
        }

        if self.instance_count == 0 {
            return Err(ConfigError::ValidationFailed(
                "Instance count must be greater than 0".to_string(),
            ));
        }

        if self.health_check_endpoint.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Health check endpoint cannot be empty".to_string(),
            ));
        }

        if !self.health_check_endpoint.starts_with('/') {
            return Err(ConfigError::ValidationFailed(
                "Health check endpoint must start with /".to_string(),
            ));
        }

        if self.build_command.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Build command cannot be empty".to_string(),
            ));
        }

        if self.start_command.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Start command cannot be empty".to_string(),
            ));
        }

        if self.port == 0 {
            return Err(ConfigError::ValidationFailed(
                "Port must be greater than 0".to_string(),
            ));
        }

        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GitHubConnection {
    pub repository_id: RepositoryId,
    pub repository_url: String,
    pub encrypted_token: Vec<u8>,
    pub webhook_secret: String,
    pub branch: String,
}

impl GitHubConnection {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.repository_url.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Repository URL cannot be empty".to_string(),
            ));
        }

        if self.encrypted_token.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Encrypted token cannot be empty".to_string(),
            ));
        }

        if self.webhook_secret.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Webhook secret cannot be empty".to_string(),
            ));
        }

        if self.branch.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Branch cannot be empty".to_string(),
            ));
        }

        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CloudflareConfig {
    pub encrypted_api_token: Vec<u8>,
    pub zone_id: String,
    pub record_names: Vec<String>,
}

impl CloudflareConfig {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.encrypted_api_token.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Encrypted API token cannot be empty".to_string(),
            ));
        }

        if self.zone_id.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Zone ID cannot be empty".to_string(),
            ));
        }

        if self.record_names.is_empty() {
            return Err(ConfigError::ValidationFailed(
                "Record names cannot be empty".to_string(),
            ));
        }

        for record_name in &self.record_names {
            if record_name.is_empty() {
                return Err(ConfigError::ValidationFailed(
                    "Record name cannot be empty".to_string(),
                ));
            }
        }

        Ok(())
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SystemSettings {
    pub ui_bind_address: SocketAddr,
    pub proxy_bind_address: SocketAddr,
    pub log_retention_days: u32,
    pub max_concurrent_deployments: u32,
}

impl SystemSettings {
    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.log_retention_days == 0 {
            return Err(ConfigError::ValidationFailed(
                "Log retention days must be greater than 0".to_string(),
            ));
        }

        if self.max_concurrent_deployments == 0 {
            return Err(ConfigError::ValidationFailed(
                "Max concurrent deployments must be greater than 0".to_string(),
            ));
        }

        Ok(())
    }
}

impl Default for SystemSettings {
    fn default() -> Self {
        Self {
            ui_bind_address: "127.0.0.1:8080".parse().unwrap(),
            proxy_bind_address: "0.0.0.0:80".parse().unwrap(),
            log_retention_days: 30,
            max_concurrent_deployments: 5,
        }
    }
}

mod duration_serde {
    use serde::{Deserialize, Deserializer, Serialize, Serializer};
    use std::time::Duration;

    pub fn serialize<S>(
        duration: &Duration,
        serializer: S,
    ) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        duration.as_secs().serialize(serializer)
    }

    pub fn deserialize<'de, D>(deserializer: D) -> Result<Duration, D::Error>
    where
        D: Deserializer<'de>,
    {
        let seconds = u64::deserialize(deserializer)?;
        Ok(Duration::from_secs(seconds))
    }
}
