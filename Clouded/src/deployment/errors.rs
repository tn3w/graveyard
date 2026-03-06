use std::fmt;

#[derive(Debug)]
pub enum GitHubError {
    AuthenticationFailed(String),
    WebhookRegistrationFailed(String),
    ApiRequestFailed(String),
    InvalidCredentials,
    NetworkError(String),
}

impl fmt::Display for GitHubError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::AuthenticationFailed(message) => {
                write!(formatter, "GitHub authentication failed: {}", message)
            }
            Self::WebhookRegistrationFailed(message) => {
                write!(formatter, "Webhook registration failed: {}", message)
            }
            Self::ApiRequestFailed(message) => {
                write!(formatter, "GitHub API request failed: {}", message)
            }
            Self::InvalidCredentials => {
                write!(formatter, "Invalid GitHub credentials")
            }
            Self::NetworkError(message) => {
                write!(formatter, "Network error: {}", message)
            }
        }
    }
}

impl std::error::Error for GitHubError {}

#[derive(Debug)]
pub enum DeploymentError {
    BuildFailed(String),
    HealthCheckFailed(String),
    SlotSwapFailed(String),
    InstanceStartFailed(String),
    ConfigurationError(String),
    ResourceExhausted,
    LogStorageError(String),
    StreamError(String),
}

impl fmt::Display for DeploymentError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::BuildFailed(message) => {
                write!(formatter, "Build failed: {}", message)
            }
            Self::HealthCheckFailed(message) => {
                write!(formatter, "Health check failed: {}", message)
            }
            Self::SlotSwapFailed(message) => {
                write!(formatter, "Slot swap failed: {}", message)
            }
            Self::InstanceStartFailed(message) => {
                write!(formatter, "Instance start failed: {}", message)
            }
            Self::ConfigurationError(message) => {
                write!(formatter, "Configuration error: {}", message)
            }
            Self::ResourceExhausted => {
                write!(formatter, "Resource exhausted")
            }
            Self::LogStorageError(message) => {
                write!(formatter, "Log storage error: {}", message)
            }
            Self::StreamError(message) => {
                write!(formatter, "Stream error: {}", message)
            }
        }
    }
}

impl std::error::Error for DeploymentError {}

#[derive(Debug)]
pub enum LoadBalancerError {
    InstanceNotFound,
    ServiceNotFound,
    NoHealthyInstances,
    PoolUpdateFailed(String),
    RoutingFailed(String),
}

impl fmt::Display for LoadBalancerError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::InstanceNotFound => write!(formatter, "Instance not found"),
            Self::ServiceNotFound => write!(formatter, "Service not found"),
            Self::NoHealthyInstances => {
                write!(formatter, "No healthy instances available")
            }
            Self::PoolUpdateFailed(message) => {
                write!(formatter, "Pool update failed: {}", message)
            }
            Self::RoutingFailed(message) => {
                write!(formatter, "Request routing failed: {}", message)
            }
        }
    }
}

impl std::error::Error for LoadBalancerError {}

#[derive(Debug)]
pub enum ProxyError {
    ServiceNotFound,
    RoutingFailed(String),
    InvalidDomain(String),
    TlsError(String),
}

impl fmt::Display for ProxyError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::ServiceNotFound => write!(formatter, "Service not found"),
            Self::RoutingFailed(message) => {
                write!(formatter, "Routing failed: {}", message)
            }
            Self::InvalidDomain(domain) => {
                write!(formatter, "Invalid domain: {}", domain)
            }
            Self::TlsError(message) => {
                write!(formatter, "TLS error: {}", message)
            }
        }
    }
}

impl std::error::Error for ProxyError {}

#[derive(Debug)]
pub enum CloudflareError {
    AuthenticationFailed,
    ApiRequestFailed(String),
    InvalidZoneId,
    RecordUpdateFailed(String),
    RateLimitExceeded,
}

impl fmt::Display for CloudflareError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::AuthenticationFailed => {
                write!(formatter, "Cloudflare authentication failed")
            }
            Self::ApiRequestFailed(message) => {
                write!(formatter, "Cloudflare API request failed: {}", message)
            }
            Self::InvalidZoneId => write!(formatter, "Invalid zone ID"),
            Self::RecordUpdateFailed(message) => {
                write!(formatter, "DNS record update failed: {}", message)
            }
            Self::RateLimitExceeded => {
                write!(formatter, "Cloudflare rate limit exceeded")
            }
        }
    }
}

