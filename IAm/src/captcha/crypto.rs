//! Stateless CAPTCHA cryptography - single verification at end
//! Token format: nonce,expires_at.encrypted_scenes.signature
//! - nonce,expires_at: visible, used for display and validation
//! - encrypted_scenes: only the correct scene indices (encrypted)
//! - signature: HMAC over nonce,expires_at.encrypted_scenes.site_hash

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use hmac::{Hmac, Mac};
use rand::Rng;
use sha2::{Digest, Sha256};

pub struct CaptchaCrypto {
    cipher: Aes256Gcm,
    hmac_key: [u8; 32],
}

impl CaptchaCrypto {
    pub fn new(secret_key: &str) -> Self {
        let mut hasher = Sha256::new();
        hasher.update(secret_key.as_bytes());
        hasher.update(b"captcha-aes");
        let aes_key = hasher.finalize();

        let mut hasher = Sha256::new();
        hasher.update(secret_key.as_bytes());
        hasher.update(b"captcha-hmac");
        let hmac_key: [u8; 32] = hasher.finalize().into();

        Self {
            cipher: Aes256Gcm::new_from_slice(&aes_key).unwrap(),
            hmac_key,
        }
    }

    /// Create challenge token: nonce,expires_at.encrypted_scenes.signature
    /// - Only scenes are encrypted
    /// - site_hash and expires_at are signed but not encrypted
    pub fn create_token(&self, correct_scenes: &[u8], site_key: &str, ttl_secs: u64) -> String {
        let mut rng = rand::rng();
        let nonce_bytes: [u8; 12] = rng.random();
        let expires_at = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs()
            + ttl_secs;

        // Encrypt only the scenes
        let scenes_str: String = correct_scenes
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>()
            .join(",");
        let nonce = Nonce::from_slice(&nonce_bytes);
        let ciphertext = self.cipher.encrypt(nonce, scenes_str.as_bytes()).unwrap();
        let encrypted = URL_SAFE_NO_PAD.encode(&ciphertext);

        // Visible part: nonce,expires_at
        let nonce_b64 = URL_SAFE_NO_PAD.encode(&nonce_bytes);
        let visible = format!("{},{}", nonce_b64, expires_at);

        // Signature over visible.encrypted.site_hash (site_hash is signed but not in token)
        let site_hash = Self::hash_site(site_key);
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&self.hmac_key).unwrap();
        mac.update(visible.as_bytes());
        mac.update(b".");
        mac.update(encrypted.as_bytes());
        mac.update(b".");
        mac.update(&site_hash);
        let sig = URL_SAFE_NO_PAD.encode(&mac.finalize().into_bytes()[..16]);

