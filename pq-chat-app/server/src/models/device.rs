use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use std::time::{SystemTime, UNIX_EPOCH};

fn current_timestamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

const X25519_PUBLIC_KEY_SIZE: usize = 32;
const KYBER1024_PUBLIC_KEY_SIZE: usize = 1568;
const COMBINED_PUBLIC_KEY_SIZE: usize = X25519_PUBLIC_KEY_SIZE + KYBER1024_PUBLIC_KEY_SIZE;
const MIN_PUBLIC_KEY_SIZE: usize = X25519_PUBLIC_KEY_SIZE;
const MAX_PUBLIC_KEY_SIZE: usize = COMBINED_PUBLIC_KEY_SIZE;

fn validate_public_key(public_key: &[u8]) -> Result<(), String> {
    let key_len = public_key.len();
    
    if key_len < MIN_PUBLIC_KEY_SIZE {
        return Err(format!(
            "Public key too small: {} bytes (minimum {})",
            key_len, MIN_PUBLIC_KEY_SIZE
        ));
    }
    
    if key_len > MAX_PUBLIC_KEY_SIZE {
        return Err(format!(
            "Public key too large: {} bytes (maximum {})",
            key_len, MAX_PUBLIC_KEY_SIZE
        ));
    }
    
    if key_len == X25519_PUBLIC_KEY_SIZE {
        validate_x25519_public_key(&public_key[..X25519_PUBLIC_KEY_SIZE])?;
    } else if key_len == COMBINED_PUBLIC_KEY_SIZE {
        validate_x25519_public_key(&public_key[..X25519_PUBLIC_KEY_SIZE])?;
        validate_kyber_public_key(&public_key[X25519_PUBLIC_KEY_SIZE..])?;
    } else {
        return Err(format!(
            "Invalid key size: {} bytes (expected {} or {})",
            key_len, X25519_PUBLIC_KEY_SIZE, COMBINED_PUBLIC_KEY_SIZE
        ));
    }
    
    Ok(())
}

fn validate_x25519_public_key(key: &[u8]) -> Result<(), String> {
    if key.len() != X25519_PUBLIC_KEY_SIZE {
        return Err(format!(
            "X25519 key must be exactly {} bytes",
            X25519_PUBLIC_KEY_SIZE
        ));
    }
    
    if key.iter().all(|&b| b == 0) {
        return Err("X25519 public key cannot be all zeros".to_string());
    }
    
    if key.iter().all(|&b| b == 0xFF) {
        return Err("X25519 public key cannot be all 0xFF".to_string());
    }
    
    let low_order_points = [
        [0u8; 32],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0xec, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
         0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
         0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
         0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f],
        [0xee, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
         0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
         0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 
         0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f],
    ];
    
    for low_order_point in &low_order_points {
        if key == low_order_point {
            return Err("X25519 public key is a low-order point".to_string());
        }
    }
    
    Ok(())
}

fn validate_kyber_public_key(key: &[u8]) -> Result<(), String> {
    if key.len() != KYBER1024_PUBLIC_KEY_SIZE {
        return Err(format!(
            "Kyber1024 public key must be exactly {} bytes",
            KYBER1024_PUBLIC_KEY_SIZE
        ));
    }
    
    if key.iter().all(|&b| b == 0) {
        return Err("Kyber public key cannot be all zeros".to_string());
    }
    
    if key.iter().all(|&b| b == 0xFF) {
        return Err("Kyber public key cannot be all 0xFF".to_string());
    }
    
    let zero_count = key.iter().filter(|&&b| b == 0).count();
    let total_bytes = key.len();
    let zero_ratio = zero_count as f64 / total_bytes as f64;
    
    if zero_ratio > 0.95 {
        return Err(format!(
            "Kyber public key has suspicious entropy: {:.1}% zeros",
            zero_ratio * 100.0
        ));
    }
    
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct Device {
    pub id: String,
    pub user_id: String,
    pub public_key: Vec<u8>,
    pub created_at: i64,
    pub last_seen: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
#[allow(dead_code)]
pub struct RegisterDeviceRequest {
    pub public_key: Vec<u8>,
}

impl Device {
    pub async fn create(
        pool: &sqlx::SqlitePool,
        user_id: String,
        public_key: Vec<u8>,
    ) -> Result<Self, sqlx::Error> {
        validate_public_key(&public_key).map_err(|e| {
            sqlx::Error::Protocol(format!("Invalid public key: {}", e))
        })?;
        
        let id = uuid::Uuid::new_v4().to_string();
        let now = current_timestamp();

        sqlx::query_as::<_, Device>(
            "INSERT INTO devices (id, user_id, public_key, created_at, last_seen)
             VALUES (?, ?, ?, ?, ?)
             RETURNING id, user_id, public_key, created_at, last_seen",
        )
        .bind(&id)
        .bind(&user_id)
        .bind(&public_key)
        .bind(now)
        .bind(now)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_id(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, Device>(
            "SELECT id, user_id, public_key, created_at, last_seen
             FROM devices
             WHERE id = ?",
        )
        .bind(id)
        .fetch_optional(pool)
        .await
    }

    pub async fn find_by_user(
        pool: &sqlx::SqlitePool,
        user_id: &str,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, Device>(
            "SELECT id, user_id, public_key, created_at, last_seen
             FROM devices
             WHERE user_id = ?
             ORDER BY last_seen DESC",
        )
        .bind(user_id)
        .fetch_all(pool)
        .await
    }

    #[allow(dead_code)]
    pub async fn update_last_seen(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<(), sqlx::Error> {
        let now = current_timestamp();

        sqlx::query("UPDATE devices SET last_seen = ? WHERE id = ?")
            .bind(now)
            .bind(id)
            .execute(pool)
            .await?;

        Ok(())
    }

    pub async fn delete(
        pool: &sqlx::SqlitePool,
        id: &str,
    ) -> Result<(), sqlx::Error> {
        sqlx::query("DELETE FROM devices WHERE id = ?")
            .bind(id)
            .execute(pool)
            .await?;

        Ok(())
    }

    pub async fn find_by_group_members(
        pool: &sqlx::SqlitePool,
        group_id: &str,
    ) -> Result<Vec<Self>, sqlx::Error> {
        sqlx::query_as::<_, Device>(
            "SELECT DISTINCT d.id, d.user_id, d.public_key, 
                    d.created_at, d.last_seen
             FROM devices d
             INNER JOIN group_members gm ON d.user_id = gm.user_id
             WHERE gm.group_id = ?
             ORDER BY d.last_seen DESC",
        )
        .bind(group_id)
        .fetch_all(pool)
        .await
    }
}
