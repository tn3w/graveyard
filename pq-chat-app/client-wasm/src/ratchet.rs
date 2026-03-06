use std::collections::HashMap;
use x25519_dalek::{PublicKey, StaticSecret};
use serde::{Serialize, Deserialize};
use crate::kdf::{RootKey, ChainKey, MessageKey};
use crate::kdf::{derive_root_key, derive_chain_key, derive_message_key};

const MAX_SKIP: u32 = 1000;

#[derive(Serialize, Deserialize, Clone)]
pub struct RatchetState {
    root_key: RootKey,
    sending_chain_key: Option<ChainKey>,
    receiving_chain_key: Option<ChainKey>,
    sending_ratchet_private: Vec<u8>,
    sending_ratchet_public: Vec<u8>,
    receiving_ratchet_public: Option<Vec<u8>>,
    sending_message_number: u32,
    receiving_message_number: u32,
    previous_sending_chain_length: u32,
    skipped_message_keys: HashMap<String, MessageKey>,
}

impl RatchetState {
    #[cfg(test)]
    pub fn new_for_test(
        root_key: RootKey,
        sending_chain_key: Option<ChainKey>,
        receiving_chain_key: Option<ChainKey>,
        sending_ratchet_private: Vec<u8>,
        sending_ratchet_public: Vec<u8>,
        receiving_ratchet_public: Option<Vec<u8>>,
    ) -> Self {
        Self {
            root_key,
            sending_chain_key,
            receiving_chain_key,
            sending_ratchet_private,
            sending_ratchet_public,
            receiving_ratchet_public,
            sending_message_number: 0,
            receiving_message_number: 0,
            previous_sending_chain_length: 0,
            skipped_message_keys: HashMap::new(),
        }
    }

    pub fn initialize_sender(
        shared_secret: &[u8],
        sender_ratchet_private: StaticSecret,
        receiver_ratchet_public: PublicKey,
    ) -> Self {
        let root_key = derive_initial_root_key(shared_secret);
        let sender_ratchet_public = PublicKey::from(&sender_ratchet_private);
        
        let dh_output = sender_ratchet_private.diffie_hellman(&receiver_ratchet_public);
        let (new_root_key, sending_chain_key) = 
            derive_root_key(&root_key, dh_output.as_bytes());
        
        Self {
            root_key: new_root_key,
            sending_chain_key: Some(sending_chain_key),
            receiving_chain_key: None,
            sending_ratchet_private: sender_ratchet_private.to_bytes().to_vec(),
            sending_ratchet_public: sender_ratchet_public.as_bytes().to_vec(),
            receiving_ratchet_public: Some(receiver_ratchet_public.as_bytes().to_vec()),
            sending_message_number: 0,
            receiving_message_number: 0,
            previous_sending_chain_length: 0,
            skipped_message_keys: HashMap::new(),
        }
    }

    pub fn initialize_receiver(
        shared_secret: &[u8],
        receiver_ratchet_private: StaticSecret,
        sender_ratchet_public: PublicKey,
    ) -> Self {
        let root_key = derive_initial_root_key(shared_secret);
        let receiver_ratchet_public = PublicKey::from(&receiver_ratchet_private);
        
        let dh_output = receiver_ratchet_private.diffie_hellman(&sender_ratchet_public);
        let (new_root_key, receiving_chain_key) = 
            derive_root_key(&root_key, dh_output.as_bytes());
        
        Self {
            root_key: new_root_key,
            sending_chain_key: None,
            receiving_chain_key: Some(receiving_chain_key),
            sending_ratchet_private: receiver_ratchet_private.to_bytes().to_vec(),
            sending_ratchet_public: receiver_ratchet_public.as_bytes().to_vec(),
            receiving_ratchet_public: Some(sender_ratchet_public.as_bytes().to_vec()),
            sending_message_number: 0,
            receiving_message_number: 0,
            previous_sending_chain_length: 0,
            skipped_message_keys: HashMap::new(),
        }
    }

    pub fn encrypt_message(&mut self, plaintext: &[u8]) -> RatchetedMessage {
        if self.sending_chain_key.is_none() {
            let new_private = StaticSecret::random_from_rng(rand::thread_rng());
            let new_public = PublicKey::from(&new_private);
            
            self.sending_ratchet_private = new_private.to_bytes().to_vec();
            self.sending_ratchet_public = new_public.as_bytes().to_vec();
            
            if let Some(receiving_public_bytes) = &self.receiving_ratchet_public {
                let receiving_public_array: [u8; 32] = receiving_public_bytes
                    .as_slice()
                    .try_into()
                    .expect("invalid receiving public key");
                let receiving_public = PublicKey::from(receiving_public_array);
                
                let dh_output = new_private.diffie_hellman(&receiving_public);
                let (new_root_key, new_chain_key) = 
                    derive_root_key(&self.root_key, dh_output.as_bytes());
                
                self.root_key = new_root_key;
                self.sending_chain_key = Some(new_chain_key);
                self.previous_sending_chain_length = self.sending_message_number;
                self.sending_message_number = 0;
            } else {
                let initial_chain_key = derive_initial_chain_key(&self.root_key);
                self.sending_chain_key = Some(initial_chain_key);
            }
        }
        
        let chain_key = self.sending_chain_key.as_ref().unwrap();
        let message_key = derive_message_key(chain_key);
        
        let header = MessageHeader {
            public_key: self.sending_ratchet_public.clone(),
            message_number: self.sending_message_number,
            previous_chain_length: self.previous_sending_chain_length,
        };
        
        let ciphertext = encrypt_with_message_key(&message_key, plaintext);
        
        self.sending_chain_key = Some(derive_chain_key(chain_key));
        self.sending_message_number += 1;
        
        RatchetedMessage { header, ciphertext }
    }

