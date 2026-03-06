pub mod crypto;
pub mod prekeys;
pub mod kdf;
pub mod ratchet;
pub mod x3dh;

use wasm_bindgen::prelude::*;
use crypto::{CryptoEngine, KeyPair, EncryptedMessage};
use prekeys::{
    IdentityKeyPair, SignedPrekey, OneTimePrekeyPair,
    generate_identity_keypair, generate_signed_prekey, 
    generate_one_time_prekeys, create_prekey_bundle, verify_signed_prekey,
};
use x3dh::{perform_x3dh_initiator, perform_x3dh_responder};

#[wasm_bindgen]
pub struct CryptoContext {
    engine: CryptoEngine,
}

#[wasm_bindgen]
impl CryptoContext {
    #[wasm_bindgen(constructor)]
    pub fn new() -> Result<CryptoContext, JsValue> {
        let engine = CryptoEngine::new()
            .map_err(|e| JsValue::from_str(&e))?;
        Ok(CryptoContext { engine })
    }

    pub fn get_public_keys(&self) -> Result<String, JsValue> {
        let keys = self.engine.get_public_keys()
            .map_err(|e| JsValue::from_str(&e))?;
        serde_json::to_string(&keys)
            .map_err(|e| JsValue::from_str(&e.to_string()))
    }

    pub fn encrypt_message(
        &self,
        plaintext: &str,
        recipient_public_keys: &str,
    ) -> Result<String, JsValue> {
        let keys: KeyPair = serde_json::from_str(recipient_public_keys)
            .map_err(|e| JsValue::from_str(&e.to_string()))?;
        
        let encrypted = self.engine.encrypt_message(plaintext, &keys)
            .map_err(|e| JsValue::from_str(&e))?;
        
        serde_json::to_string(&encrypted)
            .map_err(|e| JsValue::from_str(&e.to_string()))
    }

    pub fn decrypt_message(
        &self,
        encrypted_json: &str,
    ) -> Result<String, JsValue> {
        let encrypted: EncryptedMessage = serde_json::from_str(encrypted_json)
            .map_err(|e| JsValue::from_str(&e.to_string()))?;
        
        self.engine.decrypt_message(&encrypted)
            .map_err(|e| JsValue::from_str(&e))
    }
}

#[wasm_bindgen]
pub fn initialize() -> String {
    String::from("Post-quantum crypto module initialized")
}

