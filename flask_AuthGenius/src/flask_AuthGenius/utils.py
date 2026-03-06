import os
import random
import re
import io
import base64
import threading
import json
from time import time
import ipaddress
from typing import Optional, Union, Tuple
import mimetypes
import imghdr
from io import BytesIO
from urllib.parse import urlparse, urlunparse, parse_qs, quote
import hashlib
import secrets
from PIL import Image, ImageDraw, ImageFont, ImageOps
import sys
from urllib.parse import urlparse
import pkg_resources
from cryptography.exceptions import InvalidKey, InvalidTag, UnsupportedAlgorithm, AlreadyFinalized
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import threading
from werkzeug import Request
from jinja2 import Environment, select_autoescape, Undefined
from bs4 import BeautifulSoup, Tag
from googletrans import Translator
from captcha.image import ImageCaptcha
import requests
import magic
import pyotp
import qrcode

if __name__ == "__main__":
    sys.exit(2)

try:
    CURRENT_DIR_PATH = pkg_resources.resource_filename('flask_AuthGenius', '')
except ModuleNotFoundError:
    CURRENT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(CURRENT_DIR_PATH, 'data')

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok = True)

ASSETS_DIR = os.path.join(CURRENT_DIR_PATH, 'assets')
TEMPLATE_DIR_PATH = os.path.join(CURRENT_DIR_PATH, 'templates')
PROFILE_PICTURES_PATH = os.path.join(ASSETS_DIR, "profile_pictures.json")
FONTS = [
    os.path.join(ASSETS_DIR, "Comic_Sans_MS.ttf"),
    os.path.join(ASSETS_DIR, "Droid_Sans_Mono.ttf"),
    os.path.join(ASSETS_DIR, "Helvetica.ttf")
]

USER_AGENTS = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.3", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.1", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.3", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.2 Safari/605.1.1", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.1", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.1"]
IP_API_CACHE_PATH = os.path.join(DATA_DIR, "ipapi-cache.json")
IP_INFO_KEYS = ['continent', 'continentCode', 'country', 'countryCode', 'region', 'regionName', 'city', 'district', 'zip', 'lat', 'lon', 'timezone', 'offset', 'currency', 'isp', 'org', 'as', 'asname', 'reverse', 'mobile', 'proxy', 'hosting', 'time']
USERS_PATH = os.path.join(DATA_DIR, "users.json")

LANGUAGES_FILE_PATH = os.path.join(ASSETS_DIR, 'languages.json')
TRANSLATIONS_FILE_PATH = os.path.join(DATA_DIR, 'translations.json')


def error(error_message: str) -> None:
    """
    Prints an error in the console

    :param error_message: The error message
    """

    error_message = "[flask_AuthGenius Error] " + error_message
    print("\033[91m" + error_message + "\033[0m")


def get_scheme(request: Request) -> str:
    """
    Retrieve the scheme (HTTP or HTTPS) used in the request.

    :param request: The Flask request object.
    :return: The scheme used in the request ('http' or 'https').
    """

    scheme = request.headers.get('X-Forwarded-Proto', '')
    if scheme not in ['https', 'http']:
        if request.is_secure:
            scheme = 'https'
        else:
            scheme = 'http'

    return scheme


def is_email(text: str) -> bool:
    return re.match(r'^[\w\.-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$', text)


def is_valid_url(url) -> bool:
    """
    Check if a given URL is valid.

    :param url: The URL to be validated.
    :return: True if the URL is valid, otherwise False.
    """

    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme not in ['http', 'https']:
            return False

        domain = parsed_url.netloc
        if not domain:
            return False

        domain_pattern = re.compile(
            r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        )
        return bool(domain_pattern.match(domain))

    except ValueError:
        pass

    return False

def get_url_from_request(request: Request) -> str:
    """
    Extracts the URL from the Flask request object.

    :param request: The Flask request object.
    :return: The URL reconstructed based on the request object.
    """

    scheme = get_scheme(request)
    return scheme + '://' + request.url.split('://')[1]


def remove_args_from_url(url: str) -> str:
    """
    Removes all query parameters (query strings) from a given URL.

    :param: The URL from which query parameters need to be removed.
    :return: The cleaned URL with no query parameters.
    """

    parsed_url = urlparse(url)

    cleaned_url = urlunparse(
        (parsed_url.scheme, parsed_url.netloc,
         parsed_url.path, '', '', '')
    )

    return cleaned_url


def get_domain_from_url(url: str) -> str:
    """
    Extracts the domain from a given URL.

    :param url: The URL from which to extract the domain.
    :return: The domain extracted from the URL.
    """

    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')
    if len(domain_parts) > 2:
        domain = '.'.join(domain_parts[-2:])
    else:
        domain = parsed_url.netloc
    return domain


def get_path_from_url(url: str) -> Optional[str]:
    """
    Extracts the path component from a given URL.

    :param url: The URL from which to extract the path.
    :return: The path component of the URL, or None if the URL
             is invalid or does not contain a path.
    """

    parsed_url = urlparse(url)
    if isinstance(parsed_url.path, str):
        return parsed_url.path

    return None


def convert_image_to_base64(file_path: str) -> Optional[str]:
    """
    Converts an image file into Base64 Web Format

    :param file_path: The path to the image file
    """

    if not os.path.isfile(file_path):
        return

    with open(file_path, 'rb') as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        data_url = f'data:{mime_type};base64,{encoded_image}'

        return data_url


