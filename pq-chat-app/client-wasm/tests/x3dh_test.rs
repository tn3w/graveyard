use chat_client_wasm::prekeys::{
    generate_identity_keypair, generate_signed_prekey, 
    generate_one_time_prekeys, verify_signed_prekey,
};
use chat_client_wasm::x3dh::{
    perform_x3dh_initiator, perform_x3dh_responder,
};

#[test]
fn test_x3dh_key_agreement_with_one_time_prekey() {
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_identity = generate_identity_keypair().unwrap();
    
    let bob_signed_prekey = generate_signed_prekey(
        &bob_identity.secret_key
    ).unwrap();
    
    let bob_one_time_prekeys = generate_one_time_prekeys(1).unwrap();
    let bob_otpk = &bob_one_time_prekeys[0];
    
    let is_valid = verify_signed_prekey(
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        &bob_signed_prekey.signature,
    ).unwrap();
    assert!(is_valid, "Signed prekey signature should be valid");
    
    let initiator_result = perform_x3dh_initiator(
        &alice_identity.secret_key,
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        Some(&bob_otpk.public_key),
    ).unwrap();
    
    let ephemeral_public = &initiator_result.associated_data[..32];
    let kyber_ciphertexts_start = 32;
    let ct_size = 1568;
    
    let kyber_ct1 = initiator_result.associated_data[
        kyber_ciphertexts_start..kyber_ciphertexts_start + ct_size
    ].to_vec();
    let kyber_ct2 = initiator_result.associated_data[
        kyber_ciphertexts_start + ct_size..
        kyber_ciphertexts_start + 2 * ct_size
    ].to_vec();
    let kyber_ct3 = initiator_result.associated_data[
        kyber_ciphertexts_start + 2 * ct_size..
        kyber_ciphertexts_start + 3 * ct_size
    ].to_vec();
    
    let kyber_ciphertexts = vec![kyber_ct1, kyber_ct2, kyber_ct3];
    
    let responder_secret = perform_x3dh_responder(
        &bob_identity.secret_key,
        &bob_signed_prekey.secret_key,
        Some(&bob_otpk.secret_key),
        &alice_identity.public_key,
        ephemeral_public,
        &kyber_ciphertexts,
    ).unwrap();
    
    assert_eq!(
        initiator_result.shared_secret,
        responder_secret,
        "Shared secrets should match"
    );
    assert_eq!(
        initiator_result.shared_secret.len(),
        32,
        "Shared secret should be 32 bytes"
    );
}

#[test]
fn test_x3dh_key_agreement_without_one_time_prekey() {
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_identity = generate_identity_keypair().unwrap();
    
    let bob_signed_prekey = generate_signed_prekey(
        &bob_identity.secret_key
    ).unwrap();
    
    let initiator_result = perform_x3dh_initiator(
        &alice_identity.secret_key,
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        None,
    ).unwrap();
    
    let ephemeral_public = &initiator_result.associated_data[..32];
    let kyber_ciphertexts_start = 32;
    let ct_size = 1568;
    
    let kyber_ct1 = initiator_result.associated_data[
        kyber_ciphertexts_start..kyber_ciphertexts_start + ct_size
    ].to_vec();
    let kyber_ct2 = initiator_result.associated_data[
        kyber_ciphertexts_start + ct_size..
        kyber_ciphertexts_start + 2 * ct_size
    ].to_vec();
    
    let kyber_ciphertexts = vec![kyber_ct1, kyber_ct2];
    
    let responder_secret = perform_x3dh_responder(
        &bob_identity.secret_key,
        &bob_signed_prekey.secret_key,
        None,
        &alice_identity.public_key,
        ephemeral_public,
        &kyber_ciphertexts,
    ).unwrap();
    
    assert_eq!(
        initiator_result.shared_secret,
        responder_secret,
        "Shared secrets should match"
    );
}

#[test]
fn test_x3dh_different_identities_produce_different_secrets() {
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_identity = generate_identity_keypair().unwrap();
    let charlie_identity = generate_identity_keypair().unwrap();
    
    let bob_signed_prekey = generate_signed_prekey(
        &bob_identity.secret_key
    ).unwrap();
    
    let result1 = perform_x3dh_initiator(
        &alice_identity.secret_key,
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        None,
    ).unwrap();
    
    let result2 = perform_x3dh_initiator(
        &charlie_identity.secret_key,
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        None,
    ).unwrap();
    
    assert_ne!(
        result1.shared_secret,
        result2.shared_secret,
        "Different initiators should produce different secrets"
    );
}

#[test]
fn test_x3dh_invalid_identity_secret_length() {
    let bob_identity = generate_identity_keypair().unwrap();
    let bob_signed_prekey = generate_signed_prekey(
        &bob_identity.secret_key
    ).unwrap();
    
    let invalid_secret = vec![0u8; 32];
    
    let result = perform_x3dh_initiator(
        &invalid_secret,
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        None,
    );
    
    assert!(result.is_err(), "Should reject invalid identity secret");
}

