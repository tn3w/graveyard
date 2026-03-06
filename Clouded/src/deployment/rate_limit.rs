use chrono::{DateTime, Duration, Utc};
use std::collections::HashMap;
use std::net::IpAddr;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone)]
struct RateLimitEntry {
    request_count: u32,
    window_start: DateTime<Utc>,
}

pub struct RateLimiter {
    limits: Arc<RwLock<HashMap<IpAddr, RateLimitEntry>>>,
    max_requests_per_window: u32,
    window_duration: Duration,
}

impl RateLimiter {
    pub fn new(max_requests_per_window: u32, window_duration: Duration) -> Self {
        Self {
            limits: Arc::new(RwLock::new(HashMap::new())),
            max_requests_per_window,
            window_duration,
        }
    }

    pub async fn check_rate_limit(&self, ip: IpAddr) -> bool {
        let now = Utc::now();
        let mut limits = self.limits.write().await;

        let entry = limits.entry(ip).or_insert(RateLimitEntry {
            request_count: 0,
            window_start: now,
        });

        if now - entry.window_start > self.window_duration {
            entry.request_count = 0;
            entry.window_start = now;
        }

        if entry.request_count >= self.max_requests_per_window {
            return false;
        }

        entry.request_count += 1;
        true
    }

    pub async fn reset_rate_limit(&self, ip: IpAddr) {
        let mut limits = self.limits.write().await;
        limits.remove(&ip);
    }

    pub async fn cleanup_expired_entries(&self) {
        let now = Utc::now();
        let mut limits = self.limits.write().await;

        limits.retain(|_, entry| {
            now - entry.window_start <= self.window_duration
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    #[tokio::test]
    async fn test_rate_limit_allows_requests_within_limit() {
        let rate_limiter = RateLimiter::new(5, Duration::seconds(60));
        let ip = IpAddr::from_str("127.0.0.1").unwrap();

        for _ in 0..5 {
            assert!(rate_limiter.check_rate_limit(ip).await);
        }
    }

    #[tokio::test]
    async fn test_rate_limit_blocks_requests_exceeding_limit() {
        let rate_limiter = RateLimiter::new(5, Duration::seconds(60));
        let ip = IpAddr::from_str("127.0.0.1").unwrap();

        for _ in 0..5 {
            rate_limiter.check_rate_limit(ip).await;
        }

        assert!(!rate_limiter.check_rate_limit(ip).await);
    }

    #[tokio::test]
    async fn test_rate_limit_resets_after_window() {
        let rate_limiter = RateLimiter::new(5, Duration::milliseconds(100));
        let ip = IpAddr::from_str("127.0.0.1").unwrap();

        for _ in 0..5 {
            rate_limiter.check_rate_limit(ip).await;
        }

        assert!(!rate_limiter.check_rate_limit(ip).await);

        tokio::time::sleep(tokio::time::Duration::from_millis(150)).await;

        assert!(rate_limiter.check_rate_limit(ip).await);
    }

    #[tokio::test]
    async fn test_rate_limit_per_ip() {
        let rate_limiter = RateLimiter::new(2, Duration::seconds(60));
        let ip1 = IpAddr::from_str("127.0.0.1").unwrap();
        let ip2 = IpAddr::from_str("192.168.1.1").unwrap();

        assert!(rate_limiter.check_rate_limit(ip1).await);
        assert!(rate_limiter.check_rate_limit(ip1).await);
        assert!(!rate_limiter.check_rate_limit(ip1).await);

        assert!(rate_limiter.check_rate_limit(ip2).await);
        assert!(rate_limiter.check_rate_limit(ip2).await);
        assert!(!rate_limiter.check_rate_limit(ip2).await);
    }

    #[tokio::test]
    async fn test_reset_rate_limit() {
        let rate_limiter = RateLimiter::new(2, Duration::seconds(60));
        let ip = IpAddr::from_str("127.0.0.1").unwrap();

        rate_limiter.check_rate_limit(ip).await;
        rate_limiter.check_rate_limit(ip).await;
        assert!(!rate_limiter.check_rate_limit(ip).await);

        rate_limiter.reset_rate_limit(ip).await;

        assert!(rate_limiter.check_rate_limit(ip).await);
    }

    #[tokio::test]
    async fn test_cleanup_expired_entries() {
        let rate_limiter = RateLimiter::new(5, Duration::milliseconds(100));
        let ip = IpAddr::from_str("127.0.0.1").unwrap();

        rate_limiter.check_rate_limit(ip).await;

        tokio::time::sleep(tokio::time::Duration::from_millis(150)).await;

        rate_limiter.cleanup_expired_entries().await;

        let limits = rate_limiter.limits.read().await;
        assert!(limits.is_empty());
    }
}
