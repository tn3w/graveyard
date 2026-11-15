"""
This module provides classes and functions for serialization and encryption
using the NTRU public key cryptosystem. It includes various serialization
formats such as UTF-8, Hex, Base64, and Base64 URL-safe, as well as
functionality to generate public and secret keys.

Classes:
- Serialization: Base class for serialization formats.
- Nothing: No serialization, returns the data as-is.
- UTF8: Serializes data to and from UTF-8 format.
- Hex: Serializes data to and from hexadecimal format.
- Base64: Serializes data to and from Base64 format.
- Base64UrlSafe: Serializes data to and from URL-safe Base64 format.
- NTRUPublicKey: Represents an NTRU public key.
- NTRUSecretKey: Represents an NTRU secret key.
- NTRUKeyPair: Represents a pair of NTRU public and secret keys.
- NTRU: Provides encryption and decryption functionality using NTRU keys.

Functions:
- remove_special_characters: Removes special characters from a string.
- load_serialization: Loads a serialization class based on input.
- generate_public_key: Generates a new NTRU public key.
- generate_secret_key: Generates a new NTRU secret key.
"""

import re
from typing import Final, Callable, Union, Optional
from base64 import b64encode, b64decode, urlsafe_b64encode, urlsafe_b64decode
import py_ntru


def remove_special_characters(text: str) -> str:
    """
    Removes special characters from the input text, retaining only
    alphabetic characters.

    Args:
        text (str): The input string from which to remove special characters.

    Return:
        str: The cleaned string containing only alphabetic characters.
    """

    if not isinstance(text, str):
        return text

    return re.sub(r'[^a-zA-Z]', '', text)


class Serialization:
    """
    Base class for serialization formats. Provides methods for encoding
    and decoding data.

    Methods:
        encode(plain: bytes) -> str: Encodes the given bytes into a string.
        decode(serialized: str) -> bytes: Decodes the given string back into bytes.
    """


    @staticmethod
    def encode(plain: bytes) -> str:
        """
        Encodes the given bytes into a string.

        Args:
            plain (bytes): The bytes to encode.

        Return:
            str: The encoded string.
        """


    @staticmethod
    def decode(serialized: str) -> bytes:
        """
        Decodes the given string back into bytes.

        Args:
            serialized (str): The string to decode.

        Return:
            bytes: The decoded bytes.
        """


class Nothing(Serialization):
    """
    No serialization class. Returns the data as-is without any encoding
    or decoding.

    Methods:
        encode(plain: bytes) -> bytes: Returns the input bytes unchanged.
        decode(serialized: bytes) -> bytes: Returns the input bytes unchanged.
    """


    @staticmethod
    def encode(plain: bytes) -> bytes:
        """
        Returns the input bytes unchanged.

        Args:
            plain (bytes): The bytes to encode.

        Return:
            bytes: The unchanged input bytes.
        """

        return plain


    @staticmethod
    def decode(serialized: bytes) -> bytes:
        """
        Returns the input bytes unchanged.

        Args:
            serialized (bytes): The bytes to decode.

        Return:
            bytes: The unchanged input bytes.
        """

        return serialized


class UTF8(Serialization):
    """
    UTF-8 serialization class. Encodes and decodes data using UTF-8 format.

    Methods:
        encode(plain: bytes) -> str: Encodes bytes to a UTF-8 string.
        decode(serialized: str) -> bytes: Decodes a UTF-8 string back to bytes.
    """


    @staticmethod
    def encode(plain: bytes) -> str:
        """
        Encodes bytes to a UTF-8 string.

        Args:
            plain (bytes): The bytes to encode.

        Return:
            str: The encoded UTF-8 string.
        """

        return plain.decode('utf-8')


    @staticmethod
    def decode(serialized: str) -> bytes:
        """
        Decodes a UTF-8 string back to bytes.

        Args:
            serialized (str): The UTF-8 string to decode.

        Return:
            bytes: The decoded bytes.
        """

        return serialized.encode('utf-8')


class Hex(Serialization):
    """
    Hex serialization class. Encodes and decodes data using hexadecimal format.

    Methods:
        encode(plain: bytes) -> str: Encodes bytes to a hexadecimal string.
        decode(serialized: str) -> bytes: Decodes a hexadecimal string back to bytes.
    """


    @staticmethod
    def encode(plain: bytes) -> str:
        """
        Encodes bytes to a hexadecimal string.

        Args:
            plain (bytes): The bytes to encode.

        Return:
            str: The encoded hexadecimal string.
        """

        return plain.hex()


    @staticmethod
    def decode(serialized: str) -> bytes:
        """
        Decodes a hexadecimal string back to bytes.

        Args:
            serialized (str): The hexadecimal string to decode.

        Return:
            bytes: The decoded bytes.
        """

        return bytes.fromhex(serialized)


