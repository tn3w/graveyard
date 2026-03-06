use argon2::{
    password_hash::{PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2, Algorithm, Version, Params,
};
use jsonwebtoken::{encode, decode, Header, Validation, EncodingKey, DecodingKey};
use rand::rngs::OsRng;
use totp_rs::{TOTP, Algorithm as TotpAlgorithm, Secret};
use crate::models::{Claims, SessionClaims};

const ACCESS_TOKEN_EXPIRY: i64 = 900;
const SESSION_TOKEN_EXPIRY: i64 = 300;

pub fn hash_password(password: &str) -> Result<String, argon2::password_hash::Error> {
    let params = Params::new(19456, 2, 1, None)?;
    let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, params);
    let salt = SaltString::generate(&mut OsRng);
    let hash = argon2.hash_password(password.as_bytes(), &salt)?;
    Ok(hash.to_string())
}

pub fn verify_password(
    password: &str,
    hash: &str
) -> Result<bool, argon2::password_hash::Error> {
    let parsed_hash = PasswordHash::new(hash)?;
    let argon2 = Argon2::default();
    Ok(argon2.verify_password(password.as_bytes(), &parsed_hash).is_ok())
}

pub fn generate_totp_secret() -> String {
    use rand::RngCore;
    let mut secret = [0u8; 20];
    OsRng.fill_bytes(&mut secret);
    Secret::Raw(secret.to_vec()).to_encoded().to_string()
}

pub fn verify_totp(secret: &str, code: &str) -> bool {
    if code.len() != 6 || !code.chars().all(|c| c.is_numeric()) {
        return false;
    }
    
    let totp = match TOTP::new(
        TotpAlgorithm::SHA1,
        6,
        1,
        30,
        Secret::Encoded(secret.to_string()).to_bytes().unwrap(),
        None,
        "clouded.tn3w.dev".to_string(),
    ) {
        Ok(t) => t,
        Err(_) => return false,
    };
    
    match totp.check_current(code) {
        Ok(valid) => valid,
        Err(_) => false,
    }
}

pub fn generate_totp_uri(secret: &str, username: &str, issuer: &str) -> String {
    let totp = TOTP::new(
        TotpAlgorithm::SHA1,
        6,
        1,
        30,
        Secret::Encoded(secret.to_string()).to_bytes().unwrap(),
        Some(username.to_string()),
        issuer.to_string(),
    ).unwrap();
    
    totp.get_url()
}

pub fn create_access_token(
    _user_id: i64,
    username: &str,
    secret: &str
) -> Result<String, jsonwebtoken::errors::Error> {
    let now = chrono::Utc::now().timestamp();
    let claims = Claims {
        sub: username.to_string(),
        exp: now + ACCESS_TOKEN_EXPIRY,
        iat: now,
    };
    
    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes())
    )
}

pub fn create_refresh_token() -> String {
    uuid::Uuid::new_v4().to_string()
}

pub fn create_session_token(
    user_id: i64,
    username: &str,
    secret: &str
) -> Result<String, jsonwebtoken::errors::Error> {
    let now = chrono::Utc::now().timestamp();
    let claims = SessionClaims {
        user_id,
        username: username.to_string(),
        step1_complete: true,
        exp: now + SESSION_TOKEN_EXPIRY,
    };
    
    encode(
        &Header::default(),
        &claims,
        &EncodingKey::from_secret(secret.as_bytes())
    )
}

pub fn verify_session_token(
    token: &str,
    secret: &str
) -> Result<SessionClaims, jsonwebtoken::errors::Error> {
    let validation = Validation::default();
    let token_data = decode::<SessionClaims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation
    )?;
    
    Ok(token_data.claims)
}

pub fn verify_access_token(
    token: &str,
    secret: &str
) -> Result<Claims, jsonwebtoken::errors::Error> {
    let validation = Validation::default();
    let token_data = decode::<Claims>(
        token,
        &DecodingKey::from_secret(secret.as_bytes()),
        &validation
    )?;
    
    Ok(token_data.claims)
}

pub fn validate_password_strength(password: &str) -> Result<(), String> {
    if password.len() < 12 {
        return Err("Password must be at least 12 characters".to_string());
    }
    
    if password.len() > 128 {
        return Err("Password must not exceed 128 characters".to_string());
    }
    
    let has_uppercase = password.chars().any(|c| c.is_uppercase());
    let has_lowercase = password.chars().any(|c| c.is_lowercase());
    let has_digit = password.chars().any(|c| c.is_numeric());
    let has_special = password.chars().any(|c| !c.is_alphanumeric());
    
    if !has_uppercase || !has_lowercase || !has_digit || !has_special {
        return Err(
            "Password must contain uppercase, lowercase, digit, and special character"
                .to_string()
        );
    }
    
    Ok(())
}

pub fn validate_username(username: &str) -> Result<(), String> {
    if username.len() < 3 {
        return Err("Username must be at least 3 characters".to_string());
    }
    
    if username.len() > 32 {
        return Err("Username must not exceed 32 characters".to_string());
    }
    
    if !username.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '-') {
        return Err("Username can only contain alphanumeric, underscore, hyphen"
            .to_string());
    }
    
    Ok(())
}
