use crate::deployment::errors::AuthError;
use base64::Engine;
use chrono::{DateTime, Duration, Utc};
use rand::RngCore;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Debug, Clone)]
pub struct User {
    pub user_id: String,
    pub username: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone)]
struct ApiToken {
    token_hash: String,
    user_id: String,
    created_at: DateTime<Utc>,
    expires_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Clone)]
struct UserCredentials {
    user_id: String,
    username: String,
    password_hash: String,
    created_at: DateTime<Utc>,
}

pub struct AuthService {
    users: Arc<RwLock<HashMap<String, UserCredentials>>>,
    tokens: Arc<RwLock<HashMap<String, ApiToken>>>,
}

impl AuthService {
    pub fn new() -> Self {
        Self {
            users: Arc::new(RwLock::new(HashMap::new())),
            tokens: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn create_user(
        &self,
        username: String,
        password: String,
    ) -> Result<User, AuthError> {
        if username.is_empty() || password.is_empty() {
            return Err(AuthError::InvalidCredentials);
        }

        let users = self.users.read().await;
        if users.values().any(|user| user.username == username) {
            return Err(AuthError::InvalidCredentials);
        }
        drop(users);

        let user_id = uuid::Uuid::new_v4().to_string();
        let password_hash = Self::hash_password(&password);

        let credentials = UserCredentials {
            user_id: user_id.clone(),
            username: username.clone(),
            password_hash,
            created_at: Utc::now(),
        };

        let mut users = self.users.write().await;
        users.insert(user_id.clone(), credentials);

        Ok(User {
            user_id,
            username,
            created_at: Utc::now(),
        })
    }

    pub async fn authenticate_password(
        &self,
        username: &str,
        password: &str,
    ) -> Result<User, AuthError> {
        let users = self.users.read().await;

        let credentials = users
            .values()
            .find(|user| user.username == username)
            .ok_or(AuthError::InvalidCredentials)?;

        let password_hash = Self::hash_password(password);
        if password_hash != credentials.password_hash {
            return Err(AuthError::InvalidCredentials);
        }

        Ok(User {
            user_id: credentials.user_id.clone(),
            username: credentials.username.clone(),
            created_at: credentials.created_at,
        })
    }

    pub async fn generate_api_token(
        &self,
        user_id: &str,
        expires_in: Option<Duration>,
    ) -> Result<String, AuthError> {
        let users = self.users.read().await;
        if !users.contains_key(user_id) {
            return Err(AuthError::InvalidCredentials);
        }
        drop(users);

        let token = Self::generate_random_token();
        let token_hash = Self::hash_token(&token);

        let expires_at = expires_in.map(|duration| Utc::now() + duration);

        let api_token = ApiToken {
            token_hash: token_hash.clone(),
            user_id: user_id.to_string(),
            created_at: Utc::now(),
            expires_at,
        };

        let mut tokens = self.tokens.write().await;
        tokens.insert(token_hash, api_token);

        Ok(token)
    }

    pub async fn authenticate_token(
        &self,
        token: &str,
    ) -> Result<User, AuthError> {
        let token_hash = Self::hash_token(token);

        let tokens = self.tokens.read().await;
        let api_token =
            tokens.get(&token_hash).ok_or(AuthError::InvalidToken)?;

        if let Some(expires_at) = api_token.expires_at {
            if Utc::now() > expires_at {
                return Err(AuthError::TokenExpired);
            }
        }

        let user_id = api_token.user_id.clone();
        drop(tokens);

        let users = self.users.read().await;
        let credentials =
            users.get(&user_id).ok_or(AuthError::InvalidToken)?;

        Ok(User {
            user_id: credentials.user_id.clone(),
            username: credentials.username.clone(),
            created_at: credentials.created_at,
        })
    }

    pub async fn revoke_token(&self, token: &str) -> Result<(), AuthError> {
        let token_hash = Self::hash_token(token);

        let mut tokens = self.tokens.write().await;
        tokens.remove(&token_hash).ok_or(AuthError::InvalidToken)?;

        Ok(())
    }

    fn hash_password(password: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(password.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    fn hash_token(token: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(token.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    fn generate_random_token() -> String {
        let mut token_bytes = [0u8; 32];
        rand::rngs::OsRng.fill_bytes(&mut token_bytes);
        base64::engine::general_purpose::STANDARD.encode(&token_bytes)
    }
}

impl Default for AuthService {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_create_user() {
        let auth_service = AuthService::new();
        let user = auth_service
            .create_user("testuser".to_string(), "password123".to_string())
            .await
            .unwrap();

        assert_eq!(user.username, "testuser");
    }

    #[tokio::test]
    async fn test_authenticate_password() {
        let auth_service = AuthService::new();
        auth_service
            .create_user("testuser".to_string(), "password123".to_string())
            .await
            .unwrap();

        let user = auth_service
            .authenticate_password("testuser", "password123")
            .await
            .unwrap();

        assert_eq!(user.username, "testuser");
    }

    #[tokio::test]
    async fn test_authenticate_password_wrong_password() {
        let auth_service = AuthService::new();
        auth_service
            .create_user("testuser".to_string(), "password123".to_string())
            .await
            .unwrap();

        let result = auth_service
            .authenticate_password("testuser", "wrongpassword")
            .await;

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_generate_and_authenticate_token() {
        let auth_service = AuthService::new();
        let user = auth_service
            .create_user("testuser".to_string(), "password123".to_string())
            .await
            .unwrap();

        let token = auth_service
            .generate_api_token(&user.user_id, None)
            .await
            .unwrap();

        let authenticated_user =
            auth_service.authenticate_token(&token).await.unwrap();

        assert_eq!(authenticated_user.user_id, user.user_id);
    }

    #[tokio::test]
    async fn test_revoke_token() {
        let auth_service = AuthService::new();
        let user = auth_service
            .create_user("testuser".to_string(), "password123".to_string())
            .await
            .unwrap();

        let token = auth_service
            .generate_api_token(&user.user_id, None)
            .await
            .unwrap();

        auth_service.revoke_token(&token).await.unwrap();

        let result = auth_service.authenticate_token(&token).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_token_expiration() {
        let auth_service = AuthService::new();
        let user = auth_service
            .create_user("testuser".to_string(), "password123".to_string())
            .await
            .unwrap();

        let token = auth_service
            .generate_api_token(
                &user.user_id,
                Some(Duration::milliseconds(-1)),
            )
            .await
            .unwrap();

        let result = auth_service.authenticate_token(&token).await;
        assert!(matches!(result, Err(AuthError::TokenExpired)));
    }
}