        format!("{}.{}.{}", visible, encrypted, sig)
    }

    /// Verify and extract correct scenes from token
    pub fn verify_token(&self, token: &str, site_key: &str) -> Result<Vec<u8>, &'static str> {
        let parts: Vec<&str> = token.split('.').collect();
        if parts.len() != 3 {
            return Err("Invalid token format");
        }

        let (visible, encrypted, sig) = (parts[0], parts[1], parts[2]);

        // Parse visible part: nonce,expires_at
        let visible_parts: Vec<&str> = visible.split(',').collect();
        if visible_parts.len() != 2 {
            return Err("Invalid visible format");
        }
        let (nonce_b64, expires_str) = (visible_parts[0], visible_parts[1]);

        // Check expiry first (before expensive crypto)
        let expires_at: u64 = expires_str.parse().map_err(|_| "Invalid expiry")?;
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        if now > expires_at {
            return Err("Token expired");
        }

        // Verify signature (includes site_hash)
        let site_hash = Self::hash_site(site_key);
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&self.hmac_key).unwrap();
        mac.update(visible.as_bytes());
        mac.update(b".");
        mac.update(encrypted.as_bytes());
        mac.update(b".");
        mac.update(&site_hash);
        let expected_sig = URL_SAFE_NO_PAD.encode(&mac.finalize().into_bytes()[..16]);
        if sig != expected_sig {
            return Err("Invalid signature");
        }

        // Decrypt scenes
        let nonce_bytes = URL_SAFE_NO_PAD
            .decode(nonce_b64)
            .map_err(|_| "Invalid nonce")?;
        let ciphertext = URL_SAFE_NO_PAD
            .decode(encrypted)
            .map_err(|_| "Invalid ciphertext")?;
        let nonce = Nonce::from_slice(&nonce_bytes);
        let plaintext = self
            .cipher
            .decrypt(nonce, ciphertext.as_slice())
            .map_err(|_| "Decryption failed")?;
        let scenes_str = String::from_utf8(plaintext).map_err(|_| "Invalid payload")?;

        // Parse scenes
        let scenes: Result<Vec<u8>, _> = scenes_str.split(',').map(|s| s.parse()).collect();
        scenes.map_err(|_| "Invalid scenes")
    }

    /// Generate verified token after successful captcha completion
    pub fn generate_verified_token(&self, site_key: &str) -> String {
        let mut rng = rand::rng();
        let nonce_bytes: [u8; 12] = rng.random();
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        // Encrypt verification marker
        let payload = "verified";
        let nonce = Nonce::from_slice(&nonce_bytes);
        let ciphertext = self.cipher.encrypt(nonce, payload.as_bytes()).unwrap();

        let nonce_b64 = URL_SAFE_NO_PAD.encode(&nonce_bytes);
        let encrypted = URL_SAFE_NO_PAD.encode(&ciphertext);
        let visible = format!("{},{}", nonce_b64, now);

        // Sign with site_hash
        let site_hash = Self::hash_site(site_key);
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&self.hmac_key).unwrap();
        mac.update(visible.as_bytes());
        mac.update(b".");
        mac.update(encrypted.as_bytes());
        mac.update(b".");
        mac.update(&site_hash);
        let sig = URL_SAFE_NO_PAD.encode(&mac.finalize().into_bytes()[..16]);

        format!("{}.{}.{}", visible, encrypted, sig)
    }

    /// Verify a completed captcha token (backend verification)
    pub fn verify_completed(
        &self,
        token: &str,
        site_key: &str,
        max_age: u64,
    ) -> Result<bool, &'static str> {
        let parts: Vec<&str> = token.split('.').collect();
        if parts.len() != 3 {
            return Err("Invalid format");
        }

        let (visible, encrypted, sig) = (parts[0], parts[1], parts[2]);

        // Parse visible: nonce,timestamp
        let visible_parts: Vec<&str> = visible.split(',').collect();
        if visible_parts.len() != 2 {
            return Err("Invalid visible format");
        }
        let (nonce_b64, timestamp_str) = (visible_parts[0], visible_parts[1]);

        // Check age
        let timestamp: u64 = timestamp_str.parse().map_err(|_| "Invalid timestamp")?;
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        if now > timestamp + max_age {
            return Err("Token expired");
        }

        // Verify signature
        let site_hash = Self::hash_site(site_key);
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&self.hmac_key).unwrap();
        mac.update(visible.as_bytes());
        mac.update(b".");
        mac.update(encrypted.as_bytes());
        mac.update(b".");
        mac.update(&site_hash);
        let expected_sig = URL_SAFE_NO_PAD.encode(&mac.finalize().into_bytes()[..16]);
        if sig != expected_sig {
            return Err("Invalid signature");
        }

        // Decrypt and verify marker
        let nonce_bytes = URL_SAFE_NO_PAD
            .decode(nonce_b64)
            .map_err(|_| "Invalid nonce")?;
        let ciphertext = URL_SAFE_NO_PAD
            .decode(encrypted)
            .map_err(|_| "Invalid data")?;
        let nonce = Nonce::from_slice(&nonce_bytes);
        let plaintext = self
            .cipher
            .decrypt(nonce, ciphertext.as_slice())
            .map_err(|_| "Decryption failed")?;
        let payload = String::from_utf8(plaintext).map_err(|_| "Invalid payload")?;

        // Accept both "verified" and "passive:score" formats
        if payload == "verified" || payload.starts_with("passive:") {
            return Ok(true);
        }

        Err("Not verified")
    }

    /// Generate verified token for passive mode with encrypted score
    pub fn generate_passive_verified_token(&self, site_key: &str, score: f64) -> String {
        let mut rng = rand::rng();
        let nonce_bytes: [u8; 12] = rng.random();
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        // Encrypt verification marker with score
        let payload = format!("passive:{:.4}", score);
        let nonce = Nonce::from_slice(&nonce_bytes);
        let ciphertext = self.cipher.encrypt(nonce, payload.as_bytes()).unwrap();

        let nonce_b64 = URL_SAFE_NO_PAD.encode(&nonce_bytes);
        let encrypted = URL_SAFE_NO_PAD.encode(&ciphertext);
        let visible = format!("{},{}", nonce_b64, now);

        // Sign with site_hash
        let site_hash = Self::hash_site(site_key);
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&self.hmac_key).unwrap();
        mac.update(visible.as_bytes());
        mac.update(b".");
        mac.update(encrypted.as_bytes());
        mac.update(b".");
        mac.update(&site_hash);
        let sig = URL_SAFE_NO_PAD.encode(&mac.finalize().into_bytes()[..16]);

        format!("{}.{}.{}", visible, encrypted, sig)
    }

    /// Verify a passive token and extract the score (for backend verification with API key)
    pub fn verify_passive_token(
        &self,
        token: &str,
        site_key: &str,
        max_age: u64,
    ) -> Result<f64, &'static str> {
        let parts: Vec<&str> = token.split('.').collect();
        if parts.len() != 3 {
            return Err("Invalid format");
        }

        let (visible, encrypted, sig) = (parts[0], parts[1], parts[2]);

        // Parse visible: nonce,timestamp
        let visible_parts: Vec<&str> = visible.split(',').collect();
        if visible_parts.len() != 2 {
            return Err("Invalid visible format");
        }
        let (nonce_b64, timestamp_str) = (visible_parts[0], visible_parts[1]);

        // Check age
        let timestamp: u64 = timestamp_str.parse().map_err(|_| "Invalid timestamp")?;
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        if now > timestamp + max_age {
            return Err("Token expired");
        }

        // Verify signature
        let site_hash = Self::hash_site(site_key);
        let mut mac = <Hmac<Sha256> as Mac>::new_from_slice(&self.hmac_key).unwrap();
        mac.update(visible.as_bytes());
        mac.update(b".");
        mac.update(encrypted.as_bytes());
        mac.update(b".");
        mac.update(&site_hash);
        let expected_sig = URL_SAFE_NO_PAD.encode(&mac.finalize().into_bytes()[..16]);
        if sig != expected_sig {
            return Err("Invalid signature");
        }

        // Decrypt and extract score
        let nonce_bytes = URL_SAFE_NO_PAD
            .decode(nonce_b64)
            .map_err(|_| "Invalid nonce")?;
        let ciphertext = URL_SAFE_NO_PAD
            .decode(encrypted)
            .map_err(|_| "Invalid data")?;
        let nonce = Nonce::from_slice(&nonce_bytes);
        let plaintext = self
            .cipher
            .decrypt(nonce, ciphertext.as_slice())
            .map_err(|_| "Decryption failed")?;
        let payload = String::from_utf8(plaintext).map_err(|_| "Invalid payload")?;

        // Parse passive:score format
        if payload.starts_with("passive:") {
            let score_str = &payload[8..];
            return score_str.parse().map_err(|_| "Invalid score");
        }

        // Regular verified token has no score
        if payload == "verified" {
            return Ok(0.0); // Return 0 score for visual captcha completions
        }

        Err("Not a passive token")
    }

    fn hash_site(site_key: &str) -> [u8; 8] {
        let mut hasher = Sha256::new();
        hasher.update(site_key.as_bytes());
        let hash = hasher.finalize();
        let mut result = [0u8; 8];
        result.copy_from_slice(&hash[..8]);
        result
    }
}
