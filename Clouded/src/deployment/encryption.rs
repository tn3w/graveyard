use crate::deployment::errors::EncryptionError;
use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Key, Nonce,
};
use rand::RngCore;
use std::fs;
use std::path::Path;

const KEY_SIZE: usize = 32;
const NONCE_SIZE: usize = 12;

pub struct EncryptionService {
    key: Key<Aes256Gcm>,
}

impl EncryptionService {
    pub fn new(key: &[u8]) -> Result<Self, EncryptionError> {
        if key.len() != KEY_SIZE {
            return Err(EncryptionError::InvalidKey);
        }

        let key_array: [u8; KEY_SIZE] = key
            .try_into()
            .map_err(|_| EncryptionError::InvalidKey)?;

        Ok(Self {
            key: Key::<Aes256Gcm>::from(key_array),
        })
    }

    pub fn from_file(path: &Path) -> Result<Self, EncryptionError> {
        let key_bytes = fs::read(path).map_err(|error| {
            EncryptionError::KeyGenerationFailed(format!(
                "Failed to read key file: {}",
                error
            ))
        })?;

        Self::new(&key_bytes)
    }

    pub fn generate_key() -> Result<Vec<u8>, EncryptionError> {
        let mut key = vec![0u8; KEY_SIZE];
        OsRng.fill_bytes(&mut key);
        Ok(key)
    }

    pub fn save_key_to_file(
        key: &[u8],
        path: &Path,
    ) -> Result<(), EncryptionError> {
        fs::write(path, key).map_err(|error| {
            EncryptionError::KeyGenerationFailed(format!(
                "Failed to write key file: {}",
                error
            ))
        })?;

        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let permissions = fs::Permissions::from_mode(0o600);
            fs::set_permissions(path, permissions).map_err(|error| {
                EncryptionError::KeyGenerationFailed(format!(
                    "Failed to set key file permissions: {}",
                    error
                ))
            })?;
        }

        Ok(())
    }

    pub fn encrypt_credential(
        &self,
        plaintext: &str,
    ) -> Result<Vec<u8>, EncryptionError> {
        let cipher = Aes256Gcm::new(&self.key);

        let mut nonce_bytes = [0u8; NONCE_SIZE];
        OsRng.fill_bytes(&mut nonce_bytes);
        let nonce = Nonce::from_slice(&nonce_bytes);

        let ciphertext = cipher
            .encrypt(nonce, plaintext.as_bytes())
            .map_err(|error| {
                EncryptionError::EncryptionFailed(format!(
                    "AES-GCM encryption failed: {}",
                    error
                ))
            })?;

        let mut result = Vec::with_capacity(NONCE_SIZE + ciphertext.len());
        result.extend_from_slice(&nonce_bytes);
        result.extend_from_slice(&ciphertext);

        Ok(result)
    }

    pub fn decrypt_credential(
        &self,
        encrypted_data: &[u8],
    ) -> Result<String, EncryptionError> {
        if encrypted_data.len() < NONCE_SIZE {
            return Err(EncryptionError::DecryptionFailed(
                "Encrypted data too short".to_string(),
            ));
        }

        let (nonce_bytes, ciphertext) = encrypted_data.split_at(NONCE_SIZE);
        let nonce = Nonce::from_slice(nonce_bytes);

        let cipher = Aes256Gcm::new(&self.key);

        let plaintext_bytes =
            cipher.decrypt(nonce, ciphertext).map_err(|error| {
                EncryptionError::DecryptionFailed(format!(
                    "AES-GCM decryption failed: {}",
                    error
                ))
            })?;

        String::from_utf8(plaintext_bytes).map_err(|error| {
            EncryptionError::DecryptionFailed(format!(
                "Invalid UTF-8 in decrypted data: {}",
                error
            ))
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let key = EncryptionService::generate_key().unwrap();
        let service = EncryptionService::new(&key).unwrap();

        let plaintext = "my-secret-token";
        let encrypted = service.encrypt_credential(plaintext).unwrap();
        let decrypted = service.decrypt_credential(&encrypted).unwrap();

        assert_eq!(plaintext, decrypted);
    }

    #[test]
    fn test_encrypted_data_does_not_contain_plaintext() {
        let key = EncryptionService::generate_key().unwrap();
        let service = EncryptionService::new(&key).unwrap();

        let plaintext = "my-secret-token";
        let encrypted = service.encrypt_credential(plaintext).unwrap();

        let encrypted_string = String::from_utf8_lossy(&encrypted);
        assert!(!encrypted_string.contains(plaintext));
    }

    #[test]
    fn test_empty_credential() {
        let key = EncryptionService::generate_key().unwrap();
        let service = EncryptionService::new(&key).unwrap();

        let plaintext = "";
        let encrypted = service.encrypt_credential(plaintext).unwrap();
        let decrypted = service.decrypt_credential(&encrypted).unwrap();

        assert_eq!(plaintext, decrypted);
    }

    #[test]
    fn test_long_credential() {
        let key = EncryptionService::generate_key().unwrap();
        let service = EncryptionService::new(&key).unwrap();

        let plaintext = "a".repeat(10000);
        let encrypted = service.encrypt_credential(&plaintext).unwrap();
        let decrypted = service.decrypt_credential(&encrypted).unwrap();

        assert_eq!(plaintext, decrypted);
    }

    #[test]
    fn test_special_characters() {
        let key = EncryptionService::generate_key().unwrap();
        let service = EncryptionService::new(&key).unwrap();

        let plaintext = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~";
        let encrypted = service.encrypt_credential(plaintext).unwrap();
        let decrypted = service.decrypt_credential(&encrypted).unwrap();

        assert_eq!(plaintext, decrypted);
    }

    #[test]
    fn test_invalid_key_size() {
        let key = vec![0u8; 16];
        let result = EncryptionService::new(&key);
        assert!(result.is_err());
    }

    #[test]
    fn test_decrypt_invalid_data() {
        let key = EncryptionService::generate_key().unwrap();
        let service = EncryptionService::new(&key).unwrap();

        let invalid_data = vec![0u8; 5];
        let result = service.decrypt_credential(&invalid_data);
        assert!(result.is_err());
    }
}
