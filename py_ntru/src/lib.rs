use pyo3::prelude::*;
use pyo3::types::PyBytes;
use ntrust_native::{AesState, crypto_kem_dec, crypto_kem_enc, crypto_kem_keypair};
use ntrust_native::{CRYPTO_BYTES, CRYPTO_CIPHERTEXTBYTES, CRYPTO_PUBLICKEYBYTES, CRYPTO_SECRETKEYBYTES};
use aes_gcm::{Aes256Gcm, Key, Nonce};
use aes_gcm::aead::{Aead, NewAead};
use rand::Rng;
use std::convert::TryInto;


#[pyfunction]
/// Generates a private key for the NTRU scheme.
///
/// Returns:
///     bytes: The generated private key as a byte sequence.
fn generate_private_key(py: Python) -> PyResult<Py<PyBytes>> {
    let mut rng = AesState::new();
    let mut sk = [0u8; CRYPTO_SECRETKEYBYTES];
    let mut pk = [0u8; CRYPTO_PUBLICKEYBYTES];

    crypto_kem_keypair(&mut pk, &mut sk, &mut rng)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

    Ok(PyBytes::new(py, &sk).into())
}


#[pyfunction]
/// Generates a public key based on a given private key.
///
/// Args:
///     private_key (bytes): The private key as a byte sequence.
///
/// Returns:
///     bytes: The corresponding public key as a byte sequence.
fn generate_public_key(py: Python, private_key: &PyBytes) -> PyResult<Py<PyBytes>> {
    let mut rng = AesState::new();
    let mut pk = [0u8; CRYPTO_PUBLICKEYBYTES];
    let private_key_bytes = private_key.as_bytes();

    if private_key_bytes.len() != CRYPTO_SECRETKEYBYTES {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid private key length"));
    }

    // Create a new array for the private key
    let mut sk = [0u8; CRYPTO_SECRETKEYBYTES];
    sk.copy_from_slice(private_key_bytes);

    crypto_kem_keypair(&mut pk, &mut sk, &mut rng)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

    Ok(PyBytes::new(py, &pk).into())
}


#[pyfunction]
/// Encrypts a message using the public key.
///
/// Args:
///     public_key (bytes): The public key as a byte sequence.
///     message (bytes): The message to be encrypted as a byte sequence.
///
/// Returns:
///     bytes: The ciphertext, which includes the KEM ciphertext, nonce, and AES ciphertext.
fn encrypt(py: Python, public_key: &PyBytes, message: &PyBytes) -> PyResult<Py<PyBytes>> {
    let mut rng = AesState::new();
    let mut ct = [0u8; CRYPTO_CIPHERTEXTBYTES];
    let mut ss = [0u8; CRYPTO_BYTES];

    let public_key_bytes = public_key.as_bytes();
    if public_key_bytes.len() != CRYPTO_PUBLICKEYBYTES {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid public key length"));
    }

    crypto_kem_enc(&mut ct, &mut ss, public_key_bytes.try_into().map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid public key length"))?, &mut rng)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

    let key = Key::from_slice(&ss);
    let cipher = Aes256Gcm::new(key);

    // Generate a random nonce
    let mut nonce_bytes = [0u8; 12];
    rand::thread_rng().fill(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ciphertext = cipher.encrypt(nonce, message.as_bytes())
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

    // Combine the KEM ciphertext, nonce, and the AES ciphertext
    let mut combined = Vec::with_capacity(CRYPTO_CIPHERTEXTBYTES + nonce_bytes.len() + ciphertext.len());
    combined.extend_from_slice(&ct);
    combined.extend_from_slice(&nonce_bytes);
    combined.extend_from_slice(&ciphertext);

    Ok(PyBytes::new(py, &combined).into())
}


#[pyfunction]
/// Decrypts a ciphertext using the private key.
///
/// Args:
///     private_key (bytes): The private key as a byte sequence.
///     ciphertext (bytes): The ciphertext as a byte sequence, which includes the KEM ciphertext, nonce, and AES ciphertext.
///
/// Returns:
///     bytes: The decrypted message.
fn decrypt(py: Python, private_key: &PyBytes, ciphertext: &PyBytes) -> PyResult<Py<PyBytes>> {
    let private_key_bytes = private_key.as_bytes();
    if private_key_bytes.len() != CRYPTO_SECRETKEYBYTES {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid private key length"));
    }

    let ciphertext_bytes = ciphertext.as_bytes();
    if ciphertext_bytes.len() < CRYPTO_CIPHERTEXTBYTES + 12 {
        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid ciphertext length"));
    }

    let (kem_ct, rest) = ciphertext_bytes.split_at(CRYPTO_CIPHERTEXTBYTES);
    let nonce = Nonce::from_slice(&rest[..12]);
    let aes_ct = &rest[12..];

    let mut ss = [0u8; CRYPTO_BYTES];
    let kem_ct_array: &[u8; CRYPTO_CIPHERTEXTBYTES] = kem_ct.try_into().map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid KEM ciphertext length"))?;
    let private_key_array: &[u8; CRYPTO_SECRETKEYBYTES] = private_key_bytes.try_into().map_err(|_| PyErr::new::<pyo3::exceptions::PyValueError, _>("Invalid private key length"))?;

    crypto_kem_dec(&mut ss, kem_ct_array, private_key_array)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

    let key = Key::from_slice(&ss);
    let cipher = Aes256Gcm::new(key);

    let plaintext = cipher.decrypt(nonce, aes_ct)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("{:?}", e)))?;

    Ok(PyBytes::new(py, &plaintext).into())
}


#[pymodule]
/// A Python module that wraps the NTRU post-quantum encryption scheme using Rust.
fn py_ntru(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(generate_private_key, m)?)?;
    m.add_function(wrap_pyfunction!(generate_public_key, m)?)?;
    m.add_function(wrap_pyfunction!(encrypt, m)?)?;
    m.add_function(wrap_pyfunction!(decrypt, m)?)?;
    Ok(())
}
