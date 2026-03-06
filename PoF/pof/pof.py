"""Cross-platform Proof of Work (PoF) system for Flask applications.

Provides DDoS protection and bot filtering through cryptographic challenges
with persistent secret key storage and comprehensive security features.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
from functools import wraps
from typing import Any, Callable
from urllib.parse import urlparse

from werkzeug.wrappers.response import Response as WerkzeugResponse
from flask import Flask, g, make_response, redirect, render_template, request, Response

from .detectors import DetectionManager, IPSetDetector, BaseResult


BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


class PoF:
    """Cross-platform Proof of Work (PoW) system for Flask applications.

    Provides DDoS protection, bot filtering, and IP group lookup functionality
    through cryptographic challenges with persistent secret key storage.

    Attributes:
        difficulty (int): Number of leading zeros required in hash solution.
        expiry_time (int): Cookie expiration time in seconds.
        challenge_ttl (int): Challenge time-to-live in seconds.
        secret_key_file (str): Path to persistent secret key file.
        redirect_after_verification (bool): Whether to redirect after verification.
        dedicated_route (str | None): Flask route path for dedicated captcha page.
        detection_methods (list): List of detection methods to use.

    Detection System:
        The system uses a pluggable detection architecture with multiple detection methods:
        - IPSet: IP-based detection using local JSON file with IP group mappings
        - UserAgent: User-Agent string analysis for bot detection
        - IPApi: IP-API.com service for proxy/hosting detection

        Developers can configure which detection methods to use and customize their settings.
    """

    _secret_key: str | None = None
    _lock: threading.Lock = threading.Lock()
    _solved_challenges: dict[str, int] = {}
    _challenges_lock: threading.Lock = threading.Lock()
    _protected_routes: set[str] = set()
    _secret_key_file: str | None = None
    _detection_manager: DetectionManager | None = None

    def __init__(
        self,
        app: Flask | None = None,
        difficulty: int = 4,
        expiry_time: int = 3600,
        challenge_ttl: int = 300,
        secret_key_file: str | None = None,
        redirect_after_verification: bool = False,
        dedicated_route: str | None = None,
        detection_methods: list | None = None,
        ipset_file: str | None = None,
    ) -> None:
        """Initialize PoF instance.

        Args:
            app: Flask application instance (optional).
            difficulty: Number of leading zeros required in hash solution.
            expiry_time: Cookie expiration time in seconds.
            challenge_ttl: Challenge time-to-live in seconds.
            secret_key_file: Path to persistent secret key file.
            redirect_after_verification: Whether to redirect after verification.
            dedicated_route: Flask route path for dedicated captcha page.
            detection_methods: List of detection methods to use (None for default).
            ipset_file: Path to JSON file containing IP group mappings.
        """
        self.app: Flask | None = app
        self.difficulty: int = difficulty
        self.expiry_time: int = expiry_time
        self.challenge_ttl: int = challenge_ttl
        self.secret_key_file: str = secret_key_file or "pof_secret.key"
        self.dedicated_route: str | None = dedicated_route
        self.redirect_after_verification: bool = (
            redirect_after_verification if dedicated_route is None else True
        )
        self.ipset_file: str = ipset_file or "ipset.json"
        self.detection_methods = detection_methods

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Initialize the PoF extension with a Flask app."""
        self.app = app
        app.config.setdefault("POF_SECRET_KEY", None)

        PoF._secret_key_file = app.config.get(
            "POF_SECRET_KEY_FILE", self.secret_key_file
        )

        if PoF._detection_manager is None:
            PoF._detection_manager = self._create_detection_manager(app)

        self._ensure_secret_key(app)

        if self.dedicated_route:

            app.add_url_rule(
                self.dedicated_route,
                endpoint="pof_captcha_route",
                view_func=self._handle_challenge,
                methods=["GET", "POST"],
            )
        if not self.redirect_after_verification:
            app.after_request(self._set_pof_cookie_from_g)

    def _create_detection_manager(self, app: Flask) -> DetectionManager:
        """Create and configure the detection manager.

        Args:
            app: Flask application instance

        Returns:
            Configured DetectionManager instance
        """
        manager = DetectionManager()

        if self.detection_methods:
            for detector in self.detection_methods:
                manager.add_detector(detector)
        else:
            ipset_file = app.config.get("POF_IPSET_FILE", self.ipset_file)
            ipset_detector = IPSetDetector(enabled=True, ipset_file=ipset_file)
            manager.add_detector(ipset_detector)

        return manager

    def protect(self) -> Callable:
        """Decorator to protect routes with proof of work verification."""

        def decorator(f: Callable) -> Callable:
            self._protected_routes.add(f.__name__)

            @wraps(f)
            def decorated_function(
                *args: Any, **kwargs: Any
            ) -> str | Response | WerkzeugResponse:
                if self.is_verified:
                    return f(*args, **kwargs)
                return self._handle_challenge(original_function=f, *args, **kwargs)

            return decorated_function

        return decorator

    def challenge(self) -> str | Response | WerkzeugResponse:
        """Handle proof-of-work challenge and verification flow."""
        return self._handle_challenge(always_redirect=True)

    def client_detection_results(self, ip: str | None = None) -> dict:
        """Get the detection results for a client.

        Args:
            ip: IP address to check (defaults to request IP)

        Returns:
            Dictionary mapping detector names to results
        """
        if PoF._detection_manager is None:
            return {}

        if ip:
            results = {}
            for detector in PoF._detection_manager.detectors:
                if not detector.enabled:
                    continue

                detector_name = detector.__class__.__name__
                try:
                    if "UserAgent" in detector_name:
                        continue
                    if "Api" in detector_name:
                        result = detector.detect_with_cache(ip=ip)
                    else:
                        result = detector.detect_with_cache(ip=ip, user_agent="")

                    results[detector_name] = result
                except Exception as e:
                    print(f"Error in detector {detector_name}: {e}")
                    results[detector_name] = BaseResult()

            return results

        return PoF._detection_manager.detect_for_client()

    @property
    def flow_id(self) -> str:
        """Get the flow ID."""
        return self._client_flow_id(self._get_user_info_hash())

    @property
    def is_bot(self) -> bool:
        """Check if the current request is from a bot."""
        if PoF._detection_manager is None:
            return False
        return any(result.is_bot for result in self.client_detection_results().values())

    @property
    def is_verified(self) -> bool:
        """Check if the user is verified."""
        pof_cookie = request.cookies.get("pof_verified")
        return self._verify_cookie(pof_cookie)

    @classmethod
    def _get_secret_key(cls, app: Flask) -> str:
        """Thread-safe method to get the secret key."""
        if cls._secret_key is None:
            with cls._lock:
                if cls._secret_key is None:
                    secret_key = app.config.get("POF_SECRET_KEY")
                    if not isinstance(secret_key, str):
                        raise ValueError("POF_SECRET_KEY must be a string")
                    cls._secret_key = secret_key
        return cls._secret_key

    def _generate_challenge(self, user_info_hash: str) -> tuple[str, str]:
        """Generate HMAC-signed proof of work challenge."""
        if self.app is None:
            raise RuntimeError("PoF not initialized with Flask app")

        challenge = secrets.token_hex(16)
        timestamp = int(time.time())
        challenge_data = f"{challenge}:{timestamp}:{user_info_hash}"

        secret_key = self._get_secret_key(self.app)
        signature = hmac.new(
            secret_key.encode(), challenge_data.encode(), hashlib.sha256
        ).hexdigest()

        return challenge, f"{challenge_data}:{signature}"

    def _verify_solution(
        self, challenge_data: str, nonce: str, user_info_hash: str
    ) -> bool:
        """Verify proof of work solution with security checks."""
        try:
            if not self._verify_challenge_signature(challenge_data):
                return False

            parts = challenge_data.split(":")
            if len(parts) < 3:
                return False

            challenge_hex, timestamp_str, user_hash = parts[0], parts[1], parts[2]
            current_time = int(time.time())

            if current_time - int(timestamp_str) > self.challenge_ttl:
                return False
            if user_hash != user_info_hash:
                return False

            challenge_key = f"{challenge_hex}:{user_hash}"

            with self._challenges_lock:
                self._cleanup_old_challenges()
                combined = f"{challenge_hex}{nonce}"
                hash_result = hashlib.sha256(combined.encode()).hexdigest()
                is_valid_solution = hash_result.startswith("0" * self.difficulty)

                if is_valid_solution and challenge_key not in self._solved_challenges:
                    self._solved_challenges[challenge_key] = current_time
                    return True
                return False
        except (KeyError, TypeError, ValueError, IndexError):
            return False

    def _create_verification_cookie(self, user_info_hash: str) -> str:
        """Create an HMAC-signed verification cookie."""
        if self.app is None:
            raise RuntimeError("PoF not initialized with Flask app")

        timestamp = int(time.time())
        cookie_data = f"{timestamp}:{user_info_hash}"

        secret_key = self._get_secret_key(self.app)
        signature = hmac.new(
            secret_key.encode(), cookie_data.encode(), hashlib.sha256
        ).hexdigest()
        return f"{cookie_data}:{signature}"

    def _verify_cookie(self, cookie_value: str | None) -> bool:
        """Verify an HMAC-signed cookie with expiry and user checks."""
        if not cookie_value or self.app is None:
            return False
        try:
            parts = cookie_value.split(":")
            if len(parts) != 3 or not parts[2]:
                return False

            timestamp_str, user_id, signature = parts
            cookie_data = f"{timestamp_str}:{user_id}"

            secret_key = self._get_secret_key(self.app)
            expected_signature = hmac.new(
                secret_key.encode(), cookie_data.encode(), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                return False

            timestamp = int(timestamp_str)
            current_time = int(time.time())
            current_user_id = self._get_user_info_hash()
            return (
                current_time - timestamp <= self.expiry_time
                and user_id == current_user_id
            )
        except (ValueError, TypeError, IndexError):
            return False

    def _client_flow_id(self, user_info_hash: str) -> str:
        """Generate a client flow ID based on the user info hash."""
        digest = bytes.fromhex(user_info_hash)
        key_bytes = digest[:12]
        encoded = self._base62_encode(key_bytes)

        if len(encoded) > 16:
            encoded = encoded[:16]
        else:
            encoded = encoded.rjust(16, "0")

        return encoded

    def _handle_challenge(
        self,
        *args: Any,
        original_function: Callable | None = None,
        always_redirect: bool = False,
        **kwargs: Any,
    ) -> str | Response | WerkzeugResponse:
        """Handle proof-of-work challenge and verification flow."""
        parsed_url = urlparse(request.url)
        current_route = parsed_url.path + (
            "?" + parsed_url.query if parsed_url.query else ""
        )

        if self.dedicated_route and (original_function is not None or always_redirect):
            return redirect(f"{self.dedicated_route}?return_url={current_route}")

        request_data = request.form if request.method == "POST" else request.args
        challenge_data_str = request_data.get("challenge_data")
        nonce = request_data.get("nonce")
        return_url = self._validate_return_url(request_data.get("return_url")) or (
            "/" if original_function is None and not always_redirect else current_route
        )
        user_info_hash = self._get_user_info_hash()
        user_flow_id = self._client_flow_id(user_info_hash)

        if challenge_data_str and nonce:
            if self._verify_solution(challenge_data_str, nonce, user_info_hash):
                cookie_value = self._create_verification_cookie(user_info_hash)
                if (
                    self.redirect_after_verification
                    or always_redirect
                    or original_function is None
                ):
                    response = make_response(redirect(return_url))
                    response.set_cookie(
                        "pof_verified",
                        cookie_value,
                        max_age=self.expiry_time,
                        httponly=True,
                        secure=request.is_secure,
                    )
                    return response
                g.pof_cookie = cookie_value
                if original_function:
                    return original_function(*args, **kwargs)

            challenge, challenge_data = self._generate_challenge(user_info_hash)
            return render_template(
                "challenge_minified.html",
                challenge_data=challenge_data,
                challenge=challenge,
                difficulty=self.difficulty,
                return_url=return_url,
                error="Invalid solution. Please try again.",
                flow_id=user_flow_id,
                method=request.method,
            )

        challenge, challenge_data = self._generate_challenge(user_info_hash)
        method = "GET"
        if hasattr(request, "url_rule") and request.url_rule:
            url_rule = request.url_rule
            if url_rule.methods and "POST" in url_rule.methods:
                method = "POST"
            else:
                method = "GET"

        return render_template(
            "challenge_minified.html",
            challenge_data=challenge_data,
            challenge=challenge,
            difficulty=self.difficulty,
            return_url=return_url if original_function is None else current_route,
            flow_id=user_flow_id,
            method=method,
        )

    def _set_pof_cookie_from_g(self, response: Response) -> Response:
        """Attach PoF cookie from `g` object if it exists."""
        if hasattr(g, "pof_cookie"):
            cookie_value: str = g.pof_cookie
            response.set_cookie(
                "pof_verified",
                cookie_value,
                max_age=self.expiry_time,
                httponly=True,
                secure=request.is_secure,
            )
        return response

    def _get_user_info_hash(self) -> str:
        """Generate SHA256 hash of IP address + User-Agent."""
        ip_address = request.remote_addr or ""
        user_agent = request.headers.get("User-Agent", "")
        user_info = f"{ip_address}:{user_agent}"
        return hashlib.sha256(user_info.encode()).hexdigest()

    def _base62_encode(self, data: bytes) -> str:
        """Encode bytes into a base62 string."""
        num = int.from_bytes(data, "big")
        chars: list[str] = []
        while num > 0:
            num, rem = divmod(num, 62)
            chars.append(BASE62_CHARS[rem])
        return "".join(reversed(chars))

    def _validate_return_url(self, return_url: str | None) -> str | None:
        """Validate return URL to prevent open redirect vulnerabilities."""
        if not return_url:
            return None
        try:
            parsed = urlparse(return_url)
            if (
                parsed.scheme
                or parsed.netloc
                or not return_url.startswith("/")
                or ".." in return_url
            ):
                return None
            return return_url
        except (ValueError, TypeError):
            return None

    def _ensure_secret_key(self, app: Flask) -> None:
        """Ensure a persistent secret key is set, generating if missing."""
        if app.config.get("POF_SECRET_KEY"):
            return
        if not PoF._secret_key_file:
            app.config["POF_SECRET_KEY"] = secrets.token_hex(32)
            return
        try:
            if os.path.exists(PoF._secret_key_file):
                with open(PoF._secret_key_file, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                    if len(key) == 64 and all(c in "0123456789abcdef" for c in key):
                        app.config["POF_SECRET_KEY"] = key
                        return

            os.makedirs(
                os.path.dirname(os.path.abspath(PoF._secret_key_file)), exist_ok=True
            )
            new_key = secrets.token_hex(32)
            temp_file = PoF._secret_key_file + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                _ = f.write(new_key)
                f.flush()
                os.fsync(f.fileno())

            try:
                os.chmod(temp_file, 0o600)
            except (OSError, AttributeError):
                pass

            os.rename(temp_file, PoF._secret_key_file)
            app.config["POF_SECRET_KEY"] = new_key
        except (IOError, OSError):
            app.config["POF_SECRET_KEY"] = secrets.token_hex(32)

    def _cleanup_old_challenges(self) -> None:
        """Remove expired challenges from memory to prevent leaks."""
        current_time = int(time.time())
        expired_keys = [
            key
            for key, timestamp in self._solved_challenges.items()
            if current_time - timestamp > self.challenge_ttl
        ]
        for key in expired_keys:
            del self._solved_challenges[key]

    def _verify_challenge_signature(self, challenge_data: str) -> bool:
        """Verify HMAC signature of challenge data."""
        if self.app is None:
            return False
        try:
            parts = challenge_data.split(":")
            if len(parts) != 4 or not parts[3]:
                return False

            signature = parts[3]
            data_to_verify = ":".join(parts[:3])

            secret_key = self._get_secret_key(self.app)
            expected_signature = hmac.new(
                secret_key.encode(), data_to_verify.encode(), hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except (KeyError, TypeError, IndexError):
            return False
