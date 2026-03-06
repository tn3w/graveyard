use sha2::{Sha256, Digest};
use hkdf::Hkdf;

const KDF_RK_INFO: &[u8] = b"DoubleRatchetRootKey";
const KDF_CK_INFO: &[u8] = b"DoubleRatchetChainKey";
const MESSAGE_KEY_INFO: &[u8] = b"DoubleRatchetMessageKey";

pub type RootKey = [u8; 32];
pub type ChainKey = [u8; 32];
pub type MessageKey = [u8; 32];

pub fn derive_root_key(
    current_root_key: &RootKey,
    dh_output: &[u8],
) -> (RootKey, ChainKey) {
    let hkdf = Hkdf::<Sha256>::new(Some(current_root_key), dh_output);
    
    let mut root_key = [0u8; 32];
    let mut chain_key = [0u8; 32];
    
    hkdf.expand(KDF_RK_INFO, &mut root_key)
        .expect("root key derivation failed");
    hkdf.expand(KDF_CK_INFO, &mut chain_key)
        .expect("chain key derivation failed");
    
    (root_key, chain_key)
}

pub fn derive_chain_key(current_chain_key: &ChainKey) -> ChainKey {
    let mut hasher = Sha256::new();
    hasher.update(b"ChainKeyDerivation");
    hasher.update(current_chain_key);
    
    let result = hasher.finalize();
    let mut chain_key = [0u8; 32];
    chain_key.copy_from_slice(&result);
    chain_key
}

pub fn derive_message_key(chain_key: &ChainKey) -> MessageKey {
    let hkdf = Hkdf::<Sha256>::new(None, chain_key);
    
    let mut message_key = [0u8; 32];
    hkdf.expand(MESSAGE_KEY_INFO, &mut message_key)
        .expect("message key derivation failed");
    
    message_key
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_derive_root_key_deterministic() {
        let root_key = [1u8; 32];
        let dh_output = [2u8; 32];
        
        let (new_root1, chain1) = derive_root_key(&root_key, &dh_output);
        let (new_root2, chain2) = derive_root_key(&root_key, &dh_output);
        
        assert_eq!(new_root1, new_root2);
        assert_eq!(chain1, chain2);
    }

    #[test]
    fn test_derive_root_key_different_inputs() {
        let root_key = [1u8; 32];
        let dh_output1 = [2u8; 32];
        let dh_output2 = [3u8; 32];
        
        let (new_root1, _) = derive_root_key(&root_key, &dh_output1);
        let (new_root2, _) = derive_root_key(&root_key, &dh_output2);
        
        assert_ne!(new_root1, new_root2);
    }

    #[test]
    fn test_derive_chain_key_deterministic() {
        let chain_key = [1u8; 32];
        
        let new_chain1 = derive_chain_key(&chain_key);
        let new_chain2 = derive_chain_key(&chain_key);
        
        assert_eq!(new_chain1, new_chain2);
    }

    #[test]
    fn test_derive_message_key_deterministic() {
        let chain_key = [1u8; 32];
        
        let msg_key1 = derive_message_key(&chain_key);
        let msg_key2 = derive_message_key(&chain_key);
        
        assert_eq!(msg_key1, msg_key2);
    }

    #[test]
    fn test_chain_key_progression() {
        let chain_key = [1u8; 32];
        
        let chain1 = derive_chain_key(&chain_key);
        let chain2 = derive_chain_key(&chain1);
        let chain3 = derive_chain_key(&chain2);
        
        assert_ne!(chain1, chain2);
        assert_ne!(chain2, chain3);
        assert_ne!(chain1, chain3);
    }
}