class Base64(Serialization):
    """
    Base64 serialization class. Encodes and decodes data using Base64 format.

    Methods:
        encode(plain: bytes) -> str: Encodes bytes to a Base64 string.
        decode(serialized: str) -> bytes: Decodes a Base64 string back to bytes.
    """


    @staticmethod
    def encode(plain: bytes) -> str:
        """
        Encodes bytes to a Base64 string.

        Args:
            plain (bytes): The bytes to encode.

        Return:
            str: The encoded Base64 string without padding.
        """

        serialized = b64encode(plain).decode('utf-8')
        return serialized.rstrip("=")


    @staticmethod
    def decode(serialized: str) -> bytes:
        """
        Decodes a Base64 string back to bytes.

        Args:
            serialized (str): The Base64 string to decode.

        Return:
            bytes: The decoded bytes.
        """

        padding_needed = (4 - len(serialized) % 4) % 4
        serialized += '=' * padding_needed

        return b64decode(serialized)


class Base64UrlSafe(Serialization):
    """
    Base64 URL-safe serialization class. Encodes and decodes data using
    URL-safe Base64 format.

    Methods:
        encode(plain: bytes) -> str: Encodes bytes to a URL-safe Base64 string.
        decode(serialized: str) -> bytes: Decodes a URL-safe Base64 string back to bytes.
    """


    @staticmethod
    def encode(plain: bytes) -> str:
        """
        Encodes bytes to a URL-safe Base64 string.

        Args:
            plain (bytes): The bytes to encode.

        Return:
            str: The encoded URL-safe Base64 string without padding.
        """

        serialized = urlsafe_b64encode(plain).decode('utf-8')
        return serialized.rstrip("=")


    @staticmethod
    def decode(serialized: str) -> bytes:
        """
        Decodes a URL-safe Base64 string back to bytes.

        Args:
            serialized (str): The URL-safe Base64 string to decode.

        Return:
            bytes: The decoded bytes.
        """

        padding_needed = (4 - len(serialized) % 4) % 4
        serialized += '=' * padding_needed

        return urlsafe_b64decode(serialized)


SERIALIZATIONS: Final[dict[Callable]] = {
    "bytes": Nothing,
    "utf": UTF8,
    "hex": Hex,
    "base": Base64,
    "baseurlsafe": Base64UrlSafe
}


def load_serialization(serialization: Union[Callable, str] = Base64) -> Callable:
    """
    Loads a serialization class based on the input. If a string is provided,
    it will be matched against known serialization types.

    Args:
        serialization (Union[Callable, str]): The serialization type or class.

    Return:
        Serialization: The corresponding serialization class.
    """

    if not isinstance(serialization, Callable):
        serialization = SERIALIZATIONS.get(
            remove_special_characters(serialization).lower(), UTF8
        )

    return serialization


def generate_public_key(serialization: Union[Callable, str] = Base64) -> "NTRUPublicKey":
    """
    Generates a new NTRU public key using a newly generated secret key.

    Args:
        serialization (Union[Callable, str]): The serialization type or class.

    Return:
        NTRUPublicKey: The generated NTRU public key.
    """

    secret_key = py_ntru.generate_private_key()
    callable_secret_key = NTRUSecretKey(secret_key)

    public_key = py_ntru.generate_public_key(secret_key)
    return NTRUPublicKey(public_key, serialization, callable_secret_key)


def generate_secret_key(serialization: Union[Callable, str] = Base64) -> "NTRUSecretKey":
    """
    Generates a new NTRU secret key.

    Args:
        serialization (Union[Callable, str]): The serialization type or class.

    Return:
        NTRUSecretKey: The generated NTRU secret key.
    """

    secret_key = py_ntru.generate_private_key()

    return NTRUSecretKey(secret_key, serialization)