def generate_website_logo(name: str) -> str:
    """
    Generates a website logo matching the name

    :param name: Name whose first two letters appear on the logo
    """

    size = 200
    background_color = tuple(random.randint(0, 255) for _ in range(3))

    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([(0, 0), (size, size)], fill=background_color)

    brightness = 0.299 * background_color[0] + 0.587 * background_color[1] + 0.114 * background_color[2]
    text_color = (255, 255, 255) if brightness < 128 else (0, 0, 0)

    font = ImageFont.truetype(random.choice(FONTS), 80)

    initials = name[:2].upper()

    text_bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_position = ((size - text_width) // 2, (size - text_height) // 2 - 20)

    draw.text(text_position, initials, font=font, fill=text_color)

    image_buffer = BytesIO()
    image.save(image_buffer, format="PNG")

    image_base64 = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
    return "data:image/png;base64," + image_base64


def generate_random_profile_picture() -> Tuple[str, int]:
    """
    Generates a random profile picture and its index
    by loading a list of profile pictures
    """

    profile_pictures = JSON.load(PROFILE_PICTURES_PATH)

    random_profile_picture = random.choice(profile_pictures)
    random_profile_picture_index = profile_pictures.index(random_profile_picture)

    return random_profile_picture, random_profile_picture_index


def generate_random_string(length: int, with_punctuation: bool = True,
                           with_letters: bool = True) -> str:
    """
    Generates a random string

    :param length: The length of the string
    :param with_punctuation: Whether to include special characters
    :param with_letters: Whether letters should be included
    """

    characters = "0123456789"

    if with_punctuation:
        characters += r"!\"#$%&'()*+,-.:;<=>?@[\]^_`{|}~"

    if with_letters:
        characters += "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    random_string = ''.join(secrets.choice(characters) for _ in range(length))
    return random_string


def is_current_route(request: Request, path: str):
    """
    Helper function to determine if the provided path matches the current route or endpoint.

    :param path: The path to check against the current route or endpoint
    """

    url_path = urlparse(request.url).path
    url_endpoint = request.endpoint

    url = url_path
    if not "/" in path:
        url = url_endpoint

    if '*' in path:
        real_path = path.replace("*", "")
        if (path.startswith("*") and path.endswith("*") and real_path in url) or \
            (path.startswith("*") and url.endswith(real_path)) or \
                (path.endswith("*") and url.startswith(real_path)):
            return True
        first_part, second_part = path.split("*")[0], path.split("*")[1]

        if url.startswith(first_part) and url.endswith(second_part):
            return True

    else:
        if path == url:
            return True
    
    return False


def shorten_ipv6(ip_address: str) -> str:
    """
    Minimizes each ipv6 Ip address to be able to compare it with others
    
    :param ip_address: An ipv4 or ipv6 Ip address
    """

    try:
        return str(ipaddress.IPv6Address(ip_address).compressed)
    except:
        return ip_address


UNWANTED_IPS = ["127.0.0.1", "192.168.0.1", "10.0.0.1", "10.2.0.2",
                "192.0.2.1", "198.51.100.1", "203.0.113.1"]
IPV4_PATTERN = r'^(\d{1,3}\.){3}\d{1,3}$'
IPV6_PATTERN = (
    r'^('
    r'([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|:'
    r'|::([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}'
    r'|[0-9a-fA-F]{1,4}::([0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}'
    r'|([0-9a-fA-F]{1,4}:){1,2}:([0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}'
    r'|([0-9a-fA-F]{1,4}:){1,3}:([0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}'
    r'|([0-9a-fA-F]{1,4}:){1,4}:([0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}'
    r'|([0-9a-fA-F]{1,4}:){1,5}:([0-9a-fA-F]{1,4}:){0,1}[0-9a-fA-F]{1,4}'
    r'|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}'
    r'|([0-9a-fA-F]{1,4}:){1,7}|:((:[0-9a-fA-F]{1,4}){1,7}|:)'
    r'|([0-9a-fA-F]{1,4}:)(:[0-9a-fA-F]{1,4}){1,7}'
    r'|([0-9a-fA-F]{1,4}:){2}(:[0-9a-fA-F]{1,4}){1,6}'
    r'|([0-9a-fA-F]{1,4}:){3}(:[0-9a-fA-F]{1,4}){1,5}'
    r'|([0-9a-fA-F]{1,4}:){4}(:[0-9a-fA-F]{1,4}){1,4}'
    r'|([0-9a-fA-F]{1,4}:){5}(:[0-9a-fA-F]{1,4}){1,3}'
    r'|([0-9a-fA-F]{1,4}:){6}(:[0-9a-fA-F]{1,4}){1,2}'
    r'|([0-9a-fA-F]{1,4}:){7}(:[0-9a-fA-F]{1,4}):)$'
)


def is_valid_ip(ip_address: Optional[str] = None,
                without_filter: bool = False) -> bool:
    """
    Checks whether the current Ip is valid
    
    :param ip_address: Ipv4 or Ipv6 address (Optional)
    """

    if not without_filter:
        if not isinstance(ip_address, str)\
            or ip_address is None\
            or ip_address in UNWANTED_IPS:
            return False

    ipv4_regex = re.compile(IPV4_PATTERN)
    ipv6_regex = re.compile(IPV6_PATTERN)

    if ipv4_regex.match(ip_address):
        octets = ip_address.split('.')
        if all(0 <= int(octet) <= 255 for octet in octets):
            return True
    elif ipv6_regex.match(ip_address):
        return True

    return False


def get_client_ip(request: Request) -> Union[Optional[str], bool]:
    """
    Get the client IP in v4 or v6
    """

    invalid_ips = []

    client_ip = request.remote_addr
    invalid_ips.append(client_ip)
    if is_valid_ip(client_ip):
        client_ip = shorten_ipv6(client_ip)
        return client_ip, False

    other_client_ips = [
        request.environ.get('HTTP_X_REAL_IP', None),
        request.environ.get('REMOTE_ADDR', None),
        request.environ.get('HTTP_X_FORWARDED_FOR', None),
    ]

    for client_ip in other_client_ips:
        invalid_ips.append(client_ip)
        if is_valid_ip(client_ip):
            client_ip = shorten_ipv6(client_ip)
            return client_ip, False

    try:
        client_ip = request.headers.getlist('X-Forwarded-For')[0].rpartition(' ')[-1]
    except (IndexError, AttributeError, ValueError, TypeError):
        pass
    else:
        invalid_ips.append(client_ip)
        if is_valid_ip(client_ip):
            client_ip = shorten_ipv6(client_ip)
            return client_ip, False

    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-Ip',
        'CF-Connecting-IP',
        'True-Client-Ip',
    ]

    for header in headers_to_check:
        if header in request.headers:
            client_ip = request.headers[header]
            client_ip = client_ip.split(',')[0].strip()
            invalid_ips.append(client_ip)
            if is_valid_ip(client_ip):
                client_ip = shorten_ipv6(client_ip)
                return client_ip, False

    for invalid_ip in invalid_ips:
        if isinstance(invalid_ip, str):
            if is_valid_ip(invalid_ip, True):
                return invalid_ip, True

    for invalid_ip in invalid_ips:
        if isinstance(invalid_ip, str):
            return invalid_ip, True

    return None, False