impl std::error::Error for CloudflareError {}

#[derive(Debug)]
pub enum DnsError {
    IpDetectionFailed(String),
    UpdateFailed(String),
    ConfigurationError(String),
}

impl fmt::Display for DnsError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::IpDetectionFailed(message) => {
                write!(formatter, "IP detection failed: {}", message)
            }
            Self::UpdateFailed(message) => {
                write!(formatter, "DNS update failed: {}", message)
            }
            Self::ConfigurationError(message) => {
                write!(formatter, "DNS configuration error: {}", message)
            }
        }
    }
}

impl std::error::Error for DnsError {}

#[derive(Debug)]
pub enum LogError {
    StorageFailed(String),
    QueryFailed(String),
    StreamError(String),
}

impl fmt::Display for LogError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::StorageFailed(message) => {
                write!(formatter, "Log storage failed: {}", message)
            }
            Self::QueryFailed(message) => {
                write!(formatter, "Log query failed: {}", message)
            }
            Self::StreamError(message) => {
                write!(formatter, "Log stream error: {}", message)
            }
        }
    }
}

impl std::error::Error for LogError {}

#[derive(Debug)]
pub enum ConfigError {
    ValidationFailed(String),
    SerializationFailed(String),
    DeserializationFailed(String),
    FileIoError(String),
    CorruptedFile,
}

impl fmt::Display for ConfigError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::ValidationFailed(message) => {
                write!(formatter, "Configuration validation failed: {}", message)
            }
            Self::SerializationFailed(message) => {
                write!(formatter, "Configuration serialization failed: {}", message)
            }
            Self::DeserializationFailed(message) => {
                write!(
                    formatter,
                    "Configuration deserialization failed: {}",
                    message
                )
            }
            Self::FileIoError(message) => {
                write!(formatter, "Configuration file I/O error: {}", message)
            }
            Self::CorruptedFile => {
                write!(formatter, "Configuration file is corrupted")
            }
        }
    }
}

impl std::error::Error for ConfigError {}

#[derive(Debug)]
pub enum AuthError {
    InvalidToken,
    TokenExpired,
    InvalidCredentials,
    Unauthorized,
    RateLimitExceeded,
}

impl fmt::Display for AuthError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::InvalidToken => write!(formatter, "Invalid authentication token"),
            Self::TokenExpired => write!(formatter, "Authentication token expired"),
            Self::InvalidCredentials => write!(formatter, "Invalid credentials"),
            Self::Unauthorized => write!(formatter, "Unauthorized access"),
            Self::RateLimitExceeded => {
                write!(formatter, "Rate limit exceeded")
            }
        }
    }
}

impl std::error::Error for AuthError {}

#[derive(Debug)]
pub enum EncryptionError {
    EncryptionFailed(String),
    DecryptionFailed(String),
    KeyGenerationFailed(String),
    InvalidKey,
}

impl fmt::Display for EncryptionError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::EncryptionFailed(message) => {
                write!(formatter, "Encryption failed: {}", message)
            }
            Self::DecryptionFailed(message) => {
                write!(formatter, "Decryption failed: {}", message)
            }
            Self::KeyGenerationFailed(message) => {
                write!(formatter, "Key generation failed: {}", message)
            }
            Self::InvalidKey => write!(formatter, "Invalid encryption key"),
        }
    }
}

impl std::error::Error for EncryptionError {}

#[derive(Debug)]
pub enum MappingError {
    InvalidDomain(String),
    ServiceNotFound,
    DomainAlreadyMapped(String),
    DomainNotFound(String),
    ValidationFailed(String),
}

impl fmt::Display for MappingError {
    fn fmt(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::InvalidDomain(domain) => {
                write!(formatter, "Invalid domain format: {}", domain)
            }
            Self::ServiceNotFound => {
                write!(formatter, "Service not found")
            }
            Self::DomainAlreadyMapped(domain) => {
                write!(formatter, "Domain already mapped: {}", domain)
            }
            Self::DomainNotFound(domain) => {
                write!(formatter, "Domain not found: {}", domain)
            }
            Self::ValidationFailed(message) => {
                write!(formatter, "Validation failed: {}", message)
            }
        }
    }
}

impl std::error::Error for MappingError {}