class NTRUPublicKey:
    """
    Represents an NTRU public key. Provides methods to access the public key
    in both raw and serialized formats.

    Args:
        public_key (Union[bytes, str]): The public key in bytes or serialized format.
        serialization (Union[Callable, str]): The serialization type or class.
        callable_secret_key (Optional[NTRUSecretKey]): An optional callable secret key.

    Properties:
        public_key (bytes): The raw public key.
        serialized_public_key (str): The serialized public key.
    """


    def __init__(self, public_key: Union[bytes, str],
                 serialization: Union[Callable, str] = Base64,
                 callable_secret_key: Optional["NTRUSecretKey"] = None) -> None:
        """
        Initializes the NTRUPublicKey instance.

        Args:
            public_key (Union[bytes, str]): The public key in bytes or serialized format.
            serialization (Union[Serialization, str]): The serialization type or class.
            callable_secret_key (Optional[NTRUSecretKey]): An optional callable secret key.
        """

        self.serialization = load_serialization(serialization)

        loaded_public_key, serialized_public_key = None, None
        if isinstance(public_key, bytes):
            loaded_public_key = public_key
        else:
            serialized_public_key = public_key

        self._public_key, self._serialized_public_key =\
            loaded_public_key, serialized_public_key

        self.secret_key = callable_secret_key


    @property
    def public_key(self) -> bytes:
        """
        Gets the raw public key.

        Return:
            bytes: The raw public key.
        """

        return self.get_public_key()


    @property
    def serialized_public_key(self) -> str:
        """
        Gets the serialized public key.

        Return:
            str: The serialized public key.
        """

        return self.get_serialized_public_key()


    def generate(self) -> None:
        """
        Generates a new public key.

        Return:
            None
        """

        return self.generate_public_key()


    def generate_public_key(self) -> None:
        """
        Generates a new public key using a newly generated secret key.

        Return:
            None
        """

        secret_key = py_ntru.generate_private_key()
        self.secret_key = NTRUSecretKey(secret_key)

        self._public_key = py_ntru.generate_public_key(secret_key)


    def get_public_key(self) -> bytes:
        """
        Retrieves the raw public key, decoding it if necessary.

        Return:
            bytes: The raw public key.
        """

        if self._public_key is None and\
            self._serialized_public_key is not None:

            self._public_key = self.serialization.decode(
                self._serialized_public_key
            )

        return self._public_key


    def get_serialized_public_key(self) -> str:
        """
        Retrieves the serialized public key, encoding it if necessary.

        Return:
            str: The serialized public key.
        """

        if self._serialized_public_key is None and\
            self._public_key is not None:

            self._serialized_public_key = self.serialization.encode(
                self._public_key
            )

        return self._serialized_public_key


    def get(self) -> bytes:
        """
        Gets the raw public key.

        Return:
            bytes: The raw public key.
        """

        return self.get_public_key()


    def get_serialized(self) -> str:
        """
        Gets the serialized public key.

        Return:
            str: The serialized public key.
        """

        return self.get_serialized_public_key()


    def __call__(self) -> str:
        """
        Returns the serialized public key.

        Return:
            str: The serialized public key.
        """

        return self.serialized_public_key


    def __str__(self) -> str:
        """
        Returns the serialized public key.

        Return:
            str: The serialized public key.
        """

        return self.serialized_public_key


    def __len__(self) -> int:
        """
        Returns the length of the serialized public key.

        Return:
            int: The length of the serialized public key.
        """

        return len(self.__str__())