def random_user_agent() -> str:
    "Generates a random user agent to bypass Python blockades"

    return secrets.choice(USER_AGENTS)


def get_ip_info(ip_address: str) -> dict:
    """
    Function to query IP information with cache con ip-api.com

    :param ip_address: The client IP
    """

    ip_api_cache = JSON.load(IP_API_CACHE_PATH, {})

    for hashed_ip, crypted_data in ip_api_cache.items():
        comparison = Hashing().compare(ip_address, hashed_ip)
        if comparison:
            data = SymmetricEncryption(ip_address).decrypt(crypted_data)

            data_json = {}
            for i in range(23):
                data_json[IP_INFO_KEYS[i]] = {"True": True, "False": False}\
                    .get(data.split("-&%-")[i], data.split("-&%-")[i])

            if int(time()) - int(data_json["time"]) > 518400:
                del ip_api_cache[hashed_ip]
                break

            return data_json
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}?fields=66846719",
            headers = {"User-Agent": random_user_agent()},
            timeout = 3
        )
        response.raise_for_status()
    except Exception as e:
        error("ip-api.com could not be requested or did not provide a correct answer: " + e)
        return

    if response.ok:
        response_json = response.json()
        if response_json["status"] == "success":
            del response_json["status"], response_json["query"]
            response_json["time"] = int(time())
            response_string = '-&%-'.join([str(value) for value in response_json.values()])

            crypted_response = SymmetricEncryption(ip_address).encrypt(response_string)
            hashed_ip = Hashing().hash(ip_address)

            ip_api_cache[hashed_ip] = crypted_response
            JSON.dump(ip_api_cache, IP_API_CACHE_PATH)

            return response_json

    error("ip-api.com could not be requested or did not provide a correct answer")
    return None


def is_valid_image(image_data: bytes) -> bool:
    """
    Checks the validity of the given image data.

    :param image_data: Bytes representing the image.
    """

    try:
        image_format = imghdr.what(None, h=image_data)
        if not image_format:
            return False

        mime = magic.Magic()
        image_type = mime.from_buffer(image_data)

        allowed_types = ["image/jpeg", "image/png", "image/webp"]

        if image_type not in allowed_types:
            return False

        return True
    except:
        return False


def resize_image(image_data: bytes, target_size: tuple = (100, 100)) -> Optional[bytes]:
    """
    Resizes the given image data to the specified target size.

    :param image_data: Bytes representing the image.
    :param target_size: Tuple representing the target size (width, height).
    """

    try:
        image = Image.open(BytesIO(image_data))
        resized_image = ImageOps.fit(image, target_size, method=0, bleed=0.0, centering=(0.5, 0.5))

        bytes_io = BytesIO()
        resized_image.save(bytes_io, format='WEBP', quality=85)

        return bytes_io.getvalue()
    except:
        return None


def get_random_item(items: list, seconds: int) -> any:
    """
    Selects a random item from the provided list of items based on the current hour..

    :param items: A list of items from which to choose randomly.
    :return: The randomly selected item from the list.
    """

    current_hour = int(time() / seconds)

    random.seed(current_hour)
    selected_item = random.choice(items)

    return selected_item


file_locks = dict()