    pub fn decrypt_message(
        &mut self,
        message: &RatchetedMessage,
    ) -> Result<Vec<u8>, String> {
        let key_id = format!(
            "{}:{}",
            hex::encode(&message.header.public_key),
            message.header.message_number
        );
        
        if let Some(message_key) = self.skipped_message_keys.remove(&key_id) {
            return decrypt_with_message_key(&message_key, &message.ciphertext);
        }
        
        let received_public_bytes: [u8; 32] = message.header.public_key
            .as_slice()
            .try_into()
            .map_err(|_| "invalid public key length")?;
        let received_public = PublicKey::from(received_public_bytes);
        
        if self.receiving_ratchet_public.as_ref() 
            != Some(&message.header.public_key) {
            self.skip_message_keys(message.header.previous_chain_length)?;
            self.perform_dh_ratchet_step(&received_public);
        }
        
        self.skip_message_keys(message.header.message_number)?;
        
        let chain_key = self.receiving_chain_key.as_ref()
            .ok_or("no receiving chain key")?;
        let message_key = derive_message_key(chain_key);
        
        self.receiving_chain_key = Some(derive_chain_key(chain_key));
        self.receiving_message_number += 1;
        
        decrypt_with_message_key(&message_key, &message.ciphertext)
    }

    fn perform_dh_ratchet_step(&mut self, received_public: &PublicKey) {
        self.receiving_ratchet_public = Some(received_public.as_bytes().to_vec());
        
        let private_bytes: [u8; 32] = self.sending_ratchet_private
            .as_slice()
            .try_into()
            .expect("invalid private key");
        
        let private = StaticSecret::from(private_bytes);
        let dh_output = private.diffie_hellman(received_public);
        
        let (new_root_key, new_chain_key) = 
            derive_root_key(&self.root_key, dh_output.as_bytes());
        
        self.root_key = new_root_key;
        self.receiving_chain_key = Some(new_chain_key);
        self.previous_sending_chain_length = self.sending_message_number;
        self.receiving_message_number = 0;
    }

    fn skip_message_keys(&mut self, until: u32) -> Result<(), String> {
        if self.receiving_message_number + MAX_SKIP < until {
            return Err("too many skipped messages".to_string());
        }
        
        if let Some(chain_key) = self.receiving_chain_key.as_ref() {
            let mut current_chain = *chain_key;
            
            while self.receiving_message_number < until {
                let message_key = derive_message_key(&current_chain);
                
                let key_id = format!(
                    "{}:{}",
                    hex::encode(self.receiving_ratchet_public.as_ref().unwrap()),
                    self.receiving_message_number
                );
                
                self.skipped_message_keys.insert(key_id, message_key);
                current_chain = derive_chain_key(&current_chain);
                self.receiving_message_number += 1;
            }
            
            self.receiving_chain_key = Some(current_chain);
        }
        
        Ok(())
    }

    pub fn to_json(&self) -> Result<String, String> {
        serde_json::to_string(self).map_err(|e| e.to_string())
    }

    pub fn from_json(json: &str) -> Result<Self, String> {
        serde_json::from_str(json).map_err(|e| e.to_string())
    }
}

#[derive(Serialize, Deserialize, Clone)]
pub struct MessageHeader {
    pub public_key: Vec<u8>,
    pub message_number: u32,
    pub previous_chain_length: u32,
}

#[derive(Serialize, Deserialize, Clone)]
pub struct RatchetedMessage {
    pub header: MessageHeader,
    pub ciphertext: Vec<u8>,
}

fn derive_initial_root_key(shared_secret: &[u8]) -> RootKey {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(b"DoubleRatchetInitialRootKey");
    hasher.update(shared_secret);
    let result = hasher.finalize();
    
    let mut root_key = [0u8; 32];
    root_key.copy_from_slice(&result);
    root_key
}

fn derive_initial_chain_key(root_key: &RootKey) -> ChainKey {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(b"DoubleRatchetInitialChainKey");
    hasher.update(root_key);
    let result = hasher.finalize();
    
    let mut chain_key = [0u8; 32];
    chain_key.copy_from_slice(&result);
    chain_key
}

fn encrypt_with_message_key(key: &MessageKey, plaintext: &[u8]) -> Vec<u8> {
    use chacha20poly1305::{
        aead::{Aead, KeyInit},
        XChaCha20Poly1305, XNonce,
    };
    use sha2::{Sha256, Digest};
    
    let cipher = XChaCha20Poly1305::new(key.into());
    
    let mut hasher = Sha256::new();
    hasher.update(b"MessageNonce");
    hasher.update(key);
    let nonce_bytes = hasher.finalize();
    let nonce = XNonce::from_slice(&nonce_bytes[..24]);
    
    cipher.encrypt(nonce, plaintext)
        .expect("encryption failed")
}

fn decrypt_with_message_key(
    key: &MessageKey,
    ciphertext: &[u8],
) -> Result<Vec<u8>, String> {
    use chacha20poly1305::{
        aead::{Aead, KeyInit},
        XChaCha20Poly1305, XNonce,
    };
    use sha2::{Sha256, Digest};
    
    let cipher = XChaCha20Poly1305::new(key.into());
    
    let mut hasher = Sha256::new();
    hasher.update(b"MessageNonce");
    hasher.update(key);
    let nonce_bytes = hasher.finalize();
    let nonce = XNonce::from_slice(&nonce_bytes[..24]);
    
    cipher.decrypt(nonce, ciphertext)
        .map_err(|_| "decryption failed".to_string())
}
