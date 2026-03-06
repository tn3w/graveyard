use chat_client_wasm::prekeys::{
    generate_identity_keypair, generate_signed_prekey, 
    generate_one_time_prekeys, create_prekey_bundle, verify_signed_prekey,
};

#[test]
fn test_generate_identity_keypair() {
    let keypair = generate_identity_keypair().unwrap();
    
    assert!(!keypair.public_key.is_empty());
    assert!(!keypair.secret_key.is_empty());
    assert_eq!(keypair.public_key.len(), 32 + 1568 + 32);
    assert_eq!(keypair.secret_key.len(), 32 + 3168 + 32);
}

#[test]
fn test_generate_signed_prekey() {
    let identity = generate_identity_keypair().unwrap();
    let signed_prekey = generate_signed_prekey(&identity.secret_key).unwrap();
    
    assert!(!signed_prekey.public_key.is_empty());
    assert!(!signed_prekey.secret_key.is_empty());
    assert_eq!(signed_prekey.signature.len(), 64);
    assert!(signed_prekey.timestamp > 0);
}

#[test]
fn test_verify_signed_prekey() {
    let identity = generate_identity_keypair().unwrap();
    let signed_prekey = generate_signed_prekey(&identity.secret_key).unwrap();
    
    let is_valid = verify_signed_prekey(
        &identity.public_key,
        &signed_prekey.public_key,
        &signed_prekey.signature,
    ).unwrap();
    
    assert!(is_valid);
}

#[test]
fn test_verify_signed_prekey_invalid_signature() {
    let identity = generate_identity_keypair().unwrap();
    let signed_prekey = generate_signed_prekey(&identity.secret_key).unwrap();
    
    let wrong_signature = vec![0u8; 64];
    
    let is_valid = verify_signed_prekey(
        &identity.public_key,
        &signed_prekey.public_key,
        &wrong_signature,
    ).unwrap();
    
    assert!(!is_valid);
}

#[test]
fn test_verify_signed_prekey_wrong_identity() {
    let identity1 = generate_identity_keypair().unwrap();
    let identity2 = generate_identity_keypair().unwrap();
    let signed_prekey = generate_signed_prekey(&identity1.secret_key).unwrap();
    
    let is_valid = verify_signed_prekey(
        &identity2.public_key,
        &signed_prekey.public_key,
        &signed_prekey.signature,
    ).unwrap();
    
    assert!(!is_valid);
}

#[test]
fn test_generate_one_time_prekeys() {
    let prekeys = generate_one_time_prekeys(10).unwrap();
    
    assert_eq!(prekeys.len(), 10);
    
    for prekey in &prekeys {
        assert!(!prekey.public_key.is_empty());
        assert!(!prekey.secret_key.is_empty());
    }
    
    for i in 0..prekeys.len() {
        for j in (i + 1)..prekeys.len() {
            assert_ne!(prekeys[i].public_key, prekeys[j].public_key);
        }
    }
}

#[test]
fn test_generate_one_time_prekeys_max_limit() {
    let result = generate_one_time_prekeys(101);
    assert!(result.is_err());
}

#[test]
fn test_create_prekey_bundle() {
    let identity = generate_identity_keypair().unwrap();
    let signed_prekey = generate_signed_prekey(&identity.secret_key).unwrap();
    let one_time_prekeys = generate_one_time_prekeys(5).unwrap();
    
    let bundle = create_prekey_bundle(
        &identity,
        &signed_prekey,
        &one_time_prekeys,
    );
    
    assert_eq!(bundle.identity_key, identity.public_key);
    assert_eq!(bundle.signed_prekey, signed_prekey.public_key);
    assert_eq!(bundle.signed_prekey_signature, signed_prekey.signature);
    assert_eq!(bundle.signed_prekey_timestamp, signed_prekey.timestamp);
    assert_eq!(bundle.one_time_prekeys.len(), 5);
}

#[test]
fn test_prekey_uniqueness() {
    let identity1 = generate_identity_keypair().unwrap();
    let identity2 = generate_identity_keypair().unwrap();
    
    assert_ne!(identity1.public_key, identity2.public_key);
    assert_ne!(identity1.secret_key, identity2.secret_key);
    
    let signed1 = generate_signed_prekey(&identity1.secret_key).unwrap();
    let signed2 = generate_signed_prekey(&identity1.secret_key).unwrap();
    
    assert_ne!(signed1.public_key, signed2.public_key);
    assert_ne!(signed1.secret_key, signed2.secret_key);
}

#[test]
fn test_signed_prekey_timestamp_ordering() {
    let identity = generate_identity_keypair().unwrap();
    
    let prekey1 = generate_signed_prekey(&identity.secret_key).unwrap();
    std::thread::sleep(std::time::Duration::from_millis(10));
    let prekey2 = generate_signed_prekey(&identity.secret_key).unwrap();
    
    assert!(prekey2.timestamp >= prekey1.timestamp);
}