#[test]
fn test_x3dh_invalid_identity_public_length() {
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_signed_prekey = generate_signed_prekey(
        &alice_identity.secret_key
    ).unwrap();
    
    let invalid_public = vec![0u8; 32];
    
    let result = perform_x3dh_initiator(
        &alice_identity.secret_key,
        &invalid_public,
        &bob_signed_prekey.public_key,
        None,
    );
    
    assert!(result.is_err(), "Should reject invalid identity public");
}

#[test]
fn test_x3dh_invalid_prekey_length() {
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_identity = generate_identity_keypair().unwrap();
    
    let invalid_prekey = vec![0u8; 32];
    
    let result = perform_x3dh_initiator(
        &alice_identity.secret_key,
        &bob_identity.public_key,
        &invalid_prekey,
        None,
    );
    
    assert!(result.is_err(), "Should reject invalid prekey");
}

#[test]
fn test_x3dh_responder_insufficient_ciphertexts() {
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_identity = generate_identity_keypair().unwrap();
    let bob_signed_prekey = generate_signed_prekey(
        &bob_identity.secret_key
    ).unwrap();
    
    let ephemeral_public = vec![0u8; 32];
    let kyber_ciphertexts = vec![vec![0u8; 1568]];
    
    let result = perform_x3dh_responder(
        &bob_identity.secret_key,
        &bob_signed_prekey.secret_key,
        None,
        &alice_identity.public_key,
        &ephemeral_public,
        &kyber_ciphertexts,
    );
    
    assert!(result.is_err(), "Should reject insufficient ciphertexts");
}

#[test]
fn test_x3dh_with_ratchet_initialization() {
    use chat_client_wasm::ratchet::RatchetState;
    use x25519_dalek::{StaticSecret, PublicKey};
    use rand::rngs::OsRng;
    
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_identity = generate_identity_keypair().unwrap();
    let bob_signed_prekey = generate_signed_prekey(
        &bob_identity.secret_key
    ).unwrap();
    
    let initiator_result = perform_x3dh_initiator(
        &alice_identity.secret_key,
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        None,
    ).unwrap();
    
    let alice_ratchet_private = StaticSecret::random_from_rng(OsRng);
    let alice_ratchet_public = PublicKey::from(&alice_ratchet_private);
    
    let bob_ratchet_private = StaticSecret::random_from_rng(OsRng);
    let bob_ratchet_public = PublicKey::from(&bob_ratchet_private);
    
    let mut alice_state = RatchetState::initialize_sender(
        &initiator_result.shared_secret,
        alice_ratchet_private,
        bob_ratchet_public,
    );
    
    let ephemeral_public = &initiator_result.associated_data[..32];
    let kyber_ciphertexts_start = 32;
    let ct_size = 1568;
    
    let kyber_ct1 = initiator_result.associated_data[
        kyber_ciphertexts_start..kyber_ciphertexts_start + ct_size
    ].to_vec();
    let kyber_ct2 = initiator_result.associated_data[
        kyber_ciphertexts_start + ct_size..
        kyber_ciphertexts_start + 2 * ct_size
    ].to_vec();
    
    let kyber_ciphertexts = vec![kyber_ct1, kyber_ct2];
    
    let responder_secret = perform_x3dh_responder(
        &bob_identity.secret_key,
        &bob_signed_prekey.secret_key,
        None,
        &alice_identity.public_key,
        ephemeral_public,
        &kyber_ciphertexts,
    ).unwrap();
    
    let mut bob_state = RatchetState::initialize_receiver(
        &responder_secret,
        bob_ratchet_private,
        alice_ratchet_public,
    );
    
    let plaintext = b"Hello from Alice!";
    let message = alice_state.encrypt_message(plaintext);
    let decrypted = bob_state.decrypt_message(&message).unwrap();
    
    assert_eq!(plaintext, decrypted.as_slice(), "Message should decrypt");
}

#[test]
fn test_x3dh_associated_data_format() {
    let alice_identity = generate_identity_keypair().unwrap();
    let bob_identity = generate_identity_keypair().unwrap();
    let bob_signed_prekey = generate_signed_prekey(
        &bob_identity.secret_key
    ).unwrap();
    
    let result = perform_x3dh_initiator(
        &alice_identity.secret_key,
        &bob_identity.public_key,
        &bob_signed_prekey.public_key,
        None,
    ).unwrap();
    
    let expected_size = 32 + 2 * 1568;
    assert_eq!(
        result.associated_data.len(),
        expected_size,
        "Associated data should contain ephemeral public + 2 ciphertexts"
    );
}