#[wasm_bindgen]
pub fn generate_identity_keys() -> Result<String, JsValue> {
    let keypair = generate_identity_keypair()
        .map_err(|e| JsValue::from_str(&e))?;
    
    serde_json::to_string(&keypair)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

#[wasm_bindgen]
pub fn generate_signed_prekey_pair(
    identity_secret_json: &str,
) -> Result<String, JsValue> {
    let identity: IdentityKeyPair = serde_json::from_str(identity_secret_json)
        .map_err(|e| JsValue::from_str(&e.to_string()))?;
    
    let signed_prekey = generate_signed_prekey(&identity.secret_key)
        .map_err(|e| JsValue::from_str(&e))?;
    
    serde_json::to_string(&signed_prekey)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

#[wasm_bindgen]
pub fn generate_one_time_prekey_batch(
    count: usize,
) -> Result<String, JsValue> {
    let prekeys = generate_one_time_prekeys(count)
        .map_err(|e| JsValue::from_str(&e))?;
    
    serde_json::to_string(&prekeys)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

#[wasm_bindgen]
pub fn build_prekey_bundle(
    identity_keypair_json: &str,
    signed_prekey_json: &str,
    one_time_prekeys_json: &str,
) -> Result<String, JsValue> {
    let identity: IdentityKeyPair = serde_json::from_str(identity_keypair_json)
        .map_err(|e| JsValue::from_str(&e.to_string()))?;
    
    let signed_prekey: SignedPrekey = serde_json::from_str(signed_prekey_json)
        .map_err(|e| JsValue::from_str(&e.to_string()))?;
    
    let one_time_prekeys: Vec<OneTimePrekeyPair> = 
        serde_json::from_str(one_time_prekeys_json)
            .map_err(|e| JsValue::from_str(&e.to_string()))?;
    
    let bundle = create_prekey_bundle(
        &identity,
        &signed_prekey,
        &one_time_prekeys,
    );
    
    serde_json::to_string(&bundle)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

#[wasm_bindgen]
pub fn verify_prekey_signature(
    identity_public: &[u8],
    signed_prekey_public: &[u8],
    signature: &[u8],
) -> Result<bool, JsValue> {
    verify_signed_prekey(identity_public, signed_prekey_public, signature)
        .map_err(|e| JsValue::from_str(&e))
}




#[wasm_bindgen]
pub fn initialize_ratchet_sender(
    shared_secret: &[u8],
    receiver_public_key: &[u8],
) -> Result<String, String> {
    use x25519_dalek::{StaticSecret, PublicKey};
    use rand::rngs::OsRng;
    
    let sender_ratchet_private = StaticSecret::random_from_rng(OsRng);
    
    let receiver_public: [u8; 32] = receiver_public_key.try_into()
        .map_err(|_| "invalid receiver public key length")?;
    let receiver_public = PublicKey::from(receiver_public);
    
    let state = ratchet::RatchetState::initialize_sender(
        shared_secret,
        sender_ratchet_private,
        receiver_public,
    );
    
    state.to_json()
}

#[wasm_bindgen]
pub fn initialize_ratchet_receiver(
    shared_secret: &[u8],
    sender_public_key: &[u8],
) -> Result<String, String> {
    use x25519_dalek::{StaticSecret, PublicKey};
    use rand::rngs::OsRng;
    
    let receiver_ratchet_private = StaticSecret::random_from_rng(OsRng);
    
    let sender_public: [u8; 32] = sender_public_key.try_into()
        .map_err(|_| "invalid sender public key length")?;
    let sender_public = PublicKey::from(sender_public);
    
    let state = ratchet::RatchetState::initialize_receiver(
        shared_secret,
        receiver_ratchet_private,
        sender_public,
    );
    
    state.to_json()
}

#[wasm_bindgen]
pub fn ratchet_encrypt(
    state_json: &str,
    plaintext: &[u8],
) -> Result<String, String> {
    let mut state = ratchet::RatchetState::from_json(state_json)?;
    let message = state.encrypt_message(plaintext);
    
    let result = serde_json::json!({
        "state": state.to_json()?,
        "message": {
            "header": {
                "public_key": message.header.public_key,
                "message_number": message.header.message_number,
                "previous_chain_length": message.header.previous_chain_length,
            },
            "ciphertext": message.ciphertext,
        }
    });
    
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[wasm_bindgen]
pub fn ratchet_decrypt(
    state_json: &str,
    message_json: &str,
) -> Result<String, String> {
    let mut state = ratchet::RatchetState::from_json(state_json)?;
    
    let message_value: serde_json::Value = serde_json::from_str(message_json)
        .map_err(|e| e.to_string())?;
    
    let header = ratchet::MessageHeader {
        public_key: serde_json::from_value(
            message_value["header"]["public_key"].clone()
        ).map_err(|e| e.to_string())?,
        message_number: message_value["header"]["message_number"]
            .as_u64()
            .ok_or("invalid message number")? as u32,
        previous_chain_length: message_value["header"]["previous_chain_length"]
            .as_u64()
            .ok_or("invalid previous chain length")? as u32,
    };
    
    let ciphertext: Vec<u8> = serde_json::from_value(
        message_value["ciphertext"].clone()
    ).map_err(|e| e.to_string())?;
    
    let message = ratchet::RatchetedMessage { header, ciphertext };
    let plaintext = state.decrypt_message(&message)?;
    
    let result = serde_json::json!({
        "state": state.to_json()?,
        "plaintext": plaintext,
    });
    
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[wasm_bindgen]
pub fn x3dh_initiator(
    identity_secret: &[u8],
    recipient_identity_public: &[u8],
    recipient_signed_prekey: &[u8],
    recipient_one_time_prekey: Option<Vec<u8>>,
) -> Result<String, String> {
    let otpk = recipient_one_time_prekey.as_deref();
    
    let result = perform_x3dh_initiator(
        identity_secret,
        recipient_identity_public,
        recipient_signed_prekey,
        otpk,
    )?;
    
    serde_json::to_string(&result).map_err(|e| e.to_string())
}

#[wasm_bindgen]
pub fn x3dh_responder(
    identity_secret: &[u8],
    signed_prekey_secret: &[u8],
    one_time_prekey_secret: Option<Vec<u8>>,
    initiator_identity_public: &[u8],
    initiator_ephemeral_public: &[u8],
    kyber_ciphertexts_json: &str,
) -> Result<String, String> {
    let kyber_ciphertexts: Vec<Vec<u8>> = serde_json::from_str(
        kyber_ciphertexts_json
    ).map_err(|e| e.to_string())?;
    
    let otpk_secret = one_time_prekey_secret.as_deref();
    
    let shared_secret = perform_x3dh_responder(
        identity_secret,
        signed_prekey_secret,
        otpk_secret,
        initiator_identity_public,
        initiator_ephemeral_public,
        &kyber_ciphertexts,
    )?;
    
    let result = serde_json::json!({
        "shared_secret": shared_secret,
    });
    
    serde_json::to_string(&result).map_err(|e| e.to_string())
}
