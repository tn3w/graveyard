use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use argon2::password_hash::SaltString;
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use rand_core::OsRng;
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;
use std::time::{SystemTime, UNIX_EPOCH};

static JWT_SECRET: OnceLock<Vec<u8>> = OnceLock::new();
const ACCESS_TOKEN_EXPIRATION_SECONDS: u64 = 900;
const REFRESH_TOKEN_EXPIRATION_SECONDS: u64 = 86400 * 30;

pub fn initialize_jwt_secret() {
    JWT_SECRET.get_or_init(|| {
        let secret = std::env::var("JWT_SECRET")
            .unwrap_or_else(|_| {
                tracing::warn!("JWT_SECRET not set, generating random secret");
                use rand_core::RngCore;
                let mut random_bytes = [0u8; 32];
                rand_core::OsRng.fill_bytes(&mut random_bytes);
                random_bytes.iter()
                    .map(|b| format!("{:02x}", b))
                    .collect::<String>()
            });
        
        let secret_bytes = secret.as_bytes();
        if secret_bytes.len() < 32 {
            panic!("JWT_SECRET must be at least 32 bytes long, got {} bytes", secret_bytes.len());
        }
        
        tracing::info!("JWT secret initialized ({} bytes)", secret_bytes.len());
        secret.into_bytes()
    });
}

fn get_jwt_secret() -> &'static [u8] {
    JWT_SECRET.get().expect("JWT secret not initialized")
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub device_id: String,
    pub exp: u64,
    pub token_type: TokenType,
}

#[derive(Debug, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum TokenType {
    Access,
    Refresh,
}

pub fn hash_password(password: &str) -> Result<String, argon2::password_hash::Error> {
    let salt = SaltString::generate(&mut OsRng);
    let argon2 = Argon2::default();
    let password_hash = argon2.hash_password(password.as_bytes(), &salt)?;
    Ok(password_hash.to_string())
}

pub fn verify_password(
    password: &str,
    password_hash: &str,
) -> Result<bool, argon2::password_hash::Error> {
    let parsed_hash = PasswordHash::new(password_hash)?;
    let argon2 = Argon2::default();
    match argon2.verify_password(password.as_bytes(), &parsed_hash) {
        Ok(()) => Ok(true),
        Err(argon2::password_hash::Error::Password) => Ok(false),
        Err(error) => Err(error),
    }
}

#[allow(dead_code)]
pub fn create_token(
    user_id: &str,
    device_id: &str,
) -> Result<String, jsonwebtoken::errors::Error> {
    create_access_token(user_id, device_id)
}

pub fn create_access_token(
    user_id: &str,
    device_id: &str,
) -> Result<String, jsonwebtoken::errors::Error> {
    let expiration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
        + ACCESS_TOKEN_EXPIRATION_SECONDS;

    let claims = Claims {
        sub: user_id.to_string(),
        device_id: device_id.to_string(),
        exp: expiration,
        token_type: TokenType::Access,
    };

    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(get_jwt_secret()),
    )
}

pub fn create_refresh_token(
    user_id: &str,
    device_id: &str,
) -> Result<String, jsonwebtoken::errors::Error> {
    let expiration = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
        + REFRESH_TOKEN_EXPIRATION_SECONDS;

    let claims = Claims {
        sub: user_id.to_string(),
        device_id: device_id.to_string(),
        exp: expiration,
        token_type: TokenType::Refresh,
    };

    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(get_jwt_secret()),
    )
}

pub fn get_refresh_token_expiration() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
        + REFRESH_TOKEN_EXPIRATION_SECONDS
}

pub fn verify_token(token: &str) -> Result<Claims, jsonwebtoken::errors::Error> {
    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(get_jwt_secret()),
        &Validation::default(),
    )?;

    Ok(token_data.claims)
}
