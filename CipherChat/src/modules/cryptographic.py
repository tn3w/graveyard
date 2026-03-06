import secrets
import base64
import hashlib
import hmac
from typing import Optional


def generate_random_string(length: int, with_numbers: bool = True,
                           with_letters: bool = True,
                           with_special_characters: bool = True) -> str:
    """
    Generates a random string

    :param length: The length of the string
    :param with_numbers: Whether to include numbers
    :param with_letters: Whether letters should be included
    :param with_special_characters: Whether to include special characters
    """

    characters = ''

    if with_numbers:
        characters = '0123456789'

    if with_special_characters:
        characters += r"!\"#$%&'()*+,-.:;<=>?@[\]^_`{|}~"

    if with_letters:
        characters += 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    if characters == '':
        return ''

    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string


class ChecksumValidator:
    """
    To create and validate Sha265 checksums
    """

    @staticmethod
    def generate_checksum(data: bytes) -> str:
        """
        Generate SHA-256 checksum for given bytes.

        :param data: The bytes data for which checksum needs to be generated.
        :return: The SHA-256 checksum.
        """

        sha256 = hashlib.sha256()
        sha256.update(data)
        return sha256.hexdigest()

    @staticmethod
    def validate_checksum(data: bytes, checksum: str) -> bool:
        """
        Validate SHA-256 checksum for given bytes.

        :param data: The bytes data for which checksum needs to be validated.
        :param checksum: The SHA-256 checksum to validate against.
        :return: True if the checksum is valid, False otherwise.
        """

        return checksum == ChecksumValidator.generate_checksum(data)


class Hashing:
    """
    Implementation of secure hashing with SHA256 and 200000 iterations
    """

    def __init__(self, salt: Optional[str] = None, without_salt: bool = False):
        """
        :param salt: The salt, makes the hashing process more secure (Optional)
        :param without_salt: If True, no salt is added to the hash
        """

        self.salt = salt
        self.without_salt = without_salt

    def hash(self, plain_text: str, hash_length: int = 32) -> str:
        """
        Function to hash a plaintext

        :param plain_text: The text to be hashed
        :param hash_length: The length of the returned hashed value
        """

        plain_text = str(plain_text).encode('utf-8')

        if not self.without_salt:
            salt = self.salt
            if salt is None:
                salt = secrets.token_bytes(32)
            else:
                if not isinstance(salt, bytes):
                    try:
                        salt = bytes.fromhex(salt)
                    except (ValueError, TypeError,
                            UnicodeDecodeError, MemoryError):
                        salt = salt.encode('utf-8')
        else:
            salt = b''

        hashed_data = hashlib.pbkdf2_hmac(
            hash_name='sha256',
            password=plain_text,
            salt=salt,
            iterations=200000,
            dklen=hash_length
        )

        if not self.without_salt:
            hashed_value = base64.b64encode(hashed_data).decode('utf-8') + "//" + salt.hex()
        else:
            hashed_value = base64.b64encode(hashed_data).decode('utf-8')

        return hashed_value

    def compare(self, plain_text: str, hashed_value: str) -> bool:
        """
        Compares a plaintext with a hashed value

        :param plain_text: The text that was hashed
        :param hashed_value: The hashed value
        """

        if not self.without_salt:
            salt = self.salt
            if "//" in hashed_value:
                hashed_value, salt = hashed_value.split("//")

            if salt is None:
                raise ValueError("Salt cannot be None if there is no salt in hash")

            salt = bytes.fromhex(salt)
        else:
            salt = b''

        hash_length = len(base64.b64decode(hashed_value))

        comparison_hash = Hashing(salt=salt, without_salt = self.without_salt)\
            .hash(plain_text, hash_length = hash_length).split("//")[0]

        return comparison_hash == hashed_value


class PasswordSigning:
    """
    Functions for signing and verifying data using a password
    """

    def __init__(self, password: Optional[str] = None) -> None:
        """
        Initialize the PasswordSigning instance.

        :param password: Optional. The password to use for signing and verifying data.
                         If not provided, a random password of length 16 will be generated.
        """

        if password is None:
            password = generate_random_string(16)

        self.password = password.encode('utf-8')

    def sign(self, plain_text: str, salt_length: int = 32) -> str:
        """
        Sign the provided plain text using the password.

        :param plain_text: The plain text to be signed.
        :param salt_length: The length of the salt to be used for key derivation (default is 32).
        :return: The signature of the plain text concatenated with the salt, separated by '//'.
        """

        salt = secrets.token_bytes(salt_length)
        key = hashlib.pbkdf2_hmac('sha256', self.password, salt, 200000)

        message = bytes(plain_text, 'utf-8')
        signature = hmac.new(key, message, hashlib.sha256).hexdigest()
        return signature + '//' + salt.hex()

    def compare(self, plain_text: str, signature: str) -> bool:
        """
        Compare the provided plain text with its signature to verify authenticity.

        :param plain_text: The plain text to be compared with the signature.
        :param signature: The signature of the plain text concatenated with the salt.
        :return: Whether the signature matches the expected signature for the plain text.
        """

        signature_text, salt = signature.split('//')[:2]

        key = hashlib.pbkdf2_hmac('sha256', self.password, bytes.fromhex(salt), 200000)
        message = bytes(plain_text, 'utf-8')
        expected_signature = hmac.new(key, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_signature, signature_text)
