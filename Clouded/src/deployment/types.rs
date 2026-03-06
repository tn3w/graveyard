use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::time::Duration;
use uuid::Uuid;

pub type HttpMethod = String;
pub type HttpHeaders = HashMap<String, String>;
pub type HttpBody = Vec<u8>;

pub type ServiceId = Uuid;
pub type InstanceId = Uuid;
pub type DeploymentId = Uuid;
pub type RepositoryId = Uuid;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DeploymentStatus {
    Pending,
    Building,
    HealthChecking,
    Swapping,
    Completed,
    Failed,
    RolledBack,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum HealthStatus {
    Healthy,
    Unhealthy,
    Unknown,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum LogLevel {
    Debug,
    Info,
    Warning,
    Error,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum DeploymentSlot {
    Slot1,
    Slot2,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeploymentEvent {
    pub repository_id: RepositoryId,
    pub commit_hash: String,
    pub branch: String,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeploymentResult {
    pub service_id: ServiceId,
    pub deployment_id: DeploymentId,
    pub instances: Vec<InstanceId>,
    pub duration: Duration,
    pub status: DeploymentStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServiceInstance {
    pub instance_id: InstanceId,
    pub address: SocketAddr,
    pub health_status: HealthStatus,
    pub slot: DeploymentSlot,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: DateTime<Utc>,
    pub service_id: ServiceId,
    pub instance_id: InstanceId,
    pub level: LogLevel,
    pub message: String,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DomainMapping {
    pub domain: String,
    pub service_id: ServiceId,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimeRange {
    pub start_time: DateTime<Utc>,
    pub end_time: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogFilter {
    pub service_id: Option<ServiceId>,
    pub instance_id: Option<InstanceId>,
    pub level: Option<LogLevel>,
    pub time_range: TimeRange,
    pub search_text: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeploymentMetrics {
    pub total_deployments: u64,
    pub successful_deployments: u64,
    pub failed_deployments: u64,
    pub average_duration: Duration,
    pub error_rate: f64,
}

#[derive(Debug, Clone)]
pub struct HttpRequest {
    pub method: HttpMethod,
    pub path: String,
    pub headers: HttpHeaders,
    pub body: Option<HttpBody>,
}

#[derive(Debug, Clone)]
pub struct HttpResponse {
    pub status: u16,
    pub headers: HttpHeaders,
    pub body: Option<HttpBody>,
}