class NTRUSecretKey:
    """
    Represents an NTRU secret key. Provides methods to access the secret key
    in both raw and serialized formats.

    Args:
        secret_key (Union[bytes, str]): The secret key in bytes or serialized format.
        serialization (Union[Serialization, str]): The serialization type or class.

    Properties:
        secret_key (bytes): The raw secret key.
        serialized_secret_key (str): The serialized secret key.
        public_key (NTRUPublicKey): The associated public key.
    """


    def __init__(self, secret_key: Union[bytes, str],
                 serialization: Union[Callable, str] = Base64) -> None:
        """
        Initializes the NTRUSecretKey instance.

        Args:
            secret_key (Union[bytes, str]): The secret key in bytes or serialized format.
            serialization (Union[Callable, str]): The serialization type or class.
        """

        self.serialization = load_serialization(serialization)

        loaded_secret_key, serialized_secret_key = None, None
        if isinstance(secret_key, bytes):
            loaded_secret_key = secret_key
        else:
            serialized_secret_key = secret_key

        self._secret_key, self._serialized_secret_key =\
            loaded_secret_key, serialized_secret_key

        self._public_key = None
        self._encoded_public_key = None


    @property
    def secret_key(self) -> bytes:
        """
        Gets the raw secret key.

        Return:
            bytes: The raw secret key.
        """

        return self.get_secret_key()


    @property
    def serialized_secret_key(self) -> str:
        """
        Gets the serialized secret key.

        Return:
            str: The serialized secret key.
        """

        return self.get_serialized_secret_key()


    @property
    def public_key(self) -> NTRUPublicKey:
        """
        Gets the associated public key.

        Return:
            NTRUPublicKey: The associated public key.
        """

        return self.get_public_key()


    def generate(self) -> None:
        """
        Generates a new secret key.

        Return:
            None
        """

        return self.generate_secret_key()


    def generate_secret_key(self) -> None:
        """
        Generates a new secret key.

        Return:
            None
        """

        self._secret_key = py_ntru.generate_private_key()


    def get_secret_key(self) -> bytes:
        """
        Retrieves the raw secret key, decoding it if necessary.

        Return:
            bytes: The raw secret key.
        """

        if self._secret_key is None and\
            self._serialized_secret_key is not None:

            self._secret_key = self.serialization.decode(
                self._serialized_secret_key
            )

        return self._secret_key


    def get_serialized_secret_key(self) -> str:
        """
        Retrieves the serialized secret key, encoding it if necessary.

        Return:
            str: The serialized secret key.
        """

        if self._serialized_secret_key is None and\
            self._secret_key is not None:

            self._serialized_secret_key = self.serialization.encode(
                self.secret_key
            )

        return self._serialized_secret_key


    def get(self) -> bytes:
        """
        Gets the raw secret key.

        Return:
            bytes: The raw secret key.
        """

        return self.get_secret_key()


    def get_serialized(self) -> str:
        """
        Gets the serialized secret key.

        Return:
            str: The serialized secret key.
        """

        return self.get_serialized_secret_key()


    def get_public(self) -> NTRUPublicKey:
        """
        Gets the associated public key.

        Return:
            NTRUPublicKey: The associated public key.
        """

        return self.get_public_key()


    def get_public_key(self) -> NTRUPublicKey:
        """
        Retrieves the associated public key, generating it if necessary.

        Return:
            NTRUPublicKey: The associated public key.
        """

        if self._public_key is None:
            public_key = py_ntru.generate_public_key(self.get_secret_key())
            self._public_key = NTRUPublicKey(public_key, self.serialization)

        return self._public_key


    def __call__(self) -> str:
        """
        Returns the serialized secret key.

        Return:
            str: The serialized secret key.
        """

        return self.serialized_secret_key


    def __str__(self) -> str:
        """
        Returns the serialized secret key.

        Return:
            str: The serialized secret key.
        """

        return self.serialized_secret_key


    def __len__(self) -> int:
        """
        Returns the length of the serialized secret key.

        Return:
            int: The length of the serialized secret key.
        """

        return len(self.__str__())


