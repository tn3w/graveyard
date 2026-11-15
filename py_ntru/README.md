# py_ntru

Welcome to the `py_ntru` documentation! This library provides a Python wrapper around the Rust NTRU library, enabling the use of post-quantum cryptographic algorithms with enhanced performance and availability. The following comprehensive guide will walk you through the installation, building, and usage processes.

## 🚀 Installation

### Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Python 3.7+**: The latest version of Python 3 is recommended. You can download it from the [official Python website](https://www.python.org/downloads/).
- **Rust**: Required for compiling the Rust code. You can install it via [rustup](https://rustup.rs/).

### Virtualenv Setup

Using a virtual environment helps manage dependencies and avoid conflicts. Follow these steps to set it up:

1. **Create a Virtual Environment**

   Run the following command to create a virtual environment in the current directory:

   ```bash
   python -m venv .venv
   ```

2. **Activate the Virtual Environment**

   - On **Linux/macOS**, activate the virtual environment with:

     ```bash
     source .venv/bin/activate
     ```

   - On **Windows**, use:

     ```bash
     .venv\Scripts\activate
     ```

### Installing Dependencies

1. **Install Maturin**

   Maturin is a tool for building and publishing Rust-based Python packages. Install it using pip:

   ```bash
   pip install maturin
   ```

2. **Clone the Repository**

   Clone the `py_ntru` repository from GitHub to your local machine:

   ```bash
   git clone https://github.com/tn3w/py_ntru.git
   ```

3. **Navigate to the Repository Directory**

   Change your working directory to the `py_ntru` directory:

   ```bash
   cd py_ntru
   ```

4. **Build the Python Package**

   Use Maturin to compile the Rust code and create a Python extension wheel. The `--release` flag ensures that the code is optimized for performance:

   ```bash
   maturin build --release
   ```

5. **Locate the Wheel File**

   After building, navigate to the directory where the wheel file is located:

   ```bash
   ls target/wheels
   ```

6. **Install the Wheel File**

   Install the wheel file using pip. Replace `<version>` and `<build>` with the actual version and build number from the wheel file:

   ```bash
   pip install target/wheels/py_ntru-<version>-<build>.whl
   ```

## 🛞 Building Wheels Using Docker

If you prefer to build the package in a Docker container, follow these steps:

1. **Build the Docker Image**

   Use the provided Dockerfile to build the Docker image. This image contains all the necessary dependencies for building `py_ntru`:

   ```bash
   sudo docker build -t py_ntru_builder .
   ```

2. **Run the Docker Container**

   Start a container from the image and mount your local repository directory:

   ```bash
   sudo docker run --rm -it -v $(pwd):/workspace py_ntru_builder
   ```

   Inside the Docker container, navigate to the `/workspace` directory and build the package as described in the [Building the Python Package](#build-the-python-package) section.

## 📝 Direct Usage

Once `py_ntru` is installed, you can use it in your Python scripts. Here is a basic example of how to use the basic library:

```python
import py_ntru

# Generate a private key
private_key = py_ntru.generate_private_key()
print(f"Private Key: {private_key}")

# Generate a public key based on the private key
public_key = py_ntru.generate_public_key(private_key)
print(f"Public Key: {public_key}")

# Message to encrypt
message = b"Hello!"
print(f"Original Message: {message}")

# Encrypt the message using the public key
ciphertext = py_ntru.encrypt(public_key, message)
print(f"Ciphertext: {ciphertext}")

# Decrypt the ciphertext using the private key
decrypted_message = py_ntru.decrypt(private_key, ciphertext)
print(f"Decrypted Message: {decrypted_message}")

```

## 🛠 Troubleshooting

If you encounter any issues during installation or usage, consider the following:

- **Ensure Compatibility**: Check that your versions of Python, Rust, and Maturin are compatible with `py_ntru`.
- **Check Dependencies**: Verify that all necessary dependencies are installed and up-to-date.
- **Consult Logs**: Review error messages and logs for clues on what might be going wrong.

For additional support, you can open an issue on the [GitHub repository](https://github.com/tn3w/py_ntru/issues) or consult the community forums.

## 📚 Contributing

Contributions to `py_ntru` are welcome! If you'd like to contribute, please follow these guidelines:

1. **Fork the Repository**: Create a personal fork of the `py_ntru` repository.
2. **Create a Branch**: Make a new branch for your changes.
3. **Make Changes**: Implement your changes and ensure they adhere to the project's coding standards.
4. **Submit a Pull Request**: Push your branch to your fork and submit a pull request to the main repository.


# Documentation
Here is a test code that shows the functionality of the extended module:

```python
from ntru import (
   generate_public_key, generate_secret_key,
   NTRUPublicKey, NTRUSecretKey, NTRUKeyPair,
   NTRU
)

public_key = generate_public_key() # NTRUPublicKey instance
secret_key = generate_secret_key() # NTRUSecretKey instance

public_key = secret_key.public_key # NTRUSecretKey can generate public keys
# public_key is NTRUPublicKey instance

#### Serialization ####

base64_secret_key = NTRUSecretKey(secret_key.secret_key, "base64")
print(base64_secret_key) # Has __call__, __str__, __len__

public_key_bytes = public_key.public_key # bytes
serialized_public_key = public_key.serialized_public_key # Base64 serialized str
# also works for private key

hex_public_key = NTRUPublicKey(public_key_bytes, serialization = "hex") # Serialization can be changed
print(hex_public_key) # Hex serialized str

#### Key Pair ####

# If you have a bytes, serialized str or KeyClass you can create an KeyPair

key_pair = NTRUKeyPair(public_key) # Just public key
key_pair = NTRUKeyPair(None, secret_key) # Both (public key is generated based on private key)
key_pair = NTRUKeyPair(public_key, secret_key) # Both

#### Encryption / Decryption ####

ntru = NTRU(key_pair)

test_plain = "Hello, World!"
cipher_value = ntru.encrypt(test_plain, "base64")
print(cipher_value)

plain_value = ntru.decrypt(cipher_value, "base64")
print(plain_value) # Hello, World!

```

## Overview

This module provides a comprehensive implementation of the NTRU public key cryptosystem, including serialization options in various formats such as UTF-8, Hex, Base64, and Base64 URL-safe. It also includes functionalities for generating NTRU public and secret keys, and encrypting/decrypting data using these keys.

The module is organized into several classes, each responsible for specific tasks such as serialization, key management, and encryption/decryption. Below, we document each class and function in detail, complete with docstrings, usage examples, and expected outputs.

---

## Table of Contents

1. [Classes](#classes)
   
   Serialization:
   - [Serialization](#serialization)
   - [Nothing](#nothing)
   - [UTF8](#utf8)
   - [Hex](#hex)
   - [Base64](#base64)
   - [Base64UrlSafe](#base64urlsafe)

   NTRU:
   - [NTRUPublicKey](#ntrupublickey)
   - [NTRUSecretKey](#ntrusecretkey)
   - [NTRUKeyPair](#ntru_key_pair)
   - [NTRU](#ntru)
2. [Functions](#functions)
   - [generate_public_key](#generate_public_key)
   - [generate_secret_key](#generate_secret_key)

---

## Classes

### Serialization

**Description**:  
`Serialization` is the base class for all serialization formats. It provides two abstract methods for encoding and decoding data.

**Methods**:

- `encode(plain: bytes) -> str`: Encodes the given bytes into a string.
- `decode(serialized: str) -> bytes`: Decodes the given string back into bytes.

---

### Nothing

**Description**:  
The `Nothing` class is a subclass of `Serialization` that performs no serialization or deserialization. It returns the data as-is.

**Methods**:

- `encode(plain: bytes) -> bytes`: Returns the input bytes unchanged.
- `decode(serialized: bytes) -> bytes`: Returns the input bytes unchanged.

#### Example Usage:

```python
# Example code snippet
data = b'example data'
nothing = Nothing()
encoded_data = nothing.encode(data)
decoded_data = nothing.decode(encoded_data)

print(encoded_data)  # Outputs: b'example data'
print(decoded_data)  # Outputs: b'example data'
```

---

### UTF8

**Description**:  
The `UTF8` class is a subclass of `Serialization` that handles encoding and decoding data using the UTF-8 format.

**Methods**:

- `encode(plain: bytes) -> str`: Encodes bytes to a UTF-8 string.
- `decode(serialized: str) -> bytes`: Decodes a UTF-8 string back to bytes.

#### Example Usage:

```python
# Example code snippet
data = b'example data'
utf8 = UTF8()
encoded_data = utf8.encode(data)
decoded_data = utf8.decode(encoded_data)

print(encoded_data)  # Outputs: 'example data'
print(decoded_data)  # Outputs: b'example data'
```

---

### Hex

**Description**:  
The `Hex` class is a subclass of `Serialization` that handles encoding and decoding data using the hexadecimal format.

**Methods**:

- `encode(plain: bytes) -> str`: Encodes bytes to a hexadecimal string.
- `decode(serialized: str) -> bytes`: Decodes a hexadecimal string back to bytes.

#### Example Usage:

```python
# Example code snippet
data = b'example data'
hex_serializer = Hex()
encoded_data = hex_serializer.encode(data)
decoded_data = hex_serializer.decode(encoded_data)

print(encoded_data)  # Outputs: '6578616d706c652064617461'
print(decoded_data)  # Outputs: b'example data'
```

---

### Base64

**Description**:  
The `Base64` class is a subclass of `Serialization` that handles encoding and decoding data using the Base64 format.

**Methods**:

- `encode(plain: bytes) -> str`: Encodes bytes to a Base64 string.
- `decode(serialized: str) -> bytes`: Decodes a Base64 string back to bytes.

#### Example Usage:

```python
# Example code snippet
data = b'example data'
base64_serializer = Base64()
encoded_data = base64_serializer.encode(data)
decoded_data = base64_serializer.decode(encoded_data)

print(encoded_data)  # Outputs: 'ZXhhbXBsZSBkYXRh'
print(decoded_data)  # Outputs: b'example data'
```

---

### Base64UrlSafe

**Description**:  
The `Base64UrlSafe` class is a subclass of `Serialization` that handles encoding and decoding data using the URL-safe Base64 format.

**Methods**:

- `encode(plain: bytes) -> str`: Encodes bytes to a URL-safe Base64 string.
- `decode(serialized: str) -> bytes`: Decodes a URL-safe Base64 string back to bytes.

#### Example Usage:

```python
# Example code snippet
data = b'example data'
base64_urlsafe = Base64UrlSafe()
encoded_data = base64_urlsafe.encode(data)
decoded_data = base64_urlsafe.decode(encoded_data)

print(encoded_data)  # Outputs: 'ZXhhbXBsZSBkYXRh'
print(decoded_data)  # Outputs: b'example data'
```

---

### NTRUPublicKey

**Description**:  
The `NTRUPublicKey` class represents an NTRU public key. It provides methods to access the public key in both raw and serialized formats.

**Methods and Properties**:

- `public_key`: Retrieves the raw public key as bytes.
- `serialized_public_key`: Retrieves the serialized public key as a string.
- `generate()`: Generates a new public key.
- `get_public_key() -> bytes`: Retrieves the raw public key.
- `get_serialized_public_key() -> str`: Retrieves the serialized public key.

#### Example Usage:

```python
# Example code snippet
public_key = b'some_public_key_bytes'
ntru_public_key = NTRUPublicKey(public_key, 'hex')

print(ntru_public_key.public_key)  # Outputs: b'some_public_key_bytes'
print(ntru_public_key.serialized_public_key)  # Outputs: '736f6d655f7075626c69635f6b65795f6279746573' (hex representation)
```

---

### NTRUSecretKey

**Description**:  
The `NTRUSecretKey` class represents an NTRU secret key. It provides methods to access the secret key in both raw and serialized formats, as well as retrieving the associated public key.

**Methods and Properties**:

- `secret_key`: Retrieves the raw secret key as bytes.
- `serialized_secret_key`: Retrieves the serialized secret key as a string.
- `public_key`: Retrieves the associated public key.
- `generate()`: Generates a new secret key.
- `get_secret_key() -> bytes`: Retrieves the raw secret key.
- `get_serialized_secret_key() -> str`: Retrieves the serialized secret key.
- `get_public_key() -> NTRUPublicKey`: Retrieves the associated public key.

#### Example Usage:

```python
# Example code snippet
secret_key = b'some_secret_key_bytes'
ntru_secret_key = NTRUSecretKey(secret_key, 'base64')

print(ntru_secret_key.secret_key)  # Outputs: b'some_secret_key_bytes'
print(ntru_secret_key.serialized_secret_key)  # Outputs: 'c29tZV9zZWNyZXRfa2V5X2J5dGVz' (base64 representation)
```

---

### NTRUKeyPair

**Description**:  
The `NTRUKeyPair` class represents a pair of NTRU public and secret keys. It provides methods to generate and access these keys.

**Methods and Properties**:

- `public_key`: Retrieves the public key.
- `secret_key`: Retrieves the secret key.
- `generate()`: Generates a new key pair.
- `get_public_key() -> Optional[NTRUPublicKey]`: Retrieves the public key.
- `get_secret_key() -> Optional[NTRUSecretKey]`: Retrieves the secret key.

#### Example Usage:

```python
# Example code snippet
ntru_key_pair = NTRUKeyPair()
ntru_key_pair.generate()

print(ntru_key_pair.public_key)  # Outputs: The generated NTRU public key
print(ntru_key_pair.secret_key)  # Outputs: The generated NTRU secret key
```

---

### NTRU

**Description**:  
The `NTRU` class provides encryption and decryption functionalities using NTRU keys.

**Methods**:

- `encrypt(plain_value: Union[str, bytes], serialization: Union[Serialization, str] = "bytes") -> Union[str, bytes]`: Encrypts the given plaintext value.
- `decrypt(cipher_value: Union[str, bytes], serialization: Union[Serialization, str] = "bytes") -> Union[str, bytes]`: Decrypts the given ciphertext value.

#### Example Usage:

```python
# Example code snippet
ntru_key_pair = NTRUKeyPair()
ntru_key_pair.generate()

ntru = NTRU(ntru_key_pair.public_key, ntru_key_pair.secret_key)

cipher = ntru.encrypt("Hello, world!", "base64")
print(cipher)  # Outputs: Encrypted value in base64 format

plain = ntru.decrypt(cipher, "base64")
print(plain)  # Outputs: "Hello, world!"
```

---

## Functions

### generate_public_key

**Description**:  
Generates and returns a public key as an `NTRUPublicKey` instance.

**Parameters**:

- `serialized (bool)`: If `True`, returns the public key in serialized form.

**Returns**:  
An instance of `NTRUPublicKey`.

#### Example Usage:

```python
# Example code snippet
public_key = generate_public_key()

print(public_key)  # Outputs: NTRUPublicKey instance
```

---

### generate_secret_key

**Description**:  
Generates and returns a secret key as an `NTRUSecretKey` instance.

**Parameters**:

- `serialized (bool)`: If `True`, returns the secret key in serialized form.

**Returns**:  
An instance of `NTRUSecretKey`.

#### Example Usage:

```python
# Example code snippet
secret_key = generate_secret_key()

print(secret_key)  # Outputs: NTRUSecretKey instance
```

---

Thank you for using `py_ntru` and contributing to the advancement of post-quantum cryptography!