class JSON:
    "Class for loading / saving JavaScript Object Notation (= JSON)"

    @staticmethod
    def load(file_path: str, default: Union[dict, list] = None) -> Union[dict, list]:
        """
        Function to load a JSON file securely.

        :param file_path: The JSON file you want to load
        :param default: Returned if no data was found
        """

        if not os.path.isfile(file_path):
            if default is None:
                return []
            return default

        if not file_path in file_locks:
            file_locks[file_path] = threading.Lock()

        with file_locks[file_path]:
            with open(file_path, "r", encoding = "utf-8") as file:
                data = json.load(file)
            return data

    @staticmethod
    def dump(data: Union[dict, list], file_path: str) -> None:
        """
        Function to save a JSON file securely.
        
        :param data: The data to be stored should be either dict or list
        :param file_path: The file to save to
        """

        file_directory = os.path.dirname(file_path)
        if not os.path.isdir(file_directory):
            error("JSON: Directory '" + file_directory + "' does not exist.")
            return

        if not file_path in file_locks:
            file_locks[file_path] = threading.Lock()

        with file_locks[file_path]:
            with open(file_path, "w", encoding = "utf-8") as file:
                json.dump(data, file)


class Hashing:
    """
    A utility class for hashing and comparing hashed values.
    """

    def __init__(self, salt: Optional[str] = None,
                 without_salt: bool = False, iterations: int = 10000,
                 urlsafe: bool = False):
        """
        :param salt: The salt value to be used for hashing.
        :param without_salt: If True, hashing will be done without using salt.
        :param iterations: The number of iterations for the key derivation function.
        :param urlsafe: If True, base64 encoding will use URL-safe characters.  
        """

        self.salt = salt
        self.without_salt = without_salt
        self.iterations = iterations
        self.urlsafe = urlsafe
        self.encoding = base64.b64encode if not urlsafe else base64.urlsafe_b64encode
        self.decoding = base64.b64decode if not urlsafe else base64.urlsafe_b64decode

    def hash(self, plain_text: str, hash_length: int = 8) -> str:
        """
        Hashes the provided plain text using PBKDF2 with SHA-256.

        :param plain_text: The plain text to be hashed.
        :param hash_length: The length of the hashed value in bytes.
        :return: The hashed value encoded as a string.
        """

        plain_text = str(plain_text).encode('utf-8')

        if not self.without_salt:
            salt = self.salt
            if salt is None:
                salt = secrets.token_bytes(16)
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
            iterations=self.iterations,
            dklen=hash_length
        )

        hashed_value = self.encoding(hashed_data).decode('utf-8')
        if not self.without_salt:
            hashed_value += "//" + salt.hex()

        return hashed_value

    def compare(self, plain_text: str, hashed_value: str) -> bool:
        """
        Compares a plain text with a hashed value to verify if they match.

        :param plain_text: The plain text to be compared.
        :param hashed_value: The hashed value to compare against.
        :return: True if the plain text matches the hashed value; otherwise, False.
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

        hash_length = len(self.decoding(hashed_value))

        comparison_hash = Hashing(
            salt, self.without_salt, self.iterations, self.urlsafe)\
                .hash(plain_text, hash_length = hash_length).split("//")[0]

        return comparison_hash == hashed_value


class SymmetricEncryption:
    """
    Implementation of symmetric encryption with AES
    """

    def __init__(self, password: Optional[str] = None, salt_length: int = 32):
        """
        :param password: A secure encryption password, should be at least 32 characters long
        :param salt_length: The length of the salt, should be at least 16
        """

        if password is None:
            password = secrets.token_urlsafe(64)

        self.password = password.encode()
        self.salt_length = salt_length

    def encrypt(self, plain_text: str) -> str:
        """
        Encrypts a text

        :param plaintext: The text to be encrypted
        """

        salt = secrets.token_bytes(self.salt_length)

        kdf_ = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf_.derive(self.password)

        iv = secrets.token_bytes(16)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        padder = padding.PKCS7(algorithms.AES.block_size).padder()
        padded_data = padder.update(plain_text.encode()) + padder.finalize()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return base64.urlsafe_b64encode(salt + iv + ciphertext).decode()

    def decrypt(self, cipher_text: str) -> Optional[str]:
        """
        Decrypts a text

        :param ciphertext: The encrypted text
        """

        try:
            cipher_text = base64.urlsafe_b64decode(cipher_text.encode())

            salt, iv, cipher_text = cipher_text[:self.salt_length],\
                cipher_text[self.salt_length:self.salt_length + 16],\
                    cipher_text[self.salt_length + 16:]

            kdf_ = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = kdf_.derive(self.password)

            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            decrypted_data = decryptor.update(cipher_text) + decryptor.finalize()
            plaintext = unpadder.update(decrypted_data) + unpadder.finalize()
        except (InvalidKey, InvalidTag, ValueError,
                UnsupportedAlgorithm, AlreadyFinalized):
            return None

        return plaintext.decode()


class SymmetricData:
    """
    A utility class for symmetric encryption and encoding/decoding data.
    """

    def __init__(self, secret: str):
        """
        :param secret: A secret string to encrypt the data
        """

        self.sym_enc = SymmetricEncryption(secret)

    def encode(self, data: list | dict) -> str:
        """
        Encodes the provided data (list or dictionary) into a string after
        JSON serialization and symmetric encryption.

        :param data: The data (list or dictionary) to be encoded.
        :return: The encoded and encrypted data as a string.
        """

        encoded_data = json.dumps(data)
        return self.sym_enc.encrypt(encoded_data)

    def decode(self, text: str) -> Optional[Union[list, dict]]:
        """
        Decodes the provided encrypted text back into a list or dictionary
        after decryption and JSON deserialization. Returns None if decryption fails.

        :param: The encrypted text to be decoded.
        :return: The decoded data (list or dictionary) if decryption is successful; otherwise, None.
        """

        decrypted_data = self.sym_enc.decrypt(text)
        if decrypted_data is None:
            return None

        return json.loads(decrypted_data)


class NoEncryption:
    """
    A class that provides a no-operation (dummy) implementation for encryption and decryption.
    """

    def __init__(self):
        pass

    def encrypt(self = None, plain_text: str = "Dummy") -> str:
        """
        Dummy encryption method that returns the input plain text unchanged
        """

        return plain_text

    def decrypt(self = None, cipher_text: str = "Dummy") -> str:
        """
        Dummy decryption method that returns the input cipher text unchanged.
        """

        return cipher_text


LANGUAGES = JSON.load(LANGUAGES_FILE_PATH)
LANGUAGE_CODES = [language["code"] for language in LANGUAGES]
THEMES = ['dark', 'light']

def render_template(
        file_name: str,
        request: Request,
        template_dir: Optional[str] = None,
        template_language: Optional[str] = None,
        **args
        ) -> str:
    """
    Renders a template file into HTML content, optionally translating it to the specified language.

    :param file_name: The name of the template file to render.
    :param request: The request object providing information about the client's language preference.
    :param template_dir: The directory path where template files are located. 
                         If not provided, defaults to the 'templates' directory in the 
                         current working directory.
    :param template_language: The language code specifying the language of the template content. 
                              If not provided, defaults to 'en' (English).
    :param **args: Additional keyword arguments to pass to the template rendering function.
    :return: The rendered HTML content of the template.
    """

    if template_dir is None:
        template_dir = TEMPLATE_DIR_PATH

    if template_language is None:
        template_language = "en"

    file_path = os.path.join(template_dir, file_name)

    client_theme, is_default_theme = WebPage.client_theme(request)
    client_language = WebPage.client_language(request)[0]

    args["theme"] = client_theme
    args["is_default_theme"] = is_default_theme
    args["language"] = client_language
    args["alternate_languages"] = LANGUAGE_CODES

    current_url = get_url_from_request(request)

    args["current_url"] = current_url
    args["current_url_char"] = '?' if not '?' in current_url else '&'
    args["current_url_without_args"] = remove_args_from_url(current_url)
    args["only_args"] = current_url.replace(args["current_url_without_args"], "")

    html = WebPage.render_template(file_path = file_path, html = None, **args)
    html = WebPage.add_args(html, request)
    html = WebPage.translate(html, template_language, client_language)
    html = WebPage.minimize(html)

    return html


class WebPage:
    "Class with useful tools for WebPages"

    @staticmethod
    def client_language(request: Request, default: Optional[str] = None) -> Tuple[str, bool]:
        """
        Which language the client prefers

        :param request: An Request object

        :return language: The client languge
        :return is_default: Is Default Value
        """

        language_from_args = request.args.get("language")
        language_from_cookies = request.cookies.get("language")
        language_from_form = request.form.get("language")

        chosen_language = (
            language_from_args
            if language_from_args in LANGUAGE_CODES
            else (
                language_from_cookies
                if language_from_cookies in LANGUAGE_CODES
                else (
                    language_from_form
                    if language_from_form in LANGUAGE_CODES
                    else None
                )
            )
        )

        if chosen_language is None:
            preferred_language = request.accept_languages.best_match(LANGUAGE_CODES)

            if preferred_language is not None:
                return preferred_language, True
        else:
            return chosen_language, False

        if default is None:
            default = "en"

        return default, True

    @staticmethod
    def client_theme(request: Request, default: Optional[str] = None) -> Tuple[str, bool]:
        """
        Which color theme the user prefers
        
        :return theme: The client theme
        :return is_default: Is default Value
        """

        theme_from_args = request.args.get('theme')
        theme_from_cookies = request.cookies.get('theme')
        theme_from_form = request.form.get('theme')

        theme = (
            theme_from_args
            if theme_from_args in THEMES
            else (
                theme_from_cookies
                if theme_from_cookies in THEMES
                else (
                    theme_from_form
                    if theme_from_form in THEMES
                    else None
                )
            )
        )

        if theme is None:
            if default is None:
                default = "dark"

            return default, True

        return theme, False

    @staticmethod
    def _minimize_tag_content(html: str, tag: str) -> str:
        """
        Minimizes the content of a given tag
        
        :param html: The HTML page where the tag should be minimized
        :param tag: The HTML tag e.g. "script" or "style"
        """

        tag_pattern = rf'<{tag}\b[^>]*>(.*?)<\/{tag}>'

        def minimize_tag_content(match: re.Match):
            content = match.group(1)
            content = re.sub(r'\s+', ' ', content)
            return f'<{tag}>{content}</{tag}>'

        return re.sub(tag_pattern, minimize_tag_content, html, flags=re.DOTALL | re.IGNORECASE)

    @staticmethod
    def minimize(html: str) -> str:
        """
        Minimizes an HTML page

        :param html: The content of the page as html
        """

        html = re.sub(r'<!--(.*?)-->', '', html, flags=re.DOTALL)
        html = re.sub(r'\s+', ' ', html)

        html = WebPage._minimize_tag_content(html, 'script')
        html = WebPage._minimize_tag_content(html, 'style')
        html = html.replace('\n', '')
        return html

    @staticmethod
    def translate_text(text_to_translate: str, from_lang: str, to_lang: str) -> str:
        """
        Function to translate a text based on a translation file

        :param text_to_translate: The text to translate
        :param from_lang: The language of the text to be translated
        :param to_lang: Into which language the text should be translated
        """

        text_to_translate = text_to_translate.strip('\n ')

        if from_lang == to_lang or not text_to_translate:
            return text_to_translate

        translations = JSON.load(TRANSLATIONS_FILE_PATH, [])

        for translation in translations:
            if translation["text_to_translate"] == text_to_translate\
                and translation["from_lang"] == from_lang\
                    and translation["to_lang"] == to_lang:
                return translation["translated_output"]

        translator = Translator()

        try:
            translated_output = translator.translate(
                text_to_translate, src=from_lang, dest=to_lang
                ).text

            if translated_output is None:
                return text_to_translate
        except (UnicodeEncodeError, UnicodeDecodeError,
                ValueError, AttributeError, TypeError):
            return text_to_translate

        translation = {
            "text_to_translate": text_to_translate, 
            "from_lang": from_lang,
            "to_lang": to_lang, 
            "translated_output": translated_output
        }
        translations.append(translation)

        JSON.dump(translations, TRANSLATIONS_FILE_PATH)

        return translated_output

    @staticmethod
    def translate(html: str, from_lang: str, to_lang: str) -> str:
        """
        Function to translate a page into the correct language

        :param html: The content of the page as html
        :param from_lang: The language of the text to be translated
        :param to_lang: Into which language the text should be translated
        """

        def translate_tag(html_tag: Tag, from_lang: str, to_lang: str):
            for tag in html_tag.find_all(text=True):
                if hasattr(tag, 'attrs'):
                    if 'ntr' in tag.attrs:
                        continue

                if tag.parent.name not in ['script', 'style']:
                    translated_text = WebPage.translate_text(tag, from_lang, to_lang)
                    tag.replace_with(translated_text)

            translated_html = str(html_tag)
            return translated_html

        soup = BeautifulSoup(html, 'html.parser')

        tags = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5',
                              'h6', 'a', 'p', 'button'])
        for tag in tags:
            if str(tag) and 'ntr' not in tag.attrs:
                translate_tag(tag, from_lang, to_lang)

        inputs = soup.find_all('input')
        for input_tag in inputs:
            if input_tag.has_attr('placeholder') and 'ntr' not in input_tag.attrs:
                input_tag['placeholder'] = WebPage.translate_text(
                    input_tag['placeholder'].strip(), from_lang, to_lang
                    )

        head_tag = soup.find('head')
        if head_tag:
            title_element = head_tag.find('title')
            if title_element:
                title_element.string = WebPage.translate_text(
                    title_element.text.strip(), from_lang, to_lang
                    )

            meta_title = head_tag.find('meta', attrs={'name': 'title'})
            if meta_title and 'content' in meta_title.attrs:
                meta_title['content'] = WebPage.translate_text(
                    meta_title['content'].strip(), from_lang, to_lang
                )

            meta_description = head_tag.find('meta', attrs={'name': 'description'})
            if meta_description and 'content' in meta_description.attrs:
                meta_description['content'] = WebPage.translate_text(
                    meta_description['content'].strip(), from_lang, to_lang
                )

            meta_keywords = head_tag.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and 'content' in meta_keywords.attrs:
                meta_keywords['content'] = WebPage.translate_text(
                    meta_keywords['content'].strip(), from_lang, to_lang
                )

        translated_html = soup.prettify()
        return translated_html

    @staticmethod
    def render_template(file_path: Optional[str] = None, html: Optional[str] = None, **args) -> str:
        """
        Function to render a HTML template (= insert arguments / translation / minimization)

        :param file_path: From which file HTML code should be loaded (Optional)
        :param html: The content of the page as html (Optional)
        :param args: Arguments to be inserted into the WebPage with Jinja2
        """

        if file_path is None and html is None:
            raise ValueError("Arguments 'file_path' and 'html' are None")

        if not file_path is None:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"File `{file_path}` does not exist")

        class SilentUndefined(Undefined):
            """
            Class to not get an error when specifying a non-existent argument
            """

            def _fail_with_undefined_error(self, *args, **kwargs):
                return None

        env = Environment(
            autoescape=select_autoescape(['html', 'xml']),
            undefined=SilentUndefined
        )

        if html is None:
            with open(file_path, "r", encoding = "utf-8") as file:
                html = file.read()

        template = env.from_string(html)

        html = template.render(**args)

        return html

    @staticmethod
    def add_args(html: str, request: Request) -> str:
        """
        Adds arguments to links and forms in HTML based on the request.

        :param html: The HTML content to which arguments need to be added.
        :param request: The Flask Request object containing information about the current request.
        :return: The HTML content with arguments added to links and forms.
        """

        args = {}

        theme, is_default_theme = WebPage.client_theme(request)
        if not is_default_theme:
            args['theme'] = theme

        language, is_default_language = WebPage.client_language(request)
        if not is_default_language:
            args['language'] = language

        soup = BeautifulSoup(html, 'html.parser')

        def has_argument(url, arg):
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            return arg in query_params

        for anchor in soup.find_all('a'):
            if not 'href' in anchor.attrs:
                continue

            if '://' in anchor['href']:
                anchor_host = get_domain_from_url(anchor['href'])
                if anchor_host != get_domain_from_url(request.url):
                    continue
            elif not anchor['href'].startswith('/') and \
                not anchor['href'].startswith('#') and \
                    not anchor['href'].startswith('?') and \
                        not anchor['href'].startswith('&'):
                continue

            for arg, content in args.items():
                if arg == 'template':
                    anchor_path = get_path_from_url(anchor['href'])
                    if isinstance(anchor_path, str):
                        if not '/signature' in anchor_path:
                            continue

                if not has_argument(anchor['href'], arg):
                    special_character = '?' if '?' not in anchor['href'] else '&'
                    anchor['href'] = anchor['href'] + special_character + arg + '=' + quote(content)

        for form in soup.find_all('form'):
            action = form.get('action')
            if action:
                for arg, content in args.items():
                    if not has_argument(action, arg):
                        special_character = '?' if '?' not in action else '&'
                        form['action'] = action + special_character + arg + '=' + quote(content)

            existing_names = set()
            for input_tag in form.find_all('input'):
                existing_names.add(input_tag.get('name'))

            added_input = ''
            for arg, content in args.items():
                if arg not in existing_names:
                    added_input += f'<input type="hidden" name="{arg}" value="{content}">'

            form_button = form.find('button')
            if form_button:
                form_button.insert_before(BeautifulSoup(added_input, 'html.parser'))
            else:
                form.append(BeautifulSoup(added_input, 'html.parser'))

        html_with_args = soup.prettify()
        return html_with_args


class Captcha:
    """
    Class to generate and verify a captcha
    """

    def __init__(self, captcha_secret: str):
        """
        :param captcha_secret: A secret token that only the server knows to verify the captcha
        """

        self.captcha_secret = captcha_secret

    def generate(self, data: dict) -> Tuple[str, str]:
        """
        Generate a captcha for the client

        :param data: Some client data, that doesn't change
        """

        image_captcha_code = generate_random_string(6, with_punctuation=False).lower()

        data['time'] = int(time())
        minimized_data = json.dumps(data, indent = None, separators = (',', ':'))
        captcha_prove = image_captcha_code + "//" + minimized_data

        crypted_captcha_prove = SymmetricEncryption(self.captcha_secret).encrypt(captcha_prove)

        image_captcha = ImageCaptcha(width=480, height=120, fonts=FONTS)

        captcha_image = image_captcha.generate(image_captcha_code)
        captcha_image_data = base64.b64encode(captcha_image.getvalue()).decode('utf-8')
        captcha_image_data = "data:image/png;base64," + captcha_image_data

        return captcha_image_data, crypted_captcha_prove

    def verify(self, client_input: str, crypted_captcha_prove: str, data: dict) -> Optional[str]:
        """
        Verify a captcha

        :param client_input: The input from the client
        :param crypted_captcha_prove: The encrypted captcha prove generated by the generate function
        :param data: The original client data
        """

        captcha_prove = SymmetricEncryption(self.captcha_secret).decrypt(crypted_captcha_prove)
        if captcha_prove is None:
            return 'time'

        captcha_code, captcha_data = captcha_prove.split("//")
        captcha_data = json.loads(captcha_data)

        if int(time() - captcha_data.get('time', float('inf'))) > 120:
            return 'time'
        del captcha_data['time']
        if captcha_data != data:
            return 'data'
        if captcha_code.lower() != client_input.lower():
            return 'code'

        return None


class TOTP:
    """
    Class representing Time-based One-Time Password (TOTP) functionality.
    """

    def __init__(self) -> None:
        """
        Initialize the TOTP instance.
        """
        self.used_codes = {}

    def _clean_used_codes(self) -> None:
        """
        Clean up the used codes dictionary by removing expired entries.
        """

        new_used_codes = self.used_codes.copy()
        for secret, used_codes in self.used_codes.items():
            new_codes = []
            for used_code, use_time in used_codes:
                if int(time() - use_time) <= 30:
                    new_codes.append((used_code, use_time))

            if len(new_codes) == 0:
                del new_used_codes[secret]
            else:
                new_used_codes[secret] = new_codes

        self.used_codes = new_used_codes

    def _add_to_used_codes(self, used_code: str, secret: str) -> None:
        """
        Add a used code to the tracked dictionary after cleaning expired entries.

        :param used_code: The code that has been used.
        :param secret: The secret associated with the code.
        """

        self._clean_used_codes()

        hashed_secret = Hashing().hash(secret)
        hashed_code = Hashing().hash(used_code)

        used_codes: list = self.used_codes.get(hashed_secret, [])
        used_codes.append((hashed_code, time()))
        self.used_codes[hashed_secret] = used_codes

    def _is_already_used(self, code: str, secret: str) -> bool:
        """
        Check if a given code with its secret has already been used.

        :param code: The code to check.
        :param secret: The secret associated with the code.
        :return: True if the code is already used, False otherwise.
        """

        self._clean_used_codes()

        for hashed_secret, used_codes in self.used_codes.items():
            if Hashing().compare(secret, hashed_secret):
                for used_code in used_codes:
                    if Hashing().compare(code, used_code):
                        return True

        return False

    @staticmethod
    def generate_new(issuer_name: str, user_name: str) -> Tuple[str, str]:
        """
        Generate a new TOTP secret and associated QR code.

        :param issuer_name: The name of the issuer (e.g., the service provider).
        :param user_name: The name of the user.
        :return: A tuple containing the generated secret and a base64 encoded PNG image URI.
        """

        secret = pyotp.random_base32()

        totp = pyotp.TOTP(secret)

        uri = totp.provisioning_uri(user_name, issuer_name = issuer_name)
        qr = qrcode.QRCode()
        qr.add_data(uri)
        qr.make()

        img = qr.make_image(fill='black', back_color='white')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_data = img_bytes.getvalue()
        base64_img = base64.b64encode(img_data).decode('utf-8')

        return secret, 'data:image/png;base64,' + base64_img

    def verify(self, user_inp: str, secret: str) -> bool:
        """
        Verify a user input against a provided secret using TOTP.

        :param user_inp: The user's input code.
        :param secret: The secret to verify against.
        :return: True if the input is valid and not previously used, False otherwise.
        """

        totp = pyotp.TOTP(secret)
        current_code = totp.now()

        if str(user_inp) != str(current_code):
            return False

        if self._is_already_used(current_code, secret):
            return False

        self._add_to_used_codes(current_code, secret)
        return True


class User:

    @staticmethod
    def create(
        password: str, username: Optional[str] = None,
        email: Optional[str] = None, full_name: Optional[str] = None,
        display_name: Optional[str] = None, birthdate: Optional[str] = None,
        gender: Optional[str] = None, country: Optional[str] = None,
        profile_picture: Optional[bytes] = None, profile_picture_index: Optional[int] = None,
        language: Optional[str] = None, theme: Optional[str] = None,
        ip_address: Optional[str] = None, user_agent: Optional[str] = None,
        encrypted_fields: Optional[list] = None, hashed_fieds: Optional[list] = None) -> dict:
        return NotImplementedError('User.create is replaced by auth.UserSystem().create_user')
        """
        Creates a new user with the provided information.

        :param password: The password for the user account. Must be a string.
        :param username: (Optional) The desired username for the user account. If not provided, it defaults to None.
        :param email: (Optional) The email address associated with the user account. If not provided, it defaults to None.
        :param full_name: (Optional) The full name of the user. If not provided, it defaults to None.
        :param display_name: (Optional) The display name for the user. If not provided, it defaults to None.
        :param birthdate: (Optional) The birthdate of the user. If not provided, it defaults to None.
        :param gender: (Optional) The gender of the user. If not provided, it defaults to None.
        :param country: (Optional) The country of residence for the user. If not provided, it defaults to None.
        :param profile_picture: (Optional) A binary representation of the user's profile picture. If not provided, it defaults to None.
        :param profile_picture_index: (Optional) An index representing the profile picture chosen by the user. If not provided, it defaults to None.
        :param language: (Optional) The preferred language for the user interface. If not provided, it defaults to None.
        :param theme: (Optional) The preferred theme for the user interface. If not provided, it defaults to None.
        :param ip_address: (Optional) The IP address from which the user is creating the account. If not provided, it defaults to None.
        :param user_agent: (Optional) The user agent information of the browser or client used by the user. If not provided, it defaults to None.
        :param encrypted_fields: All fields that are to be saved in encrypted form
        :param hashed_fieds: All fields that are to be saved in hashed form

        :return: A dictionary containing the user information.
        """

        user = {"sessions": {}}

        sc = NoEncryption()
        derived_password = None
        if encrypted_fields is not None:
            derived_password, salt = derive_password(password)
            salt = b64encode(salt).decode('utf-8')

            user["enc_salt"] = salt

            sc = SymmetricEncryption(derived_password)
        else:
            encrypted_fields = []

        if display_name is not None:
            user["displayname"] = display_name
        if hashed_fieds is None:
            hashed_fieds = []

        hashing_params = {"username": username, "email": email}
        for name, value in hashing_params.items():
            if value is None:
                continue

            if name in hashed_fieds:
                value = Hashing().hash(value)
            user[name] = value

        encrypted_params = {
            "fullname": full_name, "birthdate": birthdate, 
            "gender": gender, "country": country, "language": language, "theme": theme
        }
        for name, value in encrypted_params.items():
            if value is None:
                continue

            if name in encrypted_fields:
                value = sc.encrypt(value)
            user[name] = value

        if not (profile_picture is None and profile_picture_index is None):
            if profile_picture is None:
                profile_picture = str(profile_picture_index)
            else:
                if is_valid_image(profile_picture):
                    profile_picture = resize_image(profile_picture)
                    if profile_picture is not None:
                        profile_picture = 'data:image/webp;base64,' +\
                            b64encode(profile_picture).decode('utf-8')
                else:
                    profile_picture = None

                if profile_picture is None:
                    _, random_pp_index = generate_random_profile_picture()
                    profile_picture = str(random_pp_index)

        session_id = generate_random_string(6, with_punctuation=False)
        session_token = generate_random_string(24)
        session_token_hash = Hashing().hash(session_token)

        session = {"hash": session_token_hash}

        session_encrypted_params = {"ip": ip_address, "ua": user_agent}
        for name, value in session_encrypted_params.items():
            if value is None:
                continue

            session[name] = value

        user["session"][session_id] = session

        users = JSON.load(USERS_PATH)

        while True:
            user_id = generate_random_string(12, with_punctuation=False)

            is_used = False
            for hashed_user_id, _ in users.items():
                if "id" in hashed_fieds:
                    comparison = Hashing().compare(user_id, hashed_user_id)
                    if comparison:
                        is_used = True
                        break
                else:
                    if hashed_user_id == user_id:
                        is_used = True
                        break

            if is_used:
                continue
            break

        if "id" in hashed_fieds:
            user_id = Hashing().hash(user_id)

        users = JSON.load(USERS_PATH)
        users[user_id] = user

        JSON.dump(users, USERS_PATH)

        return user_id, session_id, session_token, derived_password
