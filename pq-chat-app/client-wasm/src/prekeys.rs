use serde::{Deserialize, Serialize};
use pqc_kyber::*;
use x25519_dalek::{PublicKey as X25519Public, StaticSecret};
use ed25519_dalek::{Signer, SigningKey, VerifyingKey, Verifier, Signature};
use rand_core::OsRng;

#[derive(Serialize, Deserialize, Clone)]
pub struct IdentityKeyPair {
    pub public_key: Vec<u8>,
    pub secret_key: Vec<u8>,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct SignedPrekey {
    pub public_key: Vec<u8>,
    pub secret_key: Vec<u8>,
    pub signature: Vec<u8>,
    pub timestamp: i64,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct OneTimePrekeyPair {
    pub public_key: Vec<u8>,
    pub secret_key: Vec<u8>,
}

#[derive(Serialize, Deserialize)]
pub struct PrekeyBundle {
    pub identity_key: Vec<u8>,
    pub signed_prekey: Vec<u8>,
    pub signed_prekey_signature: Vec<u8>,
    pub signed_prekey_timestamp: i64,
    pub one_time_prekeys: Vec<Vec<u8>>,
}

pub fn generate_identity_keypair() -> Result<IdentityKeyPair, String> {
    let x25519_secret = StaticSecret::random_from_rng(OsRng);
    let x25519_public = X25519Public::from(&x25519_secret);
    
    let kyber_keys = keypair(&mut OsRng)
        .map_err(|_| "Kyber key generation failed".to_string())?;
    
    let signing_key = SigningKey::generate(&mut OsRng);
    let verifying_key = signing_key.verifying_key();
    
    let public_key = [
        x25519_public.as_bytes().to_vec(),
        kyber_keys.public.to_vec(),
        verifying_key.to_bytes().to_vec(),
    ].concat();
    
    let secret_key = [
        x25519_secret.to_bytes().to_vec(),
        kyber_keys.secret.to_vec(),
        signing_key.to_bytes().to_vec(),
    ].concat();
    
    Ok(IdentityKeyPair {
        public_key,
        secret_key,
    })
}

pub fn generate_signed_prekey(
    identity_secret: &[u8],
) -> Result<SignedPrekey, String> {
    let expected_len = 32 + KYBER_SECRETKEYBYTES + 32;
    if identity_secret.len() != expected_len {
        return Err(format!(
            "Identity secret key wrong length: {} (expected {})",
            identity_secret.len(),
            expected_len
        ));
    }
    
    let x25519_secret = StaticSecret::random_from_rng(OsRng);
    let x25519_public = X25519Public::from(&x25519_secret);
    
    let kyber_keys = keypair(&mut OsRng)
        .map_err(|_| "Kyber key generation failed".to_string())?;
    
    let public_key = [
        x25519_public.as_bytes().to_vec(),
        kyber_keys.public.to_vec(),
    ].concat();
    
    let secret_key = [
        x25519_secret.to_bytes().to_vec(),
        kyber_keys.secret.to_vec(),
    ].concat();
    
    let signing_offset = 32 + KYBER_SECRETKEYBYTES;
    let signing_key_bytes: [u8; 32] = identity_secret[signing_offset..signing_offset + 32]
        .try_into()
        .map_err(|_| "Invalid signing key".to_string())?;
    
    let signing_key = SigningKey::from_bytes(&signing_key_bytes);
    let signature = signing_key.sign(&public_key);
    
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|_| "System time error".to_string())?
        .as_secs() as i64;
    
    Ok(SignedPrekey {
        public_key,
        secret_key,
        signature: signature.to_bytes().to_vec(),
        timestamp,
    })
}

pub fn verify_signed_prekey(
    identity_public: &[u8],
    signed_prekey_public: &[u8],
    signature: &[u8],
) -> Result<bool, String> {
    let expected_len = 32 + KYBER_PUBLICKEYBYTES + 32;
    if identity_public.len() != expected_len {
        return Err(format!(
            "Identity public key wrong length: {} (expected {})",
            identity_public.len(),
            expected_len
        ));
    }
    
    if signature.len() != 64 {
        return Err("Invalid signature length".to_string());
    }
    
    let verifying_offset = 32 + KYBER_PUBLICKEYBYTES;
    let verifying_key_bytes: [u8; 32] = identity_public[verifying_offset..verifying_offset + 32]
        .try_into()
        .map_err(|_| "Invalid verifying key bytes".to_string())?;
    
    let verifying_key = VerifyingKey::from_bytes(&verifying_key_bytes)
        .map_err(|_| "Invalid verifying key".to_string())?;
    
    let signature_bytes: [u8; 64] = signature
        .try_into()
        .map_err(|_| "Invalid signature".to_string())?;
    
    let signature = Signature::from_bytes(&signature_bytes);
    
    match verifying_key.verify(signed_prekey_public, &signature) {
        Ok(_) => Ok(true),
        Err(_) => Ok(false),
    }
}

pub fn generate_one_time_prekeys(
    count: usize,
) -> Result<Vec<OneTimePrekeyPair>, String> {
    if count > 100 {
        return Err("Cannot generate more than 100 prekeys".to_string());
    }
    
    let mut prekeys = Vec::with_capacity(count);
    
    for _ in 0..count {
        let x25519_secret = StaticSecret::random_from_rng(OsRng);
        let x25519_public = X25519Public::from(&x25519_secret);
        
        let kyber_keys = keypair(&mut OsRng)
            .map_err(|_| "Kyber key generation failed".to_string())?;
        
        let public_key = [
            x25519_public.as_bytes().to_vec(),
            kyber_keys.public.to_vec(),
        ].concat();
        
        let secret_key = [
            x25519_secret.to_bytes().to_vec(),
            kyber_keys.secret.to_vec(),
        ].concat();
        
        prekeys.push(OneTimePrekeyPair {
            public_key,
            secret_key,
        });
    }
    
    Ok(prekeys)
}

pub fn create_prekey_bundle(
    identity_keypair: &IdentityKeyPair,
    signed_prekey: &SignedPrekey,
    one_time_prekeys: &[OneTimePrekeyPair],
) -> PrekeyBundle {
    PrekeyBundle {
        identity_key: identity_keypair.public_key.clone(),
        signed_prekey: signed_prekey.public_key.clone(),
        signed_prekey_signature: signed_prekey.signature.clone(),
        signed_prekey_timestamp: signed_prekey.timestamp,
        one_time_prekeys: one_time_prekeys
            .iter()
            .map(|k| k.public_key.clone())
            .collect(),
    }
}
