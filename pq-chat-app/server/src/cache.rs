use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::RwLock;

use crate::models::{GroupMember, User};

struct CacheEntry<T> {
    value: Arc<T>,
    expires_at: Instant,
}

#[derive(Clone)]
struct SimpleCache<T> {
    entries: Arc<RwLock<HashMap<String, CacheEntry<T>>>>,
    ttl: Duration,
}

impl<T> SimpleCache<T> {
    fn new(ttl: Duration) -> Self {
        Self {
            entries: Arc::new(RwLock::new(HashMap::new())),
            ttl,
        }
    }

    async fn get(&self, key: &str) -> Option<Arc<T>> {
        let entries = self.entries.read().await;
        if let Some(entry) = entries.get(key) {
            if entry.expires_at > Instant::now() {
                return Some(Arc::clone(&entry.value));
            }
        }
        None
    }

    async fn insert(&self, key: String, value: T) {
        let mut entries = self.entries.write().await;
        entries.insert(
            key,
            CacheEntry {
                value: Arc::new(value),
                expires_at: Instant::now() + self.ttl,
            },
        );
    }

    async fn invalidate(&self, key: &str) {
        let mut entries = self.entries.write().await;
        entries.remove(key);
    }
}

#[derive(Clone)]
pub struct AppCache {
    users: SimpleCache<User>,
    group_members: SimpleCache<Vec<GroupMember>>,
}

impl Default for AppCache {
    fn default() -> Self {
        Self::new()
    }
}

impl AppCache {
    pub fn new() -> Self {
        Self {
            users: SimpleCache::new(Duration::from_secs(300)),
            group_members: SimpleCache::new(Duration::from_secs(60)),
        }
    }

    pub async fn get_user(&self, user_id: &str) -> Option<Arc<User>> {
        self.users.get(user_id).await
    }

    pub async fn set_user(&self, user_id: String, user: User) {
        self.users.insert(user_id, user).await;
    }

    pub async fn get_group_members(
        &self,
        group_id: &str,
    ) -> Option<Arc<Vec<GroupMember>>> {
        self.group_members.get(group_id).await
    }

    pub async fn set_group_members(
        &self,
        group_id: String,
        members: Vec<GroupMember>,
    ) {
        self.group_members.insert(group_id, members).await;
    }

    pub async fn invalidate_group_members(&self, group_id: &str) {
        self.group_members.invalidate(group_id).await;
    }
}
