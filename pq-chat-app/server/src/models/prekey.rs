use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use std::time::{SystemTime, UNIX_EPOCH};

fn current_timestamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct PrekeyBundle {
    pub device_id: String,
    pub identity_key: Vec<u8>,
    pub signed_prekey: Vec<u8>,
    pub signed_prekey_signature: Vec<u8>,
    pub signed_prekey_timestamp: i64,
    pub created_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct OneTimePrekey {
    pub id: String,
    pub device_id: String,
    pub prekey: Vec<u8>,
    pub created_at: i64,
    pub consumed_at: Option<i64>,
}

#[derive(Debug, Deserialize)]
pub struct UploadPrekeyBundleRequest {
    pub identity_key: Vec<u8>,
    pub signed_prekey: Vec<u8>,
    pub signed_prekey_signature: Vec<u8>,
    pub signed_prekey_timestamp: i64,
    pub one_time_prekeys: Vec<Vec<u8>>,
}

#[derive(Debug, Serialize)]
pub struct PrekeyBundleResponse {
    pub identity_key: Vec<u8>,
    pub signed_prekey: Vec<u8>,
    pub signed_prekey_signature: Vec<u8>,
    pub signed_prekey_timestamp: i64,
    pub one_time_prekey: Option<Vec<u8>>,
}

impl PrekeyBundle {
    pub async fn create(
        pool: &sqlx::SqlitePool,
        device_id: String,
        identity_key: Vec<u8>,
        signed_prekey: Vec<u8>,
        signed_prekey_signature: Vec<u8>,
        signed_prekey_timestamp: i64,
    ) -> Result<Self, sqlx::Error> {
        let now = current_timestamp();

        sqlx::query_as::<_, PrekeyBundle>(
            "INSERT INTO prekey_bundles 
             (device_id, identity_key, signed_prekey, 
              signed_prekey_signature, signed_prekey_timestamp, created_at)
             VALUES (?, ?, ?, ?, ?, ?)
             ON CONFLICT(device_id) DO UPDATE SET
               identity_key = excluded.identity_key,
               signed_prekey = excluded.signed_prekey,
               signed_prekey_signature = excluded.signed_prekey_signature,
               signed_prekey_timestamp = excluded.signed_prekey_timestamp,
               created_at = excluded.created_at
             RETURNING device_id, identity_key, signed_prekey, 
                       signed_prekey_signature, signed_prekey_timestamp, 
                       created_at",
        )
        .bind(&device_id)
        .bind(&identity_key)
        .bind(&signed_prekey)
        .bind(&signed_prekey_signature)
        .bind(signed_prekey_timestamp)
        .bind(now)
        .fetch_one(pool)
        .await
    }

    pub async fn find_by_device(
        pool: &sqlx::SqlitePool,
        device_id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        sqlx::query_as::<_, PrekeyBundle>(
            "SELECT device_id, identity_key, signed_prekey, 
                    signed_prekey_signature, signed_prekey_timestamp, 
                    created_at
             FROM prekey_bundles
             WHERE device_id = ?",
        )
        .bind(device_id)
        .fetch_optional(pool)
        .await
    }
}

impl OneTimePrekey {
    pub async fn create_batch(
        pool: &sqlx::SqlitePool,
        device_id: String,
        prekeys: Vec<Vec<u8>>,
    ) -> Result<Vec<Self>, sqlx::Error> {
        let now = current_timestamp();
        let mut created_keys = Vec::new();

        for prekey in prekeys {
            let id = uuid::Uuid::new_v4().to_string();
            
            let key = sqlx::query_as::<_, OneTimePrekey>(
                "INSERT INTO one_time_prekeys 
                 (id, device_id, prekey, created_at, consumed_at)
                 VALUES (?, ?, ?, ?, NULL)
                 RETURNING id, device_id, prekey, created_at, consumed_at",
            )
            .bind(&id)
            .bind(&device_id)
            .bind(&prekey)
            .bind(now)
            .fetch_one(pool)
            .await?;

            created_keys.push(key);
        }

        Ok(created_keys)
    }

    pub async fn consume_one(
        pool: &sqlx::SqlitePool,
        device_id: &str,
    ) -> Result<Option<Self>, sqlx::Error> {
        let now = current_timestamp();

        let key = sqlx::query_as::<_, OneTimePrekey>(
            "SELECT id, device_id, prekey, created_at, consumed_at
             FROM one_time_prekeys
             WHERE device_id = ? AND consumed_at IS NULL
             ORDER BY created_at ASC
             LIMIT 1",
        )
        .bind(device_id)
        .fetch_optional(pool)
        .await?;

        if let Some(ref k) = key {
            sqlx::query(
                "UPDATE one_time_prekeys 
                 SET consumed_at = ? 
                 WHERE id = ?",
            )
            .bind(now)
            .bind(&k.id)
            .execute(pool)
            .await?;
        }

        Ok(key)
    }

    pub async fn count_available(
        pool: &sqlx::SqlitePool,
        device_id: &str,
    ) -> Result<i64, sqlx::Error> {
        let result: (i64,) = sqlx::query_as(
            "SELECT COUNT(*) 
             FROM one_time_prekeys 
             WHERE device_id = ? AND consumed_at IS NULL",
        )
        .bind(device_id)
        .fetch_one(pool)
        .await?;

        Ok(result.0)
    }

    pub async fn cleanup_consumed(
        pool: &sqlx::SqlitePool,
        older_than_seconds: i64,
    ) -> Result<u64, sqlx::Error> {
        let cutoff = current_timestamp() - older_than_seconds;

        let result = sqlx::query(
            "DELETE FROM one_time_prekeys 
             WHERE consumed_at IS NOT NULL AND consumed_at < ?",
        )
        .bind(cutoff)
        .execute(pool)
        .await?;

        Ok(result.rows_affected())
    }
}