class NTRUKeyPair:
    """
    Represents a pair of NTRU public and secret keys. Provides methods to
    generate and access the keys.

    Args:
        public_key (Optional[Union[NTRUPublicKey, bytes, str]]): The public key.
        secret_key (Optional[Union[NTRUSecretKey, bytes, str]]): The secret key.
        serialization (Union[Callable, str]): The serialization type or class.

    Properties:
        public_key (Optional[NTRUPublicKey]): The public key.
        secret_key (Optional[NTRUSecretKey]): The secret key.
    """


    def __init__(self, public_key: Optional[Union[NTRUPublicKey, bytes, str]] = None,
                 secret_key: Optional[Union[NTRUSecretKey, bytes, str]] = None,
                 serialization: Union[Callable, str] = Base64) -> None:
        """
        Initializes the NTRUKeyPair instance.

        Args:
            public_key (Optional[Union[NTRUPublicKey, bytes, str]]): The public key.
            secret_key (Optional[Union[NTRUSecretKey, bytes, str]]): The secret key.
            serialization (Union[Callable, str]): The serialization type or class.
        """

        self.serialization = load_serialization(serialization)

        if isinstance(public_key, (bytes, str)):
            public_key = NTRUPublicKey(public_key, serialization)

        self._public_key = public_key

        if isinstance(secret_key, (bytes, str)):
            secret_key = NTRUSecretKey(secret_key, serialization)

        self._secret_key = secret_key


    def generate(self) -> None:
        """
        Generates a new key pair.

        Return:
            None
        """

        return self.generate_keypair()


    def generate_keypair(self) -> None:
        """
        Generates a new NTRU key pair.

        Return:
            None
        """

        self._secret_key = generate_secret_key(self.serialization)


    @property
    def public_key(self) -> Optional[NTRUPublicKey]:
        """
        Gets the public key.

        Return:
            Optional[NTRUPublicKey]: The public key.
        """

        return self.get_public_key()


    @property
    def secret_key(self) -> Optional[NTRUSecretKey]:
        """
        Gets the secret key.

        Return:
            Optional[NTRUSecretKey]: The secret key.
        """

        return self.get_secret_key()


    def get_public_key(self) -> Optional[NTRUPublicKey]:
        """
        Retrieves the public key, generating it if necessary.

        Return:
            Optional[NTRUPublicKey]: The public key.
        """

        if self._public_key is None and\
            not self._secret_key is None:

            self._public_key = self._secret_key.get_public_key()

        return self._public_key


    def get_secret_key(self) -> Optional[NTRUSecretKey]:
        """
        Gets the secret key.

        Return:
            Optional[NTRUSecretKey]: The secret key.
        """

        return self._secret_key


    def __call__(self) -> str:
        """
        Returns the serialized public key if available, otherwise the serialized secret key.

        Return:
            str: The serialized public key and secret key.
        """

        key_string = ""
        for key in [self._public_key, self._secret_key]:
            if key is None:
                continue

            key_string += key.get_serialized()

        return key_string


    def __str__(self) -> str:
        """
        Returns the serialized public key if available, otherwise the serialized secret key.

        Return:
            str: The serialized public key or secret key.
        """

        return self.__call__()


    def __len__(self) -> int:
        """
        Returns the length of the serialized key (public or secret).

        Return:
            int: The length of the serialized key.
        """

        return len(self.__str__())


class NTRU:
    """
    Provides encryption and decryption functionality using NTRU keys.

    Args:
        key_pair (NTRUKeyPair): The NTRU key pair to use for encryption and decryption.

    Methods:
        encrypt(plain_value: Union[str, bytes], serialization:
            Union[Callable, str] = "bytes") -> Union[str, bytes]:
            Encrypts the given plaintext value.
        decrypt(cipher_value: Union[str, bytes], serialization:
            Union[Callable, str] = "bytes") -> Union[str, bytes]:
            Decrypts the given ciphertext value.
    """


    def __init__(self, key_pair: NTRUKeyPair) -> None:
        """
        Initializes the NTRU instance.
            
        Args:
            key_pair (NTRUKeyPair): The NTRU key pair to be
                                    used for encryption and decryption operations.
        """

        self.key_pair = key_pair


    def encrypt(self, plain_value: Union[str, bytes],
                serialization: Union[Callable, str] = "bytes") -> Union[str, bytes]:
        """
        Encrypts the given plaintext value using the public key.

        Args:
            plain_value (Union[str, bytes]): The plaintext value to encrypt.
            serialization (Union[Callable, str]): The serialization type or class.

        Return:
            Union[str, bytes]: The encrypted ciphertext, serialized as specified.
        """

        if isinstance(plain_value, str):
            plain_value = plain_value.encode('utf-8')

        serialization = load_serialization(serialization)

        public_key = self.key_pair.get_public_key().public_key
        cipher_value = py_ntru.encrypt(public_key, plain_value)

        serialized_cipher_value = serialization.encode(cipher_value)
        return serialized_cipher_value


    def decrypt(self, cipher_value: Union[str, bytes],
                serialization: Union[Callable, str] = "bytes") -> Union[str, bytes]:
        """
        Decrypts the given ciphertext value using the secret key.

        Args:
            cipher_value (Union[str, bytes]): The ciphertext value to decrypt.
            serialization (Union[Callable, str]): The serialization type or class.

        Return:
            Union[str, bytes]: The decrypted plaintext value, deserialized as specified.
        """

        loaded_cipher_value = cipher_value
        if isinstance(cipher_value, str):
            serialization = load_serialization(serialization)

            loaded_cipher_value = serialization.decode(cipher_value)

        secret_key = self.key_pair.get_secret_key().secret_key
        plain_value = py_ntru.decrypt(secret_key, loaded_cipher_value)

        serialized_plain_value = plain_value
        try:
            serialized_plain_value = plain_value.decode('utf-8')
        except (UnicodeDecodeError, TypeError):
            pass

        return serialized_plain_value
