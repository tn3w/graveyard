use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime};
use tokio::sync::{Mutex, RwLock};

const CLEANUP_INTERVAL_SECONDS: u64 = 300;
const MAX_ENTRIES: usize = 10000;

struct RateLimitEntry {
    tokens: f64,
    last_refill: SystemTime,
}

#[derive(Clone)]
pub struct RateLimiter {
    entries: Arc<RwLock<HashMap<String, Arc<Mutex<RateLimitEntry>>>>>,
    max_tokens: f64,
    refill_rate: f64,
    last_cleanup: Arc<Mutex<SystemTime>>,
}

impl RateLimiter {
    pub fn new(max_tokens: f64, refill_rate_per_second: f64) -> Self {
        Self {
            entries: Arc::new(RwLock::new(HashMap::new())),
            max_tokens,
            refill_rate: refill_rate_per_second,
            last_cleanup: Arc::new(Mutex::new(SystemTime::now())),
        }
    }

    pub async fn check_rate_limit(&self, key: &str) -> bool {
        self.cleanup_if_needed().await;

        let entry = {
            let entries = self.entries.read().await;
            if let Some(e) = entries.get(key) {
                Arc::clone(e)
            } else {
                drop(entries);
                let new_entry = Arc::new(Mutex::new(RateLimitEntry {
                    tokens: self.max_tokens,
                    last_refill: SystemTime::now(),
                }));
                let mut entries = self.entries.write().await;
                
                if entries.len() >= MAX_ENTRIES {
                    tracing::warn!("Rate limiter at capacity, rejecting request");
                    return false;
                }
                
                entries.insert(key.to_string(), Arc::clone(&new_entry));
                new_entry
            }
        };

        let mut entry_data = entry.lock().await;
        let now = SystemTime::now();
        let elapsed = now
            .duration_since(entry_data.last_refill)
            .unwrap_or(Duration::ZERO)
            .as_secs_f64();

        let refill_amount = elapsed * self.refill_rate;
        entry_data.tokens = (entry_data.tokens + refill_amount).min(self.max_tokens);
        entry_data.last_refill = now;

        if entry_data.tokens >= 1.0 {
            entry_data.tokens -= 1.0;
            true
        } else {
            false
        }
    }

    async fn cleanup_if_needed(&self) {
        let mut last_cleanup = self.last_cleanup.lock().await;
        let now = SystemTime::now();
        
        if now.duration_since(*last_cleanup).unwrap_or(Duration::ZERO).as_secs() 
            < CLEANUP_INTERVAL_SECONDS {
            return;
        }

        *last_cleanup = now;
        drop(last_cleanup);

        let mut entries = self.entries.write().await;
        let before_count = entries.len();
        
        entries.retain(|_, entry| {
            if let Ok(entry_data) = entry.try_lock() {
                let age = now.duration_since(entry_data.last_refill)
                    .unwrap_or(Duration::ZERO);
                age.as_secs() < 3600
            } else {
                true
            }
        });

        let removed = before_count - entries.len();
        if removed > 0 {
            tracing::info!(
                removed = removed,
                remaining = entries.len(),
                "Rate limiter cleanup completed"
            );
        }
    }

    #[allow(dead_code)]
    pub async fn reset(&self, key: &str) {
        let mut entries = self.entries.write().await;
        entries.remove(key);
    }
}
