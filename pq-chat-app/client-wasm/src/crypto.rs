use serde::{Deserialize, Serialize};
use pqc_kyber::*;
use x25519_dalek::{PublicKey as X25519Public, StaticSecret};
use chacha20poly1305::{
    aead::{Aead, KeyInit, Payload},
    ChaCha20Poly1305,
};
use hkdf::Hkdf;
use sha2::Sha256;
use rand_core::OsRng;

const MESSAGE_KEY_LABEL: &[u8] = b"ChatAppMessageKey";

#[derive(Serialize, Deserialize, Clone)]
pub struct KeyPair {
    pub public_key: Vec<u8>,
    pub secret_key: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
pub struct EncryptedMessage {
    pub ciphertext: Vec<u8>,
    pub nonce: Vec<u8>,
    pub ephemeral_public: Vec<u8>,
}

pub struct CryptoEngine {
    x25519_secret: Vec<u8>,
    kyber_secret: Vec<u8>,
}

impl CryptoEngine {
    pub fn new() -> Result<Self, String> {
        let x25519_secret = StaticSecret::random_from_rng(OsRng);
        let kyber_keys = keypair(&mut OsRng)
            .map_err(|_| "Kyber key generation failed".to_string())?;
        
        Ok(CryptoEngine {
            x25519_secret: x25519_secret.to_bytes().to_vec(),
            kyber_secret: kyber_keys.secret.to_vec(),
        })
    }

    pub fn get_public_keys(&self) -> Result<KeyPair, String> {
        let x25519_secret = StaticSecret::from(
            <[u8; 32]>::try_from(&self.x25519_secret[..])
                .map_err(|_| "Invalid secret key".to_string())?
        );
        let x25519_public = X25519Public::from(&x25519_secret);
        
        let kyber_secret = SecretKey::try_from(&self.kyber_secret[..])
            .map_err(|_| "Invalid Kyber secret".to_string())?;
        let kyber_public = public(&kyber_secret);
        
        Ok(KeyPair {
            public_key: [
                x25519_public.as_bytes().to_vec(),
                kyber_public.to_vec()
            ].concat(),
            secret_key: vec![],
        })
    }

    pub fn encrypt_message(
        &self,
        plaintext: &str,
        recipient_public_keys: &KeyPair,
    ) -> Result<EncryptedMessage, String> {
        if recipient_public_keys.public_key.len() < 32 + KYBER_PUBLICKEYBYTES {
            return Err("Invalid public key length".to_string());
        }
        
        let x25519_public = X25519Public::from(
            <[u8; 32]>::try_from(&recipient_public_keys.public_key[..32])
                .map_err(|_| "Invalid X25519 public".to_string())?
        );
        
        let kyber_public = PublicKey::try_from(
            &recipient_public_keys.public_key[32..32 + KYBER_PUBLICKEYBYTES]
        ).map_err(|_| "Invalid Kyber public".to_string())?;
        
        let ephemeral_secret = StaticSecret::random_from_rng(OsRng);
        let ephemeral_public = X25519Public::from(&ephemeral_secret);
        let x25519_shared = ephemeral_secret.diffie_hellman(&x25519_public);
        
        let encapsulated = encapsulate(&kyber_public, &mut OsRng)
            .map_err(|_| "Kyber encapsulation failed".to_string())?;
        
        let combined_secret = [
            x25519_shared.as_bytes(),
            encapsulated.1.as_ref()
        ].concat();
        
        let hkdf = Hkdf::<Sha256>::new(None, &combined_secret);
        let mut message_key = [0u8; 32];
        hkdf.expand(MESSAGE_KEY_LABEL, &mut message_key)
            .map_err(|_| "Key derivation failed".to_string())?;
        
        let cipher = ChaCha20Poly1305::new(&message_key.into());
        let nonce = generate_nonce();
        
        let payload = Payload {
            msg: plaintext.as_bytes(),
            aad: &encapsulated.0,
        };
        
        let ciphertext = cipher.encrypt(&nonce.into(), payload)
            .map_err(|_| "Encryption failed".to_string())?;
        
        Ok(EncryptedMessage {
            ciphertext,
            nonce: nonce.to_vec(),
            ephemeral_public: [
                ephemeral_public.as_bytes().to_vec(),
                encapsulated.0.to_vec()
            ].concat(),
        })
    }

    pub fn decrypt_message(
        &self,
        encrypted: &EncryptedMessage,
    ) -> Result<String, String> {
        if encrypted.ephemeral_public.len() < 32 + KYBER_CIPHERTEXTBYTES {
            return Err("Invalid ephemeral public length".to_string());
        }
        
        let ephemeral_public = X25519Public::from(
            <[u8; 32]>::try_from(&encrypted.ephemeral_public[..32])
                .map_err(|_| "Invalid ephemeral public".to_string())?
        );
        
        let kyber_ciphertext_bytes = 
            &encrypted.ephemeral_public[32..32 + KYBER_CIPHERTEXTBYTES];
        
        let x25519_secret = StaticSecret::from(
            <[u8; 32]>::try_from(&self.x25519_secret[..])
                .map_err(|_| "Invalid secret key".to_string())?
        );
        let x25519_shared = x25519_secret.diffie_hellman(&ephemeral_public);
        
        let kyber_secret = SecretKey::try_from(&self.kyber_secret[..])
            .map_err(|_| "Invalid Kyber secret".to_string())?;
        
        let kyber_ciphertext_array: [u8; KYBER_CIPHERTEXTBYTES] = 
            kyber_ciphertext_bytes.try_into()
                .map_err(|_| "Invalid ciphertext size".to_string())?;
        
        let kyber_shared = decapsulate(&kyber_ciphertext_array, &kyber_secret)
            .map_err(|_| "Kyber decapsulation failed".to_string())?;
        
        let combined_secret = [
            x25519_shared.as_bytes(),
            kyber_shared.as_ref()
        ].concat();
        
        let hkdf = Hkdf::<Sha256>::new(None, &combined_secret);
        let mut message_key = [0u8; 32];
        hkdf.expand(MESSAGE_KEY_LABEL, &mut message_key)
            .map_err(|_| "Key derivation failed".to_string())?;
        
        let cipher = ChaCha20Poly1305::new(&message_key.into());
        let nonce = <[u8; 12]>::try_from(&encrypted.nonce[..])
            .map_err(|_| "Invalid nonce".to_string())?;
        
        let payload = Payload {
            msg: &encrypted.ciphertext,
            aad: kyber_ciphertext_bytes,
        };
        
        let plaintext = cipher.decrypt(&nonce.into(), payload)
            .map_err(|_| "Decryption failed".to_string())?;
        
        String::from_utf8(plaintext)
            .map_err(|_| "Invalid UTF-8".to_string())
    }
}

fn generate_nonce() -> [u8; 12] {
    let mut nonce = [0u8; 12];
    getrandom::getrandom(&mut nonce).expect("Failed to generate nonce");
    nonce
}
