use serde::{Deserialize, Serialize};
use pqc_kyber::*;
use x25519_dalek::{PublicKey as X25519Public, StaticSecret};
use hkdf::Hkdf;
use sha2::Sha256;
use rand_core::OsRng;

const X3DH_INFO: &[u8] = b"ChatAppX3DH";

#[derive(Serialize, Deserialize, Clone)]
pub struct X3DHInitiatorKeys {
    pub identity_secret: Vec<u8>,
    pub ephemeral_secret: Vec<u8>,
    pub ephemeral_public: Vec<u8>,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct X3DHResult {
    pub shared_secret: Vec<u8>,
    pub associated_data: Vec<u8>,
}

pub fn perform_x3dh_initiator(
    identity_secret: &[u8],
    recipient_identity_public: &[u8],
    recipient_signed_prekey: &[u8],
    recipient_one_time_prekey: Option<&[u8]>,
) -> Result<X3DHResult, String> {
    validate_identity_secret(identity_secret)?;
    validate_identity_public(recipient_identity_public)?;
    validate_prekey_public(recipient_signed_prekey)?;

    if let Some(otpk) = recipient_one_time_prekey {
        validate_prekey_public(otpk)?;
    }

    let ephemeral_secret = StaticSecret::random_from_rng(OsRng);
    let ephemeral_public = X25519Public::from(&ephemeral_secret);

    let identity_x25519_secret = extract_x25519_secret(identity_secret)?;
    let recipient_identity_x25519 = extract_x25519_public(
        recipient_identity_public
    )?;
    let recipient_signed_x25519 = extract_x25519_public(
        recipient_signed_prekey
    )?;

    let dh1 = identity_x25519_secret.diffie_hellman(&recipient_signed_x25519);
    let dh2 = ephemeral_secret.diffie_hellman(&recipient_identity_x25519);
    let dh3 = ephemeral_secret.diffie_hellman(&recipient_signed_x25519);

    let recipient_identity_kyber = extract_kyber_public(
        recipient_identity_public
    )?;
    let recipient_signed_kyber = extract_kyber_public(
        recipient_signed_prekey
    )?;

    let kem1 = encapsulate(&recipient_identity_kyber, &mut OsRng)
        .map_err(|_| "Kyber encapsulation failed".to_string())?;
    let kem2 = encapsulate(&recipient_signed_kyber, &mut OsRng)
        .map_err(|_| "Kyber encapsulation failed".to_string())?;

    let mut dh_outputs = vec![
        dh1.as_bytes().to_vec(),
        dh2.as_bytes().to_vec(),
        dh3.as_bytes().to_vec(),
        kem1.1.as_ref().to_vec(),
        kem2.1.as_ref().to_vec(),
    ];

    let mut ciphertexts = vec![kem1.0.to_vec(), kem2.0.to_vec()];

    if let Some(otpk) = recipient_one_time_prekey {
        let recipient_otpk_x25519 = extract_x25519_public(otpk)?;
        let dh4 = ephemeral_secret.diffie_hellman(&recipient_otpk_x25519);
        dh_outputs.push(dh4.as_bytes().to_vec());

        let recipient_otpk_kyber = extract_kyber_public(otpk)?;
        let kem3 = encapsulate(&recipient_otpk_kyber, &mut OsRng)
            .map_err(|_| "Kyber encapsulation failed".to_string())?;
        dh_outputs.push(kem3.1.as_ref().to_vec());
        ciphertexts.push(kem3.0.to_vec());
    }

    let combined_secret = dh_outputs.concat();

    let hkdf = Hkdf::<Sha256>::new(None, &combined_secret);
    let mut shared_secret = vec![0u8; 32];
    hkdf.expand(X3DH_INFO, &mut shared_secret)
        .map_err(|_| "Key derivation failed".to_string())?;

    let associated_data = [
        ephemeral_public.as_bytes().to_vec(),
        ciphertexts.concat(),
    ].concat();

    Ok(X3DHResult {
        shared_secret,
        associated_data,
    })
}

pub fn perform_x3dh_responder(
    identity_secret: &[u8],
    signed_prekey_secret: &[u8],
    one_time_prekey_secret: Option<&[u8]>,
    initiator_identity_public: &[u8],
    initiator_ephemeral_public: &[u8],
    kyber_ciphertexts: &[Vec<u8>],
) -> Result<Vec<u8>, String> {
    validate_identity_secret(identity_secret)?;
    validate_prekey_secret(signed_prekey_secret)?;
    validate_identity_public(initiator_identity_public)?;
    validate_ephemeral_public(initiator_ephemeral_public)?;

    if let Some(otpk_secret) = one_time_prekey_secret {
        validate_prekey_secret(otpk_secret)?;
    }

    let identity_x25519_secret = extract_x25519_secret(identity_secret)?;
    let signed_x25519_secret = extract_x25519_secret(signed_prekey_secret)?;
    let initiator_identity_x25519 = extract_x25519_public(
        initiator_identity_public
    )?;
    let initiator_ephemeral_x25519 = extract_ephemeral_x25519(
        initiator_ephemeral_public
    )?;

    let dh1 = signed_x25519_secret.diffie_hellman(&initiator_identity_x25519);
    let dh2 = identity_x25519_secret.diffie_hellman(
        &initiator_ephemeral_x25519
    );
    let dh3 = signed_x25519_secret.diffie_hellman(&initiator_ephemeral_x25519);

    let identity_kyber_secret = extract_kyber_secret(identity_secret)?;
    let signed_kyber_secret = extract_kyber_secret(signed_prekey_secret)?;

    if kyber_ciphertexts.len() < 2 {
        return Err("Insufficient Kyber ciphertexts".to_string());
    }

    let kem1_ct: [u8; KYBER_CIPHERTEXTBYTES] = kyber_ciphertexts[0]
        .as_slice()
        .try_into()
        .map_err(|_| "Invalid Kyber ciphertext size".to_string())?;
    let kem2_ct: [u8; KYBER_CIPHERTEXTBYTES] = kyber_ciphertexts[1]
        .as_slice()
        .try_into()
        .map_err(|_| "Invalid Kyber ciphertext size".to_string())?;

    let kem1_ss = decapsulate(&kem1_ct, &identity_kyber_secret)
        .map_err(|_| "Kyber decapsulation failed".to_string())?;
    let kem2_ss = decapsulate(&kem2_ct, &signed_kyber_secret)
        .map_err(|_| "Kyber decapsulation failed".to_string())?;

    let mut dh_outputs = vec![
        dh1.as_bytes().to_vec(),
        dh2.as_bytes().to_vec(),
        dh3.as_bytes().to_vec(),
        kem1_ss.as_ref().to_vec(),
        kem2_ss.as_ref().to_vec(),
    ];

    if let Some(otpk_secret) = one_time_prekey_secret {
        if kyber_ciphertexts.len() < 3 {
            return Err("Missing one-time prekey ciphertext".to_string());
        }

        let otpk_x25519_secret = extract_x25519_secret(otpk_secret)?;
        let dh4 = otpk_x25519_secret.diffie_hellman(
            &initiator_ephemeral_x25519
        );
        dh_outputs.push(dh4.as_bytes().to_vec());

        let otpk_kyber_secret = extract_kyber_secret(otpk_secret)?;
        let kem3_ct: [u8; KYBER_CIPHERTEXTBYTES] = kyber_ciphertexts[2]
            .as_slice()
            .try_into()
            .map_err(|_| "Invalid Kyber ciphertext size".to_string())?;
        let kem3_ss = decapsulate(&kem3_ct, &otpk_kyber_secret)
            .map_err(|_| "Kyber decapsulation failed".to_string())?;
        dh_outputs.push(kem3_ss.as_ref().to_vec());
    }

    let combined_secret = dh_outputs.concat();

    let hkdf = Hkdf::<Sha256>::new(None, &combined_secret);
    let mut shared_secret = vec![0u8; 32];
    hkdf.expand(X3DH_INFO, &mut shared_secret)
        .map_err(|_| "Key derivation failed".to_string())?;

    Ok(shared_secret)
}

fn validate_identity_secret(secret: &[u8]) -> Result<(), String> {
    let expected = 32 + KYBER_SECRETKEYBYTES + 32;
    if secret.len() != expected {
        return Err(format!(
            "Invalid identity secret length: {} (expected {})",
            secret.len(),
            expected
        ));
    }
    Ok(())
}

fn validate_identity_public(public: &[u8]) -> Result<(), String> {
    let expected = 32 + KYBER_PUBLICKEYBYTES + 32;
    if public.len() != expected {
        return Err(format!(
            "Invalid identity public length: {} (expected {})",
            public.len(),
            expected
        ));
    }
    Ok(())
}

fn validate_prekey_secret(secret: &[u8]) -> Result<(), String> {
    let expected = 32 + KYBER_SECRETKEYBYTES;
    if secret.len() != expected {
        return Err(format!(
            "Invalid prekey secret length: {} (expected {})",
            secret.len(),
            expected
        ));
    }
    Ok(())
}

fn validate_prekey_public(public: &[u8]) -> Result<(), String> {
    let expected = 32 + KYBER_PUBLICKEYBYTES;
    if public.len() != expected {
        return Err(format!(
            "Invalid prekey public length: {} (expected {})",
            public.len(),
            expected
        ));
    }
    Ok(())
}

fn validate_ephemeral_public(public: &[u8]) -> Result<(), String> {
    if public.len() != 32 {
        return Err(format!(
            "Invalid ephemeral public length: {} (expected 32)",
            public.len()
        ));
    }
    Ok(())
}

fn extract_x25519_secret(key: &[u8]) -> Result<StaticSecret, String> {
    let bytes: [u8; 32] = key[..32]
        .try_into()
        .map_err(|_| "Failed to extract X25519 secret".to_string())?;
    Ok(StaticSecret::from(bytes))
}

fn extract_x25519_public(key: &[u8]) -> Result<X25519Public, String> {
    let bytes: [u8; 32] = key[..32]
        .try_into()
        .map_err(|_| "Failed to extract X25519 public".to_string())?;
    Ok(X25519Public::from(bytes))
}

fn extract_ephemeral_x25519(key: &[u8]) -> Result<X25519Public, String> {
    let bytes: [u8; 32] = key
        .try_into()
        .map_err(|_| "Failed to extract ephemeral X25519".to_string())?;
    Ok(X25519Public::from(bytes))
}

fn extract_kyber_public(key: &[u8]) -> Result<PublicKey, String> {
    PublicKey::try_from(&key[32..32 + KYBER_PUBLICKEYBYTES])
        .map_err(|_| "Failed to extract Kyber public".to_string())
}

fn extract_kyber_secret(key: &[u8]) -> Result<SecretKey, String> {
    SecretKey::try_from(&key[32..32 + KYBER_SECRETKEYBYTES])
        .map_err(|_| "Failed to extract Kyber secret".to_string())
}
